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

target_versions = ["0.2.6", "0.2.3", "0.2.1", "0.1.1"]

for doc in docs:
    if not os.path.exists(doc): continue
    with open(doc, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 1. Update YAML frontmatter
    content = re.sub(r'version:\s+".*?"', 'version:  "0.2.6"', content)
    
    # 2. Update changelog table
    lines = content.split('\n')
    in_changelog = False
    row_idx = 0
    
    for i, line in enumerate(lines):
        if 'CHANGELOG' in line and line.startswith('#'):
            in_changelog = True
            row_idx = 0 # reset for this file
            continue
            
        if in_changelog and line.startswith('#'):
            in_changelog = False
            
        if in_changelog and line.startswith('|') and not line.startswith('| ---') and not line.startswith('| Version'):
            cols = line.split('|')
            if len(cols) > 1:
                col1 = cols[1].strip()
                if col1 and col1.lower() not in ['version', '']:
                    # Looks like a main version row
                    if row_idx < len(target_versions):
                        old_val = cols[1]
                        new_val = old_val.replace(col1, target_versions[row_idx])
                        cols[1] = new_val
                        lines[i] = '|'.join(cols)
                    row_idx += 1

    with open(doc, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        
print("Versioning sync complete!")
