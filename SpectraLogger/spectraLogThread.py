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

# Drag in path to the library (MESSY)
import os, sys
lib_path = os.path.abspath('../')
print "Lib Path = ", lib_path
sys.path.append(lib_path)


import logSetup
import logging
import time
import numpy as np

import h5py

import os
import os.path
import cPickle

from settings import NUM_AVERAGE

def logSweeps(dataQueue, ctrlNs, printQueue, test=False):


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
	startFreq = 0

	# the size of the acquisiton array can vary. Therefore, we wait for the acq thread to send a message containing
	# the array size before allocating the HDF5 array.
	if not test:
		while 1:

			if dataQueue.empty():
				time.sleep(0.005)
			else:
				tmp = dataQueue.get()
				if "arrSize" in tmp:
					log.info("Have array size for acquisition. Creating HDF5 file and starting logging.")
					arrWidth = tmp["arrSize"]
					break
	else:
		arrWidth = 20


	# dTypeStructure = [("TimeStamp", "f8"), ("StartFreq", "f4"), ("BinSize", "f4"), ("NumScans", "f4"), ("data", "f4", arrWidth)]
	# dType = np.dtype(dTypeStructure)

	arrWidth = arrWidth + 1 + 1 + 1 + 1 # Width of the data array, plus - TimeStamp, StartFreq, BinSize, NumScans

	# Main dataset - compressed, chunked, checksummed.
	dset = out.create_dataset('Spectrum_Data', (0, arrWidth), maxshape=(None, arrWidth), dtype = np.float64, chunks=True, compression="gzip", fletcher32=True, shuffle=True)

	# Cal and system status log dataset.
	calset = out.create_dataset('Acq_info', (0, ), maxshape=(None, ), dtype=h5py.new_vlen(str))




	runningSum = np.array(())
	runningSumItems = 0
	while 1:

		if dataQueue.empty():
			time.sleep(0.005)
		else:

			tmp = dataQueue.get()
			# print "data" in tmp
			# print "info" in tmp
			# print "data" in tmp and "max" in tmp["data"]


			if "data" in tmp and "info" in tmp and "max" in tmp["data"]:
				acqInfo = tmp["info"]

				# Array has changed shape, probably because this is the first acquisition? Anyways, set up the running-sum array, and the various required values
				if runningSum.shape != tmp["data"]["max"].shape:
					runningSum = np.zeros_like(tmp["data"]["max"])
					runningSumItems = 0
					startFreq = acqInfo["ret-start-freq"]
					binSize = acqInfo["arr-bin-size"]
					log.info("Running average array size changed! Either the system just started, or something is seriously wrong!")

				changed = False

				# if the spectra freqency has changed, set the changed flag. Otherwise, add the data to the running sum array as normal.
				if startFreq != acqInfo["ret-start-freq"]:
					changed = True

				else:
					runningSum += tmp["data"]["max"]
					runningSumItems += 1

				# if we've reached the number of average items per output array, or the frequency has changed, requiring an early dump of the specra data.
				if runningSumItems == NUM_AVERAGE or changed:

					# Divide down to the average
					arr = runningSum / runningSumItems

					# Build array to write out.
					saveTime = time.time()
					# log.info("Saving data record with timestamp %f", saveTime)

					# Only write out to the file if we actually have data
					if runningSumItems != 0:

						# append it to the HDF5 file
						curSize = dset.shape[0]
						# print("Current shape = ", dset.shape)
						dset.resize(curSize+1, axis=0)

						flatten = lambda *args: args
						dset[curSize] = flatten(saveTime, startFreq, binSize, runningSumItems, *arr)

						out.flush()  # FLush early, flush often
						# Probably a bad idea without a SSD


						runningSum = np.zeros_like(runningSum)
						log.info("Running sum shape = %s, items = %s", runningSum.shape, runningSumItems)
						runningSumItems = 0

					# now = time.time()
					# delta = now-loop_timer
					# freq = 1 / (delta)
					# log.info("Elapsed Time = %0.5f, Frequency = %s", delta, freq)
					# loop_timer = now


					# If we wrote the output because the current spectra has changed, we need to update the running acq info variables with the new frequencies.
					if changed:
						log.info("Retuned! Old freq = %s, new freq = %s", startFreq, acqInfo["ret-start-freq"])

						runningSum += tmp["data"]["max"]
						startFreq = acqInfo["ret-start-freq"]
						binSize = acqInfo["arr-bin-size"]
						runningSumItems = 1





			elif "settings" in tmp or "status" in tmp:

				if "settings" in tmp:
					tmp["settings"]["averaging-interval"] = NUM_AVERAGE

				data = [time.time(), tmp]

				dataPik = cPickle.dumps(data)

				calSz = calset.shape[0]
				calset.resize([calSz+1,])
				calset[calSz,...] = dataPik

				# log.info("Status message - %s.", tmp)
				# log.info("StatusTable size = %s", calset.shape)
			else:
				log.error("WAT? Unknown packet!")
				log.error(tmp)


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

def dotest():
	print("Starting test")
	import Queue
	logSetup.initLogging()
	logSweeps(Queue.Queue(), None, Queue.Queue(), test=True)

if __name__ == "__main__":
	dotest()
