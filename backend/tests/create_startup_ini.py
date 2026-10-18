content = """[Common]
Login=
Password=
Server=

[Experts]
AllowLiveTrading=1
AllowDllImport=1
Enabled=1
WebRequest=1
WebRequestUrl=http://backend:8000;http://robot_backend:8000;http://localhost:8089;http://127.0.0.1:8089
Expert=BridgeEA
Symbol=EURUSD
Period=H1
"""

path = "/config/.wine/drive_c/Program Files/MetaTrader 5/startup.ini"
open(path, "wb").write(content.encode("utf-16"))
print("Saved startup.ini")
