import argparse
import os
import socket
import struct
import sys

import termtables as tt
from colorama import Fore, Style

from . import constants as const
from .process import Process
from .units import Size

DEBUG = os.environ.get("PYPMDEBUG")
if DEBUG is None: DEBUG = False
else: DEBUG = True

commands = [
    "init",
    "start",
    "stop",
    "add",
    "rem",
    "kill",
    "restart",
    "status",
    "list",
    "start",
    "monit"
]
commands.sort()

help_text = f"""\
Usage: python -m pypm CMD [OPTIONS]

Positional arguments:
    CMD             {', '.join(commands)}
    
For additional help use python -m pypm CMD --help
"""

def color(text, color):
    """Adds color to given text."""
    return f"{color}{text}{Style.RESET_ALL}"

def isdata(bytearr):
    """Returns True if the given data is an encoded string or binary data"""
    return bytearr[0] == const.DATA_CODE[0]

def get_start_parser():
    parser = argparse.ArgumentParser(prog="python -m pypm init")
    parser.add_argument("--port", 
                        type=int, 
                        default=8080, 
                        help="Network port")
    parser.add_argument("--logdir", 
                        type=str, 
                        default="logs", 
                        help="Logging directory")
    parser.add_argument("--logfreq", 
                        type=int, 
                        default=30, 
                        help="Logging frequency (per minute)")
    return parser

def get_cmd_parser(cmd):
    parser = argparse.ArgumentParser(prog="python -m pypm", 
                                     usage=f"usage: python -m pypm {cmd} \
[-h] [--port PORT] [--host HOST] [ARGS [ARGS ...]]")
    parser.add_argument("args",
                        metavar="ARGS",
                        nargs="*",
                        help="Command arguments")
    parser.add_argument("--port", 
                        type=int, 
                        default=8080, 
                        help="Network port")
    parser.add_argument("--host", 
                        type=str, 
                        default="localhost", 
                        help="Host")
    return parser

def print_msg(text):
    """Prints the given text, coloring it based on the first word"""
    if text.startswith("Error:"):
        print(color(text, Fore.RED))
    elif text.startswith("Warning:"):
        print(color(text, Fore.YELLOW))
    else:
        print(text)

def process_command(cmd, args, host, port):
    """Processes a given command

    Args:
        cmd (str): Command
        args (list): List of command arguments
        host (str): Remote host to connect to
        port (int): Network port
    """
    try:
        if cmd == "stop":
            if len(args) != 0:
                print_msg("Error: this command takes no arguments")
                return
            process_stop_command(args, host, port)
        elif cmd == "add":
            if len(args) < 2:
                print_msg("Error: Not enough arguments (need at least NAME and COMMAND)")
                return
            if len(args) > 4:
                print_msg("Error: Too many arguments")
            process_add_command(args, host, port)
        elif cmd == "start":
            if len(args) > 1:
                print_msg("Error: Invalid number of arguments")
                return
            process_start_command(args, host, port)
        elif cmd == "restart":
            if len(args) > 1:
                print_msg("Error: Invalid number of arguments")
                return
            process_restart_command(args, host, port)
        elif cmd == "rem":
            if len(args) != 1:
                print_msg("Error: Invalid number of arguments")
                return
            process_remove_command(args, host, port)
        elif cmd == "kill":
            if len(args) != 1:
                print_msg("Error: Invalid number of arguments")
                return
            process_kill_command(args, host, port) 
        elif cmd == "status":
            if len(args) > 1:
                print_msg("Error: Invalid number of arguments")
                return
            process_status_command(args, host, port)     
        elif cmd == "list":
            if len(args) != 0:
                print_msg("Error: Invalid number of arguments")
                return
            process_list_command(args, host, port)
        elif cmd == "monit":
            if len(args) != 0:
                print_msg("Error: Invalid number of arguments")
                return
            process_monit_command(args, host, port)
            
    except ConnectionRefusedError:
        print_msg("Error: pypm is not running")
        
def process_monit_command(args, host, port):
    from .monit import App
    resp = send_command(const.CMD_LIST, args, host, port)
    if isdata(resp):
        strings = resp[1:].decode("utf-8").split("\x00\x00")
        if strings == ['']:
            total = None
        else:
            total = map(lambda l: l.split("\x00"), strings)
    app = App(host, port)
    if total is not None:
        for name, proc in total:
            app.add_process(name, proc)
    app.start()
        
