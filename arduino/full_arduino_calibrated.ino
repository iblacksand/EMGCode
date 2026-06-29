#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>

const unsigned long STATUS_CHECK_INTERVAL = 500;
const int RED_LIGHT_PIN = 3;
const int BLUE_LIGHT_PIN = 1;
const int GREEN_LIGHT_PIN = 2;

const char* WIFI_SSID = "EnMedPrintFarm";
const char* WIFI_PASSWORD = "Physician33r";

const char SERVER[] = "192.168.1.195";
const int PORT = 8000;

const int BATCH_SIZE = 500;
const int CALIBRATION_FLEXES = 3;

WiFiClient wifi;
HttpClient client(wifi, SERVER, PORT);

String sessionId = "";

int values[BATCH_SIZE];
int valueCount = 0;

bool is_calibrated = false;
float calibration_peaks[CALIBRATION_FLEXES];
int calibration_count = 0;
float normal_peak = 0;

float good_threshold = 0;
float poor_threshold = 0;

unsigned long batchStartMicros = 0;
unsigned long lastSampleMicros = 0;

float normal_peak_min = 100.0;
float normal_peak_max = 300.0;
float good_multiplier = 1.2;
float poor_multiplier = 0.7;

enum LightStatus {
  Off,
  Error,
  Good,
  Normal,
  Calibrating,
  Poor,
  Ignore,
};

LightStatus current_status = LightStatus::Ignore;

unsigned long last_blink = 0;
int blink_interval = 500;
bool blink_on = true;
bool enable_blink = false;

int current_batch_max = 0;
bool peak_detected = false;
unsigned long peak_timestamp = 0;

bool handle_blink() {
    if (enable_blink) {
        unsigned long now = millis();
        if ((now - last_blink) >= blink_interval) {
            blink_on = !blink_on;
            last_blink = millis();
        }
        return blink_on;
    }
    return true;
}

void set_light_status(LightStatus status) {
  current_status = status;
  update_lights();
}

void update_lights() {
  if (!handle_blink()) {
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 0);
      return;
  }
  switch (current_status) {
    case LightStatus::Off:
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 0);
      break;
    case LightStatus::Error:
      analogWrite(RED_LIGHT_PIN, 255);
      analogWrite(GREEN_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 0);
      break;
    case LightStatus::Good:
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 255);
      analogWrite(BLUE_LIGHT_PIN, 0);
      break;
    case LightStatus::Normal: // Off?
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 0);
      break;
    case LightStatus::Calibrating:
      analogWrite(RED_LIGHT_PIN, 0);
      analogWrite(GREEN_LIGHT_PIN, 0);
      analogWrite(BLUE_LIGHT_PIN, 255);
      break;
    case LightStatus::Poor:
      analogWrite(RED_LIGHT_PIN, 255);
      analogWrite(GREEN_LIGHT_PIN, 50);
      analogWrite(BLUE_LIGHT_PIN, 0);
      break;
    case LightStatus::Ignore:
    default:
     break;
  }
}

