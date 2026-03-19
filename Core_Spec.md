<!-- markdownlint-disable MD041 -->
```yaml
# DOCUMENT IDENTITY
id:        "TERA-CORE"
title:     "TeraChat — Core Technical Specification"
version:  "0.2.6"
status:    "ACTIVE — Implementation Reference"
date:      "2026-03-18"
audience:  "Backend Engineer, Distributed Systems Engineer, Security Engineer"
purpose:   "Defines core architecture: cryptography (MLS/E2EE), mesh networking, CRDT synchronization, and server infrastructure. Implementation-level only."

depends_on: []
consumed_by:
  - id: "TERA-FEAT"    # Client platform behavior, IPC, OS hooks
  - id: "TERA-DESIGN"  # UI state machine, animation triggers
  - id: "TERA-MKT"     # Plugin sandbox, .tapp publishing
  - id: "TERA-TEST"    # Chaos engineering scenarios

ai_routing_hint: |
  Route to this document for: MLS key management, E2EE protocol, BLE/Wi-Fi Direct
  mesh networking, CRDT DAG synchronization, server topology, Key Management System
  (HKMS), VPS relay architecture, bare-metal HSM deployment, ZeroizeOnDrop patterns,
  Hardware Root of Trust, Post-Quantum cryptography (ML-KEM-768), or CRDT split-brain
  reconciliation.

  Do NOT route here for: UI component behavior (→ TERA-DESIGN), platform IPC or OS
  hooks (→ TERA-FEAT), plugin lifecycle or Marketplace rules (→ TERA-MKT), or
  chaos test scenarios (→ TERA-TEST).
```

---

## §0 — DATA OBJECT CATALOG

> **Read this section in full before implementing any component.**
> Every object below is an independent data unit with a defined schema, lifecycle, and security constraint. Algorithms in §5–§7 are *operations* on these objects — not data definitions.

### §0.1 Cryptographic Identity Objects

| Object | Type | Storage Location | Lifecycle | Spec Ref |
| --- | --- | --- | --- | --- |
| `DeviceIdentityKey` | Ed25519 KeyPair | Secure Enclave / StrongBox / TPM 2.0 (hardware-bound) | Permanent; never exported from chip | §5.1 |
| `Company_Key` | AES-256-GCM root key | HKMS (wrapped by `DeviceIdentityKey`) | Per-workspace; rotated on member exit | §5.2 |
| `Epoch_Key` | MLS leaf key | RAM, `ZeroizeOnDrop` struct | Per MLS Epoch; zeroized on rotation | §5.3 |
| `ChunkKey` | AES-256-GCM ephemeral | Rust `ZeroizeOnDrop` struct | Single 2 MB chunk; zeroized immediately after use | §5.3 |
| `Session_Key` | X25519 ECDH-derived | RAM, `ZeroizeOnDrop` struct | Per session; zeroized on disconnect | §5.4 |
| `Push_Key_N` | HKDF-derived symmetric | Secure Enclave (iOS) / StrongBox (Android) | Rotated after each MLS Epoch rotation; one-way chain | §5.5 |
| `Fallback_KEK` | Argon2id-derived AES-256 | RAM only | Duration of PIN unlock flow; zeroized immediately | §5.1 |
| `Escrow_Key` | Shamir-reconstructed | `mlock`-protected RAM arena | < 100 ms during Lagrange interpolation; then zeroized | §5.1 |

### §0.2 MLS Session Objects

| Object | Type | Storage Location | Lifecycle | Spec Ref |
| --- | --- | --- | --- | --- |
| `KeyPackage` | MLS RFC 9420 struct | Server public index + `hot_dag.db` | Refreshed every 7 days or on epoch rotation | §5.3 |
| `Welcome_Packet` | ECIES-encrypted payload | In-flight; single-use | Consumed on group join; never persisted | §5.3 |
| `TreeKEM_Update_Path` | MLS tree delta | In-memory; broadcast | Per epoch rotation; never persisted | §5.3 |
| `Epoch_Ratchet` | Monotonic u64 counter | `hot_dag.db` KV | Monotonically increasing; never decremented | §5.3 |
| `Sender_Data_Secret` | HKDF-SHA256 output | RAM, `ZeroizeOnDrop` | Per MLS Epoch; zeroized on rotation | §5.3 |

### §0.3 Mesh Network Objects

| Object | Type | Storage Location | Lifecycle | Spec Ref |
| --- | --- | --- | --- | --- |
| `BLE_Stealth_Beacon` | 31-byte BLE ADV PDU | Air (broadcast only) | Ephemeral per 5-minute scan cycle | §6.3 |
| `Identity_Commitment` | `HMAC-BLAKE3(R, PK_identity)[0:8]` | Embedded in Beacon | Per session nonce; 5-minute rotation | §6.3 |
| `Shun_Record` | `{Node_ID, Ed25519_Sig, HLC_Timestamp}` | `hot_dag.db` broadcast | Until Admin revokes or node re-provisions | §6.6 |
| `MergeCandidate` | `{Node_ID, BLAKE3_Hash, HLC_Timestamp}` | RAM only | Duration of split-brain resolution | §7.3 |
| `EmdpKeyEscrow` | `{relay_session_key: AesKey256, emdp_start_epoch: u64, expires_at: u64}` | BLE transfer; RAM on receiver | 60-minute TTL; destroyed on Desktop reconnect | §6.7 |

### §0.4 DAG State Objects

| Object | Type | Storage Location | Lifecycle | Spec Ref |
| --- | --- | --- | --- | --- |
| `CRDT_Event` | Typed append-only log entry | `hot_dag.db` (SQLite WAL) | Permanent; append-only; never physically deleted | §7.1 |
| `HLC_Timestamp` | `{wall_ms: u64, logical: u32, node_id: [u8;16]}` | Embedded in every `CRDT_Event` | Immutable after write | §7.2 |
| `Tombstone_Stub` | `{entity_id: Uuid, hlc: HLC_Timestamp, type: DELETED}` | `cold_state.db` | Permanent; replaces physically deleted records | §7.1 |
| `Hash_Frontier` | `{vector_clock: HashMap<NodeId,u64>, root_hash: [u8;32]}` | `hot_dag.db`; updated per Gossip round | Latest value; overwritten each round | §7.3 |

### §0.5 Infrastructure & Recovery Objects

| Object | Type | Storage Location | Lifecycle | Spec Ref |
| --- | --- | --- | --- | --- |
| `Snapshot_CAS` | `SHA-256(snapshot_content)` content-addressable hash | TeraVault VFS | Permanent | §7.4 |
| `Hydration_Checkpoint` | `{snapshot_cas_uuid: Uuid, last_chunk_index: u32}` | `hot_dag.db` KV | Overwritten on each successful chunk commit | →TERA-FEAT §3 |
| `Monotonic_Counter` | TPM 2.0 hardware counter | TPM chip register | Hardware-bound; only increments; tamper-evident | §5.1 |
| `WalStagingEntry` | `{event_id: Uuid, payload: Bytes, status: Staged\|Committed}` | `wal_staging.db` | Written before MPSC; deleted on Committed | §9.3 |
| `NetworkProfile` | `{network_id: [u8;32], strict_compliance: bool, probe_fail_count: u8}` | SQLite local config | Persisted; reset on network change | §9.2 |

---

## 1. SYSTEM OVERVIEW

### 1.1 Purpose

TeraChat is an enterprise-grade, Zero-Knowledge encrypted messaging platform. The server acts as a blind relay — it routes ciphertext and has zero access to plaintext, sender identity, or message content under any operational condition, including HSM compromise.

### 1.2 System Topology Diagram

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
│                                                                     │
│  📱 iOS    📱 Android    📱 Huawei    💻 macOS    🖥️ Win/Linux      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Rust Core (shared binary)                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │   │
│  │  │  MLS / E2EE  │  │     Mesh     │  │  CRDT / DAG  │      │   │
│  │  │    Engine    │  │  Transport   │  │     Sync     │      │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘      │   │
│  │         ↑ ZeroizeOnDrop boundary enforced at all exits ↑    │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ TLS 1.3 + mTLS (all channels)
┌──────────────────────────────▼──────────────────────────────────────┐
│                          SERVER LAYER                               │
│                                                                     │
│  ☁️ VPS Relay Cluster                │  🗄️ Bare-metal HSM Node      │
│  ┌──────────────────────────────┐   │  ┌──────────────────────┐   │
│  │  Rust Blind Relay Daemon     │   │  │  HSM FIPS 140-3 L3   │   │
│  │  Tokio + io_uring            │   │  │  KMS Bootstrap       │   │
│  │  SQLite WAL (relay state)    │   │  │  Shamir M-of-N       │   │
│  │  Redis / NATS JetStream      │   │  │  PostgreSQL Primary   │   │
│  │  HA TURN Array               │   │  │  MinIO Blind Storage  │   │
│  └──────────────────────────────┘   │  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 In-Scope / Out-of-Scope

| In-Scope (this document) | Out-of-Scope (see reference) |
| --- | --- |
| MLS key lifecycle, E2EE encryption | Client IPC bridge, OS hooks → TERA-FEAT |
| Mesh BLE/Wi-Fi Direct protocol | UI state machine, animations → TERA-DESIGN |
| CRDT DAG synchronization | Plugin sandbox, `.tapp` publishing → TERA-MKT |
| Message lifecycle, data flow | Combined-failure test scenarios → TERA-TEST |
| VPS relay and bare-metal infrastructure | Code signing pipeline → `ops/signing-pipeline.md` |
| Performance targets and scaling ceilings | Disaster recovery runbooks → `ops/db-recovery.md` |

### 1.4 Zero-Knowledge Guarantee

The Zero-Knowledge guarantee holds if and only if all three conditions are simultaneously true:

1. Every payload is encrypted by the sender device using `Company_Key` before leaving the device.
2. The server stores only `{destination_device_id, ciphertext_blob, timestamp}`. No plaintext, no sender identity, no content metadata exists anywhere on the server.
3. `Company_Key` cannot be derived by the server under any condition, including physical HSM seizure, because the HSM holds only the Master Key used to wrap workspace keys — not the workspace keys themselves.

These conditions are structurally enforced by the Blind Relay architecture (§9.2), not by operational policy.

---

## 2. DESIGN PRINCIPLES

### 2.1 Core Invariants

The following invariants hold across all environments and all operational conditions without exception:

| ID | Invariant | Enforcement Mechanism |
| --- | --- | --- |
| INV-01 | Private keys never leave hardware chip | Secure Enclave / StrongBox / TPM 2.0 hardware binding; no export API called |
| INV-02 | Plaintext never persists beyond scope | `ZeroizeOnDrop` RAII on every struct holding plaintext; verified with Miri CI |
| INV-03 | All network I/O is TLS 1.3 + mTLS encrypted | `rustls` enforces; SHA-256 SPKI pinning hardcoded in binary |
| INV-04 | DB schema changes are backward-compatible with WAL replay | Migration scripts mandatory; `BEGIN EXCLUSIVE TRANSACTION`; backup before migration |
| INV-05 | Crypto operations use approved libraries only | `ring` crate or `RustCrypto` workspace; no custom crypto; no C library wrapping |
| INV-06 | Every Audit Log entry carries a valid Ed25519 signature | Unsigned entries rejected at write time; never stored |
| INV-07 | No raw FFI pointer crosses the Rust Core boundary | Token protocol (`tera_buf_acquire` / `tera_buf_release`) mandatory; enforced by CI Clippy lint |
| INV-08 | `hot_dag.db` is append-only | Physical deletion of CRDT events is forbidden; tombstones only |

### 2.2 Shared Rust Core Principle

All cryptographic and synchronization logic resides in a **single Rust binary** compiled to native code for every target platform. The UI layer (React Native / Flutter / Tauri) is a pure renderer — it holds no crypto keys and no business state.

**Control Plane (Core → UI):** Protobuf messages < 1 KB over JSI HostObject (iOS) / Dart FFI (Android) / SharedArrayBuffer (Desktop). Used for state signals and commands only.

**Data Plane (Core → UI, zero-copy):**

- iOS: C++ JSI Shared Memory Pointer via `UniquePtr` wrapper. Throughput ~400 MB/s.
- Android: Dart FFI `TypedData` zero-copy into C ABI. Throughput ~400 MB/s.
- Desktop: `SharedArrayBuffer` 10 MB ring buffer, 2 MB chunks. Throughput ~500 MB/s. Requires `COOP+COEP` headers.

**State flow (unidirectional — no exceptions):** Rust Core emits `StateChanged(table: &str, version: u64)`. UI pulls snapshot for current viewport. UI never writes state to Core. UI never holds decrypted payloads beyond the render frame.

### 2.3 Separation of Concerns

