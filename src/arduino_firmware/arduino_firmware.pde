#include <Servo.h>
#include <CompactQik2s9v1.h>
#include <NewSoftSerial.h>

// Specify the chars for the modes
#define motorChar 'M'
#define stepperChar 'T'
#define servoChar 'S'
#define digitalChar 'D'
#define analogChar 'A'
#define initChar 'I'
#define doneChar ';'
// The motor controller reset pin (not currently used)
#define mcResetPin 53

// Implement the new and delete operators
void* operator new(size_t size) { return malloc(size); }
void operator delete(void* ptr) { free(ptr); } 


// Defines a class that manages a stepper
class Stepper
{
  public:
    int dirPin, stepPin;
    Stepper(int dir, int step)
    {
      stepPin = dir;
      dirPin = step;
    }
    void step(boolean dir, int steps)
    {
      digitalWrite(dirPin, dir);
      for (int i = 0; i < steps; i++)
      {
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(100);
        digitalWrite(stepPin, LOW);
        delayMicroseconds(100);
      }
    }
};



// Dynamic array of all the motor controllers
CompactQik2s9v1** mc;
// Dynamic array of all the stepper motors
Stepper** stepper;
// Dynamic array of all the servo ports
Servo** servo;
// Dynamic array of all the digital ports
int* digitalPorts;
// Dynamic array of all the analog ports
int* analogPorts;

// Keeps track of how many of each thing we have
int numMCs = 0;
int numSteppers = 0;
int numServos = 0;
int numDigital = 0;
int numAnalog = 0;

int resetCounter = 0;


// The dynamically sized return string
char* retVal;
int retIndex;

// Helper function to keep track of retIndex and use it to write
// a character to the correct location in the retVal array
void writeToRetVal(char c)
{
  retVal[retIndex] = c;
  retIndex++;
}


// Helper function to end our retVal string with the ';' command
// and a null character
void endRetVal()
{
  retVal[retIndex] = ';';
  retVal[retIndex+1] = 0;
}

// Helper function to send the retVal through the serial connection
// as well as reset the retIndex variable
void sendRetVal()
{
  Serial.print(retVal);
  Serial.flush();
  retIndex = 0;
}

// Define a serial read that actually blocks
char serialRead()
{
  char in;
  // Loop until input is not -1 (which means no input was available)
  while ((in = Serial.read()) == -1) {}
  return in;
}

// Handles the motor component of initialization
void motorInit()
{
  int rxPin, txPin;
  NewSoftSerial* tempSerial;
  CompactQik2s9v1* tempMC;
  
  // Free up any allocated memory from before
  // Note: there's a memory leak here - the NewSoftSerial objects
  // never get free'd. I'm too lazy to fix it :P
  for (int i = 0; i < numMCs; i++)
  {
    free(mc[i]);
  }
  free(mc);

  // Read in the new numMCs
  numMCs = (int) serialRead() - 1;
  // Reallocate the array
  mc = (CompactQik2s9v1**) malloc(sizeof(CompactQik2s9v1*) * numMCs);
  for (int i = 0; i < numMCs; i++)
  {
    // Create the NewSoftSerial and CompactQik objects and store
    // them in the array
    rxPin = (int) serialRead();
    txPin = (int) serialRead();
    tempSerial = new NewSoftSerial(rxPin, txPin);
    tempMC = new CompactQik2s9v1(tempSerial, mcResetPin);
    tempSerial->begin(9600);
    tempMC->begin();
    tempMC->getError();
    tempMC->stopBothMotors();
    // Set the stop on error to false
    tempSerial->print(0x84, BYTE);
    tempSerial->print(2, BYTE);
    tempSerial->print(0);
    tempSerial->print(0x84, BYTE);
    tempSerial->print(3, BYTE);
    tempSerial->print(0);
    mc[i] = tempMC;
  }
}

