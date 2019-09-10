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
        "boxsdk[jwt]",
        'onedrivesdk',
        'requests',
        'datetime',
        'keyring',
        'absl-py',
        'cursor',
        'python-docx',
    ],
)