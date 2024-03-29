# encoding: utf-8
'''
Sublime text de-Compressor
View compressed files ( gzip, bzip2 ) content in sublime text

Support verified for
- gzip (Sublime Text 2)
- bzip (Sublime Text 3)
- lzma (Sublime Text 4)

'''
from os import remove, rmdir, stat, rename
from os.path import basename, join, dirname, exists
import sys
import threading
import time
from tempfile import mkdtemp
import sublime
import sublime_plugin

'''
# header references

- [gzip](https://tools.ietf.org/html/rfc1952)
- [bzip2](https://en.wikipedia.org/wiki/Bzip2#File_format)
- [xz](https://tukaani.org/xz/format.html)
- [brotli (candidate for frame format)](https://github.com/google/brotli/issues/727)

'''

COMPRESSION_MODULES = {
    'gzip': {'extension': '.gz', 'header': [0x1F, 0x8B]},
    # since build 3114, Use dependency with older version
    'bz2': {'handler': 'BZ2File', 'extension': '.bz2', 'header': [0x42, 0x5A]},
    # future proof 20171031
    'backports_lzma': {'handler': 'LZMAFile', 'extension': '.xz', 'header': [0xFD, 0x37, 0x7A, 0x58, 0x5A, 0x00]},
    'lzma': {'handler': 'LZMAFile', 'extension': '.xz', 'header': [0xFD, 0x37, 0x7A, 0x58, 0x5A, 0x00]}
    # more future proof 20190307
    # brotli framing format is not fixed yet, that mean no magic for now
    # candidate framing:
    #     'brotli': {'extension': '.br', 'header': [0xCE, 0xB2, 0xCF, 0x81]}
    #     'brotli': {'extension': '.br'}
    # the official brotli module do not define any file-like interface might need to write a wrapper
}


def load_module(module, compression_module):
    '''
    Load one compression module

    Parameters
    ----------
    module : str module name
    compression_module
    '''
    try:
        open_attr = 'open'
        # module override
        if 'handler' in compression_module:
            open_attr = compression_module['handler']
        decompressor = __import__(module)
        path = module.split('.')
        if len(path) > 1:
            for element in path[1:]:
                decompressor = getattr(decompressor, element)
        compression_module['open'] = getattr(decompressor, open_attr)
        print("Compressor: loaded", module)
        return True
    except Exception as e:
        print("Compressor: couldn't load", module)
        print(e)
        return False


def get_decompressor_by_header(filename):
    '''
    Attempt to detect the file compression format

    Parameters
    ----------
    filename : str
        input file path to read the magic bytes from

    Returns
    -------
    suffix : str or None
        file extension to remove to have the original filename
    decompressor :  func on None
        callable to create a file-like object to read decompressed data from
    '''
    if not exists(filename):
        return None, None

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
    file_size = stat(filename).st_size if filename else 0
    if file_size == 0:
        return None, None
    with open(filename, "rb") as f_input:
        for module in COMPRESSION_MODULES:
            compression_module = COMPRESSION_MODULES[module]

            if 'loaded' not in compression_module:
                # Lazy loading modules
                compression_module['loaded'] = load_module(module, compression_module)

            suffix = compression_module['extension']
            if not compression_module['loaded']:
                continue
            if 'open' not in compression_module:
                continue
            if 'header' not in compression_module:
                continue
            header = compression_module['header']
            len_read = len(read_header)
            len_header = len(header)

            min_len = min(len_header, len_read)
            if file_size <= len_header:
                continue
            if (min_len > 0) and (read_header[0: min_len] != header[0: min_len]):
                continue
            while len(read_header) < len_header:
                read_header.append(ord(f_input.read(1)))
            if read_header[0: len_header] == header:
                decompressor = compression_module['open']
                return suffix, decompressor
    # headerless cases, we rely on file extension alone
    for module in COMPRESSION_MODULES:
        compression_module = COMPRESSION_MODULES[module]
        if 'open' not in compression_module:
            continue
        if 'header' in compression_module:
            continue
        suffix = compression_module['extension']
        if filename.endswith(suffix):
            return suffix, compression_module['open']
    return None, None


