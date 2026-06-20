#include <WiFiS3.h>
#include <ArduinoHttpClient.h>

const char* WIFI_SSID = "EnMedPrintFarm";
const char* WIFI_PASSWORD = "Physician33r";

const char server[] = "192.168.1.195";
const int port = 8000;

WiFiClient wifi;
HttpClient client(wifi, server, port);

void setup() {
  Serial.begin(115200);

  while (!Serial) {
    ; // Wait for Serial Monitor
  }

  Serial.println("Connecting to WiFi...");

  while (WiFi.begin(WIFI_SSID, WIFI_PASSWORD) != WL_CONNECTED) {
    Serial.println("Failed to connect. Retrying...");
    delay(5000);
  }

  Serial.println("Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

void loop() {
  int value = analogRead(A0);

  String path = "/api/arduino/" + String(value);

  Serial.print("Sending GET ");
  Serial.println(path);

  client.get(path);

  int statusCode = client.responseStatusCode();

  Serial.print("Status Code: ");
  Serial.println(statusCode);

  String response = client.responseBody();

  Serial.print("Response: ");
  Serial.println(response);

  Serial.println();

  delay(1000);
}