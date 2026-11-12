# ESP32 DNS Ad-Blocker

A self-hosted DNS ad-blocker for the ESP32-S3. It answers ad domains with
`0.0.0.0` and forwards everything else to Cloudflare (`1.1.1.1`), so any
device pointed at it — phone, laptop, TV — gets ads blocked at the DNS level.
No root, no browser extension, no subscription.

Tested on a real network (Android hotspot): `doubleclick.net`,
`pagead2.googlesyndication.com` and `adnxs.com` resolve to `0.0.0.0`, while
`google.com` / `github.com` resolve normally through the upstream resolver.

## How it works

- `tools/make_blocklist.py` downloads the [StevenBlack/hosts](https://github.com/StevenBlack/hosts)
  blocklist (~78k ad/tracking domains), hashes every domain with **FNV-1a 32-bit**,
  sorts the hashes and writes them to `adblocker/data/blocklist.bin`.
- The binary blocklist lives in the **LittleFS** data partition on the flash.
- On every DNS query the sketch parses the question name, strips subdomains
  left-to-right (`ads.example.com` → `example.com`) and binary-searches the
  hash file directly in flash (4 bytes per entry) — no RAM-hungry lookup table.
- Blocked → replies with an A record of `0.0.0.0`. Everything else → forwarded
  to `1.1.1.1` and relayed back, matching the transaction ID.

## Hardware

- ESP32-S3 dev board (4 MB flash, default partition scheme)
- FTDI/USB-serial on UART0 for flashing and logs (DTR/RTS wired to EN/IO0 —
  merely opening the serial port resets the board)

## Setup

Prerequisites (once):

- An ESP32-S3 dev board + USB-serial (FTDI) adapter
- [arduino-cli](https://arduino.github.io/arduino-cli/) or the Arduino IDE,
  plus the ESP32 core:

  ```
  arduino-cli config add board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json
  arduino-cli core install esp32:esp32
  ```

Then:

1. Copy `adblocker/wifi_config.h.example` to `adblocker/wifi_config.h` and fill
   in your Wi-Fi credentials (the file is gitignored — never commit it).
2. Build the blocklist (writes `adblocker/data/blocklist.bin`):

   ```
   python tools/make_blocklist.py
   ```

   (The repo already ships a prebuilt `blocklist.bin`, so this step is optional
   unless you want a fresher list.)
3. Upload the `adblocker/data/` folder to the LittleFS partition **once**
   (it survives later sketch flashes). Two ways:
   - Arduino IDE: "ESP32 Sketch Data Upload" (via the ESP32FS / UploadFS tool)
   - CLI equivalent — build a LittleFS image and flash it at the partition
     offset `0x290000` (the default 4 MB scheme's spiffs slot):

     ```
     mklittlefs -c adblocker/data -b 4096 -s 1441792 littlefs.bin
     esptool.py --chip esp32s3 --port COMxx write_flash 0x290000 littlefs.bin
     ```
4. Flash the sketch (next section).

## Build + flash (arduino-cli, no IDE needed)

```
CLI='path/to/arduino-cli.exe'
FQBN='esp32:esp32:esp32s3:UploadSpeed=921600,USBMode=hwcdc,CDCOnBoot=default,MSCOnBoot=default,DFUOnBoot=default,UploadMode=default,CPUFreq=240,FlashMode=qio,FlashSize=4M,PartitionScheme=default,DebugLevel=info,PSRAM=disabled,LoopCore=1,EventsCore=1,EraseFlash=none,JTAGAdapter=default,ZigbeeMode=default'
"$CLI" compile --fqbn "$FQBN" ./adblocker
"$CLI" upload --port COM14 --fqbn "$FQBN" ./adblocker
```

Notes learned the hard way:

- `CDCOnBoot=default` keeps `Serial` on UART0 (the FTDI port). `cdc` routes it
  to native USB instead and the serial monitor goes blank.
- `PartitionScheme=default,FlashSize=4M` must match what the filesystem was
  uploaded with, or the LittleFS blocklist partition gets orphaned.
- Opening the serial monitor resets the board (DTR/RTS → EN/IO0). Don't open
  it while the board should stay online.

## Usage

Watch the serial monitor for `DNS server IP: x.x.x.x`, then point your
device's DNS at that IP. Verify:

```
nslookup doubleclick.net <board-ip>   -> 0.0.0.0
nslookup google.com <board-ip>        -> real address
```

The board's IP comes from DHCP and changes between networks — find it with a
ping sweep + `arp -a` (MAC starts `14:c1:9f`) or check your router/hotspot's
client list.

## Tools

| script | what it does |
|---|---|
| `tools/make_blocklist.py` | regenerate `blocklist.bin` from StevenBlack/hosts |
| `tools/serial_capture.py` | open the serial port, reset the board, capture boot log + DNS IP |
| `tools/serial_listen.py` | listen on serial without the capture logic |
| `tools/hotspot_on.py` / `tools/hotspot_reconfig.py` | manage a Windows Mobile Hotspot test bed (WinRT, no admin needed) |

## Limitations

- DNS-level blocking only — ads served from the same domain as the content
  (e.g. some YouTube/first-party ads) are not blocked.
- Plain DNS (UDP/53). Devices using encrypted DNS (DoH/DoT) bypass it — turn
  off "Secure DNS" in browsers that are pointed at the board.
- Single-threaded query handling with a 1.5 s upstream timeout — fine for a
  home/hotspot network, not for heavy traffic.
- FNV-1a 32-bit hashes have a tiny theoretical collision chance; in practice
  with ~78k domains this has not been an issue.
