import subprocess

import psutil

from .units import Size


class Process:
    def __init__(self, name, command):
        self.name = name
        self._command = command
        self._process = None
        
    def __eq__(self, other):
        return isinstance(other, Process) and other.name == self.name
        
    def start(self):
        self._process = subprocess.Popen(self._command.split())
        
    def kill(self):
        self._process.kill()
        
    @property
    def active(self):
        return self._process.poll() is None
    
    @property 
    def pid(self):
        return self._process.pid
    
    def get_mem_usage(self):
        return Size(psutil.Process(self.pid).memory_info().rss)
    
    def get_mem_perc(self):
        return psutil.Process(self.pid).memory_percent()
    
    def get_cpu_perc(self):
        return psutil.Process(self.pid).cpu_percent() / psutil.cpu_count()
    
