from object_visibility import OBJECTS

# Check what keys and structure look like
print("Total objects:", len(OBJECTS))
print()

# Show first 5 objects
for i, (name, data) in enumerate(OBJECTS.items()):
    if i >= 5:
        break
    print(f"Name: '{name}'")
    print(f"Data: {data}")
    print()

# Search for M42
print("Searching for M42...")
for name, data in OBJECTS.items():
    if "M42" in name or "Orion" in name:
        print(f"  Found: '{name}'")
        print(f"  Data:  {data}")
        break

# Search for Jupiter
print("\nSearching for Jupiter...")
for name, data in OBJECTS.items():
    if "Jupiter" in name:
        print(f"  Found: '{name}'")
        print(f"  Data:  {data}")
        break