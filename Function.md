# TeraChat V0.2.1 — Function Breakdown & System Analysis

> **Vai trò tài liệu:** Product + Engineering Reference — phân rã toàn bộ chức năng theo cấp độ hệ thống, user role, feature tree, và flow.
> **Đối tượng:** Engineering, DevOps, Product Manager, Security Engineer.
> **Nguồn gốc:** Phân tích từ `TechSpec.md` v0.2.1.

---

## Mô tả ứng dụng

TeraChat là **nền tảng giao tiếp doanh nghiệp nội bộ** (Enterprise Secure Messaging Platform) được thiết kế cho môi trường yêu cầu bảo mật cao (tài chính, nhà hàng chuỗi, nhà máy sản xuất, tổ chức chính phủ). Nguyên tắc cốt lõi:

- **Local-First Processing:** Mọi tác vụ nặng (tìm kiếm, mã hóa, lập chỉ mục) chạy trên Client — Server chỉ relay byte mã hóa.
- **Zero-Knowledge Server:** Server không bao giờ thấy nội dung plaintext.
- **E2EE theo chuẩn MLS (IETF RFC 9420):** Mã hóa đầu cuối cho mọi kênh liên lạc.
- **Offline-First với Survival Link:** Hoạt động đầy đủ khi mất Internet qua BLE/Wi-Fi Direct Mesh.

---

## TABLE OF CONTENTS

