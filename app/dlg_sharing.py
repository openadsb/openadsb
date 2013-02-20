# Dialog for configuration of the data sharing over network connections.
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
from settings import *
import PyQt4
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class DlgConfigSharing(QDialog):

	myGroupName = "sharing"		# for QSettings

	def __init__(self, parent = None):
		QDialog.__init__(self, parent)
		self.setModal(True)
		self.setWindowTitle("Configure Data Sharing")
		self.formats = [ "PlanePlotter", "AVR", "OpenADSB v1 ASCII" ]

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		str  = "Real time aircraft data can be shared with other users, by acting as a server or client. "
		str += "In both cases data can be sent and/or received. \n"
		str += "If you run as a server, you might need to adjust your firewall settings, to allow incoming connections."
		l0 = QLabel(str)	
		l0.setWordWrap(True)
		vbox.addWidget(l0)


		# client first
		cbox = QGroupBox("Client settings")
		cgrid = QGridLayout()
		cbox.setLayout(cgrid)
		vbox.addWidget(cbox)
		lc = QLabel("Enable TCP/IP client")
		self.enableClient = QCheckBox()
		cgrid.addWidget(lc, 0, 0)
		cgrid.addWidget(self.enableClient, 0, 1)
		l1 = QLabel("Server port")
		cgrid.addWidget(QLabel("Client hostname or IP address:"), 1, 0)
		self.client = QLineEdit()
		cgrid.addWidget(self.client, 1, 1)
		l2 = QLabel("Port")
		cgrid.addWidget(l2, 2, 0)
		self.cport = QLineEdit()
		cgrid.addWidget(self.cport, 2, 1)
		l3 = QLabel("Packet format to send")
		cgrid.addWidget(l3, 3, 0)
		self.cfmt = QComboBox()
		self.cfmt.addItems(self.formats)
		cgrid.addWidget(self.cfmt, 3, 1)

	
		# server next
		sbox = QGroupBox("Server settings")
		sgrid = QGridLayout()
		sbox.setLayout(sgrid)
		vbox.addWidget(sbox)
		ls = QLabel("Enable TCP/IP server")
		sgrid.addWidget(ls, 0, 0)
		self.enableServer = QCheckBox()
		sgrid.addWidget(self.enableServer, 0, 1)
		l1 = QLabel("Server port")
		sgrid.addWidget(l1, 1, 0)
		self.sport = QLineEdit()
		sgrid.addWidget(self.sport, 1, 1)
		l2 = QLabel("Max number of connections")
		sgrid.addWidget(l2, 2, 0)
		self.maxConn = QLineEdit()
		sgrid.addWidget(self.maxConn, 2, 1)
		l3 = QLabel("Packet format to serve")
		sgrid.addWidget(l3, 3, 0)
		self.sfmt = QComboBox()
		self.sfmt.addItems(self.formats)
		sgrid.addWidget(self.sfmt, 3, 1)

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
		self.enableClient.setChecked(s.value('enableClient').toBool())
		self.enableServer.setChecked(s.value('enableServer').toBool())
		self.client.setText(s.value('client').toString())
		self.cport.setText(s.value('clientPort').toString())
		self.sport.setText(s.value('serverPort').toString())
		self.sfmt.setCurrentIndex(self.sfmt.findText(s.value('serverFormat').toString()))
		self.cfmt.setCurrentIndex(self.cfmt.findText(s.value('clientFormat').toString()))
		self.maxConn.setText(s.value('maxConn').toString())
		s.endGroup()

	def accept(self):
		QDialog.accept(self)
		s = mySettings()
		s.beginGroup(self.myGroupName)
		s.setValue('enableClient', self.enableClient.isChecked())
		s.setValue('enableServer', self.enableServer.isChecked())
		s.setValue('serverPort', self.sport.text())
		s.setValue('clientPort', self.cport.text())
		s.setValue('serverFormat', self.sfmt.currentText())
		s.setValue('clientFormat', self.cfmt.currentText())
		s.setValue('client', self.client.text())
		s.setValue('maxConn', int(self.maxConn.text()))
		s.endGroup()
		
	@staticmethod
	def dumpSettings():
		s = mySettings()
		s.beginGroup(DlgConfigSharing.myGroupName)
		for key in s.allKeys():
			print "'%s' = '%s'" % (key, s.value(key).toString())
		s.endGroup()

	@staticmethod
	def get(parent = None):
		dlg = DlgConfigSharing(parent)
		accept = dlg.exec_()
		return (accept, DlgConfigSharing.myGroupName)

	@staticmethod
	def groupName():
		return DlgConfigSharing.myGroupName


# for testing
if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)

	(accept, groupName) = DlgConfigSharing.get()
	if accept:
		DlgConfigSharing.dumpSettings()
		print "accepted"



