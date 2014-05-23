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

IF_WIDTH = 20e6


import logSetup
import logging
import time
import traceback

# Pull in the settings crap
from settings import ACQ_FREQ, ACQ_SPAN, ACQ_REF_LEVEL_DB, ACQ_ATTENUATION_DB, ACQ_GAIN_SETTING, ACQ_RBW, ACQ_VBW, ACQ_OVERLAP, ACQ_BIN_SAMPLES
from settings import ACQ_SWEEP_TIME_SECONDS, ACQ_WINDOW_TYPE, ACQ_UNITS, ACQ_TYPE, ACQ_MODE, ACQ_Y_SCALE, PRINT_LOOP_CNT, CAL_CHK_LOOP_CNT


def sweepSource(dataQueues, ctrlNs, printQueue):
	acqRunner = InternalSweepAcqThread(printQueue)
	acqRunner.sweepSource(dataQueues, ctrlNs)

class InternalSweepAcqThread(object):
	log = logging.getLogger("Main.AcqProcess")

	def __init__(self, printQueue):
		self.printQueue = printQueue
		logSetup.initLogging(printQ=printQueue)

		self.calcScanBands()

		if ACQ_TYPE != "real-time-sweeping":
			raise ValueError("internalSweep module only supports 'real-time-sweeping' mode! Configured mode = {mode}".format(mode=ACQ_TYPE))

	def calcScanBands(self):
		if ACQ_SPAN < IF_WIDTH:
			raise ValueError("Scan width is smaller then the IF bandwidth!")
		if ACQ_SPAN == IF_WIDTH:
			raise ValueError("Scan width is exactly the IF bandwith. Maybe use the real-time mode instead?")

		sweepWidth = IF_WIDTH * (1-ACQ_OVERLAP)
		bins = ACQ_SPAN/sweepWidth
		sweepSteps = int(bins+0.5)

		effectiveScanWidth = sweepWidth*sweepSteps

		self.binFreqs = []
		baseFreq = ACQ_FREQ - (effectiveScanWidth/2 + sweepWidth/2)

		for x in xrange(1, sweepSteps+1):
			self.binFreqs.append(baseFreq+x*sweepWidth)

		self.binFreqIndice = 0

	def retune(self):
		self.sh.configureCenterSpan(center = self.binFreqs[self.binFreqIndice], span = IF_WIDTH)
		self.binFreqIndice = (self.binFreqIndice + 1) % len(self.binFreqs)


	def startAcquisition(self, dataQueue, plotQueue):


		self.sh.configureAcquisition(ACQ_MODE, ACQ_Y_SCALE)

		self.retune()

		self.sh.configureLevel(ref = ACQ_REF_LEVEL_DB, atten = ACQ_ATTENUATION_DB)
		self.sh.configureGain(gain = ACQ_GAIN_SETTING)
		self.sh.configureSweepCoupling(rbw = ACQ_RBW, vbw = ACQ_VBW, sweepTime = ACQ_SWEEP_TIME_SECONDS, rbwType = "native", rejection = "no-spur-reject")
		self.sh.configureWindow(window = ACQ_WINDOW_TYPE)
		self.sh.configureProcUnits(units = ACQ_UNITS)
		self.sh.configureTrigger(trigType = "none", edge = "rising-edge", level = 0, timeout = 5)

		self.sh.initiate(mode = "real-time", flag = "ignored")



		dataQueue.put({"settings" : self.sh.getCurrentAcquisitionSettings()})
		plotQueue.put({"settings" : self.sh.getCurrentAcquisitionSettings()})

	def sweepSource(self, dataQueues, ctrlNs):

		dataQueue, plotQueue = dataQueues


		from SignalHound import SignalHound


		loop_timer = time.time()
		print "Starting sweep-logger!"

		loop_timer = time.time()
		loops = 0

		self.sh = SignalHound()
		self.startAcquisition(dataQueue, plotQueue)

		# Send the trace size to the acq thread so I can properly set up the data-log file
		numPoints = self.sh.queryTraceInfo()["arr-size"]
		dataQueue.put({"arrSize" : numPoints})

		temperature = self.sh.queryDeviceDiagnostics()["temperature"]

		lastTime = time.time()

		while 1:
			try:


				trace = self.sh.fetchTrace()
				dataQueue.put(trace)
				plotQueue.put(trace)
				confTemp = self.sh.getCurrentAcquisitionSettings()
				plotQueue.put({"settings" : confTemp})


				del(trace)




			except Exception:
				self.log.error("IOError in Acquisition Thread!")
				self.log.error(traceback.format_exc())

				dataQueue.put({"status" : "Error: Device interface craself.shed. Reinitializing"})
				self.log.error("Resetting hardware!")
				# self.sh.preset()
				self.sh.forceClose()
				try:
					while 1:
						self.log.warning("Freeing python device handle")
						del(self.sh)
				except UnboundLocalError:
					pass

				self.log.error("Hardware self.shut down, completely re-initializing device interface!")
				# sys.exit()
				self.sh = SignalHound()
				self.startAcquisition(dataQueue, dataQueue)

			if loops > 0  and loops % ACQ_BIN_SAMPLES == 0:
				print("Should retune frontend!")
				self.sh.abort()
				self.startAcquisition(dataQueue, dataQueue)

				print("Current acq mode = ", self.sh.queryTraceInfo())

			if loops % PRINT_LOOP_CNT == 0:
				now = time.time()
				delta = now-loop_timer
				freq = 1 / (delta / PRINT_LOOP_CNT)
				self.log.info("Elapsed Time = %0.5f, Frequency = %s", delta, freq)
				loop_timer = now

			if loops % CAL_CHK_LOOP_CNT == 0:
				diags = self.sh.queryDeviceDiagnostics()
				dataQueue.put({"status" : diags})

				temptmp = diags["temperature"]
				if abs(temperature - temptmp) > 2.0:    # Temperature deviations of > 2° cause IF self.shifts. Therefore, we do a re-cal if they're detected
					dataQueue.put({"status" : "Recalibrating IF"})
					self.sh.selfCal()
					self.startAcquisition(dataQueue, dataQueue)
					self.log.warning("Temperature changed > 2.0 C. Delta is %f. Recalibrated!", abs(temperature - temptmp))
					temperature = temptmp
				else:
					self.log.info("Temperature deviation = %f. Not doing recal, since drift < 2C", abs(temperature - temptmp))

			loops += 1

			if ctrlNs.run == False:
				self.log.info("Stopping Acq-thread!")
				break


		self.sh.abort()
		self.sh.closeDevice()

		del(self.sh)



		self.log.info("Acq-thread closing dataQueue!")
		dataQueue.close()
		dataQueue.join_thread()

		plotQueue.close()
		plotQueue.cancel_join_thread()

		ctrlNs.acqRunning = False

		self.log.info("Acq-thread exiting!")
		self.printQueue.close()
		self.printQueue.join_thread()
