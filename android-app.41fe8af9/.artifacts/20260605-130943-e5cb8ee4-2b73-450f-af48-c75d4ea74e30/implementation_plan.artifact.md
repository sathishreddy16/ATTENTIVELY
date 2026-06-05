# Fix Session Upload and Analysis Reliability (Part 2)

The previous changes improved error visibility, showing that the app occasionally suffers from DNS resolution issues ("Unable to resolve host"). Additionally, backend logs show database connection issues and polling for reports that stay in "analysis_pending". This updated plan refines the polling logic and adds a manual retry option.

## User Review Required

> [!IMPORTANT]
> I will add a "Retry Upload" button to the UI for failed sessions. This allows users to manually trigger a retry when they know their connection is stable, rather than relying solely on WorkManager's exponential backoff which might exhaust attempts during long periods of offline/unstable connectivity.

## Proposed Changes

### Work Manager

#### [UploadSessionWorker.kt](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/android-app/app/src/main/java/com/attentively/chantingcoach/work/UploadSessionWorker.kt)

- Refine retry logic: If the error is a `java.net.UnknownHostException` (DNS failure), use a shorter retry interval or wait for network connectivity.
- Increase max retries to 12 to handle longer backend processing or unstable networks.

```kotlin
        } catch (error: Exception) {
            Log.e("UploadSessionWorker", "Error processing session $localId", error)
            if (runAttemptCount > 12) {
                localRepo.markFailed(localId, error.message ?: "Upload failed after retries")
                Result.failure()
            } else {
                // If it's a network error, maybe wait longer or just retry with backoff
                Result.retry()
            }
        }
```

---

### UI Components

#### [Screens.kt](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/android-app/app/src/main/java/com/attentively/chantingcoach/ui/screens/Screens.kt)

- Add a "Retry" button to the session card when the status is `FAILED`.

```kotlin
// In RecordSessionScreen session list item:
if (session.uploadStatus == "FAILED") {
    Button(
        onClick = { viewModel.retryUpload(session.localId) },
        modifier = Modifier.padding(top = 4.dp)
    ) {
        Text("Retry Upload")
    }
}
```

#### [SessionViewModels.kt](file:///C:/Users/DELL/Desktop/ATTENTIVELY_CODEX/android-app/app/src/main/java/com/attentively/chantingcoach/ui/viewmodel/SessionViewModels.kt)

- Implement `retryUpload` in `RecordSessionViewModel`.

```kotlin
    fun retryUpload(localId: String) {
        viewModelScope.launch {
            localSessionsRepository.markStopped(localId) // Reset to PENDING_UPLOAD state conceptually
            UploadSessionWorker.enqueue(appContext, localId)
        }
    }
```

## Verification Plan

### Automated Tests
- Verify compilation: `./gradlew :app:assembleDebug`.

### Manual Verification
- Deploy to device.
- Simulate a failure (e.g., turn off Wi-Fi) and observe the `FAILED` status with "Unable to resolve host".
- Verify that the "Retry Upload" button appears.
- Turn on Wi-Fi and click "Retry Upload".
- Verify that the session successfully moves to `ANALYSIS_PENDING` and then `COMPLETED`.
