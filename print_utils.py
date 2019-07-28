def print_bytes(num_bytes):
	if num_bytes < 1e3:
		return '{} bytes'.format(num_bytes)
	elif num_bytes < 1e6:
		return '{} kb'.format(int(round(1.0*num_bytes/1024)))
	elif num_bytes < 1e9:
		return '{} mb'.format(int(round(1.0*num_bytes/1024**2)))
	else:
		return '{} gb'.format(int(round(1.0*num_bytes/1024**3)))