# Environment variables

Copy `.env.example` to `.env` and fill the five project and phone settings below. Values are read locally by the application and must not be committed.

| Variable | Required | Purpose |
| --- | --- | --- |
| `LIVEKIT_URL` | Yes | LiveKit project's websocket URL. |
| `LIVEKIT_API_KEY` | Yes | Project credential for rooms, SIP and LiveKit Inference. |
| `LIVEKIT_API_SECRET` | Yes | Matching project secret. |
| `SIP_OUTBOUND_TRUNK_ID` | Yes | LiveKit outbound trunk ID, usually starts with `ST_`. |
| `CALLER_NUMBER` | Yes | The one originating number, in E.164 format. |
| `ENABLE_LIVE_CALLS` | Yes for dialing | Allows calls when the explicit `--execute` command is used. |

The default separate LiveKit Inference models are Deepgram Nova-3 (`STT_MODEL`), GPT-4.1 mini (`LLM_MODEL`) and Cartesia Sonic-3 (`TTS_MODEL`). `TTS_VOICE` selects the Cartesia voice. These defaults are already in `.env.example`; they do not need additional provider keys.

`OPENAI_API_KEY` is optional and reserved for post-call audio transcription and semantic evaluation. It is not used by the live caller pipeline. With no key, the app saves its live transcript and heuristic evaluation. No S3 or AWS variables are used because recordings are local.