| Layer | Owns | Forbidden |
| --- | --- | --- |
| Rust Core | MLS state, key lifecycle, CRDT DAG, network transport | UI rendering, platform OS API calls |
| UI Layer | Viewport state, animation, user input handling | Crypto operations, direct DB writes |
| VPS Relay | Ciphertext routing, pub/sub fanout | Decryption, sender identification, content inspection |
| Bare-metal HSM Node | Master key custody, Shamir ceremony, PostgreSQL primary | Message routing, plaintext storage |

---

## 3. PLATFORM SEGMENTATION

### 3.1 Platform Behavior Matrix — Runtime Capabilities

| Capability | 📱 iOS | 📱 Android | 📱 Huawei | 💻 macOS | 🖥️ Windows | 🖥️ Linux | 🗄️ Bare-metal | ☁️ VPS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WASM JIT (wasmtime) | ❌ W^X | ✅ | ✅ | ✅ XPC Worker | ✅ | ✅ | N/A | N/A |
| WASM Interpreter (wasm3) | ✅ primary | Fallback | Fallback | Fallback | Fallback | Fallback | N/A | N/A |
| Hardware Secure Storage | ✅ SEP | ✅ StrongBox | ✅ TrustZone TEE | ✅ SEP | ✅ TPM 2.0 | ✅ TPM 2.0 | ✅ HSM PKCS#11 | N/A |
| `mlock()` | ❌ Jetsam | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Background BLE | ✅ iBeacon | ✅ CDM | ✅ HMS | ✅ | ✅ | ✅ | N/A | N/A |
| Wi-Fi Direct / AWDL | ✅ AWDL | ✅ WifiP2P | ✅ HarmonyOS P2P | ✅ AWDL | ✅ WFD | ✅ WFD | N/A | N/A |
| Mesh Super Node eligible | ❌ always Leaf | ✅ if RAM ≥ 3 GB | ✅ if RAM ≥ 3 GB | ✅ | ✅ | ✅ | N/A | N/A |
| Push channel | APNs / NSE | FCM high-priority | HMS Push Kit | APNs | WNS | systemd socket | N/A | N/A |
| CRL refresh max latency | ≤ 30 min | ≤ 30 min | ≤ 4 h (polling) | ≤ 30 min | ≤ 30 min | ≤ 30 min | N/A | N/A |
| eBPF / XDP | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ server-side only | ✅ server-side only |

> **Note:** eBPF/XDP is strictly server-side Linux kernel technology. Client platforms do not and cannot use eBPF. Desktop Linux uses `seccomp-bpf` for syscall filtering only — a different subsystem. This scope boundary is hard-enforced.

### 3.2 Platform Behavior Matrix — Private Key Storage

| Platform | Storage Location | API | Biometric Gate |
| --- | --- | --- | --- |
| 📱 iOS | Secure Enclave Processor (SEP) | `kSecAttrTokenIDSecureEnclave` + `kSecAccessControlBiometryCurrentSet` | FaceID / TouchID — required |
| 📱 Android | StrongBox Keymaster HAL | `KeyGenParameterSpec.Builder.setIsStrongBoxBacked(true)` | `BiometricPrompt` — required |
| 📱 Huawei | TrustZone TEE via HMS | `HMS SafetyDetect DeviceIntegrity()` | HMS Biometric — required |
| 💻 macOS | Secure Enclave Processor | `CryptoTokenKit` + `kSecAttrTokenIDSecureEnclave` | Touch ID / Apple Watch |
| 🖥️ Windows | TPM 2.0 chip | `CNG Microsoft Platform Crypto Provider` | Windows Hello |
| 🖥️ Linux | TPM 2.0 chip | `tpm2-pkcs11` PKCS#11 interface | PIN — required |
| 🗄️ Bare-metal | HSM FIPS 140-3 Level 3 | PKCS#11 (`SafeNet` / `Viettel CA`) | Physical presence + Shamir quorum |

**Hard rule:** `DeviceIdentityKey` never leaves the hardware boundary. Any code path that attempts to export, copy, or serialize a private key to heap, disk, or network is a **blocker — do not merge**.

### 3.3 Platform Behavior Matrix — RAM Budget (Mobile)

| Component | RAM ≤ 3 GB device (iPhone SE, budget Android) | RAM > 4 GB device (iPhone Pro, flagship) |
| --- | --- | --- |
| NSE / FCM service | 20 MB hard ceiling (OS-enforced) | 20 MB hard ceiling |
| WASM heap per `.tapp` | 50 MB; max 1 pre-warm | 50 MB; max 2 pre-warm |
| Whisper voice model | Disabled | Tiny model (39 MB) |
| BLE Mesh buffer | 8 MB | 12 MB |
| ONNX / embedding pipeline | 8 MB hard ceiling (custom allocator) | 8 MB hard ceiling |
| **Total ceiling** | **≤ 100 MB** | **≤ 130 MB** |

`MemoryArbiter` (Rust Core) reads `sysinfo::available_memory()` at startup and enforces ceilings. Any component requesting memory beyond its allocation receives `MemoryDenied` and must degrade gracefully (not crash).

### 3.4 Platform Behavior Matrix — Mesh Role Eligibility

| Role | Eligible Platforms | Required Conditions | On Condition Failure |
| --- | --- | --- | --- |
| Super Node (Backbone) | 💻 macOS, 🖥️ Windows, 🖥️ Linux | AC powered or battery ≥ 60% | Downgrade to Relay Node |
| Relay Node | 📱 Android (RAM ≥ 3 GB), 💻 💻 🖥️ | Battery ≥ 40% | Downgrade to Leaf Node |
| Tactical Relay (EMDP only) | 📱 iOS, 📱 Android | No Desktop present; battery > 20% | SoloAppendOnly mode |
| Leaf Node | 📱 iOS (always), 📱 low-battery | Default for iOS | N/A |
| Border Node | Any device | Both Internet and BLE active simultaneously | N/A |

**Hard rule:** iOS `election_weight = 0`. iOS is never elected Merge Dictator under any condition. See §6.7 for the EMDP exception and its strict constraints.

### 3.5 Platform Behavior Matrix — Hardware-Backed Signing API

| Platform | Signing API | Authentication Mechanism |
| --- | --- | --- |
| 📱 iOS | `SecKeyCreateSignature` via `LAContext` | `.biometryCurrentSet` flag |
| 📱 Android | `BiometricPrompt` + Hardware Keystore | `setUserAuthenticationRequired(true)` |
| 💻 macOS | `CryptoTokenKit` | `kSecAttrTokenIDSecureEnclave` |
| 🖥️ Windows | `CNG` (Cryptography Next Generation) | `Microsoft Platform Crypto Provider (TPM 2.0)` |
| 🗄️ Gov-grade | PKCS#11 | `SafeNet` / VNPT CA hardware token |

---

### 3.6 AI / SLM Infrastructure

**Process isolation:** AI inference runs in a dedicated OS process (`terachat-ai-worker`),
separate from Rust Core. Crash of the AI worker MUST NOT propagate to Core. `catch_unwind`
boundary enforced at worker entry (§4.4).

**Module map:**

```text
infra/ai_worker.rs
  § Responsibilities: ONNX/CoreML inference orchestration, Micro-NER PII pipeline,
                      SessionVault lifecycle, KV-Cache management, quota enforcement
  § Interfaces:
      run_inference(prompt: SanitizedPrompt) -> Result<Vec<ASTNode>, AiError>
      redact_pii(text: &str) -> (RedactedText, AliasMap)
      restore_pii(response: &str, alias_map: AliasMap) -> String
  § Dependencies: crypto/zeroize.rs (SessionVault), ffi/ipc_bridge.rs (CoreSignal),
                  infra/metrics.rs (quota counters)
```

**`SessionVault` struct (canonical definition):**

```rust
/// Holds PII alias map during a single LLM request-response cycle.
/// ZeroizeOnDrop clears alias map within 100 ms of response delivery.
#[derive(ZeroizeOnDrop)]
pub struct SessionVault {
    alias_map: HashMap<String, String>,  // { "[REDACTED_EMAIL_1]" → "real@email.com" }
    created_at: Instant,
}

impl SessionVault {
    /// Alias map MUST be dropped before any UI render frame.
    /// On drop: HashMap contents are overwritten with 0x00 via ZeroizeOnDrop.
    pub fn restore_and_drop(self, response: &str) -> String { ... }
}
```

**Micro-NER module (PII detection):**

- Runtime: ONNX model, < 1 MB compiled size. Loaded by `MemoryArbiter` at AI worker startup.
- Input: raw user prompt string.
- Output: `Vec<PiiSpan { start: usize, end: usize, kind: PiiKind }>`.
- `PiiKind`: `Name | Phone | Email | NationalId | BankAccount | Address`.
- Hard ceiling: 8 MB total RAM for ONNX allocator (custom allocator returns `AllocError` on overflow).
- On `AllocError`: fall back to regex-only detection (lower recall, no crash).

**AI quota enforcement (server-side validated):**

```rust
pub struct AiQuota {
    tokens_used_this_hour: AtomicU64,
    limit:                 u64,              // 10_000 consumer; u64::MAX enterprise
    reset_at:              Instant,
}

// Quota check MUST occur inside Rust Core before dispatching to AI worker.
// UI never has direct access to quota state.
```

**Platform-specific runtime selection:**

| Platform | Runtime | Max model size | Notes |
| --- | --- | --- | --- |
| 📱 iOS | CoreML (`.mlmodelc`) | 74 MB (Base), 39 MB (Tiny) | W^X: no dynamic WASM AI modules |
| 📱 Android | ONNX Runtime | 39 MB (Tiny) if RAM > 100 MB | HiAI fallback on Huawei |
| 📱 Huawei | HiAI / ONNX | 39 MB (Tiny) | AOT bundled only |
| 💻 macOS | ONNX / CoreML | 74 MB (Base) | XPC Worker isolation |
| 🖥️ Windows/Linux | ONNX Runtime | 74 MB (Base) | CPU inference; GPU optional |

**Security constraints:**

- AI worker has NO access to `hot_dag.db` or `cold_state.db` directly.
  All context is passed as sanitized `SanitizedPrompt` from Rust Core.
- `SanitizedPrompt` is a newtype wrapping `String` — construction requires PII redaction pass.
- LLM response delivered to `.tapp` as `Vec<ASTNode>` only. Raw HTML/Markdown rejected by AST Sanitizer.
- `SessionVault` MUST be dropped before `CoreSignal::StateChanged` is emitted.

## 4. CORE MODULE ARCHITECTURE

### 4.1 Module Map and Responsibilities

