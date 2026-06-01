#define LED_PIN 13
#define PWM_PIN 5
#define SENSOR_PIN A3
#define CONTROL_READ_PIN A0
#define BLINK_COUNT 3

// Control values
float targetSetpoint = 0.0;
float kp = 6.0;
float ki = 0.0;
float kd = 0.0;
float sensorPosition = 12.5;
float controlSignalV = 0.0; 

// PID specific variables
float integralError = 0.0;
float previousError = 0.0;
unsigned long previousTime = 0;
float pidOutput = 0.0; // Value to be written to PWM (0-255)

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
  
  previousTime = millis();
}

void loop() {
  serialRoutine();

  // Read sensor FIRST to get the most recent process variable
  updateSensorPosition();
  
  // Calculate PID response based on the new sensor reading
  updatePID();
  
  // Send the calculated output to the actuator
  analogWrite(PWM_PIN, (int)pidOutput + 127);

  // Read the control signal on A0
  updateControlSignal(); 
}

void updatePID() {
  unsigned long currentTime = millis();
  float dt = (float)(currentTime - previousTime)/1000;

  // Prevent division by zero or unnecessary calculations if time hasn't passed
  if (dt <= 0.0) return; 

  // Calculate current error
  float error = targetSetpoint - sensorPosition;

  // Proportional term
  float pTerm = kp * error;

  // Integral term
  integralError += error * dt;
  float iTerm = ki * integralError;

  // Derivative term
  float dTerm = kd * (error - previousError) / dt;

  // Calculate final PID control signal
  pidOutput = pTerm + iTerm + dTerm;

  // Constrain output to valid 8-bit PWM limits (0 to 255)
  if (pidOutput > 127) pidOutput = 127;
  if (pidOutput < -127)   pidOutput = -127;

  // Store current values for the next iteration
  previousError = error;
  previousTime = currentTime;
}

// Updates global variable sensorPosition based on analogRead on SENSOR_PIN
void updateSensorPosition() {
  int sensorValue = analogRead(SENSOR_PIN);                            // 0-1023
  sensorPosition = (float) map(sensorValue, 0, 1023, 0, 2500) / 100.0; // 0-25 cm
}

// Reads the control signal from CONTROL_READ_PIN and converts to Volts (0-5 V)
void updateControlSignal() {
  int rawValue = analogRead(CONTROL_READ_PIN);         // 0-1023
  controlSignalV = (float)rawValue * 5.0 / 1023.0;     // 0.0-5.0 V
}

// Receives and sends data through serial port
void serialRoutine() {
  if (Serial.available() > 0) {
    incomingData = Serial.readStringUntil('\n');
    if (parseIncomingPacket(incomingData)) {
      startBlinking();
    }
  }

  // Sends position (Y) and control signal (U) in the format "Y:<val>;U:<val>"
  Serial.print("Y:");
  Serial.print(sensorPosition, 2);
  Serial.print(";U:");
  Serial.println(controlSignalV * 2.0, 3);

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

// Blinks led - debug purposes
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