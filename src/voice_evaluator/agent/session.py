"""Explicit SDK-owned timing and interruption controls."""

from livekit.agents import TurnHandlingOptions, inference


def turn_options(settings):
    return TurnHandlingOptions(
        turn_detection=inference.TurnDetector(),
        endpointing={
            "mode": settings.endpointing_mode,
            "min_delay": settings.endpoint_min_delay,
            "max_delay": settings.endpoint_max_delay,
        },
        interruption={
            "mode": settings.interruption_mode,
            "min_duration": settings.interruption_min_duration,
            "min_words": settings.interruption_min_words,
            "resume_false_interruption": True,
        },
        preemptive_generation={"enabled": settings.preemptive_generation, "preemptive_tts": False},
    )
