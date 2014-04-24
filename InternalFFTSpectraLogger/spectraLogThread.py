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
import cPickle

NUM_AVERAGE = 1000

NO_WRITE_MODE = True

def logSweeps(statusMessageQueue, fftDataRingBuf, ctrlNs, printQueue):


	log = logging.getLogger("Main.LogProcess")
	logSetup.initLogging(printQ = printQueue)
	loop_timer = time.time()

	logName = time.strftime("Datalog - %Y %m %d, %a, %H-%M-%S.h5", time.localtime())
	logPath = time.strftime("./Data/%Y/%m/%d/", time.localtime())

	if not os.path.exists(logPath):
		os.makedirs(logPath)

	logFQPath = os.path.join(logPath, logName)

	log.info("Logging data to %s", logFQPath)

	if not NO_WRITE_MODE:
		out = h5py.File(logFQPath, "w")

		arrWidth = 16384 + 1  # FFT Array is 16384 items wide, +1 for time-stamp

		# Main dataset - compressed, chunked, checksummed.
		dset = out.create_dataset('Spectrum_Data', (0,arrWidth), maxshape=(None,arrWidth), chunks=True, compression="gzip", fletcher32=True)

		# Cal and system status log dataset.
		calset = out.create_dataset('Acq_info', (0,1), maxshape=(None,None), dtype=h5py.new_vlen(str))


	items = []
	loopCounter = 0
	while ctrlNs.procRunning:

		if statusMessageQueue.empty() and fftDataRingBuf.getItemsNum() == 0:
			time.sleep(0.005)
		else:
			loopCounter += 1

			if NO_WRITE_MODE:
				if not statusMessageQueue.empty():
					statusMessageQueue.get()

				if not fftDataRingBuf.getItemsNum() == 0:
					ret = fftDataRingBuf.getOldest()
					if ret != False:
						pass

			else:
				tmp = statusMessageQueue.get()
				if "max" in tmp:
					items.append(tmp["max"])
				elif "settings" in tmp or "status" in tmp:

					if "settings" in tmp:
						tmp["settings"]["averaging-interval"] = NUM_AVERAGE

					data = [time.time(), tmp]

					dataPik = cPickle.dumps(data)

					calSz = calset.shape[0]
					calset.resize([calSz+1, 1])
					calset[calSz,...] = dataPik

					log.info("Status message - %s.", tmp)
					log.info("StatusTable size = %s", calset.shape)
				else:
					log.error("WAT? Unknown packet!")
					log.error(tmp)


				if len(items) == NUM_AVERAGE:

					arr = np.array(items)
					# print "Array shape = ", arr.shape
					arr = np.average(arr, axis=0)
					# print arr.shape

					dat = np.concatenate(([time.time()], arr))

					curSize = dset.shape[0]
					dset.resize(curSize+1, axis=0)
					dset[curSize,:] = dat

					out.flush()  # FLush early, flush often
					# Probably a bad idea without a SSD

					items = []

			now = time.time()
			delta = (now-loop_timer)
			if delta > 1:
				updateInterval = delta / loopCounter
				freq = 1 / updateInterval
				log.info("Elapsed Time = %0.5f, Frequency = %s", delta, freq)
				log.info("Processed FFT queue size = %s", fftDataRingBuf.getItemsNum())
				loop_timer = now
				loopCounter = 0



	if not NO_WRITE_MODE:
		out.close()



	log.info("Log-thread exiting!")
