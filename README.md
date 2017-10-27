sublime-compressor
==================

Small plugin which transparently decompresses gzip (.gz) and bzip2 (.bz2) files when opened in Sublime Text.

This is an alpha release, use with care, feedback & code welcome!


When opening a new file this plugin will check the filename for a known compression suffix (.gz,.bz2 currently).
If this matches, the useless binary view of the file will be closed and a new temporary file will be opened, filled with the decompressed content.


Installation
------------
As usual via [Package Control](https://sublime.wbond.net/installation).


Current limitations (feedback & code welcome)
---------------------------------------------
- read only (would be cool if compressed file was substituted on save)
- compressed file contents are assumed to be 'utf-8' encoded (maybe decompress into temp file which is opened the normal way instead? (allows for encoding detection))
- single threaded (decompression should take place in bg thread)
- no partial decompression (full file is decompressed and inserted in new file, maybe it's possible to just decompress a window)
- no xz, lzma, flat zip-file support
- compressor detection only based on filename, maybe use something similar to the `file` command
- re-opening compressed file that is opened in a tab already will not jump to that tab but decompress it into a second copy
