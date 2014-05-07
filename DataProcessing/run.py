

import sys
import os
import os.path
import h5py

import matplotlib
matplotlib.use("WxAgg")

import matplotlib.pyplot as pplt

import numpy as np
import numpy.random as rand
def openFile(filePath):
	f = h5py.File(filePath)

	return f


import pyximport
pyximport.install(setup_args={"include_dirs":np.get_include()})
import allanVariance






def go():
	if len(sys.argv) == 1:
		print("You need to specify a HDF5 file name!")
		return

	if not os.path.exists(sys.argv[1]):
		print("You need to specify a valid HDF5 file name+path!")
		return

	dat = openFile(sys.argv[1])
	print dat
	print dat.keys()
	print dat["Spectrum_Data"]
	print dat["Spectrum_Data"].shape

	# mainWin = pplt.figure()

	# plot1 = mainWin.add_subplot(1,1,1)

	# sys.exit()



	for var in allanVariance.calc(dat["Spectrum_Data"]):
		print"Plotting", var

		mainWin = pplt.figure()

		plot1 = mainWin.add_subplot(1,1,1)
		plot1.plot(var)
		corr = np.sqrt(np.mean(var**2))
		plot1.plot(allanVariance.calcAllanVariance(rand.randn(16385))**2*corr)
		plot1.set_yscale('log')
		plot1.set_xscale('log')

		pplt.show()


if __name__ == "__main__":
	go()