#!/usr/bin/env python
import time
import threading

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
#  bruteForceThresholdAttempts - max failed attempts within the bruteForceThresholdTime before lockout
#  bruteForceThresholdTime - seconds of time for above number of attemps to occur within for lockout
#  lockoutTime - seconds that the bruteforce & overspeed lockout will be enforced for
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


class inputHandler:
    # vars

    params = {
        "delimiter": "#",
        "timeout": 5,
        "bruteforceThresholdAttempts": 3,
        "bruteforceThresholdTime": 20,
        "overspeedThresholdTime": 0.1,
        "lockoutTime": 600,
    }
    numpadState = "ready"
    inputBuffer = ""
    numpadLastInputTime = None
    lockout = {"state": "unlocked"}
    previousAttempts = []

    #
    # init
    # this is mostly to ge lockout bits from settings
    def __init__(self, settings, logger, tokens, outputHandler):
        # get logger
        # global l

        # internalise settings, tokens and logger
        self.settings = settings
        self.logger = logger
        self.tokens = tokens
        self.outputHandler = outputHandler

        # see if settings are set
        if self.settings.allSettings is False:
            return

        # the settings we're going to get are
        settingsToGet = ["delimiter", "timeout", "bruteforceThresholdTime", "bruteforceThresholdAttempts", "overspeedThresholdTime", "lockoutTime"]
        # make sure they exist
        # if exist, update params list
        for s in settingsToGet:
            try:
                self.settings.allSettings["inputHandling"][s]
            except:
                pass
            else:
                self.logger.log("DBUG", "input handler: new setting", {"parameter": s, "value": self.settings.allSettings["inputHandling"][s]})
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

    def newNumpadInput(self, rx):
        # make logger available
        # global l

        # set time
        timeNow = time.time()

        # if not reading and rx is not the start/stop delimiter, do nothin
        if self.numpadState == "ready" and rx != self.params["delimiter"]:
            self.logger.log("DBUG", "key press before the start key, ignoring", {"key": rx})
            return

        # start of input string
        if self.numpadState == "ready" and rx == self.params["delimiter"]:
            self.logger.log("DBUG", "new keypad string started by delimiter", {"timeNow": timeNow})
            self.numpadState = "reading"
            self.numpadLastInputTime = timeNow
            return

        # if mid way through reading
        if self.numpadState == "reading":

            # if over timeout
            if self.numpadLastInputTime + self.params["timeout"] < timeNow:
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
            if rx == self.params["delimiter"]:
                # run comparator
                self.checkInput(self.inputBuffer, "code")
                # clear up
                self.inputBuffer = ""
                self.numpadLastInputTime = None
                self.numpadState = "ready"
                # done
                return

            # this is an actual input
            #  see if we need to think about lockout
            #  if locked out by overspeed - die
            #  add it onto the end of the input buffer
            self.calculateNewOverspeedLockout()
            if self.lockout["state"] == "locked":
                if self.lockout["type"] == "overspeed":
                    self.logger.log("DBUG", "overspeed - numpad input ignored")
                    return
            self.inputBuffer += rx
            self.numpadLastInputTime = timeNow
            return

    #
    # check input
    # this if for a fully formed input to be checked/approved by lockout and then token checked
    #
    def checkInput(self, rx, rxType):
        # add attempt to previousAttempts
        self.addAttempt()

        # check the lockout, bail if locked
        if self.checkLockout() == "locked":
            self.logger.log("INFO", "ACCESS DENIED BY LOCKOUT", {"token": rx})
            return

        # check the token, true if approved, false if denied
        tokenCheckOutput = self.tokens.checkToken(rx, rxType)
        if tokenCheckOutput["allow"] is True:
            self.logger.log("INFO", "ACCESS ALLOWED BY TOKEN", {"token": rx, "type": rxType, "user": tokenCheckOutput["user"]})
            self.outputHandler.openDoor()
        else:
            self.logger.log("INFO", "ACCESS DENIED BY TOKEN", {"token": rx, "type": rxType})

        # done
        return

    #
    # add attempt into previousAttempts
    # remove last value if more than 3
    #
    def addAttempt(self):
        timeNow = time.time()
        # if previous attempts is already populated, remove entry 0
        if len(self.previousAttempts) == self.params["bruteforceThresholdAttempts"]:
            del self.previousAttempts[0]
        # append new time
        self.previousAttempts.append(timeNow)

    #
    # lockout
    def checkLockout(self):
        # if already locked, DENY
        if self.lockout["state"] == "locked":
            return "locked"

        # see if a new lockout should be started by bruteforce
        if self.calculateNewBruteforceLockout() == "locked":
            return "locked"

        # see if we need lockout from overspeed input
        if self.calculateNewOverspeedLockout() == "locked":
            return "locked"

        # it's all easy
        return "unlocked"

    #
    # calculate if there should be a lockout based on information from self.previousAttempts
    # if length of previousAttemps is below threshold, do nothing
    def calculateNewBruteforceLockout(self):
        # time
        timeNow = time.time()

        # if not at threshold, do nothing
        if len(self.previousAttempts) < self.params["bruteforceThresholdAttempts"]:
            return "no change"

        # check by time of earliest chronological entry,
        if self.previousAttempts[0] + self.params["bruteforceThresholdTime"] < timeNow:
            return "no change"

        # that must mean we're within the threshold time and attempts, initiate lockout!
        # run the thread function
        # but only if it's not already locked
        if self.lockout["state"] != "locked":
            lockoutThread = threading.Thread(name='lockoutThread', target=self.lockoutThreadFunc, args=("bruteforce",))
            lockoutThread.start()

        # done
        return "locked"

    #
    # new lockout based on overspeed input?
    #
    def calculateNewOverspeedLockout(self):
        # time
        timeNow = time.time()

        # make sure there was already an input
        if self.numpadLastInputTime is None:
            return "no change"

        # test time
        if self.numpadLastInputTime + self.params["overspeedThresholdTime"] < timeNow:
            return "no change"

        # lets lock it oot
        if self.lockout["state"] != "locked":
            lockoutThread = threading.Thread(name='lockoutThread', target=self.lockoutThreadFunc, args=("overspeed",))
            lockoutThread.start()

        # done
        return "locked"

    #
    # lockout thread
    #  a thread that will just sit for the time lockout
    #
    def lockoutThreadFunc(self, method):
        # init
        timeNow = time.time()
        # start
        self.logger.log("INFO", "Lockout started", {"method": method, "duration": self.params["lockoutTime"]})
        self.lockout = {"state": "locked", "type": method, "start": timeNow}
        # wait
        time.sleep(self.params["lockoutTime"])
        # end
        self.logger.log("INFO", "Lockout ended")
        self.lockout = {"state": "unlocked"}
        self.previousAttempts = []
        return

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
        self.logger.log("DBUG", "New read", {"bits": bits, "code": code})

        #
        # we have a card
        if bits == 34:
            # make input into a hex string
            #
            input = str(format(code, '#036b'))  # make binary string
            input = input[3:]  # trim '0b' and first parity bit
            input = input[:-1]  # trim last parity bit
            output = input[24:] + input[16:24] + input[8:16] + input[:8]  # re-order bytes
            output = int(output, 2)  # change to integer - required for doing the change to hex
            output = format(output, '#010x')  # make hex string
            output = output[2:]  # trim "0x"
            self.logger.log("DEBUG", "output from formatting", output)
            self.checkInput(output, "card")
        elif bits == 4:
            # someone pressed a button
            #  sanity check - maybe wiegand connection is swapped
            #  tidy input
            #  run numpadinput function

            # little check - hint that wiegand wires may not be correct way around
            if code > 11:
                self.logger.log("WARN", "keypad code is unexpected value - check wiegand connections are not swapped", {"input": code})

            # Tidy up the input - change * and #, or convert to string
            if code == 10:
                key = "*"
            elif code == 11:
                key = "#"
            else:
                key = str(code)
            self.logger.log("DBUG", "Keypad key pressed", key)

            # run through the keypad checker
            self.newNumpadInput(key)
        else:
            #
            # error condition
            self.logger.log("WARN", "unexpected number of bits", bits)
            return
