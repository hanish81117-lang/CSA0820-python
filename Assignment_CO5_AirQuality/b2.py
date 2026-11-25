"""B2 - Engineer adversarial data: broken files, SQL injection, tricky sentiment."""
import csv
import io
import sqlite3

# ---------- Complete the Code (given program, TODOs completed) ----------
readings = [("Adyar", "2026-10-01", 48.0), ("Guindy", "2026-10-01", 95.0),
            ("Guindy", "2026-10-03", 121.0), ("Adyar", "2026-10-04", 60.0)]

con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
# TODO 1 completed: ONE executemany call with ? placeholders, then commit
con.executemany("INSERT INTO aq VALUES (?,?,?)", readings)
con.commit()


def station_average(name):
    # TODO 2 completed: parameterised SELECT ... WHERE station = ?
    row = con.execute("SELECT AVG(pm25) FROM aq WHERE station = ?", (name,)).fetchone()
    return row[0]


print(station_average("Adyar"), station_average("Guindy"))
print(station_average("Adyar' OR '1'='1"))   # an injection attempt finds nothing

# ---------- injection: string building vs placeholder ----------
evil = "Adyar' OR '1'='1"
q = "SELECT station, pm25 FROM aq WHERE station = '" + evil + "'"
print("\nstring-built query:", q)
print("injection with + returns:", len(con.execute(q).fetchall()),
      "rows (ALL of them - attack works)")
print("placeholder returns:", con.execute(
    "SELECT station, pm25 FROM aq WHERE station = ?", (evil,)).fetchall(),
    "(treated as a literal name)")

# ---------- adversarial files ----------
FILES = {
    "missing column": "station,date,humidity\nAdyar,2026-10-01,60\n",
    "wrong delimiter": "station;date;pm25\nAdyar;2026-10-01;48\n",
    "empty file": "",
}


def load_report(name, text):
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
        if not rows:
            return f"{name}: no data rows - reported, nothing loaded"
        if "pm25" not in rows[0]:
            return f"{name}: column 'pm25' missing (found {list(rows[0])}) - reported, nothing loaded"
        return f"{name}: loaded {len(rows)} rows"
    except Exception as e:
        return f"{name}: {type(e).__name__}: {e} - reported, nothing loaded"


print()
for name, text in FILES.items():
    print(load_report(name, text))

raw_bytes = "station,date,pm25\nAdyar,2026-10-01,48\n".encode("latin-1")
try:
    raw_bytes.decode("utf-16")   # wrong encoding forced
except UnicodeDecodeError as e:
    print("wrong encoding: UnicodeDecodeError -", str(e)[:52],
          "- open with encoding= and errors='replace'")

# ---------- sentiment scorer failure cases ----------
POSITIVE = {"good", "clean", "fast", "helpful", "improved"}
NEGATIVE = {"bad", "dirty", "slow", "rude", "smoke", "broken"}
NEGATORS = {"not", "never", "no"}


def score(text):
    words = text.lower().replace(".", " ").replace(",", " ").split()
    total = 0
    for i, w in enumerate(words):
        val = 1 if w in POSITIVE else -1 if w in NEGATIVE else 0
        if i > 0 and words[i - 1] in NEGATORS:
            val = -val
        total += val
    return total


def label(text):
    s = score(text)
    return "positive" if s > 0 else "negative" if s < 0 else "neutral"


tricky = [
    ("Yeah, great, another morning of smoke.", "negative (sarcasm)"),
    ("The air is not bad today.", "positive (double negative)"),
    ("The park is clean but the road is dirty.", "mixed - genuinely both"),
    ("Not bad, service improved.", "positive"),
]
print()
for text, truth in tricky:
    print(f"score {score(text):+d} -> {label(text):8} | should be: {truth:28} | {text}")
con.close()
