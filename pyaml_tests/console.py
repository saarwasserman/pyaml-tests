import os
import py
import sys

from pathlib import Path

def main():
    args_str = " ".join(sys.argv[1:])
    home_dir = Path.home()
    file_path = os.path.dirname(os.path.abspath(__file__))
    testspath = file_path

    # future feature work against queues
    use_queue = "--queue" in args_str
    if use_queue:
        test_name = "test_using_queue --queue"
    else:
        test_name = "test"

    py.test.cmdline.main(f"{testspath}/test.py::{test_name} --rootdir={file_path} --confcutdir {file_path}".split(" ") + args_str.split(" "))


if __name__ == "__main__":
    main()
