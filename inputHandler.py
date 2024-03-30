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
#  __inputBuffer - a string of input received so far
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
#  __newNumpadInput(rx)
#   process new entry from keypad (deals with each individual key press)
#
#  __checkInput(rx, type)
#   called when there is a full token to be checked
#   take token and check if in allowedTokens list
#
#  __checkLockout()
#   see if the lock is active or not, and if it should be activated
#
#  __addDeniedAttempt()
#   puts a new bad attempt and time into __previousBadAttempts
#
#  getBruteForceLockoutState()
#   bool - if brute force is in action
#
#  calculateLockout()
#   see if a new lockout should be activated - based on __previousBadAttempts
#
#  __wiegandCallback(bytes, code)
#   called by wiegand library, process & translate input from reader
#   includes translation from incoming int to hex string
#
# gpiCallback(gpio, level, tick, gpiName)
#  called by __callbackInput in main
#  note that __callbackGeneral in main is ALSO called before gpiCallback


class inputHandler:
    # vars

    __params = {
        "delimiter": "#",
        "timeout": 5,
        "bruteforceThresholdAttempts": 3,
        "bruteforceThresholdTime": 20,
        "overspeedThresholdTime": 0.1,
        "lockoutTime": 600,
        "doorSensorOpen": 1
    }
    __numpadState = "ready"
    __inputBuffer = ""
    __numpadLastInputTime = None
    lockout = {"state": "unlocked"}
    __previousBadAttempts = []

    #
    # init
    # this is mostly to get lockout bits from __settings
    def __init__(self, systemHandler, settings, logger, tokens, outputHandler, pi, pinDef):
        import pigpio  # pigpio is started in main, but this is necessary here for pullup definitions
        try:
            import wiegand
        except ImportError:
            print("*** Wiegand.py not found - please download it and place it in the root directory for this folder ***\n")
            print("This should do the trick, assuming you're in the root directory now:")
            print("wget http://abyz.me.uk/rpi/pigpio/code/wiegand_py.zip")
            print("unzip wiegand_py.zip")
            print("rm -rf wiegand_old.py wiegand_py.zip\n")
            exit()

        # internalise settings, tokens, logger, outputHandler, pi and pinDef
        self.__systemHandler = systemHandler
        del systemHandler
        self.__settings = settings
        del settings
        self.__logger = logger
        del logger
        self.__tokens = tokens
        del tokens
        self.__outputHandler = outputHandler
        del outputHandler
        self.__pi = pi
        del pi
        self.__pinDef = pinDef
        del pinDef

        # see if __settings are set
        if self.__settings.allSettings is False:
            return

        # the __settings we're going to get are
        settingsToGet = ["delimiter", "timeout", "bruteforceThresholdTime", "bruteforceThresholdAttempts", "overspeedThresholdTime", "lockoutTime", "doorSensorOpen"]
        # make sure they exist
        # if exist, overwrite __params list with user defined settings
        for s in settingsToGet:
            try:
                self.__settings.allSettings["inputHandling"][s]
            except Exception:
                # self.__logger.log("WARN", "unable to read setting", e)
                pass
            else:
                self.__logger.log("DBUG", "input handler: new setting", {"parameter": s, "value": self.__settings.allSettings["inputHandling"][s]})
                self.__params[s] = self.__settings.allSettings["inputHandling"][s]

        # initialise some pins for pullup and glitchfilter
        self.__pi.set_glitch_filter(self.__pinDef.pins["doorbellButton"], 100000)
        self.__pi.set_glitch_filter(self.__pinDef.pins["doorSensor"], 50000)

        self.__pi.set_pull_up_down(self.__pinDef.pins["doorbellButton"], pigpio.PUD_UP)
        self.__pi.set_pull_up_down(self.__pinDef.pins["doorSensor"], pigpio.PUD_UP)

        doorbellState=self.__pi.read(self.__pinDef.pins["doorbellButton"])
        self.__logger.log("DBUG", "Doorbell Initial GPI State", {"doorbellState": doorbellState})

        doorSensorState=self.__pi.read(self.__pinDef.pins["doorSensor"])
        self.__logger.log("DBUG", "Door Sensor Initial GPI State", {"doorSensorState": doorSensorState})

        # set the wiegand reading
        # will call function __wiegandCallback on receiving data
        w = wiegand.decoder(self.__pi, self.__pinDef.pins["wiegand0"], self.__pinDef.pins["wiegand1"], self.__wiegandCallback)

        # done
        return

    #
    # function to be run with each incoming bit
    # will work out if input should go into buffer, be ignored, or starts the buffer
    #
    # globalise __logger
    # set time now
    # if state = ready AND input is not delimiter
    #  return
    # if state = ready AND input is delimiter
    #  set state to reading
    #  update lastInputTime
    # if state = reading
    #  if later that timeout
    #   empty __inputBuffer
    #   set state to ready
    #   run function again
    #   return
    #  if input = start/stop delimiter
    #   submit __inputBuffer to comparator function
    #   empty __inputBuffer
    #   set state to ready
    #   return
    #  if input is a button (basically just 'else')
    #   throw into __inputBuffer
    #   update lastInputTime
    #

    def __newNumpadInput(self, rx):
        # make __logger available
        # global l

        # set time
        timeNow = time.time()

        # if not reading and rx is not the start/stop delimiter, do nothin
        if self.__numpadState == "ready" and rx != self.__params["delimiter"]:
            self.__logger.log("DBUG", "key press before the start key, ignoring", {"key": rx})
            return

        # start of input string
        if self.__numpadState == "ready" and rx == self.__params["delimiter"]:
            self.__logger.log("DBUG", "new keypad string started by delimiter", {"timeNow": timeNow})
            self.__numpadState = "reading"
            self.__numpadLastInputTime = timeNow
            return

        # if mid way through reading
        if self.__numpadState == "reading":

            # if over timeout
            if self.__numpadLastInputTime + self.__params["timeout"] < timeNow:
                # log
                logData = {"timeNow": timeNow, "lastInputTime": self.__numpadLastInputTime}
                self.__logger.log("DBUG", "new entry is after timeout limit, resetting and going again", logData)
                logData = None
                # reset
                self.__numpadState = "ready"
                self.__inputBuffer = ""
                self.__numpadLastInputTime = None
                # run the input again (just incase its a start button)
                self.__newNumpadInput(rx)
                # done
                return

            # if delimiter, we have an end of input string
            if rx == self.__params["delimiter"]:
                # run comparator
                self.__checkInput(self.__inputBuffer, "code")
                # clear up
                self.__inputBuffer = ""
                self.__numpadLastInputTime = None
                self.__numpadState = "ready"
                # done
                return

            # this is an actual input
            #  see if we need to think about lockout
            #  if locked out by overspeed - die
            #  add it onto the end of the input buffer
            self.__calculateNewOverspeedLockout()
            if self.lockout["state"] == "locked":
                if self.lockout["type"] == "overspeed":
                    self.__logger.log("DBUG", "overspeed - numpad input ignored")
                    return
            self.__inputBuffer += rx
            self.__numpadLastInputTime = timeNow
            return

    #
    # check input
    # this if for a fully formed input to be checked/approved by lockout and then token checked
    #
    def __checkInput(self, rx, rxType):
        # check the lockout, bail if locked
        if self.__checkLockout() == "locked":
            self.__logger.log("INFO", "ACCESS DENIED BY LOCKOUT", {"token": rx})
            return

        # check the token, true if approved, false if denied
        tokenCheckOutput = self.__tokens.checkToken(rx, rxType)
        if tokenCheckOutput["allow"] is True:
            self.__outputHandler.openDoor()
            self.__logger.log("INFO", "ACCESS ALLOWED BY TOKEN", {"token": rx, "type": rxType, "user": tokenCheckOutput["user"]})
        else:
            # add bad attempt to __previousBadAttempts
            self.__addBadAttempt()
            self.__logger.log("INFO", "ACCESS DENIED BY TOKEN", {"token": rx, "type": rxType})

        # done
        return

    #
    # add attempt into __previousBadAttempts
    # remove last value if more than 3
    #
    def __addBadAttempt(self):
        timeNow = time.time()
        # if previous attempts is already populated, remove entry 0
        if len(self.__previousBadAttempts) > self.__params["bruteforceThresholdAttempts"]:
            del self.__previousBadAttempts[0]
        # append new time
        self.__previousBadAttempts.append(timeNow)

    #
    # lockout
    def __checkLockout(self):
        # if already locked, DENY
        if self.lockout["state"] == "locked":
            return "locked"

        # see if a new lockout should be started by bruteforce
        if self.__calcluateNewBruteforceLockout() == "locked":
            return "locked"

        # see if we need lockout from overspeed input
        if self.__calculateNewOverspeedLockout() == "locked":
            return "locked"

        # it's all easy
        return "unlocked"

    #
    # calculate if there should be a lockout based on information from self.__previousBadAttempts
    # if length of previousAttemps is below threshold, do nothing
    def __calcluateNewBruteforceLockout(self):
        # time
        timeNow = time.time()

        # if not at threshold, do nothing
        if len(self.__previousBadAttempts) < self.__params["bruteforceThresholdAttempts"]:
            return "no change"

        # check by time of earliest chronological entry,
        if self.__previousBadAttempts[0] + self.__params["bruteforceThresholdTime"] < timeNow:
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
    def __calculateNewOverspeedLockout(self):
        # time
        timeNow = time.time()

        # make sure there was already an input
        if self.__numpadLastInputTime is None:
            return "no change"

        # test time
        if self.__numpadLastInputTime + self.__params["overspeedThresholdTime"] < timeNow:
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
        self.__logger.log("INFO", "Lockout started", {"method": method, "duration": self.__params["lockoutTime"]})
        self.lockout = {"state": "locked", "type": method, "start": timeNow}
        # wait
        time.sleep(self.__params["lockoutTime"])
        # end
        self.__logger.log("INFO", "Lockout ended")
        self.lockout = {"state": "unlocked"}
        self.__previousBadAttempts = []
        return

    #
    # this function is called by the wiegand library when it has read something
    #
    def __wiegandCallback(self, bits, code):
        # if bits == 34 or 26, it's a card token
        #  convert to binary string
        #  trim "0b", start parity bit, end parity bit
        #  re order bytes
        #  convert to hex
        #  compare against list
        #
        # if bits == 4
        #  intrept key and pass onto __newNumpadInput

        #
        # we have a card
        if bits == 34 or bits == 26:
            # make input into a hex string
            #
            output = self.__wiegandToHex(bits, code)
            self.__logger.log("DBUG", "New token read", {"bits": bits, "code": code, "token": output})
            self.__checkInput(output, "card")
        # someone pressed a button
        elif bits == 4:
            #  tidy input
            #  sanity check - maybe wiegand connection is swapped
            #  run numpadinput function

            # Tidy up the input - change * and #, or convert to string
            if code == 10:
                key = "*"
            elif code == 11:
                key = "#"
            elif code > 11:
                # little check - hint that wiegand wires may not be correct way around
                self.__logger.log("WARN", "Keypad code is unexpected value - check wiegand connections are not swapped", {"bits": bits, "code": code})
                return
            else:
                key = str(code)

            self.__logger.log("DBUG", "Keypad key pressed", {"bits": bits, "code": code, "key": key})

            # run through the keypad checker
            self.__newNumpadInput(key)
        else:
            #
            # error condition
            self.__logger.log("WARN", "New read - unexpected amount of bits", {"bits": bits, "code": code})
            return

    def __wiegandToHex(self, bits, code):
        if bits == 34:
            binaryFormatter = "#036b"
            trimChar = 2
        elif bits == 26:
            binaryFormatter = "#028b"
            trimChar = 4
        else:
            self.__logger.log("ERRR", "__wiegandToHex called with unexpected amount of bits", {"bits": bits, "code": code})
            return False

        input = str(format(code, binaryFormatter))  # make binary string
        input = input[3:]  # trim '0b' and first parity bit
        input = input[:-1]  # trim last parity bit
        output = input[24:] + input[16:24] + input[8:16] + input[:8]  # re-order bytes
        output = int(output, 2)  # change to integer - required for doing the change to hex
        output = format(output, '#010X')  # make hex string
        output = output[trimChar:]  # trim "0X" (34) or "0X00" (26)
        return output

    def gpiCallback(self, gpi, level, tick, gpiName):
        # if it's the doorbell button, ring the doorbell
        if gpiName == "doorbellButton" and level == 0:
            self.__logger.log("DBUG", "doorbell button pushed", {"GPI": gpi, "GPI Name": gpiName, "levl": level})
            self.__outputHandler.ringDoorbell()
        elif gpiName == "doorSensor":
            self.__logger.log("DBUG", "Door sensor changed state", {"GPI": gpi, "GPI Name": gpiName, "levl": level})
        else:
            self.__logger.log("DBUG", "Unknown GPI State changed", {"GPI": gpi, "GPI Name": gpiName, "levl": level})