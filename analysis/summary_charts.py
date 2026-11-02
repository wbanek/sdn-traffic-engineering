"""Zbiorcze wykresy z wyników pomiarów na Clos - jeden zestaw na koniec serii.

Użycie (z katalogu głównego repozytorium):
    .venv/bin/python analysis/summary_charts.py [katalog_wyjściowy]     # domyślnie results/summary

Źródła to katalogi wyników z `flows.csv`, `timeseries.csv`, `report.md` (po `analyze.py`).
Dla każdej topologii podano listę (katalog, {wariant w danych: wariant na wykresie}); brakujące
warianty są pomijane. Katalogi z `*` oznaczają "najnowszy pasujący".

Rodziny wariantów wariantu C (QoS-Aware):
    L1 (m90..m30)      meter OpenFlow o stałej stawce (100 - R)% łącza + stara bramka wejścia
    L2 (L2r90..L2r30)  to samo + bramka "mieści się" (rezerwacje oczekujące, szacunek rozmiaru przepływu)
    L3 (L3H0..L3H3)    limit tła liczony z mierzonego wideo, meter modyfikowany co 1 s; H = zapas [Mb/s]
"""
import csv
import glob
import json
import os
import re
import statistics as st
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = sys.argv[1] if len(sys.argv) > 1 else "results/summary"

L1 = ["m90", "m70", "m50", "m30"]
L2 = ["L2r90", "L2r70", "L2r50", "L2r30"]
L3 = ["L3H0", "L3H1.5", "L3H3"]
BASE = ["ecmp", "lllb", "qos100"]
ORDER = BASE + L1 + L2 + L3
R_OF = {"qos100": 100, "m90": 90, "m70": 70, "m50": 50, "m30": 30,
        "L2r90": 90, "L2r70": 70, "L2r50": 50, "L2r30": 30}
H_OF = {"L3H0": 0.0, "L3H1.5": 1.5, "L3H3": 3.0}

SOURCES = {
    "Clos": [
        ("results/clos-full/*", {v: v for v in BASE + L1}),
        ("results/clos-layers/*", {v: v for v in L2 + L3}),
    ],
}
# Ta sama rezerwa bez metera (sama bramka wejścia, pomiar z 1.11) - do porównania "z meterem / bez"
NO_METER = ("Clos", "results/reserve-sweep/20261101_180238", {"qos90": "m90", "qos70": "m70", "qos50": "m50"})
# Warianty na wykresie przebiegów czasowych (przy 14 liniach wykres byłby nieczytelny)
LINE_VARIANTS = ["ecmp", "lllb", "qos100", "m70", "L2r70", "L3H1.5"]

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
FAMILY_COLOR = {"ecmp": "#8b8a86", "lllb": "#2a78d6", "qos100": "#eb6834",
                "L1": "#1baf7a", "L2": "#8a63d2", "L3": "#eda100"}


def shade(hex_color, t):
    """Mieszanie z bielą: t = 0 - kolor bazowy, t = 1 - biel."""
    c = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (255 - x) * t) for x in c)


def build_colors():
    """Kolor = rodzina; ciemniejszy odcień = silniejsza ochrona wideo (wyższe R, większy zapas H)."""
    color = {v: FAMILY_COLOR[v] for v in BASE}
    for fam, vs in (("L1", L1), ("L2", L2)):
        for i, v in enumerate(vs):                 # wyższe R -> ciemniej
            color[v] = shade(FAMILY_COLOR[fam], 0.12 * i)
    for i, v in enumerate(reversed(L3)):           # większe H -> ciemniej
        color[v] = shade(FAMILY_COLOR["L3"], 0.12 * i)
    return color


COLOR = build_colors()

FAMILIES = [
    ("ecmp", "ecmp (A: OSPF + ECMP)", "ecmp"),
    ("lllb", "lllb (B: najmniej obciążone łącze)", "lllb"),
    ("qos100", "qos100 (C: pełna rezerwa dla wideo)", "qos100"),
    ("L1", "L1 (C: meter o stałej stawce, m90...m30)", "m90"),
    ("L2", "L2 (C: meter + bramka „mieści się”, L2r90...L2r30)", "L2r90"),
    ("L3", "L3 (C: limit dynamiczny, L3H0...L3H3)", "L3H3"),
]


