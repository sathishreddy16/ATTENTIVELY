package com.attentively.chantingcoach.data.repository

import com.attentively.chantingcoach.data.local.DeviceProfileStore
import com.attentively.chantingcoach.data.local.LocalSessionDao
import com.attentively.chantingcoach.data.local.LocalSessionEntity
import java.io.File
import java.time.Instant
import java.util.UUID
import kotlinx.coroutines.flow.Flow

class LocalSessionsRepository(
    private val sessionDao: LocalSessionDao,
    private val deviceProfileStore: DeviceProfileStore,
) {
    fun observeSessions(): Flow<List<LocalSessionEntity>> = sessionDao.observeAll()

    suspend fun createRecordingSession(audioFile: File, retentionChoice: String): LocalSessionEntity {
        val session = LocalSessionEntity(
            localId = UUID.randomUUID().toString(),
            deviceId = deviceProfileStore.getOrCreateDeviceId(),
            localAudioPath = audioFile.absolutePath,
            retentionChoice = retentionChoice,
            startedAt = Instant.now().toString(),
            uploadStatus = UploadStatus.RECORDING.name,
        )
        sessionDao.upsert(session)
        return session
    }

    suspend fun createRecordingSessionWithKnownId(localId: String, audioFile: File, retentionChoice: String): LocalSessionEntity {
        val session = LocalSessionEntity(
            localId = localId,
            deviceId = deviceProfileStore.getOrCreateDeviceId(),
            localAudioPath = audioFile.absolutePath,
            retentionChoice = retentionChoice,
            startedAt = Instant.now().toString(),
            uploadStatus = UploadStatus.RECORDING.name,
        )
        sessionDao.upsert(session)
        return session
    }

    suspend fun markStopped(localId: String) {
        sessionDao.markStopped(
            localId = localId,
            status = UploadStatus.PENDING_UPLOAD.name,
            endedAt = Instant.now().toString(),
            updatedAt = Instant.now().toString(),
        )
    }

    suspend fun markUploading(localId: String) {
        val session = requireNotNull(sessionDao.getById(localId))
        sessionDao.updateSyncState(
            localId = localId,
            status = UploadStatus.UPLOADING.name,
            backendSessionId = session.backendSessionId,
            backendJobId = session.backendJobId,
            finalCount = session.finalCount,
            malaCount = session.malaCount,
            summaryText = session.summaryText,
            lastError = null,
            updatedAt = Instant.now().toString(),
        )
    }

    suspend fun markUploaded(localId: String, backendSessionId: String, backendJobId: String) {
        val session = requireNotNull(sessionDao.getById(localId))
        sessionDao.updateSyncState(
            localId = localId,
            status = UploadStatus.ANALYSIS_PENDING.name,
            backendSessionId = backendSessionId,
            backendJobId = backendJobId,
            finalCount = session.finalCount,
            malaCount = session.malaCount,
            summaryText = session.summaryText,
            lastError = null,
            updatedAt = Instant.now().toString(),
        )
    }

    suspend fun markAnalyzed(localId: String, finalCount: Int, malaCount: Int, summaryText: String?) {
        val session = requireNotNull(sessionDao.getById(localId))
        sessionDao.updateSyncState(
            localId = localId,
            status = UploadStatus.COMPLETED.name,
            backendSessionId = session.backendSessionId,
            backendJobId = session.backendJobId,
            finalCount = finalCount,
            malaCount = malaCount,
            summaryText = summaryText,
            lastError = null,
            updatedAt = Instant.now().toString(),
        )
    }

    suspend fun markFailed(localId: String, error: String) {
        val session = requireNotNull(sessionDao.getById(localId))
        sessionDao.updateSyncState(
            localId = localId,
            status = UploadStatus.FAILED.name,
            backendSessionId = session.backendSessionId,
            backendJobId = session.backendJobId,
            finalCount = session.finalCount,
            malaCount = session.malaCount,
            summaryText = session.summaryText,
            lastError = error,
            updatedAt = Instant.now().toString(),
        )
    }

    suspend fun getById(localId: String): LocalSessionEntity? = sessionDao.getById(localId)
}

enum class UploadStatus {
    RECORDING,
    PENDING_UPLOAD,
    UPLOADING,
    ANALYSIS_PENDING,
    COMPLETED,
    FAILED,
}
