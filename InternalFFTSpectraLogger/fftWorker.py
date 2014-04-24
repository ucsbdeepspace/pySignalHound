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
from SignalHound import SignalHound


def fftWorker(ctrlNs, printQueue, rawDataRingBuf, fftDataRingBuf):

	log = logging.getLogger("Main.FFTWorker")
	logSetup.initLogging(printQ = printQueue)
	loop_timer = time.time()

	log.info("FFT Worker Starting up")

	loopCounter = 0
	fftChunkSize = 2**16
	outputSize = fftChunkSize//2 + 1
	chunksPerAcq = int(SignalHound.rawSweepArrSize/fftChunkSize)
	overlap = 4
	window = np.hamming(fftChunkSize)
	inArr = pyfftw.n_byte_align_empty(fftChunkSize, 16, dtype=np.float32)
	outArr = pyfftw.n_byte_align_empty(outputSize, 16, dtype=np.complex64)

	log.info("Choosing maximally optimized transform")
	fftFunc = pyfftw.FFTW(inArr, outArr, flags=('FFTW_PATIENT', "FFTW_DESTROY_INPUT"))
	log.info("Optimized transform selected. Run starting")

	while ctrlNs.acqRunning:


		ret = rawDataRingBuf.getOldest()
		if ret != False:
			rawDataBuf, retreiveLock = ret
			loopCounter += 1
			# this immediate lock release is *probably* a bad idea, but as long as the buffer doesn't get almost entirely full, it should be OK.
			# It will also prevent blockages in the output buffer from propigating back to the input buffer.
			retreiveLock.release()
			# seqNum, dataDict = tmp["data"]
			# samples, triggers = dataDict["data"], dataDict["triggers"]
			# print(len(samples))
			# samples = fft.fft(samples)
			# print "Doing FFT", seqNum

			samples = SignalHound.fastDecodeArray(rawDataBuf, SignalHound.rawSweepArrSize, np.short)


			for x in range(chunksPerAcq*overlap-1):
				# Create byte-aligned array for efficent FFT, and copy the data we're interested into it.

				rets = pyfftw.n_byte_align_empty(outputSize, 16, dtype=np.complex64)
				dat = samples[x*(fftChunkSize/overlap):(x*(fftChunkSize/overlap))+fftChunkSize] * window
				fftFunc(dat, rets)
				fftArr = fftFunc.get_output_array()
				# # log.warning("Buf = %s, arrSize = %s, dtype=%s, as floats = %s", processedDataBuf, fftArr.shape, fftArr.dtype, fftArr.view(dtype=np.float32).shape)
				try:

					processedDataBuf, addLock = fftDataRingBuf.getAddArray()
					processedDataBuf[:] = fftArr.view(dtype=np.float32)
				finally:

					addLock.release()

				x += 1


			# fftDataQueue.put({"data" : ret})



			now = time.time()
			delta = (now-loop_timer)
			if delta > 1:
				interval = delta / (loopCounter)
				freq = 1 / interval
				log.info("Elapsed Time = %0.5f, Frequency = %s, items = %s", delta, freq, loopCounter)
				loop_timer = now
				loopCounter = 0

		time.sleep(0.001)


	log.info("FFT Worker Recieved halt signal, FFT Worker exiting!")
	sys.exit()
