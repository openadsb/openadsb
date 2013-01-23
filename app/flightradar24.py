# try to use the data stream from flightradar24.com
# parts of this borrowed from https://www.assembla.com/code/saintamh/subversion/nodes/azimuth/py/flightradar24.py?rev=2304

# we can import the following when we don't have them from ADSB: flightnum, actype, acreg, radar, origin, dest, if the ts is within some small number

import sys
import json
import urllib
import urlparse
import mmap
import httplib
import time, os, stat

def file_age_in_seconds(pathname):
    try:
	ftime = os.stat(pathname)[stat.ST_MTIME]
    except:
	return 1e9	# hack
    return time.time() - ftime

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

	def printInfo(self):
		age = time.time() - int(self.ts)
		print "Callsign: %s, ICAO24 %s, lat = %s, lon = %s, heading = %s, alt = %s, speed = %s, radar = %s, feed = %s, actype = %s, acreg = %s, ts = %s, age = %d, flightnum = %s, from %s to %s" %  \
			(self.callsign, self.aa, self.lat, self.lon, self.heading, self.alt_f, self.speed_kts, self.radar, self.feed, self.actype, self.acreg, self.ts, age, self.flightnum, self.origin, self.destination)

class fr24():
	def __init__(self):
		self.flights = dict()
		self.filename = 'full_all.json'
		
	def lookupFlight(self, aa):
		try:
			f = self.flights[aa]
			print "Found a flight matching AA = ",aa
			f.printInfo()
		except:
			print "Did not find flight with AA = ", aa

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
		#str = '{"CFG225":["3C4AA6",36.9538,-31.8911,"55","35025","525","0000","T-LPPI1","B763","D-ABUF",1357360142,"FUE","PAD","DE6225","0","0"]}'
		#j = json.loads(str)
		#print j

		# read from file
		jsonfile = open('full_all.json', 'r')
		#str = jsonfile.readlines()
		#str = jsonfile.read()
		map = mmap.mmap(jsonfile.fileno(), 0, mmap.MAP_PRIVATE)
		str = map[0:]
		#print str

		#http = SimpleHTTPClient (
			#cache_path = here (__file__, '..', 'cache', 'flightradar24'),
			#cache_requests = True,
			#courtesy_delay = 5,
		#)
#
		#fetch_html = html_fetcher (
			#http,
			#encoding = 'UTF-8',
		#)

		#json_struct = json.loads (
			#http.simple_post (
				#'http://www.flightradar24.com/PlaybackFlightsService.php',
				#'date=%s' % urllib.quote_plus (dt.strftime ('%Y-%m-%d %H:%M:%S')),
			#)
		#)
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

		# reuse structs to save memory
		#planes_by_callsign = {}	
		
		lines = 0
		success = 0
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

				#f.printInfo()

				#print "%d, Callsign: %s, ICAO24 %s, lat = %s, lon = %s, heading = %s, alt = %s, speed = %s, radar = %s, actype = %s, acreg = %s, ts = %s" % (lines, callsign, aa, lat, lon, heading, alt_f, speed_kts, radar, actype, acreg, ts)
			except:
				pass

		print "processed %d lines, %d failures" % (lines, lines-success)
		return

if __name__ == '__main__':
	f = fr24()
	age = file_age_in_seconds(f.filename)
	print type(age)
	if age > 600:
		print "data file is old (%f minutes).  Retrieving new one" % (age/60.0)
		f.getfile()
	else:
		print "data file is new enough (%f seconds)." % age
	f.decode()
	if len(sys.argv) == 2:
		f.lookupFlight(sys.argv[1])

