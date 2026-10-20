# Historical research architecture notes

**Current workflow:** local recording and one call command; no S3/Egress or separate worker. Live conversation uses separate LiveKit Inference STT, text LLM and TTS stages. See README.md, SERVICE_SETUP.md and MIGRATION.md. The notes below preserve earlier design reasoning and are not current setup instructions. The full scenario library remains available; recording selection is documented in RECORDING_SHORTLIST.md.

The original research prompt is design input, not independent verification of every paper, date, citation count, benchmark number, or provider capability. It is not included in the submission repository. The current implementation was checked against the installed LiveKit Agents 1.8.8 source and official API documentation. No literature performance number is reported as our result.

## Implemented in this iteration

| Area | Change | What remains unproven |
| --- | --- | --- |
| Turn completion | Explicit audio TurnDetector with SDK-default Silero VAD; configurable dynamic endpointing, initially 0.3-2.5 seconds | Premature-end rate and PSTN transition latency |
| Interruptions | Explicit adaptive mode, minimum duration/words, false-interruption resume; supported overlap events recorded | STT alignment compatibility and true/false interruption rates on our calls |
| Preparation | Preemptive LLM enabled for legacy prompt mode, preemptive TTS disabled | Actual latency savings and wasted token cost |
| Patient state | Opt-in typed simulation controls, authored disclosure cues, ordered pending corrections, versioned event history | Semantic trigger accuracy beyond authored literal cues |
| Disclosure | Controlled renderer receives only allowed structured facts; legacy background/strategy/assertions are excluded | A language model can guess a value; literal guard is not a general semantic verifier |
| Output verification | Full controlled utterance checked before synthesis; withheld literals and isolated stale day preferences rejected | Paraphrased identifiers, negation, inferred facts and general contradictions |
| Reproducibility | Seeded hesitation decisions, seed and exact model/turn configuration saved per call | LLM output is not deterministic merely because scheduler seed repeats |
| Speech delivery | SDK speech creation/completion and interruption state logged; interrupted corrections remain pending | SDK completion cannot prove what the remote PSTN listener heard |
| Telemetry | Append-only timeline, SDK EOT/LLM/TTS/e2e latency p50/p95/count, live ASR hypotheses, state changes and false interruptions | Remote first-audible audio, cancellation time and audio-aligned EOT require recording analysis |
| Evaluation | Exact quoted text, stable turn ID, correct speaker and timestamp range checked; every evidence entry must pass | Verified quotations establish observations, not the truth of a semantic defect claim |
| Adjudication | Fresh text-model request sees rubric, full canonical transcript and verified evidence; extractor rationale/confidence hidden | Same-provider judgments can share bias; no calibrated agreement result yet |
| Final reports | Verified-only report requires human-reviewed evidence; unsupported/unclear adjudication excluded | Human audio review is still required |

## Controlled pilot

`scenarios/memory/controlled_day_preference.yaml` is an opt-in adaptation of our existing two-correction scenario. It starts on Tuesday, schedules a Wednesday correction when the target mentions Tuesday, then a Friday correction when Wednesday is discussed. Changes commit only on a non-interrupted SDK conversation item containing the authored delivery marker. No LLM-generated state operation is trusted. A partial utterance may have been audible before interruption, but the controller conservatively retries its pending intention rather than claiming delivery.

Legacy scenarios retain the previous prompt behavior. They are explicitly labeled `legacy_prompt` in artifacts. Free-text facts, strategy, and disclosures were not silently translated into supposedly deterministic policy. Add a reviewed `simulation` block to migrate each selected scenario.

```powershell
voice-evaluator dry-run controlled_day_preference --seed 42
# Only after telephony and recording setup, with the worker running:
voice-evaluator call controlled_day_preference --seed 42 --execute
```

