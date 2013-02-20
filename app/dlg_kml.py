# Dialog for configuration of the KML server
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
from settings import *
import PyQt4
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class DlgConfigKml(QDialog):

	myGroupName = "kml"		# for QSettings

	def __init__(self, parent = None):
		QDialog.__init__(self, parent)
		self.setModal(True)
		self.setWindowTitle("Configure KML Server")

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		str  = "Real time aircraft data can be displayed on Google Earth, by running this server."
		l0 = QLabel(str)	
		l0.setWordWrap(True)
		vbox.addWidget(l0)

		# server next
		sbox = QGroupBox("Server settings")
		sgrid = QGridLayout()
		sbox.setLayout(sgrid)
		vbox.addWidget(sbox)
		ls = QLabel("Enable KML server")
		sgrid.addWidget(ls, 0, 0)
		self.enableServer = QCheckBox()
		sgrid.addWidget(self.enableServer, 0, 1)
		l1 = QLabel("Server port")
		sgrid.addWidget(l1, 1, 0)
		self.sport = QLineEdit()
		sgrid.addWidget(self.sport, 1, 1)
		#l2 = QLabel("Max number of connections")
		#sgrid.addWidget(l2, 2, 0)
		#self.maxConn = QLineEdit()
		#sgrid.addWidget(self.maxConn, 2, 1)
		#l3 = QLabel("Packet format to serve")
		#sgrid.addWidget(l3, 3, 0)
		#self.sfmt = QComboBox()
		#self.sfmt.addItems(self.formats)
		#sgrid.addWidget(self.sfmt, 3, 1)

		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		vbox.addWidget(buttonBox)

		self.setValues()
		self.connect(buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
		self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
		self.resize(max(self.sizeHint().width(), 10), self.sizeHint().height())
		self.show()
		self.raise_()

	def setValues(self):
		s = mySettings()
		s.beginGroup(self.myGroupName)
		self.enableServer.setChecked(s.value('enableServer').toBool())
		self.sport.setText(s.value('serverPort').toString())
		s.endGroup()

	def accept(self):
		QDialog.accept(self)
		s = mySettings()
		s.beginGroup(self.myGroupName)
		s.setValue('enableServer', self.enableServer.isChecked())
		s.setValue('serverPort', self.sport.text())
		s.endGroup()
		
	@staticmethod
	def dumpSettings():
		s = mySettings()
		s.beginGroup(DlgConfigKml.myGroupName)
		for key in s.allKeys():
			print "'%s' = '%s'" % (key, s.value(key).toString())
		s.endGroup()

	@staticmethod
	def get(parent = None):
		dlg = DlgConfigKml(parent)
		accept = dlg.exec_()
		return (accept, DlgConfigKml.myGroupName)

	@staticmethod
	def groupName():
		return DlgConfigKml.myGroupName


# for testing
if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)

	(accept, groupName) = DlgConfigKml.get()
	if accept:
		DlgConfigKml.dumpSettings()
		print "accepted"



