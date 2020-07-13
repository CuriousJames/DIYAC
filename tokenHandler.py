#!/usr/bin/env python
import os  # useful for file operations
import json  # for gettings settings and tokens

#
# Tokens
#
# Description:
#  basically for getting, storing and comparing tokens
#
# Vars:
#  __allowedTokens - dict- list of allowed tokens - default False
#  __wiegandLength - int - number of bits that wiegand will read
#
# Functions:
#
#  __init__(systemHandler, settings, logger)
#   store settigns and logger internally for later use
#   run getAllowedTokens()
#
#  __getWiegandLength()
#   get from __settings if the reader is 26 or 34 bit
#
#  getAllowedTokens()
#   load tokens from file
#   perform validity/sanity/other checks
#   store tokens
#
#  __loadFromFile()
#   load tokens in from file specified in __settings
#
#  moveValueToToked()
#   for backwards compatibility
#   any tokens that are stored under "value" will be moved under "token"
#
#  __sanitiseAllowedTokens
#   remove any entries from allowedTokes that are not set or otherwise invalid
#
#  __formatTokens()
#   remove ":" and make uppercase
#
#  __transformOverlengthTokens()
#   for ultraligh and other tokens that are more than 4 bytes long
#   becuase 24 bit wiegand won't return correct values
#
#  __transformFor26()
#   if __wiegandLength is 26, trim the ends off all card tokens that are 8 chars long
#
#  __removeDuplicateTokens()
#   does exactly what it says on the tin
#
#  checkToken(token, tokenType)
#   return true if given token is in __allowedTokens
#   otherwise return false


