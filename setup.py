"""
Set-up file for releasing this package.
"""

from setuptools import setup, find_packages
import sys

if sys.version_info[:2] < (3, 7):
    raise Exception("You need Python 3.7+")

setup(
    name="swift",
    version="2.0.0",  # indicate the following version
    author="QuIQCL",
    author_email="kangz12345@snu.ac.kr",
    url="https://github.com/snu-quiqcl/swift",
    description="SNU widget integration framework for PyQt",
    long_description="A framework for integration of PyQt widgets where they can communicate with each other. "
                     "This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.",
    download_url="https://github.com/snu-quiqcl/swift/releases/tag/v2.0.0",  # indicate the url of the following release
    license="MIT license"
    install_requires=["pyqt5"]
    packages=find_packages(include=["swift", "swift.*"]),
)
