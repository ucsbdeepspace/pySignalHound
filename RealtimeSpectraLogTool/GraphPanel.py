


import wx

import numpy as np

import sys
import peakFind
from scipy import signal


GRAPH_GRID_Y_STEP = 5
GRAPH_GRID_X_DIV_STEP = 1e6   # 5 Mhz per division

class GraphPanel(wx.Panel):

	def __init__(self,  *args, **kwds):
		wx.Panel.__init__(self, *args, **kwds)

		self.data = {}

		self.mdc = None # memory dc to draw off-screen
		self.mouseDc = None # fast-update drawing buffer

		# Set up min and max values so the first run will override them
		self.minVal = sys.maxint*1.0
		self.maxVal = (sys.maxint-1)*-1.0

		self.startFreq = sys.maxint*1.0
		self.stopFreq = (sys.maxint-1)*-1.0
		self.binSize = None

		self.peakSensitivityModifier = 5.5

		self.Bind(wx.EVT_SIZE, self.onSize)
		self.Bind(wx.EVT_ERASE_BACKGROUND, self.onErase)
		self.Bind(wx.EVT_PAINT, self.onPaint)


		self._colourBlack		= wx.Colour(0, 0, 0)
		self._colourWhite		= wx.Colour(255, 255, 255)
		self._colourPastelBlue	= wx.Colour(100, 100, 200)
		self._colourPastelRed	= wx.Colour(250, 100, 100)
		self._colourPastelGreen	= wx.Colour(100, 250, 100)
		self._colourGrey		= wx.Colour(150, 150, 150)
		self._colourRed			= wx.Colour(255,   0,   0)

		self._penBlack			= wx.Pen(self._colourBlack)
		self._penWhite			= wx.Pen(self._colourWhite)
		self._penGrey			= wx.Pen(self._colourGrey)
		self._penPastelBlue		= wx.Pen(self._colourPastelBlue)
		self._penPastelRed		= wx.Pen(self._colourPastelRed, width=2)
		self._penPastelGreen	= wx.Pen(self._colourPastelGreen)
		self._penHeavyRed		= wx.Pen(self._colourRed, width=3)

		self._brushBlack = wx.Brush(self._colourBlack)
		self._brushWhite = wx.Brush(self._colourWhite)
		self._brushClear = wx.Brush(self._colourWhite, style=wx.TRANSPARENT)

		self._baseFont = wx.Font(12, family=wx.FONTFAMILY_DEFAULT, style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL)
		self._pointFont = wx.Font(9, family=wx.FONTFAMILY_DEFAULT, style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL)

		# Only redraw if stale is true.
		self.stale=True

		self.onSize(None)
		#self.onTimer()

		self.redraw_timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)
		self.redraw_timer.Start(1000/30)

	def changePeakSense(self, peakSense):
		if peakSense < 1 or peakSense > 10:
			raise ValueError("wat")
		self.peakSensitivityModifier = peakSense


	def onSize(self, dummy_event):
		# re-create memory dc to fill window
		self.stale=True
		w, h = self.GetClientSize()
		self.mdc = wx.MemoryDC(wx.EmptyBitmap(w, h))
		self.mouseDc = wx.MemoryDC(wx.EmptyBitmap(w, h))
		self.redraw()

	def onErase(self, dummy_event):
		pass # don't do any erasing to avoid flicker

	def onPaint(self, dummy_event):
		# just blit the memory dc
		dc = wx.PaintDC(self)
		if not self.mdc:
			return
		w, h = self.mdc.GetSize()

		self.mouseDc.Blit(0, 0, w, h, self.mdc, 0, 0)

		self.drawMouse()

		dc.Blit(0, 0, w, h, self.mouseDc, 0, 0)


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

		dummy_w, h = self.mdc.GetSize()
		for offset in xrange(arrSz):
			tX = xArr[offset+self.xOffset]
			tY = h-yArr[offset]

			pointList.append((tX, tY))
		return pointList

	def generateGridList(self):
		w, h = self.mdc.GetSize()

		lineList = []
		yMin, yMax = int(self.minVal), int(self.maxVal)

		xDivisions = 0

		for y in range(yMin, yMax, GRAPH_GRID_Y_STEP):
			pxY = self.mapYValueToContext(y)
			lineList.append((0, pxY, w, pxY))

		gridWidth = (self.stopFreq - self.startFreq) / GRAPH_GRID_X_DIV_STEP

		for x in np.linspace(0, w, num=gridWidth+2):
			lineList.append((x, 0, x, h))
			xDivisions += 1

		# The plot window is bookended at each edge by a vertical line.
		#Therefore,  the number of divisions is the number of lines - 1
		xDivisions = xDivisions - 1

		return lineList, xDivisions


	def setDataArray(self, inData):
		self.stale=True
		# THe plotting starts to really slow down above 20kpoints.
		# Therefore, we just start skipping data-points to keep the total array size below 20k
		inData, dataInfo = inData

		if all(dataInfo.keys()):  # If there is valid data for all keys in the dict
			stop = dataInfo['startFreq'] + (dataInfo["binSize"] * dataInfo["numBins"])
			start = dataInfo['startFreq']
			if start < self.startFreq:
				self.startFreq = start
			if stop > self.stopFreq:
				self.stopFreq = stop
			self.binSize = dataInfo["binSize"]

			self.currentStart = start

			self.totalXPoints = (self.stopFreq-self.startFreq) / dataInfo["binSize"]
			print("Start", self.startFreq, "Stop", self.stopFreq, "X POints = ", self.totalXPoints)

			skip = int(len(inData)/20000)
			if skip != 0:
				# Correct the bin size for the skip setting
				self.binSize = self.binSize * skip
				inData = inData[::skip]

			self.data[start] = inData
			self.redraw()

	def preCalcScalingFactor(self, dc, startFreqOverride=None):

		xWidth, yHeight = dc.GetSize()

		dataHeight = float(self.maxVal - self.minVal)
		if dataHeight == 0:
			dataHeight = 0.001
		self.yScaleFactor = (yHeight-2.0) / dataHeight
		self.xScaleFactor = ((xWidth-2.0) / self.totalXPoints)

		if not startFreqOverride:
			curSt = self.currentStart
		else:
			curSt = startFreqOverride

		self.xOffset = int((curSt-self.startFreq)/self.binSize)

	def mapYValueToContext(self, value):


		value = ((value-self.minVal) * self.yScaleFactor) + 1
		return value

	def mapXValueToContext(self, value):
		#print("X = ", value, "offset", self.xOffset, "xScale", self.xScaleFactor)
		value = ((value + self.xOffset) * self.xScaleFactor ) + 1
		return value

	def drawMouse(self):
		xPos, yPos = self.ScreenToClient(wx.GetMousePosition())

		dc = self.mouseDc
		w, h = dc.GetSize()
		if not (0 <= xPos < w and 0 <= yPos < h):
			# Mouse is not on the canvas, ignore
			return

		if self.data == None:
			return

		if not self.data:
			return

		self.dataWidth = self.data[self.currentStart].shape[0]
		if self.dataWidth == 0:
			return

		dc.SetPen(self._penPastelGreen)
		dc.DrawLine(xPos, 0, xPos, h)


		dc.SetTextForeground(self._colourWhite)

		perStep = float(w)/self.totalXPoints
		rangeStart, rangeStop = int(xPos/perStep-self.xOffset), int((xPos+1)/perStep-self.xOffset)
		if rangeStart >= 0 and rangeStop < self.data[self.currentStart].shape[0]:

			points = self.data[self.currentStart][rangeStart:rangeStop]

			self.preCalcScalingFactor(dc)

			dc.SetBrush(self._brushClear)

			dc.SetPen(self._penHeavyRed)
			scaledData = self.mapYValueToContext(points)
			for point in scaledData:
				dc.DrawCircle(xPos, h-point, 5)

			mouseText2 = "Min = %0.1f, Max = %0.1f, Mean = %0.1f" % (np.min(points), np.max(points), np.mean(points))





			dc.DrawText(mouseText2, (w/4.5), h - 20)

			numPointsAtFreq = scaledData.shape[0]
		else:
			numPointsAtFreq = 0

		cursorFreqStart, cursorFreqStop = (rangeStart*self.binSize+self.currentStart)/1000000, (rangeStop*self.binSize+self.currentStart)/1000000

		mouseText1 = "Cursor: %0.3f - %0.3f MHz. Data Points %i" % (cursorFreqStart, cursorFreqStop, numPointsAtFreq)
		dc.DrawText(mouseText1, (w/4.5), h - 40)


	def drawGraticule(self, dc):

		gridList, self.xDivisionQuantity = self.generateGridList()
		dc.DrawLineList(gridList, pens=self._penPastelBlue)


	def drawData(self, dc, data, linePen=None):

		w, dummy_h = dc.GetSize()

		# print "Meh",  self.data[self.currentStart].shape
		# print self.data[self.currentStart].shape
		dataLen = data.shape[0]

		dataMin = data.min()
		dataMax = data.max()

		if dataMin < self.minVal:
			self.minVal = (dataMin-5.0) + (5-(dataMin % 5))

		if dataMax > self.maxVal:
			self.maxVal = (dataMax+5.0) - (dataMax % 5)

		self.dataWidth = data.shape[0]


		# print scaleFactor, self.minVal, self.maxVal, dataHeight


		dataX = np.linspace(1, w-1, num=self.totalXPoints)

		scaledData = self.mapYValueToContext(data)

		# pointList = self.generateScatterList(dataX, scaledData, dataLen, dc.GetSize())
		# pointList.sort()
		# dc.DrawPointList(pointList, self._penWhite)




		pointList = self.generateScatterList(dataX, scaledData, dataLen)
		# pointList.sort()

		if not linePen:
			dc.SetPen(self._penWhite)
		else:
			dc.SetPen(linePen)

		dc.DrawLines(pointList)

	def redraw(self):
		# do the actual drawing on the memory dc here
		if not self.stale:
			# print("Not drawing as plot is not stale")
			return
		if self.data == None:
			return

		self.stale = False
		dc = self.mdc

		dc.SetFont(self._baseFont)

		w, h = dc.GetSize()
		dc.Clear()
		dc.SetPen(self._penBlack)


		dc.SetBrush(self._brushBlack)
		dc.DrawRectangle(0, 0, w, h)

		dc.SetTextForeground(self._colourWhite)
		#print arr
		#print self.rectDims

		if self.data and self.data[self.currentStart].shape != (0,):

			self.drawGraticule(dc)

			for key, data in self.data.iteritems():
				if key != self.currentStart:

					self.preCalcScalingFactor(dc, startFreqOverride=key)
					self.drawData(dc, data, linePen=self._penGrey)



			self.preCalcScalingFactor(dc)
			self.drawData(dc, self.data[self.currentStart])


			dc.DrawText("Max: %0.5fdB" % self.maxVal, 10, 5)
			dc.DrawText("Min: %0.5fdB" % self.minVal, 10, h - 20)

			dc.DrawText("Pk-Pk: %0.8fdB" % (self.maxVal-self.minVal), w-170, 5)
			dc.DrawText("Y-Grid: %0.2fdB per div" % GRAPH_GRID_Y_STEP, w-170, h - 20)

			self.drawPlotLabels()


	def drawPlotLabels(self):
		dc = self.mdc
		w, h = dc.GetSize()

		if all((self.startFreq, self.stopFreq)):

			strtText = "Start: %0.3f MHz" % ((self.startFreq)/1000000)
			stopText = "Stop: %0.3f MHz" % ((self.stopFreq)/1000000)
			spanText = "Span: %0.3f MHz" % ((self.stopFreq-self.startFreq)/1000000)
			strtTextX, dummy_textY = dc.GetTextExtent(strtText)
			stopTextX, dummy_textY = dc.GetTextExtent(stopText)
			spanTextX, dummy_textY = dc.GetTextExtent(spanText)
			dc.DrawText(strtText, (w/4)-(strtTextX/2), 5)
			dc.DrawText(stopText, ((w/4)*3)-(stopTextX/2), 5)
			dc.DrawText(spanText, (w/2)-(spanTextX/2), 5)

			dc.DrawText("X-Grid: %0.3f kHz per div" % (((self.stopFreq-self.startFreq) / self.xDivisionQuantity)/1000), w-400, h-20)


			dc.SetBrush(self._brushClear)
			dc.SetPen(self._penPastelRed)

			dataOffset = np.mean(self.data[self.currentStart])

			dataRms = np.sqrt(np.mean((self.data[self.currentStart]-dataOffset)**2))



			maxtab, dummy_mintab = peakFind.peakdet(self.data[self.currentStart], dataRms*self.peakSensitivityModifier)

			dc.SetFont(self._pointFont)
			for x, y in maxtab:

				pointText = " %0.3f Mhz,  %0.1f dB" % ((x*self.binSize+self.currentStart)/1000000, (y))

				x = self.mapXValueToContext(x)
				y = self.mapYValueToContext(y)
				circX, circY = x, h-y
				dc.DrawCircle(circX, circY, 5)


				labelX, labelY = dc.GetTextExtent(pointText)

				dc.DrawRotatedText(pointText, circX-(labelY/2), circY-8, 90)





	def draw_plot(self):

		self.redraw()
		self.Refresh()



	def on_redraw_timer(self, dummy_event):
		self.draw_plot()

	def on_exit(self, dummy_event):
		print "trying to die"
		self.Destroy()


