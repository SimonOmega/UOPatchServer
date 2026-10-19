# UOPatchServer

A Python server for the historical **Ultima Online Classic Client** patch
protocol. It serves existing PAT/RTP patch files to `UOPatch.exe`; the patcher
downloads and applies them. An optional HTTP service supplies a page for the
patcher's embedded news browser.

This revision includes reliable TCP transfers, 64 KiB payload blocks, download
resume, persistent session logs and validation of PAT/RTP pairs before startup.
The change history is in [changelog.md](changelog.md).

## Requirements

- Python 3. This revision was validated with Python 3.12.14 and 3.14.8 on Linux;
  use that runtime or a compatible newer Python 3 installation. No third-party
  Python packages are required.
- A compatible historical Ultima Online patcher and its client installation.
- The PAT and RTP files appropriate for that client's patch sequence.
- A writable directory for `UOPatchServer.log` beside the script.

Game files and patches are not included. The supplied patcher analyzed during
development belongs to the 5.0.9.1 through 7.0.23.1 range. Its protocol was used
to implement resume and news support; compatibility with every historical
patcher is not claimed.

## Installation

1. Extract the package into its own directory.
2. Create `archive` beside `UOPatchServer.py`.
3. Place matching `.pat` and `.rtp` files directly inside `archive`. Each pair
   must have exactly the same basename, with lowercase extensions. For example:

   ```text
   archive/uoml_win32_6-0-12-0.pat
   archive/uoml_win32_6-0-12-0.rtp
   ```

4. In the Ultima Online installation, edit `vercfg.cfg`. Replace the patch
   server line, traditionally `compassion.owo.com 8888`, with:

   ```text
   localhost 8888
   ```

   Preserve the remaining configuration fields. You do not need to add a news
   URL manually: the server supplies it when a page is available.

5. Optionally enable the news page as described below.

The working directory can contain:

| Path | Purpose |
| --- | --- |
| `UOPatchServer.py` | Patch server and optional HTTP service |
| `archive/` | Your matching PAT/RTP files |
| `news/index.html` | Optional news page; create it or activate the sample |
| `news/index.html.example` | Included sample, inactive until renamed |
| `news/images/` | Optional directory for your images |
| `UOPatchServer.log` | Created automatically; previous entries are preserved |
| `README.md` | Installation and usage |
| `changelog.md` | Original and current revision history |

## Usage

Start the server before opening the patcher.

On Linux:

```bash
python3 UOPatchServer.py
```

On Windows with the Python launcher:

```text
py -3 UOPatchServer.py
```

Then run `UOPatch.exe` or the installation's launcher that invokes it, such as
`uo.exe`. Keep the server running while files are downloaded. The patcher
applies the received patches and can close its connection after completion.
Press Ctrl+C in the server terminal to stop accepting connections and shut
down the news service. Let active downloads finish before stopping or updating
the server.

The default patch listener is `localhost:8888`; the optional news listener is
`localhost:8080`. These defaults assume that server and patcher run on the same
computer. `archive`, `news` and the log are located relative to the script,
regardless of the directory from which you launch it.

To update an existing installation, stop the server and replace the script.
Preserve your `archive`, existing log and any customized news files.

## Features

### Patch transfers and resume

Files are sent in 64 KiB blocks. Each block's length and content are submitted
together, reducing small socket writes. TCP reads are completed even when
requests arrive in fragments, and responses remain ordered per connection.

When the patcher requests a byte offset for a partially downloaded file, the
server sends only the remaining bytes. The header still advertises the total
file size. An offset beyond the file size is rejected and logged. The client
must retain the correct prefix of the same file; the request does not include
a hash that the server could use to verify that prefix.

The catalog reads the first line of each PAT file for its client identifier and
patch counter. File ordering comes from those counters, rather than the order
in which files were copied. Patch listing follows consecutive counters and
stops at a missing counter; complete pairs on either side of a gap do not make
that gap downloadable automatically.

### Persistent log

`LOG = True` enables session summaries and download measurements. The script
appends to `UOPatchServer.log` beside itself; it does not erase earlier sessions.
Connection timestamps use the system's local timezone, including seconds and
the numeric UTC offset.

A completed session is recorded on one line:

```text
[127.0.0.1] connected=2026-10-14 12:12:57 -0300; download: files=68; bytes=135070171; elapsed=7.052328 s; average=18.265 MiB/s; first=uoml_win32_6-0-0-0.pat; last=uoml_win32_6-0-14-3.rtp; disconnected=2026-10-14 12:16:38 -0300
```

- `files` counts completed PAT and RTP transfers.
- `bytes` counts their payload bytes, excluding protocol headers. Resumed
  transfers count only the bytes actually sent.
- `elapsed` runs from the first file send to the end of the last completed
  file send. It includes gaps between requests, but excludes the subsequent
  wait while the patcher applies patches.
- `average` is payload throughput in MiB/s: bytes divided by elapsed seconds
  and 1,048,576.
- `first` and `last` identify the transfer endpoints. Sessions without file
  transfers report zero totals and `-` filenames.

Interrupted sends are identified with `status=incomplete`; their totals cover
completed files only. HTTP requests have separate log entries and do not add
to patch file or byte counts. The patch timing boundaries remain the same.
Completing a server send is not proof that the client applied a patch.

