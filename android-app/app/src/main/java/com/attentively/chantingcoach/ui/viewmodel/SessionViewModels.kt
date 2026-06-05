package com.attentively.chantingcoach.ui.viewmodel

import android.app.Application
import android.content.Intent
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.attentively.chantingcoach.ChantingCoachApplication
import com.attentively.chantingcoach.data.local.LocalSessionEntity
import com.attentively.chantingcoach.data.model.DailyProgress
import com.attentively.chantingcoach.data.model.SessionReport
import com.attentively.chantingcoach.recording.RecordingForegroundService
import com.attentively.chantingcoach.work.UploadSessionWorker
import java.time.LocalDate
import java.util.UUID
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

data class HomeUiState(
    val loading: Boolean = false,
    val error: String? = null,
    val progress: DailyProgress? = null,
    val recentSessions: List<LocalSessionEntity> = emptyList(),
)

data class ReportUiState(
    val loading: Boolean = false,
    val sessionIdInput: String = "",
    val error: String? = null,
    val report: SessionReport? = null,
    val recentSessions: List<LocalSessionEntity> = emptyList(),
)

data class RecordSessionUiState(
    val isRecording: Boolean = false,
    val retentionChoice: String = "delete",
    val activeLocalSessionId: String? = null,
    val serviceHint: String = "Ready to record a chanting session.",
    val error: String? = null,
    val recentSessions: List<LocalSessionEntity> = emptyList(),
)

class HomeViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val appGraph = (application as ChantingCoachApplication).appGraph
    private val repository = appGraph.sessionsRepository
    private val localSessionsRepository = appGraph.localSessionsRepository

    private val remoteState = MutableStateFlow(HomeUiState())
    val recentSessions = localSessionsRepository.observeSessions()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val uiState: StateFlow<HomeUiState> = remoteState.asStateFlow()

    init {
        viewModelScope.launch {
            recentSessions.collect { sessions ->
                remoteState.value = remoteState.value.copy(recentSessions = sessions.take(5))
            }
        }
        refresh()
    }

    fun refresh(date: LocalDate = LocalDate.now()) {
        viewModelScope.launch {
            remoteState.value = remoteState.value.copy(loading = true, error = null)
            runCatching { repository.getDailyProgress(date.toString()) }
                .onSuccess { progress ->
                    remoteState.value = remoteState.value.copy(
                        loading = false,
                        progress = progress,
                        error = null,
                    )
                }
                .onFailure { error ->
                    remoteState.value = remoteState.value.copy(
                        loading = false,
                        error = error.message ?: "Unable to load progress.",
                    )
                }
        }
    }

    fun retryUpload(localId: String) {
        viewModelScope.launch {
            localSessionsRepository.markStopped(localId)
            UploadSessionWorker.enqueue(getApplication(), localId)
        }
    }
}

class ReportViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val appGraph = (application as ChantingCoachApplication).appGraph
    private val repository = appGraph.sessionsRepository
    private val localSessionsRepository = appGraph.localSessionsRepository

    private val _uiState = MutableStateFlow(ReportUiState())
    val uiState: StateFlow<ReportUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            localSessionsRepository.observeSessions().collect { sessions ->
                _uiState.value = _uiState.value.copy(recentSessions = sessions.take(8))
            }
        }
    }

    fun updateSessionId(sessionId: String) {
        _uiState.value = _uiState.value.copy(sessionIdInput = sessionId)
    }

    fun useBackendSession(session: LocalSessionEntity) {
        session.backendSessionId?.let { updateSessionId(it) }
    }

    fun loadReport() {
        val targetId = _uiState.value.sessionIdInput.trim()
        if (targetId.isEmpty()) {
            _uiState.value = _uiState.value.copy(error = "Enter a session id first.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            runCatching { repository.getSessionReport(targetId) }
                .onSuccess { report ->
                    _uiState.value = _uiState.value.copy(loading = false, report = report, error = null)
                }
                .onFailure { error ->
                    _uiState.value = _uiState.value.copy(
                        loading = false,
                        error = error.message ?: "Unable to load report.",
                    )
                }
        }
    }

    fun retryUpload(localId: String) {
        viewModelScope.launch {
            localSessionsRepository.markStopped(localId)
            UploadSessionWorker.enqueue(getApplication(), localId)
        }
    }
}

