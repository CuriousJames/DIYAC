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
