import sys

path = "/config/.wine/drive_c/Program Files/MetaTrader 5/Config/common.ini"
try:
    content = open(path, "rb").read().decode("utf-16", errors="ignore")
except Exception as e:
    print(f"Error reading {path}: {e}")
    sys.exit(1)

experts_section = (
    "\r\n[Experts]\r\n"
    "AllowLiveTrading=1\r\n"
    "AllowDllImport=1\r\n"
    "Enabled=1\r\n"
    "WebRequest=1\r\n"
    "WebRequestUrl=http://backend:8000;http://robot_backend:8000;http://localhost:8089;http://127.0.0.1:8089\r\n"
)

if "[Experts]" not in content:
    content += experts_section
    open(path, "wb").write(content.encode("utf-16"))
    print("Successfully added [Experts] section to common.ini")
else:
    print("[Experts] section already present in common.ini")
