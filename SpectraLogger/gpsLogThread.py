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
# Drag in path to the library (MESSY)
import os, sys
lib_path = os.path.abspath('../')
print "Lib Path = ", lib_path
sys.path.append(lib_path)

import logging
import logSetup
import time
import serial
import pynmea2

import traceback

from settings import GPS_COM_PORT

def startGpsLog(dataQueues, ctrlNs, printQueue):
	gpsRunner = GpsLogThread(printQueue)
	gpsRunner.sweepSource(dataQueues, ctrlNs)

class GpsLogThread(object):
	log = logging.getLogger("Main.GpsProcess")

	def __init__(self, printQueue):
		self.printQueue = printQueue
		logSetup.initLogging(printQ=printQueue)


	def sweepSource(self, dataQueues, ctrlNs):

		dataQueue, plotQueue = dataQueues


		ser   = serial.Serial(GPS_COM_PORT, 4800, timeout=1)
		parse = pynmea2.NMEAStreamReader()


		message = {'latitude' : None, 'longitude' : None, 'numsatview' : None, 'date': None, 'time' : None}

		while 1:
			time.sleep(0.1)
			dat = ser.read(16)
			parsed = []
			try:
				parsed = parse.next(dat)
			except UnicodeDecodeError:
				print("Parse error!")
				print(traceback.format_exc())
				for key in message.keys():
					message[key] = None
			except pynmea2.nmea.ParseError:
				print("Parse error!")
				print(traceback.format_exc())
				for key in message.keys():
					message[key] = None
			except pynmea2.nmea.ChecksumError:
				print("Parse error!")
				print(traceback.format_exc())
				for key in message.keys():
					message[key] = None
			except ValueError:
				print("Parse error!")
				print(traceback.format_exc())
				for key in message.keys():
					message[key] = None

			for msg in parsed:
				if hasattr(msg, "latitude"):
					message['latitude'] = msg.latitude
					print("latitude", msg.latitude)
				if hasattr(msg, "longitude"):
					message['longitude'] = msg.longitude
					print("longitude", msg.longitude)
				if hasattr(msg, "num_sv_in_view"):
					message['numsatview'] = msg.num_sv_in_view
					print("sattelites", msg.num_sv_in_view)
				if hasattr(msg, "timestamp"):
					message['time'] = msg.timestamp
					print("timestamp", msg.timestamp)
				if hasattr(msg, "datestamp"):
					message['date'] = msg.datestamp
					print("datestamp", msg.datestamp)

				if all(message.values()):
					print("Complete message!", message)
					for key in message.keys():
						message[key] = None

			# if ctrlNs.run == False:
			# 	self.log.info("Stopping Acq-thread!")
			# 	break





		self.log.info("Acq-thread closing dataQueue!")
		dataQueue.close()
		dataQueue.join_thread()

		plotQueue.close()
		plotQueue.cancel_join_thread()

		ctrlNs.acqRunning = False

		self.log.info("Acq-thread exiting!")
		self.printQueue.close()
		self.printQueue.join_thread()



def dotest():
	print("Starting test")
	import Queue
	logSetup.initLogging()
	startGpsLog((Queue.Queue(), Queue.Queue()), None, Queue.Queue())

if __name__ == "__main__":
	dotest()


