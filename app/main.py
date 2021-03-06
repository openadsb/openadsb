# Top-level module for OpenADSB app
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
import sys
import argparse
import reader
import decoder
import tablewidget
#import webserver
import signal
import dlg_sharing
import dlg_server
import dlg_origin
import dlg_kml
import client
from server import *
import db
import gmaps
import gearth
from settings import *
import flightradar24
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *
import yappi
from kmlserver import *
import feeds
import airline_codes

class ar():
	host = ''
	port = 0
	origin = [ 0, 0 ]

# to support non-gui operation, use a subclassed QApplication as the main class rather than QMainWindow 
class MyApplication(QApplication):
	def __init__(self, args, parsedargs, en_gui = True):
		QApplication.__init__(self, args, en_gui)
		self.args = parsedargs
		self.en_gui = en_gui
		self.readers = []
		self.setOrganizationDomain("openadsb.com")
		self.setOrganizationName("OpenADSB")
		self.setApplicationName("OpenADSBApp")
		self.setApplicationVersion("0.1.0")
		self.dbThread = db.AircraftDbThread() 		# Create the database thread 
		self.fr24Thread = flightradar24.fr24Thread() 	# Create thread to query flightradar24.com
		self.airlineCodes = airline_codes.airlineCodes()	# only need one of these per app

		if en_gui:
			self.mainWindow = MainWindow(self)
		else:
			self.mainWindow = None

		# control DAC automatically
		if self.args.ditherdac:
			self.ditherdac = DitherDAC(self.mainWindow)		# fixme - make it work w/o gui too

		# file source
		if self.args.filename != None:
			r = reader.AdsbReaderThreadFile(self.args, self)
			self.addReader(r)
		else:
			# USB data source
			self.usbHotplugThread = reader.UsbHotplugWatcher(self)
			self.connect(self.usbHotplugThread, SIGNAL("addReader(PyQt_PyObject)"), self.addReader)
			self.usbHotplugThread.start()

		# Network data source
		if self.args.host != None:
			h = self.args.host.split(':')
			a = ar()
			a.origin = [ 0, 0 ]
			a.host = h[0]
			a.port = int(h[1])
			# fixme - use new ClientThread instead...
			# thread should run in the background and attempt to (re)connect to server indefinitely. add reader should be done by that thread ,not here
			#self.client = client.ClientThread(a.host, a.port)
			#self.client.start()
			#print "started client thread(s) for %s port %d" % (a.host, a.port)
			r = reader.AdsbReaderThreadSocket(a, self)
			self.addReader(r)

	def addReader(self, reader):
		print "MyApplication::addReader called"
		print reader

		# connect the signals from the reader/parser to the slots
		dec = reader.getDecoder()
		self.connect(dec, SIGNAL("appendText(const QString&)"), self.logMsg)	# so we can print to console too
		self.connect(dec, SIGNAL("addAircraft(PyQt_PyObject)"), self.fr24Thread.addAircraft)	# fixme - better way to order this after db.addAircraft has been executed
		self.connect(dec, SIGNAL("addAircraft(PyQt_PyObject)"), self.dbThread.db.addAircraft)

		# some signals are only used with gui
		if self.mainWindow:
			self.mainWindow.addReader(reader)

		self.readers.append(reader)
		reader.start()

	# SLOT: Any text sent to this slot will print on the console
	def logMsg(self, text):
		if self.args.verbose:
			print text



