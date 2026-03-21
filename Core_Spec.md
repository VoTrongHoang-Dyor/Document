# Core_Spec.md — TeraChat Alpha v0.3.0

```yaml
# DOCUMENT IDENTITY
id:                   "TERA-CORE"
title:                "TeraChat — Core Technical Specification"
version:              "3.0"
audience:             "System Architect, Backend Engineer, Security Engineer"
purpose:              "Đặc tả kiến trúc lõi hệ thống: Cryptography (MLS, E2EE), Mesh Network, Offline CRDT Sync, Server Infrastructure."
scope:                "Infrastructure, Security, Cryptography, Network Protocols — Implementation-level only."
non_goals:
  - "UI rendering logic (→ TERA-DESIGN)"
  - "Client-side IPC bridges (→ TERA-FEAT)"
  - "User-facing flows và RBAC (→ TERA-FUNC)"
  - "Plugin marketplace rules (→ TERA-MKT)"
assumptions:
  - "Mọi thiết bị iOS chạy wasm3 interpreter (không có JIT)"
  - "Android/Desktop chạy wasmtime JIT (Cranelift)"
  - "Mobile UI là Flutter Dart FFI; Desktop là Tauri"
  - "Mọi crypto đi qua ring crate hoặc RustCrypto — không self-implement"
constraints_global:
  - "ZeroizeOnDrop bắt buộc cho mọi struct giữ key material"
  - "Không mlock() trên iOS — dùng kCFAllocatorMallocZone + ZeroizeOnDrop"
  - "Mọi FFI endpoint KHÔNG trả raw ptr — dùng Token Protocol"
  - "Ed25519 signed, append-only Audit Log — không thể delete/modify"
breaking_changes_policy: |
  Major version bump bắt buộc khi thay đổi: MLS epoch format, CRDT schema,
  Crypto Host ABI, Host Function API. Minor version = additive only.
  Deprecation window: 12 tháng. Xem §11 Versioning & Migration.

ai_routing_hint: |
  Mở file này khi hỏi về Crypto, bảo mật, MLS, E2EE, Mesh network,
  CRDT sync, server infra, key management, hoặc attack surface analysis.
```

> **Status:** `ACTIVE — Implementation Reference`
> **Audience:** Backend Engineer · DevOps · Security / Cryptography Engineer
> **Last Updated:** 2026-03-15
> **Depends On:** *(root spec — no external deps)*
> **Consumed By:** → TERA-FEAT · → TERA-DESIGN · → TERA-MKT

---

## CHANGELOG

| Version | Date       | Change Summary                                                                                    |
|---------|------------|---------------------------------------------------------------------------------------------------|
| v3.0    | 2026-03-15 | Restructure toàn bộ sang production-grade format; thêm §1 Executive Summary, §5 State Machine, §8 NFR, §11 Versioning, §12 Observability |
| v0.3.6  | 2026-03-13 | Deprecate eBPF/XDP, Hardware TEE (SGX/SEV), mlock() Pinning, Envoy Sidecar                       |
| v0.3.5  | 2026-03-13 | Add §3.5 Lightweight Micro-Core Relay; §4.6 Soft-Enclave WASM Isolation; §3.4.2 SQLite OOM Prevention |
| v0.3.0  | 2026-03-11 | Remove ODES/Blind Shard → E2EE Cloud Backup (§9.1); §5.9 simplified → Gossip Broadcast + iBeacon |
| v0.2.9  | 2026-03-05 | Add §5.35 Hierarchical Crypto-Shredding; §5.36 SSA Retroactive Taint                             |
| v0.2.8  | 2026-03-04 | Add §9.2 Constant-time Memory Access; §5.24 EMIP Plugin Integrity; §6.13 TeraVault VFS           |

---

## CONTRACT: Implementation Requirements

> **Đọc toàn bộ §3 Data Model trước khi implement bất kỳ thứ gì.**
> Vi phạm bất kỳ ràng buộc dưới đây là **blocker — không merge**.

- [ ] Mọi Private Key **phải** nằm trong Secure Enclave (iOS/macOS) / StrongBox (Android) / TPM 2.0 (Desktop). Không lưu key trên disk dưới dạng plaintext.
- [ ] Mọi ephemeral plaintext buffer **phải** dùng `ZeroizeOnDrop` (RAII). Không để plaintext tồn tại sau khi scope kết thúc.
- [ ] Mọi network I/O giữa client–server **phải** qua TLS 1.3 + mTLS. Không có channel không mã hóa.
- [ ] Mọi thay đổi schema DB **phải** backward-compatible với WAL replay. Migration script bắt buộc.
- [ ] Mọi cryptographic operation **phải** dùng thư viện `ring` hoặc `RustCrypto` — không implement crypto tự làm.
- [ ] Mọi operation ghi vào Audit Log **phải** ký `Ed25519` trước khi persist. Log unsigned = bị từ chối.
- [ ] Mọi FFI endpoint **phải** dùng Token Protocol (`tera_buf_acquire` / `tera_buf_release`) — không trả raw pointer.
- [ ] WASM sandbox **phải** strip `wasi-sockets` — không cho phép `.tapp` tự mở raw TCP/UDP.

---

## §1 EXECUTIVE SUMMARY

### 1.1 Mục tiêu hệ thống

TeraChat là nền tảng nhắn tin doanh nghiệp **Zero-Knowledge, End-to-End Encrypted** với khả năng sinh tồn offline. Lõi hệ thống (Rust Core) nắm giữ toàn bộ mật mã học, state sync và mesh networking — UI chỉ là pure renderer.

**3 đảm bảo cốt lõi:**

1. Server không thể đọc nội dung — *ciphertext-only relay*.
2. Mesh P2P duy trì liên lạc khi mất Internet hoàn toàn.
3. Mọi key material tự hủy ngay khi scope kết thúc — *ZeroizeOnDrop everywhere*.

### 1.2 Tính năng chiến lược

| Feature | Mô tả | Section |
|---------|-------|---------|
| MLS E2EE (RFC 9420) | TreeKEM O(log n) cho 5000+ users, Forward Secrecy tự động | §4.2 |
| Survival Mesh | BLE 5.0 + Wi-Fi Direct P2P, Store-and-Forward CRDT | §5.2 |
| Zero-Knowledge Server | Blind Relay, Sealed Sender, Oblivious CAS Routing | §2.2 |
| WASM Sandbox (.tapp) | Capability-based isolation, Crypto Host ABI offloading | §5.18 |
| Hybrid PQ-KEM | X25519 + ML-KEM-768, CNSA 2.0 compliant | §4.4 |
| HKMS Key Hierarchy | HSM FIPS 140-3 → KEK → DEK, Shamir 3-of-5 recovery | §4.1 |

### 1.3 Kiến trúc tổng quan

```text
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENT DEVICE                             │
│  ┌──────────────┐  IPC/FFI   ┌─────────────────────────────────┐│
│  │  UI Layer    │◄──────────►│         RUST CORE               ││
│  │ (Flutter /   │ Control    │  ┌───────────────────────────┐  ││
│  │  Tauri)      │ Plane only │  │  MLS E2EE · CRDT · Mesh   │  ││
│  └──────────────┘            │  │  Key Mgmt · OPA · DAG     │  ││
│                              │  └───────────────────────────┘  ││
│  ┌──────────────┐            │         ▲              ▲        ││
│  │ WASM Sandbox │ Host Fn    │  Secure Enclave  SQLite WAL     ││
│  │  (.tapp)     │◄──────────►│  StrongBox/TPM  hot_dag.db     ││
│  └──────────────┘ Crypto ABI │  (Key Material) (CRDT Events)  ││
└──────────────────────────────┴─────────────────────────────────┘
          │ TLS 1.3 + mTLS                  │ BLE/Wi-Fi Direct
          ▼                                 ▼
┌─────────────────────┐          ┌─────────────────────┐
│   BLIND RELAY VPS   │          │    PEER DEVICES      │
│  (Ciphertext only)  │          │  (Survival Mesh P2P) │
│  PostgreSQL · Redis │          │  Store-and-Forward   │
│  MinIO CAS · NATS   │          │  CRDT Gossip         │
└─────────────────────┘          └─────────────────────┘
```

### 1.4 Trust Boundaries

| Boundary | Bên trong tin tưởng | Bên ngoài không tin tưởng |
|----------|---------------------|---------------------------|
| Secure Enclave / StrongBox / TPM | Private key ops | RAM, OS, Admin |
| Rust Core | Crypto logic, State | UI layer, WASM sandbox |
| WASM Sandbox | .tapp business logic | Host network, filesystem |
| Blind Relay VPS | Routing ciphertext | Plaintext content |
| Mesh Peer | Relaying signed packets | Unsigned/unverified data |

---

## §2 SYSTEM OVERVIEW

### 2.1 Shared Core Philosophy — Lõi Rust Độc Tài

- ☁️📱💻🖥️ **Lõi Rust (TeraChat Core)** nắm giữ 100% sinh mệnh: MLS E2EE, SQLCipher I/O, P2P Mesh, CRDT Sync. Biên dịch ra native binary cho mọi platform.
- 📱💻🖥️ **Tầng UI (Flutter / Tauri):** Pure Renderer — cấm tuyệt đối port Crypto/Business Logic lên Dart/JS Thread.
- 📱💻🖥️ **IPC — Tách Control/Data Plane:**
  - *Control Plane:* Protobuf qua FFI/JSI — lệnh nhỏ <1KB.
  - *Data Plane:* Dart FFI TypedData (Mobile) / `SharedArrayBuffer` (Desktop) — Zero-Copy, throughput ~400–500MB/s.
- 📱💻🖥️ **Unidirectional State Sync:** Rust bắn signal `StateChanged(table, version)` qua IPC. UI kéo snapshot tại thời điểm rảnh — không polling, không push JSON cục.

### 2.2 Blind Routing & Zero-Knowledge

- ☁️ Server là **Blind Relay** — chỉ thấy: `destination_device_id`, `blob_size`, `timestamp`.
- ☁️ **Sealed Sender:** Header người gửi mã hóa bằng public key người nhận — Server không biết who-to-whom.
- ☁️ **Oblivious CAS Routing:** Batch 4–10 `Fake_CAS_Hashes` khi gửi hash query (Chaffing). Tra qua Mixnet Proxy Endpoint, không đính `User_ID`.
- 🗄️☁️ **MinIO Blind Storage:** Lưu file theo `cas_hash` path — không biết tên file thực.
- ☁️ **VPS Zero-Knowledge Binary Block Routing:** Chunks mã hóa được đẩy lên VPS. VPS hoàn toàn mù về nội dung file lẫn Policy_Packet, chỉ lưu trữ dưới dạng binary blocks vô nghĩa.

### 2.3 Deployment Topologies

```text
[Global Edge / GeoDNS Routing]
         │
         ├──> [Zone 1: Enterprise Relay Cluster — Dedicated VPS]
         │      ├─ Double-O-Relay (Rust Control Plane)
         │      ├─ SQLite WAL Storage (Local SSD)
         │      └─ PostgreSQL (Metadata only)
         ├──> [Zone 2: Federation Bridge]
         │      ├─ mTLS Mutual Auth (không dùng CA công cộng)
         │      ├─ Sealed Sender Protocol
         │      └─ Cluster A ↔ Cluster B giao tiếp an toàn
         └──> [Zone 1B: VPS Cluster — Vultr / DigitalOcean / Linode]
                ├─ Single-Binary Rust Daemon (Relay)
                ├─ Local SSD Storage
                └─ HA TURN Array (WebRTC Relay, Floating IP)
```

| Quy mô    | Topology                                     | Storage                                      |
|-----------|----------------------------------------------|----------------------------------------------|
| 10k Users | Single-Node Rust Relay (Small VPS)           | Local SSD                                    |
| 100k Users| Geo-Federated Clusters (Dedicated VPS)       | PostgreSQL Geo-Partitioning + HA TURN Array  |
| 1M+ Users | Multi-Cloud Active-Active (Federation Bridge)| Data Mule + NTN Satellite routing            |

### 2.4 Dynamic Micro-Core Loading (Platform-Aware)

- 📱💻 Dynamic Library Loading (DLL/dylib) điều phối nạp/rút các phân hệ theo ngữ cảnh.
- 📱💻 JIT Micro-Core nhằm ép dung lượng RAM thường trực xuống mức tối thiểu.
- 📱💻🖥️ Kyber768 Post-Quantum engine cho kỷ nguyên Shor Algorithm (xem §4.4).

---

## §3 DATA MODEL

> **Catalog đầy đủ mọi đối tượng dữ liệu trong hệ thống.** Các algorithm (§4–§5) chỉ là *operations* tác động lên những objects này. Định nghĩa ở đây là nguồn sự thật duy nhất — các section khác phải reference về đây.

### 3.1 Domain: Cryptographic Identity

| Object | Type | Storage | Lifecycle | Security Constraint | Ref |
|--------|------|---------|-----------|--------------------|----|
| `DeviceIdentityKey` | Ed25519 Key Pair | Secure Enclave / StrongBox | Permanent (hardware-bound) | Không export. Ký/derive only. | §4.3 |
| `Company_Key` | AES-256-GCM Root Key | HKMS (wrapped by DeviceKey) | Per-workspace, rotated on member exit | Không rời thiết bị thành viên | §4.1 |
| `Epoch_Key` | MLS Leaf Key | RAM (Userspace) | Per MLS Epoch, zeroized on rotation | ZeroizeOnDrop mandatory | §4.2 |
| `ChunkKey` | AES-256-GCM Ephemeral | Rust `ZeroizeOnDrop` struct | 1 chunk (~2MB) lifetime | Zeroized immediately after use | §5.18 |
| `Session_Key` | ECDH Curve25519 Derived | RAM (Userspace) | Per session, zeroized after disconnect | ZeroizeOnDrop mandatory | §5.10.2 |
| `Push_Key` | AES-256-GCM Symmetric | Shared Keychain (iOS) / StrongBox (Android) | Per push_epoch, OOB from MLS | Versioned: push_key_version (u32) | §4.2 |
| `Master_Unlock_Key` | KDF output | RAM only (<100ms) | Duration of license validation op | ZeroizeOnDrop; never persisted | §13.3 |

### 3.2 Domain: MLS Session Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Ref |
|--------|------|---------|-----------|--------------------|----|
| `KeyPackage` | MLS RFC 9420 Struct | Server (public) / Local DB | Refreshed periodically | Public info only | §4.2 |
| `Welcome_Packet` | ECIES-encrypted payload | Encrypted in-flight | Single use, consumed on join | ECIES Curve25519, receiver-keyed | §5.10.2 |
| `TreeKEM_Update_Path` | MLS tree delta | In-memory, broadcast | Per epoch rotation | Ed25519 signed | §5.14, §5.15 |
| `Epoch_Ratchet` | Sequence counter | `hot_dag.db` | Monotonically increasing | Tamper-evident via append-only log | §4.2 |
| `Enterprise_Escrow_Key` | Shamir-split AES-256 | M-of-N hardware tokens | Per KMS bootstrap | 3-of-5 Shamir; no single holder | §4.2 |

### 3.3 Domain: Mesh Network Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Ref |
|--------|------|---------|-----------|--------------------|----|
| `BLE_Stealth_Beacon` | 31-byte BLE Adv PDU | Broadcast-only (air) | Ephemeral per scan cycle | HMAC-wrapped; no static identifiers | §5.9.3 |
| `Identity_Commitment` | `HMAC(R, PK_identity)[0:8]` | Embedded in Beacon | Per session nonce | R rotated every 5min | §5.9.3 |
| `Shun_Record` | `{Node_ID, Ed25519_Sig, HLC}` | `hot_dag.db` broadcast | Until node is rehabilitated | Enterprise CA signed | §5.10 |
| `MergeCandidate` | `{Node_ID, BLAKE3_Hash, HLC}` | RAM only | Duration of Split-brain resolution | Ephemeral; no persist | §5.12, §5.16 |
| `Hash_Frontier` | `{Vector_Clock, Root_Hash}` | `hot_dag.db` | Updated on every Gossip round | BLAKE3 integrity | §5.15 |
| `EmdpKeyEscrow` | AES-256 session key | BLE Control Plane (in-flight) | EMDP session (max 60min) | ECIES-encrypted to relay device pubkey | §12.2 |

### 3.4 Domain: DAG State Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Ref |
|--------|------|---------|-----------|--------------------|----|
| `CRDT_Event` | Typed append-only log entry | `hot_dag.db` (WAL) | Permanent (Append-Only) | Ed25519 signed per event | §5.10.1 |
| `HLC_Timestamp` | `{wall_clock, logical_counter}` | Embedded in every Event | Attached to event, immutable | No SystemTime::now() — use HLC | §5.14 |
| `Tombstone_Stub` | `{entity_id, hlc, type=DELETED}` | `cold_state.db` | Permanent (never physically deleted) | Replay-attack protection | §5.10.1, §5.17 |
| `Proof_Bundle` | `{Ed25519_Sig, HLC, Evidence}` | Encrypted broadcast | Until dispute resolved | Hardware-bound non-repudiation | §5.10.3 |
| `AppendBlock` | `{id, content, timestamp, device_sig}` | RAM / `hot_dag.db` | Pending until Desktop reconcile | Ed25519 signed; Optimistic mode | §12.1 |

