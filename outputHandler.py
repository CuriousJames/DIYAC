#!/usr/bin/env python
import time
import threading

#
# Output Handling
#
# Description:
#  Do anything that involves making an output happen
#
# Variables:
#  __doorRinging - bool - shows whether the doorbell is currently ringing
#  __doorbellCount - int - used for debounce
#  __doorbellOutputs - list of dicts - the individual doorbell outputs and whether they are inverted
#  __params - dict
#   doorOpenTime - int - seconds that the door will stay open after a successful token compare
#   doorbellCcTime - float - seconds that the doorbell closed contact output will be changed for
#
# Functions:
#
#  __init__(__systemHandler, __settings, __logger, __pi, pinDef)
#   store objects for later use
#   set initial state of some outputs
#   get parameters from __settings
#
#  openDoor()
#   called to open the door
#   starts __openDoorThreadFunc in its own thread
#
#  __openDoorThreadFunc()
#   open
#   wait for time
#   close
#
#  setDoor(state)
#   close or open the door strike
#   do the readerLed too
#   and log
#
#  ringDoorbell()
#   makes sure the doorbell is not already ringing
#   does a ring
#
#  __doorbellHit()
#   on/off cycle for the doorbell
#   calls setDoorbellOutState
#
#  setDoorbellOutState(state)
#   sets each output as described in __doorbellOutputs
#
# gpoCallback(gpio, level, tick, gpoName)
#  called by __callbackOutput in main
#  note that __callbackGeneral in main is ALSO called before gpoCallback
#  handles gpo level changes - may be used to monitor they're
#  doing as we expect


class outputHandler:
    __doorRinging = False
    __doorbellCount = 0
    __doorbellOutputs = [
        {
            "name": "doorbell12",
            "inverted": False
        },
        {
            "name": "doorbellCc",
            "inverted": True
        }
    ]
    __params = {
        "doorOpenTime": 5,
        "doorbellCcTime": 0.1
    }

    #
    # INITIALISE
    # does what it says on the tin
    #  internalise some things
    #  set initial state of some outputs
    #  get anything useful from __settings
    def __init__(self, systemHandler, settings, logger, pi, pinDef):
        # internalise the stuff
        self.__systemHandler = systemHandler
        del systemHandler
        self.__settings = settings
        del settings
        self.__logger = logger
        del logger
        self.__pi = pi
        del pi
        self.__pinDef = pinDef
        del pinDef
        self.__piActiveLedState = "on"

        # set some outputs
        try:
            self.__pi.write(self.__pinDef.pins["doorStrike"], 0)
            self.__pi.write(self.__pinDef.pins["doorbell12"], 0)
            self.__pi.write(self.__pinDef.pins["doorbellCc"], 0)
            self.__pi.write(self.__pinDef.pins["spareLed"], 0)
            self.__pi.write(self.__pinDef.pins["readerLed"], 1)
            self.__pi.write(self.__pinDef.pins["readerBuzz"], 1)
            self.__pi.write(self.__pinDef.pins["piActiveLed"], 1)
        except Exception as e:
            self.__logger.log("ERRR", "There was an issue setting output pins", e)

        # get __settings
        settingsToGet = ["doorOpenTime", "doorbellCcTime"]
        if self.__settings.allSettings is False:
            for s in settingsToGet:
                try:
                    self.__settings.allSettings["outputHandling"][s]
                except Exception as e:
                    self.__logger.log("WARN", "unable to read setting", e)
                    pass
                else:
                    self.__params[s] = self.__settings.allSettings["outputHandling"][s]
                    self.__logger.log("INFO", "new setting for output handling", {"parameter": s, "value": self.__params[s]})
            # done
        return

    def switchPiActiveLed(self, state=False):
        # if state is specified
        if state is not False:
            if state == "on":
                self.__piActiveLedState = "on"
                self.__pi.write(self.__pinDef.pins["piActiveLed"], 1)
                pass
            if state == "off":
                self.__piActiveLedState = "off"
                self.__pi.write(self.__pinDef.pins["piActiveLed"], 0)
                pass
            return
        # state not specified, do a toggle
        if self.__piActiveLedState == "on":
            self.__piActiveLedState = "off"
            self.__pi.write(self.__pinDef.pins["piActiveLed"], 0)
        elif self.__piActiveLedState == "off":
            self.__piActiveLedState = "on"
            self.__pi.write(self.__pinDef.pins["piActiveLed"], 1)
        return

    #
    # open and close the door
    # this is for when a token has been read and approved
    def openDoor(self):
        openDoorThread = threading.Thread(name='openDoorThread', target=self.__openDoorThreadFunc)
        openDoorThread.start()

    def __openDoorThreadFunc(self):
        # open
        self.setDoor("open")

        # wait
        time.sleep(self.__params["doorOpenTime"])

        # Now let's warn that the door is about to close by flashing the Reader's LED
        # l.log("DBUG", "Door Closing soon")
        # i = 5
        # while i < 5:
        #   __pi.write(p.pins["readerLed"],1)
        #   time.sleep(0.1)
        #   __pi.write(p.pins["readerLed"],0)
        #   time.sleep(0.1)
        #   i += 1

        # close
        self.setDoor("closed")

        # done
        return

    # set the door to an open or closed state
    # will do led and strike
    def setDoor(self, state):
        # error state
        if state != "open" and state != "closed":
            self.__logger.log("WARN", "No state set for changing door state")
            return
        # open
        if state == "open":
            self.__logger.log("DBUG", "Opening door")
            pinState = [{"name": "doorStrike", "state": 1}, {"name": "readerLed", "state": 0}]
        # closed
        if state == "closed":
            self.__logger.log("DBUG", "Closing door")
            pinState = [{"name": "doorStrike", "state": 0}, {"name": "readerLed", "state": 1}]
        # do the pins
        for pin in pinState:
            self.__pi.write(self.__pinDef.pins[pin["name"]], pin["state"])

    # make the doorbell do a ringing
    def ringDoorbell(self):
        self.__doorbellCount += 1
        self.__logger.log("DBUG", "******* Bell Count *******", self.__doorbellCount)

        if self.__doorRinging is False:
            self.__doorRinging = True
            self.__logger.log("INFO", "Start Doorbell")

            self.__doorbellHit()

            # Wait to give a break before hearing more bell, even if the button is pressed again
            time.sleep(2)

            self.__doorRinging = False
            self.__logger.log("INFO", "Stop Doorbell")
        else:
            self.__logger.log("INFO", "NOT Ringing doorbell - it's already ringing")
        return

    def __doorbellHit(self):
        # Some kind of nice-enough doorbell ring pattern
        self.__setDoorbellOutState(1)
        time.sleep(0.7)
        self.__setDoorbellOutState(0)
        time.sleep(0.3)
        self.__setDoorbellOutState(1)
        time.sleep(0.4)
        self.__setDoorbellOutState(0)
        time.sleep(0.2)
        self.__setDoorbellOutState(1)
        time.sleep(0.4)
        self.__setDoorbellOutState(0)

    def __setDoorbellOutState(self, state):
        if state != 1 and state != 0:
            return

        for out in self.__doorbellOutputs:
            # set state
            newState = state
            # invert if necessary
            if out["inverted"] is True:
                newState ^= 1
            # do the output
            self.__pi.write(self.__pinDef.pins[out["name"]], newState)
            del newState

        return

    def gpoCallback(self, gpio, level, tick, gpoName):
        # Doesn't do anything yet - but may be used for monitoring one day
        return
