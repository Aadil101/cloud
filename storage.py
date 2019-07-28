from pydrive.drive import GoogleDrive
from dropbox import Dropbox
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
        info = {}
        for name, drive in self.lookup.items():
            info[name] = {"used":drive.used_storage_bytes(), "remaining":drive.remaining_storage_bytes()}
        return info

class GDrive(GoogleDrive):
    def used_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesByService'][0]['bytesUsed'])
    def remaining_storage_bytes(self):
        return int(self.GetAbout()['quotaBytesTotal']) - self.used_storage_bytes()

class DBox(Dropbox):
    def used_storage_bytes(self):
        return self.users_get_space_usage().used
    def remaining_storage_bytes(self):
        return self.users_get_space_usage().allocation.get_individual().allocated - self.used_storage_bytes() 

class Box(Client):
    def used_storage_bytes(self):
        return self.user().get().space_used
    def remaining_storage_bytes(self):
        return self.user().get().space_amount - self.used_storage_bytes()

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