def label(v):
    if v in R_OF and v != "qos100":
        return "%s (tło ≤ %d%% łącza)" % (v, 100 - R_OF[v])
    if v in H_OF:
        return "%s (zapas %g Mb/s)" % (v, H_OF[v])
    return v


plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.axisbelow": True, "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def resolve(path):
    hits = sorted(glob.glob(path))
    return hits[-1] if hits else None


def num(x):
    return float(x) if x not in ("", None) else None


def mean(xs):
    xs = [x for x in xs if x is not None]
    return st.mean(xs) if xs else None


def sd(xs):
    xs = [x for x in xs if x is not None]
    return st.stdev(xs) if len(xs) > 1 else 0.0


def fmt(v):
    return ("%.2f" % v) if v < 10 else ("%.0f" % v) if v >= 100 else ("%.1f" % v)


def report_rows(d):
    """Wiersze tabeli z sekcji 4 raportu: {(wariant, rep): (średnie obciążenie %, drops)}"""
    out = {}
    p = os.path.join(d, "report.md")
    if not os.path.exists(p):
        return out
    for line in open(p):
        m = re.match(r"\|\s*(\S+)\s*\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*[\d.]+\s*\|\s*\d+/\d+\s*\|\s*(\d+)\s*\|", line)
        if m:
            out[(m.group(1), int(m.group(2)))] = (float(m.group(3)), int(m.group(4)))
    return out


def load(d, wanted):
    """Metryki per (wariant, powtórzenie) z katalogu wyniku."""
    sch = json.load(open(os.path.join(d, "schedule.json")))
    warm = sch["warmup"]
    dur = {(int(r), f["id"]): f["duration"] for r, fl in sch["schedules"].items() for f in fl}
    rows = list(csv.DictReader(open(os.path.join(d, "flows.csv"))))
    rep_rows = report_rows(d)
    res = {}
    for src, dst in wanted.items():
        reps = sorted({int(r["rep"]) for r in rows if r["variant"] == src})
        for rep in reps:
            sel = [r for r in rows if r["variant"] == src and int(r["rep"]) == rep]
            vid = [r for r in sel if r["class"] == "video"]
            bg = [r for r in sel if r["class"] == "background" and r["packets"] != ""
                  and dur.get((rep, r["id"]), 0) > warm]
            pk = sum(float(r["packets"]) for r in bg)
            util, drops = rep_rows.get((src, rep), (None, None))
            res.setdefault(dst, {})[rep] = {
                "vloss": mean([num(r["loss_pct"]) for r in vid]),
                "vjit": mean([num(r["jitter_ms"]) for r in vid]),
                "vrtt": mean([num(r["rtt_p95_ms"]) for r in vid]),
                "bgloss": 100 * sum(float(r["lost_packets"]) for r in bg) / pk if pk else None,
                "util": util, "drops": drops,
            }
    return res


def load_topology(topo):
    data = {}
    used = []
    for path, wanted in SOURCES[topo]:
        d = resolve(path)
        if not d or not os.path.exists(os.path.join(d, "flows.csv")):
            print("  pominięto (brak danych):", path)
            continue
        used.append(d)
        data.update(load(d, wanted))
    return data, used


def series(data, v, key):
    return [data[v][r][key] for r in sorted(data[v]) if data[v][r][key] is not None]


def family_legend(fig, variants, **kw):
    handles, labels = [], []
    for fam, text, rep_v in FAMILIES:
        if rep_v in variants:
            handles.append(plt.Rectangle((0, 0), 1, 1, color=COLOR[rep_v]))
            labels.append(text)
    fig.legend(handles, labels, frameon=False, fontsize=9, **kw)


