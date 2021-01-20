#! /usr/bin/env python3

# author: Luca Manini (luca.manini@liceodavincitn.it)

# Base module for processing school lessons schedule data produced by
# the EDT software and exported in CSV format (UTF-16 encoded).

# The export file has one row for every "activity" by one theacher in
# one class.  Each activity can span one or more hours! The columns
# headers can be found in this source file in the definition of the
# "Record" data type.

from itertools import zip_longest as zip
import csv
from collections import defaultdict, OrderedDict as ordereddict
from recordclass import recordclass as namedtuple
import xlsxwriter
import logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(levelname)s: %(message)s")
debug = logging.debug

CSV_INPUT = "data/export.csv"

# generic data structures and functions ----------------------------

# This are the column headers from the first row of the export file.
# I'll use them as names for the attributes of the "Record" type.  At
# import time, I use the csv module to split the row into a list of
# fields from which I create a Record object that I'll use a the base
# for all the processing.

Record = namedtuple("Record", """
    NUMERO DURATA FREQUENZA MAT_COD MAT_NOME
    DOC_COGN DOC_NOME CLASSE AULA PERIODICITA
    SPECIFICA CO_DOC COEFF GIORNO ORA_INIZIO ALUNNI
    ORA_PROG
""")

def make_record(row):
    row.append(None)              # ORA_PROG
    return Record(*row)

# Example of a (splitted) row's content:
#
# 344                             # numero
# 2h00                            # durata
# S                               # frequenza
# INF                             # mat_cod
# Informatica                     # mat_nome
# Manini                          # doc_cogn
# Luca                            # doc_nome
# 2Psa                            # classe
# <Lab...>Lab. Inf..1 (2° p 2.04) # aula
# S                               # periodicita
# ss                              # specifica
# N                               # co_doc
# 50/60                           # coeff
# martedì                         # giorno
# 07h50                           # ora_inizio
# 0                               # alunni

# In the odv-full-timetable program, I have to build a list of all the
# lessons each professor teaches in the whole week, so it is useful to
# know at which "offset" weeks data start.  In the raw data file, the
# days of the week are written using the lowercase full italian names
# (with accents!).

DAYS_SHIFT = {"lunedì":     0,
              "martedì":    8,
              "mercoledì": 16,
              "giovedì":   24,
              "venerdì":   32,
              "sabato":    40}

def list_to_items_pos_dict(oo):
    # ["foo", 123, "bar"] -> {"foo":0, 123:1, "bar":2}
    return {v:k for k,v in enumerate(oo)}

DAYS_INDEX = list_to_items_pos_dict(DAYS_SHIFT.keys())
DAYS_PER_WEEK = len(DAYS_SHIFT)

# In the raw data file, the start time of each lesson is coded in the
# format shown below, but it is useful to be able to easily convert it
# in a sequence id.

START_TIMES = "07h50 08h40 09h30 10h30 11h20 12h15 13h10 14h00".split()
START_SHIFT = list_to_items_pos_dict(START_TIMES)
START_INDEX = {t:START_TIMES.index(t) for t in START_TIMES}

LESSONS_PER_DAY = len(START_SHIFT)
LESSONS_PER_WEEK = LESSONS_PER_DAY * DAYS_PER_WEEK

# The raw data file exported from the EDT software is a CSV file
# encoded in UTF-16 (for some reason!). More often than not, a UTF-8
# encoding is preferrable as is this more amendable to unix command
# line tools like grep or less.  That means that this program should
# be able to read both formats, "guessing" the correct one.

def get_encoding(file):
    for e in ["utf-8", "utf-16"]:
        try:
            f = open(file, encoding=e)
            f.read()
            f.close()
            return e
        except UnicodeDecodeError:
            pass
    raise ValueError(f"Unable to detect enconding for '{file}'")

# Qui leggo i dati grezzi e per ciascuna riga restituisco un "record",
# ossia un oggetto con attributi (molto più comodo che una lista o una
# tupla).

def csv_to_records(csv_in):

    debug("Reading input file '%s'" % csv_in)
    enc = get_encoding(csv_in)
    with open(csv_in, newline="", encoding=enc) as data:
        rows = list(csv.reader(data, delimiter=";"))[1:]
        debug(f"{len(rows)} rows found")
        for r in rows:
            yield make_record(r)

