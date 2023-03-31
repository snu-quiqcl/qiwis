[![Pylint](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml/badge.svg)](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml)

[![unittest](https://github.com/snu-quiqcl/swift/actions/workflows/unittest.yml/badge.svg)](https://github.com/snu-quiqcl/swift/actions/workflows/unittest.yml)

# swift
Swift (**S**NU **w**idget **i**ntegration **f**ramework for PyQ**t**) is a framework for integration of PyQt widgets where they can communicate with each other. This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.

## How to download and install
One of the below:
- Using released version (_recommended_)
1. `pip install git_https://github.com/snu-quiqcl/swift.git@v1.0.1`

- Using git directly
1. `git clone ${url}`: The default branch is `develop`, not `main`. There is no guarantee for stability.
2. In the repository, `pip install -e .`

## How to use
In the repository, just do like as below:

`python -m swift.swift (-s ${setup_file))`.
