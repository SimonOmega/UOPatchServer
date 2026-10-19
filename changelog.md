# Changelog

The historical entries below preserve the original README's release dates.
The 2026 entries consolidate the connection, transfer, logging and news reports
from this revision. No version numbers have been assigned.

## 2026-10-14

### Documentation and distribution

- Rewrote the README with installation, usage, configuration and descriptions
  of logging, resume, optional news and incomplete PAT/RTP pair errors.
- Preserved all original individual and community credits and added
  [Nerun](https://github.com/nerun).
- Moved the change history into this separate file.

### Optional patcher news

- Added a static HTTP service, enabled by a readable `news/index.html`, with
  `localhost:8080` as its default address.
- Advertised the page during initial patch negotiation using MOTD state 2,
  big-endian fields and a NUL-terminated URL/fallback payload. The client
  continues patching after receiving it.
- Kept the original patches-only response when the page is absent or HTTP
  cannot start. An unavailable HTTP port produces a logged warning.
- Supported HTML, CSS, text and static images, GET/HEAD and the patcher's
  `?lang=` query parameter, without changing the process's working directory.
- Rejected directory listings, hidden path components, traversal and symlinks
  resolving outside the news root.
- Handled browser connection cancellation, including resets during headers.
- Logged HTTP requests separately from patch download totals.
- Included an inactive HTML 4.01 Transitional sample using basic CSS.
- Documented that the patcher can persist its news URL in `vercfg.cfg`.
- The combined connection and news suite passed 53 tests on Python
  3.12.14/Linux.
- News rendering in Windows/Wine was validated in Wine 11.19.

### Logging, resume and startup validation

- Added append-only `UOPatchServer.log` beside the script, with serialized
  writes from concurrent connection threads.
- Recorded local connection/disconnection timestamps with numeric UTC offsets,
  file and payload totals, elapsed seconds, average MiB/s and endpoint filenames.
- Kept performance timing restricted to the interval from the first file send
  through the last completed file send, excluding later patch application.
- Identified interrupted transfers and reported completed-file totals only.
- Clarified the terminal message for client TCP resets without treating a reset
  alone as proof that patches were applied.
- Implemented resume using the final file-request field as a byte offset;
  retained the total size in the header and sent only the remaining suffix.
- Rejected offsets beyond EOF and verified resumed reconstruction over TCP
  using SHA-256. Actual-client resume remains to be validated.
- Required matching PAT/RTP basenames before opening a socket. Reported every
  missing counterpart in red and in the log, then exited without starting.
- Kept first-line-only PAT parsing and consecutive-counter listing.
- Resolved the archive and log beside the script, independent of the caller's
  working directory. This stage passed 35 regression tests.

### Transfer optimization

- Increased patch payload blocks from 1 KiB to 64 KiB and combined each length
  and payload into one `sendall` call.
- Static inspection of the supplied patcher showed a receive buffer allocated
  from the transmitted block length, supporting variable payload sizes.
- A synthetic 16 MiB loopback benchmark reduced median transfer time from
  0.2873 s to 0.0168 s and send calls from 32,772 to 260. These are Python
  receiver measurements, not native patch-application timings or TCP packet
  counts. Payload integrity was verified with SHA-256.
- Measured identical real-client sessions of 68 files and 135,070,171 bytes:
  21.868008 s at 1 KiB versus 7.052328 s at 64 KiB, approximately 3.10 times
  the throughput. The optimization initially passed 18 tests.

### Connection handling and source style

- Handled EOF, connection resets and broken pipes, with guaranteed socket
  cleanup and no redundant transfer terminators.
- Completed fragmented TCP field reads and used `sendall` for full writes.
- Kept responses ordered in each connection's worker thread.
- Reproduced a reset at the original traceback locations and passed 17 initial
  connection tests. Subsequently confirmed successful transfers and patch
  application with the real client.
- Standardized source indentation to four spaces.
- Corrected the shebang to `#!/usr/bin/env python3`.

By: Nerun  
Assisted-by: ChatGPT (GPT-6.1 Sol @ High)

## 2015-03-02

- Original README described the project as a functional beta test.
- The historical README's disconnect-error warning was removed, although the
  supplied server still lacked the handling later repaired in this revision.

## 2015-02-01

- Project resumed; housekeeping and cleanup, as recorded in the original README.

## 2013-08-07

- Code cleanup.

## 2013-07-07

- Initial release.
