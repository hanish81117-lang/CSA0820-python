# Theory and Design Notes – CSA0820 Python Programming (CO5)

**Name:** Hanish S  **Register number:** 1925260012  **Slot:** A  **Faculty:** Keerthana S

---

# PART A – DESIGN

## TASK A1 – Design the Data Acquisition

### A1.1 Inspect the Source (2 Marks)
Each station uploads one CSV file per day with the header `station,date,hour,pm25,pm10,no2,temp_c` and 24 rows, one per hour. Expected data-quality problems, with an example of each:

- **Missing values:** a blank field (`Adyar,2026-10-03,6,,80,25,33`) or the marker `NA`.
- **Impossible values from sensor faults:** negative readings (-5 ug/m3) or absurd spikes (pm25 = 9999).
- **Duplicate rows:** the same station, date and hour appearing twice, usually from a retried upload.
- **Mixed units:** two stations (Porur and Tambaram) report temperature in Fahrenheit (90.8) while the other ten use Celsius.
- **Formatting noise:** stray spaces in station names and dates in different orders from different firmware versions.

### A1.2 Design the Storage (3 Marks)
Two tables in SQLite:

```sql
stations(station_id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL)

readings(reading_id INTEGER PRIMARY KEY,
         station_id INTEGER REFERENCES stations(station_id),
         day TEXT NOT NULL, hour INTEGER NOT NULL,
         pm25 REAL, pm10 REAL, no2 REAL, temp_c REAL,
         UNIQUE(station_id, day, hour))
```

The CSV `station` column maps to `stations.name` (looked up or inserted once); `date` and `hour` map to `readings.day` (ISO text) and `readings.hour`; the four pollutant and temperature columns map to the REAL columns after unit conversion. The UNIQUE constraint on `(station_id, day, hour)` rejects duplicates at the database level as a second line of defence.

### A1.3 CSV or SQL? (2 Marks)
Three typical board questions: the average PM2.5 of Adyar in October; the worst day in the city by average PM2.5; the number of valid readings per station.

- **From CSV files** each question needs custom code: open 12 files x 31 days, parse every row, filter and aggregate – a full O(n) scan per question, and the parsing code is rewritten each time.
- **From SQLite** each question is one declarative query (`AVG` with `WHERE`, `GROUP BY day ORDER BY average DESC LIMIT 1`, `GROUP BY station` with `COUNT`). With an index on (station, day) a filtered query touches only matching rows – about O(log n) – and the same stored data serves every future question without re-parsing.

**Alternative concept and complexity analysis:** Keeping only CSVs and loading a pandas DataFrame per question still answers every question, but each question costs a full O(n) read of the files and holds all n rows in memory (O(n) RAM). SQLite stores the data once on disk and answers an indexed question in roughly O(log n) time with O(1) working memory for the aggregate. For one-off exploration pandas is simpler; for a standing database queried daily, SQL wins on both time and space.

---

## TASK A2 – Design the Cleaning and Normalisation

### A2.1 Cleaning Rules (2 Marks)
- **Missing values:** fill with the previous hour's value for the same station (forward-fill); if there is no previous value, fill with that station's median. *Justification:* hourly pollution changes smoothly, so the previous value is the best local estimate; the median fallback is robust to outliers.
- **Impossible values (negative or above 999 ug/m3):** drop the reading and treat it as missing, then fill by the rule above. A sensor fault is not a measurement, and one 9999 spike would corrupt every average.
- **Duplicate rows:** keep the first occurrence and drop the rest; justified because the UNIQUE(station, day, hour) key means a duplicate is an upload artefact, not new information.
- **Fahrenheit temperatures:** convert to Celsius with `(F - 32) x 5/9` so every station is stored in one unit; the unit is known per station from the board's registry, so the conversion is deterministic.

### A2.2 Normalisation (2 Marks)
- **Min-max normalisation** scales PM2.5 to [0, 1] with `(v - min) / (max - min)`. It is appropriate when values must be plotted or compared on a fixed common scale, e.g. overlaying PM2.5 and PM10 on one chart.
- **Z-score standardisation** computes `(v - mean) / standard deviation`. It is appropriate for detecting unusual readings, because outliers keep large |z| values instead of being compressed by the range.

