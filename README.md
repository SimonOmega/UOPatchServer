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

Quickstart Guide
----------------
It is rather featureless atm to use it do the following:

1. Download Python 3.3.2 (or latest version).
2. Download this `UOPatchServer.py` file.
3. Create a folder named `archive` it the same directory as `UOPatchServer.py`
4. Copy your patch files `.rtp` and `.pat` to the `archive` folder.
5. Open your Ultima Online install directory.
6. Edit `vercfg.cfg` in a text editor.
7. Change the line ending in `8888` to `localhost 8888`
8. Run `python UOPatchServer.py` 
9. Wait a moment then run `UOPatch.exe` or `uo.exe`

The patcher will attach to the Python script and begin to transfer the patch files. `UOPatch.exe` will apply the patches and complete it's operations.

Problems
----------------
At this time `UOPatchServer.py` does not do any real verification on the clients current version, and the patches it has available.  What ever is in the `archive` folder will be applied.

You have to find your own patches.

[NEW UO Patches Repository](http://www.runuo.com/community/threads/new-uo-patches-repository.533684/)

Copy the patches to the `archive` folder, in their chronological order.

Script will error when client disconnects. I'll handle the error once I get time to dedicate to this project.

Downloads seem slow because the files are sent 1KB at a time.  I'll look at expanding that later.

Credits
------------
This could not be possible without help from the good people at RunUO.

The Following People put forth a great effort in this:

* [Community Effort to Restore Patching](http://www.runuo.com/community/threads/community-effort-to-restore-patching.534148/#post-3971271)
* [Morgan](http://www.runuo.com/community/members/morgan.36244/)
* [Praxiiz](http://www.runuo.com/community/members/praxiiz.12693/)
* [seanandre](http://www.runuo.com/community/members/seanandre.40964/)
* [Simon Omega](http://www.runuo.com/community/members/simon-omega.160203/)

