# Database access functions for OpenADSB
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#
import string
import sys
import re
import time
from PyQt4.QtCore import *
from PyQt4.QtSql import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import *

# object holding database-info for an aircraft
class AircraftDbInfo():
	def __init__(self, aa):
		self.aa = aa
		self.registrationStr = ""
		self.yearBuilt = ""
		self.acMfgStr = ""
		self.acModelStr = ""
		self.acTypeStr = ""
		self.numEng = 0
		self.typeEngStr = ""
		self.numSeats = 0
		self.tailNumStr = ""
		self.ownerStr = ""
		self.ownerCityStr = ""
		self.ownerStateStr = ""
		self.ownerCountryStr = ""
		self.engMfgStr = ""
		self.engModelStr = ""
		self.engTypeStr = ""
		self.engPowerStr = ""
		
	def dump(self):
		print "---------------"
		print "N-%s has ICAO24%X"%(self.registrationStr, self.aa)
		print "%s %s %s, %u seats" % (self.yearBuilt, self.acMfgStr, self.acModelStr, self.numSeats)
		print "%u engines, %s %s" % (self.numEng, self.engTypeStr, self.engPowerStr)
		print "%s, %s, %s %s" % (self.ownerStr, self.ownerCityStr, self.ownerStateStr, self.ownerCountryStr)
		print "---------------"

class AircraftDb(QObject):
	def __init__(self):
		QObject.__init__(self)
		self.db = QSqlDatabase.addDatabase("QMYSQL")
		self.db.setHostName("db1.openadsb.com")
		self.db.setDatabaseName("openadsb1")
		self.db.setUserName("openadsb1user")
		self.db.setPassword("Password#1")

	#def result(self):
		#pass

	def connectDb(self):
		if self.db.isOpen():
			return
		ok = self.db.open()
		if self.db.isOpen():
			print "Database connection opened successfully"
		else:
			str = "Unknown error"
			if self.db.isOpenError():
				err = self.db.lastError()
				if err.isValid():
					str = err.databaseText() + ', ' + err.driverText()
			print "Database connection opened failed: %s" % (str)
		
		return ok

	def getDbSize(self):
		self.connectDb()
		query = QSqlQuery()
		query.setForwardOnly(True)
		query.exec_("SELECT * FROM faa_engine")
		defaultDB = QSqlDatabase.database()
		if (defaultDB.driver().hasFeature(QSqlDriver.QuerySize)):
			numRows = query.size()
			#print "size %d" % (numRows)
		else:
			# this can be very slow
			query.last()
			numRows = query.at() + 1;
			#print "query %d" % (numRows)
		return numRows

	def lookupEngineByCode(self, code):
		self.connectDb()
		query = QSqlQuery()
		query.setForwardOnly(True)
		qstr = "SELECT MFR, MODEL, TYPE, HORSEPOWER, THRUST FROM faa_engine WHERE CODE = %s" % (code)
		query.exec_(qstr)
		if query.lastError().isValid():
			print "Database error: %s, %s" % (query.lastError().databaseText(), query.lastError().driverText())

		while (query.next()):
			mfg = query.value(0).toString().trimmed();
			model = query.value(1).toString().trimmed()
			type = query.value(2).toInt()[0]
			if type == 0:
				type = 'None'
			elif type == 1:
				type = 'Reciprocating'
			elif type == 2:
				type = 'Turbo-prop'
			elif type == 3:
				type = 'Turbo-shaft'
			elif type == 4:
				type = 'Turbo-jet'
			elif type == 5:
				type = 'Turbo-fan'
			elif type == 6:
				type = 'Ramjet'
			elif type == 7:
				type = '2 Cycle'
			elif type == 8:
				type = '4 Cycle'
			elif type == 9:
				type = 'Unknown'
			elif type == 10:
				type = 'Electric'
			elif type == 11:
				type = 'Rotary'

			horsepower = query.value(3).toInt()[0];
			thrust = query.value(4).toInt()[0];
			if horsepower == 0:
				power = "%i lbs thrust" % (thrust)
			else:
				power = "%i hp" % (horsepower)

			#print mfg, model, type, power,horsepower, thrust
			#print mfg, model, type, power
			#print mfg, model, type, power
			#print mfg, model
			#print type, power
			return [ mfg, model, type, power ]

		return [ None, None, None, None ]

	def lookupModelByMfgCode(self, code):
		self.connectDb()
		query = QSqlQuery()
		query.setForwardOnly(True)
		qstr = "SELECT `MFR`, `MODEL`, `TYPE-ACFT`, `NO-ENG`, `TYPE-ENG`, `NO-SEATS` FROM `ACFTREF` WHERE `CODE` = '%s'" % (code)
		#print qstr
		query.exec_(qstr)
		if query.lastError().isValid():
			print "Database error: %s, %s" % (query.lastError().databaseText(), query.lastError().driverText())

		# fixme - this only gets the first record...
		while (query.next()):
			mfg = query.value(0).toString().trimmed()
			model = query.value(1).toString().trimmed()
			typeac = int(query.value(2).toString().trimmed())
			numeng = int(query.value(3).toString().trimmed())
			typeeng = int(query.value(4).toString().trimmed())
			numseats = int(query.value(5).toString().trimmed())
			if typeac == 1:
				typeac = 'Glider'
			elif typeac == 2:
				typeac = 'Balloon'
			elif typeac == 3:
				typeac = 'Blimp'
			elif typeac == 4:
				typeac = 'Fixed-wing single-engine'
			elif typeac == 5:
				typeac = 'Fixed-wing multi-engine'
			elif typeac == 6:
				typeac = 'Helicopter'
			elif typeac == 7:
				typeac = 'Weight-shift-control'
			elif typeac == 8:
				typeac = 'Powered parachute'
			elif typeac == 9:
				typeac = 'Gyroplane'
			else:
				typeac = 'unknown type %u' % actype
			return [ mfg, model, typeac, numeng, typeeng, numseats ]

	def lookupAircraftByICAO24(self, aa):
		self.connectDb()
		oct_aa = ("%o"%int(aa, 16))
		# strip leading zeroes
		oct_aa = re.sub("^0+", "", oct_aa)		
		query = QSqlQuery()
		query.setForwardOnly(True)
		qstr = "SELECT `N-NUMBER`, NAME, CITY, STATE, COUNTRY, `MFR MDL CODE`, `ENG MFR MDL`, `YEAR MFR` FROM `MASTER` WHERE `MODE S CODE` = '%s'" % (oct_aa)
		query.exec_(qstr)	
		if query.lastError().isValid():
			print "Database error: %s, %s" % (query.lastError().databaseText(), query.lastError().driverText())
			# try again
			self.db.close()
			self.connectDb()
			query = QSqlQuery()
			query.setForwardOnly(True)
			query.exec_(qstr)

		# fixme - this only gets the first record...
		while (query.next()):
			nnum = query.value(0).toString().trimmed()
			owner = query.value(1).toString().trimmed()
			city = query.value(2).toString().trimmed()
			state = query.value(3).toString().trimmed()
			country = query.value(4).toString().trimmed()
			accode = query.value(5).toString().trimmed()
			ecode = query.value(6).toString().trimmed()
			year = query.value(7).toString().trimmed()
			return [ True, nnum, owner, city, state, country, accode, ecode, year ]

		return [ False, False, False, False, False, False, False, False, False ]

	# Slot which listens for new aircraft being detected
	# perform database lookup and emit signal with database info
	def addAircraft(self, ac):
		i = AircraftDbInfo(ac.aa)
		aa = "%X"%ac.aa
		print "AircraftDb() addAircraft called for %s" % aa
		[ ok, i.registrationStr, i.ownerStr, i.ownerCityStr, i.ownerStateStr, i.ownerCountryStr, accode, ecode, i.yearBuilt ] = self.lookupAircraftByICAO24(aa)
		if ok:
			[ i.acMfgStr, i.acModelStr, i.acTypeStr, i.numEng, i.engTypeStr, i.numSeats ] = self.lookupModelByMfgCode(accode)
			[ i.engMfgStr, i.engModelStr, i.engTypeStr, i.engPowerStr ] = self.lookupEngineByCode(ecode)
			i.dump()
			self.emit(SIGNAL("updateAircraftDbInfo(PyQt_PyObject)"), i)
		else:
			print "ICAO24 %s not found in database." % (aa)


