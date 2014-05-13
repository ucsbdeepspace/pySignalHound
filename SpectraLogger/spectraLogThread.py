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

from settings import NUM_AVERAGE

def logSweeps(dataQueue, ctrlNs, printQueue):


	log = logging.getLogger("Main.LogProcess")
	logSetup.initLogging(printQ = printQueue)
	loop_timer = time.time()

	logName = time.strftime("Datalog - %Y %m %d, %a, %H-%M-%S.h5", time.localtime())
	logPath = time.strftime("../Data/%Y/%m/%d/", time.localtime())

	if not os.path.exists(logPath):
		os.makedirs(logPath)

	logFQPath = os.path.join(logPath, logName)

	log.info("Logging data to %s", logFQPath)
	out = h5py.File(logFQPath, "w")


	# the size of the acquisiton array can vary. Therefore, we wait for the acq thread to send a message containing
	# the array size before allocating the HDF5 array.
	while 1:

		if dataQueue.empty():
			time.sleep(0.005)
		else:
			tmp = dataQueue.get()
			if "arrSize" in tmp:
				log.info("Have array size for acquisition. Creating HDF5 file and starting logging.")
				arrWidth = tmp["arrSize"]
				break

	arrWidth = arrWidth + 1  # FFT Array is 16384 items wide, +1 for time-stamp

	# Main dataset - compressed, chunked, checksummed.
	dset = out.create_dataset('Spectrum_Data', (0,arrWidth), maxshape=(None,arrWidth), chunks=True, compression="gzip", fletcher32=True)

	# Cal and system status log dataset.
	calset = out.create_dataset('Acq_info', (0,1), maxshape=(None,None), dtype=h5py.new_vlen(str))


	runningSum = np.array(())
	runningSumItems = 0
	while 1:

		if dataQueue.empty():
			time.sleep(0.005)
		else:

			tmp = dataQueue.get()

			if "max" in tmp:
				if runningSum.shape != tmp["max"].shape:
					runningSum = np.zeros_like(tmp["max"])
					runningSumItems = 0

				runningSum += tmp["max"]
				runningSumItems += 1
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


		if runningSumItems == NUM_AVERAGE:


			# print "Array shape = ", arr.shape
			arr = runningSum / runningSumItems
			# print arr.shape

			dat = np.concatenate(([time.time()], arr))

			curSize = dset.shape[0]
			dset.resize(curSize+1, axis=0)
			dset[curSize,:] = dat

			out.flush()  # FLush early, flush often
			# Probably a bad idea without a SSD


			runningSum = np.zeros_like(runningSum)
			print("Running sum shape = ", runningSum.shape)
			runningSumItems = 0

			now = time.time()
			delta = now-loop_timer
			freq = 1 / (delta)
			log.info("Elapsed Time = %0.5f, Frequency = %s", delta, freq)
			loop_timer = now

		if ctrlNs.acqRunning == False:
			log.info("Stopping Log-thread!")
			break


	out.close()

	log.info("Log-thread closing queues!")
	dataQueue.close()
	dataQueue.join_thread()
	log.info("Log-thread exiting!")
	printQueue.close()
	printQueue.join_thread()
