#!/usr/bin/env python
import datetime  # used for logging
import json  # for outputting pretty strings from data
import syslog
import re  # for redacting data
import sys # for stdout writing

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
#  __levelTable - list - levels of logging available
#  __syslogLevelConversion - dict - lookup for converting log level to something recognisable by syslog
#  __filePath - str - path to logfile
#  __fileLevel - str - message level to to into logfile - deafult NONE
#  __syslogLevel - str - message level for syslog - default NOTE
#  __displayLevel - str - message level to go to display - default INFO
#  __displayColour - bool - whether or not to colourize display output - default FALSE
#  __ansiEscape - str - ansi escape string for making colour output to terminal
#  __colourLookup - list of dicts - list of colour stuff for each log level
#  __settings - bool - where the settings object goes, false when no settings obj available
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
#  __setLogToSysLogSettings()
#  __setLogToDisplaySettings()
#  __setLogToFileSettings()
#   go through settings and get the ones related to the respective outputs
#
#  log(lvl, msg, [data])
#   log message to outputs
#
#  __logToSysLog(lvl, msg)
#  __logToDisplay(time, lvl, msg, data)
#  __logToFile(time, lvl, msg, data)
#   perform checks and log to each output
#
#  __checkLevel(destination, incomingLevel)
#   checks whether an incoming message is high enough level to be logged to this destination
#   returns true if it whould be logged
#
#  __dataFormat(destination, data)
#   makes incoming data into a nice string
#   will also redact any information, as specified in settings
#
#  __inList(needle, haystack)
#   find if needle is in haystack
#   if it is, return the index
#


