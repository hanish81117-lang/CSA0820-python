"""B1.4 - the four charts designed in A3.1, from aq.db (run b1.py first)."""
import sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = sqlite3.connect("/tmp/co5/aq.db")

# 1. trend of PM2.5 over the month - line chart (Adyar)
days, means = zip(*con.execute(
    "SELECT day, AVG(pm25) FROM readings WHERE station='Adyar' "
    "GROUP BY day ORDER BY day").fetchall())
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot([d[-2:] for d in days], means, marker="o", ms=3, color="#1f77b4")
ax.set_title("Daily mean PM2.5 - Adyar, October 2026")
ax.set_xlabel("Day of October")
ax.set_ylabel("PM2.5 (ug/m3)")
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("/tmp/co5/chart_trend.png", dpi=140)
plt.close(fig)

# 2. comparison of stations - bar chart (monthly mean per station)
rows = con.execute(
    "SELECT station, AVG(pm25) FROM readings GROUP BY station ORDER BY AVG(pm25) DESC").fetchall()
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar([r[0] for r in rows], [r[1] for r in rows], color="#2ca02c")
ax.set_title("Monthly mean PM2.5 by station - October 2026")
ax.set_xlabel("Station")
ax.set_ylabel("Mean PM2.5 (ug/m3)")
ax.tick_params(axis="x", rotation=45)
fig.tight_layout()
fig.savefig("/tmp/co5/chart_stations.png", dpi=140)
plt.close(fig)

# 3. temperature vs PM2.5 - scatter
rows = con.execute("SELECT temp, pm25 FROM readings").fetchall()
fig, ax = plt.subplots(figsize=(8, 4))
ax.scatter([r[0] for r in rows][::20], [r[1] for r in rows][::20], s=4, alpha=0.4, color="#d62728")
ax.set_title("Temperature vs PM2.5 - all stations, October 2026")
ax.set_xlabel("Temperature (C)")
ax.set_ylabel("PM2.5 (ug/m3)")
fig.tight_layout()
fig.savefig("/tmp/co5/chart_scatter.png", dpi=140)
plt.close(fig)

# 4. hours with the worst air - bar by hour of day
rows = con.execute("SELECT hour, AVG(pm25) FROM readings GROUP BY hour").fetchall()
fig, ax = plt.subplots(figsize=(8, 4))
ax.bar([r[0] for r in rows], [r[1] for r in rows], color="#9467bd")
ax.set_title("Average PM2.5 by hour of day - October 2026")
ax.set_xlabel("Hour of day")
ax.set_ylabel("Mean PM2.5 (ug/m3)")
fig.tight_layout()
fig.savefig("/tmp/co5/chart_hours.png", dpi=140)
plt.close(fig)

worst = con.execute(
    "SELECT hour, ROUND(AVG(pm25),1) m FROM readings GROUP BY hour ORDER BY m DESC LIMIT 2"
).fetchall()
print("charts saved; worst hours:", worst)
con.close()
