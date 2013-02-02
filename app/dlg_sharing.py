# Dialog for configuration of the data sharing over network connections.
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
import PyQt4
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class DlgConfigSharing(QDialog):

	def __init__(self, args, parent = None):
		QDialog.__init__(self, parent)
		self.setModal(True)
		self.setWindowTitle("Configure Data Sharing")
		self.args = args

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
		sgrid.addWidget(self.sfmt, 3, 1)

		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		vbox.addWidget(buttonBox)

		self.setValues()
		self.connect(buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
		self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
		self.resize(max(self.sizeHint().width(), 10), self.sizeHint().height())

	def setValues(self):
		self.enableClient.setChecked(self.args['enableClient'])
		self.enableServer.setChecked(self.args['enableServer'])
		self.client.setText(self.args['client'])
		self.cport.setText(str(self.args['clientPort']))
		self.sport.setText(str(self.args['serverPort']))
		self.cfmt.addItems(self.args['formats']) 
		self.sfmt.addItems(self.args['formats']) 
		self.sfmt.setCurrentIndex(0)			# fixme
		self.cfmt.setCurrentIndex(2)			# fixme
		self.maxConn.setText(str(self.args['maxConn']))

	def accept(self):
		QDialog.accept(self)
		self.args['enableClient'] = self.enableClient.isChecked()
		self.args['enableServer'] = self.enableServer.isChecked()
		self.args['serverPort'] = int(self.sport.text())
		self.args['clientPort'] = int(self.cport.text())
		self.args['serverFormat'] = str(self.sfmt.currentText())
		self.args['clientFormat'] = str(self.cfmt.currentText())
		self.args['client'] = str(self.client.text())
		self.args['maxConn'] = int(self.maxConn.text())
		
	@staticmethod
	#def get(enableClient, enableServer, parent = None):
	def get(args, parent = None):
		#args = dict()
		#args['enableClient'] = True
		#args['enableServer'] = True
		#args['client'] = "1.2.3.4"
		#args['clientPort'] = 57575
		#args['serverPort'] = 56565
		#args['maxConn'] = 5
		#args['formats'] = ["PlanePlotter", "AVR", "OpenADSB v1 ASCII"]
		#args['clientFormat'] = args['formats'][2]
		#args['serverFormat'] = args['formats'][0]
		dlg = DlgConfigSharing(args, parent)
		accept = dlg.exec_()
		return(accept, dlg.args)

# for testing
if __name__ == "__main__":
	import sys
	app = QApplication(sys.argv)

	args = dict()
	args['enableClient'] = True
	args['enableServer'] = True
	args['client'] = "1.2.3.4"
	args['clientPort'] = 57575
	args['serverPort'] = 56565
	args['maxConn'] = 5
	args['formats'] = ["PlanePlotter", "AVR", "OpenADSB v1 ASCII"]
	args['clientFormat'] = args['formats'][2]
	args['serverFormat'] = args['formats'][0]
	(accept, args) = DlgConfigSharing.get(args)
	if accept:
		print args

	#ret = app.exec_()


