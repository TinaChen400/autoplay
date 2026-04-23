import subprocess, sys

# Step 1: Get the raw bytes from git
result = subprocess.run(
    ["git", "show", "HEAD:src/tasks/msi_skills.py"],
    capture_output=True,
    cwd=r"D:\Dev\autoplay"
)
raw = result.stdout

# Step 2: Try GBK decode (the file was likely created on Windows with GBK)
try:
    text = raw.decode("gbk")
    print("Decoded as GBK successfully")
except Exception as e:
    print(f"GBK failed: {e}, trying utf-8-sig")
    text = raw.decode("utf-8-sig", errors="replace")

# Step 3: Check syntax
import ast
try:
    ast.parse(text)
    print("Syntax OK from git version!")
    # Write back as UTF-8 without BOM
    with open(r"D:\Dev\autoplay\src\tasks\msi_skills.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("Written to disk as UTF-8")
except SyntaxError as e:
    print(f"Git version also has syntax error at line {e.lineno}: {e.msg}")
    lines = text.splitlines()
    if e.lineno:
        print(f"Line content: {repr(lines[e.lineno-1])}")