def process_status_command(args, host, port):
    """Prints the status table for a given process/list of processes"""
    mem = process_mem_command(args, host, port)
    if mem is None:
        return
    if len(mem) == 0:
        print_msg("Warning: There are no processes being managed")
        return
    cpu = process_cpu_command(args, host, port)
    if cpu is None:
        return
    pid = process_pid_command(args, host, port)
    if pid is None:
        return
    uptime = process_uptime_command(args, host, port)
    if uptime is None:
        return
        
    lines = []
    for name in mem:
        memory = mem[name]
        if name in pid:
            active = f"{Fore.GREEN}active{Style.RESET_ALL}"
            p = pid[name]
            if p == -1:
                p = "N/A"
                active = f"{Fore.RED}stopped{Style.RESET_ALL}"
        else:
            p = "N/A"
            active = "N/A"
        if name in cpu:
            c = str(cpu[name])+"%"
        else:
            c = "N/A"
        if name in uptime:
            up = uptime[name]
        else:
            up = "N/A"
        
        lines.append([name, p, memory, c, up, active])
        
    header = ["Name", "PID", "Mem.", "CPU", "Uptime", "Status"]
    table = tt.to_string(
        lines,
        header=list(map(lambda c: color(c, Fore.CYAN), header)),
    )
    print(table)
        
def process_list_command(args, host, port):
    """List all managed processes"""
    resp = send_command(const.CMD_LIST, args, host, port)
    if isdata(resp):
        strings = resp[1:].decode("utf-8").split("\x00\x00")
        if strings == ['']:
            print_msg("Warning: There are no processes being managed")
        else:
            names, procs = zip(*map(lambda l: l.split("\x00"), strings))
            for i in range(len(names)):
                print_msg(f"* {names[i]} -> {procs[i]}")
    else:
        print_msg(resp[1:].decode())    
        
def process_mem_command(args, host, port):
    """Get the memory usage of a specific process/list of processes"""
    resp = send_command(const.CMD_GET_MEMORY, args, host, port)
    if isdata(resp):
        values = {}
        i = 0
        while i+1 < len(resp) and b"\x00" in resp[1+i:]:
            end = resp[1+i:].index(b"\x00")+1
            name = resp[1+i:i+end].decode()
            value = Size(struct.unpack("d", resp[1+i+end:i+end+9])[0])
            values[name] = value
            i += end+8
        return values
    else:
        print_msg(resp[1:].decode())
        return None
    
def process_cpu_command(args, host, port):
    """Get the cpu usage of a specific process/list of processes"""
    resp = send_command(const.CMD_GET_CPU, args, host, port)
    if isdata(resp):
        values = {}
        i = 0
        while i+1 < len(resp) and b"\x00" in resp[1+i:]:
            end = resp[1+i:].index(b"\x00")+1
            name = resp[1+i:i+end].decode()
            value = struct.unpack("d", resp[1+i+end:i+end+9])[0]
            values[name] = value
            i += end+8
        return values
    else:
        print_msg(resp[1:].decode())
        return None
    
def process_pid_command(args, host, port):
    """Get the PID of a specific process/list of processes"""
    resp = send_command(const.CMD_GET_PID, args, host, port)
    if isdata(resp):
        values = {}
        i = 0
        while i+1 < len(resp) and b"\x00" in resp[1+i:]:
            end = resp[1+i:].index(b"\x00")+1
            name = resp[1+i:i+end].decode()
            value = struct.unpack("i", resp[1+i+end:i+end+5])[0]
            values[name] = value
            i += end+4
        return values
    else:
        print_msg(resp[1:].decode())
        return None
    
def process_uptime_command(args, host, port):
    """Get the uptime of a specific process/list of processes"""
    resp = send_command(const.CMD_GET_UPTIME, args, host, port)
    if isdata(resp):
        values = {}
        i = 0
        while i+1 < len(resp) and b"\x00" in resp[1+i:]:
            end = resp[1+i:].index(b"\x00")+1
            name = resp[1+i:i+end].decode()
            i += end
            end = resp[1+i:].index(b"\x00")+1
            value = resp[1+i:i+end].decode()
            values[name] = value
            i += end
        return values
    else:
        print_msg(resp[1:].decode())
        return None
    
