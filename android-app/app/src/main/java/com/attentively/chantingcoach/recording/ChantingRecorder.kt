package com.attentively.chantingcoach.recording

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.core.app.ActivityCompat
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.io.RandomAccessFile
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean

class ChantingRecorder(private val context: Context) {
    private var audioRecord: AudioRecord? = null
    private var currentFile: File? = null
    private var recordingThread: Thread? = null
    private val isRecordingFlag = AtomicBoolean(false)

    private val sampleRate = 44100
    private val channelConfig = AudioFormat.CHANNEL_IN_MONO
    private val audioFormat = AudioFormat.ENCODING_PCM_16BIT

    fun start(localId: String): File {
        val output = File(context.filesDir, "recordings").apply { mkdirs() }
        val audioFile = File(output, "$localId.wav")

        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            throw IOException("RECORD_AUDIO permission not granted")
        }

        val bufferSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)
        if (bufferSize == AudioRecord.ERROR || bufferSize == AudioRecord.ERROR_BAD_VALUE) {
            throw IOException("Invalid audio format parameters")
        }

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            sampleRate,
            channelConfig,
            audioFormat,
            bufferSize * 2
        )

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            throw IOException("AudioRecord failed to initialize")
        }

        currentFile = audioFile
        isRecordingFlag.set(true)
        audioRecord?.startRecording()

        recordingThread = Thread {
            writeAudioDataToFile(audioFile, bufferSize * 2)
        }.apply { start() }

        return audioFile
    }

    private fun writeAudioDataToFile(file: File, bufferSize: Int) {
        val data = ByteArray(bufferSize)
        try {
            FileOutputStream(file).use { fos ->
                val emptyHeader = ByteArray(44)
                fos.write(emptyHeader)

                while (isRecordingFlag.get()) {
                    val read = audioRecord?.read(data, 0, bufferSize) ?: 0
                    if (read > 0) {
                        fos.write(data, 0, read)
                    }
                }
            }
            writeWavHeader(file)
        } catch (e: IOException) {
            e.printStackTrace()
        }
    }

    private fun writeWavHeader(file: File) {
        val totalAudioLen = file.length() - 44
        val totalDataLen = totalAudioLen + 36
        val channels = 1
        val byteRate = (sampleRate * channels * 16) / 8

        try {
            RandomAccessFile(file, "rw").use { raf ->
                raf.seek(0)
                
                val header = ByteBuffer.allocate(44).apply {
                    order(ByteOrder.LITTLE_ENDIAN)
                    put("RIFF".toByteArray())
                    putInt(totalDataLen.toInt())
                    put("WAVE".toByteArray())
                    put("fmt ".toByteArray())
                    putInt(16) // Subchunk1Size
                    putShort(1.toShort()) // AudioFormat (PCM)
                    putShort(channels.toShort()) // NumChannels
                    putInt(sampleRate) // SampleRate
                    putInt(byteRate) // ByteRate
                    putShort((channels * 16 / 8).toShort()) // BlockAlign
                    putShort(16.toShort()) // BitsPerSample
                    put("data".toByteArray())
                    putInt(totalAudioLen.toInt())
                }.array()
                
                raf.write(header)
            }
        } catch (e: IOException) {
            e.printStackTrace()
        }
    }

    fun stop(): File {
        if (!isRecordingFlag.get()) {
            throw IOException("Recorder was not started.")
        }
        isRecordingFlag.set(false)
        
        try {
            audioRecord?.stop()
        } catch (e: IllegalStateException) {
            e.printStackTrace()
        }
        
        audioRecord?.release()
        audioRecord = null
        
        recordingThread?.join(2000)
        recordingThread = null
        
        return currentFile ?: throw IOException("Recorded file is missing.")
    }

    fun isRecording(): Boolean = isRecordingFlag.get()
}
