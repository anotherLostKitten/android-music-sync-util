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
UNSELECT = " "
SELECT = colored("X", "white", "on_green", attrs=["bold"])
SEARCH_ICON = colored("?", "black", "on_white", attrs=["bold"])
SEARCH_LEFT = colored("<", "dark_grey", "on_light_grey", attrs=["bold"])
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

def calc_pg(fsl):
    tdim = os.get_terminal_size()
    a = (tdim[0] + 1) // (MAX_NAME_LENGTH + 2)
    pgl = a * (tdim[1] - 1)
    pgs = ceil(fsl / pgl)
    return (tdim, a, pgl, pgs)

def closest_pos(searfs, pos):
    oldpos = -1
    for (i, e) in enumerate(searfs):
        if e == pos:
            return i
        if e > pos:
            return oldpos if oldpos > 0 else i
        oldpos = i
    return oldpos

def print_pg(fs, searfs, pos, sel, sear):
    tdim, a, pgl, pgs = calc_pg(len(searfs))
    cpos = closest_pos(searfs, pos)
    s = cpos // pgl
    out = ""
    for fp in range(s * pgl, (s + 1) * pgl):
        if fp >= len(searfs) or fp < 0:
            out += " " * (MAX_NAME_LENGTH + 1) + ("\n" if fp % a == a - 1 else " ")
            continue
        f = fs[searfs[fp]]

        out += SELECT if sel[searfs[fp]] else UNSELECT

        fn = f if len(f) <= MAX_NAME_LENGTH else f[:MAX_NAME_LENGTH - 1] + ELLIPSIS
        spm = MAX_NAME_LENGTH - len(fn)
        if fp == cpos:
            fn = colored(fn, "black", "on_white")
        out += fn
        if spm > 0:
            out += " " * spm

        out += "\n" if fp % a == a - 1 else " "
    os.system("clear")
    sl = 2 * (MAX_NAME_LENGTH + 2)
    ss = SEARCH_ICON + sear if len(sear) < sl else SEARCH_LEFT + sear[-sl + 1:]
    pgmk = f"{s+1} / {pgs}"
    spm = tdim[0] - min(len(sear), sl - 1) - len(pgmk) - 1
    out += ss + " " * spm + pgmk
    print(out, end="", flush=True)

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

def change_pos(searfs, pos, dpos):
    pos = closest_pos(searfs, pos) + dpos
    if pos >= len(searfs):
        pos = len(searfs) - 1
    if pos < 0:
        pos = 0
    return searfs[pos] if len(searfs) > 0 else -1

def main(sp):
    fs = [f for f in os.listdir(sp) if not isfile(join(sp, f))]
    fs.sort(key=str.lower)
    sel = [False] * len(fs) # TODO
    #print(fs)
    #print_histogram(fs)
    #print(len([f for f in fs if len(f) > MAX_NAME_LENGTH]), "/", len(fs))
    sear = ""
    pos = 0
    try:
        while True:
            searfs = [i for (i, f) in enumerate(fs) if sear.lower() in f.lower()]

            if pos >= len(fs):
                pos = len(fs) - 1
            if pos < 0:
                pos = 0

            print_pg(fs, searfs, pos, sel, sear)

            k = get_key()
            tdim, a, pgl, pgs = calc_pg(len(searfs))
            if k == DIRS[0]:
                pos = change_pos(searfs, pos, -a)
            elif k == DIRS[1]:
                pos = change_pos(searfs, pos, a)
            elif k == DIRS[2]:
                pos = change_pos(searfs, pos, 1)
            elif k == DIRS[3]:
                pos = change_pos(searfs, pos, -1)
            elif k == ">":
                pos = change_pos(searfs, pos, pgl)
            elif k == "<":
                pos = change_pos(searfs, pos, -pgl)
            elif k == "\n":
                pos = change_pos(searfs, pos, 0)
                if pos > 0:
                    sel[pos] = not sel[pos]
            elif k == "\b" or ord(k) == 127:
                if len(sear) > 0:
                    sear = sear[:-1]
            else:
                sear += k

    except (KeyboardInterrupt, SystemExit):
        os.system('stty sane')
        quit()



if __name__ == "__main__":
    main(expanduser(SOURCE_PATH))
