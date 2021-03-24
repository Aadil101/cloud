from boxsdk import Client, OAuth2
import datetime
from dropbox import Dropbox, DropboxOAuth2FlowNoRedirect
from dropbox.files import FolderMetadata
import keyring
import logging
import ntpath
import onedrivesdk
from onedrivesdk import AuthProvider, HttpProvider, OneDriveClient
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import requests
import shutil
from utilities import get_downloads_folder

# constants
threshold = 1e6
drive_classes = {'google': 'GDrive', 'dropbox': 'DBox', 'box': 'Box', 'onedrive': 'ODrive'}

class Bag:
	def __init__(self, lookup={}):
		self.lookup = lookup
	def get(self, name):
		return self.lookup[name]
	def __str__(self):
		char_limit_dict = {'file_kind':7, 'file_name':20, 'drive_kind':10, 'date_modified':10}
		return ''.join(self.get(key)[:char_limit_dict[key]].ljust(char_limit_dict[key]+1) \
									 for key in ['file_kind', 'file_name', 'drive_kind', 'date_modified'])

class Sack:
	def __init__(self, lookup={}):
		self.lookup = lookup
	def get(self, name):
		return self.lookup[name]
	def __str__(self):
		char_limit_dict = {'drive_kind':10, 'account':30}
		return ''.join(self.get(key)[:char_limit_dict[key]].ljust(char_limit_dict[key]+1) \
									 for key in ['drive_kind', 'account'])

# method to obtain and/or assign a unique id for each new account 
def next_drive_id(drive_class, assign=False):
    _id = 0
    while _id in drive_class._ids: _id += 1
    if assign: drive_class._ids.add(_id)
    return _id

