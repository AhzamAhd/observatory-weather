from comet_tracker import get_current_comets

comets = get_current_comets()
has_position = [c for c in comets
                if c.get("ra_deg") is not None]
no_position  = [c for c in comets
                if c.get("ra_deg") is None]

print(f"Total comets: {len(comets)}")
print(f"With position (trackable): {len(has_position)}")
print(f"Without position: {len(no_position)}")
print()
print("Trackable comets:")
for c in has_position:
    print(f"  {c['name']} — mag {c['magnitude']}"
          f" — {c['status']}")
print()
print("Not trackable:")
for c in no_position:
    print(f"  {c['name']}")