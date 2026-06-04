package com.attentively.chantingcoach

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import com.attentively.chantingcoach.ui.screens.HomeScreen
import com.attentively.chantingcoach.ui.screens.RecordSessionScreen
import com.attentively.chantingcoach.ui.screens.ReportScreen

@Composable
fun ChantingCoachApp() {
    var tab by remember { mutableStateOf("home") }

    MaterialTheme {
        Surface(modifier = Modifier.fillMaxSize()) {
            Scaffold(
                bottomBar = {
                    NavigationBar {
                        listOf("home", "record", "report").forEach { item ->
                            NavigationBarItem(
                                selected = tab == item,
                                onClick = { tab = item },
                                label = { Text(item.replaceFirstChar { it.uppercase() }) },
                                icon = {},
                            )
                        }
                    }
                }
            ) { paddingValues ->
                when (tab) {
                    "home" -> HomeScreen(paddingValues = paddingValues)
                    "record" -> RecordSessionScreen(paddingValues = paddingValues)
                    else -> ReportScreen(paddingValues = paddingValues)
                }
            }
        }
    }
}
