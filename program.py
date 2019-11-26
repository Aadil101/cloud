from boxsdk import OAuth2
from collections import deque
import curses
from dropbox import DropboxOAuth2FlowNoRedirect
import keyring
from onedrivesdk import AuthProvider, HttpProvider
import os
from print_utils import Bag, Completer, print_bytes
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from storage import Box, Dump, DBox, GDrive, ODrive
import sys
import time

# global variables
dump = None
max_page_history_length = 100
box_username = None

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
	back_page_history = deque([(None, None)])	# bunch of (drive_name, folder_id) tuples
	forward_page_history = deque()
	while True:
		# get stuff in current folder
		(curr_drive, curr_folder_id) = back_page_history[-1]
		status_line(stdscr, '...')
		bags = []
		files = dump.files(curr_drive, curr_folder_id)
		for file_id, file_details in files.items():
			drive_name = list(file_details.keys())[0]
			(name, kind, date_modified) = file_details[drive_name]
			if name.startswith('.'):
				continue
			bags.append(Bag({'kind':kind, 'name':name, 'date_modified':date_modified, 'drive_name':drive_name, '_id':file_id}))
		# the show begins
		travel = 0
		cursor = 1
		reverse = False
		hide = False
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
				elif travel < len(bags)-(disp_height-1):
					travel += 1
			# scroll up
			elif key == curses.KEY_UP:
				if cursor > 1:
					cursor -= 1
				elif travel > 0:
					travel -= 1
			# enter
			elif key == 10 or key == curses.KEY_ENTER or key == 13:
				if bags[cursor+travel-1].get('kind') == 'folder':
					if forward_page_history:
						forward_page_history.clear()
					_id = bags[cursor+travel-1].get('_id')
					back_page_history.append((list(files[_id])[0], _id))
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
				prompt = 'delete \'{}\' (y/n)'.format(bags[cursor+travel-1].get('name'))
				char = None
				while char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
					status_line(stdscr, prompt)
					char = stdscr.getch()
					if char != curses.KEY_ENTER and char != 10 and char != 13 and char != 110:
						# yes
						if char == 121:
							# delete it
							if bags[cursor+travel-1].get('kind') == 'file':
								status_line(stdscr, '...')
								dump.delete_file(bags[cursor+travel-1].get('drive_name'), bags[cursor+travel-1].get('_id'))
							elif bags[cursor+travel-1].get('kind') == 'folder':
								status_line(stdscr, '...')
								dump.delete_folder(bags[cursor+travel-1].get('drive_name'), bags[cursor+travel-1].get('_id'))
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
						for file_id, file_details in files.items():
							drive_name = list(file_details.keys())[0]
							(name, kind, date_modified) = file_details[drive_name]
							search_bags.append(Bag({'kind':kind, 'name':name, 'date_modified':date_modified, 'drive_name':drive_name, '_id':file_id}))
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
				if bags[cursor+travel-1].get('kind') == 'file':
					status_line(stdscr, '...')
					dump.download_file(bags[cursor+travel-1].get('drive_name'), bags[cursor+travel-1].get('_id'), '/Users/pickle/Downloads/')
					status_line(stdscr, 'downloaded \'{}\''.format(bags[cursor+travel-1].get('name')))
				elif bags[cursor+travel-1].get('kind') == 'folder':
					status_line(stdscr, '...')
					dump.download_folder(bags[cursor+travel-1].get('drive_name'), bags[cursor+travel-1].get('_id'), bags[cursor+travel-1].get('name'), '/Users/pickle/Downloads/')
					status_line(stdscr, 'downloaded \'{}\''.format(bags[cursor+travel-1].get('name')))
			# storage summary
			elif key == ord('f'):
				if not hide:
					summary = ''
					status_line(stdscr, '...')
					for drive_name, drive in dump.storage().items():
						summary += drive_name + ' ' + print_bytes(drive['remaining']) + ', '
					status_line(stdscr, summary)
					hide = True
				else:
					status_line(stdscr, '')
					hide = False
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
				bags.sort(key=lambda bag: bag.get('kind'), reverse=reverse)
				reverse = not reverse
			elif key == ord('2'):
				bags.sort(key=lambda bag: bag.get('name').lower(), reverse=reverse)
				reverse = not reverse
			elif key == ord('3'):
				bags.sort(key=lambda bag: bag.get('drive_name'), reverse=reverse)
				reverse = not reverse
			elif key == ord('4'):
				bags.sort(key=lambda bag: bag.get('date_modified'), reverse=reverse)
				reverse = not reverse
			else:
				stdscr.addstr(0, 0, 'uh-oh: {}\\'.format(key))

