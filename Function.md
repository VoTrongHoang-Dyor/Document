```yaml
# DOCUMENT IDENTITY
id:       "TERA-FUNC"
title:    "TeraChat — Function & Capability Blueprint"
version:  "0.2.5"
audience: "Product Manager, CEO, Sales Engineer, Customer Success, Developer, Investor"
purpose:  "Strategic product reference: full functional architecture, system capabilities,
           component interactions, and core value propositions of TeraChat."

ai_routing_hint: |
  "Open this file to understand what TeraChat can do and why — covering role-based
   permissions, business flows, AI integration, cross-org Federation, and the .tapp
   plugin ecosystem. This is the Product-level source of truth."
```

---

> *"Trong thế giới mà dữ liệu là quyền lực, ai kiểm soát khóa mã hóa — kẻ đó làm chủ cuộc chơi.
> TeraChat trao lại chìa khóa đó về tay doanh nghiệp."*
>
> — CEO, TeraChat

---

# TeraChat — Function & Capability Blueprint

**TERA-FUNC v0.2.5 · March 2026 · Internal Document**

---

## Tóm Tắt Điều Hành

TeraChat không phải là ứng dụng nhắn tin. Đây là **Hệ điều hành Công việc Chủ quyền** (Sovereign Work OS) — nền tảng cộng tác doanh nghiệp được bảo vệ bằng toán học, nơi không có bất kỳ máy chủ, nhà cung cấp hay đối thủ nào có thể đọc được dữ liệu mà TeraChat truyền tải.

| Giá Trị Cốt Lõi | Cơ Chế Thực Thi |
|---|---|
| Bảo mật bằng Toán học | Zero-Knowledge: server chỉ định tuyến ciphertext, không bao giờ plaintext |
| Sinh tồn Offline | BLE 5.0 + Wi-Fi Direct Mesh — hoạt động khi không có Internet |
| Kiểm soát Doanh nghiệp | Admin-owned keys, HSM-backed KMS, OPA Zero-Trust enforcement |
| Nền tảng Mở rộng | .tapp WASM sandbox Marketplace với chữ ký mật mã học |
| Kết nối Liên tổ chức | Federation Bridge mTLS + Sealed Sender Protocol |
| AI Ưu tiên Riêng tư | SLM trên thiết bị + PII redaction trước mọi cuộc gọi LLM bên ngoài |

**Biểu tượng platform:**

- 📱 iOS / Android / Huawei (Mobile)
- 💻 Laptop / macOS
- 🖥️ Desktop / Windows / Linux
- 🗄️ Bare-metal Server
- ☁️ VPS Cluster / Cloud

**Chế độ hoạt động:**

- ☀️ **Online Mode** — Giao diện Sáng, kết nối Cloud/Server
- 🌑 **Mesh Mode** — Giao diện Tối, hoạt động offline P2P

---

## Module 1 — Lõi Mật Mã & Quản lý Khóa

> **Nguyên tắc bất biến:** Khóa riêng tư không bao giờ rời khỏi phần cứng. Plaintext không bao giờ tồn tại ngoài phạm vi. Không có ngoại lệ.

### 1.1 Hệ thống Quản lý Khóa Phân tầng (HKMS)

```
[Master Key] — HSM FIPS 140-3 L3 / Secure Enclave / TPM 2.0 (không bao giờ xuất ra ngoài)
      │
      └──► [Company_Key] — mã hóa toàn bộ dữ liệu workspace
                 │
                 ├──► [Epoch_Key] — khóa phiên MLS, ZeroizeOnDrop khi rotation
                 ├──► [Push_Key] — chuỗi HKDF một chiều, cô lập khỏi TreeKEM
                 └──► [Escrow_Key] — Shamir SSS M-of-N, tồn tại trong RAM < 100ms
```

- **Shamir Secret Sharing (mặc định 3-of-5):** `Enterprise_Escrow_Key` chia thành 5 mảnh cho 5 C-Level. Cần đúng 3 mảnh mới tái tạo được.
- **ZeroizeOnDrop:** Mọi struct chứa plaintext tự xóa bộ nhớ (ghi đè 0x00) khi hết phạm vi.
- **Dead Man Switch:** Bộ đếm monotonic TPM 2.0 giới hạn offline TTL (Consumer 24h / Enterprise configurable / GovMilitary 30 ngày).

