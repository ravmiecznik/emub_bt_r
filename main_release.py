from main import main
import sys, os
from setup_emubt import LOG_PATH

if __name__ == "__main__":
    _stdout = sys.stdout
    _stderr = sys.stderr
    with open(os.path.join(LOG_PATH, 'stdout.txt'), 'w', buffering=16) as stdout, open(
            os.path.join(LOG_PATH, 'stderr.txt'), 'w', buffering=16) as stderr:
        sys.stdout = stdout
        sys.stderr = stderr
        main(dev_version=False)