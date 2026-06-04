package com.attentively.chantingcoach.data.network

import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Query
import retrofit2.http.Multipart
import retrofit2.http.Part

data class SessionCreateRequestDto(
    val device_id: String,
    val started_at: String,
    val retention_choice: String,
    val original_filename: String? = null,
)

data class SessionCreateResponseDto(
    val session_id: String,
    val status: String,
)

data class UploadInitRequestDto(
    val file_size_bytes: Long,
    val mime_type: String? = null,
)

data class UploadInitResponseDto(
    val session_id: String,
    val max_chunk_bytes: Int,
    val status: String,
)

data class UploadChunkResponseDto(
    val session_id: String,
    val chunk_index: Int,
    val size_bytes: Int,
    val status: String,
)

data class CompleteUploadRequestDto(
    val ended_at: String,
)

data class CompleteUploadResponseDto(
    val job_id: String,
    val session_id: String,
    val status: String,
)

data class DailyProgressDto(
    val date: String,
    val total_count: Int,
    val total_malas: Int,
    val remaining_to_sixteen: Int,
    val completed_session_ids: List<String>,
)

data class FlaggedMantraDto(
    val id: String,
    val start_sec: Float,
    val end_sec: Float,
    val flag_color: String,
    val issue_type: String,
    val expected_text: String,
    val detected_text: String,
    val counted: Boolean,
    val playback_available: Boolean,
)

data class SessionReportDto(
    val session_id: String,
    val status: String,
    val analysis_provider: String?,
    val analysis_provider_version: String?,
    val audio_playback_url: String?,
    val final_count: Int,
    val mala_count: Int,
    val yellow_flag_count: Int,
    val red_flag_count: Int,
    val gray_flag_count: Int,
    val pronunciation_score: Float,
    val summary_text: String,
    val flagged_mantras: List<FlaggedMantraDto>,
)

interface SessionsApi {
    @POST("sessions")
    suspend fun createSession(@Body request: SessionCreateRequestDto): SessionCreateResponseDto

    @POST("sessions/{sessionId}/upload/init")
    suspend fun initUpload(
        @Path("sessionId") sessionId: String,
        @Body request: UploadInitRequestDto,
    ): UploadInitResponseDto

    @Multipart
    @PUT("sessions/{sessionId}/upload/chunks/{chunkIndex}")
    suspend fun uploadChunk(
        @Path("sessionId") sessionId: String,
        @Path("chunkIndex") chunkIndex: Int,
        @Part file: MultipartBody.Part,
    ): UploadChunkResponseDto

    @POST("sessions/{sessionId}/upload/complete")
    suspend fun completeUpload(
        @Path("sessionId") sessionId: String,
        @Body request: CompleteUploadRequestDto,
    ): CompleteUploadResponseDto

    @GET("daily-progress")
    suspend fun getDailyProgress(@Query("date") date: String): DailyProgressDto

    @GET("sessions/{sessionId}/report")
    suspend fun getSessionReport(@Path("sessionId") sessionId: String): SessionReportDto
}
