#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>

const char* WIFI_SSID = "EnMedPrintFarm";
const char* WIFI_PASSWORD = "Physician33r";

const char SERVER[] = "192.168.1.195";
const int PORT = 8000;

const int BATCH_SIZE = 500;

WiFiClient wifi;
HttpClient client(wifi, SERVER, PORT);

string sessionId = "";

int values[BATCH_SIZE];
int valueCount = 0;

unsigned long batchStartMicros = 0;
unsigned long lastSampleMicros = 0;

bool connectWifi() {
  Serial.println("Connecting to WiFi...");

  while (WiFi.begin(WIFI_SSID, WIFI_PASSWORD) != WL_CONNECTED) {
    Serial.println("Connection failed. Retrying...");
    delay(5000);
  }

  Serial.println("Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  return true;
}

bool createSession() {
  Serial.println("Creating session...");

  client.beginRequest();
  client.post("/api/arduino/new_session");
  client.sendHeader("Content-Length", "0");
  client.endRequest();

  int statusCode = client.responseStatusCode();

  if (statusCode != 200) {
    Serial.print("Session creation failed: ");
    Serial.println(statusCode);

    if (client.connected()) {
      client.responseBody();
    }

    return false;
  }

  String body = client.responseBody();

  JsonDocument doc;

  DeserializationError err = deserializeJson(doc, body);

  if (err) {
    Serial.print("JSON parse failed: ");
    Serial.println(err.c_str());
    return false;
  }

  sessionId = doc["session"].as<String>();

  Serial.print("Session ID: ");
  Serial.println(sessionId);

  return true;
}

bool sendBatch() {
  if (valueCount == 0) {
    return true;
  }

  unsigned long batchEndMicros = micros();

  uint32_t samplePeriodUs = 0;

  if (valueCount > 1) {
    samplePeriodUs =
      (batchEndMicros - batchStartMicros) /
      (valueCount - 1);
  }

  JsonDocument doc;

  doc["session"] = sessionId;
  doc["start_micros"] = batchStartMicros;
  doc["sample_period_us"] = samplePeriodUs;

  JsonArray arr = doc["values"].to<JsonArray>();

  for (int i = 0; i < valueCount; i++) {
    arr.add(values[i]);
  }

  String payload;
  serializeJson(doc, payload);

  Serial.print("Sending ");
  Serial.print(valueCount);
  Serial.println(" samples");

  client.beginRequest();
  client.post("/api/arduino/batch");
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  client.beginBody();
  client.print(payload);
  client.endRequest();

  int statusCode = client.responseStatusCode();

  String response = client.responseBody();

  Serial.print("Status: ");
  Serial.println(statusCode);

  if (statusCode == 200) {
    valueCount = 0;
    return true;
  }

  Serial.print("Response: ");
  Serial.println(response);

  return false;
}

void setup() {
  Serial.begin(115200);

  while (!Serial) {
    ;
  }

  connectWifi();

  while (!createSession()) {
    delay(2000);
  }

  Serial.println("Ready.");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  unsigned long now = micros();

  if (valueCount == 0) {
    batchStartMicros = now;
  }

  values[valueCount++] = analogRead(A0);
  lastSampleMicros = now;

  if (valueCount >= BATCH_SIZE) {
    if (!sendBatch()) {
      Serial.println("Upload failed.");
      delay(1000);
    }
  }
}
