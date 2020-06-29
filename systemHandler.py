#!/usr/bin/env python
import signal  # for nice exit
try:
    import sdnotify  # For systemd
except ImportError:
    l.log("ERRR", "sdnotify module not installed - this is required\nPlease try this to install:\nsudo apt-get update && sudo apt-get install python3-pip -y && sudo pip3 install sdnotify")
    exit()

#
# System Handler
#
# Description:
#  Deal with signal inputs
#    run log/systemd notify
#    run specified callback
#    run quit if specified
#  stop execution in a nice way
#    log/systemd notify
#    run speficied callback
#    exit with given code
#
# Variables:
#  for each signal, a dict exists with callback function, exit code and runQuit
#  sigInt
#  sigTerm
#  sigHup
#  quitFunc is similar to above, but does not contain runQuit
#  logger - obj - for the logger
#  notify - obj - for the sdNotify
#
# Functions:
#
#  __init__(logger)
#   saves logger inernally
#   makes sdNotify and saves internally
#
#  setup(type, _callback, code, runQuit)
#   saves settings for callback function, exit code, runQuit
#   type must be quit, sigInt, sigTerm, sigHup
#
#  sigIntHandler(sig, frame)
#   log/notify (different if going to runQuit or not)
#   run callback function
#   run quit if appropriate
#
#  sigTermHandler(sig, frame)
#   same as the last one
#
#  sigHupHandler(sig, frame)
#   log/Notify
#    if not going to quit, this will notify RELOADING=1
#   run callback
#   if not going to quit, notify READY=1
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
    sigInt = {
        "callback": False,
        "code": 0,
        "runQuit": True
    }
    sigTerm = {
        "callback": False,
        "code": 0,
        "runQuit": True
    }
    sigHup = {
        "callback": False,
        "code": 0,
        "runQuit": False
    }
    quitFunc = {
        "callback": False,
        "code": 0
    }
    logger = False

    #
    # init
    #
    def __init__(self, logger=False):
        # systemd notifier
        self.notify = sdnotify.SystemdNotifier()
        self.logger = logger
        return

    #
    # set listen for sig/quit
    # define callback from main code
    def setup(self, type, _callback=False, code=False, runQuit=False):
        # not a switch statment
        if type == "quit":
            self.logger.log("DBUG", "Setup for quit function", {"callback": _callback, "code": code})
            self.quitFunc["callback"] = _callback
            self.quitFunc["code"] = code
            pass
        elif type == "sigInt":
            self.logger.log("DBUG", "Setup for sigInt", {"callback": _callback, "code": code, "runQuit": runQuit})
            signal.signal(signal.SIGINT, self.sigIntHandler)
            self.sigInt["callback"] = _callback
            self.sigInt["code"] = code
            self.sigInt["runQuit"] = runQuit
            pass
        elif type == "sigTerm":
            self.logger.log("DBUG", "Setup for sigTerm", {"callback": _callback, "code": code, "runQuit": runQuit})
            signal.signal(signal.SIGTERM, self.sigTermHandler)
            self.sigTerm["callback"] = _callback
            self.sigTerm["code"] = code
            self.sigTerm["runQuit"] = runQuit
            pass
        elif type == "sigHup":
            self.logger.log("DBUG", "Setup for sigHup", {"callback": _callback, "code": code, "runQuit": runQuit})
            signal.signal(signal.SIGHUP, self.sigHupHandler)
            self.sigHup["callback"] = _callback
            self.sigHup["code"] = code
            self.sigHup["runQuit"] = runQuit
            pass
        else:
            # default?
            self.logger.log("WARN", "systemHandler: invalid type passed to setCallback", type)
            pass
        return

    #
    # individual handler functions
    #
    def sigIntHandler(self, sig, frame):
        # log/systemd notify
        if self.sigInt["runQuit"] is True:
            self.notify.notify("STOPPING=1")
            self.logger.log("NOTE", "SIGINT - Service Stop received, will exit")
            pass
        else:
            self.logger.log("NOTE", "SIGINT received")
            pass
        # callback func
        if self.sigInt["callback"] is not False:
            self.sigInt["callback"]()
            pass
        # quit
        if self.sigInt["runQuit"] is True:
            self.quit(self.sigInt["code"])
            pass
        # done
        return

    def sigTermHandler(self, sig, frame):
        # log/systemd notify
        if self.sigTerm["runQuit"] is True:
            self.notify.notify("STOPPING=1")
            self.logger.log("NOTE", "SIGTERM - Service Stop received, will exit")
            pass
        else:
            self.logger.log("NOTE", "SIGTERM received")
            pass
        # callback func
        if self.sigTerm["callback"] is not False:
            self.sigTerm["callback"]()
            pass
        # quit
        if self.sigTerm["runQuit"] is True:
            self.quit(self.sigTerm["code"])
            pass
        # done
        return

    def sigHupHandler(self, sig=False, frame=False):
        # if quit
        if self.sigHup["runQuit"] is True:
            # log/systemd notify
            self.notify.notify("STOPPING=1")
            self.logger.log("NOTE", "SIGHUP - will quit")
            pass
        # if not quit
        else:
            # log/systemd notify
            self.notify.notify("RELOADING=1")
            self.logger.log("NOTE", "SIGHUP - Service Reload received")
            pass
        # callback
        if self.sigHup["callback"] is not False:
            self.sigHup["callback"]()
            pass
        # if quit
        if self.sigHup["runQuit"] is True:
            self.quit(self.sigHup["code"])
        else:
            self.notify.notify("READY=1")
        # done
        return

    def quit(self, code, status=False, logLevel=False, logMessage=False, logData=False):
        # run the callback
        if self.quitFunc["callback"] is not False:
            self.quitFunc["callback"]()
            pass
        # stopping to systemd
        self.notify.notify("STOPPING=1")
        # status to systemd
        if status is not False:
            self.notify.notify("STATUS="+status)
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
                self.logger.log(logLevel, logMessage)
                pass
            else:
                self.logger.log(logLevel, logMessage, logData)
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
        self.notify.notify(message)
        return
