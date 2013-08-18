# Read ADSB packets from USB, and serve them over a network connection
# This provides a standalone server which doesn't do any decoding
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

import sys
import usb.core, usb.util
import socket
import time
import binascii
import argparse
import decoder
import threading
import signal
import random
from server import *
from client import *

packetlog_fname = "packetlog.txt"

# This class interfaces to the ADSB USB dongle
class AdsbReaderThreadUSB(threading.Thread):

	def __init__(self, serverThread, args, fname = None, dacval = -1):		
		threading.Thread.__init__(self)
		self.args = args
		self.serverThread = serverThread
		self.packetlog_fname = fname
		self.dacval = dacval
		self.kill_received = False
		self.PACKETLOG = None
		self.dev = None
		self.manufacturer = ''
		self.product = ''
		self.serialNumber = ''
		self.deviceName = ''
		self.friendlyName = ''
		self.location = [ 0, 0, 0 ]

	def setLocation(self, loc):
		self.location = loc

	def setFriendlyName(self, name):
		self.friendlyName = name

	def run(self):
		if self.openUSB() == None:
			print "Couldn't open an ADSB USB device... exiting"
			return

		# give server an announcement string
		self.serverThread.setFriendlyName(self.friendlyName)
		self.serverThread.setDeviceName(self.deviceName)
		self.serverThread.setLocation(self.location)

		# append to log
		if self.packetlog_fname != None and self.packetlog_fname != '':
			print "Logging received packets to file %s" % (self.packetlog_fname)
			self.PACKETLOG = open(self.packetlog_fname, "a")		

		# set DAC once or dither in background
		if self.args.ditherdac:
			self.dacThread = DitherDacThread(self)
			self.dacThread.start()
		else:
			self.setDAC(self.dacval)

		# start reading
		#self.setPriority(QThread.HighPriority)
		pktCnt = 0
		starttime = time.time()
		while not self.kill_received:
			try:
				d = self.dev.read(0x81, 64, 0, 10000)
			except:
				# device might have been removed
				# terminate thread
				break

			#if pktCnt % 10 == 0:
				#print "USB read: ", time.time(), len(d), "bytes", pktCnt/(time.time()-starttime), "pkts/sec"

			if len(d) > 0:
				pktCnt = pktCnt + 1
				pkt = self.makePacket(d)
				self.serverThread.put(pkt + '\n')
				
				if self.PACKETLOG:
					self.PACKETLOG.write(pkt)

				if self.args.verbose:
					print pkt

		print "USB reader thread exiting"	
		self.dacThread.shutdown()

	# Given a data packet from the USB device, construct a network packet
	def makePacket(self, d):
		ts = time.time()
		d = d[8:]		# skip first 8 bytes of header
		d = bytearray(d)
		pkt = "%u %u " % (ts, len(d))
		for byte in d:
			pkt += "%02hx " % byte
		return pkt

	# This is only used in client-mode
	def connectAsClient(self):
		print "Connecting to server %s:%s..." % (self.host, self.port)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((self.host, self.port))
		sock.send("Hello from OpenADSB\n")
		#f = sock.makefile('r', 0)	# create a file-object to read from w/o buffering

	def openUSB(self):
		# Open the USB device. deal with multiple devices.  pick the first available
		print "Opening USB device..."
		dev_list = usb.core.find(idVendor=0x9999, idProduct=0xffff, find_all=True)
		for self.dev in dev_list:
			self.manufacturer = usb.util.get_string(self.dev, 256, self.dev.iManufacturer)
			self.product = usb.util.get_string(self.dev, 256, self.dev.iProduct)
			self.serialNumber = usb.util.get_string(self.dev, 256, self.dev.iSerialNumber)
			print "Manufacturer:  ",self.manufacturer
			print "Product:       ",self.product
			print "Serial Number: ",self.serialNumber

			try:
				self.dev.set_configuration(1)
				self.deviceName = "%s/%s/%s" % (self.manufacturer, self.product, self.serialNumber)
				print "Opened successfully!"
				break
			except:
				print "Couldn't open!"
				pass
		return self.dev

	def sendOut(self, d):
		self.dev.write(0x02, d, 0, 100)

	def vendorGet(self):
		return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0x23, 0, 0, 64)

	def countersGet(self):
		return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0x25, 0, 0, 64)

	def bootloader(self):
		return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0xbb, 0, 0, 64)

	def setDAC(self, v):
		if self.args.verbose:
			print "setDAC to %d" % (v)
		return self.dev.ctrl_transfer(usb.util.CTRL_IN | usb.util.CTRL_TYPE_VENDOR, 0xda, v&0xFFFF, 0, 64)


