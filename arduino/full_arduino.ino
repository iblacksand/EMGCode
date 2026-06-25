#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>


const int RED_LIGHT_PIN = 1;
const int BLUE_LIGHT_PIN = 2;
const int GREEN_LIGHT_PIN = 3;

const char* WIFI_SSID = "EnMedPrintFarm";
const char* WIFI_PASSWORD = "Physician33r";

const char SERVER[] = "192.168.1.195";
const int PORT = 8000;

const int BATCH_SIZE = 500;

WiFiClient wifi;
HttpClient client(wifi, SERVER, PORT);

String sessionId = "";

int values[BATCH_SIZE];
int valueCount = 0;

bool is_calibrated = false;

unsigned long batchStartMicros = 0;
unsigned long lastSampleMicros = 0;


enum LightStatus {
  Off,
  Error,
  Good,
  Normal,
  Calibrating,
  Ignore,
};

LightStatus current_status = LightStatus::Ignore;


void set_light_status(LightStatus status) {
  current_status = status;
  update_lights();
}

void update_lights() {
  switch (current_status) {
    case LightStatus::Off:
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 0);
      break;
    case LightStatus::Error:
      analogWrite(RED_LIGHT_PIN, 255);
      analogWrite(BLUE_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 0);
      break;
    case LightStatus::Good:
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 255);
      break;
    case LightStatus::Normal:
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 255);
      analogWrite(GREEN_LIGHT_PIN, 0);
      break;
    case LightStatus::Calibrating:
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 255);
      analogWrite(GREEN_LIGHT_PIN, 255);
      break;
    case LightStatus::Ignore:
    default:
     break; // Don't update for the loop
  }
}


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
      (batchEndMicros - batchStartMicros) / (valueCount - 1);
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

  // Set pin modes
  pinMode(RED_LIGHT_PIN, OUTPUT);
  pinMode(BLUE_LIGHT_PIN, OUTPUT);
  pinMode(GREEN_LIGHT_PIN, OUTPUT);

  Serial.begin(115200);

  while (!Serial) {
    ;
  }

  set_light_status(LightStatus::Error);
  connectWifi();

  while (!createSession()) {
    delay(2000);
  }
  set_light_status(LightStatus::Calibrating);

  Serial.println("Ready.");
}

bool get_status() {
  client.beginRequest();
  client.get("/api/arduino/status?session=" + sessionId);
  client.endRequest();

  int statusCode = client.responseStatusCode();

  if (statusCode != 200) {
    Serial.print("Status request failed: ");
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

  const char* status = doc["status"];

  if (strcmp(status, "calibrating") == 0) {
    set_light_status(LightStatus::Calibrating);
  } else if (strcmp(status, "normal") == 0) {
    set_light_status(LightStatus::Normal);
  } else if (strcmp(status, "good") == 0) {
    set_light_status(LightStatus::Good);
  } else if (strcmp(status, "error") == 0) {
    set_light_status(LightStatus::Error);
  } else {
    set_light_status(LightStatus::Ignore);
  }

  return true;
}

LightStatus basic_status(int current_val) {
    if (current_val < 100) {
        return LightStatus::Error;
    }
    if (100 < current_val && 300 > current_val) {
        return LightStatus::Normal;
    }
    return LightStatus::Good;
}

void loop() {

  // update_lights();

  if (WiFi.status() != WL_CONNECTED) {
    set_light_status(LightStatus::Error);
    connectWifi();
  }

  // set_light_status(LightStatus::Calibrating);

  unsigned long now = micros();

  if (valueCount == 0) {
    batchStartMicros = now;
  }

  int current_reading = analogRead(A0);

  set_light_status(basic_status(current_reading));

  values[valueCount++] = analogRead(current_reading);
  lastSampleMicros = now;

  if (valueCount >= BATCH_SIZE) {
    if (!sendBatch()) {
      Serial.println("Upload failed.");
      delay(10);
    }
  }
}