def _me():
    # https://www.oreilly.com/library/view/python-cookbook/0596001673/ch14s08.html
    import sys
    return sys._getframe(1).f_code.co_name

def records_to_class_dict(recs):

    # This function get the usual RECS (sequence of Records) and build
    # a dictionary whith the class code as key and a list of records
    # as value. Each record corresponds to ONE hour of
    # lesson.

    # Each rec in RECS may produce more that on entry in the class's
    # item for two different reasons.  First, each record has a
    # DURATION (nomber of hours) and I'll generate one record for each
    # hour. Second, some recs are "multiclass lines" (as explained
    # below).

    # This function comes from odv-class-timetable.py, that was the
    # first place were I found out about "multiclass" lines in EDT's
    # export. Those lines originate from the fact that some classe
    # sometime "split" to attend different lessons (e.g. some students
    # get TED and some ENG) and that is indicated with the
    # "multiclass" code.

    # class "codes" can have different "formats":
    #
    # 1As  = first year, group A, type s (plain old fashion)
    # 1Bsa = first year, group B, type sa (the almost good one)
    #
    # Because there is no Asa not Bs, I'll drop the suffix
    #
    # 2G/H   SPA = second year, TWO separate classes (G/H) doing SPANISH
    # 4G/H/R SPA = second year, THREE separate classes (G/H/R) doing SPANISH
    # this line is equivalent (and will be transformed into) TWO records.

    class_single = defaultdict(list)
    class_multiple = defaultdict(list)
    multi_count = 0
    recs = tuple(recs)
    for r in recs:
        k,v = r.CLASSE, r
        if "/" in k:                   # "2G/H SPA"
            cc, mat = k.split()        # ["2G/H". "SPA"]
            try:
                cc = cc.split("/")        # ["2G", "H"]
                multi_count += 1
            except:
                error(f"{_me()}: Bad class record {cc}")
                continue
            cc = [cc[0]] + [cc[0][0] + c for c in cc[1:]]
            # debug(f"Multiclass record {cc}")
            for k in cc:
                # debug(f"Multi {k=} {v=}")
                class_multiple[k].append(v)
        else:
            # debug(f"Single {k=} {v=}")
            class_single[k[:2]].append(v)

    for k,v in class_multiple.items():
        class_single[k].extend(class_multiple[k])

    debug(f"{_me()}: multiclass recs:{multi_count}")
    debug(f"{_me()}: classes:{len(class_single)}")

    lessons_count = 0
    for k,v in class_single.items(): # k = class
        z = v.copy()                 # z = list of lessons (recs)
        for r in z:                  # r = lesson (rec)
            d = int(r.DURATA[0])
            r.ORA_PROG = START_INDEX[r.ORA_INIZIO]
            lessons_count += 1
            # debug(f"{_me()}: long lesson {r.CLASSE} -> {d}")
            for i in range(1, d):
                t = Record(*list(r))
                o = START_SHIFT[t.ORA_INIZIO] + i
                t.ORA_INIZIO = START_TIMES[o]
                v.append(t)

    classes_count = len(class_single)

    debug(f"{_me()}: lessons count:{lessons_count}")
    debug(f"{_me()}: classes:{classes_count}")
    debug(f"{_me()}: lessons/class:{lessons_count/classes_count:.2f}")

    return class_single

# code specific to full-timetable (tabellone) --------------------

def make_lessons_list():
    return [""] * LESSONS_PER_WEEK

def format_room(room):

    # Nel file di export, il dato AULA è piuttosto logorroico,
    # qualcosa del tipo "Aula 3Hsa (2.50)" (quando va bene), me nel
    # tabellone voglio qualcosa di più sintetico, ad esempio solo la
    # classe.

    if "(" in room:
        room = room.split("(")[1]
    if ")" in room:
        room = room.split(")")[0]
    room = room.replace("<Aule per gruppi>Aula Magna 4° piano", "A.M.")
    return room

