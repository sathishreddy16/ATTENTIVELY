package com.attentively.chantingcoach

import android.app.Application
import com.attentively.chantingcoach.data.local.ChantingCoachDatabase
import com.attentively.chantingcoach.data.local.DeviceProfileStore
import com.attentively.chantingcoach.data.repository.LocalSessionsRepository
import com.attentively.chantingcoach.data.repository.SessionUploader
import com.attentively.chantingcoach.data.repository.SessionsRepository
import com.attentively.chantingcoach.recording.ChantingRecorder

class ChantingCoachApplication : Application() {
    lateinit var appGraph: AppGraph
        private set

    override fun onCreate() {
        super.onCreate()
        appGraph = AppGraph(this)
    }
}

class AppGraph(application: Application) {
    private val database = ChantingCoachDatabase.build(application)
    private val deviceStore = DeviceProfileStore(application)
    val sessionsRepository = SessionsRepository()
    private val uploader = SessionUploader(sessionsRepository)

    val localSessionsRepository = LocalSessionsRepository(
        sessionDao = database.localSessionDao(),
        deviceProfileStore = deviceStore,
    )

    val recorder = ChantingRecorder(application)
    val sessionUploader = uploader
}
