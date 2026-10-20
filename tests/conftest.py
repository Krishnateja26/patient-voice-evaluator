"""Keep tests isolated from saved credentials and real telephony."""

import pytest
from livekit import api


@pytest.fixture(autouse=True)
def block_live_credentials_and_clients(monkeypatch):
    for name in (
        "LIVEKIT_URL",
        "LIVEKIT_API_KEY",
        "LIVEKIT_API_SECRET",
        "SIP_OUTBOUND_TRUNK_ID",
        "CALLER_NUMBER",
        "ENABLE_LIVE_CALLS",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)

    def blocked(*args, **kwargs):
        raise AssertionError("Real LiveKit clients are forbidden during tests")

    monkeypatch.setattr(api, "LiveKitAPI", blocked)
