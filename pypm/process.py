import datetime
import subprocess

import psutil

from .units import Size, Time


class Process:
    def __init__(self, name, command):
        self.name = name
        self._command = command
        self._process = None
        self._start = Time(0)
        
    def __eq__(self, other):
        return isinstance(other, Process) and other.name == self.name
        
    def start(self):
        self._start = datetime.datetime.now()
        self._process = subprocess.Popen(self._command.split())
        
    def kill(self):
        self._start = Time(0)
        self._process.kill()
        
    @property
    def command(self):
        return self._command
        
    @property
    def active(self):
        if self._process is None:
            return False
        return self._process.poll() is None
    
    @property 
    def pid(self):
        if self.active:
            return self._process.pid
        return -1
    
    @property
    def uptime(self):
        if self.active:
            return Time(datetime.datetime.now()-self._start)
        else:
            return Time(0)
    
    def get_mem_usage(self):
        if self.active:
            return Size(psutil.Process(self.pid).memory_info().vms)
        else:
            return Size(0)
    
    def get_mem_perc(self):
        if self.active:
            return psutil.Process(self.pid).memory_percent("vms")
        else:
            return 0
    
    def get_cpu_perc(self):
        if self.active:
            return psutil.Process(self.pid).cpu_percent() / psutil.cpu_count()
        else:
            return 0
