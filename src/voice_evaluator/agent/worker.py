"""One local process: connect, record, run LiveKit pipeline, save and disconnect."""

import asyncio
import logging
import os
import sys
import time
from contextlib import contextmanager

from livekit import api, rtc
from livekit.agents import AgentSession, room_io
from livekit.agents.utils import http_context

from voice_evaluator.agent.barge_in import BargeInScheduler
from voice_evaluator.agent.models import build_llm, build_speech
from voice_evaluator.agent.patient import PatientAgent
from voice_evaluator.agent.session import turn_options
from voice_evaluator.agent.telemetry import Timeline
from voice_evaluator.artifacts.store import CallArtifacts, allocate_call_id, next_display_name
from voice_evaluator.config import ASSESSMENT_NUMBER, get_settings
from voice_evaluator.recording.audio import ingest_recording
from voice_evaluator.recording.local import LocalRecorder
from voice_evaluator.scenarios.loader import load_one
from voice_evaluator.telephony.guard import pin_caller_number, resolve_destination

_EXPECTED_SHUTDOWN_CHANNELS = {"_reliable", "_lossy", "_data_track"}


class _ExpectedRoomShutdownFilter(logging.Filter):
    """Drop only LiveKit's three known data-channel close logs at normal shutdown."""

    def filter(self, record):
        if record.name != "livekit" or record.levelno < logging.ERROR:
            return True
        message = record.getMessage()
        prefix = (
            "livekit::rtc_engine::rtc_session:704:livekit::rtc_engine::rtc_session - "
            "publisher data channel '")
        if not message.startswith(prefix) or not message.endswith("' closed unexpectedly"):
            return True
        channel = message[len(prefix) :].split("'", 1)[0]
        return channel not in _EXPECTED_SHUTDOWN_CHANNELS


@contextmanager
def suppress_expected_room_shutdown_logs():
    """Suppress the known LiveKit close notices only during graceful room teardown."""
    logger = logging.getLogger("livekit")
    log_filter = _ExpectedRoomShutdownFilter()
    logger.addFilter(log_filter)
    try:
        yield
    finally:
        logger.removeFilter(log_filter)


def _is_duplicate_ffi_drop(args):
    """Match only LiveKit's unraisable native-handle double-drop assertion."""
    obj = args.object
    if (
        args.exc_type is not AssertionError
        or args.exc_value.args
        # Python passes the failing destructor function, not the handle instance.
        or getattr(obj, "__qualname__", None) != "FfiHandle.__del__"
        or getattr(obj, "__module__", None) != "livekit.rtc._ffi_client"
    ):
        return False
    traceback = args.exc_traceback
    while traceback:
        frame = traceback.tb_frame
        if (
            frame.f_code.co_filename.replace("\\", "/").endswith("/livekit/rtc/_ffi_client.py")
            and frame.f_code.co_name == "dispose"
            and frame.f_locals.get("dropped") is False
        ):
            return True
        traceback = traceback.tb_next
    return False


def install_known_cleanup_filter():
    """Hide only LiveKit's duplicate-drop noise after a recording validates."""
    original = sys.unraisablehook
    matches_known_noise = _is_duplicate_ffi_drop
    recording_validated = False

    def mark_recording_validated():
        nonlocal recording_validated
        recording_validated = True

    def hook(args):
        if recording_validated and matches_known_noise(args):
            return
        original(args)

    sys.unraisablehook = hook
    return mark_recording_validated


def room_token(settings, room_name, identity, *, recorder=False):
    return (
        api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        .with_identity(identity)
        .with_kind("standard" if recorder else "agent")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=not recorder,
                can_publish_data=not recorder,
                can_subscribe=True,
                hidden=recorder,
            )
        )
        .to_jwt()
    )


async def run_call(scenario_id, *, seed=42, settings=None):
    # Inference plugins need the shared HTTP lifecycle normally supplied by a worker.
    settings = settings or get_settings()
    env_values = {
        "LIVEKIT_API_KEY": settings.livekit_api_key,
        "LIVEKIT_API_SECRET": settings.livekit_api_secret,
        "LIVEKIT_INFERENCE_API_KEY": settings.livekit_api_key,
        "LIVEKIT_INFERENCE_API_SECRET": settings.livekit_api_secret,
    }
    previous = {key: os.environ.get(key) for key in env_values}
    try:
        # AgentSession constructs AdaptiveInterruptionDetector internally; that
        # SDK constructor currently reads credentials from the process environment.
        os.environ.update(env_values)
        async with http_context.open():
            return await _run_call(scenario_id, seed=seed, settings=settings)
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


