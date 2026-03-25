# Core_Spec.md — TeraChat Alpha v0.3.0

```yaml
# DOCUMENT IDENTITY
id:                   "TERA-CORE"
title:                "TeraChat — Core Technical Specification"
version:              "3.1"
audience:             "System Architect, Backend Engineer, Security Engineer"
purpose:              "Đặc tả kiến trúc lõi hệ thống: Cryptography (MLS, E2EE), Mesh Network, Offline CRDT Sync, Server Infrastructure, AI Hybrid Edge-Cloud."
scope:                "Infrastructure, Security, Cryptography, Network Protocols, AI Enclave — Implementation-level only."
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
  - "AI worker process cô lập với Rust Core — crash AI không ảnh hưởng messaging"
  - "VPS Enclave là stateless: không log, không DB cache, RAM bị xóa sau phiên"
constraints_global:
  - "ZeroizeOnDrop bắt buộc cho mọi struct giữ key material"
  - "Không mlock() trên iOS — dùng kCFAllocatorMallocZone + ZeroizeOnDrop"
  - "Mọi FFI endpoint KHÔNG trả raw ptr — dùng Token Protocol"
  - "Ed25519 signed, append-only Audit Log — không thể delete/modify"
  - "VPS Enclave KHÔNG lưu plaintext prompt/response — in-memory only, ZeroizeOnDrop"
  - "SanitizedPrompt là newtype — không thể tạo nếu không qua PII redaction pass"
breaking_changes_policy: |
  Major version bump bắt buộc khi thay đổi: MLS epoch format, CRDT schema,
  Crypto Host ABI, Host Function API, AI Enclave Protocol. Minor version = additive only.
  Deprecation window: 12 tháng. Xem §11 Versioning & Migration.

ai_routing_hint: |
  Mở file này khi hỏi về Crypto, bảo mật, MLS, E2EE, Mesh network,
  CRDT sync, server infra, key management, AI Hybrid architecture,
  VPS Enclave, BYOM, Blind RAG, Semantic Cache, hoặc attack surface analysis.
```

> **Status:** `ACTIVE — Implementation Reference`
> **Audience:** Backend Engineer · DevOps · Security / Cryptography Engineer
> **Last Updated:** 2026-03-25
> **Depends On:** *(root spec — no external deps)*
> **Consumed By:** → TERA-FEAT · → TERA-DESIGN · → TERA-MKT

---

## CHANGELOG

| Version | Date       | Change Summary                                                                                    |
|---------|------------|---------------------------------------------------------------------------------------------------|
| v3.1    | 2026-03-25 | Add §F-23 AI Hybrid Edge-Cloud Architecture (BYOM, VPS Enclave, E2EE Prompt Tunneling, Blind RAG, Semantic Caching); Add §18 AI Enclave Infrastructure; Update §9.4 AI Safety với Blind RAG threat model; Update §5.3 CRDT với AI event types; Update §3.6 License với AI tier |
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
- [ ] VPS Enclave **phải** stateless: không ghi log prompt/response, không persist KV cache, RAM ZeroizeOnDrop sau mỗi phiên.
- [ ] `SanitizedPrompt` newtype **phải** đi qua Micro-NER PII redaction trước khi rời thiết bị — raw string forbidden.
- [ ] BYOM model **phải** pass `OnnxModelLoader.load_verified()` hoặc tương đương trước khi được load vào Enclave.

---

## §1 EXECUTIVE SUMMARY

### 1.1 Mục tiêu hệ thống

TeraChat là nền tảng nhắn tin doanh nghiệp **Zero-Knowledge, End-to-End Encrypted** với khả năng sinh tồn offline và AI Hybrid Edge-Cloud. Lõi hệ thống (Rust Core) nắm giữ toàn bộ mật mã học, state sync và mesh networking — UI chỉ là pure renderer. AI pipeline tích hợp BYOM và VPS Enclave stateless để đảm bảo không có plaintext prompt nào tồn tại trên server.

**3 đảm bảo cốt lõi:**

1. Server không thể đọc nội dung — *ciphertext-only relay*.
2. Mesh P2P duy trì liên lạc khi mất Internet hoàn toàn.
3. Mọi key material và AI prompt tự hủy ngay khi scope kết thúc — *ZeroizeOnDrop everywhere*.

### 1.2 Tính năng chiến lược

| Feature | Mô tả | Section |
|---------|-------|---------|
| MLS E2EE (RFC 9420) | TreeKEM O(log n) cho 5000+ users, Forward Secrecy tự động | §4.2 |
| Survival Mesh | BLE 5.0 + Wi-Fi Direct P2P, Store-and-Forward CRDT | §5.2 |
| Zero-Knowledge Server | Blind Relay, Sealed Sender, Oblivious CAS Routing | §2.2 |
| WASM Sandbox (.tapp) | Capability-based isolation, Crypto Host ABI offloading | §5.18 |
| Hybrid PQ-KEM | X25519 + ML-KEM-768, CNSA 2.0 compliant | §4.4 |
| HKMS Key Hierarchy | HSM FIPS 140-3 → KEK → DEK, Shamir 3-of-5 recovery | §4.1 |
| **AI Hybrid Edge-Cloud** | **BYOM + VPS Enclave stateless + Blind RAG + Semantic Cache** | **§F-23** |

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
│                              │         ▲                       ││
│  ┌──────────────┐            │  AI Worker Process (isolated)   ││
│  │ AI Worker    │◄──IPC/Pipe►│  Local: CoreML/ONNX             ││
│  │  Process     │            │  Remote: E2EE Prompt Tunnel→VPS ││
│  └──────────────┘            └─────────────────────────────────┘│
└──────────────────────────────┴─────────────────────────────────┘
          │ TLS 1.3 + mTLS                  │ BLE/Wi-Fi Direct
          ▼                                 ▼
┌─────────────────────┐          ┌─────────────────────┐
│   BLIND RELAY VPS   │          │    PEER DEVICES      │
│  (Ciphertext only)  │          │  (Survival Mesh P2P) │
│  PostgreSQL · Redis │          │  Store-and-Forward   │
│  MinIO CAS · NATS   │          │  CRDT Gossip         │
├─────────────────────┤          └─────────────────────┘
│  VPS ENCLAVE CLUSTER│
│  (AI Inference)     │
│  Stateless · No Log │
│  E2EE Prompt In-RAM │
│  Semantic Cache     │
│  Blind RAG VectorDB │
└─────────────────────┘
```

### 1.4 Trust Boundaries

| Boundary | Bên trong tin tưởng | Bên ngoài không tin tưởng |
|----------|---------------------|---------------------------|
| Secure Enclave / StrongBox / TPM | Private key ops | RAM, OS, Admin |
| Rust Core | Crypto logic, State | UI layer, WASM sandbox |
| AI Worker Process | Local inference only | Raw prompt, key material |
| VPS Enclave | In-RAM decryption only | Plaintext persisted anywhere |
| WASM Sandbox | .tapp business logic | Host network, filesystem |
| Blind Relay VPS | Routing ciphertext | Plaintext content |
| Mesh Peer | Relaying signed packets | Unsigned/unverified data |

---

## §2 SYSTEM OVERVIEW

### 2.1 Shared Core Philosophy — Lõi Rust Độc Tài

- ☁️📱💻🖥️ **Lõi Rust (TeraChat Core)** nắm giữ 100% sinh mệnh: MLS E2EE, SQLCipher I/O, P2P Mesh, CRDT Sync. Biên dịch ra native binary cho mọi platform.
- 📱💻🖥️ **Tầng UI (Flutter / Tauri):** Pure Renderer — cấm tuyệt đối port Crypto/Business Logic lên Dart/JS Thread.
- 📱💻🖥️ **AI Worker Process:** Tiến trình OS riêng biệt — crash AI không kéo Rust Core sập. Giao tiếp qua Anonymous Pipe (local) hoặc E2EE mTLS Tunnel (VPS Enclave).
- 📱💻🖥️ **IPC — Tách Control/Data Plane:**
  - *Control Plane:* Protobuf qua FFI/JSI — lệnh nhỏ <1KB.
  - *Data Plane:* Dart FFI TypedData (Mobile) / `SharedArrayBuffer` (Desktop) — Zero-Copy, throughput ~400–500MB/s.
- 📱💻🖥️ **Unidirectional State Sync:** Rust bắn signal `StateChanged(table, version)` qua IPC. UI kéo snapshot tại thời điểm rảnh — không polling, không push JSON cục.

### 2.2 Blind Routing & Zero-Knowledge

- ☁️ Server là **Blind Relay** — chỉ thấy: `destination_device_id`, `blob_size`, `timestamp`.
- ☁️ **Sealed Sender:** Header người gửi mã hóa bằng public key người nhận — Server không biết who-to-whom.
- ☁️ **Oblivious CAS Routing:** Batch 4–10 `Fake_CAS_Hashes` khi gửi hash query (Chaffing). Tra qua Mixnet Proxy Endpoint, không đính `User_ID`.
- 🗄️☁️ **MinIO Blind Storage:** Lưu file theo `cas_hash` path — không biết tên file thực.
- ☁️ **VPS Enclave Zero-Knowledge AI:** Prompt được mã hóa bởi client trước khi gửi lên Enclave. Enclave giải mã trong RAM, inference, trả kết quả mã hóa về. Không ghi log, không persist plaintext bất kỳ ở đâu.

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
         ├──> [Zone 1B: VPS Cluster — Vultr / DigitalOcean / Linode]
         │      ├─ Single-Binary Rust Daemon (Relay)
         │      ├─ Local SSD Storage
         │      └─ HA TURN Array (WebRTC Relay, Floating IP)
         └──> [Zone 3: AI Enclave Cluster]
                ├─ Load Balancer (HAProxy/Nginx) — distributes AI requests
                ├─ N × Inference Nodes (vLLM + Continuous Batching)
                ├─ Semantic Cache Layer (Redis-compatible, encrypted keys)
                ├─ Blind RAG VectorDB (Qdrant/Weaviate — vector only, no plaintext)
                └─ BYOM Registry (Ed25519-signed model manifests)
```

| Quy mô    | Topology                                     | Storage                                      |
|-----------|----------------------------------------------|----------------------------------------------|
| 10k Users | Single-Node Rust Relay + 1 AI Enclave Node   | Local SSD                                    |
| 100k Users| Geo-Federated Clusters + AI Enclave HA       | PostgreSQL Geo-Partitioning + HA TURN Array  |
| 1M+ Users | Multi-Cloud Active-Active + AI Enclave Multi-Zone | Data Mule + NTN Satellite routing       |

### 2.4 Dynamic Micro-Core Loading (Platform-Aware)

- 📱💻 Dynamic Library Loading (DLL/dylib) điều phối nạp/rút các phân hệ theo ngữ cảnh.
- 📱💻 JIT Micro-Core nhằm ép dung lượng RAM thường trực xuống mức tối thiểu.
- 📱💻🖥️ Kyber768 Post-Quantum engine cho kỷ nguyên Shor Algorithm (xem §4.4).

---

## §3 DATA MODEL

> **Catalog đầy đủ mọi đối tượng dữ liệu trong hệ thống.** Các algorithm (§4–§5) chỉ là *operations* tác động lên những objects này.

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
| **`AI_Session_Key`** | **AES-256-GCM Ephemeral** | **RAM (AI Worker Process)** | **Per AI inference session; ZeroizeOnDrop after response** | **Không rời AI Worker Process; không persist** | **§F-23** |
| **`EnclaveAttestation_Token`** | **Signed JWT (Ed25519)** | **RAM; validated on each request** | **TTL 60s; re-issued per session** | **Signed by DeviceIdentityKey; Enclave verifies before decrypt** | **§F-23** |

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

### 3.7 Domain: AI Hybrid Objects *(NEW — §F-23)*

| Object | Type | Storage | Lifecycle | Security Constraint | Ref |
|--------|------|---------|-----------|--------------------|----|
| `SanitizedPrompt` | Newtype wrapping `String` | RAM (AI Worker Process) | Per inference call; ZeroizeOnDrop after send | Không thể tạo nếu không qua Micro-NER pass | §F-23.3 |
| `EncryptedPromptBundle` | `{ciphertext: Vec<u8>, nonce: [u8;12], session_key_id: u64}` | In-flight only | Tồn tại trong transit; never stored anywhere | AES-256-GCM với `AI_Session_Key` | §F-23.4 |
| `EnclaveResponseBundle` | `{ciphertext: Vec<u8>, nonce: [u8;12], request_id: Uuid}` | In-flight only | Tồn tại trong transit; decrypted in AI Worker RAM | AES-256-GCM; ZeroizeOnDrop after de-alias | §F-23.4 |
| `SemanticCacheKey` | `BLAKE3(normalized_prompt_embedding[0:16])` | Enclave Redis-compatible cache | TTL 30 min; keyed by semantic hash not plaintext | Server không bao giờ thấy plaintext; chỉ thấy hash | §F-23.6 |
| `BlindVector` | `[f32; 384]` embedding | Enclave VectorDB (Qdrant) | Per document chunk; no plaintext stored alongside | Vector chỉ; ciphertext chunk lưu ở MinIO Blind Storage | §F-23.5 |
| `ChunkCiphertext` | `AES-256-GCM(chunk_plaintext)` | MinIO Blind Storage | Permanent until user delete | Key (`ChunkKey`) chỉ tồn tại ở client | §F-23.5 |
| `ModelManifest` | `{model_id, blake3_hash, publisher_key, min_vram_gb, tier}` | Enclave BYOM Registry | Per model version | Ed25519 signed by publisher + TeraChat CA counter-sign | §F-23.2 |
| `InferenceSessionVault` | `{alias_map: HashMap<String,String>}` | AI Worker RAM | Per inference call; ZeroizeOnDrop < 100ms after response | Alias map `[MASK_01] → real@email.com`; never leaves AI Worker | §F-23.3 |

