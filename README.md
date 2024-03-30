# DIYAC - Do-It-Yourself Access Control #

- [DIYAC - Do-It-Yourself Access Control](#diyac---do-it-yourself-access-control)
  - [Warning](#warning)
  - [Purpose](#purpose)
  - [Pre-requisits](#pre-requisits)
  - [Installing the service](#installing-the-service)
  - [Settings](#settings)
  - [AllowedTokens](#allowedtokens)
  - [Logging](#logging)
  - [Resources](#resources)

## Warning ##

This is a work in progress as a personal hobby, however it has been running without any problems for the project owners use 24/7 for over a year.

That said of course, use at your own risk.

## Purpose ##

This python code allows a Raspberry Pi to be used to allow access to a door using a Wiegand keypad/ RFID reader, and a door strike
It also rings a doorbell in a (possibly) nice fashion
Also included in 'Extras' is the [Fritzing](https://fritzing.org/) pcb/breadboard design

## Pre-requisits ##

- Hardware
  - Raspberry Pi (ideally 2 or up)
- Software
  - Install raspbian legacy 64bit lite (as you don't need a desktop env) with the raspberry pi imager
  - Update your pi
    ```
    sudo apt update && sudo apt dist-upgrade
    ```
  - This repository
    ```
    sudo apt install git && git clone https://github.com/CuriousJames/DIYAC.git && cd DIYAC
    ```
  - Wiegand.py put in the project directory (as obtained from: [Abyz.me.uk](http://abyz.me.uk/rpi/pigpio/code/wiegand_py.zip))
    ```
    wget http://abyz.me.uk/rpi/pigpio/code/wiegand_py.zip && unzip wiegand_py.zip && rm -rf wiegand_py.zip && rm -rf wiegand_old.py
    ```
  - Enable PiGPIO on the Pi (just do this once and it will start automatically on boot)
    ```
    sudo apt-get update && sudo apt-get install pigpio python-pigpio python3-pigpio && sudo systemctl enable pigpiod
    ```
  - SD Notify
    - with pip3
      ```
      sudo apt-get update && sudo apt-get install python3-pip && sudo pip3 install sdnotify
      ```
    - with apt
      ```
      sudo apt install python3-sdnotify
      ```
- Config
  - Create DIYAC user, diable login and add to sudoers group
    ```
    sudo useradd -M diyac && sudo usermod -L diyac
    ```

## Installing the service ##

The hard way (hopefully there will be a script to do this and more soon!)

1. If '/home/pi/diyac' IS your diyac folder location:
   ```
   cp /home/pi/DIYAC/diyac.service_example /home/pi/DIYAC/diyac.service && sudo systemctl link /home/pi/DIYAC/diyac.service && sudo systemctl enable diyac.service
   ```
1. If '/home/pi/diyac' is NOT your diyac folder location:
     1. change the 'ExecStart' line in 'diyac.service' to 'ExecStart=/usr/bin/python3 /your/diyac/folder/location/main.py'
     2.
     ```
     sudo systemctl link /your/diyac/folder/location/diyac.service
     ```
2.
  ```
  sudo systemctl enable diyac.service
  ```
3.
  ```
  sudo reboot
  ```
4. Done - The service will now run on startup of the Pi

## Settings ##

Settings are stored in settings.json which **must** be made by the user - you may copy settings.json_example to get you started if you wish.

This is the structure of the settings.json file:

- root - str - optional, defaults to where main.py is - path to project root
- allowedTokens - obj
  - path - str - optional, default will not allow any entry - path to allowedTokens.json file, can be absolute or relative
- wiegandLength - int - optional, default 34 - number of bits that the wiegand reader will spit out
- modules - not used anymore
- logging - obj
    - redact - obj - optional, keys to redact (globally)
      - keys to redact - str
  - syslog - obj
    - level - str - optional, default NOTE - log level for syslog
  - display - obj
    - level - str - optional, default INFO - log level for display output
    - colour - bool - optional, default FALSE - whether display output should be in colour or not
    - redact - obj - optional, keys to redact
      - keys to redact - str
  - file - obj
    - level - str - optional, defalt NONE - log level for file output
    - path - str - required for logging to file - path to log file
    - redact - obj - optional, keys to redact
      - keys to redact - str
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
  - exitButton - int - optional - gpio number
- inputHandling - obj
  - delimiter - str - optional, default "#" - start/stop character for keypad entry
  - timeout - float - optional, default 5 - seconds between keypad button presses before timeout
  - bruteforceThresholdTime - float - optional, default 20 - seconds for number of attempts before lockout
  - bruteforceThresholdAttempts - int - optional, default 3 - number of bad (denied) token access attempts within threshold time that are allowed before lockout starts (so if it is 3 then the fourth attempt will be denied, and the lockout will start)
  - overspeedThresholdTime - float - minimum number of seconds between ench key press or card read
  - lockoutTime - float - optional, default 600 - seconds that a lockout will last (for both brute forces & overspeed inputs)
  - doorSensorOpen - binary - set to 1 if level reads '1' when door is open, otherwise set to '0'
- outputHandling - obj
  - doorOpenTime - float - optional, default 5 - seconds that the door strike will be open for on access granted
  - doorbellCcTime - float - optional, default 0.1 - seconds that doorbell contact closure will be closed/opened for
  
## AllowedTokens ##

Allowed (or authorised) tokens are stored in allowedTokens.json which **must** be made by the user - you may copy allowedTokens.json_example to get you started if you wish.

This file is how you store what tokens (be they cards or codes) are allowed to enter the door

Each entry in this list must contain 3 items:

- token - str - token number/keypad code
- type - str - "code", "card" - what the token is for, card or keypad code
- user - str - optional, but it would be silly to leave blank - name of user

The token handler takes hex tokens and changes them to lowercase and removes colons. This means hex tokens can be upper or lower case, and can include colons or not.

## Logging ##

Log levels are as follows:

- DBUG - lots of debug messages (most verbose)
- INFO - informational level
- NOTE - notices, mainly start and stop execution
- WARN - non critical, but should be looked at
- ERRR - critical problem
- NONE - no output (least verbose)

All levels are equivalent to linux syslog levels.

### Redacting ###

It is possible to redact values of a specified key, by key name, in the logged 'data' (it does NOT redact the message)

So if you want to redact all values of the key 'token' you can add 'token' to the global or destination (display or file) context in settings and then no token values will display -REDACTED- and nothing else, see settings.json_example for it's implementation

# code notes #

## systemHandler ##

Because systemHandler is designed to be used by various things, it's a bit flexible.
Importantly, the quit function and signal handlers can be set up with a callback, so that project specific instructions can be defined in the main body of code without having to change anything within systemHandler (hopefully)

## Resources ##

Systemd integration - <https://www.freedesktop.org/software/systemd/man/systemd.service.html>
