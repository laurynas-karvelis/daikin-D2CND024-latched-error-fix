#include <Wire.h>

#define EEPROM_ADDR 0x57
#define PAGE_SIZE 32
#define EEPROM_SIZE 8192

void setup() {
  Serial.begin(115200);
  Wire.begin(D2, D1);
  Wire.setClock(100000);
  
  while (!Serial) {
    delay(10);
  }
  
  delay(100);
  Serial.println("READY");
}

void loop() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd == "PING") {
      Serial.println("PONG");
    }
    else if (cmd.startsWith("WRITE ")) {
      handle_write(cmd);
    }
    else if (cmd.startsWith("READ ")) {
      handle_read(cmd);
    }
    else if (cmd == "SCAN") {
      handle_scan();
    }
  }
}

void handle_write(String cmd) {
  int sep1 = cmd.indexOf(' ', 6);
  uint16_t addr = cmd.substring(6, sep1).toInt();
  int len = cmd.substring(sep1 + 1).toInt();
  Serial.println("OK");
  
  uint8_t buf[32];
  int received = 0;
  while (received < len) {
    if (Serial.available()) {
      buf[received++] = Serial.read();
    }
  }
  
  Wire.beginTransmission(EEPROM_ADDR);
  Wire.write((uint8_t)(addr >> 8));
  Wire.write((uint8_t)(addr & 0xFF));
  for (int i = 0; i < len; i++) {
    Wire.write(buf[i]);
  }
  uint8_t err = Wire.endTransmission();
  
  if (err == 0) {
    delay(10);
    Serial.println("DONE");
  } else {
    Serial.print("ERR ");
    Serial.println(err);
  }
}

void handle_read(String cmd) {
  int sep1 = cmd.indexOf(' ', 5);
  uint16_t addr = cmd.substring(5, sep1).toInt();
  int len = cmd.substring(sep1 + 1).toInt();
  
  Wire.beginTransmission(EEPROM_ADDR);
  Wire.write((uint8_t)(addr >> 8));
  Wire.write((uint8_t)(addr & 0xFF));
  uint8_t err = Wire.endTransmission();
  
  if (err != 0) {
    Serial.print("ERR ");
    Serial.println(err);
    return;
  }
  
  Wire.requestFrom(EEPROM_ADDR, len);
  Serial.print("DATA ");
  while (Wire.available()) {
    uint8_t b = Wire.read();
    if (b < 16) Serial.print("0");
    Serial.print(b, HEX);
  }
  Serial.println();
}

void handle_scan() {
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.print("FOUND 0x");
      Serial.println(a, HEX);
    }
  }
  Serial.println("SCAN_DONE");
}
