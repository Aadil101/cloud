import curses
import os
import logging
from utilities import *
from storage import *
import string
import webbrowser

# global variables
dump = None
max_page_history_length = 100

# change cwd
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# method to tell you how I feel
def status_line(stdscr, message):
	stdscr.move(0, 0)
	stdscr.clrtoeol()
	stdscr.addstr(0, 0, message)
	stdscr.refresh()

# method to control curses display
def display(stdscr):
	stdscr.keypad(True)	# go ahead, type
	curses.curs_set(0)	# but no cursor for you 
	curses.start_color()  # initiate colors
	curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_BLUE)   # boom
	page_history, page_i = [(None, None, None)], 0	# bunch of (drive_kind, account, folder_id) tuples
	curr_drive_kind, curr_account, curr_folder_id = None, None, None   # holds details for current directory
	bags, to_move = [], {} # to hold stuff
	prompt, keep_prompt, travel, cursor, reverse, refresh, move, where = '', False, 0, 1, False, True, False, False
	while True:
		# maybe refresh
		if refresh:
			# get stuff in current folder
			(curr_drive_kind, curr_account, curr_folder_id) = page_history[page_i]
			status_line(stdscr, '...')
			bags = []
			curr_drive = dump.get_drive(curr_drive_kind, curr_account) if curr_drive_kind else None
			for file_id, (file_name, file_kind, drive_kind, account, date_modified) in dump.files(curr_drive, curr_folder_id).items():
				if file_name.startswith('.'):
					continue
				bags.append(Bag({'file_kind':file_kind, 'file_name':file_name, 'date_modified':date_modified, 'account':account, 'drive_kind':drive_kind, '_id':file_id}))
			# the show begins
			travel, cursor, reverse, refresh = 0, min(cursor, len(bags)), False, False
			stdscr.clear()
		(disp_height, disp_width) = stdscr.getmaxyx()
		# show as much stuff in current folder as possible
		for bag_i in range(0, min(len(bags), disp_height-1)):
			row = bag_i+1
			if bags[bag_i+travel].get('_id') in to_move:
				stdscr.addstr(row, 0, str(bags[bag_i+travel]), curses.color_pair(1))	# to move
			elif row == cursor:
				stdscr.addstr(row, 0, str(bags[bag_i+travel]), curses.A_STANDOUT)	# cursor 
			else:
				stdscr.addstr(row, 0, str(bags[bag_i+travel]))
		stdscr.refresh()
		# selected bag
		bag = bags[cursor+travel-1]
		# accept keystroke
		key = stdscr.getch()
		# clear the status line
		if keep_prompt:
			status_line(stdscr, prompt)
		else:
			status_line(stdscr, '')
		# account overview
		if key == ord('a'):
			if move or where:
				continue
			account_travel, account_cursor, account_refresh, sacks, key = 0, 1, True, [], None
			while True:
				if account_refresh:
					account_travel, account_cursor, account_refresh, sacks = 0, 1, False, []
					for drive_kind, drives in dump.get_drives().items():
						for drive in drives.values():
							sacks.append(Sack({'drive_kind': drive_kind, 'account': drive.account}))
					# refresh screen
					stdscr.clear()
				# show as many accounts as possible
				for drive_i in range(0, min(len(sacks), disp_height-1)):
					row = drive_i+1
					if row == account_cursor:
						stdscr.addstr(row, 0, str(sacks[drive_i+account_travel]), curses.A_STANDOUT)	# cursor_2
					else:
						stdscr.addstr(row, 0, str(sacks[drive_i+account_travel]))
				stdscr.refresh()
				# selected sack
				sack = sacks[account_cursor+account_travel-1]
				# accept keystroke
				key = stdscr.getch()
				# scroll down
				if key == curses.KEY_DOWN:
					if account_cursor < min(len(sacks), disp_height-1):
						account_cursor += 1
					elif account_travel < len(sacks)-(disp_height-1):
						account_travel += 1
					else:
						account_cursor, account_travel = 1, 0
				# scroll up
				elif key == curses.KEY_UP:
					if account_cursor > 1:
						account_cursor -= 1
					elif account_travel > 0:
						account_travel -= 1
					else:
						account_cursor = min(len(sacks), disp_height-1)
						account_travel = max(0, len(sacks)-(disp_height-1))
				# delete account
				elif key == curses.KEY_BACKSPACE or key == 127:
					prompt = 'delete \'{}\' \'{}\' (y/n)'.format(sack.get('drive_kind'), sack.get('account'))
					char = None
					while True:
						status_line(stdscr, prompt)
						char = stdscr.getch()
						# yes, delete it
						if char == ord('y'):
							dump.remove_drive(sack.get('drive_kind'), sack.get('account'))
							account_refresh, refresh = True, True
							status_line(stdscr, '')
							break
						# exit
						elif char == curses.KEY_ENTER or char == 10 or char == 13 or char == 27 or ord('n'):
							status_line(stdscr, '')
							break
						# otherwise
						else:
							prompt = 'nope, try again (y/n)'
				# add account
				elif key == ord('a'):
					prompt, drive_class, char = 'account type: ', '', None
					while True:
						status_line(stdscr, prompt)
						stdscr.addstr(drive_class)
						char = stdscr.getch()
						# delete
						if char == 127:
							drive_class = drive_class[:-1]
						# delete chunk
						elif char == 23:
							drive_class = drive_class.rstrip(string.punctuation).rstrip(string.digits+string.ascii_letters)
						# enter
						elif char == curses.KEY_ENTER or char == 10 or char == 13:
							if drive_class in drive_classes:
								status, output = globals()[drive_classes[drive_class]].credentials()
								credentials = None
								if status == 'success':
									credentials = output
									drive = globals()[drive_classes[drive_class]](credentials)
									dump.add_drive(drive_class, drive.account, drive)
								elif status == 'pending':
									webbrowser.open(output)
									prompt, code, key = 'code: ', '', None
									while True:
										status_line(stdscr, prompt)
										stdscr.addstr(code)
										key = stdscr.getch()
										# delete
										if key == 127:
											code = code[:-1]
										# enter
										elif key == curses.KEY_ENTER or key == 10 or key == 13:
											if code == '':
												status_line(stdscr, '')
												break
											status, output = globals()[drive_classes[drive_class]].credentials(code)
											if status == 'success':
												credentials = output
												drive = globals()[drive_classes[drive_class]](credentials)
												dump.add_drive(drive_class, drive.email(), drive)
												break
											elif status == 'failure':
												prompt = 'nope, try again: '
										# exit
										elif key == 27:
											status_line(stdscr, '')
											break
										# character
										elif key != 27:
											code += chr(key)
								account_refresh, refresh = True, True
								break
							elif drive_class == '':
								status_line(stdscr, '')
								break
							else:
								prompt = 'nope, try again: '
						# exit
						elif char == 27:
							status_line(stdscr, '')
							break
						# character
						else:
							drive_class += chr(char)
				# exit
				elif key == 27:
					status_line(stdscr, '')
					break
		# delete
		elif key == curses.KEY_BACKSPACE or key == 127:
			if move or where:
				continue
			prompt, char = 'delete \'{}\' (y/n)'.format(bag.get('file_name')), None
			while True:
				status_line(stdscr, prompt)
				char = stdscr.getch()
				# yes, delete it
				if char == ord('y'):
					drive = dump.get_drive(bag.get('drive_kind'), bag.get('account'))
					if bag.get('file_kind') == 'file':
						status_line(stdscr, '...')
						dump.delete_file(drive, bag.get('_id'))
					elif bag.get('file_kind') == 'folder':
						status_line(stdscr, '...')
						dump.delete_folder(drive, bag.get('_id'))
					status_line(stdscr, '')
					refresh, prompt = True, ''
					break
				# exit
				elif char == curses.KEY_ENTER or char == 10 or char == 13 or char == 27 or char == ord('n'):
					status_line(stdscr, '')
					break
				# otherwise
				else:
					prompt = 'nope, try again (y/n)'
		# download
		elif key == ord('d'):
			if move or where:
				continue
			drive = dump.get_drive(bag.get('drive_kind'), bag.get('account'))
			destination = get_downloads_folder()
			if bag.get('file_kind') == 'file':
				status_line(stdscr, '...')
				dump.download_file(drive, bag.get('_id'), destination)
				status_line(stdscr, 'downloaded \'{}\''.format(bag.get('file_name')))
			elif bag.get('file_kind') == 'folder':
				status_line(stdscr, '...')
				dump.download_folder(drive, bag.get('_id'), bag.get('file_name'), destination)
				status_line(stdscr, 'downloaded \'{}\''.format(bag.get('file_name')))
		# enter
		elif key == curses.KEY_ENTER or key == 10 or key == 13:
			# if moving, toggle item
			if move:
				_id = bag.get('_id')
				if _id in to_move:
					del to_move[_id]
				else:
					to_move[_id] = (bag.get('drive_kind'), bag.get('account'), bag.get('file_name'), bag.get('file_kind'))
			# enter folder
			elif bag.get('file_kind') == 'folder':
				del page_history[page_i+1:]
				page_history.append((bag.get('drive_kind'), bag.get('account'), bag.get('_id')))
				page_i += 1
				if len(page_history) > max_page_history_length:
					page_history.pop(0)
				travel, cursor, reverse, refresh = 0, 1, False, True
		# move
		elif key == ord('m'):
			# phase 2: ask where to move items
			if move:
				move, where, refresh, prompt = False, True, False, 'go to desired folder & hit \'m\'.'
			# phase 3: move items to desired folder
			elif where:
				for _id, (drive_kind, account, file_name, file_kind) in to_move.items():
					dump.move(drive_kind, account, _id, file_name, file_kind, curr_drive_kind, curr_account, curr_folder_id)
				where, to_move, refresh, prompt = False, {}, True, 'moved.'
			# phase 1: ask what items to move
			else:
				move, to_move, prompt = True, {bag.get('_id'):(bag.get('drive_kind'), bag.get('account'), bag.get('file_name'), bag.get('file_kind'))}, 'pick items to move & hit \'m\'.'
			status_line(stdscr, prompt)
		# page retreat
		elif key == curses.KEY_LEFT:
			if page_i > 0:
				page_i -= 1
				travel, cursor, reverse, refresh = 0, 1, False, True
		# page forward
		elif key == curses.KEY_RIGHT:
			if page_i < len(page_history)-1:
				page_i += 1
				travel, cursor, reverse, refresh = 0, 1, False, True
		# quit
		elif key == 27:	 # escape/alt key
			if move:
				move, to_move, prompt = False, {}, ''
				status_line(stdscr, prompt)
			elif where:
				where, to_move, prompt = False, {}, ''
				status_line(stdscr, prompt)
			else:
				curses.nocbreak()
				stdscr.keypad(False)
				curses.echo()
				curses.endwin()
				return
		# scroll down
		elif key == curses.KEY_DOWN:
			if cursor < min(len(bags), disp_height-1):
				cursor += 1
			elif travel < len(bags)-(disp_height-1):
				travel += 1
			else:
				cursor, travel = 1, 0
		# scroll up
		elif key == curses.KEY_UP:
			if cursor > 1:
				cursor -= 1
			elif travel > 0:
				travel -= 1
			else:
				cursor = min(len(bags), disp_height-1)
				travel = max(0, len(bags)-(disp_height-1))
		# search
		elif key == ord('s'):
			if move or where:
				continue
			search_travel, search_cursor, search_refresh = 0, 1, True
			prompt, query, search_bags = 'search: ', '', []
			while True:
				if search_refresh:
					search_travel, search_cursor, search_refresh, search_bags = 0, 1, False, []
					status_line(stdscr, '...')
					files = dump.query(query)
					for file_id, (file_name, file_kind, drive_kind, account, date_modified) in files.items():
						search_bags.append(Bag({'file_kind':file_kind, 'file_name':file_name, 'date_modified':date_modified, 'drive_kind':drive_kind, 'account':account, '_id':file_id}))
					# refresh screen
					stdscr.clear()
				# show as much stuff found as possible
				for seach_bag_i in range(0, min(len(search_bags), disp_height-1)):
					row = seach_bag_i+1
					if row == search_cursor:
						stdscr.addstr(row, 0, str(search_bags[seach_bag_i+search_travel]), curses.A_STANDOUT)	# cursor 
					else:
						stdscr.addstr(row, 0, str(search_bags[seach_bag_i+search_travel]))
				stdscr.refresh()		
				# show current query
				status_line(stdscr, prompt+query)
				# accept keystroke
				char = stdscr.getch()
				# delete
				if char == 127:
					query = query[:-1]
				# delete chunk
				elif char == 23:
					query = query.rstrip(string.punctuation).rstrip(string.digits+string.ascii_letters)
				# scroll down
				elif char == curses.KEY_DOWN:
					if search_cursor < min(len(search_bags), disp_height-1):
						search_cursor += 1
					elif search_travel < len(search_bags)-(disp_height-1):
						search_travel += 1
					else:
						search_cursor, search_travel = 1, 0
				# scroll up
				elif char == curses.KEY_UP:
					if search_cursor > 1:
						search_cursor -= 1
					elif search_travel > 0:
						search_travel -= 1
					else:
						search_cursor = min(len(search_bags), disp_height-1)
						search_travel = max(0, len(search_bags)-(disp_height-1))
				# enter
				elif char == curses.KEY_ENTER or char == 10 or char == 13:
					if query == '':
						status_line(stdscr, '')
						break
					search_refresh = True
				# exit
				elif char == 27:
					status_line(stdscr, '')
					break
				# character
				else:
					query += chr(char)
		# storage summary
		elif key == ord(' '):
			if move or where:
				continue
			status_line(stdscr, '...')
			summary = ', '.join([drive_kind+': '+print_bytes(details['remaining']) \
									for drive_kind, details in dump.storage().items()])
			status_line(stdscr, summary)
		# upload
		elif key == ord('u'):
			if move or where:
				continue
			prompt, path, completer = 'upload: ', '', Completer()
			# print path char-by-char loop
			while True:
				status_line(stdscr, prompt+path)
				char = stdscr.getch()
				# delete
				if char == 127:
					path = path[:-1]
				# delete chunk
				elif char == 23:
					path = path.rstrip(string.punctuation).rstrip(string.digits+string.ascii_letters)
				# tab
				elif char == 9:
					matches = completer.complete(path)
					if matches and len(matches) == 1:
						path = matches[0]
				# enter
				elif char == curses.KEY_ENTER or char == 10 or char == 13:
					path = os.path.expanduser(path)
					if path == '':
						status_line(stdscr, '')
						break
					if os.path.exists(path):
						error = None
						status_line(stdscr, '...')
						if os.path.isfile(path):
							error = dump.add_file(path, curr_drive, curr_folder_id)
						elif os.path.isdir(path):
							error = dump.add_folder(path, curr_drive, curr_folder_id)
						if not error:
							refresh = True
							break
						else:
							prompt = error + ', try again: '
					else:
						prompt = 'nope, try again: '
				# exit
				elif char == 27:
					status_line(stdscr, '')
					break
				# character
				else:
					path += chr(char)
		# sort files by file kind
		elif key == ord('1'):
			bags.sort(key=lambda bag: bag.get('file_kind'), reverse=reverse)
			reverse = not reverse
		# sort files by file name
		elif key == ord('2'):
			bags.sort(key=lambda bag: bag.get('file_name').lower(), reverse=reverse)
			reverse = not reverse
		# sort files by drive kind
		elif key == ord('3'):
			bags.sort(key=lambda bag: bag.get('drive_kind'), reverse=reverse)
			reverse = not reverse
		# sort files by date modified
		elif key == ord('4'):
			bags.sort(key=lambda bag: bag.get('date_modified'), reverse=reverse)
			reverse = not reverse
		else:
			stdscr.addstr(0, 0, 'uh-oh: {}\\'.format(key))

# method to boot up drives
def boot():
	lookup = {}
	for drive_name in os.listdir('credentials'):
		if drive_name.startswith('.'):
			continue
		lookup[drive_name] = {}
		for account_id in os.listdir(os.path.join('credentials', drive_name)):
			if not account_id.isdigit():
				continue
			drive = globals()[drive_classes[drive_name]](os.path.join('credentials', drive_name, account_id))
			lookup[drive_name][drive.account] = drive
	return lookup

# method to start 'er up
def main():
	global dump
	# logging
	logging.basicConfig(level=logging.DEBUG, filename='logfile', filemode='a+',
                        format='%(asctime)-15s %(levelname)-8s %(message)s')
	# boot er up
	dump = Dump(lookup=boot())
	# and so it begins
	curses.wrapper(display)

if __name__ == '__main__':
	main()
