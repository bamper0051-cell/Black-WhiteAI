package com.blackbugsai.app.ui.screens

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.webkit.MimeTypeMap
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.blackbugsai.app.AppViewModel
import com.blackbugsai.app.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.*
import java.net.HttpURLConnection
import java.net.URL
import java.text.SimpleDateFormat
import java.util.*

// ── File model ────────────────────────────────────────────────────────────────
data class ManagedFile(
    val name: String,
    val path: String,
    val size: Long,
    val type: FileType,
    val modified: String
)

enum class FileType { DOCUMENT, ARCHIVE, IMAGE, APK, CODE, OTHER }

fun fileTypeFor(name: String): FileType {
    val ext = name.substringAfterLast('.', "").lowercase()
    return when (ext) {
        "pdf","doc","docx","txt","xls","xlsx","ppt","pptx","csv","json","xml" -> FileType.DOCUMENT
        "zip","rar","7z","tar","gz","bz2"                                     -> FileType.ARCHIVE
        "jpg","jpeg","png","gif","webp","bmp","svg"                           -> FileType.IMAGE
        "apk"                                                                  -> FileType.APK
        "py","kt","java","js","ts","html","css","sh","dart"                   -> FileType.CODE
        else                                                                   -> FileType.OTHER
    }
}

fun fileIcon(type: FileType): ImageVector = when (type) {
    FileType.DOCUMENT -> Icons.Filled.Description
    FileType.ARCHIVE  -> Icons.Filled.FolderZip
    FileType.IMAGE    -> Icons.Filled.Image
    FileType.APK      -> Icons.Filled.Android
    FileType.CODE     -> Icons.Filled.Code
    FileType.OTHER    -> Icons.Filled.InsertDriveFile
}

fun fileColor(type: FileType): Color = when (type) {
    FileType.DOCUMENT -> NeonCyan
    FileType.ARCHIVE  -> NeonYellow
    FileType.IMAGE    -> NeonPink
    FileType.APK      -> NeonGreen
    FileType.CODE     -> NeonPurple
    FileType.OTHER    -> TextSecondary
}

fun formatSize(bytes: Long): String = when {
    bytes < 1024       -> "${bytes} B"
    bytes < 1024*1024  -> "${bytes/1024} KB"
    else               -> "${"%.1f".format(bytes/1024.0/1024.0)} MB"
}

