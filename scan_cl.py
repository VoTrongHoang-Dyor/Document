import os
import re

docs = [
    "Introduction.md",
    "Function.md",
    "Feature_Spec.md",
    "Design.md",
    "Core_Spec.md",
    "BusinessPlan.md",
    "Web_Marketplace.md",
    "TestMatrix.md"
]

print("Scanning docs for CHANGELOG rows...")
for doc in docs:
    if not os.path.exists(doc): continue
    with open(doc, 'r', encoding='utf-8') as f:
        content = f.read()
    
    in_changelog = False
    for line in content.split('\n'):
        if 'CHANGELOG' in line:
            in_changelog = True
        if in_changelog and line.startswith('|') and not line.startswith('| ---'):
            cols = line.split('|')
            if len(cols) > 2:
                col1 = cols[1].strip()
                if col1 not in ["Version", ""]:
                    print(f"{doc}: {col1}")
