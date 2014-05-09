


import wx

import numpy as np
import queVars


import random
import wx




class GraphPanel(wx.Panel):

		#Number of items in the color map LUT
		#I'm pretty sure the actual cm library only uses 256, so settings above 256 have no benefit

	def __init__(self,  *args, **kwds):
		#kwds["style"] = wx.RESIZE_BORDER|wx.TAB_TRAVERSAL|wx.CLIP_CHILDREN
		wx.Panel.__init__(self, *args, **kwds)
		#print self
		#wx.Panel.__init__( self, parent, **kwargs )

		#print "Test"
		#super(GridPanel, self).__init__(None, -1, 'CursorTracker')	# Call inheritor's __init__


		self.data = np.array([])

		self.mdc = None # memory dc to draw off-screen

		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.onErase)
		self.Bind(wx.EVT_PAINT, self.onPaint)

		#print "Size", self.rectDims
		#Blue text on a black->red->orange->yellow->white background


		self.colourBlack	= wx.Colour(0, 0, 0)
		self.colourWhite	= wx.Colour(255, 255, 255)

		self.penBlack		= wx.Pen(self.colourBlack)
		self.penWhite		= wx.Pen(self.colourWhite)

		self.brushBlack = wx.Brush(self.colourBlack)
		self.brushWhite = wx.Brush(self.colourWhite)


		self.onSize(None)
		#self.onTimer()

		self.redraw_timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
		# self.redraw_timer.Start(1000/10)

	def onSize(self, event):
		# re-create memory dc to fill window
		w, h = self.GetClientSize()
		self.mdc = wx.MemoryDC(wx.EmptyBitmap(w, h))
		self.redraw()

	def onErase(self, event):
		pass # don't do any erasing to avoid flicker

	def onPaint(self, event):
		# just blit the memory dc
		dc = wx.PaintDC(self)
		if not self.mdc:
			return
		w, h = self.mdc.GetSize()
		dc.Blit(0, 0, w, h, self.mdc, 0, 0)


	def generateLineList(self, xArr, yArr, arrSz, dcSize):

		lineList = []
		w, h = dcSize
		start = None, None
		for offset in xrange(arrSz):
			if not start:
				start = w-xArr[offset], h-yArr[offset]
			else:

				tX = w-xArr[offset]
				tY = h-yArr[offset]
				sX, sY = start
				lineList.append((sX, sY, tX, tY))
		return lineList


	def generateScatterList(self, xArr, yArr, arrSz, dcSize):

		pointList = []
		w, h = dcSize
		for offset in xrange(arrSz):
			tX = w-xArr[offset]
			tY = h-yArr[offset]

			pointList.append((tX, tY))
		return pointList

	def setDataArray(self, inData):
		self.data = inData
		self.redraw()

	def redraw(self):
		# do the actual drawing on the memory dc here
		dc = self.mdc

		w, h = dc.GetSize()
		dc.Clear()
		dc.SetPen(self.penBlack)


		dc.SetBrush(self.brushBlack)
		dc.DrawRectangle(0, 0, w, h)

		dc.SetTextForeground(self.colourWhite)
		#print arr
		#print self.rectDims

		if self.data.shape != (0,):
			# print "Meh",  self.data.shape
			# print self.data.shape
			dataLen = self.data.shape[0]

			dataMin = self.data.min()
			dataMax = self.data.max()

			dataHeight = float(dataMax - dataMin)
			if dataHeight == 0:
				dataHeight = 0.001
			scaleFactor = (h-2.0) / dataHeight
			# print scaleFactor, dataMin, dataMax, dataHeight

			dataX = np.linspace(1, w-1, num=dataLen)

			dataY = ((self.data-dataMin) * scaleFactor) + 1

			# pointList = self.generateScatterList(dataX, dataY, dataLen, dc.GetSize())
			# pointList.sort()
			# dc.DrawPointList(pointList, self.penWhite)

			pointList = self.generateScatterList(dataX, dataY, dataLen, dc.GetSize())
			# pointList.sort()

			dc.SetPen(self.penWhite)
			dc.DrawLines(pointList)


			dc.DrawText("Max: %0.5fdB" % dataMax, 10, 5)
			dc.DrawText("Min: %0.5fdB" % dataMin, 10, h - 20)

			dc.DrawText("Pk-Pk: %0.8fdB" % (dataMax-dataMin), w-140, 5)

			dat = self.data

			# dat = dat - np.mean(dat)

			# dat = dat**2
			# dat = np.mean(dat)
			# dat = np.sqrt(dat)

			# dc.DrawText("RMS:  %0.8fV" % dat, w-140, h - 20)




		self.Refresh()


	def draw_plot(self):
		""" Redraws the plot
		"""
		# when xmin is on auto, it "follows" xmax to produce a
		# sliding window effect. therefore, xmin is assigned after
		# xmax.
		#

		# for ymin and ymax, find the minimal and maximal values
		# in the data set and add a mininal margin.
		#
		# note that it's easy to change this scheme to the
		# minimal/maximal value in the current display, and not
		# the whole data set.
		#
		self.redraw()



	def on_redraw_timer(self, event):
		# if paused do not add data, but still redraw the plot
		# (to respond to scale modifications, grid change, etc.)

		#print "Bwuh?", self.channel, self.data.shape, self.data[...,self.channel], np.arange(self.data.shape[0])
		self.draw_plot()

	def on_exit(self, event):
		print "trying to die"
		self.Destroy()