class Dump:
    def __init__(self, lookup={}):
        self.lookup = lookup
    def add_drive(self, drive_kind, account, drive):
        if not drive_kind in self.lookup:
            self.lookup[drive_kind] = {}
        self.lookup[drive_kind][account] = drive
    def get_drive(self, drive_kind, account):
        return self.lookup[drive_kind][account]
    def get_drives(self):
        return self.lookup
    def remove_drive(self, drive_kind, account):
        _id = self.lookup[drive_kind][account]._id
        path = os.path.join('credentials', drive_kind, str(_id))
        shutil.rmtree(path)
        globals()[drive_classes[drive_kind]]._ids.remove(_id)
        del self.lookup[drive_kind][account]
        if not self.lookup[drive_kind]:
            del self.lookup[drive_kind]
    def storage(self):
        return {drive_kind:{'used':sum(drive.used_storage_bytes() for drive in drives.values()), \
                       'remaining':sum(drive.remaining_storage_bytes() for drive in drives.values())} \
                for drive_kind, drives in self.lookup.items()}
    def query(self, query, drive=None):
        if drive:
            return drive.query(query)
        stuff = {}
        for drives in self.lookup.values():
            for drive in drives.values():
                stuff.update(drive.query(query))
        return stuff
    def files(self, drive=None, folder_id=None):
        if drive and folder_id:
            return drive.files(folder_id)
        stuff = {}
        for drives in self.lookup.values():
            for drive in drives.values():
                stuff.update(drive.files())
        return stuff
    def move(self, drive_kind, account, _id, name, file_kind, target_drive_kind, target_account, target_folder_id):
        drive = self.get_drive(drive_kind, account)
        if drive_kind == target_drive_kind and account == target_account:
            drive.move(_id, target_folder_id)
        else:
            target_drive = self.get_drive(target_drive_kind, target_account)
            temporary_destination = get_downloads_folder()
            if file_kind == 'folder':
                self.download_folder(drive, _id, name, temporary_destination)
                self.add_folder(os.path.join(temporary_destination, name), target_drive, target_folder_id)
                self.delete_folder(drive, _id)
            else:
                self.download_file(drive, _id, temporary_destination)
                self.add_file(os.path.join(temporary_destination, name), target_drive, target_folder_id)   
    def download_folder(self, drive, folder_id, name, path):
        stack = [(folder_id, name)]
        id_to_path = {folder_id: path}
        while stack:
            curr_folder_id, curr_folder_name = stack.pop()
            curr_folder_path = id_to_path[curr_folder_id]
            os.mkdir(os.path.join(curr_folder_path, curr_folder_name))
            for file_id, (file_name, file_kind, _, __, ___) in self.files(drive, curr_folder_id).items():
                if file_kind == 'folder':
                    id_to_path[file_id] = os.path.join(curr_folder_path, curr_folder_name)
                    stack.append((file_id, file_name))
                else:
                    self.download_file(drive, file_id, os.path.join(curr_folder_path, curr_folder_name))
    def download_file(self, drive, folder_id, path):
        drive.download_file(folder_id, path)
    def delete_folder(self, drive, folder_id):
        drive.delete_folder(folder_id)
    def delete_file(self, drive, file_id):
        drive.delete_file(file_id)
    def add_folder(self, path, drive=None, folder_id=None, size_check=True):
        if os.path.isdir(path):
            path = path.rstrip('/')
            # optionally check size of directory
            size = 0
            if size_check:    
                # enumerate local files recursively
                for root, dirs, files in os.walk(path):
                    for file in files:
                        local_path = os.path.join(root, file)
                        # skip if path to symbolic link
                        if not os.path.islink(local_path):
                            size += os.path.getsize(local_path)
            # try to upload directory
            if drive:
                if not size_check or size < drive.remaining_storage_bytes()-threshold:
                    path_to_id = {}
                    if folder_id:
                        path_to_id[os.path.join(folder_id, ntpath.basename(path))] = drive.add_folder(path, folder_id)
                    else:
                        path_to_id[ntpath.basename(path)] = drive.add_folder(path)
                    for root, dirs, files in os.walk(path):
                        local = root[root.find(ntpath.basename(path)):]
                        for _dir in dirs:
                            if folder_id:
                                path_to_id[os.path.join(folder_id, local, _dir)] = drive.add_folder(os.path.join(root, _dir), path_to_id[os.path.join(folder_id, local)])
                            else:
                                path_to_id[os.path.join(local, _dir)] = drive.add_folder(os.path.join(root, _dir), path_to_id[local])
                        for file in files:
                            if not file.startswith('.'):
                                if folder_id:
                                    drive.add_file(os.path.join(root, file), path_to_id[os.path.join(folder_id, local)])
                                else:
                                    drive.add_file(os.path.join(root, file), path_to_id[local])
                else:
                    return 'RIP, \'{}\' can\'t fit in this drive'.format(ntpath.basename(path))
            else:
                for drives in self.lookup.values():
                    for _drive in drives.values():
                        if size < _drive.remaining_storage_bytes()-threshold:
                            return self.add_folder(path, _drive, None, False)
                return 'RIP, there isn\'t enough space anywhere for \'{}\''.format(ntpath.basename(path))
        else:
            return 'RIP, folder doesn\'t exist at \'{}\''.format(path)
    def add_file(self, path, drive=None, folder_id=None):
        if os.path.isfile(path):
            if drive:
                if os.path.getsize(path) < drive.remaining_storage_bytes()-threshold:
                    if folder_id:
                        drive.add_file(path, folder_id)
                    else:
                        drive.add_file(path)
                else:
                    return 'RIP, there isn\'t enough space in this drive for \'{}\''.format(ntpath.basename(path))
            else:
                for drives in self.lookup.values():
                    for _drive in drives.values():
                        if os.path.getsize(path) < _drive.remaining_storage_bytes()-threshold:
                            if _drive.add_file(path):
                                return
                return 'RIP, there isn\'t enough space anywhere for \'{}\''.format(ntpath.basename(path))
        else:
            return 'RIP, file doesn\'t exist at \'{}\''.format(path)

mimetypes = {
    # google-apps files as MS files
    'application/vnd.google-apps.document': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx'),
    'application/vnd.google-apps.spreadsheet': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', '.xlsx'),
    'application/vnd.google-apps.presentation': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx')
}