Min-max is chosen for the board's charts; z-score for flagging abnormal days.

### A2.3 Formatting (1 Mark)
Dates are stored as ISO `YYYY-MM-DD` text; station names are canonicalised to the board's official list (stripped, title-cased, e.g. 'Tambaram'); all readings are stored as REAL numbers rounded to one decimal, hours as integers 0-23.

**Alternative concept and complexity analysis:** If missing readings were simply dropped, daily averages would be computed from fewer hours and biased toward periods when the sensor happened to work – a station that fails mostly at night would look cleaner than it is. Dropping is O(n), forward-fill is O(n), and a median fill costs O(n log n) per station because of sorting; all use O(n) space. Filling keeps the day counts honest at negligible cost.

---

## TASK A3 – Design the Analysis and Visualisation

### A3.1 Choose the Charts (3 Marks)
| Question | Chart | Reason |
|----------|-------|--------|
| Trend of PM2.5 over a month | **Line chart** | Time is ordered and continuous; a line shows rise and fall between days directly. |
| Comparison of stations | **Bar chart** | Stations are categories; bar length makes ranking immediate. |
| Temperature versus PM2.5 | **Scatter plot** | Both variables are continuous; a scatter exposes correlation (or its absence). |
| Hours with the worst air | **Bar chart** of mean PM2.5 by hour of day | 24 discrete categories compared at a glance. A histogram would only show the distribution of values, and a box plot would hide the hourly pattern we need. |

### A3.2 Design the Summary Table (2 Marks)
One row per station per day: `station, day, min_pm25, max_pm25, mean_pm25` and `valid_readings` (the count of non-missing hours). It is produced by a single SQL query:

```sql
SELECT station, day, MIN(pm25), MAX(pm25), AVG(pm25), COUNT(pm25)
FROM readings GROUP BY station, day
```

so the table always reflects the stored clean data with no separate aggregation code.

**Alternative concept and complexity analysis:** Computing the same summary with Python loops after reading all rows is also O(n) time, but it holds all n rows (or at least per-group lists) in memory, O(n) space, while SQL's GROUP BY streams the rows and keeps only one accumulator per group, O(stations x days) space. At a million rows the loop version risks memory pressure the query never sees.

---

## TASK A4 – Plan Debugging and Profiling

### A4.1 Debugging Plan (2 Marks)
- **print():** quick one-off checks while developing – e.g. printing a raw row and its cleaned version side by side to confirm a rule.
- **assert:** lock invariants so faults surface immediately – `assert pm25 >= 0` after cleaning and `assert len(clean) <= len(raw)`; a failed assertion pinpoints the stage.
- **logging:** INFO for per-file counts, WARNING for every skipped or repaired row, DEBUG for row-level detail; the level is set once, so the same code runs quietly in production and loudly while hunting a bug.
- **pdb:** set a breakpoint (or `pdb.post_mortem()` after a crash) to step through the cleaning of one failing row and inspect variables interactively when logging is not enough.

### A4.2 Profiling Plan (2 Marks)
- **time.perf_counter()** wrapped around each pipeline stage (read, clean, store, query, plot) gives the wall-clock share of each stage.
- **timeit** compares small alternatives – e.g. string parsing idioms – over many repeats for stable micro-benchmarks.
- **cProfile with pstats** sorted by cumulative time runs the whole program and lists every function by total time and call count, identifying the true bottleneck instead of a guessed one.

**Alternative concept and complexity analysis:** Using `print` for all debugging adds one I/O call per message; thousands of prints can cost more time than the code being measured, and each print must be found and deleted afterwards. `logging` switches off with one `setLevel` call and `pdb` costs nothing until invoked – both survive in finished code safely, prints do not.

---

## TASK A5 – Design an AI Application for Citizen Complaints

