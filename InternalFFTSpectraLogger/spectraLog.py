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

# pylint: disable=R0913, R0912, W0603


'''
Because multiprocessing is annoying, the shutdown procedure for this script is.... involved.
Basically, "q" + enter" signals the acquisition thread to exit. That sets a flag on exit that starts the
fftWorkers shutdown, which set a flag that halts the logThread, and finally the main-script (this one) sees a
flag set on the log-thread's exit that causes it to tell the print-thread to halt, and then exit.
Yeah, it's kinda silly.

'''


# Drag in path to the library (MESSY)
import os, sys
lib_path = os.path.abspath('../')
print(lib_path)
sys.path.append(lib_path)

import multiprocessing as mp


import logSetup
import logging
import time
import spectraAcqThread
import spectraLogThread
import printThread
import sharedMemRingBuf
from SignalHound import SignalHound
import numpy as np
import ctypes as ct

import settings as s

# All imports after installing pyximport will be compiled with cython
import pyximport
pyximport.install(setup_args={"include_dirs":np.get_include()})
import cythonFftWorker as fftWorker

def go():

	print("startup")


	statusMessageQueue = mp.Queue()
	fftDataQueue = mp.Queue()
	printQueue = mp.Queue()
	ctrlManager = mp.Manager()

	logSetup.initLogging(printQ = printQueue)
	log = logging.getLogger("Main.Main")

	ctrlNs = ctrlManager.Namespace()
	ctrlNs.run = True
	ctrlNs.acqRunning = True
	ctrlNs.procRunning = True
	ctrlNs.logRunning = True
	ctrlNs.printerRun = True
	ctrlNs.stopped = False

	# A separate process for printing, which allows nice easy non-blocking printing.
	printProc = mp.Process(target=printThread.printer, name="PrintFormatterThread", args=(printQueue, ctrlNs))
	printProc.daemon = True
	printProc.start()


	rawDataRingBuf = sharedMemRingBuf.SharedMemRingBuf(2000, *SignalHound.getRawSweep_s_size())

	# 32769 =fftChunkSize//2 + 1 (fftChunkSize = 2**16). Values are a complex64, which is really 2 32 bit floats
	fftDataRingBuf = sharedMemRingBuf.SharedMemRingBuf(1000, ct.c_float, 32769*2)

	print(rawDataRingBuf)

	fftWorkerPool = mp.Pool(processes=s.NUM_FFT_PROESSES, initializer=fftWorker.FFTWorker, initargs=(ctrlNs, printQueue, rawDataRingBuf, fftDataRingBuf))


	acqProc = mp.Process(target=spectraAcqThread.sweepSource, name="SweepThread", args=(statusMessageQueue, ctrlNs, printQueue, rawDataRingBuf))


	logProc = mp.Process(target=spectraLogThread.logSweeps, name="LogThread", args=(statusMessageQueue, fftDataRingBuf, ctrlNs, printQueue))

	log.info("Waiting while worker-processes perform initialization")
	time.sleep(5)
	acqProc.start()
	logProc.start()




	try:
		while 1:
			inStr = raw_input()
			print inStr
			if inStr == "q":
				break



	except KeyboardInterrupt:
		pass



	log.info("Stopping Processes!")


	ctrlNs.run = False

	# fftWorkerPool.terminate()
	fftWorkerPool.close()


	# Sometimes the last few queue items take a little while to trickle in.
	# therefore, we both poll the queue for items, and try to join() the thread. That way
	# as soon as the queue is *actually* empty, we exit immediately
	# - - -
	# this was a fucking nightmare to track down.
	log.info("Waiting for acquisition thread to halt.")
	acqProc.join()

	log.info("Acquisition thread halted.")
	log.info("Stopping worker thread pool.")

	ctrlNs.procRunning = False
	fftWorkerPool.join()
	log.info("Threadpool Halted.")


	log.info("Waiting for log-thread to halt.")
	while logProc.is_alive():
		if not fftDataQueue.empty():
			fftDataQueue.get()
	logProc.join()


	log.info("Logging thread halted.")

	log.info("stopping printing service")


	ctrlNs.printerRun = False
	if not printQueue.empty():
		printQueue.get()
	printProc.join()

	print("Threads stopped.")


	print("Stopping Shared Memory Manager!")
	ctrlManager.shutdown()
	print("Shutdown complete. Exiting.")

	sys.exit()

if __name__ == "__main__":

	go()