class GDrive(GoogleDrive):
    _ids = set()
    def __init__(self, credentials):
        super(GDrive, self).__init__(self.boot(credentials))
        self._id = next_drive_id(GDrive, assign=True)
        self.account = self.email()
    @staticmethod
    def credentials():
        # this is a new user, so build new credentials
        gauth = GoogleAuth()
        GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = 'credentials/google/client_secrets.json'
        credentials = os.path.join('credentials/google', str(next_drive_id(GDrive)))
        os.mkdir(credentials)
        gauth.LocalWebserverAuth()
        gauth.SaveCredentialsFile(os.path.join(credentials, 'credentials.txt'))
        return 'success', credentials
    def boot(self, credentials):
        gauth = GoogleAuth()
        GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = 'credentials/google/client_secrets.json'
        # credentials exist, so grab them
        gauth.LoadCredentialsFile(os.path.join(credentials, 'credentials.txt'))
        # refresh credentials, ie. tokens, if need be
        if gauth.access_token_expired:
            gauth.Refresh()
        else:
            gauth.Authorize()
        return gauth
    def email(self):
        return self.GetAbout()['user']['emailAddress']
    def used_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesByService'][0]['bytesUsed'])
    def remaining_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesTotal']) - self.used_storage_bytes()
    def query(self, query):
        return {file['id']:(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', 'google', self.account, datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y')) \
                for file in self.ListFile({'q': 'title="{}" and trashed=false'.format(query)}).GetList()}
    def files(self, folder_id='root'):
        return {file['id']:(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', 'google', self.account, datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y')) \
                for file in self.ListFile({'q': '"{}" in parents and trashed=false'.format(folder_id)}).GetList()}
    def move(self, _id, target_folder_id):
        file = self.CreateFile({'id': _id})
        while True:
            file['parents'] = [{'kind': 'drive#fileLink', 'id': target_folder_id}]
            file.Upload()
            if _id in self.files(target_folder_id):
                break
    def download_file(self, file_id, path):
        file = self.CreateFile({'id': file_id})
        if file['mimeType'] in mimetypes:
            download_type, download_ext = mimetypes[file['mimeType']]
            file.GetContentFile(os.path.join(path, file['title'].replace('/', u'\u2215')+download_ext), mimetype=download_type)
        else:
            file.GetContentFile(os.path.join(path, file['title']), mimetype=file['mimeType'])
    def delete_folder(self, folder_id):
        self.delete_file(folder_id)
    def delete_file(self, file_id):
        file = self.CreateFile({'id': file_id})
        file.Trash()
    def add_folder(self, path, folder_id='root'):
        folder_metadata = {'title':ntpath.basename(path), 'mimeType':'application/vnd.google-apps.folder',
                            'parents':[{'id':folder_id}]}
        new_folder = self.CreateFile(folder_metadata)
        new_folder.Upload()
        return new_folder['id']
    def add_file(self, path, folder_id='root'):
        existing = {title for title, _, __, ___, ___ in self.files(folder_id).values()}
        file = self.CreateFile({'title':ntpath.basename(path), 
                                'parents':[{'kind':'drive#fileLink', 'id':folder_id}]})
        file.SetContentFile(path)
        file.Upload()

class DBox(Dropbox):
    _ids = set()
    auth_flow = None
    def __init__(self, credentials):
        super(DBox, self).__init__(self.boot(credentials))
        self._id = next_drive_id(DBox, assign=True)
        self.account = self.email()
    @staticmethod
    def credentials(auth_code=None):
        credentials = os.path.join('credentials/dropbox', str(next_drive_id(DBox)))
        if auth_code:
            oauth_result = None
            try:
                oauth_result = DBox.auth_flow.finish(auth_code)
            except:
                return 'failure', None
            else:
                os.mkdir(credentials)
                with open(os.path.join(credentials, 'credentials.txt'), 'a+') as file:
                    file.write(oauth_result.access_token)
                return 'success', credentials
        else:
            DBox.auth_flow = DropboxOAuth2FlowNoRedirect('xflfxng1226db2t', 'rnzxajzd6hq04d6')
            auth_url = DBox.auth_flow.start()
            return 'pending', auth_url
    def boot(self, credentials):
        with open(os.path.join(credentials, 'credentials.txt')) as file:
            return file.readline()
    def email(self):
        return self.users_get_current_account().email
    def used_storage_bytes(self):
        return self.users_get_space_usage().used
    def remaining_storage_bytes(self):
        return self.users_get_space_usage().allocation.get_individual().allocated - self.used_storage_bytes()
    def query(self, query):
        return {file.metadata.id:(file.metadata.name, 'folder' if isinstance(file.metadata, FolderMetadata) else 'file', 'dropbox', self.account, '?' if isinstance(file.metadata, FolderMetadata) else file.metadata.client_modified.strftime('%m/%d/%y')) \
                for file in self.files_search('', query).matches}
    def files(self, folder_id=''):
        return {file.id:(file.name, 'folder' if isinstance(file, FolderMetadata) else 'file', 'dropbox', self.account, '?' if isinstance(file, FolderMetadata) else file.client_modified.strftime('%m/%d/%y')) \
                for file in self.files_list_folder(folder_id).entries}
    def move(self, _id, target_folder_id):
        file_name = self.files_get_metadata(_id).name
        self.files_move(_id, os.path.join(target_folder_id, file_name))
    def download_file(self, file_id, path):
        meta = self.files_get_metadata(file_id)
        self.files_download_to_file(os.path.join(path, meta.name), file_id)
    def delete_folder(self, folder_id):
        self.delete_file(folder_id)
    def delete_file(self, file_id):
        self.files_delete(file_id)
    def add_folder(self, path, folder_id=''):
        new_path = os.path.join(folder_id, ntpath.basename(path), 'test.txt')
        self.files_upload(None, new_path)
        self.files_delete(new_path)
        return self.files_get_metadata(os.path.join(folder_id, ntpath.basename(path))).id
    def add_file(self, path, folder_id=''):
        existing = {title for title, _, __, ___, ___ in self.files(folder_id).values()}
        title = ntpath.basename(path)
        if title in existing:
            base, suffix = title, 1
            while '{} ({})'.format(base, suffix) in existing:
                suffix += 1
            title = '{} ({})'.format(base, suffix)
        with open(path, 'rb') as file:
            if folder_id == '' or len(folder_id) < 3 or folder_id[:3] != 'id:':
                folder_id = '/' + folder_id
            self.files_upload(file.read(), os.path.join(folder_id, title))

