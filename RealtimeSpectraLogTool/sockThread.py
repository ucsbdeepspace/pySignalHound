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


import time
import socket
import cPickle
import sys

import queVars

HOST = '127.0.0.1'                 # Symbolic name meaning all available interfaces
PORT = 50007              # Arbitrary non-privileged port

def processData(inStr):
	if not "END_DATA" in inStr:
		return inStr

	raw_data, tail = inStr.split("END_DATA", 1)

	if not raw_data.startswith("BEGIN_DATA"):
		return tail


	dummy_head, pDat = raw_data.split("BEGIN_DATA", 1)

	dat = cPickle.loads(pDat)
	startFreq = dat["startFreq"]
	binSize = dat["binSize"]
	numBins = dat["numBins"]

	data = dat["data"]
	print "Have valid data!", len(pDat)/1000000.0, "MBytes, dataPoints =", data.shape[0], "points, Bytes/Point", (len(pDat)*1.0)/data.shape[0]

	if (numBins,) != data.shape:
		print "Error?", numBins, data.shape[0]

	queVars.setData(data, {"numBins":numBins, "binSize":binSize, "startFreq":startFreq})
	return tail



def startApiClient():

	loop_timer = time.time()

	conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	conn.settimeout(0.1)
	conn.connect((HOST, PORT))

	ret = ""
	while 1:

		try:
			# Typical 80 Kpt array is 3642464 bytes
			# 2**22 is                4194304 bytes
			ret += conn.recv(2**22)
			ret = processData(ret)

		except socket.timeout:
			pass


		now = time.time()
		delta = now-loop_timer
		if delta > 5:
			freq = 1 / (delta+0.00001)
			print("Elapsed Time = %0.5f, Frequency = %s" % (delta, freq))
			loop_timer = now

		if not queVars.run:
			print("SocketThread stopping")
			break

		time.sleep(0.001)

if __name__ == "__main__":
	if len(sys.argv) > 1:
		print sys.argv

	startApiClient()

