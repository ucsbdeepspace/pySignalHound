# -*- coding: UTF-8 -*-

# Wrapper for Test-Equipment-Plus's "SignalHound" series of USB spectrum analysers.
#
# Written By Connor Wolf <wolf@imaginaryindustries.com>
#

#  * ----------------------------------------------------------------------------
#  * "THE BEER-WARE LICENSE":
#  * Connor Wolf <wolf@imaginaryindustries.com> wrote this file. As long as you retain
#  * this notice you can do whatever you want with this stuff. If we meet some day,
#  * and you think this stuff is worth it, you can buy me a beer in return.
#  * (Only I don't drink, so a soda will do). Connor
#  * Also, support the Signal-Hound devs. Their hardware is pretty damn awesome.
#  * ----------------------------------------------------------------------------
#


import logSetup
import logging
import time
import traceback
import numpy as np


NUM_AVERAGE = 500

def logSweeps(dataQueue, ctrlNs):


	log = logging.getLogger("Main.LogPlugin")
	logSetup.initLogging()
	loop_timer = time.time()


	out = open("dat.log", "wb")

	items = []
	while 1:

		if not dataQueue.empty():
			items.append(dataQueue.get()["max"])

		if len(items) == NUM_AVERAGE:

			arr = np.array(items)
			# print "Array shape = ", arr.shape
			arr = np.average(arr, axis=0)
			# print arr.shape

			outStr = ""
			outStr = "%s, " % time.time()
			outStr += " ".join(['%f,' % num for num in arr])
			outStr = outStr.rstrip(", ").lstrip(", ")
			outStr += "\n"

			out.write(outStr)

			items = []

			now = time.time()
			delta = now-loop_timer
			freq = 1 / (delta)
			log.info("Elapsed Time = %0.5f, Frequency = %s", delta, freq)
			loop_timer = now

		if ctrlNs.acqRunning == False:
			log.info("Stopping Sweep-thread!")
			break


	out.close()

	log.info("Log-thread exiting!")
	dataQueue.close()
	dataQueue.join_thread()
