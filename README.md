License
-------------------------------

Creative Commons
Attribution: CC BY

This license lets others distribute, remix, tweak, and build upon your work, even commercially, as long as they credit you for the original creation. This is the most accommodating of licenses offered. Recommended for maximum dissemination and use of licensed materials. 

[Attribution 3.0 Unported CC BY](http://creativecommons.org/licenses/by/3.0/)


Introduction
------------

### THIS IS A QUICK HACK.  

That being said this code is proof of concept and will be growing as there is time to work on it.  This was built as an example of a possible server solution and not just a wrapper to the UOPatch.exe application (localy).

### 01 Feb 2015 - I am working on making it an actual solution.

Quickstart Guide
----------------

It is rather featureless atm to use it do the following:

1. You have to find your own patches.  Try [NEW UO Patches Repository](http://www.runuo.com/community/threads/new-uo-patches-repository.533684/)
2. Copy the patches to the `archive` folder, in their chronological order.
3. Download Python 3.3.2 (or latest version).
4. Download this `UOPatchServer.py` file.
5. Create a folder named `archive` it the same directory as `UOPatchServer.py`
6. Copy your patch files `.rtp` and `.pat` to the `archive` folder.
7. Open your Ultima Online install directory.
8. Edit `vercfg.cfg` in a text editor.
9. Change the line ending in `8888` to `localhost 8888`
10. Run `python UOPatchServer.py` 
11. Wait a moment then run `UOPatch.exe` or `uo.exe`
12. NOTE: Downloads seem slow because the files are sent 1KB at a time.

The patcher will attach to the Python script and begin to transfer the patch files. `UOPatch.exe` will apply the patches and complete it's operations.


Tests
----------------

- Python Version: 3.2.2, 4.3.1
- Windows Version: Windows 7 Home Premium (64bit & 32bit), Windows 8 Pro (64bit & 32bit)
- Linux Version: CrunchBang 11 Waldorf (64bit), Fedora 21 (64bit)
- UO Client: 7.0.10.3, 7.0.11, 7.0.12, 7.21.1


Issues
----------------

- [ ] Send Customized Patch List
As of 01 Feb 2015, I am looking into the following issue as the first thing to resolve.
At this time `UOPatchServer.py` does not do any real verification on the clients current version, and the patches it has available.  What ever is in the `archive` folder will be applied.
- [ ] 3 Notifications from server to the patch client are not implemented.
- [ ] Can we continue an interupted download using the padding reported by a client's request for data?
- [ ] Increase the send block size. Files are sent 1KB at a time which is slow even for local traffic.
- [ ] Script may error when client disconnects. I think this is really just an OK from client waiting on an OK from server.  Tried a work around.


Credits
------------

In Febuary of 2015 I returned and RunUO has shutdown.  I am going to try and bring this project forward with help from the github comunity, and those at [PlayUO](http://www.playuo.org/).

* [@Iomega0318](https://github.com/Iomega0318)
* [@Nylar1971](https://github.com/Nylar1971)

###INITIAL CONTRIBUTERS

This could not be possible without help from the good people at RunUO.
The Following People put forth a great effort in this:

* [Community Effort to Restore Patching](http://www.runuo.com/community/threads/community-effort-to-restore-patching.534148/#post-3971271)
* [Morgan](http://www.runuo.com/community/members/morgan.36244/)
* [Praxiiz](http://www.runuo.com/community/members/praxiiz.12693/)
* [seanandre](http://www.runuo.com/community/members/seanandre.40964/)
* [Simon Omega](http://www.runuo.com/community/members/simon-omega.160203/)


Change Log
------------

Jul - 07 - 2013 - Initial Release.  
Aug - 07 - 2013 - Code Clean Up.  
Feb - 01 - 2015 - Returned, House Keeping and cleanup.  
