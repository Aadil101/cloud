from boxsdk import OAuth2
import keyring
from storage import Box

oauth = OAuth2(
    client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
    client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6',
    access_token=keyring.get_password('Box_Auth', 'aadilislam101@gmail.com'),
    refresh_token=keyring.get_password('Box_Refresh', 'aadilislam101@gmail.com')
)

box = Box(oauth)
files = box.files()
print(vars(box.folder('0').create_subfolder('holder')))