# ---------------------------------------------------------------- wykresy słupkowe
PANELS = [
    ("vloss", "Utrata pakietów wideo", "%", False, 1.0),
    ("vjit", "Jitter wideo", "ms", False, 1.0),
    ("vrtt", "Opóźnienie wideo (RTT, p95)", "ms, skala log.", True, 1.0),
    ("bgloss", "Utrata pakietów ruchu tła", "%", False, 1.0),
    ("drops", "Pakiety odrzucone na łączach", "tys. na serię", False, 1e-3),
    ("util", "Średnie obciążenie łączy", "%", False, 1.0),
]


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=170)
    plt.close(fig)
    return p


SLUG = {"vloss": "utrata_wideo", "vjit": "jitter_wideo", "vrtt": "rtt_wideo",
        "bgloss": "utrata_tla", "drops": "odrzucenia", "util": "obciazenie"}
NOTE = {"drops": "Suma z powtórzeń", "vrtt": "Mediana z powtórzeń (oś logarytmiczna)"}


def bars_figure(topo, data, n_reps):
    """Każdy parametr to osobny plik: slupkowe_<parametr>.png"""
    variants = [v for v in ORDER if v in data]
    paths = []
    for key, title, unit, log, scale in PANELS:
        fig, ax = plt.subplots(figsize=(8.8, 5.6))
        xs = range(len(variants))
        vals, errs = [], []
        for v in variants:
            s = [x * scale for x in series(data, v, key)]
            if key == "drops":
                vals.append(sum(s) if s else 0)       # suma z powtórzeń
                errs.append(0)
            elif key == "vrtt":
                vals.append(st.median(s) if s else 0)  # mediana z powtórzeń
                errs.append(0)
            else:
                vals.append(mean(s) or 0)
                errs.append(sd(s))
        ax.bar(xs, vals, width=0.7, color=[COLOR[v] for v in variants],
               yerr=None if log or key == "drops" else errs,
               error_kw=dict(ecolor=INK2, elinewidth=1, capsize=2.5), zorder=3)
        if log:
            ax.set_yscale("log")
            ax.set_ylim(0.02, 400)
        top = max((v + e) for v, e in zip(vals, errs)) if vals else 1
        for i, (v, e) in enumerate(zip(vals, errs)):
            if log:
                ax.text(i, v * 1.25, fmt(v), ha="center", va="bottom", fontsize=8, color=INK2)
            else:
                ax.text(i, v + e + top * 0.02, fmt(v), ha="center", va="bottom", fontsize=8, color=INK2)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(variants, fontsize=9, rotation=50, ha="right")
        ax.set_ylabel(unit)
        ax.grid(axis="x", visible=False)
        if not log:
            ax.set_ylim(0, top * 1.2 if top else 1)
        family_legend(fig, variants, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.0))
        fig.suptitle("%s - topologia %s" % (title, topo), x=0.01, ha="left", fontsize=12.5, fontweight="bold")
        fig.text(0.01, 0.905, NOTE.get(key, "Średnia ± odchylenie standardowe z %d powtórzeń" % n_reps),
                 fontsize=9, color=INK2)
        fig.tight_layout(rect=(0, 0.17, 1, 0.9))
        paths.append(save(fig, "slupkowe_%s.png" % SLUG[key]))
    return paths


