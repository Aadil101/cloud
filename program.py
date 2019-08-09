from boxsdk import OAuth2
import curses
import keyring
from onedrivesdk import HttpProvider, AuthProvider
from onedrivecmd.utils.actions import do_quota
import os
from print_utils import print_bytes, Bag
from pydrive.auth import GoogleAuth
import requests
from storage import Dump, GDrive, DBox, Box, ODrive
import sys
import time

sys.stdout = open('message.log', 'w')

# global variables
dump = None

# i've been meaning to tell you
def status_line(stdscr, message):
	stdscr.move(0, 0)
	stdscr.clrtoeol()
	stdscr.addstr(0, 0, message)
	stdscr.refresh()

# method to control curses display
def display(stdscr):
	stdscr.keypad(True)	# go ahead, type
	curses.curs_set(0)	# but no cursor for you 
	page_history_stack = [(None, None)]	# bunch of (drive_name, folder_id) tuples
	while True:
		(curr_drive, curr_folder_id) = page_history_stack[-1]
		# get stuff in current folder
		status_line(stdscr, '...')
		bags = []
		files = dump.files(curr_drive, curr_folder_id)
		for file_id, file_details in files.items():
			drive_name = list(file_details.keys())[0]
			(name, kind, date_modified) = file_details[drive_name]
			bags.append(Bag({'kind':kind, 'name':name, 'date_modified':date_modified, 'drive_name':drive_name, '_id':file_id}))
		# the show begins
		travel = 0
		cursor = 1
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
			# scroll down
			if key == curses.KEY_DOWN:
				if cursor < disp_height-1:
					if cursor < len(bags):
						cursor += 1
				elif travel < len(bags)-disp_height:
					travel += 1
			# scroll up
			elif key == curses.KEY_UP:
				if cursor > 1:
					cursor -= 1
				elif travel > 0:
					travel -= 1
			# enter folder
			elif key == 10 or key == curses.KEY_ENTER or key == 13:
				if bags[cursor+travel-1].lookup['kind'] == 'folder':
					_id = bags[cursor+travel-1].lookup['_id']
					page_history_stack.append((list(files[_id])[0], _id))
					break
			# retreat
			elif key == curses.KEY_LEFT:
				if len(page_history_stack) > 1:
					page_history_stack.pop()
					break
			# quit
			elif key == 27:	 # escape/alt key
				curses.nocbreak()
				stdscr.keypad(False)
				curses.echo()
				curses.endwin()
				return
			# download item
			elif key == ord('d'):
				if bags[cursor+travel-1].lookup['kind'] == 'file':
					status_line(stdscr, '...')
					dump.download_file(bags[cursor+travel-1].lookup['drive_name'], bags[cursor+travel-1].lookup['_id'], '/Users/pickle/Downloads/')
					status_line(stdscr, 'downloaded \'{}\''.format(bags[cursor+travel-1].lookup['name'].encode('utf-8')))
			# upload item
			elif key == ord('u'):
				prompt = 'upload file: '
				path = None
				while path != '':
					status_line(stdscr, prompt)
					curses.echo()
					path = stdscr.getstr(disp_width - len(prompt))
					curses.noecho()
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
			else:
				stdscr.addstr(0, 0, 'uh-oh: {}\\'.format(key))

def boot():
	# onedrive authentication
	http_provider = HttpProvider()
	client_id='befefb6d-535c-4769-9ab5-68ee79452fda'
	scopes=['wl.signin', 'wl.offline_access', 'onedrive.readwrite']
	api_base_url='https://api.onedrive.com/v1.0/'
	auth_provider = AuthProvider(http_provider, client_id, scopes)
	auth_provider.load_session()
	auth_provider.refresh_token()
	# box authentication
	oauth = OAuth2(
		client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
		client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6',
		access_token=keyring.get_password('Box_Auth', 'aadilislam101@gmail.com'),
		refresh_token=keyring.get_password('Box_Refresh', 'aadilislam101@gmail.com')
	)
	# spit out drives
	return GDrive(GoogleAuth().LocalWebserverAuth()), \
			DBox('Wl2ZKVSB8DQAAAAAAAABFXh6kGHd3mQ0QgvESD9PT-oKmPPif0RERQnEqnAyl_2n'), \
			Box(oauth), \
			ODrive(api_base_url, auth_provider, http_provider)

def main():
	global dump
	# boot er up
	gdrive, dbox, box, odrive = boot()
	dump = Dump({'google': gdrive, 'dropbox': dbox, 'box': box, 'onedrive': odrive})
	# and so it begins
	curses.wrapper(display)

if __name__ == '__main__':
	main()
	
'''
	for arg in sys.argv[1:]:
		if os.path.isfile(arg):
			print('\'{}\' is '.format(arg) + print_bytes(os.path.getsize(arg)))	
		else:
			print('\'{}\' is not a file!'.format(arg))
'''
'''
	storage = dump.storage()
	used_bytes = 0
	remaining_bytes = 0
	for _ , drive in storage.items():
		used_bytes += drive['used'] 
		remaining_bytes += drive['remaining']

'''