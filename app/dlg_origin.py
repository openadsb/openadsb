# Dialog for configuration of the origin location 
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
import PyQt4
from PyQt4.QtCore import *
from PyQt4.QtGui import *

class DlgOrigin(QDialog):

	def __init__(self, lat, long, parent = None):
		QDialog.__init__(self, parent)
		self.setModal(True)
		self.setWindowTitle("Configure Origin Position")

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		l0 = QLabel("The Latitude/Longitude of your antenna must be entered, so that position decoding works correctly. "
			"Use decimal format, not minutes and seconds format.")
		vbox.addWidget(l0)
		vbox.addStretch(1)
		l1 = QLabel("Latitude (prefix with '-' for south of the equator)")
		vbox.addWidget(l1)
		self.latitude = QLineEdit()
		self.latitude.setText(lat)
		vbox.addWidget(self.port)
		l2 = QLabel("Longitude (prefix with '-' for West longitude)")
		vbox.addWidget(l2)
		self.longitude = QLineEdit()
		self.longitude.setText(long)
		vbox.addWidget(self.longitude)
		
		buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		vbox.addWidget(buttonBox)

		self.connect(buttonBox, SIGNAL("accepted()"), self, SLOT("accept()"))
		self.connect(buttonBox, SIGNAL("rejected()"), self, SLOT("reject()"))
	
		self.resize(max(self.sizeHint().width(), 10), self.sizeHint().height())

	@staticmethod
	def get(lat, long, parent = None):
		dlg = DlgOrigin(lat, long, parent)
		accept = dlg.exec_()
		return(	accept, 
			float(dlg.latutude.text()), 
			float(dlg.longitude.text()))