def data_to_dict(raw_data):

    # Questo è il dizionario che, per ciascun prof usato come chiave,
    # contiene le relative ore di lezione.  Uso defaultdict così "al
    # primo giro" ho già una lista di stringhe vuote (generata da
    # make_lessons_list) della lunghezza corretta.

    prof_dict = defaultdict(make_lessons_list)

    enc = get_encoding(raw_data)

    debug(f"Reading raw data file '{raw_data}', encoding with {enc}")
    with open(raw_data, newline="", encoding=enc) as data:
        rows = list(csv.reader(data, delimiter=";"))[1:]
        for r in rows:

            # Qui creo, a partire dalla "riga" letta da CSV, una
            # struttura i cui (nomi degli) attributi sono definiti
            # dalla classe Record e che ho lasciato uguali a quelli
            # presenti nel file CSV.

            o = Record(*r)

            # I dati delle varie righe vengono raccolti in un
            # dizionario in cui le chiavi sono i dati del docente, ad
            # esempio la coppia cognome/nome.

            prof_cod = (o.DOC_COGN, o.DOC_NOME)

            # Dati sulla classe

            room = format_room(o.AULA)

            # Qui scelto cosa scrivere nelle celle del foglio. Posso
            # mettere sola la classe, solo l'aula o quello che voglio.
            # Qui ci sono alcuni esempi da (s)commentare.

            # cell = room + " / " + o.CLASSE
            cell = o.CLASSE
            # cell = room

            # Qui gestisco le ore "multiple" (consecutive). Nel file
            # CSV, per ogni lezione c'è una sola riga, in cui si
            # indica però anche la durata.  Quello che faccio qui è
            # "duplicare il dato" per ciascuna ora di lezione,
            # perdendo così il dato esplicito della durata.  Poi nella
            # generazione dell'XLS mi preoccupa di fare il merge delle
            # varie celle.

            size = int(o.DURATA[0]) # 1h00, 2h00 etc
            for i in range(size):
                day_cod = (DAYS_SHIFT[o.GIORNO] +
                           START_SHIFT[o.ORA_INIZIO] +
                           i)
                # if o.ORA_INIZIO == "13h10":
                #     print(f"{day_cod=} {o.GIORNO=}")
                prof_dict[prof_cod][day_cod] = cell

    return prof_dict

def write_prof_dict_csv(prof_dict, csv_out):

    # Qui scrivo il risultato in un file CSV usando semplicemente un
    # file di testo e relativo metodo "write".  Il modulo csv ha un
    # metodo apposito che però non mi pare offra vantaggi
    # interessanti.

    debug(f"Writing output CSV file '{csv_out}'")
    with open(csv_out, "w") as output:
        for prof_cod, ss in sorted(prof_dict.items()):
            prof_surname, prof_firstname = prof_cod
            prof_data = "%s %s." % (prof_surname, prof_firstname and
                                    prof_firstname[0])
            data = [prof_data] + ss
            line = ",".join(data)
            output.write(line + "\n")

