# These classes implement a decoder for Mode S packets
# prereqs: bitstring simplekml PyUSB 
# 	"easy_install bitstring simplekml PyUSB"
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

import sys
import bitstring 
import time, math
#import simplekml
import binascii
import aircraft

from PyQt4.QtCore import *
from PyQt4.QtGui import *


# Just a struct to hold statistics
class DecoderStats:
	def __init__(self):
		self.reset()

	def reset(self):
		self.logfileSize = 0
		self.rxLevel = 0
		self.badShortPkts = 0
		self.badLongPkts = 0
		self.totalPkts = 0
		self.DF0 = 0
		self.DF4 = 0
		self.DF5 = 0
		self.DF11 = 0
		self.DF17 = 0
		self.DF18 = 0
		self.DF20 = 0
		self.DF21 = 0
		self.DFOther = 0
		self.CrcErrs = 0
		self.goodPkts = 0	# CRC good, decoded properly
		self.uniqueAA = 0
		self.ACASonly = 0	# AAs that only send ACAS, not other ADS-B

# This class parses and decodes the ADS-B messages.
class AdsbDecoder(QObject):

	def __init__(self, args):
		QObject.__init__(self, parent = None)
		self.args = args
		self.recentAircraft = {}
		self.origin = self.args.origin
		self.stats = DecoderStats()
		#self.badShortPkts = 0
		#self.badLongPkts = 0
		#self.totalPkts = 0
		#self.rxLevel = 0

	def __del__(self):
		pass
		# delete array of recent aircraft
		#for aa in self.recentAircraft.keys():
			#del self.recentAircraft[aa]

		

	# Some statistics are maintained by the decoder, but are gleaned from the reader or elsewhere
	def updateStats(self, rxLevel, badShort, badLong, logfilesize):
		self.stats.logfileSize = int(logfilesize)
		self.stats.rxLevel = int(rxLevel)
		self.stats.badShortPkts = int(badShort)
		self.stats.badLongPkts = int(badLong)
		self.emit(SIGNAL("rxLevelChanged(int)"), self.stats.rxLevel)
		self.emit(SIGNAL("updateStats(PyQt_PyObject)"), self.stats)
		

	# Send a message to the Qt log window
	def logMsg(self, str):
		txt = QString(str)
		self.emit(SIGNAL("appendText(const QString&)"), txt)

	# the bitstring bit positions are a little strange:  bits[A:B], where B is one number greater than the ending bit position
	def decode(self, d):
		self.stats.totalPkts += 1

		# convert to a bitstring
		b = bitstring.BitArray(bytearray(d))

		df = b[0:5].uint
		if df == 0:
			self.DecodeDF0(b)
			self.stats.DF0 += 1
		elif df == 4:
			self.DecodeDF4(b)
			self.stats.DF4 += 1
		elif df == 5:
			self.DecodeDF5(b)
			self.stats.DF5 += 1
		elif df == 11:
			self.DecodeDF11(b)
			self.stats.DF11 += 1
		elif df == 17:
			self.DecodeDF17(b)
			self.stats.DF17 += 1
		elif df == 18:
			self.DecodeDF18(b)
			self.stats.DF18 += 1
		elif df == 20:
			self.DecodeDF20(b)
			self.stats.DF20 += 1
		elif df == 21:
			self.DecodeDF21(b)
			self.stats.DF21 += 1
		else:
			print "  Need decoder for DF %u: " % (df), self.ba2hex(d)
			self.stats.DFOther += 1
	
	def ba2hex(self, d):
		mystr = ""
		for byte in d:
			mystr += "%02hx " % byte
		return mystr

	def capabilitiesStr(self, ca):
		if ca == 0:
			caStr = "Level 1 transponder."
		elif ca >= 1 and ca <= 3:
			caStr = "Reserved field %u." % (ca)
		elif ca == 4:
			caStr = "Level 2 transponder. On-Ground capability."
		elif ca == 5:
			caStr = "Level 2 transponder. Airborne capability."
		elif ca == 6 or ca ==7:
			caStr = "Level 2 transponder. Airborne and on-ground capability"
		else:
			 caStr = "Unknown."
		return caStr

	def getOrigin(self):
		return self.origin

	def DecodeDF0(self, pkt):
		# Short Air-to-air surveillance
		# 56-bit packet
		df = pkt[0:5].uint
		vs = pkt[5:6].uint
		cc = pkt[6:7].uint
		sl = pkt[8:11].uint
		ri = pkt[13:17].uint
		ac = pkt[19:32]
		ap = pkt[32:56]
		[alt, altStr] = self.AltitudeCode(ac)
		if vs == 0:
			vsStr = "Airborne"
		else:
			vsStr = "On Ground"

		# fixme - these come in in sequential packets to describe both ACAS and max speed.  Fill these into two different vars
		riStr = ""
		acasStr = ""
		if ri == 0:
			acasStr = "No operating ACAS"
		if ri >= 1:
			acasStr = "Reserved"
		if ri >= 2:
			acasStr = "ACAS (resolution inhibited)"
		if ri >= 3:
			acasStr = "ACAS (vertical only)"
		if ri >= 4:
			acasStr = "ACAS (vert and horz)"
		if ri >= 5 and ri <= 7:
			acasStr = "Reserved"
		if ri == 8:
			riStr = "No Max Avail"
		if ri == 9:
			riStr = "Max <75 kts"
		if ri == 10:
			riStr = "Max 75-150 kts"
		if ri == 11:
			riStr = "Max 150-300 kts"
		if ri == 12:
			riStr = "Max 300-600 kts"
		if ri == 13:
			riStr = "Max 600-1200 kts"
		if ri == 15:
			riStr = "Max >1200 kts"
		if cc == 0:
			ccStr = "No crosslink"
		else:
			ccStr = "Crosslink supported"
		crc = self.calcParity(pkt[0:32])
		aa = crc ^ ap;	

		a = self.lookupAircraft(aa.uint)
		if (a != None):
			# AA exists in roll-call list so CRC must have been good
			crcStr = "Aircraft ID %x." % (aa.uint)
			a.setACASInfo(ccStr, alt, riStr, acasStr, vsStr)
			self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)
			self.stats.goodPkts += 1
		else:
			crcStr = "CRC error or no all-call received yet from ID %x." % (aa.uint)
			self.stats.CrcErrs += 1
		#print "  DF%u (Short ACAS Air-to-Air): %s. %s. %s. %s. %s. ap=%x. %s" % (df, vsStr, altStr, riStr, acasStr, ccStr, ap.uint, crcStr)
		self.logMsg("  DF%u (Short ACAS Air-to-Air): %s. %s. %s. %s. %s. %s" % (df, vsStr, altStr, riStr, acasStr, ccStr, crcStr))

	def DecodeDF4(self, pkt):
		# Surveillance altitude reply
		# 56-bit packet
		df = pkt[0:5].uint
		fs = pkt[5:8].uint
		dr = pkt[8:13].uint
		um = pkt[13:19]			# fixme - ?
		ac = pkt[19:32]
		ap = pkt[32:56]
		iis = um[0:4].uint
		fsStr = self.flightStatusStr(fs)
		drStr = self.downlinkReqStr(dr)
		[alt, altStr] = self.AltitudeCode(ac)
		crc = self.calcParity(pkt[0:32])
		aa = crc ^ ap;	
		a = self.lookupAircraft(aa.uint)
		if (a != None):
			# AA exists in roll-call list so CRC must have been good
			crcStr = "Aircraft ID %x." % (aa.uint)
			a.setAltitude(iis, fsStr, alt, drStr)
			self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)
			self.stats.goodPkts += 1
		else:
			crcStr = "CRC error or no all-call received yet from ID %x." % (aa.uint)
			self.stats.CrcErrs += 1
		#print "  DF%u (Altitude Roll-Call): IID=%u. %s. %s. %s. ap=%x. %s" % (df, iis, fsStr, altStr, drStr, ap.uint, crcStr)
		self.logMsg("  DF%u (Altitude Roll-Call): IID=%u. %s. %s. %s. %s" % (df, iis, fsStr, altStr, drStr, crcStr))
		
	def downlinkReqStr(self, dr):
		if dr == 0:
			drStr = "No downlink request"
		elif dr == 1:
			drStr = "Comm-B TX request"
		elif dr == 2 or dr == 3 or dr == 6 or dr == 7:
			drStr = "ACAS type %u request" % (dr)
		elif dr == 4:
			drStr = "Comm-B broadcast 1 request"
		elif dr == 5:
			drStr = "Comm-B broadcast 2 request"
		elif dr == 6:
			drStr = "Comm-B broadcast 1 and ACAS request"
		elif dr == 7:
			drStr = "Comm-B broadcast 2 and ACAS request"
		elif dr >= 16:
			drStr = "ELM protocol"
		else:
			drStr = "Unassigned DR %u" % (dr)
		return drStr

	def flightStatusStr(self, fs):
		if fs == 0:
			fsStr = "Airborne"
		elif fs == 1:
			fsStr = "On Ground"
		elif fs == 2:
			fsStr = "Alert, Airborne"
		elif fs == 3:
			fsStr = "Alert, On Ground"
		elif fs == 4:
			fsStr = "Alert, Ident"
		elif fs == 5:
			fsStr = "Ident"
		else:
			fsStr = "Reserved FS %u" % (fs)
		return fsStr

	def squawkDecode(self, b):
		# refer to section 3.1.1.6
		# fixme - test this comparing to the Mode C/A decoding table
		c1 = b[0:1]
		a1 = b[1:2]
		c2 = b[2:3]
		a2 = b[3:4]
		c4 = b[4:5]
		a4 = b[5:6]
		if b[6] != 0:
			print "Error - expected 0 for bit 6 of mode A response."
		b1 = b[7:8]
		d1 = b[8:9]
		b2 = b[9:10]
		d2 = b[10:11]
		b4 = b[11:12]
		d4 = b[12:13]
		# bitarray concatenation
		a = a4 + a2 + a1
		b = b4 + b2 + b1
		c = c4 + c2 + c1
		d = d4 + d2 + d1
		squawk = (a.uint * 1000) + (b.uint * 100) + (c.uint * 10) + d.uint
		return squawk

	# decode 6-bit encoded characters
	def decodeChars(self, c):
		set1 = [' ', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O']
		set2 = ['P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
		set3 = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

		str = ""
		while len(c) != 0:
			b_hi = c[0:2].uint
			b_lo = c[2:6].uint
			if b_hi == 0:
				if b_lo == 0:
					str += '_'	# illegal
				else:
					str += set1[b_lo]	
			elif b_hi == 1:
				if b_lo < 0xB:
					str += set2[b_lo] 
				else:
					str += '_'	# illegal
			elif b_hi == 2:
				str += ' '		# space
			elif b_hi == 3:
				if b_lo < 0xA:
					str += set3[b_lo] 
				else:
					str += '_'	# illegal
			del c[0:6]			# move to next char
		return str


	def DecodeDF5(self, pkt):
		# Surveillance identity reply
		# 56-bit packet
		df = pkt[0:5].uint
		fs = pkt[5:8].uint
		dr = pkt[8:13].uint
		um = pkt[13:19]
		id = pkt[19:32]
		ap = pkt[32:56]
		iis = um[0:4].uint
		fsStr = self.flightStatusStr(fs)
		squawk = self.squawkDecode(id)
		drStr = self.downlinkReqStr(dr)
		crc = self.calcParity(pkt[0:32])
		aa = crc ^ ap;	
		a = self.lookupAircraft(aa.uint)
		if (a != None):
			# AA exists in roll-call list so CRC must have been good
			crcStr = "Aircraft ID %x." % (aa.uint)
			a.setCommBIdent(squawk, fsStr, drStr)
			self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)
			self.stats.goodPkts += 1
		else:
			crcStr = "CRC error or no all-call received yet from ID %x." % (aa.uint)
		#print "  DF%u (Identity Reply): IID=%u. %s. Squawk %04u. %s. ap=%x. %s" % (df, iis, fsStr, squawk, drStr, ap.uint, crcStr )
		self.logMsg( "  DF%u (Identity Reply): IID=%u. %s. Squawk %04u. %s. %s" % (df, iis, fsStr, squawk, drStr, crcStr ))

	def DecodeDF11(self, pkt):
		# All-call reply
		# 56-bit packet
		df = pkt[0:5].uint
		ca = pkt[5:8].uint
		aa = pkt[8:32].uint
		pi = pkt[32:56]
		caStr = self.capabilitiesStr(ca)
		crc = self.calcParity(pkt[0:32])
		if crc == pi:
			# CRC good and AA known
			a = self.lookupAircraft(aa)
			if a == None:
				a = self.recordAircraft(aa)
			errStr = ""
			self.stats.goodPkts += 1
		else:
			errStr = "CRC error (expected %x, rx %x)." % (crc.uint, pi.uint)
		#print "  DF%u (Mode S All-Call Reply): %s Aircraft ID %03hx. %s" % (df, caStr, aa, errStr)
		self.logMsg("  DF%u (Mode S All-Call Reply): %s Aircraft ID %03hx. %s" % (df, caStr, aa, errStr))
			

	def DecodeDF17(self, pkt):
		posStr = ""
		# 112-bit packet
		# fixme - decode ca, me, lookup ICAO24
		df = pkt[0:5].uint
		ca = pkt[5:8].uint
		aa = pkt[8:32].uint
		me = pkt[32:88]
		pi = pkt[88:112]
		tc = me[0:5].uint	# type code (9 to 18 are position of various accuracies)
					# 5 to 8 are ground position
					# 0 is barometric alt only
					# 20 to 22 is position, using GPS altitude
		st = me[5:8].uint	# subtype
		crc = self.calcParity(pkt[0:88])
		caStr = self.capabilitiesStr(ca)
		if crc == pi:
			crcgood = True
		else:
			crcgood = False

		posUncertStr = ""

		tcStr = self.typeCodeStrDF17_18(tc)

		if len(pkt) < 112:
			print "short DF17 pkt"
			return

		if tc >= 1 and tc <=4:
			# Aircraft Identification String BDS0,8
			cat = me[5:8].uint
			# fixme - these decode differently for TC1,2,3
			catStr = ""
			if cat == 0:
				catStr = "A/C category unavailable"
			elif cat == 1:
				catStr = "Light weight <15K pounds"
			elif cat == 2:
				catStr = "Medium weight <75K pounds"
			elif cat == 3:
				catStr = "Medium weight <300K pounds"
			elif cat == 4:
				catStr = "Strong vortex aircraft"
			elif cat == 5:
				catStr = "Heavy weight >300K pounds"
			elif cat == 6:
				catStr = "High performance, high speed"
			elif cat == 7:
				catStr = "Rotorcraft"
			else:
				catStr = "Category %u" % (cat)
			id = self.decodeChars(me[8:56])
			if crcgood:
				a = self.lookupAircraft(aa)
				if a == None:
					a = self.recordAircraft(aa)
				a.setIdentityInfo(id, catStr)
				#print "  Aircraft identifier: %s, %s" % (id, catStr)
				self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)
			
		elif tc >=5 and tc <=8:
			# Surface position BDS0,6
			movement = me[5:12].uint
			gtv = me[12:13].uint
			track = me[13:20].uint
			timesync = me[20:21].uint
			oddeven = me[21:22].uint
			cprlat = me[22:39].uint
			cprlong = me[39:56].uint
			[lat, lon] = self.decodeCPR(cprlong, cprlat, 17, 90, oddeven)
			posStr = " at (%f, %f)" % (lat, lon)
			moveStr = self.decodeMovement(movement)
			#print "  DF17: %hx %hx tc=%u odd=%u timesync=%u cprlat=%u, cprlon=%u mvmt=%u (%s), pos %s:" % (ca, aa, tc, oddeven, timesync, cprlat, cprlong, movement, moveStr, posStr)
			self.logMsg("  DF17: %hx %hx tc=%u odd=%u timesync=%u cprlat=%u, cprlon=%u mvmt=%u (%s)" % (ca, aa, tc, oddeven, timesync, cprlat, cprlong, movement, moveStr))
			if crcgood:
				# store aa, ONGROUND, posStr, moveStr
				a = self.lookupAircraft(aa)
				if a == None:
					a = self.recordAircraft(aa)
				a.setGroundPos(posStr, moveStr, caStr)
				self.emit(SIGNAL("updateAircraftPosition(PyQt_PyObject)"), a)
				# FIXME - emit updateAircraftPosition also
			
		elif tc >=9 and tc <=22 and tc != 19:	
			# Airborne position BDS0,5
			ss = me[5:7].uint		# fime decode per (A.2.3.2.6)
			ant = me[7:8].uint		# fixme (A.2.3.2.5)
			ac = me[8:20]
			#print len(me[8:15]), len(me[15:20]), len(ac)
			if tc >= 20 and tc <= 22:
				alt = ac.uint				# GPS HAE (fixme - units?)
				altStr = "%d units?" % (alt)
				altTypeStr =  "GPS HAE"
			else:
				# m bit is omitted, add it back
				ac = ac[0:6] + bitstring.BitArray(bin='0') + ac[6:12] 	
				[alt, altStr] = self.AltitudeCode(ac)	# barometric
				altTypeStr =  "barometric"
			timesync = me[20:21].uint
			oddeven = me[21:22].uint
			cprlat = me[22:39].uint
			cprlong = me[39:56].uint
			self.logMsg("  DF17: %hx %hx %s tc=%u odd=%u timesync=%u cprlat=%u, cprlon=%u" % (ca, aa, altStr, tc, oddeven, timesync, cprlat, cprlong))
			[lat, lon] = self.decodeCPR(cprlong, cprlat, 17, 360, oddeven)
			posStr = " at (%f, %f)" % (lat, lon)
			#print "  DF17: %hx %hx %s tc=%u odd=%u timesync=%u cprlat=%u, cprlon=%u, pos %s" % (ca, aa, altStr, tc, oddeven, timesync, cprlat, cprlong, posStr)
			#print pkt, crcgood
			if crcgood:
				# store aa, AIRBORNE, posStr, altStr, posUncertStr, altTypeStr
				a = self.lookupAircraft(aa)
				if a == None:
					a = self.recordAircraft(aa)
				a.setAirbornePos(lat, lon, alt, posUncertStr, altTypeStr, caStr)
				self.emit(SIGNAL("updateAircraftPosition(PyQt_PyObject)"), a)
				# FIXME - emit updateAircraftPosition also

		elif tc == 19:
			# Airborne velocity BDS0,9
			st1 = me[5:8].uint
			st2 = me[8:11].uint
			icf = me[8:9].uint
			ifr = me[9:10].uint
			nuc = me[10:13].uint
			west = me[13:14]
			vel_ew = me[14:24].uint - 1
			south = me[24:25]
			vel_ns = me[25:35].uint - 1
			baro = me[35:36]
			down = me[36:37]
			vrate = me[37:46].uint

			if st1 == 2 or st1 == 4:
				vel_ew *= 4
				vel_ns *= 4
			if west:
				vel_ew *= -1
			if south: 
				vel_ns *= -1

			vel = math.sqrt(math.pow(vel_ew, 2) + math.pow(vel_ns, 2))
			heading = math.atan2(vel_ew, vel_ns) / math.pi * 180
			if heading < 0:
				heading += 360

			if vel == 0:
				velStr = "Speed unavailable"
			elif st1 == 1 or st1 == 2:
				velStr = "Ground speed %u kts" % vel
			elif st1 == 3 or st1 == 4:
				velStr = "Airspeed %u kts" % vel
			else:
				velStr = "Reserved"
			
			if vrate == 0:
				vertStr = "Vertical rate unavailable"
			else:	
				if down:
					vrate *= -1;
				vertStr = "%d ft/min" % (vrate*64)
				if baro:
					vertStr += " (barometric)"
				else:
					vertStr += " (GPS)"

			#print "%u %u %u Heading %d deg. %s. %s." % (icf, ifr, nuc, heading, velStr, vertStr)
			if crcgood:
				# store aa, velStr, heading, vertStr
				a = self.lookupAircraft(aa)
				if a == None:
					a = self.recordAircraft(aa)
				a.setAirborneVel(velStr, heading, vertStr, caStr)
				self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)

		else:
			print "need decoder for DF%u, type %u:" % (df, tc), self.ba2hex(pkt)

		if aa == 0x555555:
			aaStr = "Anonymous"
		else:
			aaStr = "%hx" % (aa)
			
		if crcgood:
			# CRC good 
			errStr = ""
			self.stats.goodPkts += 1
		else:
			errStr = "CRC error (expected %x, rx %x)." % (crc.uint, pi.uint)
			self.stats.CrcErrs += 1
		#print "  DF%u (Extended Squitter): Aircraft ID %s%s. %s %s" % (df, aaStr, posStr, tcStr, errStr)
		self.logMsg("  DF%u (Extended Squitter): Aircraft ID %s%s. %s %s" % (df, aaStr, posStr, tcStr, errStr))
		# fixme - print velStr, vertStr here...


	def DecodeDF18(self, pkt):
		# 112-bit packet
		df = pkt[0:5].uint
		cf = pkt[5:8].uint
		aa = pkt[8:32].uint
		me = pkt[32:88]
		pi = pkt[88:112]
		tc = me[0:5].uint	# type code - same as DF17?

		aaStr = "%hx" % (aa)
		crc = self.calcParity(pkt[0:88])
		if crc == pi:
			crcgood = True
		else:
			crcgood = False
	
		tcStr = self.typeCodeStrDF17_18(tc)

		#print " DF%u (TIS-B): Aircraft ID %s. CF=%u, TC=%u %s" % (df, aaStr, cf, tc, tcStr)

		#if tc >=9 and tc <=22 and tc != 19:	
		if tc == 13:
			# TIS-B Fine Airborne Position 
			ss = me[5:7].uint
			imf = me[7:8].uint	# ICAO/Mode A flag
			if ss == 1:
				ssStr = "Emergency Alert"
			elif ss == 2:
				ssStr = "Temporary Alert"
			elif ss == 3:
				ssStr = "SPI condition"
			else:
				ssStr = ""
			ac = me[8:20]
			oddeven = me[21:22].uint
			# m bit is omitted, add it back
			ac = ac[0:6] + bitstring.BitArray(bin='0') + ac[6:12] 	
			[alt, altStr] = self.AltitudeCode(ac)	# barometric
			altTypeStr =  "barometric"
			cprlat = me[22:39].uint
			cprlong = me[39:56].uint
			[lat, lon] = self.decodeCPR(cprlong, cprlat, 17, 360, oddeven)
			posStr = " at (%f, %f)" % (lat, lon)

			if crcgood:
				# store aa, AIRBORNE, posStr, altStr, posUncertStr, altTypeStr
				# FIXME - if CF == 5, then the AA is fake (unique, but not ICAO registered)
				a = self.lookupAircraft(aa)
				if a == None:
					a = self.recordAircraft(aa)
				a.setAirbornePos(lat, lon, alt, "", altTypeStr, "")
				self.emit(SIGNAL("updateAircraftPosition(PyQt_PyObject)"), a)

			self.logMsg(" DF%u (TIS-B): Aircraft ID %s. CF=%u, IMF=%u, TC=%u, SS=%u %s, %s %s, odd=%u, %s" % \
				(df, aaStr, cf, imf, tc, ss, ssStr, altStr, altTypeStr, oddeven, posStr))
		elif tc == 19:
			# TIS-B Velocity 
			subtype = me[5:8].uint
			imf = me[8:9].uint	# ICAO/Mode A flag
			nacp = me[9:13].uint
			geo = me[35:36]
			down = me[36:37]
			vrate = me[37:46].uint
			nic = me[47:48]

			if subtype == 1 or subtype == 2:
				# ground referenced velocity
				west = me[13:14]
				vel_ew = me[14:24].uint - 1
				south = me[24:25]
				vel_ns = me[25:35].uint - 1
				if subtype == 2:
					vel_ew *= 4		
					vel_ns *= 4
				if west:
					vel_ew *= -1
				if south: 
					vel_ns *= -1

				vel = math.sqrt(math.pow(vel_ew, 2) + math.pow(vel_ns, 2))
				heading = math.atan2(vel_ew, vel_ns) / math.pi * 180
				if heading < 0:
					heading += 360
				headingStr = "%u deg True" % heading

			elif subtype == 2 or subtype == 4:
				# air referenced velocity
				heading_valid = me[13:14]
				heading = me[14:24].uint
				heading = 360.0 * heading / 1024	#units of 360/1024
				if heading_valid == False:
					heading = 0
				mag_heading = me[54:55]
				if mag_heading:
					headingStr = "%u deg Magnetic" % heading
				else:
					headingStr = "%u deg True" % heading
				vel = me[25:35].uint - 1
				if subtype == 4:
					vel *= 4

			if vel == 0:
				velStr = "Speed unavailable"
			elif subtype == 3 or subtype == 4:
				velStr = "Airspeed %u kts" % vel
			else:
				velStr = "Ground speed %u kts" % vel
			
			if vrate == 0:
				vertStr = "Vertical rate unavailable"
			else:	
				if down:
					vrate *= -1;
				vertStr = "%d ft/min" % (vrate*64)

			if crcgood:
				# store aa, velStr, heading, vertStr
				a = self.lookupAircraft(aa)
				if a == None:
					a = self.recordAircraft(aa)
				caStr = ""
				a.setAirborneVel(velStr, heading, vertStr, caStr)
				self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)

			accStr = self.decodeNavAccuracy(nacp)
			self.logMsg( " DF%u (TIS-B): Aircraft ID %s. CF=%u, IMF=%u, TC=%u, NACP=%u %s, %s, %s, heading: %s" % \
				(df, aaStr, cf, imf, tc, nacp, accStr, velStr, vertStr, headingStr))

		else:
			self.logMsg(" DF%u (TIS-B): Aircraft ID %s. CF=%u, TC=%u" % (df, aaStr, cf, tc))
			print "Need decoder for DF18, CF %u, type %u:" % (cf, tc), self.ba2hex(pkt)
			
			
	# these are used for DF17, DF18
	def typeCodeStrDF17_18(self, tc):
		if tc == 0:
			tcStr = "No position info."
		elif tc == 1:
			tcStr = "Identification (set D)."
		elif tc == 2:
			tcStr = "Identification (set C)."
		elif tc == 3:
			tcStr = "Identification (set B)."
		elif tc == 4:
			tcStr = "Identification (set A)."
		elif tc == 5:
			tcStr = "Surface position within 3m."
			posUncertStr = "3m"
		elif tc == 6:
			tcStr = "Surface position within 10m."
			posUncertStr = "10m"
		elif tc == 7:
			tcStr = "Surface position within 100m."
			posUncertStr = "100m"
		elif tc == 8:
			tcStr = "Surface position within >100m."
			posUncertStr = ">100m"
		elif tc == 9:
			tcStr = "Airborne position within 3m. Barometric altitude."
		elif tc == 10:
			tcStr = "Airborne position within 10m. Barometric altitude."
		elif tc == 11:
			tcStr = "Airborne position within 100m. Barometric altitude."
		elif tc == 12:
			tcStr = "Airborne position within 200m. Barometric altitude."
			posUncertStr = ">100m"
		elif tc == 13:
			tcStr = "Airborne position within 500m. Barometric altitude."
		elif tc == 14:
			tcStr = "Airborne position within 1km. Barometric altitude."
		elif tc == 15:
			tcStr = "Airborne position within 2km. Barometric altitude."
		elif tc == 16:
			tcStr = "Airborne position within 10km. Barometric altitude."
		elif tc == 17:
			tcStr = "Airborne position within 20km. Barometric altitude."
		elif tc == 18:
			tcStr = "Airborne position within >20km. Barometric altitude."
		elif tc == 19:
			tcStr = "Airborne velocity. Delta altitude."
		elif tc == 20:
			tcStr = "Airborne position within 4m. GPS altitude."
		elif tc == 21:
			tcStr = "Airborne position within 15m. GPS altitude."
		elif tc == 22:
			tcStr = "Airborne position within >15m. GPS altitude."
		elif tc == 23:
			tcStr = "Reserved for test purposes."
		elif tc == 24:
			tcStr = "Reserved for surface system status."
		elif (tc >= 25 and tc <=27) or tc == 30:
			tcStr = "Reserved type %u." % (tc)
		elif tc == 28:
			tcStr = "Emergency/priority status."
		elif tc == 29:
			tcStr = "Target state and status."
		elif tc == 31:
			tcStr = "Aircraft operational status."
		return tcStr

	# used for TIS-B NACp decoding.  Maybe others
	def decodeNavAccuracy(self, p):
		if p == 0:
			s = "accuracy unknown"
		elif p == 1:
			s = "within 20km"
		elif p == 2:
			s = "within 10km"
		elif p == 3:
			s = "within 5km"
		elif p == 4:
			s = "within 2km"
		elif p == 5:
			s = "within 1km"
		elif p == 6:
			s = "within 500m"
		elif p == 7:
			s = "within 200m"
		elif p == 8:
			s = "within 100m"
		elif p == 9:
			s = "within 30m"
		elif p == 10:
			s = "within 10m"
		elif p == 11:
			s = "within 3m"
		else:
			s = "reserved"
		return s
		
	def decodeMovement(self, m):
		# refer to A.2.3.3.1
		if m == 0:
			str = "Ground speed unavailable"
		elif m == 1:
			str = "Aircraft stopped"
		elif m >= 2 and m <= 8:
			str = "Ground speed %f kts" % ((m-2)*0.125 + 0.125)
		elif m >= 9 and m <= 12:
			str = "Ground speed %f kts" % ((m-9)*0.25 + 1.0)
		elif m >= 13 and m <= 38:
			str = "Ground speed %f kts" % ((m-13)*0.5 + 2.0)
		elif m >= 39 and m <= 93:
			str = "Ground speed %f kts" % ((m-39)*1.0 + 15.0)
		elif m >= 94 and m <= 108:
			str = "Ground speed %f kts" % ((m-94)*2.0 + 70.0)
		elif m >= 109 and m <= 123:
			str = "Ground speed %f kts" % ((m-109)*5.0 + 100.0)
		elif m == 124:
			str = "Ground speed > 175 kts"
		else:
			str = "Ground speed reserved field"
		return str

	# compact position record decoding
	# Nb = 17 for airborne, 14 for intent, and 12 for TIS-B
	# odd is True for odd packet, False for even
	# range is 360.0 deg for airborne format, 90.0 deg for surface format
	# fixme - the ODD packet seems to decode incorrectly... I think fixed.  No, still problem for some A/C
	def decodeCPR(self, xz, yz, nbits, _range, odd):
		# refer to C.2.6.5 and C.2.6.6
		nz = 15		# number of latitude zones (fixed)
		yz = float(yz)	# make sure treated as floating point
		xz = float(xz)	# make sure treated as floating point
		_range = float(_range)	# must be floating point

		# our 'reference position' within 300 miles of airborne a/c or 45 miles on ground
		[lats, lons] = self.origin

		if odd:
			i = float(1)
		else:
			i = float(0)
		# first latitude
		dlat = _range / (4 * nz - i)
		j = math.floor(lats / dlat) + math.floor(0.5 + (self.mod(lats, dlat, _range)/dlat) - (yz/2**nbits))
		rlat = dlat * (j + yz/2**nbits)
		# then longitude
		if self.NL(rlat, nz)-i > 0:
			dlon = _range / (self.NL(rlat, nz)-i)
		else:	
			dlon = _range
		m = math.floor(lons / dlon) + math.floor(0.5 + (self.mod(lons, dlon, _range)/dlon) - (xz/2**nbits))
		rlon = dlon * (m + xz/2**nbits)
		return [rlat, rlon]

	def mod(self, a, b, _range):
		if a < 0:
			a += _range
		m = a - b * math.floor(a / b)
		#print "a, b, m = ", a, b, m
		return m

	# NL - compute number of "longitude zones"
	# refer to C.2.6.2
	def NL(self, lat, nz):
		nl = math.floor (2.0 * math.pi * pow(math.acos( 1.0 - ((1.0 - math.cos(math.pi/2.0/nz)) / pow(math.cos(math.pi/180.0*abs(lat)), 2.0))), -1))
		#print "NL=", nl
		return nl;

	def DecodeDF20(self, pkt):
		# 112-bit packet
		if len(pkt) < 112:
			print "short DF20 packet"
			return
		df = pkt[0:5].uint
		fs = pkt[5:8].uint
		dr = pkt[8:13].uint
		um = pkt[13:20]
		ac = pkt[19:32]
		#mb = pkt[32:88].uint
		ap = pkt[88:112]
		iis = um[0:4].uint
		fsStr = self.flightStatusStr(fs)
		drStr = self.downlinkReqStr(dr)
		[alt, altStr] = self.AltitudeCode(ac)
		crc = self.calcParity(pkt[0:88])
		aa = crc ^ ap;	
		a = self.lookupAircraft(aa.uint)
		if (a != None):
			# AA exists in roll-call list so CRC must have been good
			crcStr = "Aircraft ID %x." % (aa.uint)
			a.setCommBAltitude(alt, iis, fsStr, drStr)
			self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)
			self.stats.goodPkts += 1
		else:
			crcStr = "CRC error or no all-call received yet from ID %x." % (aa.uint)
			self.stats.CrcErrs += 1
		#print "  DF%u (Comm-B Altitude Reply): IID=%u. %s. %s. %s ap=%x. %s" % (df, iis, altStr, fsStr, drStr, ap.uint, crcStr)
		self.logMsg("  DF%u (Comm-B Altitude Reply): IID=%u. %s. %s. %s. %s" % (df, iis, altStr, fsStr, drStr, crcStr))

		
	def DecodeDF21(self, pkt):
		# 112-bit packet
		df = pkt[0:5].uint
		fs = pkt[5:8].uint
		dr = pkt[8:13].uint
		um = pkt[13:20]
		id = pkt[19:32]
		#mb = pkt[32:88].uint
		ap = pkt[88:112]
		iis = um[0:4].uint
		fsStr = self.flightStatusStr(fs)
		drStr = self.downlinkReqStr(dr)
		squawk = self.squawkDecode(id)
		if len(pkt) < 112:
			print "Short DF21 packet"
			return
		crc = self.calcParity(pkt[0:88])
		aa = crc ^ ap;	
		a = self.lookupAircraft(aa.uint)
		if (a != None):
			# AA exists in roll-call list so CRC must have been good
			crcStr = "Aircraft ID %x." % (aa.uint)
			a.setCommBIdent(squawk, fsStr, drStr)
			self.emit(SIGNAL("updateAircraft(PyQt_PyObject)"), a)
			self.stats.goodPkts += 1
		else:
			crcStr = "CRC error or no all-call received yet from ID %x." % (aa.uint)
			self.stats.CrcErrs += 1
		#print "  DF%u (Comm-B Identity Reply): IID=%u. Squawk %04u. %s. %s %s" % (df, iis, squawk, fsStr, drStr, crcStr)
		self.logMsg("  DF%u (Comm-B Identity Reply): IID=%u. Squawk %04u. %s. %s %s" % (df, iis, squawk, fsStr, drStr, crcStr))

		
	def AltitudeCode(self, ac):
		# Refer to section 3.1.2.6.5.4
		# The bit number in the ICAO annex assume this ac covers bit positions 20-32
		if len(ac) != 13:
			print "Bad length %u for AltitudeCode!" % (len(ac))
			return [-1, "Bad Altitude Code" ];
		if ac.uint == 0:
			#print "altitude not available"
			return [-1, "Altitude not available" ];
		alt = 0
		m = ac[26-20]		# feet(0) or meters(1)
		q = ac[28-20]		
		#print "AltitudeCode: m=%u, q=%u, ac=%s" % (m, q, ac.bin)	
		if m:
			ustr = "m"
			conv = 3.2808399;	# feet per meter
		else:
			ustr = "ft"
			conv = 1.0;
			if q:
				units = 25
			else:
				units = 100
		if m == 1:
			# altitude in meters
			alt = (ac[20-20:26-20] + ac[27-20:32-20]).uint
			#print "meters altitude encoding. alt = %u" % (alt)
			conv = 3.2808399;	# feet per meter
			return [alt*conv, "%d m (%d ft)" % (alt, alt*conv)]
		elif q == 0:
			# m = 0, q = 0
			# mode c encoding - gillham code
			#print "mode c altitude encoding"
			c1 = ac[20-20]
			a1 = ac[21-20]
			c2 = ac[22-20]
			a2 = ac[23-20]
			c4 = ac[24-20]
			a4 = ac[25-20]
			x  = ac[26-20]
			b1 = ac[27-20]
			d1 = 0
			b2 = ac[29-20]
			d2 = ac[30-20]
			b4 = ac[31-20]
			d4 = ac[32-20]
			#print (d1, d2, d4, a1, a2, a4, b1, b2, b4, c1, c2, c4)
			code = bitstring.BitArray([d2, d4, a1, a2, a4, b1, b2, b4, c1, c2, c4])
			alt = self.modeCtoAltitude(code.uint)
			return [alt, "%d ft (mode c encoding)" % (alt)]
		else:
			# m = 0, q = 1
			# feet
			# 11-bit field represented by bits 20 to 25, 27 and 29 to 32 
			n = ac[20-20:26-20] + ac[27-20:28-20] + ac[29-20:33-20]
			alt = 25*n.uint - 1000;
			return [alt*conv, "%d ft (direct encoding)" % (alt)]

	# these three from Ron Silvernail http://control.com/thread/1011798010	
	def grayToBinary(self, g):
		b = g ^ (g>>8)
		b ^= (b>>4)
		b ^= (b>>2)
		b ^= (b>>1)
		return b

	def getParity(self, v):
		v ^= (v>>16)
		v ^= (v>>8)
		v ^= (v>>4)
		v &= 0xf
		return (0x6996>>v) & 1;

	# takes a uint
	def modeCtoAltitude(self, code):
		c = self.grayToBinary(code & 0x7) - 1
		if(c == 6):
			c = 4
		dab = code >> 3
		if(self.getParity(dab)):
			c = 4 - c
		return ((self.grayToBinary(dab)*500)-1200) + (c*100)

	def recordAircraft(self, aa):
		# The aircraft has been identified by an all-call reply
		a = aircraft.Aircraft(self, aa)
		self.recentAircraft[ aa ] =  a
		self.emit(SIGNAL("addAircraft(PyQt_PyObject)"), a)
		return a

	def oldRecordAircraft(self, aa):
		# The aircraft has been identified by an all-call reply
		self.recentAircraft[ aa ] =  time.time() 

	def lookupAircraft(self, aa):
		# return TRUE if this AA is listed in our roll-call list
		if aa in self.recentAircraft:
			return self.recentAircraft[aa]
		else:
			return None

	def oldLookupAircraft(self, aa):
		# return TRUE if this AA is listed in our roll-call list
		if aa in self.recentAircraft:
			return True;
		else:
			return False;

	def ageRecentAircraft(self):
		# remove aircraft IDs older than 5 minutes
		for aa in self.recentAircraft.keys():
			a = self.recentAircraft[aa]
			t = a.getTimestamp()
			if time.time() > (t+(2*60)):
				print "aging %x out of queue." % (aa)
				a.dumpTrack()
				self.emit(SIGNAL("delAircraft()"))
				del self.recentAircraft[aa]
				# fixme - restart iterator after deletion

	def dumpAircraftTracks(self):
		for aa in sorted(self.recentAircraft.keys()):
			a = self.recentAircraft[aa]
			if a != None:
				a.dumpTrack()
		
	def dumpAircraft(self):
		for aa in sorted(self.recentAircraft.keys()):
			a = self.recentAircraft[aa]
			if a != None:
				a.printInfo()
		
	def printRecentAircraft(self):
		str = "%u recent aircraft: " % (len(self.recentAircraft))
		for aa in sorted(self.recentAircraft.keys()):
			c = self.lookupCountry(aa)
			if c != "":
				str += "%x (%s), " % (aa, c)
			else:
				str += "%x, " % (aa)
		print str

	# refer to 3.1.2.3.3 and "EUROCONTROL - CRC Calculation for Mode-S Transponders"
	def calcParity(self, data):
		# try to speed up the calculation.  It was by far taking the most CPU time
		if(len(data) == 32):
			return self.calcParityFast32(data)
		elif(len(data) == 88):
			return self.calcParityFast88(data)
	
		# this was the original implementation which was slow
		poly = bitstring.BitArray(hex='0xFFFA0480')
		if len(data) < len(poly):
			print "error: calcParity data must be >= 32 bits long"
			return bitstring.BitArray(hex='0xFFFFFFFF') 

		for i in range(len(data)):
			if (data[0]):
				data[0:32] ^= poly[0:32]
			data <<= 1
		return data[0:24]	# return only the 24 MSBs of the result

	def calcParityFast32(self, data):
		poly = 0xFFFA0480
		data = data.uint
		for i in range(32):
			if (data & 0x80000000):
				data ^= poly
			data = (data<<1) & 0xFFFFFFFF
		# return only the 24 MSBs of the result
		return bitstring.BitArray(uint=(data>>8), length=24)

	def calcParityFast88(self, data):
		poly = 0xFFFA0480
		data0 = data[0:32].uint
		data1 = data[32:64].uint
		data2 = data[64:88].uint << 8
		for i in range(88):
			if (data0 & 0x80000000):
				data0 ^= poly
			data0 = ((data0<<1) | (data1>>31)) & 0xFFFFFFFF
			data1 = ((data1<<1) | (data2>>31)) & 0xFFFFFFFF
			data2 = ((data2<<1)) & 0xFFFFFFFF
		# return only the 24 MSBs of the result
		return bitstring.BitArray(uint=(data0>>8), length=24)

	def lookupCountry(self, aa):
		# lookup country assigment for an AA
		if aa >= 0xAE0000 and aa < 0xAF0000:
			c = "US Military"
		elif aa >= 0xA00000 and aa < 0xB00000:
			c = "USA"
		elif aa >= 0x840000 and aa < 0x880000:
			c = "Japan"
		elif aa >= 0xC00000 and aa < 0xC40000:
			c = "Canada"
		elif aa >= 0x0D0000 and aa < 0x0D8000:
			c = "Mexico"
		elif aa >= 0x100000 and aa < 0x200000:
			c = "Russian Federation"
		elif aa >= 0x300000 and aa < 0x340000:
			c = "Italy"
		elif aa >= 0x380000 and aa < 0x3c0000:
			c = "France"
		elif aa >= 0x400000 and aa < 0x440000:
			c = "United Kingdom"
		elif aa >= 0x3C0000 and aa < 0x400000:
			c = "Germany"
		elif aa >= 0x480000 and aa < 0x488000:
			c = "Netherlands"
		elif aa >= 0x490000 and aa < 0x498000:
			c = "Portugal"
		elif aa >= 0x4B0000 and aa < 0x4B8000:
			c = "Switzerland"
		elif aa >= 0x4CA000 and aa < 0x4CB000:
			c = "Ireland"
		elif aa >= 0x710000 and aa < 0x718000:
			c = "Saudi Arabia"
		elif aa >= 0x718000 and aa < 0x720000:
			c = "Korea"
		elif aa >= 0x738000 and aa < 0x740000:
			c = "Israel"
		elif aa >= 0x750000 and aa < 0x758000:
			c = "Malaysia"
		elif aa >= 0x758000 and aa < 0x760000:
			c = "Philippines"
		elif aa >= 0x768000 and aa < 0x770000:
			c = "Singapore"
		elif aa >= 0x780000 and aa < 0x7C0000:
			c = "China"
		elif aa >= 0x7C0000 and aa < 0x800000:
			c = "Australia"
		elif aa >= 0x880000 and aa < 0x888000:
			c = "Thailand"
		elif aa >= 0x896000 and aa < 0x897000:
			c = "United Arab Emirates"
		elif aa >= 0x899000 and aa < 0x899400:
			c = "Taiwan"
		elif aa >= 0xC80000 and aa < 0xC88000:
			c = "New Zealand"
		elif aa >= 0xE80000 and aa < 0xE81000:
			c = "Chile"
		else:
			c = ""		# fixme - add complete list
		return c

	# Haversine formula example in Python
	# return distance in km bewteen origin and position (not incl altitude)
	# Author: Wayne Dyck
	def rangeAndBearingToAircraft(self, origin, position, alt):
	    lat1, lon1 = origin
	    lat2, lon2 = position
	    radius = 6371 # km
	    dlat = math.radians(lat2-lat1)
	    dlon = math.radians(lon2-lon1)
	    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
		* math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
	    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
	    d = radius * c

	    # compute initial bearing
	    # http://www.movable-type.co.uk/scripts/latlong.html
	    y = math.sin(dlon) * math.cos(math.radians(lat2))
	    x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - \
		math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
	    brng = math.degrees(math.atan2(y, x))
	    if(brng < 0):		# atan2 is -180 to +180
		brng += 360.0

	    # compute elevation angle from origin
	    # FIXME - for now assume observer at sea level.
	    el = math.degrees(math.atan2(alt, d*1000.0))		# d in km
	    if(el < 0):		# atan2 is -180 to +180
		el += 360.0

	    return [ d, brng, el ]

        def feet2meters(m):
	    return m / 3.2808399 

	def testParity(self):
		# Test the parity checker
		d = bitstring.BitArray(hex='0x5D3C6614')
		pe = bitstring.BitArray(hex='0xc315d2')
		pc = calcParity(d)
		if pe != pc: 
			print "Parity check failed on %d bit input:" % (len(d)), pe, pc
		else:
			print "Parity check successful on %d bit input:" % (len(d)), pe, pc

		d = bitstring.BitArray(hex='0x8F45AC5260BDF348222A58')
		pe = bitstring.BitArray(hex='0xB98284')
		pc = calcParity(d)
		if pe != pc: 
			print "Parity check failed on %d bit input:" % (len(d)), pe, pc
		else:
			print "Parity check successful on %d bit input:" % (len(d)), pe, pc

	def testPackets(self):
		#d = (0xa8, 0x00, 0x0b, 0x0a, 0x10, 0x01, 0x00, 0x00)
		#d = (0x5d, 0xae, 0x01, 0x3f, 0x79, 0x48, 0xba, 0x00, 0x00, 0x00, 0x00, 0x00, 0x09, 0x50)
		#d = (0x20, 0x00, 0x0c, 0x80, 0x61, 0x3b, 0xa0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x09, 0x50)
		#d = (0x8d,0xa9,0xd5,0xe7,0x58,0x2d,0x6c,0x74,0x06,0xcb,0x41,0xa2,0x09,0x50)
		#d = (8d 89 90 d2 58 bf 00 ce 2f 05 5f 47 d0 25)
		#d = (0x00,0xa1,0x01,0x0e,0xb1,0x9d,0x69)
		#d = (0x8d, 0xa8, 0x23, 0x3e, 0x58, 0x1b, 0x84, 0x86, 0xcc, 0x32, 0x53, 0x6f, 0x41, 0x23)
		#d = (0x8d , 0xa6 , 0xb2 , 0x49 , 0x26 , 0x51 , 0x0d , 0x47 , 0x9a , 0x10 , 0x21 , 0xac , 0x93 , 0x83)
		#d = (0x8d,0xac,0xf1,0x5b,0x99,0x44,0xcf,0x87,0xe8,0x44,0x86,0x32,0x94,0x52)
		# debugging CPR decoding...
		#d = (0x8d ,0xa7 ,0x1e ,0xfa ,0x36 ,0x09 ,0x51 ,0x30 ,0x2a ,0x32 ,0x09 ,0x04 ,0x3e ,0xb2)
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x20 ,0x08 ,0x29 ,0xb7 ,0xd3 ,0xea )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb1 ,0x9a ,0x20 ,0x04 ,0x29 ,0xfc ,0x83 ,0x24 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x60 ,0xbd ,0xf4 ,0x75 ,0x15 ,0xca ,0x1e ,0x51 ,0x0f ,0x21 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x60 ,0xbd ,0xf0 ,0xde ,0xe5 ,0x99 ,0x70 ,0x74 ,0x4a ,0x80 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x20 ,0x04 ,0xe0 ,0x71 ,0xc3 ,0x0d ,0xa0 ,0x21 ,0x0d ,0x67 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x60 ,0xbd ,0xf4 ,0x73 ,0xf3 ,0xcb ,0x33 ,0x50 ,0x09 ,0xf8 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x48 ,0x04 ,0x29 ,0x5e ,0xaf ,0x99 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x60 ,0xbf ,0x00 ,0xdd ,0xb2 ,0xc4 ,0x66 ,0x58 ,0x72 ,0x13 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x58 ,0xbd ,0xf4 ,0x72 ,0x9d ,0x67 ,0x8a ,0x2b ,0x40 ,0x4e )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x20 ,0x04 ,0xe0 ,0x71 ,0xc3 ,0x0d ,0xa0 ,0x21 ,0x0d ,0x67 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x58 ,0xbf ,0x00 ,0xdc ,0x8a ,0xc5 ,0x90 ,0x25 ,0x5e ,0xe4 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x11 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0x30 ,0x0d ,0x91 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x58 ,0xbf ,0x00 ,0xdc ,0x60 ,0xc5 ,0xba ,0x74 ,0x79 ,0x7f )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x91 ,0xb0 ,0x9a ,0x48 ,0x04 ,0x29 ,0xcf ,0x68 ,0xe6 )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x99 ,0x91 ,0xb0 ,0x9a ,0x40 ,0x04 ,0x29 ,0xa1 ,0xca ,0xee )
		#self.decode(d)
		#d = (0x8d ,0x86 ,0x91 ,0x44 ,0x58 ,0xbf ,0x04 ,0x71 ,0x79 ,0x68 ,0xaf ,0x1d ,0xba ,0xe2 )
		#self.decode(d)
		# testing TIS-B
		d = (0x95, 0xac, 0x07, 0x6a, 0x99, 0x3c, 0x2f, 0x08, 0xe0, 0x5a, 0x20, 0x47, 0xc7, 0x12)
		self.decode(d)
		d = (0x95, 0xac, 0x0b, 0x14, 0x68, 0x17, 0xf0, 0xf9, 0x92, 0x30, 0x86, 0x99, 0xe0, 0xec)
		self.decode(d)
		d = (0x95, 0xac, 0x0b, 0x14, 0x68, 0x17, 0xf4, 0x8f, 0x02, 0xdd, 0xca, 0x64, 0x53, 0xc5)
		self.decode(d)
		d = (0x95, 0xac, 0x04, 0x12, 0x68, 0x0f, 0xf1, 0x17, 0x3a, 0x1c, 0xb4, 0xc4, 0x67, 0xb8)
		self.decode(d)
		d = (0x95, 0xac, 0x04, 0x12, 0x99, 0x38, 0x2b, 0x1c, 0x40, 0x6a, 0x20, 0xe1, 0xab, 0x56)
		self.decode(d)
		d = (0x95, 0xac, 0x0f, 0x46, 0x68, 0x13, 0xb4, 0x77, 0xe2, 0xe1, 0x07, 0x9e, 0x54, 0x60)
		self.decode(d)
		d = (0x95, 0xac, 0x03, 0x06, 0x68, 0x07, 0x70, 0xe3, 0x9c, 0x32, 0x2e, 0x77, 0x28, 0x26)
		self.decode(d)
		d = (0x95, 0xac, 0x03, 0x06, 0x68, 0x07, 0x74, 0x79, 0x6a, 0xdf, 0x69, 0xe7, 0x4e, 0xde)
		self.decode(d)
		d = (0x95, 0xac, 0x03, 0x06, 0x99, 0x38, 0x33, 0x87, 0x80, 0x06, 0x20, 0xdd, 0xb1, 0x6b)
		self.decode(d)
		d = (0x95, 0xac, 0x0b, 0x14, 0x99, 0x40, 0x05, 0x0a, 0x60, 0x26, 0x20, 0x79, 0x23, 0x42)
		self.decode(d)
		d = (0x95, 0xac, 0x0b, 0x14, 0x68, 0x19, 0x00, 0xf9, 0xe6, 0x30, 0x8d, 0xc2, 0x14, 0x97)
		self.decode(d)
		d = (0x95, 0xac, 0x04, 0x12, 0x68, 0x11, 0x94, 0xac, 0xf2, 0xca, 0x64, 0x04, 0x20, 0x6b)
		self.decode(d)
		d = (0x95, 0xac, 0x0f, 0x46, 0x68, 0x13, 0xe0, 0xe1, 0xb4, 0x33, 0xe7, 0x21, 0x79, 0x7c)
		self.decode(d)
		d = (0x95, 0xac, 0x03, 0x06, 0x99, 0x38, 0x33, 0x87, 0x60, 0x06, 0x20, 0xf8, 0x31, 0xbd)
		self.decode(d)
		d = (0x95, 0xac, 0x0f, 0x46, 0x68, 0x13, 0xe0, 0xe1, 0x82, 0x33, 0xf0, 0x6a, 0x88, 0x3f)
		self.decode(d)
		d = (0x95, 0xac, 0x0f, 0x46, 0x68, 0x13, 0xe4, 0x77, 0x5a, 0xe1, 0x22, 0x8e, 0xd8, 0x13)
		self.decode(d)
		d = (0x95, 0xac, 0x0f, 0x46, 0x99, 0x38, 0x28, 0x8c, 0x40, 0x2a, 0x20, 0x29, 0x58, 0x78)
		self.decode(d)
		d = (0x95, 0xac, 0x07, 0xe3, 0x68, 0x0d, 0x11, 0x19, 0xd4, 0x17, 0x4d, 0xab, 0xaa, 0x1e)
		self.decode(d)
		d = (0x95, 0xac, 0x07, 0xe3, 0x68, 0x0d, 0x14, 0xae, 0xba, 0xc5, 0x1a, 0x41, 0x64, 0x1d)
		self.decode(d)
		d = (0x95, 0xac, 0x0b, 0x14, 0x68, 0x19, 0x10, 0xfa, 0x14, 0x30, 0x89, 0x6d, 0xeb, 0xf0)
		self.decode(d)
		d = (0x95, 0xac, 0x0b, 0x14, 0x68, 0x19, 0x14, 0x8f, 0x82, 0xdd, 0xcd, 0xc0, 0xd6, 0xc6)
		self.decode(d)
		d = (0x95, 0xac, 0x0b, 0x14, 0x99, 0x40, 0x05, 0x0a, 0x60, 0x22, 0x20, 0x41, 0x15, 0x42)
		self.decode(d)
		return

	    
if __name__ == "__main__":
	class a:
		def __init__(self, args):
			self.args = args
	args = a
	args.origin = (37.7, -122.02)
	d = AdsbDecoder(args)
	d.testPackets()
