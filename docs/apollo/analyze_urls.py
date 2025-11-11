import csv
from urllib.parse import urlparse, parse_qs, unquote
from collections import Counter, defaultdict
import re

# Read all URLs from CSV
urls = []
with open('Instantlead.net-2 - Sheet1.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get('apollo_url'):
            urls.append(row['apollo_url'])

print(f"Total URLs: {len(urls)}")
print(f"Unique URLs: {len(set(urls))}\n")

# Analyze URL structure - Apollo uses hash-based routing
base_paths = Counter()
query_params = defaultdict(set)
param_counts = Counter()
hash_paths = Counter()

for url in urls:
    # Extract hash part (after #)
    if '#' in url:
        hash_part = url.split('#', 1)[1]
        if '?' in hash_part:
            path_part, query_part = hash_part.split('?', 1)
            hash_paths[path_part] += 1
            
            # Parse query parameters
            params = parse_qs(query_part)
            for param, values in params.items():
                param_counts[param] += 1
                query_params[param].update([unquote(v) for v in values])

print("=== HASH PATHS ===")
for path, count in hash_paths.most_common():
    print(f"{path}: {count}")

print(f"\n=== QUERY PARAMETERS (Top 30) ===")
for param, count in param_counts.most_common(30):
    print(f"{param}: {count} (sample values: {list(query_params[param])[:3]})")

# Write unique URLs to a file for detailed analysis
with open('unique_urls.txt', 'w', encoding='utf-8') as f:
    for i, url in enumerate(set(urls), 1):
        f.write(f"{i}. {url}\n\n")

print(f"\nUnique URLs written to unique_urls.txt")

