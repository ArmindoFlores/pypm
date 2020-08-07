import os
import select
import shlex
import socket
import struct
import threading
import time

from . import constants as const
from .process import Process


def sbool(string):
    return True if string == "True" else False


class ProcessManager:
    def __init__(self, port=8080, log_dir=None, log_frequency=30):
        self.port = port
        # if log_dir is not None:
        #     if os.path.isabs(log_dir):
        #         self.log_dir = log_dir
        #     else:
        #         self.log_dir = os.path.join(os.path.dirname(__file__), log_dir)
        #     if not os.path.isdir(self.log_dir):
        #         raise FileNotFoundError(f"Log directory wasn't found ({self.log_dir})")
        # else:
        #     self.log_dir = None
        self.log_dir = log_dir
        self.log_frequency = log_frequency
        self._processes = []
        self._log_cpu = []
        self._log_memory = []
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_thread = None
        self._stop = False
        
    def add_process(self, process, log_cpu=False, log_memory=False):
        if process in self._processes:
            return False
        self._processes.append(process)
        if log_cpu and process not in self._log_cpu:
            self._log_cpu.append(process)
        if log_memory and process not in self._log_memory:
            self._log_memory.append(process) 
        return True
            
    def rem_process(self, process):
        self._processes.remove(process)
        if process in self._log_cpu:
            self._log_cpu.remove(process)
        if process in self._log_memory:
            self._log_memory.remove(process)
            
    def assert_logdir_exists(self):
        if self.log_dir is None:
            raise ValueError("Log directory wasn't specified")
        if not os.path.isdir(self.log_dir):
            os.mkdir(self.log_dir)
            
    def log_process_cpu(self, process):
        self.assert_logdir_exists()
        log_file = os.path.join(self.log_dir, process.name)
        with open(log_file+"_log_cpu", "ab") as file:
            file.write(struct.pack("d", process.get_cpu_perc()))
            
    def log_process_memory(self, process):
        self.assert_logdir_exists()
        log_file = os.path.join(self.log_dir, process.name)
        with open(log_file+"_log_mem", "ab") as file:
            file.write(struct.pack("d", process.get_mem_usage().bytes))
            
    def _process_command(self, command, sock):
        command = shlex.split(command)
        if len(command) == 0:
            sock.sendall(const.MSG_CODE+b"Error: Unrecognized command")  
        elif command[0] == const.CMD_GET_MEMORY:
            self._process_get_mem_cmd(command, sock)
        elif command[0] == const.CMD_GET_CPU:
            self._process_get_cpu_cmd(command, sock)
        elif command[0] == const.CMD_GET_PID:
            self._process_get_pid_cmd(command, sock)
        elif command[0] == const.CMD_GET_UPTIME:
            self._process_get_uptime_cmd(command, sock)
        elif command[0] == const.CMD_ADD_PROCESS:
            self._process_command_add_proc(command, sock)
        elif command[0] == const.CMD_RESTART_PROCESS:
            self._process_command_restart_proc(command, sock)
        elif command[0] == const.CMD_START_PROCESS:
            self._process_command_start_proc(command, sock)
        elif command[0] == const.CMD_STOP:
            self._process_command_stop(command, sock)
        elif command[0] == const.CMD_REMOVE_PROCESS:
            self._process_command_rem_proc(command, sock)
        elif command[0] == const.CMD_KILL_PROCESS:
            self._process_command_kill_proc(command, sock)
        elif command[0] == const.CMD_LIST:
            self._process_list_cmd(command, sock)
        else:
            sock.sendall(const.MSG_CODE+b"Error: Unrecognized command")  
            
    def _process_list_cmd(self, command, sock):
        try:
            if len(command) == 1:
                ldata = lambda p: p.name + "\x00" + p.command
                data = '\x00\x00'.join(map(ldata, self._processes)).encode("utf-8")
                sock.sendall(const.DATA_CODE+data)
            else:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't get process list")
            
    def _process_get_uptime_cmd(self, command, sock):
        try:
            if 1 <= len(command) <= 2:
                if len(command) == 2:
                    name = command[1]
                    uptime = None
                    for process in self._processes:
                        if process.name == name:
                            uptime = str(process.uptime)
                            break 
                    if uptime is None:
                        sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                    else:
                        sock.sendall(const.DATA_CODE+name.encode()+b"\x00"+uptime.encode()+b"\x00")
                else:
                    uptime = []
                    for process in self._processes:
                        uptime.append((process.name, str(process.uptime)))
                    message = []
                    for up in uptime:
                        message.append(up[0].encode()+b"\x00"+up[1].encode()+b"\x00")
                    sock.sendall(const.DATA_CODE+b"".join(message))
            else:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't get process uptime")
            
    def _process_get_mem_cmd(self, command, sock):
        try:
            if 1 <= len(command) <= 2:
                if len(command) == 2:
                    name = command[1]
                    memory = None
                    for process in self._processes:
                        if process.name == name:
                            memory = process.get_mem_usage().bytes   
                            break 
                    if memory is None:
                        sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                    else:
                        sock.sendall(const.DATA_CODE+name.encode()+b"\x00"+struct.pack("d", memory))
                else:
                    memory = []
                    for process in self._processes:
                        memory.append((process.name, process.get_mem_usage().bytes))
                    message = []
                    for mem in memory:
                        message.append(mem[0].encode()+b"\x00"+struct.pack("d", mem[1]))
                    sock.sendall(const.DATA_CODE+b"".join(message))
            else:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't get process memory usage")
            
    def _process_get_pid_cmd(self, command, sock):
        try:
            if 1 <= len(command) <= 2:
                if len(command) == 2:
                    name = command[1]
                    pid = None
                    for process in self._processes:
                        if process.name == name:
                            pid = process.pid  
                            break 
                    if pid is None:
                        sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                    else:
                        sock.sendall(const.DATA_CODE+name.encode()+b"\x00"+struct.pack("i", pid))
                else:
                    pid = []
                    for process in self._processes:
                        pid.append((process.name, process.pid))
                    message = []
                    for p in pid:
                        message.append(p[0].encode()+b"\x00"+struct.pack("i", p[1]))
                    sock.sendall(const.DATA_CODE+b"".join(message))
            else:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't get process PID")
            
    def _process_get_cpu_cmd(self, command, sock):
        try:
            if 1 <= len(command) <= 2:
                if len(command) == 2:
                    name = command[1]
                    cpu = None
                    for process in self._processes:
                        if process.name == name:
                            cpu = process.get_cpu_perc()   
                            break 
                    if cpu is None:
                        sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                    else:
                        sock.sendall(const.DATA_CODE+name.encode()+b"\x00"+struct.pack("d", cpu))
                else:
                    cpu = []
                    for process in self._processes:
                        cpu.append((process.name, process.get_cpu_perc()))
                    message = []
                    for c in cpu:
                        message.append(c[0].encode()+b"\x00"+struct.pack("d", c[1]))
                    sock.sendall(const.DATA_CODE+b"".join(message))
            else:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't get process CPU usage")
            
    def _process_command_add_proc(self, command, sock):
        try:
            if len(command) == 5:
                name, cmd, log_cpu, log_freq = command[1:]
                process = Process(name, cmd)
                if self.add_process(process, sbool(log_cpu), sbool(log_freq)):
                    sock.sendall(const.MSG_CODE+b"Successfully added process '" + name.encode() + b"'")
                else:
                    sock.sendall(const.MSG_CODE+b"Error: There is already a process named '" + name.encode() + b"'")
            else:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't add process")
            
    def _process_command_restart_proc(self, command, sock):
        try:
            if len(command) != 2:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
                return
            name = command[1]
            process = None
            for proc in self._processes:
                if proc.name == name:
                    process = proc
                    break 
            if process is None:
                sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                return
            if process.active:
                process.kill()
            process.start()
            sock.sendall(const.MSG_CODE+b"Successfully restarted process '" + name.encode() + b"'")
            
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't restart process")
    
    def _process_command_start_proc(self, command, sock):
        try:
            if not (1 <= len(command) <= 2):
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
                return
            if len(command) == 2:
                name = command[1]
                process = None
                for proc in self._processes:
                    if proc.name == name:
                        process = proc
                        break 
                if process is None:
                    sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                    return
                if process.active:
                    sock.sendall(const.MSG_CODE+b"Warning: Process was already running, so nothing was done")
                else:
                    process.start()
                    sock.sendall(const.MSG_CODE+b"Successfully started process '" + name.encode() + b"'")
            else:
                if len(self._processes) == 0:
                    sock.sendall(const.MSG_CODE+b"Warning: No processes to start")
                    return
                c = 0
                for process in self._processes:
                    if not process.active:
                        c += 1
                        process.start()
                if c == 0:
                    sock.sendall(const.MSG_CODE+b"Warning: No processes were started")
                else:
                    total = str(c).encode()
                    length = str(len(self._processes)).encode()
                    sock.sendall(const.MSG_CODE+b"Started " + total + b" out of " + length + b" processes")
                
        except Exception as e:
            print(e)
            sock.sendall(const.MSG_CODE+b"Error: Couldn't start process")
            
    def _process_command_rem_proc(self, command, sock):
        try:
            if len(command) != 2:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
                return
            name = command[1]
            process = None
            for proc in self._processes:
                if proc.name == name:
                    process = proc
                    break 
            if process is None:
                sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                return
            if process.active:
                process.kill()
            self.rem_process(process)
            sock.sendall(const.MSG_CODE+b"Successfully removed process '" + name.encode() + b"'")
            
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't remove process")
            
    def _process_command_kill_proc(self, command, sock):
        try:
            if len(command) != 2:
                sock.sendall(const.MSG_CODE+b"Error: Invalid number of arguments")
                return
            name = command[1]
            process = None
            for proc in self._processes:
                if proc.name == name:
                    process = proc
                    break 
            if process is None:
                sock.sendall(const.MSG_CODE+b"Error: Couldn't find process '" + name.encode() + b"'")
                return
            if process.active:
                process.kill()
                sock.sendall(const.MSG_CODE+b"Successfully killed process '" + name.encode() + b"'")
            else:
                sock.sendall(const.MSG_CODE+b"Error: Process '" + name.encode() + b"' is not active")
            
        except Exception:
            sock.sendall(const.MSG_CODE+b"Error: Couldn't kill process")
            
    def _process_command_stop(self, command, sock):
        host = socket.gethostname().encode()
        port = str(self.port).encode()
        sock.sendall(const.MSG_CODE+b"Stopped pypm running on " + host + b":" + port)
        self._stop = True
        
    @property
    def has_active_processes(self):
        return len(list(filter(lambda p: p.active, self._processes))) >= 1
    
    @property
    def log_period(self):
        return 60 / self.log_frequency
    
    def start(self):
        self._socket.bind(("localhost", self.port))
        for process in self._processes:
            process.start()
        self.main_loop()
        
    def server_loop(self):
        self._socket.listen()
        while not self._stop:
            sock, _ = self._socket.accept()
            command = sock.recv(2048).decode("utf-8")
            self._process_command(command, sock)
            sock.close()
        
    def main_loop(self):
        try:
            start = time.time()
            self._server_thread = threading.Thread(target=self.server_loop)
            # self._server_thread.setDaemon(True)
            self._server_thread.start()
            while not self._stop:
                if time.time() - start > self.log_period:
                    start = time.time()
                    for process in self._log_memory:
                        self.log_process_memory(process)
                    for process in self._log_cpu:
                        self.log_process_cpu(process)  
        except KeyboardInterrupt:    
            pass
        finally:
            self._stop = True
            
            # In case the server_loop hasn't stopped yet, prevent
            # socket.accept() for hanging
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.setblocking(0)
                s.settimeout(0.5)
                s.connect(("localhost", self.port))
                s.sendall(b" ")
                ready = select.select([s], [], [], 0.6)  # See if data is available
                if ready[0]:
                    s.recv(1024)
                s.close()
            except:
                pass
            
            self._socket.close()
            for process in self._processes:
                if process.active:
                    process.kill()
