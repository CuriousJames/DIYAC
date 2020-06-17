#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading
import os # useful for file operations
import json # for gettings settings and tokens
import logging # our own logging module
import inputHandler # our own input handling module
import outputHandler
import tokenHandler # our ouwn token hangling module
from settingsHandler import settingsHandler
import pinDef # our own pin definition module
import signal # for nice exit
import sys # for nice exit
import subprocess


#
# file synopsis
#
# cleanup
# nice exit
# function: init() - main script initialisation
#  settings
#  logger
#  gpio
#  tokens
#  pins
#  out
#  in
#  bind gpio callbacks
#  start iwegand
# function: keepalive()
# function: cbf(gpio, level, tick)
# some code to actually run the program


#
# cleanup
# makes things clean at exit
#
def cleanup():
    # This next bit doesn't work - we're looking into how to make it work so the door isn't left open if the script exits prematurely
    #pi.write(p.pins["doorStrike"],0)

    # release gpio resources
    try :
        pi.stop()
    except :
        pass

    #log
    l.log("ERRR", "program shutdown")


#
# exit from sigint
#  allows for nice logging of exit by ctrl-c
def signal_handler(sig, frame):
    l.log("ERRR", "CTRL-C pressed, will exit")
    sys.exit(0)


#
# initialisation
#
def init():
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, signal_handler)
    # get all the settings
    s = settingsHandler()

    # start logging
    global l
    l = logging.logger(s)
    l.log("INFO", "DoorPi starting")

    # see if pigpiod is running
    # if not running
    #  try to start
    #  check again
    #  if not running
    #   exit
    # pigpiod.pi()
    # if not connected
    #  exit
    stat = subprocess.call("systemctl status pigpiod > /dev/null", shell=True)
    if stat != 0 :
        l.log("WARN", "PIGPIOD is not running, will try to start")
        subprocess.call("sudo systemctl start pigpiod > /dev/null", shell=True)
        stat = subprocess.call("service pigpiod status > /dev/null", shell=True)
        if stat != 0 :
            l.log("ERRR", "Unable to start pigpiod daemon")
            sys.exit()
        else :
            l.log("INFO", "Starting pigpiod daemon successful")
    global pi
    pi = pigpio.pi()
    if not pi.connected:
        l.log("ERRR","PiGPIO - Unable to connect")
        exit()

    # set tokens
    global tokens
    tokens = tokenHandler.tokenHandler(s, l)

    # pin definitions
    global p
    p = pinDef.pinDef(s, l)

    # output handler (settings, logger, gpio, pins
    global outH
    outH = outputHandler.outputHandler(s, l, pi, p)

    # Input handler
    global inH
    inH = inputHandler.inputHandler(s, l, tokens, outH)

    # register these GPIO pins to run cbf on rising or falling edge
    global cb1,cb2,cb3,cb4
    cb1 = pi.callback(p.pins["doorStrike"], pigpio.EITHER_EDGE, cbf)
    cb2 = pi.callback(p.pins["doorbell12"], pigpio.EITHER_EDGE, cbf)
    cb3 = pi.callback(p.pins["doorbellButton"], pigpio.EITHER_EDGE, cbf)
    cb4 = pi.callback(p.pins["doorSensor"], pigpio.EITHER_EDGE, cbf)

    # set the wiegand reading
    # will call function wiegandCallback on receiving data
    global w
    w = wiegand.decoder(pi, p.pins["wiegand0"], p.pins["wiegand1"], inH.wiegandCallback)

    l.log("INFO", "DoorPi running")


def keepAlive():
    while True:
        time.sleep(9999)
        #Just keeping the python fed (slithering)
        l.log("INFO", "boppity")



#
# callback function that is hit whenever the GPIO changes
def cbf(gpio, level, tick):
    # log
    # see if we know which pin it is
    logData = {"gpio": gpio, "level": level}
    for pin in p.pins :
        if p.pins[pin] == gpio :
            logData["name"] = pin
    l.log("DBUG", "GPIO Change", logData)

    # if it's the doorbell button, ring the doorbell
    if gpio == p.pins["doorbellButton"] and level == 0:
        ringDoorbellThread=threading.Thread(target=outH.ringDoorbell)
        ringDoorbellThread.start()


#
# Let's start doing things
#

# run initialisation
init()

# Keep the program running to wait for callbacks
keepAlive()
