import os

# This is for autocompleting a path when the user presses tab.
# I made adjustments to samplebias's 'Completer' code from:
# https://stackoverflow.com/questions/5637124/tab-completion-in-pythons-raw-input
class Completer:
    def _listdir(self, root):
        'List directory "root" appending the path separator to subdirs.'
        res = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
        return res

    def _complete_path(self, path=None):
        'Perform completion of filesystem path.'
        if not path:
            return self._listdir('.')
        # resolve ~ shortcut if present
        path = os.path.expanduser(path)
        dirname, rest = os.path.split(path)
        tmp = dirname if dirname else '.'
        res = [os.path.join(dirname, p)
                for p in self._listdir(tmp) if p.startswith(rest)]
        # more than one match, or single match which does not exist (typo)
        if len(res) > 1 or not os.path.exists(path):
            return res
        # resolved to a single directory, so return list of files below it
        if os.path.isdir(path):
            return [os.path.join(path, p) for p in self._listdir(path)]
        # exact file match terminates this completion
        return [path + ' ']

    def complete_extra(self, args):
        'Completions for the "extra" command.'
        if not args:
            return self._complete_path('.')
        # treat the last arg as a path and complete it
        return self._complete_path(args[-1])

    def complete(self, text):
        'Generic readline completion entry point.'
        text_clean = text.split()
        if text_clean:
            return self.complete_extra(text_clean)
        return []

def print_bytes(num_bytes):
	if num_bytes < 1e3:
		return '{:.1f} bytes'.format(num_bytes)
	elif num_bytes < 1e6:
		return '{:.1f} kb'.format(1.0*num_bytes/1e3)
	elif num_bytes < 1e9:
		return '{:.1f} mb'.format(1.0*num_bytes/1e6)
	elif num_bytes < 1e12:
		return '{:.1f} gb'.format(1.0*num_bytes/1e9)
	else:
		return '{:.1f} tb'.format(1.0*num_bytes/1e12)

# Finding user's downloads folder is a bit annoying on Windows.
# I modified user4815162342's code from:
# https://stackoverflow.com/questions/35851281/python-finding-the-users-downloads-folder
def get_downloads_folder():
	if os.name == 'nt':
		import ctypes
		from ctypes import windll, wintypes
		from uuid import UUID

		# ctypes GUID copied from MSDN sample code
		class GUID(ctypes.Structure):
			_fields_ = [
				('Data1', wintypes.DWORD),
				('Data2', wintypes.WORD),
				('Data3', wintypes.WORD),
				('Data4', wintypes.BYTE * 8)
			] 

			def __init__(self, uuidstr):
				uuid = UUID(uuidstr)
				ctypes.Structure.__init__(self)
				self.Data1, self.Data2, self.Data3, \
					self.Data4[0], self.Data4[1], rest = uuid.fields
				for i in range(2, 8):
					self.Data4[i] = rest>>(8-i-1)*8 & 0xff

		SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
		SHGetKnownFolderPath.argtypes = [
			ctypes.POINTER(GUID), wintypes.DWORD,
			wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)
		]

		def _get_known_folder_path(uuidstr):
			pathptr = ctypes.c_wchar_p()
			guid = GUID(uuidstr)
			if SHGetKnownFolderPath(ctypes.byref(guid), 0, 0, ctypes.byref(pathptr)):
				raise ctypes.WinError()
			return pathptr.value
		
		FOLDERID_Download = '{374DE290-123F-4565-9164-39C4925E467B}'

		return _get_known_folder_path(FOLDERID_Download)
	else:
		home = os.path.expanduser('~')
		return os.path.join(home, 'Downloads')