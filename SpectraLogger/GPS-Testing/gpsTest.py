

import sys
import h5py
import cPickle as pik
import simplekml


def openFile(filePath):
	f = h5py.File(filePath)

	return f

def go(h5file):
	print("Processing h5 file %s" % h5file)



	dat = openFile(h5file)
	print dat
	print dat.keys()
	print dat["Spectrum_Data"]
	print dat["Spectrum_Data"].shape
	print dat["Acq_info"]
	print dat["Acq_info"].shape

	points = []

	for row in dat["Acq_info"]:
		time, dataDict = pik.loads(row)

		if "gps-info" in dataDict:
			gpsDict = dataDict["gps-info"]
			if gpsDict['latitude'] and gpsDict['longitude']:
				points.append((gpsDict['longitude'], gpsDict['latitude']))

	if points:
		print(points)

	kml = simplekml.Kml()
	kml.newlinestring(name="path", coords=points)
	kml.save(h5file+".kml")


if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("ERROR: You must pass a h5 file as a command line parameter")
		print("ex: 'python script.py {hdf5 file}'")
		sys.exit(1)

	h5file = sys.argv[1]
	go(h5file)