def write_prof_dict_xls(prof_dict, xsl_out):

    # Nel dubbio, consultare:
    # https://xlsxwriter.readthedocs.io/examples.html
    # https://xlsxwriter.readthedocs.io/format.html#format

    debug(f"Writing output XLS file '{xsl_out}'")
    book = xlsxwriter.Workbook(xsl_out)

    # Qui posso definire vari formati che poi utilizzo nelle chiamate
    # a merge_range e a write (credo). Hanno un aspetto molto CSS, ma
    # non so se la corrispondenza è completa.

    title_format = book.add_format({
        'align': 'center',
        'bold': True,
        'font_size': 20,
        })
    days_format = book.add_format({
        'align': 'center',
        'bold': True,
        })
    hours_format = book.add_format({
        'align': 'center',
        'bold': True,
        })
    merge_format = book.add_format({
        'align': 'center',
    })
    cell_format = book.add_format({
        'align': 'center',
    })
    prof_format = book.add_format({
        'align': 'left',
    })

    sheet = book.add_worksheet()
    sheet.set_default_row(20)
    sheet.set_column(0, 0, 25, prof_format)
    # sheet.set_column(1, 1, 25, prof_format)

    # Scrittura della parte "fissa" di headers
    row = 0
    prof_off = 1         # numero di colonne usate per i dati del prof
    if True:

        # Titolo: centrato su tutta la larghezza (48 colonne)

        sheet.set_row(row, 42)
        sheet.merge_range(0,0,0,48, "Orario", title_format)
        row += 1

        # Giorni della settimana, presi da DAYS_SHIFT

        sheet.set_row(row, 22)
        days = [s.capitalize() for s in DAYS_SHIFT.keys()]
        for i, day in enumerate(days):
            range_start = prof_off + i * LESSONS_PER_DAY
            range_end   = range_start + LESSONS_PER_DAY - 1
            sheet.merge_range(row, range_start,
                              row, range_end,
                              day, days_format)
        row += 1

        # Ore del giorno, prese da START_SHIFT, in cui hanno un
        # formato tipo 07h30 che converto in 7:30.

        sheet.set_row(row, 20)
        for d in range(DAYS_PER_WEEK):
            for i, hour in enumerate(START_SHIFT.keys()):
                if hour[0] == "0":
                    hour = hour[1:]
                hour = hour.replace("h", ":")
                sheet.write(row, prof_off + i + d * LESSONS_PER_DAY, # ???
                            hour, hours_format)
        row += 1

    # Scrittura delle righe relative alle ore di lezione. Tutto facile
    # a parte raggruppare le "doppiette" o le "triplette". Per fare
    # questo uso un "trucco", se una cella ha lo stesso contenuto
    # della precedente faccio un merge; fortunatamente pare funzionare
    # anche "ricorsivamente", per esempio facendo il merge di una
    # terza ora con le precedenti due già raggruppate.

    row_off = row
    for row, (prof_cod, ss) in enumerate(sorted(prof_dict.items())):
        row += row_off
        prof_surname, prof_firstname = prof_cod
        prof_data = "%s %s." % (prof_surname, prof_firstname and
                                    prof_firstname[0])
        data = [prof_data] + ss
        old = None
        for col, text in enumerate(data):
            if col in [0,1]:
                sheet.write(row, col, text, prof_format)
            else:
                if text and text == old:
                    sheet.merge_range(row, col-1,
                                      row, col,
                                      text, merge_format)
                    old = None
                else:
                    sheet.write(row, col, text, cell_format)
                    old = text

    book.close()

# code specific to odv-class-timetable --------------------

MAT_NAMES = dict()
def get_mat_names(input="data/mat_names.txt"):
    if MAT_NAMES:
        return MAT_NAMES
    debug(f"{_me()}: reading {input}")
    with open(input) as rows:
        for r in rows:
            if not r.strip():
                continue
            k, v = map(str.strip, r.split("="))
            MAT_NAMES[k] = v
    return MAT_NAMES