# ---------------------------------------------------------------- krzywe R i H
def curves_figure(topo, data):
    """Utrata wideo i tła: L1 i L2 w funkcji rezerwy R (z qos100 jako R = 100), L3 w funkcji zapasu H.
    Dwa pliki (wideo, tło); w każdym lewy panel = R, prawy = H, wspólna oś Y."""
    refs = [("ecmp", "--"), ("lllb", "--"), ("qos100", ":")]
    paths = []
    for key, ylab, slug in (("vloss", "Utrata pakietów wideo [%]", "utrata_wideo"),
                            ("bgloss", "Utrata pakietów ruchu tła [%]", "utrata_tla")):
        fig, (left, right) = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True, gridspec_kw={"width_ratios": [1.5, 1]})
        for fam, vs, dx in (("L1", L1, -0.9), ("L2", L2, 0.9)):
            group = [v for v in ["qos100"] + vs if v in data]
            if len(group) < 2:
                continue
            xs = [R_OF[v] + dx for v in group]
            ms = [mean(series(data, v, key)) for v in group]
            ss = [sd(series(data, v, key)) for v in group]
            left.errorbar(xs, ms, yerr=ss, color=FAMILY_COLOR[fam], marker="o", ms=6, lw=2, capsize=3,
                          elinewidth=1, label=fam)
        group = [v for v in L3 if v in data]
        if group:
            xs = [H_OF[v] for v in group]
            ms = [mean(series(data, v, key)) for v in group]
            ss = [sd(series(data, v, key)) for v in group]
            right.errorbar(xs, ms, yerr=ss, color=FAMILY_COLOR["L3"], marker="o", ms=6, lw=2, capsize=3,
                           elinewidth=1, label="L3")
        for ax in (left, right):
            for v, ls in refs:
                if v in data:
                    m = mean(series(data, v, key))
                    ax.axhline(m, color=FAMILY_COLOR[v], ls=ls, lw=1.4, zorder=1)
                    ax.text(1.0, m, " " + v, transform=ax.get_yaxis_transform(), ha="left", va="center",
                            fontsize=8.5, color=FAMILY_COLOR[v])
        left.set_ylabel(ylab)
        left.invert_xaxis()
        left.set_xticks([100, 90, 70, 50, 30])
        left.set_title("L1 i L2 w funkcji rezerwy R")
        right.set_title("L3 w funkcji zapasu H")
        left.set_xlabel("R: część łącza rezerwy zachowana dla wideo [%] (100 = pełna rezerwa)")
        right.set_xlabel("H: zapas na nowe wideo [Mb/s]")
        right.set_xticks([0, 1.5, 3])
        left.set_ylim(bottom=-0.4 if key == "vloss" else 0)     # punkty na 0% nie leżą na krawędzi osi
        handles, labels = left.get_legend_handles_labels()
        h3, l3 = right.get_legend_handles_labels()
        names = {"L1": "L1 (stały meter)", "L2": "L2 (meter + bramka)", "L3": "L3 (limit dynamiczny)"}
        fig.legend(handles + h3, [names[x] for x in labels + l3], frameon=False, fontsize=9.5,
                   loc="lower center", ncol=3)
        fig.suptitle("%s - topologia %s" % (ylab.split(" [")[0], topo), x=0.01, ha="left",
                     fontsize=12.5, fontweight="bold")
        fig.text(0.01, 0.912, "Średnia ± odchylenie standardowe; linie przerywane: warianty odniesienia",
                 fontsize=9, color=INK2)
        fig.tight_layout(rect=(0, 0.06, 0.97, 0.9))
        paths.append(save(fig, "krzywa_%s.png" % slug))
    return paths


