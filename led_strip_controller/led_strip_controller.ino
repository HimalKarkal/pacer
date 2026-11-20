#include <Adafruit_NeoPixel.h>

#define LED_PIN    6
#define LED_COUNT  24
#define SYNC_BYTE  0xFF
#define BAUD_RATE  115200

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  Serial.begin(BAUD_RATE);
  strip.begin();
  strip.show();
}

void loop() {
  // Look for the sync byte to align the stream
  while (Serial.available() > 0) {
    uint8_t incoming = Serial.read();

    if (incoming != SYNC_BYTE) {
      continue;
    }

    // Wait until the remaining LED_COUNT * 3 bytes of the frame arrive
    const int expectedBytes = LED_COUNT * 3;
    unsigned long startTime = millis();
    while (Serial.available() < expectedBytes) {
      if (millis() - startTime > 50) { // Timeout safety net
        break;
      }
    }

    if (Serial.available() >= expectedBytes) {
      for (int i = 0; i < LED_COUNT; i++) {
        uint8_t r = Serial.read();
        uint8_t g = Serial.read();
        uint8_t b = Serial.read();
        strip.setPixelColor(i, strip.Color(r, g, b));
      }
      strip.show();
    }
  }
}
