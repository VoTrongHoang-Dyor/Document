import re

arrange_file = "Arrange.md"
core_file = "Core_Spec.md"
feature_file = "Feature_Spec.md"

with open(arrange_file, 'r', encoding='utf-8') as f:
    text = f.read()

# For Core_Spec.md: extract PART 3
# It is between `## New §3: Infrastructure & Deployment (Redesigned)` and `# PART 4 — FEATURE_SPEC.MD UPDATES`
core_match = re.search(r"## New §3: Infrastructure & Deployment \(Redesigned\)(.*?)(?=# PART 4 — FEATURE_SPEC\.MD UPDATES)", text, re.DOTALL)
core_text = ""
if core_match:
    core_text_raw = core_match.group(1)
    # Remove markdown code block delimiters (```markdown and ```) from the boundaries
    core_text = re.sub(r'```markdown\n(.*?)\n```', r'\1', core_text_raw, flags=re.DOTALL)
    # Rename ## 3. to ## 14. to avoid conflicts, and 3.x to 14.x
    core_text = re.sub(r'## 3\.', r'## 14.', core_text)
    core_text = re.sub(r'### 3\.', r'### 14.', core_text)
    core_text = re.sub(r'#### 3\.', r'#### 14.', core_text)

# For Feature_Spec.md: extract PART 4
feature_match = re.search(r"# PART 4 — FEATURE_SPEC\.MD UPDATES(.*)", text, re.DOTALL)
feature_text = ""
if feature_match:
    feature_text_raw = feature_match.group(1)
    feature_text = re.sub(r'```markdown\n(.*?)\n```', r'\1', feature_text_raw, flags=re.DOTALL)
    # Remove heading of section if there's any meta text
    feature_text = re.sub(r'## New §INFRA-01:.*?\n', '', feature_text)
    feature_text = re.sub(r'## New §INFRA-02:.*?\n', '', feature_text)
    feature_text = re.sub(r'## New §INFRA-03:.*?\n', '', feature_text)
    feature_text = re.sub(r'## Updated §3\.5:.*?\n', '', feature_text)
    feature_text = re.sub(r'## Trade-off Analysis\n', '', feature_text)


if core_text:
    with open(core_file, 'a', encoding='utf-8') as f:
        f.write("\n\n" + core_text.strip() + "\n")
    print("Core_Spec.md updated successfully.")
else:
    print("Core_Spec.md text not found!")

if feature_text:
    with open(feature_file, 'a', encoding='utf-8') as f:
        f.write("\n\n" + feature_text.strip() + "\n")
    print("Feature_Spec.md updated successfully.")
else:
    print("Feature_Spec.md text not found!")
