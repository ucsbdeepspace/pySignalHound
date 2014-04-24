




import ctypes as ct
import multiprocessing as mp
import multiprocessing.sharedctypes as sct



class SharedMemRingBuf(object):

	def __init__(self, numChunks, chunkDtype, chunkSize):

		self.head = sct.RawValue(ct.c_uint64, 0)
		self.appendLock = mp.Lock()
		self.tail = sct.RawValue(ct.c_uint64, 0)
		self.retrieveLock = mp.Lock()


		self.len = numChunks
		self.buf = []
		for dummy_x in range(numChunks):
			self.buf.append([sct.RawArray(chunkDtype, chunkSize), mp.Lock()])

	def checkRange(self):
		if self.head.value - self.tail.value >= self.len-10:
			raise ValueError("Overran circular buffer!")


	def getAddPointer(self):
		self.checkRange()
		self.appendLock.acquire()
		self.head.value += 1
		cBuf, lock = self.buf[(self.head.value) % self.len-1]
		cBufPt = ct.pointer(cBuf)

		lock.acquire()  # Acquire the lock on the returned value. It will be released when it has been processed.
		self.appendLock.release()

		return [cBufPt, lock]

	def getAddArray(self):
		self.checkRange()
		self.appendLock.acquire()
		self.head.value += 1
		cBuf, lock = self.buf[(self.head.value) % self.len-1]


		lock.acquire()  # Acquire the lock on the returned value. It will be released when it has been processed.
		self.appendLock.release()

		return [cBuf, lock]


	def getOldest(self):
		self.retrieveLock.acquire()

		if self.head.value == self.tail.value:
			self.retrieveLock.release()
			return False

		cBuf, lock = self.buf[(self.tail.value) % self.len-1]
		self.tail.value += 1

		lock.acquire()  # Acquire the lock on the returned value. It will be released when it has been processed.

		self.retrieveLock.release()
		return cBuf, lock


	def getItemsNum(self):
		return self.head.value-self.tail.value
