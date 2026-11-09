"""Eksport wyników pomiarów do Excela (.xlsx): jeden plik, wiele arkuszy.

Użycie (z katalogu głównego repozytorium):
    .venv/bin/python analysis/export_excel.py <katalog_wyniku> [<katalog_wyniku> ...] [-o plik.xlsx]

Katalog wyniku to taki, w którym `analyze.py` zapisał `flows.csv`, `timeseries.csv`, `links.csv`
i `report.md`. Domyślny plik wyjściowy: `<katalog_wyniku>/dane_excel.xlsx` (dla jednego katalogu)
albo `dane_excel.xlsx` w bieżącym katalogu (dla kilku). Liczby zapisywane są jako liczby, więc
nie ma problemu z przecinkiem dziesiętnym w polskim Excelu.

Arkusze: opis, podsumowanie (średnia, odchylenie, przedział ufności 95%, mediana), powtorzenia,
strumienie, przebiegi_usrednione, timeseries_surowe, lacza, harmonogram.
"""
import csv
import json
import os
import re
import statistics as st
import sys
from collections import defaultdict

import openpyxl
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv, sys.argv = sys.argv, [sys.argv[0]]
import summary_charts as S   # noqa: E402  (load, timeseries, report_rows)
sys.argv = _argv

# wartości krytyczne rozkładu t (dwustronnie, 95%) dla df = 1..30
T975 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228, 2.201, 2.179,
        2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086, 2.080, 2.074, 2.069, 2.064,
        2.060, 2.056, 2.052, 2.048, 2.045, 2.042]

METRICS = [("vloss", "wideo_utrata_pct"), ("vjit", "wideo_jitter_ms"), ("vrtt", "wideo_rtt_p95_ms"),
           ("bgloss", "tlo_utrata_pct"), ("drops", "odrzucone_pakiety"), ("util", "obciazenie_lacz_pct")]

README = [
    ("Plik", "Wyniki pomiarów do własnych wykresów i obliczeń; wygenerowany przez analysis/export_excel.py"),
    ("Metoda", "Każde powtórzenie ma inny, losowy harmonogram ruchu tła (seed + numer powtórzenia), wspólny dla "
              "wszystkich wariantów w danym powtórzeniu; wideo: 2 strumienie UDP DSCP 46."),
    ("", ""),
    ("Arkusz", "Zawartość"),
    ("podsumowanie", "Jeden wiersz na wariant: n, średnia, odchylenie standardowe (sd), przedział ufności 95% "
                    "średniej (rozkład t), mediana, min, maks dla każdej metryki."),
    ("sparowane", "Różnice wariant − odniesienie (ecmp, lllb, qos100, L3H1.5) liczone w parach: to samo powtórzenie, ten sam "
                  "harmonogram; średnia różnica, sd, przedział ufności 95%. Przedział bez zera = różnica istotna."),
    ("powtorzenia", "Jeden wiersz na wariant i powtórzenie: metryki zagregowane (z nich liczone jest podsumowanie)."),
    ("strumienie", "Jeden wiersz na strumień (flows.csv): przepływność, jitter, utrata, RTT, ścieżka."),
    ("przebiegi_usrednione", "Średnie po powtórzeniach co 1 s: wideo (przepływność, jitter) i suma tła."),
    ("timeseries_surowe", "Pomiary co 1 s dla każdego strumienia i powtórzenia (timeseries.csv)."),
    ("lacza", "Przepustowość i obciążenie łączy fabric co 1 s (links.csv)."),
    ("harmonogram", "Harmonogram ruchu w każdym powtórzeniu (kto, do kogo, ile, od kiedy)."),
    ("", ""),
    ("Metryka", "Definicja"),
    ("wideo_utrata_pct", "Średnia z utraty pakietów dwóch strumieni wideo [%] (raport serwera iperf3)."),
    ("wideo_jitter_ms", "Średni jitter strumieni wideo [ms] (raport serwera iperf3)."),
    ("wideo_rtt_p95_ms", "95. percentyl RTT z ping (DSCP 46) między hostami wideo [ms]; w SDN może iść inną ścieżką."),
    ("tlo_utrata_pct", "Σ utraconych / Σ wysłanych datagramów po strumieniach tła dłuższych niż warmup [%]."),
    ("odrzucone_pakiety", "Pakiety odrzucone na łączach fabric (liczniki tc) w jednym przebiegu."),
    ("obciazenie_lacz_pct", "Średnie obciążenie łączy fabric [%] względem 10 Mb/s."),
    ("Kotwice", "qos100_ref = kotwica z części 2 serii SDN, qos100_ref_2 = ta sama konfiguracja z serii OpenQoS (kontrola, "
               "że zmiany kodu nie wpłynęły na B/C); L3H1.5_ref = kotwica z serii OpenQoS."),
    ("Uwaga", "Metryki UDP pochodzą z raportu serwera (odbiorcy). Pomiary skalowane: łącza 10 Mb/s odpowiadają "
              "łączom 10 Gb/s, więc wartości opóźnień w ms nie przenoszą się wprost na rzeczywiste DC."),
]