# ---------------------------------------------------------------- kompromis wideo / tło
def tradeoff_figure(topo, data):
    fig, ax = plt.subplots(figsize=(10.5, 6.2))
    ax.set_yscale("symlog", linthresh=2)
    for v in [v for v in ORDER if v in data]:
        x, y = series(data, v, "bgloss"), series(data, v, "vloss")
        ax.scatter(x, y, s=16, color=COLOR[v], alpha=0.28, zorder=2, linewidths=0)       # powtórzenia
    for fam, vs in (("L1", L1), ("L2", L2), ("L3", L3)):
        group = [v for v in vs if v in data]
        if len(group) > 1:
            ax.plot([mean(series(data, v, "bgloss")) for v in group],
                    [mean(series(data, v, "vloss")) for v in group],
                    color=FAMILY_COLOR[fam], lw=1.2, alpha=0.7, zorder=2)
    for v in [v for v in ORDER if v in data]:
        mx, my = mean(series(data, v, "bgloss")), mean(series(data, v, "vloss"))
        ax.scatter([mx], [my], s=120, color=COLOR[v], edgecolor=SURFACE, linewidths=1.8, zorder=4)
        if v in ("ecmp", "lllb"):
            txt, off = v, (9, 7)
        elif v == "qos100":
            txt, off = v, (-14, 70)
        elif v in H_OF:        # etykiety L3 na różnych wysokościach, żeby nie nachodziły
            txt, off = "H=%g" % H_OF[v], [(-10, 22), (0, 40), (12, 58)][L3.index(v)]
        elif v in L2:
            txt, off = "L2 R=%d" % R_OF[v], {90: (30, -34), 70: (-34, -34), 50: (12, -26), 30: (-44, -22)}[R_OF[v]]
        else:
            txt, off = "R=%d" % R_OF[v], (8, 22)
        ax.annotate(txt, (mx, my), textcoords="offset points", xytext=off, fontsize=8.5, color=INK2,
                    arrowprops=dict(arrowstyle="-", color=INK2, lw=0.5, shrinkA=0, shrinkB=4) if v not in ("ecmp", "lllb") else None)
    ax.set_xlabel("Utrata pakietów ruchu tła [%]  (koszt)")
    ax.set_ylabel("Utrata pakietów wideo [%]  (ochrona; skala symlog)")
    ax.set_yticks([0, 0.5, 1, 2, 5, 10, 20])
    ax.set_yticklabels(["0", "0,5", "1", "2", "5", "10", "20"])
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=-0.9)
    ax.set_title("Topologia %s: kompromis ochrona wideo / koszt dla tła" % topo)
    family_legend(fig, [v for v in ORDER if v in data], loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.0))
    fig.text(0.01, 0.14, "Duży znacznik = średnia z powtórzeń, małe = pojedyncze powtórzenia. Lewy dolny róg = najlepiej "
             "(wideo chronione i tło prawie nie traci).", fontsize=8.5, color=INK2)
    fig.tight_layout(rect=(0, 0.18, 1, 1))
    return [save(fig, "kompromis.png")]


# ---------------------------------------------------------------- przebiegi uśrednione
def timeseries(d, wanted):
    """Średnie po powtórzeniach i strumieniach, na siatce 1 s: wideo (przepływność, jitter) i suma tła."""
    sch = json.load(open(os.path.join(d, "schedule.json")))
    cls = {(int(r), f["id"]): f["class"] for r, fl in sch["schedules"].items() for f in fl}
    vid = defaultdict(lambda: defaultdict(list))       # wariant -> t -> [przepływność wideo]
    jit = defaultdict(lambda: defaultdict(list))
    bg = defaultdict(lambda: defaultdict(float))       # (wariant, rep) -> t -> suma tła
    for r in csv.DictReader(open(os.path.join(d, "timeseries.csv"))):
        if r["variant"] not in wanted:
            continue
        v, rep, t = wanted[r["variant"]], int(r["rep"]), round(float(r["t"]))
        c = cls.get((rep, r["id"]))
        thr = num(r["throughput_mbps"])
        if c == "video":
            if thr is not None:
                vid[v][t].append(thr)
            j = num(r["jitter_ms"])
            if j is not None:
                jit[v][t].append(j)
        elif c == "background" and thr is not None:
            bg[(v, rep)][t] += thr
    bgm = defaultdict(lambda: defaultdict(list))
    for (v, rep), per_t in bg.items():
        for t, s in per_t.items():
            bgm[v][t].append(s)
    return vid, jit, bgm


