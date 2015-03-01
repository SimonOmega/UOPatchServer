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

  def __init__(self, conn, add, catalog):
    self.listen = True
    self.buffer_len = 4
    self.connection = conn
    self.address = add
    self.reported_version = -1
    self.reported_client = 'NONE'
    # self.file_list = patches
    self.patch_catalog = catalog

  def command_server_trasnfer(self):
    # TODO: Impliment Patch Server Transfer
    # BYTE 0x01
    # BYTE[7] (all bytes 0x00)
    # BYTE[4] IP Address
    # BYTE[4] Port
    print("\nPatch Server does not support PatchServerTrasfer at this time.\n")

  def command_notification(self, message = "Welcome"):
    # TODO: Impliment Notifications
    # BYTE 0x01
    # BYTE[3] (all bytes 0x00)
    # BYTE 0x01
    # BYTE[3] (all bytes 0x00)
    # BYTE 0x02
    # BYTE[3] (all bytes 0x00)
    # BYTE[4] Text Length
    # BYTE[textlength] Notice Data (NULL Terminated)
    self.connection.send(b'\x01\x00\x00\x00\x01\x00\x00\x00\x02\x00\x00\x00')
    self.connection.send(pack('>i', len(message.encode('ascii'))))
    self.connection.send(message.encode('ascii'))
    print("\nPatch Server does not support Notifications at this time.\n")

  def command_use_self(self):
    print("\nServer Sending: Protocol, Command, and UseSelf\n")
    for i in range(0,3):
      self.connection.send(b'\x00\x00\x00\x01')

  def command_patch_list_data(self):
    print("PATCH LIST BABY")
    # TODO: I think the Client Expects just one pat and one rtp file.  Not all of them.
    requested_version = (self.reported_version + 1)
    while requested_version in self.patch_catalog.getCatalog()[self.reported_client]:
    # for a_file in self.patch_catalog.getCatalog():
      p_file = '.' + self.patch_catalog.getCatalog()[self.reported_client][requested_version] + '.pat'
      p_head, p_tail = path.split(p_file)
      r_file = '.' + self.patch_catalog.getCatalog()[self.reported_client][requested_version] + '.rtp'
      r_head, r_tail = path.split(r_file)
      file_listing = {'patname':p_tail.encode('ascii'),
                      'patnamelen':pack('>i', 
                        len(p_tail.encode('ascii'))),
                      'patlen':pack('>i', 
                        path.getsize(p_file)),
                      'rtpname':r_tail.encode('ascii'),
                      'rtpnamelen':pack('>i', 
                        len(r_tail.encode('ascii'))),
                      'rtplen':pack('>i', 
                        path.getsize(r_file))
                     }
      self.connection.send(file_listing['patnamelen'])
      self.connection.send(file_listing['patname'])
      self.connection.send(file_listing['patlen'])
      self.connection.send(file_listing['rtpnamelen'])
      self.connection.send(file_listing['rtpname'])
      self.connection.send(file_listing['rtplen'])
      print("\nSERVER << sent %s PatchListData entry %s\n" % (self.address, file_listing))
      requested_version = requested_version + 1
    self.connection.send(b'\x00\x00\x00\x00')

  def command_send_patch(self, target_file = None):
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
        print(r"SERVER << done sending %s PatchData for %s sending \x00\x00\x00\x00 Block Size" % (self.address, file_properties))
        self.connection.send(pack('>i', 0))

  def command_done_transfer(self):
    self.connection.send(b'\x00\x00\x00\x00')

  def requesthandler(self):
    self.data = self.connection.recv(self.buffer_len)
    if self.data == b'\x00\x00\x00\x15':
      print("\nCLIENT >> %s sent Client Hello/Request (%s)\n" % (self.address, self.data))
      # self.command_notification() # Notificaions force a disconnect...
      # self.command_notification("Welcome to the patch server.") # Notification here causes Client Protocol Error
      Thread(target = self.command_use_self).start()
    elif self.data == b'\x00\x00\x00\x01':
      # version_info = {'namelen':0, 'client':"", 'version':0}
      self.data = self.connection.recv(4)
      namelen = unpack('>L', self.data)[0]
      # Length of client Name
      self.data = self.connection.recv(namelen)
      self.reported_client = self.data.decode('ascii')
      # Name of the client Running
      self.data = self.connection.recv(4)
      self.reported_version = unpack('>L', self.data)[0]
      # Version Number (Patch Number) in this client
      print("\nCLIENT >> %s sent Version Information %s %s\n" % (self.address, self.reported_client, self.reported_version))
      # TODO: Only send a new list if the version has changed.
      if (self.reported_client not in self.patch_catalog.getCatalog()) or ((self.reported_version + 1) not in self.patch_catalog.getCatalog()[self.reported_client]):
        print("\nCLIENT ||  All Patched UP, No new patches.\n")
        # self.command_notification("You are all patched up.") # Notifications here force a disconnect.
        self.listen = False
        self.connection.send(b'\x00\x00\x00\x00')
        return
      else:
        Thread(target = self.command_patch_list_data).start()
    elif self.data == b'\x00\x00\x00\x02':
      file_request = {'namelen':0, 'working_filename':'', 'padding':0}
      self.data = self.connection.recv(4)
      file_request['namelen'] = unpack('>L', self.data)[0]
      self.data = self.connection.recv(file_request['namelen'])
      file_request['working_filename'] = self.data.decode('ascii')
      self.data = self.connection.recv(4)
      file_request['padding'] = unpack('>L', self.data)[0]
      # Always Null Assuming Unused... Or used to continue a failed download...
      print("\nCLIENT >> %s sent a Request for File %s (%s)\n" % (self.address, file_request['working_filename'], file_request))
      # I think padding is used for resuming a file from the last fragment that downloaded.
      ###
      # TODO: Ensure send_patch supports the new catalog structure.
      ###
      # Thread(target = self.command_send_patch, args = (4, file_request['working_filename'])).start()
    elif self.data == b'\x00\x00\x00\x03':
      Thread(target = self.command_done_transfer).start()
      # TODO: Investigate if we should have a latest version check here.
    else:
      print("\nCLIENT >> %s sent unhandled message %s\n" % (self.address, self.data)) 
      # TODO: Handle Error when Client Disconnects.
      # Is socket left open and we are reading a Null Stream?
      self.listen = False

  def run(self):
    while self.listen:
      self.requesthandler()
    self.command_done_transfer()
    # self.connection.shutdown(socket.SHUT_RDWR) # Best practice to shutdown before close, even though most people do not.
    self.connection.shutdown(2) # scoket.SHUT_RDWR == 2, Python Complaining about SHUT_RDWR Attribute undefined.
    self.connection.close()    # Close it.
    # self.connection.finish()   # Does not exist in Python 3   self.connection.close()
    return

