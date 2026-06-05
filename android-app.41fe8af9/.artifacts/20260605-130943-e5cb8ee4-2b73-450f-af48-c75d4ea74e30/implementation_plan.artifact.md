# Fix Session Upload and Analysis Reliability

The user reported that session analysis stays in "analysis_pending" and eventually fails. This plan improves the robustness of the background upload worker, handles backend failures explicitly, and provides better error visibility in the UI.

## User Review Required

> [!IMPORTANT]
> I will be increasing the logging in the `UploadSessionWorker` to better diagnose issues in the field. This will help us see the exact status returned by the backend.

## Proposed Changes

### Work Manager

#### [UploadSessionWorker.kt](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/android-app/app/src/main/java/com/attentively/chantingcoach/work/UploadSessionWorker.kt)

- Handle `report.status == "failed"` explicitly to avoid unnecessary retries.
- Only mark the session as `FAILED` in the local repository when the retry limit is reached or a terminal error occurs.
- Add `Log` calls to track progress and capture error details.

```kotlin
        return try {
            // ... upload logic ...

            val report = sessionApi.getSessionReport(backendSessionId)
            Log.d("UploadSessionWorker", "Session $backendSessionId status: ${report.status}")

            when (report.status) {
                "completed" -> {
                    localRepo.markAnalyzed(localId, report.finalCount, report.malaCount, report.summaryText)
                    if (session.retentionChoice == "delete") {
                        audioFile.delete()
                    }
                    Result.success(workDataOf(KEY_BACKEND_SESSION_ID to backendSessionId))
                }
                "failed" -> {
                    localRepo.markFailed(localId, "Backend analysis failed")
                    Result.failure()
                }
                else -> {
                    // "pending" or "processing"
                    Result.retry()
                }
            }
        } catch (error: Exception) {
            Log.e("UploadSessionWorker", "Error processing session $localId", error)
            if (runAttemptCount > 8) {
                localRepo.markFailed(localId, error.message ?: "Upload failed after retries")
                Result.failure()
            } else {
                Result.retry()
            }
        }
```

---

### UI Components

#### [Screens.kt](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/android-app/app/src/main/java/com/attentively/chantingcoach/ui/screens/Screens.kt)

- Update `RecordSessionScreen` to display the `lastError` when a session fails.
- Update `ReportScreen` to show a more descriptive status when a report is not yet available.

```kotlin
// In RecordSessionScreen session list item:
Text("Upload status: ${session.uploadStatus}")
session.lastError?.let {
    Text("Error: $it", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
}
```

## Verification Plan

### Automated Tests
- I will verify the compilation of the changes using `./gradlew :app:assembleDebug`.

### Manual Verification
- Deploy the app to the physical device.
- Perform a short recording and trigger "Stop and Analyze".
- Monitor the "Recent local sessions" list for status updates.
- Check Logcat for "UploadSessionWorker" tags to see the polling status.
- Verify that if an error occurs, the error message is visible in the list.
