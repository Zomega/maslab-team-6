from blargh import Blargh
import time

class BehaviorBlargh(Blargh):
    # States
    DODGE_WALL = 0
    GO_STRAIGHT = 1
    BACK_UP = 2
    TURN = 3

    # Constants
    BACKUP_TIME = 2
    TURN_TIME = 2

    def __init__(self, arduinoInterfaceOutputWrapper):
        self.curState = self.GO_STRAIGHT
        self.stateTimer = 0
        self.lastTime = 0
        self.aiow = arduinoInterfaceOutputWrapper

    def step(self, bumpSensorHit):
        print "BehaviorBlargh stepped"
        # Change states if the bump sensor is hit
        if (bumpSensorHit):
            print ("BUMP SENSORUUUUUUUUUU")
            self.stateTimer = 0
            if (self.curState == self.GO_STRAIGHT):
                self.curState = self.DODGE_WALL

        # Operate based on state
        if (self.curState == self.GO_STRAIGHT):
            self.aiow.setMotorSpeed(0, 50)
            self.aiow.setMotorSpeed(1, 50)
        elif (self.curState == self.DODGE_WALL):
            self.curState = self.BACK_UP
        elif(self.curState == self.BACK_UP):
           if(self.lastTime == 0):
               self.stateTimer = 0
               self.lastTime = time.time()
           elif(self.stateTimer < self.BACKUP_TIME):
               self.stateTimer += time.time() - self.lastTime
               self.lastTime = time.time()
               self.aiow.setMotorSpeed(0, -50)
               self.aiow.setMotorSpeed(1, -50)
           else:
               self.stateTimer = 0
               self.lastTime = 0
               self.curState = self.TURN
        elif(self.curState == self.TURN):
            if(self.lastTime == 0):
                self.stateTimer = 0
                self.lastTime = time.time()
            elif(self.stateTimer < self.TURN_TIME):
                self.stateTimer += time.time() - self.lastTime
                self.lastTime = time.time()
                self.aiow.setMotorSpeed(0, -50)
                self.aiow.setMotorSpeed(1, 50)
            else:
                self.stateTimer = 0
                self.lasTime = 0
                self.curState = self.GO_STRAIGHT
