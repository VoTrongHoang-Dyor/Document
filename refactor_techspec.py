import re

with open('TeraChat-V0.2.1-TechSpec.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

class Node:
    def __init__(self, level, title, content):
        self.level = level
        self.title = title
        self.content = content
        self.children = []

    def detach_child(self, title_substr):
        for i, c in enumerate(self.children):
            if title_substr.lower() in c.title.lower():
                return self.children.pop(i)
        return None

    def clone(self):
        new_node = Node(self.level, self.title, self.content)
        for c in self.children:
            new_node.children.append(c.clone())
        return new_node

current_nodes = {0: Node(0, "Root", "")}
in_code_block = False

for line in lines:
    if line.strip().startswith('```'):
        in_code_block = not in_code_block

    header_match = re.match(r'^(#{1,4})\s+(.*)', line)
    if header_match and not in_code_block:
        current_level = len(header_match.group(1))
        
        parent_level = current_level - 1
        while parent_level >= 0 and parent_level not in current_nodes:
            parent_level -= 1
            
        new_node = Node(current_level, line.strip(), "")
        if parent_level >= 0:
            current_nodes[parent_level].children.append(new_node)
        current_nodes[current_level] = new_node
        
        keys_to_delete = [k for k in current_nodes.keys() if k > current_level]
        for k in keys_to_delete:
            del current_nodes[k]
    else:
        deepest_level = max(current_nodes.keys())
        current_nodes[deepest_level].content += line

def find_node(node, substr):
    if substr.lower() in node.title.lower(): return node
    for c in node.children:
        found = find_node(c, substr)
        if found: return found
    return None

root = current_nodes[0]
new_root = Node(0, "Root", root.content)

part1 = Node(2, "## PHẦN I: KIẾN TRÚC LÕI & HẠ TẦNG (CORE ARCHITECTURE & INFRA)", "*Đây là phần \"Bên ngoài\" - Nền móng hệ thống trước khi chạm vào các thiết bị cuối.*\n\n")
part2 = Node(2, "## PHẦN II: PHÂN KHÚC DESKTOP APP (WINDOWS / MACOS / LINUX)", "*Trung tâm điều khiển chính của nhân viên văn phòng.*\n\n")
part3 = Node(2, "## PHẦN III: PHÂN KHÚC MOBILE APP (ANDROID / IOS)", "*Trạm phụ phục vụ di chuyển, đòi hỏi tối ưu pin và đánh thức từ xa.*\n\n")
part4 = Node(2, "## PHẦN IV: HỆ SINH THÁI TÍCH HỢP (ECOSYSTEM & INTEGRATION)", "*Các đầu nối hệ thống với đối tác.*\n\n")
part5 = Node(2, "## PHẦN V: PHỤ LỤC CHIẾN LƯỢC (APPENDIX)", "*Các chiến lược cốt lõi giữ chân khách hàng và doanh thu.*\n\n")

exec_sum = find_node(root, "Executive Summary")
if exec_sum: part1.children.append(exec_sum)

s1 = find_node(root, "1. Kiến trúc Hệ thống")
s2 = find_node(root, "2. Security Engine")
s3 = find_node(root, "3. Identity & Access")
s4 = find_node(root, "4. Communication Protocols")
s5 = find_node(root, "5. Platform Features")
s6 = find_node(root, "6. Operations & Deployment")
s7 = find_node(root, "7. Business API")
s8 = find_node(root, "8. Integration Hub")
appx = find_node(root, "Appendix")

ui_ux = s1.detach_child("1.4 UI/UX Philosophy") if s1 else None
arch_v2 = s1.detach_child("1.2 Architecture V2") if s1 else None
lan_p2p = s4.detach_child("4.3 LAN P2P Transport") if s4 else None

code_sandbox = s5.detach_child("5.1 Code Sandbox") if s5 else None
smart_appr = s5.detach_child("5.2 Smart Approval") if s5 else None
launchpad = s5.detach_child("5.3 Enterprise Launchpad") if s5 else None
crdt = s5.detach_child("5.5 CRDT Offline Sync") if s5 else None
global_dedup = s5.detach_child("5.6 Global Deduplication") if s5 else None
rich_file = s5.detach_child("5.7 Rich File Preview") if s5 else None
topic_thread = s5.detach_child("5.4 Topic-based") if s5 else None

if code_sandbox: code_sandbox.title = "### 10.2 Code Sandbox (WASM)"
if smart_appr: smart_appr.title = "### 10.3 Smart Approval (Fintech Bridge)"
if launchpad: launchpad.title = "### 10.4 Enterprise Launchpad (Productivity Dock)"
if global_dedup: global_dedup.title = "### 10.5 Global Deduplication (CAS)"
if rich_file: rich_file.title = "### 10.6 Rich File Preview"
if topic_thread: topic_thread.title = "### 10.7 Topic-based Threading"

components_1 = [x for x in [s1, s2, s3, s4, s6, s5] if x is not None]
part1.children.extend(components_1)

tech_stack_desktop = Node(3, "### 7. Tech Stack & Architecture (Desktop)", "**Rust Core + Tauri**\n\nKiến trúc lõi được xây dựng bằng Rust để đảm bảo an toàn bộ nhớ và hiệu năng xử lý tác vụ mã hóa nền. Giao diện Tauri bằng ReactJS giúp Web-dev dễ dàng bảo trì nhưng vẫn ăn ít RAM hơn Electron 10 lần.\n\n")
if arch_v2:
    arch_v2.title = "#### Components Manifest"
    tech_stack_desktop.children.append(arch_v2)

part2.children.append(tech_stack_desktop)

if ui_ux:
    ui_ux.title = "### 8. UI/UX Philosophy (Data Density)"
    part2.children.append(ui_ux)

if lan_p2p:
    lan_p2p.title = "### 9. Desktop-Specific Transport (LAN P2P)"
    part2.children.append(lan_p2p)

desktop_features = Node(3, "### 10. Desktop Feature Modules", "")
if crdt:
    crdt_desktop = crdt.clone()
    crdt_desktop.title = "#### 10.1 CRDT Offline Sync (Desktop Context)"
    crdt_desktop.content = "> **Context:** RAM và Ổ cứng nội bộ của desktop rất lớn. Node CRDT trên Desktop có thể lưu trữ toàn bộ lịch sử Document mà không cần lo tràn LocalStorage.\n\n" + crdt_desktop.content
    desktop_features.children.append(crdt_desktop)

features_to_add = [x for x in [code_sandbox, smart_appr, launchpad, global_dedup, rich_file, topic_thread] if x is not None]
desktop_features.children.extend(features_to_add)
part2.children.append(desktop_features)

tech_stack_mobile = Node(3, "### 11. Tech Stack & Architecture (Mobile)", "**React Native + Rust FFI**\n\nKiến trúc Mobile sử dụng React Native để đồng bộ mã nguồn UI với team Web. Giao tiếp mã hóa được gọi trực tiếp xuống thư viện C-compatible FFI của Rust Core để giải mã E2EE cực nhanh (trung bình <5ms) mà không bị nghẽn ở lớp Bridge của JS Engine.\n\n")
part3.children.append(tech_stack_mobile)

ui_mobile = Node(3, "### 12. UI/UX Constraints (Push-First)", "> **Mobile Context:** Khác với Data Density của Desktop, Mobile sử dụng triết lý \"Vuốt trượt và Cảnh báo\".\n\n- Thay vì List View hẹp dày đặc text, Mobile sử dụng Feed View hoặc Card View.\n- Command Palette được thay bằng Floating/Quick Action Button phù hợp thao tác 1 ngón tay.\n\n")
part3.children.append(ui_mobile)

transport_mobile = Node(3, "### 13. Mobile-Specific Transport (Wake-up Ping)", "**Giải quyết Bài toán Pin & Chạy nền (iOS/Android):**\n\nMobile **KHÔNG** duy trì connection WebSocket 24/7 như Desktop để tránh sập pin. \n- Khi có tin nhắn đến (E2EE payload), Relay Server gửi một **Wake-up Ping** (Data Push Notification - cấu trúc rỗng metadata) qua APNS (Apple) hoặc FCM (Google).\n- Hệ điều hành sẽ đánh thức ứng dụng đang ngủ trong background (~30 giây).\n- App Tự động mở kết nối TCP với Mesh Network trực tiếp (không qua Cloud), lấy tin nhắn về và giải mã cục bộ bằng Private Key trong Secure Enclave.\n- Sau khi giải mã thành văn bản rõ, App tự phát 'Local Notification' lên màn hình khóa.\n\n")
part3.children.append(transport_mobile)

mobile_features = Node(3, "### 14. Mobile Feature Modules", "")
if crdt:
    crdt_mobile = crdt.clone()
    crdt_mobile.title = "#### 14.1 CRDT Offline Sync (Mobile Constraint)"
    crdt_mobile.content = "> **Context:** Mobile hạn chế bộ nhớ chạy nền và ổ cứng vật lý. Engine CRDT trên Mobile sẽ bị giới hạn chỉ lưu trữ một tập hợp State Vector nhỏ (ví dụ 30 ngài gần nhất). Khi có xung đột Merge phức tạp, Mobile ủy quyền (Offload) cho Desktop của chính User hoặc VPS rà soát thay.\n\n" + crdt_mobile.content
    mobile_features.children.append(crdt_mobile)
part3.children.append(mobile_features)

if s7: part4.children.append(s7)
if s8: part4.children.append(s8)

if appx: part5.children = appx.children 

new_root.children = [part1, part2, part3, part4, part5]

def render_node(node):
    text = ""
    if node.level > 0:
        text += node.title + "\n\n"
    if node.content.strip():
        text += node.content.strip() + "\n\n"
    for child in node.children:
        text += render_node(child)
    return text

new_content = render_node(new_root)

# Overwrite the original file
with open('TeraChat-V0.2.1-TechSpec.md', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Structural refactor applied successfully onto TeraChat-V0.2.1-TechSpec.md")
