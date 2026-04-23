import json
import re
import os

path = r'd:\Dev\autoplay\config\missions.json'
if not os.path.exists(path):
    print("File not found")
    exit(1)

with open(path, 'rb') as f:
    raw = f.read()

# Try to decode, ignoring errors for now to get a string
content = raw.decode('utf-8', errors='ignore')

# Fix raw newlines inside JSON strings
def fix_newlines(match):
    s = match.group(0)
    # Only replace newlines that are NOT escaped
    return s.replace('\n', '\\n').replace('\r', '')

# Simple regex for JSON strings (doesn't handle escaped quotes perfectly but should work here)
content = re.sub(r'\"(?:\\\"|[^\"])*\"', fix_newlines, content, flags=re.DOTALL)

try:
    data = json.loads(content)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("SUCCESS: JSON fixed and saved as UTF-8")
except Exception as e:
    print(f"FAILED: {e}")
    # Print context around error if possible
    m = re.search(r'\(char (\d+)\)', str(e))
    if m:
        pos = int(m.group(1))
        print("Error context:", repr(content[max(0, pos-40):min(len(content), pos+40)]))
