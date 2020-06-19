# DIYAC - Do-It-Yourself Access Control #
## Warning! ##
This is very much a work in progress - we are still developing this as a personal hobby
## Purpose ##
This python code allows a Raspberry Pi to be used to allow access to a door using a Wiegand keypad/ RFID reader, and a door strike
It also rings a doorbell in a (possibly) nice fashion
Also included in 'Extras' is the [Fritzing](https://fritzing.org/) pcb/breadboard design
## Pre-requisits ##
* Raspberry Pi (ideally 2 or up)
* Wiegand.py put in the root directory (as obtained from: [Abyz.me.uk](http://abyz.me.uk/rpi/pigpio/code/wiegand_py.zip))
* Enable PiGPIO on the Pi (just do this once and it will start automatically on boot) `sudo systemctl enable pigpiod`
* allow sudo group to run systemctl start pigpiod without password
* sd_notify python library. Can be installed with apt-get install python-sdnotify
## Settings ##
- root - str - optional, default to where reader.py is - path to project root
- allowedTokens - obj
  - path - str - optional, default will not allow any entry - path to allowedTokens.json file, can be absolute or relative
- modules - not used anymore
- logging - obj
  - syslog - obj
    - level - str - optional, default NOTE - log level for syslog
  - display - obj
    - level - str - optional, default INFO - log level for display output
    - colour - bool - optional, default FALSE - whether display output should be in colour or not
  - file - obj
    - level - str - optional, defalt NONE - log level for file output
    - path - str - required for logging to file - path to log file
- pinDef - obj
  - pcbVersion - float - optional - pcb version being used, for pin assignments
  - doorStrike - int - optional - gpio number
  - doorbell12 - int - optional - gpio number
  - doorbellCc - int - optional - gpio number
  - readerLed - int - optional - gpio number
  - readerBuzz - int - optional - gpio number
  - doorbellButton - int - optional - gpio number
  - doorSensor - int - optional - gpio number
  - piActiveLed - int - optional - gpio number
  - spareLed - int - optional - gpio number
  - wiegand0 - int - optional - gpio number
  - wiegand1 - int - optional - gpio number
- inputHandling - obj
  - delimiter - str - optional, default "#" - start/stop character for keypad entry
  - timeout - float - optional, default 5 - seconds between keypad button presses before timeout
  - bruteforceThresholdTime - float - optional, default 20 - seconds for number of attempts before lockout
  - bruteforceThresholdAttempts - int - optional, default 3 - number of attempts within threshold time that will start lockout
  - overspeedThresholdTime - float - minimum number of seconds between ench key press or card read
  - lockoutTime - float - optional, default 600 - seconds that a lockout will last
- outputHandling - obj
  - doorOpenTime - float - optional, default 5 - seconds that the door strike will be open for on access granted
  - doorbellCcTime - float - optional, default 0.1 - seconds that doorbell contact closure will be closed/opened for
  
## AllowedTokens ##
Each entry in this list must contain 3 items:
- token - str - token number/keypad code
- type - str - "code", "card" - what the token is for, card or keypad code
- user - str - optional, but it would be silly to leave blank - name of user

The token handler takes hex tokens and changes them to lowercase and removes colons. This means hex tokens can be upper or lower case, and can include colons or not.

## logging ##
Log levels are as follows:
- DBUG - lots of debug messages (most verbose)
- INFO - informational level
- NOTE - notices, mainly start and stop execution
- WARN - non critical, but should be looked at
- ERRR - critical problem
- NONE - no output (least verbose)

All levels are equivalent to linux syslog levels.

## Resources ##
Systemd integration - https://www.freedesktop.org/software/systemd/man/systemd.service.html
