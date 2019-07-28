from boxsdk import Client, OAuth2
import keyring

oauth = OAuth2(
    client_id='x5jgd9owo4utthuk6vz0qxu3ejxv2drz',
    client_secret='X5ZVOxuOIAIIjMBCyCo7IQxWxX0UWfX6',
    access_token=keyring.get_password('Box_Auth', 'aadilislam101@gmail.com'),
    refresh_token=keyring.get_password('Box_Refresh', 'aadilislam101@gmail.com')
)

client = Client(oauth)
user = client.user().get()
policies = client.get_storage_policies()
print(type(policies))
# box object collection, specifically marker based object collection
print(client.user().get().space_amount)