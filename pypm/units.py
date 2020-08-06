from math import log2


class Size:
    def __init__(self, value):
        """"Represents the size of an object

        Args:
            value (int): value in bytes
        """
        
        self._bytes = value
        
    def __repr__(self):
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
    
        