def process_stdout_command(args, host, port):
    """Gets the last 100 lines of output from the process"""
    resp = send_command(const.CMD_GET_STDOUT, args, host, port)
    if isdata(resp):
        return resp[1:].decode().split("\n")
    else:
        print_msg(resp[1:].decode())
        
def process_stderr_command(args, host, port):
    """Gets the last 100 lines of output from the process"""
    resp = send_command(const.CMD_GET_STDERR, args, host, port)
    if isdata(resp):
        return resp[1:].decode().split("\n")
    else:
        print_msg(resp[1:].decode())
        
def process_stop_command(args, host, port):
    """Closes the pypm server running on the given host"""
    resp = send_command(const.CMD_STOP, args, host, port)
    print_msg(resp[1:].decode())
        
def process_add_command(args, host, port):
    """Adds a new process to be managed"""
    name, command = args[:2]
    log_cpu = args[2] if len(args) >= 3 else "False"
    log_freq = args[3] if len(args) == 4 else "False"
    dir_ = '"'+os.path.abspath(os.curdir)+'"'
    resp = send_command(const.CMD_ADD_PROCESS, 
                        [name, command, log_cpu, log_freq, dir_], 
                        host, port)
    print_msg(resp[1:].decode())
        
def process_restart_command(args, host, port):
    """Restarts a given process/list of processes"""
    resp = send_command(const.CMD_RESTART_PROCESS, args, host, port)
    print_msg(resp[1:].decode())
    
def process_start_command(args, host, port):
    """Starts a specific process/list of processes"""
    resp = send_command(const.CMD_START_PROCESS, args, host, port)
    print_msg(resp[1:].decode())
        
def process_kill_command(args, host, port):
    """Stops a specific process/list of processes"""
    resp = send_command(const.CMD_KILL_PROCESS, args, host, port)
    print_msg(resp[1:].decode())
        
def process_remove_command(args, host, port):
    """Removes (and stops) a process"""
    resp = send_command(const.CMD_REMOVE_PROCESS, args, host, port)
    print_msg(resp[1:].decode())

def send_command(cmd, args, host, port):
    string = ' '.join([cmd]+args)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.sendall(string.encode("utf-8"))
    resp = b""
    while True:
        data = sock.recv(2048)
        if data == b"":
            break
        resp += data
        if len(data) < 2048:
            break
    sock.close()
    return resp
    
if __name__ == "__main__":
    import subprocess
    import sys
    
    from .pypm import main
    
    
    if len(sys.argv) >= 2:
        cmd = sys.argv[1]
        sys.argv.pop(1)
    else:
        print_msg(help_text)
        quit()
    
    if cmd == "init":
        
        argparser = get_start_parser()
        args, _ = argparser.parse_known_args()
        print_msg(f"Starting process manager on port {args.port}...")
        
        # ! This is only for debugging purposes. It makes it so the start 
        # ! command hangs and prints all output to the terminal window 
        # ! where it was called from
        if DEBUG:
            try:
                main(args.port, args.logdir, args.logfreq)
            except socket.error:
                print_msg("Error: this port is already in use")
                quit()
        
        # * This is the actual production code
        else:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(("127.0.0.1", args.port))
                if result == 0:
                    print_msg("Error: this port is already in use")
                    quit()
            except socket.error:
                print_msg("Error: this port is already in use")
                quit()
        
            kwargs = {
                "shell": False,
                "stdin": None,
                "stdout": None,
                "stderr": None,
                "close_fds": True
            }
            if sys.platform == "win32":
                kwargs["creationflags"] = 0x00000008
                
            pid = subprocess.Popen([sys.executable, 
                                    "-m", 
                                    "pypm.pypm", 
                                    str(args.port), 
                                    str(args.logdir), 
                                    str(args.logfreq)],
                    **kwargs).pid
            print_msg(f"Started process manager on port {args.port} with the PID {pid}")
        
    elif cmd in commands:
        argparser = get_cmd_parser(cmd)
        args, _ = argparser.parse_known_args()
        for a in range(len(args.args)):
            arg = args.args[a]
            if " " in arg:
                args.args[a] = "'"+arg+"'"
        process_command(cmd, args.args, args.host, args.port)
    else:
        print_msg(help_text)
