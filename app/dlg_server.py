# Dialog for configuration of the streaming server
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
import PyQt4
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class DlgConfigServer(QDialog):

	def __init__(self, enable, parent = None):
		QDialog.__init__(self, parent)
		self.setModal(True)
		self.setWindowTitle("Configure Streaming Server")

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		l0 = QLabel("Enable streaming server")
		vbox.addWidget(l0)
		self.enable = QCheckBox()
		self.enable.setChecked(enable)
		vbox.addWidget(self.enable)
		l1 = QLabel("Server port")
		vbox.addWidget(l1)
		self.port = QLineEdit()
		self.port.setText("20000")
		vbox.addWidget(self.port)
		l2 = QLabel("Max number of connections")
		vbox.addWidget(l2)
		self.maxConn = QLineEdit()
		self.maxConn.setText("5")
		vbox.addWidget(self.maxConn)
		l3 = QLabel("Packet format to serve")
		vbox.addWidget(l3)
		
		self.fmt = QComboBox()
		self.fmt.addItems(["PlanePlotter", "AVR", "OpenADSB"])
		vbox.addWidget(self.fmt)

		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		vbox.addWidget(buttonBox)

		self.connect(buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
		self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
	
		self.resize(max(self.sizeHint().width(), 10), self.sizeHint().height())

	@staticmethod
	def get(enable, parent = None):
		dlg = DlgConfigServer(enable, parent)
		accept = dlg.exec_()
		return(	accept, 
			dlg.enable.isChecked(),
			int(dlg.port.text()), 
			int(dlg.maxConn.text()), 
			dlg.fmt.currentText())
