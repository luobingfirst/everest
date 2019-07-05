#!/usr/bin/python

import sys
import inspect
import ast
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
    correctPar = False
    if (len(sys.argv)>=2):
        method = getattr(c, sys.argv[1], "Invalid method")
        if callable(method):
            if (len(sys.argv)>=3):
                args = []
                for sarg in sys.argv[2:]:
                    try:
                        arg = ast.literal_eval(sarg)
                    except (ValueError, SyntaxError):
                        arg = sarg
                    args.append(arg)
                #print(args)
                method(*args)
            else:
                method()
            correctPar = True
    if (not correctPar):
        help(sys.argv[0])
    del c

if __name__ == "__main__":
    main()
