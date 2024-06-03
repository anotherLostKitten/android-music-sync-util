import os
from os.path import isfile, join, expanduser
from math import ceil
from termcolor import colored
import termios
import tty
import sys


SOURCE_PATH = "~/m/music"
MAX_NAME_LENGTH = 30

ELLIPSIS = "\u2026"
UNSELECT = colored("_", "white", "on_red", attrs=["bold"])
SELECT = colored("@", "white", "on_green", attrs=["bold"])
DIRS = ['up', 'down', 'right', 'left']

def print_histogram(fs):
    mflen = max(len(f) for f in fs)
    histo = [0] * mflen
    for f in fs:
        histo[len(f) - 1] += 1
    mh = max(histo)
    mhd = len(str(mh))
    for r in range(mhd-1, -1, -1):
        for c in range(len(histo)):
            v = str(c + 1)
            print(v[len(v) - r - 1] if len(v) > r else " ", end="")
        print("")
    for r in range(mh):
        for c in range(len(histo)):
            print("*" if histo[c] > r else " ", end="")
        print("")

def calc_pg(fs):
    tdim = os.get_terminal_size()
    a = (tdim[0] + 1) // (MAX_NAME_LENGTH + 2)
    pgl = a * (tdim[1] - 1)
    pgs = ceil(len(fs) / pgl)
    return (tdim, a, pgl, pgs)

def print_pg(fs, pos):
    tdim, a, pgl, pgs = calc_pg(fs)
    s = pos // pgl
    out = ""
    for fp in range(s * pgl, (s + 1) * pgl):
        if fp >= len(fs):
            out += " " * (MAX_NAME_LENGTH + 1) + ("\n" if fp % a == a - 1 else " ")
            continue
        f = fs[fp]

        selr = UNSELECT
        out += selr

        fn = f if len(f) <= MAX_NAME_LENGTH else f[:MAX_NAME_LENGTH - 1] + ELLIPSIS
        spm = MAX_NAME_LENGTH - len(fn)
        if fp == pos:
            fn = colored(fn, "black", "on_white")
        out += fn
        if spm > 0:
            out += " " * spm

        out += "\n" if fp % a == a - 1 else " "
    os.system("clear")
    print(out + f"{s+1} / {pgs}".rjust(tdim[0]), end="", flush=True)

def get_key():
    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    try:
        b = os.read(sys.stdin.fileno(), 6).decode()
        if len(b) == 3:
            return DIRS[ord(b[2]) - 65]
        elif len(b) == 6:
            return DIRS[ord(b[5]) - 65]
        return b
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def main(sp):
    fs = [f for f in os.listdir(sp) if not isfile(join(sp, f))]
    #print(fs)
    #print_histogram(fs)
    print(len([f for f in fs if len(f) > MAX_NAME_LENGTH]), "/", len(fs))
    pos = 0
    try:
        while True:
            if pos < 0:
                pos = 0
            elif pos >= len(fs):
                pos = len(fs - 1)
            print_pg(fs, pos)
            k = get_key()
            tdim, a, pgl, pgs = calc_pg(fs)
            if k == DIRS[0]:
                pos -= a
            elif k == DIRS[1]:
                pos += a
            elif k == DIRS[2]:
                pos += 1
            elif k == DIRS[3]:
                pos -= 1
    except (KeyboardInterrupt, SystemExit):
        os.system('stty sane')
        quit()



if __name__ == "__main__":
    main(expanduser(SOURCE_PATH))
