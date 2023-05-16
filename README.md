<p align="center">
  <img width="40%" alt="image" src="https://user-images.githubusercontent.com/65724072/235589514-ed021c0c-cf20-4ba1-b8af-3b1d0da65362.svg">
</p>

[![Pylint](https://github.com/snu-quiqcl/qiwis/actions/workflows/pylint.yml/badge.svg)](https://github.com/snu-quiqcl/qiwis/actions/workflows/pylint.yml)

[![unittest](https://github.com/snu-quiqcl/qiwis/actions/workflows/unittest.yml/badge.svg)](https://github.com/snu-quiqcl/qiwis/actions/workflows/unittest.yml)

# qiwis
QIWIS (**Q**u**I**qcl **W**idget **I**ntegration **S**oftware) is a framework for integration of PyQt widgets where they can communicate with each other. This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.

## How to download and install
One of the below:
- Using released version (_recommended_)
1. `pip install git_https://github.com/snu-quiqcl/qiwis.git@v2.0.0`

- Using git directly
1. `git clone ${url}`: The default branch is `develop`, not `main`. There is no guarantee for stability.
2. In the repository, `pip install -e .`

## How to use
In the repository, just do like as below:

`python -m qiwis (-s ${setup_file))`.
