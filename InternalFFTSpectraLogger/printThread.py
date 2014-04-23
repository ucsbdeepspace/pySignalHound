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



NUM_AVERAGE = 1

def printer(printQueue, ctrlNs):


	log = logging.getLogger("Main.Printer")
	logSetup.initLogging()

	while 1:
		if not printQueue.empty():
			print printQueue.get()





		if ctrlNs.printerRun == False:
			log.info("Stopping Printing-thread!")
			break

		time.sleep(0.001)


	log.info("Log-thread exiting!")
	printQueue.close()
	printQueue.join_thread()
