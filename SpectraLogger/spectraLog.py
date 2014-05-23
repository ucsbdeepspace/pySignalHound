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

# Drag in path to the library (MESSY)
import os, sys
lib_path = os.path.abspath('../')
print "Lib Path = ", lib_path
sys.path.append(lib_path)



import multiprocessing as mp

import logSetup
import logging
import spectraAcqThread
import internalSweepSpectraAcqThread
import spectraLogThread
import spectraPlotApiThread
import printThread

import settings


def go():



	plotQueue = mp.Queue()
	dataQueue = mp.Queue()
	printQueue = mp.Queue()
	ctrlManager = mp.Manager()

	logSetup.initLogging(printQ = printQueue)
	log = logging.getLogger("Main.Main")

	ctrlNs = ctrlManager.Namespace()
	ctrlNs.run = True
	ctrlNs.acqRunning = True
	ctrlNs.apiRunning = True
	ctrlNs.logRunning = True
	ctrlNs.stopped = False


	if settings.ACQ_TYPE == "real-time-sweeping":
		print("Importing real-time-sweeping module!")
		acqProc = mp.Process(target=internalSweepSpectraAcqThread.sweepSource, name="AcqThread", args=((dataQueue, plotQueue), ctrlNs, printQueue))
	else:
		print("Importing real-time module!")
		acqProc = mp.Process(target=spectraAcqThread.sweepSource, name="AcqThread", args=((dataQueue, plotQueue), ctrlNs, printQueue))

	acqProc.start()

	logProc = mp.Process(target=spectraLogThread.logSweeps, name="LogThread", args=(dataQueue, ctrlNs, printQueue))
	logProc.start()

	plotProc = mp.Process(target=spectraPlotApiThread.startApiServer, name="PlotApiThread", args=(plotQueue, ctrlNs, printQueue))
	plotProc.start()


	# A separate process for printing, which allows nice easy non-blocking printing.
	printProc = mp.Process(target=printThread.printer, name="PrintArbiter", args=(printQueue, ctrlNs))
	printProc.daemon = True
	printProc.start()


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

	# You have to empty the queue for everything to exit properly
	log.info("Emptying Queue")

	# Sometimes the last few queue items take a little while to trickle in.
	# therefore, we both poll the queue for items, and try to join() the thread. That way
	# as soon as the queue is *actually* empty, we exit immediately
	# - - -
	# this was a fucking nightmare to track down.
	log.info("Joining on AcqProc")
	while acqProc.is_alive():
		acqProc.join(0.1)
		# print("acqProc.is_alive()", acqProc.is_alive(), "logProc.is_alive()", logProc.is_alive(), "plotProc.is_alive()", plotProc.is_alive())
	log.info("Joining on LogProc")
	while logProc.is_alive():
		logProc.join(0.1)
		# print("acqProc.is_alive()", acqProc.is_alive(), "logProc.is_alive()", logProc.is_alive(), "plotProc.is_alive()", plotProc.is_alive())
	log.info("Joining on PlotProc")
	while plotProc.is_alive():
		plotProc.join(0.1)
		# print("acqProc.is_alive()", acqProc.is_alive(), "logProc.is_alive()", logProc.is_alive(), "plotProc.is_alive()", plotProc.is_alive())


	log.info("Joining on PlotProc")
	while printProc.is_alive():
		printProc.join(0.05)



	print("Threads stopped.")
	print("Stopping Shared Memory Manager.")
	ctrlManager.shutdown()

	print("Shutdown complete. Exiting.")

	sys.exit()

if __name__ == "__main__":

	go()
