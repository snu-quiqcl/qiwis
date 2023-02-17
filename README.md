[![Pylint](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml/badge.svg)](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml)

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

A `Frame` simply means a window of PyQt that we see.

In fact, an engine which makes a `Frame` works is a `Logic`.
A `Logic` can 
- show/hide `Frame`s, which the `Logic` manages
- set a slot for each signal of `Frame`
- receive a signal which the `Frame` emits
- emit a signal to `Frame` or a global signal to `swift`
- communicate `backend` APIs

A `swift` recognizes only `Logic`, not `Frame` or `backend`. Thus, every order for `Frame` is implemented in `Logic`.

A `backend` is a set of APIs for handling UI-independent operations, such as controlling hardwards, polling something, and connecting DB.


# Toy example applications
Several toy example applications are provided to demonstrate the basic features of `swift`.

## 1. Random number generator
### GUI - generator frame
- A combobox for selecting a database into which the generated number is saved
- A button for generating new number
### GUI - viewer frame
- A label for showing the current status (database updated, random number generated, etc.)
- A read-only spinbox showing the recently generated number
### Backend
- `generate() -> int`: Generate a random number and return it
- `save(num: int) -> bool`: Save the given number into the database

## 2. Logger
### GUI
- A read-only text field that prints out the log messages
### Backend
Not required.

## 3. Poller
### GUI
- A spinbox for adjusting the polling period
- A label for showing the polled count (how many numbers have been polled): this will confidently show when the polling occurs
- A read-only spinbox showing the recently polled number
### Backend
- `poll() -> int`: Return a predictable number e.g. `time.time() % 100`
- `save(num: int) -> bool`: Save the given number into the database

## 4. Database manager
### GUI
- A list whose each row shows the database name, information (host address, etc.), and a button to remove the row from the list
- Line-edit(s) and a button to add a row (new database)
### Backend
Not required.

## 5. Data calculator
### GUI
- A combobox for selecting the database from which the value of 'A' is fetched
- A combobox for selecting the database from which the value of 'B' is fetched
- A label showing the sum of recently fetched 'A' and 'B', or an error message if something goes wrong
### Backend
- `read_from(db) -> int`: Read the given database and return the fetched number
