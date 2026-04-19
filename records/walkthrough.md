# Walkthrough - Remote Desktop Visual AI Agent Built

The project has been successfully architected and built within `d:\Dev\autoplay`. It strictly adheres to the PyQt6 transparent overlay design and hybrid AI strategy.

## Key Accomplishments

### 1. Transparent Overlay UI
The system uses `PyQt6` to create a click-through, always-on-top window that aligns perfectly with remote desktop clients like Sunlogin.
- **Left Panel**: Task queue and creation.
- **Right Panel**: Real-time CPU/GPU/MEM monitoring and execution logs.
- **Center Dialog**: Workflow approval interface for AI-generated steps.

### 2. Hybrid AI Engine
The `ModelManager` handles the intelligence. It is designed to prioritize local models (YOLO/Llama 3) but seamlessly falls back to cloud models (Doubao) if local resources are insufficient or inference fails.

### 3. Physical Interaction (AHK)
Interactions (clicks, typing, and the critical **Page Clearing**) are handled by `AutoHotkey`. This moves the actual interaction layer to the OS level, ensuring high reliability for remote desktop environments.

## Directory Structure
- `src/overlay/`: UI and AR rendering logic.
- `src/ai/`: Decision engine and model switching.
- `src/execution/`: AHK integration and task state machine.
- `src/utils/`: High-speed vision capture (mss) and window tracking.
- `records/`: Project execution history per version.

## How to Run

1. **Configure AHK**: Ensure `config/default_config.json` points to your `AutoHotkey.exe` path.
2. **Open Remote Window**: Launch Sunlogin or Google Remote Desktop.
3. **Launch the Agent**:
   ```bash
   .venv\Scripts\python main.py
   ```
4. **Interact**: The overlay will automatically attach to the remote window. You can manage tasks on the left and see AI drawing boxes on the remote interface.

## Critical Notes
> [!WARNING]
> **llama-cpp-python**: The automatic installation of the local llama-cpp runner requires a C++ compiler. If missing, the system will use Mock/Cloud modes for testing. Please install "Build Tools for Visual Studio" if you wish to use local GGUF acceleration.

> [!TIP]
> **Page Clearing**: You can customize the `clear_page()` logic in `src/execution/ahk_executor.py` to match your specific application's refresh hotkeys.
