#!/usr/bin/python

import sys
import inspect
from cmd import cmd

def help(shellname):
    print("Command shell for kubernetes/istio traffic control.")
    print("usage: " + shellname + " <command name> [<args>*]")
    print("commands:")
    method_list = [func for func in dir(cmd) if callable(getattr(cmd, func)) and not func.startswith("__")]
    for methodname in method_list:
        method = getattr(cmd, methodname)
        a = inspect.getargspec(method)
        print("    " + methodname + ", "),
        print(a)

def main():
    c = cmd()
    if (len(sys.argv)>=2):
        method = getattr(c, sys.argv[1], "Invalid method")
        if callable(method):
            if (len(sys.argv)>=3):
                method(*sys.argv[2:])
            else:
                method()
        else:
            help(sys.argv[0])
    else:
        help(sys.argv[0])
    del c

if __name__ == "__main__":
    main()