### A5.1 Sentiment and Summary (2 Marks)
- **Sentiment scorer (word-list / lexicon based):** positive words (good, clean, fast, helpful, improved) score +1, negative words (bad, dirty, slow, rude, smoke, broken) score -1, and a negator (not, never, no) immediately before a word flips its sign – so "not good" scores -1 and "not bad" scores +1. The total sign gives the label.
- **Extractive summariser:** tokenise each complaint into sentences, count the frequency of important words (drop stop words like "the" and "is"), score each sentence by the sum of its word frequencies, and return the highest-scoring sentences – the sentences that carry the complaint's dominant content.

### A5.2 Basic Chatbot (2 Marks)
**Rule-based design:** match intent keywords ('pm2.5', 'average'), match a station name against the known list, run a parameterised SQL query on the readings table, and fill an answer template: *"The average PM2.5 in Adyar is 54.0 ug/m3."*

**Limitations:** it understands only the intents it was given, requires exact station names (no spelling tolerance), keeps no conversation context, and must refuse – honestly – every question outside its rules.

**Alternative concept and complexity analysis:** A trained model (Naive Bayes on labelled complaints, or a pre-trained language model) would classify sentiment with higher accuracy, especially on sarcasm and mixed opinions, but needs labelled training data, megabytes of model memory, and longer per-complaint time. The lexicon scorer runs in O(words) per complaint with a few kilobytes of word lists and no training; for a first-pass triage of short complaints it is the cheaper starting point, with a trained model as the upgrade path when misclassifications start to matter.

---

# PART B – IMPLEMENTATION AND ANALYSIS

## TASK B1 – Implement and Validate the Cleaning Pipeline  (`b1.py`, `b1_charts.py`)

### B1.1 Validate the Implementation (2 Marks)
The pipeline generates 8,641 raw rows for 12 stations (two reporting Fahrenheit) with every problem from A1.1 deliberately injected, then cleans them. The completed Complete-the-Code functions reproduce the paper's expected output exactly (`[('Adyar', '2026-10-01', 48.0), ('Guindy', '2026-10-01', 95.0), ('Guindy', '2026-10-03', 121.0)]` and `[0.0, 0.644, 1.0]`), and the added `>999` check skips its test row.

Before/after evidence: Porur's raw Fahrenheit row `('Porur','2026-10-01',0,'37.9','90.8')` becomes `('Porur','2026-10-01',0,37.9,32.7)` in Celsius. Of 8,641 raw rows, 8,250 survive: 250 missing, 140 impossible, 1 duplicate and 1,382 Fahrenheit rows handled.

### B1.2 Compare with Your Design (1 Mark)
The code follows the Part A design with two refinements: forward-fill falls back to the station median only when no previous value exists (a first-hour gap), and the impossible-value rule from A2.1 gained an explicit `>999` ceiling while completing the paper's TODO, which the design had stated only as "impossibly large". No other design rule changed.

### B1.3 Store and Query (2 Marks)
Clean rows are loaded with a single `executemany()` call into the `readings` table and the three A1.3 questions are answered in SQL:

- Average PM2.5 in Adyar in October = **44.7**
- Worst city day = **2026-10-27** (average 59.7)
- Valid readings per station start at 683 (Adyar), 689 (Anna Nagar), 690 (Chromepet)
- Min-max normalised PM2.5 values begin `[0.236, 0.159, 0.279, 0.444, 0.361]`

### B1.4 Visualise (2 Marks)
Charts are in `screenshots/` (`chart_trend.png`, `chart_stations.png`, `chart_scatter.png`, `chart_hours.png`).

- **Daily PM2.5 trend, Adyar:** the daily mean oscillates through October between about 40 and 51 ug/m3 with sharp spikes around the 10th, 19th and 25th. There is no sustained upward or downward drift – the line chart makes clear these are isolated bad days rather than a trend.
- **Station comparison:** monthly mean PM2.5 differs clearly between stations, with the industrial belt stations highest and the residential ones lowest. The bar chart ranks them instantly, which is exactly the comparison the board asked for.
- **Temperature vs PM2.5:** the scatter shows a mild positive relationship: hotter hours tend to carry higher PM2.5, consistent with stagnant warm air trapping particles, but the wide spread shows temperature alone does not determine pollution.
- **Worst hours of the day:** mean PM2.5 peaks at hours 8-9 and 18-19 (about 79.6 ug/m3) against roughly 54 elsewhere – the morning and evening traffic rush hours. This directly answers the board's question of when the air is worst.

