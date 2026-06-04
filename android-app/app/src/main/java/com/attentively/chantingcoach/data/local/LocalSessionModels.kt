package com.attentively.chantingcoach.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.time.Instant

@Entity(tableName = "local_sessions")
data class LocalSessionEntity(
    @PrimaryKey val localId: String,
    val deviceId: String,
    val localAudioPath: String,
    val retentionChoice: String,
    val startedAt: String,
    val endedAt: String? = null,
    val uploadStatus: String,
    val backendSessionId: String? = null,
    val backendJobId: String? = null,
    val finalCount: Int? = null,
    val malaCount: Int? = null,
    val summaryText: String? = null,
    val lastError: String? = null,
    val updatedAt: String = Instant.now().toString(),
)

fun LocalSessionEntity.startedInstant(): Instant = Instant.parse(startedAt)
