package com.attentively.chantingcoach.data.repository

import java.io.File
import java.time.Instant

class SessionUploader(
    private val repository: SessionsRepository = SessionsRepository(),
) {
    suspend fun uploadRecordedSession(
        audioFile: File,
        deviceId: String,
        retentionChoice: String = "delete",
        mimeType: String = "audio/mp4",
        startedAt: Instant = Instant.now(),
        endedAt: Instant = Instant.now(),
    ): UploadSubmissionResult {
        val sessionId = repository.createSession(
            deviceId = deviceId,
            retentionChoice = retentionChoice,
            originalFilename = audioFile.name,
            startedAt = startedAt,
        )
        val chunkSize = repository.initUpload(sessionId, audioFile, mimeType)
        val chunkFiles = audioFile.splitIntoChunkFiles(chunkSize)
        try {
            chunkFiles.forEachIndexed { index, chunk ->
                repository.uploadChunk(
                    sessionId = sessionId,
                    chunkIndex = index,
                    chunkFile = chunk,
                    mimeType = "application/octet-stream",
                )
            }
        } finally {
            chunkFiles.forEach(File::delete)
        }
        val jobId = repository.completeUpload(sessionId, endedAt)
        return UploadSubmissionResult(sessionId = sessionId, jobId = jobId)
    }
}

data class UploadSubmissionResult(
    val sessionId: String,
    val jobId: String,
)

private fun File.splitIntoChunkFiles(chunkSize: Int): List<File> {
    require(chunkSize > 0) { "chunkSize must be positive" }

    val chunks = mutableListOf<File>()
    var index = 0
    inputStream().use { input ->
        val buffer = ByteArray(chunkSize)
        while (true) {
            val bytesRead = input.read(buffer)
            if (bytesRead <= 0) {
                break
            }

            val chunkFile = File(parentFile ?: error("Audio file parent directory is required"), "$nameWithoutExtension-$index.part")
            chunkFile.outputStream().use { output ->
                output.write(buffer, 0, bytesRead)
            }
            chunks += chunkFile
            index += 1
        }
    }
    return chunks
}
