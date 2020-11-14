import random, math
import time
from random import randint
import sys, traceback, threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket

class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2
	
	clientInfo = {}
	
	def __init__(self, clientInfo):
		#print('ServerWorker: def init')
		self.clientInfo = clientInfo
		
	def run(self):
		#print('ServerWorker: def run')
		threading.Thread(target=self.recvRtspRequest).start()
	
	def recvRtspRequest(self):
		#print('ServerWorker: def recvRtspRequest')
		"""Receive RTSP request from the client."""
		connSocket = self.clientInfo['rtspSocket'][0]
#		print('connsocket: ',connSocket)
#		print('clientInfo: ',self.clientInfo)
		while True:            
			data = connSocket.recv(256)
#			print('data: ',data)
			if data:
				print("Data received:\n" + data.decode("utf-8"))
				self.processRtspRequest(data.decode("utf-8"))
	
	def processRtspRequest(self, data):
		#print('ServerWorker: def processRtspRequest')
		"""Process RTSP request sent from the client."""
		# Get the request type
		request = data.split('\n')
#		print('request: ',request)
		line1 = request[0].split(' ')
		requestType = line1[0]
		
		# Get the media file name
		filename = line1[1]
		
		# Get the RTSP sequence number 
		seq = request[1].split(' ')
		
		# Process SETUP request
		if requestType == self.SETUP:
#			print('yeu cau SETUP')
			if self.state == self.INIT:
				# Update state
				print("processing SETUP\n")
				
				try:
#					print('test try')
					self.clientInfo['videoStream'] = VideoStream(filename)
#					print('setup video')
					self.state = self.READY
#					print('SETUP:state')
				except IOError:
#					print('erro1')
					self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
#					print('erro2')
				# Generate a randomized RTSP session ID
				self.clientInfo['session'] = randint(100000, 999999)
				
				# Send RTSP reply
				self.replyRtsp(self.OK_200, seq[1])
				
				# Get the RTP/UDP port from the last line
				self.clientInfo['rtpPort'] = request[2].split(' ')[3]
				print(self.clientInfo['rtpPort'])
				print(request[2].split(' '))
				print('End SETUP')
		# Process PLAY request 		
		elif requestType == self.PLAY:
#			print('yeu cau PLAY')
			if self.state == self.READY:
				print("processing PLAY\n")
				self.state = self.PLAYING
#				print('PLAY: state')
				# Create a new socket for RTP/UDP
				self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#				print('da tao ketnoi')
				self.replyRtsp(self.OK_200, seq[1])
#				print('da phan hoi')
				# Create a new thread and start sending RTP packets
				self.clientInfo['event'] = threading.Event()
				self.clientInfo['worker']= threading.Thread(target=self.sendRtp) 
				self.clientInfo['worker'].start()
#				print('END: PLAY')
		# Process PAUSE request
		elif requestType == self.PAUSE:
#			print('yeu cau PAUSE')
			if self.state == self.PLAYING:
				print("processing PAUSE\n")
				self.state = self.READY
				
				self.clientInfo['event'].set()
			
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print("processing TEARDOWN\n")

			self.clientInfo['event'].set()
			
			self.replyRtsp(self.OK_200, seq[1])
			
			# Close the RTP socket
			self.clientInfo['rtpSocket'].close()
	#error in try - except
	def sendRtp(self):
		#print('ServerWorker: def sendRtp')
		"""Send RTP packets over UDP."""


		while True:
			self.clientInfo['event'].wait(0.05)

			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet():
				break

			data = self.clientInfo['videoStream'].nextFrame()
			if data:
				#print('data: ',data)
				frameNumber = self.clientInfo['videoStream'].frameNbr()
				try:
					address = self.clientInfo['rtspSocket'][1][0]
#					print('address: ',address)
					port = int(self.clientInfo['rtpPort'])
#					print('port: ',port)
					self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(address,port))
#					print('rtpsocket: ')
				except:
					print("Connection Error")
					#print('-'*60)
					#traceback.print_exc(file=sys.stdout)
					#print('-'*60)

	def makeRtp(self, payload, frameNbr):
		#print('ServerWorker: def makeRtp')
		"""RTP-packetize the video data."""
		version = 2
		padding = 0
		extension = 0
		cc = 0
		marker = 0
		pt = 26 # MJPEG type
		seqnum = frameNbr
		ssrc = 0 
		

		rtpPacket = RtpPacket()
		
		rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
		
		return rtpPacket.getPacket()
		
	def replyRtsp(self, code, seq):
		#print('ServerWorker: def replyRtsp')
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			#print("200 OK")
			reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
			connSocket = self.clientInfo['rtspSocket'][0]
			connSocket.send(reply.encode())
		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print("500 CONNECTION ERROR")