class logger:
    # let's have some default vars
    __levelTable = ["DBUG", "INFO", "NOTE", "WARN", "ERRR", "NONE"]
    __syslogLevelConversion = {"DBUG": syslog.LOG_DEBUG, "INFO": syslog.LOG_INFO, "NOTE": syslog.LOG_NOTICE, "WARN": syslog.LOG_WARNING, "ERRR": syslog.LOG_ERR}
    __filePath = False
    __fileLevel = "NONE"
    __syslogLevel = "NOTE"
    __displayLevel = "INFO"
    __displayColour = False
    __ansiEscape = "\033["
    # the order must be the same as the level table, it uses the indexes
    __colourLookup = [
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
    __settings = False

    def __init__(self, settings=False, runMode="normal"):
        # run mode - stop output to display
        self.__runMode = runMode
        if self.__runMode == "daemon":
            self.__displayLevel = "NONE"

        # if there's no settings, only use defaults
        if settings is False:
            self.log("INFO", "Logger started without settings, will use defaults")
            return

        # internalise settings
        self.__settings = settings

        # if no settings, there's nothing more can be done
        if self.__settings.allSettings is False:
            self.log("WARN", "no settings - no logging to file, display logging will be INFO")
            return

        # do some loading
        self.loadSettings()

    def loadSettings(self, settings=False):
        # sanity check
        if settings is False and self.__settings is False:
            self.log("WARN", "logger load settings - no settings given and no settings available")
            return

        # load settings if there's new settings
        if settings is not False:
            self.__settings = settings

        # make some loading happen
        self.__setLogToDisplaySettings()
        self.__setLogToFileSettings()
        self.__setLogToSysLogSettings()

    def __setLogToSysLogSettings(self):
        # this will only get the level for output to syslog
        # might have more in future
        try:
            self.__settings.allSettings["logging"]["syslog"]["level"]
        except:
            pass
        else:
            # make sure it's a valid value, then set
            if self.__settings.allSettings["logging"]["syslog"]["level"] in self.__levelTable:
                self.__syslogLevel = self.__settings.allSettings["logging"]["syslog"]["level"]

    def __setLogToDisplaySettings(self):
        #
        # get display settings
        #  if not exist - NONE
        #  make sure it's in the allowed list
        #

        # if running as a daemon - none
        if self.__runMode == "daemon":
            self.__displayLevel = "NONE"
            return

        # check if colour enabled
        try:
            self.__settings.allSettings["logging"]["display"]["colour"]
        except:
            pass
        else:
            # the if is only here to validate input
            if self.__settings.allSettings["logging"]["display"]["colour"] is True:
                # set the vairbale
                self.__displayColour = True

        # make sure it exists
        try:
            self.__settings.allSettings["logging"]["display"]["level"]
        except NameError:
            self.log("INFO", "display logging level not set - no logs will be printed to stdout")
            self.__displayLevel = "NONE"
            return

        # make sure it's in __levelTable
        if self.__settings.allSettings["logging"]["display"]["level"] in self.__levelTable:
            self.__displayLevel = self.__settings.allSettings["logging"]["display"]["level"]
            self.log("INFO", "display logging level set", {"level": self.__displayLevel})
        else:
            self.log("WARN", "display logging level is incorrect - no more logs to stdout", {"value in settings": self.__settings.allSettings["logging"]["display"]["level"]})
            self.__displayLevel = "NONE"

        # done
        return

    def __setLogToFileSettings(self):
        #
        # file logging
        # note - __fileLevel is stored as temporary until the end
        # -allows log function to be used without risk of errors from logging to file before it's all setup
        #  if no level, level incorrect, or level = none there will be no logging to file
        #  if no file path - no logs
        #  change path to absolute (if it's not already)
        #  test if file can be opened and closed
        #

        # test exists
        try:
            self.__settings.allSettings["logging"]["file"]["level"]
        except NameError:
            self.log("INFO", "file logging level not set - no logs will be printed to file")
            self.__fileLevel = "NONE"
            return

        # temporary var for file level
        tmpFileLevel = "NONE"

        # czech in __levelTable
        if self.__settings.allSettings["logging"]["file"]["level"] in self.__levelTable:
            tmpFileLevel = self.__settings.allSettings["logging"]["file"]["level"]
            self.log("INFO", "file logging level set", {"level": tmpFileLevel})
        else:
            self.__fileLevel = "NONE"
            self.log("WARN", "file logging level is incorrect in settings", {"value": self.__settings.allSettings["logging"]["file"]["level"]})
            return

        # see if it's none, if so we don't need to do anything more
        if tmpFileLevel == "NONE":
            return

        # test if path set
        try:
            self.__settings.allSettings["logging"]["file"]["path"]
        except NameError:
            # not set, no log to file and return
            self.log("WARN", "File path not set - no logs to file")
            self.__fileLevel = "NONE"
            return
        else:
            self.__filePath = self.__settings.allSettings["logging"]["file"]["path"]

        # change path to absolute if necessary
        if self.__filePath[0] != "/":
            # still gotta test settings["root"] exists
            try:
                self.__settings.allSettings["root"]
            except NameError:
                self.log("DBUG", "root dir not in settings - will use relative path for log file")
            else:
                self.__filePath = self.__settings.allSettings["root"] + self.__filePath
        self.log("DBUG", "log file path set ", {"path": self.__filePath})

        # open the file - this will also create the file if it doens't already exist
        try:
            # try to open file
            f = open(self.__filePath, "a")
        except:
            # unable to open
            self.log("WARN", "unable to open log file (" + self.__filePath + ")- will not perform logging to file")
            self.__fileLevel = "NONE"
            return

        # close the file
        try:
            # try to close file
            f.close()
        except:
            # unable to close file
            self.log("WARN", "unable to close log file - will not perform logging to file")
            self.__fileLevel = "NONE"
            return

        # get out __fileLevel and put it into the object
        self.__fileLevel = tmpFileLevel

        # done
        return

    def log(self, lvl, msg, data="NoLoggingDataGiven"):
        # check level is in __levelTable
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

        # check in __levelTable
        if lvl in self.__levelTable:
            pass
        else:
            self.log("WARN", "logging: message sent with incorrect level", {"level": lvl, "message": msg})
            return

        # time
        isoTime = datetime.datetime.now().replace(microsecond=0).isoformat()

        # format msg
        msg = format(msg)

        self.__logToSysLog(lvl, msg)
        self.__logToDisplay(isoTime, lvl, msg, data)
        self.__logToFile(isoTime, lvl, msg, data)
        return

    def __logToSysLog(self, lvl, msg):
        # sanity
        if self.__syslogLevel == "NONE":
            return

        # level compare
        if self.__checkLevel("syslog", lvl) is False:
            return

        # make a string
        outStr = "[" + lvl + "] " + msg
        # open / write / close
        syslog.openlog(ident="diyac", logoption=syslog.LOG_PID)
        syslog.syslog(self.__syslogLevelConversion[lvl], outStr)
        syslog.closelog()

        # done
        return

    def __logToDisplay(self, isoTime, lvl, msg, data):
        # sanity
        if self.__displayLevel == "NONE":
            return

        # level compare
        if self.__checkLevel("display", lvl) is False:
            return

        # make output string
        outStr = isoTime + " [" + lvl + "] " + msg

        # pretty-up the data and put into output string - if it's there
        if data != "NoLoggingDataGiven":
            data = self.__dataFormat("display", data)
            outStr += " - " + data

        # apply colour
        if self.__displayColour is True:
            iln = self.__inList(lvl, self.__levelTable)  # just to make the next line not horribly long
            colStr = self.__ansiEscape + self.__colourLookup[iln]["style"] + ";" + self.__colourLookup[iln]["colour"] + ";" + self.__colourLookup[iln]["bg"] + "m"
            outStr = colStr + outStr + self.__ansiEscape + "0;0;0m"

        # do an output
        sys.stdout.write(outStr + "\n")

        # done
        return

    def __logToFile(self, isoTime, lvl, msg, data):
        # sanity
        if self.__fileLevel == "NONE":
            return

        # level compare
        if self.__checkLevel("file", lvl) is False:
            return

        # make output string
        outStr = isoTime + " [" + lvl + "] " + msg

        # pretty-up the data and put into output string - if it's there
        if data != "NoLoggingDataGiven":
            data = self.__dataFormat("file", data)
            outStr += " - " + data

        # do an output
        try:
            f = open(self.__filePath, "a")
            f.write(outStr + "\n")
            f.close()
        except:
            pass

    #
    # see if the incoming message is of sufficient level to log
    #
    def __checkLevel(self, destination, incomingLevel):
        # syslog
        if destination == "syslog":
            currentLevelNumber = self.__inList(self.__syslogLevel, self.__levelTable)
        # display
        elif destination == "display":
            currentLevelNumber = self.__inList(self.__displayLevel, self.__levelTable)
        # file
        elif destination == "file":
            currentLevelNumber = self.__inList(self.__fileLevel, self.__levelTable)
        # sanity check
        else:
            return False

        # get number for incoming
        incomingLevelNumber = self.__inList(incomingLevel, self.__levelTable)

        # compare
        if incomingLevelNumber >= currentLevelNumber:
            return True
        # done, and we don't want to log the message to this destination
        else:
            return False

    def __dataRedact(self, redactList, data):
        redactWord = "-REDACTED-"
        for redactKey in redactList:
            regex = r"\"" + redactKey + r"\":\s\"([^\"]+)\""
            subst = "\"" + redactKey + "\": \"" + redactWord + "\""
            data = re.sub(regex, subst, data)
        return data

    #
    # format data into a nice string
    #  TODO
    #  redact things should happen here
    #
    def __dataFormat(self, destination, data):
        if destination == "display" or destination == "file":
            try:
                data = json.dumps(data)
                loggingSetting = self.__settings.allSettings.get("logging")
                # If there is a logging section in settings...
                if loggingSetting:
                    redactList = self.__settings.allSettings["logging"].get("redact")
                    # If there is a global redact list apply it
                    if redactList:
                        data = self.__dataRedact(redactList, data)

                    destSetting = self.__settings.allSettings["logging"].get(destination)
                    if destSetting:
                        redactList = destSetting.get("redact")
                        # If destination redact list exists, apply it
                        if redactList:
                            data = self.__dataRedact(redactList, data)
            except:
                data = format(data)
        else:
            self.log("WARN", "Logging - Unable to format data - destination not specified")
            return False
        return data

    #
    # helper function
    #  returns false if not in list
    #  returns index if it is in the list
    def __inList(self, needle, haystack):
        # do some checking
        if needle in haystack:
            # loop through
            i = 0
            for x in haystack:
                if x == needle:
                    return i
                else:
                    i += 1
        else:
            # needle is not in haystack
            return False
