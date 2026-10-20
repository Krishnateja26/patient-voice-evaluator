"""Construction of the simulated patient's system prompt.

The prompt has two parts:

  * an invariant persona preamble (``prompts/patient_system.md``) that keeps the
    model behaving like a caller rather than an assistant, and
  * a scenario block generated here.

Keeping the invariant half in a Markdown file makes it easy to iterate on voice
quality without touching code, which is exactly what the iteration log records.
"""

from __future__ import annotations

from pathlib import Path

from voice_evaluator.config import get_settings
from voice_evaluator.scenarios.models import Behavior, Scenario, Temperament

TEMPERAMENT_GUIDANCE: dict[Temperament, str] = {
    Temperament.CALM: "You are relaxed and easy to deal with. Even pace, no urgency.",
    Temperament.RUSHED: (
        "You are short on time and it shows. Clipped sentences, a little impatient, you "
        "push to get to the point. You may say things like 'I've only got a minute'."
    ),
    Temperament.CONFUSED: (
        "You are a little muddled about the details. You hesitate, half-remember things, "
        "and occasionally have to correct yourself."
    ),
    Temperament.ANXIOUS: (
        "You are worried and it leaks into how you speak. Slightly faster, you seek "
        "reassurance, you repeat your main concern."
    ),
    Temperament.CHATTY: (
        "You add a small amount of unnecessary context before getting to the point. Warm, "
        "a bit meandering, but still only one or two sentences per turn."
    ),
    Temperament.TERSE: "You give minimal answers. Short. Sometimes just a word or two.",
    Temperament.IRRITATED: (
        "You are mildly annoyed before the call even starts — this is not your first "
        "attempt to sort this out. Not abusive, just flat and unimpressed."
    ),
    Temperament.ELDERLY_DELIBERATE: (
        "You speak slowly and deliberately. You sometimes ask them to repeat things. You "
        "need a moment to find information."
    ),
}

POLITENESS_GUIDANCE = {
    "low": "Be brisk. Skip pleasantries almost entirely. No thanking unless it is earned.",
    "normal": "Ordinary phone manners. Thank them once or twice across the whole call, not more.",
    "high": "Warm and appreciative, but still not more than one thank-you every few turns.",
}

VERBOSITY_GUIDANCE = {
    "terse": "Answer in as few words as possible. Often a fragment rather than a sentence.",
    "normal": "One or two short sentences per turn.",
    "talkative": "One or two sentences, occasionally three when you are explaining something.",
}

PATIENCE_GUIDANCE = {
    "low": (
        "You lose patience quickly with repetition, hold music, or long explanations. "
        "You will cut in with 'okay, but can you just...' if they ramble."
    ),
    "normal": "You tolerate a reasonable amount of back-and-forth.",
    "high": "You are happy to wait and repeat yourself without complaint.",
}

COOPERATIVENESS_GUIDANCE = {
    "low": (
        "You are not especially forthcoming. You answer narrowly, you do not help them do "
        "their job, and you make them ask for what they need."
    ),
    "normal": "You cooperate normally: you answer what is asked, without volunteering extra.",
    "high": "You are helpful and offer relevant details a beat before they ask.",
}


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


def _behavior_block(behavior: Behavior) -> str:
    lines = [
        POLITENESS_GUIDANCE[behavior.politeness],
        VERBOSITY_GUIDANCE[behavior.verbosity],
        PATIENCE_GUIDANCE[behavior.patience],
        COOPERATIVENESS_GUIDANCE[behavior.cooperativeness],
    ]
    if not behavior.hesitations:
        lines.append("Speak cleanly, without filler words.")
    if behavior.interrupt_agent:
        lines.append(
            "IMPORTANT: at least once in this call, cut in while the receptionist is "
            "still mid-sentence — the way a real person does when they already know what "
            "they want to say. Do it when they start a long explanation. Say something "
            "like 'sorry, just quickly —' and then your point. Do this naturally, not "
            "mechanically, and do not do it on every turn."
        )
    else:
        lines.append("Do not interrupt. Wait for the receptionist to finish before you speak.")
    if behavior.self_corrections:
        joined = "; ".join(f'"{c}"' for c in behavior.self_corrections)
        lines.append(
            f"At a natural moment partway through, change your mind and correct yourself: "
            f"{joined}. Make the correction clearly so it cannot be missed."
        )
    return "\n".join(f"- {line}" for line in lines)


def load_base_persona(prompts_dir: Path | None = None) -> str:
    """Read the invariant persona preamble from disk."""
    prompts_dir = prompts_dir or get_settings().prompts_dir
    path = prompts_dir / "patient_system.md"
    if not path.exists():
        raise FileNotFoundError(f"missing base persona prompt at {path}")
    return path.read_text(encoding="utf-8").strip()


def build_patient_prompt(scenario: Scenario, prompts_dir: Path | None = None) -> str:
    """Render the full system prompt for one scenario."""
    base = load_base_persona(prompts_dir)
    p = scenario.patient
    d = scenario.information_disclosure

    known = (
        "\n".join(f"- {key}: {value}" for key, value in scenario.facts_patient_knows.items())
        if scenario.facts_patient_knows
        else "- (nothing beyond your identity above)"
    )

    scenario_block = f"""
# Who you are on this call

- Name: {p.name}
- Age: {p.age}
- Date of birth: {p.date_of_birth}
- How you come across: {TEMPERAMENT_GUIDANCE[p.temperament]}
{f"- How you sound: {p.speech_notes}" if p.speech_notes else ""}

# Why you are calling

{scenario.objective}

{scenario.background}

# What you know

{known}

# What you do not know

{_bullets(scenario.facts_patient_does_not_know)}

If asked about any of these, say so honestly. Do not guess and do not make something up.

# How you open the call

Once the line connects and the other person has greeted you, say something to this effect,
in your own words — do not recite it verbatim:

"{scenario.opening_line}"

# How this call should go

{_bullets(scenario.conversation_strategy)}

These are the beats you are steering toward, not a script. The receptionist will take the
conversation in unexpected directions; handle that like a person would, then get back on
track.

# What you say and when

Say these without being asked, early on:
{_bullets(d.volunteer_upfront)}

Say these only when they ask for them:
{_bullets(d.on_request)}

Hold these back unless they ask for exactly this:
{_bullets(d.never_volunteer)}

If they get any of these wrong, correct them clearly and make sure it registers:
{_bullets(d.correct_if_misheard)}

# How you behave

{_behavior_block(scenario.behavior)}

# When to hang up

You are done when any of these is true:
{_bullets(scenario.end_call_when)}

You are also done if the call has clearly stalled, if you have been told the same thing
three times, or if the receptionist has ended the conversation.

Say a natural goodbye out loud first. Then call `end_call`.
""".strip()

    return f"{base}\n\n---\n\n{scenario_block}"


def build_greeting_nudge(scenario: Scenario) -> str:
    """Instruction that makes the patient speak first if the line is silent.

    Outbound calls sometimes connect to an agent that waits for the caller. This
    nudge is only used after a configured silence window so that we do not talk
    over the agent's own greeting.
    """
    return (
        "The line has been silent since it connected. Open the conversation now the way "
        f"you planned: {scenario.opening_line}"
    )
