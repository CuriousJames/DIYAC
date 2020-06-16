#!/usr/bin/env python
import os # useful for file operations
import json # for gettings settings and tokens

#
# here's a class for keeping all of the settings
class settingsHandler :
    allSettings = False

    # load all settings on initialisation
    def __init__(self) :
        successfulLoad = self.loadFromFile()
        if successfulLoad == False :
            print("Initial settings load was not successful, will stop execution")
            exit
        if self.allSettings == False :
            print("Unexpected error while initialising settigns, will stop execution")
            exit
        self.checkRoot()


    # load the settings from the settings.json file
    #  test if file exists, return if not
    #  open, return if unable
    def loadFromFile(self) :
        if os.path.exists("settings.json") != True:
            print("no settings file found")
            return(False)

        # open
        try:
            settingsFile = open("settings.json", "r")
        except OSError as err :
            print("os error while opening settings file:")
            print(err)
            return (False)
        except:
            print("unknown error while opening settings file:")
            return(False)

        # read + decode
        try:
            self.allSettings = json.load(settingsFile)
        except ValueError as err :
            print("JSON Decode error while reading settings file")
            print(err)
            return(False)
        except:
            print("unknown error while reading settings file")
            return(False)

        # close
        try:
            settingsFile.close()
        except OSError as err :
            print("os error while closing settings file:")
            print(err)
        except:
            print("unknown error while closing settings file")

        return(True)

    #
    # if root is not set, make it the same as where reader.py is
    def checkRoot(self) :
        try :
            self.allSettings["root"]
        except :
            self.allSettings["root"] = os.path.dirname(os.path.realpath(__file__))