@Composable
fun FileManagerScreen(vm: AppViewModel) {
    val context = LocalContext.current
    val scope   = rememberCoroutineScope()

    var files by remember { mutableStateOf(loadFiles(context)) }
    var downloadUrl by remember { mutableStateOf("") }
    var downloadProgress by remember { mutableFloatStateOf(-1f) }
    var downloadStatus  by remember { mutableStateOf("") }
    var showDownloadBar by remember { mutableStateOf(false) }
    var filterType by remember { mutableStateOf<FileType?>(null) }
    var selectedFile by remember { mutableStateOf<ManagedFile?>(null) }

    // File picker launcher
    val filePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let {
            scope.launch(Dispatchers.IO) {
                importFileFromUri(context, it)?.let { file ->
                    withContext(Dispatchers.Main) { files = loadFiles(context) }
                }
            }
        }
    }

    val displayed = if (filterType == null) files else files.filter { it.type == filterType }

    Column(modifier = Modifier.fillMaxSize().background(BgDeep)) {

        // ── Top bar ───────────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth().background(BgDark).padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(Icons.Filled.Folder, contentDescription = null, tint = NeonYellow, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
            Text("> ФАЙЛЫ", color = NeonYellow, fontSize = 15.sp, fontWeight = FontWeight.Bold,
                fontFamily = FontFamily.Monospace, modifier = Modifier.weight(1f))
            Text("${files.size} файлов", color = TextSecondary, fontSize = 11.sp, fontFamily = FontFamily.Monospace)
        }

        // ── Actions ───────────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth().background(BgDark).padding(horizontal = 8.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            ActionChip(
                label = "ДОБАВИТЬ",
                icon = Icons.Filled.AttachFile,
                color = NeonGreen
            ) { filePicker.launch("*/*") }

            ActionChip(
                label = "СКАЧАТЬ",
                icon = Icons.Filled.Download,
                color = NeonCyan
            ) { showDownloadBar = !showDownloadBar }

            ActionChip(
                label = "ОБНОВИТЬ",
                icon = Icons.Filled.Refresh,
                color = TextSecondary
            ) { files = loadFiles(context) }
        }

        // ── Download bar ──────────────────────────────────────────────────────
        AnimatedVisibility(showDownloadBar) {
            Column(modifier = Modifier.fillMaxWidth().background(BgCard).padding(12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = downloadUrl,
                        onValueChange = { downloadUrl = it },
                        modifier = Modifier.weight(1f),
                        placeholder = { Text("https://example.com/file.pdf", color = TextSecondary,
                            fontSize = 11.sp, fontFamily = FontFamily.Monospace) },
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = NeonCyan,
                            unfocusedBorderColor = NeonCyan.copy(alpha = 0.3f),
                            focusedTextColor = TextPrimary,
                            unfocusedTextColor = TextPrimary,
                            cursorColor = NeonCyan
                        ),
                        shape = RoundedCornerShape(8.dp),
                        maxLines = 1,
                        textStyle = LocalTextStyle.current.copy(fontFamily = FontFamily.Monospace, fontSize = 12.sp),
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Go),
                        keyboardActions = KeyboardActions(onGo = {
                            if (downloadUrl.isNotBlank()) scope.launch {
                                downloadFile(context, downloadUrl,
                                    onProgress = { downloadProgress = it },
                                    onStatus   = { downloadStatus = it },
                                    onDone     = { files = loadFiles(context); downloadProgress = -1f }
                                )
                            }
                        })
                    )
                    Spacer(Modifier.width(8.dp))
                    IconButton(
                        onClick = {
                            if (downloadUrl.isNotBlank()) scope.launch {
                                downloadFile(context, downloadUrl,
                                    onProgress = { downloadProgress = it },
                                    onStatus   = { downloadStatus = it },
                                    onDone     = { files = loadFiles(context); downloadProgress = -1f }
                                )
                            }
                        },
                        modifier = Modifier.background(NeonCyan, RoundedCornerShape(8.dp))
                    ) {
                        Icon(Icons.Filled.ArrowDownward, contentDescription = null, tint = BgDeep)
                    }
                }
                if (downloadProgress >= 0) {
                    Spacer(Modifier.height(6.dp))
                    LinearProgressIndicator(
                        progress = { downloadProgress },
                        modifier = Modifier.fillMaxWidth(),
                        color = NeonCyan,
                        trackColor = NeonCyan.copy(alpha = 0.2f)
                    )
                }
                if (downloadStatus.isNotBlank()) {
                    Text(downloadStatus, color = if (downloadStatus.startsWith("✅")) NeonGreen else TextSecondary,
                        fontSize = 11.sp, fontFamily = FontFamily.Monospace, modifier = Modifier.padding(top = 4.dp))
                }
            }
        }

        // ── Type filter ───────────────────────────────────────────────────────
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            TypeFilterChip("ВСЕ", null, filterType) { filterType = null }
            FileType.entries.forEach { ft ->
                TypeFilterChip(ft.name, ft, filterType) { filterType = ft }
            }
        }

        // ── File list ─────────────────────────────────────────────────────────
        if (displayed.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Filled.FolderOpen, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(48.dp))
                    Spacer(Modifier.height(12.dp))
                    Text("Нет файлов", color = TextSecondary, fontFamily = FontFamily.Monospace, fontSize = 13.sp)
                    Text("Добавьте или скачайте файлы", color = TextSecondary.copy(alpha = 0.6f),
                        fontFamily = FontFamily.Monospace, fontSize = 11.sp)
                }
            }
        } else {
            LazyColumn(
                contentPadding = PaddingValues(12.dp),
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                items(displayed, key = { it.path }) { file ->
                    FileRow(
                        file = file,
                        onOpen   = { openFile(context, file) },
                        onShare  = { shareFile(context, file) },
                        onDelete = {
                            File(file.path).delete()
                            files = loadFiles(context)
                        }
                    )
                }
                item { Spacer(Modifier.height(8.dp)) }
            }
        }
    }
}

// ── File row ──────────────────────────────────────────────────────────────────
@Composable
private fun FileRow(file: ManagedFile, onOpen: () -> Unit, onShare: () -> Unit, onDelete: () -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val color = fileColor(file.type)

    Box(
        modifier = Modifier.fillMaxWidth()
            .background(BgCard, RoundedCornerShape(10.dp))
            .border(1.dp, color.copy(alpha = 0.3f), RoundedCornerShape(10.dp))
            .clickable { expanded = !expanded }
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(fileIcon(file.type), contentDescription = null, tint = color, modifier = Modifier.size(24.dp))
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(file.name, color = TextPrimary, fontSize = 13.sp,
                        fontFamily = FontFamily.Monospace, fontWeight = FontWeight.SemiBold,
                        maxLines = 1)
                    Text("${formatSize(file.size)}  •  ${file.modified}", color = TextSecondary,
                        fontSize = 10.sp, fontFamily = FontFamily.Monospace)
                }
                Box(
                    modifier = Modifier.background(color.copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                        .padding(horizontal = 5.dp, vertical = 2.dp)
                ) {
                    Text(file.type.name, color = color, fontSize = 8.sp,
                        fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                }
            }
            if (expanded) {
                Spacer(Modifier.height(8.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FileButton("ОТКРЫТЬ", NeonCyan,   Icons.Filled.OpenInNew, onOpen)
                    FileButton("ПОДЕЛИТЬСЯ", NeonGreen, Icons.Filled.Share,  onShare)
                    FileButton("УДАЛИТЬ", NeonPink,   Icons.Filled.Delete,   onDelete)
                }
            }
        }
    }
}

