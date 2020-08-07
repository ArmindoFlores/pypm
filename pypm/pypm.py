import sys

from .manager import ProcessManager


def main(port=8080, log_dir=None, log_freq=30):
    if log_dir == "None":
        log_dir = None
    pm = ProcessManager(port=port, log_dir=log_dir, log_frequency=log_freq)
    pm.start()
    
if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], float(sys.argv[3]))