"""Exercise the installed SDK destructor offline, including process shutdown."""

import logging
import os
import subprocess
import sys
import textwrap
from types import SimpleNamespace

import pytest
from livekit.rtc import _ffi_client as ffi

from voice_evaluator.agent import worker


@pytest.fixture
def duplicate_drop_error(monkeypatch):
    # No native runtime or call: fake only the drop result, then invoke the real
    # SDK destructor so Python supplies genuine UnraisableHookArgs.
    errors = []
    monkeypatch.setattr(sys, "unraisablehook", errors.append)
    monkeypatch.setattr(
        ffi.FfiClient,
        "_instance",
        SimpleNamespace(
            _pid=os.getpid(),
            _ffi_lib=SimpleNamespace(livekit_ffi_drop_handle=lambda handle: False),
        ),
    )
    handle = ffi.FfiHandle(123)
    del handle
    assert len(errors) == 1
    return errors[0]


def test_filter_matches_real_destructor_function(duplicate_drop_error):
    assert duplicate_drop_error.object is ffi.FfiHandle.__del__
    assert worker._is_duplicate_ffi_drop(duplicate_drop_error)


def test_filter_forwards_errors_until_recording_validates(monkeypatch, duplicate_drop_error):
    forwarded = []
    monkeypatch.setattr(sys, "unraisablehook", forwarded.append)
    mark_validated = worker.install_known_cleanup_filter()

    sys.unraisablehook(duplicate_drop_error)
    assert forwarded == [duplicate_drop_error]
    mark_validated()
    sys.unraisablehook(duplicate_drop_error)
    assert forwarded == [duplicate_drop_error]

    unexpected = SimpleNamespace(
        object=duplicate_drop_error.object,
        exc_type=RuntimeError,
        exc_value=RuntimeError("unexpected cleanup failure"),
        exc_traceback=duplicate_drop_error.exc_traceback,
    )
    sys.unraisablehook(unexpected)
    assert forwarded == [duplicate_drop_error, unexpected]


def test_only_expected_channel_close_errors_are_hidden_during_shutdown(caplog):
    logger = logging.getLogger("livekit")

    def close_message(channel):
        return (
            "livekit::rtc_engine::rtc_session:704:livekit::rtc_engine::rtc_session - "
            f"publisher data channel '{channel}' closed unexpectedly"
        )

    with caplog.at_level(logging.ERROR, logger="livekit"):
        with worker.suppress_expected_room_shutdown_logs():
            for channel in ("_reliable", "_lossy", "_data_track"):
                logger.error(close_message(channel))
            logger.error("unexpected LiveKit room failure")
        logger.error(close_message("_reliable"))

    assert [record.getMessage() for record in caplog.records] == [
        "unexpected LiveKit room failure",
        close_message("_reliable"),
    ]


@pytest.mark.parametrize(
    ("validated", "mode", "expected_error"),
    [
        (True, "duplicate", None),
        (False, "duplicate", "AssertionError"),
        (True, "runtime", "RuntimeError: unexpected cleanup failure"),
        (True, "native_assertion", "AssertionError: unexpected native assertion"),
        (True, "unrelated", "AssertionError: unrelated cleanup failure"),
    ],
)
def test_shutdown_keeps_unexpected_errors_visible(validated, mode, expected_error):
    # Simulate a saved-recording validation signal and release handles at process
    # exit, where the user's traceback occurs. This never opens a real room.
    script = textwrap.dedent("""
        import atexit
        import os
        import sys
        from types import SimpleNamespace
        from livekit.rtc import _ffi_client as ffi
        from voice_evaluator.agent.worker import install_known_cleanup_filter

        mode = sys.argv[2]
        def drop(handle):
            if mode == "runtime":
                raise RuntimeError("unexpected cleanup failure")
            if mode == "native_assertion":
                raise AssertionError("unexpected native assertion")
            return False

        ffi.FfiClient._instance = SimpleNamespace(
            _pid=os.getpid(),
            _ffi_lib=SimpleNamespace(livekit_ffi_drop_handle=drop),
        )
        mark_validated = install_known_cleanup_filter()
        if sys.argv[1] == "True":
            mark_validated()

        class Unrelated:
            def __del__(self):
                raise AssertionError("unrelated cleanup failure")

        handles = [Unrelated() if mode == "unrelated" else ffi.FfiHandle(123)]
        atexit.register(handles.clear)
        print("offline shutdown fixture")
    """)
    result = subprocess.run(
        [sys.executable, "-c", script, str(validated), mode],
        capture_output=True,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "offline shutdown fixture" in result.stdout
    if expected_error is None:
        assert result.stderr == ""
    else:
        assert expected_error in result.stderr
