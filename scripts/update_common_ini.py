import re
import os

ini_path = '/config/.wine/drive_c/Program Files/MetaTrader 5/Config/common.ini'
if not os.path.exists(ini_path):
    print(f"Error: {ini_path} not found")
    exit(1)

with open(ini_path, 'rb') as f:
    raw = f.read()

content = raw.decode('utf-16le')
lines = content.splitlines()
new_lines = []
in_experts = False
webrequest_found = False
url_found = False

for line in lines:
    stripped = line.strip()
    if stripped.startswith('[') and stripped.endswith(']'):
        if in_experts:
            if not webrequest_found:
                new_lines.append('WebRequest=1')
            if not url_found:
                new_lines.append('WebRequestUrl=http://backend:8000')
        in_experts = (stripped.lower() == '[experts]')
    
    if in_experts:
        if stripped.lower().startswith('webrequest='):
            new_lines.append('WebRequest=1')
            webrequest_found = True
            continue
        elif stripped.lower().startswith('webrequesturl='):
            new_lines.append('WebRequestUrl=http://backend:8000')
            url_found = True
            continue
        elif stripped.lower().startswith('allowdllimport='):
            new_lines.append('AllowDllImport=1')
            continue
        elif stripped.lower().startswith('allowlivetrading='):
            new_lines.append('AllowLiveTrading=1')
            continue
        elif stripped.lower().startswith('enabled='):
            new_lines.append('Enabled=1')
            continue
            
    new_lines.append(line)

if in_experts:
    if not webrequest_found:
        new_lines.append('WebRequest=1')
    if not url_found:
        new_lines.append('WebRequestUrl=http://backend:8000')

new_content = '\ufeff' + '\r\n'.join(new_lines) + '\r\n'
new_raw = new_content.encode('utf-16le')

with open(ini_path, 'wb') as f:
    f.write(new_raw)

print("SUCCESS: Updated common.ini!")
