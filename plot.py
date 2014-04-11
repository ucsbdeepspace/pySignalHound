
import sys
import numpy as np
import matplotlib
matplotlib.use("WxAgg")

import matplotlib.pyplot as pplt

import matplotlib.cm as cm

from surfPlot import surface_plot

'''

This plots the data-files logged by the tests.py file when run with the "traces" parameter.

e.g. `python tests.py traces` > Captures and saves a set of spectrum sweeps to a file named `dat.bin`
`python plot.py` then plots the contents of the `dat.bin` file.

Note that `dat.bin` is actually a CSV file. I really should change the name.

'''


H_FLIP_FREQ            = 1.420405751786e9
ACQ_FREQ               = H_FLIP_FREQ + 12.5e6
ACQ_SPAN               = 20e6


def go():

	arr = np.genfromtxt(r"C:\Users\Fake Name\Desktop\Repository\Programming\Code\Python\pySignalHound\Data\2014\04\10\Datalog - 2014 04 10, Thu, 19-36-35.csv", delimiter=",")

	arr = arr[...,1:] # Chop off timestamps.


	numPlots = 1

	yAx = np.linspace(ACQ_FREQ - (ACQ_SPAN/2), ACQ_FREQ + (ACQ_SPAN/2), num=arr.shape[1])
	print yAx
	print arr.shape
	print yAx.shape

	mainWin = pplt.figure()
	mainWin.subplots_adjust(hspace=.4, wspace=.4)
	#Add space between subplots to make them look nicer

	plot1 = mainWin.add_subplot(numPlots,1,1)
	# for x in range(arr.shape[0]):
	# 	plot1.plot(yAx, arr[x,...])
	# 	plot1.grid()
	plot1.imshow(arr, extent=(-100, 0, -100, 0), aspect=0.65, cmap=cm.gist_ncar)

	avgWin = pplt.figure()
	plot2 = avgWin.add_subplot(numPlots,1,1)
	plot2.plot(yAx, np.average(arr, axis=0))

	surface_plot(arr, x_extents=(100e6, 200e6))

	pplt.show()

	print "Done"

if __name__ == "__main__":
	go()