class tokenHandler:
    # vars
    __allowedTokens = False
    __wiegandLength = 36

    #
    # initialisation function
    # just sets vars for __settings and __logger
    #
    def __init__(self, systemHandler, settings, logger):
        # internalise everything
        self.__systemHandler = systemHandler
        del systemHandler
        self.__settings = settings
        del settings
        self.__logger = logger
        del logger
        self.__getWiegandLength()
        self.getAllowedTokens()

        # done
        return

    def __getWiegandLength(self):
        # see if it exists
        try:
            self.__settings.allSettings["__wiegandLength"]
        except Exception:
            return

        # grab into tmp for quicker writing
        tmp = self.__settings.allSettings["__wiegandLength"]

        # check sanity
        if tmp != 26 and tmp != 34:
            self.__logger.log("WARN", "Token handler: Incorrect value in __settings file for __wiegandLength", {"__wiegandLength": tmp})
            return

        # it's sane, store it
        self.__wiegandLength = tmp
        self.__logger.log("DBUG", "Token handler: new setting", {"__wiegandLength": self.__wiegandLength})

        # done
        return

    #
    # function to make var of allowed tokens
    #  reads file
    #  changes all hex values to upper case without ":"
    #  changes mifare ultralight tokens to what will be received by reader - not implemented yet
    #
    def getAllowedTokens(self):
        # if no __settings
        #  exit function
        # get tokens from file
        # move "value" to "token" - backward compatibility with older version of __allowedTokens file
        # remove ":" from all tokens
        # make all tokens upper case
        # chenge tokens that are too long for the reader
        #  TODO - this might have to be changed to be reader dependant
        #         if reader only does 26 bit wiegand for example
        # remove duplicates

        # if __settings haven't worked, return
        if self.__settings.allSettings is False:
            self.__logger.log("WARN", "no __settings - will not get __allowedTokens")
            return

        # get the tokens from the file
        self.__loadFromFile()

        # do some actions on our new shiny list of tokens
        self.__moveValueToToken()
        self.__sanitiseAllowedTokens()
        self.__formatTokens()
        self.__transformOverlengthTokens()
        self.__transformFor26()
        self.__removeDuplicateTokens()
        self.__logger.log("DBUG", "allowedTokens: loaded list of tokens", self.__allowedTokens)
        return

    def __loadFromFile(self):
        # set file path
        #
        # if tokens file exists
        #  open/read+decode/close
        #  set __allowedTokens
        #  if problem
        #   error handling
        #   return
        #
        # if no tokens file
        #  error handling
        #  return

        # check file path exists
        # if relative, make absolute
        # open / read / decode / close
        try:
            self.__settings.allSettings["allowedTokens"]["path"]
        except Exception as err:
            self.__logger.log("WARN", "Allowed tokens file path not set in settings", err)
            return

        if self.__settings.allSettings["allowedTokens"]["path"][0] != "/":
            allowedTokensFilePath = self.__settings.allSettings["root"] + self.__settings.allSettings["allowedTokens"]["path"]
        else:
            allowedTokensFilePath = self.__settings.allSettings["allowedTokens"]["path"]

        # open / read / decode / close
        if os.path.exists(allowedTokensFilePath):
            # open
            try:
                allowedTokensFile = open(allowedTokensFilePath, "r")
            except OSError as err:
                self.__logger.log("WARN", "os error while opening allowedTokensFile", err)
            except Exception as err:
                self.__logger.log("WARN", "unknown error while opening allowedTokensFile", err)
                return

            # read + decode
            try:
                self.__allowedTokens = json.load(allowedTokensFile)
            except ValueError as err:
                self.__logger.log("WARN", "JSON Decode error while reading allowedTokensFile", err)
            except Exception as err:
                self.__logger.log("WARN", "unknown error while reading/decoding allowedTokensFile", err)

            # close
            try:
                allowedTokensFile.close()
            except OSError as err:
                self.__logger.log("WARN", "os error while closing allowedTokensFile:", err)
            except Exception as err:
                self.__logger.log("WARN", "unknown error while closing allowedTokensFile", err)
        else:
            self.__logger.log("WARN", "allowedTokensFile does not exist")
            return

    #
    # key change
    #  up a semitone
    #  don't worry, it's a music joke
    # move all keys of "value" to "token"
    # backwards compatibility
    def __moveValueToToken(self):
        # sanity
        if self.__allowedTokens is False:
            return

        # iterate
        for i in self.__allowedTokens:
            # if value exists, copy to token and then delete
            if "value" in i:
                i["token"] = i["value"]
                del i["value"]

        return

    #
    # __sanitiseAllowedTokens
    #  remove from __allowedTokens if no token set
    #  remove from __allowedTokens if token is not a string of length > 0
    #  remove from __allowedTokens if no type set
    #  add empty user string if user not set
    #
    def __sanitiseAllowedTokens(self):
        # sanity
        if self.__allowedTokens is False:
            return

        indexesToDelete = []

        # check for no or invalid token
        counter = 0
        for i in self.__allowedTokens:
            # if token not set
            if "token" not in i:
                indexesToDelete.append(counter)
                self.__logger.log("WARN", "allowedTokens - entry without token, will not be used", i)
            # if token is empty string
            if "token" in i:
                if i["token"] == "":
                    indexesToDelete.append(counter)
                    self.__logger.log("WARN", "allowedTokens - entry with token of 0 length, will not be used", i)
            counter += 1

        # if entries have been marked for delete, DELETE THEM
        if not indexesToDelete:
            pass
        else:
            indexesToDelete.sort(reverse=True)  # have to sort and do from the highest index first
            for ind in indexesToDelete:
                del self.__allowedTokens[ind]

        # user cleaning
        for i in self.__allowedTokens:
            if "user" not in i:
                i["user"] = "USER NOT GIVEN"
                self.__logger.log("WARN", "allowedTokens - user not set", i)

        # done
        return

    #
    # format token values
    #  remove ":"
    #  make uppercase
    def __formatTokens(self):
        if self.__allowedTokens is False:
            return
        # remove ":" and make uppercase
        for tkn in self.__allowedTokens:
            # check token is there
            if "token" not in tkn:
                continue
            # do the operation
            tkn["token"] = tkn["token"].replace(":", "")
            tkn["token"] = tkn["token"].upper()
        return

    #
    # for mifare ultralight and other tokens that are more than 4 bytes long
    #
    def __transformOverlengthTokens(self):
        if self.__allowedTokens is False:
            return
        # Perform transform for mifare ultralight
        for tkn in self.__allowedTokens:
            # check token is there
            if "token" not in tkn:
                continue
            #
            # do some transforming here
            # Wiegand readers ONLY read the first 3 bytes from cards with more than 4 bytes of ID
            # So we need to transform the ID to what the reader is capable of reading (and how it reads it - it reads '88' and then the first 3 bytes)
            if len(tkn["token"]) > 8:
                tkn["token"] = "88" + tkn["token"][:6]
        return

    #
    # remove duplicate tokens
    #  because having duplicates would be bad
    def __removeDuplicateTokens(self):
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
        if self.__allowedTokens is False:
            return

        # initialise
        duplicateIndexes = []

        # main iterate
        i = 0
        for original in self.__allowedTokens:
            # second iterate
            j = 0
            for check in self.__allowedTokens:
                # check token is there
                if "token" not in original or "token" not in check:
                    continue
                # if tokens match, types match, it's not the same entry, and not listed in duplicate indexes
                if original["token"] == check["token"] and original["type"] == check["type"] and i != j and i not in duplicateIndexes:
                    # log - it only takes 3 lines because it wou;'dnt nicely fit on one
                    logData = {"token": self.__allowedTokens[j]["token"], "type": self.__allowedTokens[j]["type"], "user": self.__allowedTokens[j]["user"]}
                    self.__logger.log("WARN", "allowedTokens - duplicate token found", logData)
                    del logData
                    # append duplicate username to original username
                    self.__allowedTokens[i]["user"] += " DOR " + self.__allowedTokens[j]["user"]
                    # add to list of duplicates
                    duplicateIndexes.append(j)

                j += 1
            i += 1

        # if there's duplicates listed, delete them
        if not duplicateIndexes:
            pass
        else:
            duplicateIndexes.sort(reverse=True)  # have to sort and do from the highest index first
            for dup in duplicateIndexes:
                del self.__allowedTokens[dup]

        # done
        return

    def __transformFor26(self):
        # make sure we've got tokens to act on
        if self.__allowedTokens is False:
            return

        # make sure we need to do this in the first place
        if self.__wiegandLength != 26:
            return

        # iterate
        # if type is card and length is the length we want
        for t in self.__allowedTokens:
            if t["type"] == "card" and len(t["token"]) == 8:
                t["token"] = t["token"][0:6]
                pass
            pass

        # done
        return

    #
    # check incoming code against list of allowed tokens
    #  if match, open door
    #  if not match, shoot whoever entered it
    def checkToken(self, rx, rxType):
        if self.__allowedTokens is False:
            self.__logger.log("INFO", "ACCESS DENIED - no available tokens list")
            return {"allow": False}

        for t in self.__allowedTokens:
            if t["type"] == rxType:
                if t["token"] == rx:
                    return {"allow": True, "user": t["user"]}
        # all done
        return {"allow": False}
