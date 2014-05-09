
import threading

import queVars
import time
import sys
import sockThread


def run():


	import GUI

	queVars.sokThread = threading.Thread(target = sockThread.startApiClient, name = "SocketThread")
	queVars.sokThread.start()

	mainWin = GUI.MyApp(0)
	mainWin.MainLoop()


if __name__ == "__main__":

	run()