def conv(x):
    """Tekst z CSV -> liczba (int/float), pusty -> None, reszta bez zmian."""
    if x is None or x == "":
        return None
    if re.fullmatch(r"-?\d+", x):
        return int(x)
    try:
        return float(x)
    except ValueError:
        return x


def read_csv(path):
    with open(path, newline="") as f:
        r = csv.reader(f)
        head = next(r)
        return head, [[conv(c) for c in row] for row in r]


def stats(xs):
    xs = [x for x in xs if x is not None]
    n = len(xs)
    if not n:
        return [0] + [None] * 7
    m = st.mean(xs)
    sd = st.stdev(xs) if n > 1 else None
    if n > 1:
        t = T975[n - 2] if n - 1 <= 30 else (2.0 if n - 1 <= 60 else 1.96)
        half = t * sd / n ** 0.5
        lo, hi = m - half, m + half
    else:
        lo = hi = None
    return [n, m, sd, lo, hi, st.median(xs), min(xs), max(xs)]


def write_sheet(wb, name, head, rows, widths=None):
    ws = wb.create_sheet(name)
    ws.append(head)
    for row in rows:
        ws.append(row)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = ws.dimensions
    for i, h in enumerate(head, 1):
        ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, max(11, min(len(str(h)) + 2, 28)))
    return ws


