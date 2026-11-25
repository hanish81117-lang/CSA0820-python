"""B4 - Final engineering decision: scorer, summariser, index, chatbot."""
import random
import re
import sqlite3
import time
from collections import Counter

# ---------- Complete the Code (given program, TODO completed) ----------
POSITIVE = {"good", "clean", "fast", "helpful", "improved"}
NEGATIVE = {"bad", "dirty", "slow", "rude", "smoke", "broken"}
NEGATORS = {"not", "never", "no"}


def score(text):
    """+1 per positive word, -1 per negative word; a preceding negator flips it."""
    words = text.lower().replace(".", " ").replace(",", " ").split()
    total = 0
    # TODO 1 completed: value per word, flipped after a negator
    for i, w in enumerate(words):
        val = 1 if w in POSITIVE else -1 if w in NEGATIVE else 0
        if i > 0 and words[i - 1] in NEGATORS:
            val = -val
        total += val
    return total


def label(text):
    s = score(text)
    return "positive" if s > 0 else "negative" if s < 0 else "neutral"


for c in ["Roads are clean and the bus was fast.",
          "Smoke from the factory, air is bad.",
          "The staff were not helpful.",
          "Not bad, service improved."]:
    print(f"{label(c):8} | {c}")

# ---------- 50 complaints: scorer vs my own reading ----------
COMPLAINTS = [
    ("Smoke from the factory all night.", "negative"),
    ("The park near my house is clean now.", "positive"),
    ("Bus service is very slow in the morning.", "negative"),
    ("Air quality has improved a lot this month.", "positive"),
    ("Garbage burning behind the market, smoke everywhere.", "negative"),
    ("The new buses are fast and clean.", "positive"),
    ("Dust from the construction site is bad.", "negative"),
    ("Staff at the complaint desk were helpful.", "positive"),
    ("The road is broken and full of dust.", "negative"),
    ("My street is not clean at all.", "negative"),
    ("Traffic moves fast after the signal fix.", "positive"),
    ("The smoke from vehicles is not good.", "negative"),
    ("Drainage work was slow and the workers were rude.", "negative"),
    ("The lake area looks improved and clean.", "positive"),
    ("Burning smell every evening, very bad.", "negative"),
    ("The app response was fast and helpful.", "positive"),
    ("Autos blow black smoke, air feels dirty.", "negative"),
    ("Park maintenance is good these days.", "positive"),
    ("The market road is never clean.", "negative"),
    ("Fog and smoke mixed this morning, visibility bad.", "negative"),
    ("The green corridor project is good.", "positive"),
    ("Street lights broken for a week.", "negative"),
    ("Cleaning trucks are slow to come.", "negative"),
    ("The cycle track is clean and good.", "positive"),
    ("Factory smoke is not stopping at all.", "negative"),
    ("The helpline staff were not helpful.", "negative"),
    ("My area's air is good after the rain.", "positive"),
    ("Too much dust, roads are dirty.", "negative"),
    ("The bus stand is clean now, good work.", "positive"),
    ("Smoke from the dump yard is bad for kids.", "negative"),
    ("The new tree plantation looks good.", "positive"),
    ("Traffic is so slow near the signal.", "negative"),
    ("The complaint was closed fast, helpful team.", "positive"),
    ("Open drains make the area dirty.", "negative"),
    ("Air near the industrial estate is bad.", "negative"),
    ("The morning walkers' path is clean.", "positive"),
    ("Lorries park anywhere and are rude.", "negative"),
    ("The smoke issue was never fixed.", "negative"),
    ("Road sweeping is improved this week.", "positive"),
    ("The canal water is dirty and smells bad.", "negative"),
    ("Public toilets are clean now.", "positive"),
    ("Smoke from tea shops in the morning is not bad.", "positive"),
    ("The junction signal is broken again.", "negative"),
    ("School zone traffic is slow but helpful police are there.", "positive"),
    ("Construction dust is not good for asthma patients.", "negative"),
    ("The park is not bad for evening walks.", "positive"),
    ("Garbage collection is slow on Sundays.", "negative"),
    ("The air feels clean after the storm.", "positive"),
    ("Old buses leak smoke, very bad.", "negative"),
    ("The response team was fast and good.", "positive"),
]

agree = sum(1 for text, truth in COMPLAINTS if label(text) == truth)
wrong = [(text, truth, label(text)) for text, truth in COMPLAINTS if label(text) != truth]
print(f"\n50 complaints: scorer agrees with my reading on {agree}/50")
for text, truth, got in wrong:
    print(f"  wrong: got {got:8} should be {truth:8} | {text}")

# ---------- extractive summariser ----------
STOP = {"the", "is", "a", "an", "and", "of", "to", "in", "my", "was", "were", "at",
        "all", "this", "that", "very", "so", "for", "on", "from", "are", "not"}


def summarise(texts, k=2):
    words = [w for t in texts for w in re.findall(r"[a-z]+", t.lower()) if w not in STOP]
    freq = Counter(words)
    sentences = [s.strip() for t in texts for s in t.split(".") if s.strip()]
    ranked = sorted(sentences,
                    key=lambda s: -sum(freq[w] for w in re.findall(r"[a-z]+", s.lower())
                                       if w not in STOP))
    return ranked[:k]


print("\nsummary of the 50 complaints:", summarise([t for t, _ in COMPLAINTS]))

# ---------- index on (station, day) ----------
con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE aq (station TEXT, day TEXT, pm25 REAL)")
random.seed(4)
rows = [(f"Station{i % 112:03d}", f"2026-10-{i % 30 + 1:02d}", random.uniform(10, 150))
        for i in range(200000)]
con.executemany("INSERT INTO aq VALUES (?,?,?)", rows)
query = "SELECT AVG(pm25) FROM aq WHERE station='Station007' AND day='2026-10-15'"
t0 = time.perf_counter(); con.execute(query).fetchone(); t1 = time.perf_counter()
con.execute("CREATE INDEX idx_station_day ON aq(station, day)")
t2 = time.perf_counter(); con.execute(query).fetchone(); t3 = time.perf_counter()
print(f"\n200,000 rows, one station-day query: no index {t1 - t0:.4f}s, "
      f"with index {t3 - t2:.6f}s")


# ---------- rule-based chatbot ----------
def chatbot(question, db):
    q = question.lower()
    m = re.search(r"pm2\.?5|pm 2\.?5", q)
    station = next((s for s in ("adyar", "guindy") if s in q), None)
    if m and station:
        row = db.execute("SELECT AVG(pm25) FROM aq WHERE station LIKE ?",
                         (f"%{station}%",)).fetchone()
        if row[0] is None:
            return f"I have no readings for {station.title()}."
        return f"The average PM2.5 in {station.title()} is {row[0]:.1f} ug/m3."
    return "Sorry, I can only answer PM2.5 questions for known stations."


db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE aq (station TEXT, pm25 REAL)")
db.executemany("INSERT INTO aq VALUES (?,?)", [("Adyar", 48.0), ("Adyar", 60.0), ("Guindy", 95.0)])
print("\nchatbot:", chatbot("What is the PM2.5 in Adyar today?", db))
print("chatbot:", chatbot("What is the PM2.5 in Vellore today?", db))
print("chatbot:", chatbot("Will it rain tomorrow?", db))
con.close()
