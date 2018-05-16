#!/usr/bin/env python

from setuptools import setup,find_packages
import os

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
	return open(os.path.join(os.path.dirname(__file__), fname)).read()

PACKAGE = "pastor"
NAME = "pastor"
DESCRIPTION = "Description of pastor"
AUTHOR = "Banio Carpenter"
AUTHOR_EMAIL = "banio@mncarpenters.net"
URL = ""
VERSION = "0.1"

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=read("README.md"),
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="BSD",
    url=URL,
    packages=find_packages(),
    install_requires=['setuptools', 'termcolor', 'vmtools', 'argparse', 'boto3', 'sshmaster', 'botohelper', 'PyYAML'],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: cloud",
        "Intended Audience :: system admins",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    zip_safe=False,
)
