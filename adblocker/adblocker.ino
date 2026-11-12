#include <WiFi.h>
#include <WiFiUdp.h>
#include <LittleFS.h>

#include "wifi_config.h"   // local, gitignored (copy wifi_config.h.example)
IPAddress upstream(1, 1, 1, 1);          // real DNS for non-blocked names

WiFiUDP server, fwd;
uint8_t buf[512];
uint8_t rbuf[1232];
File blf;
uint32_t blCount = 0, statTotal = 0, statBlocked = 0;

uint32_t fnv(const String& s) {
  uint32_t h = 2166136261u;
  for (size_t i = 0; i < s.length(); i++) { h ^= (uint8_t)s[i]; h *= 16777619u; }
  return h;
}

// binary search directly in the flash file (4 bytes per entry)
bool inList(uint32_t h) {
  int32_t lo = 0, hi = (int32_t)blCount - 1;
  while (lo <= hi) {
    int32_t mid = (lo + hi) / 2;
    uint32_t v = 0;
    blf.seek((uint32_t)mid * 4);
    blf.read((uint8_t*)&v, 4);
    if (v == h) return true;
    if (v < h) lo = mid + 1; else hi = mid - 1;
  }
  return false;
}

// checks ads.example.com, then example.com
bool isBlocked(String name) {
  while (name.indexOf('.') >= 0) {
    if (inList(fnv(name))) return true;
    name = name.substring(name.indexOf('.') + 1);
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(1500);
  if (!LittleFS.begin(false)) { Serial.println("LittleFS mount failed"); while (1) delay(1000); }
  blf = LittleFS.open("/blocklist.bin", "r");
  if (!blf) { Serial.println("blocklist.bin missing"); while (1) delay(1000); }
  blCount = blf.size() / 4;
  Serial.printf("Blocklist: %u domains\n", blCount);

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(SSID, PASS);
  WiFi.setTxPower(WIFI_POWER_8_5dBm);
  Serial.print("Connecting to "); Serial.println(SSID);
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.printf("status=%d\n", WiFi.status());
    if (millis() - t0 > 20000) {
      Serial.println("Retrying...");
      WiFi.disconnect();
      WiFi.begin(SSID, PASS);
      t0 = millis();
    }
  }
  Serial.print("DNS server IP: "); Serial.println(WiFi.localIP());

  server.begin(53);
  fwd.begin(5300);
}

void loop() {
  int n = server.parsePacket();
  if (n <= 12 || n > 512) return;
  IPAddress cip = server.remoteIP();
  uint16_t cport = server.remotePort();
  server.read(buf, n);

  // read the question name
  int i = 12; String name = "";
  while (i < n && buf[i]) {
    int l = buf[i++];
    if (i + l > n) return;
    if (name.length()) name += '.';
    for (int k = 0; k < l; k++) name += (char)tolower(buf[i++]);
  }
  if (i + 5 > n) return;
  i++;                                   // skip the zero byte
  uint16_t qtype = (buf[i] << 8) | buf[i + 1];
  int qend = i + 4;
  statTotal++;

  if (isBlocked(name)) {
    statBlocked++;
    buf[2] = 0x81; buf[3] = 0x80;                 // response, no error
    buf[6] = 0; buf[7] = (qtype == 1) ? 1 : 0;    // 1 answer for A records only
    buf[8] = buf[9] = buf[10] = buf[11] = 0;
    int len = qend;
    if (qtype == 1) {
      const uint8_t ans[] = {0xC0,0x0C, 0,1, 0,1, 0,0,0,60, 0,4, 0,0,0,0};
      memcpy(buf + len, ans, sizeof(ans)); len += sizeof(ans);
    }
    server.beginPacket(cip, cport); server.write(buf, len); server.endPacket();
    Serial.printf("BLOCK %s  (%u/%u)\n", name.c_str(), statBlocked, statTotal);
  } else {
    fwd.beginPacket(upstream, 53); fwd.write(buf, n); fwd.endPacket();
    uint32_t t = millis();
    while (millis() - t < 1500) {
      int m = fwd.parsePacket();
      if (m > 0) {
        int r = fwd.read(rbuf, min(m, (int)sizeof(rbuf)));
        if (r > 2 && rbuf[0] == buf[0] && rbuf[1] == buf[1]) {   // match transaction ID
          server.beginPacket(cip, cport); server.write(rbuf, r); server.endPacket();
          break;
        }
      }
      delay(1);
    }
  }
}