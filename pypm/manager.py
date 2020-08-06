import os
import shlex
import socket
import struct
import threading
import time

from .constants import *
from .process import Process


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
        if process not in self._processes:
            self._processes.append(process)
        if log_cpu and process not in self._log_cpu:
            self._log_cpu.append(process)
        if log_memory and process not in self._log_memory:
            self._log_memory.append(process) 
            
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
            raise FileNotFoundError(f"Log directory wasn't found ({self.log_dir})")
            
    def log_process_cpu(self, process):
        self.assert_logdir_exists()
        log_file = os.path.join(self.log_dir, process.name)
        with open(log_file+"_log_cpu", "ab") as file:
            file.write(struct.pack("f", process.get_cpu_perc()))
            
    def log_process_memory(self, process):
        self.assert_logdir_exists()
        log_file = os.path.join(self.log_dir, process.name)
        with open(log_file+"_log_mem", "ab") as file:
            file.write(struct.pack("d", process.get_memory_usage()))
            
    def _process_command(self, command, sock):
        command = shlex.split(command)
        if command[0] == CMD_GET_MEMORY:
            self._process_get_mem_cmd(command, sock)
        elif command[0] == CMD_ADD_PROCESS:
            self._process_command_add_proc(command, sock)
        elif command[0] == CMD_STOP:
            self._process_command_stop(command, sock)
        else:
            sock.sendall(ERR_INVALID_CMD.encode())    
            
    def _process_get_mem_cmd(self, command, sock):
        try:
            if len(command) == 2:
                name = command[1]
                memory = None
                for process in self._processes:
                    if process.name == name:
                        memory = process.get_memory_usage().bytes    
                if memory is None:
                    sock.sendall(ERR_PROC_NOT_FOUND.encode())
                else:
                    sock.sendall(struct.pack("d", memory))
            else:
                sock.sendall(ERR_INVALID_CMD.encode())
        except:
            sock.sendall(ERR_INVALID_CMD.encode())
            
    def _process_command_add_proc(self, command, sock):
        try:
            if len(command) == 5:
                name, cmd, log_cpu, log_freq = command[1:]
                process = Process(name, cmd)
                self.add_process(process, bool(log_cpu), bool(log_freq))
            else:
                sock.sendall(ERR_INVALID_CMD.encode())
        except Exception:
            sock.sendall(ERR_INVALID_CMD.encode())
            
    def _process_command_stop(self, command, sock):
        sock.sendall(MSG_ACK.encode())
        self._stop = True
        
    @property
    def has_active_processes(self):
        return len(list(filter(lambda p: p.is_alive, self._processes))) >= 1
    
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
        while True:
            sock, _ = self._socket.accept()
            command = sock.recv(2048).decode("utf-8")
            self._process_command(command, sock)
            sock.close()
        
    def main_loop(self):
        start = time.time()
        self._server_thread = threading.Thread(target=self.server_loop)
        self._server_thread.setDaemon(True)
        self._server_thread.start()
        while not self._stop:
            if time.time() - start > self.log_period:
                for process in self._log_memory:
                    self.log_process_memory(process)
                for process in self._log_cpu:
                    self.log_process_cpu(process)      
        self._socket.close()  
