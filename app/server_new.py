# Threaded TCP server which handles bidirectional traffic in separate threads, so app can send/receive independently
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

# SocketHandler instantiated once for each connected client.  
# Use this handle() method to do blocking reads on queue to send outgoing traffic.
# Start a secondary thread to do blocking writes on another queue for incoming traffic.
class SocketHandler(SocketServer.BaseRequestHandler):
    def setup(self):
        print self.client_address, 'connected!'
        self.request.send('hi ' + str(self.client_address) + '\n')

	self.outgoing_q = Queue.Queue(maxsize=100)		# max 100 items
	self.server.myThread.addClientQueue(self.outgoing_q)

	# start new thread to handle incoming traffic only
	self.incomingThread = IncomingTrafficThread(self.request, self.server.myThread)
	self.incomingThread.start()

    # we will handle outgoing traffic in this thread only
    def handle(self):
	while 1:
		d = self.outgoing_q.get()			# blocking read of queue
		l = '*' + d 
		try:
			self.request.send(l)
			self.outgoing_q.task_done()		# is this needed to free memory?
		except Exception, err:
			break

    def finish(self):
        print self.client_address, 'disconnected!'
	self.server.myThread.delClientQueue(self.outgoing_q)
	self.incomingThread.terminate()
	self.incomingThread.join()

# used above
class IncomingTrafficThread(threading.Thread):
	def __init__(self, request, serverThread):
		self.request = request
		self.serverThread = serverThread
		self.terminate_flag = threading.Event()
		threading.Thread.__init__(self)

	def terminate(self):
		self.terminate_flag.set()

	def run(self):
		while not self.terminate_flag.isSet():
			try:
				d = self.request.recv(2048)
				if len(d) == 0:
					#print "zero length means socket was closed.  Exiting"
					break
			except: 
				print "Got exception on reading socket!"
				pass
			self.serverThread.putIncomingData(d)			
		#print "Exiting IncomingTrafficThread!"

# Need a handle to the parent thread, so subclass this thing
class MyThreadingTCPServer(SocketServer.ThreadingTCPServer):
	def __init__(self, myThread, (host, port), socketHandler):
		self.allow_reuse_address = True
	 	SocketServer.ThreadingTCPServer.__init__(self, (host, port), socketHandler)
		self.myThread = myThread
		

# A threaded TCP server, for use by the app.  Instantiate, then call start(), followed by get/put()
class ServerThread(threading.Thread):
	def __init__(self, host, port, maxConn, fmt):
		threading.Thread.__init__(self)
		self.outgoing_queuelist = []
		self.queuelist_mutex = threading.Lock()
		self.fmt = fmt
		self.maxConn = maxConn
		self.incoming_q = Queue.Queue(maxsize=100)		# max 100 items
		self.incoming_q_mutex = threading.Lock()
		self.server = MyThreadingTCPServer(self, (host, port), SocketHandler)

	def addClientQueue(self, out_q):
		self.queuelist_mutex.acquire()
		self.outgoing_queuelist.append(out_q)
		self.queuelist_mutex.release()

	def delClientQueue(self, out_q):
		self.queuelist_mutex.acquire()
		self.outgoing_queuelist.remove(out_q)
		self.queuelist_mutex.release()

	# multiple threads call this method to dump their incoming data
	def putIncomingData(self, d):
		self.incoming_q_mutex.acquire()
		self.incoming_q.put(d)				
		self.incoming_q_mutex.release()

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
	
	# these get/put() are for use by the app:
	# send this packet to all connected clients
	def put(self, l):
		for q in self.outgoing_queuelist:
			#q.put(l)				# fixme - this has to be non-blocking -skip if fail
			try: 
				q.put_nowait(l)			# has to be non-blocking - skip if fail
			except:
				print "Queue full! Dropping packet"

	# get packets from any connected clients
	def get(self):
		return self.incoming_q.get()	


# test this server if run directly 
if __name__ == '__main__':
	import thread
	class testThread(threading.Thread):
		def __init__(self, server, sending=True):
			self.server = server
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
				if not l: break
				self.server.put(l)
		def doRecv(self):
			print "Thread %d Receiving" % thread.get_ident()
			while True:
				l = self.server.get()
				print "Got '%s'" % l

	import signal
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	s1 = ServerThread('', 30001, 5, "none")			# bind to 0.0.0.0
	s1.start()
	print type(s1)
	print "started main server thread(s)" 

	st = testThread(s1, True)	# sender
	rt = testThread(s1, False)	# receiver
	st.start()
	rt.start()

	# wait for both threads to terminate
	st.join()
	rt.join()

	s1.shutdown()

	# open the packet log and push it to all clients
	#packetlog = open('packetlog.txt', 'r')
	#try:
		#while 1:
			#time.sleep(0.01)
			#l = packetlog.readline()	
			#if not l: break
			#s1.put(l)
	#except KeyboardInterrupt:
		#print "got ctrl c"
#
	#s1.shutdown()
