# Threaded TCP client which handles bidirectional traffic in separate threads, so app can send/receive independently
#
# Outgoing traffic comes from a blocking read of a per-client queue.  Same data is sent to all clients.
# Incoming traffic goes into a single queue, shared by all clients, for the app the read.  
#
# B. Kuschak, OpenADSB Project <brian@openadsb.com>
#

import SocketServer
import threading
import Queue
import time
import socket
import string
import sys


# A threaded TCP client, for use by the app.  instantiate, then call start(), followed by get()/put()
class ClientThread(threading.Thread):

	def __init__(self, host, port, waitForConnect = False):
		threading.Thread.__init__(self)
		self.host = host
		self.port = port
		self.outgoing_q = Queue.Queue(maxsize=100)
		self.outgoing_q_mutex = threading.Lock()
		self.terminate_flag = threading.Event()
		self.waitForConnect = waitForConnect
		self.sock = None
		if self.waitForConnect:
			self.connect()

	def connect(self):
		print "Connecting to server %s:%s..." % (self.host, self.port)
		try:
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.connect((self.host, self.port))
			self.sock.send("Hello from OpenADSB\n")
			#self.sockfile = self.sock.makefile('r', 0)		# create a file-object to read from w/o buffering
			print self.sock.getsockname(), ' connected!'
			return True
		except Exception as detail:
			print "Connection failed:", detail
			return False
		
	# in this thread, we send queued outgoing traffic only
	def run(self):
		if not self.waitForConnect:
			self.connect()

		while not self.terminate_flag.isSet():
			try:
				d = self.outgoing_q.get()
				self.sock.send(d)
			except Exception:
				break
		print "ClientThread run() exiting"
	
	def shutdown(self):
		self.terminate_flag.set()
		self.sock.close()
		# need to unblock the q.get() function above... hack - just put something in the queue
		self.outgoing_q_mutex.acquire()
		try:
			self.outgoing_q.put_nowait(" ")		# dont block if full
		except:
			pass
		self.outgoing_q_mutex.release()
	
	# send this packet to the server, but don't block
	# can be called by any thread
	def put(self, d):
		l = 0
		self.outgoing_q_mutex.acquire()
		try: 
			self.outgoing_q.put_nowait(d)				
			l = len(d)
		except:
			print "Queue full! Dropping packet to %s:%s" % (self.host, self.port)
		self.outgoing_q_mutex.release()
		return l

	# get packets from server with blocking read
	# can be called by any thread.  will generate an exception if the socket is not connected
	def get(self):
		d = self.sock.recv(2048)
		if len(d) == 0:
			print "socket was closed"
		return d


# test this client if run directly 
if __name__ == '__main__':
	import thread
	class testThread(threading.Thread):
		def __init__(self, client, sending=True):
			self.client = client
			self.sending = sending
			threading.Thread.__init__(self)
		def run(self):
			if self.sending:
				return self.doSend()
			else:
				return self.doRecv()
		def doSend(self):
			print "Thread %d Sending" % thread.get_ident()
			packetlog = open('packetlog.txt', 'r')
			while True:
				time.sleep(0.01)
				l = packetlog.readline()	
				# terminate thread when either input file ends or queue fills up
				if not l: 
					break
				if self.client.put(l) == 0:
					break
			print "Terminating Send Thread %d" % thread.get_ident()

		def doRecv(self):
			print "Thread %d Receiving" % thread.get_ident()
			while True:
				try:
					l = self.client.get()
					if len(l) == 0:
						print "testThread: connection was closed"
						break
					print "Got '%s'" % l
				except:
					time.sleep(1)
			print "Terminating Recv Thread %d" % thread.get_ident()

	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	c1 = ClientThread('localhost', 30001)	
	c1.start()
	print "started main client thread" 

	st = testThread(c1, True)	# sender
	rt = testThread(c1, False)	# receiver
	st.start()
	rt.start()

	# wait for test threads to terminate
	st.join()
	rt.join()

	# wait for client thread to terminate
	c1.shutdown()
	c1.join()
