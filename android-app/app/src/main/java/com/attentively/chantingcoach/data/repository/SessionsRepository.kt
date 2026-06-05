package com.attentively.chantingcoach.data.repository

import com.attentively.chantingcoach.BuildConfig
import com.attentively.chantingcoach.data.model.DailyProgress
import com.attentively.chantingcoach.data.model.FlaggedMantra
import com.attentively.chantingcoach.data.model.SessionReport
import com.attentively.chantingcoach.data.network.CompleteUploadRequestDto
import com.attentively.chantingcoach.data.network.SessionCreateRequestDto
import com.attentively.chantingcoach.data.network.SessionsApi
import com.attentively.chantingcoach.data.network.UploadInitRequestDto
import java.io.File
import java.time.Instant
import java.util.concurrent.TimeUnit
import okhttp3.MediaType
import okhttp3.OkHttpClient
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

class SessionsRepository(
    private val api: SessionsApi = Retrofit.Builder()
        .baseUrl(BuildConfig.BACKEND_BASE_URL)
        .client(
            OkHttpClient.Builder()
                .connectTimeout(90, TimeUnit.SECONDS)
                .readTimeout(90, TimeUnit.SECONDS)
                .writeTimeout(90, TimeUnit.SECONDS)
                .build()
        )
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(SessionsApi::class.java),
) {
    suspend fun getDailyProgress(date: String): DailyProgress {
        val dto = api.getDailyProgress(date)
        return DailyProgress(
            date = dto.date,
            totalCount = dto.total_count,
            totalMalas = dto.total_malas,
            remainingToSixteen = dto.remaining_to_sixteen,
            completedSessionIds = dto.completed_session_ids,
        )
    }

    suspend fun getSessionReport(sessionId: String): SessionReport {
        val dto = api.getSessionReport(sessionId)
        return SessionReport(
            sessionId = dto.session_id,
            status = dto.status,
            analysisProvider = dto.analysis_provider,
            analysisProviderVersion = dto.analysis_provider_version,
            audioPlaybackUrl = dto.audio_playback_url,
            finalCount = dto.final_count,
            malaCount = dto.mala_count,
            yellowFlagCount = dto.yellow_flag_count,
            redFlagCount = dto.red_flag_count,
            grayFlagCount = dto.gray_flag_count,
            pronunciationScore = dto.pronunciation_score,
            summaryText = dto.summary_text,
            flaggedMantras = dto.flagged_mantras.map { flagged ->
                FlaggedMantra(
                    id = flagged.id,
                    startSec = flagged.start_sec,
                    endSec = flagged.end_sec,
                    flagColor = flagged.flag_color,
                    issueType = flagged.issue_type,
                    expectedText = flagged.expected_text,
                    detectedText = flagged.detected_text,
                    counted = flagged.counted,
                    playbackAvailable = flagged.playback_available,
                )
            },
        )
    }

    suspend fun createSession(
        deviceId: String,
        retentionChoice: String,
        originalFilename: String?,
        startedAt: Instant = Instant.now(),
    ): String {
        val response = api.createSession(
            SessionCreateRequestDto(
                device_id = deviceId,
                started_at = startedAt.toString(),
                retention_choice = retentionChoice,
                original_filename = originalFilename,
            )
        )
        return response.session_id
    }

    suspend fun initUpload(sessionId: String, audioFile: File, mimeType: String): Int {
        val response = api.initUpload(
            sessionId = sessionId,
            request = UploadInitRequestDto(
                file_size_bytes = audioFile.length(),
                mime_type = mimeType,
            ),
        )
        return response.max_chunk_bytes
    }

    suspend fun uploadChunk(
        sessionId: String,
        chunkIndex: Int,
        chunkFile: File,
        mimeType: String,
    ) {
        val body = RequestBody.create(MediaType.parse(mimeType), chunkFile)
        val part = MultipartBody.Part.createFormData("file", chunkFile.name, body)
        api.uploadChunk(sessionId, chunkIndex, part)
    }

    suspend fun completeUpload(sessionId: String, endedAt: Instant = Instant.now()): String {
        val response = api.completeUpload(sessionId, CompleteUploadRequestDto(ended_at = endedAt.toString()))
        return response.job_id
    }
}
