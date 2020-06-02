#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading
import os # useful for file operations
import json # for gettings settings and tokens
import datetime # used for logging

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
        logger = logging()
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

#
# log
#
#
# Description:
#  this makes the logging happen
#
# Level description - when selected as display or file write level all below levels are logged in addition to the selected level
#  DBUG - everthing that's happening
#  INFO - program events, token events, door events
#  WARN - anything wrong but non-fatal
#  ERRR - fatal events
#  NONE - absolutely nothing (after logging is initialised)
#
#
# Variables:
#  filePath
#  fileLevel
#  displayLevel
#  levelTable
#
#
# Functions:
#
#  __init__()
#   gets info from settings
#   puts relevent info into vars
#
#  write(lvl, msg, [data])
#   write message to outputs
#   only if level is above what is set in settings
#   if no settings found, will log ALL to display
#

class logging :

        def __init__(self) :
                # get information out of settings
                # create some useful vars

                # globalise settings
                global settings

                # levelTable
                self.levelTable = ["DBUG", "INFO", "WARN", "ERRR", "NONE"]

                # default set : no output to file, full output to display
                self.filePath = False
                self.fileLevel = "NONE"
                self.displayLevel = "ERRR"

                # if no settings, there's nothing more can be done
                if settings == False :
                        print("no settings - all logs will be printed to stdout")
                        return

                #
                # get display settings
                #  if not exist - NONE
                #  make sure it's in the allowed list
                #

                # flag - false if problem, no subsequent operations will be done
                tmpDisplayLog = True

                # make sure it exists
                try :
                        settings["logging"]["display"]["level"]
                except NameError :
                        self.displayLevel = "NONE"
                        tmpDisplayLog = False
                        print("display logging level not set - no logs will be printed to stdout")

                # make sure it's in levelTable
                if tmpDisplayLog == True :
                        if settings["logging"]["display"]["level"] in self.levelTable :
                                self.displayLevel = settings["logging"]["display"]["level"]
                                print("display logging level set to "+settings["logging"]["display"]["level"])
                        else :
                                self.displayLevel = "NONE"
                                print("display logging level is incorrect - no more logs to stdout")

                # delete flag
                del tmpDisplayLog

                #
                # file logging
                #  if no level, level incorrect, or level = none there will be no logging to file
                #  if no file path - no logs
                #  change path to absolute (if it's not already)
                #  test if file can be opened and closed
                #

                # flag - false if error, do not do subsequent operations
                tmpFileLog = True

                # test exists
                try :
                        settings["logging"]["file"]["level"]
                except NameError :
                        self.fileLevel = "NONE"
                        tmpFileLog = False
                        print("file logging level not set - no logs will be printed to file")

                # czech in levelTable
                if tmpFileLog == True :
                        if settings["logging"]["file"]["level"] in self.levelTable :
                                self.fileLevel = settings["logging"]["file"]["level"]
                                print("file logging level set to "+settings["logging"]["file"]["level"])
                        else :
                                self.fileLevel = "NONE"
                                print("file logging level is incorrect - no logs to file")

                # see if it's none
                if tmpFileLog == True:
                        if self.fileLevel == "NONE" :
                                tmpFileLog = False

                # test if path set
                if tmpFileLog == True :
                        try :
                                settings["logging"]["file"]["path"]
                        except NameError :
                                self.fileLevel = "NONE"
                                tmpFileLog = False
                                print("File path not set - no logs to file")
                        else :
                                self.filePath = settings["logging"]["file"]["path"]

                # change path to absolute if necessary
                if tmpFileLog == True and self.fileLevel != "NONE" :
                        if self.filePath[0] != "/" :
                                # still gotta test settings["root"] exists
                                try :
                                        settings["root"]
                                except NameError:
                                        print("root dir not in settings - will use relative path for log file")
                                else :
                                        self.filePath = settings["root"] + self.filePath
                        print("log file: "+self.filePath)

                # try opening and closing the file
                if tmpFileLog == True :
                        try:
                                # try to open file
                                f = open(self.filePath, "a")
                        except:
                                # unable to open
                                print("unable to open log file - will not perform logging to file")
                                self.fileLevel = "NONE"
                                tmpFileLog = False

                        if tmpFileLog == True :
                                try:
                                        # try to close file
                                        f.close()
                                except :
                                        # unable to close file
                                        print("unable to close log file - will not perform logging to file")
                                        self.fileLevel = "NONE"
                                        tmpFileLog = False

                # double check - if flag is false but level is not NONE, something has gone wonky
                if tmpFileLog == False and self.fileLevel != "NONE" :
                        print("error while setting up file log - discrepancy found")
                        self.fileLevel = "NONE"


        def write(self, lvl, msg, data="NoLoggingDataGiven") :
                # check level is in levelTable
                # get time
                # format
                # display first
                #  check level is what set or lower
                #  print
                # file second
                #  level check
                #  open
                #  write
                #  close

                # check in levelTable
                if lvl in self.levelTable :
                        pass
                else :
                        return

                # time
                isoTime = datetime.datetime.now().replace(microsecond=0).isoformat()

                # format msg
                outMsg = format(msg)

                # if data - format
                if data != "NoLoggingDataGiven" :
                        outMsg = outMsg + " - " + format(data)

                # format
                outStr = isoTime + " - [" + lvl + "] - " + outMsg

                #
                # display
                #  get levels
                #  check levels
                #   print
                #  tidy up
                if self.displayLevel != "NONE" :
                        # get indexes
                        incomingLevelNumber = self.inList(lvl, self.levelTable)
                        currentLevelNumber = self.inList(self.displayLevel, self.levelTable)
                        # compare
                        if incomingLevelNumber >= currentLevelNumber :
                                print(outStr)
                        # tidy up
                        del incomingLevelNumber
                        del currentLevelNumber

                #
                # file
                #  get levels
                #  check levels
                #   open
                #   write
                #   close
                if self.fileLevel != "NONE" :
                        # get indexes
                        incomingLevelNumber = self.inList(lvl, self.levelTable)
                        currentLevelNumber = self.inList(self.fileLevel, self.levelTable)
                        # compare
                        if incomingLevelNumber >= currentLevelNumber :
                                try :
                                        f = open(self.filePath, "a")
                                        f.write(outStr + "\n")
                                        f.close()
                                except :
                                        print("error writing to file")
                        # tidy up
                        del incomingLevelNumber
                        del currentLevelNumber



        #
        # helper function
        #  returns false if not in list
        #  returns index if it is in the list
        def inList(self, needle, haystack) :
                # check if haystack is a list
                #if type(haystack) != "list" :
                #        return False

                # do some checking
                if needle in haystack :
                        # loop through
                        i = 0
                        for x in haystack :
                                if x == needle :
                                        return i
                                else :
                                        i += 1
                else :
                        # needle is not in haystack
                        return false

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
