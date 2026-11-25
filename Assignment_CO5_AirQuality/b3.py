"""B3 - Loops vs libraries vs SQL: daily mean PM2.5 per station."""
import cProfile
import csv
import io
import pstats
import random
import sqlite3
import statistics
import time

import pandas as pd

random.seed(8)


def make_csv(n_stations, days=365):
    """About 8,760 hourly rows per station (24 per day x 365)."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["station", "date", "hour", "pm25"])
    for s in range(n_stations):
        base = random.uniform(30, 90)
        for d in range(1, days + 1):
            for h in range(24):
                w.writerow([f"Station{s:03d}", f"2026-01-{(d - 1) % 28 + 1:02d}", h,
                            f"{base + random.gauss(0, 10):.1f}"])
    return out.getvalue()


def means_loops(text):
    sums, counts = {}, {}
    for row in csv.DictReader(io.StringIO(text)):
        key = (row["station"], row["date"])
        v = float(row["pm25"])
        sums[key] = sums.get(key, 0.0) + v
        counts[key] = counts.get(key, 0) + 1
    return {k: sums[k] / counts[k] for k in sums}


def means_pandas(text):
    df = pd.read_csv(io.StringIO(text))
    g = df.groupby(["station", "date"])["pm25"].mean()
    return {k: float(v) for k, v in g.items()}


def means_sql(text):
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE r (station TEXT, day TEXT, hour INTEGER, pm25 REAL)")
    con.executemany("INSERT INTO r VALUES (?,?,?,?)", csv.reader(io.StringIO(text)))
    con.execute("DELETE FROM r WHERE station='station'")
    res = {(s, d): m for s, d, m in con.execute(
        "SELECT station, day, AVG(pm25) FROM r GROUP BY station, day")}
    con.close()
    return res


small = make_csv(2, days=30)
a, b, c = means_loops(small), means_pandas(small), means_sql(small)
agree = all(abs(a[k] - b[k]) < 1e-6 and abs(a[k] - c[k]) < 1e-6 for k in a)
print(f"three methods on {len(a)} station-days: all agree -> {agree}")

print("\nstations  rows        loops(s)  pandas(s)  sql(s)")
sizes = {}
for n in (1, 12, 120):
    text = make_csv(n)
    rows = text.count("\n") - 1
    t0 = time.perf_counter(); means_loops(text); t1 = time.perf_counter()
    means_pandas(text); t2 = time.perf_counter()
    means_sql(text); t3 = time.perf_counter()
    sizes[n] = (rows, t1 - t0, t2 - t1, t3 - t2)
    print(f"{n:>7}  {rows:>9,}  {t1 - t0:>8.3f}  {t2 - t1:>8.3f}  {t3 - t2:>6.3f}")

print("\ncProfile of the plain-Python version, 12 stations:")
prof = cProfile.Profile()
prof.enable()
means_loops(make_csv(12))
prof.disable()
st = pstats.Stats(prof)
st.sort_stats("cumulative")
top = sorted(st.stats.items(), key=lambda kv: -kv[1][3])[:4]
for func, (cc, nc, tt, ct, callers) in top:
    print(f"  {tt:6.3f}s total  {nc:>9,} calls  {func[2]}")
