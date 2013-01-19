# Display a list of aircraft in an updating table widget
# Even though many values are floating point, we want to display them as text, so we can display an 'empty' value
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

import sys
import time
import aircraft
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

	#def __gt__(self, other):	# greater than operator, for sorting
		#print "custom operator!"
		#return 0

# Subclass QTableWidget
class MyTableWidget(QTableWidget):
    def __init__(self, hhdr):
        QTableWidget.__init__(self, 0, len(hhdr))
	self.sortAlways = False		# if true, sort on each table update
	self.mutex = QMutex()		
	self.setHorizontalHeaderLabels(hhdr)
        self.rownum = dict()		# row number by AA
	self.lastSortCol = 0
	self.lastSortOrder = Qt.AscendingOrder
	self.connect(self.horizontalHeader(), SIGNAL("sectionClicked(int)"), self.sortCol)
        
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
	n = 0
	for item in columnlist:
                newitem = MyTableWidgetItem(item)
                self.setItem(m, n, newitem)
		n += 1
	self.rownum[int(id)] = m
	self.item(m, 1).aa = int(id)	# AA in column 1
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

    def updateRowByID(self, id, columnlist):
	row = self.rownum[int(id)]
	if row != None:
		n = 0
		for col in columnlist:
			item = self.item(row, n)
			item.setText(col)
			n += 1
	#self.resize()
	if self.sortAlways:
		self.doSort(self.lastSortCol, self.lastSortOrder)
	return

    def updateDbInfo(self, i):
	row = self.rownum[i.aa]
	print "row = %d", row
	if row != None:
		text = "N%s" % i.registrationStr		# fixme - USA only
		item = self.item(row, 19)
		item.setText(text)

		item = self.item(row, 20)
		item.setText(i.acTypeStr)

		text = "%s %s %s, %u seats, %u %s engines with %s" % (i.yearBuilt, i.acMfgStr, i.acModelStr, i.numSeats, i.numEng, i.engTypeStr, i.engPowerStr)
		item = self.item(row, 21)
		item.setText(text)

		text = "%s, %s, %s %s" % (i.ownerStr, i.ownerCityStr, i.ownerStateStr, i.ownerCountryStr)
		item = self.item(row, 22)
		item.setText(text)
	if self.sortAlways:
		self.doSort(self.lastSortCol, self.lastSortOrder)
	#self.resize()
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

    def doSort(self, col, order):
	print "sort on col ",col
	self.mutex.lock()
	self.lastSortCol = col
	self.lastSortOrder = order
	self.sortItems(col, order)

	# rebuild our index
	self.rownum = dict()
	for row in range(self.rowCount()):
		id = self.item(row, 1).aa	# first row has aa
		self.rownum[id] = row
	self.mutex.unlock()


# TableWidget for ADSB display
class AdsbTableWidget(MyTableWidget):

	def __init__(self):
		hdrs = [	'Time', 'ICAO24', 'Country', 'Flight ID', 'Status', 'Range', 'Elevation', 
				'Azimuth', 'Position', 'Altitude', 'Vertical rate', 'Heading', 'Airspeed', 
				'Ground speed', 'Squawk', 'Category', 'Max speed', 'Packets', 'Track Points', 'Tail Number', 'Type', 'Kind', 'Owner' ]
		MyTableWidget.__init__(self, hdrs)

	# fixme - squawk should highlight for special codes
	# 1200 (VFR)
	# 2000 (no transponder instructions)
	# 7500 (hijack), 
	# 7600 (radio failure), 
	# 7700 (emergency), 
	# ident bit should highlight row

	# These are SLOTS
	def addAircraft(self, ac):
		#print "addRow: %X" % (ac.aa)
		self.addRow(ac.aa, [ str(ac.timestamp), ("%X"%ac.aa), ac.countryStr, ac.idStr, ac.fsStr, ac.rangeStr, ac.elevStr, ac.bearingStr, 
					ac.posStr, str(ac.alt), ac.vertStr, ac.heading, ac.velStr,
					'', ac.squawkStr, ac.catStr, ac.riStr, str(ac.pkts), str(len(ac.track)), '', '', '', '' ])
		#QSound.play("TerminalBeep.wav");
		QSound.play("beep2.wav");

	def updateAircraft(self, ac):
		self.updateRowByID(ac.aa, [ str(ac.timestamp), ("%X"%ac.aa), ac.countryStr, ac.idStr, ac.fsStr, ac.rangeStr, ac.elevStr, ac.bearingStr, 
					ac.posStr, str(ac.alt), ac.vertStr, ac.headingStr, ac.velStr,
					'', ac.squawkStr, ac.catStr, ac.riStr, str(ac.pkts), str(len(ac.track)) ])

	def delAircraft(self, ac):
		#print "delAircraft called"
		self.delRowByID(ac.aa)
	
	def updateAircraftDbInfo(self, info):
		# called from dbThread
		self.updateDbInfo(info)
		print info

