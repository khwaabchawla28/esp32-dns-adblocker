import serial, time, sys

PORT = "COM14"
BAUD = 115200
SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 60

s = serial.Serial()
s.port = PORT
s.baudrate = BAUD
s.timeout = 0.25
s.dtr = False
s.rts = False   # no reset pulse — just listen
s.open()
print(f"listening on {PORT} for {SECONDS}s", flush=True)
end = time.time() + SECONDS
while time.time() < end:
    try:
        raw = s.readline()
    except serial.SerialException as e:
        print("SERIAL_ERROR:", e)
        break
    if raw:
        print(raw.decode("utf-8", "replace").rstrip(), flush=True)
s.close()
print("---- listen done ----", flush=True)
