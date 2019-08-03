import sys
import os
import keyring
from pydrive.auth import GoogleAuth
from boxsdk import OAuth2
from onedrivesdk import HttpProvider, AuthProvider
from onedrivecmd.utils.actions import do_quota
import requests
from storage import Dump, GDrive, DBox, Box, ODrive
from print_utils import print_bytes, Bag
import time
import curses

dump = None

def show(stdscr):
	stdscr.keypad(True)
	curses.curs_set(0)
	###
	''''
	storage = dump.storage()
	used_bytes = 0
	remaining_bytes = 0
	for _ , drive in storage.items():
		used_bytes += drive['used'] 
		remaining_bytes += drive['remaining']
	'''
	###
	page_history_stack = [(None, None)]
	while True:
		(curr_drive, curr_id) = page_history_stack[-1]
		files = dump.files(curr_drive, curr_id)
		bags = []
		for _id, details in files.items():
			drive_name = list(details.keys())[0]
			(file_name, kind, date_modified) = details[drive_name]
			bags.append(Bag({'kind':kind, 'file_name':file_name, 'date_modified':date_modified, 'drive_name':drive_name, '_id':_id}))
		###
		travel = 0
		cursor = 1
		stdscr.clear()
		stdscr.refresh()
		while True:
			(height, _) = stdscr.getmaxyx()
			for bag_i in range(0, min(len(bags), height-1)):
				row = bag_i+1
				if row == cursor:
					stdscr.addstr(row, 0, str(bags[bag_i+travel]),
									curses.A_STANDOUT)
				else:
					stdscr.addstr(row, 0, str(bags[bag_i+travel]))
			stdscr.refresh()
			key = stdscr.getch()
			if key == curses.KEY_DOWN:
				if cursor < height-1:
					if cursor < len(bags):
						cursor += 1
				elif travel < len(bags)-height:
					travel += 1
			elif key == curses.KEY_UP:
				if cursor > 1:
					cursor -= 1
				elif travel > 0:
					travel -= 1
			elif key == 10:
				if bags[cursor+travel-1].lookup['kind'] == 'folder':
					_id = bags[cursor+travel-1].lookup['_id']
					page_history_stack.append((list(files[_id])[0], _id))
					break
			elif key == ord('b'):
				if len(page_history_stack) > 1:
					page_history_stack.pop()
					break
			elif key == ord('q'):
				curses.nocbreak()
				stdscr.keypad(False)
				curses.echo()
				curses.endwin()
				return
			else:
				stdscr.addstr(0, 0, 'uh-oh: {}\\'.format(key))
def main():
	global dump
	###
	http_provider = HttpProvider()
	client_id='befefb6d-535c-4769-9ab5-68ee79452fda'
	scopes=['wl.signin', 'wl.offline_access', 'onedrive.readwrite']
	api_base_url='https://api.onedrive.com/v1.0/'
	auth_provider = AuthProvider(http_provider, client_id, scopes)
	auth_provider.load_session()
	auth_provider.refresh_token()
	odrive = ODrive(api_base_url, auth_provider, http_provider)
	###
	oauth = OAuth2(
		client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
		client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6',
		access_token=keyring.get_password('Box_Auth', 'aadilislam101@gmail.com'),
		refresh_token=keyring.get_password('Box_Refresh', 'aadilislam101@gmail.com')
	)
	box = Box(oauth)
	###
	gdrive = GDrive(GoogleAuth().LocalWebserverAuth())
	###
	dbox = DBox('Wl2ZKVSB8DQAAAAAAAABFXh6kGHd3mQ0QgvESD9PT-oKmPPif0RERQnEqnAyl_2n')
	###
	dump = Dump({'google':gdrive, 'dropbox':dbox, "onedrive":odrive, "box":box})
	###
	for arg in sys.argv[1:]:
		if os.path.isfile(arg):
			print('\'{}\' is '.format(arg) + print_bytes(os.path.getsize(arg)))	
		else:
			print('\'{}\' is not a file!'.format(arg))
	###
	curses.wrapper(show)

if __name__ == '__main__':
    main()