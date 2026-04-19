# Implementation Plan - Remote Desktop Visual AI Agent

This project implements a PyQt6-based transparent overlay agent for remote desktop automation. It features AR-enhanced interaction, multi-task management, and a hybrid local/cloud AI decision engine.

## User Review Required

> [!IMPORTANT]
> **Storage & Hardware**: This plan assumes 12G RAM and an NVIDIA GPU (4080 Laptop) for Llama 3 and YOLO. We will use `d:\Dev\autoplay\models` for storage.
> **External Dependencies**: `AutoHotkey (AHK)` must be installed on the system (normally C:\Program Files\AutoHotkey). While we keep project files in D:\, the AHK interpreter typically resides in the system path. Please confirm if you have AHK installed or if I should assume its presence.
> **Python Version**: I will use Python 3.10+ in the local `.venv`.

## Proposed Changes

### 1. Project Infrastructure
- [NEW] `requirements.txt`: Project dependencies (PyQt6, mss, pygetwindow, ultralytics, llama-cpp-python, etc.).
- [NEW] `main.py`: Main entry point initializing all modules.
- [NEW] `.env`: Configuration for API keys and paths.


## Open Questions

> [!IMPORTANT]
> 1. **AHK Location**: Are you okay with the code calling the system `AutoHotkey.exe`? Or do you need the AHK executable to be placed inside the D drive folder as well?
> 2. **Llama 3 Source**: Do you already have the Llama 3 8B GGUF file, or should I provide the code to download/initialize it in the `models/` folder?

## Verification Plan

### Automated Tests
- `pytest` for module logic (AI inference logic, state machine transitions).
- Mocking screen frames to test AR drawing speed.

### Manual Verification
- Launch the overlay and verify it stays on top of a "Sunlogin" or "Google Remote Desktop" window.
- Test "Mouse Through" functionality.
- Verify coordinate sync by moving the remote window.