bool get_settings() {
  client.beginRequest();
  client.get("/api/settings");
  client.endRequest();

  int statusCode = client.responseStatusCode();

  if (statusCode != 200) {
    Serial.print("Settings request failed: ");
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

  normal_peak_min = doc["normal_peak_min"];
  normal_peak_max = doc["normal_peak_max"];
  good_multiplier = doc["good_threshold_multiplier"];
  poor_multiplier = doc["poor_threshold_multiplier"];

  Serial.println("Settings loaded:");
  Serial.print("Normal range: ");
  Serial.print(normal_peak_min);
  Serial.print(" - ");
  Serial.println(normal_peak_max);

  return true;
}

LightStatus classify_flex(float peak_value) {
  if (!is_calibrated) {
    return LightStatus::Calibrating;
  }

  if (peak_value >= good_threshold) {
    return LightStatus::Good;
  } else if (peak_value < poor_threshold) {
    return LightStatus::Poor;
  }
  return LightStatus::Normal;
}

bool send_flex_event(float peak_value, const char* quality) {
  JsonDocument doc;

  doc["session"] = sessionId;
  doc["timestamp_micros"] = peak_timestamp;
  doc["peak_value"] = peak_value;
  doc["quality"] = quality;

  String payload;
  serializeJson(doc, payload);

  client.beginRequest();
  client.post("/api/arduino/flex_event");
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  client.beginBody();
  client.print(payload);
  client.endRequest();

  int statusCode = client.responseStatusCode();
  String response = client.responseBody();

  return statusCode == 200;
}

bool send_calibration() {
  JsonDocument doc;

  doc["session"] = sessionId;
  JsonArray arr = doc["calibration_values"].to<JsonArray>();

  for (int i = 0; i < calibration_count; i++) {
    arr.add(calibration_peaks[i]);
  }

  String payload;
  serializeJson(doc, payload);

  client.beginRequest();
  client.post("/api/arduino/calibrate");
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  client.beginBody();
  client.print(payload);
  client.endRequest();

  int statusCode = client.responseStatusCode();

  if (statusCode != 200) {
    Serial.print("Calibration failed: ");
    Serial.println(statusCode);
    return false;
  }

  String body = client.responseBody();

  JsonDocument resp;
  DeserializationError err = deserializeJson(resp, body);

  if (err) {
    Serial.print("JSON parse failed: ");
    Serial.println(err.c_str());
    return false;
  }

  normal_peak = resp["normal_peak"];

  good_threshold = normal_peak * good_multiplier;
  poor_threshold = normal_peak * poor_multiplier;

  Serial.println("Calibration complete!");
  Serial.print("Normal peak: ");
  Serial.println(normal_peak);
  Serial.print("Good threshold: ");
  Serial.println(good_threshold);
  Serial.print("Poor threshold: ");
  Serial.println(poor_threshold);

  is_calibrated = true;
  enable_blink = false;

  return true;
}

bool connectWifi() {
  Serial.println("Connecting to WiFi...");

  while (WiFi.begin(WIFI_SSID, WIFI_PASSWORD) != WL_CONNECTED) {
    Serial.println("Connection failed. Retrying...");
    delay(2000);
  }

  Serial.println("Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  return true;
}

bool createSession() {
  Serial.println("Creating session...");

  client.beginRequest();
  client.get("/api/arduino/new_session");
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
  Serial.print(" samples, max: ");
  Serial.println(current_batch_max);

  if (current_batch_max > 50 && !is_calibrated) {
    if (calibration_count < CALIBRATION_FLEXES) {
      calibration_peaks[calibration_count++] = current_batch_max;
      Serial.print("Calibration flex ");
      Serial.print(calibration_count);
      Serial.print("/");
      Serial.print(CALIBRATION_FLEXES);
      Serial.print(": ");
      Serial.println(current_batch_max);

      if (calibration_count >= CALIBRATION_FLEXES) {
        if (send_calibration()) {
          set_light_status(LightStatus::Normal);
        }
      }
    }
  } else if (current_batch_max > 50 && is_calibrated) {
    LightStatus status = classify_flex(current_batch_max);
    set_light_status(status);

    const char* quality = "normal";
    if (status == LightStatus::Good) {
      quality = "good";
    } else if (status == LightStatus::Poor) {
      quality = "poor";
    }

    send_flex_event(current_batch_max, quality);

    Serial.print("Flex detected: ");
    Serial.print(current_batch_max);
    Serial.print(" - ");
    Serial.println(quality);
  }

  current_batch_max = 0;

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

  get_settings();

  set_light_status(LightStatus::Calibrating);
  enable_blink = true;

  Serial.println("Ready. Waiting for calibration...");
  Serial.print("Perform ");
  Serial.print(CALIBRATION_FLEXES);
  Serial.println(" normal flexes to calibrate.");
}

void loop() {

  update_lights();

  if (WiFi.status() != WL_CONNECTED) {
    set_light_status(LightStatus::Error);
    connectWifi();
  }

  unsigned long now = micros();

  if (valueCount == 0) {
    batchStartMicros = now;
    current_batch_max = 0;
  }

  int current_reading = analogRead(A0);

  if (current_reading > current_batch_max) {
    current_batch_max = current_reading;
    peak_timestamp = now;
  }

  values[valueCount++] = current_reading;
  lastSampleMicros = now;

  // Send live data every 100 samples to reduce HTTP overhead
  if (valueCount % 100 == 0) {
    send_live_value(current_reading);
  }

  if (valueCount >= BATCH_SIZE) {
    if (!sendBatch()) {
      Serial.println("Upload failed.");
      delay(10);
    }
  }
}

bool send_live_value(int value) {
  client.beginRequest();
  client.get("/api/arduino/single/" + String(value));
  client.endRequest();

  int statusCode = client.responseStatusCode();

  if (client.connected()) {
    client.responseBody();
  }

  return statusCode == 200;
}
