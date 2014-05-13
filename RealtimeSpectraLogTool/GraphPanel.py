


import wx

import numpy as np

import sys


GRAPH_GRID_Y_STEP = 5

class GraphPanel(wx.Panel):

	def __init__(self,  *args, **kwds):
		wx.Panel.__init__(self, *args, **kwds)

		self.data = np.array([])

		self.mdc = None # memory dc to draw off-screen

		# Set up min and max values so the first run will override them
		self.minVal = sys.maxint*1.0
		self.maxVal = (sys.maxint-1)*-1.0

		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.onErase)
		self.Bind(wx.EVT_PAINT, self.onPaint)


		self._colourBlack		= wx.Colour(0, 0, 0)
		self._colourWhite		= wx.Colour(255, 255, 255)
		self._colourPastelBlue	= wx.Colour(100, 100, 200)

		self._penBlack			= wx.Pen(self._colourBlack)
		self._penWhite			= wx.Pen(self._colourWhite)
		self._penPastelBlue		= wx.Pen(self._colourPastelBlue)

		self._brushBlack = wx.Brush(self._colourBlack)
		self._brushWhite = wx.Brush(self._colourWhite)

		# Only redraw if stale is true.
		self.stale=True

		self.onSize(None)
		#self.onTimer()

		self.redraw_timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
		self.redraw_timer.Start(1000/30)

	def onSize(self, dummy_event):
		# re-create memory dc to fill window
		self.stale=True
		w, h = self.GetClientSize()
		self.mdc = wx.MemoryDC(wx.EmptyBitmap(w, h))
		self.redraw()

	def onErase(self, dummy_event):
		pass # don't do any erasing to avoid flicker

	def onPaint(self, dummy_event):
		# just blit the memory dc
		dc = wx.PaintDC(self)
		if not self.mdc:
			return
		w, h = self.mdc.GetSize()
		dc.Blit(0, 0, w, h, self.mdc, 0, 0)


	def generateLineList(self, xArr, yArr, arrSz):

		lineList = []
		w, h = self.mdc.GetSize()
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


	def generateScatterList(self, xArr, yArr, arrSz):

		pointList = []
		w, h = self.mdc.GetSize()
		for offset in xrange(arrSz):
			tX = w-xArr[offset]
			tY = h-yArr[offset]

			pointList.append((tX, tY))
		return pointList

	def generateGridList(self):
		w, h = self.mdc.GetSize()

		lineList = []
		yMin, yMax = int(self.minVal), int(self.maxVal)



		for y in range(yMin, yMax, GRAPH_GRID_Y_STEP):
			pxY = self.mapYValueToContext(y)
			lineList.append((0, pxY, w, pxY))

		for x in np.linspace(0, w, num=w/50):
			lineList.append((x, 0, x, h))



		return lineList


	def setDataArray(self, inData):
		self.stale=True
		# THe plotting starts to really slow down above 20kpoints.
		# Therefore, we just start skipping data-points to keep the total array size below 20k
		skip = len(inData)/20000
		if skip != 0:
			inData = inData[::skip]

		self.data = inData
		self.redraw()

	def preCalcScalingFactor(self, yHeight):

		dataHeight = float(self.maxVal - self.minVal)
		if dataHeight == 0:
			dataHeight = 0.001
		self.scaleFactor = (yHeight-2.0) / dataHeight

	def mapYValueToContext(self, value):


		value = ((value-self.minVal) * self.scaleFactor) + 1
		return value

	def redraw(self):
		# do the actual drawing on the memory dc here
		if not self.stale:
			# print("Not drawing as plot is not stale")
			return

		self.stale = False
		dc = self.mdc

		w, h = dc.GetSize()
		dc.Clear()
		dc.SetPen(self._penBlack)


		dc.SetBrush(self._brushBlack)
		dc.DrawRectangle(0, 0, w, h)

		dc.SetTextForeground(self._colourWhite)
		#print arr
		#print self.rectDims

		if self.data.shape != (0,):
			# print "Meh",  self.data.shape
			# print self.data.shape
			dataLen = self.data.shape[0]

			dataMin = self.data.min()
			dataMax = self.data.max()

			if dataMin < self.minVal:
				self.minVal = (dataMin-5.0) + (5-(dataMin % 5))

			if dataMax > self.maxVal:
				self.maxVal = (dataMax+5.0) - (dataMax % 5)



			self.preCalcScalingFactor(h)

			# print scaleFactor, self.minVal, self.maxVal, dataHeight

			dataX = np.linspace(1, w-1, num=dataLen)

			dataY = self.mapYValueToContext(self.data)

			# pointList = self.generateScatterList(dataX, dataY, dataLen, dc.GetSize())
			# pointList.sort()
			# dc.DrawPointList(pointList, self._penWhite)


			gridList = self.generateGridList()
			dc.DrawLineList(gridList, pens=self._penPastelBlue)


			pointList = self.generateScatterList(dataX, dataY, dataLen)
			# pointList.sort()

			dc.SetPen(self._penWhite)
			dc.DrawLines(pointList)


			dc.DrawText("Max: %0.5fdB" % self.maxVal, 10, 5)
			dc.DrawText("Min: %0.5fdB" % self.minVal, 10, h - 20)

			dc.DrawText("Pk-Pk: %0.8fdB" % (self.maxVal-self.minVal), w-150, 5)
			dc.DrawText("Y-Grid: %0.2fdB per div" % GRAPH_GRID_Y_STEP, w-150, h - 20)



		self.Refresh()


	def draw_plot(self):

		self.redraw()



	def on_redraw_timer(self, dummy_event):
		self.draw_plot()

	def on_exit(self, dummy_event):
		print "trying to die"
		self.Destroy()


