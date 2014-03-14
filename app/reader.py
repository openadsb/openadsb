# Classes to read ADSB packets from USB, a file, or maybe network in the future
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

import sys
import usb.core, usb.util
import socket
import time, math
import binascii
import argparse
import Queue
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import decoder
import yappi

packetlog_fname = "packetlog.txt"

# Base class for readers (from USB, serial, file, other?)
#class AdsbReaderThread(threading.Thread):
class AdsbReaderThread(QThread):

    def __init__(self, args, app):
	#threading.Thread.__init__(self)
	QThread.__init__(self)
	self.args = args
	self.app = app
	self.server = None
	self.bad_short_pkts = 0
	self.bad_long_pkts = 0
	self.kill_received = False
	self.decoder = decoder.AdsbDecoder(args, self)
	self.decoder.moveToThread(self)
	self.PACKETLOG = None
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

    def logPacketStr(self, str):
	self.PACKETLOG.write(str)

    def openLogfile(self, name):
	if name != "":
		name = "%s.%s" % (packetlog_fname, name)
	else:
		name = packetlog_fname
	self.PACKETLOG = open(name, "a")
	print "Opened logfile %s" % name
	print self.PACKETLOG

	
    def logfileSize(self):
	return self.PACKETLOG.tell()

    def dumpPacket(self, d):
	ts = time.asctime()
	mystr = ""
	for byte in d:
		mystr += "%02hx " % byte
	print "%s: %u byte packet: %s" % (ts, len(d), mystr)

    # We push received packets out to this server
    def setServer(self, server):
	self.server = server

    def servePacket(self, d):
	# fixme - handle race condition when starting/stopping?
	if(self.server != None):
		d = bytearray(d)		# FIXME - bk this should be a byte array before this call...

		# for now convert this to a string - should probably be done in the server, since it will vary with format
		# My format
		ts = time.time()
		str = ""
		for byte in d:
			str += "%02hx " % byte
		str2 = "%u %u %s\n" % (ts, len(d), str)
		self.server.put(str2)

		# FIXME - "Beast" format: 
		# date    time     packet
		#20120528 12:37:53 *A8000800E6DA2123FDD7BE5052FE;

    @pyqtSlot('int')
    def setDAC(self, v):
	pass

    def setOrigin(self, origin):
	self.decoder.origin = origin

# This class interfaces to a previously recorded file of packets
class AdsbReaderThreadFile(AdsbReaderThread):

    def __init__(self, args, app):
	AdsbReaderThread.__init__(self, args, app)

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
		if (count%5000) == 0:
			time.sleep(0.02)		# yield briefly, since we cannot control thread priority
	#decoder.dumpAircraftTracks()
	return 0

    def run(self):
	#yappi.start()
	print "Reading packets from file ..."
	b = self.read()
	#yappi.print_stats()
	#return b


# This class implements a TCP client which interfaces to a TCP network server to receive packets
# fixme - we should also implement a listening server to which other openadsb apps can push their data
class AdsbReaderThreadSocket(AdsbReaderThread):

    def __init__(self, args, app):
	AdsbReaderThread.__init__(self, args, app)

    def read(self):
	# fixme - use ClientThread here instead?
	ls = 0
	pktCnt = 0
	print "Connecting to server %s:%s..." % (self.args.host, self.args.port)
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((self.args.host, self.args.port))
	sock.send("Hello from OpenADSB\n")
	f = sock.makefile('r', 0)	# create a file-object to read from w/o buffering
	print "Connected to %s:%s" % (self.args.host, self.args.port)
	#self.args.origin = get from server
	self.setOrigin([ 37.37, -122.02 ])
	# fixme - should we have one log file, or one per reader?
	self.openLogfile("socket")

	# fixme - get location info from server 

	d = f.readline();
	while len(d) > 0 and not self.kill_received:
		if len(d) > 0:
			# extract fields
			self.logPacketStr(d)
			s = d.strip().split()
			(ts, nbytes) = (s[0], s[1])
			d = ""
			d = d.join(s[2:]).strip()
			try:
				d = binascii.unhexlify(d)		# hex string to binary
				#self.dumpPacket(d)
				self.servePacket(d)
				self.decoder.decode(d)
				self.decoder.updateStats(0, self.bad_short_pkts, self.bad_long_pkts, self.logfileSize())
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


