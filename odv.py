#! /usr/bin/env/python3

# Questo programma legge dei dati da un "export" delle lezioni
# (attività) del programma EDT e produce file CSV con una riga per
# ciascun docente e una colonna per ogni ora di lezione. Ogni cella
# contiene informazioni come per esempio la classe, l'aula o altro.

import csv
from collections import defaultdict, namedtuple

# Questi sono gli header di colonna contenuti nella prima riga del
# CSV, che poi uso come nomi dei "campi del record" che costruisco per
# ciascuna riga.  Non è importante usare quelli definiti nel file ma
# non ho motivo per cambiarli.

Record = namedtuple("Record", """
    NUMERO DURATA FREQUENZA MAT_COD MAT_NOME
    DOC_COGN DOC_NOME CLASSE AULA PERIODICITA
    SPECIFICA CO_DOC COEFF GIORNO ORA_INIZIO ALUNNI
""")

# I dati delle lezioni li inserisco in una lista in una posizione che
# dipende ovviamente dall'ora (prima, seconda etc.) e dal giorno
# (lunedì, martedì etc.). Supponendo (XXX) che tutti i giorni abbiano
# sei ore di lezione, questi sono gli offset necessari.

DAYS_SHIFT = {"lunedì":     0,
              "martedì":    6,
              "mercoledì": 12,
              "giovedì":   18,
              "venerdì":   24,
              "sabato":    30}

# Nel file di export le lezioni sono conraddistinte dall'ora di
# inizio, in formato HhM, che io voglio convertire in un altro offset.
# Anche qui spero che le ore di inizio siano quelli previste nel
# seguente dizionario (in caso contrario avrei un KeyError e quindi mi
# accorgerei!).

START_SHIFT = {
    "07h50": 0,
    "08h40": 1,
    "09h30": 2,
    "10h30": 3,
    "11h20": 4,
    "12h15": 5,
    "13h10": 6,
    }

def make_lessons_list():
    return [""] * 36

# Nel file di export, il dato AULA è piuttosto logorroico, qualcosa
# del tipo "Aula 3Hsa (2.50)" (quando va bene), me nel tabellone
# voglio qualcosa di più sintetico.

def format_room(room):
    if "(" in room:
        room = room.split("(")[1]
    if ")" in room:
        room = room.split(")")[0]
    return room

# Questo è il dizionario che, per ciascun prof usato come chiave,
# contiene le relative ore di lezione.  Uso defaultdict così "al primo
# giro" ho già una lista stringhe vuote delle lunghezza corretta
# (generata da make_lessons_list).

prof_dict = defaultdict(make_lessons_list)

def go(raw_data):
    with open(raw_data, newline="", encoding="utf-16") as data:
        rows = list(csv.reader(data, delimiter=";"))[1:]
        for r in rows:
            o = Record(*r)
            prof_cod = (o.DOC_COGN, o.DOC_NOME)
            day_cod = DAYS_SHIFT[o.GIORNO] + START_SHIFT[o.ORA_INIZIO]
            room = format_room(o.AULA)
            cell = room + " / " + o.CLASSE
            prof_dict[prof_cod][day_cod] = cell
        for prof_cod, ss in sorted(prof_dict.items()):
            data = list(prof_cod) + ss
            line = ",".join(data)
            print(line)

def usage():
    print("usage: odv.py export-csv-file")

if __name__ == "__main__":

    import sys
    args = sys.argv[1:]
    if len(args) != 1:
        usage()
        sys.exit(1)
    csv_export = args[0]
    go(csv_export)