// Handles the stepper initialization
void stepperInit()
{
  Stepper* tempStepper;

  // Free up the previously allocated memory
  for (int i = 0; i < numSteppers; i++)
  {
    free(stepper[i]);
  }
  free(stepper);

  // Read in the new numSteppers
  numSteppers = (int) serialRead() - 1;
  // Reallocate the stepper array
  stepper = (Stepper**) malloc(sizeof(Stepper*) * numSteppers);
  for (int i = 0; i < numSteppers; i++)
  {
    // Read in the dirPin and stepPin
    int dirPin = (int) serialRead();
    int stepPin = (int) serialRead();
    // Create the Stepper object and store it in the array
    tempStepper = new Stepper(dirPin, stepPin);
    stepper[i] = tempStepper;
  }
}

// Handles the servo initialization
void servoInit()
{
  Servo* tempServo;
  
  // Free up the previously allocated memory
  for (int i = 0; i < numServos; i++)
  {
    free(servo[i]);
  }
  free(servo);
  
  // Read in the new numServos
  numServos = (int) serialRead() - 1;
  // Reallocate the servo array
  servo = (Servo**) malloc(sizeof(Servo*) * numServos);
  for (int i = 0; i < numServos; i++)
  {
    // Create the Servo object and store it in the array
    tempServo = new Servo();
    tempServo->attach((int) serialRead());
    servo[i] = tempServo;
  }
}

// Handles the digital sensor initialization
void digitalInit()
{
  numDigital = (int) serialRead() - 1;
  digitalPorts = (int*) malloc (sizeof(int) * numDigital);
  for (int i = 0; i < numDigital; i++)
  {
    digitalPorts[i] = (int) serialRead();
  }
}

// Handles the analog sensor initialization
void analogInit()
{
  numAnalog = (int) serialRead() - 1;
  analogPorts = (int*) malloc (sizeof(int) * numAnalog);
  for (int i = 0; i < numAnalog; i++)
  {
    analogPorts[i] = (int) serialRead();
  }
}

// Init function which is run whenever the python code needs to
// initialize all of the ports for our sensors and actuators
void initAll()
{
  // Initialize all the sensors and actuators
  char mode;
  while((mode = serialRead()) != doneChar)
  {
    switch(mode)
    {
      case motorChar:
        motorInit();
        break;
      case servoChar:
        servoInit();
        break;
      case digitalChar:
        digitalInit();
        break;
      case analogChar:
        analogInit();
        break;
    }
  }

  // Initialize retVal and retIndex
  // 2 bytes for 'Dn', numDigital bytes for the following arguments,
  // then 2 bytes for 'Am', 2*numAnalog bytes because each analog
  // input is 2 bytes long. Finally, 2 bytes for the ';' and the
  // null character at the end.
  retVal = (char*) malloc(((2+numDigital) + (2+2*numAnalog) + 2) * sizeof(char));
  retIndex = 0;
}

// Special function run when the arduino is first connected to power
void setup()
{
  // Create the serial connection with the eeePC
  Serial.begin(9600);
  // Clear the buffer
  Serial.flush();
}