# This class interfaces to a multithreaded client and/or server, to read incoming packets
class AdsbReaderThreadClientServer(AdsbReaderThread):

    def __init__(self, args, clientserver, app):
	AdsbReaderThread.__init__(self, args, app)
	self.clientserver = clientserver		# client or server
 
    def read(self):
	ls = 0
	pktCnt = 0
	starttime = time.time()
	while not self.kill_received:

		pkt = self.clientserver.get()		# get packet from queue, in form of a string
		print "Got pkt!", type(pkt), pkt
		pktlist = pkt.split("\n")		# network packet may contain a number ADSB packets
		print "pktlist: ", type(pktlist), len(pktlist)

		for d in pktlist:
			print "pkt: ", type(d), len(d)
			if len(d) > 4:
				pktCnt = pktCnt + 1

				# extract fields
				s = d.strip().split()
				(ts, nbytes) = (s[0], s[1])
				d = ""
				d = d.join(s[2:]).strip()
				#print "new d =", type(d), d
				try:
					d = binascii.unhexlify(d)		# hex string to binary
					#self.dumpPacket(d)
					#self.servePacket(d)			# fixme - we don't want to serve back to ourself, right?
					self.decoder.decode(d)
					#self.decoder.updateStats(rxlevel, self.bad_short_pkts, self.bad_long_pkts, self.logfileSize())
				except:
					print "got exception"
					pass
			ls += len(d)

		self.clientserver._free()			# discard memory used by packet

    def run(self):
	# Don't return until the we're killed
	print "Reading packets from network..."
	b = self.read()


# We want to read from the USB port at the highest possible rate, to avoid stalling the receiver. 
# Spawn a high-priority thread to actually read from the port, and enqueue the packets for processing
class UsbServiceThread(QThread):
	def __init__(self, readerThread):
		QThread.__init__(self)
		self.readerThread = readerThread
		self.q = Queue.Queue(maxsize=10)
		self.kill_received = False

	def run(self):
		self.setPriority(QThread.HighPriority)
		pktCnt = 0
		starttime = time.time()
		while not self.kill_received:
			try:
				d = self.readerThread.dev.read(0x81, 64, 0, 10000)
			except:
				# device might have been removed
				# terminate thread
				# FIXME - we should somehow wake our parent waiting on the queue, then tell it to break
				# and release the port handle.  Then return to the main loop looking for another usb device to open
				break

			#if pktCnt % 10 == 0:
				#print "USB read: ", time.time(), len(d), "bytes", pktCnt/(time.time()-starttime), "pkts/sec"

			if len(d) > 0:
				pktCnt = pktCnt + 1
				try:
					self.q.put_nowait(d)
					#if self.q.qsize() > 1:
						#print "USB read: queue size: ", self.q.qsize()
				except: 
					print "USB service thread: queue full, dropping pkt!"

		# flush the queue on exit
		#while not self.q.empty():
			#self.q.get()
			#self.q.task_done()
		# try this - put an empty item in queue to signal that we're done
		self.q.put('')
		print "USB service thread exiting"	# FIXME - deal with q deletion underneath reader thread...

	def get(self):
		return self.q.get()	# blocking read

	def _free(self):
		self.q.task_done()	# done with last data from last get()


# This class interfaces to the ADSB USB dongle
class AdsbReaderThreadUSB(AdsbReaderThread):

    def __init__(self, args, dev, app):
	AdsbReaderThread.__init__(self, args, app)
	self.dev = dev
	self.usbThread = UsbServiceThread(self)		# use another thread to keep servicing port at high rate
 
    def read(self):
	ls = 0
	pktCnt = 0
	starttime = time.time()
	while not self.kill_received:

		d = self.usbThread.get()		# get packet from queue
							# fixme - need some way to exit when usbThread has exited

		if len(d) > 0:
			pktCnt = pktCnt + 1

			rxlevel = (d[0]<<8) | d[1]
			daclevel = (d[2]<<8) | d[3]
			self.bad_short_pkts += int(d[4])
			self.bad_long_pkts += int(d[5])
			d = d[8:]
			self.logPacket(d)
			#self.dumpPacket(d)
			self.servePacket(d)
			self.decoder.decode(d)
			self.decoder.updateStats(rxlevel, self.bad_short_pkts, self.bad_long_pkts, self.logfileSize())
		else:
			# zero-length item indicates we're done
			self.kill_received = True

		ls += len(d)
		self.usbThread._free()			# discard memory used by packet

    def run(self):
	#yappi.start()
	#print "Logging received packets to file %s" % (packetlog_fname)
	#self.PACKETLOG = open(packetlog_fname, "a")		# append to log
	self.openLogfile("")

	# FIXME - treat this like a server.  For each device found, spawn a new thread to service it.
	# That thread terminates when the device is removed.  New devices are picked up automatically

	#while not self.kill_received:
		# how to wake when new usb device inserted?
	# Open the USB device. deal with multiple devices.  pick the first available
