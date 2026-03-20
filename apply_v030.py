import sys
import re

def read_file(path):
    with open(path, "r", encoding="utf-8") as f: return f.read()

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f: f.write(content)

arrange = read_file("Arrange.md")

feature_patches = {}
core_patches = {}

patches = arrange.split('\n## ')

for patch in patches:
    if not patch.strip() or patch.startswith("12. CHANGELOG") or patch.startswith("13 CHANGELOG"): 
        continue
    lines = patch.split('\n')
    header = lines[0].strip()
    content = '\n'.join(lines[1:]).strip()
    
    if "PATCH-" in header or "[PATCH" in header:
        if header.startswith("PATCH-") and not header.startswith("PATCH-NEW") and not header.startswith("PATCH-REPLACE"):
            feature_patches[header] = content
        else:
            core_patches[header] = content

f = read_file("Feature_Spec.md")

def extract_content(patch_content):
    lines = patch_content.split('\n')
    res = []
    in_payload = False
    for line in lines:
        if line.startswith('> '): continue
        if line.strip() == '' and not in_payload: continue
        in_payload = True
        res.append(line)
    return '\n'.join(res).strip()

def get_next_header_idx(text, start_search_idx, level):
    pattern = r'\n#{1,' + str(level) + r'} '
    match = re.search(pattern, text[start_search_idx:])
    if match:
        return start_search_idx + match.start()
    return len(text)

for hd, c in feature_patches.items():
    if "CHANGELOG" in hd:
        changelog_entry = extract_content(c)
        if "```markdown" in changelog_entry:
            changelog_entry = changelog_entry.split("```markdown")[1].split("```")[0].strip()
        
        table_header = "| Version | Date | Changes |\n|---|---|---|"
        if table_header in f:
            f = f.replace(table_header, table_header + "\n" + changelog_entry)
            print(f"Applied {hd}")
        else:
            print("ERROR: table header not found in Feature_Spec.md")
    else:
        target_stub = None
        for l in c.split('\n'):
            if "Thay thế stub tại:" in l:
                target_stub = l.split('`')[1]
                break
        
        if target_stub:
            new_text = target_stub + "\n\n" + extract_content(c) + "\n"
            start_idx = f.find(target_stub)
            if start_idx != -1:
                level = len(target_stub.split()[0])
                end_idx = get_next_header_idx(f, start_idx + len(target_stub), level)
                f = f[:start_idx] + new_text + f[end_idx:]
                print(f"Applied {hd}")
            else:
                print(f"FAILED to find stub {target_stub}")

f = f.replace("version:  \"0.2.6\"", "version:  \"0.3.0\"")
write_file("Feature_Spec.md", f)

c_md = read_file("Core_Spec.md")

for hd, c in core_patches.items():
    if "CHANGELOG" in hd:
        changelog_entry = extract_content(c)
        if "```markdown" in changelog_entry:
            changelog_entry = changelog_entry.split("```markdown")[1].split("```")[0].strip()
        table_header = "| Version | Date | Changes |\n|---|---|---|"
        if table_header in c_md:
            c_md = c_md.replace(table_header, table_header + "\n" + changelog_entry)
            print(f"Applied {hd}")
        else:
            print("ERROR: table header not found in Core_Spec.md")
    elif "10.2" in hd:
        target = "### 10.2 Latency Targets"
        start_idx = c_md.find(target)
        if start_idx != -1:
            end_idx = get_next_header_idx(c_md, start_idx + len(target), 3)
            c_md = c_md[:start_idx] + extract_content(c) + "\n" + c_md[end_idx:]
            print(f"Applied {hd}")
    elif "5.3b" in hd:
        target = "### 5.3 Message Layer Security — MLS RFC 9420"
        start_idx = c_md.find(target)
        if start_idx != -1:
            end_idx = get_next_header_idx(c_md, start_idx + len(target), 3)
            c_md = c_md[:end_idx] + "\n\n" + extract_content(c) + c_md[end_idx:]
            print(f"Applied {hd}")
    elif "5.1b" in hd:
        target = "### 5.1 Key Management System (HKMS)"
        start_idx = c_md.find(target)
        if start_idx != -1:
            end_idx = get_next_header_idx(c_md, start_idx + len(target), 3)
            c_md = c_md[:end_idx] + "\n\n" + extract_content(c) + c_md[end_idx:]
            print(f"Applied {hd}")
    elif "6.3b" in hd:
        target = "### 6.3 BLE Stealth Beaconing"
        start_idx = c_md.find(target)
        if start_idx != -1:
            end_idx = get_next_header_idx(c_md, start_idx + len(target), 3)
            c_md = c_md[:end_idx] + "\n\n" + extract_content(c) + c_md[end_idx:]
            print(f"Applied {hd}")
    elif "12.7" in hd:
        target = "## 12. IMPLEMENTATION CONTRACT"
        start_idx = c_md.find(target)
        if start_idx != -1:
            end_idx = get_next_header_idx(c_md, start_idx + len(target), 2)
            c_md = c_md[:end_idx] + "\n\n" + extract_content(c) + c_md[end_idx:]
            print(f"Applied {hd}")
    elif "9.7b" in hd:
        # 9.7 does not exist, appending to end of section 9
        target = "## 9. [ARCHITECTURE]"
        start_idx = c_md.find(target)
        if start_idx != -1:
            end_idx = get_next_header_idx(c_md, start_idx + len(target), 2)
            c_md = c_md[:end_idx] + "\n\n" + extract_content(c) + c_md[end_idx:]
            print(f"Applied {hd}")
        else:
            print("Failed to find section 9 in Core_Spec.md")
    elif "11.4b" in hd:
        target = "### 11.4 Known Implementation Gaps"
        start_idx = c_md.find(target)
        if start_idx != -1:
            end_idx = get_next_header_idx(c_md, start_idx + len(target), 3)
            c_md = c_md[:end_idx] + "\n\n" + extract_content(c) + c_md[end_idx:]
            print(f"Applied {hd}")
    elif "11.4" in hd:
        target = "### 11.4 Known Implementation Gaps"
        table_entry = extract_content(c)
        if "```markdown" in table_entry:
            table_entry = table_entry.split("```markdown")[1].split("```")[0].strip()
        
        start_idx = c_md.find(target)
        table_start = c_md.find("|", start_idx)
        table_end = c_md.find("\n\n", table_start)
        if table_start != -1 and table_end != -1:
            header_table = "| Feature / Component | Priority | Reference | Status / Mitigation |\n|---|---|---|---|\n"
            c_md = c_md[:table_start] + header_table + table_entry + c_md[table_end:]
            print(f"Applied {hd}")

c_md = c_md.replace("version:  \"0.2.6\"", "version:  \"0.2.7\"")
write_file("Core_Spec.md", c_md)
print("Done writing Core_Spec.md")
