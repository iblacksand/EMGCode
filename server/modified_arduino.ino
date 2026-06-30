#include <WiFiS3.h>
#include <ArduinoHttpClient.h>
#include <ArduinoJson.h>

const int RED_LIGHT_PIN = 3;
const int GREEN_LIGHT_PIN = 2;
const int BLUE_LIGHT_PIN = 1;

const char* WIFI_SSID = "EnMedPrintFarm";
const char* WIFI_PASSWORD = "Physician33r";

const char SERVER[] = "192.168.1.195";
const int PORT = 8000;

// Batch sizes: Reduced to 500 for responsive calibration feedback
// (5000 samples would take too long to give the user immediate visual feedback)
const int BATCH_SIZE = 500;
const int CALIBRATION_FLEXES = 3;

WiFiClient wifi;
HttpClient client(wifi, SERVER, PORT);

String sessionId = "";

int values[BATCH_SIZE];
int valueCount = 0;

// State Tracking
bool is_calibrated = false;
int accepted_calibrations = 0;

// Thresholds
float normal_peak = 0;
float good_threshold = 0;
float poor_threshold = 0;
const int NOISE_FLOOR = 50; // Prevents "red" light when completely idle

// Timing
unsigned long batchStartMicros = 0;
unsigned long lastSampleMicros = 0;
unsigned long last_blink = 0;
int blink_interval = 500;
bool blink_on = true;

// Helper: Easily set LED colors
void set_light_color(int r, int g, int b) {
  analogWrite(RED_LIGHT_PIN, r);
  analogWrite(GREEN_LIGHT_PIN, g);
  analogWrite(BLUE_LIGHT_PIN, b);
}

bool connectWifi() {
  Serial.println("Connecting to WiFi...");
  set_light_color(255, 0, 0); // Red while connecting

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
    if (client.connected()) client.responseBody();
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

bool get_settings() {
  client.beginRequest();
  // Fetching the final thresholds after calibration
  client.get("/api/settings");
  client.endRequest();

  int statusCode = client.responseStatusCode();
  if (statusCode != 200) {
    Serial.print("Settings request failed: ");
    Serial.println(statusCode);
    if (client.connected()) client.responseBody();
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

  // Assuming the server provides the calculated thresholds now
  normal_peak = doc["normal_peak"];
  good_threshold = doc["good_threshold"];
  poor_threshold = doc["poor_threshold"];

  Serial.println("Settings loaded:");
  Serial.print("Normal peak: ");
  Serial.println(normal_peak);
  Serial.print("Good threshold: ");
  Serial.println(good_threshold);
  Serial.print("Poor threshold: ");
  Serial.println(poor_threshold);

  return true;
}

void handle_calibration_feedback(bool accepted) {
  if (accepted) {
    Serial.println("Calibration flex accepted!");
    set_light_color(0, 255, 0); // Solid Green for 1 second
    delay(1000);
    accepted_calibrations++;
  } else {
    Serial.println("Calibration flex rejected. Try again.");
    // Blinking red for 1 second
    for (int i = 0; i < 5; i++) {
      set_light_color(255, 0, 0);
      delay(100);
      set_light_color(0, 0, 0);
      delay(100);
    }
  }
}

bool send_calibration_batch() {
  set_light_color(0, 0, 255); // Blue if using wifi to send data

  unsigned long batchEndMicros = micros();
  uint32_t samplePeriodUs = 0;
  if (valueCount > 1) {
    samplePeriodUs = (batchEndMicros - batchStartMicros) / (valueCount - 1);
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

  client.beginRequest();
  client.post("/api/arduino/calibration_signal");
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  client.beginBody();
  client.print(payload);
  client.endRequest();

  int statusCode = client.responseStatusCode();
  String response = client.responseBody();

  if (statusCode == 200) {
    // Check if server returned True/False (Handles raw string or JSON {"accepted": true})
    response.toLowerCase();
    if (response.indexOf("true") >= 0) {
      return true;
    }
  }
  return false;
}

bool send_live_batch() {
  set_light_color(0, 0, 255); // Blue if using wifi to send data

  unsigned long batchEndMicros = micros();
  uint32_t samplePeriodUs = 0;
  if (valueCount > 1) {
    samplePeriodUs = (batchEndMicros - batchStartMicros) / (valueCount - 1);
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

  client.beginRequest();
  client.post("/api/arduino/batch");
  client.sendHeader("Content-Type", "application/json");
  client.sendHeader("Content-Length", payload.length());
  client.beginBody();
  client.print(payload);
  client.endRequest();

  int statusCode = client.responseStatusCode();
  if (statusCode == 200) {
    client.responseBody(); // Clear buffer
    return true;
  }

  return false;
}

void setup() {
  pinMode(RED_LIGHT_PIN, OUTPUT);
  pinMode(BLUE_LIGHT_PIN, OUTPUT);
  pinMode(GREEN_LIGHT_PIN, OUTPUT);

  Serial.begin(115200);
  while (!Serial) { ; }

  connectWifi();

  while (!createSession()) {
    delay(2000);
  }

  Serial.println("Ready. Entering calibration phase...");
  Serial.print("Perform ");
  Serial.print(CALIBRATION_FLEXES);
  Serial.println(" normal flexes to calibrate.");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  unsigned long now = micros();
  if (valueCount == 0) {
    batchStartMicros = now;
  }

  int current_reading = analogRead(A0);

  // LED Status Handling
  if (!is_calibrated) {
    // Calibration Phase: Blinking Blue Light
    unsigned long currentMillis = millis();
    if (currentMillis - last_blink >= blink_interval) {
      last_blink = currentMillis;
      blink_on = !blink_on;
      if (blink_on) set_light_color(0, 0, 255);
      else set_light_color(0, 0, 0);
    }
  } else {
    // Live Phase: Real-time LED feedback based on current reading
    if (current_reading >= good_threshold) {
      set_light_color(0, 255, 0);       // Green if strong/good
    } else if (current_reading >= poor_threshold) {
      set_light_color(0, 0, 0);         // None if normal
    } else if (current_reading > NOISE_FLOOR) {
      set_light_color(255, 0, 0);       // Red if low (but above noise floor)
    } else {
      set_light_color(0, 0, 0);         // Off when resting
    }
  }

  // Record Data
  values[valueCount++] = current_reading;
  lastSampleMicros = now;

  // Batch Processing
  if (valueCount >= BATCH_SIZE) {
    if (!is_calibrated) {
      // Phase 1: Sending to calibration endpoint
      bool accepted = send_calibration_batch();
      handle_calibration_feedback(accepted);
      valueCount = 0; // Reset for next batch

      if (accepted_calibrations >= CALIBRATION_FLEXES) {
        Serial.println("Calibration complete. Fetching final settings...");
        if (get_settings()) {
          is_calibrated = true;
          Serial.println("Entering Live Reading Phase.");
        }
      }
    } else {
      // Phase 2: Sending to live endpoint
      if (!send_live_batch()) {
        Serial.println("Upload failed.");
      }
      valueCount = 0; // Reset for next batch
    }
  }
}
