import asyncio
import json
from types import SimpleNamespace

import pytest
from livekit.agents import Agent, StopResponse
from pydantic import ValidationError

from voice_evaluator.agent.patient import PatientAgent
from voice_evaluator.agent.state import PatientState
from voice_evaluator.agent.telemetry import Timeline
from voice_evaluator.config import Settings
from voice_evaluator.evaluation.adjudicator import adjudicate
from voice_evaluator.evaluation.judge import _verify_quote
from voice_evaluator.evaluation.schema import BugCategory, Evidence, Finding, Severity, Source
from voice_evaluator.scenarios.loader import load_one
from voice_evaluator.transcription.merge import MergedTranscript, Turn


def control():
    return load_one("controlled_day_preference").simulation


def test_withheld_values_are_not_in_renderer_context():
    state = PatientState(control(), 42)
    prompt = state.renderer_context()
    assert "Colin Doyle" not in prompt
    assert "1980-04-16" not in prompt
    assert "Friday" not in prompt
    state.target_turn("What is your date of birth?")
    assert "1980-04-16" in state.renderer_context()
    assert "Colin Doyle" not in state.renderer_context()


def test_statement_does_not_unlock_fact():
    state = PatientState(control(), 42)
    state.target_turn("I already have your phone number on file.")
    assert "phone" not in state.available


def test_preference_commits_only_completed_spoken_change():
    state = PatientState(control(), 42)
    state.target_turn("We have an option Tuesday.")
    assert state.preferences["appointment_day"] == "Tuesday"
    assert "Wednesday" in state.renderer_context()
    state.observe_patient_item("Wednesday works.", interrupted=True)
    assert state.change_index == 0
    assert state.preferences["appointment_day"] == "Tuesday"
    state.observe_patient_item("Can we do Wednesday?", interrupted=False)
    assert state.preferences["appointment_day"] == "Wednesday"
    state.target_turn("Wednesday afternoon is available.")
    assert "Friday" in state.renderer_context()
    state.observe_patient_item("Friday would work better.", interrupted=False)
    assert state.preferences["appointment_day"] == "Friday"
    assert [e.value for e in state.events if e.operation == "CORRECT"] == ["Wednesday", "Friday"]
    assert state.verify_literal_output("Book Tuesday please.") == [
        "stale_preference:appointment_day"
    ]


def test_seed_replays_behavior_schedule():
    left, right = PatientState(control(), 17), PatientState(control(), 17)
    for text in ["Hello", "What is your name?", "We have Tuesday", "What time works?"]:
        left.target_turn(text)
        right.target_turn(text)
    assert left.snapshot() == right.snapshot()


async def text_stream(*parts):
    for part in parts:
        yield part


async def test_split_hidden_value_blocked_before_tts(monkeypatch):
    patient = PatientAgent(load_one("controlled_day_preference"), asyncio.Event())
    calls = []

    async def fake_tts(agent, text, settings):
        calls.append("called")
        async for value in text:
            yield value

    monkeypatch.setattr(Agent.default, "tts_node", fake_tts)
    with pytest.raises(StopResponse):
        _ = [x async for x in patient.tts_node(text_stream("My name is Col", "in Doyle."), None)]
    assert calls == []
    assert patient.rejected == ["My name is Colin Doyle."]


async def test_authorized_value_reaches_tts(monkeypatch):
    patient = PatientAgent(load_one("controlled_day_preference"), asyncio.Event())
    patient.state.target_turn("What is your name?")

    async def fake_tts(agent, text, settings):
        async for value in text:
            yield value

    monkeypatch.setattr(Agent.default, "tts_node", fake_tts)
    result = [x async for x in patient.tts_node(text_stream("Colin ", "Doyle."), None)]
    assert result == ["Colin Doyle."]


def test_timing_unknown_is_null_not_zero(tmp_path):
    timeline = Timeline(tmp_path)
    empty = timeline.summary()["sdk_latency"]["llm_node_ttft"]
    assert empty == {"count": 0, "p50_seconds": None, "p95_seconds": None}
    timeline.record("conversation_item_added", metrics={"llm_node_ttft": 0.1, "tts_node_ttfb": 0.2})
    timeline.record("conversation_item_added", metrics={"llm_node_ttft": 0.3})
    assert timeline.summary()["sdk_latency"]["llm_node_ttft"]["p50_seconds"] == 0.2
    assert len((tmp_path / "timeline.jsonl").read_text().splitlines()) == 2