### 1.2 Mã hóa Nhóm MLS RFC 9420

- 📱💻🖥️ Hỗ trợ tới **10.000 thành viên** trong một nhóm E2EE.
- **TreeKEM:** phân phối khóa O(log n) — hiệu quả băng thông ngay cả nhóm lớn.
- **Epoch Rotation:** kích hoạt khi thành viên rời nhóm, Admin yêu cầu, hoặc theo lịch 24h.
- **Batched Update_Path:** nhóm ≤1.000: cửa sổ 60s; ≤5.000: 300s — ngăn bão mạng.
- **Post-Quantum Hybrid (ML-KEM-768 + X25519):** tuân thủ CNSA 2.0 / NIST FIPS 203.

### 1.3 Phần cứng Bảo vệ Khóa

| Platform | Nơi lưu trữ Khóa | Cổng Xác thực |
|---|---|---|
| 📱 iOS / macOS | Secure Enclave Processor (SEP) | Face ID / Touch ID — bắt buộc |
| 📱 Android | StrongBox Keymaster HAL | BiometricPrompt — bắt buộc |
| 📱 Huawei | TrustZone TEE via HMS | HMS Biometric — bắt buộc |
| 💻🖥️ Windows | TPM 2.0 — CNG Platform Provider | Windows Hello |
| 🖥️ Linux | TPM 2.0 — tpm2-pkcs11 | PIN — bắt buộc |
| 🗄️ Bare-metal | HSM FIPS 140-3 L3 (PKCS#11) | Physical presence + Shamir quorum |

### 1.4 Cryptographic Self-Destruct

- 📱💻 **PIN thất bại 5 lần:** Crypto-Shredding toàn bộ DB nội địa + factory reset. Bộ đếm HMAC-xác thực chống giả mạo.
- 📱💻 **Remote Wipe:** Xóa `DeviceIdentityKey` khỏi phần cứng, drop mọi bảng DB, xóa WASM sandbox storage. Không thể bị người dùng ngắt.
- 📱💻 **Cryptographic Erasure (GDPR):** Hết TTL → Crypto-Shredding khóa giải mã; ciphertext vĩnh viễn không đọc được.

---

## Module 2 — Nhắn tin, Cộng tác & UX

### 2.1 Engine Nhắn tin Cốt lõi

- 📱💻🖥️ **E2EE đa phương thức:** Văn bản, tệp tin, thoại, video — mã hóa và giải mã tại thiết bị.
- 📱💻 **CRDT DAG:** Nhật ký sự kiện append-only đảm bảo nhất quán trên mọi thiết bị không cần điều phối trung tâm.
- 📱💻 **Hybrid Logical Clock (HLC):** Sắp xếp toàn phần sự kiện phân tán — không cần timestamp authority phía server.
- 📱💻 **Full-text Search Zero-Knowledge:** SQLite FTS5 tại thiết bị — server không bao giờ thấy nội dung tìm kiếm.
- 📱💻 **Message TTL:** Hết hạn → Crypto-Shredding tự động.
- 📱💻 **TeraLink Multipath:** Gửi song song qua 4G + Wi-Fi LAN + BLE Mesh — 0ms latency khi roaming.

### 2.2 Thoại & Video (WebRTC)

- 📱💻 **HD Voice & Video** qua WebRTC DTLS-SRTP, E2EE đầu cuối.
- 💻 **ICE Pool Pre-warming:** Kết nối thiết lập trước khi người dùng nhấn "Gọi" — không có màn hình chờ.
- 💻 **Failover tự động < 3s:** P2P Direct → Internal TURN relay. Badge "P2P (Direct)" hoặc "Relayed (E2EE)".
- 📱 **CallKit Integration (iOS):** Dead Man Switch lockout hoãn cho đến khi cuộc gọi kết thúc.

### 2.3 Tài liệu & Smart Approval

- 📱💻 **Smart Document với RBAC:** Viewer → Commenter → Editor (Shadow Branch).
- 💻🖥️ **Smart Approval Workflow:** Ký số với sinh trắc học (Ed25519), phân giai đoạn phê duyệt.
- 📱💻 **Conflict Resolution:** Merge/Discard khi sửa song song — không bao giờ silent LWW trên CONTRACT/POLICY/APPROVAL.
- 📱💻 **TeraVault (Virtual File System):** Kéo thả file từ chat vào VFS, không nhân bản. Preview qua Zero-Byte Stub (~5KB).

### 2.4 Hệ thống UX Glassmorphism

| Trạng thái | Chế độ UI | Màu Viền | Indicator |
|---|---|---|---|
| ☀️ Online | Light Frosted Glass | Xanh lam #24A1DE | "E2EE Active · Key Epoch N" |
| 🌑 Mesh Fallback | Dark Navy #0F172A | Radar Pulse | "📡 Survival Mesh Active" |
| ⚠️ Warning | Amber Glow | #F59E0B | Warning banner |
| 🔴 Containment | Red Border 4px | #EF4444 | FCP pulse overlay |
| ☠️ Kill-Switch | Blood-Red Frosted | Đỏ máu | Shatter animation + Shield |

**Security Event Animations (bắt buộc):**

- **Self-Destruct:** Timer ring collapse → fragment dissolve (400ms)
- **Crypto-Shred:** Pixel noise → wipe (350ms)
- **Memory Purge:** "SECURE MEMORY PURGE" overlay + progress bar

**GPU Capability Fallback:**

| Tier | Điều kiện | Rendering |
|---|---|---|
| Tier A | Hardware compositing | `backdrop-filter: blur(16–24px)` |
| Tier B | Software compositing | `blur(8px)`, opacity 0.85 |
| Tier C | No compositing (legacy) | Flat solid + border accent — full functionality |

---

## Module 3 — Survival Mesh Network

> **Cam kết:** Khi Internet sụp đổ, TeraChat không suy giảm. Nó kích hoạt mạng P2P tự tổ chức, bảo mật mật mã học, không cần server trung tâm.

### 3.1 Mô hình Kết nối 4 Tầng

| Tầng | Transport | Throughput | Kích hoạt khi |
|---|---|---|---|
| ☀️ Tier 1 — Online | QUIC / gRPC / WSS | > 100 Mbps | Bình thường |
| 🌑 Tier 2 — Wi-Fi Mesh | AWDL / Wi-Fi Direct | 250–500 MB/s | LAN, không Internet |
| 🌑 Tier 3 — BLE Control | BLE 5.0 (< 15 mW) | ~50ms latency | Control plane |
| 🌑 Tier 4 — BLE Emergency | BLE Long Range | Text-only | EMDP active |

**Adaptive Voice Codec:**

- Tier 1 → Opus 128kbps Stereo
- Tier 2 → AMR-NB 4.75kbps Mono
- Tier 3 → Whisper local transcription → text only (tắt mic UI)

### 3.2 Vai trò Mesh Node

| Vai trò | Platform | Lưu trữ | Trách nhiệm |
|---|---|---|---|
| **Super Node** | 💻🖥️ Desktop (AC) | 500MB–1GB / 48–72h | Backbone, DAG merge dictator |
| **Relay Node** | 📱 Android (RAM ≥ 3GB) | 100MB / 24h | Intermediate relay |
| **Tactical Relay (EMDP)** | 📱 iOS (emergency) | 1MB / 60 phút | Text-only CRDT buffer |
| **Leaf Node** | 📱 iOS (luôn luôn) | 50MB receive-only | Nhận tin, không định tuyến |
| **Border Node** | Bất kỳ (Internet + BLE) | N/A | Bridge TCP/IP ↔ BLE Mesh |

> **Quy tắc kiến trúc bất biến:** `iOS election_weight = 0` — iOS không bao giờ là Merge Dictator.

### 3.3 BLE Stealth Beaconing

- 📱💻 **31-byte BLE PDU:** không chứa device identifier. Scanner thụ động chỉ thấy entropy.
- 📱💻 HMAC-BLAKE3 commitment với slot rotation 5 phút. MAC rotation: iOS mỗi 15 phút, Android/Desktop mỗi 5 phút.
- 📱💻 Duty cycle: 200ms active / 800ms sleep (20%). Standby: 1 beacon / 5 phút.

### 3.4 Split-Brain & Dictator Election

- **Bầu cử xác định, không bỏ phiếu:** BLAKE3 hash Node ID quyết định người thắng. Handover < 10ms.
- 🌑 **DAG Merge O(N log N):** Rayon parallel — chỉ trên Desktop. Mobile nhận `Materialized_Snapshot` → áp dụng O(1).
- **Chính sách xung đột:** MESSAGE → giữ cả hai phiên bản. CONTRACT/POLICY/APPROVAL → yêu cầu giải quyết thủ công.

### 3.5 Emergency Mobile Dictator Protocol (EMDP)

Kích hoạt khi: không có Desktop + không có Internet + ≥ 2 iOS pin > 20%.

- 📱 Text-only Store-and-Forward. Không merge DAG, không MLS Epoch rotation.
- 📱 Key Escrow: Desktop chuyển session key sang iOS qua ECIES/Curve25519 trước khi offline.
- 📱 TTL 60 phút. Extension ở phút 50: chuyển giao sang peer pin cao hơn.

---

## Module 4 — AI Privacy Shield

> **Cam kết:** AI worker không bao giờ trực tiếp truy cập database tin nhắn. PII luôn được redact trước bất kỳ cuộc gọi ra ngoài.

### 4.1 Pipeline AI Cô lập

```
User Prompt
    ↓ (bắt buộc)
Micro-NER PII Detection (ONNX < 1MB trên thiết bị)
    → Phát hiện: Tên, SĐT, Email, CMND, Tài khoản ngân hàng, Địa chỉ
    ↓
SanitizedPrompt (newtype — không thể tạo nếu không qua redaction)
    ↓
SessionVault { [MASK_01] → real@email.com } — ZeroizeOnDrop < 100ms
    ↓
AI Worker Process (cô lập OS — crash không ảnh hưởng Rust Core)
    → On-device SLM (CoreML / ONNX) hoặc External LLM (nếu Admin cho phép)
    ↓
Response Vec<ASTNode> (HTML/Markdown raw bị reject bởi AST Sanitizer)
    ↓
SessionVault.restore_and_drop() — alias map zeroized
```

### 4.2 Mức Kiểm soát AI (Admin-Configured)

| Tier | AI Shield | Egress Limit | Audit |
|---|---|---|---|
| **Tier 1 — Strict** | Vĩnh viễn BẬT (không thể toggle) | 0 | N/A |
| **Tier 1b — Network** | BẬT, gRPC direct (bypass UDP probe) | 0 | N/A |
| **Tier 2 — Role-Based** | C-Level / Marketing có thể tắt | 4KB hard | Ed25519-signed |
| **Tier 3 — DLP** | Tắt cho phép, hard block vẫn active | 4KB tối đa | Bắt buộc |

### 4.3 AI Runtime

| Platform | Runtime | Model tối đa | Ghi chú |
|---|---|---|---|
| 📱 iOS | CoreML (.mlmodelc) | 74MB / 39MB | W^X: không dynamic WASM AI |
| 📱 Android | ONNX Runtime | 39MB | HiAI fallback Huawei |
| 📱 Huawei | HiAI / ONNX | 39MB | AOT bundle only |
| 💻 macOS | CoreML / ONNX | 74MB | Isolated XPC Worker |
| 🖥️ Windows/Linux | ONNX Runtime | 74MB | CPU; GPU optional |

---

## Module 5 — Hệ sinh thái Plugin (.tapp)

> **Lập trường:** Không có .tapp nào được phép yêu cầu exception khỏi Sandbox. Mọi capability khai báo tường minh trong manifest, OPA Policy kiểm soát. Không có ngoại lệ.

### 5.1 Vòng đời .tapp

```
[Submit] → [WASM Static Scan] → [Manifest Audit] → [LLVM IR Heuristics]
    ↓
[Ed25519 Bundle Signing bởi Marketplace CA]
    ↓
[Client: BLAKE3 verify → Sandbox Launch]
    ↓
[Execute: OPA + Egress Circuit Breaker] ↔ [Suspend: AES-256-GCM Snapshot]
    ↓
[Terminate: RAM freed · Capability Tokens revoked · KV-Cache cleared]
```

### 5.2 Publisher Trust Tiers

| Tier | Yêu cầu | Egress | Badge |
|---|---|---|---|
| **Unverified** | Ed25519 key | HTTP GET < 1KB, no file | 🔵 Community |
| **Verified** | KYC + Key + Review | File < 10MB | ✅ Verified |
| **Enterprise** | SOC2 / ISO27001 | Full egress + custom consent | 🏢 Enterprise |
| **TeraChat Native** | First-party | Unrestricted (subject to OPA) | ⭐ Native |

### 5.3 WASM Sandbox Constraints

- 📱💻 **RAM:** ≤ 64MB softcap — vượt → OOM-kill không cảnh báo.
- 📱💻 **CPU:** ≤ 10% sustained — spike ≤ 500ms.
- 📱💻 **Egress Circuit Breaker:** 4.096 bytes/call hard limit. 3 vi phạm/session → terminate + quarantine.
- ☁️ **Session Quota:** 512KB tổng egress/session — vượt → suspend + Admin alert.
- 📱💻 **No Persistent Storage Egress:** `storage.read → network.write` yêu cầu user consent mỗi lần.
- 💻🖥️ **Timing Defense:** 5ms Fixed-Interval Dispatch Metronome + ChaCha20 noise padding.

### 5.4 Capability Declaration

| Capability | Grant Condition | Default |
|---|---|---|
| `network.egress` | Chỉ domain khai báo trong manifest | ❌ Blocked |
| `clipboard.read` | User consent per-session | ❌ Blocked |
| `file.read` | Explicit user file picker | ❌ Blocked |
| `crypto.sign` | Publisher Ed25519 proof | ❌ Blocked |
| `push.notify` | Admin whitelist per-tenant | ❌ Blocked |

### 5.5 Host Function ABI Versioning

```json
{ "host_api_version": "1.3.0", "min_host_api_version": "1.0.0", "max_host_api_version": "2.0.0" }
```

- Breaking changes chỉ trong major version. Minor: additive-only.
- Support 2 major versions đồng thời (deprecation window 12 tháng).

---

## Module 6 — Identity, RBAC & Quản trị

### 6.1 Role-Based Access Control

| Vai trò | Năng lực | Ràng buộc |
|---|---|---|
| **CISO / Admin** | Toàn quyền: KMS, policy, revocation, federation, audit | HSM quorum cho policy changes |
| **HR Recovery Officer** | Device re-provisioning, identity recovery | Không thể đọc nội dung tin nhắn |
| **Editor** | Tạo/sửa tài liệu, `ffi_propose_change` | Không có quyền key ceremony |
| **Commenter** | Ghi chú shadow branch | Read + comment only |
| **Viewer** | Chỉ đọc, FFI pointer frozen | `ZeroizeOnDrop` khi thoát |

### 6.2 OPA Policy Engine

- 📱💻☁️ Mọi hành động phải qua OPA Rego Policy. Không có bypass.
- 🗄️☁️ **M-of-N HSM Quorum (2-of-3: CISO + CTO + Legal):** Không một cá nhân đơn lẻ nào có thể thay đổi production policy.
- ☁️ **Policy Rollback Protection:** Monotonic version counter — client từ chối bundle version thấp hơn.
- 📱💻 **Local enforcement:** OPA WASM build tại thiết bị. Không round-trip server.

### 6.3 Device Recovery

**TH1 — Mất CẢ thiết bị:**

1. CEO khởi tạo Break-glass → BLE beacon đến C-Level trong phạm vi < 2m.
2. ≥ 3-of-5 C-Level xác thực sinh trắc học trong **10 phút** (Quorum Timer).
3. Lagrange Interpolation tái tạo `Escrow_Key` trong mlock-protected arena **< 100ms** → zeroize.
4. Thiết bị cũ nhận Remote Wipe khi chạm mạng.

**TH2 — Mất Điện thoại, Laptop còn:**

1. Laptop → Gossip Crypto-Shredding Device_Key cũ.
2. Điện thoại mới sinh khóa, QR → Laptop quét → Pending Approval trên VPS.
3. HR xác minh qua video call → ký Authorization Ticket.
4. Company_Key truyền qua P2P (BLE/Wi-Fi Direct). **Zero cloud exposure.**

### 6.4 SCIM 2.0 & Identity Sync

- ☁️ Azure AD / Google Workspace: nghỉ việc → tài khoản khóa trong **< 30 giây**.
- ☁️ Federation Revocation: cross-org mTLS vô hiệu trong < 30 giây.
- 📱💻 **1-Tap Magic Deep-Link:** App tự chuyển `pre_authenticated`, `Device_Key` sinh trước OIDC hoàn tất.

---

## Module 7 — Federation & Cross-Org Communication

### 7.1 Kiến trúc

- Mỗi tổ chức vận hành **Private Cluster độc lập** với ranh giới mã hóa riêng.
- ☁️ **Federation Bridge (Zone 2):** mTLS + **Sealed Sender** — server nhận không thể xác định người gửi.
- 🗄️ **Trust Registry:** append-only SQLite — không dùng public CA.
- Schema Version: ±1 minor → read-only federation. ±1 major → `SCHEMA_INCOMPATIBLE`, rejected.

### 7.2 Quy trình Kết nối

```
Admin HQ → Federation Invite Token (Signed JWT)
    ↓
Admin Branch → nạp Token → gửi kết nối kèm Public Key
    ↓
HQ approve → key exchange vào federation_trust_registry
    ↓
OPA Rate Limiting ngăn cross-org DoS
    ↓
SCIM offboarding → mTLS vô hiệu < 30s tự động
```

---

## Module 8 — Compliance, DLP & Audit

> **Nguyên tắc:** Tuân thủ thực thi bằng toán học, không phải hợp đồng. Không Admin nào có thể thay đổi lịch sử mà không phá vỡ Merkle chain.

### 8.1 Data Loss Prevention

- 📱💻 **OPA Egress Whitelist:** Egress đến domain không khai báo → bị chặn tại OS.
- 📱💻 **Byte-Quota Circuit Breaker:** 4KB/call. Vượt 100% session quota → Egress khóa 24h, CISO alert.
- 📱💻 **Format Whitelist:** [.pdf, .txt, .jpg]. `.vbs`, `.xlsm` bị chặn.
- 💻📱 **Redaction Rules:** Rust Core local ML redact CC numbers, nội bộ IP khỏi AI prompt.
- 🗄️ **Anti-Remanence Policy (ARP):** TTL Crypto-Shredding. CISO-initiated Wipe → zero-fill với Ed25519-signed checkpoint.

### 8.2 Tamper-Proof Audit Log

- 🗄️ Mọi entry mang chữ ký Ed25519. Entry không ký → reject khi ghi, không bao giờ lưu.
- 🗄️ **Merkle Chain:** Xóa bất kỳ entry nào → phá vỡ chain ngay lập tức, audit độc lập được.
- ☁️ Marketplace Transparency Log: append-only, Merkle-proofed.
- ☁️ Prometheus metrics delay 30 giây vs event time — ngăn timing correlation.

### 8.3 Incident Response

- ☁️ **PARA:** AI agent/tapp Token Taint → CISO nhận E2EE incident hash. Suspension không cần app update.
- 📱💻 **Sealing Conversation (SSA):** Taint → session read-only với hazard-stripe overlay. CISO approve Release.
- 🗄️ **OPA Banned Lexicon:** Keyword → MUTE_LOCK. Admin unlock bắt buộc.

---

## Module 9 — Infrastructure & Deployment

### 9.1 Server Topology

```
[GeoDNS]
    ├──► Zone 1: VPS Relay (Rust Blind Relay · SQLite WAL · NATS JetStream)
    ├──► Zone 2: Federation Bridge (mTLS · Sealed Sender)
    └──► Zone 0: Bare-metal HSM (HSM FIPS 140-3 · PostgreSQL · MinIO EC+4)
```

### 9.2 Scale Tiers

| Quy mô | Topology | Hardware Tối thiểu |
|---|---|---|
| ≤ 10.000 users | Single-node Rust relay | 512MB VPS |
| ≤ 100.000 users | Geo-federated clusters | PostgreSQL HA + MinIO |
| ≥ 1.000.000 users | Multi-cloud active-active | PostgreSQL Geo-Partitioning |

**TCO Reference:**

| Users | Storage/năm | Min VPS | DR RTO |
|---|---|---|---|
| 1.000 | ~500GB | 4 vCPU, 8GB RAM, 100GB SSD | < 15 phút |
| 5.000 | ~2.5TB | 8 vCPU, 16GB RAM, 250GB SSD | < 15 phút |
| 10.000 | ~5TB | 16 vCPU, 32GB RAM, 1TB SSD | < 15 phút |

### 9.3 Performance Targets

| Operation | Target | Platform |
|---|---|---|
| ALPN negotiation (full fallback) | < 50ms | All |
| MLS encrypt (single message) | < 5ms | All |
| Push notification decrypt (NSE) | < 500ms | 📱 iOS |
| End-to-end relay delivery | < 200ms | All |
| TURN failover | < 3s | WebRTC |
| VPS concurrent WebSocket | ~500.000 | ☁️ 4GB VPS |
| AES-256-GCM (hardware) | 4–8 GB/s | AES-NI / ARM NEON |
| Wi-Fi Direct file transfer | 250–500 MB/s | 📱 Mesh |

---

## Licensing & Service Tiers

| Feature | Community | Enterprise | GovMilitary |
|---|---|---|---|
| Offline TTL | 24 giờ | 7 ngày | **30 ngày** |
| EMDP Tactical Relay | ❌ | ✅ | ✅ |
| Air-Gapped License | ❌ | ✅ | ✅ |
| Compliance Retention | ❌ | 90 ngày | **7 năm** |
| TEE Enclaves (SGX) | ❌ | ❌ | ✅ |
| Chaos Engineering | ❌ | Optional | **Bắt buộc** |
| Federation | ❌ | ✅ | ✅ Air-gapped |
| AI Token Quota | 10K/giờ | Unlimited | Unlimited + local-only |

**Open-Core Boundary:**

| Component | License | Auditable by |
|---|---|---|
| `terachat-core` (Crypto, MLS, CRDT, Mesh) | AGPLv3 | Gov, Bank, Public |
| `terachat-license-guard` | BSL | Không public |
| `terachat-ui` (Tauri, Flutter) | Apache 2.0 | Public |

---

## Constraints & Open Items

### Platform Hard Constraints

| Platform | Ràng buộc | Giải pháp |
|---|---|---|
| 📱 iOS | W^X: không WASM JIT | wasm3 + AOT .dylib trong XPC Worker |
| 📱 iOS | NSE RAM: 20MB ceiling | Ghost Push + Main App decrypt |
| 📱 iOS | AWDL tắt khi Hotspot/CarPlay | Auto-downgrade BLE Tier 3 |
| 📱 Android | FCM throttled 10/h Restricted battery | FCM high-priority + Companion Device Manager |
| 📱 Huawei | Không có content-available background push | Foreground polling; CRL ≤ 4h |
| 🖥️ Linux | Flatpak không tương thích seccomp-bpf | .deb / .rpm / AppImage Cosign |
| ☁️ VPS | eBPF/XDP yêu cầu bare-metal | Tokio Token Bucket userspace |

### Blocker Items (Phải hoàn thành trước production)

| Item | Mức độ |
|---|---|
| CI/CD code signing pipeline (5 platform) | **BLOCKER** |
| WasmParity CI gate (wasm3 vs wasmtime) | **BLOCKER** |
| Dart FFI NativeFinalizer Clippy lint | **BLOCKER** |
| AppArmor / SELinux postinstall (Linux) | HIGH |
| Gossip PSK rotation runbook (90 ngày) | MEDIUM |
| PostgreSQL PITR recovery runbook | MEDIUM |
| Shamir ceremony runbook (Admin turnover) | MEDIUM |

---

## Document Navigation Map

| Audience | Document | Content |
|---|---|---|
| Developer | `Feature_Spec.md` → TERA-FEAT | IPC, OS hooks, platform behavior |
| System Architect | `Core_Spec.md` → TERA-CORE | MLS, CRDT, Mesh, server infrastructure |
| Designer | `Design.md` → TERA-DESIGN | UI state machine, Glassmorphism, animations |
| Ecosystem Builder | `Web_Marketplace.md` → TERA-MKT | .tapp lifecycle, WASM, Marketplace |
| Investor / Executive | `BusinessPlan.md` → TERA-BIZ | GTM, pricing, licensing |
| New Team Member | `Introduction.md` → TERA-INTRO | Vision, architecture overview, terminology |

---

*TeraChat — Hệ điều hành Công việc Sinh tồn. Trao lại chủ quyền số cho người tiên phong.*

---

```yaml
# CHANGELOG
- version: "3.0"
  date: "2026-03-19"
  changes:
    - "Complete rewrite from CEO/CTO perspective — removed low-level technical noise"
    - "Synthesized from Core_Spec.md, Design.md, Web_Marketplace.md, BusinessPlan.md, Introduction.md"
    - "Added Module 3 (Survival Mesh), Module 4 (AI Shield), Module 5 (.tapp) as standalone sections"
    - "Added TCO Reference, Performance Targets, Platform Constraints tables"
    - "Standardized platform icons and Online/Mesh mode indicators throughout"
    - "Full Licensing Tiers table (Community / Enterprise / GovMilitary)"
    - "Consolidated Recovery flows into Module 6; removed duplicate content"
```
