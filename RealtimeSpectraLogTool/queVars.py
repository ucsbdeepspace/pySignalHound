#!C:/Python26


import numpy as np
import threading



run = True

sokThread = None

DATA_FRESH = False
DATA = np.array([])
DATA_STATS = {}
DATA_LOCK = threading.Lock()

def getData():
	global DATA_FRESH
	if not DATA_FRESH:
		return None
	DATA_LOCK.acquire()
	ret = DATA.copy(), DATA_STATS
	DATA_FRESH = False
	DATA_LOCK.release()
	return ret

def setData(inData, acqInfo):
	global DATA
	global DATA_STATS
	global DATA_FRESH
	DATA_LOCK.acquire()
	DATA = inData
	DATA_STATS = acqInfo.copy()
	DATA_FRESH = True
	DATA_LOCK.release()


