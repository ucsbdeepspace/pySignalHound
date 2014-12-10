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

# TODO: Respin lots of the messy if: elif: else: statements into a dictionary lookup

import ctypes as ct
import ctypes.util as ctu
import bb_api_h as hf


import sys

if sys.platform == "win32":
	from ctypes import wintypes as wt
else:
	raise ValueError("Only windows is currently supported by the SignalHound hardware.")

import logging

import numpy as np
from numpy.core.multiarray import int_asbuffer
import os.path


class SignalHound(object):


	#: C Call return value -> integer return code mapping
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

	#: C Array size for raw sweep requests
	_rawDataArrSize = 299008

	#: Raw sweep trigger C array size
	_rawSweepTriggerArraySize = 68

	__devType = None

	def __init__(self):

		self.log = logging.getLogger("Main.DeviceInt")
		self.devOpen = False

		if sys.platform == "win32":

			self.log.info("Opening DLL")
			libPath = ctu.find_library("bb_api.dll")

			if not libPath:
				if os.path.exists("bb_api.dll"):  # This is a messy hack, but it makes imports work with my scripts. I should
													# Really put the signal hound DLL on my $PATH, but whatever
					libPath = "bb_api.dll"
				elif os.path.exists("../bb_api.dll"):
					libPath = "../bb_api.dll"

				# So, apparently despite the fact that the setup.py script drops the signal hound
				# dll in the python/DLLs directory, and the fact that that directory is in sys.path,
				# find_library somehow doesn't find it anyways.
				# As such, manually check the DLLs directory for the signalHound dll
				elif os.path.exists(os.path.join(sys.exec_prefix, "DLLs", "bb_api.dll")):
					libPath = os.path.join(sys.exec_prefix, "DLLs", "bb_api.dll")
				else:
					self.log.error("Could not locate signal hound DLL.")
					raise EnvironmentError("Required DLL not available on system PATH")


			self.log.info("Found dll located at %s", libPath)
			self.dll = ct.CDLL (libPath)

			# This is horrible ctypes DLL hackery
			# You need to access the internal DLL handle to properly force windows to close the dll handle, which
			# is the only way to COMPLETELY close the device interface.

			# It's needed if you ever want to completely close the device, to re-initialize the device interface.
			# ctypes doesn't make manually deallocating a dll easy.
			self.dllHandle = wt.HMODULE(self.dll._handle)



		elif sys.platform == "linux" or sys.platform == "linux2":
			self.log.error("Linux Not supported for API Verson 2.x!")
			raise NotImplementedError("Linux Not supported for API Verson 2.x!")


		self.cRawSweepCallbackFunc = None

		self.openDevice()

		self.acq_conf = {}

		self.sequentialADCErrors = 0

	def __del__(self):
		self.log.info("Deleting SignalHound Interface Class")
		self.forceClose()

	def forceClose(self):
		self.log.info("Force Closing.")
		if self.devOpen:
			self.closeDevice()

		if self.cRawSweepCallbackFunc:
			del(self.cRawSweepCallbackFunc)


		# Note: This is *probably* not needed. I was having some issues with dangling handles when doing
		# multople-process data-logging, and it was part of the debugging effort from that.
		# At this point, it's probably uneeded (it wasn't the root of the issue), but it's
		# harmless, and I figure it's better to explicitly clean-up the DLL handle then
		# rely on it happening automatically
		self.log.info("Forcing DLL handle closed")

		if sys.platform == "win32":
			try:
				ct.windll.kernel32.FreeLibrary(self.dllHandle)
			except ct.ArgumentError as e:
				self.log.warning("Argument error in forcing DLL closed")
				self.log.warning("%s", e)




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

		self._devType = self.getDeviceType()

		self.log.info("Opened Device with handle num: %s", self.deviceHandle.value)

	def closeDevice(self):
		self.log.info("Closing Device with handle num: %s", self.deviceHandle.value)
		try:
			self.dll.bbAbort(self.deviceHandle)
			self.log.info("Running acquistion aborted.")
		except Exception as e:
			self.log.info("Could not abort acquisition: %s", e)


		ret = self.dll.bbCloseDevice(self.deviceHandle)

		if ret != hf.bbNoError:
			raise ValueError("Error closing device!")
		self.log.info("Closed Device with handle num: %s", self.deviceHandle.value)
		self.devOpen = False


	def queryDeviceDiagnostics(self):
		raise DeprecationWarning("This function is no longer supported in the 2.0 SignalHound API")


	def getDeviceDiagnostics(self):
		'''

		Query signal-hound's physical state and hardware status.

		Args:
			No Args
		Returns:
			dictionary containing current temperature, USB Voltage, and current:

				| {
				|	"temperature": <Internal temperature of the SignalHound in Degrees Celcius.>,
				|	"voltageUSB":  <USB operating voltage, in volts. Acceptable ranges are 4.40 to 5.25 V.>,
				|	"currentUSB":  <USB current draw, in mA. Acceptable ranges are 800 - 1000 mA>,
				| }


		The device temperature is updated in the API after each sweep is retrieved. The temperature is returned
		in Celsius and has a resolution of 1/8 th of a degree. A temperature above 70 ° C or below 0 ° C indicates
		your device is operating outside of its normal operating temperature, and may cause readings to be out
		of spec, and may damage the device.

		A USB voltage of below 4.4V may cause readings to be out of spec. Check your cable for damage and
		USB connectors for damage or oxidation.

		Will raise ``EnvironmentError`` for temperatures or voltages outside the allowable range.

		Raw call ``BB_API bbStatus bbGetDeviceDiagnostics(int device, float *temperature, float *voltage1_8, float *voltage1_2, float *voltageUSB, float *currentUSB);``

		'''

		# self.log.info("Querying device diagnostics.")
		temperature = ct.c_float(0)
		voltageUSB = ct.c_float(0)
		currentUSB = ct.c_float(0)

		temperaturePnt = ct.pointer(temperature)
		voltageUSBPnt = ct.pointer(voltageUSB)
		currentUSBPnt = ct.pointer(currentUSB)



		err = self.dll.bbGetDeviceDiagnostics(self.deviceHandle, temperaturePnt, voltageUSBPnt, currentUSBPnt)

		if err == self.bbStatus["bbNoError"]:
			pass
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		else:
			raise IOError("Unknown error!")



		ret = {
			"temperature" :  temperature.value,
			"voltageUSB"  :  voltageUSB.value,
			"currentUSB"  :  currentUSB.value
		}

		if ret["currentUSB"] < 4.4:
			raise EnvironmentError("USB Supply voltage below specified minimum of 4.4V. Please check hardware. Read supply voltage = %f" % ret["currentUSB"])

		if ret["temperature"] > 70 or ret["temperature"] < 0:
			raise EnvironmentError("Hardware temperature outside of normal operating bounds.")

		# self.log.info("Diagnostics queried. Values = \n%s", "\n".join(["	{key}, {value}".format(key=key, value=value) for key, value in ret.iteritems()]))
		return ret

	def queryStreamInfo(self):
		'''
		Args:
			No Args
		Returns:
			dictionary containing status information on the IQ data stream:

				| {
				|	"return_len":       <The number of IQ samples pairs which will be returned by calling ``bbFetchRaw()``.>,
				|	"samples_per_sec":  <The number of IQ pairs to expect per second.>,
				|	"bandwidth":        <The bandpass filter bandwidth, width in Hz. Width is specified by the 3dB rolloff points.>,
				| }


		Use this function to characterize the IQ data stream.

		Will raise ``IOError`` If the device is not open, not streaming, or if an unknown error is encountered..

		Raw call ``BB_API bbStatus bbQueryStreamInfo(int device, int *return_len, double *bandwidth, int *samples_per_sec);``

		'''

		return_len         = ct.c_int(0)
		bandwidth          = ct.c_double(0)
		samples_per_sec    = ct.c_int(0)

		return_lenPnt      = ct.pointer(return_len)
		bandwidthPnt       = ct.pointer(bandwidth)
		samples_per_secPnt = ct.pointer(samples_per_sec)

		err = self.dll.bbQueryStreamInfo(self.deviceHandle, return_lenPnt, bandwidthPnt, samples_per_secPnt)

		if err == self.bbStatus["bbNoError"]:
			pass
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("The device specified is not currently streaming!")
		else:
			raise IOError("Unknown error!")

		# The raw data array returned by fetchRaw when in streaming mode is the value of return_len * 2 (since each value is two floats)
		self._rawDataArrSize = return_len.value * 2

		values = {
			"return_len"      : return_len.value,
			"samples_per_sec" : bandwidth.value,
			"bandwidth"       : samples_per_sec.value
		}

		return values

	def configureAcquisition(self, detector, scale):
		'''

		Args:
			detectorType (string): Specifies the video detector. The two possible values for detector type
					are:
					 - "average" (mapped to ``BB_AVERAGE``)
					 - "min-max" (mapped to ``BB_MIN_AND_MAX``).
			verticalScale (string):  Specifies the scale in which sweep results are returned int. The four
					possible values for verticalScale are:
					 - "log-scale" (mapped to ``BB_LOG_SCALE``)
					 - "lin-scale" (mapped to ``BB_LIN_SCALE``),
					 - "log-full-scale" (mapped to ``BB_LOG_FULL_SCALE``)
					 - "lin-full-scale" (mapped to ``BB_LIN_FULL_SCALE``)
		Returns:
			Nothing

		The verticalScale parameter will change the units of returned sweeps. If ``BB_LOG_SCALE`` is provided
		sweeps will be returned in amplitude unit dBm. If ``BB_LIN_SCALE`` is specified, the returned units will be in
		millivolts. If the full scale units are specified, no corrections are applied to the data and amplitudes are
		taken directly from the full scale input.

		detectorType specifies how to produce the results of the signal processing for the final sweep.
		Depending on settings, potentially many overlapping FFTs will be performed on the input time domain
		data to retrieve a more consistent and accurate final result. When the results overlap detectorType
		chooses whether to average the results together, or maintain the minimum and maximum values. If
		averaging is chosen the min and max trace arrays returned from bbFetchTrace will contain the same
		averaged data

		Will raise ``ValueError`` if invalid strings are passed (e.g. they're not one of the specified values above).

		Will raise ``IOError`` for the following error-codes:
		 - ``bbDeviceNotOpenErr`` - "Device not open!"
		 - ``bbInvalidDetectorErr`` - "Invalid Detector mode!"
		 - ``bbInvalidScaleErr`` - "Invalid scale setting error!"
		 - Any unknown errors

		Raw call: ``BB_API bbStatus bbConfigureAcquisition(int device, unsigned int detector, unsigned int scale);``
		'''

		self.acq_conf["detector"] = detector
		self.acq_conf["scale"] = scale

		detectorVals = {
			"min-max" : ct.c_uint(hf.BB_MIN_AND_MAX),
			"average" : ct.c_uint(hf.BB_AVERAGE)
		}

		scaleVals = {
			"log-scale"      : ct.c_uint(hf.BB_LOG_SCALE),
			"lin-scale"      : ct.c_uint(hf.BB_LIN_SCALE),
			"log-full-scale" : ct.c_uint(hf.BB_LOG_FULL_SCALE),
			"lin-full-scale" : ct.c_uint(hf.BB_LIN_FULL_SCALE)
		}

		self.log.info("Setting device acquisition configuration.")
		if detector in detectorVals:
			detector = detectorVals[detector]
		else:
			raise ValueError("Invalid Detector mode! Detector  must be one of %s. Specified detector = %s" % (detectorVals.keys(), detector))

		if scale in scaleVals:
			scale = scaleVals[scale]
		else:
			raise ValueError("Invalid Scaling mode! Scaling mode must be one of %s. Specified scale = %s" % (scaleVals.keys(), scale))

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
		'''

		Args:
			center (float): 	Center frequency in hertz.
			span (float):  	Span in hertz

		This function configures the operating frequency band of the broadband device. Start and stop
		frequencies can be determined from the center and span.

		-  start = center - (span/2)
		-  stop = center+(span/2)

		The values provided are used by the device during initialization and a more precise start frequency is
		returned after initiation. Refer to the bbQueryTraceInfo function for more information.

		Each device has a specified operational frequency range. These limits are ``BB#_MIN_FREQ`` and
		``BB#_MAX_FREQ``, where ``#`` is the signal-hound model number (see ``bb_api_h.py``). The center and
		span provided cannot specify a sweep outside of this range. There is also an absolute minimum operating span.

		Certain modes of operation have specific frequency range limits. Those mode dependent limits are
		tested against during initialization and not here.

		Raises ``IOError`` on errors.

		Raw call: ``BB_API bbStatus bbConfigureCenterSpan(int device, double center, double span);``
		'''

		self.acq_conf["center_freq"] = center
		self.acq_conf["span_freq"] = span



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
			raise IOError("Unknown error setting configureCenterSpan! Error = %s" % err)


	def configureLevel(self, ref, atten):
		'''

		Args:
			ref (float): Reference level in dBm.
			atten (float): Attenuation setting in dB. If attenuation provided is negative, attenuation is selected automatically.
				``atten`` must be a integer multiple of 10 (or ``-1``). The hardware supports attenuation levels of 0 dB, 10 dB, 20 dB, and 30 dB ONLY.

		When automatic gain is selected, the API uses the reference level provided to choose the best gain
		settings for an input signal with amplitude equal to reference level. If a gain other than BB_AUTO_GAIN
		is specified using bbConfigureGain, the reference level parameter is ignored.

		The atten parameter controls the RF input attenuator, and is adjustable from 0 to 30 dB in 10 dB steps.
		The RF attenuator is the first gain control device in the front end.

		When attenuation is automatic, the attenuation and gain for each band is selected independently. When
		attenuation is not automatic, a flat attenuation is set across the entire spectrum. A set attenuation may
		produce a non-flat noise floor.

		Raises ``ValueError`` for invalid attenuation values, ``IOError`` for other errors.

		Raw call: ``BB_API bbStatus bbConfigureLevel(int device, double ref, double atten);``

		'''


		self.acq_conf["ref_level"] = ref
		self.acq_conf["in_atten"] = atten


		if atten == "auto":
			atten = -1

		if atten % 10 != 0 and atten != -1:
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
		'''
		Args:
			gain (float): A gain setting

		To return the device to automatically choose the best gain setting, call this function with a gain of
		``BB_AUTO_GAIN``.

		The gain choices for each device range from 0 to ``BB#_MAX_GAIN``, where ``#`` is the signal-hound model number (see ``bb_api_h.py``).

		When ``BB_AUTO_GAIN`` is selected, the API uses the reference level provided in bbConfigureLevel to
		choose the best gain setting for an input signal with amplitude equal to the reference level provided.

		After the RF input attenuator (0-30 dB), the RF path contains an additional amplifier stage after band
		filtering, which is selected for medium or high gain and bypassed for low or no gain.

		Additionally, the IF has an amplifier which is bypassed only for a gain of zero.

		For the highest gain settings, additional amplification in the ADC stage is used.


		Raw call: ``BB_API bbStatus bbConfigureGain(int device, int gain);``
		'''


		self.acq_conf["rf_gain"] = gain

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
			raise IOError("Unknown error setting configureGain! Error = %s" % err)

		return


	def configureSweepCoupling(self, rbw, vbw, sweepTime, rbwType, rejection):
		'''

		Args
			rbw (float): Resolution bandwidth in Hz. Use the bandwidth table in the appendix to
					determine good values to choose. As of 1.07 in non-native mode, RBW
					can be arbitrary. Therefore you may choose values not in the table and
					they will not clamp.
			vbw (float): Video bandwidth (VBW) in Hz. VBW must be less than or equal to RBW.
					VBW can be arbitrary. For best performance use RBW as the VBW.
			sweepTime (float): Sweep time in seconds.
					In sweep mode, this value is how long the device collects data before it
					begins processing. Maximum values to be provided should be around
					100ms.
					In the real-time configuration, this value represents the length of time
					data is collected and compounded before returning a sweep. Values for
					real-time should be between 16ms-100ms for optimal viewing and use.
					In zero span mode this is the length of the returned sweep as a measure
					of time. Sweep times for zero span must range between 10us and
					100ms. Values outside this range are clamped.
			rbwType (float): The possible values for rbwType are BB_NATIVE_RBW and
					BB_NON_NATIVE_RBW. This choice determines which bandwidth table
					is used and how the data is processed. BB_NATIVE_RBW is default and
					unchangeable for real-time operation.
			rejection (float): The possible values for rejection are BB_NO_SPUR_REJECT,
					BB_SPUR_REJECT, and BB_BYPASS_RF.

		The resolution bandwidth, or RBW, represents the bandwidth of spectral energy represented in each
		frequency bin. For example, with an RBW of 10 kHz, the amplitude value for each bin would represent
		the total energy from 5 kHz below to 5 kHz above the bin's center. For standard bandwidths, the API
		uses the 3 dB points to define the RBW.

		The video bandwidth, or VBW, is applied after the signal has been converted to frequency domain as
		power, voltage, or log units. It is implemented as a simple rectangular window, averaging the amplitude
		readings for each frequency bin over several overlapping FFTs. A signal whose amplitude is modulated at
		a much higher frequency than the VBW will be shown as an average, whereas amplitude modulation at
		a lower frequency will be shown as a minimum and maximum value.

		Native RBWs represent the bandwidths from a single power-of-2 FFT using our sample rate of 80 MSPS
		and a high dynamic range window function. Each RBW is half of the previous. Using native RBWs can
		give you the lowest possible bandwidth for any given sweep time, and minimizes processing power.
		However, scalloping losses of up to 0.8 dB, occurring when a signal falls in between two bins, can cause
		problems for some types of measurements.

		Non-native RBWs use the traditional 1-3-10 sequence. As of version 1.0.7, non-native bandwidths are
		not restricted to the 1-3-10 sequence but can be arbitrary. Programmatically, non-native RBW's are
		achieved by creating variable sized bandwidth flattop windows.

		sweepTime applies to regular sweep mode and real-time mode. If in sweep mode, sweepTime is the
		amount of time the device will spend collecting data before processing. Increasing this value is useful for
		capturing signals of interest or viewing a more consistent view of the spectrum. Increasing sweepTime
		has a very large impact on the amount of resources used by the API due to the increase of data needing
		to be stored and the amount of signal processing performed. For this reason, increasing sweepTime also
		decreases the rate at which you can acquire sweeps.

		In real-time, sweepTime refers to how long data is accumulated before returning a sweep. Ensure you
		are capable of retrieving as many sweeps that will be produced by changing this value. For instance,
		changing sweepTime to 32ms in real-time mode will return approximately 31 sweeps per second
		(1000/32).

		Rejection can be used to optimize certain aspects of the signal. Default is BB_NO_SPUR_REJECT, and
		should be used in most cases. If you have a steady CW or slowly changing signal, and need to minimize
		image and spurious responses from the device, use BB_SPUR_REJECT. If you have a signal between 300
		MHz and 3 GHz, need the lowest possible phase noise, and do not need any image rejection,
		BB_BYPASS_RF can be used to rewire the front end for lowest phase noise.

		::

			Native Bandwidths (Hz)      FFT size
			        10.10e6              16
			         5.050e6             32
			         2.525e6             64
			         1.262e6            128
			       631.2e3              256  Largest Real-Time RBW
			       315.6e3              512
			       157.1e3             1024
			        78.90e3            2048
			        39.45e3            4096
			        19.72e3            8192
			         9.863e3          16384
			         4.931e3          32768
			         2.465e3          65536  Smallest Real-Time RBW
			         1.232e3         131072
			       616.45            262144
			       308.22            524288
			       154.11           1048576
			       154.11           1048576
			        77.05           2097152
			        38.52           4194304
			        19.26           8388608
			         9.63          16777549
			         4.81          33554432
			         2.40          67108864
			         1.204        134217728
			         0.602        268435456
			         0.301        536870912

		Raw Call: ``BB_API bbStatus bbConfigureSweepCoupling(int device, double rbw, double vbw, double sweepTime, unsigned int rbwType, unsigned int rejection);``
		'''


		self.log.info("Setting device sweep coupling settings.")


		self.acq_conf["rbw"]       = rbw
		self.acq_conf["vbw"]       = vbw
		self.acq_conf["sweepTime"] = sweepTime
		self.acq_conf["rbwType"]   = rbwType
		self.acq_conf["rejection"] = rejection

		rbw        = ct.c_double(rbw)
		vbw        = ct.c_double(vbw)
		sweepTime  = ct.c_double(sweepTime)


		rbwVals = {
			"native"     : ct.c_uint(hf.BB_NATIVE_RBW),
			"non-native" : ct.c_uint(hf.BB_NON_NATIVE_RBW)
		}

		rejectionVals = {
			"no-spur-reject" : ct.c_uint(hf.BB_NO_SPUR_REJECT),
			"spur-reject"    : ct.c_uint(hf.BB_SPUR_REJECT),
			"bypass"         : ct.c_uint(hf.BB_BYPASS_RF)
		}

		if rbwType in rbwVals:
			rbwType  = rbwVals[rbwType]
		else:
			raise ValueError("rbwType must be either \"native\" or \"non-native\". Passed value was %s." % rbwType)

		if rejection in rejectionVals:
			rejection    = rejectionVals[rejection]
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
			raise IOError("Unknown error setting configureSweepCoupling! Error = %s" % err)



	def configureIQ(self, downsample, bandwidth):
		'''

		Args:
			downsampleFactor:  Specify a decimation rate for the 40MS/s IQ digital stream.
			bandwidth:         Specify a bandpass filter width on the IQ digital stream.

		Downsample factor settings:
		::

			Decimation-Rate  Sample Rate (IQ pairs/s)  Maximum Bandwidth
			1                40 MS/s                   27 MHz
			2                20 MS/s                   17.8 MHz
			4                10 MS/s                   8.0 MHz
			8                5 MS/s                    3.75 MHz
			16               2.5 MS/s                  2.0 MHz
			32               1.25 MS/s                 1.0 MHz
			64               0.625 MS/s                0.5 MHz
			128              0.3125 MS/s               0.125 MHz

		This function is used to configure the digital IQ data stream. A decimation factor and filter bandwidth
		are able to be specified. The decimation rate divides the IQ sample rate directly while the bandwidth
		parameter further filters the digital stream.

		For each given decimation rate, a maximum bandwidth value must be supplied to account for sufficient
		filter rolloff. That table is above. See  bbFetchRaw() for polling the IQ data stream

		Raw Call: ``BB_API bbStatus bbConfigureIQ(int device, int downsampleFactor, double bandwidth);``

		'''

		validDecimationFactors = [1<<i for i in range(8)]
		# Resolves to [1, 2, 4, 8, 16, 32, 64, 128]
		if downsample not in validDecimationFactors:
			raise ValueError("Decimation ratio must be one of values: %s. Specified value: %s" % (validDecimationFactors, downsample))


		bandwidth  = ct.c_double(bandwidth)
		downsample = ct.c_int(downsample)

		err = self.dll.bbConfigureIQ(self.deviceHandle, downsample, bandwidth)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("configureSweepCoupling Succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			raise IOError("The downsample rate is outside the acceptable input range or the downsample rate is not a power of two.")
		elif err == self.bbStatus["bbClampedToLowerLimit"]:
			raise IOError("The bandpass filter width specified is lower than  BB_MIN_IQ_BW")
		elif err == self.bbStatus["bbClampedToUpperLimit"]:
			raise IOError("Warning that the bandpass filter width was clamped to the maximum value allowed by the downsampleFaction.")
		else:
			raise IOError("Unknown error setting bbConfigureIQ! Error = %s" % err)





	def configureWindow(self, window):
		'''
		Args:
			window:  The possible values for window are BB_NUTALL, BB_BLACKMAN,
					BB_HAMMING, and BB_FLAT_TOP.

		This changes the windowing function applied to the data before signal processing is performed. In real-
		time configuration the window parameter is permanently set to BB_NUTALL. The windows are only
		changeable when using the BB_NATIVE_RBW type in bbConfigureSweepCoupling. When using
		BB_NON_NATIVE_RBWs, a custom flattop window will be used.

		Raw Call: ``BB_API bbStatus bbConfigureWindow(int device, unsigned int window);``
		'''


		self.log.info("Setting device FFT windowing function.")

		self.acq_conf["fft_window"] = window

		windows = {
			"nutall"   : hf.BB_NUTALL,
			"blackman" : hf.BB_BLACKMAN,
			"hamming"  : hf.BB_HAMMING,
			"flat-top" : hf.BB_FLAT_TOP
		}


		if window in windows:
			window = windows[window]
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
			raise IOError("Unknown error setting configureWindow! Error = %s" % err)



	def configureProcUnits(self, units):
		'''

		Args:
			units:  The possible values are BB_LOG, BB_VOLTAGE, BB_POWER, and
					BB_BYPASS.

		The units provided determines what unit type video processing occurs in. The chart below shows which
		unit types are used for each units selection.
		For “average power” measurements, BB_POWER should be selected. For cleaning up an amplitude
		modulated signal, BB_VOLTAGE would be a good choice. To emulate a traditional spectrum analyzer,
		select BB_LOG. To minimize processing power, select BB_BYPASS.

		::

			BB_LOG      = dBm
			BB_VOLTAGE  = mV
			BB_POWER    = mW
			BB_BYPASS   = No video processing

		Raw Call: ``BB_API bbStatus bbConfigureProcUnits(int device, unsigned int units);``
		'''

		self.acq_conf["data_units"] = units

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
			raise IOError("Unknown error setting configureProcUnits! Error = %s" % err)



	def configureTrigger(self, trigType, edge, level, timeout):
		'''
		Args:
			type:  Specifies the type of trigger to use. Possible values are
				BB_NO_TRIGGER, BB_VIDEO_TRIGGER, BB_EXTERNAL_TRIGGER, and
				BB_GPS_PPS_TRIGGER. If an external signal is desired, BNC port 2 must
				be configured to accept a trigger (see bbConfigureIO). When
				BB_NO_TRIGGER is specified, the other parameters are ignored and this
				function sets only trigger type.
			edge:  Specifies the edge type of a video trigger. Possible values are
				BB_TRIGGER_RISING and BB_TRIGGER_FALLING. If you are using a
				trigger type other than a video trigger, this value is ignored but must be
				specified.
			level:  Level of the video trigger. The units of this value are determined by the
				demodulation type used when initiating the device. If demodulating
				AM, level is in dBm units, if demodulating FM, level is in Hz.
			timeout:  timeout specifies the length of a capture window in seconds. The
				capture window specifies the length of continuous time you wish to
				wait for a trigger. If no trigger is found within the window, the last
				sweepTime of data within the data is returned. The capture window
				must be greater than sweepTime. If it is not, it will be automatically
				adjusted to sweepTime. The timeout/capture window is applicable to
				both video and external triggering.

		Allows you to configure all zero-span trigger related variables. As with all configure routines, the
		changes made here are not reflected until the next initiate.

		When a trigger is specified the sweep returned will start approximately 200 microseconds before the
		trigger event. This provide a slight view of occurances directly before the event. If no trigger event is
		found, the data returned at the end of the timeout period is returned.

		Raw Call: ``BB_API bbStatus bbConfigureTrigger(int device, unsigned int type, unsigned int edge, double level, double timeout);``
		'''

		self.log.info("Setting device trigger configuration.")
		self.acq_conf["trigType"]     = trigType
		self.acq_conf["trig_edge"]    = edge
		self.acq_conf["trig_level"]   = level
		self.acq_conf["trig_timeout"] = timeout

		videoTrigDict = {
			"rising-edge"  : hf.BB_TRIGGER_RISING,
			"falling-edge" : hf.BB_TRIGGER_FALLING
		}

		if trigType == "none":
			trigType =  hf.BB_NO_TRIGGER
		elif trigType == "video":
			trigType = hf.BB_VIDEO_TRIGGER
		elif trigType == "external":
			trigType = hf.BB_EXTERNAL_TRIGGER
			self.log.warning("configureIO must be called to set up BNC port 2 as an input for proper external trigger operation")
		elif trigType == "gps-pps":
			raise ValueError("GPS PPS Trigger not supported in API files. Please contact Test-Equipment-Plus for more information.")
			# self.log.warning("GPS synchronization is not tested, and the setup constants are partially just guessed. ")
			# trigType = hf.BB_GPS_PPS_TRIGGER
		else:
			raise ValueError("Trigger type must be either \"none\", \"video\", \"external\" or \"gps-pps\". Passed value was %s." % trigType)

		if trigType == hf.BB_VIDEO_TRIGGER:
			if edge in videoTrigDict:
				edge = videoTrigDict[trigType]
			else:
				raise ValueError("Trigger type for vide-triggering must be either \"rising-edge\", \"falling-edge\". Passed value was %s." % edge)
		else:
			# Trigger type is ignored in all modes except BB_VIDEO_TRIGGER
			edge =  hf.BB_TRIGGER_FALLING


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
			raise IOError("Unknown error setting configureTrigger! Error = %s" % err)


	def configureTimeGate(self, delay, length, timeout):
		'''

		Args:
			delay:  The time in seconds, from the trigger to the beginning of the gate
			length:  The length in seconds, of the gate
			timeout:  The time in seconds to wait for a trigger. If no trigger is found, the last
					length will be used.

		Time gates are relative to an external trigger.

		Therefore it is necessary to use bbConfigureIO to setup an external trigger.

		Raw Call: ``BB_API bbStatus bbConfigureTimeGate(int device, double delay, double length, double timeout);``
		'''

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
			raise IOError("Unknown error setting configureTimeGate! Error = %s" % err)

	def configureRawSweep(self, start, ppf, steps):
		'''
		Raw Call: ``BB_API bbStatus bbConfigureRawSweep(int device, int start, int ppf, int steps, int stepsize);``

		Args:
			start:  Frequency value in MHz representing the center of the first 20MHz step
				in the sweep. Must be a multiple of 20, and no less than 20.
			ppf:  Controls the amount of digital samples to collect at each frequency
				step. The number of digital samples collected at each frequency equals
				18688 * ppf.
			steps:  Number of steps to take starting with and including the first steps.
			stepsize:  Value must be BB_TWENTY_MHZ

		This function configures the device for both BB_RAW_SWEEP and BB_RAW_SWEEP_LOOP modes. This
		function allows you to configure the sweep start frequency, the number of 20 MHz steps to take across
		the spectrum, and how long to dwell at each frequency. There are restrictions on these settings,
		outlined below.
		'''

		self.log.info("Setting device raw sweep mode configuration.")

		if start % 20 != 0 or start < 20:
			raise ValueError("The 'start' parameter must be a multiple of 20MHz")
		if (ppf * steps) % 16 != 0:
			raise ValueError("(ppf * steps) must be a multiple of 16")

		if start + (steps * 20) > 6000:
			raise ValueError("The final center frequency, obtained by the equation (start + steps*20), cannot be greater than 6000 (6 GHz).")


		self.acq_conf["ppf"] = ppf
		self.acq_conf["steps"] = steps

		start = ct.c_int(start)
		ppf = ct.c_int(ppf)
		steps = ct.c_int(steps)
		stepSize = ct.c_int(hf.BB_TWENTY_MHZ)

		err = self.dll.bbConfigureRawSweep(self.deviceHandle, start, ppf, steps, stepSize)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to configureRawSweep succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			raise IOError("A parameter specified is not valid.")
		else:
			raise IOError("Unknown error setting configureRawSweep! Error = %s" % err)

	def configureIO(self, port1Coupling, port1mode, port2mode):
		'''

		Args:
			port1:  The first BNC port may be used to input or output a 10 MHz time base
				(AC or DC coupled), or to generate a general purpose logic high/low
				output. Please refer to the example below. All possible values for this
				port are found in the header file and are prefixed with “BB_PORT1”
			port2:  Port 2 is capable of accepting an external trigger or generating a logic
				output. Port 2 is always DC coupled. All possible values for this port are
				found in the header file and are prefixed with “BB_PORT2.”

		NOTE: This function can only be called when the device is idle (not operating in any mode). To ensure
		the device is idle, call bbAbort().

		There are two configurable BNC connector ports available on the device. Both ports functionality are
		changed with this function. For both ports, ‘0’ is the default and can be supplied through this function to
		return the ports to their default values. Specifying a ‘0’ on port 1 returns the device to an internal time
		base and outputs the time base AC coupled. Specifying ‘0’ on port 2 emits a DC coupled logic low.

		For external 10 MHz timebases, best phase noise is achieved by using a low jitter 3.3V CMOS input.

		Configure combinations

		Port 1 IO  For port 1 only a coupled value must be ‘OR’ed
		together with a port type. Use the ‘|’ operator to
		combine a coupled type and a port type.

		 - ``BB_PORT1_AC_COUPLED``               Denotes an AC coupled port
		 - ``BB_PORT1_DC_COUPLED``               Denotes a DC coupled port
		 - ``BB_PORT1_INT_REF_OUT``              Output the internal 10 MHz timebase
		 - ``BB_PORT1_EXT_REF_IN``               Accept an external 10MHz time base
		 - ``BB_PORT1_OUT_LOGIC_LOW``            Self-explanitory
		 - ``BB_PORT1_OUT_LOGIC_HIGH``           Self-explanitory

		Port 2 IO
		 - ``BB_PORT2_OUT_LOGIC_LOW``            Self-explanitory
		 - ``BB_PORT2_OUT_LOGIC_HIGH``           Self-explanitory
		 - ``BB_PORT2_IN_TRIGGER_RISING_EDGE``   When set, the device is notified of a rising edge
		 - ``BB_PORT_IN_TRIGGER_FALLING_EDGE``   When set, the device is notified of a falling edge

		Raw Call: ``BB_API bbStatus bbConfigureIO(int device, unsigned int port1, unsigned int port2);``
		'''

		self.log.info("Setting device IO Configuration.")

		port1 = 0
		port2 = 0

		p1CouplingOpts = {
			"ac": hf.BB_PORT1_AC_COUPLED,
			"dc": hf.BB_PORT1_DC_COUPLED
		}

		p1ModeOpts = {
			"int-ref-out"    : hf.BB_PORT1_INT_REF_OUT,
			"ext-ref-in"     : hf.BB_PORT1_EXT_REF_IN,
			"out-logic-low"  : hf.BB_PORT1_OUT_LOGIC_LOW,
			"out-logic-high" : hf.BB_PORT1_OUT_LOGIC_HIGH
		}

		p2ModeOpts = {
			"int-ref-out"    : hf.BB_PORT2_IN_TRIGGER_RISING_EDGE,
			"ext-ref-in"     : hf.BB_PORT2_IN_TRIGGER_FALLING_EDGE,
			"out-logic-low"  : hf.BB_PORT2_OUT_LOGIC_LOW,
			"out-logic-high" : hf.BB_PORT2_OUT_LOGIC_HIGH
		}

		if port1Coupling in p1CouplingOpts:
			port1 |= p1CouplingOpts[port1Coupling]
		else:
			raise ValueError("Port1Coupling must be either'ac' or 'dc'. Passed value was %s." % port1Coupling)

		if port1mode in p1ModeOpts:
			port1 |= p1ModeOpts[port1mode]
		else:
			raise ValueError("port1mode must be one of %s. Passed value was %s." % (p1ModeOpts.keys(), port1mode))



		if port2mode in p2ModeOpts:
			port2 |= p2ModeOpts[port2mode]
		else:
			raise ValueError("port2mode must be either \"int-ref-out\", \"ext-ref-in\", \"out-logic-low\" or \"out-logic-high\". Passed value was %s." % port1mode)


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
			raise IOError("Unknown error setting configureIO! Error = %s" % err)


	def configureDemod(self, modulationType, freq, ifBw, audioLowPassFreq, audioHighPassFreq, fmDeemphasis):
		'''
		Args:
			modulationType:  Specifies the demodulation scheme, possible values are
					BB_DEMOD_AM/FM/Upper sideband (USB)/Lower Sideband (LSB)/CW.
			freq:  Center frequency. For best results, re-initiate the device if the center frequency changes +/- 8MHz from the initial value.
			IFBW:  Intermediate frequency bandwidth centered on freq. Filter takes place
					before demodulation. Specified in Hz. Should be between 2kHz and 500kHz.
			audioLowPassFreq:  Post demodulation filter in Hz. Should be between 1kHz and 12kHz Hz.
			audioHighPassFreq:  Post demodulation filter in Hz. Should be between 20 and 1000Hz.
			FMDeemphasis:  Specified in micro-seconds. Should be between 1 and 100.

		This function can be called while the device is active.
		Note : If any of the boundary conditions are not met, this function will return with no error but the
		values will be clamped to its boundary values

		Raw Call: ``BB_API bbStatus bbConfigureDemod(int device, int modulationType, double freq, float IFBW, float audioLowPassFreq, float audioHighPassFreq, float FMDeemphasis);``
		'''

		self.log.info("Setting device demodulator Configuration.")

		modTypeOpts = {
			"am"  : hf.BB_DEMOD_AM,
			"fm"  : hf.BB_DEMOD_FM,
			"usb" : hf.BB_DEMOD_USB,
			"lsb" : hf.BB_DEMOD_LSB,
			"cw"  : hf.BB_DEMOD_CW
		}


		if modulationType in modTypeOpts:
			modulationType = modTypeOpts[modulationType]
		else:
			raise ValueError("Modulation Type must be one of %s. Passed value was %s." % (modTypeOpts.keys(), modulationType))

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
			raise IOError("Unknown error setting configureDemod! Error = %s" % err)

	def initiate(self, mode, flag, gps_timestamp=False):
		'''
		Args:
			mode:  The possible values for mode are BB_SWEEPING, BB_REAL_TIME,
				BB_ZERO_SPAN, BB_TIME_GATE, BB_RAW_SWEEP,
				BB_RAW_SWEEP_LOOP and BB_AUDIO_DEMOD.
			flag:  The default value is zero.
				If mode equals BB_ZERO_SPAN, flag can be used to denote the type of
				modulation performed on the incoming signal. BB_DEMOD_AM and
				BB_DEMOD_FM are the two options.
				Flag can be used to inform the API to time
				stamp data using an external GPS reciever. Mask the bandwidth flag (‘|’
				in C) with BB_TIME_STAMP to achieve this. See Appendix:Using a GPS
				Receiver to Time-Stamp Data for information on how to set this up.
			gps_timestamp (bool): Timestamp using GPS

		bbInitiate configures the device into a state determined by the mode parameter. For more information
		regarding operating states, refer to the Theory of Operation and Modes of Operation sections. This
		function calls bbAbort before attempting to reconfigure. It should be noted, if an error is returned, any
		past operating state will no longer be active.

		Pay special attention to the bbInvalidParameterErr description below

		Raw Call: ``BB_API bbStatus bbInitiate(int device, unsigned int mode, unsigned int flag);``
		'''

		self.acq_conf["acq_mode"] = mode
		self.acq_conf["acq_flag"] = flag

		modeOpts = {
			"sweeping"       : hf.BB_SWEEPING,
			"streaming"      : hf.BB_STREAMING,
			"real-time"      : hf.BB_REAL_TIME,
			"zero-span"      : hf.BB_ZERO_SPAN,
			"time-gate"      : hf.BB_TIME_GATE,
			"raw-sweep"      : hf.BB_RAW_SWEEP,
			"raw-sweep-loop" : hf.BB_RAW_SWEEP_LOOP,
			"audio-demod"    : hf.BB_AUDIO_DEMOD
		}

		zeroSpanOpts = {
			"demod-am" : hf.BB_DEMOD_AM,
			"demod-fm" : hf.BB_DEMOD_FM
		}


		if mode in modeOpts:
			mode = modeOpts[mode]
		else:
			raise ValueError("Mode must be one of %s. Passed value was %s." % (modeOpts, mode))


		if mode == hf.BB_ZERO_SPAN or mode == hf.BB_TIME_GATE:
			raise NotImplementedError("Zero span and time-gate modes are not functional yet in the BB 2.0 API Version. Please contact signalhound for more information.")

		if mode == hf.BB_ZERO_SPAN:
			if flag in zeroSpanOpts:
				flag = zeroSpanOpts[flag]
			else:
				raise ValueError("Available flag settings for mode \"zero-span\" are \"demod-am\" and \"demod-fm\". Passed value was %s." % flag)

		# Checking for raw-pipe mode is messy, since it uses the same configuration value as the streaming mode.
		elif self.acq_conf["acq_mode"] == "raw-pipe":
			raise ValueError("Raw pipe mode is depreciated, and has been removed.")

		else:
			flag = 0


		if mode == hf.BB_REAL_TIME:
			if not "span_freq" in self.acq_conf:
				raise ValueError("You must call configureCenterSpan() before initiate()!")
			elif (self.acq_conf["span_freq"] > hf.BB60C_MAX_RT_SPAN or
				self.acq_conf["span_freq"] < hf.BB_MIN_RT_SPAN ):

				if not self._devType:
					raise ValueError("Device type not detected? How did this even occur!")
				elif self._devType == "BB60C":
					if self.acq_conf["span_freq"] > hf.BB60C_MAX_RT_SPAN:
						raise ValueError("Real-time mode maximum span frequency is 27 Mhz for the BB60C. Specified span frequency = %f" % self.acq_conf["span_freq"])

				elif self._devType == "BB60A":
					if self.acq_conf["span_freq"] > hf.BB60A_MAX_RT_SPAN:
						raise ValueError("Real-time mode maximum span frequency is 20 Mhz for the BB60A. Specified span frequency = %f" % self.acq_conf["span_freq"])

			if not "rbw" in self.acq_conf:
				raise ValueError("You must call configureSweepCoupling() before initiate()!")

			elif (self.acq_conf["rbw"] > hf.BB_MAX_RT_RBW or
				self.acq_conf["rbw"] < hf.BB_MIN_RT_RBW):
				raise ValueError("Invalid RBW for Real-time mode. Minimum RBW is %f, maximum RBW is %f. Specified RBW = %f" % (hf.BB_MIN_RT_RBW, hf.BB_MAX_RT_RBW, self.acq_conf["rbw"]))


		if gps_timestamp:
			self.log.info("Timestamping returned data with GPS time")
			flag |= hf.BB_TIME_STAMP

		mode = ct.c_uint(mode)
		flag = ct.c_uint(flag)

		err = self.dll.bbInitiate(self.deviceHandle, mode, flag)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to initiate succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbInvalidParameterErr"]:
			self.log.error("bbInvalidParameterErr!")
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
			raise IOError("Unknown error setting initiate! Error = %s" % err)

	def fetchTrace(self):
		'''
		Args:
			None

		Returns:
			dictionary containing the ``min`` and ``max`` arrays with eponymous keys.

		Returns a minimum and maximum array of values relating to the current mode of operation. If the
		detectorType provided in bbConfigureAcquisition is BB_AVERAGE, the arrays will contain identical
		values. Element zero of each array corresponds to the startFreq returned from bbQueryTraceInfo.

		Raw Call: ``BB_API bbStatus bbFetchTrace(int device, int arraySize, double *min, double *max);``
		'''

		try:
			arraySize = self.traceLen
		except AttributeError:
			self.log.error("You must call queryTraceInfo atleast once before fetchTrace")
			raise

		maxArr = (ct.c_double * arraySize)()
		minArr = (ct.c_double * arraySize)()

		maxPtr = ct.pointer(maxArr)
		minPtr = ct.pointer(minArr)

		err = self.dll.bbFetchTrace(self.deviceHandle, arraySize, minPtr, maxPtr)

		if err == self.bbStatus["bbNoError"]:
			# self.log.info("Call to fetchTrace succeeded.")  # Commented out because it was NOISY

			self.sequentialADCErrors = 0  # There was no clipping, so reset the clipping integrator
			pass
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		elif err == self.bbStatus["bbBufferTooSmallErr"]:
			raise IOError("The 'arraySize' parameter passed is less than the trace size returned from 'bbQueryTraceInfo'.")
		elif err == self.bbStatus["bbADCOverflow"]:
			self.log.warning("Clipping is common on the first acquitition cycle, presumably due to the IF stages settling.")
			self.log.warning("This error is only a problem if it occurs more then once and not at the immediate start of an acquisition, or immediately following a recalibration.")
			self.sequentialADCErrors += 1

			# Only throw an actual error if we've been clipping for a while.
			# This way, transients won't break things (as fast, in any event).
			if self.sequentialADCErrors > 10:
				raise IOError("The ADC has detected clipping of the input signal for more then 10 sequential samples!")

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
			raise IOError("Unknown error setting fetchTrace! Error = %s" % err)


		maxData = SignalHound.fastDecodeArray(maxArr, arraySize, np.double)
		minData = SignalHound.fastDecodeArray(minArr, arraySize, np.double)

		ret = {
			"max" : maxData,
			"min" : minData
		}



		return ret

	def fetchAudio(self):
		'''
		Returns:
			Numpy array of 4096 32-bit floating point values

		If the device is initiated and running in the audio demodulation mode, the function is a blocking call
		which returns the next 4096 audio samples. The approximate blocking time for this function is 128 ms if
		called again immediately after returning. There is no internal buffering of audio, meaning the audio will
		be overwritten if this function is not called in a timely fashion. The audio values are typically -1.0 to 1.0,
		representing full-scale audio. In FM mode, the audio values will scale with a change in IF bandwidth.

		Raw Call: ``BB_API bbStatus bbFetchAudio(int device, float *audio);``
		'''

		arraySize = 4096
		audioArr = (ct.c_float * arraySize)()
		audioArrPtr = ct.pointer(audioArr)

		err = self.dll.bbFetchAudio(self.deviceHandle, audioArrPtr)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to fetchAudio succeeded.")
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		elif err == self.bbStatus["bbDeviceConnectionErr"]:
			raise IOError("Device connection issues were present in the acquisition of this sweep!")
		else:
			raise IOError("Unknown error setting fetchAudio! Error = %s" % err)

		arr = np.ctypeslib.as_array(audioArr)  # Map numpy array onto the same memory location as audioArr

		#Note: Copy is *probably* not needed, as the memory location is owned by the python code, rather then the SignalHound API.
		return arr.copy()  # Copy, and return location.

	def fetchRawCorrections(self):
		'''

		Returns:
			| ``dict`` containing:
			|	 - ``corrections``   32-bit float array of length 2048. Correction values are decibel.
			|	 - ``index``         Index into the corrections array where the correction data begins.
			|	 - ``startFreq``      Frequency associated with the correction at index.

		When this function returns successfully, the correction array will contain the frequency domain
		correction constants for the given bandwidth chosen. The corrections are modified based on
		temperature, gain, attenuation, and frequency. If any of these change, a new correction array should be
		requested. The correction array will only be generated again on a new bbInitiate().
		The correction arrays and returned values differ slightly depending on the 7 or 20 MHz bandwidth
		chosen. Each one is described in depth below.

		The correction array represents 40 MHz of bandwidth where frequencies outside the requested 20 MHz
		are zeroed out. The first non-zero sample begins at corrections[index]. The frequency at this index is
		startFreq. The bin size of each index is implied through 40 MHz divided by the length of the array,
		(40.0e6 / 2048) = 19531.25 Hz. If an Fourier transform is applied on the IF data, the correction values
		will line up with the usable 20 MHz bandwdith.

		7MHz
		The correction array represents 10 Mhz of bandwdith where the usable 7 MHz is centered and all values
		outside the usable 7 MHz is zeroed. The index returned is the first non zero sample in the array. The
		startFreq returned is the frequency of the first sample in the array, corrections[0]. Every other sample’s
		frequency can be determined with the bin size. The bin size for this array is (10.0e6 / 2048) = 4882.8125
		Hz. If a complex Fourier Transform is applied to the IQ data, the correction values will line up with the
		usable 7 MHz bandwidth.

		##Tips

		Time domain corrections of the signal’s amplitude require two steps. First, an inverse Fourier Transform
		must be performed on the entire correction array (including zero’ed portions). This results in a 4096
		sample kernel. Second, the kernel is used in convolution with the time domain data. If a larger/smaller
		kernel is desired, interpolate/extrapolate the correction array while it is in the frequency domain to the
		desired length. Lengths which are powers of two are suggested.

		Frequency domain correction of the signal’s amplitude requires you to first transform the raw data into
		the frequency domain. Performing an Fourier transform on the incoming data will yeild a frequency
		domain array that will align with the correction array. You can index the Transform results using the
		index returned from this function if you wish or apply the whole array. Remember that the corrections
		are in dB. If larger Transform sizes are desired, you can interpolate the correction array to the desired
		size. (Be aware! This will change the index of the first non-zero correction, but the results of the FFT will
		still align the with usable 20 MHz)

		Raw Call: ``BB_API bbStatus bbFetchRawCorrections(int device, float *corrections, int *index, double *startFreq);``
		'''

		arraySize = 2048
		corrArr = (ct.c_float * arraySize)()
		corrArrPtr = ct.pointer(corrArr)

		index = ct.c_int(0)
		startFreq = ct.c_double(0)

		indexPtr = ct.pointer(index)
		startFreqPtr = ct.pointer(startFreq)

		err = self.dll.bbFetchRawCorrections(self.deviceHandle, corrArrPtr, indexPtr, startFreqPtr)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to fetchRawCorrections succeeded.")
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		else:
			raise IOError("Unknown error setting fetchRawCorrections! Error = %s" % err)

		ret = {
			"data" : np.ctypeslib.as_array(corrArr),
			"index" : index.value,
			"startFreq" : startFreq.value
		}

		return ret


	@classmethod
	def getRawSweep_size(cls):
		return ct.c_float, cls._rawDataArrSize

	@classmethod
	def getRawSweep_s_size(cls):
		return ct.c_short, cls._rawDataArrSize

	@classmethod
	def getRawSweepTrig_size(cls):
		return ct.c_int, cls._rawSweepTriggerArraySize




	def fetchRawSweep(self):
		'''
		returns:
			Numpy array of signed short integers

		This function is used to collect a single sweep for a device configured in raw sweep mode. The length of
		the buffer provided is determined by the settings used to configure the device for raw sweep mode. This
		length can be determined using the equation.

		Buffer-Length = 18688 * ppf * steps

		If the function returns successfully the array will contain a full sweep. The shorts will


		Raw Call: ``BB_API bbStatus bbFetchRawSweep(int device, short *buffer);``
		'''

		try:
			bufLen = 18688 * self.acq_conf["ppf"] * self.acq_conf["steps"]
		except AttributeError:
			raise ValueError("You must call configureRawSweep before fetchRawSweep")


		rawBuf = (ct.c_short * bufLen)()
		rawBufPtr = ct.pointer(rawBuf)

		err = self.dll.bbFetchRawSweep(self.deviceHandle, rawBufPtr)

		if err == self.bbStatus["bbNoError"]:
			pass  # No print statements here. Too noisy

		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured!")
		elif err == self.bbStatus["bbADCOverflow"]:
			raise IOError("The ADC has detected clipping of the input signal!")
		elif err == self.bbStatus["bbPacketFramingErr"]:
			raise IOError("Data loss or miscommunication has occurred between the device and the API!")
		elif err == self.bbStatus["bbDeviceConnectionErr"]:
			raise IOError("Device connection issues were present in the acquisition of this sweep!")
		else:
			raise IOError("Unknown error setting fetchRawSweep! Error = %s" % err)


		data = SignalHound.fastDecodeArray(rawBuf, bufLen, np.short)

		return data

	def startRawSweepLoop(self, callbackFunc):
		'''
		Args:
			callbackFunc: Python function. Used as a callback to notify the user of
				completed sweeps.

		This function can be called after being configured and initiated in RAW_SWEEP_LOOP mode. The device
		begins sweeping on the first call to this function after the device has been initiated. It is possible to call
		this function multiple times per initiate to change the function call back used.

		If this function returns successfully, the device begins sweeping immediately. The function provided is
		set as the callback function used when a sweep is completed. sweep_callback is called once per sweep
		completion. The function is passed two parameters, a pointer to the buffer of data for the sweep, and the
		length of the buffer, both ``ctypes`` variables: ``(bufPtr, bufLen)``.

		To properly decode the passed parameters, you should use the ``SignalHound.decodeRawSweep`` staticmethod.
		This takes the two ctypes arguments in the order they are passed to the callback function, and returns
		a python numpy array.

		The data buffer will not be overwritten when in the function body of sweep_callback. The API will
		maintain a circular list of buffers to store sweeps in. The API will store up to ¼ to ½ seconds worth of
		sweeps depending on parameters. If the function body of sweep_callback exceeds this amount of time,
		it is possible for the API to need to move ahead and skip over the buffer the user is still accessing. This
		will cause a loss of data. It is recommended the function body of sweep_callback is short, preferably
		simply copying the data from buffer into your own data structure. This ensures you receive every sweep
		and make your own decisions on when to drop/ignore sweeps.

		The sweep_callback function is not called in the main thread of execution. It is called once per sweep,
		which can result in the function being called anywhere from 3-250 milliseconds. It is the responsibility of
		the user to not index the buffer out of range. The buffer contents can be modified by the user only
		during the function body of sweep_callback, once the function returns, the API is free to overwrite the
		contents. Modifying the contents of the buffer not in the function body of sweep_callback is undefined.

		The user should not attempt to manage any of the memory provided through the buffer pointers.

		The device sweeps indefinitely until bbAbort or bbCloseDevice is called. When operation is suspended
		via bbAbort, the device must be reconfigured and initiated again before calling this function.

		Raw Call: ``BB_API bbStatus bbStartRawSweepLoop(int device, void(*sweep_callback)(short *buffer, int len));``
		'''

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
			raise IOError("Unknown error in startRawSweepLoop!")


	def queryTraceInfo(self):
		'''
		Returns:
			| ``dict`` containing:
			|	"arr-size": The size of arrays returned by bbFetchTrace.
			|	"arr-bin-size":  The frequency difference between two
			|			sequential bins in a returned sweep. In Zero-Span mode, binSize refers
			|			to the difference between sequential samples in seconds.
			|	"ret-start-freq":  The frequency of the first bin in a
			|			returned sweep. In Zero-Span mode, start represents the exact center
			|			frequency used by the API.

		This function should be called to determine sweep characteristics after a device has been configured
		and initiated. For zero-span mode, startFreq and binSize will refer to the time domain values. In zero-
		span mode startFreq will always be zero, and binSize will be equal to sweepTime/traceSize.

		Note: Calling while in BB_RAW_PIPE mode will produce a bbDeviceNotConfiguredErr

		Raw Call: ``BB_API bbStatus bbQueryTraceInfo(int device, unsigned int *traceLen, double *binSize, double *start);``
		'''

		# self.log.info("Querying device for trace information.")

		traceLen = ct.c_uint(0)
		traceLenPnt = ct.pointer(traceLen)

		binSize = ct.c_double(0)
		binSizePnt = ct.pointer(binSize)

		start = ct.c_double(0)
		startPnt = ct.pointer(start)


		err = self.dll.bbQueryTraceInfo(self.deviceHandle, traceLenPnt, binSizePnt, startPnt)

		if err == self.bbStatus["bbNoError"]:
			# self.log.info("returned queryTraceInfo: %d, %f, %f" % (traceLen.value, binSize.value, start.value))
			pass
		elif err == self.bbStatus["bbNullPtrErr"]:
			raise IOError("Null pointer error!")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device not Configured, or in \"raw-pipe\" mode!")
		else:
			raise IOError("Unknown error in queryTraceInfo!")

		self.traceLen = traceLen.value

		return {"arr-size" : traceLen.value, "arr-bin-size" : binSize.value, "ret-start-freq" : start.value}

	def queryStreamingCenter(self):
		'''
		Returns:
			A Double containing the absolute center frequency of
				the streaming device.

		The function retrieves the center frequency of the 20 MHz IF bandwidth of a device currently initialized
		in raw pipe mode. The center returned is representative of ¼ of the IF sample rate. The 20 MHz of usable
		bandwidth is centered on this frequency.

		Raw Call: ``BB_API bbStatus bbQueryStreamingCenter(int device, double *center);``
		'''

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
			raise IOError("Unknown error in queryStreamingCenter!")

		return center.value



	def queryTimestamp(self):
		'''

		Returns:
			| Two-Tuple containing (in order):
			|	seconds  Integer Seconds since midnight (00:00:00), January 1, 1970, coordinated
			|			universal time(UTC).
			|	nanoseconds  Integer nanoseconds between seconds and seconds + 1

		This function is used in conjunction with bbSyncCPUtoGPS and a GPS device to retrieve an absolute time
		for a data packet in raw pipe mode. This function returns an absolute time for the last packet retrieved
		from bbFetchRaw. See the Appendix:Code Examples for information on how to setup and interpret the
		time information.

		Raw Call: ``BB_API bbStatus bbQueryTimestamp(int device, unsigned int *seconds, unsigned int *nanoseconds);``
		'''

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
			raise IOError("Unknown error in queryTimestamp!")

		return (seconds.value, nanoseconds.value)

	def abort(self):
		'''

		Stops the device operation and places the device into an idle state.

		Raw Call: ``BB_API bbStatus bbAbort(int device);``
		'''

		# cleanup state variables used in various modes.
		self.acq_conf = {}


		self.log.info("Stopping acquisition")

		err = self.dll.bbAbort(self.deviceHandle)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to abort succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbDeviceNotConfiguredErr"]:
			raise IOError("Device was already idle! Did you call abort without ever calling initiate()?")
		else:
			raise IOError("Unknown error setting abort! Error = %s" % err)


	def preset(self):
		'''

		This function exists to invoke a hard reset of the device. This will function similarly to a power
		cycle(unplug/re-plug the device). This might be useful if the device has entered an undesirable or
		unrecoverable state. Often the device might become unrecoverable if a program closed unexpectedly,
		not allowing the device to close properly. This function might allow the software to perform the reset
		rather than ask the user perform a power cycle.

		Viewing the traces returned is often the best way to determine if the device is operating normally. To
		utilize this function, the device must be open. Calling this function will trigger a reset which happens
		after 2 seconds. Within this time you must call bbCloseDevice to free any remaining resources and
		release the device serial number from the open device list. From the time of the bbPreset call, we
		suggest 3 to more seconds of wait time before attempting to re-open the device.

		Raw Call: ``BB_API bbStatus bbPreset(int device);``
		'''

		self.log.warning("Performing hardware-reset of device!")
		self.log.warning("Please ensure you close the device handle within two seconds of this call!")

		err = self.dll.bbPreset(self.deviceHandle)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to preset succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		else:
			raise IOError("Unknown error calling preset! Error = %s" % err)

	def selfCal(self):
		'''

		This function causes the device to recalibrate itself to adjust for internal device temperature changes,
		generating an amplitude correction array as a function of IF frequency. This function will explicitly call
		bbAbort() to suspend all device operations before performing the calibration, and will return the device
		in an idle state and configured as if it was just opened. The state of the device should not be assumed,
		and should be fully reconfigured after a self-calibration.

		Temperature changes of 2 degrees Celsius or more have been shown to measurably alter the
		shape/amplitude of the IF. We suggest using bbQueryDiagnostics to monitor the device’s temperature
		and perform self-calibrations when needed. Amplitude measurements are not guaranteed to be
		accurate otherwise, and large temperature changes (10 ° C or more) may result in adding a dB or more of
		error.

		Because this is a streaming device, we have decided to leave the programmer in full control of when the
		device in calibrated. The device is calibrated once upon opening the device through bbOpenDevice and is
		the responsibility of the programmer after that.

		Note:
		After calling this function, the device returns to the default state. Currently the API does not retain state
		prior to the calling of bbSelfCal(). Fully reconfiguring the device will be necessary.

		Raw Call: ``BB_API bbStatus bbSelfCal(int device);``
		'''

		self.log.info("Performing self-calibration of device.")

		err = self.dll.bbSelfCal(self.deviceHandle)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to selfCal succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		else:
			raise IOError("Unknown error calling selfCal! Error = %s" % err)

	def syncCPUtoGPS(self, comPort, baudRate):
		'''
		Args:
			comPort (integer):  Com port number for the NMEA data output from the GPS reciever.
			baudRate (integer):  Baud Rate of the Com port

		The connection to the COM port is only established for the duration of this function. It is closed when
		the function returns. Call this function once before using a GPS PPS signal to time-stamp RF data. The
		synchronization will remain valid until the CPU clock drifts more than ¼ second, typically several hours,
		and will re-synchronize continually while streaming data using a PPS trigger input.

		This function calculates the offset between your CPU clock time and the GPS clock time to within a few
		milliseconds, and stores this value for time-stamping RF data using the GPS PPS trigger. This function
		ignores time zone, limiting the calculated offset to +/- 30 minutes. It was tested using an FTS 500 from
		Connor Winfield at 38.4 kbaud. It uses the “$GPRMC” string, so you must set up your GPS to output this
		string.

		Raw Call: ``BB_API bbStatus bbSyncCPUtoGPS(int comPort, int baudRate);``
		'''

		self.log.warning("GPS Synchronization not yet verified.")
		self.log.warning("e-mail Connor at connorw@imaginaryindustries.com if you have issues or comments")

		self.log.info("Attempting to synchronize CPU with GPS timebase.")

		comPort = ct.c_int(comPort)
		baudRate = ct.c_int(baudRate)

		err = self.dll.bbSyncCPUtoGPS(comPort, baudRate)

		if err == self.bbStatus["bbNoError"]:
			self.log.info("Call to syncCPUtoGPS succeeded.")
		elif err == self.bbStatus["bbDeviceNotOpenErr"]:
			raise IOError("Device not open!")
		elif err == self.bbStatus["bbGPSErr"]:
			raise IOError("Could not connect to GPS!")
		else:
			raise IOError("Unknown error synchronizing with GPS! Error = %s" % err)

	def getDeviceType(self):
		'''
		Returns:
			| Ascii string containing device type:
			| - "No device"
			| - "BB60A"
			| - "BB60C"
			| - "BB124"

		This function may be called only after the device has been opened. If the device successfully opened,
		type will contain the model type of the device pointed to by handle.


		Raw Call: ``BB_API bbStatus bbGetDeviceType(int device, int *type);``
		'''

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
			raise IOError("Unknown error setting getDeviceType! Error = %s" % err)

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
		'''

		Returns: Device serial number as a integer.

		This function may be called only after the device has been opened. The serial number returned should
		match the number on the case.

		Raw Call: ``BB_API bbStatus bbGetSerialNumber(int device, unsigned int *sid);``
		'''


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
			raise IOError("Unknown error setting getSerialNumber! Error = %s" % err)

		return serialNo.value

	def getFirmwareVersion(self):
		'''
		Returns: Device firmware rev as a integer.

		Use this function to determine which version of firmware is associated with the specified device.

		Raw Call: ``BB_API bbStatus bbGetFirmwareVersion(int device, int *version);``
		'''

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
			raise IOError("Unknown error setting getFirmwareVersion! Error = %s" % err)

		return firmwareRev.value


	def getAPIVersion(self):
		'''

		Returns: Device API version as an ascii string.

		The returned string is of the form
		major.minor.revision

		Ascii periods (“.”) separate positive integers. Major/Minor/Revision are
		not gauranteed to be a single decimal digit. The string is null
		terminated. An example string is below ..

		``[ ‘1’ | ‘.’ | ‘2’ | ‘.’ | ‘1’ | ‘1’ | ‘\0’ ] = “1.2.11”``

		Raw Call: ``BB_API const char* bbGetAPIVersion();``
		'''


		self.log.info("Querying API for revision information.")

		self.dll.bbGetAPIVersion.restype = ct.c_char_p  # Tell ctypes this function returns a pointer to a string
		apiRevStr = self.dll.bbGetAPIVersion(self.deviceHandle)
		ret = ct.c_char_p(apiRevStr).value 		# Dereference pointer, extract string
		self.log.info("Device firmware rev = %s" % ret)
		return ret

	def getErrorString(self, errCode):
		'''
		Args:
			errCode (integer): Error code value

		Returns: Ascii string containing human-readable version of the error code.

		Produce an ascii string representation of a given status code. Useful for debugging.
		Probably not really needed, since I'm doing error decoding locally in each function.

		This /should/ be of type bbStatus. bbStatus is an enum with hard-coded values, so I'm being lazy, and just using
		an int. It works well enough.

		Raw Call: ``BB_API const char* bbGetErrorString(bbStatus status);``
		'''

		serialNo = ct.c_int(errCode)

		self.dll.bbGetAPIVersion.restype = ct.c_char_p  # Tell ctypes this function returns a pointer to a string
		apiRevStr = self.dll.bbGetAPIVersion(self.deviceHandle, serialNo)

		return ct.c_char_p(apiRevStr).value  # Dereference pointer, extract string, return it.

	def getCurrentAcquisitionSettings(self):
		'''
		Return a dictionary containing the return values from ``queryTraceInfo()``, ``getDeviceDiagnostics()`` and the current ``acq_conf``

		If there is no running acquisition, ``queryTraceInfo()`` will be defaulted to ``{}``

		'''
		try:
			tmp = self.queryTraceInfo()
		except IOError:
			tmp = {}

		tmp.update(self.getDeviceDiagnostics())
		tmp.update(self.acq_conf)

		return tmp


	# staticmethod, because it's only usefull for dealing with the SignalHound stuff, and yet it should be accessible easily for stuff like callbacks where you don't have.
	# easy access to the instantiated class pointer
	@staticmethod
	def decodeRawSweep(bufPtr, bufLen):
		'''
		Args:
			bufPtr (pointer to buffer): Pointer to a C buffer containing a sweep dataset
			buflen (integer buffer size): Size of the data in ``bufPtr``

		Decode a C array into a numpy-array using buffer casts. Assumes the values in the buffer are of datatype ``np.short``

		Assumed array size is ``sizeof(np.short) * buflen`` bytes, or effectively 2 * bufLen.

		Returns:
			Numpy array containing contents of buffer

		Note: This function copies the data from the array, so it is valid even if the memory underlying the ``bufPtr`` is subsequently
		deallocated. This is intended for handling contexts like the callback, where once the callback returns, the SignalHound memory
		management may reuse or free the underlying buffer. Since the copied array will be managed by the python memory manager, it
		is safe to preserve beyond the scope of a calling function.
		'''
		bufAdr = ct.addressof(bufPtr.contents)
		arr = np.frombuffer(int_asbuffer(bufAdr, bufLen * np.short().nbytes), dtype=np.short)  # Map array memory as a numpy array.
		arr = arr.copy()  # Then copy it, so our array won't get modified when the circular buffer overwrites itself.
		# We have to copy() since the call normally just returns a array that is overlaid onto the pre-existing data
		return arr

	@staticmethod
	def fastDecodeArray(ctBuff, buffLen, dtype):
		'''
		Args:
			bufPtr (pointer to buffer): Pointer to a C buffer containing a sweep dataset
			buflen (integer buffer size): Size of the data in ``bufPtr``
			dtype (numpy data-type): Datatype of values in array.

		Decode a C array into a numpy-array using buffer casts.

		Assumed array size is ``sizeof(dtype) * buflen`` bytes.

		Returns:
			Numpy array containing contents of buffer


		Note: This function copies the data from the array, so it is valid even if the memory underlying the ``bufPtr`` is subsequently
		deallocated. This is intended for handling contexts like the callback, where once the callback returns, the SignalHound memory
		management may reuse or free the underlying buffer. Since the copied array will be managed by the python memory manager, it
		is safe to preserve beyond the scope of a calling function.
		'''
		bufAdr = ct.addressof(ctBuff)
		arr = np.frombuffer(int_asbuffer(bufAdr, buffLen * dtype().nbytes), dtype=dtype)  # Map array memory as a numpy array.
		arr = arr.copy()  # Then copy it, so our array won't get modified when the circular buffer overwrites itself.
		# We have to copy() since the call normally just returns a array that is overlaid onto the pre-existing data
		return arr
