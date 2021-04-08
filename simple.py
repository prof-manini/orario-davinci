# -*- coding: utf-8 -*-

import os
from collections import defaultdict
import logging
info = logging.info
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s: %(message)s")

def file_to_rows(file, skip_first_line=True):
    """Read FILE, split on semicolons."""
    info(f"Reading '{file}'")
    start = 1 if skip_first_line else 0
    data = open(file).readlines()[start:]
    rows = [s.split(";") for s in data]
    info(f"Read {len(rows)} lines")
    return rows

def fix_prof(surname, name):
    ss = surname.split(",")
    if len(ss) > 1:
        surname = ss[0].strip()
        name = name.split(",")[0].strip()
    surname = surname.replace("e'", "è")
    return surname, name

def fix_room(room):
    try:
        k = room.split("(")[0]
        return k
        r = k.split(")")[1]
        return f"{room} === {k} --- {r}"
    except IndexError as e:
        raise Exception(f"{room = } {k = } {e}")

def fix_class(klass):
    klass = klass.strip("sa")
    if not "[" in klass:
        return [klass]
    klass = klass.strip("[]").split()[0]
    o = klass[0]
    ss = klass[1:].split("/")
    return [o + s for s in ss]

def calc_summaries(rows, prof_set, klass_set, room_set, mat_dic):
    """Collect selected fields from ROWS and fill given collections"""
    info("Calculating summaries")
    multi_class = 0
    for r in rows:

        (num, duration, freq,
         mat_cod, mat_name,
         prof_surname, prof_name,
         klass,
         room,
         _period, _spec, _co_doc, _coeff,
         day, start, _studs) = r

        # klass = fix_class(klass)

        kk = fix_class(klass)
        if len(kk) > 1:
            multi_class += 1
        for k in kk:
            # cc[k].add((prof_surname, mat_cod))


            prof_surname, prof_name = fix_prof(prof_surname, prof_name)
            room = fix_room(room)

            prof_set.add((prof_surname, prof_name))
            klass_set.add(k)
            mat_dic[mat_cod] = mat_name
            room_set.add(room)
    info(f"{multi_class} multi-class records found")

def calc_cc(rows):
    info("Calculating 'consigli di classe'")
    cc = defaultdict(set)
    for r in rows:

        (num, duration, freq,
         mat_cod, mat_name,
         prof_surname, prof_name,
         klass,
         room,
         _period, _spec, _co_doc, _coeff,
         day, start, _studs) = r

        prof_surname, prof_name = fix_prof(prof_surname, prof_name)

        kk = fix_class(klass)
        for k in kk:
            cc[k.strip()].add((prof_surname, mat_cod))
    return cc

def string_collection(oo, name, limit=1000):
    """Show contents of OO and LEN of collections, prefix with NAME"""
    if isinstance(oo, dict):
        oo = oo.items()
    ss = list()
    for o in list(oo)[:limit]:
        ss.append(str(o))
    ss.sort()
    ss.insert(0, f"{name}: {len(oo)}")
    return "\n".join(ss)

def show_collection(oo, name, limit=1000):
    """Show contents of OO and LEN of collections, prefix with NAME"""
    print(string_collection(oo, name, limit))

def string_cc(cc):
    ss = list()
    for k,pp in sorted(cc.items()):
        ss.append(f"\n{k}")
        for p,m in sorted(pp):
            ss.append(f"    {p:20s} {m:3s}")
    return "\n".join(ss)

def show_cc(cc):
    print(string_cc(cc))

def save_cc(cc):
    f = f"simple-out/cc.txt"
    info(f"Saving {len(cc)} CC lines to '{f}'")
    with open(f, "w") as out:
        s = string_cc(cc)
        out.write(s)

def save_summaries(rows):
    prof_set = set()
    klass_set = set()
    room_set = set()
    mat_dic = dict()

    calc_summaries(rows, prof_set, klass_set, room_set, mat_dic)

    cc = {
        "Profs": prof_set,
        "Classes": klass_set,
        "Rooms": room_set,
        "Subjects": mat_dic,
    }

    info("Saving summaries...")
    for s,c in cc.items():
        f = f"simple-out/{s.lower()}.txt"
        info(f"...writing {len(c)} lines to '{f}'")
        with open(f, "w") as out:
            out.write(string_collection(c, s))

def show_summaries(rows):
    prof_set = set()
    klass_set = set()
    room_set = set()
    mat_dic = dict()

    calc_summaries(rows, prof_set, klass_set, room_set, mat_dic)

    cc = {
        "Profs": prof_set,
        "Classes": klass_set,
        "Rooms": room_set,
        "Subjects": mat_dic,
    }

    for s,c in cc.items():
        print("-" * 40)
        show_collection(c, s, limit=10)

def main(input_csv_file):
    rows = file_to_rows(input_csv_file)

    save_summaries(rows)

    cc = calc_cc(rows)
    save_cc(cc)

if __name__ == "__main__":

    main("data/export.csv")
