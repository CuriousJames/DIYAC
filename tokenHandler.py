#!/usr/bin/env python
import os # useful for file operations
import json # for gettings settings and tokens

#
# Tokens
#
# Description:
#  basically for getting, storing and comparing tokens
#
# Vars:
#  allowedTokens - list of allowed tokens - default False
#
# Functions:
#
#  __init__(settings, logger)
#   store settigns and logger internally for later use
#   run getAllowedTokens()

#  getAllowedTokens()
#
class tokenHandler :
    # vars
    allowedTokens = False


    #
    # initialisation function
    # just sets vars for settings and logger
    #
    def __init__(self, settings, logger) :
        self.settings = settings
        self.logger = logger
        self.getAllowedTokens()


    #
    # function to make var of allowed tokens
    #  reads file
    #  changes all hex values to lower case without ":"
    #  changes mifare ultralight tokens to what will be received by reader - not implemented yet
    #
    def getAllowedTokens(self):
        # if no settings
        ## exit function
        #
        # set file path
        #
        # if tokens file exists
        ## open/read+decode/close
        ## set allowedTokens
        ## if problem
        ### error handling
        ### return
        #
        # if no tokens file
        ## error handling
        ## return
        #
        # remove ":" from all tokens
        # make all tokens lower case

        # if settings haven't worked, return
        if self.settings.allSettings == False:
            self.logger.log("WARN", "no settings - will not get allowedTokens")
            return

        # check file path exists
        # if relative, make absolute
        # open / read / decode / close
        try :
            self.settings.allSettings["allowedTokens"]["path"]
        except :
            self.logger.log("WARN", "Allowed tokens file path not set in settings")
            return

        if self.settings.allSettings["allowedTokens"]["path"][0] != "/" :
            allowedTokensFilePath = self.settings.allSettings["root"] + self.settings.allSettings["allowedTokens"]["path"]
        else :
            allowedTokensFilePath = self.settings.allSettings["allowedTokens"]["path"]

        # open / read / decode / close
        if os.path.exists(allowedTokensFilePath) :
            # open
            try:
                allowedTokensFile = open(allowedTokensFilePath, "r")
            except OSError as err :
                self.logger.log("WARN", "os error while opening allowedTokens file", err)
            except:
                self.logger.log("WARN", "unknown error while opening allowedTokens file")
                return

            # read + decode
            try:
                self.allowedTokens = json.load(allowedTokensFile)
            except ValueError as err :
                self.logger.log("WARN", "JSON Decode error while reading allowedTokens file", err)
            except:
                self.logger.log("WARN", "unknown error while reading/decoding allowedTokens file")

            # close
            try:
                allowedTokensFile.close()
            except OSError as err :
                self.logger.log("WARN", "os error while closing allowedTokens file:", err)
            except:
                self.logger.log("WARN", "unknown error while closing allowedTokens file")

        else:
            self.logger.log("WARN", "allowedTokens file does not exist")
            return

        # do some actions on our new shiny list of tokens
        self.formatTokens()
        self.transformOverlengthTokens()
        self.removeDuplicateTokens()
        self.logger.log("DBUG", "allowedTokens", self.allowedTokens)
        return


    #
    # format token values
    #  remove ":"
    #  make lowercase
    def formatTokens(self) :
        # remove ":" and make lowercase
        if self.allowedTokens != False :
            for token in self.allowedTokens :
                token["value"] = token["value"].replace(":", "")
                token["value"] = token["value"].lower()
        return


    #
    # for mifare ultralight and other tokens that are more than 4 bytes long
    #
    def transformOverlengthTokens(self) :
        # Perform transform for mifare ultralight
        if self.allowedTokens != False :
            for token in self.allowedTokens :
                #
                # do some transforming here
                # Wiegand readers ONLY read the first 3 bytes from cards with more than 4 bytes of ID
                # So we need to transform the ID to what the reader is capable of reading (and how it reads it - it reads '88' and then the first 3 bytes)
                if len(token["value"]) >8:
                    token["value"] = "88" + token["value"][:6]
        return

    #
    # remove duplicate tokens
    #  because having duplicates would be bad
    def removeDuplicateTokens(self) :
        #  i and j are both index counters
        #  iterate allowed tokens
        #   iterate again to compare
        #    if token values match, types match, and it's not the same entry, and it's not already listed in duplicateIndexes
        #     log
        #     add to index
        #  if there are duplicates listed in the index
        #   iterate
        #    delete the duplicates

        # die if nothing there
        if self.allowedTokens == False :
            return
        # initialise
        duplicateIndexes = []
        # main iterate
        i = 0
        for original in self.allowedTokens :
            # second iterate
            j = 0
            for check in self.allowedTokens:
                # if tokens match, types match, it's not the same entry, and not listed in duplicate indexes
                if original["value"] == check["value"] and original["type"] == check["type"] and i != j  and i not in duplicateIndexes:
                    # log - it only takes 3 lines because it wou;'dnt nicely fit on one
                    logData = {"token": self.allowedTokens[j]["value"], "type": self.allowedTokens[j]["type"], "user": self.allowedTokens[j]["user"]}
                    self.logger.log("WARN", "Duplicate token found in allowedTokens file", logData)
                    del logData
                    # append duplicate username to original username
                    self.allowedTokens[i]["user"] += " DOR " + self.allowedTokens[j]["user"]
                    # add to list of duplicates
                    duplicateIndexes.append(j)

                j += 1
            i += 1

        # if there's duplicates listed, delete them
        if not duplicateIndexes :
            pass
        else:
            duplicateIndexes.sort(reverse=True) # have to sort and do from the highest index first
            for dup in duplicateIndexes :
                del self.allowedTokens[dup]

        # done
        return


    #
    # check incoming code against list of allowed tokens
    #  if match, open door
    #  if not match, shoot whoever entered it
    def checkToken(self, rx, rxType) :
        if self.allowedTokens == False :
            self.logger.log("INFO", "ACCESS DENIED - no available tokens list")
            return

        for t in self.allowedTokens :
            if t["type"] == rxType :
                if t["value"] == rx :
                    return {"allow": True, "user": t["user"]}
        # all done
        return {"allow": False}
