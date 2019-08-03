from setuptools import setup

setup(
    name='cloud',
    version='1.0',
    description='a cloud storage manager',
    author='Aadil Islam',
    author_email='aadilislam101@gmail.com',
    install_requires=[
        'pydrive',
        'dropbox',
        'boxsdk',
        'onedrivesdk',
        'onedrivecmd',
        'requests',
        'datetime',
        'keyring',
        'absl-py',
        'windows-curses',
    ],
)