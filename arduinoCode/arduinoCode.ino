#define LED_PIN 13
#define PWM_PIN 5
#define SENSOR_PIN A3
#define CONTROL_READ_PIN A0
#define BLINK_COUNT 3

// Control values
float targetSetpoint = 0.0;
float kp = 0.0;
float ki = 0.0;
float kd = 0.0;
float sensorPosition = 12.5;
float controlSignalV = 0.0; 

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

  Serial.begin(9600);
  Serial.println("System ready.");
}


void loop() {
  serialRoutine();

  // *** PID Routine bellow ***

  updateSensorPosition();
  updateControlSignal();   // Lê o sinal de controle em A0

  // writePWM recebe kd como debug
  writePWM(kd);
}


// Helper function for float mapping
float interpolate(float x, float in_min, float in_max, float out_min, float out_max) {
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;
}

// Writes the desired voltage to the PWM pin using piecewise linear interpolation.
void writePWM(float dc) {
  float targetV = dc * 10.0;
  float pwmValue = 0;

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
    pwmValue = 255.0;
  }

  analogWrite(PWM_PIN, (int)constrain(pwmValue, 0, 255));
}


// Updates global variable sensorPosition based on analogRead on SENSOR_PIN
void updateSensorPosition() {
  int sensorValue = analogRead(SENSOR_PIN);                          // 0–1023
  sensorPosition = (float) map(sensorValue, 0, 1023, 0, 2500) / 100; // 0–25 cm
}


// Reads the control signal from CONTROL_READ_PIN and converts to Volts (0–5 V)
void updateControlSignal() {
  int rawValue = analogRead(CONTROL_READ_PIN);         // 0–1023
  controlSignalV = (float)rawValue * 5.0 / 1023.0;    // 0.0–5.0 V
}


// Receives and sends data through serial port
void serialRoutine() {
  if (Serial.available() > 0) {
    incomingData = Serial.readStringUntil('\n');
    if (parseIncomingPacket(incomingData)) {
      startBlinking();
    }
  }

  // Sends position (Y) e control signal (U) in the format "Y:<val>;U:<val>"
  Serial.print("Y:");
  Serial.print(sensorPosition, 2);
  Serial.print(";U:");
  Serial.println(controlSignalV, 3);

  updateBlink();
}


// Parses incoming packet, updating setpoint and PID gains
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


// Blinks led — debug purposes
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
