import sys
sys.path.append("../../lib")

import usb.core, usb.util, serial, time
import threading, thread

# Class that handles communication with the arduino
# The general idea is to have a thread that constantly sends actuator commands
# based on arrays and receives sensor data into arrays. The rest of the code
# can then interface with the arduino by reading to and writing from these
# arrays.
class Arduino(threading.Thread):

    # Arrays for keeping track of input / output
    motorSpeeds = []
    stepperSteps = []
    servoAngles = []
    digitalSensors = []
    analogSensors = []

    # Arrays for keeping track of ports
    digitalPorts = []
    analogPorts = []
    motorControllerPorts = []
    stepperPorts = []
    servoPorts = []

    # Initialize the thread and variables
    def __init__(self):
        threading.Thread.__init__(self)
        self.portOpened = False
        self.killReceived = False

    # Start the connection and the thread that communicates with the arduino
    def run(self):
        self.portOpened = self.connect()
        if (self.portOpened):
            self.sendInitData()
            self.readWriteThread = threading.Thread(target=self.checkPorts)
            self.readWriteThread.start()

    # Stop the thread
    def stop(self):
        # This should tell the thread to finish
        self.killReceived = True
        self.readWriteThread.join()

    # Create the serial connection to the arduino
    def connect(self):
        print "Connecting"
        if self.portOpened: self.close()
        # Loop through possible values of ACMX, and try to connect on each one
        for i in range(4):
            try:
                # Try to create the serial connection
                self.port=serial.Serial(port='/dev/ttyACM{0}'.format(i), baudrate=9600, timeout=0)
                if self.port.isOpen():
                    time.sleep(2) #Allows the arduino to initialize
                    self.port.flush()
                    print "Connected"
                    return True
            except:
                # Some debugging prints
                print "Arduino not connected on ACM{0}".format(i)
        print "Failed to connect"
        return False

    # This function constantly sends out a command packet to the arduino
    # (based on the states of all the arrays) then blocks until it receives
    # a data packet in response (and sets the appropriate arrays based on it).
    # Thus changing the actuator-related arrays and reading from the sensor-
    # related arrays is enough to interact with the arduino.
    def checkPorts(self):
        # If killReceived is set to true, we want to kill this thread
        while not self.killReceived:
            # Build the command packet
            # Command packet format:
            # An1234Bm5678;
            # A, B = Command modes (M - motor command, S - servo command, ...)
            #        Command modes tell the arduino how to interpret what comes
            #        after it.
            # n, m = Number of arguments. This tells the arduino how many
            #        arguments to look for and parse.
            # 1234, 5678 = Arguments. These depend on the command, but specify
            #        things like motor speed and servo angle. Note - in many
            #        places we add 1 before sending an argument and subtract
            #        1 on the other end. This is because we can't send the null
            #        character across.
            # ; = Special command mode that means "end of packet"
            output = ""
            output += "M" + chr(len(self.motorSpeeds) + 1)
            for i in self.motorSpeeds:
                output += chr(i+1)
            output += "T" + chr(len(self.stepperSteps) + 1)
            for i in range(len(self.stepperSteps)):
                dir, steps = self.stepperSteps[i]
                output += chr(dir+1)
                output += chr(steps+1)
                self.stepperSteps[i] = (0, 0)
            output += "S" + chr(len(self.servoAngles) + 1)
            for i in self.servoAngles:
                output += chr(i+1)
            output += ";"
            self.port.write(output)

            #print list(output)

            # Read in the data packet that the arduino sends back
            # Data packet format is identical to the command packet format,
            # except the modes are different (ex. 'D' for digital instead of
            # 'M' for motor)
            # Possible modes:
            #     'D' - Digital sensor data
            #     'A' - Analog sensor data
            done = False
            while (not done):
                # Read in the mode
                type = serialRead(self.port)

                # Process arguments based on mode
                # Digital
                if (type == 'D'):
                    length = ord(serialRead(self.port))-1
                    # Fill the digitalSensors array with incoming data
                    for i in range(length):
                        # If we read in a 2, then the bump sensor is hit,
                        # otherwise it's not
                        self.digitalSensors[i] = ord(serialRead(self.port))==2
                # Analog
                elif (type == 'A'):
                    length = ord(serialRead(self.port))-1
                    # Fill the analogSensors array with incoming data
                    for i in range(length):
                        byte0 = ord(serialRead(self.port))-1
                        byte1 = ord(serialRead(self.port))-1
                        self.analogSensors[i] = byte1 * 256 + byte0
                # End of packet
                elif (type == ';'):
                    done = True

    # Send initializing data to the arduino, so that it can dynamically set up
    # the actuators and sensors in memory
    def sendInitData(self):
        # The 'I' command mode means initializing data
        output = ""
        output += "I"
        # Motor component of initializing
        output += "M"
        numMCs = len(self.motorControllerPorts)
        output += chr(numMCs+1)
        for i in range(numMCs):
            a,b = self.motorControllerPorts[i]
            output += chr(a)
            output += chr(b)
        # Stepper component of initializing
        output += "T"
        numSteppers = len(self.stepperPorts)
        output += chr(numSteppers+1)
        for i in range(numSteppers):
            dirPin, stepPin = self.stepperPorts[i]
            output += chr(dirPin)
            output += chr(stepPin)
        # Servo component of initializing
        output += "S"
        numServos = len(self.servoPorts)
        output += chr(numServos+1)
        for i in range(numServos):
            output+= chr(self.servoPorts[i])
        # Digital component of initializing
        output += "D"
        numDigital = len(self.digitalPorts)
        output += chr(numDigital+1)
        for i in range(numDigital):
            output+= chr(self.digitalPorts[i])
        # Analog component of initializing
        output += "A"
        numAnalog = len(self.analogPorts)
        output += chr(numAnalog+1)
        for i in range(numAnalog):
            output += chr(self.analogPorts[i])
        # Terminate the command packet
        output += ";"

        self.port.write(output)

        print "Init", output
    
    # Getting and setting values for sensors and actuators
    def setMotorSpeed(self, motorNum, speed):
        self.motorSpeeds[motorNum] = speed
    def stepStepper(self, stepperNum, dir, steps):
        self.stepperSteps[stepperNum] = (dir, steps)
    def setServoAngle(self, servoNum, angle):
        self.servoAngles[servoNum] = angle
    def getDigitalRead(self, index):
        out = self.digitalSensors[index]
        return out
    def getAnalogRead(self, index):
        out = self.analogSensors[index]
        return out

    # Functions to set up the components (these are called through the classes
    # below, don't call these yourself!)
    def addMotor(self, mcObj):
        return mcObj.addMotor()
    def addStepper(self, dirPort, stepPort):
        self.stepperPorts.append((dirPort, stepPort))
        self.stepperSteps.append((0, 0))
        return len(self.stepperPorts) - 1
    def addDigitalPort(self, port):
        self.digitalPorts.append(port)
        self.digitalSensors.append(None)
        return len(self.digitalPorts) - 1
    def addAnalogPort(self, port):
        self.analogPorts.append(port)
        self.analogSensors.append(None)
        return len(self.analogPorts) - 1
    def addMC(self, txPin, rxPin):
        self.motorControllerPorts.append((rxPin, txPin))
        self.motorSpeeds.append(0)
        self.motorSpeeds.append(0)
        return len(self.motorControllerPorts) - 1
    def addServo(self, port):
        self.servoPorts.append(port)
        self.servoAngles.append(0)
        return len(self.servoPorts) - 1

