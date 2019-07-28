from boxsdk import OAuth2
import keyring

def store_tokens(access_token, refresh_token):
    # Use keyring to store the tokens
    keyring.set_password('Box_Auth', 'aadilislam101@gmail.com', access_token)
    keyring.set_password('Box_Refresh', 'aadilislam101@gmail.com', refresh_token)

oauth = OAuth2(
    client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
    client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6',
    store_tokens=store_tokens,
)

access_token, refresh_token = oauth.authenticate('AF24Mjd8uMpMlARvQz2al37GM1PFOslo')

print(access_token)
print(refresh_token)