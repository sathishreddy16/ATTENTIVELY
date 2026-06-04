package com.attentively.chantingcoach.data.model

data class DailyProgress(
    val date: String,
    val totalCount: Int,
    val totalMalas: Int,
    val remainingToSixteen: Int,
    val completedSessionIds: List<String>,
)

data class FlaggedMantra(
    val id: String,
    val startSec: Float,
    val endSec: Float,
    val flagColor: String,
    val issueType: String,
    val expectedText: String,
    val detectedText: String,
    val counted: Boolean,
    val playbackAvailable: Boolean,
)

data class SessionReport(
    val sessionId: String,
    val status: String,
    val analysisProvider: String?,
    val analysisProviderVersion: String?,
    val audioPlaybackUrl: String?,
    val finalCount: Int,
    val malaCount: Int,
    val yellowFlagCount: Int,
    val redFlagCount: Int,
    val grayFlagCount: Int,
    val pronunciationScore: Float,
    val summaryText: String,
    val flaggedMantras: List<FlaggedMantra>,
)
