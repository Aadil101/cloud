from collections import deque
import curses
import os
from print_utils import *
from storage import *
import sys
import time

# for debugging
message = open("message.log","w")
sys.stdout = message

# global variables
dump = None
max_page_history_length = 100
drive_classes = {'google': 'GDrive', 'dropbox': 'DBox', 'box': 'Box', 'onedrive': 'ODrive'}

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
	comp = Completer()	# for autocompletion
	back_page_history = deque([(None, None, None)])	# bunch of (drive_kind, drive_i, folder_id) tuples
	forward_page_history = deque()
	while True:
		# get stuff in current folder
		(curr_drive_kind, curr_drive_i, curr_folder_id) = back_page_history[-1]
		status_line(stdscr, '...')
		bags = []
		curr_drive = dump.lookup[curr_drive_kind][curr_drive_i] if curr_drive_kind else None
		for file_id, (file_name, file_kind, drive_kind, drive_i, date_modified) in dump.files(curr_drive, curr_folder_id).items():
			if file_name.startswith('.'):
				continue
			bags.append(Bag({'file_kind':file_kind, 'file_name':file_name, 'date_modified':date_modified, 'drive_kind':drive_kind, 'drive_i': drive_i, '_id':file_id}))
		# the show begins
		travel, cursor, reverse = 0, 1, False
		stdscr.clear()
		while True:
			(disp_height, disp_width) = stdscr.getmaxyx()
			# show as much stuff in current folder as possible
			for bag_i in range(0, min(len(bags), disp_height-1)):
				row = bag_i+1
				if row == cursor:
					stdscr.addstr(row, 0, str(bags[bag_i+travel]), curses.A_STANDOUT)	# cursor 
				else:
					stdscr.addstr(row, 0, str(bags[bag_i+travel]))
			stdscr.refresh()
			# accept keystroke
			key = stdscr.getch()
			# clear the status line
			status_line(stdscr, '')
			# account overview
			if key == ord('a'):
				status_line(stdscr, '...')
				sacks = []
				for drive_name, drives in dump.lookup.items():
					for _drive in drives:
						sacks.append(Sack({'account': drive_name, 'email': _drive.email()}))
				account_travel, account_cursor = 0, 1
				stdscr.clear()
				while True:
					for drive_i in range(0, min(len(sacks), disp_height-1)):
						row = drive_i+1
						if row == account_cursor:
							stdscr.addstr(row, 0, str(sacks[drive_i+account_travel]), curses.A_STANDOUT)	# cursor_2
						else:
							stdscr.addstr(row, 0, str(sacks[drive_i+account_travel]))
					stdscr.refresh()
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
					# exit
					elif key == 27:	 # escape/alt key
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
				if bags[cursor+travel-1].get('file_kind') == 'folder':
					if forward_page_history:
						forward_page_history.clear()
					back_page_history.append((bags[cursor+travel-1].get('drive_kind'), bags[cursor+travel-1].get('drive_i'), bags[cursor+travel-1].get('_id')))
					if len(back_page_history) + len(forward_page_history) > max_page_history_length:
						back_page_history.popleft()
					break
			# retreat
			elif key == curses.KEY_LEFT:
				if len(back_page_history) > 1:
					forward_page_history.appendleft(back_page_history.pop())
					break
			# forward
			elif key == curses.KEY_RIGHT:
				if forward_page_history:
					back_page_history.append(forward_page_history.popleft())
					break
			# quit
			elif key == 27:	 # escape/alt key
				curses.nocbreak()
				stdscr.keypad(False)
				curses.echo()
				curses.endwin()
				return
			# delete
			elif key == curses.KEY_BACKSPACE or key == 127:
				prompt = 'delete \'{}\' (y/n)'.format(bags[cursor+travel-1].get('file_name'))
				char = None
				while char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
					status_line(stdscr, prompt)
					char = stdscr.getch()
					if char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
						# yes
						if char == 121:
							# delete it
							if bags[cursor+travel-1].get('file_kind') == 'file':
								status_line(stdscr, '...')
								dump.delete_file(dump.lookup[bags[cursor+travel-1].get('drive_kind')][bags[cursor+travel-1].get('drive_i')], bags[cursor+travel-1].get('_id'))
							elif bags[cursor+travel-1].get('file_kind') == 'folder':
								status_line(stdscr, '...')
								dump.delete_folder(dump.lookup[bags[cursor+travel-1].get('drive_kind')][bags[cursor+travel-1].get('drive_i')], bags[cursor+travel-1].get('_id'))
							break
						# otherwise
						else:
							prompt = 'nope, try again (y/n)'
				else:
					status_line(stdscr, '')
					continue
				status_line(stdscr, '')
				break
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
							if search_cursor < disp_height-1:
								if search_cursor < len(search_bags):
									search_cursor += 1
							elif search_travel < len(search_bags)-(disp_height-1):
								search_travel += 1
						# scroll up
						elif char == curses.KEY_UP:
							if search_cursor > 1:
								search_cursor -= 1
							elif search_travel > 0:
								search_travel -= 1
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
						for file_id, (file_name, file_kind, drive_kind, drive_i, date_modified) in files.items():
							search_bags.append(Bag({'file_kind':file_kind, 'file_name':file_name, 'date_modified':date_modified, 'drive_kind':drive_kind, '_id':file_id}))
						stdscr.clear()
				else:
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
				if bags[cursor+travel-1].get('file_kind') == 'file':
					status_line(stdscr, '...')
					dump.download_file(dump.lookup[bags[cursor+travel-1].get('drive_kind')][bags[cursor+travel-1].get('drive_i')], bags[cursor+travel-1].get('_id'), '/Users/pickle/Downloads/')
					status_line(stdscr, 'downloaded \'{}\''.format(bags[cursor+travel-1].get('file_name')))
				elif bags[cursor+travel-1].get('file_kind') == 'folder':
					status_line(stdscr, '...')
					dump.download_folder(dump.lookup[bags[cursor+travel-1].get('drive_kind')][bags[cursor+travel-1].get('drive_i')], bags[cursor+travel-1].get('_id'), bags[cursor+travel-1].get('file_name'), '/Users/pickle/Downloads/')
					status_line(stdscr, 'downloaded \'{}\''.format(bags[cursor+travel-1].get('file_name')))
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
				break
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
		lookup[drive_name] = []
		for account in os.listdir(os.path.join('credentials', drive_name)):
			if account.startswith('.'):
				continue
			lookup[drive_name].append(globals()[drive_classes[drive_name]](os.path.join('credentials', drive_name, account), int(account)))
	return lookup

def main():
	global dump
	# boot er up
	dump = Dump(lookup=boot())
	# and so it begins
	curses.wrapper(display)

if __name__ == '__main__':
	main()
