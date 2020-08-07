from math import log2


class Size:
    def __init__(self, value):
        """"Represents the size of an object

        Args:
            value (int): value in bytes
        """
        
        self._bytes = value
        
    def __repr__(self):
        if self._bytes == 0:
            i = 0
        else:
            i = int(log2(self.bytes)/10)
        if i == 0:
            return f"{round(self.bytes, 1)}B"
        elif i == 1:
            return f"{round(self.kbytes, 1)}KB"
        elif i == 2:
            return f"{round(self.mbytes, 1)}MB"
        else:
            return f"{round(self.gbytes, 1)}GB"
        
    @property
    def bytes(self):
        return self._bytes
    
    @property
    def kbytes(self):
        return self.bytes / 2**10
    
    @property
    def mbytes(self):
        return self.kbytes / 2**10
    
    @property
    def gbytes(self):
        return self.mbytes / 2**10
    
    
class Time:
    def __init__(self, value):
        """Represents a measure of time

        Args:
            value (datetime.timedelta): Time object
        """
        
        self._value = value
        
    def __repr__(self):
        if self._value == 0:
            return "0s"
        if self.years > 0.5:
            return f"{round(self.years)}Y"
        elif self.months > 0.5:
            return f"{round(self.months)}M"
        elif self.days > 0:
            return f"{self.days}D"
        elif self.hours > 0.5:
            return f"{round(self.hours)}h"
        elif self.minutes > 0.5:
            return f"{round(self.minutes)}m"
        else:
            return f"{round(self.seconds)}s"
        
    @property
    def seconds(self):
        return self._value.total_seconds()
    
    @property 
    def minutes(self):
        return self.seconds / 60
    
    @property
    def hours(self):
        return self.minutes / 60
    
    @property
    def days(self):
        if hasattr(self._value, "days"):
            return self._value.days
        return 0
    
    @property
    def months(self):
        return self.days / 30.417
    
    @property
    def years(self):
        return self.days / 365.25
