import datetime
import subprocess
import tempfile
import threading

import psutil

from .units import Size, Time


class Process:
    def __init__(self, name, command):
        self.max_buff_size = 100
        self.name = name
        self._command = command
        self._process = None
        self._start = Time(0)
        self._cpu_usage = 0
        self._thread = None
        self._outstream = None
        self._errstream = None
        self._outbuff = []
        self._errbuff = []
        
    def __eq__(self, other):
        return isinstance(other, Process) and other.name == self.name
        
    def start(self, pipe=False):
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
            
    @property
    def stdout(self):
        return self._outbuff
    
    @property
    def stderr(self):
        return self._errbuff
            
    def process_stdout(self):
        new = self.get_stdout().decode()
        if new != "":
            self._outbuff = self._outbuff + new.split("\n")
        while len(self._outbuff) > self.max_buff_size:
            self._outbuff.pop(0)
            
    def process_stderr(self):
        new = self.get_stderr().decode()
        if new != "":
            self._errbuff = self._errbuff + new.split("\n")  
        while len(self._errbuff) > self.max_buff_size:
            self._errbuff.pop(0)
        
    def get_stdout(self):
        self._outstream.flush()
        self._outstream.seek(0)
        r = self._outstream.read()
        if b"\n" in r:
            nl = r.rindex(b"\n")
            self._outstream.truncate(0)
            self._outstream.write(r[nl+1:])
            return r[:nl]
        else:
            return b""
    
    def get_stderr(self):
        self._errstream.flush()
        self._errstream.seek(0)
        r = self._errstream.read()
        if b"\n" in r:
            nl = r.rindex(b"\n")
            self._errstream.truncate(0)
            self._errstream.write(r[nl+1:])
            return r[:nl]
        else:
            return b""
        
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