# Qt main window for the GUI
class MainWindow(QMainWindow):
	def __init__(self, app):
		QMainWindow.__init__(self )
		self.app = app
		self.server = None
		self.client = None
		self.kmlServer = None
		self.initUI()

	def initUI(self):
		# Menus and actions
		kmlAction = QAction(QIcon(), 'KML', self)
		kmlAction.setShortcut('Ctrl+K')
		kmlAction.setStatusTip('Generate KML for selected aircraft')
		kmlAction.triggered.connect(self.cfgKmlServer)
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
		serverAction = QAction(QIcon(), 'Data Sharing...', self)
		serverAction.setShortcut('Ctrl+S')
		serverAction.setStatusTip('Run a client or server to connect to others')
		#serverAction.triggered.connect(self.cfgServer)
		serverAction.triggered.connect(self.cfgSharing2)
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
		toolbar = self.addToolBar('Toolbar')
		toolbar.addAction(exitAction)
		toolbar.addAction(resizeAction)
		toolbar.addAction(kmlAction)
		toolbar.show()

		# Aircraft Table 
		self.t = tablewidget.AdsbTableWidget(self)
		self.t.show()
		resizeAction.triggered.connect(self.t.resizeColumnsToContents)

		# Create a progress bar to show the current RX level
		#self.rxbar = QProgressBar()
		#self.rxbar.setRange(0, 4096)
		#self.rxbar.setValue(50)
		#self.rxbar.show()
		#self.rxbar.connect(self.dec, SIGNAL("rxLevelChanged(int)"), self.rxbar.setValue)

		self.daclevel = QSpinBox()
		self.daclevel.setMinimum(0)
		self.daclevel.setMaximum(4095)
		self.daclevel.setValue(self.app.args.daclevel)

		# create a set of labels for statistics
		# Add labels to grid
		grid = QGridLayout()
		grid.setSpacing(10)
		grid.addWidget(QLabel("DAC Level:"), 0, 0)
		grid.addWidget(QLabel("RX Level:"), 1, 0)
		grid.addWidget(QLabel("Total Packets:"), 2, 0)
		grid.addWidget(QLabel("Packet rate:"), 3, 0)
		grid.addWidget(QLabel("Good Packets:"), 4, 0)
		grid.addWidget(QLabel("CRC Errors:"), 5, 0)
		grid.addWidget(QLabel("Bad Short Packets:"), 6, 0)
		grid.addWidget(QLabel("Bad Long Packets:"), 7, 0)
		grid.addWidget(QLabel("Logfile Size:"), 8, 0)
		grid.addWidget(QLabel("DF0 (Short ACAS Air-to-Air):"), 9, 0)
		grid.addWidget(QLabel("DF4 (Altitude Roll-Call):"), 10, 0)
		grid.addWidget(QLabel("DF5 (Identity Reply):"), 11, 0)
		grid.addWidget(QLabel("DF11 (Mode S All-Call Reply):"), 12, 0)
		grid.addWidget(QLabel("DF16 (Long ACAS Air-to-Air):"), 13, 0)
		grid.addWidget(QLabel("DF17 (Extended Squitter):"), 14, 0)
		grid.addWidget(QLabel("DF18 (TIS-B):"), 15, 0)
		grid.addWidget(QLabel("DF20 (Comm-B Altitude Reply):"), 16, 0)
		grid.addWidget(QLabel("DF21 (Comm-B Identity Reply):"), 17, 0)
		grid.addWidget(QLabel("DF Other (Unknown):"), 18, 0)
		grid.addWidget(QLabel("List of Interrogators:"), 19, 0)
		grid.addWidget(QLabel("Barometric pressure:"), 20, 0)

		self.rxLevel = QLabel("0")
		self.totalPkts = QLabel("0")
		self.packetRate = QLabel("0")
		self.goodPkts = QLabel("0")
		self.CrcErrs = QLabel("0")
		self.DF0 = QLabel("0")
		self.DF4 = QLabel("0")
		self.DF5 = QLabel("0")
		self.DF11 = QLabel("0")
		self.DF16 = QLabel("0")
		self.DF17 = QLabel("0")
		self.DF18 = QLabel("0")
		self.DF20 = QLabel("0")
		self.DF21 = QLabel("0")
		self.IICs = QLabel("")
		self.lastPressure = QLabel("")
		self.DFOther = QLabel("0")
		self.badShortPkts = QLabel("0")
		self.badLongPkts = QLabel("0")
		self.logfileSize= QLabel("0")
		grid.addWidget(self.daclevel, 0, 1)
		grid.addWidget(self.rxLevel, 1, 1)
		grid.addWidget(self.totalPkts, 2, 1)
		grid.addWidget(self.packetRate, 3, 1)
		grid.addWidget(self.goodPkts, 4, 1)
		grid.addWidget(self.CrcErrs, 5, 1)
		grid.addWidget(self.badShortPkts, 6, 1)
		grid.addWidget(self.badLongPkts, 7, 1)
		grid.addWidget(self.logfileSize, 8, 1)
		grid.addWidget(self.DF0, 9, 1)
		grid.addWidget(self.DF4, 10, 1)
		grid.addWidget(self.DF5, 11, 1)
		grid.addWidget(self.DF11, 12, 1)
		grid.addWidget(self.DF16, 13, 1)
		grid.addWidget(self.DF17, 14, 1)
		grid.addWidget(self.DF18, 15, 1)
		grid.addWidget(self.DF20, 16, 1)
		grid.addWidget(self.DF21, 17, 1)
		grid.addWidget(self.DFOther, 18, 1)
		grid.addWidget(self.IICs, 19, 1)
		grid.addWidget(self.lastPressure, 20, 1)
		statsWindow = QWidget()
		statsWindow.setLayout(grid)

		# timer for packets/sec 
		self.packetRateTimer = QTimer()
		self.connect(self.packetRateTimer, SIGNAL("timeout()"), self.updatePacketRate)
		self.packetRateFilter = [ 0, 0, 0, 0, 0, 0 ]	
		self.lastPacketCount = 0
		self.packetRateTimer.start(500)

		# Google Maps window
		self.gmapsWindow = gmaps.gmaps(self)
		self.gmapsWindow.show()
		#self.t.connect(self.dec, SIGNAL("updateAircraftPosition(PyQt_PyObject)"), self.gmapsWindow.updateAircraftPosition)
		self.t.connect(self.gmapsWindow, SIGNAL("highlightAircraft(int)"), self.t.highlightAircraft)
		self.t.connect(self.gmapsWindow, SIGNAL("unhighlightAircraft(int)"), self.t.unhighlightAircraft)
		
		# fixme - Google Earth plugin doesn't work yet
		earthWindow = gearth.gearth()
		earthWindow.show()

		# create log message textbox 
		self.logmsg = QTextEdit()
		self.logmsg.document().setMaximumBlockCount(100)		# max lines in the log window - old lines deleted from top

		# Create a layout
		#hbox = QHBoxLayout(self)
		hbox = QHBoxLayout()
		hbox.addWidget(QLabel("Show message types:  "))
		self.logCheckboxes = [ 	QCheckBox("DF0  "), 
					QCheckBox("DF4  "), 
					QCheckBox("DF5  "), 
					QCheckBox("DF11  "), 
					QCheckBox("DF17  "), 
					QCheckBox("DF18  "), 
					QCheckBox("DF20  "), 
					QCheckBox("DF21  ") ]
		for b in self.logCheckboxes:
			hbox.addWidget(b)
		hbox.addStretch(1)
		logheader = QWidget()
		logheader.setLayout(hbox)

		self.hsplit = QSplitter(self)
		self.hsplit.addWidget(statsWindow)
		self.hsplit.addWidget(self.gmapsWindow)
		self.hsplit.addWidget(earthWindow)

		# Data feeds is a tableWidget
		self.feedsWidget = feeds.AdsbFeedsWidget(self)

		# create tabbed window on bottom
		tabWidget = QTabWidget(self)
		tabWidget.addTab(self.logmsg, "Received Packets")
		tabWidget.addTab(self.feedsWidget, "Receivers")

		#vbox = QVBoxLayout(self)
		vbox = QVBoxLayout()
		vbox.setSpacing(0)
		vbox.addWidget(logheader)
		vbox.addWidget(tabWidget)
		logbox = QWidget()
		logbox.setLayout(vbox)
		
		# use a vertical splitter instead of vbox
		self.vsplit = QSplitter(self)
		self.vsplit.setOrientation(Qt.Vertical)
		self.vsplit.addWidget(self.t)
		self.vsplit.addWidget(self.hsplit)
		self.vsplit.addWidget(logbox)
		self.setCentralWidget(self.vsplit)

		self.statusBar().showMessage('Ready')
		self.setGeometry(300, 300, 250 ,150)
		self.setWindowTitle('OpenADSB Project')
		self.show()
		self.raise_()
		
		# load window geometry and state from previous settings (after show() so it works on linux)
		settings = mySettings()
		settings.beginGroup("mainWindow")
		self.restoreGeometry(settings.value("geometry").toByteArray())
		self.restoreState(settings.value("state").toByteArray())
		self.hsplit.restoreState(settings.value("hsplitterState").toByteArray())
		self.vsplit.restoreState(settings.value("vsplitterState").toByteArray())
		settings.beginReadArray("logCheckboxes")
		for idx, b in enumerate(self.logCheckboxes):
			settings.setArrayIndex(idx)
			b.setChecked(settings.value("checked").toBool())
		settings.endArray()
		settings.endGroup()

		# connect database thread and flightradar24 lookup thread to the tablewidget
		self.connect(self.app.dbThread.db, SIGNAL("updateAircraftDbInfo(PyQt_PyObject)"), self.t.updateAircraftDbInfo)
		self.connect(self.app.fr24Thread, SIGNAL("updateAircraftFR24Info(PyQt_PyObject)"), self.t.updateAircraftFR24Info)

	# update average packet rate, averaged over 3 seconds
	# we get here every 0.5 second
	def updatePacketRate(self):
		count = int(self.totalPkts.text())
		l = len(self.packetRateFilter)
		rate = float(sum(self.packetRateFilter)) / float(l) / 0.5
		self.packetRateFilter[1:l] = self.packetRateFilter[0:l-1]
		self.packetRateFilter[0] = count - self.lastPacketCount
		self.packetRate.setText("%.0f / sec"% rate)
		self.lastPacketCount = count
		

	# connect gui signals for this new reader
	def addReader(self, reader):
		print type(reader)
		# connect the signals from the reader/parser to the slots
		dec = reader.getDecoder()
		self.connect(dec, SIGNAL("addAircraft(PyQt_PyObject)"), self.t.addAircraft)
		self.connect(dec, SIGNAL("updateAircraft(PyQt_PyObject)"), self.t.updateAircraft)
		self.connect(dec, SIGNAL("updateAircraftPosition(PyQt_PyObject)"), self.t.updateAircraftPosition)
		self.connect(dec, SIGNAL("delAircraft()"), self.t.delAircraft)
		self.connect(dec, SIGNAL("updateStats(PyQt_PyObject)"), self.updateStats)
		self.connect(dec, SIGNAL("updateAircraftPosition(PyQt_PyObject)"), self.gmapsWindow.updateAircraftPosition)
		self.connect(dec, SIGNAL("appendText(const QString&)"), self.logmsg.append)
		self.connect(self.daclevel, SIGNAL("valueChanged(int)"), reader, SLOT("setDAC(int)"))
		self.connect(self.daclevel, SIGNAL("valueChanged(int)"), self.testDAC)
		self.feedsWidget.addFeed(None)	
		#emit signal addFeed (fixme - only one signal updateFeeds - widget should iterate over reader list)

	# FIXME -figure out why the slot above is never called directly...
	def testDAC(self, d):
		for r in self.app.readers:
			r.setDAC(d)

	# override to save current settings on close
	def closeEvent(self, event):
		print "Saving settings"
		settings = mySettings()

		settings.beginGroup("mainWindow")
		settings.setValue("geometry", self.saveGeometry())
		settings.setValue("state", self.saveState())
		settings.setValue("hsplitterState", self.hsplit.saveState())
		settings.setValue("vsplitterState", self.vsplit.saveState())

		settings.beginWriteArray("logCheckboxes")
		for idx, b in enumerate(self.logCheckboxes):
			settings.setArrayIndex(idx)
			settings.setValue("checked", b.isChecked())
		settings.endArray()
		settings.endGroup()

	def openWiki(self):
		# open in browser
		OPENADSB_WIKI_URL = "http://www.openadsb.com/wiki"
		QDesktopServices.openUrl(QUrl(OPENADSB_WIKI_URL, QUrl.TolerantMode))

			
	# dialog box for configuring data sharing 
	# testing new settings method
	def cfgSharing2(self):
		(accepted, groupName) = dlg_sharing.DlgConfigSharing.get(self)
		if accepted:
			s = mySettings()
			s.beginGroup(groupName)
			dlg_sharing.DlgConfigSharing.dumpSettings()

			class ar():
				host = ''
				port = 0
				origin = [ 0, 0 ]

			# two-way data sharing with openadsb acting as a server
			if self.server != None:
				self.server.shutdown()
				self.server = None
			if s.value("enableServer").toBool():
				self.server = ServerThread(	'', 
									s.value('serverPort').toInt()[0], 
									s.value('maxConn').toInt()[0], 
									str(s.value('serverFormat').toString()))
				self.server.start()
				print "started server thread(s) on port %d" % (s.value("serverPort").toInt()[0])

				# connect a reader to the incoming traffic
				a = ar()
				a.origin = [ 0, 0 ]
				socketReader = reader.AdsbReaderThreadClientServer(a, self.server, self.app)
				dec = socketReader.getDecoder()
				self.connect(dec, SIGNAL("addAircraft(PyQt_PyObject)"), self.t.addAircraft)
				self.connect(dec, SIGNAL("updateAircraft(PyQt_PyObject)"), self.t.updateAircraft)
				self.connect(dec, SIGNAL("updateAircraftPosition(PyQt_PyObject)"), self.t.updateAircraftPosition)
				self.connect(dec, SIGNAL("delAircraft()"), self.t.delAircraft)
				self.readers.append(socketReader)
				socketReader.start()

			self.reader.setServer(self.server)

			# two-way data sharing with openadsb acting as a client
			if self.client != None:
				self.client.shutdown()
				self.client.join()
				self.client = None

			if s.value('enableClient').toBool():
				#a = [ host = s.value('client').toString(), port = s.value('clientPort').toInt()[0] ]
				a.host = s.value('client').toString()
				a.port = s.value('clientPort').toInt()[0]
				self.client = client.ClientThread(a.host, a.port)
				self.client.start()
				print "started client thread(s) for %s port %d" % (a.host, a.port)
				r = reader.AdsbReaderThreadSocket(a, self.app)


	# dialog for configuring the local KML server
	def cfgKmlServer(self):
		(accepted, groupName) = dlg_kml.DlgConfigKml.get(self)
		if accepted:
			s = mySettings()
			s.beginGroup(groupName)
			dlg_kml.DlgConfigKml.dumpSettings()

			# two-way data sharing with openadsb acting as a server
			if self.kmlServer != None:
				self.kmlServer.shutdown()
				self.kmlServer = None
			if s.value("enableServer").toBool():
				self.kmlServer = kmlServer(s.value('serverPort').toInt()[0])
				self.kmlServer.start()
				print "started KML HTTP server thread(s) on port %d" % (s.value("serverPort").toInt()[0])

				self.connect(self.dec, SIGNAL("addAircraft(PyQt_PyObject)"), self.kmlServer.addAircraft)
				self.connect(self.dec, SIGNAL("updateAircraft(PyQt_PyObject)"), self.kmlServer.updateAircraft)
				self.connect(self.dec, SIGNAL("updateAircraftPosition(PyQt_PyObject)"), self.kmlServer.updateAircraftPosition)
				#self.connect(self.dec, SIGNAL("updateAircraftFR24Info(PyQt_PyObject)"), self.kmlServer.updateAircraftFR24Info)
				self.connect(self.dec, SIGNAL("delAircraft()"), self.kmlServer.delAircraft)

	# bk - make new one - using server and client
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
		self.DF16.setNum(stats.DF16)
		self.DF17.setNum(stats.DF17)
		self.DF18.setNum(stats.DF18)
		self.DF20.setNum(stats.DF20)
		self.DF21.setNum(stats.DF21)
		self.DFOther.setNum(stats.DFOther)
		self.lastPressure.setText("%.2f mbar" % stats.lastPressure)

		ics = ""
		for (ic,seen) in enumerate(stats.IICSeen):
			if ic != 0 and seen:
				ics += "%d, " % ic
		if len(ics) != 0:
			ics = ics.strip(", ")		# strip trailing comma
		self.IICs.setText(ics)

		if stats.logfileSize < 1024:
			self.logfileSize.setText("%u B"%(stats.logfileSize))
		elif stats.logfileSize < 1024*1024:
			self.logfileSize.setText("%.2f KB"%(float(stats.logfileSize)/1024))
		elif stats.logfileSize < 1024*1024*1024:
			self.logfileSize.setText("%.2f MB"%(float(stats.logfileSize)/1024/1024))

		
