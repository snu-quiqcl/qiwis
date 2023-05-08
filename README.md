<p align="center">
  <img width="40%" alt="image" src="https://user-images.githubusercontent.com/65724072/235589514-ed021c0c-cf20-4ba1-b8af-3b1d0da65362.svg">
</p>

[![Pylint](https://github.com/snu-quiqcl/qiwi/actions/workflows/pylint.yml/badge.svg)](https://github.com/snu-quiqcl/qiwi/actions/workflows/pylint.yml)

[![unittest](https://github.com/snu-quiqcl/qiwi/actions/workflows/unittest.yml/badge.svg)](https://github.com/snu-quiqcl/qiwi/actions/workflows/unittest.yml)

# QIWI
QIWI (**S**NU **w**idget **i**ntegration **f**ramework for PyQ**t**) is a framework for integration of PyQt widgets where they can communicate with each other. This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.

## How to download and install
One of the below:
- Using released version (_recommended_)
1. `pip install git_https://github.com/snu-quiqcl/qiwi.git@v1.0.1`

- Using git directly
1. `git clone ${url}`: The default branch is `develop`, not `main`. There is no guarantee for stability.
2. In the repository, `pip install -e .`

## How to use
In the repository, just do like as below:

`python -m qiwi (-s ${setup_file))`.
