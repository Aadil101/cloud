import sys
import os
import keyring
from pydrive.auth import GoogleAuth
from boxsdk import OAuth2
from onedrivesdk import HttpProvider, AuthProvider
from onedrivecmd.utils.actions import do_quota
import requests
from storage import Dump, GDrive, DBox, Box, ODrive
from print_utils import print_bytes
import time
import curses

dump = None

def show(stdscr):
	stdscr.clear()
	stdscr.refresh()
	###
	storage = dump.storage()
	used_bytes = 0
	remaining_bytes = 0
	for _ , drive in storage.items():
		used_bytes += drive['used'] 
		remaining_bytes += drive['remaining']
	stdscr.addstr(0, 0, '{} used of {} available'.format(print_bytes(used_bytes), print_bytes(used_bytes+remaining_bytes)))
	###
	page_history_stack = [(None, None)]
	row = 1
	while True:
		(curr_drive, curr_id) = page_history_stack[-1]
		files = dump.files(curr_drive, curr_id)
		lines = []
		for _id, details in files.items():
			drive_name = list(details.keys())[0]
			(file_name, kind, date_modified) = details[drive_name]
			lines.append(''.join(word[:15].ljust(16) for word in [kind, file_name, date_modified, drive_name]))
			'''
			stdscr.addstr(row, 0, ''.join(word[:15].ljust(16) for word in [kind, file_name, date_modified, drive_name]))
			row += 1
			if row == height:
				break
			'''
		###
		while True:
			(height, _) = stdscr.getmaxyx()
			travel = 0
			for row in range(1, min(len(lines), height)):
				stdscr.addstr(row, 0, lines[row+travel])
			stdscr.refresh()
			key = stdscr.getch()
			if key == curses.KEY_DOWN: 
				if height-1 < len(lines) and row+travel < len(lines)-1:
					travel += 1
			elif key == curses.KEY_UP:
				if height-1 < len(lines) and row+travel > 0:
					travel -= 1
			else: break

		'''
		next_id = input('gimme id: ')
		if next_id == 'q': 
			break
		elif next_id == 'b':
			if len(page_history_stack) > 1:
				page_history_stack.pop()
		elif next_id in files and next(iter(files[next_id].values()))[1]=='folder':
			page_history_stack.append((list(files[next_id])[0], next_id))
			print('-----------------------------------')
		'''

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