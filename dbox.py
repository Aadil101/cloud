import dropbox
dbx = dropbox.Dropbox('Wl2ZKVSB8DQAAAAAAAABFXh6kGHd3mQ0QgvESD9PT-oKmPPif0RERQnEqnAyl_2n')

#####

for file in dbx.files_list_folder('').entries:
    print(file.name)

#####

box = dbx.users_get_space_usage()
print('{0:.2f} gb used by dropbox'.format(box.used/1.0e9))
print('{0:.2f} gb remaining in dropbox'.format((box.allocation.get_individual().allocated-box.used)/1.0e9))

