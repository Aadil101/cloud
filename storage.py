from pydrive.drive import GoogleDrive
from dropbox import Dropbox
from dropbox.files import FolderMetadata
from boxsdk import Client
from onedrivesdk import OneDriveClient
from onedrivecmd.utils.actions import do_quota
import requests
import datetime

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
    def files(self):
        stuff = {}
        for _, drive in self.lookup.items():
            stuff.update(drive.files_list())
        return stuff

class GDrive(GoogleDrive):
    def used_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesByService'][0]['bytesUsed'])
    def remaining_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesTotal']) - self.used_storage_bytes()
    def files_list(self, _id='root'):
        return {file['id']:{'google':(file['title'], 'folder' if file['mimeType']=='application/vnd.google-apps.folder' else 'file', datetime.datetime.strptime(file['modifiedDate'].split('T')[0], '%Y-%m-%d').strftime('%m/%d/%y'))} \
                for file in self.ListFile({'q': "'{}' in parents and trashed=false".format(_id)}).GetList()}

class DBox(Dropbox):
    def used_storage_bytes(self):
        return self.users_get_space_usage().used
    def remaining_storage_bytes(self):
        return self.users_get_space_usage().allocation.get_individual().allocated - self.used_storage_bytes()
    def files_list(self, _id=''):
        return {file.id:{'dropbox':(file.name, 'folder' if isinstance(file, FolderMetadata) else 'file', '?' if isinstance(file, FolderMetadata) else file.client_modified.strftime('%m/%d/%y'))} \
                for file in self.files_list_folder(_id).entries}

class Box(Client):
    def used_storage_bytes(self):
        return self.user().get().space_used
    def remaining_storage_bytes(self):
        return self.user().get().space_amount - self.used_storage_bytes()
    def files_list(self, _id='0'):
        return {item.id:{'box':(item.name, item.type, '?')} \
                for item in self.folder(_id).get_items()}

class ODrive(OneDriveClient):
    def _quota_dict(self):
        return requests.get(self.base_url + 'drive/',
                            headers = {
                                'Authorization': 'bearer {access_token}'.format(access_token = str(self.auth_provider.access_token)),
                                'content-type': 'application/json'}).json()['quota']
    def used_storage_bytes(self):
        return self._quota_dict()['used']
    def remaining_storage_bytes(self):
        return self._quota_dict()['remaining']
    def files_list(self, _id='root'):
        return {item.id:{'onedrive':(item.name, 'file' if item.folder == None else 'folder', item.last_modified_date_time.strftime('%m/%d/%y'))} \
                for item in self.item(drive='me', id=_id).children.request().get()}