# BlackBugsAI - Android APK Build Guide

## Overview

This guide explains how to build the BlackBugsAI Android application (APK) locally or via GitHub Actions.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Build (Recommended)](#local-build-recommended)
3. [GitHub Actions Build](#github-actions-build)
4. [Build Outputs](#build-outputs)
5. [Installation](#installation)
6. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### Required Software

| Software | Version | Download |
|----------|---------|----------|
| **Flutter** | 3.24.5+ | https://flutter.dev/docs/get-started/install |
| **Java JDK** | 17 | https://adoptium.net/ |
| **Android SDK** | 21+ | Installed via Flutter or Android Studio |
| **Git** | Latest | https://git-scm.com/ |

### Verify Installation

```bash
# Check Flutter
flutter --version
# Expected: Flutter 3.24.5 • Dart 3.5.4

# Check Java
java -version
# Expected: openjdk version "17.0.x"

# Check Android SDK
flutter doctor
# All checkmarks should be green
```

---

## 2. Local Build (Recommended)

### Step 1: Clone Repository

```bash
git clone https://github.com/bamper0051-cell/Black-WhiteAI.git
cd Black-WhiteAI/android_app
```

### Step 2: Install Dependencies

```bash
flutter pub get
```

**Expected Output:**
```
Running "flutter pub get" in android_app...
Resolving dependencies...
+ http 1.1.0
+ web_socket_channel 2.4.0
+ flutter_animate 4.3.0
+ fl_chart 0.65.0
+ shared_preferences 2.2.2
+ intl 0.18.1
+ url_launcher 6.2.1
+ font_awesome_flutter 10.6.0
Changed 24 dependencies!
```

### Step 3: Analyze Code (Optional)

```bash
flutter analyze
```

**Expected Output:**
```
Analyzing android_app...
No issues found! (ran in 2.1s)
```

### Step 4: Generate local.properties

Create `android_app/android/local.properties`:

```properties
flutter.sdk=/path/to/flutter
sdk.dir=/path/to/Android/Sdk
```

**Auto-generate:**
```bash
echo "flutter.sdk=$HOME/flutter" > android/local.properties
echo "sdk.dir=$ANDROID_SDK_ROOT" >> android/local.properties
```

### Step 5: Build APK

#### Debug Build (Development)

```bash
flutter build apk --debug
```

**Output:** `build/app/outputs/flutter-apk/app-debug.apk`

**Size:** ~50 MB
**Use Case:** Testing, development

#### Release Build (Production)

```bash
flutter build apk --release
```

**Output:** `build/app/outputs/flutter-apk/app-release.apk`

**Size:** ~20 MB
**Use Case:** Production distribution

#### Split APKs (Optimized Size)

```bash
flutter build apk --release --split-per-abi
```

**Outputs:**
- `app-arm64-v8a-release.apk` (~15 MB) — **Most Android devices (2017+)**
- `app-armeabi-v7a-release.apk` (~14 MB) — Older devices (2012-2017)
- `app-x86_64-release.apk` (~16 MB) — Emulators, x86 tablets

**Recommended:** Use split APKs for distribution (smaller downloads)

---

## 3. GitHub Actions Build

### Trigger Build

**Option 1: Push to Main Branch**

```bash
git add .
git commit -m "Trigger APK build"
git push origin main
```

**Option 2: Manual Workflow Dispatch**

1. Go to: https://github.com/bamper0051-cell/Black-WhiteAI/actions
2. Select **"Build Android APK"** workflow
3. Click **"Run workflow"**
4. (Optional) Enter release tag (e.g., `v1.0.0`)
5. Click **"Run workflow"** button

### Workflow Steps

The GitHub Actions workflow (`.github/workflows/build-apk.yml`) performs:

1. **Checkout repository**
2. **Setup Java 17** (Temurin distribution)
3. **Install Flutter 3.24.5**
4. **Run `flutter pub get`**
5. **Analyze code** (`flutter analyze`)
6. **Build universal APK** (`flutter build apk --release`)
7. **Build split APKs** (`flutter build apk --split-per-abi`)
8. **Rename APKs**:
   - `BlackBugsAI-universal.apk`
   - `BlackBugsAI-arm64.apk`
   - `BlackBugsAI-arm32.apk`
   - `BlackBugsAI-x86_64.apk`
9. **Upload artifacts** (30 days retention)
10. **(Optional)** **Create GitHub Release** (if triggered manually)

### Download Built APKs

**From Workflow Run:**

1. Go to: https://github.com/bamper0051-cell/Black-WhiteAI/actions
2. Click on the latest **"Build Android APK"** run
3. Scroll to **"Artifacts"** section
4. Download **BlackBugsAI-APKs.zip**
5. Extract ZIP to get all APK files

**From GitHub Releases:**

If workflow was triggered manually with release tag:

1. Go to: https://github.com/bamper0051-cell/Black-WhiteAI/releases
2. Find the release (e.g., `v1.0.0`)
3. Download desired APK from **Assets** section

---

## 4. Build Outputs

### File Locations

**Local Build:**
```
android_app/
└── build/
    └── app/
        └── outputs/
            └── flutter-apk/
                ├── app-debug.apk              # Debug build
                ├── app-release.apk            # Universal release
                ├── app-arm64-v8a-release.apk  # ARM64 (modern)
                ├── app-armeabi-v7a-release.apk # ARM32 (old)
                └── app-x86_64-release.apk     # x86-64 (emulators)
```

**GitHub Actions:**
```
release-apks/
├── BlackBugsAI-universal.apk  # All architectures
├── BlackBugsAI-arm64.apk      # ARM64 only
├── BlackBugsAI-arm32.apk      # ARM32 only
└── BlackBugsAI-x86_64.apk     # x86-64 only
```

### APK Details

| APK | Size | Architecture | Use Case |
|-----|------|--------------|----------|
| **universal** | ~20 MB | All | Works everywhere, larger size |
| **arm64** | ~15 MB | ARM64-v8a | **Most Android devices (recommended)** |
| **arm32** | ~14 MB | armeabi-v7a | Older devices (pre-2017) |
| **x86_64** | ~16 MB | x86-64 | Emulators, rare tablets |

### Which APK to Use?

```
┌─────────────────────────────────────────────┐
│  Device Type          │  Recommended APK    │
├───────────────────────┼─────────────────────┤
│  Modern Android       │  BlackBugsAI-arm64  │
│  (2017+, 64-bit)      │                     │
├───────────────────────┼─────────────────────┤
│  Older Android        │  BlackBugsAI-arm32  │
│  (2012-2017, 32-bit)  │                     │
├───────────────────────┼─────────────────────┤
│  Android Emulator     │  BlackBugsAI-x86_64 │
│  (AVD, Genymotion)    │                     │
├───────────────────────┼─────────────────────┤
│  Unknown / Universal  │  BlackBugsAI-       │
│  (works on all)       │  universal          │
└───────────────────────┴─────────────────────┘
```

**To check device architecture:**
```bash
adb shell getprop ro.product.cpu.abi
# Output examples:
# arm64-v8a    → Use arm64 APK
# armeabi-v7a  → Use arm32 APK
# x86_64       → Use x86_64 APK
```

---

## 5. Installation

### On Physical Device

**Prerequisites:**
- Android 5.0+ (API 21)
- 100 MB free storage
- **Unknown Sources** enabled

**Steps:**

1. **Transfer APK to device:**
   ```bash
   # Via ADB
   adb install build/app/outputs/flutter-apk/app-release.apk

   # Or upload to device (Telegram, Drive, etc.)
   ```

2. **Enable Unknown Sources:**
   - Android 8+: Settings → Apps → Special Access → Install Unknown Apps → Select browser/file manager → Allow
   - Android 7 or lower: Settings → Security → Unknown Sources → Enable

3. **Install APK:**
   - Tap APK file in file manager
   - Tap **"Install"**
   - Tap **"Open"** when complete

4. **First Launch Setup:**
   - Enter **Server IP** (e.g., `34.XX.XX.XX`)
   - Enter **Port** (default: `8080`)
   - Enter **Admin Token** (from `.env` → `ADMIN_WEB_TOKEN`)
   - Toggle **Use HTTPS** (OFF for development)
   - Tap **"TEST"** to verify connection
   - Tap **"SAVE"** if test succeeds

### On Emulator

**Prerequisites:**
- Android Studio with AVD
- Or Genymotion

**Steps:**

1. **Start emulator:**
   ```bash
   emulator -avd Pixel_5_API_30 &
   ```

2. **Install APK:**
   ```bash
   adb install build/app/outputs/flutter-apk/app-release.apk
   ```

3. **Launch app:**
   - Find "BlackBugsAI" in app drawer
   - Or: `adb shell am start -n com.blackbugsai.app/.MainActivity`

4. **Connect to local server:**
   - Server IP: `10.0.2.2` (Android emulator host)
   - Port: `8080`
   - Admin Token: Your `ADMIN_WEB_TOKEN`

---

## 6. Troubleshooting

### Build Errors

#### Error: "Flutter not found"

**Cause:** Flutter not in PATH

**Fix:**
```bash
export PATH="$HOME/flutter/bin:$PATH"
# Add to ~/.bashrc or ~/.zshrc for persistence
```

#### Error: "Java version mismatch"

**Cause:** Wrong Java version (need JDK 17)

**Fix:**
```bash
# Ubuntu/Debian
sudo apt install openjdk-17-jdk
sudo update-alternatives --config java

# macOS
brew install openjdk@17
```

#### Error: "Android SDK not found"

**Cause:** `ANDROID_SDK_ROOT` not set

**Fix:**
```bash
# Find SDK location
flutter doctor -v | grep "Android SDK"

# Set environment variable
export ANDROID_SDK_ROOT=/path/to/Android/Sdk

# Generate local.properties
echo "sdk.dir=$ANDROID_SDK_ROOT" > android/local.properties
```

#### Error: "Execution failed for task ':app:lintVitalRelease'"

**Cause:** Lint warnings blocking build

**Fix:**
```bash
# Disable lint checks (add to android/app/build.gradle)
android {
    lintOptions {
        checkReleaseBuilds false
        abortOnError false
    }
}
```

#### Error: "Gradle daemon disappeared unexpectedly"

**Cause:** Out of memory

**Fix:**
```bash
# Increase Gradle memory (android/gradle.properties)
org.gradle.jvmargs=-Xmx4096m -XX:MaxPermSize=512m
```

### Installation Errors

#### Error: "App not installed"

**Possible Causes & Fixes:**

1. **Insufficient storage:**
   - Free up 100+ MB space

2. **Wrong architecture:**
   - Check: `adb shell getprop ro.product.cpu.abi`
   - Install matching APK (arm64/arm32/x86_64)

3. **Signature conflict:**
   - Old version installed with different signature
   - Fix: Uninstall old app first
   ```bash
   adb uninstall com.blackbugsai.app
   ```

4. **Corrupt APK:**
   - Re-download or rebuild
   - Verify file size: `ls -lh app-release.apk`

#### Error: "Parse error: There is a problem parsing the package"

**Cause:** Corrupt download or wrong Android version

**Fix:**
- Re-download APK
- Verify device is Android 5.0+ (API 21+)

### Connection Errors

#### Error: "Connection refused"

**Possible Causes & Fixes:**

1. **Server not running:**
   ```bash
   # On server
   docker-compose up -d
   docker-compose logs -f
   ```

2. **Wrong IP:**
   ```bash
   # Check server IP
   curl ifconfig.me
   # Or on GCP
   gcloud compute instances list
   ```

3. **Firewall blocking:**
   ```bash
   # On GCP, allow port 8080
   gcloud compute firewall-rules create allow-admin \
     --allow tcp:8080 \
     --source-ranges 0.0.0.0/0
   ```

4. **Admin web not started:**
   ```bash
   # Check logs
   docker exec -it automuvie bash
   ps aux | grep admin_web
   ```

#### Error: "401 Unauthorized"

**Cause:** Wrong admin token

**Fix:**
```bash
# On server, check token
cat .env | grep ADMIN_WEB_TOKEN
# Update token in Android app settings
```

#### Error: "Network error"

**Cause:** Device not on internet or firewall

**Fix:**
- Check WiFi/mobile data
- Try different network
- Use VPN if blocked
- Check server firewall rules

---

## 7. Advanced Build Options

### Signed Release Build

For Google Play Store or official releases, you need a **signing key**.

**Create Keystore:**
```bash
keytool -genkey -v -keystore ~/blackbugsai.jks \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -alias blackbugsai
```

**Create key.properties:**
```properties
# android_app/android/key.properties
storePassword=YOUR_STORE_PASSWORD
keyPassword=YOUR_KEY_PASSWORD
keyAlias=blackbugsai
storeFile=/path/to/blackbugsai.jks
```

**Update build.gradle:**
```gradle
// android_app/android/app/build.gradle

// Load key properties
def keystoreProperties = new Properties()
def keystorePropertiesFile = rootProject.file('key.properties')
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {
    // ...

    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile file(keystoreProperties['storeFile'])
            storePassword keystoreProperties['storePassword']
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            shrinkResources true
        }
    }
}
```

**Build Signed APK:**
```bash
flutter build apk --release
# Output: app-release.apk (signed)
```

### App Bundle (Google Play)

```bash
flutter build appbundle --release
# Output: build/app/outputs/bundle/release/app-release.aab
```

**Upload to Play Store:**
1. Go to: https://play.google.com/console
2. Create app → Upload AAB
3. Complete store listing
4. Submit for review

### Obfuscation

Enable code obfuscation for security:

```bash
flutter build apk --release --obfuscate --split-debug-info=build/debug-info
```

**Benefits:**
- Harder to reverse-engineer
- Smaller APK size
- Better performance

**Debug crashes:**
```bash
flutter symbolize --input=crash.txt --debug-info=build/debug-info
```

---

## 8. CI/CD Integration

### GitHub Actions (Already Configured)

Workflow file: `.github/workflows/build-apk.yml`

**Triggers:**
- Push to `main` branch
- Manual workflow dispatch

**Outputs:**
- Universal APK
- Split APKs (arm64, arm32, x86_64)
- GitHub Release (if manual trigger)

**Customize:**
```yaml
# Change Flutter version
- name: Install Flutter 3.24.5
  run: |
    git clone --depth 1 --branch 3.24.5 https://github.com/flutter/flutter.git
    # Change to: --branch 3.27.0 (or latest stable)

# Change build number
--build-number=${{ github.run_number }}
# Change to: --build-number=$(date +%Y%m%d%H%M)
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
stages:
  - build

build-apk:
  stage: build
  image: cirrusci/flutter:3.24.5
  script:
    - flutter pub get
    - flutter build apk --release --split-per-abi
  artifacts:
    paths:
      - android_app/build/app/outputs/flutter-apk/*.apk
    expire_in: 30 days
```

### Jenkins

Create `Jenkinsfile`:

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'flutter pub get'
                sh 'flutter build apk --release'
            }
        }
        stage('Archive') {
            steps {
                archiveArtifacts artifacts: '**/outputs/flutter-apk/*.apk'
            }
        }
    }
}
```

---

## 9. APK Size Optimization

### Current Sizes

- Universal APK: ~20 MB
- Split APKs: ~14-16 MB each

### Optimization Techniques

**1. Enable R8 Shrinking:**
```gradle
// android/app/build.gradle
android {
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
        }
    }
}
```
**Savings: -30%**

**2. Remove Unused Resources:**
```gradle
android {
    defaultConfig {
        resConfigs "en", "ru"  // Only English and Russian
    }
}
```
**Savings: -10%**

**3. Compress Images:**
```bash
# Install pngquant
brew install pngquant  # macOS
apt install pngquant   # Ubuntu

