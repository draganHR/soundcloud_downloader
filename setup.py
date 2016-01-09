#!/usr/bin/env python

import os
import re
from codecs import open

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

packages = [
    'soundcloud_downloader',
]


def get_version(package):
    """
    Return version from `__init__.py`.
    """
    module = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"](.+?)['\"]", module).group(1)


requires = [
    'requests>=2.9.0',
]


with open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

setup(
    name='soundcloud_downloader',
    version=get_version('soundcloud_downloader'),
    description='Soundcloud Downloader',
    long_description=readme,
    author='Dragan Bosnjak',
    author_email='draganHR@gmail.com',
    packages=packages,
    zip_safe=False,
    classifiers=(
        'Topic :: Utilities',
    ),
    install_requires=requires,
    entry_points={
        'console_scripts': [
            'soundcloud-downloader = soundcloud_downloader:main',
        ]
    }
)