#	print "Opening USB device..."
#	dev_list = usb.core.find(idVendor=0x9999, idProduct=0xffff, find_all=True)
#	print dev_list
#	for self.dev in dev_list:
#		print self.dev
#		self.manufacturer = usb.util.get_string(self.dev, 256, self.dev.iManufacturer)
#		self.product = usb.util.get_string(self.dev, 256, self.dev.iProduct)
#		self.serialNumber = usb.util.get_string(self.dev, 256, self.dev.iSerialNumber)
#		print "Manufacturer: ",self.manufacturer
#		print "Serial Number: ",self.serialNumber
#		print "Product: ",self.product
#
#		try:
#			print "trying ",vars(self.dev)
#			self.dev.set_configuration(1)
#			print "found one!"
#			break
#		except:
#			pass
#
	if self.args.daclevel != None:
		print "Setting DAC level to 0x%x" % (self.args.daclevel)
		self.setDAC(self.args.daclevel)

	print "Reading packets from USB device..."
	self.usbThread.start()

	# Don't return until the USB device is removed.
	b = self.read()
	print "read returned ",b

	# kill USB service thread
	self.usbThread.kill_received = True
	self.usbThread.wait()

	#yappi.print_stats(sys.stdout, yappi.SORTTYPE_TTOTAL)
	#yappi.print_stats()
	#return b

    def sendOut(self, d):
	self.dev.write(0x02, d, 0, 100)

    def vendorGet(self):
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0x23, 0, 0, 64)

    def countersGet(self):
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0x25, 0, 0, 64)
    
    def bootloader(self):
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0xbb, 0, 0, 64)

    @pyqtSlot('int')
    def setDAC(self, v):
	#print "AdsbReaderThreadUSB::setDAC to %d" % (v)
	return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0xda, v&0xFFFF, 0, 64)


# long-running thread which looks for USB devices inserted or removed
class UsbHotplugWatcher(QThread):

	def __init__(self, app):
		QThread.__init__(self)
		self.app = app
		self.kill_received = False
		self.active_devs = []	

	def run(self):
		print "Started USB Hotplug Watcher Thread"
		self.setPriority(QThread.LowPriority)

		readers = []
		while not self.kill_received:
			dev_list = usb.core.find(idVendor=0x9999, idProduct=0xffff, find_all=True)
			#print dev_list
			for dev in dev_list:
				unique_id = "%d:%d" % (dev.bus, dev.address)
				if not unique_id in self.active_devs:
					print "Opening USB device", dev, "..." 
					manufacturer = usb.util.get_string(dev, 256, dev.iManufacturer)
					product = usb.util.get_string(dev, 256, dev.iProduct)
					serialNumber = usb.util.get_string(dev, 256, dev.iSerialNumber)
					print "Manufacturer: ",manufacturer
					print "Serial Number: ",serialNumber
					print "Product: ",product
					print dev.bus, dev.address

					try:
						print "trying ",vars(dev)
						dev.set_configuration(1)
						cfg = dev.get_active_configuration()
						iface = cfg[(0,0)].bInterfaceNumber
						try:
							usb.util.claim_interface(dev, iface)
						except:
							print "couldn't claim interface %d!" % (iface)
							
						# successfully opened device.  start a reader thread for it
						print "found one!"
						self.active_devs.append(unique_id)
						r = AdsbReaderThreadUSB(self.app.args, dev, self.app)
						readers.append(r)
						self.emit (SIGNAL("addReader(PyQt_PyObject)"), r)
					
					except:
						pass


			# fixme - need to remove this device from active_devs when removed
			# if the thread has terminated, assume it was removed
			for r in readers:
				if r.isFinished():
					print r,"is finished"
					r.wait()
					readers.remove(r)
					print r,"is removed from list"
					# fixme - also need to remove the dev from active_devs
				

			# pyusb doesn't support hotplug events yet, so just poll at low rate
			time.sleep(30000)

		print "USB Hotplug Watcher thread exiting"
	
