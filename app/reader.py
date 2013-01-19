# Classes to read ADSB packets from USB, a file, or maybe network in the future
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

import sys
import usb.core, usb.util
import socket
import time, math
import binascii
import argparse
#import threading
from PyQt4.QtCore import *
import decoder
import yappi

packetlog_fname = "packetlog.txt"

# Base class for readers (from USB, serial, file, other?)
#class AdsbReaderThread(threading.Thread):
class AdsbReaderThread(QThread):

    def __init__(self, args):
	#threading.Thread.__init__(self)
	QThread.__init__(self)
	self.args = args
	self.server = None
	self.bad_short_pkts = 0
	self.bad_long_pkts = 0
	self.kill_received = False
	self.decoder = decoder.AdsbDecoder(args)
	self.decoder.moveToThread(self)
	#self.yappi = yappi
	#self.yappi.start()

    #def __del__(self):
	#self.yappi.print_stats()
	#QThread.__del__(self)

    def getDecoder(self):
	return self.decoder

    def logPacket(self, d):
	ts = time.time()
	str = ""
	for byte in d:
		str += "%02hx " % byte
	str2 = "%u %u %s\n" % (ts, len(d), str)
	self.PACKETLOG.write(str2)

    def logfileSize(self):
	return self.PACKETLOG.tell()

    def dumpPacket(self, d):
	ts = time.asctime()
	mystr = ""
	for byte in d:
		mystr += "%02hx " % byte
	print "%s: %u byte packet: %s" % (ts, len(d), mystr)

    def setServer(self, server):
	self.server = server

    def servePacket(self, d):
	# fixme - handle race condition when starting/stopping?
	if(self.server != None):
		# for now convert this to a string - should probably be done in the server, since it will vary with format
		ts = time.time()
		str = ""
		for byte in d:
			str += "%02hx " % byte
		str2 = "%u %u %s\n" % (ts, len(d), str)
		self.server.put(str2)

    def setDAC(self, v):
	# dummy 
	pass

# This class interfaces to a previously recorded file of packets
class AdsbReaderThreadFile(AdsbReaderThread):

    def __init__(self, args):
	AdsbReaderThread.__init__(self, args)

    def __del__(self):
	pass
	#AdsbReaderThread.__del__(self)

    # fixme - handle timestamps in file
    def read(self):
	fname = self.args.filename;
	count = int(self.args.count);
	skip = int(self.args.skip);
	ls = 0
	pktCnt = 0
	RDONLY_PACKETLOG = open(fname, "r")	# read only
	while skip > 0:
		d = RDONLY_PACKETLOG.readline();
		skip -= 1

	d = RDONLY_PACKETLOG.readline();
	while count != 0 and len(d) > 0 and not self.kill_received:
		count -= 1
		if len(d) > 0:
			# extract fields
			s = d.strip().split()
			#print s
			(ts, nbytes) = (s[0], s[1])
			d = ""
			d = d.join(s[2:]).strip()
			#print d
			#print type(d), len(d)
			#print type(binascii.a2b_hex(d))
			try:
				d = binascii.unhexlify(d)		# hex string to binary
				#self.dumpPacket(d)
				self.servePacket(d)
				self.decoder.decode(d)
				self.decoder.updateStats(0, self.bad_short_pkts, self.bad_long_pkts, RDONLY_PACKETLOG.tell())
			except:
				pass
		ls += len(d)
		d = RDONLY_PACKETLOG.readline();
		if (count%5) == 0:
			time.sleep(0.02)		# yield briefly, since we cannot control thread priority
	#decoder.dumpAircraftTracks()
	return 0

    def run(self):
	yappi.start()
	print "Reading packets from file ..."
	b = self.read()
	yappi.print_stats()
	#return b


