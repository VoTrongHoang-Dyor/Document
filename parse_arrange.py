import re

with open("Arrange.md", "r") as f:
    lines = f.readlines()

patches = []
current_patch = None

for line in lines:
    if line.startswith("## PATCH-") or line.startswith("## [PATCH-"):
        if current_patch:
            patches.append(current_patch)
        current_patch = {"title": line.strip(), "content": []}
    elif current_patch:
        current_patch["content"].append(line)

if current_patch:
    patches.append(current_patch)

print(f"Found {len(patches)} patches")
for p in patches:
    print(p["title"])
