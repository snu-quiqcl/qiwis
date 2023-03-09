"""
Set-up file for releasing this package.
"""

from setuptools import setup, find_packages

setup(
    name='swift',
    version='1.0.0',
    packages=find_packages(include=['swift', 'swift.*']),
    install_requires=[
        'pyqt5'
    ]
)
