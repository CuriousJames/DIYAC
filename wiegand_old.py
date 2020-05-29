#!/usr/bin/env python

import pigpio

class decoder:

   """
   A class to read Wiegand codes of an arbitrary length.

   The code length and value are returned.

   EXAMPLE

   #!/usr/bin/env python

   import time

   import pigpio

   import wiegand

   def callback(bits, code):
      print("bits={} code={}".format(bits, code))

   pigpio.start()

   w = wiegand.decoder(14, 15, callback)

   time.sleep(300)

   w.cancel()

   pigpio.stop()
   """

   def __init__(self, gpio_0, gpio_1, callback, bit_timeout=5):

      """
      Instantiate with the gpio for 0 (green wire), the gpio for 1 (white wire),
      the callback function, and the bit timeout in milliseconds which indicates
      the end of a code.

      The callback is passed the code length in bits and the value.
      """

      self.gpio_0 = gpio_0
      self.gpio_1 = gpio_1

      self.callback = callback

      self.bit_timeout = bit_timeout

      self.in_code = False

      pigpio.set_mode(gpio_0, pigpio.INPUT)
      pigpio.set_mode(gpio_1, pigpio.INPUT)

      pigpio.set_pull_up_down(gpio_0, pigpio.PUD_UP)
      pigpio.set_pull_up_down(gpio_1, pigpio.PUD_UP)

      self.cb_0 = pigpio.callback(gpio_0, pigpio.FALLING_EDGE, self._cb)
      self.cb_1 = pigpio.callback(gpio_1, pigpio.FALLING_EDGE, self._cb)

   def _cb(self, gpio, level, tick):

      """
      Accumulate bits until both gpios 0 and 1 timeout.
      """

      if level < pigpio.TIMEOUT:

         if self.in_code == False:
            self.bits = 1
            self.num = 0

            self.in_code = True
            self.code_timeout = 0
            pigpio.set_watchdog(self.gpio_0, self.bit_timeout)
            pigpio.set_watchdog(self.gpio_1, self.bit_timeout)
         else:
            self.bits += 1
            self.num = self.num << 1

         if gpio == self.gpio_0:
            self.code_timeout = self.code_timeout & 2 # clear gpio 0 timeout
         else:
            self.code_timeout = self.code_timeout & 1 # clear gpio 1 timeout
            self.num = self.num | 1

      else:

         if self.in_code:

            if gpio == self.gpio_0:
               self.code_timeout = self.code_timeout | 1 # timeout gpio 0
            else:
               self.code_timeout = self.code_timeout | 2 # timeout gpio 1

            if self.code_timeout == 3: # both gpios timed out
               pigpio.set_watchdog(self.gpio_0, 0)
               pigpio.set_watchdog(self.gpio_1, 0)
               self.in_code = False
               self.callback(self.bits, self.num)

   def cancel(self):

      """
      Cancel the Wiegand decoder.
      """

      self.cb_0.cancel()
      self.cb_1.cancel()

if __name__ == "__main__":

   import time

   import pigpio

   import wiegand

   def callback(bits, value):
      print("bits={} value={}".format(bits, value))

   pigpio.start()

   w = wiegand.decoder(14, 15, callback)

   time.sleep(300)

   w.cancel()

   pigpio.stop()

