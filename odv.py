#! /usr/bin/env python3

# author: Luca Manini (luca.manini@liceodavincitn.it)

# Questo programma legge dei dati da un "export" delle lezioni
# (attività) del programma EDT e produce un file CSV con una riga per
# ciascun docente e una colonna per ogni ora di lezione. Ogni cella
# contiene informazioni come per esempio la classe, l'aula o altro.

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

    with open(raw_data, newline="", encoding="utf-16") as data:
        rows = list(csv.reader(data, delimiter=";"))[1:]
        for r in rows:
            o = Record(*r)
            prof_cod = (o.DOC_COGN, o.DOC_NOME)
            room = format_room(o.AULA)
            # cell = room + " / " + o.CLASSE
            cell = room
            size = int(o.DURATA[0]) # 1h00, 2h00 etc
            for i in range(size):
                day_cod = (DAYS_SHIFT[o.GIORNO] +
                           START_SHIFT[o.ORA_INIZIO] +
                           i)
                prof_dict[prof_cod][day_cod] = cell

    return prof_dict

def write_prof_dict_csv(prof_dict, csv_out):

    # Qui scrivo il risultato in un file CSV usando semplicemente un
    # file di testo e relativo metodo "write".  Il modulo csv ha un
    # metodo apposito che però non mi pare offra vantaggi
    # interessanti.

    with open(csv_out, "w") as output:
        for prof_cod, ss in sorted(prof_dict.items()):
            data = list(prof_cod) + ss
            line = ",".join(data)
            output.write(line + "\n")

def write_prof_dict_xls(prof_dict, xsl_out):

    # https://xlsxwriter.readthedocs.io/examples.html
    # https://xlsxwriter.readthedocs.io/format.html#format

    book = xlsxwriter.Workbook(xsl_out)
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

    sheet = book.add_worksheet()
    sheet.set_default_row(20)

    # Scrittura della parte "fissa" di headers
    row = 0
    if True:

        # Titolo: centrato su tutta la larghezza (36 colonne)

        sheet.set_row(row, 24)
        sheet.merge_range(0,0,0,36, "Orario", title_format)
        row += 1

        # Giorni della settimana, presi da DAYS_SHIFT

        sheet.set_row(row, 22)
        days = [s.capitalize() for s in DAYS_SHIFT.keys()]
        for i, s in enumerate(days):
            sheet.merge_range(row, 2 + i * 6,
                              row, 2 + i * 6 + 5,
                              s, days_format)
        row += 1

        # Ore del giorno, prese da START_SHIFT, in cui hanno un
        # formato tipo 07h30 che converto in 7:30.

        sheet.set_row(row, 20)
        for r in range(6):
            for i, s in enumerate(START_SHIFT.keys()):
                if s[0] == "0":
                    s = s[1:]
                s = s.replace("h", ":")
                sheet.write(row, 2 + i + r * 6, s, hours_format)
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
        data = list(prof_cod) + ss
        old = None
        for col, text in enumerate(data):
            if text and text == old:
                sheet.merge_range(row, col-1,
                                  row, col,
                                  text, merge_format)
                old = None
            else:
                sheet.write(row, col, text)
                old = text
    book.close()

def main(csv_in,
         csv_out="output-orario.csv",
         xls_out="output-orario.xls"):

    # Questa funzione è l'entry point del modulo, sia nel senso che è
    # la funzione chiamata nel blocco "if __name__ ..." sia nel senso
    # che è la funzione chiamabile da un altro file dopo aver
    # importato questo come modulo.

    prof_dict = data_to_dict(csv_in)
    write_prof_dict_csv(prof_dict, csv_out)
    write_prof_dict_xls(prof_dict, xls_out)

def usage():
    print("usage: odv.py export-csv-file [output-csv-file]")

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
