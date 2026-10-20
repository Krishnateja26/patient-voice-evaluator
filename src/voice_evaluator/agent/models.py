"""LiveKit Inference models for the local patient caller."""

from livekit.agents import inference


def build_llm(settings):
    return inference.LLM(
        model=settings.llm_model,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
    )


def build_speech(settings):
    return (
        inference.STT(
            model=settings.stt_model,
            language="en",
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ),
        inference.TTS(
            model=settings.tts_model,
            voice=settings.tts_voice,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        ),
        None,
    )
