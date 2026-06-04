package com.attentively.chantingcoach.data.local

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import java.util.UUID
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.deviceStore by preferencesDataStore("device_profile")

class DeviceProfileStore(private val context: Context) {
    suspend fun getOrCreateDeviceId(): String {
        val key = stringPreferencesKey("device_id")
        val existing = context.deviceStore.data.map { it[key] }.first()
        if (existing != null) {
            return existing
        }
        val generated = UUID.randomUUID().toString()
        context.deviceStore.edit { prefs ->
            prefs[key] = generated
        }
        return generated
    }
}
