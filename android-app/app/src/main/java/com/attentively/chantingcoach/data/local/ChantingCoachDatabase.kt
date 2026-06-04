package com.attentively.chantingcoach.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [LocalSessionEntity::class],
    version = 1,
    exportSchema = false,
)
abstract class ChantingCoachDatabase : RoomDatabase() {
    abstract fun localSessionDao(): LocalSessionDao

    companion object {
        fun build(context: Context): ChantingCoachDatabase {
            return Room.databaseBuilder(
                context.applicationContext,
                ChantingCoachDatabase::class.java,
                "chanting_coach.db",
            )
            .fallbackToDestructiveMigration()
            .build()
        }
    }
}