@Composable
private fun FileButton(label: String, color: androidx.compose.ui.graphics.Color, icon: ImageVector, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
        modifier = Modifier.height(32.dp),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = color),
        border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.6f)),
        shape = RoundedCornerShape(6.dp)
    ) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(13.dp))
        Spacer(Modifier.width(4.dp))
        Text(label, fontSize = 9.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun ActionChip(label: String, icon: ImageVector, color: Color, onClick: () -> Unit) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(8.dp),
        color = color.copy(alpha = 0.12f),
        border = androidx.compose.foundation.BorderStroke(1.dp, color.copy(alpha = 0.5f))
    ) {
        Row(modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(4.dp))
            Text(label, color = color, fontSize = 10.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun TypeFilterChip(label: String, type: FileType?, current: FileType?, onClick: () -> Unit) {
    val selected = type == current
    FilterChip(
        selected = selected,
        onClick  = onClick,
        label    = { Text(label, fontSize = 9.sp, fontFamily = FontFamily.Monospace) },
        colors   = FilterChipDefaults.filterChipColors(
            selectedContainerColor = NeonYellow.copy(alpha = 0.2f),
            selectedLabelColor     = NeonYellow,
            labelColor             = TextSecondary
        )
    )
}

// ── File operations ───────────────────────────────────────────────────────────
private fun filesDir(context: Context): File =
    File(context.filesDir, "managed_files").also { it.mkdirs() }

private fun loadFiles(context: Context): List<ManagedFile> {
    val dir = filesDir(context)
    val sdf = SimpleDateFormat("dd.MM.yy HH:mm", Locale.getDefault())
    return dir.listFiles()?.sortedByDescending { it.lastModified() }?.map { f ->
        ManagedFile(
            name     = f.name,
            path     = f.absolutePath,
            size     = f.length(),
            type     = fileTypeFor(f.name),
            modified = sdf.format(Date(f.lastModified()))
        )
    } ?: emptyList()
}

private suspend fun downloadFile(
    context: Context,
    urlStr: String,
    onProgress: (Float) -> Unit,
    onStatus: (String) -> Unit,
    onDone: () -> Unit
) = withContext(Dispatchers.IO) {
    try {
        onStatus("Подключение...")
        val url  = URL(urlStr)
        val conn = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 15_000; readTimeout = 60_000
            connect()
        }
        val total = conn.contentLength.toLong()
        val name  = urlStr.substringAfterLast('/').ifBlank { "download_${System.currentTimeMillis()}" }
        val dest  = File(filesDir(context), name)
        var downloaded = 0L
        onStatus("Скачивание $name...")
        conn.inputStream.use { inp ->
            FileOutputStream(dest).use { out ->
                val buf = ByteArray(8192)
                var n: Int
                while (inp.read(buf).also { n = it } != -1) {
                    out.write(buf, 0, n)
                    downloaded += n
                    if (total > 0) onProgress(downloaded.toFloat() / total)
                }
            }
        }
        conn.disconnect()
        withContext(Dispatchers.Main) {
            onStatus("✅ Сохранено: $name (${formatSize(dest.length())})")
            onDone()
        }
    } catch (e: Exception) {
        withContext(Dispatchers.Main) { onStatus("❌ Ошибка: ${e.message}") }
    }
}

private fun importFileFromUri(context: Context, uri: Uri): File? = try {
    val name = uri.lastPathSegment?.substringAfterLast('/')
        ?: "file_${System.currentTimeMillis()}"
    val dest = File(filesDir(context), name)
    context.contentResolver.openInputStream(uri)?.use { inp ->
        FileOutputStream(dest).use { out -> inp.copyTo(out) }
    }
    dest
} catch (e: Exception) { null }

private fun openFile(context: Context, file: ManagedFile) {
    try {
        val uri = androidx.core.content.FileProvider.getUriForFile(
            context, "${context.packageName}.provider", File(file.path))
        val mime = MimeTypeMap.getSingleton()
            .getMimeTypeFromExtension(file.name.substringAfterLast('.')) ?: "*/*"
        context.startActivity(Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, mime)
            flags = Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK
        })
    } catch (e: Exception) { /* no app */ }
}

private fun shareFile(context: Context, file: ManagedFile) {
    try {
        val uri = androidx.core.content.FileProvider.getUriForFile(
            context, "${context.packageName}.provider", File(file.path))
        context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply {
            type = "*/*"; putExtra(Intent.EXTRA_STREAM, uri)
            flags = Intent.FLAG_GRANT_READ_URI_PERMISSION
        }, "Поделиться").apply { flags = Intent.FLAG_ACTIVITY_NEW_TASK })
    } catch (e: Exception) { /* ignore */ }
}
