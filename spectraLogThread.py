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
import numpy as np

import h5py

import os
import os.path
import time

NUM_AVERAGE = 1000

def logSweeps(dataQueue, ctrlNs, printQueue):


	log = logging.getLogger("Main.LogProcess")
	logSetup.initLogging(printQ = printQueue)
	loop_timer = time.time()

	logName = time.strftime("Datalog - %Y %m %d, %a, %H-%M-%S.h5", time.localtime())
	logPath = time.strftime("./Data/%Y/%m/%d/", time.localtime())

	if not os.path.exists(logPath):
		os.makedirs(logPath)

	logFQPath = os.path.join(logPath, logName)

	log.info("Logging data to %s", logFQPath)
	out = h5py.File(logFQPath, "w")

	arrWidth = 16384 + 1  # FFT Array is 16384 items wide, +1 for time-stamp

	dset = out.create_dataset('Spectrum_Data', (0,arrWidth), maxshape=(None,arrWidth))
	calset = out.create_dataset('Acq_info', (0,2), maxshape=(None,2))
	items = []
	while 1:

		if not dataQueue.empty():

			tmp = dataQueue.get()

			if "max" in tmp:
				items.append(tmp["max"])
			elif "settings" in tmp:
				for key, val in tmp.iteritems():
					if isinstance(val, dict):
						val["averaging-interval"] = NUM_AVERAGE
					calset.attrs[key] = str(val)
			elif "status" in tmp:

				calset.resize(calset.shape[0]+1, axis=0)
				calset[calset.shape[0]-1,:] = [time.time(), 1]
				log.info("Recalibrated?")
			else:
				log.error("WAT? Unknown packet!")
				log.error(tmp)


		if len(items) == NUM_AVERAGE:

			arr = np.array(items)
			# print "Array shape = ", arr.shape
			arr = np.average(arr, axis=0)
			# print arr.shape

			dat = np.concatenate(([time.time()], arr))

			dset.resize(dset.shape[0]+1, axis=0)
			dset[dset.shape[0]-1,:] = dat

			out.flush()  # FLush early, flush often
			# Probably a bad idea without a SSD

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
