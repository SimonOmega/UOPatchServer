'''
Created on Jul 07, 2013

@author: simonomega
'''

from os import path, listdir
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack 

class PatchHandler:
  '''
  This is a move to a class based structure to support the UO patch server.
  I'm not a huge fan of classes, but it will help development forward.
  '''

  def __init__(self, conn, add, path):
    self.listen = True
    self.buffer_len = 4
    self.connection = conn
    self.address = add
    self.working_directory = path
    self.file_list = []
    print("PatchHandler for %s is using directory %s", (self.address, self.working_directory))
    for a_file in listdir(_PATCH_DIR):
      if a_file.endswith(".rtp"):
        self.file_list.append(a_file)
      elif a_file.endswith(".pat"):
        self.file_list.append(a_file)
    print("PatchHandler for %s is using file list %s" % (self.address, self.file_list))


  def commands(self, command, target_file = None):
    if command == 0:
      # TODO: Impliment Patch Server Transfer
      # BYTE 0x01
      # BYTE[7] (all bytes 0x00)
      # BYTE[4] IP Address
      # BYTE[4] Port
      print("\nPatch Server does not support PatchServerTrasfer at this time.\n")
    if command == 1:
      # TODO: Impliment Notifications
      # BYTE 0x01
      # BYTE[3] (all bytes 0x00)
      # BYTE 0x01
      # BYTE[3] (all bytes 0x00)
      # BYTE 0x02
      # BYTE[3] (all bytes 0x00)
      # BYTE[4] Text Length
      # BYTE[textlength] Notice Data (NULL Terminated)
      print("\nPatch Server does not support Notifications at this time.\n")
    if command == 2:
      print("\nServer Sending: Protocol, Command, and UseSelf\n")
      for i in range(0,3):
        self.connection.send(b'\x00\x00\x00\x01')
    if command == 3:
      for a_file in self.file_list:
        file_listing = {'working_filename':a_file.encode('ascii'),
                     'namelen':pack('>i', len(a_file.encode('ascii'))),
                     'working_filelen':pack('>i', path.getsize(path.join(self.working_directory, a_file)))}
        print("\nSERVER << sent %s PatchListData entry %s\n" % (self.address, file_listing))
        self.connection.send(file_listing['namelen'])
        self.connection.send(file_listing['working_filename'])
        self.connection.send(file_listing['working_filelen'])
        self.connection.send(b'\x00\x00\x00\x00')
    if command == 4:
      if target_file == None:
        print("\nTrying to send PatchData to Client, but no target_file name was sent to command 4.\n")
      else:
        file_properties = {'working_filename':target_file,
                           'namelen':pack('>i', len(target_file.encode('ascii'))),
                           'working_filelen':path.getsize(path.join(self.working_directory, target_file))}
        print("\nSERVER << sending %s PatchData for %s\n" % (self.address, file_properties))
        self.connection.send(file_properties['namelen'])
        self.connection.send(file_properties['working_filename'].encode('ascii'))
        self.connection.send(pack('>i', file_properties['working_filelen']))
        with open(path.join(self.working_directory, file_properties['working_filename']), 'rb') as push_file:
          block = push_file.read(1024)
          while block:
            self.connection.send(pack('>i', len(block)))
            self.connection.send(block)
            block = push_file.read(1024)
        print(r"]nSERVER << done sending %s PatchData for %s sending \x00\x00\x00\x00 Block Size\n" % (self.address, file_properties))
        self.connection.send(pack('>i', 0))
    if command == 5:
      self.connection.send(b'\x00\x00\x00\x00')
      

  def requesthandler(self):
    self.data = self.connection.recv(self.buffer_len)
    if self.data == b'\x00\x00\x00\x15':
      print("\nCLIENT >> %s sent Client Hello/Request (%s)\n" % (self.address, self.data))
      Thread(target = self.commands, args = (2, )).start()
    elif self.data == b'\x00\x00\x00\x01':
      version_info = {'namelen':0, 'addon':"", 'version':0}
      self.data = self.connection.recv(4)
      version_info['namelen'] = unpack('>L', self.data)[0]
      # Length of addon Name
      self.data = self.connection.recv(version_info['namelen'])
      version_info['addon'] = self.data.decode('ascii')
      # Name of the addon Running
      self.data = self.connection.recv(4)
      version_info['version'] = unpack('>L', self.data)[0]
      # Version Number (Patch Number) in this addon
      print("\nCLIENT >> %s sent Version Information (%s)\n" % (self.address, version_info))
      Thread(target = self.commands, args = (3, )).start()
    elif self.data == b'\x00\x00\x00\x02':
      file_request = {'namelen':0, 'working_filename':'', 'padding':0}
      self.data = self.connection.recv(4)
      file_request['namelen'] = unpack('>L', self.data)[0]
      self.data = self.connection.recv(file_request['namelen'])
      file_request['working_filename'] = self.data.decode('ascii')
      self.data = self.connection.recv(4)
      file_request['padding'] = unpack('>L', self.data)[0]
      # Always Null Assuming Unused
      print("\nCLIENT >> %s sent a Request for File %s (%s)\n" % (self.address, file_request['working_filename'], file_request))
      # I think padding is used for resuming a file from the last fragment that downloaded.
      Thread(target = self.commands, args = (4, file_request['working_filename'])).start()
    elif self.data == b'\x00\x00\x00\x03':
      Thread(target = self.commands, args = (5, )).start()
    else:
      print("\nCLIENT >> %s sent unhandled message %s\n" % (self.address, self.data)) 
      # TODO: Handle Error when Client Disconnects.
      # Is socket left open and we are reading a Null Stream?
      self.finish()

  def run(self):
    while self.listen:
      self.requesthandler()


if __name__ == "__main__":
  _PATCH_DIR = path.join('.', 'archive')
  _HOST = '127.0.0.1'
  _PORT = 8888
  _RUNNING = True
  _CLIENTS = {}
  _THREADS = []
  
  opensocket = socket(AF_INET, SOCK_STREAM)
  opensocket.bind((_HOST, _PORT))
  print("%s listening on %i" % (_HOST, _PORT))
  opensocket.listen(1)
  while _RUNNING:
    print("Socket: Waiting on Connections.")
    connection, ip_port = opensocket.accept()
    _CLIENTS[ip_port[0]] = PatchHandler(connection, ip_port[0], _PATCH_DIR)
  #  _CLIENTS[ip_port[0]] = Thread(target = PatchListener, args = (connection, address[0]))
    _THREADS.append(Thread(target = _CLIENTS[ip_port[0]].run).start())
  #  _CLIENTS[ip_port[0]].start()
  print("MAIN _RUNNING == False")
