#define LED_PIN 13
#define PWM_PIN 5
#define SENSOR_PIN A3
#define BLINK_COUNT 3

// Control values
float targetSetpoint = 0.0;
float kp = 0.0;
float ki = 0.0;
float kd = 0.0;
float sensorPosition = 12.5;

// Serial incoming data
String incomingData = "";

// Debug led config
bool isBlinking = false;
int blinkCount = 0;
unsigned long previousMillis = 0;
const long interval = 250;


void setup() {
  // Defining builtin led as output for debug pourposes
  pinMode(LED_PIN, OUTPUT);
  // Defining output and input of control system
  pinMode(PWM_PIN, OUTPUT);
  pinMode(SENSOR_PIN, INPUT);

  // Serial config
  Serial.begin(9600);
  Serial.println("System ready.");
}


void loop() {
  // Parses incoming data and sends data through serial port
  serialRoutine();

  // *** PID Routine bellow ***

  // Reading sensor
  updateSensorPosition();

  // Writing in output
  writePWM(kd);
}


// Helper function for float mapping
float interpolate(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

/**
 * Writes the desired voltage to the PWM pin using piecewise linear interpolation.
 * @param dc Normalized value (0.0 for 0V, 1.0 for 10V).
 */
void writePWM(float dc) {
  // Target voltage based on 0.0-1.0 scale
  float targetV = dc * 10.0;
  float pwmValue = 0;

  // Inverse mapping based on user-provided table (Voltage -> PWM)
  if (targetV <= 0.0) {
    pwmValue = 0;
  } else if (targetV <= 1.16) {
    pwmValue = interpolate(targetV, 0.0, 1.16, 0.0, 12.75);
  } else if (targetV <= 1.82) {
    pwmValue = interpolate(targetV, 1.16, 1.82, 12.75, 25.5);
  } else if (targetV <= 3.06) {
    pwmValue = interpolate(targetV, 1.82, 3.06, 25.5, 51.0);
  } else if (targetV <= 3.62) {
    pwmValue = interpolate(targetV, 3.06, 3.62, 51.0, 63.75);
  } else if (targetV <= 4.14) {
    pwmValue = interpolate(targetV, 3.62, 4.14, 63.75, 76.5);
  } else if (targetV <= 5.19) {
    pwmValue = interpolate(targetV, 4.14, 5.19, 76.5, 102.0);
  } else if (targetV <= 6.12) {
    pwmValue = interpolate(targetV, 5.19, 6.12, 102.0, 127.5);
  } else if (targetV <= 7.01) {
    pwmValue = interpolate(targetV, 6.12, 7.01, 127.5, 153.0);
  } else if (targetV <= 7.80) {
    pwmValue = interpolate(targetV, 7.01, 7.80, 153.0, 178.5);
  } else if (targetV <= 8.22) {
    pwmValue = interpolate(targetV, 7.80, 8.22, 178.5, 191.25);
  } else if (targetV <= 8.57) {
    pwmValue = interpolate(targetV, 8.22, 8.57, 191.25, 204.0);
  } else if (targetV <= 9.26) {
    pwmValue = interpolate(targetV, 8.57, 9.26, 204.0, 229.5);
  } else if (targetV <= 9.77) {
    pwmValue = interpolate(targetV, 9.26, 9.77, 229.5, 255.0);
  } else {
    // Hardware saturation limit: 9.77V is the maximum measured output
    pwmValue = 255.0;
  }

  // Write finalized 8-bit value to the pin
  analogWrite(PWM_PIN, (int)constrain(pwmValue, 0, 255));
}


// Updates global variable sensorPosition based on analogRead on SENSOR_PIN
void updateSensorPosition(){
  int sensorValue = analogRead(SENSOR_PIN); // Read 0-1023 (0-5V)
  sensorPosition = (float) map(sensorValue, 0, 1023, 0, 2500)/100; // Transforms 0-1023 into 0-250mm
}


// Receives and sends data through serial port
void serialRoutine(){
  // Receives serial data
  if (Serial.available() > 0) {
    // Reads the incoming string from serial port until '\n'
    incomingData = Serial.readStringUntil('\n');
    // Parses incoming packet, i.e., updates targetSetpoint, kp, ki and kd
    if (parseIncomingPacket(incomingData)){
      // Debug via led. Blinks LED_PIN BLINK_COUNT times
      startBlinking();
    }
  }

  // Sends serial data
  Serial.println(sensorPosition);
  updateBlink(); // Debug via led
}


// Parses incoming packet, updating setpoint and PID gains
bool parseIncomingPacket(String packet) {
  int indexSP = packet.indexOf("SP:");
  int indexP = packet.indexOf(";P:");
  int indexI = packet.indexOf(";I:");
  int indexD = packet.indexOf(";D:");

  if (indexSP == -1 || indexP == -1 || indexI == -1 || indexD == -1) {
    return false;
  }

  targetSetpoint = packet.substring(indexSP + 3, indexP).toFloat();
  kp = packet.substring(indexP + 3, indexI).toFloat();
  ki = packet.substring(indexI + 3, indexD).toFloat();
  kd = packet.substring(indexD + 3).toFloat();

  return true;
}


// Blinks led. Debug pourposes
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