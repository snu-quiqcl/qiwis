[![Pylint](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml/badge.svg)](https://github.com/snu-quiqcl/swift/actions/workflows/pylint.yml)

[![unittest](https://github.com/snu-quiqcl/swift/actions/workflows/unittest.yml/badge.svg)](https://github.com/snu-quiqcl/swift/actions/workflows/unittest.yml)

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
<img width="80%" alt="image" src="https://user-images.githubusercontent.com/76851886/219574551-2f798863-ea48-4857-8db6-15840a0505e5.png">

```python
class Swift:
    """
    1. Read json set-up files
        - App information file  (e.g. whether to show frames at the beginning, which bus the app subscribes to)
        - Bus information file  (e.g. name, timeout)
    
    2. Create an instance of each bus
        - set a slot of received signal to router method

    3. Create an instance of each app
        - Set a slot of broadcast signal to router method
        
    4. Show frames of each app
    """
    pass


class Bus:
    received = pyqtSignal(...)
    
    def __init__():
         queue = []  # Queue for storing signals
         # Start thread for popping from queue and emitting signal to frames
         
    # Method when called when a frame emits a broadcast signal
    def write(msg):
        queue.push(msg)
        
    # Method polling until queue is empty
    def poll():
        while True:
            if queue is not empty:
                msg = queue.pop()
                received.emit(msg)
    

class App:
    broadcastRequested = pyqtSignal(...)
    received = pyqtSignal(...)
    
    def frames():
        # return frames to show
```

### App structure
<img width="50%" alt="image" src="https://user-images.githubusercontent.com/76851886/220836255-055aab3f-d65c-4809-9024-34fb2122a933.png">

A `Frame` simply means a window of PyQt that we see.

In fact, an engine which makes a `Frame` works is a `App`.
A `App` can 
- show/hide `Frame`s, which the `App` manages
- set a slot for each signal of `Frame`
- receive a signal which the `Frame` emits
- emit a signal to `Frame` or a global signal to `swift`
- communicate `backend` APIs

A `swift` recognizes only `App`, not `Frame` or `backend`. Thus, every order for `Frame` is implemented in `App`.

A `backend` is a set of APIs for handling UI-independent operations, such as controlling hardwards, polling something, and connecting DB.

```python
class App(BaseApp):
    """
    1. Create frames (generally only one frame)
         
    2. Connect signal of frame elements to API of App
    """
    
    # Method returning frames for showing
    def frames():
        return [...]
    
    # Example method that receive signal of frame elements
    def receive(...):
        # If necessary, start thread
        # Communicate with backend
        pass


class Frame(QWidget):
    pass
```

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
- `save(num: int, db) -> bool`: Save the given number into the database

## 2. Logger
### GUI
- A read-only text field that prints out the log messages
### Backend
Not required.

## 3. Poller
### GUI
- A combobox for selecting a database into which the polled number is saved
- A spinbox for adjusting the polling period
- A label for showing the polled count (how many numbers have been polled): this will confidently show when the polling occurs
- A read-only spinbox showing the recently polled number
### Backend
- `poll() -> int`: Return a predictable number e.g. `time.time() % 100`
- `save(num: int, db) -> bool`: Save the given number into the database

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
- `read(db) -> int`: Read the given database and return the fetched number
