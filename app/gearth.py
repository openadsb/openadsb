#start Display Google maps in web browser window, using its Javascript API
# B. Kuschak <brian@openadsb.com>

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *

# fixme - rather than just adding each line segment, maintain a javascript dict of the AA to polyline object
# then addline will lookup the MVCArray of Polyline object, and push() the new point onto the end.
# it will also allow us to remove line segments by AA also (hide them, delete them, etc), based on Qt signals

js = """
function moveNewCenter()
{
    map.setCenter(new google.maps.LatLng(37.4419, -122.1419), 13);
}
function bktest2()
{
    alert("bktest2() called");
    map.setCenter(new google.maps.LatLng(37.4419, -122.1419), 13);
}
function addLine(lat1, lon1, h1, lat2, lon2, h2)
{
    var coords = [
	new google.maps.LatLng(lat1, lon1, h1),
	new google.maps.LatLng(lat2, lon2, h2)
    ];
    var pline = new google.maps.Polyline({
	path: coords,
	strokeColor: "#FF0000",
	strokeOpacity: 1.0,
	strokeWeight: 5
    });
    pline.setMap(map);
    //map.setCenter(new google.maps.LatLng(lat2, lon2), h2)
    google.maps.event.addListener(pline, 'mouseover', function() {
     pline.setOptions({
       strokeOpacity: 1,
       strokeWeight: 10 
     });
   });

   google.maps.event.addListener(pline, 'mouseout', function() {
     pline.setOptions({
       strokeOpacity: 0.5,
       strokeWeight: 5
     });
   });

}
"""

# This hack needed to make drag/zoom work. See http://qt-project.org/forums/viewthread/1643
class ChromePage(QWebPage):
	def userAgentForUrl(self, url):
		return 'Chrome/1.0'

class gearth(QWebView):
	def __init__(self):
		QWebView.__init__(self)
		self.setPage(ChromePage())
		self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
		self.settings().setAttribute(QWebSettings.PluginsEnabled, True)
		url = QUrl.fromLocalFile("/Users/bk/src/openadsb/app/gearth.html")
		#url = QUrl.fromLocalFile("/Users/bk/src/openadsb/app/blah.html")
		self.load(url)
		self.frame = self.page().mainFrame()
		self.frame.evaluateJavaScript(js);		# load the functions

	# start, end are both [ lon, lat, alt, heading ]
	def drawTrackSeg(self, start, end):
		[ lon1, lat1, alt1, h1 ] = start
		[ lon2, lat2, alt2, h2 ] = end
		str = "addLine(%f, %f, %f, %f, %f, %f);" % (lat1, lon1, alt1, lat2, lon2, alt2)
		self.frame.evaluateJavaScript(str)

	# SLOTS
	# FIXME - this is called for more than just position updates... Only update map when position changes.
	def updateAircraft(self, ac):
		l = len(ac.track)
		#print "gearth: updateAircraft, len = ", l
		if l > 2:
			end = ac.track[l-1]
			start = ac.track[l-2]
			#print "***************************** start = ", start
			#print "***************************** end = ", end
			self.drawTrackSeg(start, end)
		
class ConsolePrinter(QObject):
    def __init__(self, frame, parent=None):
        super(ConsolePrinter, self).__init__(parent)
	self.frame = frame

    @pyqtSlot(str)
    def text(self, message):
        print message

    @pyqtSlot(str)
    def init_done(self, message):
	print message

	
