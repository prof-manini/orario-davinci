#! /usr/bin/env python3

# author: Luca Manini (luca.manini@liceodavincitn.it)

import os
import csv
from collections import defaultdict
import logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(levelname)s: %(message)s")
debug = logging.debug

from odv import (
    Record, get_encoding, csv_to_records,
    DAYS_INDEX, START_SHIFT, START_TIMES,
    )

progname = os.path.basename(__file__)

def main(csv_in, base_tables_outdir="./out"):

    recs = tuple(csv_to_records(csv_in))

    # subjects (materie) ----------------------------------------

    mat_dic = dict()
    for r in recs:
        mat_dic[r.MAT_COD] = r.MAT_NOME

    mat_file = os.path.join(base_tables_outdir, "mat_out.txt")
    with open(mat_file, "w") as out:
        for k,v in sorted(mat_dic.items()):
            out.write(f"{k} = {v}\n")

    # classes --------------------------------------------------

    # class "codes" can have different "formats":
    #
    # 1As  = first year, group A, type s (plain old fashion)
    # 1Bsa = first year, group B, type sa (the almost good one)
    #
    # Because there is no Asa not Bs, I'll drop the suffix
    #
    # 2G/H   SPA = second year, TWO separate classes (G/H) doing SPANISH
    # 4G/H/R SPA = second year, THREE separate classes (G/H/R) doing SPANISH
    # this line is equivalent (and will be transformed into) TWO lines

    class_single = defaultdict(set)
    class_multiple = defaultdict(set)

    class_file = os.path.join(base_tables_outdir, "class_out.txt")

    for r in recs:
        k,v = r.CLASSE, r.MAT_COD
        if "/" in k:                   # "2G/H SPA"
            print(k, "---")
            cc, mat = k.split()        # ["2G/H". "SPA"]
            try:
                cc = cc.split("/")        # ["2G", "H"]
            except:
                error(f"Bad class record {cc}")
                continue
            cc = [cc[0]] + [cc[0][0] + c for c in cc[1:]]
            debug(f"Multiclass record {cc}")
            for k in cc:
                debug(f"Multi {k=} {v=}")
                class_multiple[k].add(v.lower())
        else:
            # debug(f"Single {k=} {v=}")
            class_single[k[:2]].add(v)

    for k,v in class_multiple.items():
        class_single[k].update(class_multiple[k])

    class_file = os.path.join(base_tables_outdir, "class_out.txt")
    with open(class_file, "w") as out:
        for k,v in sorted(class_single.items()):
            z = " ".join([s for s in sorted(v)])
            out.write(f"{k} = {z}\n")

    # professors --------------------------------------------------

    prof_dic = defaultdict(set)

    for r in recs:
        k,v = (r.DOC_COGN, r.DOC_NOME), r.MAT_COD
        prof_dic[k].add(v)

    class_file = os.path.join(base_tables_outdir, "prof_out.txt")
    with open(class_file, "w") as out:
        for k,v in sorted(prof_dic.items()):
            z = " ".join([s for s in sorted(v)])
            k = ", ".join(k)
            out.write(f"{k} = {z}\n")

    # rooms --------------------------------------------------------

    room_dic = defaultdict(set)

    for r in recs:
        k,v = r.AULA, r.CLASSE
        v = v.rstrip("[as]")
        room_dic[k].add(v)

    class_file = os.path.join(base_tables_outdir, "room_out.txt")
    with open(class_file, "w") as out:
        for k,v in sorted(room_dic.items()):
            z = " ".join([s for s in sorted(v)])
            out.write(f"{k} = {z}\n")

def usage():
    print(f"usage: {progname} export-csv-file")

if __name__ == "__main__":

    import sys
    args = sys.argv[1:]
    if len(args) > 1:
        usage()
        sys.exit(1)
    if not args or args[0] in "-h --help".split():
        usage()
        sys.exit(0)
    csv_in = args[0]
    main(csv_in)
