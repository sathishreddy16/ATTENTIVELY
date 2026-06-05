# Fix Backend Errors and Analysis Processing

The backend is currently experiencing two main issues:
1.  **SQL Error in `daily-progress`**: A type mismatch in the PostgreSQL query is causing 500 errors.
2.  **Sessions Stuck in `analysis_pending`**: Analysis jobs are either not being enqueued correctly in QStash or are failing silently during background processing.

## Proposed Changes

### Backend - API & Services

#### [backend/app/services/sessions.py](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/backend/app/services/sessions.py)

- Fix the `psycopg.errors.UndefinedFunction` error by ensuring the `target_date` is correctly handled in the SQL query. PostgreSQL's `date()` function might not like the parameter binding style being used by SQLAlchemy with certain drivers.
- I will change `func.date(SessionRecord.started_at) == target_date` to a more robust range-based comparison or explicit cast.

```python
def build_daily_progress(db: Session, target_date: date) -> DailyProgressResponse:
    # Use range-based comparison to avoid issues with date() function on different DBs
    start_dt = datetime.combine(target_date, time.min).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(target_date, time.max).replace(tzinfo=timezone.utc)

    rows = db.execute(
        select(SessionRecord.id, SessionRecord.final_count)
        .where(SessionRecord.started_at >= start_dt)
        .where(SessionRecord.started_at <= end_dt)
        .where(SessionRecord.status == SessionStatus.completed.value)
    ).all()
    # ...
```

#### [backend/app/api/sessions.py](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/backend/app/api/sessions.py)

- Improve logging in `complete_upload_route` to track why jobs might be failing to enqueue.
- Ensure that if QStash is not configured (`qstash_token` is empty), the code correctly falls back to synchronous processing instead of potentially swallowing errors.

### Backend - Jobs & Processing

#### [backend/app/services/jobs.py](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/backend/app/services/jobs.py)

- Add more granular logging inside `process_job` to identify which step is stalling (audio normalization, provider transcription, or scoring).
- Handle potential timeouts more gracefully.

## Verification Plan

### Automated Tests
- I will run the backend locally if possible to verify the SQL fix.
- Since I don't have a local backend environment set up with PostgreSQL, I will rely on the user to deploy these changes to Render and provide logs.

### Manual Verification
1.  **Deploy to Render**: User pushes changes to the backend repository.
2.  **Check `daily-progress`**: Trigger the "Refresh Progress" button in the app and verify the 500 error is gone.
3.  **Perform New Recording**: Record a short session, stop it, and monitor its progress.
4.  **Monitor Backend Logs**: Check for "Publishing job... to QStash" and "Processing job..." logs.
5.  **Verify Analysis**: Ensure the session moves from `analysis_pending` to `COMPLETED`.