// Special function that is repeatedly called during normal running
// of the Arduino
void loop()
{
  // Check if there is any input, otherwise do nothing
  if (Serial.available() > 0)
  {
    //------------ READ IN ALL THE COMMMANDS -------------
    // Command packet format:
    // An1234Bm5678;
    // A, B = mode markers (telling us what type of command it is)
    // n, m = length markers (telling us how many arguments follow
    //     the command)
    // 1234, 5678 = command arguments
    // ; = special mode marker that deliminates the end of the command
    //     packet

    // Use the done helper variable to know when to move on
    boolean done = false;
    while (!done)
    {
      // Read in the first character, which is the mode, telling
      // us what to do
      char mode = serialRead();

      // Perform actions based on the mode read in
      switch (mode)
      {
        case initChar:
          // Process all the input data and set up all the dynamic
          // arrays
          initAll();
          return;
          break;
        case motorChar:
          // Process the next characters and use them to set motor
          // speeds
          moveMotors();
          break;
  
        case servoChar:
          // Process the next characters and use them to set servo
          // angles
          moveServos();
          break;
  
        case doneChar:
          // We're done reading in input from python
          done = true;
          break;
      }
    }


    //------------- WRITE OUT ALL THE SENSOR DATA -----------

    // Write digital data
    // Add our mode character
    writeToRetVal(digitalChar);
    // Add the number of sensors
    // Add 1 because 0 terminates the string
    writeToRetVal((char) numDigital+1);
    // Add all the sensor data
    for (int i = 0; i < numDigital; i++)
    {
      // Digital read the ith sensor and add it's value to retVal
      // We add 1 to the value because 0 would terminate the string
      writeToRetVal((char) digitalRead(digitalPorts[i])+1);
    }

    // Write analog data
    // Add our mode character
    writeToRetVal(analogChar);
    // Add the number of sensors
    // Add 1 because 0 terminates the string
    writeToRetVal((char) numAnalog + 1);
    // Add all the sensor data
    for (int i = 0; i < numAnalog; i++)
    {
      // Analog read the ith sensor and decompose into two bytes
      int analogVal = analogRead(analogPorts[i]);
      unsigned char byte0 = analogVal % 256;
      unsigned char byte1 = analogVal / 256;
      // Do a little tweaking to make sure we don't send a null byte
      // by accident. We possibly lose a little bit of accuracy
      // here.
      if (byte0 != 255)
      {
        byte0++;
      }
      if (byte1 != 255)
      {
        byte1++;
      }

      // Write the two bytes to the retVal, byte0 first
      writeToRetVal(byte0);
      writeToRetVal(byte1);
    }

    // Add a ';' and null terminate the retVal string
    endRetVal();

    // Send the built string
    sendRetVal();
  }
}

// Set the motor speed to s
void setMotorSpeed(int index, int s)
{
  // Figure out which MC we're using
  int mcNumber = index/2;
  CompactQik2s9v1* curMC = (CompactQik2s9v1*) mc[mcNumber];

  // We're using motor0
  if (index % 2 == 0)
  {
    // Break down the 0 - 255 speed into forward/reverse commands
    if (s < 0)
    {
      curMC->motor0Reverse(-1 * s);
    }
    else
    {
      curMC->motor0Forward(s);
    }
  }
  // We're using motor1
  else
  {
    // Break down the 0 - 255 speed into forward/reverse commands
    if (s < 0)
    {
      curMC->motor1Reverse(-1 * s);
    }
    else
    {
      curMC->motor1Forward(s);
    }
  }
}

// Function called to handle the motor command
// Should read in one character to determine how many motors, 
// followed by 1 character per motor and sets the motor speed
// based on that.
void moveMotors()
{
  if (resetCounter > 50)
  {
    resetCounter = 0;
    for (int i = 0; i < numMCs; i++)
    {
      mc[i]->begin();
      mc[i]->getError();
    }
  }
  
  // Read in (and cast to an int) the number of motors
  int numMotors = (int) serialRead() - 1;
  // Per motor, read in the speed and call setMotorSpeed to actually
  // set it
  for (int i = 0; i < numMotors; i++)
  {
    char in = serialRead();
    int s = (int) in - 1;
    // Set the motor speed for the ith motor
    setMotorSpeed(i, s);
  }
}

// Set the servo angle
void setServoAngle(int index, int angle)
{
  servo[index]->write(angle);
}

// Function called to handle the servo command
// Should read in one character to determine how many servos,
// followed by 1 character per servo, setting the servo angle
// based on that (takes the 256 possible inputs and distrubutes
// them through the 360 degrees)
void moveServos()
{
  // Read in (and cast to an int) the number of servos
  int numServos = (int) serialRead() - 1;
  // Per servo, read in the angle and call setServoAngle to actually set it
  for (int i = 0; i < numServos; i++)
  {
    // Set the servo angle for the ith motor
    setServoAngle(i, (int) serialRead() - 1);
  }
}