# Compress all PNGs
find assets/images -name "*.png" -exec pngquant --ext .png --force {} \;
```
**Savings: -20% (image files)**

**4. Use WebP:**
```bash
# Convert PNG to WebP
cwebp assets/images/logo.png -o assets/images/logo.webp
```
**Savings: -40% (image files)**

**5. Split APKs (Already Implemented):**
```bash
flutter build apk --split-per-abi
```
**Savings: -25% (per architecture)**

---

## 10. Summary

### Quick Start

```bash
# 1. Clone repo
git clone https://github.com/bamper0051-cell/Black-WhiteAI.git
cd Black-WhiteAI/android_app

# 2. Install deps
flutter pub get

# 3. Build APK
flutter build apk --release --split-per-abi

# 4. Install on device
adb install build/app/outputs/flutter-apk/app-arm64-v8a-release.apk

# 5. Connect to server
# Enter server IP:port and admin token in app
```

### Best Practices

✅ **DO:**
- Use split APKs for distribution (smaller downloads)
- Test on real device before release
- Enable ProGuard/R8 for production
- Use signed release builds for Play Store
- Version APKs with git tags

❌ **DON'T:**
- Commit signing keys to git (add to `.gitignore`)
- Distribute debug APKs in production
- Use hardcoded server URLs (make configurable)
- Skip `flutter analyze` (catches issues early)
- Forget to update version in `pubspec.yaml`

---

**Last Updated:** 2026-04-11
**Flutter Version:** 3.24.5
**Min Android:** 5.0 (API 21)
**Target Android:** 14 (API 34)
