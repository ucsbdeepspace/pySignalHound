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

import ctypes as ct

import bb_api_h as hf

import logSetup
import logging

import time

# pylint: disable=R0913, R0912

import numpy as np
from numpy.core.multiarray import int_asbuffer

class SignalHound():

	bbStatus = {
		"bbInvalidModeErr"             : -112,
		"bbReferenceLevelErr"          : -111,
		"bbInvalidVideoUnitsErr"       : -110,
		"bbInvalidWindowErr"           : -109,
		"bbInvalidBandwidthTypeErr"    : -108,
		"bbInvalidSweepTimeErr"        : -107,
		"bbBandwidthErr"               : -106,
		"bbInvalidGainErr"             : -105,
		"bbAttenuationErr"             : -104,
		"bbFrequencyRangeErr"          : -103,
		"bbInvalidSpanErr"             : -102,
		"bbInvalidScaleErr"            : -101,
		"bbInvalidDetectorErr"         : -100,

		# General Errors
		"bbDeviceConnectionErr"        : -14,
		"bbPacketFramingErr"           : -13,
		"bbGPSErr"                     : -12,
		"bbGainNotSetErr"              : -11,
		"bbDeviceNotIdleErr"           : -10,
		"bbDeviceInvalidErr"           : -9,
		"bbBufferTooSmallErr"          : -8,
		"bbNullPtrErr"                 : -7,
		"bbAllocationLimitErr"         : -6,
		"bbDeviceAlreadyStreamingErr"  : -5,
		"bbInvalidParameterErr"        : -4,
		"bbDeviceNotConfiguredErr"     : -3,
		"bbDeviceNotStreamingErr"      : -2,
		"bbDeviceNotOpenErr"           : -1,

		# No Error
		"bbNoError"                    : 0,

		# Warnings/Messages
		"bbAdjustedParameter"          : 1,
		"bbADCOverflow"                : 2,
		"bbNoTriggerFound"             : 3
	}


	def __init__(self):

		self.log = logging.getLogger("Main.DevPlugin")
		self.devOpen = False

		self.log.info("Opening DLL")
		self.dll = ct.WinDLL ("bb_api.dll")

		self.cRawSweepCallbackFunc = None

		self.openDevice()

	def __del__(self):

		if self.devOpen:
			self.closeDevice()

		if self.cRawSweepCallbackFunc:
			del(self.cRawSweepCallbackFunc)

	def openDevice(self):


		self.log.info("Opening Device")

		self.deviceHandle = ct.c_int(0)
		deviceHandlePnt = ct.pointer(self.deviceHandle)
		ret = self.dll.bbOpenDevice(deviceHandlePnt)

		if ret != hf.bbNoError:
			if ret == hf.bbNullPtrErr:
				raise ValueError("Could not open device due to null-pointer error!")
			elif ret == hf.bbDeviceNotOpenErr:
				raise ValueError("Could not open device!")
			else:
				raise ValueError("Could not open device due to unknown reason!")

		self.devOpen = True
		self.log.info("Opened Device with handle num: %s", self.deviceHandle.value)

	def closeDevice(self):
		self.log.info("Closing Device with handle num: %s", self.deviceHandle.value)
		ret = self.dll.bbCloseDevice(self.deviceHandle)

		if ret != hf.bbNoError:
			raise ValueError("Error closing device!")
		self.log.info("Closed Device with handle num: %s", self.deviceHandle.value)
		self.devOpen = False


	def queryDeviceDiagnostics(self):
		# BB_API bbStatus bbQueryDiagnostics(int device, float *temperature, float *voltage1_8, float *voltage1_2, float *voltageUSB, float *currentUSB);

		# temperature  Pointer to 32bit float. If the function is successful temperature will point
		# 		to the current internal device temperature, in degrees Celsius. See
		# 		"bbSelfCal" for an explanation on why you need to monitor the device
		# 		temperature.
		# voltage1_8  Factory use only: Internal regulator.
		# voltage1_2 Factory use only: Internal regulator.
		# voltageUSB  USB operating voltage, in volts. Acceptable ranges are 4.40 to 5.25 V.
		# currentUSB  USB current draw, in mA. Acceptable ranges are 800 - 1000 mA

		# Pass NULL to any parameter you do not wish to query.
		# The device temperature is updated in the API after each sweep is retrieved. The temperature is returned
		# in Celsius and has a resolution of 1/8 th of a degree. A temperature above 70 ° C or below 0 ° C indicates
		# your device is operating outside of its normal operating temperature, and may cause readings to be out
		# of spec, and may damage the device.
		# A USB voltage of below 4.4V may cause readings to be out of spec. Check your cable for damage and
		# USB connectors for damage or oxidation.

		self.log.info("Querying device diagnostics.")
		temperature = ct.c_float(0)
		voltage1_8 = ct.c_float(0)
		voltage1_2 = ct.c_float(0)
		voltageUSB = ct.c_float(0)
		currentUSB = ct.c_float(0)

		temperaturePnt = ct.pointer(temperature)
		voltage1_8Pnt = ct.pointer(voltage1_8)
		voltage1_2Pnt = ct.pointer(voltage1_2)
		voltageUSBPnt = ct.pointer(voltageUSB)
		currentUSBPnt = ct.pointer(currentUSB)



		err = self.dll.bbQueryDiagnostics(self.deviceHandle, temperaturePnt, voltage1_8Pnt, voltage1_2Pnt, voltageUSBPnt, currentUSBPnt)

		if err == self.bbStatus["bbNoError"]:
			pass
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		else:
			raise IOError("Unknown error!")



		ret = {
			"temperature" :  temperature.value,
			"voltage1_8"  :  voltage1_8.value,
			"voltage1_2"  :  voltage1_2.value,
			"voltageUSB"  :  voltageUSB.value,
			"currentUSB"  :  currentUSB.value
		}

		if ret["currentUSB"] < 4.4:
			raise EnvironmentError("USB Supply voltage below specified minimum of 4.4V. Please check hardware.")

		if ret["temperature"] > 70 or ret["temperature"] < 0:
			raise EnvironmentError("Hardware temperature outside of normal operating bounds.")

		self.log.info("Diagnostics queried. Values = %s", ret)
		return ret

	def configureAcquisition(self, detector, scale):
		# BB_API bbStatus bbConfigureAcquisition(int device, unsigned int detector, unsigned int scale);

		# detectorType  Specifies the video detector. The two possible values for detector type
		# 		are BB_AVERAGE and BB_MIN_AND_MAX.
		# verticalScale  Specifies the scale in which sweep results are returned int. The four
		# 		possible values for verticalScale are BB_LOG_SCALE, BB_LIN_SCALE,
		# 		BB_LOG_FULL_SCALE, and BB_LIN_FULL_SCALE

		# The verticalScale parameter will change the units of returned sweeps. If BB_LOG_SCALE is provided
		# sweeps will be returned in amplitude unit dBm. If BB_LIN_SCALE is return, the returned units will be in
		# millivolts. If the full scale units are specified, no corrections are applied to the data and amplitudes are
		# taken directly from the full scale input.
		# detectorType specifies how to produce the results of the signal processing for the final sweep.
		# Depending on settings, potentially many overlapping FFTs will be performed on the input time domain
		# data to retrieve a more consistent and accurate final result. When the results overlap detectorType
		# chooses whether to average the results together, or maintain the minimum and maximum values. If
		# averaging is chosen the min and max trace arrays returned from bbFetchTrace will contain the same
		# averaged data

		self.log.info("Setting device acquisition configuration.")
		if detector == "min-max":
			detector = ct.c_uint(hf.BB_MIN_AND_MAX)
		elif detector == "average":
			detector = ct.c_uint(hf.BB_AVERAGE)
		else:
			raise ValueError("Invalid Detector mode! Detector must be either \"average\" or \"min-max\". Specified detector = %s" % detector)

		if scale == "log-scale":
			scale = ct.c_uint(hf.BB_LOG_SCALE)
		elif scale == "log-full-scale":
			scale = ct.c_uint(hf.BB_LOG_FULL_SCALE)
		elif scale == "lin-scale":
			scale = ct.c_uint(hf.BB_LIN_SCALE)
		elif scale == "lin-full-scale":
			scale = ct.c_uint(hf.BB_LIN_FULL_SCALE)
		else:
			raise ValueError("Invalid Scaling mode! Scaling mode must be either \"log-scale\" \"log-full-scale\" \"lin-scale\" or \"lin-full-scale\". Specified scale = %s" % scale)

		err = self.dll.bbConfigureAcquisition(self.deviceHandle, detector, scale)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureAcquisition succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidDetectorErr"]:
			raise IOError("Invalid Detector mode!")
		elif err == self.bbStatus["bbInvalidScaleErr"]:
			raise IOError("Invalid scale setting error!")
		else:
			raise IOError("Unknown error setting configureAcquisition! Error = %s" % err)


	def configureCenterSpan(self, center, span):
		# BB_API bbStatus bbConfigureCenterSpan(int device, double center, double span);

		# center 	Center frequency in hertz.
		# span  	Span in hertz

		# This function configures the operating frequency band of the broadband device. Start and stop
		# frequencies can be determined from the center and span.
		# -  start = center - (span/2)
		# -  stop = center+(span/2)
		# The values provided are used by the device during initialization and a more precise start frequency is
		# returned after initiation. Refer to the bbQueryTraceInfo function for more information.
		# Each device has a specified operational frequency range. These limits are BB#_MIN_FREQ and
		# BB#_MAX_FREQ. The center and span provided cannot specify a sweep outside of this range.
		# There is also an absolute minimum operating span.
		# Certain modes of operation have specific frequency range limits. Those mode dependent limits are
		# tested against during initialization and not here.

		self.log.info("Setting device frequency center & span settings.")
		center = ct.c_double(center)
		span = ct.c_double(span)

		err = self.dll.bbConfigureCenterSpan(self.deviceHandle, center, span)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureCenterSpan succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidSpanErr"]:
			raise IOError("The span provided is less than the minimum acceptable span.")
		elif err == self.bbStatus["bbFrequencyRangeErr"]:
			raise IOError("The calculated start or stop frequencies fall outside of the operational frequency range of the specified device.")
		else:
			raise IOError("Unknown error setting configureAcquisition! Error = %s" % err)


	def configureLevel(self, ref, atten):
		# BB_API bbStatus bbConfigureLevel(int device, double ref, double atten);

		# Reference and attenuation in dBm
		# ref		Reference level in dBm.
		# atten		Attenuation setting in dB. If attenuation provided is negative,
		#	attenuation is selected automatically.

		# When automatic gain is selected, the API uses the reference level provided to choose the best gain
		# settings for an input signal with amplitude equal to reference level. If a gain other than BB_AUTO_GAIN
		# is specified using bbConfigureGain, the reference level parameter is ignored.
		# The atten parameter controls the RF input attenuator, and is adjustable from 0 to 30 dB in 10 dB steps.
		# The RF attenuator is the first gain control device in the front end.
		# When attenuation is automatic, the attenuation and gain for each band is selected independently. When
		# attenuation is not automatic, a flat attenuation is set across the entire spectrum. A set attenuation may
		# produce a non-flat noise floor.

		if atten % 10 != 0:
			raise ValueError("Attenuator value must be a multiple of 10. Passed value of %s" % atten)

		self.log.info("Setting device reference level and attentuation.")
		ref = ct.c_double(ref)
		atten = ct.c_double(atten)

		err = self.dll.bbConfigureLevel(self.deviceHandle, ref, atten)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureLevel succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbReferenceLevelErr"]:
			raise IOError("The reference level provided exceeds 20 dBm.")
		elif err == self.bbStatus["bbAttenuationErr"]:
			raise IOError("The attenuation value provided exceeds 30 db.")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

		return

	def configureGain(self, gain):
		# BB_API bbStatus bbConfigureGain(int device, int gain);

		# gain		A gain setting

		# To return the device to automatically choose the best gain setting, call this function with a gain of
		# BB_AUTO_GAIN.
		# The gain choices for each device range from 0 to BB#_MAX_GAIN.
		# When BB_AUTO_GAIN is selected, the API uses the reference level provided in bbConfigureLevel to
		# choose the best gain setting for an input signal with amplitude equal to the reference level provided.
		# After the RF input attenuator (0-30 dB), the RF path contains an additional amplifier stage after band
		# filtering, which is selected for medium or high gain and bypassed for low or no gain.
		# Additionally, the IF has an amplifier which is bypassed only for a gain of zero.
		# For the highest gain settings, additional amplification in the ADC stage is used.

		self.log.info("Setting device reference gain.")

		if gain == "auto":
			gain = hf.BB60_MAX_GAIN

		try:
			gain = ct.c_int(gain)
		except TypeError:
			self.log.critical("Gain value must be an integer value, or \"auto\"")
			raise


		err = self.dll.bbConfigureGain(self.deviceHandle, gain)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureGain succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidGainErr"]:
			raise IOError("The specified gain value is outside the range of possible gains. Valid values are 0-%d, or \"auto\"" % hf.BB60_MAX_GAIN)
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

		return


	def configureSweepCoupling(self, rbw, vbw, sweepTime, rbwType, rejection):
		# BB_API bbStatus bbConfigureSweepCoupling(int device, double rbw, double vbw, double sweepTime, unsigned int rbwType, unsigned int rejection);

		# device  Handle to the device being configured.
		# rbw  	Resolution bandwidth in Hz. Use the bandwidth table in the appendix to
		# 		determine good values to choose. As of 1.07 in non-native mode, RBW
		# 		can be arbitrary. Therefore you may choose values not in the table and
		# 		they will not clamp.
		# vbw  Video bandwidth (VBW) in Hz. VBW must be less than or equal to RBW.
		# 		VBW can be arbitrary. For best performance use RBW as the VBW.
		# sweepTime  Sweep time in seconds.
		# 		In sweep mode, this value is how long the device collects data before it
		# 		begins processing. Maximum values to be provided should be around
		# 		100ms.
		# 		In the real-time configuration, this value represents the length of time
		# 		data is collected and compounded before returning a sweep. Values for
		# 		real-time should be between 16ms-100ms for optimal viewing and use.
		# 		In zero span mode this is the length of the returned sweep as a measure
		# 		of time. Sweep times for zero span must range between 10us and
		# 		100ms. Values outside this range are clamped.
		# rbwType  The possible values for rbwType are BB_NATIVE_RBW and
		# 		BB_NON_NATIVE_RBW. This choice determines which bandwidth table
		# 		is used and how the data is processed. BB_NATIVE_RBW is default and
		# 		unchangeable for real-time operation.
		# rejection  The possible values for rejection are BB_NO_SPUR_REJECT,
		# 		BB_SPUR_REJECT, and BB_BYPASS_RF.

		# The resolution bandwidth, or RBW, represents the bandwidth of spectral energy represented in each
		# frequency bin. For example, with an RBW of 10 kHz, the amplitude value for each bin would represent
		# the total energy from 5 kHz below to 5 kHz above the bin's center. For standard bandwidths, the API
		# uses the 3 dB points to define the RBW.
		# The video bandwidth, or VBW, is applied after the signal has been converted to frequency domain as
		# power, voltage, or log units. It is implemented as a simple rectangular window, averaging the amplitude
		# readings for each frequency bin over several overlapping FFTs. A signal whose amplitude is modulated at
		# Test Equipment Plus | 17
		# a much higher frequency than the VBW will be shown as an average, whereas amplitude modulation at
		# a lower frequency will be shown as a minimum and maximum value.
		# Native RBWs represent the bandwidths from a single power-of-2 FFT using our sample rate of 80 MSPS
		# and a high dynamic range window function. Each RBW is half of the previous. Using native RBWs can
		# give you the lowest possible bandwidth for any given sweep time, and minimizes processing power.
		# However, scalloping losses of up to 0.8 dB, occurring when a signal falls in between two bins, can cause
		# problems for some types of measurements.
		# Non-native RBWs use the traditional 1-3-10 sequence. As of version 1.0.7, non-native bandwidths are
		# not restricted to the 1-3-10 sequence but can be arbitrary. Programmatically, non-native RBW's are
		# achieved by creating variable sized bandwidth flattop windows.
		# sweepTime applies to regular sweep mode and real-time mode. If in sweep mode, sweepTime is the
		# amount of time the device will spend collecting data before processing. Increasing this value is useful for
		# capturing signals of interest or viewing a more consistent view of the spectrum. Increasing sweepTime
		# has a very large impact on the amount of resources used by the API due to the increase of data needing
		# to be stored and the amount of signal processing performed. For this reason, increasing sweepTime also
		# decreases the rate at which you can acquire sweeps.
		# In real-time, sweepTime refers to how long data is accumulated before returning a sweep. Ensure you
		# are capable of retrieving as many sweeps that will be produced by changing this value. For instance,
		# changing sweepTime to 32ms in real-time mode will return approximately 31 sweeps per second
		# (1000/32).
		# Rejection can be used to optimize certain aspects of the signal. Default is BB_NO_SPUR_REJECT, and
		# should be used in most cases. If you have a steady CW or slowly changing signal, and need to minimize
		# image and spurious responses from the device, use BB_SPUR_REJECT. If you have a signal between 300
		# MHz and 3 GHz, need the lowest possible phase noise, and do not need any image rejection,
		# BB_BYPASS_RF can be used to rewire the front end for lowest phase noise.

		self.log.info("Setting device sweep coupling settings.")

		rbw        = ct.c_double(rbw)
		vbw        = ct.c_double(vbw)
		sweepTime  = ct.c_double(sweepTime)

		if rbwType == "native":
			rbwType    = ct.c_uint(hf.BB_NATIVE_RBW)
		elif rbwType == "non-native":
			rbwType    = ct.c_uint(hf.BB_NON_NATIVE_RBW)
		else:
			raise ValueError("rbwType must be either \"native\" or \"non-native\". Passed value was %s." % rbwType)

		if rejection == "no-spur-reject":
			rejection    = ct.c_uint(hf.BB_NO_SPUR_REJECT)
		elif rejection == "spur-reject":
			rejection    = ct.c_uint(hf.BB_SPUR_REJECT)
		elif rejection == "bypass":
			rejection    = ct.c_uint(hf.BB_BYPASS_RF)
		else:
			raise ValueError("rejection must be either \"no-spur-reject\", \"spur-reject\" or \"bypass\". Passed value was %s." % rejection)



		err = self.dll.bbConfigureSweepCoupling(self.deviceHandle, rbw, vbw, sweepTime, rbwType, rejection)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("configureSweepCoupling Succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbBandwidthErr"]:
			raise IOError("'rbw' falls outside device limits or 'vbw' is greater than resolution bandwidth.")
		elif err == self.bbStatus["bbInvalidBandwidthTypeErr"]:
			raise IOError("'rbwType' is not one of the accepted values.")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			raise IOError("'rejection' value is not one of the accepted values.")
		else:
			raise IOError("Unknown error setting configureAcquisition! Error = %s" % err)




	def configureWindow(self, window):
		# BB_API bbStatus bbConfigureWindow(int device, unsigned int window);

		# device  Handle to the device being configured.
		# window  The possible values for window are BB_NUTALL, BB_BLACKMAN,
		# 		BB_HAMMING, and BB_FLAT_TOP.

		# This changes the windowing function applied to the data before signal processing is performed. In real-
		# time configuration the window parameter is permanently set to BB_NUTALL. The windows are only
		# changeable when using the BB_NATIVE_RBW type in bbConfigureSweepCoupling. When using
		# BB_NON_NATIVE_RBWs, a custom flattop window will be used.

		self.log.info("Setting device FFT windowing function.")

		if window == "nutall":
			window =  hf.BB_NUTALL
		elif window == "blackman":
			window = hf.BB_BLACKMAN
		elif window == "hamming":
			window = hf.BB_HAMMING
		elif window == "flat-top":
			window = hf.BB_FLAT_TOP
		else:
			raise ValueError("Window function name must be either \"nutall\", \"blackman\", \"hamming\" or \"flat-top\". Passed value was %s." % window)

		window = ct.c_uint(window)



		err = self.dll.bbConfigureWindow(self.deviceHandle, window)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureWindow succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidWindowErr"]:
			raise IOError("The specified windowing function is unknown.")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)



	def configureProcUnits(self, units):
		# BB_API bbStatus bbConfigureProcUnits(int device, unsigned int units);

		# device  Handle to the device being configured.
		# units  The possible values are BB_LOG, BB_VOLTAGE, BB_POWER, and
		# 		BB_BYPASS.


		# The units provided determines what unit type video processing occurs in. The chart below shows which
		# unit types are used for each units selection.
		# For “average power” measurements, BB_POWER should be selected. For cleaning up an amplitude
		# modulated signal, BB_VOLTAGE would be a good choice. To emulate a traditional spectrum analyzer,
		# select BB_LOG. To minimize processing power, select BB_BYPASS.

		# BB_LOG      = dBm
		# BB_VOLTAGE  = mV
		# BB_POWER    = mW
		# BB_BYPASS   = No video processing

		self.log.info("Setting device video processing units.")

		if units == "log":
			units =  hf.BB_LOG
		elif units == "voltage":
			units = hf.BB_VOLTAGE
		elif units == "power":
			units = hf.BB_POWER
		elif units == "bypass":
			units = hf.BB_BYPASS
		else:
			raise ValueError("Video processing unit name must be either \"log\", \"voltage\", \"power\" or \"bypass\". Passed value was %s." % units)

		units = ct.c_uint(units)

		err = self.dll.bbConfigureProcUnits(self.deviceHandle, units)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureProcUnits succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidVideoUnitsErr"]:
			raise IOError("The video-processing units did not match any available setting.")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)



	def configureTrigger(self, trigType, edge, level, timeout):
		# BB_API bbStatus bbConfigureTrigger(int device, unsigned int type, unsigned int edge, double level, double timeout);

		# device  Handle to the device being configured.
		# type  Specifies the type of trigger to use. Possible values are
		# 	BB_NO_TRIGGER, BB_VIDEO_TRIGGER, BB_EXTERNAL_TRIGGER, and
		# 	BB_GPS_PPS_TRIGGER. If an external signal is desired, BNC port 2 must
		# 	be configured to accept a trigger (see bbConfigureIO). When
		# 	BB_NO_TRIGGER is specified, the other parameters are ignored and this
		# 	function sets only trigger type.
		# edge  Specifies the edge type of a video trigger. Possible values are
		# 	BB_TRIGGER_RISING and BB_TRIGGER_FALLING. If you are using a
		# 	trigger type other than a video trigger, this value is ignored but must be
		# 	specified.
		# level  Level of the video trigger. The units of this value are determined by the
		# 	demodulation type used when initiating the device. If demodulating
		# 	AM, level is in dBm units, if demodulating FM, level is in Hz.
		# timeout  timeout specifies the length of a capture window in seconds. The
		# 	capture window specifies the length of continuous time you wish to
		# 	wait for a trigger. If no trigger is found within the window, the last
		# 	sweepTime of data within the data is returned. The capture window
		# 	must be greater than sweepTime. If it is not, it will be automatically
		# 	adjusted to sweepTime. The timeout/capture window is applicable to
		# 	both video and external triggering.

		# Allows you to configure all zero-span trigger related variables. As with all configure routines, the
		# changes made here are not reflected until the next initiate.
		# When a trigger is specified the sweep returned will start approximately 200 microseconds before the
		# trigger event. This provide a slight view of occurances directly before the event. If no trigger event is
		# found, the data returned at the end of the timeout period is returned.

		self.log.info("Setting device trigger configuration.")

		if trigType == "none":
			trigType =  hf.BB_NO_TRIGGER
		elif trigType == "video":
			trigType = hf.BB_VIDEO_TRIGGER
		elif trigType == "external":
			trigType = hf.BB_EXTERNAL_TRIGGER
			self.log.warning("configureIO must be called to set up BNC port 2 as an input for proper external trigger operation")
		elif trigType == "gps-pps":
			raise ValueError("GPS PPS Trigger not supported in API files. Please contact Test-Equipment-Plus for more information.")
			# trigType = hf.BB_GPS_PPS_TRIGGER
		else:
			raise ValueError("Trigger type must be either \"none\", \"video\", \"external\" or \"gps-pps\". Passed value was %s." % trigType)

		if edge == "rising-edge":
			edge =  hf.BB_NO_TRIGGER
		elif edge == "falling-edge":
			edge = hf.BB_VIDEO_TRIGGER
		else:
			raise ValueError("Trigger edge must be either \"rising-edge\", \"falling-edge\". Passed value was %s." % edge)


		trigType = ct.c_uint(trigType)
		edge = ct.c_uint(edge)
		level = ct.c_double(level)
		timeout = ct.c_double(timeout)

		err = self.dll.bbConfigureTrigger(self.deviceHandle, trigType, edge, level, timeout)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureTrigger succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			raise IOError("A parameter specified is not valid.")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)


	def configureTimeGate(self, delay, length, timeout):
		# BB_API bbStatus bbConfigureTimeGate(int device, double delay, double length, double timeout);
		# device  Handle to the device being configured.
		# delay  The time in seconds, from the trigger to the beginning of the gate
		# length  The length in seconds, of the gate
		# timeout  The time in seconds to wait for a trigger. If no trigger is found, the last
		# 		length will be used.

		# Time gates are relative to an external trigger.
		# Therefore it is necessary to use bbConfigureIO to setup an external trigger.

		self.log.info("Setting device external trigger time-gating settings.")
		self.log.warning("configureTimeGate is only valid for external trigger sources.")
		self.log.warning("Please ensure you are set up to use an external trigger")

		delay = ct.c_double(delay)
		length = ct.c_double(length)
		timeout = ct.c_double(timeout)

		err = self.dll.bbConfigureTimeGate(self.deviceHandle, delay, length, timeout)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureTimeGate succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			raise IOError("A parameter specified is not valid.")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

	def configureRawSweep(self, start, ppf, steps):
		# BB_API bbStatus bbConfigureRawSweep(int device, int start, int ppf, int steps, int stepsize);
		# device  Handle to the device being configured.
		# start  Frequency value in MHz representing the center of the first 20MHz step
		# 	in the sweep. Must be a multiple of 20, and no less than 20.
		# ppf  Controls the amount of digital samples to collect at each frequency
		# 	step. The number of digital samples collected at each frequency equals
		# 	18688 * ppf.
		# steps  Number of steps to take starting with and including the first steps.
		# stepsize  Value must be BB_TWENTY_MHZ

		# This function configures the device for both BB_RAW_SWEEP and BB_RAW_SWEEP_LOOP modes. This
		# function allows you to configure the sweep start frequency, the number of 20 MHz steps to take across
		# the spectrum, and how long to dwell at each frequency. There are restrictions on these settings,
		# outlined below.


		self.log.info("Setting device raw sweep mode configuration.")

		if start % 20 != 0 or start < 20:
			raise ValueError("The 'start' parameter must be a multiple of 20MHz")
		if (ppf * steps) % 16 != 0:
			raise ValueError("(ppf * steps) must be a multiple of 16")

		if start + (steps *20) > 6000:
			raise ValueError("The final center frequency, obtained by the equation (start + steps*20), cannot be greater than 6000 (6 GHz).")


		start = ct.c_int(start)
		ppf = ct.c_int(ppf)
		steps = ct.c_int(steps)
		stepSize = ct.c_int(hf.BB_TWENTY_MHZ)

		err = self.dll.bbConfigureRawSweep(self.deviceHandle, start, ppf, steps, stepSize)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureTimeGate succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			raise IOError("A parameter specified is not valid.")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

	def configureIO(self, port1Coupling, port1mode, port2mode):
		# BB_API bbStatus bbConfigureIO(int device, unsigned int port1, unsigned int port2);
		# device  Handle to the device being configured.
		# port1  The first BNC port may be used to input or output a 10 MHz time base
		# 	(AC or DC coupled), or to generate a general purpose logic high/low
		# 	output. Please refer to the example below. All possible values for this
		# 	port are found in the header file and are prefixed with “BB_PORT1”
		# port2  Port 2 is capable of accepting an external trigger or generating a logic
		# 	output. Port 2 is always DC coupled. All possible values for this port are
		# 	found in the header file and are prefixed with “BB_PORT2.”

		# NOTE: This function can only be called when the device is idle (not operating in any mode). To ensure
		# the device is idle, call bbAbort().
		# There are two configurable BNC connector ports available on the device. Both ports functionality are
		# changed with this function. For both ports, ‘0’ is the default and can be supplied through this function to
		# return the ports to their default values. Specifying a ‘0’ on port 1 returns the device to an internal time
		# base and outputs the time base AC coupled. Specifying ‘0’ on port 2 emits a DC coupled logic low.
		# For external 10 MHz timebases, best phase noise is achieved by using a low jitter 3.3V CMOS input.
		# Configure combinations


		# Port 1 IO  For port 1 only a coupled value must be ‘OR’ed
		# together with a port type. Use the ‘|’ operator to
		# combine a coupled type and a port type.

		# BB_PORT1_AC_COUPLED               Denotes an AC coupled port
		# BB_PORT1_DC_COUPLED               Denotes a DC coupled port
		# BB_PORT1_INT_REF_OUT              Output the internal 10 MHz timebase
		# BB_PORT1_EXT_REF_IN               Accept an external 10MHz time base
		# BB_PORT1_OUT_LOGIC_LOW            Self-explanitory
		# BB_PORT1_OUT_LOGIC_HIGH           Self-explanitory

		# Port 2 IO
		# BB_PORT2_OUT_LOGIC_LOW            Self-explanitory
		# BB_PORT2_OUT_LOGIC_HIGH           Self-explanitory
		# BB_PORT2_IN_TRIGGER_RISING_EDGE   When set, the device is notified of a rising edge
		# BB_PORT_IN_TRIGGER_FALLING_EDGE   When set, the device is notified of a falling edge

		self.log.info("Setting device IO Configuration.")

		port1 = 0
		port2 = 0
		if port1Coupling == "ac":
			port1 |= hf.BB_PORT1_AC_COUPLED
		elif port1Coupling == "dc":
			port1 |= hf.BB_PORT1_DC_COUPLED
		else:
			raise ValueError("Port1Coupling must be either'ac' or 'dc'. Passed value was %s." % port1Coupling)

		if port1mode == "int-ref-out":
			port1 |= hf.BB_PORT1_INT_REF_OUT
		elif port1mode == "ext-ref-in":
			port1 |= hf.BB_PORT1_EXT_REF_IN
		elif port1mode == "out-logic-low":
			port1 |= hf.BB_PORT1_OUT_LOGIC_LOW
		elif port1mode == "out-logic-high":
			port1 |= hf.BB_PORT1_OUT_LOGIC_HIGH
		else:
			raise ValueError("port1mode must be either \"int-ref-out\", \"ext-ref-in\", \"out-logic-low\" or \"out-logic-high\". Passed value was %s." % port1mode)


		if port2mode == "int-ref-out":
			port2 |= hf.BB_PORT2_IN_TRIGGER_RISING_EDGE
		elif port2mode == "ext-ref-in":
			port2 |= hf.BB_PORT2_IN_TRIGGER_FALLING_EDGE
		elif port2mode == "out-logic-low":
			port2 |= hf.BB_PORT2_OUT_LOGIC_LOW
		elif port2mode == "out-logic-high":
			port2 |= hf.BB_PORT2_OUT_LOGIC_HIGH
		else:
			raise ValueError("port1mode must be either \"int-ref-out\", \"ext-ref-in\", \"out-logic-low\" or \"out-logic-high\". Passed value was %s." % port1mode)


		port1 = ct.c_uint(port1)
		port2 = ct.c_uint(port2)

		err = self.dll.bbConfigureIO(self.deviceHandle, port1, port2)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureIO succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotIdleErr"]:
			raise IOError("The device is currently operating in a mode. The device must be idle to configure ports.")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			raise IOError("A parameter supplied is unknown.")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)


	def configureDemod(self, modulationType, freq, ifBw, audioLowPassFreq, audioHighPassFreq, fmDeemphasis):
		# BB_API bbStatus bbConfigureDemod(int device, int modulationType, double freq, float IFBW, float audioLowPassFreq, float audioHighPassFreq, float FMDeemphasis);

		# device  Handle to the device being configured.
		# modulationType  Specifies the demodulation scheme, possible values are
		# 		BB_DEMOD_AM/FM/Upper sideband (USB)/Lower Sideband (LSB)/CW.
		# freq  Center frequency. For best results, re-initiate the device if the center frequency changes +/- 8MHz from the initial value.
		# IFBW  Intermediate frequency bandwidth centered on freq. Filter takes place
		# 		before demodulation. Specified in Hz. Should be between 2kHz and 500kHz.
		# audioLowPassFreq  Post demodulation filter in Hz. Should be between 1kHz and 12kHz Hz.
		# audioHighPassFreq  Post demodulation filter in Hz. Should be between 20 and 1000Hz.
		# FMDeemphasis  Specified in micro-seconds. Should be between 1 and 100.

		# This function can be called while the device is active.
		# Note : If any of the boundary conditions are not met, this function will return with no error but the
		# values will be clamped to its boundary values

		self.log.info("Setting device demodulator Configuration.")

		if modulationType == "am":
			modulationType = hf.BB_DEMOD_AM
		elif modulationType == "fm":
			modulationType = hf.BB_DEMOD_FM
		elif modulationType == "usb":
			modulationType = hf.BB_DEMOD_USB
		elif modulationType == "lsb":
			modulationType = hf.BB_DEMOD_LSB
		elif modulationType == "cw":
			modulationType = hf.BB_DEMOD_CW
		else:
			raise ValueError("Modulation Type must be either \"am\", \"fm\", \"usb\", \"lsb\" or \"cw\". Passed value was %s." % modulationType)

		if ifBw < 2e3 or ifBw > 500e3:
			raise ValueError("IFBW Should be between 2kHz and 500kHz.")

		if audioLowPassFreq < 1e3 or audioLowPassFreq > 12e3:
			raise ValueError("Audio low-pass Should be between 1kHz and 12kHz Hz.")

		if audioHighPassFreq < 20 or audioHighPassFreq > 1e3:
			raise ValueError("Audio high-pass should be between 20 and 1000Hz.")

		if fmDeemphasis < 1 or fmDeemphasis > 100:
			raise ValueError("FM De-emphasis should be between 1 and 100 microseconds.")


		modulationType     = ct.c_int(modulationType)
		freq               = ct.c_double(freq)
		ifBw               = ct.c_float(ifBw)
		audioLowPassFreq   = ct.c_float(audioLowPassFreq)
		audioHighPassFreq  = ct.c_float(audioHighPassFreq)
		fmDeemphasis       = ct.c_float(fmDeemphasis)


		err = self.dll.bbConfigureDemod(self.deviceHandle, modulationType, freq, ifBw, audioLowPassFreq, audioHighPassFreq, fmDeemphasis)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureDemod succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

	def initiate(self, mode, flag):
		# BB_API bbStatus bbInitiate(int device, unsigned int mode, unsigned int flag);


		if mode == "sweeping":
			mode = hf.BB_SWEEPING
		elif mode == "real-time":
			mode = hf.BB_REAL_TIME
		elif mode == "zero-span":
			mode = hf.BB_ZERO_SPAN
		elif mode == "time-gate":
			mode = hf.BB_TIME_GATE
		elif mode == "raw-sweep":
			mode = hf.BB_RAW_SWEEP
		elif mode == "raw-sweep-loop":
			mode = hf.BB_RAW_SWEEP_LOOP
		elif mode == "audio-demod":
			mode = hf.BB_AUDIO_DEMOD
		elif mode == "raw-pipe":
			mode = hf.BB_RAW_PIPE
		else:
			raise ValueError("Mode must be one of \"sweeping\", \"real-time\", \"zero-span\", \"time-gate\", \"raw-sweep\", \"raw-sweep-loop\", \"audio-demod\" or \"raw-pipe\". Passed value was %s." % mode)


		if mode == hf.BB_ZERO_SPAN:
			if flag == "demod-am":
				flag = hf.BB_DEMOD_AM
			elif flag == "demod-fm":
				flag = hf.BB_DEMOD_FM
			else:
				raise ValueError("Available flag settings for mode \"zero-span\" are \"demod-am\" and \"demod-fm\". Passed value was %s." % flag)

		elif mode == hf.BB_RAW_PIPE:
			if flag == "7-mhz":
				flag = hf.BB_DEMOD_AM
			elif flag == "20-mhz":
				flag = hf.BB_DEMOD_FM
			else:
				raise ValueError("Available flag settings for mode \"raw-pipe\" are \"7-mhz\" or \"20-mhz\". Passed value was %s." % flag)

			self.log.warning("GPS flag configuration masking not currently supported")

		else:
			flag = 0


		mode = ct.c_uint(mode)
		flag = ct.c_uint(flag)

		err = self.dll.bbInitiate(self.deviceHandle, mode, flag)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureDemod succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			self.log.error('''In real-time mode, this value may be returned if the span limits defined in the API header are broken. Also in real-time mode, this error will be
				returned if the resolution bandwidth is outside the limits defined in the API header.''')
			self.log.error('''In time-gate analysis mode this error will be returned if span limits defined in the API header are broken. Also in time gate analysis, this
				error is returned if the bandwidth provided require more samples for processing than is allowed in the gate length. To fix this, increase rbw/vbw.''')
			raise IOError("The value for mode did not match any known value.")
		elif err == self.bbStatus["bbAllocationLimitError"]:
			self.log.error('''This value is returned in extreme circumstances. The API currently limits the amount of RAM usage to 1GB. When exceptional parameters are
				provided, such as very low bandwidths, or long sweep times, this error may be returned. At this point you have reached the boundaries of the
				device. The processing algorithms are optimized for speed at the expense of space, which is the reason this can occur.''')
			raise IOError("Could not allocate sufficent RAM!")

		elif err == self.bbStatus["bbBandwidthErr"]:
			raise IOError("RBW is larger than your span. (Sweep Mode)!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

	def fetchTrace(self, arraySize):
		# BB_API bbStatus bbFetchTrace(int device, int arraySize, double *min, double *max);
		# device  Handle of an initialized device.
		# arraySize  A provided arraySize. This value must be equal to or greater than the
		# traceSize value returned from bbQueryTraceInfo.
		# 		min  Pointer to a double buffer, whose length is equal to or greater than
		# traceSize returned from bbQueryTraceInfo.
		# 		max  Pointer to a double buffer, whose length is equal to or greater than
		# traceSize returned from bbQueryTraceInfo.

		# Returns a minimum and maximum array of values relating to the current mode of operation. If the
		# detectorType provided in bbConfigureAcquisition is BB_AVERAGE, the array will be populated with the
		# same values. Element zero of each array corresponds to the startFreq returned from bbQueryTraceInfo.

		maxArr = (ct.c_double * arraySize)()
		minArr = (ct.c_double * arraySize)()

		maxPtr = ct.pointer(maxArr)
		minPtr = ct.pointer(minArr)

		err = self.dll.bbFetchTrace(self.deviceHandle, arraySize, minPtr, maxPtr)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to fetchTrace succeeded.")
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		elif err == self.bbStatus["bbBufferTooSmallErr"]:
			raise IOError("The 'arraySize' parameter passed is less than the trace size returned from 'bbQueryTraceInfo'.")
		elif err == self.bbStatus["bbADCOverflow"]:
			raise IOError("The ADC has detected clipping of the input signal!")
		elif err == self.bbStatus["bbNoTriggerFound"]:
			raise IOError('''In time-gated analysis, if the spectrum returned is not representative of
				the gate specified, this warning is returned.
				In zero-span analysis, if the device is configured to anticipate a video or
				external trigger, this warning is returned when the trigger condition has
				not been met for this trace.''')
		elif err == self.bbStatus["bbPacketFramingErr"]:
			raise IOError("Data loss or miscommunication has occurred between the device and the API!")
		elif err == self.bbStatus["bbDeviceConnectionErr"]:
			raise IOError("Device connection issues were present in the acquisition of this sweep!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

	def fetchAudio(self, *audio):
		# BB_API bbStatus bbFetchAudio(int device, float *audio);

		pass

	def fetchRawCorrections(self):
		# BB_API bbStatus bbFetchRawCorrections(int device, float *corrections, int *index, double *startFreq);

		pass

	def fetchRaw(self):
		# BB_API bbStatus bbFetchRaw(int device, float *buffer, int *triggers);

		pass

	def fetchRaw_s(self):
		# BB_API bbStatus bbFetchRaw_s(int device, short *buffer, int *triggers);

		pass

	def fetchRawSweep(self):
		# BB_API bbStatus bbFetchRawSweep(int device, short *buffer);

		pass

	def startRawSweepLoop(self, callbackFunc):
		# BB_API bbStatus bbStartRawSweepLoop(int device, void(*sweep_callback)(short *buffer, int len));

		# device  Handle of an initialized device.
		# sweep_callback  Pointer to a C function. Used as a callback to notify the user of
		# 		completed sweeps.

		# This function can be called after being configured and initiated in RAW_SWEEP_LOOP mode. The device
		# begins sweeping on the first call to this function after the device has been initiated. It is possible to call
		# this function multiple times per initiate to change the function call back used.
		# If this function returns successfully, the device begins sweeping immediately. The function provided is
		# set as the callback function used when a sweep is completed. sweep_callback is called once per sweep
		# completion. The function passes two parameters, a pointer to the buffer of data for the sweep, and the
		# length of the buffer.
		# The data buffer will not be overwritten when in the function body of sweep_callback. The API will
		# maintain a circular list of buffers to store sweeps in. The API will store up to ¼ to ½ seconds worth of
		# sweeps depending on parameters. If the function body of sweep_callback exceeds this amount of time,
		# it is possible for the API to need to move ahead and skip over the buffer the user is still accessing. This
		# will cause a loss of data. It is recommended the function body of sweep_callback is short, preferably
		# simply copying the data from buffer into your own data structure. This ensures you receive every sweep
		# and make your own decisions on when to drop/ignore sweeps.
		# The sweep_callback function is not called in the main thread of execution. It is called once per sweep,
		# which can result in the function being called anywhere from 3-250 milliseconds. It is the responsibility of
		# the user to not index the buffer out of range. The buffer contents can be modified by the user only
		# during the function body of sweep_callback, once the function returns, the API is free to overwrite the
		# contents. Modifying the contents of the buffer not in the function body of sweep_callback is undefined.
		# The user should not attempt to manage any of the memory provided through the buffer pointers.
		# The device sweeps indefinitely until bbAbort or bbCloseDevice is called. When operation is suspended
		# via bbAbort, the device must be reconfigured and initiated again before calling this function.

		if not callable(callbackFunc):
			raise ValueError("You must pass a callable variable for the callback!")

		callBackFactory = ct.WINFUNCTYPE(None, ct.POINTER(ct.c_short), ct.c_int)
		self.cRawSweepCallbackFunc = callBackFactory(callbackFunc)

		err = self.dll.bbStartRawSweepLoop(self.deviceHandle, self.cRawSweepCallbackFunc)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Started raw sweep loop.")
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		else:
			raise IOError("Unknown error!")


	def queryTraceInfo(self):
		# BB_API bbStatus bbQueryTraceInfo(int device, unsigned int *traceLen, double *binSize, double *start);

		# device  Handle of an initialized device.
		# traceLen  A pointer to an unsigned int. If the function returns successfully
		# 		traceLen will contain the size of arrays returned by bbFetchTrace.
		# binSize  A pointer to a 64bit floating point variable. If the function returns
		# 		successfully, binSize will contain the frequency difference between two
		# 		sequential bins in a returned sweep. In Zero-Span mode, binSize refers
		# 		to the difference between sequential samples in seconds.
		# start  A pointer to a 64bit floating point variable. If the function returns
		# 		successfully, start will contain the frequency of the first bin in a
		# 		returned sweep. In Zero-Span mode, start represents the exact center
		# 		frequency used by the API.

		# This function should be called to determine sweep characteristics after a device has been configured
		# and initiated. For zero-span mode, startFreq and binSize will refer to the time domain values. In zero-
		# span mode startFreq will always be zero, and binSize will be equal to sweepTime/traceSize.

		self.log.info("Querying device for trace information.")

		traceLen = ct.c_uint(0)
		traceLenPnt = ct.pointer(traceLen)

		binSize = ct.c_double(0)
		binSizePnt = ct.pointer(binSize)

		start = ct.c_double(0)
		startPnt = ct.pointer(start)


		err = self.dll.bbQueryTraceInfo(self.deviceHandle, traceLenPnt, binSizePnt, startPnt)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("returned queryTraceInfo: %d, %f, %f" % (traceLen.value, binSize.value, start.value))
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		else:
			raise IOError("Unknown error!")

		return (traceLen.value, binSize.value, start.value)

	def queryStreamingCenter(self):
		# BB_API bbStatus bbQueryStreamingCenter(int device, double *center);
		# device  Handle of an initialized device.
		# center  Pointer to a double which will receive the absolute center frequency of
		# 		the streaming device.

		# The function retrieves the center frequency of the 20 MHz IF bandwidth of a device currently initialized
		# in raw pipe mode. The center returned is representative of ¼ of the IF sample rate. The 20 MHz of usable
		# bandwidth is centered on this frequency.

		self.log.info("Querying device for streaming center-freqency.")

		center = ct.c_double(0)
		centerPnt = ct.pointer(center)


		err = self.dll.bbQueryStreamingCenter(self.deviceHandle, centerPnt)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("returned streaming center-frequency: %f" % (center.value))
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		else:
			raise IOError("Unknown error!")

		return center.value



	def queryTimestamp(self):
		# BB_API bbStatus bbQueryTimestamp(int device, unsigned int *seconds, unsigned int *nanoseconds);

		# device  Handle of an initialized device.
		# seconds  Seconds since midnight (00:00:00), January 1, 1970, coordinated
		# 		universal time(UTC).
		# nanoseconds  nanoseconds between seconds and seconds + 1

		# This function is used in conjunction with bbSyncCPUtoGPS and a GPS device to retrieve an absolute time
		# for a data packet in raw pipe mode. This function returns an absolute time for the last packet retrieved
		# from bbFetchRaw. See the Appendix:Code Examples for information on how to setup and interpret the
		# time information.

		self.log.info("Querying device for timestamp.")
		seconds = ct.c_uint(0)
		nanoseconds = ct.c_uint(0)

		secondsPnt = ct.pointer(seconds)
		nanosecondsPnt = ct.pointer(nanoseconds)

		err = self.dll.bbQueryTimestamp(self.deviceHandle, secondsPnt, nanosecondsPnt)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("returned timestamp values: Seconds - %d, nanoseconds - %d" % (seconds.value, nanoseconds.value))
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		else:
			raise IOError("Unknown error!")

		return (seconds.value, nanoseconds.value)

	def abort(self):
		# BB_API bbStatus bbAbort(int device);

		# Stops the device operation and places the device into an idle state.

		self.log.info("Stopping acquisition")

		err = self.dll.bbAbort(self.deviceHandle)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to abort succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device was already idle!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)


	def preset(self):
		# BB_API bbStatus bbPreset(int device);

		# This function exists to invoke a hard reset of the device. This will function similarly to a power
		# cycle(unplug/re-plug the device). This might be useful if the device has entered an undesirable or
		# unrecoverable state. Often the device might become unrecoverable if a program closed unexpectedly,
		# not allowing the device to close properly. This function might allow the software to perform the reset
		# rather than ask the user perform a power cycle.

		# Viewing the traces returned is often the best way to determine if the device is operating normally. To
		# utilize this function, the device must be open. Calling this function will trigger a reset which happens
		# after 2 seconds. Within this time you must call bbCloseDevice to free any remaining resources and
		# release the device serial number from the open device list. From the time of the bbPreset call, we
		# suggest 3 to more seconds of wait time before attempting to re-open the device.

		self.log.warning("Performing hardware-reset of device!")
		self.log.warning("Please ensure you close the device handle within two seconds of this call!")

		err = self.dll.bbPreset(self.deviceHandle)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to preset succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

	def selfCal(self):
		# BB_API bbStatus bbSelfCal(int device);

		# This function causes the device to recalibrate itself to adjust for internal device temperature changes,
		# generating an amplitude correction array as a function of IF frequency. This function will explicitly call
		# bbAbort() to suspend all device operations before performing the calibration, and will return the device
		# in an idle state and configured as if it was just opened. The state of the device should not be assumed,
		# and should be fully reconfigured after a self-calibration.
		# Temperature changes of 2 degrees Celsius or more have been shown to measurably alter the
		# shape/amplitude of the IF. We suggest using bbQueryDiagnostics to monitor the device’s temperature
		# and perform self-calibrations when needed. Amplitude measurements are not guaranteed to be
		# accurate otherwise, and large temperature changes (10 ° C or more) may result in adding a dB or more of
		# error.
		# Because this is a streaming device, we have decided to leave the programmer in full control of when the
		# device in calibrated. The device is calibrated once upon opening the device through bbOpenDevice and is
		# the responsibility of the programmer after that.
		# Note:
		# After calling this function, the device returns to the default state. Currently the API does not retain state
		# prior to the calling of bbSelfCal(). Fully reconfiguring the device will be necessary.

		self.log.info("Performing self-calibration of device.")

		err = self.dll.bbSelfCal(self.deviceHandle)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to selfCal succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

	def syncCPUtoGPS(self, comPort, baudRate):
		# BB_API bbStatus bbSyncCPUtoGPS(int comPort, int baudRate);

		self.log.error("GPS Synchronization not yet implemented.")
		self.log.error("e-mail Connor at connorw@imaginaryindustries.com for more information")


	def getDeviceType(self):
		# BB_API bbStatus bbGetDeviceType(int device, int *type);

		# This function may be called only after the device has been opened. If the device successfully opened,
		# type will contain the model type of the device pointed to by handle.
		# Possible values for type are BB_DEVICE_NONE, BB_DEVICE_BB60A, BB_DEVICE_BB124. These values can
		# be found in the bb_api header file

		self.log.info("Querying device for model information")

		devType = ct.c_uint(0)
		devTypePnt = ct.pointer(devType)

		err = self.dll.bbGetDeviceType(self.deviceHandle, devTypePnt)

		if err == self.bbStatus["bbNoError"]:
			pass
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

		if devType.value == hf.BB_DEVICE_NONE:
			dev = "No device"
		elif devType.value == hf.BB_DEVICE_BB60A:
			dev = "BB60A"
		elif devType.value == hf.BB_DEVICE_BB60C:
			dev = "BB60C"
		elif devType.value == hf.BB_DEVICE_BB124A:
			dev = "BB124"
		else:
			raise ValueError("Unknown device type!")

		self.log.info("Call to getDeviceType succeeded. Type = %s" % dev)

		return dev


	def getSerialNumber(self):
		# BB_API bbStatus bbGetSerialNumber(int device, unsigned int *sid);

		# This function may be called only after the device has been opened. The serial number returned should
		# match the number on the case.

		self.log.info("Querying device for serial number.")

		serialNo = ct.c_uint(0)
		serialNoPnt = ct.pointer(serialNo)


		err = self.dll.bbGetSerialNumber(self.deviceHandle, serialNoPnt)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to getSerialNumber succeeded. Value = %s" % serialNo.value)
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

		return serialNo.value

	def getFirmwareVersion(self):
		# BB_API bbStatus bbGetFirmwareVersion(int device, int *version);

		# Use this function to determine which version of firmware is associated with the specified device.


		self.log.info("Querying device for firmware version.")

		firmwareRev = ct.c_uint(0)
		firmwareRevPnt = ct.pointer(firmwareRev)


		err = self.dll.bbGetFirmwareVersion(self.deviceHandle, firmwareRevPnt)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to getFirmwareVersion succeeded. Value = %s" % firmwareRev.value)
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		else:
			raise IOError("Unknown error setting configureLevel! Error = %s" % err)

		return firmwareRev.value


	def getAPIVersion(self):
		# BB_API const char* bbGetAPIVersion();

		# The returned string is of the form
		# major.minor.revision
		# Ascii periods (“.”) separate positive integers. Major/Minor/Revision are
		# not gauranteed to be a single decimal digit. The string is null
		# terminated. An example string is below ..
		# [ ‘1’ | ‘.’ | ‘2’ | ‘.’ | ‘1’ | ‘1’ | ‘\0’ ] = “1.2.11”


		self.log.info("Querying API for revision information.")

		self.dll.bbGetAPIVersion.restype = ct.c_char_p  # Tell ctypes this function returns a pointer to a string
		apiRevStr = self.dll.bbGetAPIVersion(self.deviceHandle)
		ret = ct.c_char_p(apiRevStr).value 		# Dereference pointer, extract string
		self.log.info("Device firmware rev = %s" % ret)
		return ret

	def getErrorString(self, errCode):
		# BB_API const char* bbGetErrorString(bbStatus status);

		# Produce an ascii string representation of a given status code. Useful for debugging.
		# Probably not really needed, since I'm doing error decoding locally in each function.

		# This /should/ be of type bbStatus. bbStatus is an enum with hard-coded values, so I'm being lazy, and just using
		# an int. It works well enough.

		serialNo = ct.c_int(errCode)

		self.dll.bbGetAPIVersion.restype = ct.c_char_p  # Tell ctypes this function returns a pointer to a string
		apiRevStr = self.dll.bbGetAPIVersion(self.deviceHandle, serialNo)

		return ct.c_char_p(apiRevStr).value  # Dereference pointer, extract string, return it.


START_TIME = time.time()

def testFunct(bufPtr, bufLen):
	global START_TIME  #hacking about for determining callback interval times. I shouldn't be using global, but fukkit.
	now = time.time()

	print "Callback!", bufPtr, bufLen
	print bufPtr[0]
	# HOLY UNPACKING ONE-LINER BATMAN
	arr = np.frombuffer(int_asbuffer(ct.addressof(bufPtr.contents), bufLen * 2), dtype=np.short)  # Map array memory as a numpy array.
	arr = arr.copy()  # Then copy it, so our array won't get modified when the circular buffer overwrites itself.
	# We have to copy() since the call normally just returns a array that is overlaid onto the pre-existing data

	print "NP Array = ", arr.shape, arr
	print "Elapsed Time = ", now-START_TIME
	START_TIME = now

def go():

	logSetup.initLogging()
	sh = SignalHound()
	# sh.preset()
	sh.queryDeviceDiagnostics()
	sh.configureAcquisition("average", "log-scale")
	sh.configureCenterSpan(150e6, 100e6)
	sh.configureLevel(-50, 10)
	sh.configureGain(0)
	sh.configureSweepCoupling(9.863e3, 9.863e3, 10, "native", "no-spur-reject")
	sh.configureWindow("hamming")
	sh.configureProcUnits("power")
	sh.configureTrigger("none", "rising-edge", 0, 5)
	sh.configureIO("dc", "int-ref-out", "out-logic-low")
	# sh.configureDemod("fm", 92.9e6, 250e3, 12e3, 20, 50)
	sh.getDeviceType()
	sh.getSerialNumber()
	sh.getFirmwareVersion()
	sh.getAPIVersion()
	sh.initiate("raw-sweep-loop", 0)
	# print sh.queryTimestamp()
	sh.startRawSweepLoop(testFunct)

	try:
		time.sleep(50)
	except KeyboardInterrupt:
		pass
	# sh.configureTimeGate(0,0,0)
	# sh.configureRawSweep(500, 10, 16)

	sh.abort()
	sh.closeDevice()



if __name__ == "__main__":
	go()
