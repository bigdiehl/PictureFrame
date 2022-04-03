
import time
import subprocess
from spidev import SpiDev
import config
import viewer
import os

class MCP3008:
    """Class to interface with the MCP3008 chip via SPI interface"""
    def __init__(self, bus = 0, device = 0):
        self.bus, self.device = bus, device
        self.spi = SpiDev()
        self.open()
        self.spi.max_speed_hz = 1000000 # 1MHz

    def open(self):
        self.spi.open(self.bus, self.device)
        self.spi.max_speed_hz = 1000000 # 1MHz

    def read(self, channel = 0):
        adc = self.spi.xfer2([1, (8 + channel) << 4, 0])
        data = ((adc[1] & 3) << 8) + adc[2]
        return data

    def close(self):
        self.spi.close()



class LightSensor():
    # Class Constants
    THRESHOLD = 100
    MAX_COUNT = 10
    SAMPLE_PERIOD = 1 # sec

    def __init__(self, manager, viewer):
        self.alive = True
        self.adc = MCP3008()
        self.manager = manager
        self.viewer = viewer
        
        # Get initial reading to set initial state
        reading = self.adc.read(channel=0)
        if reading < self.THRESHOLD:
            self.asleep = True
            self.go_to_sleep()
        else:
            self.asleep = False
    
    def run(self):
        """Main logic for light sensor. Change state if light levels above/below
        a specified threshold for MAX_COUNT samples. If state change occurs, then
        signal other threads to sleep/wakeup"""
        count = 0        
        
        # TODO - add some error handling...
        
        while self.alive:
            time.sleep(self.SAMPLE_PERIOD)
            reading = self.adc.read(channel=0)
            #print("Reading is...", reading)
            if self.asleep:
                if reading > self.THRESHOLD:
                    count +=1
                else:
                    count = 0
                    
                if count > self.MAX_COUNT:
                    self.asleep = False
                    self.wake_up()
                    count = 0
            else:
                if reading < self.THRESHOLD:
                    count +=1
                else:
                    count = 0
                    
                if count > self.MAX_COUNT:
                    self.asleep = True
                    self.go_to_sleep()
                    count = 0
            
    def kill(self):
        self.alive = False
        
    # TODO - Need to clean this up. Don't like that we are accessing shared resources without a lock
    def go_to_sleep(self):
        #lock.acquire()
        self.manager.enqueue_pic("/home/pi/PictureFrame/DisplayManager/black.png")
        viewer.viewer_signal = viewer.view_signal.TRANSITION_NOW
        time.sleep(0.5)
        self.viewer.go_to_sleep()
        #lock.release()
        #subprocess.check_call('xset -display :0.0 dpms force off', shell=True) # TODO - what to do if this fails?
        print("Going to sleep...")
        
    def wake_up(self):
        viewer.viewer_signal = viewer.view_signal.TRANSITION_NOW
        time.sleep(0.5)
        self.viewer.wake_up()
        #subprocess.check_call('xset -display :0.0 dpms force on', shell=True) # TODO - what to do if this fails?
        print("Waking up...")
        
