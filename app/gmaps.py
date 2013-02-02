# Display Google maps in web browser window, using its Javascript API
# B. Kuschak <brian@openadsb.com>

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
import sys


js = """
var plines = {};
var infoWindow;
var prevZIndex;
function moveNewCenter()
{
    map.setCenter(new google.maps.LatLng(37.4419, -122.1419), 13);
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

class gmaps(QWebView):
	def __init__(self):
		QWebView.__init__(self)
		self.setPage(QWebPage())
		self.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
		loc = QFileInfo(sys.argv[0])
		url = QUrl.fromLocalFile(loc.absolutePath() + "/gmap.html")
		self.load(url)
		self.frame = self.page().mainFrame()
		self.frame.evaluateJavaScript(js);		# load the functions
		# Allow javascript to call back into Qt
                printer = ConsolePrinter(self.frame)
                self.frame.addToJavaScriptWindowObject('printer', printer)
                self.frame.evaluateJavaScript("printer.text('Testing Javascript printing from Qt... good!');")
                highlighter = TableHighlighter(self.frame, self)
                self.frame.addToJavaScriptWindowObject('highlighter', highlighter)


	# SLOTS
	def updateAircraftPosition(self, ac):
		l = len(ac.track)
		if l > 2:
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

