import sys
from tkinter import Tk
from Client import Client
from Client2 import Client2
if __name__ == "__main__":
	#print('Launcher')
	try:
		serverAddr = sys.argv[1]
		serverPort = sys.argv[2]
		rtpPort = sys.argv[3]
		fileName = sys.argv[4]	
	except:
		print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")	
	

	
	# Create a new client
	print('Nhap option ban muon: ')
	print('1. option 1')
	print('2. option 2')
	while True:
		INPUT = int(input('option ban muon su dung la: '))
		if(INPUT == 1 ):
			root = Tk()
			app = Client(root, serverAddr, serverPort, rtpPort, fileName)
			break
		elif(INPUT == 2):
			root = Tk()
			app = Client2(root, serverAddr, serverPort, rtpPort, fileName)
			break
		else:
			print('Vui long nhap lai option (1 hoac 2):')
	app.master.title("RTPClient")
	root.mainloop()
	