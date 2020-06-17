#!/usr/bin/env python
import time

#
# Input Handler
#
# Description:
#  Handle input from everything (mostly wiegand)
#  do appropriate things
#  including lockouts
#
# Variables:
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
#
# Functions:
#  newNumpadInput(rx)
#   process new entry from keypad (deals with each individual key press)
#
#  checkInput(rx, type)
#   called when there is a full token to be checked
#   take token and check if in allowedTokens list
#
#  checkLockout()
#   see if the lock is active or not, and if it should be activated
#
#  addAttempt()
#   puts a new attempt and time into previousAttempts
#
#  getBruteForceLockoutState()
#   bool - if brute force is in action
#
#  calculateLockout()
#   see if a new lockout should be activated - based on previousAttempts
#
#  wiegandCallback(bytes, code)
#   called by wiegand library, process & translate input from reader
#   includes translation from incoming int to hex string
#
class inputHandler :
    # vars

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
    def __init__(self, settings, logger, tokens, outputHandler) :
        # get logger
        #global l

        # internalise settings, tokens and logger
        self.settings = settings
        self.logger = logger
        self.tokens = tokens
        self.outputHandler = outputHandler

        # see if settings are set
        if self.settings.allSettings == False :
            return

        # the settings we're going to get are
        settingsToGet = ["delimiter", "timeOut", "bruteForceThresholdTime", "bruteForceThresholdAttempts", "bruteForceLockoutTime"]
        # make sure they exist
        # if exist, update params list
        for s in settingsToGet :
            try :
                self.settings.allSettings["inputHandling"][s]
            except :
                pass
            else :
                self.logger.log("DBUG", "new setting for input handling parameter", {"parameter": s, "value": self.settings.allSettings["inputHandling"][s]})
                self.params[s] = self.settings.allSettings["inputHandling"][s]

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
        #global l

        # set time
        timeNow = time.time()

        # if not reading and rx is not the start/stop delimiter, do nothin
        if self.numpadState == "ready" and rx != self.params["delimiter"] :
            self.logger.log("DBUG", "key press before the start key, ignoring", {"key": rx})
            return

        # start of input string
        if self.numpadState == "ready" and rx == self.params["delimiter"] :
            self.logger.log("DBUG", "new keypad string started by delimiter", {"timeNow": timeNow})
            self.numpadState = "reading"
            self.numpadLastInputTime = timeNow
            return

        # if mid way through reading
        if self.numpadState == "reading" :

            # if over timeout
            if self.numpadLastInputTime + self.params["timeOut"] < timeNow :
                # log
                logData = {"timeNow": timeNow, "lastInputTime": self.numpadLastInputTime}
                self.logger.log("DBUG", "new entry is after timeout limit, resetting and going again", logData)
                logData = None
                # reset
                self.numpadState = "ready"
                self.inputBuffer = ""
                self.numpadLastInputTime = None
                # run the input again (just incase its a start button)
                self.newNumpadInput(rx)
                # done
                return

            # if delimiter, we have an end of input string
            if rx == self.params["delimiter"] :
                # run comparator
                self.checkInput(self.inputBuffer, "code")
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
    # check input
    # this if for a fully formed input to be checked/approved by lockout and then token checked
    #
    def checkInput(self, rx, rxType) :
        # check the lockout, bail if locked
        if self.checkLockout() == "locked" :
            self.logger.log("INFO", "ACCESS DENIED BY LOCKOUT", {"token": rx})
            return

        # check the token, true if approved, false if denied
        tokenCheckOutput = self.tokens.checkToken(rx, rxType)
        if tokenCheckOutput["allow"]  == True :
            self.logger.log("INFO", "ACCESS ALLOWED BY TOKEN", {"token": rx, "type": rxType, "user": tokenCheckOutput["user"]})
            self.outputHandler.openDoor()
        else :
            self.logger.log("INFO", "ACCESS DENIED BY TOKEN", {"token": rx, "type": rxType})


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
        #global l

        # time
        timeNow = time.time()

        # if lockoutStart == 0, no lock is set
        if self.bruteForceLockoutStart == 0 :
            self.logger.log("DBUG", "No bruteforce lockout")
            return "unlocked"

        # if lockoutStart + lockoutTime <= timeNow, reset lock and return unlocked
        if self.bruteForceLockoutStart + self.params["bruteForceLockoutTime"] <= timeNow :
            self.logger.log("INFO", "BruteForce Lockout stopped")
            self.bruteForceLockoutStart = 0
            self.previousAttempts = []
            return "unlocked"

        # it's locked
        self.logger.log("DBUG", "lockout still active")
        return "locked"


    #
    # calculate if there should be a lockout based on information from self.previousAttempts
    # if length of previousAttemps is below threshold, do nothing
    def calculateNewLockout(self) :
        # time and logger
        timeNow = time.time()
        #global l

        # if not at threshold, do nothing
        if len(self.previousAttempts) < self.params["bruteForceThresholdAttempts"] :
            return "no change"

        # check by time of earliest chronological entry,
        if self.previousAttempts[0] + self.params["bruteForceThresholdTime"] < timeNow :
            return "no change"

        # that must mean we're within the threshold time and attempts, initiate lockout
        self.logger.log("INFO", "Bruteforce lockout started")
        self.bruteForceLockoutStart = timeNow
        return "locked"


    #
    # this function is called by the wiegand library when it has read something
    #
    def wiegandCallback(self, bits, code):
        # if bits != 4 AND bits != 34
        #  error
        #
        # if bits == 34, it's a card token
        #  convert to binary string
        #  trim "0b", start parity bit, end parity bit
        #  re order bytes
        #  convert to hex
        #  compare against list
        #
        # if bits == 4
        #  if code = 0
        #   ring doorbell
        #  else
        #   do something else

        #
        # log
        self.logger.log("DBUG", "New read", {"bits":bits, "code":code})

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
            self.logger.log("DEBUG", "output from formatting", output)

            self.checkInput(output, "card")
        elif bits == 4:
            # someone pressed a button
            #  sanity check - maybe wiegand connection is swapped
            #  tidy input
            #  run numpadinput function

            # little check - hint that wiegand wires may not be correct way around
            if code > 11 :
                self.logger.log("WARN", "keypad code is unexpected value - check wiegand connections are not swapped", {"input": code})

            # Tidy up the input - change * and #, or convert to string
            if code == 10:
                key="*"
            elif code == 11:
                key="#"
            else:
                key=str(code)
            self.logger.log("DBUG", "Keypad key pressed", key)

            # run through the keypad checker
            self.newNumpadInput(key)
        else:
            #
            # error condition
            self.logger.log("WARN", "unexpected number of bits", bits)
            return
