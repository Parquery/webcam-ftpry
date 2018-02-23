"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""
import os

from setuptools import setup, find_packages

# pylint: disable=redefined-builtin

here = os.path.abspath(os.path.dirname(__file__))  # pylint: disable=invalid-name

with open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()  # pylint: disable=invalid-name

setup(
    name='webcam-ftpry',
    version='1.0.5',
    description='Captures images from a web cam and uploads them to an FTP server',
    long_description=long_description,
    url='https://bitbucket.org/parqueryopen/webcam-ftpry',
    author='Marko Ristin',
    author_email='marko@parquery.com',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='webcam ftp image',
    python_requires='>=3.5',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=['opencv-python>=3.4.0.12', 'reconnecting_ftp>=1.0.4'],
    extras_require={
        'test': ['pyftpdlib'],
        'dev': ['mypy==0.560', 'pylint==1.8.2', 'yapf==0.20.2']
    },
    py_modules=['webcam_ftpry'],
    scripts=['bin/webcam-ftpry'])
