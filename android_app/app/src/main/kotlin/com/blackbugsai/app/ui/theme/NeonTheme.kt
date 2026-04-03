package com.blackbugsai.app.ui.theme

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Paint
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

// ── Neon palette ──────────────────────────────────────────────────────────────
val NeonCyan    = Color(0xFF00D4FF)
val NeonPurple  = Color(0xFFBF00FF)
val NeonPink    = Color(0xFFFF0080)
val NeonGreen   = Color(0xFF00FF88)
val NeonYellow  = Color(0xFFFFE600)
val BgDeep      = Color(0xFF010B13)
val BgDark      = Color(0xFF020D18)
val BgCard      = Color(0xFF041220)
val TextPrimary   = Color(0xFFE0FFFF)
val TextSecondary = Color(0xFF7AA8B8)

// ── Glow shadow modifier ──────────────────────────────────────────────────────
fun Modifier.neonGlow(
    glowColor: Color = NeonCyan,
    glowRadius: Dp = 12.dp,
    cornerRadius: Dp = 12.dp
): Modifier = this.drawBehind {
    drawIntoCanvas { canvas ->
        val paint = Paint().apply {
            asFrameworkPaint().apply {
                isAntiAlias = true
                color = android.graphics.Color.TRANSPARENT
                setShadowLayer(
                    glowRadius.toPx(),
                    0f, 0f,
                    glowColor.copy(alpha = 0.85f).toArgb()
                )
            }
        }
        canvas.drawRoundRect(
            left   = 0f,
            top    = 0f,
            right  = size.width,
            bottom = size.height,
            radiusX = cornerRadius.toPx(),
            radiusY = cornerRadius.toPx(),
            paint   = paint
        )
    }
}

// ── NeonCard ──────────────────────────────────────────────────────────────────
@Composable
fun NeonCard(
    modifier: Modifier = Modifier,
    borderColor: Color = NeonCyan,
    cornerRadius: Dp = 12.dp,
    content: @Composable () -> Unit
) {
    Card(
        modifier = modifier
            .neonGlow(glowColor = borderColor, cornerRadius = cornerRadius)
            .border(
                width = 1.dp,
                color = borderColor.copy(alpha = 0.8f),
                shape = RoundedCornerShape(cornerRadius)
            ),
        shape = RoundedCornerShape(cornerRadius),
        colors = CardDefaults.cardColors(containerColor = BgCard)
    ) {
        content()
    }
}

// ── NeonButton ────────────────────────────────────────────────────────────────
@Composable
fun NeonButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    borderColor: Color = NeonCyan,
    enabled: Boolean = true,
    content: @Composable () -> Unit
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .then(
                if (enabled) Modifier.neonGlow(glowColor = borderColor, glowRadius = 8.dp)
                else Modifier
            )
            .border(
                width = 1.dp,
                color = if (enabled) borderColor else borderColor.copy(alpha = 0.3f),
                shape = RoundedCornerShape(8.dp)
            ),
        shape = RoundedCornerShape(8.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = borderColor.copy(alpha = 0.15f),
            contentColor   = borderColor,
            disabledContainerColor = borderColor.copy(alpha = 0.05f),
            disabledContentColor   = borderColor.copy(alpha = 0.4f)
        )
    ) {
        content()
    }
}

// ── NeonTextField ─────────────────────────────────────────────────────────────
@Composable
fun NeonTextField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    label: String = "",
    placeholder: String = "",
    singleLine: Boolean = true,
    accentColor: Color = NeonCyan
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = modifier,
        label = { Text(label, color = accentColor.copy(alpha = 0.8f)) },
        placeholder = { Text(placeholder, color = TextSecondary) },
        singleLine = singleLine,
        colors = OutlinedTextFieldDefaults.colors(
            focusedTextColor      = TextPrimary,
            unfocusedTextColor    = TextPrimary,
            cursorColor           = accentColor,
            focusedBorderColor    = accentColor,
            unfocusedBorderColor  = accentColor.copy(alpha = 0.4f),
            focusedLabelColor     = accentColor,
            unfocusedLabelColor   = accentColor.copy(alpha = 0.6f),
            focusedContainerColor    = BgCard,
            unfocusedContainerColor  = BgCard
        )
    )
}

// ── App-wide Material3 theme wrapper ─────────────────────────────────────────
private val NeonColorScheme = darkColorScheme(
    primary          = NeonCyan,
    onPrimary        = BgDeep,
    secondary        = NeonPurple,
    onSecondary      = BgDeep,
    tertiary         = NeonPink,
    background       = BgDeep,
    surface          = BgDark,
    onBackground     = TextPrimary,
    onSurface        = TextPrimary,
    surfaceVariant   = BgCard,
    onSurfaceVariant = TextSecondary
)

@Composable
fun BlackBugsAITheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = NeonColorScheme,
        typography  = Typography(),
        content     = content
    )
}