def class_time_table_try(csv_in):

    recs = csv_to_records(csv_in)
    class_dict = records_to_class_dict(recs)
    lessons_dict = defaultdict(list)

    # Reorganize date from class_dict (that uses classes as keys) to
    # lessons_dict (that uses days as keys).  Both use records a
    # values.

    for klass, recs in sorted(class_dict.items()):
        day_lessons = defaultdict(list)
        lessons_dict[klass] = day_lessons
        for r in recs:
            day_lessons[r.GIORNO].append(r)

    # Load abbreviations for subjects: "Inglese" instead "Lingua e
    # Cultura Straniera Inglese" as description for ING).

    mat_names = get_mat_names()

    # The timetable should look something like:
    """
    |-------+-----------+-------------+-----------+---------+---------+--------|
    |       | Lunedì    | Martedì     | Mercoledì | Giovedì | Venerdì | Sabato |
    |-------+-----------+-------------+-----------+---------+---------+--------|
    |  7.50 |           | Informatica |           |         |         |        |
    |       |           | Manini      |           |         |         |        |
    |-------+-----------+-------------+-----------+---------+---------+--------|
    |  8.40 |           | Informatica |           |         |         |        |
    |       |           | Manini      |           |         |         |        |
    |-------+-----------+-------------+-----------+---------+---------+--------|
    |  9.30 |           |             | Italiano  |         |         |        |
    |       |           |             | Rossi     |         |         |        |
    |-------+-----------+-------------+-----------+---------+---------+--------|
    | 10.30 |           |             |           |         |         |        |
    |       |           |             |           |         |         |        |
    |-------+-----------+-------------+-----------+---------+---------+--------|
    | 11.20 | Dir. Eco. |             |           |         |         |        |
    |       | Verdi     |             |           |         |         |        |
    |-------+-----------+-------------+-----------+---------+---------+--------|
    """
    # Here we have all the data we need, but ordered by weekday first
    # (and then by time) while in the table the
    # order should be time first.
    #
    # If we put the data in a "matrix" (list of lists, We may then use
    # the zip function to "transpose" it.
    #
    # >>> t = [[1,2,3], [4,5,6], [7,8,9]]
    # >>> list(zip(*t))
    # [(1, 4, 7), (2, 5, 8), (3, 6, 9)]

    for klass, lessons in sorted(lessons_dict.items()):
        print(f"\n=== {klass} ====================")
        for day, lessons in sorted(lessons.items(), key=day_sorter):
            print(f"\n    {day} ----------------")
            for o in sorted(lessons, key=start_sorter):
                start = o.ORA_INIZIO.replace("h", ".") # 07h50 -> 07.50
                start = start.lstrip("0")              # 07.50 ->  7.50
                mat = mat_names[o.MAT_COD]             # ING -> Inglese
                print(f"{mat:12s} {start:>5.5s}   {o.DOC_COGN}")

def make_class_timetable_csv(klass, lessons):

    # Load abbreviations for subjects: "Inglese" instead "Lingua e
    # Cultura Straniera Inglese" as description for ING).

    mat_names = get_mat_names()

    # print(f"\n=== {klass} ====================")
    rr = list()
    # dd = ["Ora"] + [d[:3].upper() for d in DAYS_SHIFT]

    hh = [""] + [s.replace("h", ":").lstrip("0") for s in START_TIMES]
    rr.append(hh)

    for day, lessons in sorted(lessons.items(), key=day_sorter):
        r = [day]
        for o in sorted(lessons, key=start_sorter):
            mat = mat_names[o.MAT_COD]             # ING -> Inglese
            r.append(f'"{o.ORA_INIZIO} {o.DOC_COGN}"')
            # r.append(f"{mat:12s} {o.DOC_COGN}")
        rr.append(r)

    rr = list(zip(*rr, fillvalue=""))
    kk = [""] * 3 + [klass] + [""] * 3
    rr.insert(0, [""] * len(kk))
    rr.insert(1, kk)
    return rr

def class_time_table(csv_in, csv_out="./a.csv"):

    recs = csv_to_records(csv_in)
    class_dict = records_to_class_dict(recs)
    lessons_dict = defaultdict(list)

    # Reorganize date from class_dict (that uses classes as keys) to
    # lessons_dict (that uses days as keys).  Both use records a
    # values.

    for klass, recs in sorted(class_dict.items()):
        day_lessons = defaultdict(list)
        lessons_dict[klass] = day_lessons
        for r in recs:
            day_lessons[r.GIORNO].append(r)

    with open(csv_out, "w") as output:
        for klass, lessons in sorted(lessons_dict.items()):
            out = make_class_timetable_csv(klass, lessons)
            for r in out:
                if any (r[1:]):
                    s = ",".join(r)
                    # return
                    output.write(s + "\n")
            output.write("\n")

def start_sorter(r):
    return r.ORA_PROG

def day_sorter(d):
    return DAYS_INDEX[d[0]]

