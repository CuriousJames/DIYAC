#!/usr/bin/env python
import time
import threading
import sys  # for nice exit
import subprocess
import os  # used for systemd related ops


#
# file synopsis
#
# cleanup
# nice exit
# function: init() - main script initialisation
#  settings
#  logger
#  gpio
#  tokens
#  pins
#  out
#  in
#  bind gpio callbacks
#  start iwegand
# function: keepalive()
# function: __cbf(gpio, level, tick)
# some code to actually run the program


#
# cleanup
# makes things clean at exit
#
def cleanup():
    # log
    l.log("DBUG", "cleanup started")

    # close the door
    try:
        outH.setDoor("closed")
    except Exception as e:
        l.log("WARN", "Unable to close the door", e)

    # turn off the active led
    try:
        outH.switchPiActiveLed("off")
    except Exception as e:
        l.log("WARN", "Unable to turn off active led", e)

    # release gpio resources
    try:
        pi.stop()
    except Exception as e:
        l.log("WARN", "Unable to stop PiGPIO conenction", e)
        pass

    # done
    return


# SIGHUP handler
# to reload tokens
def sigHup_callback():
    tokens.getAllowedTokens()
    return


#
# initialisation
#
def __init():
    import logging  # our own logging module
    import outputHandler
    import tokenHandler  # our ouwn token hangling module
    import settingsHandler
    import pinDef  # our own pin definition module
    import systemHandler
    import inputHandler  # our own input handling module
    try:
        import pigpio
    except ImportError:
        print("*** PiGPIO not found - please run the following command to install it ***")
        print("sudo apt-get update && sudo apt-get install pigpio python-pigpio python3-pigpio\n")
        exit()
    # exit flag
    global __flagExit
    __flagExit = False

    # get our run mode - find out if daemon
    global runMode
    # Assume runMode is normal
    runMode = "normal"

    # Confirm if it's actually running as a daemon
    for i in sys.argv:
        if i == "--daemon":
            runMode = "daemon"
            break
    if os.environ.get("LAUNCHED_BY_SYSTEMD") == "1":
        runMode = "daemon"

    # start logging
    global l
    l = logging.logger(runMode=runMode)
    del logging
    l.log("NOTE", "DIYAC starting")

    # systemHandler
    global sysH
    sysH = systemHandler.systemHandler(l)
    del systemHandler
    sysH.setup("sigInt", runQuit=True)
    sysH.setup("sigTerm", runQuit=True)
    sysH.setup("sigHup", sigHup_callback, runQuit=False)
    sysH.setup("quit", cleanup)

    # get all the settings
    s = settingsHandler.settingsHandler(sysH, l)
    del settingsHandler

    # update the logger with new settings
    l.loadSettings(s)

    # see if pigpiod is running
    # if not running
    #  try to start
    #  check again
    #  if not running
    #   exit
    # pigpiod.pi()
    # if not connected
    #  exit
    stat = subprocess.call("systemctl status pigpiod > /dev/null", shell=True)
    if stat != 0:
        l.log("WARN", "PIGPIOD is not running, will try to start")
        subprocess.call("sudo systemctl start pigpiod > /dev/null", shell=True)
        stat = subprocess.call("service pigpiod status > /dev/null", shell=True)
        if stat != 0:
            l.log("ERRR", "Unable to start pigpiod daemon")
            sysH.quit(code=1, status="Fail - PIGPIO not started and unable to start")
        else:
            l.log("INFO", "Starting pigpiod daemon successful")
    global pi
    pi = pigpio.pi()
    if not pi.connected:
        l.log("ERRR", "PiGPIO - Unable to connect")
        sysH.quit(code=1, status="Failed - unable to connect to PIGPIOD")

    # set tokens
    global tokens
    tokens = tokenHandler.tokenHandler(sysH, s, l)
    del tokenHandler

    # pin definitions
    global p
    p = pinDef.pinDef(sysH, s, l)
    del pinDef

    # output handler (settings, logger, gpio, pins
    global outH
    outH = outputHandler.outputHandler(sysH, s, l, pi, p)
    del outputHandler

    # Input handler
    global inH
    inH = inputHandler.inputHandler(sysH, s, l, tokens, outH, pi, p)
    del inputHandler

    time.sleep(0.1)

    # register these GPI pins to run __cbf on rising or falling edge
    for pin in p.pins["input"]:
        pi.callback(p.pins[pin], pigpio.EITHER_EDGE, __callbackInput)

    # register these GPO pins to run __cbf on rising or falling edge
    for pin in p.pins["output"]:
        pi.callback(p.pins[pin], pigpio.EITHER_EDGE, __callbackOutput)

    # state ready
    sysH.notifyUp("READY=1")
    sysH.notifyUp("STATUS=Running")
    l.log("NOTE", "DIYAC running", runMode)
    import getpass
    l.log("DBUG", "Running program as user", getpass.getuser())


def __keepAlive():
    keepAliveCounter = 0
    # GO!
    while 1:
        # wait
        time.sleep(1)
        # flash
        outH.switchPiActiveLed()
        # hit the systemd watchdog every 10 seconds
        if keepAliveCounter == 10:
            # l.log("DBUG", "Bopity - Program still running OK")
            sysH.notifyUp("WATCHDOG=1")
            keepAliveCounter = 1
        else:
            keepAliveCounter += 1
    return


#
# callback function that is hit whenever the GPIO changes
def __callbackGeneral(gpio, level, tick, inputOutput):
    # log
    # see if we know which pin it is
    logData = {"gpio": gpio, "level": level}
    for pin in p.pins[inputOutput]:
        if p.pins[pin] == gpio:
            logData["name"] = pin
            # Break out of the for loop as soon as we've found it (if we find it)
            break
    if inputOutput == "input":
        logMsg = "GPI Change"
    else:
        logMsg = "GPO Change"
    l.log("DBUG", logMsg, logData)
    return logData["name"]


#
# callback function that is hit whenever the GPI changes
def __callbackInput(gpi, level, tick):
    gpiName = __callbackGeneral(gpi, level, tick, "input")

    inH.gpiCallback(gpi, level, tick, gpiName)


#
# callback function that is hit whenever the GPO changes
def __callbackOutput(gpio, level, tick):
    if gpio == p.pins["piActiveLed"]:
        # Do nothing with piActiveLed - as it really clogs up the log
        return
    gpoName = __callbackGeneral(gpio, level, tick, "output")

    outH.gpoCallback(gpio, level, tick, gpoName)


#
# Let's start doing things
#

# run initialisation
__init()

# Keep the program running to wait for callbacks
__keepAlive()
