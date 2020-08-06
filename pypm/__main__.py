import argparse

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", 
                        type=int, 
                        default=8080, 
                        help="Network port")
    parser.add_argument("--logdir", 
                        type=str, 
                        default=None, 
                        help="Logging directory")
    parser.add_argument("--logfreq", 
                        type=int, 
                        default=30, 
                        help="Logging frequency (per minute)")
    return parser
    
if __name__ == "__main__":
    import subprocess
    import sys
     
    #  pid = subprocess.Popen([sys.executable, "-m", "pypm.pypm"], shell=False,
    #          stdin=None, stdout=None, stderr=None, close_fds=True, creationflags=0x00000008).pid
    #  print(f"Started process manager on port 8080 with the PID {pid}")
    from .pypm import main
    argparser = get_parser()
    args, _ = argparser.parse_known_args()
    print(f"Starting process manager on port {args.port}...")
    main(args.port, args.logdir, args.logfreq)