class Box(Client):
    _ids = set()
    def __init__(self, credentials):
        super(Box, self).__init__(self.boot(credentials))
        self._id = next_drive_id(Box, assign=True)
        self.account = self.email()
    @staticmethod
    def credentials(auth_code=None):
        credentials = os.path.join('credentials/box', str(next_drive_id(Box)))
        oauth = OAuth2(
            client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
            client_secret='icDxjMAFSuERimeonuwQEiutp696b2wb'
        )
        if auth_code:
            access_token, refresh_token = None, None
            try:    
                access_token, refresh_token = oauth.authenticate(auth_code)
            except:
                return 'failure', None
            else:
                os.mkdir(credentials)
                account = Client(oauth).user().get().__dict__['login']
                with open(os.path.join(credentials, 'credentials.txt'), 'a+') as file:
                    file.write(account)
                keyring.set_password('Box_Auth', account, access_token)
                keyring.set_password('Box_Refresh', account, refresh_token)
                return 'success', credentials
        else:
            auth_url, _ = oauth.get_authorization_url('http://localhost')
            return 'pending', auth_url
    def store_tokens(self, access_token, refresh_token):
        # use keyring to store the tokens
        keyring.set_password('Box_Auth', self.account, access_token)
        keyring.set_password('Box_Refresh', self.account, refresh_token)
    def boot(self, credentials):
        with open(os.path.join(credentials, 'credentials.txt')) as file:
            self.account = file.readline()
        # build credentials
        oauth = OAuth2(
            client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
            client_secret='icDxjMAFSuERimeonuwQEiutp696b2wb',
            store_tokens=self.store_tokens,
            access_token=keyring.get_password('Box_Auth', self.account),
            refresh_token=keyring.get_password('Box_Refresh', self.account)
		)
        return oauth
    def email(self):
        return self.user().get().__dict__['login']
    def used_storage_bytes(self):
        return self.user().get().space_used
    def remaining_storage_bytes(self):
        return self.user().get().space_amount - self.used_storage_bytes()
    def query(self, query):
        if query == '': return {}
        return {item.id:(item.name, item.type, 'box', self.account, '?') \
                for item in self.search().query(query)}
    def files(self, folder_id='0'):
        return {item.id:(item.name, item.type, 'box', self.account, '?') \
                for item in self.folder(folder_id).get_items()}
    def move(self, _id, target_folder_id):
        item = None
        try:
            item = self.file(_id).get()
        except:
            item = self.folder(_id).get()
        finally:
            item.move(self.folder(target_folder_id))
    def download_file(self, file_id, path):
        file = self.file(file_id)
        with open(os.path.join(path, file.get().name), 'wb') as out_file:
            file.download_to(out_file)
            out_file.close()
    def delete_folder(self, folder_id):
        self.folder(folder_id).delete()
    def delete_file(self, file_id):
        self.file(file_id).delete()
    def add_folder(self, path, folder_id='0'):
        return self.folder(folder_id).create_subfolder(ntpath.basename(path)).id
    def add_file(self, path, folder_id='0'):
        existing = {title for title, _, __, ___, ___ in self.files(folder_id).values()}
        title = ntpath.basename(path)
        if title in existing:
            base, suffix = title, 1
            while '{} ({})'.format(base, suffix) in existing:
                suffix += 1
            title = '{} ({})'.format(base, suffix)
        self.folder(folder_id).upload(path, title)