def make_class_timetable_array(klass, lessons):

    # Load abbreviations for subjects: "Inglese" instead "Lingua e
    # Cultura Straniera Inglese" as description for ING).

    mat_names = get_mat_names()

    # print(f"\n=== {klass} ====================")
    rr = list()
    # dd = ["Ora"] + [d[:3].upper() for d in DAYS_SHIFT]

    # START_TIMES = "07h50 08h40 09h30 10h30 11h20 12h15 13h10 14h00".split()

    END_TIMES = [               # BUG: stupid name!
        "8:00 - 8:40",
        "8:50 - 9:30",
        "9:40 - 10:20",
        "10:40 - 11:20",
        "11:30 - 12:10",
        "12:20 - 13:00",
        "13:10 - 14:00",
        "14:00 - 14:40",
    ]
    END_TIMES = ordereddict((               # BUG: stupid name!
        ("07h50",  "8:00\n 8:40"),
        ("08h40",  "8:50\n 9:30"),
        ("09h30",  "9:40\n10:20"),
        ("10h30", "10:40\n11:20"),
        ("11h20", "11:30\n12:10"),
        ("12h15", "12:20\n13:00"),
        ("13h10", "13:10\n14:00"),
        ("14h00", "14:00\n14:40"),
    ))
    # BUG
    # hh = [""] + [s.replace("h", ".").lstrip("0") for s in START_TIMES]
    hh = [""] + list(END_TIMES.values())
    rr.append(hh)

    for day, lessons in sorted(lessons.items(), key=day_sorter):
        r = [day.capitalize()]
        # BUG:
        # Here I'm looping on lessons but it is important to also
        # produce lines (hour) where this class has no lesson (e.g.:
        # this class start the day with the second hour on monday).
        # for o in sorted(lessons, key=start_sorter):
        #     mat = mat_names[o.MAT_COD]             # ING -> Inglese
        #     r.append(f"{mat.strip()}\n{o.DOC_COGN.strip()}")

        foo = ordereddict()
        for st in START_TIMES:
            foo[st] = None
        for less in lessons:
            foo[less.ORA_INIZIO] = less

        for st, o in foo.items():
            if o is None:
                r.append("")
            else:
                mat = mat_names[o.MAT_COD]             # ING -> Inglese
                if o.DOC_NOME:
                    zot = o.DOC_NOME[0] + "."
                else:
                    zot = ""
                r.append(f"{mat.strip()}\n{o.DOC_COGN.strip()} {zot}\nsincrona")
        rr.append(r)

    rr = list(zip(*rr, fillvalue=""))
    kk = [""] * 3 + [klass] + [""] * 3
    rr.insert(0, [""] * len(kk))
    rr.insert(1, kk)
    return rr

def write_class_time_table_xls(csv_in, xls_out="out/class-timetable.xls"):

    # https://xlsxwriter.readthedocs.io/format.html#set_align
    debug(f"Writing output XLS file '{xls_out}'")
    book = xlsxwriter.Workbook(xls_out)
    wrap_text = book.add_format()
    wrap_text.set_text_wrap()
    wrap_text.set_align("center")
    wrap_text.set_align("vcenter")

    recs = csv_to_records(csv_in)
    class_dict = records_to_class_dict(recs)
    lessons_dict = defaultdict(list)

    sheet = book.add_worksheet()
    sheet.set_default_row(44)
    sheet.set_column(1, 6, 15)

    # Reorganize date from class_dict (that uses classes as keys) to
    # lessons_dict (that uses days as keys).  Both use records a
    # values.

    for klass, recs in sorted(class_dict.items()):
        day_lessons = defaultdict(list)
        lessons_dict[klass] = day_lessons
        for r in recs:
            day_lessons[r.GIORNO].append(r)

    # Load abbreviations for subjects: "Inglese" instead "Lingua e
    # Cultura Straniera Inglese" as description for ING).

    mat_names = get_mat_names()

    row_index = 0
    for klass, lessons in sorted(lessons_dict.items()):
        sheet.write(row_index, 0, "")
        row_index += 1
        out = make_class_timetable_array(klass, lessons)
        for r in out:
            if not any (r[1:]):
                continue
            for col_index, s in enumerate(r):
                sheet.write(row_index, col_index, s, wrap_text)
            row_index += 1

    book.close()

if __name__ == "__main__":

    import sys
    import os
    progname = os.path.basename(__file__)

    def usage():
        print(f"usage: {progname} export-csv-file")

    import sys
    args = sys.argv[1:]
    if len(args) > 1:
        usage()
        sys.exit(1)
    if args and args[0] in "-h --help".split():
        usage()
        sys.exit(0)
    csv_in = args and args[0] or CSV_INPUT

    write_class_time_table_xls(csv_in)
    class_time_table(csv_in)
