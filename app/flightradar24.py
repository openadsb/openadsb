# try to use the data stream from flightradar24.com
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
# parts of this borrowed from https://www.assembla.com/code/saintamh/subversion/nodes/azimuth/py/flightradar24.py?rev=2304

# we can import the following when we don't have them from ADSB: flightnum, actype, acreg, radar, origin, dest, if the ts is within some small number

# here's more supported stuff from fr24.com:
# http://www.flightradar24.com/FlightDataService.php?callsign=WZZ1MF&hex=47340F  (seem to need both callsign and hex)
# http://www.flightradar24.com/FlightDataService.php?callsign=%20&hex=AA7F5E
#  http://www.flightradar24.com/data/airplanes/A7-HHM
# and these:
# http://www.planespotters.net/search.php?q=A7-HHM
# http://www.planepictures.net/netsearch4.cgi?srch=A7-HHM&srng=2&stype=reg
# http://www.jetphotos.net/showphotos.php?regsearch=A7-HHM
# http://www.airliners.net/search/photo.search?regsearch=A7-HHM
# http://www.flightradar24.com/data/_ajaxcalls/autocomplete_airplanes.php?typing=AA7F5E

import sys
import json
import urllib
import urlparse
import mmap
import httplib
import time, os, stat
import csv
from PyQt4.QtCore import *

# class for converting IATA airport codes
#  Using data file from http://www.codediesel.com/data/international-airport-codes-download/
#  by Sameer Borate, metapix[at]gmail.com
class airportCodes():
	def __init__(self):
		self.codes = dict()
		with open('airport-codes.csv', 'r') as csvfile:
			self.reader = csv.reader(csvfile)
			for row in self.reader:
				(airport, code) = row
				self.codes[code.upper().strip()] = airport.strip()

	def lookup(self, code):
		if code == '':
			return ''
		try:
			return self.codes[code.upper()]
		except:
			return ''

# class representing one flight
class flight():
	def __init__(self):
		self.callsign = ""
		self.aa = ""
		self.lat = ""
		self.lon = ""
		self.heading = ""
		self.alt_f = ""
		self.speed_kts = ""
		self.radar = ""
		self.feed = ""
		self.actype = ""
		self.acreg = ""
		self.ts = ""
		self.origin = ""
		self.destination = ""
		self.flightnum = ""
		self.originVerbose = "?"
		self.destinationVerbose = "?"

	def printInfo(self):
		age = time.time() - int(self.ts)
		print "Callsign: %s, ICAO24 %s, lat = %s, lon = %s, heading = %s, alt = %s, speed = %s, radar = %s, feed = %s, actype = %s, acreg = %s, ts = %s, age = %d, flightnum = %s, from %s (%s) to %s (%s)" %  \
			(self.callsign, self.aa, self.lat, self.lon, self.heading, self.alt_f, self.speed_kts, self.radar, self.feed, self.actype, self.acreg, self.ts, age, self.flightnum, self.origin, self.originVerbose, self.destination, self.destinationVerbose)