class RecordSessionViewModel(
    application: Application,
) : AndroidViewModel(application) {
    private val appGraph = (application as ChantingCoachApplication).appGraph
    private val localSessionsRepository = appGraph.localSessionsRepository
    private val recorder = appGraph.recorder
    private val appContext = application.applicationContext

    private val _uiState = MutableStateFlow(RecordSessionUiState())
    val uiState: StateFlow<RecordSessionUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            localSessionsRepository.observeSessions().collect { sessions ->
                _uiState.value = _uiState.value.copy(recentSessions = sessions.take(6))
            }
        }
    }

    fun setRetentionChoice(choice: String) {
        _uiState.value = _uiState.value.copy(retentionChoice = choice)
    }

    fun retryUpload(localId: String) {
        viewModelScope.launch {
            localSessionsRepository.markStopped(localId)
            UploadSessionWorker.enqueue(appContext, localId)
        }
    }

    fun startRecording() {
        if (_uiState.value.isRecording) return
        viewModelScope.launch {
            runCatching {
                val localId = UUID.randomUUID().toString()
                val audioFile = recorder.start(localId)
                localSessionsRepository.createRecordingSessionWithKnownId(
                    localId = localId,
                    audioFile = audioFile,
                    retentionChoice = _uiState.value.retentionChoice,
                )
                val serviceIntent = Intent(appContext, RecordingForegroundService::class.java)
                appContext.startForegroundService(serviceIntent)
                localId
            }.onSuccess { localId ->
                _uiState.value = _uiState.value.copy(
                    isRecording = true,
                    activeLocalSessionId = localId,
                    serviceHint = "Recording in progress. Stop when your chanting session ends.",
                    error = null,
                )
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    error = error.message ?: "Unable to start recording.",
                )
            }
        }
    }

    fun stopRecording() {
        val localId = _uiState.value.activeLocalSessionId ?: return
        viewModelScope.launch {
            runCatching {
                recorder.stop()
                localSessionsRepository.markStopped(localId)
                appContext.stopService(Intent(appContext, RecordingForegroundService::class.java))
                UploadSessionWorker.enqueue(appContext, localId)
            }.onSuccess {
                _uiState.value = _uiState.value.copy(
                    isRecording = false,
                    activeLocalSessionId = null,
                    serviceHint = "Recording finished. Upload and analysis queued.",
                    error = null,
                )
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    isRecording = false,
                    activeLocalSessionId = null,
                    error = error.message ?: "Unable to stop recording cleanly.",
                )
            }
        }
    }

    fun uploadFile(uri: android.net.Uri) {
        viewModelScope.launch {
            runCatching {
                val localId = java.util.UUID.randomUUID().toString()
                var extension = "wav"
                appContext.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                    if (cursor.moveToFirst()) {
                        val displayNameIndex = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                        if (displayNameIndex != -1) {
                            val displayName = cursor.getString(displayNameIndex)
                            if (displayName != null && displayName.contains(".")) {
                                extension = displayName.substringAfterLast('.')
                            }
                        }
                    }
                }
                val outputDir = java.io.File(appContext.filesDir, "recordings").apply { mkdirs() }
                val audioFile = java.io.File(outputDir, "$localId.$extension")
                appContext.contentResolver.openInputStream(uri)?.use { input ->
                    audioFile.outputStream().use { output ->
                        input.copyTo(output)
                    }
                } ?: throw IllegalStateException("Could not open input stream for URI")

                localSessionsRepository.createRecordingSessionWithKnownId(
                    localId = localId,
                    audioFile = audioFile,
                    retentionChoice = _uiState.value.retentionChoice,
                )
                localSessionsRepository.markStopped(localId)
                UploadSessionWorker.enqueue(appContext, localId)
            }.onSuccess {
                _uiState.value = _uiState.value.copy(
                    error = null,
                    serviceHint = "File uploaded and queued for analysis."
                )
            }.onFailure { error ->
                _uiState.value = _uiState.value.copy(
                    error = error.message ?: "Unable to upload file."
                )
            }
        }
    }
}
