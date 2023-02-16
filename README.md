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

## Structure chart
### Overall structure
<img width="80%" alt="image" src="https://user-images.githubusercontent.com/76851886/219294678-f93f729d-684b-4668-8094-9ae90680c817.png">

### Frame structure
<img width="50%" alt="image" src="https://user-images.githubusercontent.com/76851886/219294817-c135dad4-bf7a-49f3-a33b-16b3bc632ca7.png">
