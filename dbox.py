from storage import DBox
dbx = DBox('Wl2ZKVSB8DQAAAAAAAABFXh6kGHd3mQ0QgvESD9PT-oKmPPif0RERQnEqnAyl_2n')

#####
'''
files = dbx.files_list_folder('').entries
folder = files[0]
print(folder)
'''
import os
import ntpath
'''
path = '/stuff/for.txt'
folder = '/dest'
path_mod = ntpath.basename(path)
path_new = os.path.join(folder, ntpath.basename(path))
print(path_new)
'''
###

#filename, file_extension = os.path.splitext(path)
#print(filename)
#print(file_extension)
#path = os.path.join(folder, base_filename + "." + filename_suffix)

###

'''
path = 'data/for.txt'
folder = '/'

with open(path, 'rb') as file:
    dbx.files_upload(file.read(), os.path.join(folder, ntpath.basename(path)))
'''

###

#for file in dbx.files_list_folder(files[0].path_display).entries:
#    print(file.name)
#for file in dbx.files_list_folder('').entries:
#    print(type(file))

#####

#box = dbx.users_get_space_usage()
#print('{0:.2f} gb used by dropbox'.format(box.used/1.0e9))
#print('{0:.2f} gb remaining in dropbox'.format((box.allocation.get_individual().allocated-box.used)/1.0e9))

'''
path = 'data/for.txt'
folder_id = 'id:6FHHBVgfxDkAAAAAAAAAHA/in_a_world'
with open(path, 'rb') as file:
    if folder_id == '' or len(folder_id) < 3 or folder_id[:3] != 'id:':
        folder_id = '/' + folder_id
    out_path = os.path.join(folder_id, ntpath.basename(path))
    print(out_path)
    dbx.files_upload(file.read(), out_path)
'''

'''
folder = 'id:6FHHBVgfxDkAAAAAAAAAHA'
path = 'in_a_world'
#dbx.files_create_folder_v2(os.path.join(folder, path))
new_path = os.path.join(folder, ntpath.basename(path), 'test.txt')
dbx.files_upload(None, new_path)
dbx.files_delete(new_path)
'''

#dbx.add_folder('data/in_a_world', 'id:6FHHBVgfxDkAAAAAAAAAHA')
path = 'data/in_a_world'
folder = 'id:6FHHBVgfxDkAAAAAAAAAHA'
new_path = os.path.join(folder, ntpath.basename(path), 'test.txt')
dbx.files_upload(None, new_path)
dbx.files_delete(new_path)
meta = dbx.files_get_metadata(os.path.join(folder, ntpath.basename(path)))
print(meta.id)