def smooth(ts, vals, k=3):
    out = []
    for i in range(len(vals)):
        w = vals[max(0, i - k // 2): i + k // 2 + 1]
        out.append(sum(w) / len(w))
    return out


def lines_figure(topo, dirs):
    """Trzy pliki: przepływność wideo, jitter wideo, przepływność ruchu tła (przebiegi uśrednione)."""
    rows = [("Przepływność wideo [Mb/s]", 0, "przebieg_wideo_przeplywnosc"),
            ("Jitter wideo [ms]", 1, "przebieg_wideo_jitter"),
            ("Przepływność ruchu tła, suma [Mb/s]", 2, "przebieg_tlo_przeplywnosc")]
    agg = [defaultdict(lambda: defaultdict(list)) for _ in range(3)]
    for d, wanted in dirs:
        vid, jit, bgm = timeseries(d, {k: v for k, v in wanted.items() if v in LINE_VARIANTS})
        for i, src in enumerate((vid, jit, bgm)):
            for v, per_t in src.items():
                for t, xs in per_t.items():
                    agg[i][v][t] += xs
    paths = []
    for (title, i, slug) in rows:
        fig, ax = plt.subplots(figsize=(10, 5.4))
        for v in [v for v in LINE_VARIANTS if v in agg[i]]:
            ts = sorted(t for t in agg[i][v] if 0 <= t <= 60)
            vals = smooth(ts, [mean(agg[i][v][t]) for t in ts])
            ax.plot(ts, vals, color=COLOR[v], lw=2, label=v, solid_capstyle="round")
        ax.set_ylabel(title)
        ax.set_xlabel("czas od startu scenariusza [s]")
        if i == 0:
            ax.set_ylim(2.0, 3.1)        # oś skrócona, żeby różnice były czytelne (zadane 3 Mb/s)
        else:
            ax.set_ylim(bottom=0)
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, [label(v) if v != "qos100" else "qos100 (C: pełna rezerwa)" for v in labels],
                   loc="lower center", ncol=3, frameon=False, fontsize=9)
        fig.suptitle("%s - topologia %s" % (title.split(" [")[0], topo), x=0.01, ha="left",
                     fontsize=12.5, fontweight="bold")
        fig.text(0.01, 0.905, "Średnia z powtórzeń i strumieni, średnia ruchoma z 3 s", fontsize=9, color=INK2)
        fig.tight_layout(rect=(0, 0.11, 1, 0.9))
        paths.append(save(fig, "%s.png" % slug))
    return paths


# ---------------------------------------------------------------- z meterem / bez
def meter_figure(clos_data):
    """Dwa pliki: wideo i tło, rezerwa z meterem (L1) i bez niego (sama bramka wejścia)."""
    topo, d, mapping = NO_METER
    d = resolve(d)
    shown = [v for v in L1 if v in clos_data and v in mapping.values()]
    if not d or not shown:
        return []
    nom = load(d, mapping)          # klucze: m90 / m70 / m50 (zmierzone bez metera)
    paths = []
    for key, title, unit, slug in (("vloss", "Utrata pakietów wideo", "%", "wideo"),
                                   ("bgloss", "Utrata pakietów ruchu tła", "%", "tlo")):
        fig, ax = plt.subplots(figsize=(7.6, 5.2))
        w = 0.36
        top = 0
        for i, v in enumerate(shown):
            if v not in nom:
                continue
            for j, (src, lab, hatch) in enumerate(((nom, "bez metera (tylko bramka wejścia)", "////"),
                                                   (clos_data, "z meterem (L1)", None))):
                s = series(src, v, key)
                x = i + (j - 0.5) * w
                top = max(top, mean(s) + sd(s))
                ax.bar(x, mean(s), width=w * 0.92, color=COLOR[v], hatch=hatch,
                       edgecolor=SURFACE if not hatch else INK2, linewidth=0.8, yerr=sd(s),
                       error_kw=dict(ecolor=INK2, elinewidth=1, capsize=3),
                       label=lab if i == 0 else None, zorder=3)
        for i, v in enumerate(shown):
            for j, src in enumerate((nom, clos_data)):
                if v in src:
                    s = series(src, v, key)
                    ax.text(i + (j - 0.5) * w, mean(s) + sd(s) + top * 0.02, "%.1f" % mean(s),
                            ha="center", fontsize=9, color=INK2)
        ax.set_xticks(range(len(shown)))
        ax.set_xticklabels(["R = %d%%" % R_OF[v] for v in shown])
        ax.set_ylim(0, top * 1.18 if top else 1)
        ax.set_ylabel(unit)
        ax.grid(axis="x", visible=False)
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, frameon=False, fontsize=9.5, loc="lower center", ncol=2)
        fig.suptitle("%s: rezerwa z meterem i bez niego - topologia Clos" % title, x=0.01, ha="left",
                     fontsize=12, fontweight="bold")
        fig.text(0.01, 0.905, "Średnia ± odchylenie standardowe z 5 powtórzeń", fontsize=9, color=INK2)
        fig.tight_layout(rect=(0, 0.09, 1, 0.9))
        paths.append(save(fig, "metery_vs_bez_%s.png" % slug))
    return paths


