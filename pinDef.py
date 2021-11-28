#!/usr/bin/env python

#
# Pin Definitions
#
# Description:
#  define what pins do what things - either by specifying a PCB version or defining each pin
#
# Variables:
#  pins - dict of all pin names and numbers, this is what is used by other functions
#  __pcbVersion - the pcb version specified in __settings file
#  __pcbVersionsAvailable - allowable values of __pcbVersion
#  pcbPinout - what each pin definition is by PCB version
#
# Functions:
#
#  __init__(__systemHandler, __settings, __logger)
#   setup the usable pin defs
#   get from pcb version
#   get from custom - this will overwrite any pcb defaults
#   make sure all critical pins are defined
#
#  __setByPcb()
#   get pin definitions as shown by pcb version in __settings
#
#  __setByCustom()
#   get pin definitions as defined in the __settings file
#


class pinDef:

    #
    # default pins
    #  these are the ones used by the hat
    #
    pins = {
        "doorStrike": None,
        "doorbell12": None,
        "doorbellCc": None,
        "readerLed": None,
        "readerBuzz": None,
        "doorbellButton": None,
        "doorSensor": None,
        "piActiveLed": None,
        "spareLed": None,
        "wiegand0": None,
        "wiegand1": None,
        "exitButton": None
    }

    # Pins which MUST be defined in order to have basic DIYAC functionality
    # these pins MUST be initialised as 'None' in pins above
    __criticalPins = {
        "wiegand0",
        "wiegand1",
        "doorStrike",
        "doorbellButton",
        "doorbell12"
    }

    # GP Input pins - not wiegand though
    __inputPins = {
        "doorbellButton",
        "doorSensor",
        "exitButton"
    }

    # GP Output pins
    __outputPins = {
        "doorStrike",
        "doorbell12",
        "doorbellCc",
        "readerLed",
        "readerBuzz",
        "piActiveLed",
        "spareLed"
    }

    __pcbVersion = None
    __pcbVersionsAvailable = [1, 2.0, 2.1]
    __pcbPinouts = {
        1: {
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
        },
        2.0: {
            "doorStrike": 27,
            "doorbell12": 22,
            "doorbellCc": 17,
            "readerLed": 6,
            "readerBuzz": 5,
            "doorbellButton": 26,
            "doorSensor": 20,
            "piActiveLed": 4,
            "spareLed": 3,
            "wiegand0": 19,
            "wiegand1": 13
        },
        2.1: {
            "doorStrike": 27,
            "doorbell12": 22,
            "doorbellCc": 17,
            "readerLed": 6,
            "readerBuzz": 5,
            "doorbellButton": 26,
            "doorSensor": 20,
            "piActiveLed": 4,
            "spareLed": 3,
            "wiegand0": 19,
            "wiegand1": 13,
            "exitButton": 10
        }
    }

    #
    # function to get pins from settings
    #
    def __init__(self, systemHandler, settings, logger):

        # internalise __settings and logger
        self.__systemHandler = systemHandler
        del systemHandler
        self.__logger = logger
        del logger
        self.__settings = settings
        del settings

        # get pins from PCB Version
        # get any other pins that have been set
        self.__setByPcb()
        self.__setByCustom()

        # make sure critical pins are set
        # crash out if critical pins are still 'None'
        missingCriticalPins = []
        for p in list(self.pins):
            if self.pins[p] is None:
                if p in self.__criticalPins:
                    missingCriticalPins.append(p)
                else:
                    del self.pins[p]
                    self.__logger.log("WARN", "pin not defined", {"pin": p})
        if missingCriticalPins:
            self.__systemHandler.quit(1, "Failed - Critical pin/s not defined", "ERRR", "Critical pin/s not defined", missingCriticalPins)

        self.__sortInputOutputPins()

        # done
        return

    #
    # set pinout by PCB version
    #
    def __setByPcb(self):
        # see if it's set
        try:
            self.__settings.allSettings["pinDef"]["pcbVersion"]
        except KeyError:
            pass
        else:
            self.__pcbVersion = self.__settings.allSettings["pinDef"]["pcbVersion"]
            # make sure it's a valid value
            if self.__pcbVersion in self.__pcbVersionsAvailable:
                # store it
                self.__logger.log("DBUG", "PCB Version found", {"version": self.__pcbVersion})
            else:
                self.__systemHandler.quit(1, "Failed - PCB Version set, but not recognised", "ERRR", "PCB Version set, but not recognised", {"version": self.__pcbVersion})

        # if it's defined, set the values
        if self.__pcbVersion is not None:
            for p in self.pins:
                if p in self.__pcbPinouts[self.__pcbVersion]:
                    self.pins[p] = self.__pcbPinouts[self.__pcbVersion][p]
                # self.__logger.log("DBUG", "pin from PCB", self.pins[p])

        # done
        return

    #
    # set individual pins from __settings
    #
    def __setByCustom(self):
        # is it set?
        try:
            self.__settings.allSettings["pinDef"]
        except KeyError:
            pass
        else:
            # grab it all in
            for p in self.pins:
                # but first make sure it's been set in settings
                try:
                    self.__settings.allSettings["pinDef"][p]
                except KeyError:
                    pass
                else:
                    self.pins[p] = self.__settings.allSettings["pinDef"][p]
                    self.__logger.log("DBUG", "custom pin set", {"name": p, "pin": self.pins[p]})

        # done
        return

    #
    # Create two lists, one for input and one for output pins
    #
    def __sortInputOutputPins(self):
        inputPins = {}
        outputPins = {}
        for pin in self.pins:
            if pin in self.__inputPins:
                inputPins = {**inputPins, pin: self.pins[pin]}
            elif pin in self.__outputPins:
                outputPins = {**outputPins, pin: self.pins[pin]}
        self.pins["input"] = inputPins
        self.pins["output"] = outputPins