# This class implements a TCP client which interfaces to a TCP network server to receive packets
# fixme - we should also implement a listening server to which other openadsb apps can push their data
class AdsbReaderThreadSocket(AdsbReaderThread):

    def __init__(self, args):
	AdsbReaderThread.__init__(self, args)

    def __del__(self):
	pass
	#AdsbReaderThread.__del__(self)

    def read(self):
	ls = 0
	pktCnt = 0
	print "Connecting to server %s:%s..." % (self.args.host, self.args.port)
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((self.args.host, self.args.port))
	sock.send("Hello from OpenADSB\n")
	f = sock.makefile('r', 0)	# create a file-object to read from w/o buffering

	d = f.readline();
	while len(d) > 0 and not self.kill_received:
		if len(d) > 0:
			# extract fields
			print "Got message from server! ",d
			s = d.strip().split()
			(ts, nbytes) = (s[0], s[1])
			d = ""
			d = d.join(s[2:]).strip()
			try:
				d = binascii.unhexlify(d)		# hex string to binary
				#self.dumpPacket(d)
				self.servePacket(d)
				self.decoder.decode(d)
				self.decoder.updateStats(0, self.bad_short_pkts, self.bad_long_pkts, RDONLY_PACKETLOG.tell())
			except:
				pass
		ls += len(d)
		d = f.readline();
	print "Disconnecting from server %s:%s" % (self.args.host, self.args.port)
	return 0

    def run(self):
	print "Reading packets from network..."
	b = self.read()
	return b


# This class interfaces to the ADSB USB dongle
class AdsbReaderThreadUSB(AdsbReaderThread):

    def __init__(self, args):
	AdsbReaderThread.__init__(self, args)

    #def __del__(self):
	#pass

    def read(self):
	ls = 0
	pktCnt = 0
	while not self.kill_received:
		#try:
			#d = self.dev.read(0x81, 64, 0, 100)
		d = self.dev.read(0x81, 64, 0, 10000)
		#except:							# use a 5-second timer to age aircraft?
			#break

		if len(d) > 0:
			rxlevel = (d[0]<<8) | d[1]
			daclevel = (d[2]<<8) | d[3]
			self.bad_short_pkts += int(d[4])
			self.bad_long_pkts += int(d[5])
			#print "rxlevel=%u, dac=%u, bad_short_pkts=%u, bad_long_pkts=%u" % (rxlevel, daclevel, self.bad_short_pkts, self.bad_long_pkts)
			d = d[8:]
			self.logPacket(d)
			self.dumpPacket(d)
			self.servePacket(d)
			self.decoder.decode(d)
			self.decoder.updateStats(rxlevel, self.bad_short_pkts, self.bad_long_pkts, self.logfileSize())
		ls += len(d)

    def run(self):
	yappi.start()
	print "Logging received packets to file %s" % (packetlog_fname)
	self.PACKETLOG = open(packetlog_fname, "a")		# append to log

	# Open the USB device
	print "Opening USB device..."
	#self.dev = usb.core.find(idVendor=0x9999, idProduct=0xffff)
	# deal with multiple devices.  pick the first available
	dev_list = usb.core.find(idVendor=0x9999, idProduct=0xffff, find_all=True)
	print dev_list
	for self.dev in dev_list:
		print self.dev
		self.manufacturer = usb.util.get_string(self.dev, 256, self.dev.iManufacturer)
		self.product = usb.util.get_string(self.dev, 256, self.dev.iProduct)
		self.serialNumber = usb.util.get_string(self.dev, 256, self.dev.iSerialNumber)
		print "Manufacturer: ",self.manufacturer
		print "Serial Number: ",self.serialNumber
		print "Product: ",self.product

		try:
			print "trying ",self.dev
			self.dev.set_configuration(1)
			print "found one!"
			break
		except:
			pass

	if self.args.daclevel != None:
		print "Setting DAC level to 0x%x" % (self.args.daclevel)
		self.setDAC(self.args.daclevel)

	print "Reading packets from USB device..."
	# Don't return until the USB device is removed.
	b = self.read()
	print "read returned ",b
	#yappi.print_stats(sys.stdout, yappi.SORTTYPE_TTOTAL)
	yappi.print_stats()
	#return b

    def sendOut(self, d):
	self.dev.write(0x02, d, 0, 100)

    def vendorGet(self):
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0x23, 0, 0, 64)

    def countersGet(self):
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0x25, 0, 0, 64)
    
    def bootloader(self):
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0xbb, 0, 0, 64)

    def setDAC(self, v):
	print "setDAC to %d" % (v)
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0xda, v&0xFFFF, 0, 64)

