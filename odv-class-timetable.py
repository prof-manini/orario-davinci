#! /usr/bin/env python3

# author: Luca Manini (luca.manini@liceodavincitn.it)

# Questo orribile programma prende i dati dell'orario della scuola e
# genera l'orario delle singole classi: una tabella con una colonna
# per i giorni e le righe per le ore di lezione, per ogni lezione
# indica la materia e il docente.

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

CSV_INPUT = "data/export.csv"
HTML_OUTDIR = "out/class-timetable-html/"
XML_OUTDIR = "out/class-timetable-xls/"
CSV_OUTDIR = "out/class-timetable-csv/"

# Qui prendo i record generati in csv_to_records e creo un dizionario
# con il nome della classe come chiave e i dati (di solito materia e
# docente) per le celle della tabella dell'orario per classe.

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
    debug(f"{len(class_dict)} classes found")
    return class_dict

# Questa stringa contiene il "formato" della tabella con l'orario
# della classe.  Al momento una cosa molto grezza a cui sarebbe meglio
# aggiungere un po' di classi per poi abbellirla con i CSS.

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

# Qui prendo le ore di lezione di una classe e restituisco una
# "griglia" (una lista di liste) che poi "formatterò" in HTML (o
# altro).

def lessons_to_grid(lessons):
    grid = list()
    for i in range(8):
        grid.append([""] * 6)
    for d, h, m, p in lessons:
        grid[h][d] = (m,p)
    return grid

# Qui prendo la griglia di cui sopra e la formatto in HTML.

def grid_to_table(grid):
    t = ""
    for ri, row in enumerate(grid):              # hours
        t += "  <tr>\n    "
        t += "<td>%s</td>" % START_TIMES[ri]
        for cell in row:
            if cell:
                m, p = cell
            else:
                m, p = "",""
            t += '  <td align="center">%s</br>%s</td>' % (m, p)
        t += "\n  </tr>\n"
    # print(t)
    return t

# Qui ... si capisce.

def lessons_to_table(lessons):
    g = lessons_to_grid(lessons)
    return grid_to_table(g)

# E qui anche.

def class_to_html_table(klass, lessons):
    return HTML_FMT % {"klass": klass,
                       "rows": lessons_to_table(lessons)}

def class_to_csv_table(klass, lessons):
    return f"{klass} -> {lessons}\n"

def write_csv(class_dict, csv_outdir):

    os.makedirs(csv_outdir, exist_ok=True) # grant dir existence
    csv_out = os.path.join(csv_outdir, "class-timetable.csv")
    debug(f"Writing output CSV file '{csv_out}'")
    with open(csv_out, "w") as output:
        for k, v in class_dict.items():
            t = class_to_csv_table(k, v)
            output.write(t)

def write_html(class_dict, html_outdir):

    os.makedirs(html_outdir, exist_ok=True) # grant dir existence
    for k, v in class_dict.items():
        t = class_to_html_table(k, v)

        # A volte il "codice della classe" è qualcosa del tipo "2G/H
        # SPA", che come stringa da utilizzare nel nome di un file non
        # è proprio il massimo!

        k = k.replace("/", "-")
        k = k.replace(" ", "_")

        f = os.path.join(html_outdir, "%s.html" % k)
        with open(f, "w") as html_out:
            html_out.write(t + "\n")

# Entry point principale del programma

def main(csv_in, html_outdir=HTML_OUTDIR):

    recs = csv_to_records(csv_in)
    class_dict = records_to_class_dict(recs)
    write_html(class_dict, html_outdir)
    write_csv(class_dict, CSV_OUTDIR)

def usage():
    print(f"usage: {progname} [export-csv-file]")

if __name__ == "__main__":

    import sys
    args = sys.argv[1:]
    if len(args) > 1:
        usage()
        sys.exit(1)
    if args and args[0] in "-h --help".split():
        usage()
        sys.exit(0)
    csv_in = args and args[0] or CSV_INPUT
    main(csv_in)
