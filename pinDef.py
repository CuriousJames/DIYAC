#!/usr/bin/env python
import sys

#
# Pin Definitions
#
# Description:
#  define what pins do what things - either by specifying a PCB version or defining each pin
#
# Variables:
#  pins - dict of all pin names and numbers, this is what is used by other functions
#  pcbVersion - the pcb version specified in settings file
#  pcbVersionsAvailable - allowable values of pcbVersion
#  pcbPinout - what each pin definition is by PCB version
#
# Functions:
#
#  __init__(settings, logger)
#   setup the usable pin defs
#   get from pcb version
#   get from custom - this will overwrite any pcb defaults
#   make sure all critical pins are defined
#
#  setByPcb()
#   get pin definitions as shown by pcb version in settings
#
#  setByCustom()
#   get pin definitions as defined in the settings file
#
class pinDef :

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
        "wiegand1": None
    }
    pcbVersion = None
    pcbVersionsAvailable = [1, 2.0, 2.1]
    pcbPinouts = {
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
    def __init__(self, settings, logger) :

        # internalise settings and logger
        self.logger = logger
        self.settings = settings

        # get pins from PCB Version
        # get any other pins that have been set
        self.setByPcb()
        self.setByCustom()

        # make sure pins are set
        # crash out if critical pins aren't set
        criticalPins = ["doorStrike"]
        for p in self.pins :
            if self.pins[p] == None :
                if p in criticalPins :
                    self.logger.log("ERRR", "Critical pin not defined", {"pin": p})
                    sys.exit()
                else :
                    self.logger.log("WARN", "pin not defined", {"pin": p})

        # done
        return

    #
    # set pinout by PCB version
    #
    def setByPcb(self) :
        # see if it's set
        try :
            self.settings.allSettings["pinDef"]["pcbVersion"]
        except :
            pass
        else :
            # make sure it's a valid value
            if self.settings.allSettings["pinDef"]["pcbVersion"] in self.pcbVersionsAvailable :
                # store it
                self.pcbVersion = self.settings.allSettings["pinDef"]["pcbVersion"]
                self.logger.log("DBUG", "pcb version found", {"version": self.pcbVersion} )

        # if it's defined, set the values
        if self.pcbVersion != None :
            for p in self.pins :
                self.pins[p] = self.pcbPinouts[self.pcbVersion][p]
                #self.logger.log("DBUG", "pin from PCB", self.pins[p])

        # done
        return

    #
    # set individual pins from settings
    #
    def setByCustom(self) :
        # is it set?
        try :
            self.settings.allSettings["pinDef"]
        except :
            pass
        else :
            # grab it all in
            for p in self.pins :
                # but first make sure it exists
                try :
                    self.settings.allSettings["pinDef"][p]
                except :
                    pass
                else :
                    self.pins[p] = self.settings.allSettings["pinDef"][p]
                    self.logger.log( "DBUG", "custom pin set", {"name": p, "pin": self.pins[p]} )

        # done
        return
