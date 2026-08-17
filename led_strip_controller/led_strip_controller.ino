#include <WiFiS3.h>
#include <Adafruit_NeoPixel.h>

const char* ssid     = "Pixel_9355";
const char* password = "scottjurek";

#define LED_PIN    6
#define LED_COUNT 24

Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
WiFiServer server(8080);

void setup() {
  Serial.begin(115200);
  strip.begin();
  strip.show(); // Turn off all pixels initially

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  // Wait for a valid IP assignment from the hotspot
  while (WiFi.localIP() == IPAddress(0, 0, 0, 0)) {
    delay(500);
    Serial.print("w");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("Arduino IP Address: ");
  Serial.println(WiFi.localIP());

  server.begin();
}

void loop() {
  WiFiClient client = server.available();

  if (client) {
    while (client.connected()) {
      // Drain everything currently buffered, then refresh the strip once.
      // (Previously strip.show() fired after every single 4-byte command,
      // which added latency and made a batched frame render pixel-by-pixel
      // instead of all at once.)
      bool dirty = false;
      while (client.available() >= 4) {
        uint8_t index = client.read();
        uint8_t r     = client.read();
        uint8_t g     = client.read();
        uint8_t b     = client.read();

        if (index < LED_COUNT) {
          strip.setPixelColor(index, strip.Color(r, g, b));
          dirty = true;
        }
      }
      if (dirty) {
        strip.show();
      }
      // Small yield to let the WiFi stack breathe
      yield();
    }
    client.stop();
  }
}
