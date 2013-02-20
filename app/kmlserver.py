# Webserver and KML file generation for external Google Earth client
#
import sys
import BaseHTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from PyQt4.QtCore import *
import simplekml
import aircraft
import decoder 

class kmlServer(QThread):

	HandlerClass = SimpleHTTPRequestHandler
	ServerClass  = BaseHTTPServer.HTTPServer
	Protocol     = "HTTP/1.0"

	def __init__(self, port):
		QThread.__init__(self)
		self.port = port
		self.server_address = ('127.0.0.1', port)
		
	def run(self):
		self.HandlerClass.protocol_version = self.Protocol
		self.httpd = self.ServerClass(self.server_address, self.HandlerClass)
		sa = self.httpd.socket.getsockname()
		print "Serving HTTP on", sa[0], "port", sa[1], "..."
		self.httpd.serve_forever()
	
	
		#self.pt = kml.newpoint(coords=[(lon,lat,alt)], altitudemode='absolute')
		#self.pt.iconstyle = simplekml.IconStyle(heading=self.heading,icon=icon)
		#if self.idStr != "":
			#self.pt.name=self.idStr
		#else:
			#self.pt.name=("%x"%(self.aa))
		##kml.save("adsb.kml")

	# called periodically to regenerate the KML file
	def updateKmlFile(self):
		pass
		#dec = 
		#for aa in sorted(dec.recentAircraft.keys()):
			#a = self.recentAircraft[aa]
			#if a != None:
				#self.createTrack(a)

	def createTrack(self, ac):
		pass
		#if self.idStr != "":
			#name=ac.idStr
		#else:
			#name=("%x"%(ac.aa))
		# track path first
		#if len(ac.track) > 0:
			#track_meters = [ ]
			#for tp in ac.track:
				#track_meters += [(tp[0], tp[1], feet2meters(tp[2]))]
			#desc = (ac.countryStr)
			## fixme - to description add: max speed, min speed, max alt, min alt, country, category, ID str, registration info, fsStr, squawk, range
			## fixme - add TimeSpan, TimeStamp
			## fixme - add Schema for custom parameters to be displayed in elevation plot
			## fixme - sort this dump by AA or ID
			#ls = kml.newlinestring(name=name, coords=track_meters, altitudemode='absolute', description=desc)
			#ls.linestyle = simplekml.LineStyle(color="FF0000FF", width=5)
			#kml.save("openadsb.kml")

		# then actual points (fixme - skip if distance from last pt is < threshold
		# fixme - new folder structure:
		#   	tracks
		#		linestring per aircraft
		#	waypoints
		#		folder per aircraft
		#			set of waypoints
		#	
		# fixme - IconStyle for each waypoint, not global
		#folder = kml.newfolder(name=name)
		#folder_style = simplekml.Style()
		##folder_style.liststyle.listitemtype = "radioFolder"
		#folder.style = folder_style
		#for tp in self.track:
			#point_meters = [(tp[0], tp[1], feet2meters(tp[2]))]
			#pt = folder.newpoint(name=name, coords=point_meters, altitudemode='absolute')
			#pt.iconstyle = simplekml.IconStyle(heading=self.heading,icon=icon)
			##pt.timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(tp[3]))	bk fixme 
			#pt.description = '<![CDATA[ Altitude 8000 ft<br/> Climbing 1000 ft/min<br/> Airspeed 425 kts<br/> Heading 289 deg/min<br/> Time XXXXX ]]>'

		# fixme - add another track which is ground path (altitude mode), and use different line style

	# SLOTS
	def addAircraft(self, ac):
		pass

	def delAircraft(self, ac):
		pass

	def updateAircraft(self, ac):
		pass

	def updateAircraftPosition(self, ac):
		l = len(ac.track)
		pass

	def updateAircraftDbInfo(self, info):
		pass

	def updateAircraftFR24Info(self, info):
		pass


if __name__ == '__main__':
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	if sys.argv[1:]:
	    port = int(sys.argv[1])
	else:
	    port = 8000

	s = kmlServer(port)
	s.start()
	s.wait()
