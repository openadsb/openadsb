# Top-level module for ADSB decoder
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
import sys
import argparse
import reader
import decoder
import tablewidget
#import webserver
import signal
import dlg_server
import dlg_origin
import server
import db
import gmaps
import gearth
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
#from PyQt4 import QtGui 
import yappi

# Qt main window for the GUI
class MainWindow(QMainWindow):
	def __init__(self, reader, args):
		QMainWindow.__init__(self)
		self.reader = reader
		self.server = None
		self.args = args
		self.initUI()

	def initUI(self):
		# Menus and actions
		kmlAction = QAction(QIcon(), 'KML', self)
		kmlAction.setShortcut('Ctrl+K')
		kmlAction.setStatusTip('Generate KML for selected aircraft')
		#kmlAction.triggered.connect(self.dumpKml)
		exitAction = QAction(QIcon(), 'Exit', self)
		exitAction.setShortcut('Ctrl+Q')
		exitAction.setStatusTip('Exit application')
		exitAction.triggered.connect(self.close)
		resizeAction = QAction(QIcon(), 'Resize', self)
		resizeAction.setShortcut('Ctrl+R')
		resizeAction.setStatusTip('Resize columns to fit')
		#resizeAction.triggered.connect()
		aboutAction = QAction(QIcon(), 'About', self)
		aboutAction.setShortcut('Ctrl+H')
		aboutAction.setStatusTip('About this program')
		#aboutAction.triggered.connect()
		wikiAction= QAction(QIcon(), 'Wiki...', self)
		wikiAction.setShortcut('Ctrl+W')
		wikiAction.setStatusTip('Open the Wiki webpage')
		wikiAction.triggered.connect(self.openWiki)
		serverAction = QAction(QIcon(), 'Streaming Server...', self)
		serverAction.setShortcut('Ctrl+S')
		serverAction.setStatusTip('Run a streaming server for other clients')
		serverAction.triggered.connect(self.cfgServer)
		originAction = QAction(QIcon(), 'Set Origin ...', self)
		originAction.setShortcut('Ctrl+O')
		originAction.setStatusTip('Set the position of your antenna, so position decoding works')
		originAction.triggered.connect(self.setOrigin)

		menubar = self.menuBar()	 
		fileMenu = menubar.addMenu('&File')	
		editMenu = menubar.addMenu('&Edit')
		viewMenu = menubar.addMenu('&View')
		toolsMenu = menubar.addMenu('&Tools')
		helpMenu = menubar.addMenu('&Help')	
		fileMenu.addAction(kmlAction)
		fileMenu.addAction(exitAction)
		viewMenu.addAction(resizeAction)
		toolsMenu.addAction(serverAction)
		helpMenu.addAction(aboutAction)
		helpMenu.addAction(wikiAction)

		# Toolbar actions
		toolbar = self.addToolBar('Exit')
		toolbar.addAction(exitAction)
		toolbar.addAction(resizeAction)
		toolbar.addAction(kmlAction)
		toolbar.show()

		# Aircraft Table 
		self.t = tablewidget.AdsbTableWidget(self)
		self.t.show()
		resizeAction.triggered.connect(self.t.resizeColumnsToContents)

		# connect the signals from the reader/parser to the slots in tablewidget
		self.dec = self.reader.getDecoder()
		self.t.connect(self.dec, SIGNAL("addAircraft(PyQt_PyObject)"), self.t.addAircraft)
		self.t.connect(self.dec, SIGNAL("updateAircraft(PyQt_PyObject)"), self.t.updateAircraft)
		self.t.connect(self.dec, SIGNAL("updateAircraftPosition(PyQt_PyObject)"), self.t.updateAircraftPosition)
		self.t.connect(self.dec, SIGNAL("delAircraft()"), self.t.delAircraft)
		
		# Create a progress bar to show the current RX level
		self.rxbar = QProgressBar()
		self.rxbar.setRange(0, 4096)
		self.rxbar.setValue(50)
		self.rxbar.show()
		#self.rxbar.connect(self.dec, SIGNAL("rxLevelChanged(int)"), self.rxbar.setValue)

		self.daclevel = QSpinBox()
		self.daclevel.setMinimum(0)
		self.daclevel.setMaximum(4095)
		self.daclevel.setValue(self.args.daclevel)
		self.daclevel.connect(self.daclevel, SIGNAL("valueChanged(int)"), self.reader.setDAC)

		# create a set of labels for statistics
		# Add labels to grid
		grid = QGridLayout()
		grid.setSpacing(10)
		grid.addWidget(QLabel("DAC Level:"), 0, 0)
		grid.addWidget(QLabel("RX Level:"), 1, 0)
		grid.addWidget(QLabel("Total Packets:"), 2, 0)
		grid.addWidget(QLabel("Good Packets:"), 3, 0)
		grid.addWidget(QLabel("CRC Errors:"), 4, 0)
		grid.addWidget(QLabel("Bad Short Packets:"), 5, 0)
		grid.addWidget(QLabel("Bad Long Packets:"), 6, 0)
		grid.addWidget(QLabel("Logfile Size:"), 7, 0)
		grid.addWidget(QLabel("DF0 (Short ACAS Air-to-Air):"), 8, 0)
		grid.addWidget(QLabel("DF4 (Altitude Roll-Call):"), 9, 0)
		grid.addWidget(QLabel("DF5 (Identity Reply):"), 10, 0)
		grid.addWidget(QLabel("DF11 (Mode S All-Call Reply):"), 11, 0)
		grid.addWidget(QLabel("DF17 (Extended Squitter):"), 12, 0)
		grid.addWidget(QLabel("DF20 (Comm-B Altitude Reply):"), 13, 0)
		grid.addWidget(QLabel("DF21 (Comm-B Identity Reply):"), 14, 0)
		grid.addWidget(QLabel("DF Other (Unknown):"), 15, 0)

		self.rxLevel = QLabel("0")
		self.totalPkts = QLabel("0")
		self.goodPkts = QLabel("0")
		self.CrcErrs = QLabel("0")
		self.DF0 = QLabel("0")
		self.DF4 = QLabel("0")
		self.DF5 = QLabel("0")
		self.DF11 = QLabel("0")
		self.DF17 = QLabel("0")
		self.DF20 = QLabel("0")
		self.DF21 = QLabel("0")
		self.DFOther = QLabel("0")
		self.badShortPkts = QLabel("0")
		self.badLongPkts = QLabel("0")
		self.logfileSize= QLabel("0")
		grid.addWidget(self.daclevel, 0, 1)
		grid.addWidget(self.rxLevel, 1, 1)
		grid.addWidget(self.totalPkts, 2, 1)
		grid.addWidget(self.goodPkts, 3, 1)
		grid.addWidget(self.CrcErrs, 4, 1)
		grid.addWidget(self.badShortPkts, 5, 1)
		grid.addWidget(self.badLongPkts, 6, 1)
		grid.addWidget(self.logfileSize, 7, 1)
		grid.addWidget(self.DF0, 8, 1)
		grid.addWidget(self.DF4, 9, 1)
		grid.addWidget(self.DF5, 10, 1)
		grid.addWidget(self.DF11, 11, 1)
		grid.addWidget(self.DF17, 12, 1)
		grid.addWidget(self.DF20, 13, 1)
		grid.addWidget(self.DF21, 14, 1)
		grid.addWidget(self.DFOther, 15, 1)
		statsWindow = QWidget()
		statsWindow.setLayout(grid)
		#self.connect(self.dec, SIGNAL("updateStats(int, int, int, int)"), self.updateStats)
		self.connect(self.dec, SIGNAL("updateStats(PyQt_PyObject)"), self.updateStats)


		# create web-browser window
		#webWindow = QWebView()
		#webWindow.settings().setAttribute(QWebSettings.JavascriptEnabled, True)
		##webfname = qApp.applicationDirPath() + "/map.html"
		#webfname = "./map.html"
		#if (QFile(webfname).exists() != True):
			#print "HTML file %s not found" % (webfname)
		##url = QUrl.fromLocalFile(webfname)
		#url = QUrl.fromLocalFile("/Users/bk/src/openadsb/app/map.html")
		##url = QUrl("http://www.google.com")
		#print url
		#webWindow.load(url)
		#webWindow.show()

		self.gmapsWindow = gmaps.gmaps()
		self.gmapsWindow.show()
		self.t.connect(self.dec, SIGNAL("updateAircraftPosition(PyQt_PyObject)"), self.gmapsWindow.updateAircraftPosition)
		self.t.connect(self.gmapsWindow, SIGNAL("highlightAircraft(int)"), self.t.highlightAircraft)
		self.t.connect(self.gmapsWindow, SIGNAL("unhighlightAircraft(int)"), self.t.unhighlightAircraft)
		
		# fixme - Google Earth plugin doesn't work yet
		earthWindow = gearth.gearth()
		earthWindow.show()
		#self.t.connect(self.dec, SIGNAL("updateAircraft(PyQt_PyObject)"), earthWindow.updateAircraft)
		

		# create log message textbox 
		logmsg = QTextEdit()
		self.t.connect(self.dec, SIGNAL("appendText(const QString&)"), logmsg.append)
		logmsg.document().setMaximumBlockCount(100)		# max lines in the log window - old lines deleted from top

		# Create a layout
		hbox = QHBoxLayout()
		hbox.addWidget(QLabel("Show message types:  "))
		hbox.addWidget(QCheckBox("DF0  "))
		hbox.addWidget(QCheckBox("DF4  "))
		hbox.addWidget(QCheckBox("DF5  "))
		hbox.addWidget(QCheckBox("DF11  "))
		hbox.addWidget(QCheckBox("DF17  "))
		hbox.addWidget(QCheckBox("DF20  "))
		hbox.addWidget(QCheckBox("DF21  "))
		hbox.addStretch(1)
		logheader = QWidget()
		logheader.setLayout(hbox)

		hsplit = QSplitter()
		hsplit.addWidget(statsWindow)
		hsplit.addWidget(self.gmapsWindow)
		hsplit.addWidget(earthWindow)
		#hbox2 = QHBoxLayout()
		#hbox2.addWidget(statsWindow)
		#hbox2.addWidget(webWindow)
		#hbox2.addStretch(1)
		#statsWebBox = QWidget()
		#statsWebBox.setLayout(hbox2)

		vbox = QVBoxLayout()
		vbox.setSpacing(0)
		vbox.addWidget(logheader)
		vbox.addWidget(logmsg)
		logbox = QWidget()
		logbox.setLayout(vbox)
		
		# use a vertical splitter instead of vbox
		vsplit = QSplitter()
		vsplit.setOrientation(Qt.Vertical)
		vsplit.addWidget(self.t)
		vsplit.addWidget(self.rxbar)
		#vsplit.addWidget(statsWindow)
		#vsplit.addWidget(statsWebBox)
		vsplit.addWidget(hsplit)
		vsplit.addWidget(logbox)
		self.setCentralWidget(vsplit)

		self.statusBar().showMessage('Ready')
		self.setGeometry(300, 300, 250 ,150)
		self.setWindowTitle('OpenADSB Project')
		self.show()
		self.raise_()

		# Create the database thread and connect its slots and signals
		#self.dbThread = QThread()
		#self.dbWorker = db.AircraftDbWorker(self.dbThread)
		self.dbThread = db.AircraftDbThread()
		self.connect(self.dec, SIGNAL("addAircraft(PyQt_PyObject)"), self.dbThread.db.addAircraft)
		self.connect(self.dbThread.db, SIGNAL("updateAircraftDbInfo(PyQt_PyObject)"), self.t.updateAircraftDbInfo)

	def openWiki(self):
		# open in browser
		OPENADSB_WIKI_URL = "http://www.openadsb.com/wiki"
		QDesktopServices.openUrl(QUrl(OPENADSB_WIKI_URL, QUrl.TolerantMode))

	# bk - make new one - using server_new and client
	def cfgServer(self, enable, port, maxConn, fmt):
		(accepted, enable, port, maxConn, fmt) = dlg_server.DlgConfigServer.get(self.server != None)
		if accepted:
			if self.server != None:
				self.server.shutdown()
				self.server = None
			if enable:
				# bind to 0.0.0.0
				self.server = server.ServerThread('', port, maxConn, fmt)                    
				self.server.start()
				print "started server thread(s) on port %d" % (port)
			self.reader.setServer(self.server)

	def setOrigin(self):
		(accepted, lat, long) = dlg_server.DlgConfigServer.get(self.origin)
		if accepted:
			if self.server != None:
				self.server.shutdown()
				self.server = None
			if enable:
				# bind to 0.0.0.0
				self.server = server.ServerThread('', port, maxConn, fmt)                    
				self.server.start()
				print "started server thread(s) on port %d" % (port)
		self.reader.setServer(self.server)

	def updateStats(self, stats):
		self.totalPkts.setNum(stats.totalPkts)
		self.goodPkts.setNum(stats.goodPkts)
		self.CrcErrs.setNum(stats.CrcErrs)
		self.badShortPkts.setNum(stats.badShortPkts)
		self.badLongPkts.setNum(stats.badLongPkts)
		self.rxLevel.setNum(stats.rxLevel)
		self.DF0.setNum(stats.DF0)
		self.DF4.setNum(stats.DF4)
		self.DF5.setNum(stats.DF5)
		self.DF11.setNum(stats.DF11)
		self.DF17.setNum(stats.DF17)
		self.DF20.setNum(stats.DF20)
		self.DF21.setNum(stats.DF21)
		self.DFOther.setNum(stats.DFOther)
		if stats.logfileSize < 1024:
			self.logfileSize.setText("%u B"%(stats.logfileSize))
		elif stats.logfileSize < 1024*1024:
			self.logfileSize.setText("%.2f KB"%(float(stats.logfileSize)/1024))
		elif stats.logfileSize < 1024*1024*1024:
			self.logfileSize.setText("%.2f MB"%(float(stats.logfileSize)/1024/1024))

		
		
