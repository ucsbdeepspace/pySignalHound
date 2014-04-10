# -*- coding: UTF-8 -*-

import numpy as np

# This import appears to monkey-patch matplotlib, adding the `projection='3d'` option
# Yes, this is fucking obscure. What the hell, people?
from mpl_toolkits.mplot3d import Axes3D

from matplotlib import cm
import matplotlib.pyplot as pplt


def surface_plot(arr, cmap=cm.jet, x_extents=(0,1), y_extents=(0,1)):

	if len(arr.shape) != 2:
		raise ValueError("You must pass a 2D array.")
	if len(x_extents) != 2 or len(y_extents) != 2:
		raise ValueError("Extents parameters must be 2-tuples.")


	x = np.linspace(x_extents[0],x_extents[1], arr.shape[1])
	y = np.linspace(y_extents[0],y_extents[1], arr.shape[0])

	x_surf, y_surf = np.meshgrid(x, y)

	fig = pplt.figure()
	ax = fig.add_subplot(111, projection='3d')
	ax.plot_surface(x_surf, y_surf, arr, cmap=cmap)




def test():
	import pylab as p

	x = np.linspace(-5, 5, 200)
	y = np.linspace(-5, 5, 150)

	X,Y = p.meshgrid(x, y)
	Z = p.bivariate_normal(X, Y)

	# mainWin = pplt.figure()
	print X, Y, Z
	print X.shape
	print Y.shape
	print Z.shape
	surface_plot(Z)

	pplt.show()

if __name__ == "__main__":
	test()
