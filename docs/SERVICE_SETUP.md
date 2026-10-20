# Service setup

The normal call flow uses a LiveKit project and a single outbound SIP trunk. LiveKit Inference supplies the separate STT, text LLM and TTS stages using the same LiveKit project credentials. You do not need separate Deepgram or Cartesia API keys for this configuration.

## 1. LiveKit project

Create or open a project in [LiveKit Cloud](https://cloud.livekit.io/). In project settings, copy the project URL, API key and API secret into `.env`. The project URL is the websocket URL, generally `wss://<project-host>.livekit.cloud`; it is different from the dashboard URL in your browser.

## 2. SIP trunk and caller number

Use one originating number you control. For an existing Twilio number, configure an outbound Elastic SIP trunk and its credentials, then create a LiveKit outbound trunk using the Twilio termination address and credentials. Copy the LiveKit outbound trunk ID (starts with `ST_`) into `SIP_OUTBOUND_TRUNK_ID`. Put the same caller number in E.164 format, including `+` and country code, in `CALLER_NUMBER`.

See LiveKit's [Twilio provider instructions](https://docs.livekit.io/telephony/start/providers/twilio/) and [outbound trunk guide](https://docs.livekit.io/telephony/making-calls/outbound-trunk/). Twilio setup screens can change, so use their current console labels when creating the trunk.

## 3. Configure and run

Copy `.env.example` to `.env` and fill `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `SIP_OUTBOUND_TRUNK_ID` and `CALLER_NUMBER`. Keep `.env` local and private. `ENABLE_LIVE_CALLS=true` permits the explicit call command; it does not place a call by itself.

After installation, list available scenarios and start an intentional call with:

```powershell
voice-evaluator scenarios
voice-evaluator call new_patient_record_intake --execute
```

The recorder and patient run within that command. MP3, transcript, metadata and evaluation are saved locally under `artifacts/calls/`. No S3, Egress, public tunnel, separate worker terminal or manual download is needed.

## Optional post-call analysis

`OPENAI_API_KEY` is optional. It is used for post-call audio transcription or semantic evaluation only, not for the live patient conversation. If it is blank, the app keeps the live transcript and heuristic evaluation. Never commit `.env` or include credentials in logs or screenshots.
