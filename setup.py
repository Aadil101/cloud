from setuptools import setup

setup(
    name='cloud',
    version='1.0',
    description='A cloud storage manager',
    author='Aadil Islam',
    author_email='aadilislam101@gmail.com',
    install_requires=[
        'boxsdk',
        'cursor',
        'datetime',
        'dropbox',
        'keyring',
        'onedrivesdk',
        'pydrive',
        'python-docx',
        'requests',
    ],
)