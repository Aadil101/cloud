from boxsdk import Client
import datetime
from dropbox import Dropbox
from dropbox.files import FolderMetadata
import ntpath
import onedrivesdk
from onedrivesdk import OneDriveClient
import os
from pydrive.drive import GoogleDrive
import requests
import sys

sys.stdout = open('message.log', 'w')

# constants
threshold = 1e6

class Dump:
    def __init__(self, lookup={}):
        self.lookup = lookup
    def add_drive(self, drive, drive_name):
        self.lookup[drive_name] = drive
    def get_drive(self, drive_name):
        return self.lookup[drive_name]
    def storage(self):
        return {drive_name:{'used':drive.used_storage_bytes(), 'remaining':drive.remaining_storage_bytes()} \
                for drive_name, drive in self.lookup.items()}
    def query(self, query, drive_name=None):
        if drive_name:
            return self.get_drive(drive_name).query(query)
        else:
            files = {}
            for _ , drive in self.lookup.items():
                files.update(drive.query(query))
            return files
    def files(self, drive_name=None, _id=None):
        if drive_name and _id:
            return self.get_drive(drive_name).files(_id)
        stuff = {}
        for drive_name in self.lookup:
            stuff.update(self.get_drive(drive_name).files())
        return stuff
    def download_folder(self, drive_name, _id, name, path):
        stack = [(_id, name)]
        id_to_path = {_id: path}
        while stack:
            folder_id, folder_name = stack.pop()
            folder_path = id_to_path[folder_id]
            os.mkdir(os.path.join(folder_path, folder_name))
            for file_id, file_details in self.files(drive_name, folder_id).items():
                (file_name, file_kind, _) = file_details[drive_name]
                if file_kind == 'folder':
                    id_to_path[file_id] = os.path.join(folder_path, folder_name)
                    stack.append((file_id, file_name))
                else:
                    self.download_file(drive_name, file_id, os.path.join(folder_path, folder_name))
    def download_file(self, drive_name, _id, path):
        self.get_drive(drive_name).download_file(_id, path)
    def delete_folder(self, drive_name, _id):
        self.get_drive(drive_name).delete_folder(_id)
    def delete_file(self, drive_name, _id):
        self.get_drive(drive_name).delete_file(_id)
    def add_folder(self, path, drive_name=None, folder=None, size_check=True):
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
            if drive_name:
                if drive_name in self.lookup:
                    drive = self.get_drive(drive_name)
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
                        return 'RIP, \'{}\' can\'t fit in \'{}\''.format(ntpath.basename(path, drive_name))
                else:
                    return 'RIP, \'{}\' isn\'t a drive'.format(drive_name)
            else:
                for _drive_name, _drive in self.lookup.items():
                    if size < _drive.remaining_storage_bytes()-threshold:
                        return self.add_folder(path, _drive_name, None, False)
                return 'RIP, there isn\'t enough space anywhere for \'{}\''.format(ntpath.basename(path))
        else:
            return 'RIP, folder doesn\'t exist at \'{}\''.format(path)
    def add_file(self, path, drive_name=None, folder=None):
        if os.path.isfile(path):
            if drive_name:
                if drive_name in self.lookup:
                    drive = self.get_drive(drive_name)
                    if os.path.getsize(path) < drive.remaining_storage_bytes()-threshold:
                        if folder:
                            if not drive.add_file(path, folder):
                                return 'RIP, \'{}\' already exists in this directory of \'{}\''.format(ntpath.basename(path), drive_name)
                        else:
                            if not drive.add_file(path):
                                return 'RIP, \'{}\' already exists in the root directory of \'{}\''.format(ntpath.basename(path), drive_name)
                    else:
                        return 'RIP, there isn\'t enough space in \'{}\' for \'{}\''.format(drive_name, ntpath.basename(path))
                else:
                    return 'RIP, \'{}\' isn\'t a drive'.format(drive_name)
            else:
                for _ , drive in self.lookup.items():
                    if os.path.getsize(path) < drive.remaining_storage_bytes()-threshold:
                        if drive.add_file(path):
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
    def used_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesByService'][0]['bytesUsed'])
    def remaining_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesTotal']) - self.used_storage_bytes()
    def query(self, query):
        return {file['id']:{'google':(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y'))} \
                for file in self.ListFile({'q': 'title="{}" and trashed=false'.format(query)}).GetList()}
    def files(self, _id='root'):
        return {file['id']:{'google':(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y'))} \
                for file in self.ListFile({'q': "'{}' in parents and trashed=false".format(_id)}).GetList()}
    def download_file(self, _id, path):
        file = self.CreateFile({'id': _id})
        if file['mimeType'] in mimetypes:
            download_type, download_ext = mimetypes[file['mimeType']]
            print('download_type: '+str(download_type)+', download_ext: '+str(download_ext))
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
        existing = {list(file.values())[0][0] for file in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            file = self.CreateFile({'title':ntpath.basename(path), 
                                'parents':[{'kind':'drive#fileLink', 'id':folder}]})
            file.SetContentFile(path)
            file.Upload()
            return True

class DBox(Dropbox):
    def used_storage_bytes(self):
        return self.users_get_space_usage().used
    def remaining_storage_bytes(self):
        return self.users_get_space_usage().allocation.get_individual().allocated - self.used_storage_bytes()
    def query(self, query):
        return {file.metadata.id:{'dropbox':(file.metadata.name, 'folder' if isinstance(file.metadata, FolderMetadata) else 'file', '?' if isinstance(file.metadata, FolderMetadata) else file.metadata.client_modified.strftime('%m/%d/%y'))} \
                for file in self.files_search('', query).matches}
    def files(self, _id=''):
        return {file.id:{'dropbox':(file.name, 'folder' if isinstance(file, FolderMetadata) else 'file', '?' if isinstance(file, FolderMetadata) else file.client_modified.strftime('%m/%d/%y'))} \
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
        existing = {list(file.values())[0][0] for file in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            with open(path, 'rb') as file:
                if folder == '' or len(folder) < 3 or folder[:3] != 'id:':
                    folder = '/' + folder
                self.files_upload(file.read(), os.path.join(folder, ntpath.basename(path)))
            return True

class Box(Client):
    def used_storage_bytes(self):
        return self.user().get().space_used
    def remaining_storage_bytes(self):
        return self.user().get().space_amount - self.used_storage_bytes()
    def query(self, query):
        return {item.id:{'box':(item.name, item.type, '?')} \
                for item in self.search().query(query)}
    def files(self, _id='0'):
        return {item.id:{'box':(item.name, item.type, '?')} \
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
        existing = {list(file.values())[0][0] for file in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            self.folder(folder).upload(path)
            return True

class ODrive(OneDriveClient):
    def _quota_dict(self):
        return requests.get(self.base_url + 'drive/', headers = {
                            'Authorization': 'bearer {access_token}'.format(access_token = str(self.auth_provider.access_token)),
                            'content-type': 'application/json'}).json()['quota']
    def used_storage_bytes(self):
        return self._quota_dict()['used']
    def remaining_storage_bytes(self):
        return self._quota_dict()['remaining']
    def query(self, query):
        return {item.id:{'onedrive':(item.name, 'file' if item.folder == None else 'folder', item.last_modified_date_time.strftime('%m/%d/%y'))} \
                for item in self.item(drive='me', id='root').search(q=query).get().items()}
    def files(self, _id='root'):
        return {item.id:{'onedrive':(item.name, 'file' if item.folder == None else 'folder', item.last_modified_date_time.strftime('%m/%d/%y'))} \
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
        existing = {list(file.values())[0][0] for file in self.files(folder).values()}
        if ntpath.basename(path) in existing:
            return False
        else:
            self.item(drive='me', id=folder).children[ntpath.basename(path)].upload(path)
            return True

'''
    #from absl import flags
    #FLAGS = flags.FLAGS
    #flags.DEFINE_float('threshold', 1e6, 'how close to full a drive can be')
'''