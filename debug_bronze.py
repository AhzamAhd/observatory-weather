import json
import glob
import os

bronze_dir = "data/bronze"
files      = glob.glob(f"{bronze_dir}/*.json")

all_data = []
for f in files:
    with open(f, "r") as fp:
        data = json.load(fp)
        if isinstance(data, list):
            all_data.extend(data)
        else:
            all_data.append(data)

print(f"Bronze records: {len(all_data)}")
print(f"\nFirst record keys:")
print(all_data[0].keys())
print(f"\nFirst full record:")
print(all_data[0])
print(f"\nSecond full record:")
print(all_data[1])