```text
terachat-core/
├── crypto/
│   ├── hkms.rs            § Responsibilities: Master Key lifecycle, KEK derivation, workspace init
│   │                      § Interfaces: init_workspace(), derive_kek(), remote_wipe()
│   │                      § Dependencies: ring crate, Secure Enclave / TPM FFI
│   ├── mls_engine.rs      § Responsibilities: MLS RFC 9420 state machine, TreeKEM, epoch rotation
│   │                      § Interfaces: create_group(), add_member(), remove_member(), encrypt(), decrypt()
│   │                      § Dependencies: hkms.rs, ring crate
│   ├── pq_kem.rs          § Responsibilities: ML-KEM-768 + X25519 hybrid, CNSA 2.0 compliance
│   │                      § Interfaces: hybrid_keygen(), hybrid_encap(), hybrid_decap()
│   │                      § Dependencies: ring crate, RustCrypto ml-kem crate
│   ├── push_ratchet.rs    § Responsibilities: OOB push key chain, NSE/FCM key versioning
│   │                      § Interfaces: derive_push_key(epoch), rotate_push_key()
│   │                      § Dependencies: hkms.rs
│   └── zeroize.rs         § Responsibilities: ZeroizeOnDrop wrappers, Miri-verifiable patterns
│                          § Interfaces: SecureBuffer<T>, SecureArena
│                          § Dependencies: zeroize crate
├── mesh/
│   ├── transport.rs       § Responsibilities: MeshTransport trait definition; platform-agnostic routing
│   │                      § Interfaces: send(), recv_stream(), discover_peers()
│   │                      § Dependencies: None (trait only; implementations in host layer)
│   ├── ble_beacon.rs      § Responsibilities: Stealth beacon construction, HMAC-BLAKE3 encoding
│   │                      § Interfaces: build_beacon(), verify_beacon()
│   │                      § Dependencies: ring crate, transport.rs
│   ├── duty_cycle.rs      § Responsibilities: BLE power management, TDM slot scheduling
│   │                      § Interfaces: start_duty_cycle(), set_standby_mode()
│   │                      § Dependencies: transport.rs
│   ├── election.rs        § Responsibilities: BLAKE3 Dictator election, EMDP Tactical Relay selection
│   │                      § Interfaces: elect_dictator(), elect_tactical_relay()
│   │                      § Dependencies: crdt/hlc.rs
│   ├── emdp.rs            § Responsibilities: Emergency Mobile Dictator Protocol, key escrow
│   │                      § Interfaces: build_escrow(), transfer_escrow(), extend_ttl()
│   │                      § Dependencies: crypto/pq_kem.rs, election.rs
│   └── anti_spam.rs       § Responsibilities: PoW challenges, Byzantine quarantine, Shun propagation
│                          § Interfaces: verify_pow(), quarantine_node(), broadcast_shun()
│                          § Dependencies: transport.rs, crdt/dag.rs
├── crdt/
│   ├── dag.rs             § Responsibilities: Append-only DAG, event validation, Ed25519 verification
│   │                      § Interfaces: append_event(), get_event(), get_parents()
│   │                      § Dependencies: crypto/hkms.rs, hlc.rs
│   ├── hlc.rs             § Responsibilities: Hybrid Logical Clock, total ordering, causality
│   │                      § Interfaces: new_timestamp(), update_on_receive(), compare()
│   │                      § Dependencies: None
│   ├── reconcile.rs       § Responsibilities: Split-brain merge, Gossip frontier exchange
│   │                      § Interfaces: merge_partitions(), exchange_frontier(), resolve_conflict()
│   │                      § Dependencies: dag.rs, hlc.rs, mesh/election.rs
│   └── snapshot.rs        § Responsibilities: Materialized snapshot export, recovery bootstrap
│                          § Interfaces: export_snapshot(), apply_snapshot(), verify_cas()
│                          § Dependencies: dag.rs
├── infra/
│   ├── relay.rs           § Responsibilities: Blind Relay daemon, ciphertext routing, MPSC dispatch
│   │                      § Interfaces: start_relay(), handle_connection(), dispatch_message()
│   │                      § Dependencies: wal_staging.rs, metrics.rs
│   ├── wal_staging.rs     § Responsibilities: At-least-once delivery guarantee, staging lifecycle
│   │                      § Interfaces: stage_event(), commit_event(), replay_staged()
│   │                      § Dependencies: SQLite (rusqlite crate)
│   ├── metrics.rs         § Responsibilities: Prometheus /metrics endpoint, zero-knowledge counters
│   │                      § Interfaces: increment(), observe(), export()
│   │                      § Dependencies: prometheus crate
│   └── federation.rs      § Responsibilities: Cross-cluster mTLS bridge, schema version negotiation
│                          § Interfaces: handshake(), forward_message(), reject_incompatible()
│                          § Dependencies: relay.rs
└── ffi/
    ├── token_protocol.rs  § Responsibilities: tera_buf_acquire / tera_buf_release token lifecycle
    │                      § Interfaces: tera_buf_acquire(u64) -> u64, tera_buf_release(u64)
    │                      § Dependencies: crypto/zeroize.rs
    └── ipc_bridge.rs      § Responsibilities: Control/Data plane signal emission, command receipt
                           § Interfaces: emit_signal(), recv_command()
                           § Dependencies: All Core modules (read-only signal emission)
```

### 4.2 IPC Signal and Command Contract

**Signals emitted by Core (Core → UI, unidirectional):**

```rust
pub enum CoreSignal {
    StateChanged      { table: &'static str, version: u64 },
    ComponentFault    { component: &'static str, severity: FaultSeverity },
    MeshRoleChanged   { new_role: MeshRole },
    EmdpExpiryWarning { minutes_remaining: u32 },   // emitted at T-10 min and T-2 min
    DeadManWarning    { hours_remaining: u32 },      // emitted at T-12 h and T-1 h
    TierChanged       { new_tier: NetworkTier, reason: TierChangeReason },
    DagMergeProgress  { completed: u64, total: u64 }, // emitted every 200 ms when backlog > 500
}
```

**Commands received by Core (UI → Core):**

```rust
pub enum UICommand {
    ScrollViewport    { top_message_id: Uuid, bottom_message_id: Uuid },
    SendMessage       { recipient_did: DeviceId, plaintext: Vec<u8> },
    RequestMeshActivation,
    ReleaseBuffer     { token: u64 },
    CancelTask        { message_id: Uuid },
}
```

UI never modifies Core state directly. UI never holds decrypted payloads beyond the render frame.

### 4.3 FFI Token Protocol

<!-- INSERTED PATCH: Formal IPC Memory Ownership Contract -->
- 🔗 Token expiration is NOT automatic — tokens are only released upon explicit call execution.
- 🔗 TTL timeouts MUST trigger a UI notification to the user, strictly avoiding silent auto-zeroization to protect against dangling pointer read-flashes in the Dart GC gap.

```rust
pub struct TokenRegistry {
    tokens: DashMap<TokenId, TokenEntry>,
}

impl TokenRegistry {
    /// Rust will NOT automatically expire tokens.
    /// Emits a warning signal to Dart/UI directing UI to initiate an explicit release.
    pub async fn check_ttl_warnings(&self) {
        // ... (Warning trigger execution details)
    }

    /// Memory Release strictly relies on explicit Dart invocation.
    pub fn release(&self, token_id: TokenId) -> Result<(), TokenError> {
        // ... (Manual Token Drop processing rules)
    }
}
```


Every FFI endpoint that transfers buffer ownership uses the token protocol. Raw pointer return (`*const u8`, `*mut u8`, `Vec<u8>`) from any `pub extern "C"` function is a **blocker**.

```rust
/// Returns an opaque u64 token — never a raw pointer.
#[no_mangle]
pub extern "C" fn tera_buf_acquire(operation_id: u64) -> u64;

/// Triggers ZeroizeOnDrop when ref_count reaches 0.
#[no_mangle]
pub extern "C" fn tera_buf_release(token: u64);
```

Rust Core maintains an atomic reference counter per token. `ZeroizeOnDrop` executes only when `ref_count == 0`. iOS JSI calls `tera_buf_release()` in the C++ destructor. Android Dart FFI calls it in the Dart `NativeFinalizer`. This eliminates the GC race condition on Dart `NativeFinalizer`.

**CI enforcement:** Custom Clippy lint in `ffi/` rejects any `pub extern "C"` function returning `Vec<u8>`, `*const u8`, or `*mut u8` without routing through the token protocol. Lint failure blocks merge.

### 4.4 Component Fault Isolation

Relay binary and mobile library use `panic = 'unwind'`. Binary size increases ~15% due to unwind tables. This is accepted.

**Required `catch_unwind()` boundaries:**

- WASM sandbox execution entry
- CRDT merge function entry
- MLS crypto operations entry
- DAG write entry

**Caught panic handling — mandatory sequence:**

1. Log structured context: `{component: &str, operation: &str}`. No plaintext data in log entry.
2. Emit `CoreSignal::ComponentFault { component, severity }` via IPC.
3. Stop accepting new requests to that component (quarantine).
4. Schedule component restart after exactly 1-second delay via Tokio task.

**Relay SIGTERM handler:**

```rust
tokio::signal::ctrl_c().await?;
let result = timeout(
    Duration::from_secs(30),
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
).await;
// Exit regardless of checkpoint result after 30 s
process::exit(0);
```

systemd unit: `TimeoutStopSec = 35` (5-second margin).

---

## 5. CRYPTOGRAPHY (MLS, E2EE)

### 5.1 Key Management System (HKMS)

<!-- INSERTED PATCH: Bloom Filter CRL -->
- ☁️ Static Bloom Filters have been entirely superseded by a `RotatingCrlFilter` implementation. Time-window intervals require full array rotation sequentially every 24 hours.
- ☁️ False positive resolutions strictly mandate an inline verification check against Merkle Proof authorities.

```rust
pub struct RotatingCrlFilter {
    /// Employs active filters representing current and prior epochs
    current: BloomFilter,
    previous: BloomFilter,
    current_epoch: u64,
    epoch_start: Instant,
    /// Mandated Epoch duration parameter constraints (24 hours)
    epoch_duration: Duration,
}
```


**Key hierarchy:**

```text
[Master Key] ─── HSM PKCS#11 / TPM 2.0 / Secure Enclave (never leaves chip)
      │
      └──► [KEK — Key Encryption Key] ─── decrypted in RAM, ZeroizeOnDrop
                 │
                 └──► [DEK — Data Encryption Key] ─── per-content encryption
                            │
                            └──► DB rows / File chunks / Channel keys / Push keys
```

**Workspace bootstrap sequence:**

1. Admin initiates workspace creation on a trusted device.
2. Rust Core generates `terachat_master_<domain>.terakey` (Master Key wrapped with AES-256 using Admin password + Argon2id-derived KEK).
3. Rust Core **blocks all DB writes** until Admin confirms Key Backup is stored.
4. Shamir Secret Sharing: Master Key split into N shards. Each shard stored in a distinct Admin device's Secure Enclave / StrongBox. Default: 3-of-5. Configurable: M-of-N via `workspace_policy.json`.
5. `Company_Key` derived: `HKDF-SHA256(Master_Key, "company-key-v1" || workspace_id)`.

**Shamir reconstruction (legal hold / disaster recovery):**

- M Admin devices present their shards via biometric-authenticated FFI call.
- Lagrange interpolation runs in `mlock`-protected RAM arena.
- Reconstructed `Escrow_Key` exists in RAM for < 100 ms.
- `ZeroizeOnDrop` clears arena immediately after use.
- Every reconstruction event is written to Append-Only Audit Log with Ed25519 signature.

**Dead Man Switch:**

- Monotonic hardware counter stored in TPM 2.0 / Secure Enclave / StrongBox.
- Counter increments on every DB unlock.
- Server stores `last_valid_counter`. If `device_counter < server_counter` → reject + initiate Self-Destruct.
- Grace period: Admin-configurable per user group (`max_offline_hours`, range 24–168 h, default 72 h), baked into License JWT field `offline_ttl_hours`.
- Warning signals: `CoreSignal::DeadManWarning { hours_remaining }` at T-12 h and T-1 h.
- **Exception:** Dead Man Switch lockout does NOT interrupt an active CallKit session. Lockout is deferred until the call ends. This matches `TestMatrix SC-06` expected behavior.

**TPM Counter Reset Recovery (Admin-Initiated Ceremony):**

Trigger conditions for counter desynchronization:

- Device RMA (hardware replacement).
- Enterprise re-imaging that resets TPM.
- Migration to a new device without BIP-39 mnemonic flow.

**Recovery protocol:**

```text
Precondition: Admin authenticates on a separate trusted device (biometric + Shamir quorum not
              required — standard Admin mTLS cert sufficient).

Step 1: Admin opens CISO Console → Device Management → [Target Device] → "Reset Counter Sync".
Step 2: Server sets a one-time `counter_reset_token { device_id, nonce, expires_at: now()+3600 }`.
        Token is Ed25519-signed by Admin's DeviceIdentityKey. Stored in PostgreSQL, single-use.
Step 3: Target device, on next connection attempt, detects `counter_mismatch` rejection.
        Core emits `CoreSignal::DeadManWarning { hours_remaining: 0 }` with reason `COUNTER_MISMATCH`.
        UI presents: "Device identity requires Admin re-authorization. Contact your Administrator."
Step 4: Admin sends `counter_reset_token` out-of-band to user (secure channel, e.g. another app).
Step 5: User enters token on device. Core verifies Ed25519 signature against Admin's public key.
Step 6: On valid token:
          a. Server resets `last_valid_counter` to current device TPM counter value.
          b. `counter_reset_token` marked `used = true` in PostgreSQL (idempotent; replay-safe).
          c. Device re-enrolls normally.
          d. Audit Log records: { event: "COUNTER_RESET", device_id, admin_did, timestamp }.
Step 7: On invalid/expired token: reject silently. Audit Log records failed attempt.
```

**Hard constraints:**

- `counter_reset_token` is single-use. Replay → silent reject + Audit Log entry.
- TTL: 1 hour. Expired token → reject. Admin must issue new token.
- Admin cannot reset counter for their own device (self-signing prohibited). Requires a second Admin.
- Maximum 3 counter resets per device per 30-day window (prevents abuse). 4th attempt → CISO alert.
- This recovery path does NOT bypass Self-Destruct if it has already executed. Self-Destruct is
  irreversible by design.

**Audit Log entry (mandatory):**

```rust
AuditLogEntry {
    event_type: EventType::CounterReset,
    target_device_id: DeviceId,
    authorized_by_admin_did: DeviceId,
    token_nonce: [u8; 32],
    hlc: HLCTimestamp,
    signature: Ed25519Signature,  // signed by Admin's DeviceIdentityKey
}
```

**Runbook reference:** `ops/counter-reset-ceremony.md` (must be created).

**Offline TTL profiles:**

```rust
pub enum OfflineTTLProfile {
    Consumer    { ttl_hours: u32 },          // default: 24
    Enterprise  { ttl_hours: u32 },          // Admin-configurable; baked into JWT
    GovMilitary { ttl_hours: u32 },          // default: 720 (30 days)
    AirGapped   { revocation_only: bool },   // local validation; no phone-home
}
```

**Remote Wipe — guaranteed execution sequence:**

