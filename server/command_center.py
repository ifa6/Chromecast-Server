#!/usr/bin/env python


import libcommand_center as libcc
import asyncore
import socket
import ws_proxy
from socket import timeout as TIMEOUT_ERROR
import os.path
import time
import dial.rest

#--------------
# Constants
#--------------

class Update_Handler(asyncore.dispatcher):
	def __init__(self,sock,cc):
		asyncore.dispatcher.__init__(self,sock)
		self.read_buffer = ""
		self.write_buffer = ""

		# Keep track of the command center and the CC and DB
		self.command_center = cc
		self.db = cc.db

	def writable(self):
		if len(self.write_buffer) > 0:
			return True
		else:
			return False

	def handle_write(self):
		sent = self.send(self.write_buffer)
		self.write_buffer[sent:]

	
	def handle_read(self):
		# Add new data to the read buffer
		self.read_buffer += self.recv(1024)
		# Attempt to decode the packet
		req, size = libcc.pkt_to_json(self.read_buffer)
		# If The Request oject is None, wait for more data
		if req == None:
			return
		else:
			# If Request packet is created, prepare a response
			self.prepare_response(req)
			# Adjust the read buffer accordingly
			self.read_buffer = self.read_buffer[size:]

	def prepare_response(self,req):
		resp = {
			"source":"command_center",
			"message":"OK"
			}
		if req["source"] == "discoverer":
			for d in req["devices"]:
				self.db["devices"][d["ip"]] = d	
		elif req["source"] == "converter":
			if "progress" in req:
				pass
				# Update Progress for given item
			elif "complete" in req:
				pass
				# Remove Item from Queue
		elif req["source"] in ["cli","webui"]:
			print "CLI Command"
			# If an address is in the request, it is intneded for
			# a Chromecast Devices
			if "addr" in req:
				# Forward  Request to WebSocket Server
				device = self.db["devices"][req["addr"]]
				app_id="e7689337-7a7a-4640-a05a-5dd2bd7699f9_1"
				if req["cmd"] == "launch":
					dial.rest.launch_app( device, app_id)
				elif req["cmd"] == "exit":
					dial.rest.exit_app(device,app_id)
				else:
					resp["message"] = "CLI Error - Bad CMD"
			elif "cmd" not in req:
				resp["message"] = "CLI Error - No Comand Given"
			elif req["cmd"] == "movies":
				print "Movies"
				resp["movies"] = self.db["movies"]
			elif req["cmd"] == "devices":
				resp["devices"] = self.db["devices"]
			else:
				resp["message"] = "CLI Error - Bad Command"				

		elif req["source"] == "scanner":
			# Overwrite the list of movies/tv on the database
			self.db["movies"] = req["movies"]
			self.db["tv"] = req["tv"]
		else:
			resp["msg"] = "Error"
			resp["error"] = "No Packet Source Given"

		self.write_buffer += libcc.json_to_pkt(resp)

## Main Command Center Unix Socket Server
#
# This is the main Command Center server.  It maintains a database and waits 
# for Unix Socket connections.  It also creates a WebSocket Server object
class Command_Center(asyncore.dispatcher):
	def __init__(self):
		# Init the generic dispatcher
		asyncore.dispatcher.__init__(self)

		if(os.path.exists(libcc.UNIX_SOCKET_PATH)):
			os.remove(libcc.UNIX_SOCKET_PATH)

		# Create a Unix socket to listen to
		self.create_socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.bind(libcc.UNIX_SOCKET_PATH)
		self.listen(5)

		# Create a JSON database in Memory to keep track of all of the
		# sub processes
		self.db = {
			"devices":{},	# Dict of Chromecast Devices found
			"movies":[],	# List of Movies On Server
			"tv":[],	# List of TV series on Server
			"transcode_queue":[], # List of Videos to Transcode
			"websockets":{}, # Dict of currently Open WebSockets
			}

		# Start the Websocket Proxy
		self.start_websocket_proxy()

	# This method is called whenever a socket connection is made
	def handle_accept(self):
		# Create a handler object to deal with the socket
		sock,addr = self.accept()
		Update_Handler(sock,self)

	# Write the Memory database to disk
	def _write_db(self):
		# We will do nothing for now
		pass	

	## Add a WebSocket to the Database
	#
	# When the WebSocket Proxy Server opens, it will add the socket 
	# instance to the database
	def add_websocket(self,addr,ws):
		self.db["websockets"][addr] = ws

	## Remove a WebSocket from the Database
	#
	# When a Websocket Proxy is closed, this should be called to remove
	# it from the command center database
	def remove_websocket(self,addr):
		del self.db["websockets"][addr]

	## Starts the WebSocket Proxy Server
	def start_websocket_proxy(self):
		# Create a WebSocket Proxy object.  Send the "self" variable
		# so that the WebSocket proxy has a pointer to the Command 
		# Center
		ws_proxy.WS_Server(self)
	

	## Communicate with a WebSocket
	#
	# Send a message to the websockets.  The target address should 
	# contained inside the req JSON object
	def websocket_communicate(self,req):
		if req["addr"] in self.db["websockets"]:
			wsock = self.db["websockets"][req["addr"]]
			wsock.send_msg(req)
			return wsock.recv_msg()
		else:
			return {"error":"No WS Connection for that address"}

# Start the Command center when this script is run indepen
if __name__ == '__main__':
	# Create a Command Center Object
	cc = Command_Center()

	# Initialize the list of processes
	ps = libcc.get_process_list()
	
	# Server Forever
	watchdog_length = 10
	watchdog_time = time.time() + watchdog_length 
	while(1):
		# Timeout after at most 10 seconds
		asyncore.loop(timeout=1,count=10)
		# Verify that the timeout is at least 10 seconds
		if time.time() > watchdog_time:
			# Update the watchdog
			watchdog_time = time.time()+watchdog_length
			# Check processes and write to db
			libcc.check_processes(ps)
			cc._write_db()
			# Print DB stats
			
			print "Current DB stats:"
			for key in cc.db:
				print "\t"+key+": "+str(len(cc.db[key]))



