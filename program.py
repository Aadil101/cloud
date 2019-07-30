import sys
import os
from pydrive.auth import GoogleAuth
from boxsdk import OAuth2
import keyring
from onedrivesdk import HttpProvider, AuthProvider
from onedrivecmd.utils.actions import do_quota
import requests
from storage import Dump, GDrive, DBox, Box, ODrive
from print_utils import print_bytes
import time

def store_tokens(access_token, refresh_token):
    # Use keyring to store the tokens
    keyring.set_password('Box_Auth', 'aadilislam101@gmail.com', access_token)
    keyring.set_password('Box_Refresh', 'aadilislam101@gmail.com', refresh_token)

def main():
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
		store_tokens=store_tokens,
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
	storage = dump.storage()
	used_bytes = 0
	remaining_bytes = 0
	for _ , drive in storage.items():
		used_bytes += drive['used'] 
		remaining_bytes += drive['remaining']
	print('{} used of {} available'.format(print_bytes(used_bytes), print_bytes(used_bytes+remaining_bytes)))
	#t0 = time.time()
	files = dump.files()
	print(files)
	#print("time: "+str(time.time()-t0))
	_id = '0B0Lnx0czKN_6ZmMwTW5KT3dGMFE'
	print("I want file with id: " + _id)
	_id_drive = dump.get_drive(list(files[_id].keys())[0])
	_id_files = _id_drive.files_list(_id)
	print(_id_files)
	
if __name__ == '__main__':
    main()