import curses


class App:
    def __init__(self):
        self._selected = 0
        self._screen = None
        self._leftwin = None
        self._rightwin = None
        self._should_update = {
            "left": False,
            "right": False,
        }
        self.WHITE = None
        self.GREEN = None
        self.BLUE = None
        self.CYAN = None
        self.RED = None
        
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
        curses.wrapper(self.main_loop)
        
    def setup(self):
        curses.curs_set(False)
        self._screen.nodelay(True)
        lsize = (curses.LINES, curses.COLS//3)
        self._leftwin = curses.newwin(*lsize, 0, 0)
        self._rightwin = curses.newwin(curses.LINES, curses.COLS-lsize[1], 0, lsize[1])
        
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
        
        self.WHITE = curses.color_pair(1)
        self.GREEN = curses.color_pair(2)
        self.BLUE = curses.color_pair(3)
        self.CYAN = curses.color_pair(4)
        self.RED = curses.color_pair(5)    
        
    def update_leftwin(self):
        self._leftwin.attron(self.BLUE)
        self._leftwin.box()
        self._leftwin.attroff(self.BLUE)
        self._leftwin.addstr(0, 2, " Process List ")
        self._leftwin.refresh()
        
    def update_rightwin(self):
        self._rightwin.box()
        self._rightwin.refresh()
        
    def main_loop(self, screen):
        self._screen = screen
        self.setup()
        self._screen.clear()
        
        self.schedule_update()
        
        while True:
            char = self._screen.getch()
            if char != curses.ERR:
                break
            
            if self._should_update["left"]:
                self.update_leftwin()
                self._should_update["left"] = False
            if self._should_update["right"]:
                self.update_rightwin()
                self._should_update["right"] = False  
                

if __name__ == "__main__":
    app = App()
    app.start()