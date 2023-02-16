# swift
**S**NU **w**idget **i**ntegration **f**ramework for PyQ**t**

A framework for integration of PyQt widgets where they can communicate with each other.
This project is mainly developed for trapped ion experiment controller GUI in SNU QuIQCL.

`swift` provides a dashboard-like main window, in which variety of `Frame`s reside.
A `Frame` is in fact a special `QWidget` which obeys the interface of `swift`, and it will be wrapped by a `QDockWidget`.

## Features
- Independent development of each `Frame`, which is a sub-window application resides in the framework
- Communication channel between `Frame`s
- Thread-safety
