# pypm: A python-based process manager

## 💻 What is pypm?

pypm is a simple, python-based process manager. You can launch and monitor processes and their resources, automatically detect changes and log outputs. It keeps running after you close the console, which is very useful when dealing with remote sessions (for example, through `ssh`).


## 📥 How do I install it?

You can install pypm via pip with `pip install py-pm`


## 📖 How do I use it?
### Basic use

To start a pypm instance, use the command `python -m pypm init`. For more info about this command, you can use `python -m pypm init --help`. This starts a server on your local machine which can be interacted with through the other commands.
The next thing you're going to want to do is add a process to be monitored. You can use `python -m pypm add [name] [command]`. An example would be `python -m pypm add server "python -m http.server 80"`, which would launch an HTTP server.
To list all current processes, use `python -m pypm list`. To get the status of a specific process you can call `python -m pypm status [name]`, which will display a table like the one below.

![table](https://imgur.com/QBeGfoC.png "Table")

Killing processes is done using the `kill` instruction. All other options are listed on the help menu. Stopping the pypm instance will kill all running processes. There is a simple visual interface available with the command `python -m pypm monit`.

![monit](https://imgur.com/j9beUPF.png "Monitoring")

On Linux it might be useful to add `alias pypm="python3 -m pypm"` to your bash profile so the command syntax becomes simpler.
