# Chanting Coach MVP v5

Monorepo for an Android-first chanting analysis app and its backend.

## Structure

- `backend/` FastAPI API, upload pipeline, async job orchestration, chanting analysis logic, and provider failover.
- `android-app/` Kotlin/Compose Android client scaffold with recording, report, and playback hooks.
- `docs/` deployment and environment notes.

## Highlights

- Chunked upload flow for long chanting sessions.
- Deepgram-first speech provider with Groq Whisper fallback.
- Red, yellow, and gray classification for each mantra repetition.
- Daily 16-mala progress aggregation.
- Render + Neon + Upstash QStash friendly backend architecture.

## Quick Start

### Backend

1. Create a Python 3.13 virtual environment.
2. Install dependencies from `backend/pyproject.toml`.
3. Copy `backend/.env.example` to `.env`.
4. Run `uvicorn app.main:app --reload` from `backend/`.

### Android

Open `android-app/` in Android Studio. The project is scaffolded for Kotlin + Jetpack Compose and expects the backend URL to be supplied through the `BACKEND_BASE_URL` build config field.

## Current Status

- Backend: implemented API surface, chunked upload flow, retained-audio playback route, provider failover, analysis scoring, normalization hook, and API/unit tests.
- Android: implemented app shell, network contracts, local Room persistence, recorder manager, upload worker orchestration, report playback hooks, and session-driven screens.
- Infra: Render/Neon/QStash oriented configuration and deployment notes.

## Android Flow

The Android app now supports this lifecycle in code:

1. Start chanting and record audio locally with `MediaRecorder`.
2. Persist the local session in Room with upload status tracking.
3. Stop recording and enqueue a `WorkManager` upload job.
4. Create the backend session, upload audio in chunks, and complete upload.
5. Poll the backend report until analysis completes.
6. Show the final report and allow flagged-clip playback when retained audio is available.
