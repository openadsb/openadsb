import csv

# class for converting ICAO airline codes documented in ICAO Document 8585
#  Using data file from http://www.flugzeuginfo.net/table_airlinecodes_airline_en.php
#  converted to CSV format
class airlineCodes():
	def __init__(self):
		self.codes = dict()
		with open('datafiles/airline-codes.csv', 'r') as csvfile:
			self.reader = csv.reader(csvfile)
			for row in self.reader:
				(iata, icao, airline, callsign, country) = row
				self.codes[icao.upper().strip()] = [ airline.strip(), country.strip(), callsign.strip() ]

	# given a three-character ICAO airline code, return a list [ airline, country, callsign ]
	def lookup(self, code):
		if code == '':
			return [ '', '', '' ]
		try:
			return self.codes[code.upper()]
		except:
			return [ '', '', '' ]

	# given a typical flight id, extract the first three alpha chars and use that as the airline code
	# fixme - some flights only use their flt number (Airtran 709 is just '709').  If we have an tail number, use that 
	# to lookup callsign.
	def lookupByFlightID(self, idStr):
		code = idStr[0:3]
		num = idStr[3:]
		if str.isalpha(code) and not str.isalpha(num[0]):
			(airline, country, callsign) = self.lookup(code)
			# append the flight number to the callsign to match what ATC uses
			callsignStr = "%s %s" % (callsign, num)
			return [ airline, country, callsignStr ]
		else:
			#print "Expected Flight ID starting with three alpha characters, followed by number!"
			return self.lookup('')


# for testing
if __name__ == '__main__':
	import sys
	c = airlineCodes()
	argc = len(sys.argv)
	if argc > 1:
		icao = sys.argv[1]
		#print c.lookup(icao)
		print c.lookupByFlightID(icao)
