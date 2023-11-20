"""
Set-up file for releasing this package.
"""

import sys
from setuptools import setup

if sys.version_info[:2] < (3, 8):
    print("You need Python 3.8+")
    sys.exit()

setup(
    name="qiwis",
    version="3.0.0",
    author="QuIQCL",
    author_email="kangz12345@snu.ac.kr",
    url="https://github.com/snu-quiqcl/qiwis",
    description="QuIqcl Widget Integration Software",
    long_description=
        "A framework for integration of PyQt widgets where they can communicate with each other. "
        "This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.",
    download_url="https://github.com/snu-quiqcl/qiwis/releases/tag/v3.0.0",
    license="MIT license",
    install_requires=["pyqt5"],
    py_modules=["qiwis"],
    entry_points={
        "console_scripts": ["qiwis = qiwis:main"]
    }
)
