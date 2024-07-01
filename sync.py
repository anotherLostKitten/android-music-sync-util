import os
from os.path import isfile, isdir, ismount, join, expanduser, getmtime
import re
from math import ceil
from termcolor import colored
import termios
import tty
import sys
import json
import subprocess

SOURCE_PATH = expanduser("~/m/music")
SYNC_PATH = "./sync.json"
MOUNT_DIR = expanduser("~/android_mnt")
DEST_PATH = "Internal shared storage/Music/"

MAX_NAME_LENGTH = 30
SONG_REGEX = r"^.+\.mp3$"
SONG_METADATAS = ["artist", "date"]
GET_METADATAS = True

ELLIPSIS = "\u2026"
UNSELECT = " "
SELECT = colored("X", "white", "on_green", attrs=["bold"])
SEARCH_ICON = colored("?", "black", "on_white", attrs=["bold"])
SEARCH_LEFT = colored("<", "dark_grey", "on_light_grey", attrs=["bold"])
DIRS = ['up', 'down', 'right', 'left']

sync_ts = None

def load_sel(fs):
    sel = [False] * len(fs)
    ts = [None] * len(fs)
    try:
        with open(SYNC_PATH, "rt") as f:
            cache = json.loads(f.read())
            for (i, e) in enumerate(fs):
                if e in cache:
                    sel[i] = True
                    ts[i] = cache[e]
    except Exception as e:
        print("caught error reading sync data", e)
    global sync_ts
    sync_ts = ts
    return sel

def get_modified_ts(fn):
    try:
        return max(getmtime(join(fn, sn)) for sn in os.listdir(fn)
                   if isfile(join(fn, sn)) and re.match(SONG_REGEX, sn))
    except Exception as e:
        print(f"caught error getting last modified time for album {fn}:\n\t{e}")
        return None

def print_progress_indicator(done_count, done_total):
    print(f"\r{done_count:03} / {done_total:03}", end="", flush=True)

def sync(fs, sel):
    global sync_ts
    to_del = []
    to_add = []
    to_upd = []
    save_dict = {}
    for (i, e) in enumerate(sel):
        if not e and sync_ts[i]:
            to_del.append(i)
        elif e:
            ts = get_modified_ts(join(SOURCE_PATH, fs[i]))
            save_dict[fs[i]] = ts
            if not sync_ts[i]:
                to_add.append(i)
            elif sync_ts[i] != ts:
                to_upd.append(i)

    print(f"to_del({len(to_del)}): {[fs[i] for i in to_del]}\nto_add({len(to_add)}): {[fs[i] for i in to_add]}\nto_upd({len(to_upd)}): {[fs[i] for i in to_upd]}")

    done_count = 0
    done_total = len(to_del) + len(to_add) + len(to_upd)
    print_progress_indicator(done_count, done_total)

    try:
        if not ismount(MOUNT_DIR):
            subprocess.run(["aft-mtp-mount", MOUNT_DIR], check=True)
        dest = join(MOUNT_DIR, DEST_PATH)
        for i in to_del:
            if os.path.exists(join(dest, fs[i])):
                subprocess.run(["rm", "-rf", join(dest, fs[i])], check=True)
            done_count += 1
            print(f"\r{done_count:03} / {done_total:03}", end="", flush=True)
            sync_ts[i] = None
        for i in to_add + to_upd:
            if isdir(join(dest, fs[i])):
                subprocess.run(["rm", "-rf", f"{join(dest, fs[i])}/*"], check=True)
            else:
                subprocess.run(["mkdir", join(dest, fs[i])], check=True)
            fn = join(SOURCE_PATH, fs[i])
            for sn in os.listdir(fn):
                if isfile(join(fn, sn)) and re.match(SONG_REGEX, sn):
                    subprocess.run(["cp", join(fn, sn), f"{join(dest, fs[i])}/"], check=True)
            done_count += 1
            print_progress_indicator(done_count, done_total)
            sync_ts[i] = save_dict[fs[i]]

    except Exception as e:
        print("\nerror syncing", e)
    print("")

    if done_count < done_total:
        print("rolling back", done_total - done_count)
        if done_count < len(to_del):
            for i in range(done_total - done_count - len(to_add) - len(to_upd)):
                save_dict[fs[to_del[-1-i]]] = sync_ts[to_del[-1-i]]
        else:
            all_todos = to_add + to_upd
            for i in range(done_total - done_count):
                del save_dict[fs[all_todos[-1-i]]]
    try:
        with open(SYNC_PATH, "wt") as f:
            f.write(json.dumps(save_dict))
            return done_count == done_total
    except Exception as e:
        print("caught error writing sync data", e)
        return False

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

def print_pg(fs, searfs, pos, sel, sear, metas):
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
    sl = 2 * (MAX_NAME_LENGTH + 2)
    ss = SEARCH_ICON + sear if len(sear) < sl else SEARCH_LEFT + sear[-sl + 1:]
    tags = ""
    if searfs and metas:
        tags = f"{'; '.join(metas[searfs[cpos]])}   "
    pgmk = f"{tags}{s+1} / {pgs}"
    spm = tdim[0] - min(len(sear), sl - 1) - len(pgmk) - 1
    out += ss + " " * spm + pgmk
    os.system("clear")
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

def get_album_metadata(fn, print_progress_length = None):
    dat = None
    fnp = join(SOURCE_PATH, fn)
    for sn in os.listdir(fnp):
        if isfile(join(fnp, sn)) and re.match(SONG_REGEX, sn):
            try_dat = get_song_metadata(join(fnp, sn), SONG_METADATAS)
            if len(try_dat) == len(SONG_METADATAS):
                dat = tuple(try_dat)
                break
    if print_progress_length:
        print_progress_indicator(*print_progress_length)
    return dat

def get_song_metadata(file_name, tags):
    res = subprocess.run(["ffprobe", "-show_entries", f"format_tags={','.join(tags)}", "-of", "compact=p=0:nk=1", "-loglevel", "error", "-i", file_name], check=True, capture_output = True, text = True)
    return res.stdout.strip().split("|")

def change_pos(searfs, pos, dpos):
    pos = closest_pos(searfs, pos) + dpos
    if pos >= len(searfs):
        pos = len(searfs) - 1
    if pos < 0:
        pos = 0
    return searfs[pos] if len(searfs) > 0 else -1

def main():
    fs = [fn for fn in os.listdir(SOURCE_PATH) if isdir(join(SOURCE_PATH, fn))]
    fs.sort(key=str.lower)
    metas = None
    if GET_METADATAS:
        metas = [get_album_metadata(fn, (i, len(fs))) for i, fn in enumerate(fs)]
    sel = load_sel(fs)
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

            print_pg(fs, searfs, pos, sel, sear, metas)

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
            elif k == "\t":
                pos = change_pos(searfs, pos, 0)
                if pos > 0:
                    sel[pos] = not sel[pos]
            elif k == "\b" or ord(k) == 127:
                if len(sear) > 0:
                    sear = sear[:-1]
            elif k == "\n":
                os.system("clear")
                success = sync(fs, sel)
                if not success and input("continue? [y/N]").lower() == "y":
                    continue
                os.system('stty sane')
                quit()
            else:
                sear += k

    except (KeyboardInterrupt, SystemExit):
        os.system('stty sane')
        quit()



if __name__ == "__main__":
    main()