def main():
    args = sys.argv[1:]
    out = None
    if "-o" in args:
        i = args.index("-o")
        out = args[i + 1]
        args = args[:i] + args[i + 2:]
    dirs = [a.rstrip("/") for a in args]
    if not dirs:
        raise SystemExit(__doc__)
    if out is None:
        out = os.path.join(dirs[0], "dane_excel.xlsx") if len(dirs) == 1 else "dane_excel.xlsx"

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    ws = wb.create_sheet("opis")
    for a, b in README:
        ws.append([a, b])
    ws.append([])
    ws.append(["Źródła", ""])
    for d in dirs:
        sch = json.load(open(os.path.join(d, "schedule.json")))
        ws.append([d, "seed %s, %s powtórzeń, %s s, warmup %s s, warianty: %s" % (
            sch["seed"], sch["repetitions"], sch["duration"], sch["warmup"],
            ", ".join(v["name"] for v in sch["variants"]))])
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        if row[0].value in ("Arkusz", "Metryka", "Źródła"):
            for c in row:
                c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 120

    rep_head = ["zrodlo", "wariant", "powtorzenie"] + [n for _, n in METRICS]
    rep_rows, flows_rows, ts_rows, link_rows, sched_rows, avg_rows = [], [], [], [], [], []
    flows_head = ts_head = link_head = None
    data = {}
    taken = set()
    for d in dirs:
        sch = json.load(open(os.path.join(d, "schedule.json")))
        orig = [v["name"] for v in sch["variants"]]
        # ta sama nazwa wariantu w kilku katalogach (np. kotwica qos100_ref) -> kolejne dostają przyrostek _2, _3...
        rename = {}
        for v in orig:
            k, new = 1, v
            while new in taken:
                k += 1
                new = "%s_%d" % (v, k)
            taken.add(new)
            rename[v] = new
        names = [rename[v] for v in orig]
        part = S.load(d, rename)
        for v in names:
            for rep in sorted(part.get(v, {})):
                m = part[v][rep]
                rep_rows.append([d, v, rep] + [m[k] for k, _ in METRICS])
            data.setdefault(v, {}).update(part.get(v, {}))
        h, rows = read_csv(os.path.join(d, "flows.csv"))
        flows_head = ["zrodlo"] + h
        flows_rows += [[d] + r for r in rows]
        h, rows = read_csv(os.path.join(d, "timeseries.csv"))
        ts_head = ["zrodlo"] + h
        ts_rows += [[d] + r for r in rows]
        h, rows = read_csv(os.path.join(d, "links.csv"))
        link_head = ["zrodlo"] + h
        link_rows += [[d] + r for r in rows]
        for rep, fl in sch["schedules"].items():
            for f in fl:
                sched_rows.append([d, int(rep), f["id"], f["class"], f["src"], f["dst"], f["proto"],
                                   f["rate_bps"] / 1e6 if f.get("rate_bps") else None, f["dscp"],
                                   f["start"], f["duration"], f["port"]])
        vid, jit, bgm = S.timeseries(d, rename)
        for v in names:
            for t in sorted(set(vid[v]) | set(jit[v]) | set(bgm[v])):
                avg_rows.append([d, v, t] + [round(S.mean(src[v][t]), 4) if src[v].get(t) else None
                                              for src in (vid, jit, bgm)])

    # podsumowanie
    sum_head = ["wariant"]
    for _, n in METRICS:
        sum_head += ["%s_%s" % (n, s) for s in ("n", "srednia", "sd", "ci95_dol", "ci95_gora", "mediana", "min", "maks")]
    sum_rows = []
    for v in data:
        row = [v]
        for k, _ in METRICS:
            row += stats([data[v][r][k] for r in sorted(data[v])])
        sum_rows.append(row)
    write_sheet(wb, "podsumowanie", sum_head, sum_rows)

    # różnice sparowane (to samo powtórzenie = ten sam harmonogram): wariant - odniesienie
    pair_rows = []
    for ref in ("ecmp", "lllb", "qos100", "L3H1.5"):
        for v in data:
            if v == ref or ref not in data:
                continue
            reps = sorted(set(data[v]) & set(data[ref]))
            for k, n in METRICS[:4] + METRICS[5:]:
                diffs = [data[v][r][k] - data[ref][r][k] for r in reps
                         if data[v][r][k] is not None and data[ref][r][k] is not None]
                if len(diffs) > 1:
                    pair_rows.append([v, ref, n] + stats(diffs)[:5])
    write_sheet(wb, "sparowane", ["wariant", "odniesienie", "metryka", "n", "srednia_roznica", "sd",
                                  "ci95_dol", "ci95_gora"], pair_rows)
    write_sheet(wb, "powtorzenia", rep_head, rep_rows)
    write_sheet(wb, "strumienie", flows_head, flows_rows, {"path": 44, "zrodlo": 36})
    write_sheet(wb, "przebiegi_usrednione",
                ["zrodlo", "wariant", "t_s", "wideo_przeplywnosc_mbps", "wideo_jitter_ms", "tlo_suma_mbps"], avg_rows)
    write_sheet(wb, "timeseries_surowe", ts_head, ts_rows)
    write_sheet(wb, "lacza", link_head, link_rows)
    write_sheet(wb, "harmonogram",
                ["zrodlo", "powtorzenie", "id", "klasa", "src", "dst", "proto", "przeplywnosc_mbps", "dscp",
                 "start_s", "czas_s", "port"], sched_rows)
    wb.save(out)
    print("Zapisano:", out)
    for ws in wb.worksheets:
        print("  %-22s %6d wierszy" % (ws.title, ws.max_row - 1))


if __name__ == "__main__":
    main()
