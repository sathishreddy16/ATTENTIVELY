package com.attentively.chantingcoach.playback

import android.content.Context
import android.os.Handler
import android.os.Looper
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer

class FlaggedClipPlayer(context: Context) {
    private val player = ExoPlayer.Builder(context).build()
    private val handler = Handler(Looper.getMainLooper())
    private var stopRunnable: Runnable? = null

    fun play(uri: String, startSec: Float, endSec: Float) {
        stopRunnable?.let(handler::removeCallbacks)
        player.setMediaItem(MediaItem.fromUri(uri))
        player.prepare()
        player.seekTo((startSec * 1000).toLong())
        player.play()
        val durationMs = ((endSec - startSec).coerceAtLeast(0.5f) * 1000).toLong()
        stopRunnable = Runnable { player.pause() }.also {
            handler.postDelayed(it, durationMs)
        }
    }

    fun release() {
        stopRunnable?.let(handler::removeCallbacks)
        player.release()
    }
}
