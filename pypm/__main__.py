import argparse
import struct
import socket

from . import constants as const
from .units import Size

commands = [
    "start",
    "stop",
    "add",
    "rem",
    "kill",
    "restart",
    "stats",
    "list"
]
commands.sort()

help_text = f"""\
Usage: python -m pypm CMD [OPTIONS]

Positional arguments:
    CMD             {', '.join(commands)}
    
For additional help use python -m pypm CMD --help
"""

def isdata(bytearr):
    return bytearr[0] == const.DATA_CODE[0]

def get_start_parser():
    parser = argparse.ArgumentParser(prog="python -m pypm")
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

def process_command(cmd, args, host, port):
    try:
        if cmd == "stop":
            if len(args) != 0:
                print("Error: this command takes no arguments")
                return
            process_stop_command(args, host, port)
        elif cmd == "add":
            if len(args) < 2:
                print("Error: Not enough arguments (need at least NAME and COMMAND)")
                return
            if len(args) > 4:
                print("Error: Too many arguments")
            process_add_command(args, host, port)
        elif cmd == "restart":
            if len(args) != 1:
                print("Error: Invalid number of arguments")
                return
            process_restart_command(args, host, port)
        elif cmd == "rem":
            if len(args) != 1:
                print("Error: Invalid number of arguments")
                return
            process_remove_command(args, host, port)
        elif cmd == "kill":
            if len(args) != 1:
                print("Error: Invalid number of arguments")
                return
            process_kill_command(args, host, port) 
        elif cmd == "stats":
            if len(args) != 1:
                print("Error: Invalid number of arguments")
                return
            mem = process_mem_command(args, host, port)
            if mem is not None:
                print(mem)
        elif cmd == "list":
            if len(args) != 0:
                print("Error: Invalid number of arguments")
                return
            process_list_command(args, host, port)
            
    except ConnectionRefusedError:
        print("Error: pypm is not running")
        
def process_list_command(args, host, port):
    resp = send_command(const.CMD_LIST, args, host, port)
    if isdata(resp):
        strings = resp[1:].decode("utf-8").split("\x00\x00")
        if strings == ['']:
            print("There are no processes being managed")
        else:
            names, procs = zip(*map(lambda l: l.split("\x00"), strings))
            for i in range(len(names)):
                print(f"* {names[i]} -> {procs[i]}")
    else:
        print(resp[1:].decode())    
        
def process_mem_command(args, host, port):
    resp = send_command(const.CMD_GET_MEMORY, args, host, port)
    if isdata(resp):
        size = Size(struct.unpack("d", resp[1:])[0])
        return size
    else:
        print(resp[1:].decode())
        return None
        
def process_stop_command(args, host, port):
    resp = send_command(const.CMD_STOP, args, host, port)
    print(resp[1:].decode())
        
def process_add_command(args, host, port):
    name, command = args[:2]
    log_cpu = args[2] if len(args) >= 3 else "False"
    log_freq = args[3] if len(args) == 4 else "False"
    resp = send_command(const.CMD_ADD_PROCESS, 
                        [name, command, log_cpu, log_freq], 
                        host, port)
    print(resp[1:].decode())
        
def process_restart_command(args, host, port):
    resp = send_command(const.CMD_RESTART_PROCESS, args, host, port)
    print(resp[1:].decode())
        
def process_kill_command(args, host, port):
    resp = send_command(const.CMD_KILL_PROCESS, args, host, port)
    print(resp[1:].decode())
        
def process_remove_command(args, host, port):
    resp = send_command(const.CMD_REMOVE_PROCESS, args, host, port)
    print(resp[1:].decode())

def send_command(cmd, args, host, port):
    string = ' '.join([cmd]+args)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    sock.sendall(string.encode("utf-8"))
    resp = sock.recv(2048)
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
        print(help_text)
        quit()
    
    if cmd == "start":
        argparser = get_start_parser()
        args, _ = argparser.parse_known_args()
        print(f"Starting process manager on port {args.port}...")
        try:
            main(args.port, args.logdir, args.logfreq)
        except socket.error:
            print("Error: this port is already in use")
        
        # pid = subprocess.Popen([sys.executable, 
        #                         "-m", 
        #                         "pypm.pypm", 
        #                         str(args.port), 
        #                         str(args.logdir), 
        #                         str(args.logfreq)],
        #         shell=False, stdin=None, stdout=None, stderr=None,
        #          close_fds=True, creationflags=0x00000008).pid
        # print(f"Started process manager on port {args.port} with the PID {pid}")
        
    elif cmd in commands:
        argparser = get_cmd_parser(cmd)
        args, _ = argparser.parse_known_args()
        for a in range(len(args.args)):
            arg = args.args[a]
            if " " in arg:
                args.args[a] = "'"+arg+"'"
        process_command(cmd, args.args, args.host, args.port)
    else:
        print(help_text)
