import os
import codecs

css_path = r'D:\Industry\InvestmentPortal\frontend\src\index.css'

# Read as raw bytes and decode
with open(css_path, 'rb') as f:
    raw_bytes = f.read()

# PowerShell Add-Content might have appended UTF-16LE with BOM or just raw bytes
# Let's clean it by reading it with 'utf-8' ignoring errors, or finding the split point.
# It's easier to just read the whole file, strip bad characters, and write back.
try:
    content = raw_bytes.decode('utf-8')
except UnicodeDecodeError:
    # Try decoding the first part as utf-8 and the second part as utf-16
    content = raw_bytes.decode('utf-8', errors='ignore')

# To be perfectly safe, let's just strip null bytes which come from UTF-16
content = content.replace('\x00', '')

# Remove any weird BOMs
content = content.replace('\ufeff', '')
content = content.replace('\ufffe', '')

with open(css_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed index.css encoding.")

# Also fix useRef in App.jsx
app_path = r'D:\Industry\InvestmentPortal\frontend\src\App.jsx'
with open(app_path, 'r', encoding='utf-8') as f:
    app_text = f.read()

app_text = app_text.replace('const isHomeRef = useRef(isHome);', 'const isHomeRef = React.useRef(isHome);')

with open(app_path, 'w', encoding='utf-8') as f:
    f.write(app_text)
print("Fixed App.jsx useRef.")