class ODrive(OneDriveClient):
    _ids = set()
    redirect_url = 'http://localhost:8080/'
    client_id='06d11a46-6c06-4dd2-8f8a-23b22041cb22'
    client_secret = 'r2A/ce3_u+WaF27EiCHTP[Eu7*rbK+55'
    base_url='https://api.onedrive.com/v1.0/'
    scopes=['wl.signin', 'wl.offline_access', 'onedrive.readwrite']
    auth_provider = None
    def __init__(self, credentials):
        super(ODrive, self).__init__(*self.boot(credentials))
        self._id = next_drive_id(ODrive, assign=True)
        self.account = self.email()
    @staticmethod
    def credentials(auth_code=None):
        credentials = os.path.join('credentials/onedrive', str(next_drive_id(ODrive)))
        http_provider = HttpProvider()
        auth_provider = AuthProvider(
            http_provider=HttpProvider(),
            client_id=ODrive.client_id,
            scopes=ODrive.scopes,
        )
        if auth_code:
            try:
                ODrive.auth_provider.authenticate(auth_code, ODrive.redirect_url, ODrive.client_secret)
            except:
                return 'failure', None
            else:
                os.mkdir(credentials)
                ODrive.auth_provider.save_session(path=os.path.join(credentials, 'credentials.pickle'))
                return 'success', credentials
            ODrive.auth_provider = None
        else:
            ODrive.auth_provider = auth_provider
            return 'pending', auth_provider.get_auth_url(ODrive.redirect_url)
    def boot(self, credentials):
        http_provider = HttpProvider()
        auth_provider = AuthProvider(
            http_provider=http_provider,
            client_id=ODrive.client_id,
            scopes=ODrive.scopes,
        )
        # credentials exist, so grab them
        auth_provider.load_session(path=os.path.join(credentials, 'credentials.pickle'))
        auth_provider.refresh_token()
        return ODrive.base_url, auth_provider, http_provider
    def email(self):
        return 'id: {}'.format(requests.get(self.base_url + 'drive/', headers = {
                            'Authorization': 'bearer {access_token}'.format(access_token = str(self.auth_provider.access_token)),
                            'content-type': 'application/json'}).json()['owner']['user']['id'])
    def _quota_dict(self):
        return requests.get(self.base_url + 'drive/', headers = {
                            'Authorization': 'bearer {access_token}'.format(access_token = str(self.auth_provider.access_token)),
                            'content-type': 'application/json'}).json()['quota']
    def used_storage_bytes(self):
        return self._quota_dict()['used']
    def remaining_storage_bytes(self):
        return self._quota_dict()['remaining']
    def query(self, query):
        if query == '': return {}
        return {item.id:(item.name, 'file' if item.folder == None else 'folder', 'onedrive', self.account, item.last_modified_date_time.strftime('%m/%d/%y')) \
                for item in self.item(drive='me', id='root').search(q=query).get().items()}
    def files(self, folder_id='root'):
        return {item.id:(item.name, 'file' if item.folder == None else 'folder', 'onedrive', self.account, item.last_modified_date_time.strftime('%m/%d/%y')) \
                for item in self.item(drive='me', id=folder_id).children.request().get()}
    def move(self, _id, target_folder_id):
        item = self.item(drive='me', id=_id).request().get()
        folder = self.item(drive='me', id=target_folder_id).request().get()
        folder_path = None
        if folder.name == 'root':
            folder_path = '/drive/items/root'
        else:
            folder_path = os.path.join(folder.parent_reference.path, folder.name)
        ref = onedrivesdk.ItemReference()
        ref.path = folder_path
        self.item(drive='me', id=_id).copy(name=item.name, parent_reference=ref).post()
        self.delete_file(_id)
    def download_file(self, file_id, path):
        item = self.item(drive='me', id=file_id)
        item.download(os.path.join(path, item.request().get().name))
    def delete_folder(self, folder_id):
        self.delete_file(folder_id)
    def delete_file(self, file_id):
        self.item(id=file_id).delete()
    def add_folder(self, path, folder_id='root'):
        item = onedrivesdk.Item({'name':ntpath.basename(path), 'folder':onedrivesdk.Folder()})
        return self.item(drive='me', id=folder_id).children.add(item).id
    def add_file(self, path, folder_id='root'):
        existing = {title for title, _, __, ___, ___ in self.files(folder_id).values()}
        title = ntpath.basename(path)
        if title in existing:
            base, suffix = title, 1
            while '{} ({})'.format(base, suffix) in existing:
                suffix += 1
            title = '{} ({})'.format(base, suffix)
        self.item(drive='me', id=folder_id).children[title].upload(path)