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
	'''
	def get_item(self, key):
		return self.lookup[key]
	'''
    def __str__(self):
        return ''.join(str(val)[:15].ljust(16) for _, val in self.lookup.items())