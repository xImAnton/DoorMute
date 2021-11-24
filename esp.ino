#include <ESP8266WiFi.h>
#include "user_interface.h"
#include <ESP8266HTTPClient.h>

const char* ssid = "";
const char* password = "";

bool button_pressed = false;

void setup() {
  pinMode(3, INPUT);
  wifi_set_sleep_type(LIGHT_SLEEP_T);
  
  WiFi.begin(ssid, password);
 
  int timeout = 10 * 4;
  while(WiFi.status() != WL_CONNECTED && (timeout-- > 0)) { // todo: retry after x seconds when timeout expired
    delay(250);
  }
}

void loop() {
  bool pressed = !digitalRead(3);
  if (!button_pressed && pressed) {
    button_pressed = true;
    WiFiClient client;
    HTTPClient http;
  
    if (http.begin(client, "http://host:3465/trigger?key=<password>")) {  // HTTP
      http.GET();
      http.end();
    }
  }
  if (button_pressed && !pressed) {
    button_pressed = false;
  }
  delay(50);
}
