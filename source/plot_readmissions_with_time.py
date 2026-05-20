import pandas as pd
import matplotlib.pylab as plt

data = pd.read_csv("data/processed/feature_dataset.csv", index_col=0)

df = data.copy()

df["episode_start"] = pd.to_datetime(df["episode_start"])
df["episode_end"] = pd.to_datetime(df["episode_end"])

df = df.sort_values(["crypted_patient_id", "episode_start"])

df["days_between"] = (
    df.groupby("crypted_patient_id")["episode_start"]
      .diff()
      .dt.days
)

# print(df['days_between'])

gaps = df["days_between"].dropna()

gaps_sorted = gaps.sort_values().values

cum_percent = (pd.Series(range(1, len(gaps_sorted) + 1)) / len(gaps_sorted)) * 100

plt.figure()
plt.plot(gaps_sorted, cum_percent)
plt.xlabel("Days between consecutive episodes")
plt.ylabel("Cumulative percentage of episodes")
plt.title("Cumulative Readmission Rate")
plt.xlim(1, 90)
plt.grid(True)
# plt.show()
plt.savefig("plots/cumulative_readmission_rate.png")


