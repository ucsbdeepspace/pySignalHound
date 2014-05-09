#!C:/Python26


import numpy as np
import threading



run = True

sokThread = None


DATA = np.array([])
DATA_LOCK = threading.Lock()

def getData():
	DATA_LOCK.acquire()
	ret = DATA.copy()
	DATA_LOCK.release()
	return ret

def setData(inData):
	global DATA
	DATA_LOCK.acquire()
	DATA = inData
	DATA_LOCK.release()


