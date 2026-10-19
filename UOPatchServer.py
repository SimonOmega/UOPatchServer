#!/usr/bin/env python3
'''Classes that allow the implementation of an UltimaOnline style RTP Patch
Server.

Implemented classes:
  PatchCatalog
  PatchHandler

PatchCatalog creates and returns a multidimensional Dictionary in the
following form:
{'Win32_UOSA': {34: '\\archive\\uosa_win32_7-0-11-0',
                35: '\\archive\\uosa_win32_7-0-11-1',
                36: '\\archive\\uosa_win32_7-0-11-2',}}
Which the data represents:
{'Client Name': {Patch Release Version: 'Path/File Name (no extension)', ... }}

PatchHandler takes the following items:
  a Connection from an accepted connection
  an IP Address from and accepted connection
  a Patch Catalog
All connections are from a socket of type socket(AF_INET, SOCK_STREAM).
Patch Handler listens for Client requests and responds appropriately.

Started on Jul 07, 2013
@author: simonomega
'''

from os import fstat, listdir, path, sep
from threading import Lock, Thread
from socket import socket, AF_INET, SOCK_STREAM, SHUT_RDWR
from struct import pack, unpack
from time import perf_counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import unquote, urlsplit
import shutil
import sys

LOG = True

# Optional static news, served only when news/index.html exists.
NEWS_BIND_HOST = 'localhost'
NEWS_PORT = 8080
NEWS_PUBLIC_HOST = 'localhost'
NEWS_FALLBACK_TEXT = 'Welcome. Patch downloads will continue normally.'

_PATCH_BLOCK_SIZE = 64 * 1024
LOG_FILE = path.join(path.dirname(path.abspath(__file__)), 'UOPatchServer.log')
_LOG_LOCK = Lock()


def log_timestamp():
    return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')


def write_log(message, error=False):
    # Serialize appends so summaries from different clients cannot interleave.
    with _LOG_LOCK:
        with open(LOG_FILE, 'a', encoding='utf-8') as logfile:
            logfile.write(message + '\n')
        print('\033[31m' + message + '\033[0m' if error else message)


class CatalogError(ValueError):
    pass


class PatchRequestError(ValueError):
    pass


_NEWS_CONTENT_TYPES = {
    '.html': 'text/html',
    '.htm': 'text/html',
    '.css': 'text/css',
    '.gif': 'image/gif',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.bmp': 'image/bmp',
    '.ico': 'image/x-icon',
    '.txt': 'text/plain',
}


def news_file_path(directory, target):
    """Resolve a static resource without exposing files outside news."""
    try:
        requested = unquote(urlsplit(target).path, errors='strict')
    except (ValueError, UnicodeError):
        return None
    requested = requested.replace('\\', '/')
    if requested == '/':
        requested = '/index.html'
    parts = requested.lstrip('/').split('/')
    if any(not part or part.startswith('.') or ':' in part or '\0' in part
           for part in parts):
        return None
    if path.splitext(parts[-1])[1].lower() not in _NEWS_CONTENT_TYPES:
        return None
    root = path.realpath(directory)
    filename = path.realpath(path.join(root, *parts))
    if not path.normcase(filename).startswith(path.normcase(root + sep)):
        return None
    if path.splitext(filename)[1].lower() not in _NEWS_CONTENT_TYPES:
        return None
    return filename if path.isfile(filename) else None