class PatchCatalog:
  '''
  '''
  def __init__(self, directory):
    self.catalog = {}
    for a_file in listdir(directory):
      if a_file.endswith(".pat"):
        with open(path.join(directory, a_file)) as patch_info:
          client, version = next(patch_info).rstrip().split(' ')
          if client in self.catalog:
            self.catalog[client][int(version)] = path.join(directory, a_file).split('.')[1]
          else:
            self.catalog[client] = {}
            self.catalog[client][int(version)] = path.join(directory, a_file).split('.')[1]
    print("Patch Catalog\n%s\n" % self.catalog)

  def getCatalog(self):
    return self.catalog

if __name__ == "__main__":
  _PATCH_DIR = path.join('.', 'archive')
  # _HOST = '127.0.0.1' # Loopback
  # _HOST = ''# Listen on all IPs
  # _HOST = socket.gethostname()
  _HOST = 'localhost'
  # docs.python.org - local host - On most platforms, this will take a shortcut around a couple of layers of network code and be quite a bit faster.'''
  _PORT = 8888
  _RUNNING = True
  # _PATCHES = {}
  _CLIENTS = {}
  _THREADS = []
  
  print("Generating Patch Catalog\n")
  _UO_CATALOG = PatchCatalog(_PATCH_DIR)

  opensocket = socket(AF_INET, SOCK_STREAM)
  opensocket.bind((_HOST, _PORT))
  print("%s listening on %i\n" % (_HOST, _PORT))
  # opensocket.listen(1) # queue up to 1 connection.
  opensocket.listen(5) # queue up to 5 connections.
  while _RUNNING:
    print("Socket: Waiting on Connections.\n")
    connection, ip_port = opensocket.accept()
    _CLIENTS[ip_port[0]] = PatchHandler(connection, ip_port[0], _UO_CATALOG)
  #  _CLIENTS[ip_port[0]] = Thread(target = PatchListener, args = (connection, address[0]))
    _THREADS.append(Thread(target = _CLIENTS[ip_port[0]].run).start())
  #  _CLIENTS[ip_port[0]].start()
  print("MAIN _RUNNING == False")
