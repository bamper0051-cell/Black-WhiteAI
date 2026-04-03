package com.blackbugsai.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.blackbugsai.app.navigation.AppNavigation
import com.blackbugsai.app.ui.theme.BlackBugsAITheme
import com.blackbugsai.app.ui.theme.BgDeep

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            BlackBugsAITheme {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(BgDeep)
                ) {
                    AppNavigation()
                }
            }
        }
    }
}
