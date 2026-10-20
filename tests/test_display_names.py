import json

from voice_evaluator.artifacts.store import next_display_name


def test_failed_attempt_does_not_consume_display_name(tmp_path):
    calls = tmp_path / "calls"
    calls.mkdir()

    completed = calls / "call-005"
    completed.mkdir()
    (completed / "metadata.json").write_text(
        json.dumps({"call_name": "Call 5"}), encoding="utf-8"
    )

    failed_attempt = calls / "call-006"
    failed_attempt.mkdir()
    (failed_attempt / "metadata.json").write_text(
        json.dumps({"recording_status": "local_recording_invalid"}), encoding="utf-8"
    )

    assert next_display_name(tmp_path) == "Call 6"
