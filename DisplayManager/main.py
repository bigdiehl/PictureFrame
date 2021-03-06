#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 25 21:42:05 2021

@author: diehl
"""

import logging
import threading
import time
import os, sys
import config

from viewer import ViewerPi3D
from manager import Manager

import logging
from sensors import LightSensor

def check_keyboard(kbd):
    """Check for and respond to keyboard events. Used primarily 
    for debugging"""
    if kbd is not None:
        k = kbd.read()
        if k != -1:
            nexttm = time.time() - 86400.0
        if k==27: #ESC
            raise KeyboardInterrupt
        if k==ord(' '):
            pass #paused = not paused
        if k==ord('s'): # go back a picture
            pass #next_pic_num -= 2
        #if next_pic_num < -1:
                #next_pic_num = -1

if __name__ == "__main__":
    
    try:
        config.PIC_DIRS = []

        # Parse config file and extract parameters
        config_file = 'picframe.config'
        with open(config_file) as f:
            for line in f.readlines():
                line = line.strip()
                if len(line) > 0 and line[0] != '#':
                    key,value = line.split("=")
                    if key == 'PIC_DIRS':
                        config.PIC_DIRS = [x for x in value.split(';') if len(x) > 0]
                        
                        
        print("PIC DIRS = ", config.PIC_DIRS)

        # Set up logging - Basic format to console and more detailed format to file
        log_path = r'picframe.log'
        if os.path.exists(log_path):
            os.remove(log_path)
            
        rootLogger = logging.getLogger()
        rootLogger.setLevel(logging.INFO)

        consoleLogFormatter = logging.Formatter("[%(levelname)-5.5s]  %(message)s")
        consoleHandler = logging.StreamHandler()
        consoleHandler.setFormatter(consoleLogFormatter)
        rootLogger.addHandler(consoleHandler)

        fileLogFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        fileHandler = logging.FileHandler(log_path)
        fileHandler.setFormatter(fileLogFormatter)
        rootLogger.addHandler(fileHandler)
        

        logging.info("Main start...")
        
        manager = Manager()
        manager_thread = threading.Thread(target=manager.run)
        manager_thread.start()

        sensor = LightSensor()
        sensor_thread = threading.Thread(target=sensor.run)
        sensor_thread.start()

        viewer = ViewerPi3D(manager)
        
        # For debugging
        #kbd = None
        #if config.KEYBOARD:
        #    kbd = pi3d.Keyboard()

        # Stay open while other threads do work
        #while True:
        #    time.sleep(0.1)
        #    check_keyboard(kbd)
        
        # Viewer must be main thread for pi3D to use openGL 
        viewer.run()

    except KeyboardInterrupt:
        print("Exiting...")
        #kbd.close()

        viewer.alive = False
        manager.alive = False
        sensor.alive = False
        
        manager_thread.join()
        sensor_thread.join()
        

    """Features:
    * Can select which pictures you want from web interface
        - By folder
        - By date range
    * Can control picture flow (play, pause, next, etc)
    * Can control viewer options (delay, transisiton time, randomizer, etc)


    Manager maintains a database of files/playlists. Using this database, we
    can select which pictures we want, filter pics, etcs

    * Show text when paused
    """
       
        
    
    
    
