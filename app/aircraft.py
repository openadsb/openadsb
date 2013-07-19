# This class represents a single aircraft, and all the data known about it
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
import time
from PyQt4.QtCore import *
from PyQt4.QtGui import *

#Aircraft = {
#	aa, 'icao24 address',
#	last_time, 'last seen',
#	id, 'textual aircraft identifier',
#	category, 'aircraft size category',
#	vstatus, 'airborne or on ground',
#	heading, 'magnetic or true??',
#	position, 'lat, lon',
#	alt, 'altitude',
#	alt_type, 'barometric or gps',
#	rate, 'vertical rate',
#	uncertainty, 'position uncertainty',
#	speed, 'air or ground speed',
#	squawk, 'mode c code',
#	movement, 'speed?'
#	
#	country = 'country of registration'
#	mfg, 'manufacturer',
#	model, 'model',
#	type, 'aircrafy type', 
#	i_t, 'type ICAO 8643
#	built, 'build date',
#	owner, 'registered owner',
#	owner_addr, 'address',
#	registration, 'registration number (tail number)'
#
#	acas, 'ACAS capability and status',
#	downlink_fmts, 'sent these downlink packet formats'
#	//flight number?
#	//origination
#	//destination
#	
#	//max speed,
#
#}

class Aircraft(QObject):
	def __init__(self, decoder, aa):
		QObject.__init__(self, parent = None)
		self.decoder = decoder
		self.aa = aa
		self.idStr = ""
		self.caStr = ""
		self.catStr = ""
		self.posStr = ""
		#self.moveStr = ""
		self.altStr = ""
		self.posUncertStr = ""
		self.altTypeStr = ""
		self.velStr = ""
		self.vertStr = ""
		self.ccStr = ""
		self.riStr = ""
		self.fsStr = ""
		self.emergStr = ""
		self.acasStr = ""
		self.iis = 0				# interrogator identity subfield 
		self.alt = 0
		self.squawk = 0
		self.squawkStr = ""
		self.range = 0
		self.bearing = 0
		self.elev = 0
		self.elevStr = ""
		self.rangeStr = ""
		self.bearingStr = ""
		self.heading = 0
		self.headingStr = ""
		self.fakeICAO24 = False
		self.pkts = 1
		self.timestamp = time.time()
		self.countryStr = decoder.lookupCountry(aa)
		self.track = [ ]

	def __del__(self):
		pass

	def getAA(self):
		return aa
	
	def getHeadingStr(self, deg):
		d = 360.0/32
		if deg >= d and deg < 3*d:		
			str = "NNE"
		elif deg >= 3*d and deg < 5*d:
			str = "NE"
		elif deg >= 5*d and deg < 7*d:
			str = "ENE"
		elif deg >= 7*d and deg < 9*d:	
			str = "E"
		elif deg >= 9*d and deg < 11*d:
			str = "ESE"
		elif deg >= 11*d and deg < 13*d:
			str = "SE"
		elif deg >= 13*d and deg < 15*d:
			str = "SSE"
		elif deg >= 15*d and deg < 17*d:
			str = "S"
		elif deg >= 17*d and deg < 19*d:
			str = "SSW"
		elif deg >= 19*d and deg < 21*d:
			str = "SW"
		elif deg >= 21*d and deg < 23*d:
			str = "WSW"
		elif deg >= 23*d and deg < 25*d:
			str = "W"
		elif deg >= 25*d and deg < 27*d:
			str = "WNW"
		elif deg >= 27*d and deg < 29*d:
			str = "NW"
		elif deg >= 29*d and deg < 31*d:
			str = "NNW"
		elif deg >= 31*d or deg < d:
			str = "N"
		return "%.0f (%s)" % (deg, str)
	
	def formatPos(self, lat, long):
		NS = "N"
		EW = "E"
		if(lat < 0):
			NS = "S"
			lat = lat * -1.0
		if(long < 0):
			EW = "W"
			long = long * -1.0
		return "%f %s, %f %s" % (lat, NS, long, EW)

	def getTimestamp(self):
		return self.timestamp

	def setIdentityInfo(self, idStr, catStr):
		self.pkts += 1
		self.idStr = idStr
		self.catStr = catStr
		self.timestamp = time.time()

	#def setGroundPos(self, posStr, moveStr, caStr):
	def setGroundPos(self, lat, lon, velStr, caStr):
		self.pkts += 1
		self.posStr = self.formatPos(lat, lon)
		self.velStr = velStr
		self.caStr = caStr
		self.fsStr = "On Ground"
		self.vertStr = ""
		self.headingStr = ""
		self.timestamp = time.time()
		self.pos_timestamp = self.timestamp = t = time.time()
		self.track += [(lon, lat, self.alt, t)]		# fixme - alt might not be valid yet

	def setAirbornePos(self, lat, lon, alt, posUncertStr, altTypeStr, caStr):
		self.pkts += 1
		self.pos_timestamp = self.timestamp = t = time.time()
		#self.posStr = "(%f, %f)" % (lat, lon)
		self.posStr = self.formatPos(lat, lon)
		[self.range, self.bearing, self.elev ] = self.decoder.rangeAndBearingToAircraft(self.decoder.getOrigin(), [lat, lon], alt)
		self.rangeStr = ("%0.2f" % self.range)
		self.bearingStr = ("%.0f" % self.bearing)
		self.elevStr = ("%.0f" % self.elev)
		if alt != 0:
			self.alt = alt
		self.posUncertStr = posUncertStr
		self.altTypeStr = altTypeStr
		self.caStr = caStr
		self.fsStr = "Airborne"
		self.track += [(lon, lat, alt, t)]		# fixme - add heading
		#self.pt = kml.newpoint(coords=[(lon,lat,alt)], altitudemode='absolute')
		#self.pt.iconstyle = simplekml.IconStyle(heading=self.heading,icon=icon)
		#if self.idStr != "":
			#self.pt.name=self.idStr
		#else:
			#self.pt.name=("%x"%(self.aa))
		##kml.save("adsb.kml")
		
	def setAirbornePos2(self, posStr, altStr, posUncertStr, altTypeStr):
		self.pkts += 1
		if posStr != "":
			self.posStr = posStr
		if altStr != "":
			self.altStr = altStr
		self.posUncertStr = posUncertStr
		self.altTypeStr = altTypeStr
		self.fsStr = "Airborne"
		self.pos_timestamp = self.timestamp = time.time()

	def setAirborneVel(self, velStr, heading, vertStr, caStr):
		self.pkts += 1
		self.velStr = velStr
		self.heading = heading
		self.headingStr = self.getHeadingStr(heading)
		self.vertStr = vertStr
		self.fsStr = "Airborne"
		self.timestamp = time.time()
		self.vel_timestamp = self.timestamp = time.time()

	def setACASInfo(self, ccStr, alt, riStr, acasStr, vsStr):
		self.pkts += 1
		self.ccStr = ccStr
		if alt != 0:
			self.alt = alt
		if riStr != "":
			self.riStr = riStr
		if acasStr != "":
			self.acasStr = acasStr
		self.fsStr = vsStr
		self.timestamp = time.time()

	def setCommBAltitude(self, alt, iis, fsStr, drStr):
		self.pkts += 1
		if alt != 0:
			self.alt = alt
		self.iis = iis;
		self.fsStr = fsStr
		self.drStr = drStr
		self.timestamp = time.time()

	def setCommBIdent(self, squawk, fsStr, drStr):
		self.pkts += 1
		self.squawk = squawk;
		self.squawkStr = ("%04u" % squawk)
		self.fsStr = fsStr
		self.drStr = drStr
		self.timestamp = time.time()

	def setAltitude(self, iis, fsStr, alt, drStr):
		self.pkts += 1
		if alt != 0:
			self.alt = alt
		self.iis = iis
		self.fsStr = fsStr
		self.drStr = drStr
		self.timestamp = time.time()

	def setEmergStatus(self, squawk, esStr):
		self.pkts += 1
		self.squawk = squawk;
		self.squawkStr = ("%04u" % squawk)
		self.emergStr = esStr
		self.timestamp = time.time()
		
	def setFakeICAO24(self, state):
		self.fakeICAO24 = state

	def dumpTrack(self):
		if self.idStr != "":
			name=self.idStr
		else:
			name=("%x"%(self.aa))
		# track path first
		if len(self.track) > 0:
			track_meters = [ ]
			for tp in self.track:
				track_meters += [(tp[0], tp[1], feet2meters(tp[2]))]
			desc = (self.countryStr)
			# fixme - to description add: max speed, min speed, max alt, min alt, country, category, ID str, registration info, fsStr, squawk, range
			# fixme - add TimeSpan, TimeStamp
			# fixme - add Schema for custom parameters to be displayed in elevation plot
			# fixme - sort this dump by AA or ID
			ls = kml.newlinestring(name=name, coords=track_meters, altitudemode='absolute', description=desc)
			ls.linestyle = simplekml.LineStyle(color="FF0000FF", width=5)
			kml.save("adsb.kml")

		# then actual points (fixme - skip if distance from last pt is < threshold
		# fixme - new folder structure:
		#   	tracks
		#		linestring per aircraft
		#	waypoints
		#		folder per aircraft
		#			set of waypoints
		#	
		# fixme - IconStyle for each waypoint, not global
		folder = kml.newfolder(name=name)
		folder_style = simplekml.Style()
		#folder_style.liststyle.listitemtype = "radioFolder"
		folder.style = folder_style
		for tp in self.track:
			point_meters = [(tp[0], tp[1], feet2meters(tp[2]))]
			pt = folder.newpoint(name=name, coords=point_meters, altitudemode='absolute')
			pt.iconstyle = simplekml.IconStyle(heading=self.heading,icon=icon)
			#pt.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(tp[3]))	bk fixme 
			pt.description = '<![CDATA[ Altitude 8000 ft<br/> Climbing 1000 ft/min<br/> Airspeed 425 kts<br/> Heading 289 deg/min<br/> Time XXXXX ]]>'

		# fixme - add another track which is ground path (altitude mode), and use different line style

	def printInfo(self):
		#kml.newlinestring(name=("%x"%(self.aa)), coords=self.track)
		#kml.save("adsb.kml")
		age = time.time() - self.timestamp
		print "age %3u: %14s %x: %s, %s, Range: %2u km, Pos: %s (+/- %s), Alt: %6d (%s), %s, Heading: %3u, Speed: %s, Squawk: %4u, %s %s" % \
			(age, self.countryStr, self.aa, self.idStr, self.fsStr, self.range, self.posStr, self.posUncertStr, self.alt, \
			self.altTypeStr, self.vertStr, self.heading, self.velStr, self.squawk, self.catStr, self.caStr)

		
