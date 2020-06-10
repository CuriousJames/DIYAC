#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading
import os # useful for file operations
import json # for gettings settings and tokens
import logging # our own logging module
from inputHandler import inputHandler # our own input handling module
from outputHandler import outputHandler
from tokenHandler import tokenHandler # our ouwn token hangling module
from pinDef import pinDef # our own pin definition module
import signal # for nice exit
import sys # for nice exit


#
# file synopsis
#
# cleanup
# nice exit
# class: pinDef
#  vars
#  function: init(settings, logger) - get custom pin defs from settings
# function: init() - main script initialisation
# function: getSettings() - get settings from settings file
# class: token
#  vars
#  function: getAllowedTokens(settings)
#  function: formatTokens()
#  function: transformOverlengthTokens()
#  function: removeDuplicateTokens()
# funciton: openDoor()
# function: ringDoorbell()
# class: inputHandler
#  vars
#  function: init(settings)
#  function: newNumpadInput(rx)
#  function: checkToken(rx, rxType)
#  function: checkLockout()
#  function: addAttempt()
#  function: getBruteForceState()
#  function: calculateNewLockout()
#  function: wiegandCallback(bits, code)
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
        pi.stop()

        #log
        l.log("ERRR", "program shutdown")

atexit.register(cleanup)

#
# exit from sigint
#  allows for nice logging of exit by ctrl-c
def signal_handler(sig, frame):
        l.log("ERRR", "CTRL-C pressed, will exit")
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)



#
# initialisation
#
def init():

        # define some variables
        global pi
        pi = pigpio.pi()

        # get all the settings
        getSettings()


        # start logging
        global l
        l = logging.logger(settings)
        l.log("INFO", "DoorPi starting")

        # set tokens
        global tokens
        tokens = tokenHandler(settings, l)
        tokens.getAllowedTokens()

        # pin definitions
        global p
        p = pinDef(settings, l)

        # output handler
        global outH
        outH = outputHandler(settings, l, pi, p)

        # Input handler
        global inH
        inH = inputHandler(settings, l, tokens, outH)




        # get the token list
        #getAllowedTokens()


#
# function to get settings from file
def getSettings():
        # define global var settings = false
        # if settings file exists
        ## open/read+decode/close
        ## put into settings var
        ## if problem
        ### error handling
        #
        # if no settings file
        ## error handling

        # make settings var
        global settings
        settings = False

        if os.path.exists("settings.json"):
                # open
                try:
                        settingsFile = open("settings.json", "r")
                except OSError as err :
                        print("os error while opening settings file:")
                        print(err)
                except:
                        print("unknown error while opening settings file:")
                        print(err)
                        return

                # read + decode
                try:
                        settings = json.load(settingsFile)
                except ValueError as err :
                        print("JSON Decode error while reading settings file")
                        print(err)
                except:
                        print("unknown error while reading settings file")

                # close
                try:
                        settingsFile.close()
                except OSError as err :
                        print("os error while closing settings file:")
                        print(err)
                except:
                        print("unknown error while closing settings file")

        else:
                # error - no file found
                print("Critical Error - settings file not found - please create settings.json using the example provided")
                exit
                return
        return









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
                ringDoorbellThread=threading.Thread(target=ringDoorbell)
                ringDoorbellThread.start()


#
# Let's start doing things
#

# run initialisation
init()
l.log("INFO", "DoorPi running")

# register these GPIO pins to run cbf on rising or falling edge
cb1 = pi.callback(p.pins["doorStrike"], pigpio.EITHER_EDGE, cbf)
cb2 = pi.callback(p.pins["doorbell12"], pigpio.EITHER_EDGE, cbf)
cb3 = pi.callback(p.pins["doorbellButton"], pigpio.EITHER_EDGE, cbf)
cb4 = pi.callback(p.pins["doorSensor"], pigpio.EITHER_EDGE, cbf)

# set the wiegand reading
# will call function wiegandCallback on receiving data
w = wiegand.decoder(pi, p.pins["wiegand0"], p.pins["wiegand1"], inH.wiegandCallback)

while True:
        time.sleep(9999)
        #Just keeping the python fed (slithering)
        l.log("INFO", "boppity")
