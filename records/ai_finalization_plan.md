# Implementation Plan - Bringing AI Models Online

This plan focuses on getting YOLOv8n and Llama 3 operational in the local environment (`d:\Dev\autoplay`).

## User Review Required

> [!CAUTION]
> **Llama 3 Library**: `llama-cpp-python` failed to install because your system likely lacks the Visual Studio C++ Redistributable/Build Tools. 
> 1. I will attempt to install a **pre-compiled CPU-only version** first.
> 2. If you want **GPU acceleration (NVIDIA 4080)**, you MUST install "Build Tools for Visual Studio" with the "C++ Desktop Development" workload. Should I proceed with the CPU-version attempt first?
> 3. You need to download the **Llama-3-8B-Instruct-GGUF** file (~5GB). Do you want me to provide the download link/script, or do you have it?

## Proposed Changes

### 1. Environment Verification
- [NEW] `check_ai_env.py`: A script to test `ultralytics`, `PyQt6`, and `llama-cpp` functionality.

---

### 2. YOLO Completion
- **Download**: Run a small script to fetch `yolov8n.pt` from Ultralytics into the `models/` folder.
- **Update**: `src/ai/local_engine.py` to load this file.

---

### 3. Llama 3 Resolve
- **Library**: `pip install llama-cpp-python --prefer-binary --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu` (Try pre-built binaries).
- **Stub/Fallback**: If it fails, keep the current "Cloud/Mock" fallback active but warn the user.

---

## Open Questions

> [!IMPORTANT]
> 1. **GPU Driver**: Do you have CUDA installed? (Needed for 4080 acceleration).
> 2. **Model Download**: Do you permit me to use `requests` or `wget` to download the YOLO model file (~6MB)?

## Verification Plan

### Automated Tests
- Run `check_ai_env.py` and report status.

### Manual Verification
- Attempt to load YOLO in a small script and print "Model Loaded".