# Use QThread to run the db query in a background thread.
class AircraftDbThread(QThread):
	def __init__(self):
		QThread.__init__(self)
		self.setObjectName("DB Thread")
		self.db = AircraftDb()
		# This object exists in caller's thread context.  Move it to our thread content so signal/slots work
		self.db.moveToThread(self)	
		self.start()

	def run(self):
		self.db.connectDb()
		print "Connected to DB"
		self.exec_()				# run the event loop
		print "AircraftDbThread() exiting"
	
	def shutdown(self):
		print "shutting down db thread"
	

########################################################################################################
# for testing only
#
def printAircraftInfo(db, code):
	[ ok, nnum, owner, city, state, country, accode, ecode, year ] = db.lookupAircraftByICAO24(code)
	if ok:
		[ mfg, model, typeac, numeng, typeeng, numseats ] = db.lookupModelByMfgCode(accode)
		[ emfg, emodel, type, power ] = db.lookupEngineByCode(ecode)
		print "---------------"
		print code
		print "N-%s"%(nnum)
		print year, mfg, "%s,"%model, "%u seats"%(numseats)
		print "%u engines,"%(numeng), type, power
		print owner, ",", city, ",", state, country
		print "---------------"
	else:
		print "ICAO24 %s not found in database." % (code)

def main():
	argc = len(sys.argv)
	app = QApplication(sys.argv)
	db = AircraftDb()
	db.connectDb()
	if argc > 1:
		idx = 1
		while (idx < argc):
			aa = sys.argv[idx]
			idx += 1
			printAircraftInfo(db, aa)
	else:
		print "%d records in the DB" % (db.getDbSize())
		printAircraftInfo(db, 'A6A3C2')
		printAircraftInfo(db, 'A12345')
		printAircraftInfo(db, 'AB1DB2')
		printAircraftInfo(db, 'A4E108')
		printAircraftInfo(db, 'A71D34')
		printAircraftInfo(db, 'A1FF06')
		printAircraftInfo(db, 'A34B10')
	sys.exit(0)


if __name__ == "__main__":
	main()
