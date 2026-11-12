import serial, time, re, sys

PORT = "COM14"
BAUD = 115200
CAPTURE_SECONDS = 45

s = serial.Serial()
s.port = PORT
s.baudrate = BAUD
s.timeout = 0.25
try:
    s.dtr = False   # IO0 high -> normal boot
    s.rts = True    # EN low -> hold in reset
    s.open()
except serial.SerialException as e:
    print("OPEN_FAILED:", e)
    sys.exit(1)

time.sleep(0.15)
s.rts = False       # release reset -> board boots
print(f"opened {PORT} @{BAUD}, reset pulse sent", flush=True)

end = time.time() + CAPTURE_SECONDS
ip = None
lines = 0
while time.time() < end:
    try:
        raw = s.readline()
    except serial.SerialException as e:
        print("SERIAL_ERROR:", e)
        break
    if raw:
        text = raw.decode("utf-8", "replace").rstrip()
        lines += 1
        print(text, flush=True)
        m = re.search(r"DNS server IP:\s*(\d+\.\d+\.\d+\.\d+)", text)
        if m:
            ip = m.group(1)
            # keep reading 5 more seconds for extra lines
            end = min(end, time.time() + 5)

print(f"---- captured {lines} lines ----", flush=True)
print("RESULT_IP=" + (ip or "NONE"), flush=True)
s.close()
