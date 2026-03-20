import re

core_file = 'Core_Spec.md'
feature_file = 'Feature_Spec.md'
arrange_file = 'Arrange.md'

with open(core_file, 'r', encoding='utf-8') as f:
    core = f.read()

with open(feature_file, 'r', encoding='utf-8') as f:
    feature = f.read()

with open(arrange_file, 'r', encoding='utf-8') as f:
    arrange = f.read()

def extract_markdown_block(header_pattern, text):
    pattern = header_pattern + r'.*?```markdown\n(.*?)\n```'
    m = re.search(pattern, text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""

parts = arrange.split('# PHẦN 2')
part_1 = parts[0]
part_2 = parts[1] if len(parts) > 1 else ""

# --- 1. Core_Spec.md ---
core_cl = extract_markdown_block(r'## CHANGELOG \(bổ sung vào bảng hiện có\)', part_1)
s16 = extract_markdown_block(r'## §16 — Observability Layer', arrange)
s17 = extract_markdown_block(r'## §17 — Schema Versioning Protocol', arrange)
s18 = extract_markdown_block(r'## §18 — Hydration Scheduler', arrange)
s19 = extract_markdown_block(r'## §19 — HSM High Availability', arrange)
s20 = extract_markdown_block(r'## §20 — TeraEdge Device Architecture', arrange)

core_new_sections = "\n\n" + "\n\n".join(filter(bool, [s16, s17, s18, s19, s20])) + "\n\n"

core = core.replace('## 13. CHANGELOG', core_new_sections + '## 21. CHANGELOG')

table_header = r'(\| Version \| Date \| Summary \|\n\| --- \| --- \| --- \|\n)'
if core_cl:
    core = re.sub(table_header, r'\1' + core_cl + '\n', core)


# --- 2. Feature_Spec.md ---
feat_cl = extract_markdown_block(r'## CHANGELOG \(bổ sung\)', part_2)

f_obs1 = extract_markdown_block(r'## OBSERVE-01 — Client-Side', part_2)
f_obs2 = extract_markdown_block(r'## OBSERVE-02 — DAG Merge', part_2)
f_plat17 = extract_markdown_block(r'## PLATFORM-17 — Dart', part_2)
f_plat18 = extract_markdown_block(r'## PLATFORM-18 — ONNX Model', part_2)
f_plat19 = extract_markdown_block(r'## PLATFORM-19 — TeraEdge', part_2)
f_inf4 = extract_markdown_block(r'## INFRA-04 — Canary', part_2)
f_inf5 = extract_markdown_block(r'## INFRA-05 — SBOM', part_2)
f_cicd = extract_markdown_block(r'## CICD-01 — CI Pipeline', part_2)
f_inf6 = extract_markdown_block(r'## INFRA-06 — Chaos Engineering', part_2)

def downlevel(text):
    return re.sub(r'^(#+)', r'\1#', text, flags=re.MULTILINE)

feature_new_elems = [f_obs1, f_obs2, f_plat17, f_plat18, f_plat19, f_inf4, f_inf5, f_cicd, f_inf6]
feature_new = "\n\n".join(map(downlevel, filter(bool, feature_new_elems)))

# Insert before '## 5. FEATURE \u2194 CORE MAPPING (CRITICAL)'
feature = feature.replace('## 5. FEATURE ↔ CORE MAPPING (CRITICAL)', feature_new + "\n\n" + '## 5. FEATURE ↔ CORE MAPPING (CRITICAL)')

# Delete PLATFORM-14
feature = re.sub(r'### PLATFORM-14:.*?(\n### |\n## 5\.)', r'\1', feature, flags=re.DOTALL)

# Inject changelog
if feat_cl:
    feature = re.sub(table_header, r'\1' + feat_cl + '\n', feature)

with open(core_file, 'w', encoding='utf-8') as f:
    f.write(core)

with open(feature_file, 'w', encoding='utf-8') as f:
    f.write(feature)

print("v0.4.0 integration complete!")
