#!/usr/bin/env python
import datetime # used for logging
import sys # for checking python type for ansi escape
import json # for outputting pretty strings from data

#
# log
#
#
# Description:
#  this makes the logging happen
#
# Level description - when selected as display or file write level all below levels are logged in addition to the selected level
#  DBUG - everthing that's happening
#  INFO - program events, token events, door events
#  WARN - anything wrong but non-fatal
#  ERRR - fatal events
#  NONE - absolutely nothing (after logging is initialised)
#
#
# Variables:
#  filePath - path to logfile
#  fileLevel - message level to to into logfile - deafult NONE
#  displayLevel - message level to go to display - default INFO
#  displayColour - whether or not to colourize display output - default FALSE
#  levelTable - levels of logging available
#  ansiEscape - ansi escape string for making colour output to terminal
#  colourLookup - list of colour stuff for each log level
#
#
# Functions:
#
#  __init__()
#   gets info from settings
#   puts relevent info into vars
#
#  log(lvl, msg, [data])
#   log message to outputs
#   only if level is above what is set in settings
#   if no settings found, will log ALL to display
#
#  setLogToDisplaySettings()
#   go through settings and get the ones related to display output
#
#  setLogToFileSettings()
#   go through settings and get the ones related to file output
#
#  inList(needle, haystack)
#   find if needle is in haystack
#   if it is, return the index
#