The structured controller uses narrow authored request phrases and question cues; it is not an intent model. Its renderer knows only currently permitted facts, current preferences, the pending correction and the goal. The full scenario remains available to the controller/evaluator, outside that renderer context. The caller has a short generic persona and no evaluator rubric. Hidden values must not be repeated in authored control goals or correction text.

## Deliberate latency tradeoff

Controlled mode disables speculative generation and buffers each full utterance before the literal guard allows it to enter TTS. This avoids using obsolete turn-specific policy and leaking a value split across token chunks. The ordinary path retains SDK text/TTS streaming. The controlled path still uses the provider's audio stream after approval, but does not claim clause-level early synthesis. Measure its added delay before introducing a structured per-clause generator/verifier. No custom VAD/turn detector, silence heuristic, or hard-coded prosody classifier was added.

## Artifacts

- `timeline.jsonl`: event sequence, monotonic relative observation time, wall-clock observation time, permitted SDK payloads.
- `timing_summary.json`: available SDK metrics; missing data stays `null`, never zero.
- `patient_state.json`: controlled event ledger, pending correction, seeded behavior choices and disclosure IDs.
- `metadata.json`: seed, model/voice/turn settings, simulation mode, status and Egress ID; human verification defaults false.
- `live_transcript.json`: diagnostic text, not an audio-aligned ground-truth transcript.

The callback names come from this SDK: `overlapping_speech` and `agent_false_interruption`, not the unverified `user_interruption_detected` name in the source narrative. Raw provider objects, opaque errors and credential-bearing error messages are not included in error telemetry. Synthetic patient values are used; no legal compliance certification is implied.

## Next measured experiments

1. Validate the now-implemented private stereo Egress retrieval and canonical speaker transcription on a real pilot. These paths passed synthetic/mocked checks but have no live evidence yet.
2. Run a baseline and the controlled pilot with the same target and compare false endpoints, false interruptions, latency, disclosure and correction fidelity by listening to audio.
3. Verify aligned transcripts and tune interruption/endpoint bounds; never claim reduced latency from configuration alone.
4. Add STT scenario keyterms only through a supported provider interface. Build a synthetic/annotated narrowband medication/name/date corpus; report entity errors separately from WER.
5. Migrate 12-15 selected scenarios into authored controlled blocks; do not automatically guess disclosure permissions from free text.
6. Add constrained metamorphic variants and repeated-seed reliability with invariant goals. Seeded scheduling is reproducibility input, not proof of statistical stability.
7. Use labeled pause failures to justify semantic holds or response-conditioned turn prediction. Avoid a bespoke neural detector without data.
8. Calibrate evidence precision/recall and adjudicator disagreement against manually labeled calls. Add order swaps for actual pairwise comparisons; this is not a pairwise judge today.

## API sources checked

- [Turn handling options](https://docs.livekit.io/reference/agents/turn-handling-options/)
- [Turn-taking tuning](https://docs.livekit.io/agents/logic/turns/tuning/)
- [Adaptive interruptions](https://docs.livekit.io/agents/logic/turns/adaptive-interruption-handling/)
- Installed `livekit/agents/voice/agent.py`, `events.py`, `turn.py`, `agent_session.py`, `llm/chat_context.py`.

## Local verification

151 tests passed. Ruff lint and formatting checks passed for all 43 Python files. Dependency checks reported no broken requirements. The controlled dry-run exposes the initial Tuesday preference and shoulder-review reason while withholding name, birth date, phone number, and future corrections. These are offline/simulated checks; no live calls, paid model requests, or provider benchmarks were performed in this iteration.

## Subsequent compliance milestone

The strict-compliance iteration implemented private storage configuration, dual-channel MP3 retrieval/decoding and post-call ASR, renamed the package to voice_evaluator, corrected artifact discovery and readiness, pinned caller identity and added one real scheduled overlap attempt. Earlier backlog statements describe the stage at which this research was introduced; see MIGRATION.md and COMPLIANCE_REVIEW.md for current status. The full local suite now has 161 passing tests. No live quality improvement or call-based calibration is claimed.
