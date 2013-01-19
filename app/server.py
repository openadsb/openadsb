# Threaded TCP server which accepts connections, and does blocking read on an external queue.  It writes queue contents to the client
# This was borrowed from somewhere, but I don't remember where..
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

# FIXME - need to allow asynchronous, bidirectional traffic on this socket, interfacing to openadsb using separate blocking queues for each direction 
# Since the 'Queue' object isn't implemented with file descriptors, it cannot be used directly as part of a select() polling loop.
# Can we let the sending thread modify the select() loop thread by telling it to add 'writeable' to the socket FD_SET, when it transitions from an 
# empty queue to a non-empty queue?  The select lop would then remove the 'writable' FD from the set if/when it drains the queue.  The loop() thread
# would use a non-blocking get() from the queue.  It would use a non-blocking read of the socket.

# OR - simpler  method - two threads - one read only, one write only.  

import SocketServer
import threading
import Queue
import time
import socket
import string
import sys


# SocketHandler exists for each connected client.  Read from our queue and write data out to client.
# Discard any incoming data from client
class SocketHandler(SocketServer.BaseRequestHandler):
    def setup(self):
	#global queuelist 
        print self.client_address, 'connected!'
        self.request.send('hi ' + str(self.client_address) + '\n')
	self.q = Queue.Queue(maxsize=100)		# max 100 items
	self.server.addClientQueue(self.q)

    def handle(self):
	while 1:
		# FIXME - this is the 'send' portion of the server
		# This should be per packet format
		# FIXME 
		d = self.q.get()			# blocking read of queue
		l = '*' + d 
		try:
			self.request.send(l)
		except Exception, err:
			break
	
		# FIXME - we need a 'recv' portion of the server as well
		# need to block on both the self.queue and the socket itself

    def finish(self):
	global queuelist 
        print self.client_address, 'disconnected!'
	self.server.delClientQueue(self.q)
	#queuelist.remove(self.q)

# Need a handle to the parent thread, so subclass this thing
class MyThreadingTCPServer(SocketServer.ThreadingTCPServer):
	def __init__(self, myThread, (host, port), socketHandler):
		self.allow_reuse_address = True
	 	SocketServer.ThreadingTCPServer.__init__(self, (host, port), socketHandler)
		self.myThread = myThread
		
	def addClientQueue(self, q):
		self.myThread.addClientQueue(q)

	def delClientQueue(self, q):
		self.myThread.delClientQueue(q)

# A threaded TCP server
class ServerThread(threading.Thread):
	def __init__(self, host, port, maxConn, fmt):
		threading.Thread.__init__(self)
		self.queuelist = []
		self.fmt = fmt
		self.maxConn = maxConn
		self.server = MyThreadingTCPServer(self, (host, port), SocketHandler)

	def addClientQueue(self, q):
		self.queuelist.append(q)

	def delClientQueue(self, q):
		self.queuelist.remove(q)

	def run(self):
		try:
			self.server.serve_forever()			# returns only on shutdown
			print "serve_forever() returned"
		except Exception:
			print "run() got exception"
		except KeyboardInterrupt:
			print "key1"					#fixme - thread.interrupt_main()
			raise Exception('bk exception')
		print "server thread exiting"
	
	def shutdown(self):
		print "shutting down server"
		self.server.shutdown()				# tell server thread to quit
		self.server.server_close()			
	
	def put(self, l):
		for q in self.queuelist:
			q.put(l)				# fixme - this has to be non-blocking -skip if fail
			#try: 
			#	q.put_nowait(l)			# non-blocking - skip if fail
			#except:
			#	print "Queue full! Dropping packet"


# test this server if run directly 
if __name__ == '__main__':
	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	s1 = ServerThread('', 30001, 5, "none")			# bind to 0.0.0.0
	s1.start()
	print "started server thread(s)"

	# open the packet log and push it to all clients
	packetlog = open('packetlog.txt', 'r')
	try:
		while 1:
			time.sleep(0.01)
			l = packetlog.readline()	
			if not l: break
			s1.put(l)
	except KeyboardInterrupt:
		print "got ctrl c"

	s1.shutdown()
