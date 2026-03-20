import re

core_content = open("Core_Spec.md").read()
feature_content = open("Feature_Spec.md").read()

def insert_after(content, anchor_regex, text_to_insert):
    match = re.search(anchor_regex, content)
    if not match:
        print(f"FAILED to find {anchor_regex}")
        return content
    idx = match.end()
    return content[:idx] + "\n\n" + text_to_insert + content[idx:]
    
def replace_chunk(content, anchor_regex, new_text):
    pass

# Print some matches
print("Core match dict:")
print(re.search(r"### 5.5 Out-of-Band Push Key Ratchet", core_content) is not None)
print(re.search(r"### 6.3 BLE Stealth Beaconing", core_content) is not None)
print(re.search(r"### 7.1 DAG Structure and Storage", core_content) is not None)
print(re.search(r"### 6.5 Dictator Election \(Split-Brain Resolution\)", core_content) is not None)
print(re.search(r"### 4.3 FFI Token Protocol", core_content) is not None)
print(re.search(r"### 6.7 Emergency Mobile Dictator Protocol \(EMDP\)", core_content) is not None)
print(re.search(r"### 9.5 Database Layer", core_content) is not None)

print("Feature match dict:")
print(re.search(r"### F-04: Local Storage Management", feature_content) is not None)
print(re.search(r"### F-01: Secure E2EE Messaging", feature_content) is not None)
print(re.search(r"### F-02: Push Notification Delivery \(E2EE\)", feature_content) is not None)
print(re.search(r"### F-03: IPC Bridge and State Synchronization", feature_content) is not None)
print(re.search(r"### F-10: AI / SLM Integration", feature_content) is not None)

