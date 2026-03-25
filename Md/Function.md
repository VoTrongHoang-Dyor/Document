# Function.md — TeraChat Function & Capability Blueprint

```yaml
# DOCUMENT IDENTITY
id:       "TERA-FUNC"
title:    "TeraChat — Enterprise Function & Capability Blueprint"
version:  "1.1.0"
status:   "ACTIVE"
date:     "2026-03-25"
audience: "Product Manager, Enterprise Sales, Solution Architect, C-Suite, Investor"
purpose:  "Mô tả toàn bộ năng lực chức năng của TeraChat từ góc độ doanh nghiệp:
           access model, modules, enterprise controls, và giá trị kinh doanh."

ai_routing_hint: |
  "Mở file này khi hỏi về TeraChat làm được gì, role-based permissions,
   enterprise business flows, AI integration, federation, hay .tapp ecosystem."
```

---

> *"Trong thế giới mà dữ liệu là quyền lực, ai kiểm soát khóa mã hóa — kẻ đó làm chủ cuộc chơi. TeraChat trao lại chìa khóa đó về tay doanh nghiệp."*

---

## Mô hình Truy cập Doanh nghiệp

**TeraChat không có tài khoản cá nhân.** Mọi người dùng thuộc về một tổ chức có license. Không thể đăng ký, không thể tự cài và dùng độc lập — đây là thuộc tính thiết kế, không phải hạn chế kỹ thuật.

> Chi tiết đầy đủ về License-Gated Architecture và phân tầng tổ chức: xem **Introduction.md §2**.

---

## Module 1 — Lõi Mật mã & Quản lý Khóa

> **Technical Spec:** Core_Spec.md §5 (Crypto), §5.1 (HKMS), §5.3 (MLS) · Feature_Spec.md §F-01

### 1.1 Hệ thống Quản lý Khóa Phân tầng (HKMS)

```
[Master Key] — HSM FIPS 140-3 / Secure Enclave / TPM 2.0
      └──► [Company_Key] — mã hóa toàn bộ dữ liệu workspace
                 ├──► [Epoch_Key]   — khóa phiên MLS, ZeroizeOnDrop khi rotation
                 ├──► [Push_Key]    — chuỗi HKDF một chiều, cô lập khỏi TreeKEM
                 └──► [Escrow_Key]  — Shamir SSS M-of-N, RAM < 100ms
```

**Shamir Secret Sharing (3-of-5)**: Enterprise_Escrow_Key chia thành 5 mảnh cho C-Level. Cần đúng 3 mảnh để tái tạo — không một cá nhân nào có đủ quyền.

**ZeroizeOnDrop**: Mọi struct chứa plaintext tự xóa bộ nhớ (ghi đè 0x00) khi hết scope. Kiểm tra bởi Miri trong CI pipeline — vi phạm là CI blocker.

**Dead Man Switch**: Bộ đếm monotonic TPM 2.0 giới hạn offline TTL theo tier. Session đóng băng khi vượt TTL; tự phục hồi khi reconnect và xác thực.

### 1.2 Mã hóa Nhóm MLS RFC 9420

- Hỗ trợ tới **10,000 thành viên** trong một nhóm E2EE
- TreeKEM: phân phối khóa O(log n) — hiệu quả ngay cả nhóm lớn nhất
- Epoch Rotation: kích hoạt khi member rời, Admin yêu cầu, hoặc lịch 24h
- Post-Quantum Hybrid (ML-KEM-768 + X25519): tuân thủ CNSA 2.0 / NIST FIPS 203

### 1.3 Bảo vệ Khóa bằng Phần cứng

