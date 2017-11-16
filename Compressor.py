# encoding: utf-8
'''
Sublime text de-Compressor
View compressed files ( gzip, bzip2 ) content in sublime text

'''
from os.path import basename, join
from os import remove
import sys
from shutil import copyfileobj
from tempfile import mkdtemp

import sublime
import sublime_plugin
''' 
# header references

- [gzip](https://tools.ietf.org/html/rfc1952)
- [bzip2](https://en.wikipedia.org/wiki/Bzip2#File_format)
- [xz](https://tukaani.org/xz/format.html)

'''
compression_modules = [
    {'module' : 'gzip', 'depend' : 'zlib',  'extension' : '.gz',  'header':[0x1F, 0x8B]},
    # since build 3114
    {'module' : 'bz2',  'depend' : '_bz2',  'extension' : '.bz2', 'header' : [0x42, 0x5A]},
    # future proof 20171031
    {'module' : 'lzma', 'depend' : '_lzma', 'extension' : '.xz',  'header' : [0xDF, 0x37, 0x7A, 0x58, 0x5A, 0x00]} 
]


for compression_module in compression_modules:
    dependendy = compression_module['depend']
    if dependendy in sys.builtin_module_names:
        module = compression_module['module']

        decompressor = __import__(module)
        compression_module['open'] = decompressor.open

def get_decompressor_by_header(filename):
    read_header = []
    '''
    We cannot reliably get character from the buffer to figure out the header 
    although it would have been nice to do it with View.substr(point)

    Reading a binary file open an hexdump view
    depending on the `enable_hexadecimal_encoding` setting

    Investigation :
    sublime.load_settings("Preferences.sublime-settings").get("enable_hexadecimal_encoding")
    to get current view
    and have head guess depending on the view 
    probably too much work for our current needs
    '''
    with open(filename, "rb") as f_input:
        for compression_module in compression_modules:
            suffix = compression_module['extension']

            if not 'open' in compression_module:
                continue
            print(compression_module['module'])

            header = compression_module['header']
            len_read   = len(read_header)
            len_header = len(header)

            min_len = min(len_header, len_read)

            if (min_len > 0) and (read_header[0: min_len] != header[0: min_len]):
                continue
            while len(read_header) < len_header:
                read_header.append(ord(f_input.read(1)))
            if read_header[0: len_header] == header:
                decompressor = compression_module['open']
                return suffix, decompressor
    return None, None

def decompressInputFile(view):
    if view.get_status('decompressed'):
        return
    '''
    Execute work for both version
    ''' 
    filepath = view.file_name()
    suffix, decompressor = get_decompressor_by_header(filepath)
    if suffix and decompressor:
        window = view.window()

        '''
        https://stackoverflow.com/a/25631071
        you apparently cannot close a view outside of a command 
        using `view.close` would throw:
            AttributeError: 'View' object has no attribute 'close'
        '''
        view.window().run_command('close_file')

        file_basename = basename(filepath)[:-len(suffix)]
        file_temp = join(mkdtemp(), file_basename)

        sublime.status_message("opening compressed file: " + filepath)
        print("opening compressed file: " + filepath)
        print("decompress into: " + file_temp)

        #with decompressor(filepath) as f_input:
        f_input = decompressor(filepath)
        with open(file_temp,"wb") as f_output:
            copyfileobj(f_input, f_output)
        decomp_view = window.open_file(file_temp)
        decomp_view.set_status('decompressed','1')
        decomp_view.set_read_only(True)

class OpenCompressedFile3(sublime_plugin.EventListener):
    if hasattr(sublime_plugin.EventListener,'on_load_async'):
        def on_load_async(self, view):
            decompressInputFile(view)
    else:
        def on_load(self, view):
            decompressInputFile(view)

    def on_close(self, view):
        if view.get_status('decompressed'):
            filepath = view.file_name()
            remove(filepath)
