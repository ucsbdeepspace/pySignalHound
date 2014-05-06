# -*- coding: UTF-8 -*-

# Wrapper for Test-Equipment-Plus's "SignalHound" series of USB spectrum analysers.
#
# Written By Connor Wolf <wolf@imaginaryindustries.com>

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

# Pull in the settings crap
from settings import H_FLIP_FREQ, ACQ_FREQ, ACQ_SPAN, ACQ_REF_LEVEL_DB, ACQ_ATTENUATION_DB, ACQ_GAIN_SETTING, ACQ_RBW, ACQ_VBW
from settings import ACQ_SWEEP_TIME_SECONDS, ACQ_WINDOW_TYPE, ACQ_UNITS, ACQ_TYPE, ACQ_MODE, ACQ_Y_SCALE, PRINT_LOOP_CNT, CAL_CHK_LOOP_CNT

def startAcquisition(sh, dataQueue):

	sh.configureAcquisition(ACQ_MODE, ACQ_Y_SCALE)
	sh.configureCenterSpan(center = ACQ_FREQ, span = ACQ_SPAN)
	sh.configureLevel(ref = ACQ_REF_LEVEL_DB, atten = ACQ_ATTENUATION_DB)
	sh.configureGain(gain = ACQ_GAIN_SETTING)
	sh.configureSweepCoupling(rbw = ACQ_RBW, vbw = ACQ_VBW, sweepTime = ACQ_SWEEP_TIME_SECONDS, rbwType = "native", rejection = "no-spur-reject")
	sh.configureWindow(window = ACQ_WINDOW_TYPE)
	sh.configureProcUnits(units = ACQ_UNITS)
	sh.configureTrigger(trigType = "none", edge = "rising-edge", level = 0, timeout = 5)
	# sh.configureIO("dc", "int-ref-out", "out-logic-low")
	# sh.configureDemod("fm", 102.3e6, 250e3, 12e3, 20, 50)

	# sh.configureRawSweep(100, 8, 2)
	sh.initiate(mode = ACQ_TYPE, flag = "ignored")

	dataQueue.put({"settings" : sh.getCurrentAcquisitionSettings()})

def sweepSource(dataQueue, ctrlNs, printQueue):




	from SignalHound import SignalHound

	logSetup.initLogging(printQ = printQueue)
	loop_timer = time.time()
	print "Starting sweep-logger!"
	log = logging.getLogger("Main.AcqProcess")

	loop_timer = time.time()
	loops = 0

	sh = SignalHound()
	startAcquisition(sh, dataQueue)


	temperature = sh.queryDeviceDiagnostics()["temperature"]

	while 1:
		try:
			dataQueue.put(sh.fetchTrace())
		except Exception:
			log.error("IOError in Acquisition Thread!")
			log.error(traceback.format_exc())

			dataQueue.put({"status" : "Error: Device interface crashed. Reinitializing"})
			log.error("Resetting hardware!")
			# sh.preset()
			sh.forceClose()
			try:
				while 1:
					log.warning("Freeing python device handle")
					del(sh)
			except UnboundLocalError:
				pass

			log.error("Hardware shut down, completely re-initializing device interface!")
			# sys.exit()
			sh = SignalHound()
			startAcquisition(sh, dataQueue)

		if loops % PRINT_LOOP_CNT == 0:
			now = time.time()
			delta = now-loop_timer
			freq = 1 / (delta / PRINT_LOOP_CNT)
			log.info("Elapsed Time = %0.5f, Frequency = %s", delta, freq)
			loop_timer = now

		if loops % CAL_CHK_LOOP_CNT == 0:
			diags = sh.queryDeviceDiagnostics()
			dataQueue.put({"status" : diags})

			temptmp = diags["temperature"]
			if abs(temperature - temptmp) > 2.0:    # Temperature deviations of > 2° cause IF shifts. Therefore, we do a re-cal if they're detected
				dataQueue.put({"status" : "Recalibrating IF"})
				sh.selfCal()
				startAcquisition(sh, dataQueue)
				log.warning("Temperature changed > 2.0 C. Delta is %f. Recalibrated!", abs(temperature - temptmp))
				temperature = temptmp
			else:
				log.info("Temperature deviation = %f. Not doing recal, since drift < 2C", abs(temperature - temptmp))

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