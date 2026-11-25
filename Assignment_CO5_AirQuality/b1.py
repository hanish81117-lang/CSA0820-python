"""B1 - Implement and validate the air-quality cleaning pipeline."""
import csv
import io
import os
import random
import sqlite3

# ---------- Complete the Code (given program, TODOs completed) ----------
RAW = """station,date,pm25
Adyar,2026-10-01,48
Adyar,2026-10-02,NA
Adyar,2026-10-03,
Guindy,2026-10-01,95
Guindy,2026-10-02,-5
Guindy,2026-10-03,121
"""


def load_clean(text):
    """Returns (station, date, pm25) tuples for valid, non-negative readings only."""
    rows = []
    # TODO 1 completed: DictReader; skip empty, 'NA' or negative pm25; convert to float
    for row in csv.DictReader(io.StringIO(text)):
        v = row["pm25"].strip()
        if v in ("", "NA"):
            continue
        v = float(v)
        if v < 0 or v > 999:      # added check: skip impossible values above 999
            continue
        rows.append((row["station"], row["date"], v))
    return rows


def min_max(values):
    # TODO 2 completed: scale to 0-1 with (v - min) / (max - min), rounded to 3 decimals
    lo, hi = min(values), max(values)
    return [round((v - lo) / (hi - lo), 3) for v in values]


clean = load_clean(RAW)
print(clean)
print(min_max([pm for _, _, pm in clean]))
extra = RAW + "T Nagar,2026-10-01,1500\n"   # test row for the >999 check
print("1500 row skipped:", load_clean(extra) == clean)

# ---------- the full pipeline on generated messy data ----------
STATIONS = ["Adyar", "Guindy", "T Nagar", "Anna Nagar", "Velachery", "Porur",
            " Tambaram", "Saidapet", "Mylapore", "Perambur", "Sholinganallur", "Chromepet"]
FAHRENHEIT = {"Porur", "Sholinganallur"}
random.seed(21)


def generate():
    rows = []
    for st in STATIONS:
        base = random.uniform(30, 90)
        for day in range(1, 31):
            for hour in range(24):
                pm = base + 25 * (hour in (8, 9, 18, 19)) + random.gauss(0, 12)
                temp_c = random.uniform(24, 36)
                r = random.random()
                if r < 0.02:
                    pm_s = "NA"
                elif r < 0.03:
                    pm_s = ""
                elif r < 0.04:
                    pm_s = "-5"
                elif r < 0.045:
                    pm_s = "1500"
                else:
                    pm_s = f"{pm:.1f}"
                temp = temp_c * 9 / 5 + 32 if st in FAHRENHEIT else temp_c
                rows.append((st, f"2026-10-{day:02d}", hour, pm_s, f"{temp:.1f}"))
    rows.append(rows[100])  # duplicate row
    return rows


raw = generate()
print(f"\ngenerated {len(raw)} raw rows for 12 stations (2 reporting Fahrenheit)")

before = [r for r in raw if r[0] == "Porur"][:2]
print("before (Porur, Fahrenheit):", before)

cleaned, problems = [], {"missing": 0, "impossible": 0, "duplicate": 0, "fahrenheit": 0}
seen = set()
for st, day, hour, pm_s, t_s in raw:
    if pm_s in ("", "NA"):
        problems["missing"] += 1
        continue
    pm = float(pm_s)
    if pm < 0 or pm > 999:
        problems["impossible"] += 1
        continue
    temp = float(t_s)
    if st in FAHRENHEIT:
        temp = (temp - 32) * 5 / 9
        problems["fahrenheit"] += 1
    key = (st, day, hour)
    if key in seen:
        problems["duplicate"] += 1
        continue
    seen.add(key)
    cleaned.append((st, day, hour, pm, round(temp, 1)))

print("after (same readings, Celsius):",
      [(st, d, h, pm, t) for st, d, h, pm, t in cleaned if st == "Porur"][:2])
print(f"clean rows: {len(cleaned)}   removed: {problems}")

# ---------- store in SQLite with executemany ----------
os.makedirs("/tmp/co5", exist_ok=True)
con = sqlite3.connect("/tmp/co5/aq.db")
con.execute("DROP TABLE IF EXISTS readings")
con.execute("""CREATE TABLE readings
               (station TEXT, day TEXT, hour INTEGER, pm25 REAL, temp REAL,
                PRIMARY KEY (station, day, hour))""")
con.executemany("INSERT INTO readings VALUES (?,?,?,?,?)", cleaned)
con.commit()

print("\nSQL answers:")
print(" avg PM2.5 in Adyar in October:",
      round(con.execute("SELECT AVG(pm25) FROM readings WHERE station='Adyar'").fetchone()[0], 1))
print(" worst day (city avg):",
      con.execute("""SELECT day, ROUND(AVG(pm25),1) FROM readings
                     GROUP BY day ORDER BY AVG(pm25) DESC LIMIT 1""").fetchone())
print(" valid readings per station (first 3):",
      con.execute("SELECT station, COUNT(*) FROM readings GROUP BY station LIMIT 3").fetchall())
print(" min-max normalised PM2.5 (first 5):",
      min_max([r[3] for r in cleaned])[:5])
con.close()