### 3.5 Domain: Recovery & Audit Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Ref |
|--------|------|---------|-----------|--------------------|----|
| `Snapshot_CAS` | Content-Addressable Hash | `TeraVault VFS` | Permanent | SHA-256 integrity | §5.10.2, §6.13 |
| `Hydration_Checkpoint` | `{Snapshot_CAS_UUID, last_chunk_index}` | `hot_dag.db` | Overwritten on each successful chunk | Atomic pre-write before batch | §6.14.1 |
| `Monotonic_Counter` | TPM 2.0 hardware counter | TPM chip register | Hardware-bound, tamper-evident | Rollback-proof; hardware only | §4.5 |
| `Audit_Log_Entry` | `{device_id, timestamp, payload_hash, ed25519_sig}` | Append-only CRDT chain | Permanent | Ed25519 signed; cannot delete | §4.3 |
| `XpcTransactionJournal` | `{tx_id, status, payload_hash}` | `hot_dag.db` | Per XPC transaction | PENDING/VERIFIED/COMMITTED states | §14.4 |

### 3.6 Domain: License Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Ref |
|--------|------|---------|-----------|--------------------|----|
| `License_JWT` | Ed25519-signed JSON | Delivered via email/USB | Valid until `valid_until` field | HSM FIPS 140-3 signed; no export | §13.1 |
| `Feature_Flags` | Struct returned by license-guard FFI | RAM only | Duration of license check | No key material crosses FFI | §13.2 |
| `OfflineTTL_Profile` | Enum: Consumer/Enterprise/GovMilitary/AirGapped | License JWT field | Per tenant | Configurable; not hardcoded | §13.5 |

---

## §4 FEATURE MODEL

> Mỗi feature được đặc tả đầy đủ: description, platforms, dependencies, data interactions, state machine (nếu có), observability, security notes.

---

### F-01: Hardware Root of Trust & Anti-Extraction

**Description:** Private key sinh và tồn tại vĩnh viễn trong chip bảo mật vật lý. Mọi ký/giải mã thực hiện trong enclave — key không bao giờ rời chip.

