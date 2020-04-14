#!/usr/bin/env python
import time
import pigpio
import wiegand
import atexit
import threading

def cleanup():
	#pi.write(4,0)
	pi.stop()
	print "cleanly shutdown"

atexit.register(cleanup)

pi = pigpio.pi()

doorRinging=True

def init():
	global doorRinging
	pi.write(4,0)
	pi.write(17,0)
	doorRinging=False

def openDoor():
	print "opening door"
	pi.write(4,1)
	time.sleep(5)
	pi.write(4,0)
	print "door closed"

def ringDoorbell():
	global doorRinging
	if doorRinging == False:
		doorRinging=True
		print "ringing doorbell"
		pi.write(17,1)
		time.sleep(2)
		pi.write(17,0)

		time.sleep(0.1)

		pi.write(17,1)
		time.sleep(0.2)
		pi.write(17,0)

		time.sleep(0.1)

		pi.write(17,1)
		time.sleep(0.2)
		pi.write(17,0)

		doorRinging=False
		print "stopping doorbell"
	else:
		print "NOT Ringing doorbell - it's already ringing"

#openDoorThread=threading.Thread(target=openDoor)

def callback(bits, code):
	print("bits={} code={}".format(bits, code))
	if code == 111:
		openDoorThread=threading.Thread(target=openDoor)
		openDoorThread.start()
	elif code == 0:
		ringDoorbellThread=threading.Thread(target=ringDoorbell)
		ringDoorbellThread.start()
	#	if pi.read(17)==0:
	#		pi.write(17,1)
	#	else:
	#		pi.write(17,0)

def cbf(gpio, level, tick):
	print(gpio, level, tick)

init()

cb1 = pi.callback(04, pigpio.EITHER_EDGE, cbf)
cb2 = pi.callback(17, pigpio.EITHER_EDGE, cbf)

w = wiegand.decoder(pi, 14, 15, callback)

while True:
	time.sleep(9999)
	#Just keeping the python fed (slithering)
	print "boppity"
