import datetime
import os
import subprocess
import tempfile
import threading

import psutil

from .units import Size, Time


class Process:
    def __init__(self, name, command, dir="."):
        self.max_buff_size = 10000
        self.name = name
        self._command = command
        self._process = None
        self._start = Time(0)
        self._cpu_usage = 0
        self._thread = None
        self._outstream = None
        self._errstream = None
        self._outbuff = b""
        self._errbuff = b""
        self._dir = dir
        print(self._dir)
        
    def __eq__(self, other):
        return isinstance(other, Process) and other.name == self.name
        
    def start(self, pipe=False):
        previous = os.path.abspath(os.curdir)
        os.chdir(self._dir)
        if self.active:
            raise OSError("Process is already running")
        self._start = datetime.datetime.now()
        if pipe:
            self._outstream = tempfile.TemporaryFile()
            self._errstream = tempfile.TemporaryFile()
            self._process = subprocess.Popen(self._command.split(),
                                             stdout=self._outstream,
                                             stderr=self._errstream)
        else:
            self._process = subprocess.Popen(self._command.split())
        os.chdir(previous)
            
    @property
    def stdout(self):
        return self._outbuff
    
    @property
    def stderr(self):
        return self._errbuff
            
    def process_stdout(self):
        new = self.get_stdout().replace(b"\x00", b"")
        self._outbuff += new
        start = max(0, len(self._outbuff)-self.max_buff_size)
        self._outbuff = self._outbuff[start:]
            
    def process_stderr(self):
        new = self.get_stderr().replace(b"\x00", b"")
        self._errbuff += new
        start = max(0, len(self._errbuff)-self.max_buff_size)
        self._errbuff = self._errbuff[start:]
        
    def get_stdout(self):
        self._outstream.flush()
        self._outstream.seek(0)
        r = self._outstream.read()
        self._outstream.truncate(0)
        return r
    
    def get_stderr(self):
        self._errstream.flush()
        self._errstream.seek(0)
        r = self._errstream.read()
        self._errstream.truncate(0)
        return r
        
    def kill(self):
        self._start = Time(0)
        self._process.kill()
        self._outstream.close()
        self._errstream.close()
        
    def update_cpu(self):
        try:
            self._cpu_usage = psutil.Process(self.pid).cpu_percent(0.5) / psutil.cpu_count()
        except psutil.NoSuchProcess:
            pass
        
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
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self.update_cpu)
                self._thread.setDaemon(True)
                self._thread.start()
            return self._cpu_usage
        else:
            return 0
