package com.attentively.chantingcoach.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.core.content.ContextCompat
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.attentively.chantingcoach.playback.FlaggedClipPlayer
import com.attentively.chantingcoach.ui.viewmodel.HomeViewModel
import com.attentively.chantingcoach.ui.viewmodel.RecordSessionViewModel
import com.attentively.chantingcoach.ui.viewmodel.ReportViewModel
import androidx.lifecycle.viewmodel.compose.viewModel

@Composable
fun HomeScreen(
    paddingValues: PaddingValues,
    viewModel: HomeViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Today's Chanting")
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text("Count: ${uiState.progress?.totalCount ?: 0}")
                Text("Malas: ${uiState.progress?.totalMalas ?: 0}")
                Text("Remaining to 16: ${uiState.progress?.remainingToSixteen ?: 16}")
                if (uiState.loading) {
                    CircularProgressIndicator(modifier = Modifier.padding(top = 12.dp))
                }
            }
        }
        uiState.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Text(
            "Completed sessions today: ${uiState.progress?.completedSessionIds?.joinToString().orEmpty().ifEmpty { "None yet" }}"
        )
        Text("Local recent sessions")
        uiState.recentSessions.take(4).forEach { session ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Local session: ${session.localId.take(8)}")
                    Text("Status: ${session.uploadStatus}")
                    session.lastError?.let {
                        Text("Error: $it", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                    if (session.uploadStatus == "FAILED") {
                        Button(
                            onClick = { viewModel.retryUpload(session.localId) },
                            modifier = Modifier.padding(top = 4.dp)
                        ) {
                            Text("Retry Upload")
                        }
                    }
                    Text("Backend: ${session.backendSessionId ?: "Not uploaded yet"}")
                }
            }
        }
        Button(onClick = { viewModel.refresh() }) {
            Text("Refresh Progress")
        }
    }
}

@Composable
fun RecordSessionScreen(
    paddingValues: PaddingValues,
    viewModel: RecordSessionViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission(),
        onResult = { granted ->
            if (granted) {
                viewModel.startRecording()
            }
        },
    )
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Recording Session")
        Text(uiState.serviceHint)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = uiState.retentionChoice == "delete",
                onClick = { viewModel.setRetentionChoice("delete") },
                label = { Text("Delete audio") },
            )
            FilterChip(
                selected = uiState.retentionChoice == "keep",
                onClick = { viewModel.setRetentionChoice("keep") },
                label = { Text("Keep audio") },
            )
        }
        val filePickerLauncher = rememberLauncherForActivityResult(
            contract = ActivityResultContracts.GetContent()
        ) { uri ->
            if (uri != null) {
                viewModel.uploadFile(uri)
            }
        }

        uiState.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(
            onClick = {
                val granted = ContextCompat.checkSelfPermission(
                    context,
                    Manifest.permission.RECORD_AUDIO,
                ) == PackageManager.PERMISSION_GRANTED
                if (granted) {
                    viewModel.startRecording()
                } else {
                    permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                }
            },
            enabled = !uiState.isRecording,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Start Recording")
        }
        Button(
            onClick = viewModel::stopRecording, 
            enabled = uiState.isRecording,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Stop and Analyze")
        }
        Button(
            onClick = { filePickerLauncher.launch("audio/*") },
            enabled = !uiState.isRecording,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Upload Audio File")
        }
        Text("Recent local sessions")
        uiState.recentSessions.forEach { session ->
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("Local ID: ${session.localId.take(8)}")
                    Text("Upload status: ${session.uploadStatus}")
                    session.lastError?.let {
                        Text("Error: $it", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                    if (session.uploadStatus == "FAILED") {
                        Button(
                            onClick = { viewModel.retryUpload(session.localId) },
                            modifier = Modifier.padding(top = 4.dp)
                        ) {
                            Text("Retry Upload")
                        }
                    }
                    Text("Summary: ${session.summaryText ?: "Pending analysis"}")
                }
            }
        }
    }
}

@Composable
fun ReportScreen(
    paddingValues: PaddingValues,
    viewModel: ReportViewModel = viewModel(),
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val player = remember { FlaggedClipPlayer(context) }

    DisposableEffect(Unit) {
        onDispose { player.release() }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(paddingValues)
            .padding(16.dp)
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("Session Report")
        OutlinedTextField(
            value = uiState.sessionIdInput,
            onValueChange = viewModel::updateSessionId,
            label = { Text("Session ID") },
            modifier = Modifier.fillMaxWidth(),
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = viewModel::loadReport) {
                Text("Load Report")
            }
            if (uiState.loading) {
                CircularProgressIndicator()
            }
        }
        uiState.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        if (uiState.recentSessions.isNotEmpty()) {
            Text("Recent analyzed/uploaded sessions")
            uiState.recentSessions.forEach { session ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable(enabled = session.backendSessionId != null) {
                            viewModel.useBackendSession(session)
                        }
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text("Local: ${session.localId.take(8)}")
                        Text("Backend: ${session.backendSessionId ?: "Not available yet"}")
                        Text("Status: ${session.uploadStatus}")
                        session.lastError?.let {
                            Text("Error: $it", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                        }
                        if (session.uploadStatus == "FAILED") {
                            Button(
                                onClick = { viewModel.retryUpload(session.localId) },
                                modifier = Modifier.padding(top = 4.dp)
                            ) {
                                Text("Retry Upload")
                            }
                        }
                    }
                }
            }
        }

        val report = uiState.report
        Text("Count: ${report?.finalCount ?: 0}")
        Text("Malas: ${report?.malaCount ?: 0}")
        Text(
            "Yellow: ${report?.yellowFlagCount ?: 0}  Red: ${report?.redFlagCount ?: 0}  Gray: ${report?.grayFlagCount ?: 0}"
        )
        report?.summaryText?.let { Text(it) }
        (report?.flaggedMantras ?: emptyList()).forEach { flagged ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable(
                        enabled = flagged.playbackAvailable && report?.audioPlaybackUrl != null,
                    ) {
                        report?.audioPlaybackUrl?.let { url ->
                            player.play(url, flagged.startSec, flagged.endSec)
                        }
                    }
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text("${flagged.flagColor.uppercase()} - ${flagged.issueType}")
                    Text("Detected: ${flagged.detectedText}")
                    Text("Time: ${flagged.startSec}s to ${flagged.endSec}s")
                    Text(if (flagged.playbackAvailable) "Tap to play clip" else "Playback unavailable")
                }
            }
        }
    }
}