def test_timing_config_rejects_inverted_range():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, endpoint_min_delay=3, endpoint_max_delay=1)


def test_stable_turn_ids_and_exact_speaker_required():
    transcript = MergedTranscript(
        turns=[Turn(index=7, speaker="agent", start=1, end=2, text="Tuesday is available.")]
    )
    valid = {"line": 7, "speaker": "agent", "quote": "Tuesday is available."}
    assert _verify_quote(valid, transcript).quote_verified
    for change in (
        {"line": 0},
        {"line": True},
        {"speaker": "patient"},
        {"quote": "tuesday is available."},
        {"quote": ""},
        {"timestamp": "00:05.000"},
    ):
        assert not _verify_quote(valid | change, transcript).quote_verified
    transcript.turns[0].end = 0.5
    assert not _verify_quote(valid, transcript).quote_verified


def finding():
    return Finding(
        id="f",
        title="claim",
        severity=Severity.HIGH,
        category=BugCategory.GROUNDING,
        source=Source.JUDGE,
        expected="No confirmation without availability",
        actual="Confirmed",
        why_it_matters="Extractor rationale should stay hidden",
        evidence=[
            Evidence(
                turn_index=7, speaker="agent", quote="Tuesday is available.", quote_verified=True
            )
        ],
    )


def test_one_invalid_quote_disqualifies_whole_finding():
    item = finding()
    item.evidence.append(Evidence(quote="invented", quote_verified=False))
    assert not item.has_verified_evidence


def test_adjudicator_is_blind_to_extractor_rationale():
    payload = {}

    def create(**kwargs):
        payload.update(kwargs)
        return SimpleNamespace(
            output_text=json.dumps(
                {"verdict": "not_supported", "reason": "Availability does not establish booking"}
            )
        )

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    transcript = MergedTranscript(
        turns=[Turn(index=7, speaker="agent", start=1, end=2, text="Tuesday is available.")]
    )
    result = adjudicate(
        client, "test", finding(), transcript, load_one("controlled_day_preference")
    )
    assert result[0] == "not_supported"
    assert "Extractor rationale should stay hidden" not in json.dumps(payload)


def test_adjudicator_failure_requires_review():
    def create(**kwargs):
        raise RuntimeError("provider down")

    client = SimpleNamespace(responses=SimpleNamespace(create=create))
    result = adjudicate(
        client, "test", finding(), MergedTranscript(), load_one("controlled_day_preference")
    )
    assert result[0] == "unclear"


def test_error_and_playout_telemetry_uses_sdk_provenance(tmp_path):
    callbacks = {}

    class Session:
        def on(self, name):
            def register(callback):
                callbacks[name] = callback
                return callback

            return register

    failures = []
    timeline = Timeline(tmp_path)
    timeline.subscribe(Session(), on_fatal=lambda: failures.append(True))
    callbacks["error"](
        SimpleNamespace(
            error=SimpleNamespace(recoverable=False), source="secret-credential", created_at=1
        )
    )
    assert failures == [True]
    assert "secret-credential" not in timeline.path.read_text()
    done = []
    handle = SimpleNamespace(
        id="speech-test", interrupted=True, add_done_callback=lambda fn: done.append(fn)
    )
    callbacks["speech_created"](SimpleNamespace(speech_handle=handle, source="generate_reply"))
    done[0](handle)
    assert timeline.events[-1]["payload"]["delivery_status"] == "interrupted"
    assert timeline.events[-1]["payload"]["remote_audibility_verified"] is False


def test_control_schema_cannot_leak_hidden_fact_through_correction():
    from voice_evaluator.scenarios.control import SimulationControl

    data = control().model_dump()
    data["changes"][0]["utterance"] = "Colin Doyle wants Wednesday"
    with pytest.raises(ValidationError, match="withheld"):
        SimulationControl.model_validate(data)


def test_rejected_and_unreviewed_candidates_cannot_enter_verified_report():
    from voice_evaluator.evaluation.schema import CallEvaluation
    from voice_evaluator.reporting import render_bug_report

    item = finding()
    record = CallEvaluation(
        call_id="call-test",
        scenario_id="controlled_day_preference",
        evaluated_at="test",
        deterministic_findings=[item],
    )
    fake = SimpleNamespace(
        evaluation_json="evaluation.json",
        read_json=lambda _: record.model_dump(),
        call_id="call-test",
        dir=SimpleNamespace(name="call-test"),
    )
    report = render_bug_report([fake], verified_only=True)
    assert "Findings: **0**" in report
