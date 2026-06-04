# Deployment Notes

## Default Free-First Stack

- API host: Render free web service
- Database: Neon free Postgres
- Async trigger/retry: Upstash QStash
- Optional retained audio: S3-compatible object storage

## Environment Variables

Set the values from `backend/.env.example` on the Render service and locally.

## Render

- Render free services cold-start after idle periods.
- QStash retries and can wake the service when a job processing callback is sent.
- The service only needs a web process because analysis jobs are executed through the internal endpoint.

## Neon

- Use the pooled connection string for `DATABASE_URL`.
- Keep SSL enabled in hosted environments.

## QStash

- Set `QSTASH_URL`, `QSTASH_TOKEN`, and `QSTASH_CURRENT_SIGNING_KEY`.
- Point callback URLs to `/internal/jobs/{job_id}/process`.
- Signature verification is enforced in the internal route.
- For local development, leaving the signing key empty allows manual/internal triggering without QStash verification.

## S3-Compatible Storage

- Keep `STORAGE_BACKEND=s3` only when retained session audio must be stored outside the Render filesystem.
- For local development, `STORAGE_BACKEND=local` stores uploads under `backend/uploads/`.
- Retained audio exposes a playback URL through the session report; deleted-audio sessions intentionally return no playback URL.

## Secondary Host Option

Koyeb can be used later if faster wake-up matters more than Render simplicity, but it is not the default in this repository.