# This class dithers the DAC value in the background
class DitherDacThread(threading.Thread):

	def __init__(self, readerThread):
		threading.Thread.__init__(self)
		self.readerThread = readerThread
		self.kill_received = False

	def shutdown(self):
		self.kill_received = True
		self.join()

	def run(self):
		high = 4095
		low = 1200
		while not self.kill_received:
			time.sleep(0.5)
			r = random.randrange(low, high+1, 1)
			self.readerThread.setDAC(r)
		print "DAC thread exiting"


def main():
	default_friendlyName = "OpenADSB receiver"
	default_maxconn = 5
	default_sport = 57575
	default_daclevel = 1892
	default_origin = [ 0, 0, 0 ]

	# terminate on ctrl-c
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	# Parse cmd line args
	desc =  'Mode S packet server or client.\n'
	desc += 'Read from USB dongle and send the packets over the network.\n'
	desc += 'Can act as either a server and/or client.\n'
	parser = argparse.ArgumentParser(description=desc)
	parser.add_argument('-o', '--output', dest="filename", help="log all packets to FILE", metavar="FILE")
	parser.add_argument('-v', '--verbose', dest="verbose", help="print extra info", action="store_true")
	parser.add_argument('-H', '--host', dest="host", help="connect as a client to server at IPADDR:PORT", metavar="IPADDR:PORT")
	parser.add_argument('-S', '--server', dest="serverport", metavar="PORT", help="start a packet server on this host on port PORT", \
			type=int, default=default_sport)
	parser.add_argument('-n', '--name', dest="name", help="friendly name to identify this data feed", type=str, \
			default=default_friendlyName)
	parser.add_argument('-m', '--maxconn', dest="maxconn", help="maximum allowed client connections in server mode", type=int, \
			default=default_maxconn)
	parser.add_argument('-d', '--dac', dest="daclevel", metavar="VALUE", help="set the DAC level to VALUE (0 to 4096)", type=int, \
			default=default_daclevel)
	parser.add_argument('-D', '--dither', dest="ditherdac", help="automatically control DAC value", action='store_true' )
	parser.add_argument('-O', '--origin', dest="origin", nargs=3, metavar="FLOAT", \
			help="Latitude and Longitude of Origin in degrees (-90 to 90, -180 to 180) and altitude in meters", \
			default=default_origin)
	# MacOS starts programs with -psn_XXXXXXX "process serial number" argument.  Ignore it. FIXME SetFrontProcess()
	parser.add_argument('-p')		
	args = parser.parse_args()

	if args.verbose:
		print "Args: ", args

	if args.host != None:
		# client arguments
		h = args.host.split(':')
		host = h[0]
		port = int(h[1])
		socketThread = ClientThread(host, port)
	
	elif args.serverport != None:
		socketThread = ServerThread('', args.serverport, args.maxconn, "none")	# bind to 0.0.0.0
	else:
		print "Must select either client or server mode.  Use -h for help"
		sys.exit(1)

	# start either client or server
	socketThread.start()
	
	# start the USB reader
	reader = AdsbReaderThreadUSB(socketThread, args, dacval=1900)
	reader.setFriendlyName(args.name)
	if args.origin != None:
		origin = [float(args.origin[0]), float(args.origin[1]), float(args.origin[2])]
		reader.setLocation(origin)
	reader.start()

	# wait for both threads to terminate
	reader.join()
	socketThread.shutdown()
	

# This is intended to be be run from the command line
if __name__ == '__main__':
	main()


