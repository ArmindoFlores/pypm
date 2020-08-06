import sys

from .manager import ProcessManager


def main(port=8080, log_dir=None, log_freq=30):
    pm = ProcessManager(port=port, log_dir=log_dir, log_frequency=log_freq)
    pm.start()

if __name__ == "__main__":
    main()