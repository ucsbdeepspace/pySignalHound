
import threading

import queVars
import time
import sys
import sockThread

from pycallgraph import PyCallGraph
from pycallgraph.output import GraphvizOutput

def threadRun():

	# with PyCallGraph(output=GraphvizOutput()):
	sockThread.startApiClient()

def run():


	import GUI

	queVars.sokThread = threading.Thread(target = threadRun, name = "SocketThread")
	queVars.sokThread.start()

	mainWin = GUI.MyApp(0)
	mainWin.MainLoop()


if __name__ == "__main__":
	# with PyCallGraph(output=GraphvizOutput()):
	run()