1. [Phân loại chức năng theo cấp độ hệ thống](#1-phân-loại-chức-năng-theo-cấp-độ-hệ-thống)
2. [Phân rã theo User Role](#2-phân-rã-theo-user-role)
3. [Feature Breakdown — Feature Tree](#3-feature-breakdown--feature-tree)
4. [User Flow & System Flow](#4-user-flow--system-flow)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Câu hỏi hệ thống chưa được định nghĩa](#6-câu-hỏi-hệ-thống-chưa-được-định-nghĩa)

---

## 1. Phân loại chức năng theo cấp độ hệ thống

### 1.1 Core Features — Chức năng sống còn

| # | Tên chức năng | Mô tả ngắn | Nếu thiếu → hậu quả |
|---|---|---|---|
| C1 | **E2EE Messaging (MLS/RFC 9420)** | Nhắn tin nhóm/DM với mã hóa đầu cuối theo chuẩn MLS TreeKEM | App không thể ra thị trường doanh nghiệp |
| C2 | **Identity & Device Binding** | Bind thiết bị vào định danh doanh nghiệp bằng PKI + Invite Token | Không ai đăng nhập được |
| C3 | **Encrypted File Transfer (Salted MLE)** | Gửi/nhận file có deduplication không phá vỡ E2EE | Mất chức năng giao tiếp thực tế |
| C4 | **Secure Key Management (HKMS)** | Quản lý Key Hierarchy, Dead Man Switch, Remote Wipe | Toàn bộ mô hình bảo mật sụp đổ |
| C5 | **Offline / Survival Link Messaging** | Nhắn tin qua BLE/Wi-Fi Direct khi mất Internet | Không dùng được ở hiện trường |
| C6 | **Push Notification E2EE (NSE/FCM)** | Nhận thông báo khi App bị kill trên iOS/Android | User không biết có tin nhắn mới |
| C7 | **Multi-Device Sync** | Đồng bộ tin nhắn trên nhiều thiết bị cùng tài khoản | UX không dùng được trong thực tế |
| C8 | **Remote Wipe** | Xóa toàn bộ dữ liệu trên thiết bị từ xa khi nhân viên nghỉ/bị đuổi | Rò rỉ dữ liệu khi thiết bị bị mất |

### 1.2 Supporting Features — Chức năng hỗ trợ

| # | Tên chức năng | Mô tả ngắn |
|---|---|---|
| S1 | **Voice / Video Call (WebRTC)** | Gọi thoại và video call P2P qua TURN/STUN, HA Cluster |
| S2 | **Zero-Knowledge Search (FTS5)** | Tìm kiếm toàn văn bản trong lịch sử tin nhắn đã giải mã, không rò metadata lên Server |
| S3 | **TeraVault (Virtual File System)** | Tổ chức file doanh nghiệp theo cây thư mục ảo; không duplicate dữ liệu |
| S4 | **AI Virtual Employee (Bot @mention)** | Gọi AI trong Channel qua `@gpt` — Bot chạy trong TEE Enclave |
| S5 | **Enterprise Utility Tools (.tapp)** | Mini-app nghiệp vụ chạy trong WASM Sandbox (Smart Order, CRM, Magic Logger) |
| S6 | **DLP Smart Clipboard** | Ngăn copy nội dung nội bộ sang app bên ngoài (Zalo, Telegram…) |
| S7 | **External Messaging Sandbox** | Tích hợp Zalo/Telegram qua Isolated WebView, không leak session nội bộ |
| S8 | **Tiered Storage (Zero-Byte Stubs)** | Client chỉ lưu metadata; file thực tải theo 3 tầng (Auto/On-demand/Offline) |
| S9 | **Slack Archive Migration** | Import lịch sử Slack, mã hóa bằng `Archive_Key`, tìm kiếm qua FTS5 |

### 1.3 Administrative / Internal Features — Chức năng quản trị

| # | Tên chức năng | Mô tả ngắn |
|---|---|---|
| A1 | **Identity Provisioning (SCIM/SSO)** | Tự động tạo/xóa user từ Azure AD / Google Workspace / Okta |
| A2 | **OPA Policy Engine (ABAC)** | Kiểm soát truy cập theo thuộc tính: phòng ban, địa lý, vai trò |
| A3 | **Enterprise Escrow Key** | Admin giữ Recovery Key để giải mã theo yêu cầu pháp lý |
| A4 | **DLP Multi-Sig Quarantine** | File cần M-of-N Supervisor ký trước khi Release (qua OPA intercept) |
| A5 | **Rate Limiting Engine** | Sliding Window chặn brute-force; giới hạn băng thông theo phòng ban |
| A6 | **Blind Observability** | Crash log xóa nội dung text, chỉ giữ Stack Trace — Admin PubKey mã hóa |
| A7 | **Remote Attestation** | Server từ chối cấp key nếu thiết bị không chứng minh Hardware Integrity |
| A8 | **GeoHash Access Control** | OPA dùng GeoHash prefix để áp dụng policy địa lý O(1) thay Haversine |
| A9 | **Offboarding Cascade** | Khi HR deactivate user: auto-revoke key, MLS Epoch Rotation, Queue purge |

### 1.4 Optional / Future Features — Chức năng tương lai

| # | Tên chức năng | Ghi chú |
|---|---|---|
| F1 | **Federation Interoperability** | Liên kết với tổ chức TeraChat khác qua mTLS + Sealed Sender (đang ở giai đoạn thiết kế) |
| F2 | **AI Dynamic Tokenization (Dual-Mask Protocol)** | PII redaction trước khi gửi LLM, rehydration sau khi nhận response |
| F3 | **BYOK (Bring Your Own Key)** | Doanh nghiệp tự quản lý Master Key ngoài Cluster |
| F4 | **Custom .tapp Marketplace** | Admin upload `.tapp` nội bộ cho từng phòng ban |
| F5 | **WebAuthn / Passkey** | Thay thế PIN bằng Passkey cho Kiosk Mode |

---

## 2. Phân rã theo User Role

### 2.1 Bảng tổng hợp Roles

| Role | Mô tả | Phạm vi |
|---|---|---|
| **End User (Employee)** | Nhân viên thông thường | Chỉ thấy Channel/DM mình được thêm vào |
| **IT Admin** | Quản trị viên hệ thống | Toàn bộ tổ chức |
| **Channel Manager** | Trưởng nhóm được Admin cấp quyền | Phạm vi Channel |
| **Supervisor** | Phê duyệt trong DLP Multi-Sig | File vượt Policy |
| **Bot / AI Worker** | Egress Worker tự động | Chỉ Channel được Bot join |
| **API Client (External)** | Hệ thống tích hợp bên ngoài | Theo OAuth scope |
| **Auditor** | Đọc Audit Log, không can thiệp | Read-only toàn bộ |

---

### 2.2 End User (Employee)

**Quyền hạn:**
- Gửi/nhận tin nhắn (text, file, voice) trong Channel được thêm vào
- Tìm kiếm lịch sử tin nhắn cục bộ (FTS5)
- Gọi thoại/video với thành viên có quyền
- Upload/download file theo Tiered Storage rules

**Chức năng có thể truy cập:**

| Chức năng | Điều kiện |
|---|---|
| Gửi tin nhắn E2EE | Đã bind thiết bị, còn trong MLS Group |
| Gửi file (Salted MLE / Strict E2EE) | File < 5MB → StrictE2EE; ≥ 5MB phổ biến → SaltedMLE auto |
| Dùng AI Bot (`@gpt`) | Bot đã được Admin deploy vào Channel |
| Toggle "Make Available Offline" | Chỉ trên folder mình có quyền đọc |
| Dùng `.tapp` Tool (Smart Order…) | OPA Policy cho phép theo phòng ban |
| External Messaging Sandbox | Phải được Admin cho phép qua OPA |

**Bị giới hạn:**
- Không thêm/xóa Bot khỏi Channel
- Không xem tin nhắn Channel khác (kể cả cùng công ty)
- Không tắt DLP chặn clipboard
- Không xuất/copy dữ liệu ra ngoài nếu OPA chặn

---

### 2.3 IT Admin

**Quyền hạn:** Toàn quyền trên tổ chức.

**Chức năng có thể truy cập:**

| Chức năng | Hành động |
|---|---|
| Identity Provisioning | Tạo/xóa/suspend User thủ công hoặc qua SCIM |
| OPA Policy Editor | Định nghĩa rule truy cập theo phòng ban, geo, role |
| Enterprise CA Management | Phát hành/thu hồi Certificate cho thiết bị |
| Remote Wipe & Revoke | Gửi lệnh xóa thiết bị từ xa qua MLS Epoch Rotation |
| DLP Policy Config | Thiết lập ngưỡng file size, loại file bị Quarantine |
| Bot Deployment | Tạo Bot, gán API Key từ Vault, thêm vào Channel |
| Escrow Key Access | Giải mã dữ liệu theo yêu cầu pháp lý (có audit) |
| Rate Limiting Config | Thiết lập giới hạn API theo phòng ban qua OPA |
| Offline TTL Config | Điều chỉnh `OFFLINE_TTL` (mặc định 24h) qua OPA |
| SCIM Integration Setup | Kết nối Azure AD/Okta/Google Workspace |
| Federation Config | Thiết lập mTLS trust với tổ chức TeraChat khác |

**Bị giới hạn:** Không đọc plaintext tin nhắn của User (Server Zero-Knowledge không giải được). Recovery Key chỉ giải mã được với sự đồng thuận M-of-N.

---

### 2.4 Channel Manager

**Quyền hạn:** Phạm vi Channel được giao.

| Chức năng | Hành động |
|---|---|
| Thêm/xóa thành viên Channel | Trigger MLS Epoch Rotation |
| Pin file trong Channel (Tầng 1 Auto Download) | Rust Core tự tải file về thiết bị thành viên |
| Xóa tin nhắn trong Channel | Gửi Delete Event vào MLS Group |
| Thiết lập TTL tin nhắn Custom | Override TTL mặc định 14 ngày |
| Mute / Block thành viên | OPA scope Channel |

---

### 2.5 Supervisor (DLP Multi-Sig)

| Chức năng | Điều kiện |
|---|---|
| Nhận thông báo file bị Quarantine | OPA intercept file gửi từ R&D sang Vùng 2 |
| Xem trước nội dung file Quarantine | Giải mã bằng Supervisor Key trong Session |
| Ký Phê duyệt (Secure Enclave) | Cần M-of-N Supervisor ký đủ → File được Release |
| Từ chối + ghi log | File bị xóa, Audit Log ghi nhận |

---

### 2.6 Bot / AI Worker

- **Không phải human user** — là process chạy trong TEE (Intel SGX / AMD SEV / AWS Nitro)
- Được cấp `Channel_Key` dạng mã hóa bằng Enclave Public Key
- Chỉ giải mã Channel_Key trong Secure Enclave RAM
- Gọi LLM API, zeroize Channel_Key và API Key ngay sau mỗi request
- Không thể gọi bất kỳ OS syscall nào ngoài Enclave sandbox
- Remote Attestation: Client verify CPU certificate trước khi gửi Channel_Key

---

### 2.7 API Client (External Integration)

| Scope | Quyền |
|---|---|
| `messages:read` | Đọc tin nhắn Channel được phép |
| `messages:write` | Gửi tin nhắn vào Channel |
| `users:read` | Đọc danh sách User (ẩn plaintext attr) |
| `scim:write` | SCIM Provisioning |
| `audit:read` | Đọc Audit Log (chỉ Auditor client) |

Rate Limiting áp dụng: Sliding Window 100 req/phút/client.

---

## 3. Feature Breakdown — Feature Tree

### 3.1 E2EE Messaging (C1)

- **Mục đích:** Trao đổi nội dung an toàn tuyệt đối — Server không bao giờ có plaintext.
- **Protocol:** MLS RFC 9420, TreeKEM O(log n), Sealed Sender.
- **Input:** Plaintext message từ User, Channel_Key từ MLS Group State.
- **Output:** Encrypted Ciphertext gửi lên Server → forward đến Recipient mailbox.
- **Điều kiện kích hoạt:** User đã được thêm vào MLS Group và thiết bị đã đăng ký KeyPackage.
- **Dependency:** HKMS (C4), Identity Binding (C2), Cluster network.
- **Edge cases:**

| Trường hợp | Hành vi |
|---|---|
| Recipient offline | Store-and-Forward Mailbox — giữ 14 ngày |
| Epoch Rotation xảy ra giữa chừng | Client tái mã hóa với Epoch mới, retry |
| ACK từ Recipient thất bại | Server giữ bản cũ, retry sau 30s |
| User bị revoke trong lúc nhắn | Server Epoch Rotation, message drop |
| Recipient có 3 thiết bị | Server nhân 3 bản copy, từng device ACK riêng lẻ |

---

### 3.2 Encrypted File Transfer — Salted MLE + Strict E2EE (C3)

- **Mục đích:** Gửi file có dedup server-side mà không lộ nội dung.
- **Heuristics Engine phân luồng:**

| Điều kiện | Route | Mô tả |
|---|---|---|
| DM hoặc kênh bảo mật cao | Strict E2EE | `File_Key` random, không dedup, không qua MLE |
| File < 5MB | Strict E2EE | File nhỏ không cần dedup |
| File nhạy cảm (PDF, DOCX phát hiện PII) | Strict E2EE | Heuristics Engine classify |
| File phổ thông ≥ 5MB, kênh nhóm phổ thông | Salted MLE | Dedup, tiết kiệm storage |

- **Salted MLE flow (sau Fix #2 — Static_Dedup_Key):**
  1. `CAS_Hash = HMAC-SHA256(Static_Dedup_Key, file_content)` — bất biến xuyên MLS Epoch
  2. `MLE_Key = HMAC-SHA256(Channel_Key, file_content)` — xoay theo Epoch (Forward Secrecy)
  3. `Ciphertext = AES-256-GCM(MLE_Key, file_content)`
  4. Server check `CAS_Hash` → MISS → upload; HIT → trả CAS reference, không upload lại
- **Static_Dedup_Key:** Sinh từ `HKDF-SHA256(Channel_Master_Secret, "dedup-v1")` lúc tạo Channel, không bao giờ thay đổi.
- **Edge cases:**

| Trường hợp | Hành vi |
|---|---|
| Cùng file gửi lại sau MLS Epoch Rotation | CAS_Hash giống → HIT → không upload lại ✓ |
| File 0 byte | Từ chối ở Client, hiển thị lỗi |
| Upload thất bại giữa chừng | Chunked upload retry từ chunk cuối cùng thành công |
| LAN/Mesh (offline) | Stream ciphertext P2P qua Wi-Fi Direct; sync CAS lên Cluster sau |

---

### 3.3 Offline / Survival Link (C5)

- **Mục đích:** Duy trì liên lạc khi mất Internet hoàn toàn (hầm mỏ, giàn khoan, thảm họa).
- **Trigger:** App phát hiện mất Internet → tự động chuyển Survival Link mode (User-Prompted Fallback).
- **Dependency:** BLE 5.0, Wi-Fi Direct/AWDL, MeshQosRouter.
- **QoS phân luồng (sau Fix #3):**

| Lane | Giao thức | Payload | Hành vi |
|---|---|---|---|
| Lane 1 — Critical | BLE 5.0 Gossip | Text < 4KB, Discovery | Gửi ngay lập tức |
| Lane 2 — Bulk | Wi-Fi Direct / AWDL | File, CRDT blob, .tapp sync | Queue đến khi có Wi-Fi Direct channel |

- **Security khi Offline:**
  - Cert-Based Auth: chỉ thiết bị có Enterprise Certificate mới vào Mesh
  - Offline TTL 24h: Rust Core tự đóng băng Session nếu chưa ping Server trong 24h
  - Gossip CRL: 1 node bắt được Internet → lan truyền danh sách revoke sang toàn Mesh trong ~30s (Ed25519 signed)
  - Prim's Algorithm: chọn spanning tree tối ưu cho Mesh topology
- **Edge cases:**

| Trường hợp | Hành vi |
|---|---|
| Nhân viên bị đuổi sáng, Mesh sập chiều | Offline TTL chặn sau 24h. Gossip CRL revoke nếu 1 node online |
| BLE range quá xa (> 100m) | Wi-Fi Direct phải handshake trước qua BLE — fail → không kết nối |
| 50 thiết bị gửi file cùng lúc qua BLE | Lane 2 Queue — BLE không bị flood, Lane 1 text không bị đứt |

---

### 3.4 Secure Key Management / HKMS (C4)

- **Key Hierarchy:**
  - `Master_Key` → trong Secure Enclave/TPM, không bao giờ rời chip
  - `KEK` (Key Encryption Key) → wrap DEK, rotate 30 ngày
  - `DEK` (Data Encryption Key) → mã hóa DB instance
  - `Channel_Key` → MLS TreeKEM, rotate khi Epoch thay đổi
  - `Static_Dedup_Key` → HKDF từ Channel_Master_Secret, không bao giờ rotate
  - `Company_Key` → mã hóa .tapp data trước khi lên Server
  - `Company_Media_Key` → Tenant-level key cho Salted MLE xuyên Channel

- **Dead Man Switch:**
  - Monotonic Hardware Counter (iOS Secure Enclave / Android StrongBox)
  - Counter++ mỗi lần unlock DB. Server lưu "Last Valid Counter"
  - Nếu Counter < Server Value → thiết bị bị clone → Remote Wipe + reject
  - Offline Grace: 72h

- **Crypto-Shredding:** Xóa KEK từ Secure Enclave → DEK không decrypt được → DB = garbage.

- **Remote Wipe flow:**
  1. Admin revoke user trên Server
  2. MLS Epoch Rotation: user bị loại khỏi Group
  3. App nhận `onEpochChanged` + self in `removedMembers`
  4. `KeyStore.deleteKeys()` → xóa Private Key
  5. `WatermelonDB.unsafeResetDatabase()` → drop chat DB
  6. Sandbox files xóa sạch
  7. Thực thi trong `autoreleasepool` (iOS) / `try-finally` (Android) — không thể block

---

### 3.5 AI Virtual Employee (S4)

- **Mục đích:** Bot AI tham gia Channel như user thực, được gọi qua `@gpt`, chạy trong TEE để đảm bảo Zero-Knowledge.

- **Kiến trúc TEE (sau Fix #4):**
  - Secure Enclave cách ly RAM hoàn toàn: Host OS, Hypervisor, Root Admin không đọc được
  - Remote Attestation: Client verify CPU certificate (Intel/AMD/AWS Root CA) trước khi gửi Channel_Key
  - Channel_Key truyền dạng `Enclave_PubKey.encrypt(channel_key)` — Host OS chỉ thấy ciphertext

- **Flow xử lý request:**
  1. User gõ `@gpt [câu hỏi]` → Channel_Key mã hóa → gửi lên VPS
  2. Enclave giải mã Channel_Key trong RAM cách ly
  3. Enclave giải mã tin nhắn + unseal API Key từ Vault
  4. Gọi LLM API (OpenAI/Claude/Gemini)
  5. Zeroize Channel_Key + API_Key khỏi RAM ngay lập tức
  6. Mã hóa response → gửi về Channel

- **Edge cases:**

| Trường hợp | Hành vi |
|---|---|
| LLM API timeout | Enclave trả error message vào Channel, zeroize key |
| Remote Attestation fail | Client từ chối gửi Channel_Key — Bot không hoạt động được |
| Enclave bị memory dump | RAM mã hóa cứng bởi CPU hardware key — không đọc được |
| Bot bị remove khỏi Channel | Epoch Rotation — Bot không còn nhận được tin mới |

---

### 3.6 Enterprise Utility Tools (.tapp) (S5)

- **Mục đích:** Công cụ nghiệp vụ chuyên biệt chạy trong WASM Sandbox, không cần Internet.
- **Runtime:** WASM Sandbox — không có OS syscall, không có Network trực tiếp.
- **Data sync (sau Fix #1 — Hybrid Event-Sourcing):**
  - CRDT Automerge: chỉ cho Schema/State (vài KB)
  - Event Log: dữ liệu thực tế (< 1KB/event) → `push_app_event_log()` → Cluster Blind Storage
  - RAM tiết kiệm ~95% so với CRDT thuần túy
- **Mobile workaround:** iOS cấm WASM dynamic → `.tapp` Mobile trả về JSON Adaptive Cards; React Native/Flutter đóng vai Engine Renderer tĩnh.

**Danh sách Tool hiện tại:**

| Tool | Slash Command | Đối tượng |
|---|---|---|
| Smart Order Entry | `/order` | Nhà hàng, F&B, Kiosk |
| POS Terminal | `/pos` | Thanh toán bán hàng |
| Magic Logger | `/log` | Ghi nhật ký sự cố, vận hành |
| CRM Lite | `/crm` | Quản lý khách hàng nội bộ |
| Ticket System | `/ticket` | IT Helpdesk |

---

### 3.7 TeraVault — Virtual File System (S3)

- **Mục đích:** Tổ chức file doanh nghiệp theo cây thư mục ảo; không duplicate dữ liệu vì dùng pointer đến E2EE blob trên Cluster.
- **Nguyên tắc:** Không có file vật lý trong TeraVault — chỉ có mappings đến `cas_hash` của file đã upload.
- **Auto-mapping:** File upload từ Channel → tự động xuất hiện trong TeraVault folder tương ứng.
- **ZK Search:** Tìm kiếm file qua FTS5 local index (metadata: tên, loại, ngày) — không gửi query lên Server.
- **Access Control:** OPA Policy — nhân viên chỉ thấy file của phòng ban mình.

---

### 3.8 DLP Multi-Sig Quarantine (A4) + Smart Clipboard (S6)

**DLP Multi-Sig Quarantine:**
- Trigger: OPA intercept khi file từ phòng R&D gửi sang Vùng 2 (bên ngoài)
- Client sinh `File_Key`, mã hóa E2EE cho Recipient + N Supervisors
- M-of-N ký Phê duyệt bằng Secure Enclave → Release
- Không đủ chữ ký trong TTL → file bị xóa, Audit Log ghi

**DLP Smart Clipboard:**
- Ngăn copy text từ cửa sổ nội bộ sang app bên ngoài (phát hiện app đích qua IPC)
- Phát hiện `SYSTEM_ALERT_WINDOW` (overlay) → vô hiệu hóa Smart Approval
- Clipboard được mã hóa trong bộ nhớ — app bên ngoài chỉ thấy ciphertext rác

---

### 3.9 Zero-Knowledge Search (S2)

- **Mục đích:** Tìm kiếm tin nhắn lịch sử mà không gửi bất kỳ query hay metadata lên Server.
- **Index:** Desktop Background Worker lập chỉ mục toàn bộ tin nhắn đã giải mã bằng SQLite FTS5.
- **Mobile:** Local FTS5 index giới hạn theo window lịch sử (không phải toàn bộ — giới hạn Storage).
- **Legacy/Archive:** Export từ Slack → mã hóa `Archive_Key` → `.sqlite.enc` → FTS5 qua tab "Archive".
- **Edge case:** Tin nhắn chưa được giải mã (offline lâu ngày) → không xuất hiện trong kết quả tìm kiếm.

---

### 3.10 Push Notification E2EE — NSE / FCM (C6)

- **iOS — NSE (Notification Service Extension):**
  - Dùng `mutable-content: 1` (không phải `content-available`)
  - NSE nhận Push → giải mã notification preview trong Enclave context
  - Giới hạn cứng: 24MB RAM, 30s timeout
  - NSE build chỉ load Micro-Crypto: AES-256-GCM + Ed25519. Loại bỏ MLS, CRDT, SQLCipher write
  - Zeroize ngay sau giải mã — không lưu gì trong NSE context

- **Android — FCM:**
  - `content-available: 1` wake-up App
  - App kết nối TCP tới Cluster, tải bản mã, giải mã bằng Private Key trong StrongBox
  - Phát Local Notification

- **Edge cases:**

| Trường hợp | Hành vi |
|---|---|
| iOS Force Kill app | NSE vẫn chạy độc lập — vượt qua giới hạn Force Kill |
| NSE vượt 24MB RAM | iOS OOM kill NSE → thông báo rỗng (chỉ "Có tin nhắn mới") |
| FCM không khả dụng (China/offline) | Mesh BLE Discovery làm phương án dự phòng |

---

## 4. User Flow & System Flow

### 4.1 Happy Path — Nhắn tin thông thường

```
[User A gõ tin nhắn]
       ↓
Rust Core mã hóa bằng Channel_Key (MLS Epoch hiện tại)
       ↓
Sealed Sender wrapping — Server không biết từ ai
       ↓
Ciphertext gửi lên Private Cluster
       ↓
Cluster định tuyến đến Mailbox của từng thiết bị đã đăng ký của User B
       ↓
User B online → tải ciphertext → giải mã bằng Channel_Key → hiển thị
       ↓
Client B gửi ACK → Server xóa bản này khỏi Mailbox
```

### 4.2 Happy Path — Gửi file lớn (Salted MLE)

```
[User A chọn file 150MB — setup.exe]
       ↓
Heuristics Engine: kênh nhóm phổ thông + file > 5MB → Salted MLE
       ↓
CAS_Hash = HMAC-SHA256(Static_Dedup_Key, file) → gửi check Cluster
       ↓
Cluster: HIT (đã có) → không upload lại → trả CAS reference
       ↓
User A tạo FileStub: {cas_ref, mle_key wrapped bằng PubKey User B}
       ↓
FileStub gửi vào Channel (E2EE như tin nhắn thường)
       ↓
User B nhận Stub → click download → Cluster trả ciphertext → giải mã bằng mle_key
```

### 4.3 Error Path — Nhân viên nghỉ việc

```
[HR deactivate user trên Azure AD]
       ↓
SCIM Listener nhận webhook → mark user inactive trong PostgreSQL
       ↓
Auto-Revoke Trigger PostgreSQL → revoke Certificate
       ↓
Admin xác nhận → Server phát MLS Epoch Rotation cho tất cả Channel user đó tham gia
       ↓
Tất cả thiết bị nhận Epoch mới → Channel_Key cũ bị invalidate
       ↓
Thiết bị của nhân viên cũ nhận `removedMembers` → trigger Remote Wipe tự động
       ↓
Gossip CRL: nếu đang Mesh offline → lan truyền revoke trong ~30s
       ↓
Sau 24h Offline TTL: Session frozen hoàn toàn dù Mesh vẫn hoạt động
```

### 4.4 Error Path — File bị OPA Quarantine (DLP)

```
[Nhân viên R&D gửi file bí mật sang đối tác ngoài]
       ↓
OPA intercept: (Dept==R&D) AND (Destination=Zone2) → QUARANTINE
       ↓
Client sinh File_Key → mã hóa E2EE cho Recipient + N Supervisors
       ↓
Gói neo trên Message Queue (chưa deliver)
       ↓
Supervisor nhận thông báo → xem trước → ký Phê duyệt (Secure Enclave)
       ↓
Đủ M-of-N chữ ký → OPA release → Gói deliver đến Recipient
       ↓  (nếu không đủ)
TTL hết hạn → File bị Crypto-Shred, Audit Log ghi nhận đầy đủ
```

### 4.5 Abuse / Misuse Path — Thiết bị bị clone / Time Travel Attack

```
[Hacker clone ảnh snapshot thiết bị → revert về trạng thái cũ]
       ↓
Hardware Monotonic Counter bị revert (iOS Secure Enclave biết)
       ↓
Khi online, Client gửi Counter hiện tại lên Server
       ↓
Server: Counter < Last Valid Counter → Device bị clone
       ↓
Server từ chối cấp Session Token + phát Remote Wipe tới thiết bị gốc
       ↓
Admin nhận alert, điều tra
```

### 4.6 Abuse Path — Overlay Attack (WYSIWYS)

```
[Hacker cài app độc, vẽ overlay che đổi số tiền phê duyệt]
       ↓
TeraChat Anti-Overlay: quét SYSTEM_ALERT_WINDOW liên tục
       ↓
Phát hiện overlay → vô hiệu hóa Smart Approval flow
       ↓
Fallback: yêu cầu nhập Password thủ công
       ↓
BiometricPrompt / System-Managed UI hiển thị dữ liệu gốc (không bị overlay)
       ↓
User xác nhận trên System UI (không phải App UI) → ký bằng Secure Enclave
```

---

## 5. Non-Functional Requirements

### 5.1 Bảo mật

| Yêu cầu | Cách thực hiện |
|---|---|
| E2EE toàn diện | MLS RFC 9420, Sealed Sender, không plaintext lên Server |
| Zero-Knowledge Server | Server chỉ thấy ciphertext + metadata tối thiểu |
| Hardware-backed key | iOS Secure Enclave, Android StrongBox, PC TPM 2.0 |
| Anti-tampering | Binary Hardening (O-LLVM), Hash `.text section` khi khởi chạy |
| Remote Attestation | DCAppAttestService (iOS), Play Integrity API (Android), TPM Health (Windows) |
| Continuous Fuzzing | LibFuzzer (Packet Parser), AFL++ (File Format), LLVM Sanitizers |
| Formal Verification | Z3 SMT Solver cho OPA Policy + Approval Logic |
| AI Isolation | TEE (Intel SGX / AMD SEV / AWS Nitro) + Remote Attestation |

### 5.2 Hiệu năng

| Target | Chỉ tiêu |
|---|---|
| E2EE decrypt latency | < 5ms (Rust FFI trực tiếp, không qua JS Bridge) |
| FTS5 search | < 100ms cho 1 triệu tin nhắn |
| MLS TreeKEM | O(log n) — nhóm 5000 user không gây lag |
| APNS delivery | < 2s kể từ khi gửi (NSE model) |
| Mesh GossipCRL propagation | < 30s cho 50 node |
| Cluster HA Failover | < 3s (Floating IP) |
| File dedup savings | 99% cho file phổ thông được gửi nhiều lần |

### 5.3 Khả năng mở rộng (Scalability)

- Cluster Erasure Coding: 3–5 nodes, tự phục hồi khi 1 node sập
- MLS TreeKEM: linear scalability đến nhóm 5000+ người
- SCIM Listener: real-time HR sync không giới hạn số lượng user
- Hybrid Event-Sourcing: Event Log ~1KB/event → không phình RAM theo thời gian
- GeoHash OPA: O(1) geo-lookup thay Haversine O(n)

### 5.4 Logging / Audit

| Loại log | Nội dung | Ai đọc được |
|---|---|---|
| Audit Log (DLP) | Ai gửi gì, khi nào, có bị quarantine không | Auditor (read-only) |
| Crash Log | Stack Trace chỉ — text đã xóa, mã hóa Admin PubKey | Admin sau giải mã |
| Federation Audit | Mọi request xuyên tổ chức, OPA decision | Auditor cả 2 bên |
| Security Event | Attestation fail, Counter mismatch, Clone detect | Admin + SIEM |
| Rate Limiting Log | Redis ZSET timestamps — không chứa nội dung | Admin |

### 5.5 Khả năng tích hợp (API / Webhook / Third-party)

| Integration | Giao thức | Direction |
|---|---|---|
| Azure AD / Google Workspace / Okta | SCIM 2.0 + OIDC/SAML | Inbound (HR → TeraChat) |
| SAP / Jira / CRM | Business API (REST + Webhook) | Bidirectional |
| External LLM (OpenAI / Claude / Gemini) | HTTPS (từ Enclave) | Outbound (AI Worker) |
| External Messaging (Zalo / Telegram) | Isolated WebView | Outbound (controlled) |
| Federation (TeraChat ↔ TeraChat) | mTLS + Sealed Sender | Bidirectional |
| SIEM / Security Platform | Webhook / Syslog | Outbound (Audit) |
| Custom `.tapp` API | REST (Cluster Interop Hub) | Internal |

---

## 6. Câu hỏi hệ thống chưa được định nghĩa

### 6.1 Những chỗ mơ hồ

| # | Vấn đề | Impact |
|---|---|---|
| Q1 | **DLP: Ngưỡng "file nhạy cảm" Heuristics Engine là gì?** Regex-based? ML model? Admin config? | Nếu sai → Salted MLE áp dụng nhầm cho file nhạy cảm |
| Q2 | **M-of-N DLP: N và M mặc định là bao nhiêu?** Admin config hay cứng trong code? Hết TTL bao lâu? | Nếu quá cao → tắc nghẽn workflow |
| Q3 | **Static_Dedup_Key thu hồi khi nào?** Khi Channel bị xóa? Khi Admin reset? | Nếu không có cơ chế xóa → dedup key leak tiềm ẩn |
| Q4 | **Offline TTL 24h: Admin được phép giảm xuống bao nhiêu phút?** | Nếu quá ngắn → thiết bị hiện trường bị lock giữa ca làm việc |
| Q5 | **TeraVault: Khi file gốc trong Channel bị xóa → mapping trong TeraVault còn không?** | Nếu còn → orphan pointer; nếu xóa → user mất file không báo trước |
| Q6 | **Kiosk Mode iPad: PIN TTL là bao lâu?** Hết PIN → auto logout hay hỏi xác thực lại? | Ảnh hưởng UX ca làm việc ban đêm |
| Q7 | **Federation Trust: Tổ chức A có thể query danh sách User của tổ chức B không?** | Nếu có → privacy leak; nếu không → Sealed Sender cần được document rõ |
| Q8 | **AI Bot: Nếu Enclave chạy trên provider không hỗ trợ TEE (VPS rẻ)?** | Không có fallback → Bot deploy thất bại mà không có error rõ ràng |

### 6.2 Quyết định kiến trúc cần làm rõ

| # | Quyết định | Phương án hiện tại | Cần confirm |
|---|---|---|---|
| D1 | **Event Log conflict resolution** | Last-Write-Wins theo Timestamp | Nếu 2 thiết bị offline sync cùng Event ID → collision? |
| D2 | **NSE fallback khi vượt 24MB** | Hiển thị "Có tin nhắn mới" (ẩn nội dung) | Có rò thông tin gì không? |
| D3 | **Mobile .tapp Adaptive Cards** | JSON renderer tĩnh | List Card types hỗ trợ? Input type? |
| D4 | **Company_Media_Key vs Static_Dedup_Key** | Hai key tách nhau | Liệu có thể gộp thành 1 concept không? |
| D5 | **Gossip CRL size giới hạn** | BLE packet MTU ~512 bytes | CRL rất lớn (nhiều revoke) → cần fragmentation? |

### 6.3 Rủi ro nếu bỏ qua

| Rủi ro | Mức độ | Giải pháp đề xuất |
|---|---|---|
| Heuristics Engine phân loại sai → file nhạy cảm đi qua Salted MLE | HIGH | Audit log mọi Heuristics decision. Allow-list file extension ngay cả trong kênh nhóm |
| Event Log không có sequence number → replay attack | MEDIUM | Thêm `seq_id` monotonic per-device vào AppEvent struct |
| TEE không available trên VPS rẻ → AI Bot deploy không có isolation | HIGH | Fallback: chạy Bot trong Docker với seccomp và no-network policy (giảm cấp bảo mật, phải document) |
| Gossip CRL delay 30s → window vulnerability với nhân viên bị đuổi | MEDIUM | Kết hợp với Offline TTL 24h — acceptable trade-off trong hầu hết môi trường |
| TeraVault orphan pointer sau khi xóa file gốc | LOW | Implement soft-delete CASCADE: xóa file Channel → mark mapping as "deleted" trong TeraVault |

---

*Tài liệu này chỉ mô tả chức năng và cấu trúc hệ thống. Xem `TechSpec.md` cho implementation details, `PRD.md` cho user flows và `BusinessPlan.md` cho chiến lược go-to-market.*