class NewsRequestHandler(BaseHTTPRequestHandler):
    # HTTP/1.0 with Content-Length also works with old IE/Wine browsers.
    protocol_version = 'HTTP/1.0'

    def setup(self):
        self.request.settimeout(10)
        BaseHTTPRequestHandler.setup(self)

    def handle(self):
        try:
            BaseHTTPRequestHandler.handle(self)
        except (ConnectionError, TimeoutError):
            # Navigation or patcher exit can cancel headers as well as content.
            pass

    def do_GET(self):
        self.send_news(head_only=False)

    def do_HEAD(self):
        self.send_news(head_only=True)

    def send_news(self, head_only):
        filename = news_file_path(self.server.news_directory, self.path)
        if filename is None:
            self.send_error(404, 'News resource not found')
            return
        try:
            content = open(filename, 'rb')
        except OSError:
            self.send_error(404, 'News resource not found')
            return
        with content:
            stat = fstat(content.fileno())
            self.send_response(200)
            # Let the page's meta tag specify UTF-8 or a legacy encoding.
            self.send_header('Content-Type',
                             _NEWS_CONTENT_TYPES[path.splitext(filename)[1].lower()])
            self.send_header('Content-Length', str(stat.st_size))
            self.send_header('Last-Modified', self.date_time_string(stat.st_mtime))
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            if not head_only:
                shutil.copyfileobj(content, self.wfile)

    def log_message(self, format, *args):
        if LOG:
            message = (format % args).replace('\r', ' ').replace('\n', ' ')
            # Keep HTTP entries independent of the patch download summary.
            write_log('[%s] HTTP %s: %s' %
                      (self.client_address[0], log_timestamp(), message))


class NewsHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class NewsService:
    """Own the optional HTTP listener and its advertised patcher URL."""

    def __init__(self, directory, host=None, port=None, public_host=None):
        self.directory = directory
        self.host = NEWS_BIND_HOST if host is None else host
        self.port = NEWS_PORT if port is None else port
        self.public_host = NEWS_PUBLIC_HOST if public_host is None else public_host
        self.server = None
        self.thread = None

    def has_page(self):
        filename = news_file_path(self.directory, '/index.html')
        if filename is None:
            return False
        try:
            with open(filename, 'rb'):
                pass
        except OSError:
            return False
        return True

    def start(self):
        if not self.has_page():
            print('News disabled: no readable news/index.html; patches only.')
            return
        try:
            server = NewsHTTPServer((self.host, self.port), NewsRequestHandler)
        except OSError as error:
            write_log('WARNING %s: news HTTP unavailable; patches only: %s' %
                      (log_timestamp(), error))
            return
        server.news_directory = self.directory
        self.server = server
        self.thread = Thread(target=server.serve_forever)
        self.thread.daemon = True
        try:
            self.thread.start()
        except RuntimeError:
            self.server = None
            server.server_close()
            raise
        print('News enabled: %s' % self.get_url())

    def get_url(self):
        # Recheck at each hello so a removed page is no longer advertised.
        if self.server is None or not self.has_page():
            return None
        return 'http://%s:%i/index.html' % (
            self.public_host, self.server.server_port)

    def close(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            self.server = None


class PatchHandler:
    '''
    PatchHandler takes the following items:
      a Connection from an accepted connection
      an IP Address from and accepted connection
      a Patch Catalog
    All connections are from a socket of type socket(AF_INET, SOCK_STREAM).
    Patch Handler listens for Client requests and responds appropriately.
    '''

    def __init__(self, conn, add, catalog, connected_at=None, news=None):
        self.listen = True
        self.buffer_len = 4
        self.connection = conn
        self.address = add
        self.reported_version = -1
        self.reported_client = 'NONE'
        self.file_request = None
        self.patch_catalog = catalog
        self.news = news
        self.connected_at = (
            connected_at if connected_at is not None else log_timestamp()
        )
        self.disconnected_at = None
        self.log_started = None
        self.log_last_finished = None
        self.log_first_file = None
        self.log_last_file = None
        self.log_bytes = 0
        self.log_files = 0
        self.log_transfer_in_progress = False

    def log_begin_transfer(self, filename):
        if not LOG:
            return
        if self.log_started is None:
            self.log_started = perf_counter()
            self.log_first_file = filename
        self.log_transfer_in_progress = True

    def log_end_transfer(self, filename, size):
        if not LOG:
            return
        # Freeze the endpoint before the client applies downloaded patches.
        self.log_last_finished = perf_counter()
        self.log_last_file = filename
        self.log_bytes += size
        self.log_files += 1
        self.log_transfer_in_progress = False

    def log_download_summary(self):
        if not LOG:
            return
        elapsed = (self.log_last_finished - self.log_started
            if self.log_last_finished is not None else 0.0)
        speed = (
            self.log_bytes / (1024 * 1024 * elapsed) if elapsed > 0 else 0.0
        )
        message = ("[%s] connected=%s; download: files=%i; bytes=%i; "
            "elapsed=%.6f s; "
            "average=%.3f MiB/s; first=%s; last=%s; disconnected=%s" %
            (self.address, self.connected_at, self.log_files, self.log_bytes,
                elapsed, speed, self.log_first_file or '-',
                self.log_last_file or '-',
                self.disconnected_at))
        if self.log_transfer_in_progress:
            message += (
                "; status=incomplete (totals cover completed files only)"
            )
        write_log(message)

    def recv_exact(self, size):
        # TCP may split a single protocol field across several reads.
        data = bytearray()
        while len(data) < size:
            block = self.connection.recv(size - len(data))
            if not block:
                raise EOFError(
                    "Client closed the connection (%i of %i bytes received)" %
                    (len(data), size))
            data.extend(block)
        return bytes(data)

    def command_server_trasnfer(self):
        # TODO: Implement Patch Server Transfer
        # BYTE 0x01
        # BYTE[7] (all bytes 0x00)
        # BYTE[4] IP Address
        # BYTE[4] Port
        print(
            "\nPatch Server does not support PatchServerTrasfer at this time.\n"
        )

    def command_notification(self, url, message=NEWS_FALLBACK_TEXT):
        # MOTD state 2 updates the URL and continues normal patch negotiation.
        # The legacy client expects ASCII URL, LF, fallback text and final NUL.
        if any(character in url for character in '\r\n\0?#'):
            raise PatchRequestError('News URL contains an unsupported delimiter')
        if '\0' in message:
            raise PatchRequestError('News fallback text contains a NUL byte')
        payload = (url + '\n' + message + '\0').encode('ascii')
        self.connection.sendall(pack('>4I', 1, 1, 2, len(payload)) + payload)
        print('[%s] News URL sent: %s' % (self.address, url))

    def command_use_self(self):
        print("\nServer Sending: Protocol, Command, and UseSelf\n")
        for i in range(0, 3):
            self.connection.sendall(b'\x00\x00\x00\x01')

    def command_patch_list_data(self):
        requested_version = (self.reported_version + 1)
        while (
            requested_version
            in self.patch_catalog.getCatalog()[self.reported_client]
        ):
            p_file = path.join(self.patch_catalog.getCatalog()['path'],
                self.patch_catalog.getCatalog()[self.reported_client][
                    requested_version
                ] + '.pat')
            p_head, p_tail = path.split(p_file)
            r_file = path.join(self.patch_catalog.getCatalog()['path'],
                self.patch_catalog.getCatalog()[self.reported_client][
                    requested_version
                ] + '.rtp')
            r_head, r_tail = path.split(r_file)
            file_listing = {'patname': p_tail.encode('ascii'),
                'patnamelen': pack('>i',
                    len(p_tail.encode('ascii'))),
                'patlen': pack('>i',
                    path.getsize(p_file)),
                'rtpname': r_tail.encode('ascii'),
                'rtpnamelen': pack('>i',
                    len(r_tail.encode('ascii'))),
                'rtplen': pack('>i',
                    path.getsize(r_file))
            }
            self.connection.sendall(file_listing['patnamelen'])
            self.connection.sendall(file_listing['patname'])
            self.connection.sendall(file_listing['patlen'])
            self.connection.sendall(file_listing['rtpnamelen'])
            self.connection.sendall(file_listing['rtpname'])
            self.connection.sendall(file_listing['rtplen'])
            print("\nSERVER << sent %s PatchListData entry %s\n" %
                (self.address, file_listing))
            requested_version = requested_version + 1
        self.connection.sendall(b'\x00\x00\x00\x00')
        return

    def command_send_patch(self):
        if self.file_request is None or self.file_request['filename'] is None:
            print(
                "\nTrying to send PatchData to Client, but no target_file "
                "name was sent to command 4.\n"
            )
            self.command_done_transfer()
        else:
            send_file = path.join(self.patch_catalog.getCatalog()['path'],
                self.file_request['filename'])
            file_properties = {'filename': self.file_request['filename'],
                'filenamelen': pack(
                    '>i', len(self.file_request['filename'].encode('ascii'))
                ),
                'filesize': path.getsize(send_file)}
            print("\nSERVER << sending %s PatchData for %s\n" %
                (self.address, file_properties))
            offset = self.file_request.get('padding', 0)
            if offset < 0 or offset > file_properties['filesize']:
                raise PatchRequestError(
                    "Invalid resume offset for %s: %i (file size %i)" %
                    (file_properties['filename'], offset,
                        file_properties['filesize']))
            self.log_begin_transfer(file_properties['filename'])
            self.connection.sendall(file_properties['filenamelen'])
            self.connection.sendall(
                file_properties['filename'].encode('ascii')
            )
            self.connection.sendall(pack('>i', file_properties['filesize']))
            with open(send_file, 'rb') as push_file:
                # The offset is the existing partial file length on the client.
                push_file.seek(offset)
                block = push_file.read(_PATCH_BLOCK_SIZE)
                while block:
                    # Send length and payload together to avoid tiny writes.
                    self.connection.sendall(pack('>i', len(block)) + block)
                    block = push_file.read(_PATCH_BLOCK_SIZE)
            print(
                r"SERVER << done sending %s PatchData for %s sending "
                r"\x00\x00\x00\x00 Block Size" %
                (self.address, file_properties)
            )
            self.connection.sendall(pack('>i', 0))
            self.log_end_transfer(
                file_properties['filename'], file_properties['filesize'] - offset
            )
        self.file_request = {'filenamelen': 0, 'filename': None, 'padding': 0}
        return

    def command_done_transfer(self):
        self.connection.sendall(b'\x00\x00\x00\x00')

    def requesthandler(self):
        self.data = self.recv_exact(self.buffer_len)
        if self.data == b'\x00\x00\x00\x15':
            print("\nCLIENT >> %s sent Client Hello/Request (%s)\n" %
                (self.address, self.data))
            news_url = self.news.get_url() if self.news is not None else None
            if news_url is None:
                self.command_use_self()
            else:
                self.command_notification(news_url)
        elif self.data == b'\x00\x00\x00\x01':
            self.data = self.recv_exact(4)
            namelen = unpack('>L', self.data)[0]
            self.data = self.recv_exact(namelen)
            self.reported_client = self.data.decode('ascii')
            self.data = self.recv_exact(4)
            self.reported_version = unpack('>L', self.data)[0]
            print("\nCLIENT >> %s sent Version Information %s %s\n" %
                (self.address, self.reported_client, self.reported_version))
            # TODO: Only send a new list if the version has changed.
            if (
                self.reported_client not in self.patch_catalog.getCatalog()
                or (self.reported_version + 1) not in
                self.patch_catalog.getCatalog()[self.reported_client]
            ):
                print("\nCLIENT ||  All Patched UP, No new patches.\n")
                self.listen = False
                self.connection.sendall(b'\x00\x00\x00\x00')
                return
            else:
                self.command_patch_list_data()
        elif self.data == b'\x00\x00\x00\x02':
            self.file_request = {'filenamelen': 0, 'filename': None, 'padding': 0}
            self.data = self.recv_exact(4)
            self.file_request['filenamelen'] = unpack('>L', self.data)[0]
            self.data = self.recv_exact(self.file_request['filenamelen'])
            self.file_request['filename'] = self.data.decode('ascii')
            self.data = self.recv_exact(4)
            self.file_request['padding'] = unpack('>L', self.data)[0]
            # The final request field is the resume offset, in bytes.
            print("\nCLIENT >> %s sent a Request for File %s (%s)\n" % (
                self.address,
                    self.file_request['filename'],
                    self.file_request))
            self.command_send_patch()
        elif self.data == b'\x00\x00\x00\x03':
            self.command_done_transfer()
        else:
            print("\nCLIENT >> %s sent unhandled message %s\n" %
                (self.address, self.data))
            self.listen = False

    def run(self):
        print("[%s] connected=%s" % (self.address, self.connected_at))
        try:
            while self.listen:
                self.requesthandler()
        except EOFError:
            self.disconnected_at = log_timestamp()
            print("[%s] The client closed the connection." % self.address)
        except ConnectionError as error:
            self.disconnected_at = log_timestamp()
            if isinstance(error, ConnectionResetError):
                message = (
                    "The client closed the connection (TCP reset, errno %s)." %
                    error.errno
                )
            else:
                message = (
                    "Connection closed by the client or unavailable (errno %s)." %
                    error.errno
                )
            print("[%s] %s" % (self.address, message))
            if self.log_transfer_in_progress:
                write_log("[%s] ERROR %s: transfer interrupted; %s" %
                    (self.address, self.disconnected_at, message), error=True)
        except PatchRequestError as error:
            self.disconnected_at = log_timestamp()
            write_log("[%s] ERROR %s: %s" %
                (self.address, self.disconnected_at, error), error=True)
        finally:
            self.listen = False
            if self.disconnected_at is None:
                self.disconnected_at = log_timestamp()
            # Do not send another terminator after EOF or a connection reset.
            try:
                self.connection.shutdown(SHUT_RDWR)
            except OSError:
                # Always close the socket, even if the peer disconnected.
                pass
            self.connection.close()
            self.log_download_summary()


class PatchCatalog:
    '''
    PatchCatalog creates and returns a multidimensional Dictionary in the
    following form:
    {'Win32_UOSA': {34: '\\archive\\uosa_win32_7-0-11-0',
                    35: '\\archive\\uosa_win32_7-0-11-1',
                    36: '\\archive\\uosa_win32_7-0-11-2',}}
    Which the data represents:
    {'Client Name': {Patch Release Version: 'Path/File Name (no extension)',
                     ... }}
    '''
    def __init__(self, directory):
        self.catalog = {}
        self.catalog['path'] = directory
        filenames = {name for name in listdir(directory)
            if path.isfile(path.join(directory, name))}
        pats = {
            path.splitext(name)[0]
            for name in filenames if name.endswith('.pat')
        }
        rtps = {
            path.splitext(name)[0]
            for name in filenames if name.endswith('.rtp')
        }
        incomplete = sorted(pats ^ rtps)
        if incomplete:
            for stem in incomplete:
                missing = '.rtp' if stem in pats else '.pat'
                write_log("ERROR %s: incomplete pair in %s; missing %s%s" %
                    (log_timestamp(), directory, stem, missing), error=True)
            raise CatalogError(
                "%i incomplete PAT/RTP pair(s)" % len(incomplete)
            )
        for a_file in sorted(filenames):
            if a_file.endswith(".pat"):
                with open(path.join(directory, a_file)) as patch_info:
                    client, version = next(patch_info).rstrip().split(' ')
                    if client in self.catalog:
                        self.catalog[client][int(version)] = (
                            a_file.split('.')[0]
                        )
                    else:
                        self.catalog[client] = {}
                        self.catalog[client][int(version)] = (
                            a_file.split('.')[0]
                        )
        print("Patch Catalog\n%s\n" % self.catalog)

    def getCatalog(self):
        return self.catalog


def main():
    # Enable ANSI colors in modern Windows consoles as well as POSIX terminals.
    if sys.platform == 'win32':
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 0x0004)
    try:
        # Check log writability before catalog validation or binding a socket.
        with open(LOG_FILE, 'a', encoding='utf-8'):
            pass
    except OSError as error:
        print("\033[31mERROR: could not open %s: %s\033[0m" %
            (LOG_FILE, error))
        return 1
    patch_dir = path.join(path.dirname(path.abspath(__file__)), 'archive')
    print("Generating Patch Catalog\n")
    try:
        catalog = PatchCatalog(patch_dir)
    except (OSError, ValueError, StopIteration) as error:
        write_log("ERROR %s: server not started: %s" %
            (log_timestamp(), error), error=True)
        return 1
    news = NewsService(path.join(path.dirname(path.abspath(__file__)), 'news'))
    try:
        with socket(AF_INET, SOCK_STREAM) as listener:
            listener.bind(('localhost', 8888))
            listener.listen(5)
            news.start()
            print("localhost listening on 8888\n")
            while True:
                print("Socket: Waiting on Connections.\n")
                connection, ip_port = listener.accept()
                connected_at = log_timestamp()
                Thread(target=PatchHandler(connection, ip_port[0], catalog,
                        connected_at=connected_at, news=news).run).start()
    except KeyboardInterrupt:
        print('\nPatch server stopped.')
    finally:
        news.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
