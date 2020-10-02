#! /usr/bin/env python3

# author: Luca Manini (luca.manini@liceodavincitn.it)

import csv
from collections import defaultdict, namedtuple
import xlsxwriter

# Questi sono gli header di colonna contenuti nella prima riga del
# CSV, che poi uso come nomi dei "campi del record" che costruisco per
# ciascuna riga.  Non è importante usare quelli definiti nel file ma
# non ho motivo per cambiarli.

Record = namedtuple("Record", """
    NUMERO DURATA FREQUENZA MAT_COD MAT_NOME
    DOC_COGN DOC_NOME CLASSE AULA PERIODICITA
    SPECIFICA CO_DOC COEFF GIORNO ORA_INIZIO ALUNNI
""")

START_SHIFT = {
    "07h50": 0,
    "08h40": 1,
    "09h30": 2,
    "10h30": 3,
    "11h20": 4,
    "12h15": 5,
    "13h10": 6,
    "14h00": 7
    }

START_TIMES = {v:k for k,v in START_SHIFT.items()}

DAYS_INDEX = {"lunedì":    0,
              "martedì":   1,
              "mercoledì": 2,
              "giovedì":   3,
              "venerdì":   4,
              "sabato":    5}

def get_encoding(file):
    for e in ["utf-8", "utf-16"]:
        try:
            f = open(file, encoding=e)
            f.read()
            f.close()
            return e
        except UnicodeDecodeError:
            pass

def csv_to_records(csv_in):

    enc = get_encoding(csv_in)
    with open(csv_in, newline="", encoding=enc) as data:
        rows = list(csv.reader(data, delimiter=";"))[1:]
        for r in rows:
            yield Record(*r)

def records_to_class_dict(records):

    class_dict = defaultdict(list)
    for r in records:
        class_id = r.CLASSE
        size = int(r.DURATA[0])
        for i in range(size):
            o = START_SHIFT[r.ORA_INIZIO] + i
            class_data = (DAYS_INDEX[r.GIORNO],
                          o,
                          r.MAT_COD,
                          r.DOC_COGN)
            class_dict[class_id].append(class_data)
    return class_dict

HTML_FMT = r"""

<table border="1">
  <tr>
    <td align="center" colspan="7" bold="1">%(klass)s</td>
  </tr>
  <tr>
    <th></th>
    <th>Lun</th><th>Mar</th><th>Mer</th>
    <th>Gio</th><th>Ven</th><th>Sab</th>
  </tr>

  %(rows)s
</table>

"""

def lessons_to_grid(lessons):
    grid = list()
    for i in range(8):
        grid.append([""] * 6)
    for d, h, m, p in lessons:
        grid[h][d] = (m,p)
    return grid

def grid_to_table(grid):
    t = ""
    for ri, row in enumerate(grid):              # hours
        t += "  <tr>\n    "
        t += "<td>%s</td>" % START_TIMES[ri]
        for cell in row:
            if cell:
                m, p = cell
            t += '  <td align="center">%s</br>%s</td>' % (m, p)
        t += "\n  </tr>\n"
    # print(t)
    return t

def lessons_to_table(lessons):
    g = lessons_to_grid(lessons)
    return grid_to_table(g)

def class_to_table(klass, lessons):
    return HTML_FMT % {"klass": klass,
                       "rows": lessons_to_table(lessons)}

def main(csv_in,
         csv_out="output-orario-classi.csv",
         xls_out="output-orario-classi.xls"):

    recs = csv_to_records(csv_in)
    class_dict = records_to_class_dict(recs)
    for k, v in class_dict.items():
        if k in "3Nsa".split():
            t = class_to_table(k, v)
            # print(v)
            print(t)

def usage():
    print("usage: orario-classi export-csv-file [output-csv-file]")

if __name__ == "__main__":

    import sys
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
        csv_out = "output-orario.csv"
    main(csv_in, csv_out)
