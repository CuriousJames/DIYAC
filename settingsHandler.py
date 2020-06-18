#!/usr/bin/env python
import os # useful for file operations
import sys
import json # for gettings settings and tokens

#
# here's a class for keeping all of the settings
class settingsHandler :
    allSettings = False


    # load all settings on initialisation
    def __init__(self, logger=False) :
        # sort out the logger
        self.logger = logger

        # load the stuff
        successfulLoad = self.loadFromFile()

        # see if it worked
        if successfulLoad == False :
            self.log("ERRR", "Initial settings load was not successful, will stop execution")
            sys.exit(1)
        if self.allSettings == False :
            self.log("ERRR", "Unexpected error while initialising settigns, will stop execution")
            sys.exit(1)

        # work out root - set if unset
        self.checkRoot()


    # load the settings from the settings.json file
    #  test if file exists, return if not
    #  open, return if unable
    def loadFromFile(self) :
        if os.path.exists("settings.json") != True:
            self.log("WARN", "no settings file found")
            return(False)

        # open
        try:
            settingsFile = open("settings.json", "r")
        except OSError as err :
            self.log("ERRR", "os error while opening settings file", err)
            return (False)
        except:
            self.log("ERRR", "unknown error while opening settings file")
            return(False)

        # read + decode
        try:
            self.allSettings = json.load(settingsFile)
        except ValueError as err :
            self.log("ERRR", "JSON Decode error while reading settings file", err)

            return(False)
        except:
            self.log("ERRR", "unknown error while reading settings file")
            return(False)

        # close
        try:
            settingsFile.close()
        except OSError as err :
            self.log("ERRR", "os error while closing settings file", err)
        except:
            self.log("ERRR", "unknown error while closing settings file")

        return(True)

    #
    # if root is not set, make it the same as where reader.py is
    def checkRoot(self) :
        try :
            self.allSettings["root"]
        except :
            print
            self.allSettings["root"] = os.path.dirname(os.path.realpath(__file__))



    #
    # down and dirty logger
    # just in case there wasan't a logger available
    def log(self, lvl, msg, data="NoDataHere") :
        if self.logger == False :
            outStr = "[" + lvl + "] " + msg
            if data != "NoDataHere" :
                outStr += " - " + format(data)
            print(outStr)
        else :
            if data == "NoDataHere" :
                self.logger.log(lvl, msg)
            else :
                self.logger.log(lvl, msg, data)

        return
