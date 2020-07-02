#!/usr/bin/env python
import signal  # for nice exit


#
# System Handler
#
# Description:
#  Deal with signal inputs
#    run log/systemd __notify
#    run specified callback
#    run quit if specified
#  stop execution in a nice way
#    log/systemd __notify
#    run speficied callback
#    exit with given code
#
# Variables:
#  for each signal, a dict exists with callback function, exit code and runQuit
#  __sigInt
#  __sigTerm
#  __sigHup
#  __quitFunc is similar to above, but does not contain runQuit
#  __logger - obj - for the __logger
#  __notify - obj - for the sdNotify
#
# Functions:
#
#  __init__(__logger)
#   saves __logger inernally
#   makes sdNotify and saves internally
#
#  setup(type, _callback, code, runQuit)
#   saves settings for callback function, exit code, runQuit
#   type must be quit, __sigInt, __sigTerm, __sigHup
#
#  __sigIntHandler(sig, frame)
#   log/__notify (different if going to runQuit or not)
#   run callback function
#   run quit if appropriate
#
#  __sigTermHandler(sig, frame)
#   same as the last one
#
#  __sigHupHandler(sig, frame)
#   log/Notify
#    if not going to quit, this will __notify RELOADING=1
#   run callback
#   if not going to quit, __notify READY=1
#   run quit if appropriate
#
#  quit(code, status, logLevel, logMessage, logData)
#   run callback
#   sdNotify
#   log (if appropriate)
#   exit with given code
#
#  notifyUp(message)
#   just does an sdNotify


class systemHandler:

    # vars
    __sigInt = {
        "callback": False,
        "code": 0,
        "runQuit": True
    }
    __sigTerm = {
        "callback": False,
        "code": 0,
        "runQuit": True
    }
    __sigHup = {
        "callback": False,
        "code": 0,
        "runQuit": False
    }
    __quitFunc = {
        "callback": False,
        "code": 0
    }
    __logger = False

    #
    # init
    #
    def __init__(self, logger=False):
        self.__logger = logger
        del logger

        try:
            import sdnotify  # For systemd
        except ImportError:
            self.__logger.log("ERRR", "sdnotify module not installed - this is required\nPlease try this to install:\nsudo apt-get update && sudo apt-get install python3-pip -y && sudo pip3 install sdnotify")
            exit()
        # systemd notifier
        self.__notify = sdnotify.SystemdNotifier()
        return

    #
    # set listen for sig/quit
    # define callback from main code
    def setup(self, type, _callback=False, code=False, runQuit=False):
        # not a switch statment
        if type == "quit":
            self.__logger.log("DBUG", "Setup for quit function", {"callback": _callback, "code": code})
            self.__quitFunc["callback"] = _callback
            self.__quitFunc["code"] = code
            pass
        elif type == "sigInt":
            self.__logger.log("DBUG", "Setup for sigInt", {"callback": _callback, "code": code, "runQuit": runQuit})
            signal.signal(signal.SIGINT, self.__sigIntHandler)
            self.__sigInt["callback"] = _callback
            self.__sigInt["code"] = code
            self.__sigInt["runQuit"] = runQuit
            pass
        elif type == "sigTerm":
            self.__logger.log("DBUG", "Setup for sigTerm", {"callback": _callback, "code": code, "runQuit": runQuit})
            signal.signal(signal.SIGTERM, self.__sigTermHandler)
            self.__sigTerm["callback"] = _callback
            self.__sigTerm["code"] = code
            self.__sigTerm["runQuit"] = runQuit
            pass
        elif type == "sigHup":
            self.__logger.log("DBUG", "Setup for sigHup", {"callback": _callback, "code": code, "runQuit": runQuit})
            signal.signal(signal.SIGHUP, self.__sigHupHandler)
            self.__sigHup["callback"] = _callback
            self.__sigHup["code"] = code
            self.__sigHup["runQuit"] = runQuit
            pass
        else:
            # default?
            self.__logger.log("WARN", "systemHandler: invalid type passed to setCallback", type)
            pass
        return

    #
    # individual handler functions
    #
    def __sigIntHandler(self, sig, frame):
        # log/systemd __notify
        if self.__sigInt["runQuit"] is True:
            self.__notify.notify("STOPPING=1")
            self.__logger.log("NOTE", "SIGINT - Service Stop received, will exit")
            pass
        else:
            self.__logger.log("NOTE", "SIGINT received")
            pass
        # callback func
        if self.__sigInt["callback"] is not False:
            self.__sigInt["callback"]()
            pass
        # quit
        if self.__sigInt["runQuit"] is True:
            self.quit(self.__sigInt["code"])
            pass
        # done
        return

    def __sigTermHandler(self, sig, frame):
        # log/systemd __notify
        if self.__sigTerm["runQuit"] is True:
            self.__notify.notify("STOPPING=1")
            self.__logger.log("NOTE", "SIGTERM - Service Stop received, will exit")
            pass
        else:
            self.__logger.log("NOTE", "SIGTERM received")
            pass
        # callback func
        if self.__sigTerm["callback"] is not False:
            self.__sigTerm["callback"]()
            pass
        # quit
        if self.__sigTerm["runQuit"] is True:
            self.quit(self.__sigTerm["code"])
            pass
        # done
        return

    def __sigHupHandler(self, sig=False, frame=False):
        # if quit
        if self.__sigHup["runQuit"] is True:
            # log/systemd __notify
            self.__notify.notify("STOPPING=1")
            self.__logger.log("NOTE", "SIGHUP - will quit")
            pass
        # if not quit
        else:
            # log/systemd __notify
            self.__notify.notify("RELOADING=1")
            self.__logger.log("NOTE", "SIGHUP - Service Reload received")
            pass
        # callback
        if self.__sigHup["callback"] is not False:
            self.__sigHup["callback"]()
            pass
        # if quit
        if self.__sigHup["runQuit"] is True:
            self.quit(self.__sigHup["code"])
        else:
            self.__notify.notify("READY=1")
        # done
        return

    def quit(self, code, status=False, logLevel=False, logMessage=False, logData=False):
        # run the callback
        if self.__quitFunc["callback"] is not False:
            self.__quitFunc["callback"]()
            pass
        # stopping to systemd
        self.__notify.notify("STOPPING=1")
        # status to systemd
        if status is not False:
            self.__notify.notify("STATUS="+status)
            pass
        # log
        if logMessage is not False or logData is not False:
            # level
            if logLevel is False:
                logLevel = "NOTE"
                pass
            # message
            if logMessage is False:
                logMessage = "Quitting"
                pass
            # do it
            if logData is False:
                self.__logger.log(logLevel, logMessage)
                pass
            else:
                self.__logger.log(logLevel, logMessage, logData)
                pass
        # exit
        if code is False:
            exit(0)
            pass
        else:
            exit(code)
            pass
        return

    def notifyUp(self, message):
        self.__notify.notify(message)
        return