class logger:
        # let's have some default vars
        levelTable = ["DBUG", "INFO", "WARN", "ERRR", "NONE"]
        filePath = False
        fileLevel = "NONE"
        displayLevel = "INFO"
        displayColour = False
        ansiEscape = "\033["
        # the order must be the same as the level table, it uses the indexes
        colourLookup = [
                {
                        "colour": "0",
                        "bg": "40",
                        "style": "0"
                },
                {
                        "colour": "32",
                        "bg": "40",
                        "style": "0"
                },
                {
                        "colour": "33",
                        "bg": "40",
                        "style": "0"
                },
                {
                        "colour": "37",
                        "bg": "41",
                        "style": "0"
                }
        ]

        def __init__(self,settings) :
                # internalise settings
                self.settings = settings

                # if no settings, there's nothing more can be done
                if self.settings.allSettings == False :
                        self.log("WARN", "no settings - no logging to file, display logging will be INFO")
                        return

                # setup for logging to display
                self.setLogToDisplaySettings()
                self.setLogToFileSettings()



        def setLogToDisplaySettings(self) :
                #
                # get display settings
                #  if not exist - NONE
                #  make sure it's in the allowed list
                #

                # check if colour enabled
                try :
                        self.settings.allSettings["logging"]["display"]["colour"]
                except :
                        pass
                else :
                        # the if is only here to validate input
                        if self.settings.allSettings["logging"]["display"]["colour"] == True :
                                # set the vairbale
                                self.displayColour = True

                # make sure it exists
                try :
                        self.settings.allSettings["logging"]["display"]["level"]
                except NameError :
                        self.log("INFO","display logging level not set - no logs will be printed to stdout")
                        self.displayLevel = "NONE"
                        return

                # make sure it's in levelTable
                if self.settings.allSettings["logging"]["display"]["level"] in self.levelTable :
                        self.displayLevel = self.settings.allSettings["logging"]["display"]["level"]
                        self.log("INFO", "display logging level set", {"level": self.displayLevel})
                else :
                        self.log("WARN", "display logging level is incorrect - no more logs to stdout", {"value in settings": self.settings.allSettings["logging"]["display"]["level"]})
                        self.displayLevel = "NONE"

                # done
                return


        def setLogToFileSettings(self) :
                #
                # file logging
                # note - fileLevel is stored as temporary until the end
                # -allows log function to be used without risk of errors from logging to file before it's all setup
                #  if no level, level incorrect, or level = none there will be no logging to file
                #  if no file path - no logs
                #  change path to absolute (if it's not already)
                #  test if file can be opened and closed
                #

                # test exists
                try :
                        self.settings.allSettings["logging"]["file"]["level"]
                except NameError :
                        self.log("INFO", "file logging level not set - no logs will be printed to file")
                        self.fileLevel = "NONE"
                        return

                # temporary var for file level
                tmpFileLevel = "NONE"

                # czech in levelTable
                if self.settings.allSettings["logging"]["file"]["level"] in self.levelTable :
                        tmpFileLevel = self.settings.allSettings["logging"]["file"]["level"]
                        self.log("INFO", "file logging level set", {"level": tmpFileLevel})
                else :
                        self.fileLevel = "NONE"
                        self.log("WARN", "file logging level is incorrect in settings", {"value": self.settings.allSettings["logging"]["file"]["level"]})
                        return

                # see if it's none, if so we don't need to do anything more
                if tmpFileLevel == "NONE" :
                        return

                # test if path set
                try :
                        self.settings.allSettings["logging"]["file"]["path"]
                except NameError :
                        # not set, no log to file and return
                        self.log("WARN", "File path not set - no logs to file")
                        self.fileLevel = "NONE"
                        return
                else :
                        self.filePath = self.settings.allSettings["logging"]["file"]["path"]

                # change path to absolute if necessary
                if self.filePath[0] != "/" :
                        # still gotta test settings["root"] exists
                        try :
                                self.settings.allSettings["root"]
                        except NameError:
                                self.log("DBUG", "root dir not in settings - will use relative path for log file")
                        else :
                                self.filePath = self.settings.allSettings["root"] + self.filePath
                self.log("DBUG", "log file path set ", {"path": self.filePath})

                # open the file - this will also create the file if it doens't already exist
                try:
                        # try to open file
                        f = open(self.filePath, "a")
                except:
                        # unable to open
                        self.log("WARN", "unable to open log file - will not perform logging to file")
                        self.fileLevel = "NONE"
                        return

                # close the file
                try:
                        # try to close file
                        f.close()
                except :
                        # unable to close file
                        self.log("WARN", "unable to close log file - will not perform logging to file")
                        self.fileLevel = "NONE"
                        return

                # get out fileLevel and put it into the object
                self.fileLevel = tmpFileLevel

                # done
                return


        def log(self, lvl, msg, data="NoLoggingDataGiven") :
                # check level is in levelTable
                # get time
                # format
                # display first
                #  check level is what set or lower
                #  print
                # file second
                #  level check
                #  open
                #  write
                #  close

                # check in levelTable
                if lvl in self.levelTable :
                        pass
                else :
                        return

                # time
                isoTime = datetime.datetime.now().replace(microsecond=0).isoformat()

                # format msg
                outMsg = format(msg)

                # if data - format
                if data != "NoLoggingDataGiven" :
                        outMsg = outMsg + " - " + json.dumps(data)

                # format
                outStr = isoTime + " - [" + lvl + "] - " + outMsg

                #
                # display
                #  get levels
                #  check levels
                #   print
                #  tidy up
                if self.displayLevel != "NONE" :
                        # get indexes
                        incomingLevelNumber = self.inList(lvl, self.levelTable)
                        currentLevelNumber = self.inList(self.displayLevel, self.levelTable)
                        # compare
                        if incomingLevelNumber >= currentLevelNumber :
                                dispStr = outStr
                                if self.displayColour == True :
                                        iln = incomingLevelNumber # just to make the next line not horribly long
                                        colStr = self.ansiEscape + self.colourLookup[iln]["style"] +";"+ self.colourLookup[iln]["colour"] +";"+ self.colourLookup[iln]["bg"] +"m"
                                        dispStr = colStr + dispStr
                                        dispStr += self.ansiEscape + "0;0;0m"

                                # if incomingLevelNumber == 0:
                                #         outStr = "\033[1;37;40m"+outStr
                                # elif incomingLevelNumber == 1:
                                #         outStr="\033[1;32;40m"+outStr
                                # elif incomingLevelNumber == 2:
                                #         outStr="\033[1;33;40m"+outStr
                                # elif incomingLevelNumber == 3:
                                #         outStr="\033[0;37;41m"+outStr

                                print(dispStr)

                        # tidy up
                        del incomingLevelNumber
                        del currentLevelNumber

                #
                # file
                #  get levels
                #  check levels
                #   open
                #   write
                #   close
                if self.fileLevel != "NONE" :
                        # get indexes
                        incomingLevelNumber = self.inList(lvl, self.levelTable)
                        currentLevelNumber = self.inList(self.fileLevel, self.levelTable)
                        # compare
                        if incomingLevelNumber >= currentLevelNumber :
                                try :
                                        f = open(self.filePath, "a")
                                        f.write(outStr + "\n")
                                        f.close()
                                except :
                                        self.log("WARN","error writing to file")
                        # tidy up
                        del incomingLevelNumber
                        del currentLevelNumber


        #
        # helper function
        #  returns false if not in list
        #  returns index if it is in the list
        def inList(self, needle, haystack) :
                # do some checking
                if needle in haystack :
                        # loop through
                        i = 0
                        for x in haystack :
                                if x == needle :
                                        return i
                                else :
                                        i += 1
                else :
                        # needle is not in haystack
                        return False
