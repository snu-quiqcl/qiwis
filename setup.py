"""
Set-up file for releasing this package.
"""

from setuptools import setup, find_packages
import sys

if sys.version_info[:2] < (3, 7):
    raise Exception("You need Python 3.7+")

setup(
    name='swift',
    version='1.0.0',
    packages=find_packages(include=['swift', 'swift.*']),
    install_requires=[
        'pyqt5'
    ]
)
