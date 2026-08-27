This application aggregates and uses the following third-party software executables.
None of these programs have been modified.
These are separate works and are subject to their own respective licenses.

Full license texts are in the LICENSES folder.

1. PrusaSlicer
   - License: GNU Affero General Public License v3.0 (AGPL-3.0)
   - Source Code: https://github.com/prusa3d/PrusaSlicer
   - Files: prusa-slicer-console.exe, prusa-slicer.exe,
     prusa-gcodeviewer.exe, PrusaSlicer.dll, and everything in
     assets/bin/resources except the fonts listed at 5

2. OpenSCAD
   - License: GNU General Public License v2.0 (GPL-2.0)
   - Source Code: https://github.com/openscad/openscad
   - Files: openscad.exe

3. FFmpeg
   - License: GNU Lesser General Public License (LGPL) v2.1 or later
   - Source Code: https://ffmpeg.org/download.html
   - No longer bundled as of version 2.1. Version 1.3.1 referred to
     ffmpeg.exe and ffprobe.exe; version 2.1 does not use them and does not
     ship them. The license text is kept here for the earlier releases.

The following libraries are shipped alongside OpenSCAD and PrusaSlicer
because those programs need them to run:

4. Libraries used by OpenSCAD
   - GMP (libgmp-10.dll) - LGPL v3 or GPL v2 - https://gmplib.org/
   - MPFR (libmpfr-4.dll) - LGPL v3 - https://www.mpfr.org/
   - Mesa (mesa/opengl32.dll) - MIT - https://www.mesa3d.org/

5. Libraries and fonts used by PrusaSlicer
   - Open CASCADE Technology (OCCTWrapper.dll) - LGPL v2.1 with an
     exception - https://dev.opencascade.org/
   - Noto Sans and Noto Sans CJK (assets/bin/resources/fonts) -
     SIL Open Font License 1.1 - (c) 2015 Google Inc. -
     https://openfontlicense.org/

6. Microsoft redistributable runtime files
   - msvcp140.dll, msvcp140_codecvt_ids.dll, vcruntime140.dll,
     vcruntime140_1.dll, api-ms-win-crt-runtime-l1-1-0.dll,
     WebView2Loader.dll
   - Distributed under Microsoft's redistributable terms, which permit them
     to accompany a program that requires them.

The Windows executable is built with PyInstaller, which packs the following
into it:

7. Python and its libraries
   - Python - Python Software Foundation License 2.0 -
     https://docs.python.org/3/license.html
   - requests - Apache License 2.0 - https://github.com/psf/requests
   - urllib3 - MIT - https://github.com/urllib3/urllib3
   - certifi - Mozilla Public License 2.0 -
     https://github.com/certifi/python-certifi
   - charset-normalizer - MIT - https://github.com/jawah/charset_normalizer
   - idna - BSD 3-Clause - https://github.com/kjd/idna
   - OpenSSL (libssl-3-x64.dll, libcrypto-3-x64.dll) - Apache License 2.0 -
     https://www.openssl.org/source/

8. PyInstaller
   - License: GPL v2 with an exception permitting the programs it builds to
     carry any license. Its bootloader code is present inside the executable.
   - Source Code: https://github.com/pyinstaller/pyinstaller

The use of these tools does not imply that the BgeraPrint source code is governed by the GPL/AGPL.
BgeraPrint interacts with these tools via Command Line Interface (CLI) as a separate process.
