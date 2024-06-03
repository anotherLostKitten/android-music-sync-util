from os import listdir, get_terminal_size
from os.path import isfile, join, expanduser
from math import ceil
from termcolor import colored

SOURCE_PATH = "~/m/music"
MAX_NAME_LENGTH = 30

ELLIPSIS = "\u2026"
UNSELECT = colored("_", "white", "on_red", attrs=["bold"])
SELECT = colored("@", "white", "on_green", attrs=["bold"])

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
    tdim = get_terminal_size()
    a = (tdim[0] + 1) // (MAX_NAME_LENGTH + 2)
    pgl = a * (tdim[1] - 1)
    pgs = ceil(len(fs) / pgl)
    return (tdim, a, pgl, pgs)

def print_pg(fs, pos):
    tdim, a, pgl, pgs = calc_pg(fs)
    s = pos // pgl
    for fp in range(s * pgl, (s + 1) * pgl):
        f = fs[fp]
        fn = f if len(f) <= MAX_NAME_LENGTH else f[:MAX_NAME_LENGTH - 1] + ELLIPSIS
        spm = MAX_NAME_LENGTH - len(fn)
        if fp == pos:
            fn = colored(fn, "black", "on_white")
        if spm > 0:
            fn += " " * spm
        selr = UNSELECT
        print(selr + fn, end="\n" if fp % a == a - 1 else " ")
    print(f"{s+1} / {pgs}".rjust(tdim[0]), end="", flush=True)

def main(sp):
    fs = [f for f in listdir(sp) if not isfile(join(sp, f))]
    #print(fs)
    #print_histogram(fs)
    print(len([f for f in fs if len(f) > MAX_NAME_LENGTH]), "/", len(fs))
    print_pg(fs, 4)
    while True:
        pass



if __name__ == "__main__":
    main(expanduser(SOURCE_PATH))
