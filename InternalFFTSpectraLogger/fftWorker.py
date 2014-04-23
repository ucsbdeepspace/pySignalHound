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
import sys
import pyfftw
import numpy as np


def fftWorker(rawDataQueue, fftDataQueue, ctrlNs, printQueue):

	log = logging.getLogger("Main.FFTWorker")
	logSetup.initLogging(printQ = printQueue)
	loop_timer = time.time()

	log.info("FFT Worker Starting up")

	loopCounter = 0

	while ctrlNs.acqRunning:


		if not rawDataQueue.empty():

			loopCounter += 1
			tmp = rawDataQueue.get()
			if "data" in tmp:
				seqNum, dataDict = tmp["data"]
				samples, triggers = dataDict["data"], dataDict["triggers"]
				# print(len(samples))
				# samples = fft.fft(samples)
				# print "Doing FFT", seqNum

				x = 0
				ret = []
				while x < 9:
					tmpArr = pyfftw.n_byte_align_empty(2**14, 16, dtype=np.float)
					tmpArr = samples[x*(2**14):(x+1)*(2**14)]
					ret.append(pyfftw.interfaces.numpy_fft.fft(tmpArr))
					x += 1
				# print("Dtype = ", samples.dtype)
				# print "FFT", seqNum, "done"

				fftDataQueue.put({"data" : (seqNum, {"data" : ret, "triggers" : triggers})})

			else:
				fftDataQueue.put(tmp)


			now = time.time()
			delta = (now-loop_timer)
			if delta > 1:
				interval = delta / (loopCounter)
				freq = 1 / interval
				log.info("Elapsed Time = %0.5f, Frequency = %s, items = %s", delta, freq, loopCounter)
				loop_timer = now
				loopCounter = 0

		time.sleep(0.001)


	log.info("FFT Worker Recieved halt signal. Flushing queues!")
	while not rawDataQueue.empty():
		rawDataQueue.get()

	fftDataQueue.close()
	fftDataQueue.join_thread()



	log.info("FFT Worker exiting!")
	sys.exit()
