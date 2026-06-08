#define LED_PIN 13
#define PWM_PIN 5
#define SENSOR_PIN A3
#define CONTROL_READ_PIN A0
#define BLINK_COUNT 3

// Telemetry and buffer definitions
#define TELEMETRY_INTERVAL 2  // 2ms = 500Hz sampling rate for the buffer
#define BLOCK_INTERVAL 100    // 100ms block accumulation time
#define BUFFER_SIZE 70        // 50 samples expected in 100ms, 70 provides a safe margin

// Control values
float targetSetpoint = 0.0;
float kp = 0.0;
float ki = 0.0;
float kd = 0.0;
float sensorPosition = 0.0;
float controlSignalV = 0.0; 

// PID specific variables
float integralError = 0.0;
float previousError = 0.0;
unsigned long previousTimeMicros = 0;
float pidOutput = 0.0; // Value to be written to PWM (0-255)

// Oversampling accumulators
float sumPos = 0.0;
float sumCtrl = 0.0;
unsigned int sampleCount = 0;

// Buffer arrays
unsigned long timeBuffer[BUFFER_SIZE];
float posBuffer[BUFFER_SIZE];
float ctrlBuffer[BUFFER_SIZE];
int bufferHead = 0;
unsigned long lastTelemetryTime = 0;
unsigned long lastBlockSendTime = 0;

// Serial incoming data
String incomingData = "";

// Debug led config
bool isBlinking = false;
int blinkCount = 0;
unsigned long previousMillis = 0;
const long interval = 250;

void setup() {
  pinMode(LED_PIN, OUTPUT);
  pinMode(PWM_PIN, OUTPUT);
  pinMode(SENSOR_PIN, INPUT);
  pinMode(CONTROL_READ_PIN, INPUT);

  // High baud rate is mandatory to flush the 100ms data block without freezing the PID
  Serial.begin(500000);
  Serial.println("System ready.");
  
  // Use micros() for precision in PID loop
  previousTimeMicros = micros();
}

void loop() {
  serialRoutine();

  // Control loop runs as fast as the hardware allows
  updateSensorPosition();
  updatePID();
  analogWrite(PWM_PIN, (int)pidOutput + 127);
  updateControlSignal(); 

  // Accumulate samples continuously
  sumPos += sensorPosition;
  sumCtrl += controlSignalV;
  sampleCount++;

  unsigned long currentMillis = millis();

  // Save averaged data to buffer at fixed frequency
  if (currentMillis - lastTelemetryTime >= TELEMETRY_INTERVAL) {
    lastTelemetryTime = currentMillis;
    
    if (bufferHead < BUFFER_SIZE && sampleCount > 0) {
      timeBuffer[bufferHead] = currentMillis;
      posBuffer[bufferHead] = sumPos / sampleCount;
      ctrlBuffer[bufferHead] = sumCtrl / sampleCount;
      bufferHead++;
    }

    // Reset accumulators for the next interval
    sumPos = 0.0;
    sumCtrl = 0.0;
    sampleCount = 0;
  }

  // Send the entire block every 100ms
  if (currentMillis - lastBlockSendTime >= BLOCK_INTERVAL) {
    lastBlockSendTime = currentMillis;
    sendTelemetryBlock();
  }
}

void updatePID() {
  // Using micros() prevents dt dropping to 0 in fast control loops
  unsigned long currentMicros = micros();
  float dt = (float)(currentMicros - previousTimeMicros) / 1000000.0;

  // Safeguard against division by zero or negative time
  if (dt <= 0.00001) return; 

  float error = targetSetpoint - sensorPosition;

  float pTerm = kp * error;

  integralError += error * dt;
  float iTerm = ki * integralError;

  float dTerm = kd * (error - previousError) / dt;

  pidOutput = pTerm + iTerm + dTerm;

  if (pidOutput > 127) pidOutput = 127;
  if (pidOutput < -127)   pidOutput = -127;

  previousError = error;
  previousTimeMicros = currentMicros;
}

void updateSensorPosition() {
  int sensorValue = analogRead(SENSOR_PIN);                                  // 0-1023
  sensorPosition = (float) map(sensorValue, 0, 1023, 0, 2500) / 100.0;       // 0-25 cm
}

void updateControlSignal() {
  int rawValue = analogRead(CONTROL_READ_PIN);         // 0-1023
  controlSignalV = (float)rawValue * 5.0 / 1023.0;     // 0.0-5.0 V
}

void serialRoutine() {
  if (Serial.available() > 0) {
    incomingData = Serial.readStringUntil('\n');
    if (parseIncomingPacket(incomingData)) {
      startBlinking();
    }
  }
  updateBlink();
}

void sendTelemetryBlock() {
  if (bufferHead == 0) return;

  // Send a 2-byte synchronization marker (0xAAAA) and the payload size
  const uint16_t syncMarker = 0xAAAA;
  Serial.write((uint8_t*)&syncMarker, sizeof(syncMarker));
  Serial.write((uint8_t*)&bufferHead, sizeof(bufferHead));

  // Bulk write memory arrays directly to hardware serial buffer
  Serial.write((uint8_t*)timeBuffer, bufferHead * sizeof(unsigned long));
  Serial.write((uint8_t*)posBuffer, bufferHead * sizeof(float));
  Serial.write((uint8_t*)ctrlBuffer, bufferHead * sizeof(float));

  bufferHead = 0;
}

bool parseIncomingPacket(String packet) {
  int indexSP = packet.indexOf("SP:");
  int indexP  = packet.indexOf(";P:");
  int indexI  = packet.indexOf(";I:");
  int indexD  = packet.indexOf(";D:");

  if (indexSP == -1 || indexP == -1 || indexI == -1 || indexD == -1) {
    return false;
  }

  targetSetpoint = packet.substring(indexSP + 3, indexP).toFloat();
  kp = packet.substring(indexP + 3, indexI).toFloat();
  ki = packet.substring(indexI + 3, indexD).toFloat();
  kd = packet.substring(indexD + 3).toFloat();

  return true;
}

void startBlinking() {
  if (!isBlinking) {
    isBlinking = true;
    blinkCount = 0;
    previousMillis = millis();
    digitalWrite(LED_PIN, HIGH);
  }
}

void updateBlink() {
  if (isBlinking) {
    unsigned long currentMillis = millis();
    if (currentMillis - previousMillis >= interval) {
      previousMillis = currentMillis;
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      if (digitalRead(LED_PIN) == LOW) {
        blinkCount++;
      }
      if (blinkCount >= 3) {
        isBlinking = false;
        digitalWrite(LED_PIN, LOW);
      }
    }
  }
}