import re

filepath = r"C:\Users\infomax\.gemini\antigravity\brain\6531c14d-086c-46bb-88d5-04b1428d67ce\.system_generated\steps\244\content.md"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Look for anything resembling JSON arrays of data
matches = re.findall(r'var\s+\w+\s*=\s*(\[.*?\]);', content, re.DOTALL)
for i, match in enumerate(matches):
    if len(match) > 100:  # likely data
        print(f"Match {i} length: {len(match)}")
        print(match[:200])

if not matches:
    print("No js array vars found.")
