import pyautogui
import time
import sys

def interactive_log(text):
    print(f"\n>>>> [AGENT] {text}")
    sys.stdout.flush()

def heavy_type(text):
    for char in text:
        pyautogui.write(char)
        time.sleep(0.5)

interactive_log("STEP 1: [READY CALIBRATION]")
print("Please switch to the MSI remote desktop window.")
print("Wait for the prompt to click the search bar.")

time.sleep(1)
interactive_log("STEP 2: [START CAPTURING]")
print("--- NOW! Please CLICK the Google Search Bar! ---")

# Countdown for clicking
for i in range(5, 0, -1):
    print(f"Waiting for click... {i}s")
    time.sleep(1)

abs_x, abs_y = pyautogui.position()
interactive_log("STEP 3: [LOCATION LOCKED]")
print(f"Captured: ({abs_x}, {abs_y})")
print("--- RECEIVED! Location stored. Please RELEASE MOUSE and WAIT ---")

# Withdrawal countdown
for i in range(3, 0, -1):
    print(f"Typing in... {i}s")
    time.sleep(1)

interactive_log("STEP 4: [TYPING NOW]")
# Double-click focus
pyautogui.click(abs_x, abs_y)
time.sleep(1.0)
pyautogui.click(abs_x, abs_y)
time.sleep(2.0)

# Heavy typing (Slow & Steady)
heavy_type("123456")

interactive_log("STEP 5: [MISSION COMPLETED]")
print("Please check the search box for '123456'.")