# interface to flightradar24.com
class fr24(QObject):
	def __init__(self):
		self.flights = dict()
		self.filename = 'full_all.json'
		self.airports = airportCodes()
		self.dumpFilename = 'fr24reg_dump.txt'
		
	def lookupFlight(self, aa):
		try:
			f = self.flights[aa]
			#print "Found a flight matching AA = ",aa
			if f.origin != '':
				f.originVerbose = self.airports.lookup(f.origin)
			if f.destination != '':
				f.destinationVerbose = self.airports.lookup(f.destination)
			#f.printInfo()
			return f
		except:
			#print "FR24: Did not find flight with AA = ", aa
			return None

	def getfile(self):
		h = httplib.HTTPConnection('www.flightradar24.com')
		h.request('GET', '/zones/full_all.json')
		r = h.getresponse()
		rh = r.getheaders()
		rr = r.read()
		f = open(self.filename, 'w')
		f.write(rr)
		f.close()

	def decode(self):
		# read from file
		jsonfile = open('full_all.json', 'r')
		map = mmap.mmap(jsonfile.fileno(), 0, mmap.MAP_PRIVATE)
		str = map[0:]
		json_struct = json.loads(str)

		# "UAE747": [    // "callsign": ICAO (not IATA!) ID, plus flight number
		#     "896015",  // 0: "hex" (?)
		#     35.9888,   // 1: lat
		#     17.8126,   // 2: lng
		#     "279",     // 3: aircraft_track (degrees, 0 is north, going clockwise)
		#     "37975",   // 4: altitude (feet)
		#     "426",     // 5: speek (knots)
		#     "",        // 6: squawk
		#     "LMML",    // 7: "radar" (some code for ID on a radar?)
		#     "A332",    // 8: aircraft_type
		#     "A6-EKQ",  // 9: aircraft registration
		#     1327921638 // 10: looks like a timestamp
		#     ],

		# fixme - add mutex here so other threads don't lookup while building new index

		lines = 0
		success = 0
		self.flights = {}
		for callsign, s in json_struct.iteritems():
			lines += 1
			try:
				f = flight()
				f.callsign = callsign
				f.aa = s[0]
				f.lat = s[1]
				f.lon = s[2]
				f.heading = s[3]
				f.alt_f = s[4]
				f.speed_kts = s[5]
				f.radar = s[6]
				f.feed = s[7]
				f.actype = s[8]
				f.acreg = s[9]
				f.ts = s[10]
				f.origin = s[11]
				f.destination = s[12]
				f.flightnum = s[13]
				self.flights[f.aa] = f
				success += 1

			except:
				pass

		print "processed %d lines, %d failures" % (lines, lines-success)
		return

	# dump a list of ICAO24 codes, tail number, equipment type, and callsign to file 
	# for later scraping
	def dumpRegInfo(self):
		f = open(self.dumpFilename, "w") 
		for aa in self.flights.keys():
			fl = self.flights[aa]
			str = '%s, %s, %s, %s\n' % (fl.aa, fl.acreg, fl.actype, fl.callsign)
			f.write(str)
		f.close()

	@staticmethod
	def file_age_in_seconds(pathname):
		try:
			ftime = os.stat(pathname)[stat.ST_MTIME]
		except:
			return 1e9	# hack
		return time.time() - ftime

# long-running thread to handle lookups
class fr24Thread(QThread):
	def __init__(self):
		QThread.__init__(self)
		self.setObjectName("FR24 Thread")
		self.fr24 = None
		#self.fr24 = fr24()
		# This object exists in caller's thread context.  Move it to our thread content so signal/slots work
		#self.fr24.moveToThread(self)	
		self.start()

	def updateIfNecessary(self):
		# download new file if older than 10 minutes
		age = self.fr24.file_age_in_seconds(self.fr24.filename)
		if age > 600:
			print "FR24 data file is old (%f minutes).  Retrieving new one" % (age/60.0)
			self.fr24.getfile()
		#else:
			#print "data file is new enough (%f seconds)." % age

	def run(self):
		self.fr24 = fr24()
		self.updateIfNecessary()
		self.fr24.decode()
		self.exec_()				# run the event loop
		print "FR24 thread exiting"
	
	def shutdown(self):
		print "shutting down FR24 thread"

	# slot which listens for new aircraft being detected
	# perform lookup and emit signal with database info
	def addAircraft(self, ac):
		aa = "%X" % ac.aa
		#print "FR24 addAircraft: aa =", aa
		# fixme - call updateIfNecessary and decode()
		if self.fr24 == None:
			return

		f = self.fr24.lookupFlight(aa)
		if f != None:
			self.emit(SIGNAL("updateAircraftFR24Info(PyQt_PyObject)"), f)


if __name__ == '__main__':
	f = fr24()
	age = f.file_age_in_seconds(f.filename)
	print type(age)
	if age > 600:
		print "data file is old (%f minutes).  Retrieving new one" % (age/60.0)
		f.getfile()
	else:
		print "data file is new enough (%f seconds)." % age
	f.decode()
	f.dumpRegInfo()
	if len(sys.argv) == 2:
		fl = f.lookupFlight(sys.argv[1])
		if fl != None:
			fl.printInfo()

