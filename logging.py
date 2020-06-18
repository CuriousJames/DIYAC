#!/usr/bin/env python
import datetime # used for logging
import sys # for checking python type for ansi escape
import json # for outputting pretty strings from data
import syslog

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
#  NOTE - notices that are a tad more important than INFO level (makes for good syslog without loads if INFO level stuff, eg. can have program start/close)
#  WARN - anything wrong but non-fatal
#  ERRR - fatal events
#  NONE - absolutely nothing (after logging is initialised)
#
#
# Variables:
#  levelTable - list - levels of logging available
#  syslogLevelConversion - dict - lookup for converting log level to something recognisable by syslog
#  filePath - str - path to logfile
#  fileLevel - str - message level to to into logfile - deafult NONE
#  syslogLevel - str - message level for syslog - default NOTE
#  displayLevel - str - message level to go to display - default INFO
#  displayColour - bool - whether or not to colourize display output - default FALSE
#  ansiEscape - str - ansi escape string for making colour output to terminal
#  colourLookup - list of dicts - list of colour stuff for each log level
#  settings - bool - where the settings object goes, false when no settings obj available
#
#
# Functions:
#
#  __init__([settings])
#   basic setup of useful vars
#   if settings have been given, store them and run loadSettings
#
#  loadSettings([settings])
#   if given settings, store them
#   run setLogTo***Settings functions
#
#  setLogToSyslogSettings()
#  setLogToDisplaySettings()
#  setLogToFileSettings()
#   go through settings and get the ones related to the respective outputs
#
#  log(lvl, msg, [data])
#   log message to outputs
#
#  logToSyslog(lvl, msg)
#  logToDisplay(time, lvl, msg, data)
#  logToFile(time, lvl, msg, data)
#   perform checks and log to each output
#
#  checkLevel(destination, incomingLevel)
#   checks whether an incoming message is high enough level to be logged to this destination
#   returns true if it whould be logged
#
#  dataFormat(destination, data)
#   makes incoming data into a nice string
#   will also redact any information, as specified in settings
#
#  inList(needle, haystack)
#   find if needle is in haystack
#   if it is, return the index
#

class logger:
    # let's have some default vars
    levelTable = ["DBUG", "INFO", "NOTE", "WARN", "ERRR", "NONE"]
    syslogLevelConversion = {"DBUG": syslog.LOG_DEBUG, "INFO": syslog.LOG_INFO, "NOTE": syslog.LOG_NOTICE, "WARN": syslog.LOG_WARNING, "ERRR": syslog.LOG_ERR}
    filePath = False
    fileLevel = "NONE"
    syslogLevel = "NOTE"
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
            "colour": "35",
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
    settings = False

    def __init__(self,settings=False) :
        # if there's no settings, only use defaults
        if settings == False :
            self.log("INFO", "Logger started without settings, will use defaults")
            return

        # internalise settings
        self.settings = settings

        # if no settings, there's nothing more can be done
        if self.settings.allSettings == False :
            self.log("WARN", "no settings - no logging to file, display logging will be INFO")
            return

        # do some loading
        self.loadSettings()

    def loadSettings(self, settings=False) :
        # sanity check
        if settings == False and self.settings == False :
            self.log("WARN", "logger load settings - no settings given and no settings available")
            return

        # load settings if there's new settings
        if settings != False :
            self.settings = settings

        # make some loading happen
        self.setLogToDisplaySettings()
        self.setLogToFileSettings()
        self.setLogToSyslogSettings()


    def setLogToSyslogSettings(self) :
        # this will only get the level for output to syslog
        # might have more in future
        try :
            self.settings.allSettings["logging"]["syslog"]["level"]
        except :
            pass
        else :
            # make sure it's a valid value, then set
            if self.settings.allSettings["logging"]["syslog"]["level"] in self.levelTable :
                self.syslogLevel = self.settings.allSettings["logging"]["syslog"]["level"]



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
        msg = format(msg)

        self.logToSyslog(lvl, msg)
        self.logToDisplay(isoTime, lvl, msg, data)
        self.logToFile(isoTime, lvl, msg, data)
        return


    def logToSyslog(self, lvl, msg) :
        # sanity
        if self.syslogLevel == "NONE" :
            return

        # level compare
        if self.checkLevel("syslog", lvl) == False:
            return

        # make a string
        outStr = "[" + lvl + "] " + msg
        # open / write / close
        syslog.openlog(ident="diyac", logoption=syslog.LOG_PID)
        syslog.syslog(self.syslogLevelConversion[lvl], outStr)
        syslog.closelog()

        # done
        return


    def logToDisplay(self, isoTime, lvl, msg, data) :
        # sanity
        if self.displayLevel == "NONE" :
            return

        # level compare
        if self.checkLevel("display", lvl) == False:
            return

        # make output string
        outStr = isoTime + " [" + lvl + "] " + msg

        # pretty-up the data and put into output string - if it's there
        if data != "NoLoggingDataGiven" :
            data = self.dataFormat("display", data)
            outStr += " - " + data

        # apply colour
        if self.displayColour == True :
            iln = self.inList(lvl, self.levelTable) # just to make the next line not horribly long
            colStr = self.ansiEscape + self.colourLookup[iln]["style"] +";"+ self.colourLookup[iln]["colour"] +";"+ self.colourLookup[iln]["bg"] +"m"
            outStr = colStr + outStr + self.ansiEscape + "0;0;0m"

        # do an output
        print(outStr)

        # done
        return


    def logToFile(self, isoTime, lvl, msg, data) :
        # sanity
        if self.fileLevel == "NONE" :
            return

        # level compare
        if self.checkLevel("file", lvl) == False :
            return

        # make output string
        outStr = isoTime + " [" + lvl + "] " + msg

        # pretty-up the data and put into output string - if it's there
        if data != "NoLoggingDataGiven" :
            data = self.dataFormat("display", data)
            outStr += " - " + data

        # do an output
        try :
            f = open(self.filePath, "a")
            f.write(outStr + "\n")
            f.close()
        except :
            pass


    #
    # see if the incoming message is of sufficient level to log
    #
    def checkLevel(self, destination, incomingLevel) :
        # sanity check
        if destination != "syslog" and destination != "display" and destination != "file" :
            return False

        # syslog
        if destination == "syslog" :
            currentLevelNumber = self.inList(self.syslogLevel, self.levelTable)
        # display
        if destination == "display" :
            currentLevelNumber = self.inList(self.displayLevel, self.levelTable)
        # file
        if destination == "file" :
            currentLevelNumber = self.inList(self.fileLevel, self.levelTable)

        # get number for incoming
        incomingLevelNumber = self.inList(incomingLevel, self.levelTable)

        # compare
        if incomingLevelNumber >= currentLevelNumber :
            return True

        # done, and we don't want to log the message to this destination
        return False


    #
    # format data into a nice string
    #  TODO
    #  redact things should happen here
    #
    def dataFormat(self, destination, data) :
        if destination == "syslog" :
            try :
                data = json.dumps(data)
            except :
                data = format(data)
        if destination == "display" :
            try :
                data = json.dumps(data)
            except :
                data = format(data)
        if destination == "file" :
            try :
                data = json.dumps(data)
            except :
                data = format(data)
        return data


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
