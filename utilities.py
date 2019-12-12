import os
import random
import re
import readline
import string

COMMANDS = ['extra']
RE_SPACE = re.compile('.*\s+$', re.M)

def random_string(length):
	return ''.join([random.choice(string.ascii_letters + string.digits) for n in range(length)])

# I made some improvements to samplebias's 'Completer' code from:
# https://stackoverflow.com/questions/5637124/tab-completion-in-pythons-raw-input
# :)
class Completer(object):

	def _listdir(self, root):
		"List directory 'root' appending the path separator to subdirs."
		res = []
		for name in os.listdir(root):
			path = os.path.join(root, name)
			if os.path.isdir(path):
				name += os.sep
			res.append(name)
		return res

	def _complete_path(self, path=None):
		"Perform completion of filesystem path."
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
		"Completions for the 'extra' command."
		if not args:
			return self._complete_path('.')
		# treat the last arg as a path and complete it
		return self._complete_path(args[-1])

	def complete(self, text, state):
		"Generic readline completion entry point."
		buffer = readline.get_line_buffer()
		line = readline.get_line_buffer().split()
		# account for last argument ending in a space
		if RE_SPACE.match(buffer):
			line.append('')
		# default command to extra
		command = 'extra'
		attr = getattr(self, 'complete_%s' % command)
		if line:
			return (attr(line) + [None])[state]
			return [command + ' '][state]
		results = [c + ' ' for c in COMMANDS if c.startswith(command)] + [None]
		return results[state]

def print_bytes(num_bytes):
	if num_bytes < 1e3:
		return '{} bytes'.format(num_bytes)
	elif num_bytes < 1e6:
		return '{} kb'.format(int(round(1.0*num_bytes/1024)))
	elif num_bytes < 1e9:
		return '{} mb'.format(int(round(1.0*num_bytes/1024**2)))
	else:
		return '{} gb'.format(int(round(1.0*num_bytes/1024**3)))

class Bag:
	def __init__(self, lookup={}):
		self.lookup = lookup
	def get(self, name):
		return self.lookup[name]
	def __str__(self):
		char_limit_dict = {'file_kind':7, 'file_name':20, 'drive_kind':10, 'date_modified':10}
		return ''.join(self.get(key)[:char_limit_dict[key]].ljust(char_limit_dict[key]+1) \
									 for key in ['file_kind', 'file_name', 'drive_kind', 'date_modified'])

class Sack:
	def __init__(self, lookup={}):
		self.lookup = lookup
	def get(self, name):
		return self.lookup[name]
	def __str__(self):
		char_limit_dict = {'drive_kind':10, 'account':30}
		return ''.join(self.get(key)[:char_limit_dict[key]].ljust(char_limit_dict[key]+1) \
									 for key in ['drive_kind', 'account'])

class Completer:
    def _listdir(self, root):
        "List directory 'root' appending the path separator to subdirs."
        res = []
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isdir(path):
                name += os.sep
            res.append(name)
        return res

    def _complete_path(self, path=None):
        "Perform completion of filesystem path."
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
        "Completions for the 'extra' command."
        if not args:
            return self._complete_path('.')
        # treat the last arg as a path and complete it
        return self._complete_path(args[-1])

    def complete(self, text):
        "Generic readline completion entry point."
        text_clean = text.split()
        if text_clean:
            return self.complete_extra(text_clean)
        return []
