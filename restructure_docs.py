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

# --- Core_Spec.md Update ---
# Remove appended Section 14 and beyond
core = re.sub(r'\n## 14\. \[ARCHITECTURE\].*', '', core, flags=re.DOTALL)

# Extract from Arrange.md
core_patch_match = re.search(r'## New §3: Infrastructure & Deployment \(Redesigned\).*?```markdown\n(.*?)```\n\n---.*?# PART 4', arrange, re.DOTALL)
if core_patch_match:
    core_patch = core_patch_match.group(1).strip()
    # Numbering 3.x -> 9.x
    core_patch = re.sub(r'## 3\.', r'## 9.', core_patch)
    core_patch = re.sub(r'### 3\.', r'### 9.', core_patch)
    core_patch = re.sub(r'#### 3\.', r'#### 9.', core_patch)
    
    # Replace Section 9
    core = re.sub(r'## 9\. SERVER INFRASTRUCTURE.*?## 10\. PERFORMANCE & SCALING CONSIDERATIONS', core_patch + '\n\n## 10. PERFORMANCE & SCALING CONSIDERATIONS', core, flags=re.DOTALL)

# --- Feature_Spec.md Update ---
# Remove appended INFRA/PLATFORM/ARCH sections
feature = re.sub(r'\n## INFRA-01: \[ARCHITECTURE\].*', '', feature, flags=re.DOTALL)

# Extract INFRA-01 to PLATFORM-19 patches
def get_patch(pattern):
    m = re.search(pattern, arrange, re.DOTALL)
    return m.group(1).strip() if m else ""

infra_01 = get_patch(r'## New §INFRA-01: Client Compute Offload Architecture.*?```markdown\n(.*?)\n```')
infra_02 = get_patch(r'## New §INFRA-02: Blob Storage Client Integration.*?```markdown\n(.*?)\n```')
infra_03 = get_patch(r'## New §INFRA-03: Relay Health & Self-Healing.*?```markdown\n(.*?)\n```')
platform_19 = get_patch(r'## Updated §3\.5: Deployment Simplification in Feature_Spec.*?```markdown\n(.*?)\n```')
arch_tradeoffs = get_patch(r'## Trade-off Analysis.*?```markdown\n(.*?)\n```')

def downlevel(text):
    return re.sub(r'^(#+)', r'\1#', text, flags=re.MULTILINE)

features_to_insert = "\n\n" + downlevel(infra_01) + "\n\n" + downlevel(infra_02) + "\n\n" + downlevel(infra_03) + "\n\n" + downlevel(platform_19) + "\n\n"

feature = feature.replace('## 5. FEATURE ↔ CORE MAPPING (CRITICAL)', features_to_insert + '## 5. FEATURE ↔ CORE MAPPING (CRITICAL)')

# Rename ARCH-TRADEOFFS
arch_tradeoffs = re.sub(r'^## ARCH-TRADEOFFS: New Architecture Trade-offs', '## 11. ARCHITECTURE TRADE-OFFS', arch_tradeoffs)

feature = feature.replace('## 11. CHANGELOG', arch_tradeoffs + '\n\n## 12. CHANGELOG')

with open(core_file, 'w', encoding='utf-8') as f:
    f.write(core)

with open(feature_file, 'w', encoding='utf-8') as f:
    f.write(feature)

print("Documentation restructured successfully.")
