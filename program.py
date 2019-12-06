# lots o' imports
import curses
import os
from print_utils import *
from storage import *
import sys
import webbrowser

# for debugging
sys.stdout = open('message.log','w')

# global variables
dump = None
max_page_history_length = 100

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
	page_history, page_i = [(None, None, None)], 0	# bunch of (drive_kind, account, folder_id) tuples
	travel, cursor, reverse, refresh = 0, 1, False, True
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
			travel, cursor, reverse, refresh = 0, 1, False, False
			stdscr.clear()
		(disp_height, disp_width) = stdscr.getmaxyx()
		# show as much stuff in current folder as possible
		for bag_i in range(0, min(len(bags), disp_height-1)):
			row = bag_i+1
			if row == cursor:
				stdscr.addstr(row, 0, str(bags[bag_i+travel]), curses.A_STANDOUT)	# cursor 
			else:
				stdscr.addstr(row, 0, str(bags[bag_i+travel]))
		stdscr.refresh()
		# selected bag
		bag = bags[cursor+travel-1]
		# accept keystroke
		key = stdscr.getch()
		# clear the status line
		status_line(stdscr, '')
		# account overview
		if key == ord('a'):
			account_travel, account_cursor, account_refresh, sacks = 0, 1, True, []
			while True:
				if account_refresh:
					account_travel, account_cursor, account_refresh, sacks = 0, 1, False, []
					for drive_name, drives in dump.get_drives().items():
						for drive in drives.values():
							sacks.append(Sack({'drive_kind': drive_name, 'account': drive.account}))
				key = None
				while True:
					# refresh screen
					stdscr.clear()
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
						while char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
							status_line(stdscr, prompt)
							char = stdscr.getch()
							if char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
								# yes, delete it
								if char == ord('y'):
									dump.remove_drive(sack.get('drive_kind'), sack.get('account'))
									break
								# otherwise
								else:
									prompt = 'nope, try again (y/n)'
						else:
							status_line(stdscr, '')
							continue
						status_line(stdscr, '')
						account_refresh, refresh = True, True
						break
					# add account
					elif key == ord('a'):
						prompt = 'account type: '
						drive_class = ''
						char = None
						while True:
							status_line(stdscr, prompt)
							stdscr.addstr(drive_class)
							char = stdscr.getch()
							# delete
							if char == 127:
								drive_class = drive_class[:-1]
							# enter
							elif char == curses.KEY_ENTER or char == 10 or char == 13:
								if drive_class in drive_classes:
									break
								else:
									prompt = 'nope, try again: '
							# exit
							elif char == 27:
								break
							# character
							else:
								drive_class += chr(char)
						if char == 27:
							break
						status, output = globals()[drive_classes[drive_class]].credentials()
						credentials = None
						if status == 'success':
							credentials = output
							drive = globals()[drive_classes[drive_class]](credentials)
							dump.add_drive(drive_class, drive.account, drive)
						elif status == 'pending':
							webbrowser.open(output)
							prompt = 'code: '
							code = ''
							char = None
							while True:
								status_line(stdscr, prompt)
								stdscr.addstr(code)
								char = stdscr.getch()
								# delete
								if char == 127:
									code = code[:-1]
								# enter
								elif char == curses.KEY_ENTER or char == 10 or char == 13:
									status, output = globals()[drive_classes[drive_class]].credentials(code)
									if status == 'success':
										credentials = output
										break
									elif status == 'failure':
										prompt = 'nope, try again: '
								# exit
								elif char == 27:
									break
								# character
								else:
									code += chr(char)
							drive = globals()[drive_classes[drive_class]](credentials)
							dump.add_drive(drive_class, drive.email(), drive)
						account_refresh, refresh = True, True
						break
					elif key == 27:
						break
				if key == 27:
					break
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
		# enter
		elif key == 10 or key == curses.KEY_ENTER or key == 13:
			if bag.get('file_kind') == 'folder':
				del page_history[page_i+1:]
				page_history.append((bag.get('drive_kind'), bag.get('account'), bag.get('_id')))
				page_i += 1
				if len(page_history) > max_page_history_length:
					page_history.pop(0)
				travel, cursor, reverse, refresh = 0, 1, False, True
		# retreat
		elif key == curses.KEY_LEFT:
			if page_i > 0:
				page_i -= 1
				travel, cursor, reverse, refresh = 0, 1, False, True
		# forward
		elif key == curses.KEY_RIGHT:
			if page_i < len(page_history)-1:
				page_i += 1
				travel, cursor, reverse, refresh = 0, 1, False, True
		# quit
		elif key == 27:	 # escape/alt key
			curses.nocbreak()
			stdscr.keypad(False)
			curses.echo()
			curses.endwin()
			return
		# delete
		elif key == curses.KEY_BACKSPACE or key == 127:
			prompt = 'delete \'{}\' (y/n)'.format(bag.get('file_name'))
			char = None
			while char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
				status_line(stdscr, prompt)
				char = stdscr.getch()
				if char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
					# yes, delete it
					if char == ord('y'):
						drive = dump.get_drive(bag.get('drive_kind'), bag.get('account'))
						if bag.get('file_kind') == 'file':
							status_line(stdscr, '...')
							dump.delete_file(drive, bag.get('_id'))
						elif bag.get('file_kind') == 'folder':
							status_line(stdscr, '...')
							dump.delete_folder(drive, bag.get('_id'))
						break
					# otherwise
					else:
						prompt = 'nope, try again (y/n)'
			else:
				status_line(stdscr, '')
				continue
			status_line(stdscr, '')
			refresh = True
		# search
		elif key == ord('s'):
			prompt = 'search: '
			query = None
			search_bags = []
			while query != '':
				search_travel = 0
				search_cursor = 1
				if not query:
					query = ''
				# print path char-by-char loop
				while True:
					# show as much stuff in current folder as possible
					for seach_bag_i in range(0, min(len(search_bags), disp_height-1)):
						row = seach_bag_i+1
						if row == search_cursor:
							stdscr.addstr(row, 0, str(search_bags[seach_bag_i+search_travel]), curses.A_STANDOUT)	# cursor 
						else:
							stdscr.addstr(row, 0, str(search_bags[seach_bag_i+search_travel]))
					status_line(stdscr, prompt)
					stdscr.addstr(query)
					char = stdscr.getch()
					# delete
					if char == 127:
						query = query[:-1]
					# enter
					elif char == curses.KEY_ENTER or char == 10 or char == 13:
						break
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
					# exit
					elif char == 27:
						query = ''
						break
					# character
					else:
						query += chr(char)
				if query != '':
					status_line(stdscr, '...')
					files = dump.query(query)
					search_bags = []
					for file_id, (file_name, file_kind, drive_kind, account, date_modified) in files.items():
						search_bags.append(Bag({'file_kind':file_kind, 'file_name':file_name, 'date_modified':date_modified, 'drive_kind':drive_kind, 'account':account, '_id':file_id}))
					stdscr.clear()
			else:
				# exit
				stdscr.clear()
				for bag_i in range(0, min(len(bags), disp_height-1)):
					row = bag_i+1
					if row == cursor:
						stdscr.addstr(row, 0, str(bags[bag_i+travel]), curses.A_STANDOUT)	# cursor 
					else:
						stdscr.addstr(row, 0, str(bags[bag_i+travel]))
				stdscr.refresh()
		# download
		elif key == ord('d'):
			drive = dump.get_drive(bag.get('drive_kind'), bag.get('account'))
			destination = '/Users/pickle/Downloads/'
			if bag.get('file_kind') == 'file':
				status_line(stdscr, '...')
				dump.download_file(drive, bag.get('_id'), destination)
				status_line(stdscr, 'downloaded \'{}\''.format(bag.get('file_name')))
			elif bag.get('file_kind') == 'folder':
				status_line(stdscr, '...')
				dump.download_folder(drive, bag.get('_id'), bag.get('file_name'), destination)
				status_line(stdscr, 'downloaded \'{}\''.format(bag.get('file_name')))
		# storage summary
		elif key == ord(' '):
			status_line(stdscr, '...')
			summary = ', '.join([drive_name+': '+print_bytes(details['remaining']) \
									for drive_name, details in dump.storage().items()])
			status_line(stdscr, summary)
		# upload item
		elif key == ord('u'):
			prompt = 'upload: '
			path = None
			completer = Completer()
			# invalid path loop
			while path != '':
				if not path:
					path = ''
				# print path char-by-char loop
				while True:
					status_line(stdscr, prompt)
					stdscr.addstr(path)
					char = stdscr.getch()
					# delete
					if char == 127:
						path = path[:-1]
					# tab
					elif char == 9:
						matches = completer.complete(path)
						if matches and len(matches) == 1:
							path = matches[0]
					# enter
					elif char == curses.KEY_ENTER or char == 10 or char == 13:
						break
					# exit
					elif char == 27:
						path = ''
						break
					# character
					else:
						path += chr(char)
				path = os.path.expanduser(path)
				if path != '':
					if os.path.exists(path):
						error = None
						status_line(stdscr, '...')
						if os.path.isfile(path):
							error = dump.add_file(path, curr_drive, curr_folder_id)
						elif os.path.isdir(path):
							error = dump.add_folder(path, curr_drive, curr_folder_id)
						if error:
							prompt = error + ', try again: '
						else:
							break
					else:
						prompt = 'nope, try again: '
			else:
				status_line(stdscr, '')
				continue
			refresh = True
		elif key == ord('1'):
			bags.sort(key=lambda bag: bag.get('file_kind'), reverse=reverse)
			reverse = not reverse
		elif key == ord('2'):
			bags.sort(key=lambda bag: bag.get('file_name').lower(), reverse=reverse)
			reverse = not reverse
		elif key == ord('3'):
			bags.sort(key=lambda bag: bag.get('drive_kind'), reverse=reverse)
			reverse = not reverse
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
	# boot er up
	dump = Dump(lookup=boot())
	# and so it begins
	curses.wrapper(display)

if __name__ == '__main__':
	main()