#def signalHandler(signal, frame):
	#print "Ctrl+C received... shutting down"
	
def main():
	#yappi.start()		# profiling
	recentAircraft = {}
	#default_daclevel = 0xc80
	#efault_daclevel = 0x950
	#default_daclevel = 0x500
	#default_daclevel = 0xa00
	default_daclevel = 0x750
	#default_daclevel = 0xf00
	default_origin = [ 37.38, -122.04 ]

	# Parse cmd line args
	desc =  'Mode S packet decoder and logger.\n'
	desc += 'By default, will read from USB dongle.\n'
	desc += 'Otherwise, read from file or network.\n'
	parser = argparse.ArgumentParser(description=desc)
	parser.add_argument('-f', '--file', dest="filename", help="read from previously recorded packetlog FILE", metavar="FILE")
	parser.add_argument('-s', '--skip', dest="skip", help="when using -f, how many packets to skip from the start of file", default=0, metavar="NUM")
	parser.add_argument('-c', '--count', dest="count", help="how many packets to process", metavar="NUM", default=-1)
	parser.add_argument('-n', '--nogui', dest="nogui", help="command-line only - no GUI", action="store_true")
	parser.add_argument('-v', '--verbose', dest="verbose", metavar="LEVEL", help="increasing output levels 1 to 5")
	#parser.add_argument('-o', '--output', dest='output', metavar="FILE", help="log packets to FILE")
	parser.add_argument('-H', '--host', dest="host", help="read packets from ipaddr:port")
	parser.add_argument('-S', '--server', dest="server", metavar="PORT", help="start a packet server on this host on port PORT")
	parser.add_argument('-d', '--dac', dest="daclevel", metavar="VALUE", help="set the DAC level to VALUE (0 to 4096?)", default=default_daclevel)
	parser.add_argument('-O', '--origin', dest="origin", nargs=2, metavar="FLOAT",  help="Latitude and Longitude of Origin in degrees (-90 to 90, -180 to 180)", default=default_origin)
	parser.add_argument('-p')		# MacOS starts programs with -psn_XXXXXXX "process serial number" argument.  Ignore it. FIXME SetFrontProcess()
	args = parser.parse_args()
	print args
	args.origin = [float(args.origin[0]), float(args.origin[1])]

	# Open the correct reader
	if args.host != None:
		h = args.host.split(':')
		args.host = h[0]
		args.port = int(h[1])
		print args.host, args.port
		exit
		r = reader.AdsbReaderThreadSocket(args)
	elif args.filename != None:
		r = reader.AdsbReaderThreadFile(args)
	else:
		r = reader.AdsbReaderThreadUSB(args)

	# start a server if instructed by command line
	if args.server != None:
		port = int(args.server)
		maxConn = 5
		fmt = "None"
		s = server.ServerThread('', port, maxConn, fmt)	# bind to 0.0.0.0
		s.start()
		print "started server thread(s) on port %d" % (port)
		r.setServer(s)

	# install the default action signal handler for SIGINT - terminate immediately
	# not the nicest - should install custom handler to shutdown gracefully
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	# Create the GUI.  Must be in the main thread.
	if args.nogui:
		en_gui = False
	else:
		en_gui = True
	#en_gui = (notargs.nogui ? False : True)
	app = QApplication(sys.argv, en_gui)
	#if(not args.nogui):
	if en_gui:
		m = MainWindow(r, args)
	r.start()

	ret = app.exec_()
	r.kill_received = True
	r.wait()
	#yappi.print_stats()			# profiling
	sys.exit(ret)


if __name__ == "__main__":
	main()
