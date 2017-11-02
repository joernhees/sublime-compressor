# encoding: utf-8

import sublime
import sublime_plugin

''' 
# header references

- [gzip](https://tools.ietf.org/html/rfc1952)
- [bzip2](https://en.wikipedia.org/wiki/Bzip2#File_format)
- [xz](https://tukaani.org/xz/format.html)

'''
compression_modules = [
    { 'module' : 'gzip', 'depend' : 'zlib',  'extension' : '.gz', 'header':[0x1F,0x8B] },
    # since build 3114
    { 'module' : 'bz2',  'depend' : '_bz2',  'extension' : '.bz2', 'header' : [0x42,0x5A] },
    # future proof 20171031
    { 'module' : 'lzma', 'depend' : '_lzma', 'extension' : '.xz', 'header' : [0xDF,0x37,0x7A,0x58,0x5A,0x00] } 
]

compression_formats = {}

import sys
import importlib

for compression_module in compression_modules :
    dependendy = compression_module['depend'];
    if dependendy in sys.builtin_module_names :
        module    = compression_module['module']
        extension = compression_module['extension']
        decompressor = importlib.import_module(module);
        compression_formats[extension] = decompressor.open

def get_decompressor_by_filename(filename):
    for suffix, decompressor in compression_formats.items():
        if filename.endswith(suffix):
            return suffix, decompressor
    return None, None

def get_decompressor_by_header(filename):
    read_header = []
    with open(filename,"rb") as f:
        for compression_module in compression_modules :
            suffix = compression_module['extension']
            if not suffix in compression_formats:
                continue
            print(compression_module['module'])
            header = compression_module['header']
            len_header = len(header)
            while len(read_header) < len_header :
                read_header.append(ord(f.read(1)))
            if read_header[ 0: len_header ] == header:
                decompressor = compression_formats[suffix]
                return suffix, decompressor
    return None, None

class DecompressFileCommand(sublime_plugin.TextCommand):
    def run(self, edit, filename=None, suffix=None, decompressor=None):
        if filename is None:
            filename = self.view.file_name()
            if not filename:
                print("can't find filename for decompression")
                return
        if not suffix:
            suffix, decompressor = get_decompressor_by_filename(filename)
            if not suffix or not decompressor:
                print("trying to decompress unknown file format")
                return
        if not decompressor:
            decompressor = compression_formats[suffix]

        view = self.view
        view.set_name(filename[:-len(suffix)])

        pos = 0
        with decompressor(filename) as f:
            for line in f:
                # print(type(line), line)
                pos += view.insert(edit, pos, line.decode('utf-8'))

        view.set_read_only(True)

class OpenCompressedFile(sublime_plugin.EventListener):

    def on_load(self, view):
        filename = view.file_name()
        # suffix, decompressor = get_decompressor_by_filename(filename)
        suffix, decompressor = get_decompressor_by_header(filename)
        if suffix and decompressor:
            sublime.status_message("opening compressed file: " + filename)
            print("opening compressed file: " + filename)

            decomp_view = view.window().new_file()
            view.close()
            decomp_view.run_command(
                'decompress_file', {'filename': filename, 'suffix': suffix}
            )