# Sweep the DAC value around, to improve dynamic range
class DitherDAC(QObject):
	def __init__(self, mainWindow):
		QObject.__init__(self, parent = None)
		self.mainWindow = mainWindow
		self.dactimer = QTimer()
		self.connect(self.dactimer, SIGNAL("timeout()"), self.dacupdate)
		self.dactimer.start(500)

	def dacupdate(self):
		# called periodically by timer
		#high = 3000
		#high = 4095
		# fixme - make these configurable
		high = 3300
		#low = 1800
		low = 1400
		r = qrand() % ((high+1) - low) + low
		self.mainWindow.daclevel.setValue(r)

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
	parser.add_argument('-H', '--host', dest="host", help="read packets from ipaddr:port")
	parser.add_argument('-S', '--server', dest="server", metavar="PORT", help="start a packet server on this host on port PORT")
	parser.add_argument('-d', '--dac', dest="daclevel", metavar="VALUE", help="set the DAC level to VALUE (0 to 4096?)", type=int, default=default_daclevel)
	parser.add_argument('-D', '--dither', dest="ditherdac", help="automatically control DAC value", action='store_true' )
	parser.add_argument('-O', '--origin', dest="origin", nargs=2, metavar="FLOAT",  help="Latitude and Longitude of Origin in degrees (-90 to 90, -180 to 180)", default=default_origin)
	#parser.add_argument('-o', '--output', dest='output', metavar="FILE", help="log packets to FILE")
	parser.add_argument('-p')		# MacOS starts programs with -psn_XXXXXXX "process serial number" argument.  Ignore it. FIXME SetFrontProcess()
	args = parser.parse_args()
	print args
	args.origin = [float(args.origin[0]), float(args.origin[1])]

	# Open the correct reader
	#if args.host != None:
		#h = args.host.split(':')
		#args.host = h[0]
		#args.port = int(h[1])
		#print args.host, args.port
		#r = reader.AdsbReaderThreadSocket(args)
	#elif args.filename != None:
		#r = reader.AdsbReaderThreadFile(args)
	#else:
		#pass
		#r = reader.AdsbReaderThreadUSB(args)

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

	app = MyApplication(sys.argv, args, en_gui)
	#app.addReader(r)

	ret = app.exec_()
	r.kill_received = True
	r.wait()
	#yappi.print_stats()			# profiling
	sys.exit(ret)


if __name__ == "__main__":
	main()
