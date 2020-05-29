#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading

def cleanup():
	# This next bit doesn't work - we're looking into how to make it work so the door isn't left open if the script exits prematurely
	#pi.write(doorStrike,0)
	pi.stop()
	print("cleanly shutdown")

atexit.register(cleanup)

pi = pigpio.pi()

doorRinging=True
#GPIO Variables so we don't have to remember pin numbers!
doorStrike=17
doorbell12=4
doorbellCc=26
readerLed=27
readerBuzz=22
doorbellButton=5
doorSensor=6
piActiveLed=13
spareLed=19
wiegand1=14
wiegand2=15

def init():
	global doorRinging
	pi.write(doorStrike,0)
	pi.write(doorbell12,0)
	doorRinging=False

def openDoor():
	print("opening door")
	pi.write(doorStrike,1)
	time.sleep(5)
	pi.write(doorStrike,0)
	print("door closed")

def ringDoorbell():
	global doorRinging
	if doorRinging == False:
		doorRinging=True
		print("ringing doorbell")
		pi.write(doorbell12,1)
		time.sleep(2)
		pi.write(doorbell12,0)

		time.sleep(0.1)

		pi.write(doorbell12,1)
		time.sleep(0.2)
		pi.write(doorbell12,0)

		time.sleep(0.1)

		pi.write(doorbell12,1)
		time.sleep(0.2)
		pi.write(doorbell12,0)

		doorRinging=False
		print("stopping doorbell")
	else:
		print("NOT Ringing doorbell - it's already ringing")

def callback(bits, code):
	print("bits={} code={}".format(bits, code))

	# old stuff
	#
	#if code == 111:
	#	openDoorThread=threading.Thread(target=openDoor)
	#	openDoorThread.start()
	#elif code == 0:
	#	ringDoorbellThread=threading.Thread(target=ringDoorbell)
	#	ringDoorbellThread.start()

	#
	# New stuff
	## if bits != 4 AND bits != 34
	### error
	#
	## if bits == 34, it's a card token
	### convert to binary string
	### trim "0b", start parity bit, end parity bit
	### re order bytes
	### convert to hex
	### compare against list
	#
	## if bits == 4
	### if code = 0
	#### ring doorbell
	### else
	#### do something else

	##
	## error condition
	if bits != 34 and bits != 4:
		print("error")

	##
	## we have a card
	if bits == 34:
		input = str(format(code, '#036b')) # make binary string
		input = input[3:]  # trim '0b' and first parity bit
		input = input[:-1] # trim last parity bit
		# print(input)
		output = input[24:] + input[16:24] + input[8:16] + input[:8] # re-order bytes
		output = int(output, 2) # change to integer - required for doing the change to hex
		output = format(output, '#010x') # make hex string
		output = output[2:] # trim "0x"
		print(output)

	##
	## someone pressed a button
	if bits == 4:
		## if 0 pressed - ring doorbell
		## this is only for testing things
		if code == 0:
			ringDoorbellThread=threading.Thread(target=ringDoorbell)
			ringDoorbellThread.start()

def cbf(gpio, level, tick):
	print(gpio, level, tick)

init()

cb1 = pi.callback(doorStrike, pigpio.EITHER_EDGE, cbf)
cb2 = pi.callback(doorbell12, pigpio.EITHER_EDGE, cbf)

w = wiegand.decoder(pi, wiegand1, wiegand2, callback)

while True:
	time.sleep(9999)
	#Just keeping the python fed (slithering)
	print("boppity")