# method to store Box tokens
def store_tokens(access_token, refresh_token):
    # use keyring to store the tokens
    keyring.set_password('Box_Auth', box_username, access_token)
    keyring.set_password('Box_Refresh', box_username, refresh_token)

# method to boot up drives
def boot():
	########################
	# google authentication
	########################
	gauth = GoogleAuth()
	GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = 'google/client_secrets.json'
	# save credentials if this is a new user
	if not os.path.isfile('google/credentials.txt'):
		gauth.LocalWebserverAuth()
		gauth.SaveCredentialsFile('google/credentials.txt')
	# credentials exist, so grab them
	gauth.LoadCredentialsFile('google/credentials.txt')
	# refresh credentials, ie. tokens, if need be
	if gauth.access_token_expired:
		gauth.Refresh()
	else:
		gauth.Authorize()
	#########################
	# dropbox authentication
	#########################
	token = None
	# save credentials if this is a new user
	if not os.path.isfile('dropbox/credentials.txt'):
		auth_flow = DropboxOAuth2FlowNoRedirect('xflfxng1226db2t', 'rnzxajzd6hq04d6')
		auth_url = auth_flow.start()
		print('1. Go to: ' + auth_url)
		print('2. Click \'Allow\' (you might have to log in first).')
		print('3. Copy the authorization code.')
		auth_code = input('Enter the authorization code here: ').strip()
		oauth_result = auth_flow.finish(auth_code)
		with open('dropbox/credentials.txt', 'a') as file:
			token = oauth_result.access_token
			file.write(token)
	# credentials exist, so grab them
	else:
		with open('dropbox/credentials.txt') as file:
			token = file.readline()
	#####################
	# box authentication
	#####################
	# save credentials if this is a new user
	if not os.path.isfile('box/credentials.txt'):
		oauth = OAuth2(
			client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
			client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6'
		)
		auth_url, csrf_token = oauth.get_authorization_url('http://localhost')
		print('1. Go to: ' + auth_url)
		auth_code = input('2. Enter the authorization code here: ').strip()
		access_token, refresh_token = oauth.authenticate(auth_code)
		box_username = Box(oauth).user().get().__dict__['login']
		print(box_username)
		keyring.set_password('Box_Auth', box_username, access_token)
		keyring.set_password('Box_Refresh', box_username, refresh_token)
		with open('box/credentials.txt', 'a') as file:
			file.write(box_username)
	# credentials exist, so grab them
	else:
		with open('box/credentials.txt') as file:
			box_username = file.readline()
	# build credentials
	oauth = OAuth2(
		client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
		client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6',
		store_tokens=store_tokens,
		access_token=keyring.get_password('Box_Auth', box_username),
		refresh_token=keyring.get_password('Box_Refresh', box_username)
	)
	##########################
	# onedrive authentication
	##########################
	client_id = '06d11a46-6c06-4dd2-8f8a-23b22041cb22'
	client_secret = 'r2A/ce3_u+WaF27EiCHTP[Eu7*rbK+55'
	base_url='https://api.onedrive.com/v1.0/'
	scopes = ['wl.signin', 'wl.offline_access', 'onedrive.readwrite']
	http_provider = HttpProvider()
	auth_provider = AuthProvider(
		http_provider=http_provider,
		client_id=client_id,
		scopes=scopes
	)
	# save credentials if this is a new user
	if not os.path.isfile('onedrive/credentials.pickle'):
		redirect_url = 'http://localhost:8080/'
		auth_url = auth_provider.get_auth_url(redirect_url)
		print('1. Go to: ' + auth_url)
		auth_code = input('2. Enter the authorization code here, ie. after \'code=\': ').strip()
		auth_provider.authenticate(auth_code, redirect_url, client_secret)
		auth_provider.save_session(path='onedrive/credentials.pickle')
	# credentials exist, so grab them
	auth_provider.load_session(path='onedrive/credentials.pickle')
	auth_provider.refresh_token()
	########################
	# spit out the 4 drives
	return GDrive(gauth), DBox(token), Box(oauth), ODrive(base_url, auth_provider, http_provider)

def main():
	global dump
	# boot er up
	google, dropbox, box, onedrive = boot()
	dump = Dump({'google': google, 'dropbox': dropbox, 'box': box, 'onedrive': onedrive})
	# and so it begins
	curses.wrapper(display)

if __name__ == '__main__':
	main()
