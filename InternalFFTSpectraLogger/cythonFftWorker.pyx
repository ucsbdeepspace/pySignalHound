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
cimport numpy as np
import cython
from SignalHound import SignalHound

import settings as s


IN_DTYPE = np.int16
ctypedef np.int16_t IN_DTYPE_t

PROC_DTYPE = np.float32
ctypedef np.float32_t PROC_DTYPE_t

OUT_DTYPE = np.complex64
ctypedef np.complex64_t OUT_DTYPE_t

class FFTWorker(object):


	def __init__(self, ctrlNs, printQueue, rawDataRingBuf, fftDataRingBuf):

		self.log = logging.getLogger("Main.FFTWorker")
		logSetup.initLogging(printQ = printQueue)

		self.log.info("FFT Worker Starting up")

		self.ctrlNs         = ctrlNs
		self.printQueue     = printQueue
		self.rawDataRingBuf = rawDataRingBuf
		self.fftDataRingBuf = fftDataRingBuf

		self.fftChunkSize = s.FFT_CHUNK_SIZE
		self.outputSize = self.fftChunkSize//2 + 1
		self.chunksPerAcq = int(SignalHound.rawSweepArrSize/self.fftChunkSize)
		self.overlap = s.FFT_OVERLAP
		self.window = np.hamming(self.fftChunkSize)
		inArr = pyfftw.n_byte_align_empty(self.fftChunkSize, 16, dtype=np.float32)
		outArr = pyfftw.n_byte_align_empty(self.outputSize, 16, dtype=np.complex64)

		self.log.info("Choosing maximally optimized transform")
		self.fftFunc = pyfftw.FFTW(inArr, outArr, flags=('FFTW_PATIENT', "FFTW_DESTROY_INPUT"))
		self.log.info("Optimized transform selected. Run starting")

		self.run()

	@cython.boundscheck(False)
	def chunkFFT(self, np.ndarray[IN_DTYPE_t, ndim=1] arrIn):
		cdef int chunks = self.chunksPerAcq
		cdef int overlap = self.overlap-1
		cdef int chunkSz = self.fftChunkSize
		cdef int x, y, o, c
		cdef np.ndarray[PROC_DTYPE_t,  ndim=1] inDat  = pyfftw.n_byte_align_empty(self.fftChunkSize, 16, dtype=PROC_DTYPE)
		cdef np.ndarray[OUT_DTYPE_t, ndim=1]  outDat = pyfftw.n_byte_align_empty(self.outputSize,   16, dtype=OUT_DTYPE)

		for x in range(chunks*overlap-1):


			c = x * chunkSz/overlap
			for y in range(self.fftChunkSize):
				o = y + c
				inDat[y] = <PROC_DTYPE_t> arrIn[o]

			self.fftFunc(inDat, outDat)
			fftArr = self.fftFunc.get_output_array()


	def run(self):
		loop_timer = time.time()
		loopCounter = 0

		while self.ctrlNs.acqRunning:

			# Process returns 1 if there was something to process, 0 if there was not.
			loopCounter += self.process()

			now = time.time()
			delta = (now-loop_timer)
			if delta > 1:
				if loopCounter != 0:
					interval = delta / (loopCounter)
					freq = 1 / interval
					self.log.info("Elapsed Time = %0.5f, Frequency = %s, items = %s", delta, freq, loopCounter)
					loop_timer = now
					loopCounter = 0

			time.sleep(0.001)


		self.log.info("FFT Worker Recieved halt signal, FFT Worker exiting!")
		sys.exit()


	def process(self):

		ret = self.rawDataRingBuf.getOldest()
		if ret != False:
			rawDataBuf, retreiveLock = ret

			# this immediate lock release is *probably* a bad idea, but as long as the buffer doesn't get almost entirely full, it should be OK.
			# It will also prevent blockages in the output buffer from propigating back to the input buffer.
			retreiveLock.release()
			# seqNum, dataDict = tmp["data"]
			# samples, triggers = dataDict["data"], dataDict["triggers"]
			# print(len(samples))
			# samples = fft.fft(samples)
			# print "Doing FFT", seqNum

			samples = SignalHound.fastDecodeArray(rawDataBuf, SignalHound.rawSweepArrSize, np.short)

			self.chunkFFT(samples)

			#for x in range(self.chunksPerAcq*self.overlap-1):
			#	# Create byte-aligned array for efficent FFT, and copy the data we're interested into it.

			#	rets = pyfftw.n_byte_align_empty(self.outputSize, 16, dtype=np.complex64)
			#	dat = samples[x*(self.fftChunkSize/self.overlap):(x*(self.fftChunkSize/self.overlap))+self.fftChunkSize] * self.window
			#	self.fftFunc(dat, rets)
			#	fftArr = self.fftFunc.get_output_array()
			#	# # log.warning("Buf = %s, arrSize = %s, dtype=%s, as floats = %s", processedDataBuf, fftArr.shape, fftArr.dtype, fftArr.view(dtype=np.float32).shape)
			#	# try:

			#	# 	processedDataBuf, addLock = self.fftDataRingBuf.getAddArray()
			#	# 	processedDataBuf[:] = fftArr.view(dtype=np.float32)
			#	# finally:

			#	# 	addLock.release()

			#	x += 1

			return 1
		return 0
			# fftDataQueue.put({"data" : ret})

