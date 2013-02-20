# make this a storage place for all our settings.
# emit SIGNAL when settings change, listeners can update if necessary

import sys
from PyQt4.QtCore import *

class mySettings(QSettings):
	def __init__(self, parent = None):

		# store settings in the same directory as our files
		loc = QFileInfo(sys.argv[0])
                path = loc.absolutePath() + "/openadsb.ini"
		QSettings.__init__(self, path, QSettings.IniFormat, parent)

		# or, store settings in native format
		#QSettings.__init__(self, parent)


