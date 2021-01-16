import csv
from recordclass import recordclass
from collections import defaultdict

import logging
logging.basicConfig(level=logging.DEBUG,
                    format="%(levelname)s: %(message)s")
debug = logging.debug

# The raw data file exported from the EDT software is a CSV file
# encoded in UTF-16 (for some reason!). More often than not, a UTF-8
# encoding is preferrable as is this more amendable to unix command
# line tools like grep or less.  That means that this program should
# be able to read both formats, "guessing" the correct one.

def guessed_encoding(file):
    "Guessed encoding for text FILE"
    for e in ["utf-8", "utf-16"]:
        try:
            f = open(file, encoding=e)
            f.read()
            f.close()
            return e
        except UnicodeDecodeError:
            pass
    raise ValueError(f"Unable to detect enconding for '{file}'")

def csv_to_rows(csv_in):
    "Lines (list of strings) read from CVS file CSV_IN"
    debug("Reading CSV file '%s'" % csv_in)
    enc = guessed_encoding(csv_in)
    with open(csv_in, newline="", encoding=enc) as data:
        return list(csv.reader(data, delimiter=";"))[1:]

DAYS_SHIFT = {"lunedì":     0,
              "martedì":    8,
              "mercoledì": 16,
              "giovedì":   24,
              "venerdì":   32,
              "sabato":    40}

DAYS = list(DAYS_SHIFT.keys())
DAYS_DICT = {d:i for i,d in enumerate(DAYS)}

def day_index(day):
    return DAYS_DICT[day]

COLUMNS = """
  NUMERO   DURATA      FREQUENZA  MAT_COD
  MAT_NOME DOC_COGN    DOC_NOME   CLASSE
  AULA     PERIODICITA SPECIFICA  CO_DOC
  COEFF    GIORNO      ORA_INIZIO ALUNNI
  ORA_PROG
"""

COLUMNS = """
    num duration freq mat_code mat_name
    prof_surname prof_name klass room period
    spec prof_bis coeff day start stud_count
    day_index start_index start_str prof_fullname
""".strip()

COLUMNS_COUNT = len(COLUMNS.split())

START_TIMES = "07:50 08:40 09:30 10:30 11:20 12:15 13:10 14:00".split()

START_DICT = {s:i for i,s in enumerate(START_TIMES)}
def start_index(start):
    return START_DICT[start]

Record = recordclass("Record", COLUMNS)

def make_empty_record():
    "An empty record, to be 'manually' filled, used for testing"
    line = [""] * COLUMNS_COUNT
    r = Record(*line)
    # r.duration = 1
    # r.klass = "5A"
    return r

def clean_record(r):
    "Modify/fix some fields in R (in place!)"
    r.duration = int(r.duration[0])
    r.klass = r.klass.strip("as")
    r.day_index = day_index(r.day)
    r.start = r.start.replace("h", ":")
    r.start_index = start_index(r.start)
    name = r.prof_name and r.prof_name[0] or ""
    r.prof_fullname = f"{r.prof_surname} {name}."

def make_record(row, clean=True):
    "Return a new record with data from ROW"
    # row.append(None)
    missing = COLUMNS_COUNT - len(row)
    row.extend([" "] * missing)
    r = Record(*row)
    if clean:
        clean_record(r)
    return r

def rows_to_records(rows):
    "Converts rows into records"
    debug(f"Converting {len(rows)} rows into records")
    return [make_record(r) for r in rows]

def has_multiple_duration(r):
    "True if R has duration > 1"
    return r.duration > 1

def expand_multiple_duration(r):
    """List on NEW records from 'multiduration' R (to REPLACE r)
    >>> r = make_empty_record()
    >>> r.duration = 3
    >>> r.start = "09h30"
    >>> rr = expand_multiple_duration(r)
    >>> for r in rr: print(r.duration, r.start)
    1 09h30
    1 10h30
    1 11h20
    """
    oo = list()
    for off in range(r.duration):
        c = r.__copy__()
        c.duration = 1
        index = start_index(r.start) + off
        c.start_index = index
        c.start = START_TIMES[index]
        oo.append(c)
    return oo

def has_multiple_classes(r):
    "True if R.klass lists multiple classes like '4/A/C/F TED'"
    return "/" in r.klass or " " in r.klass

def expand_multiple_classes(r):
    """List on NEW records from 'multiclass' R (to REPLACE r)
    >>> r = make_empty_record()
    >>> r.klass = "4B/C/F TED"
    >>> r.mat_code = "---"
    >>> rr = expand_multiple_classes(r)
    >>> for r in rr: print(r.klass, r.mat_code)
    4B TED
    4C TED
    4F TED
    """
    oo = list()
    k, mat = r.klass.split()
    n, kk = k[0], k[1:]
    kk = kk.split("/")
    # debug(f"exp klass: {k=} {mat=} {n=} {kk=}")
    for k in kk:
        c = r.__copy__()
        c.klass = n + k
        c.mat_code = mat
        # debug(f"   : {c.klass=} {c.mat_code=}")
        oo.append(c)
    return oo

