#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jan 25 21:42:05 2021

@author: diehl
"""

import logging
import threading
import time
import os, sys
import logging
import signal

import config
from manager import Manager
from sensors import LightSensor
from viewer import TkinterViewer  

if __name__ == "__main__":

    # Set up logging - Basic format to console and more detailed format to file
    log_path = config.LOG_PATH
    log_path = os.path.abspath(log_path)
    if os.path.exists(log_path):
        os.remove(log_path)
        
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)

    # Logging to stdout
    consoleLogFormatter = logging.Formatter("[%(levelname)-5.5s]  %(message)s")
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(consoleLogFormatter)
    rootLogger.addHandler(consoleHandler)

    # logging to file
    fileLogFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    fileHandler = logging.FileHandler(log_path)
    fileHandler.setFormatter(fileLogFormatter)
    rootLogger.addHandler(fileHandler)
        
    try:
        logging.info("Main start...")
        
        #lock = threading.Lock()
        
        manager = Manager()
        manager_thread = threading.Thread(target=manager.run)
        manager_thread.start()

        if config.LIGHT_SENSOR:
            sensor = LightSensor(manager, viewer)
            sensor_thread = threading.Thread(target=sensor.run)
            sensor_thread.start()

        # Run viewer in the main thread
        viewer = TkinterViewer(manager)
        viewer.run()

    except KeyboardInterrupt:
        print("Exiting...")

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
       
        
    
    
    
