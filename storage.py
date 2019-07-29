from pydrive.drive import GoogleDrive
from dropbox import Dropbox
from dropbox.files import FolderMetadata
from boxsdk import Client
from onedrivesdk import OneDriveClient
from onedrivecmd.utils.actions import do_quota
import requests

class Dump:
    def __init__(self, lookup={}):
        self.lookup = lookup
    def add_drive(self, drive, name):
        self.lookup[name] = drive
    def details(self):
        return {name:{"used":drive.used_storage_bytes(), "remaining":drive.remaining_storage_bytes()} \
                for name, drive in self.lookup.items()}
    def files(self):
        return {name:drive.files_list() \
                for name, drive in self.lookup.items()}

class GDrive(GoogleDrive):
    def used_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesByService'][0]['bytesUsed'])
    def remaining_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesTotal']) - self.used_storage_bytes()
    def files_list(self):
        return [(file['title'], file['mimeType'], file['modifiedDate']) \
                for file in self.ListFile({'q': "'root' in parents and trashed=false"}).GetList()]

class DBox(Dropbox):
    def used_storage_bytes(self):
        return self.users_get_space_usage().used
    def remaining_storage_bytes(self):
        return self.users_get_space_usage().allocation.get_individual().allocated - self.used_storage_bytes()
    def files_list(self):
        return [(file.name, str(type(file)), '?' if isinstance(file, FolderMetadata) else file.client_modified) \
                for file in self.files_list_folder('').entries]

class Box(Client):
    def used_storage_bytes(self):
        return self.user().get().space_used
    def remaining_storage_bytes(self):
        return self.user().get().space_amount - self.used_storage_bytes()
    def files_list(self):
        return [(item.name, item.type, '?') \
                for item in self.folder('0').get_items()]

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
    def files_list(self):
        return [(item.name, 'file' if item.folder == None else item.folder, item.last_modified_date_time) \
                for item in self.item(drive='me', id='root').children.request().get()]