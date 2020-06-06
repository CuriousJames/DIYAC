#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading
import os # useful for file operations
import json # for gettings settings and tokens
import logging # our own logging module

#
# cleanup
# makes things clean at exit

def cleanup():
        # This next bit doesn't work - we're looking into how to make it work so the door isn't left open if the script exits prematurely
        #pi.write(p.pins["doorStrike"],0)

        pi.stop()
        l.log("ERRR", "program shutdown")

atexit.register(cleanup)

#
# define some variables
#

pi = pigpio.pi()

doorRinging=False
doorbellCount=0

#
# GPIO Variables so we don't have to remember pin numbers!
#
class pinDef :

        #
        # default pins
        #  these are the ones used by the hat
        #
        pins = {
                "doorStrike": 17,
                "doorbell12": 4,
                "doorbellCc": 26,
                "readerLed": 27,
                "readerBuzz": 22,
                "doorbellButton": 5,
                "doorSensor": 6,
                "piActiveLed": 13,
                "spareLed": 19,
                "wiegand0": 14,
                "wiegand1": 15
        }

        #
        # function to get pins from settings
        #  if settings[pinDef] does not exist
        #   return
        #  iterate through settings[pinDef]
        #   check it's in the list of pins
        #   check value is an integer in the correct range
        #   update var
        #
        def __init__(self, settings, logger) :

                # see if anything even exists in settings
                try :
                        settings["pinDef"]
                except :
                        logger.log("DBUG", "No new pin definitions from settings")
                        return

                # iterate settigns[pinDef]
                for p in settings["pinDef"] :
                        # see if it's one of the pinDefs we already have
                        if p in self.pins :
                                # validate
                                #  >=2, <=27
                                if settings["pinDef"][p] >= 2 and settings["pinDef"][p] <= 27 :
                                        # update pin definition
                                        l.log("DBUG", "New pin defined by settings", {"name": p, "pin": settings["pinDef"][p]})
                                        self.pins[p] = settings["pinDef"][p]



#
# initialisation
#
def init():

        # get all the settings and allowed tokens
        getSettings()

        # start logging
        global l
        l = logging.logger(settings)
        l.log("INFO", "DoorPi starting")

        # pin definitions
        global p
        p = pinDef(settings, l)

        # Ensure GPOs are initialised as expected
        try :
                pi.write(p.pins["doorStrike"],0)
                pi.write(p.pins["doorbell12"],0)
                pi.write(p.pins["doorbellCc"],0)
                pi.write(p.pins["readerLed"],1)
                pi.write(p.pins["readerBuzz"],1)
        except :
                l.log("ERRR", "There was an issue setting output pins")

        # get the token list
        getAllowedTokens()


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
# function to make var of allowed tokens
#  reads file
#  changes all hex values to lower case without ":"
#  changes mifare ultralight tokens to what will be received by reader - not implemented yet
#
def getAllowedTokens():
        # define global var allowedTokens = false
        #
        # if no settings
        ## exit function
        #
        # set file path
        #
        # if tokens file exists
        ## open/read+decode/close
        ## set allowedTokens
        ## if problem
        ### error handling
        ### return
        #
        # if no tokens file
        ## error handling
        ## return
        #
        # remove ":" from all tokens
        # make all tokens lower case

        # make allowedTokens var
        global allowedTokens
        allowedTokens = False

        # if settings haven't worked, return
        if settings == False:
                l.log("WARN", "no settings - will not get allowedTokens")
                return

        # make filepath
        allowedTokensFilePath = settings["root"] + settings["allowedTokens"]["path"]

        if os.path.exists(allowedTokensFilePath) :
                # open
                try:
                        allowedTokensFile = open(allowedTokensFilePath, "r")
                except OSError as err :
                        l.log("WARN", "os error while opening allowedTokens file", err)
                except:
                        l.log("WARN", "unknown error while opening allowedTokens file")
                        return

                # read + decode
                try:
                        allowedTokens = json.load(allowedTokensFile)
                except ValueError as err :
                        l.log("WARN", "JSON Decode error while reading allowedTokens file", err)
                except:
                        l.log("WARN", "unknown error while reading/decoding allowedTokens file")

                # close
                try:
                        allowedTokensFile.close()
                except OSError as err :
                        l.log("WARN", "os error while closing allowedTokens file:", err)
                except:
                        l.log("WARN", "unknown error while closing allowedTokens file")

        else:
                l.log("WARN", "allowedTokens file does not exist")
                return

        # remove ":" and make lowercase
        for token in allowedTokens:
                token["value"] = token["value"].replace(":", "")
                token["value"] = token["value"].lower()

        # Perform transform for mifare ultralight
        for token in allowedTokens:
                ##
                ## do some transforming here
                ## Wiegand readers ONLY read the first 3 bytes from cards with more than 4 bytes of ID
                ## So we need to transform the ID to what the reader is capable of reading (and how it reads it - it reads '88' and then the first 3 bytes)
                if len(token["value"]) >8:
                        token["value"] = "88" + token["value"][:6]

        # print allowedTokens
        l.log("DBUG", "allowedTokens", allowedTokens)

        return

