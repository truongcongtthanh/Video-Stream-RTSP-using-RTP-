class VideoStream:
	def __init__(self, filename):
		#print('VideoStream: def init')
		self.filename = filename
		try:
			self.file = open(filename, 'rb')
#			print(filename)
#			print('da bat video LL')
		except:
#			print('loi video')
			raise IOError
#		print('end try')
		self.frameNum = 0
		print('frame = 0')
	def nextFrame(self):
		"""Get next frame."""
		#print('VideoStream: def nextFrame')
		data = self.file.read(5) # Get the framelength from the first 5 bits
		if data: 
			framelength = int(data)
							
			# Read the current frame
			data = self.file.read(framelength)
			self.frameNum += 1
		return data
		
	def frameNbr(self):
		#print('VideoStream: def frameNbr')
		"""Get frame number."""
		return self.frameNum
	
	