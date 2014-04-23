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
import fftWorker
import printThread

FFT_PROCESSES = 3

def go():




	rawDataQueue = mp.Queue()
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


	acqProc = mp.Process(target=spectraAcqThread.sweepSource, name="SweepThread", args=(rawDataQueue, ctrlNs, printQueue))
	acqProc.start()

	logProc = mp.Process(target=spectraLogThread.logSweeps, name="LogThread", args=(fftDataQueue, ctrlNs, printQueue))
	logProc.start()

	fftWorkerPool = mp.Pool(processes=FFT_PROCESSES, initializer=fftWorker.fftWorker, initargs=(rawDataQueue, fftDataQueue, ctrlNs, printQueue))

	# A separate process for printing, which allows nice easy non-blocking printing.
	printProc = mp.Process(target=printThread.printer, name="PrintFormatterThread", args=(printQueue, ctrlNs))
	printProc.daemon = True
	printProc.start()

	print("Living children =", )

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
	while acqProc.is_alive():
		if not rawDataQueue.empty():
			rawDataQueue.get()

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
