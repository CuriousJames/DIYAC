#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading
import os # useful for file operations
import json # for gettings settings and tokens
import logging # our own logging module
import signal # for nice exit
import sys # for nice exit

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

        # Input handler
        global inH
        inH = inputHandler(settings)

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

        #
        # remove duplicates
        # matching tokens will be deleted, with the duplicate's user appended to the first user with DOR (meaning DuplicateOR) - user1 DOR user2
        #
        #  i and j are both index counters
        #  iterate allowed tokens
        #   iterate again to compare
        #    if token values match, types match, and it's not the same entry, and it's not already listed in duplicateIndexes
        #     log
        #     add to index
        #  if there are duplicates listed in the index
        #   iterate
        #    delete the duplicates
        duplicateIndexes = []
        # main iterate
        i = 0
        for original in allowedTokens :
                # second iterate
                j = 0
                for check in allowedTokens:
                        # if tokens match, types match, it's not the same entry, and not listed in duplicate indexes
                        if original["value"] == check["value"] and original["type"] == check["type"] and i != j  and i not in duplicateIndexes:
                                l.log("WARN", "Duplicate token found in allowedTokens file", {"token": allowedTokens[j]["value"], "type": allowedTokens[j]["type"], "user": allowedTokens[j]["user"]})
                                allowedTokens[i]["user"] += " DOR " + allowedTokens[j]["user"]
                                duplicateIndexes.append(j)

                        j += 1
                i += 1
        # if there's duplicates listed, delete them
        if not duplicateIndexes :
                pass
        else:
                duplicateIndexes.sort(reverse=True) # have to sort and do from the highest index first
                for dup in duplicateIndexes :
                        del allowedTokens[dup]

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


