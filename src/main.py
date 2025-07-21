import subprocess
import sys

def main():
    # Forward all arguments to the master script
    args = [sys.executable, '-m', 'distributed.master'] + sys.argv[1:]
    subprocess.run(args)

if __name__ == '__main__':
    main()