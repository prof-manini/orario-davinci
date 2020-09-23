import csv
from collections import defaultdict, namedtuple

Record = namedtuple("Record", """
    NUMERO DURATA FREQUENZA MAT_COD MAT_NOME DOC_COGN DOC_NOME CLASSE
    AULA PERIODICITA SPECIFICA CO_DOC COEFF GIORNO ORA_INIZIO ALUNNI
""")

SRC = "./data/exp-1.csv"
DAYS_SHIFT = {"lunedì":     0,
              "martedì":    6,
              "mercoledì": 12,
              "giovedì":   18,
              "venerdì":   24,
              "sabato":    30}

def make_lessons_list():
    return [""] * 35
prof_dict = defaultdict(make_lessons_list)
with open(SRC, newline="", encoding="utf-16") as data:
    rows = list(csv.reader(data, delimiter=";"))[1:]
    for r in rows:
        o = Record(*r)
        prof = "%s - %s" % (o.DOC_COGN, o.DOC_NOME)
        prof = (o.DOC_COGN, o.DOC_NOME)
        prof_dict[prof][DAYS_SHIFT[o.GIORNO]] = o.MAT_COD + " / " + o.CLASSE
        aula = o.AULA
        if "(" in aula:
            aula = aula.split("(")[1]
        if ")" in aula:
            aula = aula.split(")")[0]
        # aula = o.AULA.split("(")[1].split(")")[0]
        prof_dict[prof][DAYS_SHIFT[o.GIORNO]] = aula + " / " + o.CLASSE
            # o.GIORNO,
            # DAYS_SHIFT[o.GIORNO],
            # o.ORA_INIZIO,
    for prof, ss in sorted(prof_dict.items()):
        # if prof.startswith("Manini"):
        #     print(prof, ss)
        # ss.insert(0, prof)
        data = list(prof) + ss
        line = ",".join(data)
        print(line)