def copy_file(f_input, f_output, bytes_total):
    '''
    Copy file while attempting to report progress

    Parameters
    ----------
    f_input : file
        input file to read from
    f_output : file
        output file to write to
    bytes_total : array of int
        container to hold a reference to the total bytes decompressed
    '''
    bytes_total[0] = 0
    start_time = time.time()
    while True:
        read_buffer = f_input.read(4096)
        bytes_read = len(read_buffer)
        if bytes_read == 0:
            break
        f_output.write(read_buffer)
        bytes_total[0] += bytes_read
    print("Compressor: %f seconds spent decompressing" % (time.time() - start_time))


def decompress(source, target):
    suffix, decompressor = get_decompressor_by_header(source)
    if not (suffix and decompressor):
        return None
    sublime.status_message("opening compressed file: %s" % source)
    print("Compressor: opening compressed file: " + source)
    print("Compressor: decompress into: " + target)

    # some compressor don't support the `with` statement
    f_input = decompressor(source, 'rb')
    with open(target, "wb") as f_output:
        bytes_total = [0]
        thread = threading.Thread(target=copy_file, args=[f_input, f_output, bytes_total])
        thread.start()
        while thread.is_alive():
            time.sleep(.1)
            message = "opening compressed file: %s, %i bytes decompressed" % (source, bytes_total[0])
            sublime.status_message(message)
        thread.join()
    f_input.close()
    return suffix


def load_decompress(view):
    '''
    Decompress the view if the file is compressed in an acceptable format

    Parameters
    ----------
    view : sublime.View
        view that contains the file to be decompressed
    '''
    if view.get_status('decompressed'):
        return
    '''
    Execute work for both version
    '''
    filepath = view.file_name()
    window = view.window()
    
    if window is None:
        # Sometime window can be None 
        return

    for item in window.views():
        if item.get_status('decompressed') == filepath:
            window.run_command('close_file')
            window.focus_view(item)
            return

    # file_basename = basename(filepath)[:-len(suffix)]
    file_basename = basename(filepath)
    file_temp = join(mkdtemp(), file_basename)

    suffix = decompress(filepath, file_temp)
    if suffix is None:
        return
    if file_temp.endswith(suffix):
        old_name = file_temp
        file_temp = file_temp[:-len(suffix)]
        rename(old_name, file_temp)

    '''
    https://stackoverflow.com/a/25631071
    you apparently cannot close a view outside of a command
    using `view.close` would throw:
        AttributeError: 'View' object has no attribute 'close'
    '''
    window.run_command('close_file')
    decomp_view = window.open_file(file_temp)
    decomp_view.set_status('decompressed', filepath)
    decomp_view.set_status('decompressed_mtime', str(stat(filepath).st_mtime))
    print("Compressor: ", decomp_view.get_status('decompressed_mtime'))
    decomp_view.set_read_only(True)


def update_decompressed(view):
    if not view.get_status('decompressed'):
        return
    origin = view.get_status('decompressed')
    if not exists(origin):
        return
    mtime = float(view.get_status('decompressed_mtime'))
    current = stat(origin).st_mtime
    if current <= mtime:
        return
    output = view.file_name()

    if decompress(origin, output) is None:
        return
    view.set_status('decompressed_mtime', str(stat(origin).st_mtime))


class OpenCompressedFile3(sublime_plugin.EventListener):
    '''
    Sublime Text Event for the compressor plugin
    '''
    if hasattr(sublime_plugin.EventListener, 'on_load_async'):
        def on_load_async(self, view):
            '''
            Sublime text 3 async event listener
            '''
            load_decompress(view)
    else:
        def on_load(self, view):
            '''
            Fallback event listener
            '''
            load_decompress(view)

    if hasattr(sublime_plugin.EventListener, 'on_activated_async'):
        def on_activated_async(self, view):
            update_decompressed(view)
    else:
        def on_activated(self, view):
            update_decompressed(view)

    def on_close(self, view):
        '''
        Cleanup
        '''
        if view.get_status('decompressed'):
            filepath = view.file_name()
            remove(filepath)
            # Should be empty by now
            rmdir(dirname(filepath))