**Supported Platforms:** 📱 iOS (Secure Enclave), 📱 Android (StrongBox Keymaster), 💻🖥️ Desktop (TPM 2.0), 🗄️ Server (HSM PKCS#11)

**Dependencies:** Biometric API (FaceID/TouchID/NNAPI), OS Keychain/Keystore

**Data Interaction:** Tạo → `DeviceIdentityKey`, `Company_Key` (wrapped). Consume → ký `OIDC_ID_Token`, `Audit_Log_Entry`, `License_JWT` verification.

**Key Mechanisms:**

- 📱💻🖥️ **Biometric-Bound Cryptographic Handshake:** `Device_Key` sinh với `kSecAccessControlBiometryCurrentSet`. Biometric required cho mọi signing op. `ZeroizeOnDrop` ghi đè `OIDC_ID_Token` ngay khi lỗi phần cứng.
- 📱💻🖥️ **Enterprise PIN Độc lập & Dual-Wrapped KEK:** Argon2id (0.5s CPU) sinh `Fallback_KEK`. Device_Key bọc 2 bản độc lập: Bản 1 qua Secure Enclave/StrongBox; Bản 2 qua `Fallback_KEK`. `Drop()` + Zeroize xóa PIN và KEK khỏi RAM ngay sau wrap.
- 📱💻🖥️ **Cryptographic PIN Fallback via FFI Pointer:** PIN 6 số truyền từ UI qua FFI Pointer (không qua UI state). Tái tạo `Fallback_KEK` → giải mã Bản bọc 2 → extract `Device_Key` → ký `OIDC_ID_Token` → `ZeroizeOnDrop` PIN thô.
- 📱💻🖥️ **Ruthless Cryptographic Self-Destruct:** Counter `Failed_PIN_Attempts` (max 5). Vượt giới hạn → Crypto-Shredding toàn bộ Local DB + `OIDC_ID_Token` + 2 bản bọc `Device_Key` → Factory Reset.

**Platform Signing APIs:**

| Platform | API | Mechanism |
|----------|-----|-----------|
| 📱 iOS | `LAContext` | `SecKeyCreateSignature` + `.biometryCurrentSet` |
| 📱 Android | `BiometricPrompt` | `setUserAuthenticationRequired(true)` + Hardware Keystore |
| 💻 macOS | `CryptoTokenKit` | `kSecAttrTokenIDSecureEnclave` |
| 💻🖥️ Windows | `CNG` | `Microsoft Platform Crypto Provider (TPM 2.0)` + `NCryptSignHash` |
| 🗄️ Gov-Grade | PKCS#11 | SafeNet/Viettel/VNPT CA — Rust `pkcs11` crate |

**Remote Attestation:**

| Platform | API | Requirement |
|----------|-----|-------------|
| 📱 iOS | `DCAppAttestService` | App gốc, không Jailbreak |
| 📱 Android | `Play Integrity API` | `MEETS_STRONG_INTEGRITY` |
| 📱 Huawei | HMS SafetyDetect `DeviceIntegrity()` | TrustZone (ARM) |
| 💻🖥️ Windows | `TPM 2.0 Health Attestation` | PCR check + BitLocker ON |
| 💻 macOS | Notarization + Hardened Runtime | Secure Enclave |
| 🖥️ Linux | TPM 2.0 + IMA | varies |

**Security Notes:**

- ☁️ Chỉ `MEETS_BASIC_INTEGRITY` hoặc Root → từ chối + Remote Wipe.
- 📱💻🖥️ DMA Protection: IOMMU check tại startup; mới device join PCIe bus → `SecurityEvent::DMA_INTRUSION` → Crypto-Shredding `Session_Key` + lockscreen.

**Observability:**

- Signal: `SecurityEvent::HardwareAttestationFailed`, `SecurityEvent::DMA_INTRUSION`
- Audit: Mọi key signing op ghi vào `Audit_Log_Entry` (Ed25519 signed)

---

### F-02: Hierarchical Multi-Sig Escrow — Offline Device Recovery

**Description:** Phục hồi thiết bị khi server sập, không có iCloud Keychain, qua Multi-Sig quorum offline.

**Supported Platforms:** 📱💻🖥️ (client-side quorum), ☁️🗄️ (audit log)

**Dependencies:** `DeviceIdentityKey`, Shamir's Secret Sharing, BLE Physical Presence

**Data Interaction:** Tạo → `Enterprise_Escrow_Key` (sharded). Consume → `Recovery_Ticket`, triggers `Epoch_Key` rotation.

**Key Mechanisms:**

- ☁️ **Hierarchical Multi-Sig Escrow:** `Enterprise_Escrow_Key` sinh khi KMS Bootstrap, chia Shamir 3-of-5 (GF(2^256)), phân phát vào Secure Enclave của Admin/HR devices.
- 📱💻🖥️ **Threshold Cryptography (m-of-n):** Yêu cầu tối thiểu 2/3 thiết bị quản trị quét QR khôi phục qua BLE/Wi-Fi Direct.
- 🗄️ **Tamper-Proof Escrow Log:** Mọi thao tác ghép khóa khôi phục sinh ra `Ed25519 Signature` ghi Append-Only Audit Log trên server — Non-Repudiation.
- 📱 **Abuse Prevention:** BLE SOS phải ký bởi Enterprise CA. Đồng nghiệp chỉ thấy yêu cầu từ cùng OU. `user_id` chỉ phát SOS **1 lần/24h**.

**State Machine:**

```text
[Nhân viên mất thiết bị]
        │
        ▼
[Báo HR/Admin] ──BLE Physical Presence──▶ [2/3 Admin xác nhận Biometric]
        │                                         │
        ▼                                         ▼
[QR Code Recovery Ticket]            [Lagrange Interpolation in mlock arena]
        │                                         │
        ▼                                         ▼
[Thiết bị mới quét QR]              [Enterprise_Escrow_Key (RAM <100ms)]
        │                                         │
        ▼                                         ▼
[Rust verify Ed25519 Ticket]         [Wrap → new DeviceIdentityKey]
        │                                         │
        └─────────────────────────────────────────┘
                          ▼
                [Append Audit Log → Epoch Rotation]
```

**Security Notes:**

- Plaintext `Escrow_Key` chỉ tồn tại trong RAM < 100ms trong Secure Arena
- Mỗi Recovery Event ký `Ed25519(Device_Key, {event_id, shard_holder_ids, timestamp, target_message_hashes})`
- Court Order reference number bắt buộc trong field `legal_basis`

---

### F-03: Disaster Recovery Protocols

**Description:** Giao thức phục hồi phần cứng (YubiKey CTAP2) và intermittent sync cho môi trường mạng không ổn định.

**Supported Platforms:** 💻🖥️ (CTAP2), ☁️💻 (Intermittent Sync)

**Key Mechanisms:**

- 💻🗄️ **CTAP2 Hardware Challenge:** YubiKey cắm vào thiết bị mới → Rust phát Challenge nội bộ → YubiKey giải mã trong Secure Element. Bắt buộc FIDO2 UV = Required (PIN 6 số hoặc biometric trực tiếp trên YubiKey).
- ☁️💻 **Intermittent Sync Engine:** Delta-State CRDT Buffer duy trì. Khi thiết bị mới quét được mạng → broadcast "Thiết bị cũ đã bị vô hiệu hóa" + tải danh bạ Mesh local → hoạt động offline hoàn toàn.
- 💻📱 **Self-Revocation & Epoch Rotation (TH2):** Khi mất 1 thiết bị, thiết bị còn lại sinh `Epoch_Key` mới, cập nhật Merkle Tree, ký bằng `DeviceIdentityKey`. Thiết bị đã mất bị từ chối ở tầng giao thức.

---

### F-04: Key Management System (HKMS)

**Description:** Hệ thống quản lý khóa phân cấp: Master Key → KEK → DEK, với Master Key không bao giờ rời hardware enclave.

**Supported Platforms:** 📱💻🖥️☁️🗄️

**Data Interaction:** Tạo toàn bộ key hierarchy. Consume → mọi encrypt/decrypt operation.

**Key Hierarchy:**

```text
[Master Key]  — HSM / TPM / Secure Enclave (không rời chip)
      └──> [KEK]  — giải mã trong RAM, ZeroizeOnDrop protected
                └──> [DEK]  — mã hóa nội dung thực tế
                          └──> [DB / File / Channel / API Key]
```

| Device | Private Key Storage | Mechanism |
|--------|--------------------|-----------|
| 📱 iOS | Secure Enclave | Không extract. Ký/Giải mã yêu cầu biometric. |
| 📱 Android | StrongBox Keymaster (HAL) | Key sinh trong chip, không export. |
| 💻🖥️ Desktop | TPM 2.0 (NCrypt / macOS SEP) | Key binding với device. |
| 🗄️ Server | HSM Software (PKCS#11) | CA / Cluster signing key. |

**KMS Bootstrap Ritual:**

1. ☁️🗄️ Workspace khởi tạo → App sinh `terachat_master_<domain>.terakey` (Master Key bọc AES-256 bằng Argon2id từ Admin password).
2. Lõi Rust **Block** tạo Database cho đến khi Admin xác nhận lưu Key Backup.
3. Shamir 3-of-5 phân phát vào YubiKey/Smartcard của C-Level.
4. HSM Decrementing Monotonic Counter: mỗi lần issue cert → counter giảm → chống cloning.

**Dead Man Switch:**

- 📱💻🖥️ Monotonic Hardware Counter — chống Time Travel Attack.
- Mỗi unlock DB → Counter++. Server lưu "Last Valid Counter". `Counter < Server's Value` → từ chối + Self-Destruct.
- **Offline Grace:** Tối đa theo `OfflineTTLProfile` (mặc định 72h consumer, 720h GovMilitary).

**Remote Wipe:**

- 📱💻🖥️ `self.userID` trong `removedMembers` → xóa Private Key trong SE → Drop bảng chat → Quét xóa Sandbox files. Thực thi trong `autoreleasepool` (iOS) / `try-finally` (Android) — không thể bị User chặn.

**Security Notes:**

- KDF entanglement: `Master_Unlock_Key = HKDF(DeviceIdentityKey || LicenseToken || CurrentEpoch)` — xem §13.3
- Shamir Lagrange Interpolation chạy trong `mlock`-protected Secure Arena; plaintext `Escrow_Key` chỉ tồn tại <100ms

---

### F-05: Message Layer Security (MLS — IETF RFC 9420)

**Description:** TreeKEM-based E2EE cho group messaging tới 5000+ users với Forward Secrecy tự động.

**Supported Platforms:** 📱💻🖥️☁️

**Data Interaction:** Tạo → `KeyPackage`, `Welcome_Packet`, `TreeKEM_Update_Path`, `Epoch_Ratchet`. Consume → message encryption/decryption, member add/remove.

**Key Properties:**

- ☁️ **TreeKEM:** Mã hóa O(log n) cho nhóm 5000+ user.
- ☁️ **Self-Healing:** Epoch Rotation khi member rời — Forward Secrecy tự động.
- ☁️ **Sealed Sender:** Server không biết người gửi.
- ☁️ **Multi-Device Queue:** N bản copy (1/device). Device ACK → xóa bản đó. TTL 14 ngày → Crypto-Shred KEK.
- ☁️ **Enterprise Escrow KEM:** Shamir's Secret Sharing — M-of-N Recovery Key cho Supervisors. Audit Log bắt buộc (HIPAA/SOC2).

**Sender Downgrade Mode (Version Conflict Resolution):**

- 📱💻🖥️ Extension `TeraChat_App_Version` trong `KeyPackage` để đàm phán năng lực.
- 📱💻🖥️ Min-Version Roster scan → kích hoạt Serialization Downgrade Mode khi có device cũ.
- 📱 UI Feature Gray-out dựa trên version metadata — ngăn tạo payload không tương thích.

**OOB Symmetric Push Ratchet (NSE isolation):**

- 📱 `Push_Key = HKDF(Company_Key, "push-ratchet" || chat_id || push_epoch)` — hash-chain một chiều, **độc lập với MLS TreeKEM**.
- 📱 NSE chỉ đọc `Push_Key_current` từ Shared Keychain → giải mã payload O(1) RAM (<5MB) → `ZeroizeOnDrop`.
- 📱 NSE **không bao giờ** tái dựng TreeKEM. Main App chịu trách nhiệm ratchet khi Foreground.
- 📱 **Key Desync Fallback:** Key không tìm thấy → fallback text an toàn, không crash.
- 📱 **Versioned Key Ladder:** `push_key_version (u32)` trong Shared Keychain. Payload version lệch → cache raw ciphertext vào `nse_staging.db` → `content-available:1` → Main App wakeup → rotate → decrypt.

**Legal Hold & Shamir Distributed Escrow:**

- 🗄️ `Enterprise_Escrow_Key` sinh 1 lần trong KMS Bootstrap, chia thành N mảnh GF(2^256) polynomial.
- 📱💻 NFC/FIDO2 Shard Authentication: FIDO2 challenge-response; Shard chỉ decrypt tạm thời trong RAM.
- 🗄️ Lagrange Interpolation trong Secure Arena — plaintext <100ms.
- 📱💻 Ed25519 Signed Recovery Audit Trail: `{event_id, shard_holder_ids, timestamp, target_message_hashes}`.
- ☁️ Distributed Shard Storage: Mỗi holder giữ Shard riêng; server chỉ lưu encrypted Shards TTL 90 ngày.

**Observability:**

- Signal: `MlsEpochRotated(epoch_n)`, `MlsKeyDesync(chat_id)`, `MlsWelcomePacketDelivered`
- Metric: `epoch_rotation_latency_ms`, `multi_device_queue_depth`

---

### F-06: Hybrid PQ-KEM (Kyber768) — Quantum-Resistant Key Exchange

**Description:** Kết hợp X25519 (classical) + ML-KEM-768/Kyber768 (post-quantum) để chống Store-Now-Decrypt-Later (SNDL) attack.

**Supported Platforms:** 📱💻🖥️☁️🗄️

**Key Derivation:**

```
Final_Session_Key = HKDF(X25519_Shared || Kyber768_Shared)
```

Tuân thủ chuẩn CNSA 2.0 và NSA SNDL/HNDL requirements.

**Bandwidth Optimization:**

- 📱 **Quantum Checkpoints:** ML-KEM payload (~1.18KB) chỉ đính kèm vào `KeyPackage` MLS Handshake hoặc mỗi 10.000 tin nhắn. Luồng hàng ngày chạy thuần AES-256-GCM → tiết kiệm 99.9% băng thông.
- 📱💻 **Survival Mesh Fragmentation:** BLE 5.0 MTU ~512 bytes → Rust Core băm nhỏ Kyber blob 1.18KB thành mảnh 400 bytes + Sequence ID + FEC (RaptorQ RFC 6330).

**Hardware Key Wrapping:**

- 📱💻🖥️ Sinh cặp khóa PQ trên phân vùng RAM được bảo vệ bởi `MAP_CONCEAL`.
- 📱 ML-KEM Private Key bọc bằng `Hardware_Wrap_Key` trong Secure Enclave/StrongBox.
- 📱💻🖥️ `ZeroizeOnDrop` ghi đè `0x00` lên plaintext key ngay sau tính toán KEM.

**Pre-fetched PQ Roster (Offline Mesh):**

- 📱💻 `KeyPackage (X25519 + ML-KEM-768)` lưu vào SQLite WAL mode khi có Internet.
- 📱💻 Truy vấn qua `Key_Hash` (16 bytes) để kích hoạt Hybrid Handshake qua BLE.

**Lazy Quantum Ratchet:**

- 📱 X25519 Fast Handshake (<100 bytes) cho SOS — thiết lập kênh E2EE cổ điển trong 1 BLE packet.
- 📱 MLS Epoch Rotation hòa trộn ML-KEM-768 Secret vào Master Secret sau khi tải dữ liệu ngầm.

---

### F-07: Infrastructure & Control Plane

**Description:** Backend services, Gateway, OPA Policy, Database layer.

**Supported Platforms:** ☁️🗄️

#### Gateway & Identity Broker

- ☁️ **API Gateway:** Rate Limiting (Sliding Window Log — Redis ZSET), OPA Policy trên mọi request.
- ☁️ **Identity Broker (Keycloak/Dex):** OIDC/SAML bridge — Azure AD / Google Workspace / Okta / OneLogin.
- ☁️ **Enterprise CA (PKI nội bộ):** Chỉ tin tưởng key ký bởi CA nội bộ. Không CA công cộng.
- ☁️ **SCIM Listener:** Lắng nghe SCIM 2.0 events — tự động offboarding nhân viên (<30s).

#### OPA/ABAC Policy Engine

- ☁️ Mọi request đi qua **OPA (Open Policy Agent)** tại API Gateway.
- ☁️ **GeoHash Indexing:** Tọa độ → GeoHash prefix string. OPA so sánh String thay vì Haversine — O(1) lookup.
- ☁️ **Formal Verification:** OPA Policy → SMT Model → **Z3 Solver** → Block Deploy nếu có kẽ hở.
- ☁️ **ZKP-based Attribute Routing:** zk-SNARKs để OPA xác thực Policy mà không giải mã danh tính.
- ☁️📱💻🖥️ **VOPRF Token:** Blind Tokens cho Rate Limit ẩn danh.

#### Cluster 4-trong-1

| Component | Chức năng |
|-----------|-----------|
| **MLS Backbone** | Phân phối khóa & định tuyến nhóm 5000+. Zero-Knowledge Encrypted Log Streams. |
| **HA TURN Cluster** | Floating IP, failover 3s. WebRTC Relay HD/Video Conference. |
| **Execution Environment** | VPS Egress Proxy backend — dữ liệu chỉ trên RAM, không persist. |
| **Interop Hub** | Gateway E2EE hóa dữ liệu SAP/Jira/CRM trước khi đẩy xuống Client. |

#### Database Layer

**PostgreSQL HA:**

- ☁️🗄️ pgRepmgr + PgPool — Failover tự động, streaming replication.
- ☁️🗄️ Geo-Partitioning cho quy mô 100k+ user.

**MinIO Blind Storage:**

- ☁️🗄️ **Erasure Coding (EC+4):** Sharding 3–5 Nodes. 1 Node sập → tự phục hồi.
- ☁️ Lưu file theo `cas_hash` path (CAS). Server không biết tên file thực.
- ☁️ **Zero-Byte Stub:** Client nhận Stub <5KB (`file_name`, `cas_hash`, `encrypted_thumbnail`, `storage_ref`). File thực tải khi user yêu cầu.

**SQLite OOM Prevention (VPS Resource Constraints):**

- ☁️ **Micro-batching DB Lock Yielding:** Chunk ghi WAL thành các batch. Rust yield khóa DB sau mỗi 1000 hàng.
- ☁️ **Zero-Copy Atomic Rename:** `renameat2()` với `RENAME_WHITEOUT` để tráo tệp vfs-journal — giảm 90% áp lực RAM.
- ☁️ **SQLite WAL Autocheckpoint:** `wal_autocheckpoint=1000` giữ WAL file ở ngưỡng kiểm soát được.

#### Concurrency Model

- ☁️🗄️ **Asynchronous Rust + io_uring:** Loại bỏ "1 Thread / 1 Connection". Tokio + io_uring Linux kernel.
- ☁️🗄️ **Ultra-Light Connections:** ~2KB RAM/connection WebSocket. 1 VPS 4GB RAM → ~500.000 kết nối đồng thời.

---

### F-08: ALPN & Protocol Fallback State Machine

**Description:** Tự động đàm phán giao thức từ QUIC → gRPC → WebSocket → Mesh, minh bạch với người dùng và tuân thủ mọi Enterprise Firewall.

**Supported Platforms:** ☁️📱💻

**State Machine:**

```text
ALPN Protocol State Machine (Auto-negotiation, < 50ms total)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1 │ QUIC/HTTP3 over UDP:443
       │ ◉ ACK within 50ms → ONLINE_QUIC (0-RTT, ~30ms)
       │ ✗ No ACK / Firewall DROP → fallback Step 2
       ▼
Step 2 │ gRPC over HTTP/2 (TCP:443)
       │ ◉ TLS handshake OK → ONLINE_GRPC (1-RTT, ~80ms)
       │ ✗ DPI rejects binary framing → fallback Step 3
       ▼
Step 3 │ WebSocket Secure (wss:// over TCP:443)
       │ ◉ WS Upgrade OK → ONLINE_WSS (1-RTT, ~120ms)
       │ ✗ All transports fail → MESH_MODE (BLE/Wi-Fi Direct)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Key Properties:**

- ☁️📱💻 **Fast Fallback <50ms:** Parallel probe (không tuần tự). HUD QUIC Status cập nhật icon không hiện dialog.
- ☁️📱💻 **Strict Compliance Mode:** Admin kích hoạt → Client bỏ qua Step 1 hoàn toàn, kết nối thẳng gRPC TCP.
- ☁️ **Certificate Pinning (rustls):** SHA-256(SubjectPublicKeyInfo) hardcoded. Reject certificate nào không khớp SPKI hash.
- ☁️ **Socket Panic Circuit Breaker:** Phát hiện downgrade attack hoặc Handshake bị thao túng → cắt Socket 30s.
- ☁️ **Anti-Downgrade:** QUIC-Pinning State Machine trong Strict Compliance Mode chặn QUIC → WSS downgrade.

**Observability:**

- Signal: `NetworkProtocolChanged(old, new)`, `AlpnFallbackTriggered(step)`
- Metric: `protocol_latency_ms{protocol}`, `fallback_count_total`

---

### F-09: Lightweight Micro-Core Relay

**Description:** Single-binary Rust relay chạy trên VPS phổ thông, thay thế eBPF/XDP và Envoy Sidecar.

**Supported Platforms:** ☁️

**Key Properties:**

- ☁️ **Single-Binary Rust Daemon:** `opt-level='z'`, `panic='abort'`, Link-Time Optimization. Hoạt động từ 512MB RAM.
- ☁️ **Tokio Async Userspace Filter:** Token Bucket Rate-limit, chống DoS — không cần `CAP_SYS_ADMIN`.
- 📱💻☁️ **Protocol Versioning via ALPN:** QUIC/gRPC/WS đàm phán linh hoạt. Hot-reload không gián đoạn.
- ☁️ **Gossip-based Discovery (Memberlist):** Worker tìm Cluster WireGuard LAN sau Bootstrap.

**Note:** eBPF/XDP là **server-side Linux kernel technology** — không phải client-side. Client hưởng lợi từ server-side protection qua connection quality.

---

### F-10: Update Security & Binary Transparency

**Description:** Bảo vệ toàn vẹn binary update, chống downgrade attack và rogue admin injection.

**Supported Platforms:** 📱💻🖥️

**Key Mechanisms:**

- 📱💻🖥️ **Root CA Binary Transparency:** Mọi build (Native App, Rust Core, `.tapp`) ký bằng **TeraChat Root CA Key** từ hầm lạnh offline. Admin không thể tạo chữ ký này.
- 📱💻🖥️ **Ed25519 Signature Verification:** Client hard-code Public Key của TeraChat. Update từ VPS bắt buộc kiểm tra chữ ký trước khi thực thi. Sửa 1 bit → chữ ký vỡ → Drop + Báo động đỏ.
- 📱💻🖥️ **Anti-Rollback Monotonic Counter:** `Version_Sequence` trong build header. `Sequence < Current_Sequence` → Drop tức thì.
- 📱💻🖥️ **Global CVE Heartbeat via DNS TXT (DoH):** Tra cứu `security.terachat.com` mỗi 24h qua DNS-over-HTTPS (Cloudflare/Google). Ed25519 verify trước khi nạp `Version_Sequence_Blacklist`.
- 📱💻🖥️ **Atomic IPC Security Lock & RSOD:** `ATOMIC_SECURITY_LOCK` khóa toàn bộ IPC Data Plane khi CVE Blacklist match → Red Screen of Death (người dùng không thể đóng) → Zeroize RAM.

**Update Distribution:**

- 📱 **Mobile (Signal-Only):** VPS phát cờ lệnh `"V0.3.0 là bắt buộc"`. App → Khóa UI → Nút *"Đến App Store / CH Play"*. VPS không chứa `.ipa/.apk`.
- 💻🖥️ **Desktop (LAN P2P):** VPS "mồi" 10 Super Nodes. Desktop dùng Survival Mesh phân phối Binary cho phần còn lại — 99% tải VPS giải phóng.

**Distributed Binary Transparency (DBT):**

- 📱💻🖥️ `Global_Update_Log` trên Append-Only CRDT Log.
- 📱💻 Hash đồng bộ qua Gossip trên Mesh.
- 📱💻 Rust đối soát Hash của JMM với sổ cái chung trước khi nạp module.

---

### F-11: WASM Runtime & Capability-Based Sandboxing

**Description:** Runtime WASM dual-engine (wasm3/wasmtime), capability-based isolation, Crypto Host ABI offloading.

**Supported Platforms:** 📱💻🖥️

**Dual-Engine Strategy (W^X Conflict Resolution):**

> ⚠️ iOS áp đặt chính sách W^X nghiêm cấm JIT Runtime. Lõi Rust PHẢI tự động phát hiện Platform và chọn Engine phù hợp.

| Platform | WASM Engine | Rationale |
|----------|------------|-----------|
| 📱 iOS | `wasm3` pure interpreter (~10KB binary, zero JIT) | W^X compliant, App Store safe. +15-20ms latency/call — chấp nhận được |
| 📱 Huawei HarmonyOS | `wasmtime` JIT (Cranelift) | Không bị W^X như iOS |
| 📱 Android | `wasmtime` JIT (Cranelift) | W^X protection, sandbox CFI |
| 💻🖥️ Desktop/Server | `wasmtime` JIT (Cranelift) | Maximum throughput |

Switch condition: `#[cfg(target_os = "ios")]` tại compile-time.

**WASM Behavioral Parity:**

- WasmParity CI gate chạy cùng test vector trên `wasm3` (iOS) và `wasmtime` (Android).
- Fail → block merge. Latency delta ≤ 20ms chấp nhận được. **Output semantic phải identical.**
- `wasm3` = reference runtime; `wasmtime` = optimized runtime.

**Sandbox Security Properties:**

- 📱💻🖥️ Mọi engine chạy **Deny-by-Default** — không cấp `Company_Key` vào sandbox.
- 📱💻🖥️ Strip `wasi-sockets` tại compile time — không có direct network access.
- 📱💻🖥️ Blind Return + Zeroize: tiêu hủy tàn dư RAM của WASM ngay sau execution.
- 📱💻🖥️ Linear Memory Isolation: mỗi instance có vùng nhớ cô lập (max 64MB). Overflow → SIGSEGV + kill.

**AST Opcode Filtering:**

- 📱💻🖥️ `wasmparser` phân tích tĩnh, chặn opcode `f32/f64` gây bất tất định.
- 📱💻🖥️ Cưỡng ép Fixed-point arithmetic hoặc Soft-float tại compilation level.
- 💻🖥️ `cranelift_nan_canonicalization` chuẩn hóa NaN bit pattern.
- 📱💻🖥️ Vô hiệu hóa `relaxed_simd` và phần cứng SIMD để loại bỏ micro-architecture dependency.

**Crypto Host ABI (Native Crypto Offloading):**

> WASM sandbox KHÔNG tự chạy crypto. Mọi crypto op delegate về Rust Core qua host functions.

```rust
// Host function ABI — WASM calls these, Rust implements
extern "C" {
    fn host_blake3_hash(data_ptr: *const u8, data_len: usize, out_ptr: *mut u8) -> i32;
    fn host_ed25519_sign(key_id: u64, msg_ptr: *const u8, msg_len: usize, sig_out: *mut u8) -> i32;
    fn host_aes256gcm_encrypt(key_id: u64, nonce_ptr: *const u8, plaintext_ptr: *const u8, 
                               plaintext_len: usize, ciphertext_out: *mut u8) -> i32;
}
// key_id references a ZeroizeOnDrop key in Rust Core — never crosses boundary as bytes
```

**OPA-driven IPC Bridge:**

- 📱💻🖥️ IPC Protobuf qua SharedArrayBuffer là cầu nối duy nhất cho I/O.
- ☁️📱💻🖥️ OPA Engine đối chiếu quyền hạn khai báo trong Manifest với quyền User.
- 💻🖥️ Plaintext trả vào RAM của WASM — tuyệt đối không cấp File Handle gốc của OS.

**Data Diode Architecture (Company_Key leak prevention):**

```text
[Lõi Rust - Crypto Core] ──Push Masked Data──▶ [WASM Sandbox .tapp]
                                                          │
                                            (không có callback ngược)
                                                          │
                                              Write ──▶ [Egress_Outbox]
                                                          │
                               [tera_egress_daemon / OS Background Service]
                                   (Separate process, không share memory với Lõi Rust)
                                                          │
                                          OPA DLP Check + BLAKE3 Hash Verify
                                                          │
                               URLSession (iOS) / Cronet (Android) / HTTP (Desktop)
                                                          ▼
                                                    Internet / Partner API
```

**Egress_Outbox:**

- 📱💻🖥️ Write-only từ `.tapp`, Read-only từ Egress Daemon. Giới hạn cứng **2MB** — vượt → Outbox sealed + terminate.
- ☁️ **BLAKE3 DLP Hash Chain:** Lõi Rust tính `BLAKE3(masked_payload)` trước khi push. Egress Daemon tái tính trước khi send — mismatch → block + alert.

**iOS macOS XPC Process Isolation:**

- 💻 macOS Hardened Runtime tách `wasmtime` JIT ra `terachat-wasm-worker` (child process).
- Main process không có `allow-jit`. Giao tiếp qua XPC Service (Mach port).
- XPC crash → Transaction Journal recovery (xem §14.4).

**Soft-Enclave WASM Isolation (Cold Boot Defense):**

- ☁️ **Wasmtime Cranelift JIT Isolation:** "Soft-Enclave" cô lập xử lý khóa trong WASM Sandbox. Leak ra ngoài sandbox bị chặn bởi ranh giới Linear Memory.
- ☁️ **ChaCha8 Ephemeral Key Scrambling:** CSPRNG XOR liên tục vùng RAM chứa khóa. Plaintext chỉ xuất hiện trong CPU registers trong micro-giây khi tính toán.
- ☁️ **RAII ZeroizeOnDrop:** Tiêu hủy dữ liệu ngay khi biến rời scope — thay thế mlock() và TEE hardware locking.

**Observability:**

- Signal: `WasmSandboxTerminated(reason)`, `EgressSchemaViolation(plugin_id)`, `WasmOomKill`
- Metric: `wasm_execution_time_ms`, `egress_bytes_total{plugin_id}`

---

### F-12: Survival Mesh Network (P2P, BLE 5.0, Wi-Fi Direct)

**Description:** Mạng P2P sinh tồn tự thiết lập khi mất Internet, Store-and-Forward CRDT, phân cấp vai trò Desktop/Mobile.

**Supported Platforms:** 📱💻🖥️

**Transport Architecture:**

```rust
trait MeshTransport: Send + Sync {
    fn send(&self, payload: &[u8], peer_id: &PeerId) -> Result<(), MeshError>;
    fn recv_stream(&self) -> impl Stream<Item = (PeerId, Vec<u8>)>;
    fn discover_peers(&self) -> impl Stream<Item = PeerId>;
}
```

| Layer | Protocol | iOS | Android/Desktop |
|-------|----------|-----|----------------|
| **Signal Plane** | BLE 5.0 Advertising | `CoreBluetooth` | `BluetoothLeAdvertiser` |
| **Data Plane** | Wi-Fi P2P | `MultipeerConnectivity (AWDL)` | `Wi-Fi Direct` |

**Platform-Specific Adapters:**

- 📱 **iOS — `MultipeerConnectivityAdapter`:** `MeshTransport` implemented bằng Apple MultipeerConnectivity (MCSession). Dùng BLE + AWDL (~200 Mbps). App Review Guidelines compliant.
- 📱 **Android — `WifiDirectAdapter`:** Implement `MeshTransport` với `WifiP2PManager`.
- 💻🖥️ **Desktop — `LocalSocketAdapter`:** Full Wi-Fi Direct socket.

**Asymmetric Hierarchical Roles:**

| Role | Device | Capabilities |
|------|--------|-------------|
| Super Node (Backbone) | Desktop/Laptop (AC powered) | Full DAG history, Store-and-Forward 24/7, DAG merge O(N log N) |
| Relay Node | Android Foreground Service | Data Mule, Temporary Super Node (RAM ≥ 4GB, battery > 30%) |
| Leaf Node | iOS | Delta-only (max 50MB disk), Observer mode, no DAG merge |

**iOS Exclusion from Dictator Candidacy:**

- 📱 `election_weight = 0` cố định cho mọi node `device_class = "mobile"` iOS.
- 📱 Sau DAG merge bởi Desktop Dictator, Rust xuất **Materialized Snapshot** và phân phát về Mobile Leaf Nodes. Mobile apply Snapshot — O(1) thay vì O(N log N).

**EMDP — Emergency Mobile Dictator Protocol:**

Khi không có Desktop trong Mesh (xem chi tiết §12):

```text
Normal:         BLAKE3 Hash Election → Desktop/Android Super Node
EmergencyMobile: iOS-only mesh → Tactical Relay (Append-Only, text-forward, TTL 60min)
SoloAppendOnly: 1 device only, no election needed
```

**Energy Optimization:**

- 📱 **BLE Duty-Cycle:** 200ms Advertising/Scanning + 800ms Sleep → giảm 80% power.
- 📱 **iBeacon Stealth Mode:** CoreLocation iBeacon Ranging để duy trì BLE background scan.
- 📱 **OS Native Path Monitor:** `NWPathMonitor` (iOS) / `ConnectivityManager` (Android) để phát hiện mạng → Rust ngủ cho đến khi cần.

**Gossip Protocol & Broadcast:**

- 📱💻🖥️ **Store-and-Forward Gossip (Text):** Tin nhắn CRDT (<1KB) E2EE truyền multi-hop qua Router trung gian. Node lưu tạm và forward — không đọc được nội dung.
- 📱💻🖥️ **Direct-Link Only (File/Video):** File nặng bắt buộc P2P Wi-Fi Aware khép kín khi 2 máy trong phạm vi <20m. UI hiển thị "Chỉ gửi file khi ở gần".
- 📱💻 **Gossip Rate Limiting + zstd compression:** Giảm gói tin dư thừa trên BLE.

**Offline PKI Defense:**

- **Offline TTL:** App đóng băng Session nếu mất Server > TTL (theo `OfflineTTLProfile`).
- **Gossip CRL:** 1 node bắt Internet → tải CRL delta → ký Enterprise CA → Gossip BLE sang toàn Mesh ~30s → node revoked bị evict + Key Rotation.
- **Replay Protection:** Monotonic Version Counter + CA Signature + Timestamp Window (48h).

**AWDL Monitor — Hotspot/CarPlay Conflict:**

- 📱 Khi Hotspot active hoặc CarPlay → iOS tắt AWDL → Rust downgrade Tier 2 → Tier 3 (BLE only).
- 📱 Emit `UIEvent::TierChanged`: *"Hotspot đang bật — Mesh chuyển sang BLE. Voice tạm không khả dụng."*
- 📱 Queue voice packets TTL 30s. Sau 30s không phục hồi → drop voice.

**iOS Mesh Graceful Super Node Handover:**

- 📱 iOS detect memory pressure sắp trigger Jetsam → broadcast `MeshRoleHandover(candidate_node_id)` qua BLE trước khi bị kill.
- Desktop nhận → assume Super Node role. iOS → Leaf Node.
- UI: *"Đã chuyển vai trò Relay sang [tên thiết bị]"*.

**Observability:**

- Signal: `MeshModeActivated`, `MeshRoleChanged(old_role, new_role)`, `MeshPeerJoined(node_id)`, `MeshPeerShunned(node_id)`
- Metric: `mesh_active_peers`, `mesh_gossip_round_trip_ms`, `mesh_stored_bytes`

---

### F-13: Mesh Anti-Spam, DoS Resilience & Byzantine Fault Tolerance

**Description:** Chống Sybil attack, Byzantine quarantine, PoM epidemic broadcast, và OCPM (Objective Cryptographic Proof of Malfeasance).

**Supported Platforms:** 📱💻🖥️

**Micro-Proof-of-Work Defense:**

- 📱💻🖥️ SHA-256 Hashcash: 12-bit prefix challenge trước khi phát sóng tín hiệu.
- 📱 **Argon2id Adaptive (Nâng cấp):** `m=1MB, t=2, p=1` — ~50ms/challenge. Chống GPU/ASIC brute-force. Emergency SOS = 0ms (miễn phí).
- 📱 **Thermal Throttling Feedback:** iOS `ProcessInfo.thermalState` / Android `ThermalStatus` → tăng `t` khi thiết bị nóng.
- 💻📱 **Rate-limiting Ring Buffer:** 32-entry per `Node_ID`. Khoảng cách trung bình <100ms → Quarantine 15 phút.

**Byzantine Quarantine & Gossip Poison Pill:**

- ☁️📱 Phát hiện vi phạm (>3 signature errors / 10s) → **Poison Pill packet** (ký Enterprise CA) → lan truyền `SHUN: Node_ID` toàn Mesh ~30s.
- 💻📱 Thêm vào Local Denylist (SQLite WAL Append-Only). BLE/Wi-Fi Direct từ địa chỉ này bị Drop tại Hardware MAC Filter.
- ☁️📱 Xác thực CA signature trên Poison Pill trước khi áp dụng. Expired TTL (30 phút) → bỏ qua.

**OCPM (Objective Cryptographic Proof of Malfeasance):**

- 📱 Hardware-bound Non-repudiation: vi phạm ký ngay bằng `Device_Key` trong Secure Enclave.
- 💻📱 `Proof_Bundle = {raw_packet_bytes, timestamp_HLC, Node_ID, Ed25519_sig}` — không thể tái sử dụng cho node khác.
- 💻📱 Immutable Evidence: SQLite WAL với cờ `READ_ONLY` ngay sau ghi.
- 💻📱 Multi-party Attribution: yêu cầu ≥2 `Proof_Bundle` độc lập từ 2 node khác nhau trước khi Byzantine Shun.

**HLC-Epoch Temporal Binding (Chống Replay):**

- 💻📱 `|hlc_now - hlc_packet| < DRIFT_THRESHOLD (5s)` — quá ngưỡng → `TEMPORAL_VIOLATION`, drop.
- ☁️📱 Proof_Bundle bound với MLS Epoch hiện tại. Epoch mới → bằng chứng cũ invalid.
- 💻📱 24h Temporal Validation Window: Bloom Filter lưu `Evidence_Hash`. Duplicate → reject `EVIDENCE_REPLAYED`.
- 📱 Monotonic Hardware Counter Binding: Counter trong Proof_Bundle thấp hơn thiết bị hiện tại → `COUNTER_ROLLBACK`, reject.

**Gas-Metered Ephemeral Quarantine & PoM Epidemic:**

- 📱💻🖥️ **CFI + OLLVM Obfuscation:** Rust biên dịch với CFI — mỗi indirect call/jump xác thực tại runtime. Triệt tiêu ROP/JOP chain.
- 📱💻🖥️ **Gas-Metered Validation Sandbox:** Delta-State từ ngoài "detonated" trong WASM partition dùng một lần. Gas-metering: vượt quota → sandbox killed. Buffer overflow → `ZeroizeOnDrop`.
- 📱🖥️ **PoM Epidemic Broadcast:** Ngay khi Validation Sandbox phát hiện exploit → (1) đóng băng socket, (2) `BLAKE3(malicious_payload)` làm fingerprint, (3) phát tán qua Survival Mesh. Peers nhận → match hash → tự động Blacklist `DeviceIdentityKey`.

**Fixed-Size Relay Ring Buffer:**

- 📱💻🖥️ Static Ring Buffer trên Shared Memory giới hạn RAM chứa tin relay — chống OOM.
- 📱💻🖥️ OPA Engine quy chiếu Rate Limiting theo tín nhiệm user.
- 📱💻🖥️ QoS: loại trừ file/video tại Hop số 2+ trong pure P2P multi-hop mode.

---

### F-14: CRDT Sync & DAG State Management

**Description:** Offline-first append-only DAG với Hybrid Logical Clocks, deterministic convergence, split-brain recovery.

**Supported Platforms:** 📱💻🖥️☁️

**Core Properties:**

- 📱💻🖥️ **Hybrid Logical Clocks (HLC):** Mọi event dùng `(Lamport_Counter, Node_ID, Wall_Clock_HLC)`. Không dùng `SystemTime::now()` cho ordering.
- 📱💻🖥️ **Delta-State CRDT Pending Buffer:** Event out-of-order thiếu gốc → `Pending_RAM_Buffer`. UI chỉ render khi Causal Graph đầy đủ.
- 📱💻🖥️ **Deterministic LWW:** `Hash(Node_ID)` Tie-breaker + HLC cho Last-Write-Wins conflicts.
- 📱💻🖥️ **Ed25519 Signed Merge Patches:** Mọi state change phải kèm chữ ký Ed25519. Nodes xác thực trước khi apply.

**Tombstone & GC:**

- 💻📱🖥️ **Merged_Vector_Clock (MVC):** Tombstone chỉ Vacuum khi `tombstone.clock ≤ MVC` — tất cả peer đã xác nhận.
- 📱 **Zero-Byte Stub Transformation:** Sau Vacuum, Tombstone chuyển thành `(entity_id, hlc, type=DELETED)` — chống Replay Attack.
- 📱💻 **GC dựa trên Mesh ACK:** Chỉ GC sau khi ≥M peer ACK hoặc global sync. Không GC khi Partitioned.
- 📱💻🖥️ **7-Day Hot DAG Eviction:** `hot_dag.db` giữ 7 ngày gần nhất. GC scheduler 24h (background + sạc): chunk cũ → AEAD-encrypt → `cold_state.db` VPS → DELETE + VACUUM local. Mục tiêu: App <300MB mobile.

**Split-Brain Resolution:**

```text
Partition Detected
        │
        ▼
[Gossip Vector Clock Exchange] → Xác định Hash_Frontier cao nhất
        │
        ▼
[Tie-Breaker Hash Election (BLAKE3)]
  ├─ Has Desktop → Desktop Super Node = Dictator
  └─ Mobile Only → Android (RAM cao nhất) = Temp Dictator (max 200 delta/round)
        │
        ▼
[Dictator thực hiện O(N log N) Causal Merge]
        │
        ▼
[Materialized Snapshot → phân phát về Leaf Nodes]
        │
        ▼
[MLS Epoch Stitching → Epoch N+2 via TreeKEM Update Path]
```

**Multi-Island Fast-Forward:**

- 📱💻🖥️ **Gossip Frontier Discovery:** Nodes trao đổi Vector Clock qua Gossip để xác định biên giới.
- 📱💻🖥️ **Cryptographic Fast-Forward:** Node tụt hậu (Epoch N-k) bỏ qua giải mã tuần tự → hấp thụ `Update_Path` của MLS TreeKEM trực tiếp lên Epoch hiện tại.
- 📱 **iOS Lazy Evaluation + Asymmetric CRDT State-Squashing:** O(1) Memory Metadata Exchange qua BLE. DAG merge bởi Android/Desktop, iOS nhận Materialized Snapshot.

**Append-Only Immutable Hash Chain:**

- 📱💻🖥️ Mọi sự kiện là mắt xích trong Hash Chain một chiều — cấm rollback.
- 📱💻🖥️ Sự kiện bị xóa → Tombstone Stub móc vào DAG, không xóa vật lý.
- 📱💻🖥️ Byzantine Fault Tolerance: Mọi mắt xích xác thực Ed25519 — tampered entry bị network lật tẩy và reject.

**Deterministic State Reconciliation (Post-Crypto-Shredding):**

- 📱 `Hydration_Checkpoint`: extract `{Snapshot_CAS_UUID, vector_clock_frontier}` từ `hydration_checkpoints`.
- 📱☁️ `GossipStateRequest` siêu nhẹ (<2KB Vector Clock Summary) đến Super Nodes.
- ☁️ Server: set difference `(current_frontier) \ (client_known)` → chỉ gửi Delta thiếu. Bandwidth O(gap) không phải O(N).

**Observability:**

- Signal: `DagMergeCompleted(epoch_n)`, `SplitBrainDetected`, `TombstoneVacuumed(count)`
- Metric: `dag_event_count`, `crdt_pending_buffer_size`, `merge_latency_ms`

---

### F-15: Network Communication Protocols

**Description:** WebSocket E2EE Relay, WebRTC TURN, QUIC/gRPC/WSS multiplexing, push notifications.

**Supported Platforms:** 📱💻🖥️☁️

#### Real-time Messaging

- ☁️ Server relay ciphertext blob — không giải mã. Rate Limiting (Redis ZSET Sliding Window). OPA throttle theo phòng ban.

#### WebRTC Blind Relay (TURN)

- 📱💻🖥️ **Signaling:** Trao đổi SDP qua kênh chat MLS (E2EE channel).
- ☁️ **Transport:** SRTP — E2EE Audio/Video. TURN Server chỉ relay UDP mã hóa — không nắm Key.
- ☁️ **HA:** Keepalived Floating IP, failover 3 giây. Sizing: 1 Node ~ 50 HD streams, 4 vCPUs, 8GB RAM, 1 Gbps.
- 📱 **CallKit Integration (iOS):** iOS treat TeraChat calls như native calls → không bị background kill. TURN failover trong CallKit context không bị suspend.
- 📱 **Dual TURN Preconnect:** Khi app sắp vào Background, Rust proactively connect tới TURN dự phòng.

#### Application-Layer Priority Multiplexing (Chống HoLB)

- 📱💻🖥️ **P0/P1/P2 Priority Queue:** P0 = Key Updates, Ed25519 Sigs, BFT Consensus; P1 = Text messages, CRDT Delta; P2 = File transfer chunks, DB Hydration.
- ☁️ **Micro-Chunk Interleaving (64KB):** Sau mỗi 64KB file chunk, scheduler check P0/P1 queue → ưu tiên trước khi tiếp. Text không bao giờ chờ >1 chunk (<50ms).
- 🗄️ **BLAKE3 Segmented Merkle Tree:** Mỗi 64KB chunk có BLAKE3 hash riêng trong Merkle Tree. Corrupt chunk → requeset lại chunk đó only.

#### E2EE Push — iOS (NSE)

- 📱 `UNNotificationServiceExtension` + `mutable-content: 1` (chuẩn Signal/WhatsApp).
- 📱 **NSE Micro-Crypto Build Target:** 100% loại bỏ MLS, CRDT Automerge, SQLCipher. Chỉ AES-256-GCM decrypt + Shared Keychain read. Footprint ~4MB (safe dưới 24MB Apple limit).
- 📱 **Push Payload ≤ 4KB:** `chat_id`, `sender_display`, `preview_ct` (AES-256-GCM), `has_attachment`, `push_epoch`.

#### E2EE Push — Android & Huawei

- 📱 **Android:** FCM Data Message → `FirebaseMessagingService` → giải mã Rust FFI. StrongBox Keymaster lưu Symmetric Push Key.
- 📱 **Huawei:** HMS Push Kit (HPK) thay FCM. HMS Data Message trigger wakeup → Rust FFI giải mã. CRL refresh tối đa 4h delay (vs iOS/Android 30 phút).

#### Desktop Background Daemon

- 💻🖥️ **`terachat-daemon`** ~4.5MB RAM — tách biệt khỏi Tauri UI.
- 💻 Windows Service / macOS `launchd` LaunchAgent / 🖥️ Linux `systemd` user service.
- 💻🖥️ Nhận E2EE payload → giải mã preview → OS Native Notification → xóa plaintext.

**Linux Multi-Init Support:**

- 🐧 Init detection: systemd / openrc / runit / s6 / launchd → generate correct service file.
- Fallback: XDG autostart `.desktop` file. Daemon viết PID file cho bất kỳ init system nào.

---

### F-16: Large File Transfer & Streaming

**Description:** Zero-RAM streaming chunker cho file 10GB+, BLAKE3 Segmented Merkle, S3 Multipart, iOS Background delegation.

**Supported Platforms:** 📱💻🖥️☁️🗄️

**Crash Surface (trước khi có giải pháp):**
> Monolithic Encryption một file 10GB → RAM 10GB → Jetsam/Android OOM-Kill ngay. SQLite `SQLITE_TOOBIG` khi BLOB > 2GB. HTTP Keep-alive 30 phút trên mạng di động → Timeout.

**Streaming Chunker — Zero RAM Overhead:**

- 📱💻🖥️ **Hard Chunk Size = 2MB:** `pread(fd, buf, 2MB, offset)`. RAM max tại mọi thời điểm: ~10MB (Double Buffer).
- 📱💻🖥️ **mmap + ZeroizeOnDrop Pipeline:** Mỗi chunk mmap vào RAM bảo vệ bởi ZeroizeOnDrop. Sau push lên S3 + ACK → zeroize() → giải phóng.
- 📱💻🖥️ **Chunk-Level Key Derivation:** `Chunk_Key = HKDF(Session_Key, File_ID || Chunk_Index || Byte_Offset)`. Replay 1 chunk không ảnh hưởng chunks khác.

**BLAKE3 Segmented Merkle Tree:**

- 📱💻🖥️ `Leaf_Hash = BLAKE3(Ciphertext_Chunk || Chunk_Key || Chunk_Index)` → tổng hợp thành `Merkle_Root_Hash`.
- 📱💻🖥️ Client nhận `Merkle_Root_Hash` từ Control Plane TRƯỚC khi nhận payload. Verify từng chunk độc lập.
- 📱💻🖥️ **Fault Tolerance:** Đứt mạng ở chunk 4999/5000 → chỉ re-upload 2MB đó. 9.998GB được giữ nguyên.
- ☁️ `Merkle_Root_Hash` cuối ký Ed25519 + lưu Append-Only Audit Log.

**S3 Multipart Upload:**

- ☁️🗄️ **Salted MLE via MinIO S3 Multipart:** Mỗi Part = 1 Chunk ciphertext. VPS/MinIO nhận ciphertext thuần túy.
- ☁️🗄️ Throughput: 300–500MB/s. Latency từ chọn file → bắt đầu upload < 50ms.
- ☁️ Anti-`413 Request Entity Too Large`: Mỗi Part = 2MB, không vi phạm `client_max_body_size` của Nginx (thường 100MB).

**iOS Background Delegation:**

- 📱 **Pre-signed URL Per Chunk:** TTL 15 phút, HMAC-SHA256 bound to device. Bàn giao cho `NSURLSession Background Transfer`.
- 📱 Apple OS tự quản lý socket, báo progress `URLSession didSendBodyData`, xử lý retry. App không cần thức.
- 📱 **Android WorkManager:** `[Encrypt_Chunk → S3_Upload_Chunk → ZeroizeOnDrop]` per chunk. Constraint: `NetworkType.CONNECTED`, `requiresBatteryNotLow()`.

---

### F-17: API Secret Management

**Description:** E2EE Vault cho API Keys, Cryptographic Binding bot-to-key, Instant Revoke.

**Supported Platforms:** ☁️🗄️📱💻🖥️

**Key Mechanisms:**

- ☁️🗄️ **Blind Vault Storage:** Admin nhập `{name, value}` → Rust sinh `Vault_Key (AES-256)` sync giữa Admin devices qua E2EE → `encrypted_blob = AES-256-GCM(Vault_Key, api_key)` → VPS. VPS lưu label + ciphertext — **không biết giá trị thực.**
- 📱💻🖥️ **Cryptographic Bot Binding:** Admin bấm [+] cấp key cho Bot → Client giải mã trong RAM (<100ms) → `Bot_Bound_Blob = Curve25519_ECIES.encrypt(Bot_Public_Key, api_key)` → DROP(api_key) → push VPS. VPS chỉ mở được bằng `Bot_Private_Key` — không rời chip.
- ☁️ **Instant Revoke:** Admin đổi key gốc → `rebind_all_bots()` mã hóa lại toàn bộ `Bot_Bound_Blob` trong <2 giây.
- ☁️🗄️ **BYOK:** API Key lưu trong Secure Enclave / OS Keychain — không bao giờ plaintext trên Server.

---

### F-18: Federation Bridge

**Description:** Cross-cluster communication qua mTLS, Sealed Sender, OPA Policy, circuit breaker.

**Supported Platforms:** ☁️

**Key Mechanisms:**

- ☁️ **mTLS Mutual Auth (PKI nội bộ):** Không dùng CA công cộng.
- ☁️ **Signed JWT Federation_Invite_Token:** Keycloak/Dex xác thực lời mời.
- ☁️ **Federation Trust Registry:** Public Key các Cluster liên kết trong sổ cái PKI nội bộ — update bất đồng bộ qua CRDT Gossip.
- ☁️ **Sealed Sender Protocol:** Header người gửi mã hóa bằng Public Key người nhận — Server Chi nhánh không biết danh tính HQ.
- ☁️ **OPA ABAC tại API Gateway:** `sender_role` + `allow_reply` lọc gói tin liên cụm.
- ☁️ **Circuit Breaker:** Khi tin nhắn liên cụm vượt ngưỡng → OPEN fail-fast về UI trong <1s.
- ☁️ **Z3 Formal Verification:** OPA Policy liên cụm qua SMT Model → Z3 Solver trước khi deploy.

---

### F-19: E2EE Cloud Backup & Identity Restore

**Description:** Zero-Knowledge cloud backup, biometric-backed restore, BIP-39 recovery phrase.

**Supported Platforms:** ☁️🗄️📱💻

**Key Mechanisms:**

- ☁️🗄️ **E2EE Cloud Backup (Zero-Knowledge):** Lõi Rust mã hóa `cold_state.db` bằng `Device_Key` (Secure Enclave/StrongBox) trước khi push lên Cloud. Server chỉ thấy Ciphertext.
- 📱💻 **Biometric-backed Restore:** Thiết bị mới xác thực FaceID/TouchID hoặc TPM 2.0. Lõi Rust tải Ciphertext về, giải mã local.
- 📱💻 **Recovery Phrase (BIP-39 Mnemonic):** 24-word Mnemonic phát sinh khi thiết lập lần đầu. Dùng Mnemonic + Biometric để khôi phục `Device_Key`.

---

### F-20: Zero-Access Diagnostics (TeraDiag)

**Description:** Thu thập log chẩn đoán trong WASM Sandbox cô lập mà không tiếp xúc dữ liệu tin nhắn.

**Supported Platforms:** 📱💻☁️

**Key Mechanisms:**

- 📱 **WASM Sandbox (ReadOnly Partition):** TeraDiag chỉ có `PROT_READ` đối với phân vùng `diag_logs`. Không thể truy xuất DB chính.
- 📱 **XChaCha20-Poly1305 Pipeline:** Log mã hóa stream-based trước khi đồng bộ.
- 📱 **Wi-Fi Direct (Log Sync over Mesh):** P2P tức thì khi mất Internet.
- ☁️ **OPA Block Egress:** App ID `com.terachat.diag` — Egress Blocked ra Internet; chỉ Mesh nội bộ.
- 🗄️ **128MB RAM Cap + Deterministic Chunking.**
- ⭐ **Publisher Trust Tier 1 (TeraChat HQ Sign):** Phải mang chữ ký Root CA TeraChat HQ.

---

### F-21: Huawei HarmonyOS Stack

**Description:** Thay thế Google Services bằng HMS equivalents cho Huawei HarmonyOS platform.

**Supported Platforms:** 📱 Huawei HarmonyOS

**HMS Integration:**

| Component | Android | Huawei HarmonyOS |
|-----------|---------|-----------------|
| Push | FCM | HMS Push Kit (HPK) |
| Neural Acceleration | NNAPI | HiAI Foundation API |
| BLE | Android BLE API | HarmonyOS BLE API |
| Attestation | Play Integrity | HMS SafetyDetect `DeviceIntegrity()` |
| TEE | StrongBox | TrustZone (ARM) — same ARM API, different HAL |
| WASM | wasmtime JIT | wasmtime JIT (không bị W^X như iOS) |
| Distribution | Google Play | AppGallery |
| Enterprise MDM | Android EMM | Huawei Device Manager |

**HarmonyOS-Specific Notes:**

- 📱 Không có dynamic WASM từ marketplace → AOT bundle bắt buộc (như iOS).
- 📱 CRL refresh: 4h polling Foreground + HMS Data Message Background (delay tối đa 4h vs iOS/Android 30 phút).
- 📱 AppGallery: submit `.apk` + AOT-bundled `.tapp` packages.

**Formal IPC Memory Ownership Contract (Token Protocol):**

```rust
// Rust Core xuất 2 FFI primitive thay vì raw pointer
extern "C" {
    fn tera_buf_acquire(id: u64) -> u64; // returns opaque token, NOT raw pointer
    fn tera_buf_release(token: u64);    // Rust mới được phép zeroize
}
// iOS JSI và Android Dart FFI đều gọi tera_buf_release() trong destructor/finalizer
// Rust Core: ref_count per-token; ZeroizeOnDrop chỉ khi ref_count == 0
// CI lint rule: cấm FFI endpoint trả Vec<u8>/ptr trực tiếp
```

**iOS Key Protection — Double-Buffer Zeroize Protocol:**

```
1. Phân bổ key vào 2 page liền kề MAP_ANONYMOUS|MAP_PRIVATE
2. Ngay sau decrypt: ghi đè 0x00 vào page 1 TRƯỚC KHI dùng key
3. Dùng key từ page 2
4. Sau ZeroizeOnDrop: ghi đè cả 2 page
5. Nếu Jetsam kill trước Drop: page 1 đã clean; page 2 = 1 page đơn lẻ khó exploit
```

**Dart FFI NativeFinalizer Contract:**

```dart
class TeraSecureBuffer {
  // Mọi buffer PHẢI dùng useInTransaction hoặc explicit releaseNow()
  // KHÔNG được để GC làm finalizer là đường duy nhất release
  void releaseNow() { /* explicit before GC */ }
  T useInTransaction<T>(T Function(Pointer<Uint8> ptr) action) {
    try { return action(_token.toPointer()); }
    finally { releaseNow(); } // kể cả exception
  }
}
```

---

### F-22: License Architecture & Cryptographic Entanglement

**Description:** HSM FIPS 140-3 JWT licensing, KDF entanglement với DeviceIdentityKey, graceful degradation.

**Supported Platforms:** 📱💻🖥️☁️🗄️

**Open-Core Boundary:**

| Component | License | Scope |
|-----------|---------|-------|
| `terachat-core/` (Crypto, MLS, CRDT, Mesh) | AGPLv3 | Public — Gov/Bank audit |
| `terachat-license-guard/` (License validation) | BSL | Closed — không trong security audit scope |
| `terachat-ui/` (Flutter, Tauri) | Apache 2.0 | Public |

**License JWT Structure (HSM FIPS 140-3 Level 4):**

```json
{
  "tenant_id": "acme-corp-vn",
  "domain": "acme.terachat.io",
  "max_seats": 500,
  "tier": "enterprise",
  "valid_until": "2027-03-15T00:00:00Z",
  "max_protocol_version": "2.0",
  "offline_ttl_hours": 720,
  "features": ["mesh_survival", "ai_dlp", "federation", "compliance_audit"]
}
```

Chữ ký **Ed25519** từ HSM Private Key — key không bao giờ rời chip.

**Cryptographic Entanglement (Write-Only Pattern):**

```rust
fn derive_master_unlock_key(
    license_token: &LicenseToken,
    epoch: u64,
) -> Result<MasterUnlockKey, LicenseError> {
    // DeviceIdentityKey không rời chip — chỉ làm KDF input
    let device_key_material = secure_enclave::sign_derive(
        b"license-kdf-v1",
        epoch.to_le_bytes().as_ref(),
    )?;
    
    let kdf_input = [
        device_key_material.as_ref(),
        license_token.signature.as_ref(),
        &epoch.to_le_bytes(),
    ].concat();

    // Sai license → sai key → mọi AEAD decrypt = rác
    Ok(MasterUnlockKey(hkdf_sha256(&kdf_input, b"terachat-master-v1")))
}
// Không return device_key_material. Không export master_key qua FFI.
```

**Runtime Heartbeat Validation (24h, offline-capable):**

| Check | Mechanism | Fail → |
|-------|-----------|--------|
| JWT signature | Ed25519 vs bundled Root CA | Immediate lock |
| Expiry | `valid_until` > TPM Monotonic Counter | Immediate lock |
| Seat count | `active_device_keys` ≤ `max_seats` | Block new enrollment |
| Revocation | CRL endpoint (online) / skip (air-gapped) | Immediate lock |

**Offline TTL Profile:**

```rust
pub enum OfflineTTLProfile {
    Consumer { ttl_hours: 24 },
    Enterprise { ttl_hours: u32 },     // configurable, default 168 (7 days)
    GovMilitary { ttl_hours: 720 },    // 30 ngày
    AirGapped { revocation_only: bool },
}
```

**Graceful Degradation (4 cấp độ):**

| Thời điểm | UI | Ảnh hưởng hoạt động |
|-----------|-----|---------------------|
| T-30 ngày | Banner vàng Admin Console | Không |
| T-0 | Admin Console partial lock | Chat/Mesh OK; AI + add user bị khóa |
| T+90 | Refuse new bootstrap | App đang chạy OK; không restart được |
| Gia hạn | JWT mới → restore <5s | Không restart |

**Anti-Crack Measures:**

- 💻 **O-LLVM Control Flow Flattening:** State Machine kiểm tra License bị flatten và xáo trộn → IDA Pro/Ghidra bị mù.
- 🖥️ **Bogus Control Flow (Dead Code Injection):** Tăng CFG complexity, triệt tiêu concretization.
- 🗄️ **TPM 2.0 Monotonic Counter:** Chặn Clock Rollback và Snapshot replay.

**HSM Sub-CA Anti-Cloning (FIPS 140-3 Level 4):**

- 🗄️ HSM ký `DeviceIdentityKey` mới — Private Key không rời chip.
- 🗄️ Decrementing Monotonic Counter: mỗi lần issue → counter giảm; counter = 0 → HSM từ chối.
- 🖥️ Offline Ed25519 Signing tại hầm ngầm air-gapped; chỉ Signed Certificate ra ngoài qua USB mã hóa.

---

## §5 STATE MACHINE

> Tổng hợp state logic từ toàn bộ hệ thống.

### 5.1 Network Connectivity State Machine

```text
States: ONLINE_QUIC → ONLINE_GRPC → ONLINE_WSS → MESH_MODE → SOLO_OFFLINE

Transitions:
  ONLINE_QUIC    ──UDP timeout 50ms──▶  ONLINE_GRPC
  ONLINE_GRPC    ──DPI rejects──────▶  ONLINE_WSS
  ONLINE_WSS     ──all fail──────────▶  MESH_MODE
  MESH_MODE      ──no peers──────────▶  SOLO_OFFLINE
  Any            ──reconnect OK──────▶  ONLINE_QUIC (retry from top)

Triggers:
  ONLINE_* → MESH_MODE: Heartbeat timeout >30s || loss of Wi-Fi/4G
  MESH_MODE → ONLINE_*: Heartbeat success
  MESH_MODE → SOLO_OFFLINE: No BLE/Wi-Fi Direct peers for TTL period

Side effects:
  → MESH_MODE:   All WASM Sandboxes terminate; 100% CPU/RAM → Mesh routing
  → ONLINE_QUIC: Resume WASM; emit StateChanged(protocol=QUIC)
```

### 5.2 MLS Epoch State Machine

```text
States: EPOCH_ACTIVE(n) → EPOCH_ROTATING → EPOCH_ACTIVE(n+1)

Transitions:
  EPOCH_ACTIVE    ──member_leave || schedule──▶  EPOCH_ROTATING
  EPOCH_ROTATING  ──Update_Path commit OK──────▶  EPOCH_ACTIVE(n+1)
  EPOCH_ROTATING  ──timeout / network loss──────▶  EPOCH_ROTATING (retry)

Triggers:
  Member leave: immediate rotation
  Push Key desync: Main App rotate push_epoch after Foreground wakeup
  Peer-Assisted Re-induction: reconnecting device triggers Add_Member

Side effects:
  → EPOCH_ROTATING: Old Epoch_Key zeroized; Push_Key rotated OOB
  → EPOCH_ACTIVE(n+1): Forward Secrecy guaranteed; Sealed Sender re-keyed
```

### 5.3 CRDT DAG State Machine

```text
States: SYNCED → PARTITIONED → SPLIT_BRAIN → MERGING → SYNCED

Transitions:
  SYNCED       ──network loss──────────▶  PARTITIONED
  PARTITIONED  ──local writes only────▶  SPLIT_BRAIN (multiple DAG branches)
  SPLIT_BRAIN  ──reconnect + Gossip───▶  MERGING
  MERGING      ──Dictator Election────▶  MERGING (O(N log N) merge)
  MERGING      ──Snapshot distributed─▶  SYNCED

Triggers:
  Partition: Heartbeat to server/peers fails
  Reconnect: BLE peer discovery || server heartbeat resumes
  Dictator: BLAKE3 Hash Election; Desktop preferred; iOS excluded

Side effects:
  → SPLIT_BRAIN:  UI shows dashed border on pending messages
  → MERGING:      Desktop O(N log N) merge; Mobile receives Snapshot
  → SYNCED:       MLS Epoch stitching; CRDT borders solid
```

### 5.4 WASM Sandbox Lifecycle State Machine

```text
States: UNLOADED → LOADING → ACTIVE → SUSPENDED → TERMINATED

Transitions:
  UNLOADED   ──Admin install + Ed25519 verify──▶  LOADING
  LOADING    ──OPA policy check pass────────────▶  ACTIVE
  LOADING    ──Signature fail || OPA deny───────▶  TERMINATED
  ACTIVE     ──idle timeout || Mesh mode─────────▶  SUSPENDED
  ACTIVE     ──Gas quota exceeded───────────────▶  TERMINATED
  SUSPENDED  ──User interaction──────────────────▶  ACTIVE (re-hydrate snapshot)
  SUSPENDED  ──KILL_DIRECTIVE received──────────▶  TERMINATED
  Any        ──MESH_MODE activated──────────────▶  TERMINATED (immediate)

Side effects:
  → TERMINATED: ZeroizeOnDrop all Linear Memory; revoke Delegation Tokens; clear KV-Cache
  → SUSPENDED:  AES-256-GCM encrypted Snapshot saved
```

### 5.5 License State Machine

```text
States: VALID → WARNING → DEGRADED → LOCKED → RESTORED

Transitions:
  VALID     ──T-30 days──────────────▶  WARNING
  WARNING   ──T-0 (valid_until = now)─▶  DEGRADED
  DEGRADED  ──T+90 days────────────────▶  LOCKED
  LOCKED    ──new JWT loaded────────────▶  RESTORED → VALID
  Any       ──signature invalid───────▶  LOCKED (immediate)
  Any       ──TPM counter rollback───▶  LOCKED (immediate)

Side effects:
  → WARNING:   Banner vàng Admin Console
  → DEGRADED:  AI module off; add user blocked; Chat/Mesh continue
  → LOCKED:    Refuse new bootstrap; existing session continues
  → RESTORED:  All features restored in <5s; no restart needed
```

### 5.6 EMDP — Emergency Mobile Dictator Protocol State Machine

```text
States: NORMAL → EMERGENCY_MOBILE_ONLY → SOLO_APPEND_ONLY

Transitions:
  NORMAL              ──no Desktop/Android peers──▶  EMERGENCY_MOBILE_ONLY
  EMERGENCY_MOBILE_ONLY ──60 min TTL expired─────▶  expired (auto-cleanup)
  EMERGENCY_MOBILE_ONLY ──Desktop reconnects─────▶  NORMAL (key escrow decrypt + DAG merge)
  NORMAL              ──single device only────────▶  SOLO_APPEND_ONLY

EMERGENCY_MOBILE_ONLY Properties:
  - Tactical Relay = iOS device (battery_score + ble_rssi highest)
  - Tactical Relay ≠ Super Node: Append-Only CRDT, store-and-forward text only
  - NO DAG merge, NO MLS Epoch rotation, NO conflict resolution
  - EMDP Key Escrow: Desktop exports AES-256 relay_session_key before offline
    Encrypted with iOS device pubkey; delivered via BLE Control Plane
  - When Desktop reconnects: decrypt relay messages → merge DAG → epoch reconcile
```

---

## §6 API / IPC CONTRACT

> Nguồn sự thật duy nhất cho mọi giao tiếp cross-boundary.

### 6.1 CoreSignals (Rust → UI)

| Signal | Payload | Trigger | UI Action |
|--------|---------|---------|-----------|
| `StateChanged(table, version)` | table name, version number | Any DB write | UI query fresh snapshot |
| `MeshModeActivated` | `{peer_count, transport}` | Network loss | Switch dark UI (#0F172A) |
| `MeshRoleChanged(role)` | new role enum | Jetsam pressure / Desktop join | Show role transfer banner |
| `NetworkProtocolChanged(proto)` | QUIC/gRPC/WSS | ALPN fallback | Update HUD icon |
| `MemoryPressureHigh` | `{available_mb}` | OS memory warning | Reduce blur 20px→8px |
| `MlsEpochRotated(n)` | epoch number | Member leave / schedule | Update E2EE badge |
| `SecurityEvent::*` | event details | Various | RSOD / warning overlay |
| `MlsKeyDesync(chat_id)` | chat ID | NSE push_epoch mismatch | Trigger Main App wakeup |
| `WasmSandboxTerminated(reason)` | reason string | Gas/timeout/mesh | Remove .tapp from UI |
| `LicenseStateChanged(state)` | new state enum | Heartbeat check | Show/hide feature lock UI |
| `FcpTriggered` | `{plugin_id, timestamp}` | Admin FCP activation | Red border overlay |
| `ConversationSealed` | `{chat_id}` | SSA taint threshold | Hazard-stripe overlay |
| `EgressSchemaViolation(plugin_id)` | plugin ID | Payload mismatch | Alert + quarantine .tapp |
| `DmaIntrusionDetected` | PCI device info | IOMMU group change | Full-screen DMA alert |
| `AwdlUnavailable(reason)` | hotspot/carplay | iOS AWDL monitor | Tier downgrade banner |

### 6.2 UICommands (UI → Rust via FFI/JSI)

| Command | Parameters | Effect |
|---------|-----------|--------|
| `fetch_ai_context(depth: u32)` | message depth | Rust handles decrypt→mask→egress; returns via StateChanged |
| `invoke_ai_context(message_ids)` | Vec<String> | Trigger AI pipeline |
| `request_mesh_activation()` | none | Rust calls OS BLE/Wi-Fi APIs |
| `terachat_core_flush_io()` | none | Flush WAL checkpoint (on app terminate) |
| `terachat_core_emergency_wipe()` | none | Hard kill + ZeroizeOnDrop all (priority override) |
| `terachat_cancel_task(task_id)` | task ID | AbortHandle → tokio::select! cancel |
| `tera_buf_acquire(id)` | buffer ID | Returns opaque token (NOT raw ptr) |
| `tera_buf_release(token)` | token | Triggers ZeroizeOnDrop when ref_count==0 |
| `vault::pin_file(cas_ref, folder_id)` | CAS ref, folder | Virtual pin; O(1); no file copy |

### 6.3 Data Plane IPC

| Platform | Mechanism | Throughput | Use Case |
|----------|-----------|-----------|----------|
| 📱 iOS | JSI C++ `std::unique_ptr` + Custom Deleter | ~400MB/s | Large payloads, media |
| 📱 Android / Huawei | Dart FFI TypedData (C ABI static buffer) | ~400MB/s | Large payloads, media |
| 💻🖥️ Desktop | `SharedArrayBuffer` (mmap physical) | ~500MB/s | File chunks, embeddings |
| All | Protobuf over Control Plane (<50 bytes) | N/A | Commands, metadata |

**IPC Security Rules:**

- Control Plane: lệnh nhỏ <1KB — không carry plaintext key material.
- Data Plane: Zero-Copy qua shared memory — Rust kiểm tra `offset + length ≤ SAB_SIZE` + CRC32. Vi phạm → SIGSEGV trap + panic.
- `Company_Key` / `Channel_Key` **tuyệt đối không** truyền qua IPC lên WASM. WASM gửi data vào buffer, Rust tự dùng Key đang trong ZeroizeOnDrop scope.

### 6.4 Host Function ABI (WASM → Rust)

```rust
// ABI version: semver — breaking changes = major version bump
// Deprecated: 12 tháng support window

// Crypto operations (offloaded to Rust Core)
extern "C" {
    fn host_blake3_hash(data: *const u8, len: usize, out: *mut u8) -> i32;
    fn host_ed25519_sign(key_id: u64, msg: *const u8, msg_len: usize, sig_out: *mut u8) -> i32;
    fn host_aes256gcm_encrypt(key_id: u64, nonce: *const u8, pt: *const u8, pt_len: usize, ct_out: *mut u8) -> i32;
    fn host_aes256gcm_decrypt(key_id: u64, nonce: *const u8, ct: *const u8, ct_len: usize, pt_out: *mut u8) -> i32;
}

// Network egress (via Egress_Outbox — not direct socket)
extern "C" {
    fn host_egress_write(endpoint_id: u64, payload: *const u8, len: usize) -> i32;
    // Returns: 0=OK, 1=QuotaExceeded, 2=SchemaViolation, 3=OPADeny, 4=MeshRestricted
}

// Storage (scoped per .tapp DID)
extern "C" {
    fn host_storage_get(key: *const u8, key_len: usize, out: *mut u8, out_max: usize) -> i32;
    fn host_storage_set(key: *const u8, key_len: usize, val: *const u8, val_len: usize) -> i32;
}
```

**Manifest ABI Versioning (required in manifest.json):**

```json
{
  "host_api_version": "1.3.0",
  "min_host_api_version": "1.0.0",
  "max_host_api_version": "2.0.0"
}
```

Reject `.tapp` nếu `host_api_version` ngoài range Core support.

---

## §7 PLATFORM MATRIX

| Feature | 📱 iOS | 📱 Android | 📱 Huawei | 💻 macOS | 💻 Windows | 🖥️ Linux |
|---------|--------|-----------|---------|---------|----------|---------|
| WASM Engine | wasm3 (interpreter) | wasmtime JIT | wasmtime JIT | wasmtime JIT (XPC isolated) | wasmtime JIT | wasmtime JIT |
| Key Storage | Secure Enclave | StrongBox Keymaster | TrustZone (ARM) | Secure Enclave | TPM 2.0 + NCrypt | TPM 2.0 + IMA |
| mlock() | ❌ (kCFAllocatorMallocZone) | ✅ | ✅ | ✅ | ✅ VirtualLock() | ✅ |
| JIT WASM | ❌ W^X | ✅ | ✅ | ✅ (child XPC only) | ✅ | ✅ |
| Background BLE | iBeacon + L2CAP | CDM + Doze bypass | HMS BLE API | ✅ | ✅ USB dongle | ✅ |
| Push | APNs NSE | FCM | HMS Push Kit | Daemon | Daemon | Daemon |
| Attestation | DeviceCheck + App Attest | Play Integrity | HMS SafetyDetect | Notarization | TPM Health | TPM 2.0 + IMA |
| File Transfer BG | NSURLSession BGT | WorkManager | WorkManager | ✅ daemon | ✅ daemon | ✅ daemon |
| Mesh Wi-Fi | AWDL (MCSession) | Wi-Fi Direct | Wi-Fi Direct | AWDL | Wi-Fi Direct | Wi-Fi Direct |
| DMA Protection | N/A (mobile) | N/A (mobile) | N/A (mobile) | ✅ IOMMU | ✅ IOMMU + WFP | ✅ IOMMU /sys |
| Full Disk Encrypt | FileVault (N/A mobile) | N/A | N/A | FileVault (checked) | BitLocker (checked) | Checked at startup |
| Super Node Eligible | ❌ (iOS excluded) | ✅ (RAM ≥ 4GB) | ✅ | ✅ | ✅ | ✅ |
| EMDP Tactical Relay | ✅ (Leaf/Tactical only) | ✅ | ✅ | ✅ Super Node | ✅ Super Node | ✅ Super Node |
| Clipboard Protection | `UIPasteboard` 60s TTL | FLAG_SECURE + Sensitive API | FLAG_SECURE | Rust Hook syscall | Rust Hook SetClipboardData | wl-clipboard / xclip |
| Wayland Clipboard | N/A | N/A | N/A | N/A | N/A | wl-clipboard (detected) |

**Build Target Matrix:**

```
x86_64-apple-darwin        → macOS Intel
aarch64-apple-darwin       → macOS Apple Silicon
x86_64-pc-windows-msvc     → Windows x64
aarch64-pc-windows-msvc    → Windows ARM64
x86_64-unknown-linux-gnu   → Linux x64 (.deb/.rpm/AppImage)
aarch64-unknown-linux-gnu  → Linux ARM64 (server deployment)
aarch64-apple-ios          → iOS
aarch64-linux-android      → Android + Huawei HarmonyOS
```

**Linux Packaging Strategy:**

| Format | memfd_create | seccomp-bpf | Gov Enterprise |
|--------|-------------|-------------|---------------|
| **Signed .deb/.rpm** | ✅ | ✅ | ✅ GPG signed |
| **AppImage (fallback)** | ✅ | ✅ | Cosign signature |
| ~~Flatpak~~ | ❌ blocked by bubblewrap | ❌ conflict | ❌ không dùng |

**GPU Capability Tiers (Glassmorphism rendering):**

| Tier | Condition | Rendering |
|------|-----------|-----------|
| A | GPU Hardware Compositing | Full Glass: `backdrop-filter: blur(16-24px)` |
| B | Software Compositing | Frosted Glass Lite: `blur(8px)`, opacity 0.85 |
| C | No Compositing (Intel UHD 620 old) | Flat Solid + border accent |

---

## §8 NON-FUNCTIONAL REQUIREMENTS

> Trích xuất từ nội dung implementation. Không tự bịa.

### 8.1 Performance

| Metric | Target | Platform | Notes |
|--------|--------|---------|-------|
| Message E2EE encrypt/decrypt | <10ms | 📱💻🖥️ | AES-NI/ARM NEON accelerated |
| CRDT Write Local | <5ms | 📱💻🖥️ | SQLite WAL WAL-mode |
| MLS Group operation (5000 users) | O(log n) | ☁️ | TreeKEM |
| ALPN Protocol Negotiation | <50ms total | 📱💻☁️ | Parallel probe |
| Cold Start .tapp | <50ms | 💻🖥️ | AOT pre-warming |
| Cold Start .tapp (iOS wasm3) | <20ms init | 📱 | No pre-warming |
| DAG GC Epoch | <50ms | 📱 | CPU throttled background |
| Snapshot Apply | O(1) | 📱💻 | cold_state.db INSERT OR REPLACE |
| ONNX Trial Matching (10k users) | <3ms | 💻📱 | Vectorized AES-NI/NEON |
| E2E Latency (Online QUIC) | <30ms | ☁️📱💻 | Co-located VPS, SLA 99.999% |
| Throughput IPC Data Plane | ~400-500MB/s | 📱💻🖥️ | Zero-copy |
| File Chunker Throughput | 300-500MB/s | ☁️🗄️ | NVMe + io_uring |
| WebSocket Connections per VPS | ~500,000 | ☁️ | 4GB RAM, ~2KB/connection |

### 8.2 Memory

| Component | Limit | Platform | Notes |
|-----------|-------|---------|-------|
| NSE Process | ≤24MB | 📱 iOS | Apple hard limit |
| NSE Micro-Crypto | ~4MB | 📱 iOS | Stripped MLS/CRDT/SQLCipher |
| WASM Sandbox per instance | ≤64MB (soft cap) | 📱💻🖥️ | OOM-kill without warning |
| LRU Cache (Main App) | 50MB | 📱 | ZeroizeOnDrop on evict |
| Delta-State CRDT Buffer | ≤50MB disk | 📱 | Mobile Leaf Node limit |
| hot_dag.db target | <300MB | 📱 | Mobile; 7-day eviction window |
| Whisper AI Tiny | 39MB | 📱 | Only load when available_ram > 100MB |
| Whisper AI Base | 74MB | 📱 | Only load when available_ram > 200MB |
| Vector Index RAM | ≤8MB heap | 📱💻 | ZeroizeOnDrop per session |
| Egress_Outbox Ring Buffer | 2MB max | 📱💻🖥️ | Hard limit; overflow = terminate |
| File Chunk Double Buffer | ~10MB | 📱💻🖥️ | 2 chunks × 2MB at any time |

### 8.3 Reliability

| Scenario | SLA | Mechanism |
|----------|-----|-----------|
| Online messaging (SLA) | 99.999% | Anti-Entropy Merkle Sync fallback |
| TURN failover | <3s | Keepalived Floating IP |
| SCIM offboarding | <30s | Event-driven revocation |
| Epoch Rotation (member leave) | Immediate | TreeKEM Update Path |
| Snapshot recovery | O(1) | cold_state.db cold bootstrap |
| Jetsam kill NSE mid-WAL | No data loss | Two-Phase Cryptographic Commit |
| XPC Worker crash | User re-sign prompt | XPC Transaction Journal (PENDING state) |
| Hard power loss during Hydration | Resume from checkpoint | Hydration_Checkpoint + Shadow Paging |

### 8.4 Security SLA

| Property | Guarantee | Mechanism |
|----------|-----------|-----------|
| Forward Secrecy | Per MLS Epoch | TreeKEM Update Path; old key zeroized |
| Key Extraction | Computationally infeasible | Hardware Enclave; no key in RAM plaintext |
| Plaintext on disk | Never | SQLCipher + ZeroizeOnDrop; no plaintext persist |
| Audit Log tamper | Cryptographically impossible | Ed25519 Append-Only Hash Chain |
| License forgery | Computationally infeasible | HSM FIPS 140-3 Ed25519 + KDF entanglement |
| Replay attack | <48h window | HLC Epoch binding + Monotonic Counter |

---

## §9 SECURITY MODEL

### 9.1 Key Management & Cryptographic Primitives

| Operation | Algorithm | Library | Notes |
|-----------|-----------|---------|-------|
| Asymmetric signing | Ed25519 | `ring` | All audit log entries, update signatures |
| Key exchange | X25519 + ML-KEM-768 | `ring` + `pqcrypto` | Hybrid PQ-KEM |
| Symmetric encryption | AES-256-GCM | `ring` | All E2EE payloads |
| Hashing | BLAKE3 | `blake3` | DAG integrity, CAS routing |
| Password KDF | Argon2id | `argon2` | PIN Fallback KEK, 0.5s CPU tuning |
| Key derivation | HKDF-SHA256 | `ring` | Key hierarchy derivation |
| Constant-time comparison | `subtle` crate | `subtle` | All MAC/signature comparisons |
| Random generation | OS CSPRNG | `ring::rand` | All nonces, session keys |

**Invariants:**

- Không self-implement bất kỳ cryptographic primitive nào.
- `f32/f64` WASM opcodes bị block — Fixed-point arithmetic only cho consensus-critical paths.
- Constant-time logic via `subtle` crate — triệt tiêu timing attack.

### 9.2 Attack Surface Matrix

| Attack Vector | Mitigation | Section |
|---------------|-----------|---------|
| Memory dump / Cold Boot | ZeroizeOnDrop everywhere; ChaCha8 RAM scrambling | §4.6 |
| DMA (Thunderbolt/PCIe) | IOMMU check at startup; MDM DMA compliance policy | §4.4 |
| JIT spraying (WASM) | iOS: wasm3 interpreter; others: sandbox CFI | §F-11 |
| Timing side-channel | `subtle` crate; constant-time logic; Timer degradation 5-10ms | §2.6 |
| Traffic pattern analysis | Fixed-size padding; Heartbeat Dummy Traffic; Oblivious CAS Routing | §2.6 |
| Sybil (Mesh) | mPoW Argon2id; Signed identity via DeviceIdentityKey | §F-13 |
| Byzantine fault | PoM Epidemic; Multi-party attribution; Gas-metered sandbox | §F-13 |
| Eclipse attack | BLE Root Hash broadcast; AWDL out-of-band sync | §9.13 |
| Replay attack | HLC Epoch binding; Monotonic Counter; 48h window | §5.10.3 |
| License bypass | KDF entanglement with hardware key; O-LLVM obfuscation | §F-22 |
| Rogue admin injection | Root CA Binary Transparency; M-of-N update signing | §F-10 |
| WASM sandbox escape | CFI; Gas-metering; PoM Epidemic; Linear Memory isolation | §F-11 |
| Prompt injection (AI) | SASB AST sanitizer; EDES scanner; SSA retroactive taint | §5.31–5.36 |
| PII egress via AI | ISDM Dual-Mask; Micro-NER; BLAKE3 DLP Hash Chain | §5.23 |
| Key cloning | HSM Decrementing Monotonic Counter; Offline Ed25519 ceremony | §F-22 |
| DNS poisoning | DNS-over-HTTPS; Certificate Pinning (SPKI hash) | §5.25 |

### 9.3 Hardware-Level Cryptography Defenses

**Timing Attack:**

- 📱💻🖥️ **Constant-time Logic** via `subtle` crate — triệt tiêu `if/else` nhạy cảm dữ liệu.
- 📱💻🖥️ **Bit-masking** (AND, OR, XOR, NOT) — mọi phép tính mật mã tiêu tốn cùng CPU cycles.

**Traffic Pattern Analysis:**

- 📱💻🖥️ **Fixed-size Padding:** Mọi TCP/UDP payload đạt mức cố định (4096 bytes).
- 📱💻🖥️ **Heartbeat Dummy Traffic:** Lưu lượng đồng nhất không đứt gãy.
- ☁️📱💻🖥️ **Oblivious CAS Routing + Batch Requests** (<1KB) qua Mixnet Proxy.

**Software Leakage:**

- 📱💻🖥️ **Hardware-Accelerated Primitives:** AES-NI (Intel/AMD) / ARM NEON tập lệnh phần cứng.
- 📱💻🖥️ **Hardware Root of Trust:** Secure Enclave/TPM 2.0 chuyên trách giải nén và phong ấn E2EE keys.

**Side-Channel via Timer:**

- 📱💻🖥️ Timer Degradation: 5-10ms + Jitter để phá đo độ trễ RAM.
- 📱💻🖥️ Thread Concurrency limit; `Atomics.wait` vô hiệu nếu không khai báo trong Permission Manifest.

### 9.4 Cryptographic Architecture — AI Safety

**ISDM (Interactive SLM Dual-Masking):**

- 📱💻🖥️ SLM cục bộ "rút ruột" PII trước khi gọi LLM ngoài. Alias: `[REDACTED_PHONE_1]`, v.v.
- 📱💻🖥️ De-tokenization sau khi nhận LLM response — trên Client.
- 📱💻🖥️ `SessionVault::drop()` overwrite với `0x00` ngay sau De-tokenize.
- ☁️ Header `X-Zero-Retention: true` — ép API Provider không train model.

**SASB (Strict AST Sanitization Bridge):**

- 💻📱 `pulldown-cmark` Rust AST parsing của mọi AI response trước khi về UI.
- 💻📱 Whitelist strict: chỉ `Text, Heading, Paragraph, Code, CodeBlock, Strong, Emphasis, List, Link`.
- 💻📱 Output: `Vec<ASTNode>` Protobuf → UI renderer. Không bao giờ raw HTML string.

**EDES (Edge Deterministic Entity Scanner):**

- 📱💻 Aho-Corasick O(n) scanner. Multi-pattern 500MB/s throughput. Banned Lexicon + PII regex.
- 📱💻 Zero-copy scanning trực tiếp trên plaintext buffer ZeroizeOnDrop.

**SSA (Stateful Semantic Accumulator — Chống Salami Attack):**

- 📱💻 Sliding Context Buffer (SCB) N=20 messages, bảo vệ ZeroizeOnDrop, không persist.
- 📱💻 Lazy Triggered ONNX: chạy khi EDES flag ≥2 borderline entities trong 5 messages.
- 📱💻 Retroactive Taint: nếu `Intent_Score[SOCIAL_ENGINEERING] > 0.75` → taint N-3 messages + seal conversation.

---

## §10 FAILURE MODEL

### 10.1 Network Failures

| Failure | Detection | Recovery | Max Data Loss |
|---------|-----------|----------|---------------|
| Internet outage | Heartbeat timeout >30s | Auto-switch to Mesh Mode | None (Store-and-Forward) |
| QUIC firewall block | UDP timeout 50ms | ALPN fallback → gRPC → WSS | None (transparent) |
| TURN failover | Keepalived monitor | Floating IP switch <3s | <3s call interruption |
| AWDL unavailable (Hotspot/CarPlay) | NWPathMonitor | Tier 2 → Tier 3 (BLE) | Voice drop (30s queue) |
| Federation bridge timeout | OPA Circuit Breaker | OPEN state, fail-fast to UI | Buffered messages resent |
| Server-side split-brain | Anti-Entropy Merkle | Gossip reconciliation | None (CRDT convergence) |

### 10.2 Storage Failures

| Failure | Detection | Recovery | Max Data Loss |
|---------|-----------|----------|---------------|
| Jetsam kill NSE mid-WAL | `PRAGMA quick_check(1)` at startup | Two-Phase Commit: PENDING → re-decrypt from `nse_staging.db` | None |
| `nse_staging.db` Poison Pill | SQLite integrity check | POSIX `unlink()` + Crypto-Shredding | NSE messages in corrupted frame |
| Hard power loss during Hydration | `Hydration_Checkpoint` present at boot | Resume from last committed chunk_index | Uncommitted chunk |
| cold_state.db migration fail | Schema version mismatch | Rebuild from hot_dag.db (safety net) | None (rebuilt) |
| SQLite WAL bloat (OOM) | WAL size > threshold | `wal_autocheckpoint=1000` + BGTask Vacuum | None |
| VFS journal torn write | Shadow Paging: `cold_state_shadow.db` | POSIX atomic rename after fsync | None |

### 10.3 Key Failures

| Failure | Detection | Recovery | Impact |
|---------|-----------|----------|--------|
| DeviceIdentityKey lost | Device lost/wiped | Admin QR Key Exchange or BIP-39 Mnemonic | New key provisioned; old messages inaccessible without Escrow |
| MLS Key Desync | NSE `push_epoch` mismatch | `content-available:1` → Main App rotate → decrypt staged | Delayed notification (Foreground required) |
| Epoch Key orphan (EMDP) | Desktop reconnect | EMDP Key Escrow decrypt + DAG merge | Max 60min EMDP window messages |
| Escrow Key unrecoverable | <M shards available | Requires additional C-Level holders; else data inaccessible | Legal hold data inaccessible |
| License JWT expired | Monotonic Counter check | New JWT via email/USB | Chat/Mesh continues; AI/add-user blocked |
| Counter Rollback detected | `Counter < Server's Value` | Self-Destruct + Remote Wipe signal | Total session termination |

### 10.4 Runtime Failures

| Failure | Detection | Recovery | Impact |
|---------|-----------|----------|--------|
| WASM Gas quota exceeded | Gas-metering trap | `ZeroizeOnDrop` Linear Memory; terminate instance | .tapp unavailable |
| XPC Worker OOM (macOS) | `NSXPCConnectionInterrupted` | Journal state: PENDING → abort; user re-sign prompt | Smart Approval requires re-sign |
| iOS Jetsam kills NSE | `SIGKILL` during WAL write | Two-Phase Commit recovery | No data loss; slight delay |
| Android LMK kills process | `onTrimMemory(CRITICAL)` | ZeroizeOnDrop vector cache; WorkManager restart | ONNX indexing paused; resume |
| AES-NI not available | `is_cpu_feature_detected!("aes")` | Software fallback ChaCha20-Poly1305 | ~3x slower encryption; Admin warned |
| Argon2id memory exhaustion | Memory allocator OOM | Graceful degradation to software crypto | Performance degradation |
| BFT Dictator crash mid-merge | `election_weight` timeout | Second-highest Hash node takes over (<10ms) | Merge briefly paused |

### 10.5 Security Failures

| Failure | Detection | Response | Impact |
|---------|-----------|----------|--------|
| DMA intrusion detected | IOMMU group change monitor | `SecurityEvent::DMA_INTRUSION` → Crypto-Shred `Session_Key` + lockscreen | Session terminated |
| Jailbreak/Root detected | Remote Attestation fail | Reject + Remote Wipe trigger | Access denied |
| Binary tampered | Ed25519 signature mismatch | Silent Crash + Red Alert | App non-functional |
| CVE blacklist match | DNS TXT poll (24h) + `ATOMIC_SECURITY_LOCK` | RSOD; user cannot dismiss | Full lock until update |
| WASM exploit (PoM) | Validation Sandbox gas exceeded | Freeze socket; BLAKE3 fingerprint; Epidemic broadcast | Node blacklisted network-wide |
| Byzantine Shun false-flag | OCPM: <2 independent Proof_Bundle | Boomerang Penalty: trust score −; quarantine from Shun voting 72h | Accuser penalized |

---

## §11 VERSIONING & MIGRATION

### 11.1 Schema Migration Strategy

```rust
const CURRENT_HOT_DAG_SCHEMA_VERSION: u32 = 1;
const CURRENT_COLD_STATE_SCHEMA_VERSION: u32 = 1;

pub struct MigrationRunner {
    migrations: Vec<Box<dyn Migration>>,
}

impl MigrationRunner {
    pub fn run(&self, db: &Connection) -> Result<()> {
        let current_version: u32 = db.pragma_query_value(None, "user_version", |r| r.get(0))?;
        for migration in &self.migrations {
            if migration.version() > current_version {
                // 1. Backup: db.backup(DatabaseName::Main, &backup_path, None)?
                // 2. BEGIN EXCLUSIVE TRANSACTION
                // 3. migration.up(db)?
                // 4. PRAGMA user_version = migration.version()
                // 5. COMMIT
            }
        }
        Ok(())
    }
}
```

**Safety Net:** `cold_state.db` có thể rebuild hoàn toàn từ `hot_dag.db` bất kỳ lúc nào. Nếu migration `cold_state.db` fail → drop và rebuild.

### 11.2 Backward Compatibility Rules

| Change Type | Version Bump | Policy |
|-------------|-------------|--------|
| New CRDT event type | Minor | Existing clients ignore unknown types (`UnknownFieldSet` in Protobuf) |
| MLS epoch format change | **Major** | Full deprecation window (12 months) |
| Crypto Host ABI signature change | **Major** | Dual-support old+new for 12 months |
| Host Function API additive | Minor | No breakage; new fields ignored by old clients |
| Host Function API breaking | **Major** | `.tapp` must declare `max_host_api_version` |
| OPA Policy format | Minor (if additive) | Backward-compatible Rego rules |
| Database schema | Migration script mandatory | WAL replay backward-compatible required |

### 11.3 MLS Protocol Versioning

- 📱💻🖥️ Extension `TeraChat_App_Version` trong `KeyPackage` để đàm phán năng lực.
- 📱💻🖥️ Min-Version Roster scan → Sender Downgrade Mode nếu có device cũ.
- 📱 UI Feature Gray-out dựa trên version metadata — ngăn tạo payload không tương thích.
- PDU Adapter: tự động giáng cấp/nâng cấp schema v1/v2 trong Grace Period.

### 11.4 .tapp Host Function ABI Contract

```json
{
  "host_api_version": "1.3.0",
  "min_host_api_version": "1.0.0",
  "max_host_api_version": "2.0.0"
}
```

**Publisher Migration Guide:**

1. T-6 tháng: Thông báo trong Developer Console + Email.
2. T-3 tháng: CI/CD warning khi compile against old ABI.
3. T-0: Core support cả 2 ABI version. Old `.tapp` badge ⚠️ "Cần cập nhật".
4. T+12: Core drop support; `.tapp` cũ bị reject.

### 11.5 Database Migration — Two-Phase DB Upgrade

- 📱💻🖥️ **Dual-State Overlay:** Mở V1 DB ở `SQLITE_OPEN_READONLY`. Khởi tạo V2 DB trong <5ms. Mọi ghi đi vào V2; đọc `UNION` từ cả hai.
- 📱 **Read-Through Lazy Migration:** Khi user cuộn xem tin nhắn cũ → giải mã V1 + tái mã hóa sang V2 (JIT Migration). BGProcessingTask (iOS) / WorkManager (Android) batch 500 records khi cắm sạc.
- 📱💻 **WAL Atomic Rollback:** Mỗi batch bọc trong `BEGIN IMMEDIATE TRANSACTION` — tự rollback nếu OS kill.

---

## §12 EMERGENCY MOBILE DICTATOR PROTOCOL (EMDP)

> **Bối cảnh:** 20 nhân viên iOS trong tòa nhà bị cô lập — không có Laptop, không Android Super Node. BLAKE3 Tie-Breaker Hash Election cần ít nhất 1 node đủ năng lực làm Dictator. → Tất cả đều là Leaf Node iOS → Election loop không kết thúc → không gửi được tin nhắn.

### 12.1 EMDP State Machine

```rust
pub enum DictatorElectionMode {
    Normal,              // BLAKE3 Hash Election → Desktop/Android Super Node
    EmergencyMobileOnly, // iOS-only mesh → Tactical Relay
    SoloAppendOnly,      // 1 device, no election needed
}

pub struct TacticalRelayConfig {
    node_id: NodeId,
    mode: TacticalRelayMode, // TextOnlyForward
    ttl_minutes: u64,        // 60 minutes
}

// Selection: battery_score (battery_pct * 100) + ble_rssi_score (rssi+100)
// iOS CANNOT be full Dictator — Jetsam constraint
```

**Semantic quan trọng:** Tactical Relay ≠ Super Node:

- iOS làm Tactical Relay: **Append-Only CRDT đơn giản nhất** — store-and-forward text.
- **Không merge DAG**, **không xử lý conflict**, **không rotate MLS Epoch**.
- TTL 60 phút; auto-expire để tránh pin drain.

### 12.2 EMDP Key Escrow Handshake

```rust
pub struct EmdpKeyEscrow {
    relay_session_key: AesKey256,
    emdp_start_epoch: u64,
    emdp_expires_at: u64, // now() + 3600
}
// Desktop xuất EMDP Escrow Key trước khi offline:
// 1. Sinh EmdpKeyEscrow
// 2. ECIES encrypt với iOS device pubkey
// 3. Gửi qua BLE Control Plane
// Khi Desktop reconnect:
// 1. Nhận lại escrow từ iOS
// 2. Decrypt relay messages trong EMDP window
// 3. Merge vào DAG với đúng epoch context
// Không có orphan messages.
```

---

## §13 LICENSE ARCHITECTURE (DETAIL)

### 13.1 License JWT Structure

```json
{
  "tenant_id": "acme-corp-vn",
  "domain": "acme.terachat.io",
  "max_seats": 500,
  "tier": "enterprise",
  "valid_from": "2026-03-15T00:00:00Z",
  "valid_until": "2027-03-15T00:00:00Z",
  "max_protocol_version": "2.0",
  "offline_ttl_hours": 720,
  "air_gapped": false,
  "features": ["mesh_survival", "ai_dlp", "federation", "compliance_audit"]
}
```

Chữ ký **Ed25519** từ HSM Private Key FIPS 140-3 Level 4 — key không bao giờ rời chip.

### 13.2 License Boundary Separation (Open-Core)

```
Mã nguồn mở (AGPLv3): terachat-core/     ← Crypto, CRDT, MLS, Mesh
Mã nguồn đóng (BSL):  terachat-license-guard/ ← License validation
```

`terachat-core` gọi FFI vào `license-guard` để lấy `Feature_Flags`. Không có raw key nào đi qua FFI. Không có `license-guard.so` → Community mode (unlimited users, watermark).

### 13.3 Cryptographic Entanglement (Write-Only Pattern)

```rust
fn derive_master_unlock_key(license_token: &LicenseToken, epoch: u64) -> Result<MasterUnlockKey> {
    let device_key_material = secure_enclave::sign_derive(b"license-kdf-v1", epoch.to_le_bytes())?;
    // DeviceIdentityKey không rời chip — chỉ làm KDF input
    let kdf_input = [device_key_material, license_token.signature, &epoch.to_le_bytes()].concat();
    Ok(MasterUnlockKey(hkdf_sha256(&kdf_input, b"terachat-master-v1")))
}
// master_key dùng để mở DB — nếu license sai → key sai → DB = rác
// Không return device_key_material. Không export master_key qua FFI.
```

### 13.4 License Heartbeat Validation

| Kiểm tra | Cơ chế | Fail → |
|----------|--------|--------|
| JWT signature | Ed25519 vs bundled Root CA | Immediate lock |
| Thời hạn | `valid_until` > Monotonic Counter TPM | Immediate lock |
| Seat count | `active_device_keys` ≤ `max_seats` | Block new enrollment |
| Revocation | CRL endpoint (online) / skip (air-gapped) | Immediate lock |

### 13.5 Offline TTL Profile

```rust
pub enum OfflineTTLProfile {
    Consumer { ttl_hours: 24 },
    Enterprise { ttl_hours: u32 },      // configurable
    GovMilitary { ttl_hours: 720 },     // 30 ngày
    AirGapped { revocation_only: bool },
}
```

### 13.6 Tiered Conflict Resolution (Shadow DAG)

```
Tier 1 (Online):       Shadow DAG full → User thấy conflict, chọn merge
Tier 2 (Mesh P2P):     Lightweight Conflict Marker → Desktop Super Node mediator
Tier 3 (Solo offline): Optimistic Append → WARNING "Bản này có thể bị ghi đè"
```

Bắt buộc Conflict Resolution UI trước khi ghi với `content_type = CONTRACT | POLICY | APPROVAL`.

---

## §14 NETWORK LAYER DETAILS

### 14.1 QUIC/eBPF Scope Clarification

> ⚠️ **eBPF/XDP là server-side Linux kernel technology — KHÔNG phải client-side.**

```
Server-side (☁️🗄️): eBPF/XDP anti-DDoS — hợp lệ
Client-side:
  iOS/Android:    Network.framework QUIC native
  Desktop Linux:  seccomp-bpf (KHÔNG phải XDP)
  Windows:        Windows Filtering Platform (WFP)
```

Client không implement eBPF/XDP filtering. Client hưởng lợi từ server-side protection qua connection quality.

### 14.2 iOS WebRTC TURN — CallKit Integration

```swift
class TeraCallKitProvider: NSObject, CXProviderDelegate {
    // CXProvider giữ audio session active dù app background
    // TURN failover xảy ra trong CallKit context → không bị suspend
    // Dual TURN preconnect: khi call active + sắp vào Background,
    // Rust proactively connect tới TURN server dự phòng
}
```

### 14.3 iOS AWDL Monitor — Hotspot/CarPlay Conflict

```swift
class AWDLMonitor {
    // NWPathMonitor detect AWDL interface + bridge (hotspot/CarPlay)
    // Callback → Rust Core downgrade Tier 2 → Tier 3 (BLE only)
    // Emit UIEvent::TierChanged với message giải thích
    // Queue voice packets TTL 30s chờ AWDL phục hồi
}
```

### 14.4 XPC Transaction Journal Protocol

```rust
// hot_dag.db journal trước khi dispatch sang XPC Worker
// States: PENDING → VERIFIED → COMMITTED
// Crash in PENDING → abort + notify user "Phiên ký bị gián đoạn. Vui lòng ký lại."
// Crash in VERIFIED → commit from journal (idempotent)
```

### 14.5 AES-NI / ARM NEON — Software Fallback

```rust
pub fn init_crypto_backend() -> CryptoBackend {
    if is_cpu_feature_detected!("aes") && is_cpu_feature_detected!("sse2") {
        CryptoBackend::HardwareAccelerated
    } else {
        tracing::warn!("AES-NI not available, using software backend. Expect ~3x slower.");
        CryptoBackend::Software
    }
}
// Admin Console hiển thị warning khi thiết bị dùng software backend.
```

### 14.6 Android 14+ Battery Bucket — FCM Throttle Handling

```kotlin
// Android 14 "Restricted" bucket → FCM Data Message throttle 10/h
// → delay push E2EE 5-15 phút worst case
<uses-permission android:name="android.permission.USE_EXACT_ALARM"/>
// Companion Device Manager: REQUEST_COMPANION_RUN_IN_BACKGROUND
// FCM `high` priority message + CDM registration → bypass Doze
```

### 14.7 Shadow DB Write Lock Protocol

```rust
pub struct ShadowMigrationLock { migration_in_progress: AtomicBool }
// NSURLSession completion check lock → queue to hot_dag.db nếu migration đang chạy
// Đảm bảo không race giữa shadow rename và NSURLSession write
```

---

## §15 CHAOS ENGINEERING GATE

> Tham chiếu đến → TERA-TEST cho chi tiết đầy đủ. Đây là non-negotiable trước Gov/Military go-live.

| Scenario | Điều kiện | Expected Behavior |
|----------|-----------|-------------------|
| SC-01 | iOS AWDL off + TURN failover + CRDT merge >5000 events | AWDL warn → BLE → TURN preconnect → CRDT queue |
| SC-02 | Jetsam kill NSE mid-WAL + Desktop offline + EMDP active | WAL rollback → DAG self-heal → EMDP key escrow |
| SC-03 | XPC Worker OOM + Smart Approval pending | Journal PENDING → abort → user re-sign prompt |
| SC-04 | Battery <20% + Mesh active + Whisper loading | Whisper disabled → Voice text-fallback → BLE only |
| SC-05 | AppArmor deny memfd + mlock + seccomp active | Graceful degrade to software crypto → performance warn |
| SC-06 | License expire T+0 + Active emergency call | Chat survives → Admin Console lock only |
| SC-07 | EMDP 60min + Desktop reconnect + 1000 relay messages | Key escrow decrypt → DAG merge → epoch reconcile |

---

## §16 OBSERVABILITY

### 16.1 Signal Types

| Signal Category | Examples | Consumer |
|----------------|---------|---------|
| Security Events | `SecurityEvent::DMA_INTRUSION`, `SecurityEvent::HardwareAttestationFailed` | Admin Console, CISO Alert |
| Network State | `NetworkProtocolChanged`, `AlpnFallbackTriggered`, `MeshModeActivated` | UI HUD, Monitoring |
| Crypto Events | `MlsEpochRotated`, `MlsKeyDesync`, `WasmSandboxTerminated` | UI Badge, Audit Log |
| License Events | `LicenseStateChanged`, `LicenseHeartbeatFailed` | Admin Console |
| CRDT Events | `DagMergeCompleted`, `SplitBrainDetected`, `TombstoneVacuumed` | Internal, Monitoring |
| AI Safety | `ConversationSealed`, `EgressSchemaViolation`, `FcpTriggered` | UI Overlay, Admin Alert |

### 16.2 Metrics

| Metric | Type | Notes |
|--------|------|-------|
| `message_e2ee_latency_ms` | Histogram | Per-platform |
| `mesh_active_peers` | Gauge | Updated per Gossip round |
| `crdt_pending_buffer_size` | Gauge | Alarm if >8MB (iOS NSE) |
| `epoch_rotation_latency_ms` | Histogram | SLA <100ms |
| `dag_event_count` | Counter | Monitor growth rate |
| `wasm_execution_time_ms` | Histogram | Per .tapp DID |
| `egress_bytes_total` | Counter | Per .tapp DID; DLP alert |
| `protocol_latency_ms` | Histogram | Per protocol (QUIC/gRPC/WSS) |
| `license_heartbeat_status` | Gauge | 0=OK, 1=Warning, 2=Failed |
| `mesh_gossip_round_trip_ms` | Histogram | P99 alert >500ms |
| `file_upload_chunk_acked` | Counter | Per file_id |

### 16.3 Audit Trail

Mọi entry trong Audit Log phải có:

- `device_id` (từ `DeviceIdentityKey`)
- `timestamp` (HLC, không dùng wall clock đơn thuần)
- `payload_hash` (BLAKE3)
- `ed25519_sig` (ký bằng `Device_Key`)
- `event_type` (từ enum định nghĩa)

**Audit Log là Append-Only Immutable Hash Chain — không thể delete hoặc modify.**

Các event bắt buộc phải ghi Audit Log:

- Mọi MLS Epoch Rotation
- Mọi Escrow Key usage (kèm `legal_basis` Court Order number)
- Mọi FCP trigger (`[FCP_TRIGGERED | timestamp | BLAKE3(payload) | ed25519_sig]`)
- Mọi Remote Wipe execution
- Mọi License validation failure
- Mọi Byzantine Shun issuance
- Mọi `EgressSchemaViolation`

### 16.4 Zero-Knowledge Non-Repudiation (AI Egress)

```sql
-- Ghi trước khi bất kỳ TLS connection nào được mở
INSERT INTO ai_egress_audit (
    fcp_triggered,   -- boolean
    utc_timestamp,   -- wall clock + HLC
    payload_hash,    -- BLAKE3(raw_payload) -- KHÔNG lưu nội dung Prompt
    agent_endpoint_hash, -- BLAKE3(endpoint_url)
    device_ed25519_sig   -- ký bằng Device_Key
);
-- Không lưu nội dung Prompt. Liability shift sang phía Admin kích hoạt FCP.
```

---

## §17 APPENDIX

### 17.1 Glossary

| Thuật ngữ | Định nghĩa |
|-----------|-----------|
| `.tapp` | Gói tiện ích: `logic.wasm` + JSON Schema UI. Chạy trong WASM Sandbox trên thiết bị — không thực thi trên Server. |
| `Company_Key` | Khóa cấp Tenant, sinh khi Onboarding. Không rời thiết bị thành viên. Mã hóa mọi payload trước khi lên Cluster. |
| `Blind Relay` | Server chỉ chuyển tiếp ciphertext — không nắm key giải mã. Áp dụng cho Messaging (MLS), File (MinIO CAS), Voice (TURN). |
| `TreeKEM` | Cấu trúc cây nhị phân trong MLS, phân phối khóa nhóm O(log n). Tăng tốc sync 100× cho nhóm 5000+ user. |
| `HKMS` | Hierarchical Key Management System — Master Key → KEK → DEK. Master Key giam trong HSM/Secure Enclave. |
| `Sealed Sender` | Server biết gói tin đi đến đâu, nhưng không biết từ ai. |
| `cas_hash` | BLAKE3 của ciphertext dùng cho CAS path và dedup. Server tra hash, không tra nội dung. |
| `Crypto-Shredding` | Xóa KEK thay vì xóa dữ liệu vật lý. Ciphertext còn trên disk nhưng trở thành garbage. |
| `ZeroizeOnDrop` | RAII pattern trong Rust: `Drop` trait ghi đè `0x00` lên toàn bộ struct. Mandatory cho mọi key material. |
| `HLC` | Hybrid Logical Clock: `{wall_clock, logical_counter}`. Bảo toàn causality bất chấp clock drift. |
| `DAG` | Directed Acyclic Graph — cấu trúc dữ liệu cho CRDT Event Log. Append-only, không loop. |
| `CRDT` | Conflict-free Replicated Data Type. Delta-State CRDT cho offline sync. |
| `mPoW` | Micro-Proof-of-Work. Argon2id memory-hard challenge cho Mesh anti-spam. |
| `EMDP` | Emergency Mobile Dictator Protocol. iOS-only Mesh fallback khi không có Desktop. |
| `ISDM` | Interactive SLM Dual-Masking. PII tokenization trước khi gọi external LLM. |
| `SASB` | Strict AST Sanitization Bridge. AST-level XSS prevention cho AI response. |
| `EDES` | Edge Deterministic Entity Scanner. Aho-Corasick O(n) real-time PII scanner. |
| `SSA` | Stateful Semantic Accumulator. Sliding context buffer cho Salami Attack detection. |
| `FCP` | Full Context Passthrough. Admin-opt-in bypass của PII scrubbing cho on-premise AI. |
| `OCPM` | Objective Cryptographic Proof of Malfeasance. Hardware-bound non-repudiation cho Byzantine fault. |
| `PoM` | Proof of Malfeasance. BLAKE3 fingerprint của malicious payload; epidemic broadcast. |
| `TeraVault VFS` | Virtual File System: Content-Addressable Storage với Zero-Byte Stubs cho large files. |
| `ALPN` | Application-Layer Protocol Negotiation. QUIC → gRPC → WSS auto-negotiation. |
| `W^X` | Write XOR Execute. iOS hardware policy cấm vùng nhớ vừa ghi vừa thực thi. |
| `HPKP` | HTTP Public Key Pinning. SHA-256 hash của server TLS public key — hardcoded trong binary. |
| `VOPRF` | Verifiable Oblivious Pseudorandom Function. Blind Tokens cho anonymous rate limiting. |

### 17.2 Section Cross-Reference Map

| Topic | Primary Section | Related Sections |
|-------|----------------|-----------------|
| Key Management | §F-04 | §F-01, §9.1, §13 |
| MLS E2EE | §F-05 | §F-04, §F-06 |
| Mesh Network | §F-12 | §F-13, §F-14, §5.x |
| WASM Sandbox | §F-11 | §6.x (TERA-MKT) |
| License | §F-22 | §13, §8.4 |
| CRDT Sync | §F-14 | §5.x, §11.x |
| EMDP | §12 | §F-12, §5.1 |
| AI Safety | §9.4 | §5.22–5.37 (TERA-FEAT) |
| Failure Handling | §10 | §F-xx Security Notes |
| Observability | §16 | §12.x, §9.x |

### 17.3 Out-of-Scope References

| Topic | Tài liệu |
|-------|---------|
| Client IPC bridges, OS hooks, WASM runtime client-side | → TERA-FEAT |
| UI rendering, Glassmorphism, Animation states | → TERA-DESIGN |
| User flows, RBAC, Admin/User actions | → TERA-FUNC |
| Plugin lifecycle, ABI versioning, Publisher rules | → TERA-MKT |
| Chaos Engineering test scenarios | → TERA-TEST |
| Business model, pricing, GTM | → TERA-BIZ |

---

*Xem → TERA-FEAT cho Client App-layer. Xem → TERA-FUNC cho Product flows.*
