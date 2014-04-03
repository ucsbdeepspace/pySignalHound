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

# pylint: disable=R0913, R0912

import numpy as np
import pyaudio
import SignalHound

def go():

	FORMAT = pyaudio.paFloat32
	CHANNELS = 1
	RATE = 32000  # bbFetchAudio returns samples at 32 Khz

	sOut = pyaudio.PyAudio()
	stream = sOut.open(format = FORMAT, channels = 1, rate = RATE, output = True, frames_per_buffer = 4096)

	logSetup.initLogging()
	sh = SignalHound.SignalHound()
	# sh.preset()
	sh.queryDeviceDiagnostics()
	sh.configureAcquisition("average", "log-scale")
	sh.configureCenterSpan(100e6, 50e6)
	sh.configureLevel(-50, 10)
	sh.configureGain(0)
	# sh.configureSweepCoupling(9.863e3, 9.863e3, 10, "native", "no-spur-reject")
	sh.configureWindow("hamming")
	sh.configureProcUnits("power")
	sh.configureTrigger("none", "rising-edge", 0, 5)
	sh.configureIO("dc", "int-ref-out", "out-logic-low")
	sh.configureDemod("fm", 92.9e6, 160e3, 12e3, 20, 75)
	# sh.getDeviceType()
	# sh.getSerialNumber()
	# sh.getFirmwareVersion()
	# sh.getAPIVersion()
	# sh.initiate("raw-sweep-loop", 0)
	sh.initiate("audio-demod", "demod-fm")
	# print sh.queryTimestamp()
	# sh.startRawSweepLoop(testFunct)

	try:
		while 1:
			audio = sh.fetchAudio()
			stream.write(audio.astype(np.float32).tostring())
		time.sleep(50)
	except KeyboardInterrupt:
		pass
	# sh.configureTimeGate(0,0,0)
	# sh.configureRawSweep(500, 10, 16)

	sh.abort()
	sh.closeDevice()



if __name__ == "__main__":
	go()
