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
import traceback


def sweepSource(dataQueue, ctrlNs):


	from SignalHound import SignalHound

	logSetup.initLogging()
	loop_timer = time.time()
	print "Starting sweep-logger!"
	log = logging.getLogger("Main.DevPlugin")

	loop_timer = time.time()
	loops = 0

	sh = SignalHound()

	sh.configureAcquisition("average", "log-scale")
	sh.configureCenterSpan(center = 150e6, span = 100e6)
	sh.configureLevel(ref = 10, atten = "auto")
	sh.configureGain(gain = 0)
	sh.configureSweepCoupling(rbw = 9.863e3, vbw = 9.863e3, sweepTime = 0.010, rbwType = "native", rejection = "no-spur-reject")
	sh.configureWindow(window = "hamming")
	sh.configureProcUnits(units = "power")
	sh.configureTrigger(trigType = "none", edge = "rising-edge", level = 0, timeout = 5)
	# sh.configureIO("dc", "int-ref-out", "out-logic-low")
	# sh.configureDemod("fm", 102.3e6, 250e3, 12e3, 20, 50)

	# sh.configureRawSweep(100, 8, 2)
	sh.initiate(mode = "sweeping", flag = "ignored")
	print sh.queryTraceInfo()

	printLoopCount = 50

	while 1:
		try:
			dataQueue.put(sh.fetchTrace())
		except IOError:

			log.error("IOError in Acquisition Thread!")
			log.error(traceback.format_exc())

		if loops % printLoopCount == 0:
			now = time.time()
			delta = now-loop_timer
			freq = 1 / (delta / printLoopCount)
			log.info("Elapsed Time = %0.5f, Frequency = %s", delta, freq)
			loop_timer = now

		loops += 1

		if ctrlNs.run == False:
			log.info("Stopping Sweep-thread!")
			break


	sh.abort()
	sh.closeDevice()

	del(sh)

	ctrlNs.acqRunning = False

	while not dataQueue.empty():
		dataQueue.get()

	log.info("Sweep-thread exiting!")
	dataQueue.close()
	dataQueue.join_thread()