1. `self.userID` detected in `removedMembers` of an MLS Commit.
2. Delete `DeviceIdentityKey` from Secure Enclave / StrongBox / TPM 2.0.
3. Drop all tables in `hot_dag.db` and `cold_state.db`.
4. Delete all WASM sandbox storage files.
5. Execution wrapped in `autoreleasepool` (iOS) / `try-finally` (Android) — cannot be interrupted by user process.

### 5.2 Hardware Root of Trust & Anti-Extraction

**Biometric-bound key initialization (all platforms):**

```rust
// Pseudocode — platform-specific via FFI
let device_key = hardware_enclave::generate_key(
    algorithm: Ed25519,
    access_control: BiometryCurrentSet | DevicePasscode,
    permanent: true,
)?;
let oidc_token_signed = device_key.sign(oidc_id_token)?;
// On hardware error:
oidc_id_token.zeroize(); // ZeroizeOnDrop enforced
```

**Enterprise PIN Fallback (Dual-Wrapped KEK):**

- PIN is 6 digits. Transmitted via FFI Pointer — never through UI state buffer.
- Argon2id derivation: `m = 64 MB`, `t = 3`, `p = 1` → `Fallback_KEK`. Resistant to GPU/ASIC brute force.
- `DeviceIdentityKey` wrapped into two independent copies: Copy 1 via Secure Enclave, Copy 2 via `Fallback_KEK`.
- After wrapping: `ZeroizeOnDrop` clears PIN and `Fallback_KEK` from RAM.

**Cryptographic self-destruct:**

- `Failed_PIN_Attempts` counter stored encrypted with `Device_Key`. Maximum: 5 consecutive failures.
- On 5th failure: Crypto-Shredding of all local DBs + `OIDC_ID_Token` + both `DeviceIdentityKey` copies → Factory Reset state.

**`Failed_PIN_Attempts` Counter — Access Control (mandatory):**

| Platform | Storage Location | Read Access Control | Write Access Control |
| --- | --- | --- | --- |
| 📱 iOS | Keychain, `kSecAttrAccessible = kSecAttrAccessibleWhenUnlockedThisDeviceOnly` | Main App process only; `kSecAttrAccessGroup` restricted | Requires `LAContext` biometric evaluation before write |
| 📱 Android | `EncryptedSharedPreferences` backed by StrongBox | App UID only | `BiometricPrompt` authentication required before write |
| 📱 Huawei | HMS SafetyDetect + EncryptedPreferences | App process only | HMS Biometric gate required |
| 💻 macOS | Keychain, `kSecAttrAccessControl` with `kSecAccessControlBiometryCurrentSet` | Main process + daemon only | SEP biometric before write |
| 🖥️ Windows | DPAPI with `CRYPTPROTECT_LOCAL_MACHINE = false` | Current user only | Windows Hello PIN or biometric |
| 🖥️ Linux | TPM 2.0 NV Index with PCR policy sealing | `terachat` user UID only | TPM PCR policy (boot chain validation) |

**Tamper detection (mandatory):**

```rust
/// Counter value is authenticated — tamper causes Self-Destruct.
pub struct PinAttemptCounter {
    value:  u8,               // 0..=5; anything above 5 treated as 5
    mac:    [u8; 32],         // HMAC-BLAKE3(Device_Key, value || device_id || "pin-counter-v1")
}

pub fn read_counter(device_key: &DeviceKey) -> Result<u8, PinCounterError> {
    let stored = platform_secure_read(COUNTER_KEY)?;
    let expected_mac = hmac_blake3(device_key, &[stored.value, device_id, PIN_COUNTER_DOMAIN]);
    if stored.mac != expected_mac {
        // MAC mismatch: counter corrupted or tampered.
        // Treat as 5 failures. Log COUNTER_TAMPERED. Initiate Self-Destruct.
        log_audit(AuditEvent::PinCounterTampered);
        trigger_self_destruct();
        return Err(PinCounterError::Tampered);
    }
    Ok(stored.value)
}

pub fn write_counter(device_key: &DeviceKey, new_value: u8) -> Result<()> {
    // Biometric gate MUST be cleared before this call (enforced by call site).
    let mac = hmac_blake3(device_key, &[new_value, device_id, PIN_COUNTER_DOMAIN]);
    platform_secure_write(COUNTER_KEY, PinAttemptCounter { value: new_value, mac })?;
    Ok(())
}
```

**Backup exclusion (mandatory):**

- iOS: counter Keychain item MUST use `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`.
  This flag prevents iCloud Keychain sync and iTunes backup inclusion.
- Android: `EncryptedSharedPreferences` backing file MUST be excluded from `auto-backup`
  via `android:allowBackup="false"` on the SharedPreferences provider, or explicit
  `backup_rules.xml` exclusion.
- Restoring a device backup MUST reset the counter to 0 via a counter integrity re-validation
  step on first unlock post-restore. This is acceptable (new device, legitimate user).

**iOS Double-Buffer Zeroize (Jetsam mitigation):**
`mlock()` is rejected by iOS for non-root processes. Mitigation:

1. Allocate key material into two contiguous `MAP_ANONYMOUS | MAP_PRIVATE` pages.
2. Immediately after decryption: overwrite Page 1 with `0x00` before using key from Page 2.
3. On `ZeroizeOnDrop`: overwrite both pages.

- If Jetsam kills before Drop: Page 1 is already zeroed; Page 2 is a single isolated page with no adjacent context.

### 5.3 Message Layer Security — MLS RFC 9420

**Compliance target:** IETF RFC 9420. Maximum group size: 10,000 members. TreeKEM key distribution complexity: O(log n).

**Epoch rotation triggers:**

- Member removal or forced exit
- Admin-initiated rotation
- Scheduled rotation: every 24 h (default; Admin-configurable)

**Batched TreeKEM Update_Path delivery:**

| Group size | Delivery window | Broadcast complexity |
| --- | --- | --- |
| ≤ 100 members | 0 s (immediate) | O(n × changes) |
| 101 – 1,000 members | 60 s sliding window | O(n × batches); batches ≪ changes |
| 1,001 – 5,000 members | 300 s sliding window (Admin-configurable) | O(n × batches) |
| > 5,000 members | Manual Admin trigger only | N/A |

Within each window, Rust Core batches all pending proposals into a single `Commit`. Server fans out one `Update_Path` instead of N independent `Update_Path` messages.

**Epoch rotation SLA:**

- ≤ 100 members: rotation completes in ≤ 1 s
- ≤ 1,000 members: rotation completes in ≤ 60 s
- ≤ 5,000 members: rotation completes in ≤ 5 min

**Peer-assisted Epoch re-induction (offline device reconnect):**

```text
Reconnecting device
  │  WAKEUP_BEACON (BLE, signed by DeviceIdentityKey in SEP)
  ▼
Online peer
  │  Verify signature against Enterprise_CA + Shun List
  │  If on Shun List → reject; require Admin re-provision
  ▼
  │  Re-Add_Member MLS proposal (no server required)
  │  Commit → Welcome_Packet (ECIES/Curve25519 encrypted for reconnecting device)
  ▼
Reconnecting device
  │  Decrypt Welcome_Packet using own private key
  │  Verify sender certificate against Enterprise_CA
  ▼
  Epoch key restored; device rejoins group
```

**Dynamic skip keys:**

- Mobile: maximum 2,000 skip keys.
- Desktop: maximum 10,000 skip keys.
- GC: keys older than 48 h purged automatically.

**Forward Secrecy TTL:** Chain keys expire after 7 days. Devices that have not completed epoch negotiation within 7 days are removed from the group via `Tombstone_Stub`.

**Nonce derivation (MLS RFC 9420 §5.4.9 compliant):**

```rust
/// Per-message nonce — derived, never random, never hardcoded.
pub fn derive_message_nonce(
    sender_data_secret: &[u8; 32],  // from current MLS Epoch_Key material
    reuse_guard:        &[u8; 4],   // 4 random bytes from CSPRNG; embedded in MLSCiphertext header
    seq_number:         u64,        // chunk_seq_number for chunked media; 0 for single messages
) -> [u8; 12] {
    // Step 1: derive base nonce via HKDF-SHA256
    let base_nonce = hkdf_sha256(
        ikm:  sender_data_secret,
        info: b"nonce",
        length: 12,
    );
    // Step 2: XOR with reuse_guard (left-padded to 12 bytes) to prevent cross-epoch reuse
    let guarded = xor_12(base_nonce, pad_left_4(reuse_guard));
    // Step 3: XOR with chunk_seq_number (right-aligned u64 in 12-byte field)
    xor_12(guarded, seq_u64_to_12(seq_number))
}
```

**Rules enforced by `mls_engine.rs`:**

- `reuse_guard` MUST be generated by `ring::rand::SystemRandom` per message. Never reused.
- `sender_data_secret` MUST be rotated on every MLS Epoch rotation. Stale epoch key = reject.
- For chunked media (F-09): `seq_number` increments per 2 MB chunk. `reuse_guard` is shared
  across all chunks of the same file transfer (bound to `cas_hash`).
- `base_nonce` MUST NOT be persisted to disk. Derived fresh from `sender_data_secret` on each use.
- CI: property-based test (proptest) MUST verify no two (reuse_guard, seq_number) pairs produce
  the same 12-byte nonce under the same `sender_data_secret`. Block merge on failure.

### 5.4 Post-Quantum Cryptography — Hybrid PQ-KEM

**Session key derivation:**

```text
Final_Session_Key = HKDF-SHA256(
    ikm:  X25519_Shared_Secret || ML-KEM-768_Shared_Secret,
    info: "terachat-session-v1",
    length: 32
)
```

Compliant with CNSA 2.0 and NIST FIPS 203 (ML-KEM / Kyber768).

**Bandwidth optimization (Quantum Checkpoints):**

