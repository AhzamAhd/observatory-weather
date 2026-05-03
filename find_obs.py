from db import query_df

df = query_df("SELECT name FROM observatories ORDER BY name")

keywords = [
    'paranal', 'alma', 'vla', 'mauna', 'la silla',
    'subaru', 'keck', 'palomar', 'kitt', 'cerro',
    'chile', 'hawaii', 'canary', 'palma', 'roque'
]

for kw in keywords:
    matches = df[
        df['name'].str.lower().str.contains(
            kw, na=False)]
    if not matches.empty:
        print(f"\n{kw.upper()}:")
        for name in matches['name'].tolist():
            print(f"  {name}")