#
# class to handle inputs
#  functions:
#   newNumpadInput(rx) - process new keypad entry
#   checkToken(rx, type) - take token and check if in allowedTokens list
#   checkBruteForce() - see if the lock is active or not, and if it should be activated
#   wiegandCallback - called by wiegand library, process & translate input from reader
#
class inputHandler :
        # vars
        #  state - [ready|reading], state of what is happen, ready for no input yet, reading for midway through a code input
        #  inputBuffer - a string of input received so far
        #  lastInputTime - used for allowing a timeout and other such stuff
        #  delimiter - start/stop key - can only be # or *
        #  timeOut - seconds before timeout occurs and state should be returned to ready
        #  bruteForceThresholdAttempts - max failed attempts within the bruteForceLockoutTime before lockout
        #  bruteForceThresholdTime - seconds of time for above number of attemps to occur within for lockout
        #  bruteForceLockoutTime - seconds that the lockout will be enforced for
        #  bruteForceLockoutStart - time in seconds of last lockout start
        #  previousAttemps - list of times of last 3 attempts
        params = {
                "delimiter": "#",
                "timeOut": 5,
                "bruteForceThresholdAttempts": 3,
                "bruteForceThresholdTime": 20,
                "bruteForceLockoutTime": 600,
        }
        numpadState = "ready"
        inputBuffer = ""
        numpadLastInputTime = None
        bruteForceLockoutStart = 0
        previousAttempts = []


        #
        # init
        # this is mostly to ge lockout bits from settings
        def __init__(self, settings) :
                # get logger
                global l

                # see if settings are set
                if settings == False :
                        return

                # the settings we're going to get are
                settingsToGet = ["delimiter", "timeOut", "bruteForceThresholdTime", "bruteForceThresholdAttempts", "bruteForceLockoutTime"]
                settingsAvailable = []
                # make sure they exist
                # if exist, update params list
                for s in settingsToGet :
                        try :
                                settings["inputHandling"][s]
                        except :
                                pass
                        else :
                                l.log("DBUG", "new setting for input handling parameter", {"parameter": s, "value": settings["inputHandling"][s]})
                                self.params[s] = settings["inputHandling"][s]

                # done
                return


        #
        # function to be run with each incoming bit
        # will work out if input should go into buffer, be ignored, or starts the buffer
        #
        # globalise logger
        # set time now
        # if state = ready AND input is not delimiter
        #  return
        # if state = ready AND input is delimiter
        #  set state to reading
        #  update lastInputTime
        # if state = reading
        #  if later that timeout
        #   empty inputBuffer
        #   set state to ready
        #   run function again
        #   return
        #  if input = start/stop delimiter
        #   submit inputBuffer to comparator function
        #   empty inputBuffer
        #   set state to ready
        #   return
        #  if input is a button (basically just 'else')
        #   throw into inputBuffer
        #   update lastInputTime
        #
        def newNumpadInput(self, rx) :

                # make logger available
                global l

                # set time
                timeNow = time.time()

                # if not reading and rx is not the start/stop delimiter, do nothin
                if self.numpadState == "ready" and rx != self.params["delimiter"] :
                        l.log("DBUG", "key press before the start key, ignoring", {"key": rx})
                        return

                # start of input string
                if self.numpadState == "ready" and rx == self.params["delimiter"] :
                        l.log("DBUG", "new keypad string started by delimiter", {"timeNow": timeNow})
                        self.numpadState = "reading"
                        self.numpadLastInputTime = timeNow
                        return

                # if mid way through reading
                if self.numpadState == "reading" :

                        # if over timeout
                        if self.numpadLastInputTime + self.params["timeOut"] < timeNow :
                                l.log("DBUG", "new entry is after timeout limit, resetting and going again", {"timeNow": timeNow, "lastInputTime": self.numpadLastInputTime})
                                self.numpadState = "ready"
                                self.inputBuffer = ""
                                self.numpadLastInputTime = None
                                self.newNumpadInput(rx)
                                return

                        # if delimiter, we have an end of input string
                        if rx == self.params["delimiter"] :
                                # run comparator
                                self.checkToken(self.inputBuffer, "code")
                                # clear up
                                self.inputBuffer = ""
                                self.numpadLastInputTime = None
                                self.numpadState = "ready"
                                # done
                                return

                        # this is an actual input
                        #  add it onto the end of the input buffer
                        self.inputBuffer += rx
                        self.numpadLastInputTime = timeNow
                        return

        #
        # check incoming code against list of allowed tokens
        #  if match, open door
        #  if not match, shoot whoever entered it
        def checkToken(self, rx, rxType) :

                # make the allowedTokens and logger accessible
                global allowedTokens
                global l

                # check the lockout, bail if locked
                if self.checkLockout() == "locked" :
                        l.log("INFO", "ACCESS DENIED BY LOCKOUT", {"token": rx})
                        return

                # see if it exists in tokens
                allowFlag = False
                for t in allowedTokens :
                        if t["type"] == rxType :
                                if t["value"] == rx :
                                        l.log("INFO", "ACCESS ALLOWED BY TOKEN", {"token": rx, "type": rxType, "user": t["user"]})
                                        allowFlag = True
                                        # open the door
                                        return
                # log incorrect code entered
                if allowFlag == False :
                        l.log("INFO", "ACCESS DENIED BY TOKEN", {"token": rx, "type": rxType})

                # all done
                return

        #
        # check whether lockout is happening
        #  add attempt
        #  if getLockoutState == "locked"
        #   return "locked"
        #  if calculateNewLockout == "locked"
        #   return "locked"
        #  else
        #   return "unlocked"
        def checkLockout(self) :

                self.addAttempt()
                if self.getBruteForceLockoutState() == "locked" :
                        return "locked"
                if self.calculateNewLockout() == "locked" :
                        return "locked"
                return "unlocked"

        #
        # add attempt into previousAttempts
        # remove last value if more than 3
        #
        def addAttempt(self) :
                timeNow = time.time()
                # if previous attempts is already populated, remove entry 0
                if len(self.previousAttempts) == self.params["bruteForceThresholdAttempts"] :
                        del self.previousAttempts[0]
                # append new time
                self.previousAttempts.append(timeNow)

        #
        # get lockout state
        #  basically just time comparator
        #  get logger
        #  if lockoutStart == 0, it's not locked
        #   return "unlocked"
        #  if lockoutStart + lockoutTime < timeNow
        #   lockout has finished
        #   lockoutStart = 0
        #   return "unlocked"
        #  else
        #   return "locked"
        def getBruteForceLockoutState(self) :
                # logger
                global l

                # time
                timeNow = time.time()

                # if lockoutStart == 0, no lock is set
                if self.bruteForceLockoutStart == 0 :
                        l.log("DBUG", "No bruteforce lockout")
                        return "unlocked"

                # if lockoutStart + lockoutTime <= timeNow, reset lock and return unlocked
                if self.bruteForceLockoutStart + self.params["bruteForceLockoutTime"] <= timeNow :
                        l.log("INFO", "BruteForce Lockout stopped")
                        self.bruteForceLockoutStart = 0
                        return "unlocked"

                # it's locked
                l.log("DBUG", "lockout still active")
                return "locked"

        #
        # calculate if there should be a lockout based on information from self.previousAttempts
        # if length of previousAttemps is below threshold, do nothing
        def calculateNewLockout(self) :
                # time and logger
                timeNow = time.time()
                global l

                # if not at threshold, do nothing
                if len(self.previousAttempts) < self.params["bruteForceThresholdAttempts"] :
                        return "no change"

                # check by time of earliest chronological entry,
                if self.previousAttempts[0] + self.params["bruteForceThresholdTime"] < timeNow :
                        return "no change"

                # that must mean we're within the threshold time and attempts, initiate lockout
                l.log("INFO", "Bruteforce lockout started")
                self.bruteForceLockoutStart = timeNow
                return "locked"


        #
        # this function is called by the wiegand library when it has read something
        #
        def wiegandCallback(self, bits, code):
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
                        # match = False
                        # for token in allowedTokens:
                        #         # for generic cards - no changing necessary
                        #         if token["type"] != "code":
                        #                 if token["value"] == output:
                        #                         # open the door
                        #                         match = True
                        #                         l.log("INFO", "token allowed (generic card)", output)
                        # # if it wasn't a match
                        # if match == False :
                        #         l.log("INFO", "token not allowed", output)
                        self.checkToken(output, "card")
                elif bits == 4:
                        # someone pressed a button
                        #  sanity check - maybe wiegand connection is swapped
                        #  tidy input
                        #  run numpadinput function

                        # little check - hint that wiegand wires may not be correct way around
                        if code > 11 :
                                l.log("WARN", "keypad code is unexpected value - check wiegand connections are not swapped", {"input": code})

                        # Tidy up the input - change * and #, or convert to string
                        if code == 10:
                                key="*"
                        elif code == 11:
                                key="#"
                        else:
                                key=str(code)
                        l.log("DBUG", "Keypad key pressed", key)

                        # run through the keypad checker
                        self.newNumpadInput(key)
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
w = wiegand.decoder(pi, p.pins["wiegand0"], p.pins["wiegand1"], inH.wiegandCallback)

while True:
        time.sleep(9999)
        #Just keeping the python fed (slithering)
        l.log("INFO", "boppity")
