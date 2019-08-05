from pydrive.auth import GoogleAuth

gauth = GoogleAuth()
# Create local webserver and auto handles authentication.
gauth.LocalWebserverAuth()

from pydrive.drive import GoogleDrive

drive = GoogleDrive(gauth)

'''
file_list = drive.ListFile({'q': "'root' in parents and trashed=false"}).GetList()
folder = file_list[0]
print(folder)
print(folder['title'])
folder_file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(folder['id'])}).GetList()
for file in folder_file_list:
    print(file['title'])
'''

#####

'''
for file in file_list:
    print(file['title'])
    for key in file:
        print('  '+str(key))
        print('     '+str(file[key]))
    #print('title: %s, id: %s' % (file['title'], file['id']))
'''
#####

info = drive.GetAbout()
#print(info['quotaBytesByService'][0]['bytesUsed'])
#print(info['quotaBytesByService'])
#print(info['quotaBytesTotal'])
#print(info.keys())
print('{0:.2f} gb used by google drive'.format(int(info['quotaBytesByService'][0]['bytesUsed'])/1.0e9))
#print('{0:.2f} gb remaining in google cloud storage'.format(  ( (int(info['quotaBytesTotal'])-int(info['quotaBytesUsedAggregate'])))/1.0e9 )  )

#####
from pydrive.auth import GoogleAuth
from storage import GDrive
import ntpath

gdrive = GDrive(GoogleAuth().LocalWebserverAuth())
#####
'''
gdrive.add_file('data/for.txt')
file = drive.CreateFile({'title': ntpath.basename('data/for.txt'), 
                        'parents': [{'kind': 'drive#fileLink', 'id': 'root'}]})
file.SetContentFile('data/for.txt')
file.Upload()
'''
#####
#folder_metadata = {'title' : 'MyFolder', 'mimeType' : 'application/vnd.google-apps.folder'}
#folder = drive.CreateFile(folder_metadata)
#folder.Upload()
#def add_folder(self, path, folder='root'):
path = 'data/in_a_world/whoosh'
folder = '13VuIovcnfrcWOrsqRaxVIHOaqnAADZa5'
#'1PvS58VGMpaXIM5He8GIb5Df0WCdRmpyM'
'''
print('path: '+ str(path)+ ', folder: ' + str(folder))
folder_metadata = {'title':ntpath.basename(path), 'mimeType':'application/vnd.google-apps.folder',
                    'parents':[{'id':folder}]}
new_folder = gdrive.CreateFile(folder_metadata)
new_folder.Upload()
'''
#gdrive.add_folder(path, folder)
folder_metadata = {'title':'test', 'mimeType':'application/vnd.google-apps.folder',
                            'parents':[{'id':'13VuIovcnfrcWOrsqRaxVIHOaqnAADZa5'}]}
new_folder = gdrive.CreateFile(folder_metadata)
new_folder.Upload()
print(new_folder['id'])