# Read from the serial port ignoring junk (use this instead of just port.read())
def serialRead(port):
    inp = port.read()
    # Throw out no input (when python overtakes arduino)
    while inp == "": 
        inp = port.read()
    return inp

# Class to interact with a servo
class Servo:
    def __init__(self, arduino, port):
        self.arduino = arduino 
        self.index = self.arduino.addServo(port)
    def setAngle(self, angle):
        self.arduino.setServoAngle(self.index, angle)

# Class to interact with a motor
class Motor:
    def __init__(self, arduino, controller):
        self.arduino= arduino
        self.controller = controller
        self.index = self.arduino.addMotor(controller)
    def setVal(self, val):
        # Modify the -126 to 127 range to be 0 to 255 for the Arduino
        val = val % 255
        self.arduino.setMotorSpeed(self.index, val)

class Stepper:
    def __init__(self, arduino, dirPort, stepPort):
        self.arduino = arduino
        self.dirPort = dirPort
        self.stepPort = stepPort
        self.index = self.arduino.addStepper(dirPort, stepPort)
    def step(self, dir, steps):
        if not dir in [0,1]:
            dir = 0
        self.arduino.stepStepper(self.index, dir, steps)

# Class to interact with a digital sensor
class DigitalSensor:
    def __init__ (self, arduino, port):
        self.arduino = arduino
        self.port = port
        self.index = self.arduino.addDigitalPort(port)
    def getValue(self):
        return self.arduino.getDigitalRead(self.index)

# Class to interact with an analog sensor
class AnalogSensor:
    def __init__(self, arduino, port):
        self.arduino = arduino
        self.port = port
        self.index = self.arduino.addAnalogPort(port)
    def getValue(self):
        return self.arduino.getAnalogRead(self.index)

# Class to interact with a motor controller
class MotorController:
    def __init__(self, arduino, txPin, rxPin):
        self.arduino = arduino
        self.txPin = txPin
        self.rxPin = rxPin
        self.index = arduino.addMC(txPin, rxPin)
        self.numMotors = 0
    def getIndex(self):
        return self.index
    def addMotor(self):
        self.numMotors += 1
        return self.index * 2 + self.numMotors - 1

if __name__ == "__main__":
    ## Example setup for various sensors and actuators

    ## Set up the arduino itself (do this every time)
    a = Arduino()
    ## Setting up a motor controller (txPin = 18, rxPin = 19) and two motors
    ## on that motor controller
    mc0 = MotorController(a, 18, 19)
    m0 = Motor(a, mc0)
    m1 = Motor(a, mc0)
    mc1 = MotorController(a, 16, 17)
    m2 = Motor(a, mc1)
    m3 = Motor(a, mc1)
    #stepper = Stepper(a, 11, 12)

    a.run()

    import time
    while True:
        m2.setVal(-126)
        time.sleep(0.1)

## Setting up a digital sensor on digital port 2
#d = DigitalSensor(a, 2)
## Setting up a servo on digital port 1
#s = Servo(a, 1)
#analog = AnalogSensor(a, 2)
#a.run()

## Example code snippets for things to do with the various sensors and
## actuators

## Set motor speeds
#m0.setVal(-50)
#m1.setVal(-50)

## Read analog values
#while True:
#    time.sleep(0.1)
#    print analog.getValue()

## Set servo angles
#while True:
#    for i in range(100):
#        s.setAngle(i)
#        time.sleep(0.01)
#    for i in range(100, 0, -1):
#        s.setAngle(i)
#        time.sleep(0.01)

## Get digital sensor input
#    while val == None:
#        val = d.getValue()
#    print val
