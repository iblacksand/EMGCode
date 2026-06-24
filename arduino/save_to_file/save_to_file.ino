const int ANALOG_PIN = A0;
const float VREF = 5.0;  // Uno R4 default analog reference

void setup() {
    Serial.begin(115200);

    while (!Serial) {
        ; // Wait for serial connection
    }

    Serial.println("millis,voltage");
}

void loop() {
    int raw = analogRead(ANALOG_PIN);

    // float voltage = raw * VREF / 1023.0;

    Serial.print(millis());
    Serial.print(",");
    Serial.println(raw);

    // delay(100);
}
