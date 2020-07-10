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
    for i in sys.argv:
        if i == "--daemon":
            runMode = "daemon"
        else:
            runMode = "normal"
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

    # register these GPIO pins to run __cbf on rising or falling edge
    # global cb1, cb2, cb3, cb4
    cb1 = pi.callback(p.pins["doorStrike"], pigpio.EITHER_EDGE, __cbf)
    cb2 = pi.callback(p.pins["doorbell12"], pigpio.EITHER_EDGE, __cbf)
    cb3 = pi.callback(p.pins["doorbellButton"], pigpio.EITHER_EDGE, __cbf)
    cb4 = pi.callback(p.pins["doorSensor"], pigpio.EITHER_EDGE, __cbf)

    # state ready
    sysH.notifyUp("READY=1")
    sysH.notifyUp("STATUS=Running")
    l.log("NOTE", "DIYAC running")
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
def __cbf(gpio, level, tick):
    # log
    # see if we know which pin it is
    logData = {"gpio": gpio, "level": level}
    for pin in p.pins:
        if p.pins[pin] == gpio:
            logData["name"] = pin
            # Break out of the for loop as soon as we've found it (if we find it)
            break
    l.log("DBUG", "GPIO Change", logData)

    # if it's the doorbell button, ring the doorbell
    if gpio == p.pins["doorbellButton"] and level == 0:
        ringDoorbellThread = threading.Thread(name='doorbellThread', target=outH.ringDoorbell)
        ringDoorbellThread.start()


#
# Let's start doing things
#

# run initialisation
__init()

# Keep the program running to wait for callbacks
__keepAlive()