**Alternative concept and complexity analysis:** Measured with pandas instead of csv loops (times from Task B3's runs): 8,760 rows – loops 0.011 s, pandas 0.005 s; 105,120 rows – loops 0.137 s, pandas 0.042 s; 1,051,200 rows – loops 1.403 s, pandas 0.369 s. Pandas vectorises the same O(n) work in C, about 4x faster, at the cost of holding the whole O(n) DataFrame in memory where the loop version streams row by row.

---

## TASK B2 – Engineer Adversarial Data  (`b2.py`)

### Adversarial files and SQL injection
- The completed Complete-the-Code program matches the expected output exactly (`54.0 108.0`, then `None` for the injection attempt).
- **Injection test:** building the query with `+` as `... WHERE station = 'Adyar' OR '1'='1'` returns all 4 rows – the attack works, because the input becomes part of the SQL grammar. The `?` placeholder binds the input as a literal value, so `Adyar' OR '1'='1` is just a station name that does not exist and the query returns `None`. Parameters are never parsed as SQL, which is why placeholders are safe.
- **Adversarial files:** a file missing the `pm25` column is reported (`column pm25 missing, found [station, date, humidity]`) and nothing is loaded; a semicolon-delimited file is caught the same way (the header parses as one column `station;date;pm25`); an empty file is reported as having no data rows. Each failure is loud and specific instead of a silent empty database.
- **Sentiment scorer under attack:** sarcasm fails as expected – *"Yeah, great, another morning of smoke."* scores -1 (only "smoke" is in the lexicon; the lexicon cannot hear the tone). The double negative *"The air is not bad today."* correctly flips to positive. The genuinely mixed *"The park is clean but the road is dirty."* nets to neutral, which is arguably honest for a mixed complaint.

### What each adversarial input reveals
The design assumes the header contract, the delimiter and non-empty input, and each assumption is now checked and reported rather than trusted; the injection test shows every station name must always go through a `?` parameter; the sentiment failures mark the boundary of a word-list approach – tone and mixed opinion need a trained model.

**Alternative concept and complexity analysis:** With f-string SQL, `station = 'Adyar' OR '1'='1'` is parsed as two conditions and returns every row – a data leak by construction; the `?` placeholder makes the same input harmless. `executemany()` versus `execute()` in a loop: both are O(n) inserts, but `executemany` runs the loop inside sqlite's C layer with one statement preparation, while the Python loop pays per-call parsing and overhead for every row – a constant-factor penalty that grows painful at lakhs of rows.

---

## TASK B3 – Loops vs Libraries vs SQL  (`b3.py`)

### B3.1 Correctness on Small Data (2 Marks)
Daily mean PM2.5 per station computed three ways – plain Python loops with `csv`, pandas `groupby`, and SQL `GROUP BY` – on 56 station-days: all three agree exactly (`all agree -> True`). Three independent implementations returning identical numbers is strong evidence the aggregation is correct.

### B3.2 Increase the Data Size (2 Marks)
Generated data for 1, 12 and 120 stations over a year (about 8,760 readings per station) and timed each method (report run):

| Stations | Rows | loops (s) | pandas (s) | sql (s) |
|---------:|-----:|----------:|-----------:|--------:|
| 1 | 8,760 | 0.011 | 0.005 | 0.019 |
| 12 | 105,120 | 0.137 | 0.042 | 0.234 |
| 120 | 1,051,200 | 1.403 | 0.369 | 2.401 |

### B3.3 Profile (2 Marks)
cProfile on the plain-Python version at 12 stations: the csv reader's `__next__` dominates with 105,121 calls and about 0.097 s – row parsing, not the averaging math, is the bottleneck. `means_loops` itself is only 0.068 s total. Optimising the aggregation would be wasted effort; reading rows faster (or letting pandas do it in C) is where the time is.

### B3.4 Engineering Trade-Off (2 Marks)
pandas is consistently fastest (about 4x over loops at a million rows) and the least code, so it wins for a quick one-time analysis. SQL is slower on a bulk year-load because it parses and aggregates on each query, but for the daily automated report the data already lives in SQLite, the query touches one day, and indexes keep it in milliseconds with no reloading – so SQL wins for the standing pipeline. Plain loops lose on speed but teach exactly what the other two hide, and carry no dependencies.

**Alternative concept and complexity analysis:** A running sum-and-count dictionary computes each station-day mean in one pass: still O(n) time like `statistics.mean()`, but space drops from O(n) – storing all readings before averaging – to O(stations x days), one sum and one count per group. At a million rows that is the difference between holding the whole dataset and holding 43,800 small tuples.

---

## TASK B4 – Final Engineering Decision  (`b4.py`)

### B4.1 Implement a Practical Strategy (2 Marks)
The completed Complete-the-Code scorer reproduces the paper's expected output exactly (positive / negative / negative / positive for the four samples). Run on 50 complaints, the scorer agrees with my own reading on **48 of 50**. The two misses:

1. *"Smoke from tea shops in the morning is not bad."* scores neutral – "not bad" flips positive and cancels "smoke", but the complaint is really about smoke.
2. *"School zone traffic is slow but helpful police are there."* nets neutral where "slow" should dominate.

Both failures are the known lexicon blind spots: double-duty words and mixed opinions.

### B4.2 Check the Database (1 Mark)
Added `CREATE INDEX ON readings(station, day)` on a 200,000-row table and measured the slowest single station-day query: 0.0056 s without the index, 0.000039 s with it – about **143 times faster**, for the price of a small on-disk structure.

### B4.3 Production Decision (2 Marks)
At the new scale (112 stations reporting every 15 minutes is about 10,750 rows a day, roughly 3.9 million a year) my measurements say:

- **Database:** keep SQLite with the (station, day) index – indexed queries stay in tens of microseconds, inserts go through batched `executemany`, and a year fits comfortably in one file.
- **Cleaning:** rules stay as designed (they are O(n) and stream row by row).
- **Analysis:** SQL `GROUP BY` serves the daily report and pandas loads query results only for charts.
- **Complaints (50,000 a month):** the lexicon scorer's 96% agreement is good enough for first-pass triage and routing, and its O(words) cost handles 50,000 complaints in seconds; but the 2% it misses are exactly the sarcastic and mixed complaints a board should not misfile, so I would label a sample by hand and train a Naive Bayes classifier as the second opinion, keeping the lexicon as the fast default.
- **Chatbot:** the rule-based chatbot is sufficient for the board's fixed question types; it fails honestly with a refusal instead of inventing answers.

**Alternative concept and complexity analysis:** A first-k-sentences summariser is O(1) in the text length and trivially fast, but on the 50 complaints it keeps the greeting and drops the substance; the frequency-scored summariser costs O(words) time and O(vocabulary) space and picks the sentences carrying the dominant words – on these complaints it selected *"The bus stand is clean now, good work"* and *"Fog and smoke mixed this morning, visibility bad"*, which are the sentences I would have picked. The extra linear scan is worth it.

---

# OVERALL CONCLUSION
This assignment took a messy 12-station air-quality feed through the full engineering progression: acquire, inspect, clean, normalise, store, query, visualise, profile and interpret. The cleaning pipeline recovered 8,250 reliable rows from 8,641 raw ones with justified rules; SQLite with a single composite index answered the board's questions up to 143 times faster than an unindexed scan; measured comparisons at three scales showed pandas fastest for one-off analysis and SQL the right home for the daily pipeline; cProfile proved the CSV reader, not the math, is the bottleneck worth fixing; adversarial testing exposed and closed an SQL-injection hole; and the lexicon-based AI tools reached 96% agreement with human reading while honestly revealing where a trained model must take over. Every design claim from Part A was tested against real measurement in Part B, and where the two disagreed, the measurement won.