def expand_records(recs):
    oo = list()
    duration_count = 0
    class_count = 0
    for r in recs:
        add_ori = True
        if has_multiple_duration(r):
            duration_count += 1
            rr = expand_multiple_duration(r)
            oo.extend(rr)
            add_ori = False
        if has_multiple_classes(r):
            class_count += 1
            rr = expand_multiple_classes(r)
            oo.extend(rr)
            add_ori = False
        if add_ori:
            oo.append(r)
    debug(f"Expanded {duration_count} multiple duration records")
    debug(f"Expanded {class_count} multiple classes records")
    return oo

def prof_classes(recs):
    d = defaultdict(set)
    for r in recs:
        pp = r.prof_fullname
        d[pp].add( (r.klass, r.mat_code) )
    return d

def class_profs(recs):
    d = defaultdict(set)
    for r in recs:
        k = r.klass
        v = r.prof_fullname
        d[k].add(v)
    return d

def class_lessons(recs):
    d = defaultdict(list)
    for r in recs:
        k = r.klass
        v = r.day_index, r.start_index, r.mat_code, r.prof_fullname
        d[k].append(v)
    return d

def banner(s, char="-", count=40, max_len=40):
    out = "--- %s %s" % (s, char * count)
    print(out[:40])

def get_distinct(field, recs):
    return list({r.__getattribute__(field) for r in recs})

def show_summary(field, recs, dist_count=5, exa_count=10, title=None):
    oo = get_distinct(field, recs)
    c = len(oo)
    if title is None:
        title = field
    banner("%s (field summary)" % title)
    print("Count: %d" % c)
    print("Distinct: ", oo[:dist_count], "... and more" if c > dist_count else "")
    if exa_count:
        print("Examples:")
        for o in recs[:min(c, exa_count)]:
            print(o.__getattribute__(field))

def show_summaries(recs):
    banner("Totals records count")
    print(len(recs))

    banner("Prof")
    profs = list({(r.prof_surname, r.prof_name) for r in recs})
    for p in profs[:5]:
        print(p)

    show_summary("prof_surname", recs)
    show_summary("klass", recs, exa_count=0)
    show_summary("period", recs, exa_count=0)
    show_summary("stud_count", recs, exa_count=0)

    multiple = [r for r in recs if r.duration > 1]
    show_summary("duration", multiple,
                 exa_count=0,
                 title="multiple hours classes")
    multiple = [(r.duration, r) for r in recs if r.duration > 1]
    dd = [d for d,_ in multiple]
    for d in set(dd):
        print("Duration: %d - count:%d" % (d, dd.count(d)))

    stupid = [r for r in recs if "/" in r.klass]
    show_summary("klass", stupid,
                 dist_count=5, exa_count=5,
                 title="Stupid klass names")

    banner("start times")
    times = {r.start for r in recs}
    for t in times:
        if t not in START_TIMES:
            raise Exception("Bad start time", t)
    print(START_TIMES)

    count = 0
    for r in recs:
        if has_multiple_classes(r) and has_multiple_duration(r):
            count += 1
    debug(f"{count} recs are both multi class and multi duration")

if __name__ == "__main__":

    file = "data/export.csv"
    rows = csv_to_rows(file)
    recs = rows_to_records(rows)
    # show_summaries(recs)

    klasses = {r.klass for r in recs}
    debug(f"{len(klasses)} BEFORE expansion")
    debug(klasses)

    banner("Summaries BEFORE expansion")
    # show_summaries(recs)

    # AFTER ==========================================

    recs = expand_records(recs)
    debug(f"Records after expansion: {len(recs)}")

    klasses = {r.klass for r in recs}
    debug(f"{len(klasses)} AFTER expansion")
    debug(klasses)

    banner("Summaries AFTER expansion")
    # show_summaries(recs)

    banner("Prof -> classes")
    pp = prof_classes(recs)
    for p,oo in sorted(pp.items()):
        print("%s -> %s" % (p, sorted(oo)))

    banner("Class -> Profs")
    pp = class_profs(recs)
    for p,oo in sorted(pp.items()):
        print("%s -> %s" % (p, sorted(oo)))

    banner("Class -> Lessons")
    pp = class_lessons(recs)
    for k,oo in sorted(pp.items()):
        print(f"\n{k}")
        for day_idx, start_idx, mat_code, prof_fullname in oo:
            day = DAYS[day_idx]
            start = START_TIMES[start_idx]
            print(day_idx, "%-10s" % day,
                  start_idx, start,
                  mat_code, prof_fullname)
