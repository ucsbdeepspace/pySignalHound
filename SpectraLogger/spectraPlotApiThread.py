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


import logging
import time
import socket
import logSetup
import traceback
import cPickle


HOST = ''                 # Symbolic name meaning all available interfaces
PORT = 50007              # Arbitrary non-privileged port

TX_TIMEOUT = 2
CONN_TIMEOUT = 0.01

def startApiServer(dataQueue, ctrlNs, printQueue):


	log = logging.getLogger("Main.PlotApiProcess")
	logSetup.initLogging(printQ = printQueue)
	log.info("PlotApiProcess starting up")
	loop_timer = time.time()

	conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	conn.bind((HOST, PORT))
	conn.listen(1)

	# Needs to be blocking, so we don't get non-blocking errors on transmission for LARGE data-chunks
	conn.settimeout(CONN_TIMEOUT)

	data = None
	sok = None
	dataChunks = 0
	while 1:

		if not sok:
			try:
				sok, addr = conn.accept()

				# Needs to be blocking, so we don't get non-blocking errors on transmission for LARGE data-chunks
				sok.settimeout(TX_TIMEOUT)

				log.info("Have connection %s from %s", sok, addr)
			except socket.timeout:
				if not dataQueue.empty():
					dummy = dataQueue.get()
					dataChunks += 1

		if sok != None:
			if dataQueue.empty():
				time.sleep(0.005)
			else:
				# log.info("Sending plot data out socket")
				tmp = dataQueue.get()

				if "max" in tmp:
					data = tmp["max"]
					pData = cPickle.dumps(data)
					pData = "BEGIN_DATA"+pData+"END_DATA"
					try:
						# Holy shit, sok.send is MUCH faster then sok.sendall. Wat?
						# I bet senall() is sending each byte at a time from native python, rather then just calling send() from the OS
						# API directly on the buffer to send. Stupid.
						ret = sok.send(pData)
						if ret != len(pData):
							raise BufferError
						dataChunks += 1
					except BufferError:
						log.error("Transmission failed to properly transmit all bytes")
						log.error(traceback.format_exc())

					except socket.timeout:
						log.error("Timeout on transmit?")
						log.error(traceback.format_exc())
					except AttributeError:
						# I have NO idea how this was happening, but somehow sok.sendall was being called after
						# sok had been set = None.
						log.error("WAT?")
						log.error(traceback.format_exc())


					except socket.error:
						log.error("Socket Error!")
						log.error(traceback.format_exc())
						sok = False
				else:
					log.error("WAT? Unknown packet!")
					log.error(tmp)


		if ctrlNs.acqRunning == False:
			log.info("Stopping API-thread!")
			break


		now = time.time()
		delta = now-loop_timer
		if delta >= 5:
			if dataChunks:
				freq = 1 / (delta/dataChunks)
				log.info("Elapsed Time = %0.5f, Chunk Update Frequency = %s", delta, freq)
				loop_timer = now
				dataChunks = 0
			else:
				log.info("Elapsed Time = %0.5f, No chunks processed?", delta)
				loop_timer = now


	log.info("Print-API-thread exiting!")
	ctrlNs.apiRunning = False
	dataQueue.close()
	dataQueue.join_thread()
