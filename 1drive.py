import onedrivesdk

redirect_uri = 'http://localhost'
client_secret = 'EGwuldkL5sMZ3-b7Yr:7LHxKaZ/P-a5A'
client_id='3a52d46c-a064-45db-92af-5ca0f06c14af'
api_base_url='https://api.onedrive.com/v1.0/'
scopes=['wl.signin', 'wl.offline_access', 'onedrive.readwrite']

http_provider = onedrivesdk.HttpProvider()
auth_provider = onedrivesdk.AuthProvider(
    http_provider=http_provider,
    client_id=client_id,
    scopes=scopes)

client = onedrivesdk.OneDriveClient(api_base_url, auth_provider, http_provider)
auth_url = client.auth_provider.get_auth_url(redirect_uri)
# Ask for the code
print('Paste this URL into your browser, approve the app\'s access.')
print('Copy everything in the address bar after "code=", and paste it below.')
print(auth_url)
code = raw_input('Paste code here: ')

client.auth_provider.authenticate(code, redirect_uri, client_secret)

# Save the session for later
auth_provider.save_session()