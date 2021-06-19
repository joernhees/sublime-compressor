sublime-compressor
==================

Small plugin which transparently decompresses gzip (.gz), bzip2 (.bz2), LZMA (.xz) files when opened in Sublime Text.

This is an alpha release, use with care, feedback & code welcome!

When opening a new file this plugin will check the magic bytes for identifying the compression format.
If this matches, the useless binary view of the file will be closed and a new temporary file will be opened as readonly, filled with the decompressed content.


Installation
------------
As usual via [Package Control](https://sublime.wbond.net/installation).


Current limitations (feedback & code welcome)
---------------------------------------------
- read only (would be cool if compressed file was substituted on save)
- no partial decompression (full file is decompressed and inserted in new file, maybe it's possible to just decompress a window)
- re-opening compressed file that is opened in a tab already will not jump to that tab but decompress it into a second copy
