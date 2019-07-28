from pydrive.auth import GoogleAuth

gauth = GoogleAuth()
# Create local webserver and auto handles authentication.
gauth.LocalWebserverAuth()

from pydrive.drive import GoogleDrive

drive = GoogleDrive(gauth)

file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()

#####

for file in file_list:
    print('title: %s, id: %s' % (file['title'], file['id']))

#####

info = drive.GetAbout()
#print(info['quotaBytesByService'][0]['bytesUsed'])
#print(info['quotaBytesByService'])
#print(info['quotaBytesTotal'])
#print(info.keys())
print('{0:.2f} gb used by google drive'.format(int(info['quotaBytesByService'][0]['bytesUsed'])/1.0e9))
print('{0:.2f} gb remaining in google cloud storage'.format(  ( (int(info['quotaBytesTotal'])-int(info['quotaBytesUsedAggregate'])))/1.0e9 )  )

#####