#! /usr/bin/env python3

import sys
import os
# from odv import data_to_dict, write_prof_dict_csv, write_prof_dict_xls
from odv import data_to_prof_dict, write_prof_dict_xls

progname = os.path.basename(__file__)

def main(csv_in,
         csv_out="out/full-timetable.csv",
         xls_out="out/full-timetable.xls"):

    # Questa funzione è l'entry point del modulo, sia nel senso che è
    # la funzione chiamata nel blocco "if __name__ ..." sia nel senso
    # che è la funzione chiamabile da un altro file dopo aver
    # importato questo come modulo.

    prof_dict = data_to_prof_dict(csv_in)
    # write_prof_dict_csv(prof_dict, csv_out)
    write_prof_dict_xls(prof_dict, xls_out)

def usage():
    print(f"usage: {progname} export-csv-file [output-csv-file]")

if __name__ == "__main__":

    args = sys.argv[1:]
    if len(args) > 2:
        usage()
        sys.exit(1)
    if not args or args[0] in "-h --help".split():
        usage()
        sys.exit(0)
    csv_in = args[0]
    if len(args) == 2:
        csv_out = args[1]
    else:
        csv_out = "out/full-timetable.csv"
    main(csv_in, csv_out)
