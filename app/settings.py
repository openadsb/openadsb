# make this a storage place for all our settings.
# emit SIGNAL when settings change, listeners can update if necessary

import sys
from PyQt4.QtCore import *
#from PyQt4.QtGui import *
#from PyQt4.QtWebKit import *

class sharingSettings():
	def __init__(self, settings, mainWindow):
		self.settings = settings
		self.mainWindow = mainWindow
		# defaults
		self.client = QString("localhost")
		self.clientPort = 56565
		self.enableClient = False
		self.serverPort = 56565
		self.enableServer = False
		self.load()

	def load(self):
		self.client = 		self.settings.value("sharing/client")
		self.clientPort = 	self.settings.value("sharing/clientPort").toInt()
		self.enableClient = 	self.settings.value("sharing/enableClient").toBool()
		self.serverPort = 	self.settings.value("sharing/serverPort").toInt()
		self.enableServer = 	self.settings.value("sharing/enableServer").toBool()

	def save(self):
		self.settings.setValue("sharing/client", self.client)
		self.settings.setValue("sharing/clientPort", self.clientPort)
		self.settings.setValue("sharing/enableClient", self.enableClient)
		self.settings.setValue("sharing/serverPort", self.serverPort)
		self.settings.setValue("sharing/enableServer", self.enableServer)

class windowSettings():
	def __init__(self, settings, mainWindow):
		self.settings = settings
		self.mainWindow = mainWindow
		# defaults
		self.pos = QPoint(100, 100)
		self.size = QSize(640, 480)
		self.load()

	def load(self):
		self.pos = 		self.settings.value("window/pos").toPoint()
		self.size = 		self.settings.value("window/size").toSize()

	def save(self):
		self.settings.setValue("window/pos", self.pos)
		self.settings.setValue("window/size", self.size)


# this is the public one
class globalSettings(QObject):
	def __init__(self, mainWindow, parent = None):
		QObject.__init__(self, parent)

		# store settings in the same directory as our files
		loc = QFileInfo(sys.argv[0])
                path = loc.absolutePath() + "/openadsb.ini"
		self.settings = QSettings(path, QSettings.IniFormat)
		#self.settings = QSettings("OpenADSB", "OpenADSB_v1.0")

		self.sharing = sharingSettings(self.settings, mainWindow)
		self.window = windowSettings(self.settings, mainWindow)

	def save(self):
		self.sharing.save()
		self.window.save()


