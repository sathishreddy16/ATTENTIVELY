package com.attentively.chantingcoach.recording

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import java.io.File
import java.io.IOException

class ChantingRecorder(private val context: Context) {
    private var recorder: MediaRecorder? = null
    private var currentFile: File? = null

    fun start(localId: String): File {
        val output = File(context.filesDir, "recordings").apply { mkdirs() }
        val audioFile = File(output, "$localId.m4a")
        val mediaRecorder = (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) MediaRecorder(context) else MediaRecorder()).apply {
            setAudioSource(MediaRecorder.AudioSource.MIC)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioEncodingBitRate(128000)
            setAudioSamplingRate(44100)
            setOutputFile(audioFile.absolutePath)
            prepare()
            start()
        }
        recorder = mediaRecorder
        currentFile = audioFile
        return audioFile
    }

    fun stop(): File {
        val activeRecorder = recorder ?: throw IOException("Recorder was not started.")
        try {
            activeRecorder.stop()
        } finally {
            activeRecorder.reset()
            activeRecorder.release()
            recorder = null
        }
        return currentFile ?: throw IOException("Recorded file is missing.")
    }

    fun isRecording(): Boolean = recorder != null
}