- ML-KEM payload (~1.18 KB) attached only at Handshake or every 10,000 messages.
- Daily message stream uses AES-256-GCM (inherently quantum-resistant against Grover's algorithm at 128-bit security equivalent).
- BLE fragmentation: RaptorQ (RFC 6330) encodes the 1.2 KB PQ key into 200-byte drops for BLE MTU 512 bytes. No ACK/NACK required.

**Key material protection:**

- ML-KEM Private Key generated in RAM region allocated with `MAP_CONCEAL`.
- Wrapped with `Hardware_Wrap_Key` from Secure Enclave / StrongBox.
- `ZeroizeOnDrop` executes after KEM computation.

**Pre-fetched PQ Roster:**

- `KeyPackage` (X25519 + ML-KEM-768) pre-fetched and stored in `hot_dag.db` SQLite WAL when Internet is available.
- BLE handshake uses `Key_Hash` (16 bytes) for lookup — avoids transmitting the full 1.2 KB key over BLE.

### 5.5 Out-of-Band Push Key Ratchet

<!-- INSERTED PATCH: MLS — OOB Push Ratchet -->
- ☁️ Reference `§17.2` for key versioning protocols.
```rust
pub struct PushKeyEntry {
    pub version: u32,           // Monotonic identification, per chat_id
    pub key_material: [u8; 32], // AES-256-GCM session key
    pub derived_at_epoch: u64,  // MLS epoch correlation when key was derived
    pub valid_until: u64,       // Unix timestamp bounds
}
```


Push key is **deliberately separated** from TreeKEM to avoid loading the full MLS Update_Path into iOS NSE (20 MB RAM ceiling) or Android FCM Service.

**Key derivation (one-way hash chain):**

```rust
Push_Key_N = HKDF-SHA256(
    ikm:  Company_Key,
    info: "push-ratchet" || chat_id || push_epoch_N,
    length: 32
);
// Push_Key_N cannot derive Push_Key_{N-1}
```

**Storage by platform:**

- iOS: Shared Keychain, Access Group `group.com.terachat.nse` (NSE-only; Main App and Share Extension cannot read).
- Android: StrongBox Keymaster.

**Versioned Key Ladder (prevents notification loss on key rotation):**

```text
NSE receives push payload
  │  Read push_key_version from payload header
  ├── version matches keychain → decrypt inline → display notification
  └── version mismatch →
        cache raw ciphertext to nse_staging.db
        set main_app_decrypt_needed = true in Shared Keychain
        send content-available:1 wake signal
        Main App wakes → rotates key → decrypts staged payload → clears staging
```

**NSE RAM budget enforcement:**

- Static Memory Arena: 10 MB pre-allocated at NSE startup.
- All decryption reuses arena buffers.
- `ZeroizeOnDrop` clears arena after each notification.
- Ghost Push Skeleton: if `payload_size > 4 KB` or `epoch_delta > 1`, NSE shows "Decrypting securely…" and defers to Main App.

### 5.6 Side-Channel Defenses

**Timing attack mitigation:**

- All comparison operations use the `subtle` crate (constant-time equality, conditional select, conditional swap).
- All cryptographic operations use `ring` which implements constant-time primitives internally.

**Traffic analysis mitigation:**

- Fixed-size padding: all outgoing messages padded to nearest multiple of 4,096 bytes before encryption.
- Heartbeat dummy traffic: fixed-size packets at random intervals in range [500 ms, 3,000 ms].

**AES hardware acceleration with software fallback:**

```rust
pub fn init_crypto_backend() -> CryptoBackend {
    #[cfg(target_arch = "x86_64")]
    {
        if std::arch::is_x86_feature_detected!("aes")
            && std::arch::is_x86_feature_detected!("sse2")
        {
            return CryptoBackend::HardwareAccelerated; // AES-NI
        }
    }
    #[cfg(target_arch = "aarch64")]
    {
        if std::arch::is_aarch64_feature_detected!("aes") {
            return CryptoBackend::HardwareAccelerated; // ARM Crypto Extension
        }
    }
    // Software fallback: ~3× slower; functionally correct
    tracing::warn!("Hardware crypto unavailable; using software backend");
    CryptoBackend::Software
}
```

Admin Console displays a persistent warning when any enrolled device uses the software backend.

---

## 6. MESH NETWORK PROTOCOL

### 6.1 Transport Abstraction Layer

Rust Core does **not** call any Wi-Fi or BLE OS API directly. All transport decisions are delegated to the host layer (Swift / Kotlin) via the `MeshTransport` trait. This enforces the platform-agnostic Core principle and prevents Apple App Review rejection for direct Wi-Fi API calls.

```rust
pub trait MeshTransport: Send + Sync {
    fn send(&self, payload: &[u8], peer_id: &PeerId) -> Result<(), MeshError>;
    fn recv_stream(&self) -> impl Stream<Item = (PeerId, Vec<u8>)>;
    fn discover_peers(&self) -> impl Stream<Item = PeerId>;
}
```

**Platform adapter implementations:**

| Platform | Adapter struct | Data Plane | Control Plane | Throughput |
| --- | --- | --- | --- | --- |
| 📱 iOS | `MultipeerConnectivityAdapter` | Apple AWDL (802.11ac) | BLE 5.0 CoreBluetooth | ~250 MB/s |
| 📱 Android | `WifiDirectAdapter` | Wi-Fi Direct (WifiP2PManager) | BLE 5.0 BluetoothLeAdvertiser | ~250–500 MB/s |
| 💻 macOS | `AWDLMultipeerAdapter` | Apple AWDL | BLE 5.0 CoreBluetooth | ~250 MB/s |
| 🖥️ Windows/Linux | `WpaSupplicantAdapter` | Wi-Fi Direct (wpa_supplicant P2P) | BLE Peripheral (USB dongle fallback) | ~250 MB/s |

**Payload routing decision — < 1 µs via enum dispatch:**

```rust
fn route_payload(payload: &Payload) -> TransportChannel {
    match (payload.size, &payload.kind) {
        (s, PayloadKind::Control) if s < 4_096 => TransportChannel::BLE,
        _ => TransportChannel::WiFi,
    }
}
```

### 6.2 Mesh Topology and Role Assignment

**Deterministic auto-promotion (no voting, no configuration):**

```rust
fn assign_role(device: &DeviceInfo) -> MeshRole {
    match device.os_type {
        OsType::iOS => MeshRole::LeafNode, // always; election_weight = 0
        OsType::MacOS | OsType::Windows | OsType::Linux
            if device.power_source == PowerSource::AC =>
            MeshRole::SuperNode,
        OsType::Android if device.available_ram_mb >= 3_072
            && device.battery_pct >= 40 =>
            MeshRole::RelayNode,
        _ => MeshRole::LeafNode,
    }
}
```

**Store-and-Forward relay quotas:**

| Role | Storage Quota | Message TTL |
| --- | --- | --- |
| Super Node (Desktop) | 500 MB – 1 GB | 48 – 72 h |
| Relay Node (Android) | 100 MB | 24 h |
| Leaf Node (iOS) | 50 MB receive-only | N/A |
| Tactical Relay (EMDP iOS) | 1 MB text-only CRDT buffer | 60 min (extendable once) |

**Border Node auto-detection:** Any device with both `internet_available == true` and `ble_active == true` is automatically classified as Border Node. Border Nodes route between TCP/IP and BLE Mesh without configuration.

### 6.3 BLE Stealth Beaconing

<!-- INSERTED PATCH: Stealth Wake-up Protocol -->
- 🌐 `IdentityCommitment` structure updated to utilize a 16-byte `c_trunc` instead of 8 bytes to establish 128-bit collision resistance.
- 🌐 Backward-compatibility dual parsing is mandatory to support legacy 8-byte beacon configurations simultaneously with newer 16-byte setups. Deprecation of legacy format scheduled post 90 days.

```rust
pub struct IdentityCommitment {
    /// REVISED: 16 bytes payload (upgraded from 8 bytes)
    /// Guarantees 128-bit security making brute-forcing infeasible across GPU clusters
    c_trunc: [u8; 16],
}
```


**Beacon frame format (31 bytes, fits single BLE 5.0 ADV_EXT_IND PDU — no fragmentation):**

```text
Offset  Size  Field
0       4 B   timestamp_slot_5min (little-endian u32)
4       8 B   HMAC-BLAKE3(Mesh_PSK_daily, root_hash || timestamp_slot_5min)[0:8]
12      11 B  encrypted_delta_hint (AES-128-SIV with ephemeral session key)
23      8 B   padding (zero-fill)
```

**Daily PSK derivation:**

```text
Mesh_PSK_daily = HKDF-SHA256(Company_Key, "mesh-beacon" || date_utc || cluster_id)
```

A passive BLE scanner observes only random-appearing entropy. No `Device_MAC`, `Node_ID`, or `User_ID` is present in any field under any encoding.

**MAC address rotation:**

- iOS: Resolvable Private Address (RPA), rotated every 15 minutes. Derived from IRK stored in SEP. Only authorized peers can resolve RPA → real MAC.
- Android / Desktop: Random static address rotated every 5 minutes via OS BLE API.

**BLE duty cycle (power management):**

- Active: 200 ms advertising/scanning + 800 ms sleep. Net: 20% duty cycle.
- Standby (no pending payload): 1 advertisement per 5 minutes.
- Extended Connection Event: activated only on confirmed large payload pending.
- Android Doze mitigation: Companion Device Manager `REQUEST_COMPANION_RUN_IN_BACKGROUND`.

### 6.4 iOS AWDL Conflict Resolution

**Trigger:** iOS radio hardware cannot simultaneously support AWDL and Personal Hotspot or CarPlay. AWDL drops silently when either is activated.

**Detection and response sequence:**

```text
NWPathMonitor detects bridge interface (Hotspot indicator) + no AWDL interface
  │
  ▼
Swift adapter → FFI → tera_awdl_unavailable(reason: AWDLUnavailableReason)
  │
  ▼
Rust Core:
  1. Downgrade mesh tier: Wi-Fi Direct → BLE only (Tier 3)
  2. Emit CoreSignal::TierChanged { new_tier: BleOnly, reason: HotspotConflict }
  3. Queue voice packets with TTL:
     - Default: 30 s
     - CallKit session active: 90 s
  4. After TTL expiry with no AWDL recovery: drop voice, notify user
```

**Pre-emptive warning (1–2 s window before AWDL drops):** When `NWPathMonitor` detects a tethering interface appearing while a CallKit session is active: emit `TierChanged` with reason `HotspotConflictImminent`. UI presents: "Enabling Hotspot will interrupt the Mesh call — continue?" Auto-dismiss after 3 s if no user action.

### 6.5 Dictator Election (Split-Brain Resolution)

<!-- INSERTED PATCH: Split-Brain Resolution -->
- 🔗 Reconciliations now require deterministic conflict detection utilizing `EpochId` fused with a BLAKE3 `tree_fingerprint`.
- 📱 Resolves ANR faults during high-volume node synchronization via explicit IPC fallbacks to Desktop snapshots upon crossing `MAX_MOBILE_MERGE_EVENTS`.

```rust
#[derive(Clone, PartialEq, Eq, Hash)]
pub struct EpochId {
    /// Epoch sequence number (monotonic execution)
    pub sequence: u64,
    /// BLAKE3 hash of TreeKEM tree root at the exact moment of epoch creation
    /// Uniquely resolves WHICH specific tree state this epoch coordinates
    pub tree_fingerprint: [u8; 16],
    /// Hybrid Logical Timestamp mapping to epoch creation
    pub created_at: HybridLogicalTimestamp,
}

pub struct ChunkedDagMerger {
    chunk_size: usize,
    yield_every_ms: u64,
}
```


When a Mesh partition reconnects, a single Merge Dictator is elected. The election is deterministic — zero voting rounds, zero network coordination.

**Election algorithm:**

```rust
fn elect_dictator(peers: &[PeerInfo]) -> Option<PeerId> {
    peers.iter()
        .filter(|p| p.device_class != DeviceClass::iOS)
        .max_by_key(|p| blake3::hash(p.node_id.as_bytes()))
        .map(|p| p.node_id)
}
```

**Dictator responsibilities after election:**

1. Execute O(N log N) HLC DAG merge using Rayon parallel thread pool.
2. Emit `Materialized_Snapshot` to all Leaf Nodes (Leaf Nodes apply in O(1)).
3. Publish MLS TreeKEM `Update_Path` for Epoch N+2, covering all members.

**Failover:** Dictator heartbeat monitored at 10-second intervals. On timeout: node with second-highest BLAKE3 hash assumes Dictator role. Handover latency: < 10 ms.

**All-iOS Causal Freeze:** If the entire Mesh consists exclusively of iOS devices and EMDP conditions are not met, the system enters Causal Freeze: read-only mode, no DAG writes, no merges. Freeze persists until a non-iOS node joins.

### 6.6 Byzantine Fault Tolerance & Anti-Spam

**Micro Proof-of-Work:**

| Context | Algorithm | Cost | Note |
| --- | --- | --- | --- |
| Standard messages | SHA-256 Hashcash, 12-bit prefix | ~5 ms | Default |
| Post-violation challenge | Argon2id `m=1MB, t=2, p=1` | ~50 ms | After 3 violations |
| SOS / Emergency | None | 0 ms | Always exempt |

**Byzantine Quarantine — Poison Pill Protocol:**

```text
Node violates signature verification > 3 times within 10 s
  │
  ▼
Reporter constructs ProofBundle:
  {raw_packet, hlc_timestamp, violator_id, Ed25519_sig_by_reporter_DeviceKey}

Requires: minimum 2 independent ProofBundles from different reporters
  │
  ▼
Enterprise CA signs Shun Record:
  {Node_ID, Ed25519_Sig_by_Enterprise_CA, TTL: 30 min}

Gossip broadcast to all Mesh nodes
  │
  ▼
Each receiver:
  1. Verify Enterprise CA signature (unsigned Shun Records dropped — prevents false-flag)
  2. If valid: BLE disconnect + routing entry deletion
  3. Node cannot rejoin until Admin revokes Shun Record
```

**HLC causality check on evidence:** `|hlc_now - hlc_packet| > 5 s` → `TEMPORAL_VIOLATION`; packet dropped. Evidence older than 24 h: `EVIDENCE_REPLAYED`; tracked via Bloom Filter.

**Rate limiting ring buffer:** 32 entries per `Node_ID`. Messages < 100 ms apart: Quarantine for 15 min.

### 6.7 Emergency Mobile Dictator Protocol (EMDP)

<!-- INSERTED PATCH: EMDP Key Escrow -->
- 💻 The Desktop client MUST finalize and emit the active security escrow state parameters *before* triggering network disconnection logic.
- 💻 Exception fallback: If the Desktop disconnects non-gracefully prior to generating the escrow, standard Timeout constraints govern connection collapse handling.


**Activation conditions (all three must be true simultaneously):**

1. No Desktop (`macOS | Windows | Linux`) or high-RAM Android Super Node present in Mesh.
2. Internet is unavailable on all present devices.
3. Minimum 2 iOS devices in Mesh with battery > 20%.

**Tactical Relay selection:**

```rust
fn elect_tactical_relay(peers: &[PeerInfo]) -> PeerId {
    peers.iter()
        .max_by_key(|p| {
            let battery = p.battery_pct as u64 * 100;
            let signal  = (p.ble_rssi.saturating_add(100)) as u64;
            battery + signal
        })
        .map(|p| p.node_id)
        .expect("at least 2 peers required by EMDP activation precondition")
}
```

**Tactical Relay hard constraints:**

- Text-only Store-and-Forward (Append-Only CRDT buffer). No file or media transfer.
- No DAG merge. No MLS Epoch rotation.
- Storage quota: 1 MB CRDT buffer.
- TTL: 60 minutes.

**Key Escrow Handshake (Desktop → iOS, executed before Desktop goes offline):**

```rust
pub struct EmdpKeyEscrow {
    relay_session_key:  AesKey256,  // AES-256 for encrypting EMDP-relayed messages
    emdp_start_epoch:   u64,        // MLS Epoch at handover time
    expires_at:         u64,        // Unix timestamp: now() + 3600
}
// Serialized and encrypted via ECIES/Curve25519 with iOS Tactical Relay's public key
// Transmitted over BLE Control Plane before Desktop disconnects
// On Desktop reconnect: receive escrow from iOS, decrypt relay messages, merge into DAG
```

**TTL Extension Protocol:**

```text
At T-10 min:
  Tactical Relay broadcasts EMDP_TTL_EXTENSION_REQUEST (BLE, signed by DeviceIdentityKey)
    │
    ▼
  Peer with battery_pct > 30% accepts → sends EMDP_TTL_ACCEPT
    │
    ▼
  Original Relay:
    1. Serialize CRDT buffer (max 1 MB)
    2. Encrypt via ECIES/Curve25519 with accepting peer's public key
    3. Transfer over BLE Data Plane
    4. Revert to Leaf Node
    │
    ▼
  New Tactical Relay assumes role; TTL resets to 60 min
```

**User warning signals:**

- `CoreSignal::EmdpExpiryWarning { minutes_remaining: 10 }` at T-10 min
- `CoreSignal::EmdpExpiryWarning { minutes_remaining: 2 }` at T-2 min

**SoloAppendOnly mode:** Single iOS device with no peers. Append-only, no election, full merge deferred to next non-iOS contact.

---

## 7. OFFLINE-FIRST & CRDT SYNCHRONIZATION

### 7.1 DAG Structure and Storage

<!-- INSERTED PATCH: Hydration Scheduler & Thundering Herd Protection -->
- ☁️ Reconnecting clients MUST funnel through the global `HydrationScheduler` queue boundary prior to triggering direct WAL hydration workloads.
- **Constraints:** Max concurrency configuration limits mathematically map to `floor(available_ram_mb / 64)`. Per-tenant limits cap at exactly 10 clients/second handling a 30-second rejection queue timeout.
- 🗄️ Background WAL checkpoints execute parallel to decoupled dedicated thread pools bypassing the core Tokio runtime logic entirely. Utilizes `PRAGMA wal_checkpoint(PASSIVE)` yielding to read constraints smoothly avoiding fsync blocks.


<!-- INSERTED PATCH: SQLite WAL Hydration & Tombstone Vacuum -->
- ☁️ Reference `HydrationScheduler §18.1` for global cross-session concurrency controls.
- ☁️ Clients MUST implement exponential backoff with jitter prior to requesting a hydration slot.
- ☁️ Per-tenant rate limit is strictly enforced at a maximum of 10 clients per second.
- 🗄️ Clarification on 7-day hot DAG eviction and the `tombstone.clock ≤ MVC` condition: The 7-day eviction mechanism is triggered strictly AFTER the MVC condition is satisfied.
- 🗄️ During an active Mesh Network partition (Mesh_Partition_Active = true), eviction protocols are strictly suspended.


Every message, edit, deletion, and group event is an immutable node in an append-only DAG. Physical deletion never occurs.

**`CRDT_Event` schema:**

```rust
pub struct CrdtEvent {
    id:           Uuid,              // UUID v7 (time-ordered for index locality)
    parents:      Vec<Uuid>,         // causal parent IDs; typically 1–2
    hlc:          HLCTimestamp,      // { wall_ms: u64, logical: u32, node_id: [u8;16] }
    author_did:   DeviceId,          // Ed25519 public key hash
    payload:      EncryptedPayload,  // AES-256-GCM ciphertext; server never decrypts
    signature:    Ed25519Signature,  // signed by author's DeviceIdentityKey (in SEP)
    content_type: ContentType,       // Message | Edit | Delete | GroupOp | Tombstone
}
```

**Deletion representation:**

- Physical deletion: forbidden.
- Deletion appends a `Tombstone_Stub { entity_id, hlc, type: DELETED }` to `cold_state.db`.
- UI renders tombstone as "[Message deleted]". DAG integrity preserved for audit.

**Storage layer:**

| DB File | Mode | Encryption | Purpose |
| --- | --- | --- | --- |
| `hot_dag.db` | SQLite WAL, `synchronous = NORMAL` | None (ciphertext blobs only) | Append-only event log |
| `cold_state.db` | SQLite WAL | SQLCipher AES-256 (key from Secure Enclave) | Materialized current state |
| `wal_staging.db` | SQLite WAL | None (server relay only) | At-least-once delivery staging |
| `nse_staging.db` | SQLite WAL | None (ciphertext only) | iOS NSE push delivery staging |

**Device-Level Metadata Privacy — Threat Model Boundary (mandatory documentation):**

This section explicitly defines what is and is not protected at the device level.

**Protected (encrypted):**

- `payload` field: AES-256-GCM ciphertext, key = `Epoch_Key` in RAM. Server and filesystem
  adversary cannot read message content.
- `cold_state.db`: fully encrypted with SQLCipher AES-256 (key = Secure Enclave-derived).

**Not protected against physical device seizure (by design):**

- `hot_dag.db` metadata: `author_did`, `hlc`, `content_type`, `parents`, `id`.
- This metadata is necessary for DAG integrity verification and cannot be encrypted without
  making the append-only structure unverifiable by the relay without key access.

**Accepted risk:**
A physically seized device allows an adversary without biometric/PIN to recover:

- Communication frequency (event timestamps and HLC counters).
- Causal graph structure (parent relationships between events).
- Event type distribution (Message vs GroupOp vs Edit vs Delete).
- Pseudonymous author identifiers (`author_did` = Ed25519 public key hash; not directly PII).

This risk is accepted for the following operational reasons:

- Encrypting `hot_dag.db` metadata would require the relay to hold decryption keys,
  breaking the Zero-Knowledge server guarantee.
- SQLCipher on `hot_dag.db` is architecturally viable but would add ~15% read/write overhead
  on mobile (single-core WAL append path). This trade-off is deferred to a future version.

**Mitigation (implemented):**

- `author_did` is an Ed25519 public key hash, not a username or email. Not directly PII.
- `content_type` leaks event category but not content.
- Biometric gate prevents access to `Epoch_Key` → payload is never decryptable without
  the live user present (physical seizure does not break payload encryption).

**Future work (not in this version — tracked):**

- Encrypted `hot_dag.db` with a key derived from `Secure Enclave` (SQLCipher): adds payload
  metadata protection for physical seizure at the cost of ~15% I/O overhead. Tracked as
  `TERA-SEC-007`.

**Invariant:** `cold_state.db` is always rebuildable from `hot_dag.db`. If `cold_state.db` migration fails: drop the file and rebuild. Never abort without a recovery path.

**SQLite WAL anti-bloat:**

- `PRAGMA wal_autocheckpoint = 1000` enforced.
- Auto-VACUUM trigger: WAL > 50 MB (mobile) or > 200 MB (desktop/server).
- Mobile (iOS): BGTask scheduled when device is charging + screen off.
- Mobile (Android): WorkManager periodic task (same conditions).
- Foreground opportunistic VACUUM: if app idle > 60 s and WAL > 50 MB, spawn low-priority Tokio task with `VACUUM INTO hot_dag_tmp.db` followed by atomic POSIX `rename()`. Task self-cancels on user interaction within 5 s.
- `VACUUM INTO` guarantees zero-downtime: creates clean copy then atomic swap.

**Schema migration protocol:**

```rust
pub fn run_migration(db: &Connection, target_version: u32) -> Result<()> {
    let current: u32 = db.pragma_query_value(None, "user_version", |r| r.get(0))?;
    if current < target_version {
        let backup_path = format!("{}.bak.v{}", db_path, current);
        db.backup(DatabaseName::Main, &backup_path, None)?;
        db.execute_batch("BEGIN EXCLUSIVE TRANSACTION")?;
        migration_up(db, current, target_version)?;
        db.pragma_update(None, "user_version", target_version)?;
        db.execute_batch("COMMIT")?;
    }
    Ok(())
}
```

### 7.2 Hybrid Logical Clock (HLC)

**Timestamp structure:**

```rust
pub struct HLCTimestamp {
    wall_ms:  u64,       // milliseconds since Unix epoch
    logical:  u32,       // tie-breaker when wall_ms values are equal
    node_id:  [u8; 16],  // originating device UUID; final tie-breaker
}
```

**Total ordering rules (deterministic across all nodes):**

1. Higher `wall_ms` = later event.
2. Equal `wall_ms`: higher `logical` = later event.
3. Equal `wall_ms` and `logical`: higher `node_id` lexicographic value = later event.

**Clock update on event receive:**

```rust
fn update_hlc(local: &mut HLCTimestamp, received: &HLCTimestamp) {
    let max_wall = local.wall_ms.max(received.wall_ms).max(system_clock_ms());
    local.logical = if max_wall == local.wall_ms && max_wall == received.wall_ms {
        local.logical.max(received.logical) + 1
    } else if max_wall == local.wall_ms {
        local.logical + 1
    } else {
        0
    };
    local.wall_ms = max_wall;
}
```

**Eclipse Attack detection:** If a peer's `Latest_HLC_Timestamp` diverges > 3 MLS Epochs from local state → emit `ComponentFault { component: "hlc", severity: Critical }` and switch to Pure Mesh Mode (discard all data from that peer pending Admin review).

### 7.3 Split-Brain Reconciliation

<!-- INSERTED PATCH: Split-Brain — Causal Fast-Forward -->
- 🖥️ The Canonical Epoch Election specifies `HLC timestamp` as the primary deterministic key.
- 🖥️ `tree_fingerprint` serves as the explicit tie-breaker fallback mechanism ensuring uniform network progression regardless of partition divergence origins.
- 📱 Desktop architectures utilize chunking without yield delays; Mobile forces chunks with yields for frame drops.


**Trigger:** Two or more Mesh partitions reconnect after a network partition period.

**Reconciliation sequence:**

```text
Step 1: Gossip — each node broadcasts Hash_Frontier { vector_clock, root_hash }
  │
  ▼
Step 2: Identify winner — highest Hash_Frontier = most recent causal state
  │
  ▼
Step 3: Elected Dictator executes O(N log N) HLC merge via Rayon thread pool
        (Desktop only; Mobile receives Materialized_Snapshot from Dictator)
  │
  ▼
Step 4: LWW conflict resolution via HLC for concurrent edits:
        - ContentType::Message     → siblings preserved; UI shows conflict indicator
        - ContentType::CONTRACT |
          ContentType::POLICY |
          ContentType::APPROVAL    → both preserved; UI requires explicit user resolution
        - ContentType::GroupOp     → HLC LWW; later operation wins
  │
  ▼
Step 5: Dictator broadcasts Materialized_Snapshot
        Leaf Nodes apply in O(1) via INSERT OR REPLACE transaction
  │
  ▼
Step 6: TreeKEM Merge Commit → Epoch N+2 Update_Path → new Epoch_Key for all members
  │
  ▼
Step 7: Multi-epoch RAM (forked epoch keys held during partition) released via ZeroizeOnDrop
```

**Mobile DAG merge (ANR prevention):** Mobile devices do not execute the O(N log N) merge. Time-sliced processing: 100 events per Tokio task, `tokio::task::yield_now()` between batches (preserves 1–2 ms for UI event loop). `CoreSignal::DagMergeProgress` emitted every 200 ms when backlog > 500 events.

### 7.4 Snapshot Export and Recovery

**`MaterializedSnapshot` structure:**

```rust
pub struct MaterializedSnapshot {
    cas_uuid:      Uuid,                    // SHA-256(snapshot_content) → CAS lookup
    epoch_id:      u64,                     // MLS Epoch at snapshot time
    vector_clock:  HashMap<NodeId, u64>,
    format:        SnapshotFormat,          // Parquet (Desktop/Server) | SQLite (Mobile)
}
```

**Recovery bootstrap sequence:**

1. New device downloads `epoch_current.snapshot` from TeraVault VFS.
2. Verify: `SHA-256(downloaded_content) == cas_uuid`. Reject on mismatch.
3. Write to `cold_state.db` via single `INSERT OR REPLACE` transaction. Complexity: O(1) regardless of history depth.
4. Full history in `hot_dag.db` available for audit. Not required for functional operation.

**Mobile CRDT pruning:** After 7 days, raw CRDT events in `hot_dag.db` are squashed into `Squash_State` blob. Super Nodes retain 100% DAG history. Mobile devices retain squashed state + last 7 days of raw events.

---

## 8. DATA FLOW & MESSAGE LIFECYCLE

### 8.1 Outbound Message Flow

```text
User input (text / media bytes)
  │  UICommand::SendMessage { recipient_did, plaintext }
  ▼
Rust Core — HKMS lookup → Company_Key
  │
  ▼
MLS Encrypt:
  EncryptedPayload = AES-256-GCM(Epoch_Key, plaintext)
  nonce = Base_Nonce XOR chunk_seq_number  // guarantees nonce uniqueness
  │
  ▼
CRDT_Event construction:
  { id: Uuid::v7(), parents: [last_event_id], hlc: current_hlc(),
    author_did, payload: EncryptedPayload, content_type: Message }
  │
  ▼
Ed25519 signature via DeviceIdentityKey (Secure Enclave — biometric required)
  │
  ▼
Append to hot_dag.db WAL  ← (event is durable before network dispatch)
  │
  ├── Online path:
  │     TLS 1.3 + mTLS → VPS Relay → WAL Staging → Pub/Sub fanout
  │
  └── Offline path:
        BLE Control Plane → Mesh Store-and-Forward
```

**Atomicity guarantee:** Event written to `hot_dag.db` WAL before network dispatch. Network failure does not cause event loss — at-least-once delivery via WAL staging on relay restart.

### 8.2 Inbound Message Flow

```text
VPS Relay / Mesh peer delivers { destination_device_id, ciphertext_blob, timestamp }
  │  TLS 1.3 verification
  ▼
Rust Core — CRDT_Event.signature verified via sender's DeviceIdentityKey
  │  Reject conditions: invalid signature | sender on Shun List
  ▼
MLS Decrypt: EncryptedPayload → Plaintext using Epoch_Key
  │  Epoch_Key held in RAM ZeroizeOnDrop struct
  ▼
DAG insertion: hot_dag.db WAL append (Ed25519 signature stored with event)
  │
  ▼
cold_state.db materialized view update (INSERT OR REPLACE)
  │
  ▼
CoreSignal::StateChanged { table, version } → UI pulls viewport snapshot (20 messages)
  │
  ▼
Plaintext ZeroizeOnDrop immediately after render frame
```

### 8.3 Push Notification Inbound Flow (iOS NSE)

```text
APNs delivers push payload (ciphertext)
  │  NSE extension wakes; RAM ≤ 20 MB enforced
  ▼
Static Memory Arena 10 MB — pre-allocated at NSE startup
  │
  ▼
Read Push_Key_current from Shared Keychain (group.com.terachat.nse)
  │  Check push_key_version vs payload header version
  ├── Match → AES-256-GCM decrypt in arena → OS notification display
  └── Mismatch →
        cache raw ciphertext to nse_staging.db
        set main_app_decrypt_needed=true in Shared Keychain
        send content-available:1 wake signal
          │
          ▼
        Main App wakes → rotates key → decrypts nse_staging.db entry → clears staging
  │
  ▼
ZeroizeOnDrop: clears arena contents and Push_Key from NSE memory
```

### 8.4 Server Relay Flow (Blind)

```text
Client sends TLS 1.3 + mTLS authenticated request
  │  Relay extracts only: { destination_device_id, ciphertext_blob, timestamp }
  │  Relay has zero access to: plaintext | sender identity | content
  ▼
WAL Staging:
  INSERT INTO wal_staging (event_id, payload, status='STAGED')
  │  Durable before MPSC enqueue
  ▼
Tokio MPSC channel → Redis / NATS JetStream pub/sub
  │
  ▼
On confirmed delivery acknowledgment:
  UPDATE wal_staging SET status='COMMITTED' WHERE event_id = ?
  │
  ▼
Prometheus: relay_message_relay_total++
```

**At-least-once delivery:** On relay restart, all `wal_staging` entries with `status = STAGED` are replayed into the MPSC channel before accepting new connections.

---

## 9. [ARCHITECTURE] [IMPLEMENTATION] Infrastructure & Deployment

> **Triết lý thiết kế lại:** TeraChat là hệ thống Zero-Knowledge.
> Server KHÔNG THỂ đọc dữ liệu. Do đó, server không cần compute phức tạp.
> Infrastructure complexity phải tỷ lệ thuận với actual server workload,
> không phải với perceived importance.
>
> **Kết luận:** TeraRelay là một blind router.
> Một blind router cần: 1 process, 1 SQLite file, 1 blob storage URL.
> KHÔNG cần: PostgreSQL HA cluster, MinIO EC+4, Redis, NATS, Kubernetes.

---

### 9.1 [ARCHITECTURE] Three-Tier Edge-Native Topology

```text
TIER 0 — COMPUTE EDGE (Client Devices)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 Mobile Leaf Nodes          💻🖥️ Desktop Super Nodes
• Delta CRDT only             • Full DAG storage + merge
• No ONNX inference           • ONNX inference (offloads mobile)
• UI rendering                • CRDT Snapshot publisher
• ZeroizeOnDrop crypto        • Mesh relay (BLE/Wi-Fi Direct)
• Push notification decrypt   • FTS5 full-history indexing
• hot_dag.db: ≤ 25MB          • hot_dag.db: unlimited (SSD)

TIER 1 — SOVEREIGN RELAY (1 Binary)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☁️ TeraRelay Rust Binary (~12MB)
• Blind message routing (WebSocket/QUIC)
• Presence tracking (device_hash only, no PII)
• Push gateway (APNs/FCM/HMS proxy)
• Blob index (CAS hash → URL mapping)
• License JWT verification (Ed25519, offline-capable)
• Federation bridge (mTLS inter-cluster)
Deployment: 1 VPS × 1 binary × 1 SQLite
Minimum spec: 1 vCPU, 512MB RAM, 20GB SSD = $5-6/month

TIER 2 — BLOB STORAGE (Pluggable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
☁️ Option A: Cloudflare R2 / Backblaze B2 (SME default)
🗄️ Option B: MinIO Single Node (Enterprise self-hosted)
🗄️ Option C: NAS with S3 API (Gov/Military air-gapped)
All options: store ONLY ciphertext — provider sees nothing

## 10. PERFORMANCE & SCALING CONSIDERATIONS

### 10.1 Throughput Benchmarks

| Component | Platform | Throughput | Conditions |
| --- | --- | --- | --- |
| IPC Data Plane (SAB) | 🖥️ Desktop | ~500 MB/s | SharedArrayBuffer, 2 MB chunks, COOP+COEP |
| IPC Data Plane (JSI) | 📱 iOS | ~400 MB/s | C++ JSI Shared Memory Pointer |
| IPC Data Plane (FFI) | 📱 Android | ~400 MB/s | Dart FFI TypedData |
| BLE Control Plane | 📱 All mobile | ~50 ms latency | 200 ms duty cycle; < 15 mW |
| AWDL / Wi-Fi Direct | 📱 iOS / Android | ~250–500 MB/s | Foreground; < 20 m range |
| VPS concurrent connections | ☁️ 4 GB RAM VPS | ~500,000 WebSocket | Tokio + io_uring; ~2 KB/connection |
| DAG merge | 💻 🖥️ Desktop | > 10,000 events/s | Rayon parallel thread pool |
| AES-256-GCM (hardware) | AES-NI / ARM NEON | 4–8 GB/s | `ring` crate |
| AES-256-GCM (software) | Legacy Android | ~800 MB/s | `ring` crate software backend |
| ML-KEM-768 keygen | 📱 Mobile | < 10 ms | ARM Crypto Extension |

### 10.2 Latency Targets

| Operation | Target | Action on Failure |
| --- | --- | --- |
| ALPN negotiation (all steps) | < 50 ms | MESH_MODE fallback |
| MLS message encrypt (single) | < 5 ms | Log warning; no user impact |
| Push notification decrypt (NSE) | < 500 ms | Ghost Push skeleton; Main App decrypt |
| DAG merge batch (mobile) | ≤ 2 ms UI blocking per batch | `yield_now()` enforced |
| End-to-end relay delivery (online) | < 200 ms | Increment `relay_delivery_timeout_total` |
| TURN failover | < 3 s | Keepalived floating IP takeover |
| XPC Worker crash recovery | < 5 s (3 retries) | `XpcPermanentFailure` event + support_id |
| SIGTERM WAL checkpoint | ≤ 30 s | Exit unconditionally; `Restart=on-failure` |

### 10.3 Scaling Ceilings

| Constraint | Ceiling | Mitigation |
| --- | --- | --- |
| MLS group real-time epoch rotation | 100 members | Batched delivery (§5.3) |
| MLS group batched epoch rotation | 5,000 members | Manual Admin rotation above this |
| VPS concurrent connections (4 GB) | ~500,000 | Add relay nodes behind GeoDNS |
| BLE Mesh hop distance | 3 hops | Beyond 3 hops: overhead exceeds value |
| DAG events before mobile squash | 7 days raw events | Auto-squash + Materialized Snapshot |
| NSE RAM | 20 MB hard limit (OS) | Ghost Push + Main App decrypt |
| WASM heap per `.tapp` | 50 MB mobile / 64 MB desktop | OOM-kill sandbox; Core unaffected |

### 10.4 WebRTC and Voice/Video

**TURN sizing:** 1 node: ~50 concurrent HD streams. Spec: 4 vCPUs, 8 GB RAM, 1 Gbps NIC. Keepalived Floating IP: 3-second failover.

**iOS CallKit requirement:** iOS grants 30-second background network window. TURN failover (3 s) + SRTP renegotiation could exceed this. `CXProvider` keeps audio session active regardless of background state.

**Dual TURN Preconnect:** When a CallKit session is active and app is about to enter background, Rust Core proactively connects to a secondary TURN server as backup. This prevents audio drop during TURN server failover.

---

## 11. CONSTRAINTS & LIMITATIONS

### 11.1 Platform Hard Constraints

**📱 iOS:**

- W^X policy: wasmtime JIT is prohibited inside App Sandbox (`com.apple.security.app-sandbox = true, NO allow-jit`). Use `wasm3` interpreter or AOT-compiled `.dylib` bundles. XPC Worker process (`com.apple.security.cs.allow-jit = true`) is the only exception.
- `mlock()` rejected for non-root processes. Use Double-Buffer Zeroize (§5.2) instead.
- NSE RAM: 20 MB hard ceiling enforced by OS. No override.
- Background network: 30-second window. Voice calls require CallKit integration.
- AWDL disabled with Personal Hotspot or CarPlay. Detection and BLE fallback mandatory (§6.4).
- iOS `election_weight = 0`. Never elected Merge Dictator. EMDP Tactical Relay only, with strict text-only constraints.

**📱 Android:**

- Android 14+ (`targetSdk = 34`): FCM Data Messages throttled to 10/hour in Restricted battery bucket. Mitigation: FCM `priority = "high"` + Companion Device Manager `REQUEST_COMPANION_RUN_IN_BACKGROUND`.
- StrongBox not available on all devices. Fall back to TEE-backed AndroidKeyStore if StrongBox unavailable. Log `STRONGBOX_UNAVAILABLE` in Admin Console.

**📱 Huawei HarmonyOS:**

- HMS Push Kit: no `content-available` background push equivalent. CRL refresh latency ≤ 4 h (foreground polling) vs ≤ 30 min on iOS/Android. This SLA delta must be disclosed to enterprise customers.
- Dynamic WASM loading from Marketplace: not available. AOT-compiled `.waot` bundles required for AppGallery.

**💻 macOS:**

- XPC Worker OOM crash during WASM JIT execution: transaction may be in `PENDING` state. Mitigation: `XpcTransactionJournal` with states `PENDING → VERIFIED → COMMITTED` persisted in `hot_dag.db`. Recovery determined by last journal state on `NSXPCConnectionInterrupted`.
- Maximum 3 XPC retry attempts: backoff 0 s, 2 s, 8 s. On 3rd failure: emit `XpcPermanentFailure { support_id: Uuid }`.

**🖥️ Linux:**

- Flatpak packaging: incompatible with TeraChat's `seccomp-bpf` custom filter (bubblewrap sandbox conflict). Use `.deb` / `.rpm` (enterprise, Tier 1) or AppImage with Cosign signature (Tier 2).
- AppArmor (Ubuntu) and SELinux (RHEL): postinstall script must detect enforcement mode and load the correct MAC profile before first launch. Without this, startup crashes on `memfd_create` and `ipc_lock` capability denial.

**☁️ VPS:**

- eBPF/XDP, Hardware TEE (SGX/SEV), and `mlock()` pinning are deprecated for VPS deployments (removed in v0.3.6). Replaced by: Tokio Token Bucket rate limiting (userspace), Soft-Enclave WASM Isolation (Cranelift JIT + ChaCha8 RAM scrambling + `ZeroizeOnDrop`).
- Redis / NATS JetStream are external processes — not included in relay binary RAM budget.

### 11.2 Network Constraints

- BLE MTU: 512 bytes (BLE 5.0). PQ-KEM keys (~1.2 KB) require RaptorQ (RFC 6330) fragmentation for BLE transport.
- BLE capacity: Control Plane only (~50 ms latency). File/media transfer requires Wi-Fi Direct / AWDL Data Plane.
- Voice in EMDP/Tactical Relay mode: not supported. Voice requires Wi-Fi Direct or Internet.
- Mesh hop maximum: 3 hops. Beyond 3 hops: routing overhead exceeds message utility for text messages.

### 11.3 Cryptographic Constraints

- All crypto: `ring` crate or `RustCrypto` workspace only. No custom implementations. No C library wrapping.
- Signature algorithm: Ed25519 exclusively. RSA and ECDSA are not used anywhere in the system.
- AES-256-GCM nonce uniqueness: `nonce = Base_Nonce XOR chunk_seq_number` for chunked streams.
- ML-KEM-768: used only in hybrid with X25519. Neither algorithm alone is sufficient.

### 11.4 Known Implementation Gaps (Open Items)

**Engineers must not ship to production without resolving all Blocker items:**

| Item | Severity | Reference | Status |
| --- | --- | --- | --- |
| CI/CD code signing pipeline (all 5 platforms) | Blocker | `ops/signing-pipeline.md` | Not implemented |
| WasmParity CI gate (wasm3 vs wasmtime output identity, ≤ 20 ms delta, block merge on diff) | Blocker | §4.4, TERA-FEAT §PLATFORM-02 | Not implemented |
| Dart FFI NativeFinalizer Clippy lint rule | Blocker | §4.3 | Not implemented |
| AppArmor / SELinux postinstall script (Linux) | High | TERA-FEAT §PLATFORM-16 | Not implemented |
| Gossip PSK rotation runbook (90-day cycle) | Medium | §9.2 | No runbook |
| PostgreSQL PITR recovery runbook | Medium | §9.5 | No runbook |
| Shamir ceremony runbook (Admin turnover procedure) | Medium | §5.1 | No runbook |

---

## 12. IMPLEMENTATION CONTRACT (NON-NEGOTIABLE RULES)

> **Read §0 (Data Object Catalog) in full before implementing any component.**
> Violating any rule below is a **BLOCKER — do not merge.**

### §12.1 — Security Rules

- [x] **KEY-01** — Every `Private Key` MUST reside in Secure Enclave (iOS/macOS), StrongBox (Android), or TPM 2.0 (Desktop/Linux). Storage in plaintext on disk, heap, or any exported form is forbidden under all conditions.

- [x] **KEY-02** — Every struct or variable holding plaintext MUST implement `ZeroizeOnDrop`. Plaintext MUST NOT survive scope exit. Verified with `cargo miri test` in CI.

- [x] **KEY-03** — All cryptographic operations MUST use the `ring` crate or `RustCrypto` workspace. Custom crypto implementations are forbidden. Wrapping C cryptographic libraries (OpenSSL, BoringSSL, libsodium) is forbidden.

- [x] **NET-01** — All network I/O between client and server MUST use TLS 1.3 + mTLS. No unencrypted channels. SHA-256 SPKI pinning hardcoded in Rust binary via `rustls`.

- [x] **NET-02** — eBPF/XDP is server-side Linux kernel technology only (☁️🗄️). Client platforms (iOS, Android, Huawei, macOS, Windows, Linux Desktop) do not implement eBPF. Desktop Linux uses `seccomp-bpf` for syscall filtering — a different subsystem with no network filtering capability.

- [x] **LOG-01** — Every Audit Log entry MUST carry a valid Ed25519 signature before persistence. Unsigned entries MUST be rejected at write time and never stored.

- [x] **LOG-02** — `hot_dag.db` is append-only. Physical deletion of CRDT events is forbidden. Deletion is represented exclusively by `Tombstone_Stub` entries.

### §12.2 — Data Integrity Rules

- [x] **DB-01** — Every DB schema change MUST be backward-compatible with WAL replay. A migration script is required for every schema version increment. Migrations execute inside `BEGIN EXCLUSIVE TRANSACTION`. A backup is created before any migration runs.

- [x] **DB-02** — `cold_state.db` MUST be rebuildable from `hot_dag.db` at any time and under any failure condition. If `cold_state.db` migration fails: drop and rebuild from `hot_dag.db`. Never abort without a complete recovery path.

- [x] **DB-03** — `PRAGMA wal_autocheckpoint = 1000` MUST be set on all SQLite databases. WAL files exceeding 50 MB (mobile) or 200 MB (desktop/server) MUST trigger automatic VACUUM.

### §12.3 — FFI and IPC Rules

- [x] **FFI-01** — No `pub extern "C"` function in the `ffi/` module may return `Vec<u8>`, `*const u8`, or `*mut u8` directly. All buffer transfers MUST use the token protocol (`tera_buf_acquire` / `tera_buf_release`). Enforced by CI Clippy lint — lint failure blocks merge.

- [x] **FFI-02** — UI layer MUST NOT hold decrypted payloads beyond the render frame. Plaintext delivered to UI is zeroized immediately after rendering.

- [x] **IPC-01** — State flow is strictly unidirectional: Rust Core → UI. UI sends Commands only. UI never writes state to Rust Core.

### §12.4 — Platform Rules

- [x] **PLT-01** — iOS `election_weight = 0`. iOS devices are never elected Merge Dictator. EMDP Tactical Relay (§6.7) is the sole exception — it operates in text-only Append-Only mode with no DAG merge and no MLS Epoch rotation.

- [x] **PLT-02** — NSE (iOS) and FCM Service (Android) MUST enforce ≤ 20 MB RAM via Circuit Breaker. On breach: terminate gracefully, set `main_app_decrypt_needed = true` in Shared Keychain, never crash without cleanup.

- [x] **PLT-03** — WASM `.tapp` MUST execute in Sandbox with `PROT_READ`-only access to DAG buffer. Write attempts outside sandbox boundaries MUST trigger `SIGSEGV` trap caught by `catch_unwind`.

- [x] **PLT-04** — Clipboard operations MUST route through Protected Clipboard Bridge. Direct OS clipboard API calls from Rust Core are forbidden.

- [x] **PLT-05** — Relay binary and mobile library MUST use `panic = 'unwind'`. `panic = 'abort'` is permitted only for WASM-compiled `.tapp` target binaries themselves.

### §12.5 — Fault Isolation Rules

- [x] **FLT-01** — `catch_unwind()` boundaries MUST be implemented at all four entry points: WASM sandbox execution, CRDT merge, MLS crypto operations, DAG write.

- [x] **FLT-02** — CRDT events MUST be written to `wal_staging.db` with `status = STAGED` before entering the MPSC channel. Events transition to `COMMITTED` only after pub/sub delivery acknowledgment. On relay restart: all `STAGED` entries MUST be replayed before accepting new connections.

- [x] **FLT-03** — On SIGTERM: relay daemon MUST call `wal_checkpoint(TRUNCATE)` within 30 seconds before exit. systemd `TimeoutStopSec = 35`.

### §12.6 — Observability Rules

- [x] **OBS-01** — Relay daemon MUST expose a Prometheus `/metrics` endpoint on `127.0.0.1:9100`. All metrics MUST be Zero-Knowledge: no user identifiers, no message content, no session data.

- [x] **OBS-02** — All metrics MUST be delayed 30 seconds vs event time to prevent timing correlation attacks.

- [x] **OBS-03** — `ComponentFault` signal MUST be emitted within 1 second of any caught panic.

---



## 16. [ARCHITECTURE] [IMPLEMENTATION] Observability Layer

> **Nguyên tắc Zero-Knowledge Observability:** Metrics và traces KHÔNG
> chứa plaintext message, User_ID thật, key material, hay bất kỳ thông tin
> có thể deanonymize user. Mọi telemetry content-free và pseudonymous.
> Đây là hard constraint, không phải best-practice.

---

### 16.1 [ARCHITECTURE] Stack Overview

## 17. [ARCHITECTURE] [IMPLEMENTATION] Schema Versioning Protocol

> **Nguyên tắc:** Mọi data schema có cross-component dependency PHẢI có
> formal versioning. Breaking changes chỉ được phép trong major version.
> Migration phải backward-compatible và có automated rollback.

---

### 17.1 [IMPLEMENTATION] hot_dag.db Schema Versioning

## 18. [ARCHITECTURE] [IMPLEMENTATION] Hydration Scheduler

> **Bài toán:** >50 clients reconnect đồng thời sau outage →
> concurrent WAL hydration → OOM-Kill VPS.
> Giải pháp: global semaphore + per-tenant rate limit + exponential backoff.

## 19. [ARCHITECTURE] [SECURITY] HSM High Availability

> **Vấn đề:** Single HSM = single point of failure cho License JWT signing
> và KMS Bootstrap. HSM failure → không issue được license mới → revenue block.

---

### 19.1 [ARCHITECTURE] Dual-HSM Setup

## 20. [ARCHITECTURE] [IMPLEMENTATION] TeraEdge Device

> **Bài toán:** Fully-remote enterprise (không có Desktop AC-powered) và
> field operations (quân đội, y tế dã chiến) không có Super Node.
> Không có Super Node = Mobile overload lại.
>
> **Giải pháp:** TeraEdge — mini-PC on-premise ($150-200) chạy TeraRelay
> + Super Node role trong cùng một thiết bị. Không cần cloud VPS.
> Phù hợp cho đơn vị có LAN nhưng không có Desktop cố định.

---

### 20.1 [ARCHITECTURE] TeraEdge Hardware Profile

| Tier | Hardware | Cost | Use Case |
|------|----------|------|----------|
| TeraEdge Nano | Raspberry Pi 5 (4GB) | ~$80 | SME remote, ≤50 users |
| TeraEdge Mini | Intel N100 mini-PC (8GB) | ~$150 | Enterprise remote, ≤500 users |
| TeraEdge Pro | ARM SBC + NVMe (16GB) | ~$300 | Gov field, ≤2000 users |

### 20.2 [ARCHITECTURE] TeraEdge Role Matrix

## 21. CHANGELOG

| Version | Date | Summary |
| --- | --- | --- |
| 0.2.6 | 2026-03-19 | Add §16 Observability Layer; §17 Schema Versioning; §19 HSM HA;
|         |            | §20 TeraEdge Device; Update §5.15 EpochId split-brain fix;
|         |            | Update §5.9.3 C_trunc 8B→16B; Update §10.6 RotatingCrlFilter |
| 0.2.3 | 2026-03-18 | Complete rewrite from scratch. Unified §0–§13 structure with stable anchors. Zero duplicate section numbering. All CHANGELOG entries populated. Rules section replaced with `[ ]` checklist using unique rule IDs (KEY-01, NET-01, etc.). Platform Behavior Matrices added (§3.1–§3.5). AI routing hint with explicit positive/negative routing directives. Incorporated all decisions from architecture sessions: EMDP Key Escrow (§6.7), Adaptive WAL batch sizing (§9.3), Component Fault Isolation with `panic='unwind'` mandate (§4.4), Relay WAL Staging at-least-once delivery (§9.3), Prometheus Zero-Knowledge metrics (§9.6), WasmParity CI gate requirement (§11.4), Configurable Dead Man Switch grace period (§5.1), Batched TreeKEM Update_Path delivery (§5.3), XPC Transaction Journal with retry policy (§11.1), iOS Double-Buffer Zeroize (§5.2), Adaptive QUIC Probe Learning (§9.2), Federation schema version negotiation (§9.4), Mobile DAG merge time-slicing (§7.3). |
| 0.2.1 | 2026-03-13 | Deprecated: eBPF/XDP, Hardware TEE (SGX/SEV), `mlock()` pinning, Envoy Sidecar — removed for VPS compatibility. Added: §3.5 Micro-Core Relay, §4.6 Soft-Enclave WASM Isolation (ChaCha8 + ZeroizeOnDrop), §3.4.2 SQLite OOM Prevention. |
| 0.1.4 | 2026-03-11 | Removed ODES/Blind Shard. Added E2EE Cloud Backup (§9.1). Simplified Mesh Gossip: iBeacon + Gossip Broadcast (removed 3D-A* routing). |
| 0.1.3 | 2026-03-05 | Added Hierarchical Crypto-Shredding (§5.35), SSA Retroactive Taint (§5.36), Anti-Snapshot TPM 2.0 Monotonic Counter. |
| 0.1.2 | 2026-03-04 | Added Constant-time Memory Access (§9.2), EMIP Plugin Integrity (§5.24), TeraVault VFS (§6.13). |

---

*Cross-references:*

- *Client IPC, OS hooks, WASM platform runtime → `TERA-FEAT` (`Feature_Spec.md`)*
- *UI state machine, animation, Glassmorphism states → `TERA-DESIGN` (`Design.md`)*
- *Plugin publishing, `.tapp` lifecycle, Marketplace rules → `TERA-MKT` (`Web_Marketplace.md`)*
- *Combined-failure chaos test scenarios → `TERA-TEST` (`TestMatrix.md`)*
- *Code signing pipeline → `ops/signing-pipeline.md`*
- *PostgreSQL PITR recovery → `ops/db-recovery.md`*
- *Shamir ceremony, Admin turnover → `ops/shamir-bootstrap.md`*

