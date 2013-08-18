# Widget to display the data feeds
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

import sys
import time
import aircraft
from settings import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *

thread = None

# Subclass QTableWidgetItem
class MyTableWidgetItem(QTableWidgetItem):
	def __init__(self, item):
		QTableWidgetItem.__init__(self, item)
		self.aa = None		# will set this for AA-specific cells, to simplify sorting

	def __lt__(self, other):	# less than operator, for sorting
		sfloat = self.text().toFloat() 		# returns a tuple: (result, valid)
		ofloat = other.text().toFloat()
		if sfloat[1] & ofloat[1] == True:
			return sfloat[0] < ofloat[0]
		else:
			return QTableWidgetItem.__lt__(self, other)

# Subclass QTableWidget
class MyTableWidget(QTableWidget):
    def __init__(self, hhdr, mainWindow):
        QTableWidget.__init__(self, 0, len(hhdr))
	self.mainWindow = mainWindow
	self.mutex = QMutex()		
	self.setHorizontalHeaderLabels(hhdr)
        self.rownum = dict()		# row number by AA
	self.lastSortCol = 0
	self.sortAlways = True
	self.lastSortOrder = Qt.AscendingOrder
	self.connect(self.horizontalHeader(), SIGNAL("sectionClicked(int)"), self.sortCol)

	# enable draggable columns
	# note, column numbers seem to be the same, even after moving them
	self.setDragDropOverwriteMode(True)
	self.setDragEnabled(True)
	self.setDragDropMode(QAbstractItemView.InternalMove)
	self.setSelectionBehavior(QAbstractItemView.SelectRows)
	self.horizontalHeader().setMovable(True)
	self.verticalHeader().setMovable(True)
        
	# load window geometry and state from previous settings 
	settings = mySettings()
	settings.beginGroup("feedsTable")
	self.restoreGeometry(settings.value("geometry").toByteArray())
	self.horizontalHeader().restoreState(settings.value("header").toByteArray())
	settings.endGroup()


    def saveSettings(self):
	settings = mySettings()
	settings.beginGroup("feedsTable")
	settings.setValue("geometry", self.saveGeometry())
	settings.setValue("header", self.horizontalHeader().saveState())
	settings.endGroup()

    # we want resizeColumnnsToContents() to consider all rows, not just the visible ones
    def resize(self):
    	#self.setVisible(False)		# this is a hack - causes weirdness...
	self.resizeColumnsToContents()
    	#self.setVisible(True)		# this is a hack
	
    # These are SLOTS
    def addRow(self, id, columnlist):	
	self.mutex.lock() 		# disable sorting around this addition
	rows = self.rowCount()
	self.setRowCount(rows+1)
	m = rows
	#self.connect(checkbox, SIGNAL("stateChanged(int, int)"), self.mainWindow.gmapsWindow.setTrackVisible)
	n = 1
	for item in columnlist:
                newitem = MyTableWidgetItem(item)
                self.setItem(m, n, newitem)
		n += 1
	self.rownum[int(id)] = m
	self.item(m, 2).aa = int(id)	# AA in column 2
	self.mutex.unlock()
	self.resize()
	if self.sortAlways:
		self.doSort(self.lastSortCol, self.lastSortOrder)
	return m

    def delRow(self, row):
	self.removeRow(row)
	
    def delRowByID(self, id):
	row = self.rownum[int(id)]
	if row != None:
		self.delRow(row)
	return

    def setHighlightRow(self, aa, val):
	row = self.rownum[int(aa)]
	if row != None:
		if val:
			print "setHighlightRow on for row ", row
			self.selectRow(row);
		else:
			print "setHighlightRow off for row ", row
			self.selectRow(-1);
	return

    def updateRowByID(self, id, columnlist):
	row = self.rownum[int(id)]
	if row != None:
		n = 1
		for col in columnlist:
			item = self.item(row, n)
			item.setText(col)
			n += 1
	#self.resize()
	if self.sortAlways:
		self.doSort(self.lastSortCol, self.lastSortOrder)
	return

    # if clicked on a header column, sort by that column
    def sortCol(self, col):
	if self.lastSortCol != col:
		order = Qt.AscendingOrder
	elif (self.lastSortOrder == Qt.AscendingOrder):
		order = Qt.DescendingOrder
	else:
		order = Qt.AscendingOrder
	self.doSort(col, order)
	self.saveSettings()

    def doSort(self, col, order):
	print "sort on col ",col
	self.mutex.lock()
	self.lastSortCol = col
	self.lastSortOrder = order
	self.sortItems(col, order)

	# rebuild our index
	self.rownum = dict()
	for row in range(self.rowCount()):
		id = self.item(row, 2).aa	# aa
		self.rownum[id] = row
	self.mutex.unlock()


class AdsbFeedsWidget(MyTableWidget):

	def __init__(self, mainWindow):
		hdrs = [	'Use', 'Name', 'Location', 'Connection', 'Status', 'Mfg.', 'Product', 'Serial No.', 'Version', 'Pkts' ]
		MyTableWidget.__init__(self, hdrs, mainWindow)

	# These are SLOTS
	def addFeed(self, ac):
		self.addRow(0, [ 'testing, roof ant.', '37.2 N, 121.0 W', 'USB', 'Connected', 'openadsb', 'ADS-B 1090 MHz USB Receiver', '138413235343FFFF70FF60004100', '1.01', '451520' ])
		self.addRow(0, [ 'testing, window', '37.2 N, 121.0 W', 'USB', 'Connected', 'openadsb', 'ADS-B 1090 MHz USB Receiver', '138413235343FFFF70FF60004200', '1.01', '1103' ])
		self.addRow(0, [ 'testing, remote', '39.9 N, 120.0 W', '63.23.55.124', 'Connected as client', 'openadsb', 'ADS-B 1090 MHz USB Receiver', '138413235343FFFF70FF60004500', '1.00a', '15230' ])
		#QSound.play("beep2.wav");

	def updateFeed(self, ac):
		pass

	def delFeed(self, ac):
		self.delRowByID(ac.aa)
	

if __name__ == '__main__':
	import sys, time
        app = QApplication(sys.argv)
	m = QMainWindow()

	f = AdsbFeedsWidget(m)
	f.addFeed(None)	
	f.show()
	f.raise_()
	app.exec_()


