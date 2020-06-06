#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading
import os # useful for file operations
import json # for gettings settings and tokens
import logging #our own logging class

#
# cleanup
# makes things clean at exit

def cleanup():
	# This next bit doesn't work - we're looking into how to make it work so the door isn't left open if the script exits prematurely
	#pi.write(doorStrike,0)

	pi.stop()
	logger.write("ERRR", "program shutdown")

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
doorStrike=17
doorbell12=4
doorbellCc=26
readerLed=27
readerBuzz=22
doorbellButton=5
doorSensor=6
piActiveLed=13
spareLed=19
wiegand0=14
wiegand1=15

#
# initialisation
#
def init():

        # get all the settings and allowed tokens
        getSettings()

        # start logging
        global logger
        logger = logging(settings)
        logger.write("INFO", "DoorPi starting")

        # Ensure GPOs are initialised as expected
        try :
	        pi.write(doorStrike,0)
	        pi.write(doorbell12,0)
	        pi.write(doorbellCc,0)
	        pi.write(readerLed,1)
	        pi.write(readerBuzz,1)
        except :
                logger.write("ERRR", "There was an issue setting output pins")

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
                logger.write("WARN", "no settings - will not get allowedTokens")
                return

        # make filepath
        allowedTokensFilePath = settings["root"] + settings["allowedTokens"]["path"]

        if os.path.exists(allowedTokensFilePath) :
                # open
                try:
                        allowedTokensFile = open(allowedTokensFilePath, "r")
                except OSError as err :
                        logger.write("WARN", "os error while opening allowedTokens file", err)
                except:
                        logger.write("WARN", "unknown error while opening allowedTokens file")
                        return

                # read + decode
                try:
                        allowedTokens = json.load(allowedTokensFile)
                except ValueError as err :
                        logger.write("WARN", "JSON Decode error while reading allowedTokens file", err)
                except:
                        logger.write("WARN", "unknown error while reading/decoding allowedTokens file")

                # close
                try:
                        allowedTokensFile.close()
                except OSError as err :
                        logger.write("WARN", "os error while closing allowedTokens file:", err)
                except:
                        logger.write("WARN", "unknown error while closing allowedTokens file")

        else:
                logger.write("WARN", "allowedTokens file does not exist")
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
        logger.write("DBUG", "allowedTokens", allowedTokens)

        return

def openDoor():
	logger.write("INFO", "Opening Door")
	pi.write(readerLed,0)
	pi.write(doorStrike,1)
	time.sleep(4)
	#Now let's warn that the door is about to close by flashing the Reader's LED
	logger.write("DBUG", "Door Closing soon")
	i = 5
	while i < 5:
		pi.write(readerLed,1)
		time.sleep(0.1)
		pi.write(readerLed,0)
		time.sleep(0.1)
		i += 1
	pi.write(readerLed,1)
	pi.write(doorStrike,0)
	logger.write("INFO", "Door Closed")

def ringDoorbell():
	global doorRinging
	global doorbellCount
	doorbellCount+=1
	logger.write("DBUG", "******* Bell Count *******", doorbellCount)

	if doorRinging == False:
		doorRinging=True
		logger.write("INFO", "Start Doorbell")
		pi.write(doorbell12,1)
		time.sleep(2)
		pi.write(doorbell12,0)

		time.sleep(0.1)

		pi.write(doorbell12,1)
		time.sleep(0.2)
		pi.write(doorbell12,0)

		time.sleep(0.1)

		pi.write(doorbell12,1)
		time.sleep(0.2)
		pi.write(doorbell12,0)

		doorRinging=False
		logger.write("INFO", "Stop Doorbell")
	else:
		logger.write("INFO", "NOT Ringing doorbell - it's already ringing")

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
        logger.write("DBUG", "New read", {"bits":bits, "code":code})

        #
        # error condition
        if bits != 34 and bits != 4:
                logger.write("WARN", "unexpected number of bits", bits)
                return

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
                logger.write("DEBUG", "output from formatting", output)

                # see if the card is in allowed tokens
                #
                match = False
                for token in allowedTokens:

                        # for generic cards - no changing necessary
                        if token["type"] != "code":
                                if token["value"] == output:
                                        # open the door
                                        match = True
                                        logger.write("INFO", "token allowed (generic card)", output)

                # if it wasn't a match
                if match == False :
                        logger.write("INFO", "token not allowed", output)

        #
        # someone pressed a button
        if bits == 4:
		# someone pressed a button
		# We don't handle these yet - but for debugging let's print out what button they pressed!
		if code == 10:
			key="*"
		elif code == 11:
			key="#"
		else:
			key=code
		logger.write("DBUG", "Keypad key pressed", key)


def cbf(gpio, level, tick):
	logger.write("DBUG", "GPIO Change", [gpio, level])
	if gpio == doorbellButton and level == 0:
		ringDoorbellThread=threading.Thread(target=ringDoorbell)
		ringDoorbellThread.start()


#
# Let's start doing things
#

# run initialisation
init()
logger.write("INFO", "DoorPi running")

# this comment will give a nice hint about what the next 4 lines do
cb1 = pi.callback(doorStrike, pigpio.EITHER_EDGE, cbf)
cb2 = pi.callback(doorbell12, pigpio.EITHER_EDGE, cbf)
cb3 = pi.callback(doorbellButton, pigpio.EITHER_EDGE, cbf)
cb4 = pi.callback(doorSensor, pigpio.EITHER_EDGE, cbf)

# set the wiegand reading
# will call function wiegandCallback on receiving data
w = wiegand.decoder(pi, wiegand0, wiegand1, wiegandCallback)

while True:
	time.sleep(9999)
	#Just keeping the python fed (slithering)
	logger.write("INFO", "boppity")
