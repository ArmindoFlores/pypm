import curses
import threading
import time
import traceback

from .__main__ import (process_cpu_command, process_mem_command,
                       process_pid_command, process_stderr_command,
                       process_stdout_command, process_uptime_command)
from .units import Size, Time

CTRL_Z = 26
CTRL_C = 3
K_UP = 450
K_DOWN = 456
K_LEFT = 452
K_RIGHT = 454
K_RETURN = 10
K_ESCAPE = 27
K_SPACE = 32
DISPLAY = {
    "command": "Command",
    "pid": "PID",
    "mem": "Memory Usage",
    "cpu": "CPU Usage",
    "uptime": "Uptime"
}

def wrap(string, width):
    c = 0
    while c < len(string):
        yield string[c:c+width]
        c += width

def pad(string, size):
    return string[:size] + " "*max(0, size-len(string))

class App:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._processes = {}
        self._selected_proc = 0
        self._log_offset = 0
        self._log_mode = "stderr"
        self._proc_offset = 0
        self._selected = 0
        self._screen = None
        self._topleftwin = None
        self._toprightwin = None
        self._botrightwin = None
        self._should_update = {
            "topleft": False,
            "topright": False,
            "botright": False            
        }
        self.WHITE = None
        self.YELLOW = None
        self.GREEN = None
        self.BLUE = None
        self.SELECT = None
        self.RED = None
        
        self._stop = False
        
    def update_info(self):
        try:
            start = time.time()
            while not self._stop:
                if len(self._processes) > 0:
                    keys = list(self._processes.keys())
                    proc = keys[self._selected_proc]
                    if time.time()-start > 1:
                        mem = process_mem_command([proc], self._host, self._port)
                        if mem is None:
                            break
                        cpu = process_cpu_command([proc], self._host, self._port)
                        if cpu is None:
                            break
                        uptime = process_uptime_command([proc], self._host, self._port)
                        if uptime is None:
                            break
                        pid = process_pid_command([proc], self._host, self._port)
                        if pid is None:
                            break
                        stdout = process_stdout_command([proc], self._host, self._port)
                        stderr = process_stderr_command([proc], self._host, self._port)
                        self._processes[proc]["pid"] = pid[proc] if pid[proc] != -1 else "N/A"
                        self._processes[proc]["uptime"] = uptime[proc]
                        self._processes[proc]["mem"] = mem[proc]
                        self._processes[proc]["cpu"] = str(cpu[proc])+"%"
                        self._processes[proc]["logs"]["stdout"] = stdout
                        self._processes[proc]["logs"]["stderr"] = stderr
                        start = time.time()
                    self.schedule_update(["botright", "topright"])
        except Exception:
            traceback.print_exc()
            pass
        finally:
            self._stop = True
            
    def add_process(self, name, command):
        self._processes[name]={
            "command": command,
            "pid": "N/A",
            "uptime": "0s",
            "mem": "0.0B",
            "cpu": "0.0%",
            "logs": {
                "stdout": [],
                "stderr": []
            }
        }
        
    def schedule_update(self, screens=[]):
        if screens == []:
            self._should_update.update(
                zip(self._should_update.keys(), [True]*len(self._should_update))
            )
        else:
            self._should_update.update(
                zip(screens, [True]*len(screens))
            )
        
    def start(self):
        thread = threading.Thread(target=self.update_info)
        thread.setDaemon(True)
        thread.start()
        curses.wrapper(self.main_loop)
        
    def setup(self):
        if curses.LINES < 17 or curses.COLS < 54:
            print("Your terminal isn't big enough")
            return False
        curses.curs_set(False)
        self._screen.nodelay(True)
        lsize = (curses.LINES-1, curses.COLS//3)
        self._topleftwin = curses.newwin(*lsize, 0, 0)
        height = curses.LINES-9
        width = curses.COLS-lsize[1]
        self._toprightwin = curses.newwin(height, width, 0, lsize[1])
        self._botrightwin = curses.newwin(curses.LINES-height-1, width, height, lsize[1])
        
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        
        self.WHITE = curses.color_pair(1)
        self.GREEN = curses.color_pair(2)
        self.BLUE = curses.color_pair(3)
        self.SELECT = curses.color_pair(4)
        self.RED = curses.color_pair(5)
        self.YELLOW = curses.color_pair(6)
        return True
    
    def get_log_lines(self, ltype):
        max_x = self._toprightwin.getmaxyx()[1]-4
        keys = list(self._processes.keys())
        proc_name = keys[self._selected_proc]
        proc = self._processes[proc_name]
        c = 0
        for line in proc["logs"][ltype]:
            for sub in wrap(line, max_x):
                c += 1
        return c
        
    def update_topleftwin(self):
        self._topleftwin.clear()
        if self._selected == 0:
            self._topleftwin.attron(self.BLUE)
        self._topleftwin.box()
        self._topleftwin.attroff(self.BLUE)
        self._topleftwin.addstr(0, 2, " Process List ")
        max_y , max_x = self._topleftwin.getmaxyx()
        max_x -= 4
        max_y -= 4
        for i in range(len(self._processes)):
            if i-self._proc_offset < 0:
                continue
            if i-self._proc_offset >= max_y:
                break
            proc = list(self._processes.keys())[i]
            if i == self._selected_proc:
                self._topleftwin.attron(self.SELECT)
            self._topleftwin.addstr(2+i-self._proc_offset, 2, pad(proc, max_x))
            self._topleftwin.attroff(self.SELECT)
        if len(self._processes) != self._proc_offset+max_y:
            if len(self._processes) > max_y:
                self._topleftwin.attron(self.YELLOW)
                self._topleftwin.addstr(max_y+2, 2, "...".center(max_x))
                self._topleftwin.attroff(self.YELLOW)
        self._topleftwin.refresh()
        
    def update_toprightwin(self):
        self._toprightwin.clear()
        if self._selected == 1:
            self._toprightwin.attron(self.BLUE)
        self._toprightwin.box()
        self._toprightwin.attroff(self.BLUE)
        self._toprightwin.addstr(0, 2, f" Logs ({self._log_mode}) ")
        self._toprightwin.move(2, 0)
        max_y , max_x = self._toprightwin.getmaxyx()
        max_x -= 4
        max_y -= 3
        if len(self._processes) > 0:
            keys = list(self._processes.keys())
            proc_name = keys[self._selected_proc]
            proc = self._processes[proc_name]
            c = self.get_log_lines(self._log_mode)
            start = max(0, c-max_y)
            l = 2-start-self._log_offset
            for line in proc["logs"][self._log_mode]:
                for sub in wrap(line, max_x):
                    if l >= 2:
                        if "warning" in sub.lower():
                            self._toprightwin.attron(self.YELLOW)
                        elif "error" in sub.lower() or "critical" in sub.lower():
                            self._toprightwin.attron(self.RED)
                        self._toprightwin.addstr(l, 2, sub)
                        self._toprightwin.attroff(self.YELLOW|self.RED)
                    l += 1
                    if l > max_y:
                        break
                if l > max_y:
                    break
        self._toprightwin.refresh()
        
    def update_botrightwin(self):
        self._botrightwin.clear()
        if self._selected == 2:
            self._botrightwin.attron(self.BLUE)
        self._botrightwin.box()
        self._botrightwin.attroff(self.BLUE)
        self._botrightwin.addstr(0, 2, " Status: ")
        max_y , max_x = self._botrightwin.getmaxyx()
        max_x -= 4
        max_y -= 3
        if len(self._processes) > 0:
            keys = list(self._processes.keys())
            proc_name = keys[self._selected_proc]
            proc = self._processes[proc_name]
            if proc["pid"] == "N/A":
                self._botrightwin.attron(self.RED)
            else:
                self._botrightwin.attron(self.GREEN)
            self._botrightwin.addstr(0, 10, " ⬤ ")
            self._botrightwin.attroff(self.RED|self.GREEN)
            
            self._botrightwin.addstr(1, 2, f"Name: {pad(proc_name, max_x-5)}")
            for i in range(len(proc)-1):
                if i >= max_y:
                    break
                attr = list(proc.keys())[i]
                self._botrightwin.addstr(2+i, 2, f"{DISPLAY[attr]}: {proc[attr]}")
        self._botrightwin.refresh()
        
    def update_proc_offset(self):
        max_y = self._topleftwin.getmaxyx()[0]-4
        if len(self._processes) < max_y:
            self._proc_offset = 0
        else:
            if self._selected_proc-self._proc_offset >= max_y:
                self._proc_offset = self._selected_proc-max_y+1
            elif self._selected_proc == 0:
                self._proc_offset = 0
            elif self._selected_proc-self._proc_offset <= 0:
                self._proc_offset = self._selected_proc
        
    def main_loop(self, screen):
        self._screen = screen
        if not self.setup():
            return
        self._screen.clear()
        self._botrightwin.clear()
        self._toprightwin.clear()
        self._topleftwin.clear()
        string = "Press Ctrl+C to exit | Use [SPACE] to change log mode".center(curses.COLS-1)
        self._screen.addstr(curses.LINES-1, 0, string)
        self.schedule_update()
        
        while not self._stop:
            char = self._screen.getch()
            if char != -1:
                if char == CTRL_C or char == CTRL_Z:
                    break
                elif char == K_SPACE:
                    self._log_offset = 0
                    if self._selected == 1:
                        if self._log_mode == "stderr":
                            self._log_mode = "stdout"
                        else:
                            self._log_mode = "stderr"
                elif char == K_RIGHT or char == curses.KEY_RIGHT:
                    self._selected = (self._selected + 1)%3
                    self.schedule_update()
                elif char == K_LEFT or char == curses.KEY_LEFT:
                    self._selected = (self._selected - 1)%3
                    self.schedule_update()
                elif char == K_UP or char == curses.KEY_UP:
                    if self._selected == 0:
                        if len(self._processes) != 0:
                            self._selected_proc -= 1
                            self._selected_proc %= len(self._processes)
                            self.update_proc_offset()
                            self.schedule_update(["topleft"])
                    elif self._selected == 1:
                        if len(self._processes) != 0:
                            keys = list(self._processes.keys())
                            proc_name = keys[self._selected_proc]
                            proc = self._processes[proc_name]
                            lines = self.get_log_lines(self._log_mode)
                            max_y = self._toprightwin.getmaxyx()[0] - 3
                            if self._log_offset > -(lines - max_y):
                                self._log_offset -= 1
                                self.schedule_update(["topright"])
                elif char == K_DOWN or char == curses.KEY_DOWN:
                    if self._selected == 0:
                        if len(self._processes) != 0:
                            self._selected_proc += 1
                            self._selected_proc %= len(self._processes)
                            self.update_proc_offset()
                            self.schedule_update(["topleft"])
                    elif self._selected == 1:
                        if len(self._processes) != 0:
                            keys = list(self._processes.keys())
                            proc_name = keys[self._selected_proc]
                            proc = self._processes[proc_name]
                            lines = self.get_log_lines(self._log_mode)
                            if self._log_offset < 0:
                                self._log_offset += 1
                                self.schedule_update(["topright"])
                
            if self._should_update["topleft"]:
                self.update_topleftwin()
                self._should_update["topleft"] = False
            if self._should_update["topright"]:
                self.update_toprightwin()
                self._should_update["topright"] = False  
            if self._should_update["botright"]:
                self.update_botrightwin()
                self._should_update["botright"] = False  
                

if __name__ == "__main__":
    app = App()
    app.start()
