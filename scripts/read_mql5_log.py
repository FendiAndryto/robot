with open('/config/.wine/drive_c/Program Files/MetaTrader 5/MQL5/logs/20261018.log', 'rb') as f:
    f.seek(0, 2)
    size = f.tell()
    f.seek(max(0, size - 4000), 0)
    raw = f.read()

lines = raw.decode('utf-16le', errors='ignore').splitlines()
for l in lines[-10:]:
    print(l)
