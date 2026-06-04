package com.attentively.chantingcoach.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface LocalSessionDao {
    @Query("SELECT * FROM local_sessions ORDER BY startedAt DESC")
    fun observeAll(): Flow<List<LocalSessionEntity>>

    @Query("SELECT * FROM local_sessions WHERE localId = :localId LIMIT 1")
    suspend fun getById(localId: String): LocalSessionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(session: LocalSessionEntity)

    @Query("UPDATE local_sessions SET uploadStatus = :status, endedAt = :endedAt, updatedAt = :updatedAt WHERE localId = :localId")
    suspend fun markStopped(localId: String, status: String, endedAt: String, updatedAt: String)

    @Query(
        """
        UPDATE local_sessions
        SET uploadStatus = :status,
            backendSessionId = :backendSessionId,
            backendJobId = :backendJobId,
            finalCount = :finalCount,
            malaCount = :malaCount,
            summaryText = :summaryText,
            lastError = :lastError,
            updatedAt = :updatedAt
        WHERE localId = :localId
        """
    )
    suspend fun updateSyncState(
        localId: String,
        status: String,
        backendSessionId: String?,
        backendJobId: String?,
        finalCount: Int?,
        malaCount: Int?,
        summaryText: String?,
        lastError: String?,
        updatedAt: String,
    )
}
