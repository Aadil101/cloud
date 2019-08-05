from pydrive.drive import GoogleDrive
from dropbox import Dropbox
from dropbox.files import FolderMetadata
from boxsdk import Client
import onedrivesdk
from onedrivesdk import OneDriveClient
from onedrivecmd.utils.actions import do_quota
import requests
import datetime
import os
import sys
#from absl import flags
import ntpath

#sys.stdout = open('message.log', 'w')

#FLAGS = flags.FLAGS
#flags.DEFINE_float('threshold', 1e6, 'how close to full a drive can be')
threshold = 1e6

class Dump:
    def __init__(self, lookup={}):
        self.lookup = lookup
    def add_drive(self, drive, name):
        self.lookup[name] = drive
    def get_drive(self, name):
        return self.lookup[name]
    def storage(self):
        return {name:{"used":drive.used_storage_bytes(), "remaining":drive.remaining_storage_bytes()} \
                for name, drive in self.lookup.items()}
    def files(self, drive=None, _id=None):
        if drive and _id:
            return self.lookup[drive].files(_id)
        stuff = {}
        for _ , drive in self.lookup.items():
            stuff.update(drive.files())
        return stuff
    def add_folder(self, path, drive=None, folder=None, size_check=True):
        if os.path.isdir(path):
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
                if not size_check or size < self.lookup[drive].remaining_storage_bytes()-threshold:
                    path_to_id = {}
                    if folder:
                        path_to_id[os.path.join(folder, ntpath.basename(path))] = self.lookup[drive].add_folder(path, folder)
                    else:
                        path_to_id[ntpath.basename(path)] = self.lookup[drive].add_folder(path)
                    for root, dirs, files in os.walk(path):
                        local = root[root.find(ntpath.basename(path)):]
                        for _dir in dirs:
                            if folder:
                                path_to_id[os.path.join(folder, local, _dir)] = self.lookup[drive].add_folder(os.path.join(root, _dir), path_to_id[os.path.join(folder, local)])
                            else:
                                path_to_id[os.path.join(local, _dir)] = self.lookup[drive].add_folder(os.path.join(root, _dir), path_to_id[local])
                        for file in files:
                            if not file.startswith('.'):
                                if folder:
                                    self.lookup[drive].add_file(os.path.join(root, file), path_to_id[os.path.join(folder, local)])
                                else:
                                    self.lookup[drive].add_file(os.path.join(root, file), path_to_id[local])
                else:
                    return 'RIP, \'{}\' can\'t fit in \'{}\''.format(ntpath.basename(path, drive))
            else:
                for _ , drive in self.lookup.items():
                    if size < drive.remaining_storage_bytes()-threshold:
                        return self.add_folder(path, drive, size_check=False)
                return 'RIP, there isn\'t enough space anywhere for \'{}\''.format(ntpath.basename(path))
        else:
            return 'RIP, folder doesn\'t exist at \'{}\''.format(path)
    def add_file(self, path, drive=None, folder=None):
        if os.path.isfile(path):
            if drive:
                if drive in self.lookup:
                    if os.path.getsize(path) < self.lookup[drive].remaining_storage_bytes()-threshold:
                        if folder:
                            if not self.lookup[drive].add_file(path, folder):
                                return 'RIP, \'{}\' already exists in this directory of \'{}\''.format(ntpath.basename(path), drive)
                        else:
                            if not self.lookup[drive].add_file(path):
                                return 'RIP, \'{}\' already exists in the root directory of \'{}\''.format(ntpath.basename(path), drive)
                    else:
                        return 'RIP, there isn\'t enough space in \'{}\' for \'{}\''.format(drive, ntpath.basename(path))
                else:
                    return 'RIP, \'{}\' isn\'t a drive'.format(drive)
            else:
                for _ , drive in self.lookup.items():
                    if os.path.getsize(path) < drive.remaining_storage_bytes()-threshold:
                        if drive.add_file(path):
                            return
                return 'RIP, there isn\'t enough space anywhere for \'{}\''.format(ntpath.basename(path))
        else:
            return 'RIP, file doesn\'t exist at \'{}\''.format(path)

class GDrive(GoogleDrive):
    def used_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesByService'][0]['bytesUsed'])
    def remaining_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesTotal']) - self.used_storage_bytes()
    def files(self, _id='root'):
        return {file['id']:{'google':(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y'))} \
                for file in self.ListFile({'q': "'{}' in parents and trashed=false".format(_id)}).GetList()}
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
    def files(self, _id=''):
        return {file.id:{'dropbox':(file.name, 'folder' if isinstance(file, FolderMetadata) else 'file', '?' if isinstance(file, FolderMetadata) else file.client_modified.strftime('%m/%d/%y'))} \
                for file in self.files_list_folder(_id).entries}
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
    def files(self, _id='0'):
        return {item.id:{'box':(item.name, item.type, '?')} \
                for item in self.folder(_id).get_items()}
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
    def files(self, _id='root'):
        return {item.id:{'onedrive':(item.name, 'file' if item.folder == None else 'folder', item.last_modified_date_time.strftime('%m/%d/%y'))} \
                for item in self.item(drive='me', id=_id).children.request().get()}
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