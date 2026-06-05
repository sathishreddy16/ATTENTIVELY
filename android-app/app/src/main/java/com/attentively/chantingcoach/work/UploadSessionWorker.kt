package com.attentively.chantingcoach.work

import android.content.Context
import android.util.Log
import androidx.work.CoroutineWorker
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import com.attentively.chantingcoach.ChantingCoachApplication
import java.io.File
import java.time.Instant
import java.util.concurrent.TimeUnit

class UploadSessionWorker(
    appContext: Context,
    workerParams: WorkerParameters,
) : CoroutineWorker(appContext, workerParams) {
    override suspend fun doWork(): Result {
        val localId = inputData.getString(KEY_LOCAL_SESSION_ID) ?: return Result.failure()
        val appGraph = (applicationContext as ChantingCoachApplication).appGraph
        val localRepo = appGraph.localSessionsRepository
        val remoteRepo = appGraph.sessionUploader
        val sessionApi = appGraph.sessionsRepository

        if (runAttemptCount > 12) {
            localRepo.markFailed(localId, "Max retry limit reached")
            return Result.failure()
        }

        val session = localRepo.getById(localId) ?: return Result.failure()
        val audioFile = File(session.localAudioPath)
        if (!audioFile.exists()) {
            localRepo.markFailed(localId, "Audio file missing")
            return Result.failure()
        }

        return try {
            val backendSessionId = if (session.backendSessionId == null) {
                localRepo.markUploading(localId)
                Log.d("UploadSessionWorker", "Starting upload for local session $localId")
                val upload = remoteRepo.uploadRecordedSession(
                    audioFile = audioFile,
                    deviceId = session.deviceId,
                    retentionChoice = session.retentionChoice,
                    startedAt = Instant.parse(session.startedAt),
                    endedAt = session.endedAt?.let(Instant::parse) ?: Instant.now(),
                )
                localRepo.markUploaded(localId, upload.sessionId, upload.jobId)
                Log.d("UploadSessionWorker", "Upload successful: ${upload.sessionId}")
                upload.sessionId
            } else {
                session.backendSessionId
            }

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
            if (runAttemptCount > 12) {
                localRepo.markFailed(localId, error.message ?: "Upload failed after retries")
                Result.failure()
            } else {
                Result.retry()
            }
        }
    }

    companion object {
        const val KEY_LOCAL_SESSION_ID = "local_session_id"
        const val KEY_BACKEND_SESSION_ID = "backend_session_id"

        fun enqueue(context: Context, localSessionId: String) {
            val request = OneTimeWorkRequestBuilder<UploadSessionWorker>()
                .setInputData(workDataOf(KEY_LOCAL_SESSION_ID to localSessionId))
                .setBackoffCriteria(
                    androidx.work.BackoffPolicy.EXPONENTIAL,
                    30,
                    TimeUnit.SECONDS,
                )
                .build()
            WorkManager.getInstance(context).enqueue(request)
        }
    }
}