def openDoor():
        l.log("INFO", "Opening Door")
        pi.write(p.pins["readerLed"],0)
        pi.write(p.pins["doorStrike"],1)
        time.sleep(4)
        #Now let's warn that the door is about to close by flashing the Reader's LED
        l.log("DBUG", "Door Closing soon")
        i = 5
        while i < 5:
                pi.write(p.pins["readerLed"],1)
                time.sleep(0.1)
                pi.write(p.pins["readerLed"],0)
                time.sleep(0.1)
                i += 1
        pi.write(p.pins["readerLed"],1)
        pi.write(p.pins["doorStrike"],0)
        l.log("INFO", "Door Closed")

def ringDoorbell():
        global doorRinging
        global doorbellCount
        doorbellCount+=1
        l.log("DBUG", "******* Bell Count *******", doorbellCount)

        if doorRinging == False:
                doorRinging=True
                l.log("INFO", "Start Doorbell")
                pi.write(p.pins["doorbell12"],1)
                time.sleep(2)
                pi.write(p.pins["doorbell12"],0)

                time.sleep(0.1)

                pi.write(p.pins["doorbell12"],1)
                time.sleep(0.2)
                pi.write(p.pins["doorbell12"],0)

                time.sleep(0.1)

                pi.write(p.pins["doorbell12"],1)
                time.sleep(0.2)
                pi.write(p.pins["doorbell12"],0)

                doorRinging=False
                l.log("INFO", "Stop Doorbell")
        else:
                l.log("INFO", "NOT Ringing doorbell - it's already ringing")

def wiegandCallback(bits, code):
        # if bits != 4 AND bits != 34
        ## error
        #
        # if bits == 34, it's a card token
        ## convert to binary string
        ## trim "0b", start parity bit, end parity bit
        ## re order bytes
        ## convert to hex
        ## compare against list
        #
        # if bits == 4
        ## if code = 0
        ### ring doorbell
        ## else
        ### do something else

        #
        # log
        l.log("DBUG", "New read", {"bits":bits, "code":code})

        #
        # we have a card
        if bits == 34:
                # make input into a hex string
                #
                input = str(format(code, '#036b')) # make binary string
                input = input[3:]  # trim '0b' and first parity bit
                input = input[:-1] # trim last parity bit
                output = input[24:] + input[16:24] + input[8:16] + input[:8] # re-order bytes
                output = int(output, 2) # change to integer - required for doing the change to hex
                output = format(output, '#010x') # make hex string
                output = output[2:] # trim "0x"
                l.log("DEBUG", "output from formatting", output)

                # see if the card is in allowed tokens
                #
                match = False
                for token in allowedTokens:
                        # for generic cards - no changing necessary
                        if token["type"] != "code":
                                if token["value"] == output:
                                        # open the door
                                        match = True
                                        l.log("INFO", "token allowed (generic card)", output)
                # if it wasn't a match
                if match == False :
                        l.log("INFO", "token not allowed", output)
        elif bits == 4:
                # someone pressed a button
                # We don't handle these yet - but for debugging let's print out what button they pressed!
                if code == 10:
                        key="*"
                elif code == 11:
                        key="#"
                else:
                        key=code
                l.log("DBUG", "Keypad key pressed", key)
        else:
                #
                # error condition
                l.log("WARN", "unexpected number of bits", bits)
                return

def cbf(gpio, level, tick):
        l.log("DBUG", "GPIO Change", [gpio, level])
        if gpio == p.pins["doorbellButton"] and level == 0:
                ringDoorbellThread=threading.Thread(target=ringDoorbell)
                ringDoorbellThread.start()


#
# Let's start doing things
#

# run initialisation
init()
l.log("INFO", "DoorPi running")

# this comment will give a nice hint about what the next 4 lines do
cb1 = pi.callback(p.pins["doorStrike"], pigpio.EITHER_EDGE, cbf)
cb2 = pi.callback(p.pins["doorbell12"], pigpio.EITHER_EDGE, cbf)
cb3 = pi.callback(p.pins["doorbellButton"], pigpio.EITHER_EDGE, cbf)
cb4 = pi.callback(p.pins["doorSensor"], pigpio.EITHER_EDGE, cbf)

# set the wiegand reading
# will call function wiegandCallback on receiving data
w = wiegand.decoder(pi, p.pins["wiegand0"], p.pins["wiegand1"], wiegandCallback)

while True:
        time.sleep(9999)
        #Just keeping the python fed (slithering)
        l.log("INFO", "boppity")