---

## §4 FEATURE MODEL

> Mỗi feature được đặc tả đầy đủ: description, platforms, dependencies, data interactions, state machine (nếu có), observability, security notes.

---

### F-01: Hardware Root of Trust & Anti-Extraction

**Description:** Private key sinh và tồn tại vĩnh viễn trong chip bảo mật vật lý. Mọi ký/giải mã thực hiện trong enclave — key không bao giờ rời chip.

**Supported Platforms:** 📱 iOS (Secure Enclave), 📱 Android (StrongBox Keymaster), 💻🖥️ Desktop (TPM 2.0), 🗄️ Server (HSM PKCS#11)

**Dependencies:** Biometric API (FaceID/TouchID/NNAPI), OS Keychain/Keystore

**Data Interaction:** Tạo → `DeviceIdentityKey`, `Company_Key` (wrapped). Consume → ký `OIDC_ID_Token`, `Audit_Log_Entry`, `License_JWT` verification, `EnclaveAttestation_Token`.

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
                          └──> [AI_Session_Key]  ← ephemeral, per AI session
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
- `AI_Session_Key` được derive từ `Epoch_Key` và `AI_session_nonce`; không lưu, không rời AI Worker Process

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
AI_Session_Key    = HKDF(Final_Session_Key, "ai-session-v1" || ai_session_nonce)
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
| **AI Enclave Cluster** | Stateless inference nodes — xem §F-23 và §18. |

#### Database Layer

**PostgreSQL HA (Relay-Side Only — Enterprise+ / Gov/Military):**

> **Clarification:** PostgreSQL chỉ sử dụng cho relay server (store-and-forward metadata, user directory). Client-side hoàn toàn dùng SQLite encrypted. Deployment Business/Enterprise tier KHÔNG yêu cầu PostgreSQL.

- ☁️🗄️ pgRepmgr + PgPool — Failover tự động, streaming replication.
- ☁️🗄️ Geo-Partitioning cho quy mô 100k+ user.

**MinIO Blind Storage:**

- ☁️🗄️ **Erasure Coding (EC+4):** Sharding 3–5 Nodes. 1 Node sập → tự phục hồi.
- ☁️ Lưu file theo `cas_hash` path (CAS). Server không biết tên file thực.
- ☁️ **Zero-Byte Stub:** Client nhận Stub <5KB (`file_name`, `cas_hash`, `encrypted_thumbnail`, `storage_ref`). File thực tải khi user yêu cầu.

**SQLite OOM Prevention (VPS Resource Constraints):**

- ☁️ **Micro-batching DB Lock Yielding:** Chunk ghi WAL thành các batch. Rust yield khóa DB sau mỗi 1000 hàng.
- ☁️ **Zero-Copy Atomic Rename:** `renameat2()` với `RENAME_WHITEOUT` để trao tệp vfs-journal — giảm 90% áp lực RAM.
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

---

### F-10: Update Security & Binary Transparency

**Description:** Bảo vệ toàn vẹn binary update, chống downgrade attack và rogue admin injection.

**Supported Platforms:** 📱💻🖥️

**Key Mechanisms:**

- 📱💻🖥️ **Root CA Binary Transparency:** Mọi build (Native App, Rust Core, `.tapp`, BYOM Models) ký bằng **TeraChat Root CA Key** từ hầm lạnh offline.
- 📱💻🖥️ **Ed25519 Signature Verification:** Client hard-code Public Key của TeraChat. Update từ VPS bắt buộc kiểm tra chữ ký trước khi thực thi.
- 📱💻🖥️ **Anti-Rollback Monotonic Counter:** `Version_Sequence` trong build header.
- 📱💻🖥️ **Global CVE Heartbeat via DNS TXT (DoH):** Tra cứu `security.terachat.com` mỗi 24h qua DNS-over-HTTPS.
- 📱💻🖥️ **Atomic IPC Security Lock & RSOD:** `ATOMIC_SECURITY_LOCK` khóa toàn bộ IPC Data Plane khi CVE Blacklist match → Red Screen of Death → Zeroize RAM.

**Update Distribution:**

- 📱 **Mobile (Signal-Only):** VPS phát cờ lệnh bắt buộc. App → Khóa UI → Nút đến App Store / CH Play.
- 💻🖥️ **Desktop (LAN P2P):** VPS "mồi" 10 Super Nodes. Desktop dùng Survival Mesh phân phối Binary cho phần còn lại.

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

- ☁️ **Wasmtime Cranelift JIT Isolation:** "Soft-Enclave" cô lập xử lý khóa trong WASM Sandbox.
- ☁️ **ChaCha8 Ephemeral Key Scrambling:** CSPRNG XOR liên tục vùng RAM chứa khóa.
- ☁️ **RAII ZeroizeOnDrop:** Tiêu hủy dữ liệu ngay khi biến rời scope.

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

- 📱 **iOS — `MultipeerConnectivityAdapter`:** `MeshTransport` implemented bằng Apple MultipeerConnectivity (MCSession). Dùng BLE + AWDL (~200 Mbps).
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
- 📱 Sau DAG merge bởi Desktop Dictator, Rust xuất **Materialized Snapshot** và phân phát về Mobile Leaf Nodes.

**EMDP — Emergency Mobile Dictator Protocol:** Xem chi tiết §12.

**Energy Optimization:**

- 📱 **BLE Duty-Cycle:** 200ms Advertising/Scanning + 800ms Sleep → giảm 80% power.
- 📱 **iBeacon Stealth Mode:** CoreLocation iBeacon Ranging để duy trì BLE background scan.
- 📱 **OS Native Path Monitor:** `NWPathMonitor` (iOS) / `ConnectivityManager` (Android) để phát hiện mạng.

**Gossip Protocol & Broadcast:**

- 📱💻🖥️ **Store-and-Forward Gossip (Text):** Tin nhắn CRDT (<1KB) E2EE truyền multi-hop qua Router trung gian.
- 📱💻🖥️ **Direct-Link Only (File/Video):** File nặng bắt buộc P2P Wi-Fi Aware khép kín khi 2 máy trong phạm vi <20m.
- 📱💻 **Gossip Rate Limiting + zstd compression:** Giảm gói tin dư thừa trên BLE.

**Offline PKI Defense:**

- **Offline TTL:** App đóng băng Session nếu mất Server > TTL (theo `OfflineTTLProfile`).
- **Gossip CRL:** 1 node bắt Internet → tải CRL delta → ký Enterprise CA → Gossip BLE sang toàn Mesh ~30s.
- **Replay Protection:** Monotonic Version Counter + CA Signature + Timestamp Window (48h).

**AWDL Monitor — Hotspot/CarPlay Conflict:**

- 📱 Khi Hotspot active hoặc CarPlay → iOS tắt AWDL → Rust downgrade Tier 2 → Tier 3 (BLE only).
- 📱 Emit `UIEvent::TierChanged`: *"Hotspot đang bật — Mesh chuyển sang BLE. Voice tạm không khả dụng."*
- 📱 Queue voice packets TTL 30s. Sau 30s không phục hồi → drop voice.

**iOS Mesh Graceful Super Node Handover:**

- 📱 iOS detect memory pressure sắp trigger Jetsam → broadcast `MeshRoleHandover(candidate_node_id)` qua BLE trước khi bị kill.

**Observability:**

- Signal: `MeshModeActivated`, `MeshRoleChanged(old_role, new_role)`, `MeshPeerJoined(node_id)`, `MeshPeerShunned(node_id)`
- Metric: `mesh_active_peers`, `mesh_gossip_round_trip_ms`, `mesh_stored_bytes`

---

### F-13: Mesh Anti-Spam, DoS Resilience & Byzantine Fault Tolerance

**Description:** Chống Sybil attack, Byzantine quarantine, PoM epidemic broadcast, và OCPM.

**Supported Platforms:** 📱💻🖥️

**Micro-Proof-of-Work Defense:**

- 📱💻🖥️ SHA-256 Hashcash: 12-bit prefix challenge trước khi phát sóng tín hiệu.
- 📱 **Argon2id Adaptive (Nâng cấp):** `m=1MB, t=2, p=1` — ~50ms/challenge. Emergency SOS = 0ms (miễn phí).
- 📱 **Thermal Throttling Feedback:** iOS `ProcessInfo.thermalState` / Android `ThermalStatus` → tăng `t` khi thiết bị nóng.
- 💻📱 **Rate-limiting Ring Buffer:** 32-entry per `Node_ID`.

**Byzantine Quarantine & Gossip Poison Pill:**

- ☁️📱 Phát hiện vi phạm → **Poison Pill packet** → lan truyền `SHUN: Node_ID` toàn Mesh ~30s.
- 💻📱 Thêm vào Local Denylist (SQLite WAL Append-Only).
- ☁️📱 Xác thực CA signature trên Poison Pill trước khi áp dụng.

**OCPM (Objective Cryptographic Proof of Malfeasance):**

- 📱 Hardware-bound Non-repudiation: vi phạm ký ngay bằng `Device_Key` trong Secure Enclave.
- 💻📱 `Proof_Bundle = {raw_packet_bytes, timestamp_HLC, Node_ID, Ed25519_sig}`.
- 💻📱 Immutable Evidence: SQLite WAL với cờ `READ_ONLY` ngay sau ghi.
- 💻📱 Multi-party Attribution: yêu cầu ≥2 `Proof_Bundle` độc lập.

**HLC-Epoch Temporal Binding (Chống Replay):**

- 💻📱 `|hlc_now - hlc_packet| < DRIFT_THRESHOLD (5s)` — quá ngưỡng → `TEMPORAL_VIOLATION`, drop.
- ☁️📱 Proof_Bundle bound với MLS Epoch hiện tại.
- 💻📱 24h Temporal Validation Window: Bloom Filter lưu `Evidence_Hash`.

**Gas-Metered Ephemeral Quarantine & PoM Epidemic:**

- 📱💻🖥️ **CFI + OLLVM Obfuscation:** Rust biên dịch với CFI.
- 📱💻🖥️ **Gas-Metered Validation Sandbox:** Delta-State từ ngoài "detonated" trong WASM partition dùng một lần.
- 📱🖥️ **PoM Epidemic Broadcast:** Ngay khi phát hiện exploit → đóng băng socket → BLAKE3 fingerprint → phát tán.

**Fixed-Size Relay Ring Buffer:**

- 📱💻🖥️ Static Ring Buffer trên Shared Memory giới hạn RAM chứa tin relay.
- 📱💻🖥️ OPA Engine quy chiếu Rate Limiting theo tín nhiệm user.

---

### F-14: CRDT Sync & DAG State Management

**Description:** Offline-first append-only DAG với Hybrid Logical Clocks, deterministic convergence, split-brain recovery.

**Supported Platforms:** 📱💻🖥️☁️

**Core Properties:**

- 📱💻🖥️ **Hybrid Logical Clocks (HLC):** Mọi event dùng `(Lamport_Counter, Node_ID, Wall_Clock_HLC)`. Không dùng `SystemTime::now()` cho ordering.
- 📱💻🖥️ **Delta-State CRDT Pending Buffer:** Event out-of-order thiếu gốc → `Pending_RAM_Buffer`.
- 📱💻🖥️ **Deterministic LWW:** `Hash(Node_ID)` Tie-breaker + HLC cho Last-Write-Wins conflicts.
- 📱💻🖥️ **Ed25519 Signed Merge Patches:** Mọi state change phải kèm chữ ký Ed25519.

**Tombstone & GC:**

- 💻📱🖥️ **Merged_Vector_Clock (MVC):** Tombstone chỉ Vacuum khi `tombstone.clock ≤ MVC`.
- 📱 **Zero-Byte Stub Transformation:** Sau Vacuum, Tombstone chuyển thành `(entity_id, hlc, type=DELETED)`.
- 📱💻 **GC dựa trên Mesh ACK:** Chỉ GC sau khi ≥M peer ACK hoặc global sync.
- 📱💻🖥️ **7-Day Hot DAG Eviction:** `hot_dag.db` giữ 7 ngày gần nhất. GC scheduler 24h (background + sạc).

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
  └─ Mobile Only → Android (RAM cao nhất) = Temp Dictator
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

**Append-Only Immutable Hash Chain:**

- 📱💻🖥️ Mọi sự kiện là mắt xích trong Hash Chain một chiều — cấm rollback.
- 📱💻🖥️ Sự kiện bị xóa → Tombstone Stub móc vào DAG, không xóa vật lý.
- 📱💻🖥️ Byzantine Fault Tolerance: Mọi mắt xích xác thực Ed25519.

**Deterministic State Reconciliation (Post-Crypto-Shredding):**

- 📱 `Hydration_Checkpoint`: extract `{Snapshot_CAS_UUID, vector_clock_frontier}`.
- 📱☁️ `GossipStateRequest` siêu nhẹ (<2KB Vector Clock Summary) đến Super Nodes.
- ☁️ Server: set difference `(current_frontier) \ (client_known)` → chỉ gửi Delta thiếu.

**Observability:**

- Signal: `DagMergeCompleted(epoch_n)`, `SplitBrainDetected`, `TombstoneVacuumed(count)`
- Metric: `dag_event_count`, `crdt_pending_buffer_size`, `merge_latency_ms`

---

### F-15: Network Communication Protocols

**Description:** WebSocket E2EE Relay, WebRTC TURN, QUIC/gRPC/WSS multiplexing, push notifications.

**Supported Platforms:** 📱💻🖥️☁️

#### Real-time Messaging

- ☁️ Server relay ciphertext blob — không giải mã. Rate Limiting (Redis ZSET Sliding Window).

#### WebRTC Blind Relay (TURN)

- 📱💻🖥️ **Signaling:** Trao đổi SDP qua kênh chat MLS (E2EE channel).
- ☁️ **Transport:** SRTP — E2EE Audio/Video. TURN Server chỉ relay UDP mã hóa.
- ☁️ **HA:** Keepalived Floating IP, failover 3 giây. Sizing: 1 Node ~ 50 HD streams, 4 vCPUs, 8GB RAM, 1 Gbps.
- 📱 **CallKit Integration (iOS):** iOS treat TeraChat calls như native calls → không bị background kill.
- 📱 **Dual TURN Preconnect:** Khi app sắp vào Background, Rust proactively connect tới TURN dự phòng.

#### Application-Layer Priority Multiplexing (Chống HoLB)

- 📱💻🖥️ **P0/P1/P2 Priority Queue:** P0 = Key Updates, Ed25519 Sigs, BFT Consensus; P1 = Text messages, CRDT Delta; P2 = File transfer chunks, DB Hydration.
- ☁️ **Micro-Chunk Interleaving (64KB):** Sau mỗi 64KB file chunk, scheduler check P0/P1 queue.
- 🗄️ **BLAKE3 Segmented Merkle Tree:** Mỗi 64KB chunk có BLAKE3 hash riêng trong Merkle Tree.

#### E2EE Push — iOS (NSE)

- 📱 `UNNotificationServiceExtension` + `mutable-content: 1`.
- 📱 **NSE Micro-Crypto Build Target:** ~4MB (stripped MLS/CRDT/SQLCipher). Chỉ AES-256-GCM decrypt + Shared Keychain read.
- 📱 **Push Payload ≤ 4KB:** `chat_id`, `sender_display`, `preview_ct` (AES-256-GCM), `has_attachment`, `push_epoch`.

#### E2EE Push — Android & Huawei

- 📱 **Android:** FCM Data Message → `FirebaseMessagingService` → giải mã Rust FFI.
- 📱 **Huawei:** HMS Push Kit (HPK). CRL refresh tối đa 4h delay.

#### Desktop Background Daemon

- 💻🖥️ **`terachat-daemon`** ~4.5MB RAM — tách biệt khỏi Tauri UI.
- 💻 Windows Service / macOS `launchd` LaunchAgent / 🖥️ Linux `systemd` user service.

**Linux Multi-Init Support:**

- 🐧 Init detection: systemd / openrc / runit / s6 / launchd → generate correct service file.

---

### F-16: Large File Transfer & Streaming

**Description:** Zero-RAM streaming chunker cho file 10GB+, BLAKE3 Segmented Merkle, S3 Multipart, iOS Background delegation.

**Supported Platforms:** 📱💻🖥️☁️🗄️

**Streaming Chunker — Zero RAM Overhead:**

- 📱💻🖥️ **Hard Chunk Size = 2MB:** `pread(fd, buf, 2MB, offset)`. RAM max tại mọi thời điểm: ~10MB (Double Buffer).
- 📱💻🖥️ **mmap + ZeroizeOnDrop Pipeline:** Mỗi chunk mmap vào RAM bảo vệ bởi ZeroizeOnDrop.
- 📱💻🖥️ **Chunk-Level Key Derivation:** `Chunk_Key = HKDF(Session_Key, File_ID || Chunk_Index || Byte_Offset)`.

**BLAKE3 Segmented Merkle Tree:**

- 📱💻🖥️ `Leaf_Hash = BLAKE3(Ciphertext_Chunk || Chunk_Key || Chunk_Index)` → tổng hợp thành `Merkle_Root_Hash`.
- 📱💻🖥️ Client nhận `Merkle_Root_Hash` từ Control Plane TRƯỚC khi nhận payload.
- 📱💻🖥️ **Fault Tolerance:** Đứt mạng ở chunk 4999/5000 → chỉ re-upload 2MB đó.

**S3 Multipart Upload:**

- ☁️🗄️ **Salted MLE via MinIO S3 Multipart:** Mỗi Part = 1 Chunk ciphertext.
- ☁️🗄️ Throughput: 300–500MB/s.

**iOS Background Delegation:**

- 📱 **Pre-signed URL Per Chunk:** TTL 15 phút, HMAC-SHA256 bound to device. Bàn giao cho `NSURLSession Background Transfer`.
- 📱 **Android WorkManager:** `[Encrypt_Chunk → S3_Upload_Chunk → ZeroizeOnDrop]` per chunk.

---

### F-17: API Secret Management

**Description:** E2EE Vault cho API Keys, Cryptographic Binding bot-to-key, Instant Revoke.

**Supported Platforms:** ☁️🗄️📱💻🖥️

**Key Mechanisms:**

- ☁️🗄️ **Blind Vault Storage:** Admin nhập `{name, value}` → Rust sinh `Vault_Key (AES-256)` → `encrypted_blob = AES-256-GCM(Vault_Key, api_key)` → VPS.
- 📱💻🖥️ **Cryptographic Bot Binding:** Admin bấm [+] cấp key cho Bot → Client giải mã trong RAM (<100ms) → ECIES encrypt với Bot_Public_Key.
- ☁️ **Instant Revoke:** Admin đổi key gốc → `rebind_all_bots()` mã hóa lại toàn bộ `Bot_Bound_Blob` trong <2 giây.
- ☁️🗄️ **BYOK:** API Key lưu trong Secure Enclave / OS Keychain.

---

### F-18: Federation Bridge

**Description:** Cross-cluster communication qua mTLS, Sealed Sender, OPA Policy, circuit breaker.

**Supported Platforms:** ☁️

**Key Mechanisms:**

- ☁️ **mTLS Mutual Auth (PKI nội bộ):** Không dùng CA công cộng.
- ☁️ **Signed JWT Federation_Invite_Token:** Keycloak/Dex xác thực lời mời.
- ☁️ **Federation Trust Registry:** Public Key các Cluster liên kết trong sổ cái PKI nội bộ.
- ☁️ **Sealed Sender Protocol:** Header người gửi mã hóa bằng Public Key người nhận.
- ☁️ **OPA ABAC tại API Gateway:** `sender_role` + `allow_reply` lọc gói tin liên cụm.
- ☁️ **Circuit Breaker:** Khi tin nhắn liên cụm vượt ngưỡng → OPEN fail-fast về UI trong <1s.
- ☁️ **Z3 Formal Verification:** OPA Policy liên cụm qua SMT Model → Z3 Solver trước khi deploy.

---

### F-19: E2EE Cloud Backup & Identity Restore

**Description:** Zero-Knowledge cloud backup, biometric-backed restore, BIP-39 recovery phrase.

**Supported Platforms:** ☁️🗄️📱💻

**Key Mechanisms:**

- ☁️🗄️ **E2EE Cloud Backup (Zero-Knowledge):** Lõi Rust mã hóa `cold_state.db` bằng `Device_Key` trước khi push lên Cloud.
- 📱💻 **Biometric-backed Restore:** Thiết bị mới xác thực FaceID/TouchID hoặc TPM 2.0. Lõi Rust tải Ciphertext về, giải mã local.
- 📱💻 **Recovery Phrase (BIP-39 Mnemonic):** 24-word Mnemonic phát sinh khi thiết lập lần đầu.

---

### F-20: Zero-Access Diagnostics (TeraDiag)

**Description:** Thu thập log chẩn đoán trong WASM Sandbox cô lập mà không tiếp xúc dữ liệu tin nhắn.

**Supported Platforms:** 📱💻☁️

**Key Mechanisms:**

- 📱 **WASM Sandbox (ReadOnly Partition):** TeraDiag chỉ có `PROT_READ` đối với phân vùng `diag_logs`.
- 📱 **XChaCha20-Poly1305 Pipeline:** Log mã hóa stream-based trước khi đồng bộ.
- 📱 **Wi-Fi Direct (Log Sync over Mesh):** P2P tức thì khi mất Internet.
- ☁️ **OPA Block Egress:** App ID `com.terachat.diag` — Egress Blocked ra Internet; chỉ Mesh nội bộ.
- 🗄️ **128MB RAM Cap + Deterministic Chunking.**
- ⭐ **Publisher Trust Tier 1 (TeraChat HQ Sign).**

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
| TEE | StrongBox | TrustZone (ARM) |
| WASM | wasmtime JIT | wasmtime JIT |
| Distribution | Google Play | AppGallery |

**Formal IPC Memory Ownership Contract (Token Protocol):**

```rust
extern "C" {
    fn tera_buf_acquire(id: u64) -> u64;
    fn tera_buf_release(token: u64);
}
```

**iOS Key Protection — Double-Buffer Zeroize Protocol:**

```
1. Phân bổ key vào 2 page liền kề MAP_ANONYMOUS|MAP_PRIVATE
2. Ngay sau decrypt: ghi đè 0x00 vào page 1 TRƯỚC KHI dùng key
3. Dùng key từ page 2
4. Sau ZeroizeOnDrop: ghi đè cả 2 page
```

---

### F-22: License Architecture & Cryptographic Entanglement

**Description:** HSM FIPS 140-3 JWT licensing, KDF entanglement với DeviceIdentityKey, graceful degradation.

**Supported Platforms:** 📱💻🖥️☁️🗄️

**Open-Core Boundary:**

| Component | License | Scope |
|-----------|---------|-------|
| `terachat-core/` | AGPLv3 | Public — Gov/Bank audit |
| `terachat-license-guard/` | BSL | Closed |
| `terachat-ui/` | Apache 2.0 | Public |

**License JWT Structure:**

```json
{
  "tenant_id": "acme-corp-vn",
  "tier": "enterprise",
  "valid_until": "2027-03-15T00:00:00Z",
  "offline_ttl_hours": 720,
  "features": ["mesh_survival", "ai_dlp", "federation", "compliance_audit"],
  "ai_tier": "byom",
  "byom_model_slots": 3,
  "enclave_inference_quota_tokens_per_hour": 0
}
```

**AI Tier within License:**

| License AI Tier | Capabilities | Note |
|-----------------|-------------|------|
| `local_only` | CoreML/ONNX on-device, no VPS Enclave | Community / Standard |
| `enclave_shared` | Shared VPS Enclave, quota-limited | Enterprise default |
| `enclave_dedicated` | Dedicated Enclave node(s) | Enterprise Premium |
| `byom` | BYOM model slots in dedicated Enclave | Enterprise / Gov |

**Cryptographic Entanglement:**

```rust
fn derive_master_unlock_key(license_token: &LicenseToken, epoch: u64) -> Result<MasterUnlockKey> {
    let device_key_material = secure_enclave::sign_derive(b"license-kdf-v1", epoch.to_le_bytes())?;
    let kdf_input = [device_key_material, license_token.signature, &epoch.to_le_bytes()].concat();
    Ok(MasterUnlockKey(hkdf_sha256(&kdf_input, b"terachat-master-v1")))
}
```

**Graceful Degradation (4 cấp độ):**

| Thời điểm | UI | Ảnh hưởng hoạt động |
|-----------|-----|---------------------|
| T-30 ngày | Banner vàng Admin Console | Không |
| T-0 | Admin Console partial lock | Chat/Mesh OK; AI + add user bị khóa |
| T+90 | Refuse new bootstrap | App đang chạy OK |
| Gia hạn | JWT mới → restore <5s | Không restart |

---

### F-23: AI Hybrid Edge-Cloud Architecture *(NEW)*

**Description:** Kiến trúc AI lai Edge-Cloud với BYOM (Bring Your Own Model), VPS Enclave stateless, E2EE Prompt Tunneling, Blind RAG, và Semantic Caching. Đảm bảo Zero-Knowledge AI — server không bao giờ thấy plaintext prompt hoặc document content.

**Supported Platforms:** 📱💻🖥️☁️

**Mesh Mode behavior:** AI inference (bao gồm Enclave path) bị disable hoàn toàn khi Mesh Mode active. Return `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED`.

#### §F-23.1 Kiến trúc Tổng quan

TeraChat tách AI thành hai plane độc lập:

```text
CLIENT DEVICE (Edge)
┌─────────────────────────────────────────────────────┐
│  AI Worker Process (OS-isolated)                     │
│  ┌────────────────────────────────────────────────┐  │
│  │  1. PII Redaction (Micro-NER)                  │  │
│  │     → SanitizedPrompt newtype                  │  │
│  │  2. Session Key Derivation                     │  │
│  │     AI_Session_Key = HKDF(Epoch_Key, nonce)    │  │
│  │  3. Encrypt SanitizedPrompt                    │  │
│  │     → EncryptedPromptBundle (AES-256-GCM)      │  │
│  │  4. Local inference (CoreML/ONNX)              │  │
│  │     OR route to VPS Enclave                    │  │
│  │  5. Receive EncryptedResponseBundle            │  │
│  │  6. Decrypt → de-alias → ZeroizeOnDrop         │  │
│  └────────────────────────────────────────────────┘  │
│  IPC: Anonymous Pipe (local model)                   │
│       mTLS + Dynamic Attestation (VPS Enclave)        │
└─────────────────────────────────────────────────────┘
                          │
                   mTLS + Ed25519 Attestation
                   EncryptedPromptBundle only
                          │
                          ▼
VPS ENCLAVE CLUSTER (Stateless)
┌─────────────────────────────────────────────────────┐
│  Load Balancer (HAProxy/Nginx)                       │
│  ┌──────────────────┐  ┌────────────────────────┐   │
│  │ Inference Node 1 │  │  Semantic Cache        │   │
│  │ vLLM + Continuous│  │  (Redis-compatible)    │   │
│  │ Batching         │  │  key = BLAKE3(embed)   │   │
│  │ PagedAttention   │  │  value = Encrypted resp│   │
│  └──────────────────┘  └────────────────────────┘   │
│  ┌──────────────────┐  ┌────────────────────────┐   │
│  │ Blind RAG        │  │  BYOM Registry         │   │
│  │ VectorDB (Qdrant)│  │  Ed25519-signed models │   │
│  │ BlindVectors only│  │                        │   │
│  └──────────────────┘  └────────────────────────┘   │
│                                                      │
│  INVARIANTS:                                         │
│  - No plaintext stored anywhere (RAM only)           │
│  - No logging of prompt/response content             │
│  - RAM ZeroizeOnDrop after each session              │
│  - No DB, no persistent cache of plaintext           │
└─────────────────────────────────────────────────────┘
```

**Inference Backend Resolution (thứ tự ưu tiên):**

```rust
pub enum InferenceBackend {
    LocalCoreML,        // iOS/macOS — tốt nhất, không network
    LocalOnnx,          // Android/Desktop — offline, on-device
    TeraEdgeLan,        // Desktop Super Node trên LAN
    VpsEnclave,         // VPS Enclave — cloud, zero-knowledge
    Unavailable,        // Mesh Mode hoặc quota exhausted
}

pub fn resolve_inference_backend(ctx: &InferenceContext) -> InferenceBackend {
    if ctx.mesh_mode_active { return InferenceBackend::Unavailable; }
    if ctx.local_model_available && ctx.battery_pct > 30 && ctx.available_ram_mb > 100 {
        return InferenceBackend::LocalCoreML; // hoặc LocalOnnx
    }
    if ctx.tera_edge_latency_ms < 50 && ctx.tera_edge_load_pct < 80 {
        return InferenceBackend::TeraEdgeLan;
    }
    if ctx.license.enclave_available && ctx.internet_available {
        return InferenceBackend::VpsEnclave;
    }
    InferenceBackend::Unavailable
}
```

#### §F-23.2 BYOM — Bring Your Own Model

BYOM cho phép enterprise tự đưa custom AI model vào VPS Enclave của TeraChat thay vì dùng model mặc định.

**Model Lifecycle:**

```text
[Enterprise]                    [TeraChat Enclave Registry]
     │                                    │
     │  Upload ModelManifest              │
     │  (Ed25519 signed by Publisher Key) │
     ├──────────────────────────────────►│
     │                                    │  Verify Publisher Key
     │                                    │  BLAKE3 hash check
     │                                    │  Hardware requirement check
     │                                    │  TeraChat CA counter-sign
     │  EncryptedModel (AES-256-GCM)      │
     ├──────────────────────────────────►│
     │                                    │  Load to Enclave Node RAM
     │                                    │  OnnxModelLoader.load_verified()
     │                                    │  Isolated ORT session
     │◄──────────────────────────────────│
     │  ModelId + Attestation Receipt     │
```

**ModelManifest schema:**

```json
{
  "model_id": "acme-finance-llm-v2",
  "publisher_key": "ed25519:ACME_Corp_PubKey",
  "blake3_hash": "a3f9e1d4...",
  "min_vram_gb": 8,
  "max_context_tokens": 8192,
  "tier": "byom",
  "input_schema": { "type": "SanitizedPrompt" },
  "output_schema": { "type": "Vec<ASTNode>" },
  "manifest_signature": "Ed25519:TeraChat_Marketplace_CA_Key:XXXXXXXX"
}
```

**Security Constraints:**

- Model PHẢI accept `SanitizedPrompt` input (không phải raw string).
- Model output PHẢI trả `Vec<ASTNode>` — AST Sanitizer wrap trước khi về client.
- Model không được gọi bất kỳ host function nào ngoài `host_inference_compute()`.
- OnnxModelLoader.load_verified() → manifest signature check → BLAKE3 verify → isolated ORT session.

#### §F-23.3 E2EE Prompt Tunneling (Client → VPS Enclave)

**Invariant:** Raw prompt không bao giờ rời thiết bị. Chỉ `EncryptedPromptBundle` đi qua network.

**Protocol Flow:**

```rust
// Step 1: PII Redaction (Micro-NER, on-device, < 1ms)
let sanitized: SanitizedPrompt = micro_ner::redact(raw_prompt)?;
let alias_vault = InferenceSessionVault::new(); // alias_map: "John" → "[MASK_01]"

// Step 2: Derive ephemeral AI session key
let ai_session_nonce = ring::rand::SystemRandom::new().generate::<[u8; 12]>()?;
let ai_session_key = hkdf_sha256(
    epoch_key.as_bytes(),
    b"ai-session-v1",
    &ai_session_nonce
);

// Step 3: Encrypt sanitized prompt
let bundle = EncryptedPromptBundle {
    ciphertext: aes_256_gcm_seal(&ai_session_key, &ai_session_nonce, sanitized.as_bytes())?,
    nonce: ai_session_nonce,
    session_key_id: ai_session_key.id(),
    model_id: model_id.clone(),
    request_id: Uuid::new_v4(),
};

// Step 4: Attestation token (proves request is from legit TeraChat app)
let attestation = EnclaveAttestation_Token::sign(&device_identity_key, &bundle.request_id)?;

// Step 5: Send to VPS Enclave via mTLS
let response_bundle = enclave_client.send_encrypted(bundle, attestation).await?;

// Step 6: Decrypt response
let ast_nodes: Vec<ASTNode> = {
    let plaintext = aes_256_gcm_open(&ai_session_key, &response_bundle)?;
    serde_json::from_slice(&plaintext)?
};

// Step 7: De-alias (restore masked PII)
let final_response = alias_vault.restore_aliases(ast_nodes)?;

// Step 8: ZeroizeOnDrop
drop(ai_session_key);     // ZeroizeOnDrop
drop(sanitized);          // ZeroizeOnDrop
drop(alias_vault);        // ZeroizeOnDrop — < 100ms total
```

**VPS Enclave side:**

```rust
// Enclave NEVER sees plaintext prompt
pub async fn handle_inference_request(
    encrypted_bundle: EncryptedPromptBundle,
    attestation: EnclaveAttestation_Token,
) -> Result<EnclaveResponseBundle> {
    // Verify attestation — reject if invalid
    attestation.verify(&device_ca_public_key)?;

    // Retrieve session key from Rust Core (key management)
    let session_key = key_registry.get(encrypted_bundle.session_key_id)?;

    // Decrypt in RAM — NEVER write to disk
    let plaintext_prompt = {
        let decrypted = aes_256_gcm_open(&session_key, &encrypted_bundle)?;
        SanitizedPrompt::from_bytes_trusted(decrypted) // mark as already-redacted
    };

    // Check semantic cache first
    let cache_key = blake3::hash(&plaintext_prompt.embedding_prefix());
    if let Some(cached) = semantic_cache.get(&cache_key).await {
        let response = aes_256_gcm_seal(&session_key, &cached)?;
        drop(session_key); // ZeroizeOnDrop
        drop(plaintext_prompt); // ZeroizeOnDrop
        return Ok(EnclaveResponseBundle { ciphertext: response, request_id: encrypted_bundle.request_id });
    }

    // Run inference on BYOM or default model
    let ast_output = model.infer(plaintext_prompt).await?;

    // Re-encrypt response
    let response_ciphertext = aes_256_gcm_seal(&session_key, &serde_json::to_vec(&ast_output)?)?;

    // Store in semantic cache (encrypted key)
    semantic_cache.set(cache_key, serde_json::to_vec(&ast_output)?, TTL_30_MIN).await;

    // ZeroizeOnDrop everything in RAM
    drop(session_key);
    drop(plaintext_prompt);
    drop(ast_output);

    Ok(EnclaveResponseBundle { ciphertext: response_ciphertext, request_id: encrypted_bundle.request_id })
}
```

#### §F-23.4 mTLS + Dynamic App Attestation

**Mục đích:** Chỉ có TeraChat app hợp lệ mới được kết nối đến VPS Enclave. Curl, terminal, API tools bị chặn hoàn toàn.

**Two-Layer Defense:**

```
Layer 1: mTLS (Transport)
  - Client certificate: issued per-device bởi Enterprise CA, TTL 24h
  - Server certificate: TeraChat Enclave CA, pinned in binary
  - Mutual verification: cả hai chiều

Layer 2: Dynamic App Attestation (Application)
  - EnclaveAttestation_Token = Ed25519(DeviceIdentityKey, {request_id, timestamp, bundle_id})
  - TTL: 60 seconds (ngắn để chống replay)
  - Enclave verifies signature trước bất kỳ decrypt nào
  - Token không thể tái sử dụng: request_id must be unique per request
```

**Attestation Verification trên Enclave:**

```rust
pub fn verify_attestation(
    token: &EnclaveAttestation_Token,
    device_ca_pubkey: &Ed25519PublicKey,
) -> Result<()> {
    // 1. Verify Ed25519 signature
    device_ca_pubkey.verify(token.payload.as_bytes(), &token.signature)?;

    // 2. Check TTL (60s window)
    let now = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs();
    if now - token.payload.timestamp > 60 {
        return Err(AttestationError::TokenExpired);
    }

    // 3. Check replay: request_id must not be in Bloom filter
    if enclave_bloom_filter.contains(&token.payload.request_id) {
        return Err(AttestationError::TokenReplayed);
    }
    enclave_bloom_filter.insert(&token.payload.request_id);

    // 4. Verify bundle_id matches expected TeraChat bundle
    if token.payload.bundle_id != EXPECTED_BUNDLE_ID {
        return Err(AttestationError::InvalidBundleId);
    }

    Ok(())
}
```

#### §F-23.5 Blind RAG (Retrieval-Augmented Generation không lộ document)

**Mục đích:** Enterprise upload tài liệu lên hệ thống; VPS có thể tìm kiếm ngữ nghĩa nhưng không bao giờ đọc được nội dung.

**Architecture:**

```text
CLIENT                        VPS ENCLAVE           MINIO BLIND STORAGE
  │                               │                         │
  │ 1. Split document             │                         │
  │    into 512-token chunks      │                         │
  │                               │                         │
  │ 2. For each chunk:            │                         │
  │    a. Encrypt chunk           │                         │
  │       ChunkKey = HKDF(...)    │                         │
  │       ciphertext = AES-GCM    │                         │
  │    b. Compute embedding       │                         │
  │       (local ONNX model)      │                         │
  │       BlindVector [f32; 384]  │                         │
  │                               │                         │
  │ 3. Upload ciphertext ─────────┼─────────────────────►  │
  │    (path = cas_hash)          │                    (ciphertext stored)
  │                               │                         │
  │ 4. Upload BlindVector ────────►                         │
  │    (with cas_hash ref)   (stored in VectorDB)           │
  │                               │                         │
  │ 5. Query time:                │                         │
  │    a. Compute query embed     │                         │
  │       (local ONNX model)      │                         │
  │    b. Send query_vector ──────►                         │
  │                          (ANN search → top-k cas_hashes)│
  │    c. Receive cas_hashes ◄────│                         │
  │    d. Fetch ciphertexts ──────┼─────────────────────►  │
  │                               │             (return ciphertexts)
  │    e. Decrypt locally         │                         │
  │       → plaintext chunks      │                         │
  │    f. Build augmented prompt  │                         │
  │    g. Encrypt & send          │                         │
  │       to Enclave inference ──►│                         │
```

**Security Properties:**

- VPS Enclave VectorDB chứa `BlindVector` + `cas_hash` reference — không bao giờ plaintext.
- MinIO Blind Storage chứa ciphertext — không biết nội dung.
- Chỉ client có `ChunkKey` để decrypt.
- ANN search (Approximate Nearest Neighbor) hoạt động thuần túy trên vector space — không cần plaintext.

**Implementation:**

```rust
pub struct BlindRagStore {
    vector_db: QdrantClient,     // blind vectors only
    blob_store: MinioClient,     // ciphertext only
}

impl BlindRagStore {
    pub async fn upload_document(&self, doc: &[u8], company_key: &CompanyKey) -> Result<Vec<Uuid>> {
        let chunks = split_into_chunks(doc, 512); // 512 tokens per chunk
        let mut chunk_ids = Vec::new();

        for (idx, chunk) in chunks.iter().enumerate() {
            // Derive chunk key (client side only)
            let chunk_key = ChunkKey::derive(company_key, &doc_id, idx);

            // Encrypt chunk
            let ciphertext = aes_256_gcm_seal(&chunk_key, chunk)?;
            let cas_hash = blake3::hash(&ciphertext);

            // Compute embedding LOCALLY (never sent to server in plaintext)
            let blind_vector = local_embedding_model.embed(chunk)?; // [f32; 384]

            // Upload ciphertext to MinIO (blind)
            self.blob_store.put(&cas_hash.to_hex(), &ciphertext).await?;

            // Upload blind vector to VectorDB
            self.vector_db.upsert_point(PointStruct {
                id: Uuid::new_v4(),
                vector: blind_vector.to_vec(),
                payload: hashmap! { "cas_hash" => cas_hash.to_hex() },
            }).await?;

            // ZeroizeOnDrop chunk key immediately
            drop(chunk_key);
            chunk_ids.push(cas_hash.into());
        }
        Ok(chunk_ids)
    }

    pub async fn query(&self, query_text: &str, top_k: usize, company_key: &CompanyKey) -> Result<Vec<String>> {
        // Compute query embedding locally
        let query_vector = local_embedding_model.embed(query_text)?;

        // Send only vector to VPS (no plaintext)
        let results = self.vector_db.search_points(SearchRequest {
            vector: query_vector.to_vec(),
            limit: top_k,
            ..Default::default()
        }).await?;

        // Fetch ciphertexts and decrypt locally
        let mut plaintext_chunks = Vec::new();
        for point in results {
            let cas_hash = point.payload["cas_hash"].as_str().unwrap();
            let ciphertext = self.blob_store.get(cas_hash).await?;
            let chunk_idx = point.payload["chunk_idx"].as_u64().unwrap() as usize;
            let chunk_key = ChunkKey::derive(company_key, &doc_id, chunk_idx);
            let plaintext = aes_256_gcm_open(&chunk_key, &ciphertext)?;
            plaintext_chunks.push(String::from_utf8(plaintext)?);
            drop(chunk_key);
        }
        Ok(plaintext_chunks)
    }
}
```

#### §F-23.6 Semantic Caching (Tăng thông lượng, giảm latency)

**Mục đích:** Các câu hỏi có ngữ nghĩa tương tự được trả kết quả từ cache mà không cần chạy inference, tiết kiệm GPU và giảm latency xuống mili-giây.

**Invariant:** Cache key là BLAKE3 hash của embedding — không phải plaintext prompt.

```rust
pub struct SemanticCache {
    store: RedisClient,           // encrypted values
    embedding_model: EmbeddingModel,
    similarity_threshold: f32,   // 0.92 — chỉ hit cache khi rất tương đồng
}

impl SemanticCache {
    pub async fn get(&self, sanitized_prompt: &SanitizedPrompt, session_key: &AiSessionKey) -> Option<Vec<ASTNode>> {
        // Compute embedding of sanitized prompt (no PII)
        let embedding = self.embedding_model.embed(sanitized_prompt.as_str())?;

        // Cache key = BLAKE3(first 16 floats of embedding)
        // This is semantic fingerprint — similar prompts have similar fingerprints
        let cache_key = blake3::hash(
            &embedding.iter().take(16).flat_map(|f| f.to_le_bytes()).collect::<Vec<_>>()
        );

        // Lookup in Redis (encrypted value)
        let encrypted_val = self.store.get(cache_key.to_hex()).await?;

        // Decrypt with session_key
        let ast_bytes = aes_256_gcm_open(session_key, &encrypted_val).ok()?;
        serde_json::from_slice(&ast_bytes).ok()
    }

    pub async fn set(&self, sanitized_prompt: &SanitizedPrompt, response: &[ASTNode], session_key: &AiSessionKey) {
        let embedding = self.embedding_model.embed(sanitized_prompt.as_str()).unwrap();
        let cache_key = blake3::hash(
            &embedding.iter().take(16).flat_map(|f| f.to_le_bytes()).collect::<Vec<_>>()
        );

        // Encrypt response before storing — server cannot read cached content
        let encrypted = aes_256_gcm_seal(session_key, &serde_json::to_vec(response).unwrap()).unwrap();
        self.store.set_ex(cache_key.to_hex(), encrypted, 1800).await.ok(); // TTL 30 min
    }
}
```

**Cache Hit Rate Optimization:**

- Normalize prompt trước khi embedding: lowercase, strip whitespace, normalize unicode.
- Similarity threshold 0.92 ngăn false positive (câu hỏi khác nghĩa nhưng embedding gần).
- Cache key KHÔNG bao giờ là plaintext → server không thể đọc query history từ cache.

#### §F-23.7 VPS Enclave Cluster Infrastructure

**Mô hình triển khai:**

```
Internet ──► Load Balancer (HAProxy)
                 │
        ┌────────┴────────┐
        │                 │
  Inference Node 1   Inference Node 2    (horizontal scale)
  [vLLM + Cont.Batch] [vLLM + Cont.Batch]
  [PagedAttention]    [PagedAttention]
  [Isolated ORT]      [Isolated ORT]
        │
  ┌─────┴─────┐
  │           │
Semantic   Blind RAG
Cache      VectorDB
(Redis)    (Qdrant)
```

**Continuous Batching + PagedAttention (vLLM):**

Thay vì xử lý từng request một (static batching), vLLM xử lý nhiều request đồng thời bằng cách:

- **Continuous Batching:** Mỗi iteration có thể nhận request mới và hoàn thành request cũ — không cần chờ cả batch hoàn tất.
- **PagedAttention:** KV Cache được quản lý như RAM ảo (paging) — mỗi user session có "trang" KV riêng, tránh fragmentation. Tăng throughput 5–10× so với naive batching.

```python
# Conceptual — vLLM handles this internally
engine = AsyncLLMEngine.from_engine_args(EngineArgs(
    model="path/to/byom_model",
    max_num_seqs=256,          # 256 concurrent sessions
    max_model_len=8192,        # max context tokens
    gpu_memory_utilization=0.85,
))

# Each request is independent E2EE session
async def handle_request(encrypted_bundle: bytes) -> bytes:
    session_key = retrieve_session_key(encrypted_bundle)
    plaintext = aes_gcm_decrypt(session_key, encrypted_bundle)  # in RAM only
    
    output = await engine.generate(plaintext, sampling_params)  # batched with other sessions
    
    response_ciphertext = aes_gcm_encrypt(session_key, output.text)
    
    # ZeroizeOnDrop
    del session_key
    del plaintext
    del output
    
    return response_ciphertext
```

**Node Sizing Guidelines:**

| Workload | GPU | VRAM | Sessions/Node | Latency (p99) |
|----------|-----|------|---------------|---------------|
| Base (7B BYOM) | 1× A10G | 24GB | ~50 concurrent | < 2s |
| Mid (13B BYOM) | 2× A10G | 48GB | ~30 concurrent | < 4s |
| Large (70B BYOM) | 4× A100 | 320GB | ~10 concurrent | < 10s |

**Stateless Guarantee:**

```rust
// Lifecycle of every inference session
pub struct EnclaveSession {
    request_id: Uuid,
    session_key: ZeroizeOnDrop<AiSessionKey>,
    plaintext_prompt: ZeroizeOnDrop<SanitizedPrompt>,
    // NO: no DB connection, no log file handle, no persistent state
}

impl Drop for EnclaveSession {
    fn drop(&mut self) {
        // Rust RAII: ZeroizeOnDrop automatically overwrites all fields
        // session_key → 0x00
        // plaintext_prompt → 0x00
        // No trace left in RAM
    }
}
```

**Observability (Zero-Knowledge metrics):**

```
enclave_inference_latency_ms{model_id, backend} histogram
enclave_requests_total{status="success|error"} counter
enclave_cache_hit_rate gauge
enclave_active_sessions gauge
enclave_gpu_utilization_pct gauge
# NO: no prompt content, no user ID, no response content in any metric
```

**Failure Handling:**

- Enclave node crash: Load Balancer health check (2s interval) → route to healthy node. In-flight requests retry once.
- GPU OOM: vLLM's PagedAttention prevents OOM; if happens → graceful degradation to smaller batch, emit `CoreSignal::ComponentFault { component: "ai_enclave", severity: Warning }`.
- Semantic Cache miss: Forward to inference node, no data loss.
- BYOM model hash mismatch: Terminate session immediately, emit `CoreSignal::ComponentFault { severity: Critical }`, log `ModelIntegrityViolation`.
- Attestation failure: Return `ERR_ATTESTATION_FAILED`, do not decrypt bundle.

**Dependencies:**

- REF: TERA-CORE §4.1 (F-01) — `DeviceIdentityKey` cho `EnclaveAttestation_Token`
- REF: TERA-CORE §4.2 (F-05) — `Epoch_Key` là nguồn derive `AI_Session_Key`
- REF: TERA-CORE §9.4 — AI Safety pipeline (ISDM, SASB, EDES, SSA)
- REF: TERA-FEAT §F-10 — Client-side AI Worker, inference backend selection, CoreML/ONNX local
- REF: TERA-FEAT §INFRA-01 — Mobile ONNX offload protocol (TeraEdge LAN path)
- REF: TERA-CORE §F-22 — License JWT `ai_tier` field

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

Side effects:
  → MESH_MODE:   All WASM Sandboxes terminate; AI Enclave path disabled; 100% CPU/RAM → Mesh routing
  → ONLINE_QUIC: Resume WASM; AI Enclave re-enabled; emit StateChanged(protocol=QUIC)
```

### 5.2 MLS Epoch State Machine

```text
States: EPOCH_ACTIVE(n) → EPOCH_ROTATING → EPOCH_ACTIVE(n+1)

Transitions:
  EPOCH_ACTIVE    ──member_leave || schedule──▶  EPOCH_ROTATING
  EPOCH_ROTATING  ──Update_Path commit OK──────▶  EPOCH_ACTIVE(n+1)
  EPOCH_ROTATING  ──timeout / network loss──────▶  EPOCH_ROTATING (retry)

Side effects:
  → EPOCH_ROTATING: Old Epoch_Key zeroized; AI_Session_Key derived from old Epoch_Key also zeroized;
                    Push_Key rotated OOB; New AI sessions must use new Epoch_Key
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

Side effects:
  → SPLIT_BRAIN:  UI shows dashed border on pending messages; Blind RAG queries use local vectors only
  → MERGING:      Desktop O(N log N) merge; Mobile receives Snapshot; Blind RAG sync vectors
  → SYNCED:       MLS Epoch stitching; CRDT borders solid; Full AI Enclave path available
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

Side effects:
  → DEGRADED:  AI module (including Enclave path) off; add user blocked; Chat/Mesh continue
  → LOCKED:    Refuse new bootstrap; existing session continues
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
  - Tactical Relay: Append-Only CRDT, store-and-forward text only
  - NO DAG merge, NO MLS Epoch rotation, NO AI inference (any backend)
  - EMDP Key Escrow: Desktop exports AES-256 relay_session_key before offline
```

### 5.7 AI Inference State Machine *(NEW)*

```text
States: IDLE → RESOLVING_BACKEND → LOCAL_INFERENCE → ENCLAVE_TUNNELING →
        ENCLAVE_WAITING → RESPONSE_DECRYPTING → COMPLETE → ERROR

Transitions:
  IDLE               ──user AI request──▶  RESOLVING_BACKEND
  RESOLVING_BACKEND  ──local available──▶  LOCAL_INFERENCE
  RESOLVING_BACKEND  ──VPS available────▶  ENCLAVE_TUNNELING
  RESOLVING_BACKEND  ──none available───▶  ERROR (ERR_AI_UNAVAILABLE)
  RESOLVING_BACKEND  ──mesh mode────────▶  ERROR (ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED)
  LOCAL_INFERENCE    ──complete─────────▶  RESPONSE_DECRYPTING
  LOCAL_INFERENCE    ──OOM─────────────▶  RESOLVING_BACKEND (retry with VPS)
  ENCLAVE_TUNNELING  ──bundle sent──────▶  ENCLAVE_WAITING
  ENCLAVE_TUNNELING  ──attestation fail─▶  ERROR (ERR_ATTESTATION_FAILED)
  ENCLAVE_WAITING    ──response received▶  RESPONSE_DECRYPTING
  ENCLAVE_WAITING    ──timeout 5s───────▶  ERROR (retry once, then Unavailable)
  RESPONSE_DECRYPTING──de-alias done────▶  COMPLETE
  COMPLETE           ──ZeroizeOnDrop────▶  IDLE

Side effects at each state exit:
  → LOCAL_INFERENCE exit: ZeroizeOnDrop(local_model_context)
  → ENCLAVE_TUNNELING exit: ZeroizeOnDrop(AI_Session_Key if error)
  → RESPONSE_DECRYPTING exit: ZeroizeOnDrop(AI_Session_Key, SanitizedPrompt, InferenceSessionVault)
  → ERROR: emit CoreSignal::ComponentFault if Enclave unreachable 3× in 60s
```

---

## §6 API / IPC CONTRACT

> Nguồn sự thật duy nhất cho mọi giao tiếp cross-boundary.

### 6.1 CoreSignals (Rust → UI)

| Signal | Payload | Trigger | UI Action |
|--------|---------|---------|-----------|
| `StateChanged(table, version)` | table name, version number | Any DB write | UI query fresh snapshot |
| `MeshModeActivated` | `{peer_count, transport}` | Network loss | Switch dark UI (#0F172A); disable AI UI |
| `MeshRoleChanged(role)` | new role enum | Jetsam pressure / Desktop join | Show role transfer banner |
| `NetworkProtocolChanged(proto)` | QUIC/gRPC/WSS | ALPN fallback | Update HUD icon |
| `MemoryPressureHigh` | `{available_mb}` | OS memory warning | Reduce blur 20px→8px |
| `MlsEpochRotated(n)` | epoch number | Member leave / schedule | Update E2EE badge; invalidate AI session keys |
| `SecurityEvent::*` | event details | Various | RSOD / warning overlay |
| `MlsKeyDesync(chat_id)` | chat ID | NSE push_epoch mismatch | Trigger Main App wakeup |
| `WasmSandboxTerminated(reason)` | reason string | Gas/timeout/mesh | Remove .tapp from UI |
| `LicenseStateChanged(state)` | new state enum | Heartbeat check | Show/hide feature lock UI |
| `FcpTriggered` | `{plugin_id, timestamp}` | Admin FCP activation | Red border overlay |
| `ConversationSealed` | `{chat_id}` | SSA taint threshold | Hazard-stripe overlay |
| `EgressSchemaViolation(plugin_id)` | plugin ID | Payload mismatch | Alert + quarantine .tapp |
| `DmaIntrusionDetected` | PCI device info | IOMMU group change | Full-screen DMA alert |
| `AwdlUnavailable(reason)` | hotspot/carplay | iOS AWDL monitor | Tier downgrade banner |
| **`AiBackendChanged(backend)`** | **InferenceBackend enum** | **Backend selection changed** | **Update AI mode indicator in HUD** |
| **`AiEnclaveUnavailable`** | **reason** | **Attestation fail or timeout** | **Show local-fallback indicator** |
| **`AiSessionComplete`** | **tokens_used, latency_ms** | **Inference done** | **Update quota display** |

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
| **`invoke_ai_inference(prompt, context_ids, model_id?)`** | **SanitizedPrompt, RAG context refs, optional BYOM model** | **Trigger full AI pipeline (local or enclave)** |
| **`upload_rag_document(file_bytes, doc_id)`** | **document bytes, document ID** | **Chunk, embed locally, encrypt, upload to Blind RAG** |
| **`query_rag(query_text, top_k)`** | **query string, result count** | **Local embed → Blind vector search → decrypt locally** |
| **`select_byom_model(model_id)`** | **BYOM model ID** | **Switch active model for current workspace (Admin only)** |

### 6.3 Data Plane IPC

| Platform | Mechanism | Throughput | Use Case |
|----------|-----------|-----------|----------|
| 📱 iOS | JSI C++ `std::unique_ptr` + Custom Deleter | ~400MB/s | Large payloads, media |
| 📱 Android / Huawei | Dart FFI TypedData (C ABI static buffer) | ~400MB/s | Large payloads, media |
| 💻🖥️ Desktop | `SharedArrayBuffer` (mmap physical) | ~500MB/s | File chunks, embeddings |
| All | Protobuf over Control Plane (<50 bytes) | N/A | Commands, metadata |
| **AI Worker ↔ Rust Core** | **Anonymous Pipe (local)** | **~1GB/s** | **AI prompt/response (local path)** |
| **AI Worker ↔ VPS Enclave** | **mTLS + EncryptedBundle** | **Network-bound** | **AI prompt/response (enclave path)** |

**IPC Security Rules:**

- Control Plane: lệnh nhỏ <1KB — không carry plaintext key material.
- Data Plane: Zero-Copy qua shared memory — Rust kiểm tra `offset + length ≤ SAB_SIZE` + CRC32.
- `Company_Key` / `Channel_Key` **tuyệt đối không** truyền qua IPC lên WASM.
- `AI_Session_Key` **tuyệt đối không** rời AI Worker Process — chỉ encrypted bundles đi qua network.

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

// AI (via sanitized pipeline only — .tapp cannot bypass PII redaction)
extern "C" {
    fn host_ai_infer(sanitized_prompt: *const u8, prompt_len: usize,
                     ast_out: *mut u8, ast_out_max: usize) -> i32;
    // Returns: 0=OK, 1=Unavailable, 2=QuotaExceeded, 3=MeshMode, 4=AttestationFailed
    // NEVER exposes raw model, raw session key, or backend selection to .tapp
}
```

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
| Super Node Eligible | ❌ (iOS excluded) | ✅ (RAM ≥ 4GB) | ✅ | ✅ | ✅ | ✅ |
| AI Local | CoreML | ONNX Runtime | HiAI/ONNX | CoreML/ONNX | ONNX | ONNX |
| AI Enclave Path | ✅ (mTLS + Attestation) | ✅ | ✅ | ✅ | ✅ | ✅ |
| BYOM model load | ❌ (Enclave only) | ❌ (Enclave only) | ❌ (Enclave only) | ❌ (Enclave only) | ❌ (Enclave only) | ❌ (Enclave only) |
| Blind RAG local embed | CoreML embed model | ONNX embed model | HiAI/ONNX | CoreML/ONNX | ONNX | ONNX |

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

---

## §8 NON-FUNCTIONAL REQUIREMENTS

### 8.1 Performance

| Metric | Target | Platform | Notes |
|--------|--------|---------|-------|
| Message E2EE encrypt/decrypt | <10ms | 📱💻🖥️ | AES-NI/ARM NEON accelerated |
| CRDT Write Local | <5ms | 📱💻🖥️ | SQLite WAL mode |
| MLS Group operation (5000 users) | O(log n) | ☁️ | TreeKEM |
| ALPN Protocol Negotiation | <50ms total | 📱💻☁️ | Parallel probe |
| AI Local inference (7B model) | <3s p99 | 💻🖥️ | Depends on hardware |
| AI Enclave inference (7B BYOM) | <2s p99 | ☁️ | vLLM continuous batching |
| Semantic cache hit | <50ms | ☁️ | BLAKE3 lookup + decrypt |
| Blind RAG query (10K vectors) | <200ms | ☁️ | ANN search + fetch + decrypt |
| BYOM model load (7B) | <30s | ☁️ | One-time per Enclave restart |
| E2EE Prompt bundle round-trip | <5ms overhead | 📱💻🖥️ | PII redact + encrypt |
| E2E Latency (Online QUIC) | <30ms | ☁️📱💻 | Co-located VPS |
| Throughput IPC Data Plane | ~400-500MB/s | 📱💻🖥️ | Zero-copy |
| File Chunker Throughput | 300-500MB/s | ☁️🗄️ | NVMe + io_uring |

### 8.2 Memory

| Component | Limit | Platform | Notes |
|-----------|-------|---------|-------|
| NSE Process | ≤24MB | 📱 iOS | Apple hard limit |
| WASM Sandbox per instance | ≤64MB (soft cap) | 📱💻🖥️ | OOM-kill without warning |
| AI Worker Process (local) | ≤150MB | 📱 | Whisper Base = 74MB |
| AI Worker Process (Desktop) | ≤4GB | 💻🖥️ | vLLM handles KV paging |
| InferenceSessionVault RAM | < 1MB | AI Worker | alias_map; ZeroizeOnDrop < 100ms |
| BlindVector per chunk | 384 × 4 bytes = 1.5KB | ☁️ | per document chunk in VectorDB |
| Enclave KV Cache per session | Managed by PagedAttention | ☁️ | Not persisted across sessions |

### 8.3 Reliability

| Scenario | SLA | Mechanism |
|----------|-----|-----------|
| Online messaging (SLA) | 99.999% | Anti-Entropy Merkle Sync fallback |
| AI Enclave node failure | <3s failover | HAProxy health check → healthy node |
| AI Enclave full cluster failure | Fallback to local | `resolve_inference_backend()` |
| Semantic cache miss | No degradation | Transparent fallback to inference |
| BYOM model crash | Restart + retry | Isolated ORT session per request |

### 8.4 Security SLA

| Property | Guarantee | Mechanism |
|----------|-----------|-----------|
| Forward Secrecy | Per MLS Epoch | TreeKEM Update Path; old key zeroized |
| AI prompt privacy | Zero-Knowledge | E2EE Prompt Tunneling; VPS never persists plaintext |
| BYOM model integrity | Computationally verifiable | BLAKE3 + Ed25519 on every load |
| AI session unlinkability | Semantic cache keyed by embedding hash | No plaintext prompt in cache keys |
| Blind RAG server-side | Server sees vectors only | Client holds all ChunkKeys |

---

## §9 SECURITY MODEL

### 9.1 Key Management & Cryptographic Primitives

| Operation | Algorithm | Library | Notes |
|-----------|-----------|---------|-------|
| Asymmetric signing | Ed25519 | `ring` | All audit log entries, attestation tokens |
| Key exchange | X25519 + ML-KEM-768 | `ring` + `pqcrypto` | Hybrid PQ-KEM |
| Symmetric encryption | AES-256-GCM | `ring` | All E2EE payloads, AI session bundles |
| Hashing | BLAKE3 | `blake3` | DAG integrity, semantic cache keys |
| AI embedding | Local ONNX/CoreML | Platform-specific | Blind RAG vector generation |
| Password KDF | Argon2id | `argon2` | PIN Fallback KEK |
| Key derivation | HKDF-SHA256 | `ring` | Key hierarchy, AI_Session_Key |
| Constant-time comparison | `subtle` crate | `subtle` | MAC/signature comparisons |
| Random generation | OS CSPRNG | `ring::rand` | All nonces, session keys, AI nonces |

### 9.2 Attack Surface Matrix

| Attack Vector | Mitigation | Section |
|---------------|-----------|---------|
| Memory dump / Cold Boot | ZeroizeOnDrop everywhere; ChaCha8 RAM scrambling | §4.6 |
| DMA (Thunderbolt/PCIe) | IOMMU check at startup | §4.4 |
| JIT spraying (WASM) | iOS: wasm3 interpreter; others: sandbox CFI | §F-11 |
| Timing side-channel | `subtle` crate; constant-time logic | §2.6 |
| Traffic pattern analysis | Fixed-size padding; Heartbeat Dummy Traffic; Oblivious CAS Routing | §2.6 |
| Sybil (Mesh) | mPoW Argon2id; Signed identity | §F-13 |
| Byzantine fault | PoM Epidemic; Multi-party attribution | §F-13 |
| Replay attack | HLC Epoch binding; Monotonic Counter; 48h window | §5.10.3 |
| License bypass | KDF entanglement; O-LLVM obfuscation | §F-22 |
| Rogue admin injection | Root CA Binary Transparency; M-of-N update signing | §F-10 |
| WASM sandbox escape | CFI; Gas-metering; PoM Epidemic | §F-11 |
| **AI prompt exfiltration** | **E2EE Prompt Tunneling; VPS Enclave stateless; ZeroizeOnDrop** | **§F-23** |
| **BYOM model poisoning** | **BLAKE3 + Ed25519 on every model load; OnnxModelLoader.load_verified()** | **§F-23.2** |
| **Prompt injection via .tapp** | **SASB AST sanitizer; only Vec<ASTNode> returned; 3-strike suspend** | **§9.4** |
| **Semantic cache timing attack** | **Threshold 0.92 prevents near-miss fingerprinting; cache keys are embeddings not prompts** | **§F-23.6** |
| **Blind RAG plaintext exposure** | **VectorDB contains only BlindVector + cas_hash; ChunkKey stays on client** | **§F-23.5** |
| **VPS Enclave attestation bypass** | **Ed25519 + 60s TTL + Bloom filter replay prevention** | **§F-23.4** |
| **Unauthorized Enclave access (curl/tools)** | **mTLS client cert (per-device, TTL 24h) + Dynamic App Attestation** | **§F-23.4** |

### 9.3 Hardware-Level Cryptography Defenses

**Timing Attack:**

- 📱💻🖥️ **Constant-time Logic** via `subtle` crate.
- 📱💻🖥️ **Bit-masking** (AND, OR, XOR, NOT) — mọi phép tính mật mã tiêu tốn cùng CPU cycles.

**Traffic Pattern Analysis:**

- 📱💻🖥️ **Fixed-size Padding:** Mọi TCP/UDP payload đạt mức cố định (4096 bytes). AI bundles padded to fixed sizes.
- 📱💻🖥️ **Heartbeat Dummy Traffic:** Lưu lượng đồng nhất không đứt gãy.
- ☁️📱💻🖥️ **Oblivious CAS Routing + Batch Requests** qua Mixnet Proxy.

### 9.4 Cryptographic Architecture — AI Safety

**ISDM (Interactive SLM Dual-Masking):**

- 📱💻🖥️ SLM cục bộ "rút ruột" PII trước khi gọi LLM ngoài. Alias: `[REDACTED_PHONE_1]`, v.v.
- 📱💻🖥️ De-tokenization sau khi nhận LLM response — trên Client, trong `InferenceSessionVault`.
- 📱💻🖥️ `InferenceSessionVault::drop()` overwrite với `0x00` ngay sau De-tokenize — < 100ms total.
- ☁️ Header `X-Zero-Retention: true` — ép API Provider không train model.
- **Blind RAG extension:** Document chunks are de-aliased locally before being included in augmented prompt context.

**SASB (Strict AST Sanitization Bridge):**

- 💻📱 `pulldown-cmark` Rust AST parsing của mọi AI response trước khi về UI.
- 💻📱 Whitelist strict: chỉ `Text, Heading, Paragraph, Code, CodeBlock, Strong, Emphasis, List, Link`.
- 💻📱 Output: `Vec<ASTNode>` Protobuf → UI renderer. Không bao giờ raw HTML string.
- **BYOM extension:** BYOM models MUST output JSON-serializable `Vec<ASTNode>`. Any model outputting raw string is rejected.

**EDES (Edge Deterministic Entity Scanner):**

- 📱💻 Aho-Corasick O(n) scanner. Multi-pattern 500MB/s throughput.
- 📱💻 Zero-copy scanning trực tiếp trên plaintext buffer ZeroizeOnDrop.
- **Blind RAG extension:** EDES runs on retrieved document chunks before they join the augmented prompt.

**SSA (Stateful Semantic Accumulator — Chống Salami Attack):**

- 📱💻 Sliding Context Buffer (SCB) N=20 messages, bảo vệ ZeroizeOnDrop.
- 📱💻 Lazy Triggered ONNX: chạy khi EDES flag ≥2 borderline entities trong 5 messages.
- 📱💻 Retroactive Taint: nếu `Intent_Score[SOCIAL_ENGINEERING] > 0.75` → taint N-3 messages + seal conversation.

**AI Zero-Knowledge Audit Trail:**

```sql
-- Ghi trước khi bất kỳ TLS connection nào được mở
INSERT INTO ai_egress_audit (
    request_id,          -- Uuid v4 — unique per request
    backend_used,        -- Local | TeraEdgeLan | VpsEnclave
    model_id,            -- model identifier (not content)
    tokens_estimated,    -- approximate, not exact (prevent inference attacks)
    payload_size_bucket, -- 0-512B, 512B-1KB, 1KB-4KB, 4KB+ (bucketed)
    device_ed25519_sig   -- ký bằng Device_Key
    -- NO: no prompt content, no response content, no session key
);
```

---

## §10 FAILURE MODEL

### 10.1 Network Failures

| Failure | Detection | Recovery | Max Data Loss |
|---------|-----------|----------|---------------|
| Internet outage | Heartbeat timeout >30s | Auto-switch to Mesh Mode; AI Enclave disabled | None (Store-and-Forward) |
| QUIC firewall block | UDP timeout 50ms | ALPN fallback → gRPC → WSS | None (transparent) |
| AI Enclave node down | HAProxy health check 2s | Route to healthy node; in-flight retry once | Single AI request |
| AI Enclave cluster down | All nodes health-fail | Fallback to local inference; `AiEnclaveUnavailable` signal | None for messaging |
| VPS Enclave attestation fail | Token validation error | `ERR_ATTESTATION_FAILED`; log; do not retry same node for 30s | Single AI request |

### 10.2 Storage Failures

| Failure | Detection | Recovery | Max Data Loss |
|---------|-----------|----------|---------------|
| Jetsam kill NSE mid-WAL | `PRAGMA quick_check(1)` at startup | Two-Phase Commit recovery | None |
| `nse_staging.db` Poison Pill | SQLite integrity check | POSIX `unlink()` + Crypto-Shredding | NSE messages in corrupted frame |
| Hard power loss during Hydration | `Hydration_Checkpoint` present at boot | Resume from last committed chunk_index | Uncommitted chunk |
| Blind RAG VectorDB failure | ANN search error | Return empty context; AI proceeds without RAG context | No document retrieval for that query |
| Semantic cache failure | Redis unavailable | Transparent fallback to inference; log metric | Slight latency increase |

### 10.3 Key Failures

| Failure | Detection | Recovery | Impact |
|---------|-----------|----------|--------|
| DeviceIdentityKey lost | Device lost/wiped | Admin QR Key Exchange or BIP-39 Mnemonic | New key; old messages inaccessible without Escrow |
| AI_Session_Key derivation fail | HKDF returns error | Retry once; then return `ERR_AI_SESSION_KEY_FAILED` | Single AI request fails |
| BYOM model BLAKE3 mismatch | OnnxModelLoader.load_verified() | Terminate Enclave session; `ModelIntegrityViolation` audit | BYOM unavailable until model re-verified |
| EnclaveAttestation_Token expired | TTL check >60s | Re-sign with DeviceIdentityKey (biometric may be required) | <100ms delay |

### 10.4 Runtime Failures

| Failure | Detection | Recovery | Impact |
|---------|-----------|----------|--------|
| WASM Gas quota exceeded | Gas-metering trap | `ZeroizeOnDrop` Linear Memory; terminate instance | .tapp unavailable |
| AI Worker process crash (local) | OS process exit code | `catch_unwind`; emit `ComponentFault`; restart after 1s | Single AI request delayed |
| Enclave inference OOM | vLLM OOM | Reduce batch; queue request; emit `ComponentFault { severity: Warning }` | AI response delayed |
| PII redaction Micro-NER fail | ONNX runtime error | Block AI request entirely; return `ERR_PII_REDACTION_FAILED` | Single AI request fails; no raw prompt leaves device |
| InferenceSessionVault leak (GC instead of explicit drop) | `ffi.gc_finalizer_release.count` metric | Log WARNING; GC still ZeroizeOnDrop; but it's a code smell | Security: eventual ZeroizeOnDrop still happens |

---

## §11 VERSIONING & MIGRATION

### 11.1 Schema Migration Strategy

```rust
const CURRENT_HOT_DAG_SCHEMA_VERSION: u32 = 1;
const CURRENT_COLD_STATE_SCHEMA_VERSION: u32 = 1;
```

**Safety Net:** `cold_state.db` có thể rebuild hoàn toàn từ `hot_dag.db` bất kỳ lúc nào.

### 11.2 Backward Compatibility Rules

| Change Type | Version Bump | Policy |
|-------------|-------------|--------|
| New CRDT event type | Minor | Existing clients ignore unknown types |
| MLS epoch format change | **Major** | Full deprecation window (12 months) |
| Crypto Host ABI signature change | **Major** | Dual-support old+new for 12 months |
| **AI Enclave Protocol change** | **Major** | **Dual-support: old clients use local inference** |
| **BYOM manifest schema change** | **Major** | **Old manifests rejected with clear error** |
| Semantic cache key scheme change | Minor | Old cache entries simply miss; no data loss |
| Blind RAG vector dimension change | **Major** | Re-embed all documents |

### 11.3 MLS Protocol Versioning

- 📱💻🖥️ Extension `TeraChat_App_Version` trong `KeyPackage` để đàm phán năng lực.
- 📱💻🖥️ Min-Version Roster scan → Sender Downgrade Mode nếu có device cũ.

### 11.4 .tapp Host Function ABI Contract

```json
{
  "host_api_version": "1.3.0",
  "min_host_api_version": "1.0.0",
  "max_host_api_version": "2.0.0"
}
```

### 11.5 AI Enclave Protocol Versioning

```json
{
  "enclave_protocol_version": "1.0.0",
  "min_enclave_version": "1.0.0",
  "max_context_tokens": 8192,
  "supported_backends": ["vllm", "ort"]
}
```

Clients với `enclave_protocol_version` không tương thích → fallback to local inference automatically.

---

## §12 EMERGENCY MOBILE DICTATOR PROTOCOL (EMDP)

### 12.1 EMDP State Machine

```rust
pub enum DictatorElectionMode {
    Normal,
    EmergencyMobileOnly,
    SoloAppendOnly,
}

pub struct TacticalRelayConfig {
    node_id: NodeId,
    mode: TacticalRelayMode, // TextOnlyForward
    ttl_minutes: u64,        // 60 minutes
}
```

**Semantic quan trọng:** Tactical Relay ≠ Super Node. Không AI inference trong EMDP mode.

### 12.2 EMDP Key Escrow Handshake

```rust
pub struct EmdpKeyEscrow {
    relay_session_key: AesKey256,
    emdp_start_epoch: u64,
    emdp_expires_at: u64,
}
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
  "features": ["mesh_survival", "ai_dlp", "federation", "compliance_audit"],
  "ai_tier": "enclave_dedicated",
  "byom_model_slots": 3,
  "enclave_inference_quota_tokens_per_hour": 0,
  "blind_rag_storage_gb": 100
}
```

### 13.2 License Boundary Separation (Open-Core)

```
Mã nguồn mở (AGPLv3): terachat-core/     ← Crypto, CRDT, MLS, Mesh, AI pipeline client-side
Mã nguồn đóng (BSL):  terachat-license-guard/ ← License validation
Mã nguồn đóng (BSL):  terachat-enclave/   ← VPS Enclave server runtime
```

### 13.3 Cryptographic Entanglement

```rust
fn derive_master_unlock_key(license_token: &LicenseToken, epoch: u64) -> Result<MasterUnlockKey> {
    let device_key_material = secure_enclave::sign_derive(b"license-kdf-v1", epoch.to_le_bytes())?;
    let kdf_input = [device_key_material, license_token.signature, &epoch.to_le_bytes()].concat();
    Ok(MasterUnlockKey(hkdf_sha256(&kdf_input, b"terachat-master-v1")))
}
```

### 13.4 License Heartbeat Validation

| Kiểm tra | Cơ chế | Fail → |
|----------|--------|--------|
| JWT signature | Ed25519 vs bundled Root CA | Immediate lock |
| Thời hạn | `valid_until` > Monotonic Counter TPM | Immediate lock |
| Seat count | `active_device_keys` ≤ `max_seats` | Block new enrollment |
| AI tier | `ai_tier` field present + valid | Downgrade to local_only |
| BYOM slots | `byom_model_slots` ≥ active models | Block new BYOM upload |

### 13.5 Offline TTL Profile

```rust
pub enum OfflineTTLProfile {
    Consumer { ttl_hours: 24 },
    Enterprise { ttl_hours: u32 },
    GovMilitary { ttl_hours: 720 },
    AirGapped { revocation_only: bool },
}
```

### 13.6 Tiered Conflict Resolution (Shadow DAG)

```
Tier 1 (Online):       Shadow DAG full → User thấy conflict, chọn merge
Tier 2 (Mesh P2P):     Lightweight Conflict Marker → Desktop Super Node mediator
Tier 3 (Solo offline): Optimistic Append → WARNING "Bản này có thể bị ghi đè"
```

---

## §14 NETWORK LAYER DETAILS

### 14.1 QUIC/eBPF Scope Clarification

> ⚠️ **eBPF/XDP là server-side Linux kernel technology — KHÔNG phải client-side.**

Client không implement eBPF/XDP filtering. Client hưởng lợi từ server-side protection qua connection quality.

### 14.2 iOS WebRTC TURN — CallKit Integration

```swift
class TeraCallKitProvider: NSObject, CXProviderDelegate {
    // CXProvider giữ audio session active dù app background
    // TURN failover xảy ra trong CallKit context → không bị suspend
}
```

### 14.3 iOS AWDL Monitor — Hotspot/CarPlay Conflict

```swift
class AWDLMonitor {
    // NWPathMonitor detect AWDL interface + bridge
    // Callback → Rust Core downgrade Tier 2 → Tier 3 (BLE only)
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
```

### 14.6 Android 14+ Battery Bucket — FCM Throttle Handling

```kotlin
<uses-permission android:name="android.permission.USE_EXACT_ALARM"/>
// Companion Device Manager: REQUEST_COMPANION_RUN_IN_BACKGROUND
```

### 14.7 Shadow DB Write Lock Protocol

```rust
pub struct ShadowMigrationLock { migration_in_progress: AtomicBool }
```

---

## §15 CHAOS ENGINEERING GATE

> Tham chiếu đến → TERA-TEST cho chi tiết đầy đủ.

| Scenario | Điều kiện | Expected Behavior |
|----------|-----------|-------------------|
| SC-01 | iOS AWDL off + TURN failover + CRDT merge >5000 events | AWDL warn → BLE → TURN preconnect → CRDT queue |
| SC-02 | Jetsam kill NSE mid-WAL + Desktop offline + EMDP active | WAL rollback → DAG self-heal → EMDP key escrow |
| SC-03 | XPC Worker OOM + Smart Approval pending | Journal PENDING → abort → user re-sign prompt |
| SC-04 | Battery <20% + Mesh active + Whisper loading | Whisper disabled → Voice text-fallback → BLE only |
| SC-05 | AppArmor deny memfd + mlock + seccomp active | Graceful degrade to software crypto → performance warn |
| SC-06 | License expire T+0 + Active emergency call | Chat survives → Admin Console lock only |
| SC-07 | EMDP 60min + Desktop reconnect + 1000 relay messages | Key escrow decrypt → DAG merge → epoch reconcile |
| **SC-08** | **VPS Enclave cluster fully down during active AI session** | **Graceful fallback to local inference; AiEnclaveUnavailable signal; session ZeroizeOnDrop** |
| **SC-09** | **BYOM model BLAKE3 mismatch on Enclave node restart** | **Reject model load; ModelIntegrityViolation audit; all new AI requests route to fallback model** |
| **SC-10** | **Network partition between client and Enclave mid-inference** | **Client-side timeout 5s; session ZeroizeOnDrop; retry with local inference** |
| **SC-11** | **Blind RAG VectorDB unavailable during RAG-augmented query** | **Proceed without RAG context; user sees degraded AI response indicator** |

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
| **AI Hybrid** | **`AiBackendChanged`, `AiEnclaveUnavailable`, `AiSessionComplete`** | **UI HUD, Metrics** |
| **Model Integrity** | **`ModelIntegrityViolation`** | **Admin Console, Audit Log (CRITICAL)** |

### 16.2 Metrics

| Metric | Type | Notes |
|--------|------|-------|
| `message_e2ee_latency_ms` | Histogram | Per-platform |
| `mesh_active_peers` | Gauge | Updated per Gossip round |
| `dag_event_count` | Counter | Monitor growth rate |
| `wasm_execution_time_ms` | Histogram | Per .tapp DID |
| `egress_bytes_total` | Counter | Per .tapp DID; DLP alert |
| `protocol_latency_ms` | Histogram | Per protocol (QUIC/gRPC/WSS) |
| `license_heartbeat_status` | Gauge | 0=OK, 1=Warning, 2=Failed |
| **`ai_inference_latency_ms`** | **Histogram** | **{backend=local\|enclave, model_id}** |
| **`ai_enclave_cache_hit_rate`** | **Gauge** | **Semantic cache effectiveness** |
| **`ai_enclave_requests_total`** | **Counter** | **{status=success\|error\|timeout}** |
| **`ai_enclave_active_sessions`** | **Gauge** | **Current concurrent sessions** |
| **`blind_rag_query_latency_ms`** | **Histogram** | **ANN search + fetch + decrypt** |
| **`byom_model_load_success`** | **Counter** | **Per model_id** |
| **`ai_pii_redaction_entities`** | **Histogram** | **Entities redacted per request (count, not content)** |

### 16.3 Audit Trail

Mọi entry trong Audit Log phải có: `device_id`, `timestamp` (HLC), `payload_hash` (BLAKE3), `ed25519_sig`, `event_type`.

**Audit Log là Append-Only Immutable Hash Chain — không thể delete hoặc modify.**

Events bắt buộc phải ghi Audit Log:

- Mọi MLS Epoch Rotation
- Mọi Escrow Key usage
- Mọi FCP trigger
- Mọi Remote Wipe execution
- Mọi License validation failure
- Mọi Byzantine Shun issuance
- Mọi `EgressSchemaViolation`
- **Mọi BYOM model upload + load attempt** (bao gồm failures)
- **Mọi `ModelIntegrityViolation`** (BLAKE3 hoặc signature mismatch)
- **Mọi `AttestationFailed` event từ Enclave** (with device_id, not prompt content)
- **Mọi Blind RAG document upload** (doc_id, size_bucket, not content)

### 16.4 Zero-Knowledge Non-Repudiation (AI Egress)

```sql
INSERT INTO ai_egress_audit (
    request_id,
    backend_used,
    model_id,
    tokens_estimated,
    payload_size_bucket,
    rag_context_used,      -- boolean
    cache_hit,             -- boolean
    device_ed25519_sig
    -- NO prompt content, NO response content, NO session key
);
```

---

## §17 APPENDIX

### 17.1 Glossary

| Thuật ngữ | Định nghĩa |
|-----------|-----------|
| `.tapp` | Gói tiện ích: `logic.wasm` + JSON Schema UI. Chạy trong WASM Sandbox. |
| `Company_Key` | Khóa cấp Tenant, sinh khi Onboarding. Không rời thiết bị thành viên. |
| `Blind Relay` | Server chỉ chuyển tiếp ciphertext — không nắm key giải mã. |
| `TreeKEM` | Cấu trúc cây nhị phân trong MLS, phân phối khóa nhóm O(log n). |
| `HKMS` | Hierarchical Key Management System — Master Key → KEK → DEK. |
| `Sealed Sender` | Server biết gói tin đi đến đâu, nhưng không biết từ ai. |
| `cas_hash` | BLAKE3 của ciphertext dùng cho CAS path và dedup. |
| `ZeroizeOnDrop` | RAII pattern trong Rust: `Drop` trait ghi đè `0x00` lên toàn bộ struct. |
| `HLC` | Hybrid Logical Clock: `{wall_clock, logical_counter}`. |
| `DAG` | Directed Acyclic Graph — cấu trúc dữ liệu cho CRDT Event Log. |
| `CRDT` | Conflict-free Replicated Data Type. |
| `EMDP` | Emergency Mobile Dictator Protocol. iOS-only Mesh fallback. |
| `ISDM` | Interactive SLM Dual-Masking. PII tokenization trước khi gọi external LLM. |
| `SASB` | Strict AST Sanitization Bridge. AST-level XSS prevention cho AI response. |
| `EDES` | Edge Deterministic Entity Scanner. Aho-Corasick O(n) real-time PII scanner. |
| `SSA` | Stateful Semantic Accumulator. Sliding context buffer cho Salami Attack detection. |
| **`BYOM`** | **Bring Your Own Model. Enterprise mang custom AI model vào VPS Enclave.** |
| **`VPS Enclave`** | **Stateless AI inference cluster — không log, không persist plaintext.** |
| **`E2EE Prompt Tunneling`** | **Protocol mã hóa prompt trước khi rời thiết bị; chỉ ciphertext lên VPS.** |
| **`Blind RAG`** | **RAG architecture mà server chứa BlindVectors; không bao giờ thấy document plaintext.** |
| **`SanitizedPrompt`** | **Newtype wrapping String đã qua PII redaction; không thể tạo trực tiếp.** |
| **`SemanticCache`** | **Cache keyed by embedding hash; server không thể đọc cached prompt/response.** |
| **`InferenceSessionVault`** | **alias_map cho de-aliasing; ZeroizeOnDrop < 100ms sau mỗi inference.** |
| **`AI_Session_Key`** | **AES-256-GCM key ephemeral per AI session; derived từ Epoch_Key; ZeroizeOnDrop.** |
| **`EnclaveAttestation_Token`** | **Ed25519 signed JWT (TTL 60s) proving request from legitimate TeraChat app.** |
| **`BlindVector`** | **[f32; 384] embedding stored in VectorDB; no plaintext stored alongside.** |
| `ALPN` | Application-Layer Protocol Negotiation. |
| `W^X` | Write XOR Execute. iOS hardware policy cấm JIT. |
| `HPKP` | HTTP Public Key Pinning. |
| `VOPRF` | Verifiable Oblivious Pseudorandom Function. Blind Tokens cho anonymous rate limiting. |
| **`PagedAttention`** | **vLLM memory management — treats KV cache like virtual memory pages; 5-10× throughput.** |
| **`Continuous Batching`** | **vLLM scheduling — new requests join running batch; no waiting for full batch.** |

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
| AI Safety | §9.4 | §F-23 |
| **AI Hybrid Architecture** | **§F-23** | **§9.4, §3.7, §5.7, §F-04, §F-05** |
| Failure Handling | §10 | §F-xx Security Notes |
| Observability | §16 | §12.x, §9.x |

### 17.3 Out-of-Scope References

| Topic | Tài liệu |
|-------|---------|
| Client IPC bridges, OS hooks, WASM runtime client-side, AI Worker process OS integration | → TERA-FEAT |
| UI rendering, Glassmorphism, Animation states | → TERA-DESIGN |
| User flows, RBAC, Admin/User actions | → TERA-FUNC |
| Plugin lifecycle, ABI versioning, Publisher rules | → TERA-MKT |
| Chaos Engineering test scenarios | → TERA-TEST |
| Business model, pricing, GTM | → TERA-BIZ |

---

## §18 AI ENCLAVE INFRASTRUCTURE *(NEW)*

> Đây là phần đặc tả infrastructure cho VPS Enclave cluster. Phần §F-23 đặc tả protocol; phần này đặc tả deployment.

### 18.1 Infrastructure Requirements

**Minimum Production Cluster (shared Enclave):**

```yaml
load_balancer:
  type: HAProxy
  health_check_interval: 2s
  health_check_timeout: 1s
  backend_failover: immediate

inference_nodes:
  count: 2  # minimum HA
  per_node:
    vcpu: 8
    ram_gb: 32
    gpu: 1x A10G (24GB VRAM)
    storage: 100GB NVMe (model storage only)
    network: 10Gbps

semantic_cache:
  type: Redis-compatible (Valkey/KeyDB)
  memory_gb: 4
  persistence: disabled  # stateless by design
  eviction: allkeys-lru

vector_db:
  type: Qdrant
  memory_gb: 8  # for 10M vectors
  persistence: enabled  # vectors are not secret; safe to persist
  replication: 2

model_registry:
  type: MinIO (existing blob store)
  encryption: AES-256-GCM at rest
  access: Enclave nodes only (mTLS)
```

**Scaling Guidelines:**

- 1 A10G (24GB VRAM) → ~50 concurrent sessions with 7B model
- Add inference node for every 50 concurrent session headroom
- Semantic cache reduces inference load by 20-40% for common enterprise queries
- VectorDB scales horizontally via Qdrant distributed mode

### 18.2 Security Hardening (Enclave Cluster)

**Network isolation:**

```
Client → mTLS (per-device cert) → Load Balancer → Inference Node
                                                        │
                                              Internal-only network
                                                        │
                                          ┌─────────────┼─────────────┐
                                    Semantic Cache  VectorDB    Model Registry
                                    (no plaintext)  (vectors only)  (encrypted)
```

**Process isolation per Inference Node:**

- Each AI request runs in isolated ORT session — no shared state between sessions.
- Linux cgroups v2: per-request CPU/memory limits.
- seccomp-bpf: inference nodes cannot open arbitrary network connections (only allowed: MinIO for model loading, internal Redis/Qdrant).

**Immutable Enclave Nodes:**

- Nodes boot from read-only image; `/tmp` is tmpfs (cleared on reboot).
- No SSH, no console access in production; deployment via CI/CD pipeline only.
- System logs: only aggregate metrics pushed to OTEL Collector — no request-level logs.

### 18.3 BYOM Model Management

**Model Upload Flow (Admin only):**

```bash
# Admin CLI (runs locally, never uploads plaintext model weights)
terachat-admin byom upload \
  --model-path ./acme-llm-v2.onnx \
  --manifest ./acme-llm-v2.manifest.json \
  --publisher-key ./acme-publisher.pem \
  --workspace acme-corp-vn

# CLI operations:
# 1. Compute BLAKE3 hash locally
# 2. Sign manifest with publisher key
# 3. Request TeraChat CA counter-signature (requires Admin auth)
# 4. Upload encrypted model to MinIO (key = HKDF(Company_Key, model_id))
# 5. Register ModelManifest in BYOM Registry
# 6. Trigger Enclave node pre-load (async)
```

**Model Security Properties:**

- Model weights encrypted at rest with workspace-specific key.
- BLAKE3 verified on every Enclave node load (not just first load).
- If BLAKE3 mismatch → `ModelIntegrityViolation` audit event + model quarantined.
- Enclave nodes cannot access other workspaces' models (OPA policy enforcement).

### 18.4 Observability Stack Integration

The AI Enclave integrates with the existing OTEL stack defined in §16:

```
Inference Node → OTEL Collector → Prometheus → Grafana
                                → Loki (aggregate logs, no prompt content)
                                → Tempo (trace IDs, not content)

Metrics emitted (Zero-Knowledge):
  enclave_inference_latency_ms{backend, model_id, cache_hit}
  enclave_requests_total{status}
  enclave_gpu_utilization_pct
  enclave_active_sessions
  enclave_cache_hit_rate
  byom_model_load_duration_ms{model_id}
  blind_rag_ann_search_ms
  blind_rag_chunk_decrypt_ms
```

**Alert Rules:**

```yaml
- alert: EnclaveHighLatency
  expr: enclave_inference_latency_ms{quantile="0.99"} > 5000
  for: 5m
  labels: { severity: warning }

- alert: EnclaveAllNodesDown
  expr: count(up{job="enclave_node"} == 1) == 0
  for: 30s
  labels: { severity: critical }
  annotations:
    summary: "AI Enclave cluster fully down — clients falling back to local inference"

- alert: ModelIntegrityViolation
  expr: increase(byom_model_integrity_violations_total[5m]) > 0
  labels: { severity: critical }
  annotations:
    summary: "BYOM model BLAKE3 mismatch detected — potential supply chain attack"
```

---

*Xem → TERA-FEAT cho Client App-layer. Xem → TERA-FUNC cho Product flows.*
*AI Hybrid Architecture: §F-23 (protocol) + §18 (infrastructure) + TERA-FEAT §F-10 (client integration).*