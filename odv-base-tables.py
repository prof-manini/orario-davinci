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

    # Il file mat_out.txt contiene una riga per ciascuna materia con
    # il codice della materia, un segno di uguale come separatore e
    # poi il nome per esteso della materia (come compare nel file di
    # export di EDT). Qualcosa del tipo:
    #
    # DIR = Diritto ed Economia
    # DIS = Disegno e Storia dell'arte
    # FIL = Filosofia
    # ING = Lingua e Cultura Straniera Inglese
    #
    # Questo file può essere usato come base di partenza per creare un
    # altro file da usare come dizionario delle "abbreviazioni".
    # Qualcosa del tipo:
    #
    # DIR = Dir. Eco.
    # DIS = Dis. Arte
    # FIL = Filosofia
    # ING = Inglese

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

    # Il file class_out contiene una riga per classe con il codice
    # della classe, un segno di uguale come separatore e poi le
    # materie di quella classe (le materie in minuscolo solo estratte
    # dalle righe "multiple").  Qualcosa del tipo:
    #
    # 2F = DIS FIS INF ING IRC ITA MAT MOT SCI STG TED
    # 2G = DIS FIS ING IRC ITA LAT MAT MOT SCI STG spa ted
    # 2H = DIS FIS INF ING IRC ITA MAT MOT SCI STG spa ted
    # 2I = DIS FIS ING IRC ITA LAT MAT MOT SCI STG TED

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

    # Il file prof_out.txt contiene una riga per ciascun professore,
    # con cognome e nome (separati da virgola), il solito separatore e
    # poi la lista delle materie insegnate (codice).

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

    # Il file room_out.txt contiene una riga per ciascuna aula, con il
    # nome dell'aula (che in realtà è una descrizione abbastanza
    # logorroica che contiene anche la "sigla" dell'aula, tipo 1.23),
    # il solito separatore e poi la lista delle classi che la
    # utilizzano (che in orario hanno almeno un'ora in quell'aula).
    # Qualcosa del tipo:
    #
    # <Aule per gruppi>Aula proiezioni (0.22) = 3D/I TED ..............
    # <Aule per gruppi>Mediateca (0.45) = 1G/H TED 2G/H  ..............
    # <Lab. Informatica>Lab. Informatica 1 (2° p 2.04) = 1D 1F ........
    # <Palestre>Palestra 2 (Est) = 1A 1D 1I 1N 1P 1R 2F 2Q 3B  ........
    # Aula 1Gs (1.33) = 1G
    #
    # Anche qui sarebbe bene cercare di trovare dei "nomi" più corti e
    # più pratici e creare (magari in parte in modo automatico in
    # parte a mano) un nuovo file con un contenuto del tipo:
    #
    # Proiezioni = (0.22)
    # Lab. Info 1 = (2.04)
    # Palestra 2 (Est) = ???
    # Aula 1G = (1.33)

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
