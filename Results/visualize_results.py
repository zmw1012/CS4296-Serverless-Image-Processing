import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# 1. upload raw results
df_raw = pd.read_csv('raw_results.csv')

# 2. keep the 'ok' results
df_raw['timestamp'] = pd.to_datetime(df_raw['timestamp'])
df = df_raw[df_raw['status'] == 'ok'].copy() 

df['image_tier'] = df['image_tier'].str.lower()
df['test_type'] = df['test_type'].str.lower()

summary = df.groupby(['platform', 'test_type', 'image_tier']).agg(
    count=('total_latency_seconds', 'size'),
    mean_total_latency=('total_latency_seconds', 'mean'),
    median_total_latency=('total_latency_seconds', 'median'),
    p95_total_latency=('total_latency_seconds', lambda x: np.percentile(x, 95)),
    mean_processing_sec=('processing_seconds', 'mean'),
    std_total_latency=('total_latency_seconds', 'std')
).round(4)

summary.to_csv('cleaned_summary.csv')

sns.set_style("whitegrid")
plt.rcParams['font.sans-serif'] = ['Arial']

# Visualization 1: Cold Start Comparison（AWS vs GCP，different image_tier）
cold = df[df['test_type'] == 'cold_start']
plt.figure(figsize=(10, 6))
sns.barplot(data=cold, x='image_tier', y='total_latency_seconds', hue='platform', errorbar=('ci', 95)) # 95% confidence interval
plt.title('Cold Start Latency Comparison (AWS vs GCP)')
plt.ylabel('Total Latency (seconds)')
plt.savefig('cold_start_comparison1.png', dpi=300, bbox_inches='tight')

# Visualization 2: Warm Start Comparison（AWS vs GCP，different image_tier）
warm = df[df['test_type'] == 'warm']
plt.figure(figsize=(10, 6))
sns.barplot(data=warm, x='image_tier', y='total_latency_seconds', hue='platform', errorbar=('ci', 95)) # 95% confidence interval
plt.title('Warm Start Latency Comparison (AWS vs GCP)')
plt.ylabel('Total Latency (seconds)')
plt.savefig('warm_start_comparison1.png', dpi=300, bbox_inches='tight')

# Visualization 3: Concurrency_500 Comparison（AWS vs GCP，different image_tier）
conc_all = df_raw[df_raw['test_type'].str.contains('concurrency_500')] 
conc_ok = conc_all[conc_all['status'] == 'ok'] 
success_count = conc_ok.groupby(['platform', 'image_tier']).size()
total_count = conc_all.groupby(['platform', 'image_tier']).size()
success_rate = (success_count / total_count * 100).round(2)
print("Concurrency Success Rate (%):\n", success_rate)
plt.figure(figsize=(10, 6))
sns.boxplot(data=conc_ok, x='image_tier', y='total_latency_seconds', hue='platform') # 25% percentile, 50% percentile, 75% percentile
plt.title('Concurrency 500: Tail Latency & Stability (AWS vs GCP)')
plt.ylabel('Total Latency (seconds)')
plt.savefig('concurrency_comparison1.png', dpi=300, bbox_inches='tight')

plt.show()