The terminal describes a reset without an unhandled traceback:

```text
[127.0.0.1] The client closed the connection (TCP reset, errno 104).
```

The **errno** can differ by operating system. A reset after successful patching
describes connection closure; it does not independently establish patching
success. Detailed patch protocol messages remain in the terminal.

Set `LOG = False` to disable session measurements, summaries and HTTP request
logging. Startup validation errors remain recorded.

### Optional news page and images

Create `news/index.html` beside the script. To use the included template,
rename `news/index.html.example` to `news/index.html` and edit its contents.

With a readable page at startup, the server starts HTTP on port 8080 and sends
its URL to the patcher during the initial negotiation. The embedded browser
fetches the HTML and its referenced resources while patching proceeds normally.
The page can contain text only, or text with images, links and stylesheets.

Without `news/index.html`, the server starts in patches-only mode and opens no
HTTP listener. If the HTTP port is unavailable, a warning is logged and patches
remain available. Restart the server after adding a page if HTTP was disabled
at startup. Edits to an enabled page and its resources are read on subsequent
requests without restarting. Removing the page stops advertising it to new
patch connections; the HTTP listener remains open until shutdown.

Test the page at `http://localhost:8080/index.html`. The patcher adds a `?lang=`
query parameter; this service accepts it and returns the same page. Automatic
language selection is not implemented.

Put resources inside `news` and reference them with relative paths:

```html
<img src="images/banner.jpg" alt="Shard banner" width="440" height="100">
<link rel="stylesheet" type="text/css" href="style.css">
```

Supported file extensions are HTML/HTM, CSS, TXT, GIF, JPG/JPEG, PNG, BMP and
ICO. Directory listings, hidden path components and access outside the news
directory are rejected. The service does not execute dynamic code.

> [!IMPORTANT]
>
> **The historical patcher uses the Internet Explorer WebBrowser control. The
sample uses HTML 4.01 Transitional and basic CSS, without JavaScript or modern
layout features**. Use simple headings, paragraphs, lists and tables; JPG and
GIF are conservative image choices. Declare your page's encoding explicitly, as
the sample does for UTF-8. The server does not convert or validate your HTML.
Actual rendering depends on the Windows/Wine browser engine and should be
checked in your patcher.

The patcher can save the received URL in the last news field of `vercfg.cfg`.
After news is disabled, it may still try that saved address at launch. To remove
it, clear only the saved news field and preserve the other configuration fields.

### Incomplete PAT/RTP pairs

Before opening either listener, the server checks every PAT/RTP basename in
`archive`. If either member is missing, it lists every missing counterpart,
prints the errors in red, records them in the log and refuses to start.

For an RTP with no matching PAT, an entry looks like:

```text
ERROR 2026-10-14 12:12:57 -0300: incomplete pair in /path/to/archive; missing uoml_win32_6-0-12-0.pat
```

The inverse case reports the missing `.rtp`. Supply the correct counterpart or
remove the incomplete pair from the served archive before starting again. This
validation checks paired filenames, not the authenticity or applicability of the
patch contents. A missing archive, invalid first PAT line or unwritable log also
prevents startup; an unwritable log can only be reported in the terminal.

## Configuration

Settings are near the top of `UOPatchServer.py`:

| Setting | Default | Purpose |
| --- | --- | --- |
| `LOG` | `True` | Session measurements, summaries and HTTP request logging |
| `_PATCH_BLOCK_SIZE` | `64 * 1024` | Patch payload block size in bytes. Increasing it will not increase speed, but it will increase buffer usage and use more memory per connection. |
| `NEWS_BIND_HOST` | `'localhost'` | Address on which the HTTP service listens |
| `NEWS_PORT` | `8080` | HTTP port |
| `NEWS_PUBLIC_HOST` | `'localhost'` | Hostname advertised to the patcher |
| `NEWS_FALLBACK_TEXT` | English welcome message | Text shown if the browser control is unavailable |

The patch listener's address and port are configured by `listener.bind` in
`main()`. For clients on another computer, both listeners must be reachable,
the client's CFG must point to the patch server, and `NEWS_PUBLIC_HOST` must
name that server from the client's perspective. Do not advertise `0.0.0.0` as
the news host. Use an ASCII hostname or IPv4 address, without URL delimiters.

## Credits

The original author's and community's credits are retained:

- [Simon Omega](http://www.runuo.com/community/members/simon-omega.160203/),
  the original author.
- [Iomega0318](https://github.com/Iomega0318)
- [Nylar1971](https://github.com/Nylar1971)
- [Morgan](http://www.runuo.com/community/members/morgan.36244/)
- [Praxiiz](http://www.runuo.com/community/members/praxiiz.12693/)
- [seanandre](http://www.runuo.com/community/members/seanandre.40964/)
- The RunUO community and its
  [Community Effort to Restore Patching](http://www.runuo.com/community/threads/community-effort-to-restore-patching.534148/#post-3971271).
- The GitHub community and [PlayUO](http://www.playuo.org/), acknowledged in
  the original project's continuation.
- [Nerun](https://github.com/nerun) contributed to this revision through project
coordination, feature requirements, real-client validation and comparative
performance measurements.

Historical community links are retained for attribution.
