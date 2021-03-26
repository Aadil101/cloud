# Cloud
Command-line access to your files across major cloud service accounts. Currently works with Google Drive, OneDrive, Box, and Dropbox. Implemented such that new services (Python API required) can easily be incorporated in the future.

## Demo
![demo](images/demo.gif)

### Upload this
![upload](images/upload.gif)

### Delete that
![delete](images/delete.gif)

### Download things
![download](images/download.gif)

### Search it
![search](images/search.gif)

### Storage summary
![summary](images/summary.gif)

## Installation

Use the package manager `pip` to install Cloud:

`pip install -r requirements.txt`

## Usage

Start the program using the following:

`python program.py`

Keyboard Controls:
- ⬆️:
  - Scroll up.
- ⬇️:
  - Scroll down.
- ➡️
  - Move forward in page history.
- ⬅️:
  - Move backward in page history.
- `1-4`:
  - Sort items in working directory by metadata.
- `a`:
  - Initiate account management mode.
  - `a`: 
    - Add new account.
  - `delete`/`backspace`:
    - Remove selected account.
- `d`:
  - Download selected file/folder locally.
- `delete`/`backspace`:
  - Remove selected file/folder.
- `m`:
  - Initiate file/folder staging mode.
  - `return`/`enter`:
    -  Add selected file/folder to staging area.
    -  (Hit enter again if you want to un-stage it.)
  - `m`:
    -  Initiate file/folder moving mode.
    -  `m`:
       -  Move staged items to working directory.
- `return`/`enter`:
  - If a folder is selected, this changes the working directory to that folder.
- `q`:
  - Exit program.
- `s`:
  - Initiate file/folder searching mode.
- `space`:
  - Show remaining storage summary.
- `u`:
  - Initiate file/folder uploading mode.

## Contributing 

Pull requests are always welcome :)

## License

Distributed under the MIT License. See LICENSE for more information.