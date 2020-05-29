#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading
import json
import os

#
# cleanup
#  makes things clean at exit

def cleanup():
	# This next bit doesn't work - we're looking into how to make it work so the door isn't left open if the script exits prematurely
	#pi.write(doorStrike,0)

	pi.stop()
	print("cleanly shutdown")

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
	# Ensure GPOs are initialised as expected
	pi.write(doorStrike,0)
	pi.write(doorbell12,0)
	pi.write(doorbellCc,0)
	pi.write(readerLed,1)
	pi.write(readerBuzz,1)

        # get all the settings and allowed tokens
        getSettings()
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
                print("settings file not found")
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
                print("no settings - will not get allowedTokens")
                return

        # make filepath
        allowedTokensFilePath = settings["root"] + settings["allowedTokens"]["path"]

        if os.path.exists(allowedTokensFilePath) :
                # open
                try:
                        allowedTokensFile = open(allowedTokensFilePath, "r")
                except OSError as err :
                        print("os error while opening allowedTokens file:")
                        print(err)
                except:
                        print("unknown error while opening allowedTokens file:")
                        return

                # read + decode
                try:
                        allowedTokens = json.load(allowedTokensFile)
                except ValueError as err :
                        print("JSON Decode error while reading allowedTokens file")
                        print(err)
                except:
                        print("unknown error while reading allowedTokens file")

                # close
                try:
                        allowedTokensFile.close()
                except OSError as err :
                        print("os error while closing allowedTokens file:")
                        print(err)
                except:
                        print("unknown error while closing allowedTokens file")

        else:
                print("allowedTokens file does not exist")
                return

        # remove ":" and make lowercase
        for token in allowedTokens:
                token["value"] = token["value"].replace(":", "");
                token["value"] = token["value"].lower()

        # Perform transform for mifare ultralight
        for token in allowedTokens:
                ##
                ## do some transforming here
                pass
                ##

        # print allowedTokens
        print(allowedTokens)

        return

#
# function to make log ready
#  will not enable logging if:
#   no settings
#   settings for logging is not enabled
#   file path is not spefifed
#   theres an error getting to the file
#
# incomplete
#
def logSetup() :
        # set global var logging = false
        # if no settings
        ## return
        # if settings[log][enabled] == false
        ## return
        # if settings[log][path] not specified
        ## return
        # if file path does not start with "/"
        ## make file path be root+path
        # if file does not exist
        ## make file
        # open file and close file
        # if error on open/close
        ## return
        # set logging = true
        # if settings[log][level] not set
        ## set to error

        # if no settings
        if settings == False :
                print("no settings - will not log")
                return

        # if logging-enabled does not exist or is false
        try:
                settings["logging"]["enabled"]
        except NameError:
                settings["logging"]["enabled"] == False
        if settings["logging"]["enabled"] == False :
                return

        # if logging-path is not set, do not log to file
        try:
                settings["logging"]["path"]
        except NameError:
                settings["logging"]["level"]["file"] = "NONE"

        # this whoel bit only happens if file logging is not none
        #  set proper file path
        #  test if file exists
        #  make sure read/write/close is possible
        if settings["logging"]["level"]["file"] != "NONE" :

                # set path so it's absolute
                if settings["logging"]["path"][0] != "/" :
                        settings["logging"]["path"] = settings["root"]+settings["logging"]["path"]

                # see if file exists
                if os.path.exists(settings["logging"]["path"]) :
                        pass
                else:
                        print("log file does not exist, will try to make one in a moment")

                # try to open then close the file
                openCloseError = False
                try:
                        f = open(settings["logging"]["path"], "w+")
                except:
                        print("unable to create log file - will not perform logging to file")
                        settings["logging"]["level"]["file"] = "NONE"
                        openCloseError = True

                if openCloseError == False :
                        try :
                                f.close()
                        except:
                                print("unable to close log file - will not perform logging to file")
                                settings["logging"]["level"]["file"] = "NONE"
                                openCloseError = True




#
# function to put a message into the log file
#  only does anything if log file is setup and ready
def log(lvl, msg) :
        # log levels
        #  FATL - 0
        #  EROR - 1
        #  WARN - 2
        #  INFO - 3
        #  DBUG - 4
        pass


def openDoor():
	print("Opening Door")
	pi.write(readerLed,0)
	pi.write(doorStrike,1)
	time.sleep(4)
	#Now let's warn that the door is about to close by flashing the Reader's LED
	print("Door Closing soon")
	i = 5
	while i < 5:
		pi.write(readerLed,1)
		time.sleep(0.1)
		pi.write(readerLed,0)
		time.sleep(0.1)
		i += 1
	pi.write(readerLed,1)
	pi.write(doorStrike,0)
	print("Door Closed")

def ringDoorbell():
	global doorRinging
	global doorbellCount
	doorbellCount+=1
	print("******* Bell Count:",doorbellCount,"*******")

	if doorRinging == False:
		doorRinging=True
		print("Ringing Doorbell")
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
		print("Stopping Doorbell")
	else:
		print("NOT Ringing doorbell - it's already ringing")

def wiegandCallback(bits, code):
	print("bits={} code={}".format(bits, code))

        #
        # New stuff
        ## if bits != 4 AND bits != 34
        ### error
        #
        ## if bits == 34, it's a card token
        ### convert to binary string
        ### trim "0b", start parity bit, end parity bit
        ### re order bytes
        ### convert to hex
        ### compare against list
        #
        ## if bits == 4
        ### if code = 0
        #### ring doorbell
        ### else
        #### do something else


        ##
        ## error condition
        if bits != 34 and bits != 4:
                print("error - unexpected number of bits")
                return

        ##
        ## we have a card
        if bits == 34:

                ## make input into a hex string
                ##
                input = str(format(code, '#036b')) # make binary string
                input = input[3:]  # trim '0b' and first parity bit
                input = input[:-1] # trim last parity bit
                # print(input)
                output = input[24:] + input[16:24] + input[8:16] + input[:8] # re-order bytes
                output = int(output, 2) # change to integer - required for doing the change to hex
                output = format(output, '#010x') # make hex string
                output = output[2:] # trim "0x"
                print(output)

                ## see if the card is in allowed tokens
                ##
                match = False
                for token in allowedTokens:

                        ## for generic cards - no changing necessary
                        if token["type"] != "code":
                                if token["value"] == output:
                                        # open the door
                                        match = True
                                        print("ITS A FUCKING MATCH, OPEN THE DOOR (generic card)")

                ## if it wasn't a match
                if match == False :
                        print("That token was not a match with any cards in the allowedTokens file")

                ## log
                ##  but logging isn't implementd yet
                if settings != False :
                        pass

        ##
        ## someone pressed a button
        if bits == 4:
		## someone pressed a button
		# We don't handle these yet - but for debugging let's print out what button they pressed!
		if code == 10:
			key="*"
		elif code == 11:
			key="#"
		else:
			key=code
		print("Keypad key pressed:",key)


def cbf(gpio, level, tick):
	print(gpio, level, tick)
	if gpio == doorbellButton and level == 0:
		ringDoorbellThread=threading.Thread(target=ringDoorbell)
		ringDoorbellThread.start()



##
## Let's start doing things
##

# run initialisation
init()
print("running")

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
	print("boppity")