| Platform | Lưu trữ Khóa | Cổng Xác thực |
|---------|-------------|--------------|
| iOS / macOS | Secure Enclave Processor | Face ID / Touch ID |
| Android | StrongBox Keymaster HAL | BiometricPrompt |
| Huawei | TrustZone TEE via HMS | HMS Biometric |
| Windows | TPM 2.0 — CNG Platform Provider | Windows Hello |
| Linux | TPM 2.0 — tpm2-pkcs11 | PIN bắt buộc |
| Bare-metal | HSM FIPS 140-3 (PKCS#11) | Physical presence + Shamir quorum |

---

## Module 2 — Nhắn tin, Cộng tác & Thoại/Video

> **Technical Spec:** Core_Spec.md §7 (CRDT), §8 (Messaging) · Feature_Spec.md §F-01, §F-06, §F-09

### 2.1 Engine Nhắn tin

- E2EE đa phương thức: văn bản, file, thoại, video — encrypt/decrypt tại thiết bị
- CRDT DAG: đảm bảo nhất quán không cần server coordination
- Hybrid Logical Clock: sắp xếp toàn phần trên distributed system
- Full-text Search zero-knowledge: SQLite FTS5 local — server không thấy query
- Message TTL: Crypto-Shredding tự động khi hết hạn

### 2.2 Thoại & Video (WebRTC)

- HD Voice & Video qua DTLS-SRTP E2EE
- ICE Pool Pre-warming: kết nối sẵn trước khi user bấm "Gọi"
- TURN HA failover < 3s (Keepalived Floating IP)
- iOS CallKit: Dead Man Switch không interrupt active call — lockout defer đến khi call kết thúc
- Signal: `DeadManDeferralEntry` được log với call_id + TPM counter delta

### 2.3 Tài liệu & Smart Approval

- Smart Document với RBAC: Viewer → Commenter → Editor
- Smart Approval Workflow: ký số với sinh trắc học (Ed25519, pháp lý hợp lệ tại VN)
- Conflict Resolution: không bao giờ silent LWW với `content_type = CONTRACT | POLICY | APPROVAL`
- TeraVault VFS: file trong chat → virtual pin, không nhân bản, preview qua Zero-Byte Stub

---

## Module 3 — Survival Mesh Network

> **Technical Spec:** Core_Spec.md §6 (Mesh) · Feature_Spec.md §F-05
>
> Khi Internet sụp đổ, TeraChat không suy giảm. Nó kích hoạt mạng P2P tự tổ chức, zero-trust, không cần server.

### 3.1 Mô hình Kết nối 4 Tầng

| Tầng | Transport | Throughput | Kích hoạt |
|------|-----------|-----------|----------|
| ☀️ Tier 1 Online | QUIC/gRPC/WSS | > 100 Mbps | Bình thường |
| 🌑 Tier 2 Wi-Fi Mesh | AWDL / Wi-Fi Direct | 250–500 MB/s | LAN, không Internet |
| 🌑 Tier 3 BLE Control | BLE 5.0 | ~50ms latency | Control plane |
| 🌑 Tier 4 BLE Emergency | BLE Long Range | Text-only | EMDP active |

### 3.2 Vai trò Node trong Tổ chức

| Vai trò | Platform | Lưu trữ | Trách nhiệm |
|---------|---------|---------|-------------|
| **Super Node** | Desktop/Laptop (AC) | 500MB–1GB / 48–72h | Backbone, DAG merge dictator |
| **Relay Node** | Android (RAM ≥ 3GB) | 100MB / 24h | Intermediate relay |
| **Tactical Relay (EMDP)** | iOS (emergency only) | 1MB / 60 phút | Text-only CRDT buffer |
| **Leaf Node** | iOS (permanent) | 50MB receive-only | Nhận tin, không định tuyến |
| **Border Node** | Bất kỳ (Internet + BLE) | N/A | Bridge TCP/IP ↔ BLE |

> **Quy tắc bất biến kiến trúc**: `iOS election_weight = 0` — iOS không bao giờ là Merge Dictator.

### 3.3 Emergency Mobile Dictator Protocol (EMDP)

Kích hoạt khi: không có Desktop + không Internet + ≥ 2 iOS + battery > 20%.

- Text-only Store-and-Forward; không merge DAG, không MLS Epoch rotation
- Key Escrow: Desktop export session key sang iOS qua ECIES trước khi offline
- TTL 60 phút; auto-handover ở phút 50
- Khi Desktop reconnect: escrow decrypt → DAG merge → epoch reconcile

---

## Module 4 — AI Privacy Shield

> **Technical Spec:** Core_Spec.md §3.3 (Memory), §4.4 (Component Isolation) · Feature_Spec.md §F-10, §INFRA-07, §INFRA-08
>
> AI worker không bao giờ truy cập database tin nhắn trực tiếp. PII luôn được redact trước bất kỳ cuộc gọi nào ra ngoài thiết bị.

### 4.1 Pipeline AI Cô lập

```
User Prompt
    ↓ (bắt buộc qua)
Micro-NER PII Detection (ONNX < 1MB, on-device)
    → Phát hiện: Tên, SĐT, Email, CMND, Tài khoản ngân hàng, Địa chỉ
    ↓
SanitizedPrompt (newtype — không thể tạo nếu không qua redaction)
    ↓
SessionVault {[MASK_01] → real@email.com} — ZeroizeOnDrop < 100ms
    ↓
AI Worker Process (cô lập OS — crash không ảnh hưởng Rust Core)
    → On-device SLM (CoreML/ONNX) hoặc VPS Enclave (nếu configured)
    ↓
Response Vec<ASTNode> (raw HTML/Markdown bị reject bởi AST Sanitizer)
    ↓
SessionVault.restore_and_drop() — alias map zeroized
```

### 4.2 AI Runtime Theo Platform

| Platform | Runtime | Ghi chú |
|---------|---------|--------|
| iOS | CoreML | Không dynamic WASM AI (W^X constraint) |
| Android | ONNX Runtime | HiAI fallback trên Huawei |
| Huawei | HiAI / ONNX | AOT bundle only |
| macOS | CoreML / ONNX | Isolated XPC Worker process |
| Windows/Linux | ONNX Runtime | CPU; GPU optional |

### 4.3 Mức Kiểm soát AI (IT Admin Configured)

| Tier | AI Shield | Egress | Audit |
|------|----------|--------|-------|
| **Strict** | Vĩnh viễn BẬT | 0 | N/A |
| **Role-Based** | C-Level / chỉ định có thể tắt | 4KB hard | Ed25519 signed |
| **DLP** | Tắt cho phép; hard block vẫn active | 4KB max | Bắt buộc |

---

## Module 5 — Enterprise Plugin Ecosystem (.tapp)

> **Technical Spec:** Core_Spec.md §4.1 (Sandbox), §4.4 (Fault Isolation) · Feature_Spec.md §F-07, §F-08

### 5.1 Mô hình Quản trị

Không có end user self-service. Toàn bộ plugin lifecycle qua IT Admin:

```
Registry → IT Admin Review → IT Admin Approve → Deploy to Workspace
```

### 5.2 Sandbox Constraints

- RAM: ≤ 64MB softcap; OOM-kill không cảnh báo
- CPU: ≤ 10% sustained; spike ≤ 500ms
- Egress: 4KB/call hard limit; 512KB/session cumulative
- Network: HTTPS/WSS đến declared endpoints only; raw TCP/UDP: forbidden
- Storage: sled KV namespace per-DID; AES-256-GCM encrypted

### 5.3 Mesh Mode — Plugin Suspension

Khi Mesh Mode active, tất cả .tapp terminate ngay lập tức. CPU/RAM reserved cho BLE routing. State snapshot về sled trước khi terminate — restore < 50ms khi Internet trở lại.

---

## Module 6 — Identity, RBAC & Enterprise Controls

> **Technical Spec:** Core_Spec.md §5.1 (Identity), §5.2 (Key Hierarchy) · Feature_Spec.md §F-11, §F-12, §F-13

### 6.1 Role-Based Access Control

| Vai trò | Năng lực | Ràng buộc |
|---------|---------|----------|
| **CISO / Admin** | Toàn quyền: KMS, policy, revocation, federation | HSM quorum cho policy changes |
| **HR Recovery Officer** | Device re-provisioning, identity recovery | Không đọc được nội dung tin nhắn |
| **Editor** | Tạo/sửa tài liệu, biometric approval | Không có key ceremony access |
| **Commenter** | Ghi chú shadow branch | Read + comment only |
| **Viewer** | Chỉ đọc, buffer frozen | ZeroizeOnDrop khi exit |

### 6.2 OPA Policy Engine

- Mọi hành động qua OPA Rego Policy — không bypass
- M-of-N HSM Quorum (2-of-3: CISO + CTO + Legal) để thay đổi production policy
- Policy Rollback Protection: monotonic version counter
- Local enforcement tại thiết bị: không round-trip server

### 6.3 Device Enrollment & Recovery

**Enrollment:**

1. Admin tạo enrollment token (mTLS Certificate, TTL 12–24h)
2. Thiết bị mới scan QR hoặc nhập token
3. Sinh `DeviceIdentityKey` trong hardware chip (biometric required)
4. Server xác thực và add vào workspace MLS group

**Recovery — Admin-Approved:**

1. Admin xác thực biometric trên thiết bị của mình
2. Tạo Recovery Ticket (Ed25519 signed, single-use, TTL 15 phút)
3. Thiết bị mới scan QR — Rust Core verify signature trước khi action
4. Fresh DeviceIdentityKey + re-keyed backup restore

**Recovery — BIP-39 Mnemonic:**

1. User nhập 24-word mnemonic **VÀ** biometric (cả hai bắt buộc)
2. Core derive Recovery_Key → reconstruct DeviceIdentityKey
3. Không có attempt limit — protected bởi biometric gate

### 6.4 SCIM 2.0 Auto-Offboarding

Khi HR system gửi `SCIM DELETE /Users/{id}`:

1. Core emit MLS `removedMembers` Commit cho toàn bộ devices của user
2. Remote Wipe triggered trên tất cả devices (< 30 giây)
3. Audit log entry với Ed25519 signature
4. Admin nhận notification

---

## Module 7 — Federation & Cross-Org Communication

> **Technical Spec:** Core_Spec.md §9.6 (Federation) · Feature_Spec.md §F-13

### 7.1 Kiến trúc

- Mỗi tổ chức vận hành Private Cluster độc lập với encryption boundary riêng
- Federation Bridge (Zone 2): mTLS + **Sealed Sender** — server nhận không biết người gửi
- Trust Registry: append-only, không dùng public CA
- Schema ±1 minor → read-only federation; ±1 major → `SCHEMA_INCOMPATIBLE`

**OPA Policy Distribution Exception**: Policy updates (CRL, permission changes, revocation) được sync qua federation bất kể schema compatibility — security không bị block bởi version mismatch.

### 7.2 Cross-Org Use Case

Phù hợp cho:

- Tập đoàn mẹ ↔ chi nhánh (sealed sender giữa BU)
- Đối tác chiến lược với yêu cầu data residency riêng
- Chuỗi cung ứng cần giao tiếp an toàn giữa các tổ chức

---

## Module 8 — Compliance, DLP & Audit

> **Technical Spec:** Core_Spec.md §12.4 (Compliance) · Feature_Spec.md §F-11, §F-13

### 8.1 Data Loss Prevention

- OPA Egress Whitelist: outbound đến domain không khai báo → blocked tại OS
- Byte-Quota Circuit Breaker: 4KB/call; 100% session quota → Egress lock 24h + CISO alert
- Format Whitelist: [.pdf, .txt, .jpg, .png, .docx, ...]; `.vbs`, `.xlsm` blocked
- AI Redaction: Rust Core local ML redact PII khỏi AI prompt trước khi gửi

### 8.2 Tamper-Proof Audit Log

- Mọi entry mang chữ ký Ed25519 — entry không ký bị reject khi ghi
- Merkle Chain: xóa bất kỳ entry → phá vỡ chain, audit độc lập phát hiện ngay
- Retention: configurable per tier (Enterprise: 90 ngày min; Gov: 7 năm)

### 8.3 Incident Response

- **Conversation Sealing (SSA)**: phát hiện social engineering → session read-only + hazard overlay; CISO approve để release
- **Plugin Emergency Kill**: TeraChat có thể push kill directive cho compromised .tapp trong < 60s

---

## Module 9 — Infrastructure & Deployment

> **Technical Spec:** Core_Spec.md §9 (Infrastructure) · Feature_Spec.md §INFRA-01–09

### 9.1 Deployment Tiers

| Tier | Users | VPS Spec | Setup Time | Phù hợp |
|------|-------|---------|-----------|----------|
| Business | ≤ 100 | 1 vCPU, 512MB RAM | 5 phút | SME, startup |
| Enterprise | ≤ 500 | 2 vCPU, 2GB RAM | 10 phút | Mid-size |
| Enterprise+ | ≤ 1,000 | 4 vCPU, 8GB RAM | 20 phút | Large org |
| Gov/Military | Custom | Existing hardware | 1–4 giờ | Government, defense |

Single Rust binary. Không cluster coordination. Không Kubernetes.

> **Lưu ý:** PostgreSQL chỉ dùng cho relay-side (server) khi triển khai Enterprise+ và Gov/Military. Client-side hoàn toàn sử dụng SQLite encrypted.

### 9.2 Performance Targets

| Operation | Target | Platform |
|-----------|--------|---------|
| E2EE encrypt/decrypt message | < 10ms | All |
| ALPN negotiation full | < 50ms | All |
| Push notification decrypt (NSE) | < 500ms | iOS |
| TURN failover | < 3s | WebRTC |
| License feature restore sau renewal | < 5s | All |
| Remote Wipe execution | < 30s | All |
| SCIM offboarding | < 30s | All |

---

## Licensing & Service Tiers

| Feature | Business | Enterprise | Enterprise+ | Gov/Military |
|---------|----------|------------|-------------|-------------|
| Offline Mesh TTL | 7 ngày | 7 ngày | 30 ngày | 30 ngày |
| EMDP Tactical Relay | ✓ | ✓ | ✓ | ✓ |
| Air-Gapped License | — | — | ✓ | ✓ |
| Compliance Retention | — | 90 ngày | 1 năm | 7 năm |
| Chaos Engineering Cert | — | — | Optional | **Bắt buộc** |
| Intel SGX / TEE | — | — | — | Available |
| Federation mTLS | — | — | ✓ | Air-gapped option |
| AI Token Quota | 50K/tháng/workspace | Unlimited | Unlimited | Unlimited + local-only |

> **Giá chi tiết:** Xem `Pricing_Packages.html` — single source of truth cho enterprise pricing.

**Open-Core Boundary:**

| Component | License | Auditable |
|-----------|---------|----------|
| `terachat-core` (Crypto, MLS, CRDT, Mesh) | AGPLv3 | Gov, Bank, Public |
| `terachat-license-guard` | BSL | Không public |
| `terachat-ui` (Flutter, Tauri) | Apache 2.0 | Public |

---

## Platform Hard Constraints

| Platform | Constraint | Solution |
|---------|------------|---------|
| iOS | W^X: không WASM JIT | wasm3 interpreter |
| iOS | NSE RAM: 20MB ceiling | Ghost Push + Main App decrypt |
| iOS | AWDL tắt khi Hotspot/CarPlay | Auto-downgrade BLE Tier 3 |
| Android | FCM throttle Restricted battery | FCM high-priority + CDM |
| Huawei | Không content-available push | Polling + HMS Data Message |
| Linux | Flatpak incompatible seccomp-bpf | .deb / .rpm / AppImage Cosign |

---

*TeraChat — Hệ điều hành Công việc Chủ quyền. Trao lại chủ quyền số cho người tiên phong.*

*TERA-FUNC v1.1.0 · 2026-03-25*
