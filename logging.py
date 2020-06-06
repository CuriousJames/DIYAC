import datetime # used for logging

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
#  filePath
#  fileLevel
#  displayLevel
#  levelTable
#
#
# Functions:
#
#  __init__()
#   gets info from settings
#   puts relevent info into vars
#
#  write(lvl, msg, [data])
#   write message to outputs
#   only if level is above what is set in settings
#   if no settings found, will log ALL to display
#

class logger:
        def __init__(self,settings) :
                # get information out of settings
                # create some useful vars

                # levelTable
                self.levelTable = ["DBUG", "INFO", "WARN", "ERRR", "NONE"]

                # default set : no output to file, full output to display
                self.filePath = False
                self.fileLevel = "NONE"
                self.displayLevel = "ERRR"

                # if no settings, there's nothing more can be done
                if settings == False :
                        print("no settings - all logs will be printed to stdout")
                        return

                #
                # get display settings
                #  if not exist - NONE
                #  make sure it's in the allowed list
                #

                # flag - false if problem, no subsequent operations will be done
                tmpDisplayLog = True

                # make sure it exists
                try :
                        settings["logging"]["display"]["level"]
                except NameError :
                        self.displayLevel = "NONE"
                        tmpDisplayLog = False
                        print("display logging level not set - no logs will be printed to stdout")

                # make sure it's in levelTable
                if tmpDisplayLog == True :
                        if settings["logging"]["display"]["level"] in self.levelTable :
                                self.displayLevel = settings["logging"]["display"]["level"]
                                print("display logging level set to "+settings["logging"]["display"]["level"])
                        else :
                                self.displayLevel = "NONE"
                                print("display logging level is incorrect - no more logs to stdout")

                # delete flag
                del tmpDisplayLog

                #
                # file logging
                #  if no level, level incorrect, or level = none there will be no logging to file
                #  if no file path - no logs
                #  change path to absolute (if it's not already)
                #  test if file can be opened and closed
                #

                # flag - false if error, do not do subsequent operations
                tmpFileLog = True

                # test exists
                try :
                        settings["logging"]["file"]["level"]
                except NameError :
                        self.fileLevel = "NONE"
                        tmpFileLog = False
                        print("file logging level not set - no logs will be printed to file")

                # czech in levelTable
                if tmpFileLog == True :
                        if settings["logging"]["file"]["level"] in self.levelTable :
                                self.fileLevel = settings["logging"]["file"]["level"]
                                print("file logging level set to "+settings["logging"]["file"]["level"])
                        else :
                                self.fileLevel = "NONE"
                                print("file logging level is incorrect - no logs to file")

                # see if it's none
                if tmpFileLog == True:
                        if self.fileLevel == "NONE" :
                                tmpFileLog = False

                # test if path set
                if tmpFileLog == True :
                        try :
                                settings["logging"]["file"]["path"]
                        except NameError :
                                self.fileLevel = "NONE"
                                tmpFileLog = False
                                print("File path not set - no logs to file")
                        else :
                                self.filePath = settings["logging"]["file"]["path"]

                # change path to absolute if necessary
                if tmpFileLog == True and self.fileLevel != "NONE" :
                        if self.filePath[0] != "/" :
                                # still gotta test settings["root"] exists
                                try :
                                        settings["root"]
                                except NameError:
                                        print("root dir not in settings - will use relative path for log file")
                                else :
                                        self.filePath = settings["root"] + self.filePath
                        print("log file: "+self.filePath)

                # try opening and closing the file
                if tmpFileLog == True :
                        try:
                                # try to open file
                                f = open(self.filePath, "a")
                        except:
                                # unable to open
                                print("unable to open log file - will not perform logging to file")
                                self.fileLevel = "NONE"
                                tmpFileLog = False

                        if tmpFileLog == True :
                                try:
                                        # try to close file
                                        f.close()
                                except :
                                        # unable to close file
                                        print("unable to close log file - will not perform logging to file")
                                        self.fileLevel = "NONE"
                                        tmpFileLog = False

                # double check - if flag is false but level is not NONE, something has gone wonky
                if tmpFileLog == False and self.fileLevel != "NONE" :
                        print("error while setting up file log - discrepancy found")
                        self.fileLevel = "NONE"


        def write(self, lvl, msg, data="NoLoggingDataGiven") :
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
                        outMsg = outMsg + " - " + format(data)

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
                                print(outStr)
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
                                        print("error writing to file")
                        # tidy up
                        del incomingLevelNumber
                        del currentLevelNumber



        #
        # helper function
        #  returns false if not in list
        #  returns index if it is in the list
        def inList(self, needle, haystack) :
                # check if haystack is a list
                #if type(haystack) != "list" :
                #        return False

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
                        return false