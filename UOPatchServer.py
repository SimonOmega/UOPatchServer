'''
Created on Jul 07, 2013

@author: simonomega
'''

from os import path, listdir
from threading import Thread
from socket import socket, AF_INET, SOCK_STREAM
from struct import pack, unpack 

_FILE_LIST = []
_PATCH_DIR = path.join('.', 'archive')
print("Using Patch Directory: ", _PATCH_DIR)
for working_file in listdir(_PATCH_DIR):
  if working_file.endswith(".rtp"):
    _FILE_LIST.append(working_file)
  if working_file.endswith(".pat"):
    _FILE_LIST.append(working_file)
print("Using File List: %s" % _FILE_LIST)

_HOST = '127.0.0.1'
_PORT = 8888
_RUNNING = True
_CLIENTS = {}

def PatchListener(connection, host):
  _LISTEN = True
  _RECIEVED_COMMAND = False
  while _LISTEN:
    data = connection.recv(4)
    if data == b'\x00\x00\x00\x15':
      print("%s Sent: Client Hello/Request: %s" % (host, data))
      Thread(target = SendCommands, args = (2, connection)).start()
    elif data == b'\x00\x00\x00\x01':
      version_info = {'namelen':0, 'addon':"", 'version':0}
      data = connection.recv(4)
      version_info['namelen'] = unpack('>L', data)[0]
      # Length of addon Name
      data = connection.recv(version_info['namelen'])
      version_info['addon'] = data.decode('ascii')
      # Name of the addon Running
      data = connection.recv(4)
      version_info['version'] = unpack('>L', data)[0]
      # Version Number (Patch Number) in this addon
      print("%s Sent: Version: %s" % (host, version_info))
      Thread(target = SendCommands, args = (3, connection)).start()
    elif data == b'\x00\x00\x00\x02':
      working_file_request = {'namelen':0, 'working_filename':'', 'padding':0}
      data = connection.recv(4)
      working_file_request['namelen'] = unpack('>L', data)[0]
      data = connection.recv(working_file_request['namelen'])
      working_file_request['working_filename'] = data.decode('ascii')
      data = connection.recv(4)
      working_file_request['padding'] = unpack('>L', data)[0]
      # Always Null Assuming Unused
      print("%s Sent: File Request: %s" % (host, working_file_request))
      Thread(target = SendCommands, args = (4, connection, working_file_request['working_filename'])).start()
    elif data == b'\x00\x00\x00\x03':
      Thread(target = SendCommands, args = (5, connection)).start()      
    else:
      print("%s Sent Unhandeled Packets: %s" % (host, data))

def SendCommands(command, connection, target = None):
  if command == 0:
    # TODO: Impliment Patch Server Transfer
    # BYTE 0x01
    # BYTE[7] (all bytes 0x00)
    # BYTE[4] IP Address
    # BYTE[4] Port
    print("PATCH SERVER TRANSFER NOT FUNCTIONAL")
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
    print("NOTIFICATIONS NOT FUNCTIONAL")
  if command == 2:
    print("Server Sending: Protocol, Command, and UseSelf")
    for i in range(0,3):
      connection.send(b'\x00\x00\x00\x01')
  if command == 3:
    for working_file in _FILE_LIST:
      working_file_listing = {'working_filename':working_file.encode('ascii'),
                   'namelen':pack('>i', len(working_file.encode('ascii'))),
                   'working_filelen':pack('>i', path.getsize(path.join(_PATCH_DIR, working_file)))}
      print("Sever Sending File List Entry: %s" % working_file_listing)
      connection.send(working_file_listing['namelen'])
      connection.send(working_file_listing['working_filename'])
      connection.send(working_file_listing['working_filelen'])
    connection.send(b'\x00\x00\x00\x00')
  if command == 4:
    working_file_properties = {'working_filename':target,
                       'namelen':pack('>i', len(target.encode('ascii'))),
                       'working_filelen':path.getsize(path.join(_PATCH_DIR, target))}
    print("Sever Sending File: %s" % working_file_properties)
    connection.send(working_file_properties['namelen'])
    connection.send(working_file_properties['working_filename'].encode('ascii'))
    connection.send(pack('>i', working_file_properties['working_filelen']))
    with open(path.join(_PATCH_DIR, working_file_properties['working_filename']), 'rb') as working_file:
      block = working_file.read(1024)
      while block:
        connection.send(pack('>i', len(block)))
        connection.send(block)
        block = working_file.read(1024)
    print(r"Sever Sending File End: \x00 Block Size")
    connection.send(pack('>i', 0))
  if command == 5:
    connection.send(b'\x00\x00\x00\x00')
    # TODO: Handle Error when Client Disconnects.

opensocket = socket(AF_INET, SOCK_STREAM)
opensocket.bind((_HOST, _PORT))
print("%s listening on %i" % (_HOST, _PORT))
opensocket.listen(1)
print("Socket: Waiting on Connections.")
while _RUNNING:
  connection, address = opensocket.accept()
  _CLIENTS[address[0]] = Thread(target = PatchListener, args = (connection, address[0]))
  _CLIENTS[address[0]].start()
print("MAIN _RUNNING == False")
