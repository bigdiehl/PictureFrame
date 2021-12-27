
import time

class LightSensor():
    def __init__(self):
        self.alive = True
    
    def run(self):
        while self.alive:
            time.sleep(1)
            
    def kill(self):
        self.alive = False
        
