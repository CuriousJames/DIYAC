#!/usr/bin/env python
import time
import threading
import logging  # our own logging module
import inputHandler  # our own input handling module
import outputHandler
import tokenHandler  # our ouwn token hangling module
import settingsHandler
import pinDef  # our own pin definition module
import systemHandler
import signal  # for nice exit
import sys  # for nice exit
import subprocess
import os  # used for systemd related ops
try:
    import sdnotify
except ImportError:
    print("*** sdnotify module not installed - this is required ***\n")
    print("Please try this to install:")
    print("sudo apt-get update && sudo apt-get install python3-pip -y && sudo pip3 install sdnotify")
    exit()
try:
    import pigpio
except ImportError:
    print("*** PiGPIO not found - please run the following command to install it ***")
    print("sudo apt-get update && sudo apt-get install pigpio python-pigpio python3-pigpio\n")
    exit()
try:
    import wiegand
except ImportError:
    print("*** Wiegand.py not found - please download it and place it in the root directory for this folder ***\n")
    print("This should do the trick, assuming you're in the root directory now:")
    print("wget http://abyz.me.uk/rpi/pigpio/code/wiegand_py.zip")
    print("unzip wiegand_py.zip")
    print("rm -rf wiegand_old.py wiegand_py.zip\n")
    exit()

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
# function: cbf(gpio, level, tick)
# some code to actually run the program


#
# cleanup
# makes things clean at exit
#
def cleanup():
    l.log("DBUG", "cleanup started")

    # close the door
    try:
        outH.setDoor("closed")
    except Exception as e:
        l.log("WARN", "Unable to close the door", e)
    # release gpio resources
    try:
        pi.stop()
    except Exception as e:
        l.log("WARN", "Unable to stop PiGPIO conenction", e)
        pass


# SIGHUP handler
# to reload tokens
def sigHup_callback():
    tokens.getAllowedTokens()
    return



#
# initialisation
#
def init():
    
    # exit flag
    global flagExit
    flagExit = False

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
    l.log("NOTE", "DIYAC starting")

    # systemHandler
    global sysH
    sysH = systemHandler.systemHandler(l)
    sysH.setup("sigInt", runQuit=True)
    sysH.setup("sigTerm", runQuit=True)
    sysH.setup("sigHup", sigHup_callback, runQuit=False)
    sysH.setup("quit", cleanup)

    # get all the settings
    s = settingsHandler.settingsHandler(sysH, l)

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

    # pin definitions
    global p
    p = pinDef.pinDef(sysH, s, l)

    # output handler (settings, logger, gpio, pins
    global outH
    outH = outputHandler.outputHandler(sysH, s, l, pi, p)

    # Input handler
    global inH
    inH = inputHandler.inputHandler(sysH, s, l, tokens, outH)

    pi.set_glitch_filter(p.pins["doorbellButton"], 100000)
    pi.set_glitch_filter(p.pins["doorSensor"], 50000)

    pi.set_pull_up_down(p.pins["doorbellButton"], pigpio.PUD_UP)
    pi.set_pull_up_down(p.pins["doorSensor"], pigpio.PUD_UP)

    time.sleep(0.1)

    # register these GPIO pins to run cbf on rising or falling edge
    global cb1, cb2, cb3, cb4
    cb1 = pi.callback(p.pins["doorStrike"], pigpio.EITHER_EDGE, cbf)
    cb2 = pi.callback(p.pins["doorbell12"], pigpio.EITHER_EDGE, cbf)
    cb3 = pi.callback(p.pins["doorbellButton"], pigpio.EITHER_EDGE, cbf)
    cb4 = pi.callback(p.pins["doorSensor"], pigpio.EITHER_EDGE, cbf)

    # set the wiegand reading
    # will call function wiegandCallback on receiving data
    global w
    w = wiegand.decoder(pi, p.pins["wiegand0"], p.pins["wiegand1"], inH.wiegandCallback)

    # state ready
    sysH.notifyUp("READY=1")
    sysH.notifyUp("STATUS=Running")
    l.log("NOTE", "DIYAC running")
    import getpass
    l.log("DBUG", "Running program as user", getpass.getuser())


def keepAlive():
    # init
    global sysH
    global outH
    keepAliveCounter = 0
    # GO!
    while 1:
        # wait
        time.sleep(1)
        # flash
        outH.switchPiActiveLed()
        # hit the systemd watchdog every 10 seconds
        if keepAliveCounter == 10:
            #l.log("DBUG", "Bopity - Program still running OK")
            sysH.notifyUp("WATCHDOG=1")
            keepAliveCounter = 1
        else:
            keepAliveCounter += 1
    return
#
# callback function that is hit whenever the GPIO changes
def cbf(gpio, level, tick):
    # log
    # see if we know which pin it is
    logData = {"gpio": gpio, "level": level}
    for pin in p.pins:
        if p.pins[pin] == gpio:
            logData["name"] = pin
    l.log("DBUG", "GPIO Change", logData)

    # if it's the doorbell button, ring the doorbell
    if gpio == p.pins["doorbellButton"] and level == 0:
        ringDoorbellThread = threading.Thread(name='doorbellThread', target=outH.ringDoorbell)
        ringDoorbellThread.start()


#
# Let's start doing things
#

# run initialisation
init()

# Keep the program running to wait for callbacks
keepAlive()
