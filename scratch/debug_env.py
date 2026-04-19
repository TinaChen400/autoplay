import sys
print("Python Version:", sys.version)

try:
    import PyQt6
    from PyQt6.QtWidgets import QApplication
    print("[OK] PyQt6")
except Exception as e: print("[FAIL] PyQt6:", e)

try:
    import mss
    print("[OK] mss")
except Exception as e: print("[FAIL] mss:", e)

try:
    import cv2
    print("[OK] cv2")
except Exception as e: print("[FAIL] cv2:", e)

try:
    import pyautogui
    print("[OK] pyautogui")
except Exception as e: print("[FAIL] pyautogui:", e)

try:
    import pyperclip
    print("[OK] pyperclip")
except Exception as e: print("[FAIL] pyperclip:", e)

print("Environment Test End.")
