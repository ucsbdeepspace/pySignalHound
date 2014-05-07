


import numpy as np
cimport numpy as np


import cython


ctypedef np.float32_t OUT_DTYPE_t

@cython.boundscheck(False)
def calcAllanVariance(inArr):
	if not len(inArr.shape) == 1:
		raise ValueError("Can only calculate allan variance across 1D array")



	"""Compute the Allan variance on a set of regularly-sampled data (1D).

	   If the time between samples is dt and there are N total
	   samples, the returned variance spectrum will have frequency
	   indices from 1/dt to (N-1)/dt."""
	# 2008-07-30 10:20 IJC: Created
	# 2011-04-08 11:48 IJC: Moved to analysis.py
	# 2011-10-27 09:25 IJMC: Corrected formula; thanks to Xunchen Liu
	#                        of U. Alberta for catching this.

	cdef np.ndarray[OUT_DTYPE_t, ndim=1]  newdata = np.array(inArr, subok=True, copy=True, dtype=np.float32)

	cdef int numDatPts = newdata.shape[0]
	alvar = np.zeros(numDatPts-1, float)

	for lag in xrange(1, numDatPts):
		# Old, wrong formula:
		#alvar[lag-1]  = mean( (newdata[0:-lag] - newdata[lag:])**2 )
		alvar[lag-1] = (np.mean(newdata[0:(lag+1)])-
						np.mean(newdata[0:lag]))**2

	return (alvar*0.5)

def calc(inArr):
	cdef int numCols = inArr.shape[0]
	for x in xrange(numCols):
		yield calcAllanVariance(inArr[x,...])


