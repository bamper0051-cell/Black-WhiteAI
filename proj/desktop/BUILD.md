# BlackBugsAI - Build & Deployment Guide

## 🏗️ Building the EXE

### Prerequisites
- Windows 10/11 64-bit
- Python 3.10+
- Visual C++ Build Tools (for llama-cpp-python with GPU)

### Step 1: Setup Build Environment

```bash
# Clone repository
git clone https://github.com/yourusername/BlackBugsAI.git
cd BlackBugsAI

# Create virtual environment
python -m venv build_env
build_env\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install build dependencies
pip install -r requirements.txt
```

### Step 2: (Optional) GPU Acceleration

For NVIDIA GPU support with llama-cpp-python:

```bash
# Install with CUDA support
set CMAKE_ARGS=-DLLAMA_CUDA=on
pip install --force-reinstall llama-cpp-python
```

For AMD GPU:
```bash
set CMAKE_ARGS=-DLLAMA_HIPBLAS=on
pip install --force-reinstall llama-cpp-python
```

### Step 3: Build EXE

```bash
# Run PyInstaller
pyinstaller build.spec

# Output location: dist/BlackBugsAI/BlackBugsAI.exe
```

### Step 4: Verify Build

```bash
# Test the built executable
dist\BlackBugsAI\BlackBugsAI.exe
```

## 📦 Creating Release Package

### Create Installer

Install NSIS (Nullsoft Scriptable Install System):

```bash
# Download from https://nsis.sourceforge.io/

# Create installer script (installer.nsi)
# See template below
```

**installer.nsi template:**
```nsis
; BlackBugsAI Installer
!include "MUI2.nsh"

Name "BlackBugsAI"
OutFile "BlackBugsAI-1.0.0-installer.exe"
InstallDir "$PROGRAMFILES\BlackBugsAI"

!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\BlackBugsAI\*.*"
  
  ; Create shortcuts
  CreateDirectory "$SMPROGRAMS\BlackBugsAI"
  CreateShortcut "$SMPROGRAMS\BlackBugsAI\BlackBugsAI.lnk" "$INSTDIR\BlackBugsAI.exe"
  CreateShortcut "$DESKTOP\BlackBugsAI.lnk" "$INSTDIR\BlackBugsAI.exe"
SectionEnd

Section "Uninstall"
  Delete "$SMPROGRAMS\BlackBugsAI\BlackBugsAI.lnk"
  Delete "$DESKTOP\BlackBugsAI.lnk"
  RMDir /r "$SMPROGRAMS\BlackBugsAI"
  RMDir /r "$INSTDIR"
SectionEnd
```

Build installer:
```bash
# Install NSIS first
# Then run:
"C:\Program Files (x86)\NSIS\makensis.exe" installer.nsi
```

### Create Portable ZIP

```bash
# Create zip without installer
Compress-Archive -Path "dist\BlackBugsAI\*" -DestinationPath "BlackBugsAI-1.0.0-portable.zip"
```

## 🚀 Distribution

### Release Checklist

- [ ] Update version in `config.py`: `APP_VERSION = "1.0.0"`
- [ ] Update `SETUP_GUIDE.md` with new features
- [ ] Test all providers on clean system
- [ ] Verify all file types can be attached
- [ ] Test code execution sandbox
- [ ] Check memory usage with large files
- [ ] Run full test suite: `python test_all.py`

### GitHub Release

```bash
# Tag the release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Create release on GitHub with:
# - Release notes
# - BlackBugsAI-1.0.0-installer.exe
# - BlackBugsAI-1.0.0-portable.zip
# - SETUP_GUIDE.md
```

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow

**.github/workflows/build.yml:**
```yaml
name: Build BlackBugsAI

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Build EXE
      run: pyinstaller build.spec
    
    - name: Create ZIP
      run: powershell Compress-Archive -Path "dist\BlackBugsAI\*" -DestinationPath "BlackBugsAI-${{ github.ref_name }}-portable.zip"
    
    - name: Upload Release
      uses: softprops/action-gh-release@v1
      with:
        files: |
          dist/BlackBugsAI/**
          BlackBugsAI-${{ github.ref_name }}-portable.zip
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## 📊 System Requirements

### Minimum (CPU-only)
- Windows 10/11 64-bit
- 4GB RAM
- 500MB disk space
- Any modern CPU

### Recommended (Local LLM)
- Windows 10/11 64-bit
- 16GB+ RAM
- 20GB disk space (for models)
- NVIDIA GPU (8GB+ VRAM) or CPU

### Optimal (Cloud API)
- Windows 10/11 64-bit
- 4GB RAM
- 500MB disk space
- Internet connection

## 🔍 Troubleshooting Build Issues

### Issue: "ModuleNotFoundError" when running EXE

**Solution:** Add missing module to `hiddenimports` in `build.spec`

```python
hiddenimports=[
    # ... existing imports ...
    "missing_module",
]
```

### Issue: EXE is very large (500MB+)

**Solution:** Reduce included libraries:
```python
excludes=[
    "matplotlib", "numpy", "scipy", "PIL", "tkinter",
    "pandas", "sklearn", "torch",  # Add more as needed
]
```

### Issue: GPU acceleration not working

**Solution:** Reinstall llama-cpp-python with GPU flags:
```bash
pip uninstall llama-cpp-python
set CMAKE_ARGS=-DLLAMA_CUDA=on
pip install llama-cpp-python
```

### Issue: Code execution sandbox not working

**Solution:** Ensure Python and Node.js are available:
```bash
python --version
node --version
bash --version
```

## 📈 Performance Optimization

### EXE Size Optimization
1. Use UPX compression
2. Exclude unused modules
3. Minify assets

### Runtime Optimization
1. Lazy load providers
2. Cache model paths
3. Stream responses
4. Limit context window

### Memory Optimization
1. Batch file processing
2. Stream file reading
3. Cleanup temp files
4. Monitor with psutil

## 🔐 Security Considerations

### Code Signing
```bash
# Sign the EXE (requires code signing certificate)
signtool sign /f "cert.pfx" /p password "dist\BlackBugsAI\BlackBugsAI.exe"
```

### Antivirus False Positives
- PyInstaller-built EXEs may trigger false positives
- Request whitelisting from antivirus vendors
- Sign the executable with valid code signing certificate

### User Data Protection
- Store API keys in encrypted format
- Clear temporary files on exit
- Implement prompt sanitization
- Log security events

## 📝 Version Management

**Semantic Versioning:**
- MAJOR (1.0.0): Breaking changes
- MINOR (1.1.0): New features
- PATCH (1.1.1): Bug fixes

**Update Locations:**
1. `config.py`: `APP_VERSION`
2. `build.spec`: Comments
3. `SETUP_GUIDE.md`: Version references
4. Git tags: `v1.0.0`

## 🎯 Post-Release Checklist

- [ ] Announce on social media
- [ ] Update website/docs
- [ ] Monitor GitHub issues
- [ ] Collect user feedback
- [ ] Plan next release

## 📞 Support

For build issues:
1. Check GitHub Issues
2. Review error messages carefully
3. Try clean rebuild
4. Report with full error trace

---

**Last Updated:** 2024
