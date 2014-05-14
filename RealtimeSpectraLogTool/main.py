
import threading

import queVars
import time
import sys
import sockThread

# from pycallgraph import PyCallGraph
# from pycallgraph.output import GraphvizOutput

def threadRun():

	# with PyCallGraph(output=GraphvizOutput()):
	sockThread.startApiClient()

def run():

	if len(sys.argv) > 1:
		print("Using IP from command line for remote server")
		print("Server IP = %s" % sys.argv[1])
		sockThread.HOST = sys.argv[1]
	else:
		print("Remote server IP can be specified as a command line parameter - ")
		print("E.g. 'python main.py {ip address}'")
		print("Using default server address (localhost)")

	import GUI

	queVars.sokThread = threading.Thread(target = threadRun, name = "SocketThread")
	queVars.sokThread.start()

	mainWin = GUI.MyApp(0)
	mainWin.MainLoop()


if __name__ == "__main__":
	# with PyCallGraph(output=GraphvizOutput()):
	run()