# ---------------------------------------------------------------- eksport danych do CSV
METRICS = [("vloss", "wideo_utrata_pct"), ("vjit", "wideo_jitter_ms"), ("vrtt", "wideo_rtt_p95_ms"),
           ("bgloss", "tlo_utrata_pct"), ("drops", "odrzucone_pakiety"), ("util", "obciazenie_lacz_pct")]


def family_of(v):
    return "L1" if v in L1 else "L2" if v in L2 else "L3" if v in L3 else v


def export_csv(topo, data, dirs):
    """Trzy pliki CSV z danymi do własnych wykresów: powtórzenia, podsumowanie, przebiegi czasowe."""
    prefix = "dane_%s" % topo.lower()
    variants = [v for v in ORDER if v in data]
    paths = []

    p = os.path.join(OUT, prefix + "_powtorzenia.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wariant", "rodzina", "R_pct", "H_mbps", "powtorzenie"] + [n for _, n in METRICS])
        for v in variants:
            for rep in sorted(data[v]):
                w.writerow([v, family_of(v), R_OF.get(v, ""), H_OF.get(v, ""), rep] +
                           [data[v][rep][k] if data[v][rep][k] is not None else "" for k, _ in METRICS])
    paths.append(p)

    p = os.path.join(OUT, prefix + "_podsumowanie.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        head = ["wariant", "rodzina", "R_pct", "H_mbps", "powtorzenia"]
        for _, n in METRICS:
            head += [n + "_srednia", n + "_sd"]
        w.writerow(head)
        for v in variants:
            row = [v, family_of(v), R_OF.get(v, ""), H_OF.get(v, ""), len(data[v])]
            for k, _ in METRICS:
                xs = series(data, v, k)
                row += [round(mean(xs), 4) if xs else "", round(sd(xs), 4) if xs else ""]
            w.writerow(row)
    paths.append(p)

    agg = [defaultdict(lambda: defaultdict(list)) for _ in range(3)]
    for d, wanted in dirs:
        vid, jit, bgm = timeseries(d, {k: v for k, v in wanted.items() if v in LINE_VARIANTS})
        for i, src in enumerate((vid, jit, bgm)):
            for v, per_t in src.items():
                for t, xs in per_t.items():
                    agg[i][v][t] += xs
    p = os.path.join(OUT, prefix + "_przebiegi_czasowe.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wariant", "t_s", "wideo_przeplywnosc_mbps", "wideo_jitter_ms", "tlo_przeplywnosc_suma_mbps"])
        for v in LINE_VARIANTS:
            ts = sorted(set(agg[0][v]) | set(agg[1][v]) | set(agg[2][v]))
            for t in ts:
                w.writerow([v, t] + [round(mean(agg[i][v][t]), 4) if agg[i][v].get(t) else "" for i in range(3)])
    paths.append(p)
    return paths


def main():
    os.makedirs(OUT, exist_ok=True)
    outputs = []
    for topo in SOURCES:
        print("Topologia", topo)
        data, used = load_topology(topo)
        if not data:
            continue
        n = max(len(r) for r in data.values())
        outputs += bars_figure(topo, data, n)
        outputs += curves_figure(topo, data)
        outputs += tradeoff_figure(topo, data)
        dirs = [(resolve(path), wanted) for path, wanted in SOURCES[topo]
                if resolve(path) and os.path.exists(os.path.join(resolve(path), "timeseries.csv"))]
        outputs += lines_figure(topo, dirs)
        outputs += export_csv(topo, data, dirs)
        if topo == "Clos":
            outputs += meter_figure(data)
    print("Zapisano:")
    for p in outputs:
        print(" ", p)


if __name__ == "__main__":
    main()
