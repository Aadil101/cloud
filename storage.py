from boxsdk import Client, OAuth2
import datetime
from dropbox import Dropbox, DropboxOAuth2FlowNoRedirect
from dropbox.files import FolderMetadata
import keyring
import ntpath
import onedrivesdk
from onedrivesdk import AuthProvider, HttpProvider, OneDriveClient
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import requests
import sys

# constants
threshold = 1e6

class Dump:
    def __init__(self, lookup={}):
        self.lookup = lookup
    def add_drive(self, drive, drive_kind):
        self.lookup[drive_kind].append(drive)
    def storage(self):
        return {drive_kind:{'used':sum(drive.used_storage_bytes() for drive in drives), \
                       'remaining':sum(drive.remaining_storage_bytes() for drive in drives)} \
                for drive_kind, drives in self.lookup.items()}
    def query(self, query, drive=None):
        if drive:
            return drive.query(query)
        stuff = {}
        for drives in self.lookup.values():
            for drive in drives:
                stuff.update(drive.query(query))
        return stuff
    def files(self, drive=None, _id=None):
        if drive and _id:
            return drive.files(_id)
        stuff = {}
        for drives in self.lookup.values():
            for drive in drives:
                stuff.update(drive.files())
        return stuff
    def download_folder(self, drive, _id, name, path):
        stack = [(_id, name)]
        id_to_path = {_id: path}
        while stack:
            folder_id, folder_name = stack.pop()
            folder_path = id_to_path[folder_id]
            os.mkdir(os.path.join(folder_path, folder_name))
            for file_id, (file_name, file_kind, _, __, ___) in self.files(drive, folder_id).items():
                if file_kind == 'folder':
                    id_to_path[file_id] = os.path.join(folder_path, folder_name)
                    stack.append((file_id, file_name))
                else:
                    self.download_file(drive, file_id, os.path.join(folder_path, folder_name))
    def download_file(self, drive, _id, path):
        drive.download_file(_id, path)
    def delete_folder(self, drive, _id):
        drive.delete_folder(_id)
    def delete_file(self, drive, _id):
        drive.delete_file(_id)
    def add_folder(self, path, drive=None, folder=None, size_check=True):
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
                    if folder:
                        path_to_id[os.path.join(folder, ntpath.basename(path))] = drive.add_folder(path, folder)
                    else:
                        path_to_id[ntpath.basename(path)] = drive.add_folder(path)
                    for root, dirs, files in os.walk(path):
                        local = root[root.find(ntpath.basename(path)):]
                        for _dir in dirs:
                            if folder:
                                path_to_id[os.path.join(folder, local, _dir)] = drive.add_folder(os.path.join(root, _dir), path_to_id[os.path.join(folder, local)])
                            else:
                                path_to_id[os.path.join(local, _dir)] = drive.add_folder(os.path.join(root, _dir), path_to_id[local])
                        for file in files:
                            if not file.startswith('.'):
                                if folder:
                                    drive.add_file(os.path.join(root, file), path_to_id[os.path.join(folder, local)])
                                else:
                                    drive.add_file(os.path.join(root, file), path_to_id[local])
                else:
                    return 'RIP, \'{}\' can\'t fit in this drive'.format(ntpath.basename(path))
            else:
                for drives in self.lookup.values():
                    for _drive in drives:
                        if size < _drive.remaining_storage_bytes()-threshold:
                            return self.add_folder(path, _drive, None, False)
                return 'RIP, there isn\'t enough space anywhere for \'{}\''.format(ntpath.basename(path))
        else:
            return 'RIP, folder doesn\'t exist at \'{}\''.format(path)
    def add_file(self, path, drive=None, folder=None):
        if os.path.isfile(path):
            if drive:
                if os.path.getsize(path) < drive.remaining_storage_bytes()-threshold:
                    if folder:
                        if not drive.add_file(path, folder):
                            return 'RIP, \'{}\' already exists in this directory'.format(ntpath.basename(path))
                    else:
                        if not drive.add_file(path):
                            return 'RIP, \'{}\' already exists in the root directory'.format(ntpath.basename(path))
                else:
                    return 'RIP, there isn\'t enough space in this drive for \'{}\''.format(ntpath.basename(path))
            else:
                for drives in self.lookup.values():
                    for _drive in drives:
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
    count = 0
    def __init__(self, credentials):
        self._id = GDrive.count
        super(GDrive, self).__init__(self.boot(credentials))
        GDrive.count += 1
    @staticmethod
    def credentials():
        # this is a new user, so build new credentials
        gauth = GoogleAuth()
        credentials = os.path.join('credentials/google', str(GDrive.count))
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
        return {file['id']:(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', 'google', self._id, datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y')) \
                for file in self.ListFile({'q': 'title="{}" and trashed=false'.format(query)}).GetList()}
    def files(self, _id='root'):
        return {file['id']:(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', 'google', self._id, datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y')) \
                for file in self.ListFile({'q': "'{}' in parents and trashed=false".format(_id)}).GetList()}
    def download_file(self, _id, path):
        file = self.CreateFile({'id': _id})
        if file['mimeType'] in mimetypes:
            download_type, download_ext = mimetypes[file['mimeType']]
            file.GetContentFile(os.path.join(path, file['title'].replace('/', u'\u2215')+download_ext), mimetype=download_type)
        else:
            file.GetContentFile(os.path.join(path, file['title']), mimetype=file['mimeType'])
    def delete_folder(self, _id):
        file = self.CreateFile({'id': _id})
        file.Trash()
    def delete_file(self, _id):
        file = self.CreateFile({'id': _id})
        file.Trash()
    def add_folder(self, path, folder='root'):
        folder_metadata = {'title':ntpath.basename(path), 'mimeType':'application/vnd.google-apps.folder',
                            'parents':[{'id':folder}]}
        new_folder = self.CreateFile(folder_metadata)
        new_folder.Upload()
        return new_folder['id']
    def add_file(self, path, folder='root'):
        existing = {title for title, _, __, ___, ___ in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            file = self.CreateFile({'title':ntpath.basename(path), 
                                'parents':[{'kind':'drive#fileLink', 'id':folder}]})
            file.SetContentFile(path)
            file.Upload()
            return True

class DBox(Dropbox):
    count = 0
    auth_flow = None
    def __init__(self, credentials):
        self._id = DBox.count
        super(DBox, self).__init__(self.boot(credentials))
        DBox.count += 1
    @staticmethod
    def credentials(auth_code=None):
        credentials = os.path.join('credentials/dropbox', str(DBox.count))
        if auth_code:
            oauth_result = None
            try:
                oauth_result = DBox.auth_flow.finish(auth_code)
            except:
                return 'failure', None
            else:
                with open(os.path.join(credentials, 'credentials.txt'), 'a+') as file:
                    file.write(oauth_result.access_token)
                return 'success', credentials
        else:
            os.mkdir(credentials)
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
        return {file.metadata.id:(file.metadata.name, 'folder' if isinstance(file.metadata, FolderMetadata) else 'file', 'dropbox', self._id, '?' if isinstance(file.metadata, FolderMetadata) else file.metadata.client_modified.strftime('%m/%d/%y')) \
                for file in self.files_search('', query).matches}
    def files(self, _id=''):
        return {file.id:(file.name, 'folder' if isinstance(file, FolderMetadata) else 'file', 'dropbox', self._id, '?' if isinstance(file, FolderMetadata) else file.client_modified.strftime('%m/%d/%y')) \
                for file in self.files_list_folder(_id).entries}
    def download_file(self, _id, path):
        meta = self.files_get_metadata(_id)
        self.files_download_to_file(os.path.join(path, meta.name), _id)
    def delete_folder(self, _id):
        self.delete(_id)
    def delete_file(self, _id):
        self.delete(_id)
    def add_folder(self, path, folder=''):
        new_path = os.path.join(folder, ntpath.basename(path), 'test.txt')
        self.files_upload(None, new_path)
        self.files_delete(new_path)
        return self.files_get_metadata(os.path.join(folder, ntpath.basename(path))).id
    def add_file(self, path, folder=''):
        existing = {title for title, _, __, ___, ___ in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            with open(path, 'rb') as file:
                if folder == '' or len(folder) < 3 or folder[:3] != 'id:':
                    folder = '/' + folder
                self.files_upload(file.read(), os.path.join(folder, ntpath.basename(path)))
            return True

class Box(Client):
    count = 0
    def __init__(self, credentials):
        self._id = Box.count
        self.username = None
        super(Box, self).__init__(self.boot(credentials))
        Box.count += 1
    @staticmethod
    def credentials(auth_code=None):
        credentials = os.path.join('credentials/box', str(Box.count))
        oauth = OAuth2(
            client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
            client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6'
        )
        if auth_code:
            access_token, refresh_token = None, None
            try:    
                access_token, refresh_token = oauth.authenticate(auth_code)
            except:
                return 'failure', None
            else:
                username = Client(oauth).user().get().__dict__['login']
                with open(os.path.join(credentials, 'credentials.txt'), 'a+') as file:
                    file.write(username)
                keyring.set_password('Box_Auth', username, access_token)
                keyring.set_password('Box_Refresh', username, refresh_token)
                return 'success', credentials
        else:
            os.mkdir(credentials)
            auth_url, _ = oauth.get_authorization_url('http://localhost')
            return 'pending', auth_url
    def store_tokens(self, access_token, refresh_token):
        # use keyring to store the tokens
        keyring.set_password('Box_Auth', self.username, access_token)
        keyring.set_password('Box_Refresh', self.username, refresh_token)
    def boot(self, credentials):
        with open(os.path.join(credentials, 'credentials.txt')) as file:
            self.username = file.readline()
        # build credentials
        oauth = OAuth2(
            client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
            client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6',
            store_tokens=self.store_tokens,
            access_token=keyring.get_password('Box_Auth', self.username),
            refresh_token=keyring.get_password('Box_Refresh', self.username)
		)
        return oauth
    def email(self):
        return self.user().get()['login']
    def used_storage_bytes(self):
        return self.user().get().space_used
    def remaining_storage_bytes(self):
        return self.user().get().space_amount - self.used_storage_bytes()
    def query(self, query):
        return {item.id:(item.name, item.type, 'box', self._id, '?') \
                for item in self.search().query(query)}
    def files(self, _id='0'):
        return {item.id:(item.name, item.type, 'box', self._id, '?') \
                for item in self.folder(_id).get_items()}
    def download_file(self, _id, path):
        file = self.file(_id)
        with open(os.path.join(path, file.get().name), 'wb') as out_file:
            file.download_to(out_file)
            out_file.close()
    def delete_folder(self, _id):
        self.folder(_id).delete()
    def delete_file(self, _id):
        self.file(_id).delete()
    def add_folder(self, path, folder='0'):
        return self.folder(folder).create_subfolder(ntpath.basename(path)).id
    def add_file(self, path, folder='0'):
        existing = {title for title, _, __, ___, ___ in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            self.folder(folder).upload(path)
            return True

class ODrive(OneDriveClient):
    redirect_url = 'http://localhost:8080/'
    client_id='06d11a46-6c06-4dd2-8f8a-23b22041cb22'
    client_secret = 'r2A/ce3_u+WaF27EiCHTP[Eu7*rbK+55'
    base_url='https://api.onedrive.com/v1.0/'
    scopes=['wl.signin', 'wl.offline_access', 'onedrive.readwrite']
    count = 0
    auth_provider = None
    def __init__(self, credentials):
        self._id = ODrive.count
        super(ODrive, self).__init__(*self.boot(credentials))
        ODrive.count += 1
    @staticmethod
    def credentials(auth_code=None):
        credentials = os.path.join('credentials/onedrive', str(ODrive.count))
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
                ODrive.auth_provider.save_session(path=os.path.join(credentials, 'credentials.pickle'))
                return 'success', credentials
            ODrive.auth_provider = None
        else:
            os.mkdir(credentials)
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
        return '?'
    def _quota_dict(self):
        return requests.get(self.base_url + 'drive/', headers = {
                            'Authorization': 'bearer {access_token}'.format(access_token = str(self.auth_provider.access_token)),
                            'content-type': 'application/json'}).json()['quota']
    def used_storage_bytes(self):
        return self._quota_dict()['used']
    def remaining_storage_bytes(self):
        return self._quota_dict()['remaining']
    def query(self, query):
        return {item.id:(item.name, 'file' if item.folder == None else 'folder', 'onedrive', self._id, item.last_modified_date_time.strftime('%m/%d/%y')) \
                for item in self.item(drive='me', id='root').search(q=query).get().items()}
    def files(self, _id='root'):
        return {item.id:(item.name, 'file' if item.folder == None else 'folder', 'onedrive', self._id, item.last_modified_date_time.strftime('%m/%d/%y')) \
                for item in self.item(drive='me', id=_id).children.request().get()}
    def download_file(self, _id, path):
        item = self.item(drive='me', id=_id)
        item.download(os.path.join(path, item.request().get().name))
    def delete_folder(self, _id):
        self.item(id=_id).delete()
    def delete_file(self, _id):
        self.item(id=_id).delete()
    def add_folder(self, path, folder='root'):
        item = onedrivesdk.Item({'name':ntpath.basename(path), 'folder':onedrivesdk.Folder()})
        return self.item(drive='me', id=folder).children.add(item).id
    def add_file(self, path, folder='root'):
        existing = {title for title, _, __, ___, ___ in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            self.item(drive='me', id=folder).children[ntpath.basename(path)].upload(path)
            return True