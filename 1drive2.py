import onedrivesdk

client_id='3a52d46c-a064-45db-92af-5ca0f06c14af'
api_base_url='https://api.onedrive.com/v1.0/'
scopes=['wl.signin', 'wl.offline_access', 'onedrive.readwrite']

http_provider = onedrivesdk.HttpProvider()
auth_provider = onedrivesdk.AuthProvider(
    http_provider=http_provider,
    client_id=client_id,
    scopes=scopes)

#### Next time you start the app ####
auth_provider = onedrivesdk.AuthProvider(http_provider,
                                         client_id,
                                         scopes)
auth_provider.load_session()
auth_provider.refresh_token()
client = onedrivesdk.OneDriveClient(api_base_url, auth_provider, http_provider)

from onedrivecmd.utils.actions import do_quota
import requests

def sizeof_fmt(num, suffix = 'B'):
    '''int, str->str
    Format file size as human readable.
    From:
    https://web.archive.org/web/20111010015624/http://blogmag.net/blog/read/38/Print_human_readable_file_size
    '''
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

access_token = str(client.auth_provider.access_token)
req = requests.get(client.base_url + 'drive/',
                       headers = {
                           'Authorization': 'bearer {access_token}'.format(access_token = str(auth_provider.access_token)),
                           'content-type': 'application/json'})
total = req.json()['quota']['total']
print(total)