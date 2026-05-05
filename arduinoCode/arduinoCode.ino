#define LED_PIN 13
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

  // Serial config
  Serial.begin(9600);
  Serial.println("System ready.");
}


void loop() {
  // Parses incoming data and sends data through serial port
  serialRoutine();

  // PID Routine bellow
  sensorPosition += 0.001; // Apenas de teste, excluir dps
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