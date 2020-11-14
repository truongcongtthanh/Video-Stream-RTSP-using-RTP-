from tkinter import *
import tkinter.messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os
import datetime
from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client2:
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    DESCRIBE = 4

    counter = 0
    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        #print('Client: def init')

        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)


        self.createWidgets()

        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        ## ---

        self.DESCRIBE_STR = "DESCRIBE"
        self.SETUP_STR = "SETUP"
        self.RTSP_VER = "RTSP/1.0"
        self.TRANSPORT = "RTP/AVP"
        self.PLAY_STR = "PLAY"
        self.PAUSE_STR = "PAUSE"
        self.TEARDOWN_STR = "TEARDOWN"

        self.setupMovie()
    def createWidgets(self):
        #print('Client: def createWidgets')
        """Build GUI."""
        # Create Setup button
        self.setup = Button(self.master, width=20, padx=3, pady=3)
        self.setup["text"] = "Describe"
        self.setup["command"] = self.describeMovie
        self.setup.grid(row=1, column=0, padx=2, pady=2)

        # Create Play button
        self.start = Button(self.master, width=20, padx=3, pady=3)
        self.start["text"] = "Play"
        self.start["command"] = self.playMovie
        self.start.grid(row=1, column=1, padx=2, pady=2)

        # Create Pause button
        self.pause = Button(self.master, width=20, padx=3, pady=3)
        self.pause["text"] = "Pause"
        self.pause["command"] = self.pauseMovie
        self.pause.grid(row=1, column=2, padx=2, pady=2)

        # Create Teardown button
        self.teardown = Button(self.master, width=20, padx=3, pady=3)
        self.teardown["text"] = "Stop"
        self.teardown["command"] = self.exitClient
        self.teardown.grid(row=1, column=3, padx=2, pady=2)

        # Create a label to display the movie
        self.label = Label(self.master, height=19)
        self.label.grid(row=0, column=0, columnspan=4, sticky=W + E + N + S, padx=5, pady=5)

    def describeMovie(self):
        """Describe button handler"""
        #if self.state == self.READY:
        self.sendRtspRequest(self.DESCRIBE)
    def setupMovie(self):
        #print('Client: def setupMovie')
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitClient(self):
        #print('Client: def exitClient')
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)  # Delete the cache image from video
        print('count: ', self.counter)
        rate = float(self.counter / self.frameNbr)
        print ('-' * 60 + "\nRTP Packet Loss Rate :" + str(rate) + "\n" + '-' * 60)
        sys.exit(0)
    def pauseMovie(self):
        #print('Client: def pauseMovie')
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        #print('Client: def playmovie')
        """Play button handler."""
        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    def listenRtp(self):
        #print('Client: def listenRtp')
        """Listen for RTP packets."""
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    #currFrameNbr = rtpPacket.seqNum()
                    print("Current Seq Num: " + str(rtpPacket.seqNum()))
                    try:
                        if self.frameNbr + 1 != rtpPacket.seqNum():
                            #print('count: ',self.counter)
                            self.counter += 1
                            print
                            ('!' * 60 + "\nPACKET LOSS\n" + '!' * 60)
                        currFrameNbr = rtpPacket.seqNum()
                    # version = rtpPacket.version()
                    except:
                        print("seqNum() error")
                        print('-' * 60)
                        traceback.print_exc(file=sys.stdout)
                        print('-' * 60)
                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                    break

    def writeFrame(self, data):
        #print('Client: def writeFrame')
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        #print('Client: def updateMovie')
        """Update the image file as video frame in the GUI."""
        photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.label.configure(image=photo, height=288)
        self.label.image = photo

    def connectToServer(self):
        #print('Client: def connectToServer')
        """Connect to the Server. Start a new RTSP/TCP session."""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            tkinter.messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    def sendRtspRequest(self, requestCode):
        #print('Client: def sendRtspRequest')
        """Send RTSP request to the server."""
        # -------------
        # TO COMPLETE
        # -------------

        # Setup request
        if requestCode == self.SETUP:  # and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "%s %s %s\nCSeq: %d\nTransport: %s; client_port= %d" % (
            self.SETUP_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.TRANSPORT, self.rtpPort)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.SETUP
        # Play request
        elif requestCode == self.PLAY:  # and self.state == self.READY:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "%s %s %s\nCSeq: %d\nSession: %d" % (
            self.PLAY_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PLAY
        # Pause request
        elif requestCode == self.PAUSE:  # and self.state == self.PLAYING:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "%s %s %s\nCSeq: %d\nSession: %d" % (
            self.PAUSE_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.PAUSE
        # Teardown request
        elif requestCode == self.TEARDOWN:  # and not self.state == self.INIT:
            # Update RTSP sequence number.
            # ...
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            # request = ...
            request = "%s %s %s\nCSeq: %d\nSession: %d" % (
            self.TEARDOWN_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.sessionId)

            # Keep track of the sent request.
            # self.requestSent = ...
            self.requestSent = self.TEARDOWN
        elif requestCode ==self.DESCRIBE:

            self.rtspSeq = self.rtspSeq + 1
            request = "%s %s %s\nCSeq: %d\nSession: %d" % (
                self.DESCRIBE_STR, self.fileName, self.RTSP_VER, self.rtspSeq, self.sessionId)
            self.requestSent = self.DESCRIBE
            self.rtspSocket.send(request.encode())
            print('\nData sent:\n' + request)
            x = datetime.datetime.now()
            top = Toplevel()
            top.geometry('300x100')
            Lb1 = Listbox(top, width=50, height=20)
            Lb1.insert(1, "Describe: ")
            Lb1.insert(2, "1. File Video: " + str(self.fileName))
            Lb1.insert(3, "2. Date: " + str(x.date()))
            Lb1.insert(4, "3. Time: " + str(x.strftime("%X")))
            Lb1.insert(5, "4. Day: " + str(x.strftime("%A")))

            Lb1.pack()
            top.mainloop()
        else:
            return

        # Send the RTSP request using rtspSocket.
        # ...
        self.rtspSocket.send(request.encode())
        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        #print('Client: def recvRtspReply')
        """Receive RTSP reply from the server."""
        while True:
            reply = self.rtspSocket.recv(1024)

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    def parseRtspReply(self, data):
        #print('Client: def parseRtspReply')
        """Parse the RTSP reply from the server."""
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        # -------------
                        # TO COMPLETE
                        # -------------
                        # Update RTSP state.
                        # self.state = ...
                        self.state = self.READY
                        # Open RTP port.
                        self.openRtpPort()
                    elif self.requestSent == self.PLAY:
                        # self.state = ...
                        self.state = self.PLAYING
                    elif self.requestSent == self.PAUSE:
                        # self.state = ...
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        # self.state = ...
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1
                    #elif self.requestSent == self.DESCRIBE:
                    #   self.state = self.READY

    def openRtpPort(self):
        #print('Client: def openRtpPort')
        """Open RTP socket binded to a specified port."""
        # -------------
        # TO COMPLETE
        # -------------
        # Create a new datagram socket to receive RTP packets from the server
        # self.rtpSocket = ...
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Set the timeout value of the socket to 0.5sec
        # ...
        self.rtpSocket.settimeout(0.5)
        try:
            # Bind the socket to the address using the RTP port given by the client user
            # ...
            self.state = self.READY
            self.rtpSocket.bind(('', self.rtpPort))
        except:
            tkinter.messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)

    def handler(self):
        #print('Client: def handler')
        """Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if tkinter.messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:  # When the user presses cancel, resume playing.
            self.playMovie()
