#!/usr/bin/env python
import sys

#
# GPIO Variables so we don't have to remember pin numbers!
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
    pcbVersionsAvailable = [1, 2]
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
        2: {
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

        # internalise settings and logger
        self.logger = logger
        self.settings = settings

        # # see if anything even exists in settings
        # try :
        #     self.settings["pinDef"]
        # except :
        #     self.logger.log("DBUG", "No new pin definitions from settings")
        #     return

        # # iterate settigns[pinDef]
        # for p in self.settings["pinDef"] :
        #     # see if it's one of the pinDefs we already have
        #         if p in self.pins :
        #             # validate
        #             #  >=2, <=27
        #             if self.settings["pinDef"][p] >= 2 and self.settings["pinDef"][p] <= 27 :
        #                 # update pin definition
        #                 self.logger.log("DBUG", "New pin defined by settings", {"name": p, "pin": settings["pinDef"][p]})
        #                 self.pins[p] = self.settings["pinDef"][p]

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
            self.settings["pinDef"]["pcbVersion"]
        except :
            pass
        else :
            # make sure it's a valid value
            if self.settings["pinDef"]["pcbVersion"] in self.pcbVersionsAvailable :
                # store it
                self.pcbVersion = self.settings["pinDef"]["pcbVersion"]
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
            self.settings["pinDef"]
        except :
            pass
        else :
            # grab it all in
            for p in self.pins :
                # but first make sure it exists
                try :
                    self.settings["pinDef"][p]
                except :
                    pass
                else :
                    self.pins[p] = self.settings["pinDef"][p]
                    self.logger.log( "DBUG", "custom pin set", {"name": p, "pin": self.pins[p]} )

        # done
        return
