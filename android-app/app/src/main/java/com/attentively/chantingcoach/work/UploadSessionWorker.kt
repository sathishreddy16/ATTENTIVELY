package com.attentively.chantingcoach.work

import android.content.Context
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

        if (runAttemptCount > 8) {
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
                val upload = remoteRepo.uploadRecordedSession(
                    audioFile = audioFile,
                    deviceId = session.deviceId,
                    retentionChoice = session.retentionChoice,
                    startedAt = Instant.parse(session.startedAt),
                    endedAt = session.endedAt?.let(Instant::parse) ?: Instant.now(),
                )
                localRepo.markUploaded(localId, upload.sessionId, upload.jobId)
                upload.sessionId
            } else {
                session.backendSessionId
            }

            val report = sessionApi.getSessionReport(backendSessionId)
            if (report.status == "completed") {
                localRepo.markAnalyzed(localId, report.finalCount, report.malaCount, report.summaryText)
                if (session.retentionChoice == "delete") {
                    audioFile.delete()
                }
                Result.success(workDataOf(KEY_BACKEND_SESSION_ID to backendSessionId))
            } else {
                Result.retry()
            }
        } catch (error: Exception) {
            localRepo.markFailed(localId, error.message ?: "Upload failed")
            Result.retry()
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
