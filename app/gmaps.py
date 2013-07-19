# Display Google maps in web browser window, using its Javascript API
# B. Kuschak <brian@openadsb.com>

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
import sys
from settings import *


js = """
var plines = {};
var infoWindow;
var prevZIndex;
function moveNewCenter(lat, lon, zoom)
{
    centerLat = lat;
    centerLon = lon;
    zoomLevel = zoom;
    map.setCenter(new google.maps.LatLng(lat, lon), zoom);
}
function createPolyline(lat, lon, alt)
{
    var pline = new google.maps.Polyline({
	strokeColor: "#FF0000",		// red
	strokeOpacity: 0.8,
	strokeWeight: 5
    });
    pline.setMap(map);

    // highlight track when you mouse over, and display an arrow at the end of the track
    google.maps.event.addListener(pline, 'mouseover', function() {
     var arrow = {
	icon: {
		path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
		strokeColor: "#000000",
		strokeOpacity: 1,
		strokeWeight: 1
	},
	offset: '100%'
     };
     prevZIndex = pline.zIndex;
     pline.setOptions({
       icons: [arrow],
       strokeColor: "#000000",		// black
       strokeOpacity: 1.0,
       strokeWeight: 5,
       zIndex: 100			// on top of other lines
     });
     highlighter.highlight(pline.aa);
   });
   google.maps.event.addListener(pline, 'mouseout', function() {
     pline.setOptions({
       icons: [ ],
       strokeColor: "#FF0000",		// red
       strokeOpacity: 0.8,
       strokeWeight: 5,
       zIndex: prevZIndex
     });
     highlighter.unhighlight(pline.aa);
   });
   //google.maps.event.addListener(pline, 'click', function(event) {
     	//infoWindow = new google.maps.InfoWindow();
     	//var str = "<b>" + pline.aa + "</b>";
     	//infoWindow.setContent(str);
     	//infoWindow.setPosition(event.latLng);
	//infoWindow.open(map);
   //});
   return pline
}
function getNumPlines()
{
    var len = Object.keys(plines).length;
    return len;
}
function showTrack(aa, enable)
{
    var pline = plines[aa];
    if(pline != null) {
	if(enable) { pline.setVisible(true); }
	else { pline.setVisible(false); }
    }
}
function plotTrack(aa, lat, lon, alt)
{
    var pline = plines[aa];
    if(pline == null) {
	    pline = createPolyline(lat, lon, alt);
	    pline.aa = aa;
	    plines[aa] = pline;
    }
    var path = pline.getPath(); 
    var pt = new google.maps.LatLng(lat, lon, alt);
    //printer.text('javascript plotTrack(): ' + lat + ' ' + lon + ' ' + alt)
    path.push(pt);
    //var n = getNumPlines();
    //printer.text(n);
}
"""
# save these in our settings, and restore on restart
#map.getCenter()
#map.getZoom()

# from http://stackoverflow.com/questions/5792832/print-javascript-exceptions-in-a-qwebview-to-the-console
class WebPage(QWebPage):
	def javaScriptConsoleMessage(self, msg, line, source):
		print 'WebPage: %s line %d: %s' % (source, line, msg)

class gmaps(QWebView):
	def __init__(self, parent = None):
		# BK - it seems like the page we load here doesn't get its javascript evaluated until AFTER we return from this function.
		# That's good - we can add all our Python functions so they can be called immediately when the page is loaded
		QWebView.__init__(self, parent)
		#self.centerLat = 0
		#self.centerLon = 0
		#self.zoomLevel = 0
		#self.setPage(QWebPage())
		self.setPage(WebPage())
		self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
		loc = QFileInfo(sys.argv[0])
		url = QUrl.fromLocalFile(loc.absolutePath() + "/gmap.html")
		self.load(url)
		self.frame = self.page().mainFrame()
		self.frame.evaluateJavaScript(js);		# load the functions above

		# Allow javascript to call back into Qt
                printer = ConsolePrinter(self.frame)
                self.frame.addToJavaScriptWindowObject('printer', printer)
                self.frame.evaluateJavaScript("printer.text('Testing Javascript printing from Qt... good!');")

                highlighter = TableHighlighter(self.frame, self)
                self.frame.addToJavaScriptWindowObject('highlighter', highlighter)

                map_settings = mapSettings(self.frame, self)
                self.frame.addToJavaScriptWindowObject('settings', map_settings)


	# SLOTS
	def updateAircraftPosition(self, ac):
		l = len(ac.track)
		if l > 1:
			end = ac.track[l-1]
			[ lon, lat, alt, head ] = end
			s = "plotTrack(%s, %f, %f, %f);" % (ac.aa, lat, lon, alt)
			self.frame.evaluateJavaScript(s)

	def setTrackVisible(self, aa, enable):
		s = "showTrack(%s, %d);" % (aa, enable)
		self.frame.evaluateJavaScript(s)
		
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


class TableHighlighter(QObject):
    def __init__(self, frame, parent=None):
        super(TableHighlighter, self).__init__(parent)
	self.parent = parent
	self.frame = frame

    @pyqtSlot(str)
    def highlight(self, aa):
        #print "will highlight table id ", aa
	self.parent.emit(SIGNAL("highlightAircraft(int)"), int(aa))

    @pyqtSlot(str)
    def unhighlight(self, aa):
        #print "will unhighlight table id ", aa
	self.parent.emit(SIGNAL("unhighlightAircraft(int)"), int(aa))


class mapSettings(QObject):
    def __init__(self, frame, parent=None):
        super(mapSettings, self).__init__(parent)
	self.parent = parent
	self.frame = frame
	self.getSettings()

    def saveSettings(self):
	settings = mySettings()
	settings.beginGroup("googleMaps")
	settings.setValue("zoomLevel", self.zoomLevel)
	settings.setValue("centerLat", self.centerLat)
	settings.setValue("centerLon", self.centerLon)
	settings.endGroup()

    def getSettings(self):
	settings = mySettings()
	settings.beginGroup("googleMaps")
	self.zoomLevel = settings.value("zoomLevel").toInt()[0]
	self.centerLat = settings.value("centerLat").toFloat()[0]
	self.centerLon = settings.value("centerLon").toFloat()[0]
	settings.endGroup()

    # These are called from Javascript:
    @pyqtSlot(result=float)
    def getCenterLat(self):
	return self.centerLat

    @pyqtSlot(result=float)
    def getCenterLon(self):
	return self.centerLon

    @pyqtSlot(result=int)
    def getZoomLevel(self):
	return self.zoomLevel

    @pyqtSlot(int)
    def zoomChanged(self, zoom):
        #print "zoom Changed on map: %d" % (zoom)
	self.zoomLevel = zoom
	self.saveSettings()

    @pyqtSlot(float, float)
    def centerChanged(self, lat, lon):
        #print "center Changed on map %f, %f:" % (lat, lon)
	self.centerLat = lat
	self.centerLon = lon
	self.saveSettings()