async def _run_call(scenario_id, *, seed=42, settings=None):
    settings = settings or get_settings()
    if not settings.enable_live_calls or settings.missing_for_real_calls():
        raise ValueError("Live calls disabled or configuration incomplete")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("Invalid simulation seed")
    scenario = load_one(scenario_id, settings.scenarios_dir)
    caller = pin_caller_number(settings.caller_number, settings.artifacts_dir)
    call_id = allocate_call_id(settings.artifacts_dir)
    call = CallArtifacts(call_id, settings.artifacts_dir)
    call.write_scenario(scenario)
    (call.dir / "scenario.json").write_text(scenario.model_dump_json(indent=2), encoding="utf-8")
    timeline = Timeline(call.dir)
    done = asyncio.Event()
    errors = []
    termination_reason = None

    def signal_done(reason):
        nonlocal termination_reason
        if termination_reason is None:
            termination_reason = reason
            timeline.record("termination_signal", source=reason)
        done.set()

    def failed(kind):
        errors.append(kind)
        signal_done(kind)

    patient_identity = "patient-" + call_id
    room = rtc.Room()
    recorder = LocalRecorder(
        call.dir, patient_identity, on_failure=lambda: failed("recording_error")
    )
    session = None
    barge = None
    client = None
    status = "failed"
    events = []
    call.write_metadata(
        {
            "call_id": call_id,
            "scenario_id": scenario.id,
            "caller_number": caller,
            "destination": ASSESSMENT_NUMBER,
            "status": status,
            "seed": seed,
            "llm_model": settings.llm_model,
            "stt_model": settings.stt_model,
            "tts_model": settings.tts_model,
            "tts_voice": settings.tts_voice,
            "recording_source": "local_rtc_subscriber",
            "recording_channel_mapping": ["patient", "agent"],
            "patient_identity": patient_identity,
            "audio_validated": False,
            "human_verified": False,
            "call_completed": False,
        }
    )
    try:
        client = api.LiveKitAPI(
            settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret
        )
        await room.connect(settings.livekit_url, room_token(settings, call_id, patient_identity))
        # Join the local subscriber and open disk files before placing the phone call.
        await recorder.start(
            settings.livekit_url,
            room_token(settings, call_id, "recorder-" + call_id, recorder=True),
        )
        patient = PatientAgent(
            scenario,
            done,
            seed=seed,
            timeline=timeline,
            on_end_call=lambda: signal_done("patient_end_call"),
        )
        options = turn_options(settings)
        if patient.state:
            options["preemptive_generation"] = {"enabled": False, "preemptive_tts": False}
        stt, tts, vad = build_speech(settings)
        session = AgentSession(
            stt=stt,
            llm=build_llm(settings),
            tts=tts,
            vad=vad,
            turn_handling=options,
        )
        timeline.subscribe(session, on_fatal=lambda: failed("provider_error"))
        barge = BargeInScheduler(session, scenario.behavior, timeline)
        if scenario.behavior.interrupt_agent and scenario.behavior.interruption_utterance:
            session.on("user_state_changed", barge.on_state)

        @session.on("conversation_item_added")
        def item_added(event):
            item = event.item
            if getattr(item, "role", None) not in {"user", "assistant"}:
                return
            barge.on_item(event)
            data = {
                "role": item.role,
                "text": item.text_content,
                "interrupted": item.interrupted,
                "elapsed_seconds": time.monotonic() - timeline.start,
                "metrics": getattr(item, "metrics", {}),
            }
            events.append(data)
            timeline.record("conversation_item_added", **data)
            if (
                patient.state
                and item.role == "assistant"
                and item.text_content not in patient.rejected
            ):
                patient.state.observe_patient_item(item.text_content or "", item.interrupted)

        @session.on("close")
        def closed(event):
            if getattr(event, "error", None):
                failed("provider_error")
            else:
                signal_done("session_closed")

        @room.on("participant_disconnected")
        def disconnected(participant):
            if participant.identity == "assessment-line":
                signal_done("assessment_line_disconnected")

        timeline.record(
            "configuration",
            seed=seed,
            stt=settings.stt_model,
            llm=settings.llm_model,
            tts=settings.tts_model,
            turn_handling={k: v for k, v in options.items() if k != "turn_detection"},
        )
        # Arm input before dialing so the receptionist's first greeting is not missed.
        await session.start(
            room=room,
            room_options=room_io.RoomOptions(participant_identity="assessment-line"),
            agent=patient,
            record=False,
            session_host=False,
        )
        if done.is_set():
            raise RuntimeError("Agent or recorder stopped before dialing; no call placed")
        await client.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                sip_trunk_id=settings.sip_outbound_trunk_id,
                sip_call_to=resolve_destination(ASSESSMENT_NUMBER),
                sip_number=caller,
                room_name=call_id,
                participant_identity="assessment-line",
                wait_until_answered=True,
            )
        )
        status = "connected"
        try:
            await asyncio.wait_for(
                done.wait(), timeout=min(settings.max_call_seconds, scenario.max_duration_seconds)
            )
            status = errors[0] if errors else "ended"
        except TimeoutError:
            status = "watchdog_timeout"
            signal_done("watchdog_timeout")
    finally:
        # Delete the phone room even if local capture/encoding fails. Save partial
        # evidence on all failure paths; it cannot qualify as a complete call.
        try:
            if barge:
                await barge.aclose()
            if session:
                await session.aclose()
        finally:
            try:
                if client:
                    await client.room.delete_room(api.DeleteRoomRequest(room=call_id))
            finally:
                try:
                    await asyncio.sleep(0.2)
                    await recorder.close()
                finally:
                    try:
                        if status == "ended":
                            with suppress_expected_room_shutdown_logs():
                                await room.disconnect()
                        else:
                            await room.disconnect()
                    finally:
                        if client:
                            await client.aclose()
                        timeline.record("call_finished", status=status)
                        timeline.save_summary()
                        call.write_json(call.dir / "live_transcript.json", events)
                        call.update_metadata(
                            status=status, termination_reason=termination_reason or status
                        )
                        if "patient" in locals() and patient.state:
                            call.write_json(
                                call.dir / "patient_state.json", patient.state.snapshot()
                            )
    try:
        path = await asyncio.to_thread(recorder.finalize)
        await asyncio.to_thread(ingest_recording, call, path)
    except Exception as exc:
        call.update_metadata(recording_status="local_recording_invalid", audio_validated=False)
        raise RuntimeError(
            f"Call evidence saved at {call.dir}; local recording needs inspection"
        ) from exc
    # Failed attempts reserve an internal folder ID but do not consume a
    # human-facing call number. Label only after recording validation succeeds.
    call.update_metadata(call_name=next_display_name(settings.artifacts_dir))
    return call
