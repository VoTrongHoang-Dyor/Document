<!-- markdownlint-disable MD041 -->

```yaml
# DOCUMENT IDENTITY
id:        "TERA-FEAT"
title:     "TeraChat — Feature Technical Specification"
version:   "0.5.0"
status:    "ACTIVE — Implementation Reference"
date:      "2026-03-23"
audience:  "Frontend Engineer, Mobile Engineer, Desktop Engineer, Product Engineer"
purpose:   "Defines all client-facing and system-level features. Maps every feature to a
            verified core module in Core_Spec.md (TERA-CORE). Governs platform-specific
            behavior, OS lifecycle hooks, IPC bridge, WASM runtime, local storage, and
            user interaction contracts."

depends_on:
  - id: "TERA-CORE"

consumed_by:
  - id: "TERA-DESIGN"
  - id: "TERA-MKT"
  - id: "TERA-TEST"

scope: |
  Client-side and system-level features of TeraChat across iOS, Android, Huawei, macOS,
  Windows, and Linux platforms. Includes the IPC bridge, OS lifecycle hooks, WASM runtime,
  local SQLite storage, push notification handling, platform-specific constraints, and
  operational infrastructure (INFRA-01 through INFRA-06, OBSERVE-01/02, CICD-01).

non_goals:
  - MLS cryptographic internals         → TERA-CORE §5
  - CRDT merge algorithms               → TERA-CORE §7
  - Server relay infrastructure         → TERA-CORE §9
  - UI animations and glassmorphism     → TERA-DESIGN
  - Plugin publishing and Marketplace   → TERA-MKT
  - Chaos engineering test scenarios    → TERA-TEST

assumptions:
  - Rust Core is the single source of truth for all business state.
  - UI layer is a pure renderer — holds no crypto keys, no business state.
  - Host adapters (Swift/Kotlin/ArkTS) handle all platform-specific OS APIs.
  - VPS relay has zero-knowledge of plaintext content.
  - TERA-CORE v2.0 is the canonical reference for all Core module contracts.

constraints_global:
  - All plaintext buffers use ZeroizeOnDrop; no plaintext outlives the render frame.
  - No raw pointer crosses the FFI boundary; FFI token protocol mandatory.
  - All cryptographic operations route through TERA-CORE crypto/ modules.
  - Platform-specific code lives in host adapters, never in shared Rust Core.
  - Every feature maps to at least one TERA-CORE module; orphan features are blockers.

breaking_changes_policy: |
  Schema migrations require {db_path}.bak.v{version} backup before execution.
  cold_state.db may be dropped and rebuilt from hot_dag.db at any time (DB-02 safety net).
  CoreSignal and UICommand enum changes: additive only; no removal without deprecation cycle.
  DelegationToken field additions permitted; removals require migration path.
  TERA-CORE §12.2 governs all DB migration rules (DB-01, DB-02, DB-03).

patch_history:
  - version: "0.5.0"
    date: "2026-03-23"
    issues_fixed:
      - "Issue-01: Dart FFI NativeFinalizer double-release race (PLATFORM-17)"
      - "Issue-02: iOS NSE Static Memory Arena additive overflow (F-02)"
      - "Issue-03: QUIC parallel probe race corrupts strict_compliance (F-14)"
      - "Issue-04: VACUUM INTO hot_dag concurrent Tokio writer race (F-04)"
      - "Issue-05: EMDP Key Escrow orphan on sudden Desktop loss (F-05)"
      - "Issue-06: WasmParity CI gate not implemented (F-07, CICD-01)"
      - "Issue-07: XPC Transaction Journal PENDING + unsynced WAL (F-07)"
      - "Issue-08: Shadow DB rename + NSURLSession TOCTOU (F-04)"
      - "Issue-09: Windows ARM64 SAB untested (§7.5)"
      - "Issue-10: Linux AppArmor/SELinux postinstall absent (F-15)"
      - "Issue-11: Huawei HMS CRL 4-hour revocation window (F-02)"
      - "Issue-12: Android 14+ FCM CDM revocation no fallback (F-02)"
      - "Issue-13: Dead Man Switch deferral no audit trail (F-11)"
      - "Issue-14: Federation OPA policy sync blocked by schema version (F-13)"
      - "Issue-15: BLE GATT pre-auth gap for ML-KEM key exchange (F-05)"
```

---

## §1 — EXECUTIVE SUMMARY

TeraChat is a Zero-Knowledge, end-to-end encrypted team messaging platform. The server relay receives only ciphertext and has no access to user identity, message content, or group membership. All cryptography and business logic live in a shared Rust Core binary deployed identically across iOS, Android, Huawei, macOS, Windows, and Linux.

**Architecture in one sentence:** A shared Rust Core (cryptography, CRDT DAG, network, storage) exposes a strict unidirectional IPC bridge to platform UI layers (Flutter/Swift/Tauri), with a blind VPS relay for ciphertext routing only.

### §1.1 Primary Objectives

| Objective | Mechanism |
|---|---|
| Zero-Knowledge E2EE at rest and in transit | MLS RFC 9420; AES-256-GCM; server-blind storage |
| Offline-first survival | BLE 5.0 / Wi-Fi Direct Mesh; CRDT DAG; Store-and-Forward |
| Extensible mini-app platform | WASM `.tapp` sandbox with capability-based isolation |
| Privacy-safe AI inference | Local ONNX/CoreML SLM with PII redaction; no raw prompt leaves device |
| Single-binary operational simplicity | VPS relay: 512 MB RAM; 5-minute setup; no cluster coordination |

### §1.2 Five Critical Features

| Feature | Why Critical |
|---|---|
| F-01: Secure E2EE Messaging | Core value proposition; all other features serve or protect it |
| F-05: Survival Mesh Networking | Differentiator; text messaging survives total Internet loss |
| F-03: IPC Bridge and State Sync | Foundation for all UI interaction; security boundary for key material |
| F-07: WASM Plugin Sandbox | Extensibility layer; untrusted code isolated from Core |
| F-10: AI / SLM Integration | Local inference with PII redaction; no cloud dependency for base tier |

### §1.3 Architecture Overview

```text
┌─────────────────────────────────────────────────────────┐
│  UI Layer (Swift / Flutter / Tauri)                      │
│  Pure renderer — no keys, no business state              │
├──────────────── IPC Bridge (F-03) ──────────────────────┤
│  CoreSignal ← (unidirectional) ← Rust Core             │
│  UICommand  → (commands only)  → Rust Core             │
│  Data Plane: SAB / JSI / Dart FFI (token protocol)     │
├─────────────────────────────────────────────────────────┤
│  Rust Core (shared binary across all platforms)          │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐  │
│  │ crypto/ │ │  crdt/   │ │ mesh/  │ │    infra/    │  │
│  │ MLS,    │ │ hot_dag  │ │ BLE,   │ │ relay, TURN, │  │
│  │ push,   │ │ cold_state│ │ WiFi   │ │ WASM, ONNX  │  │
│  │ zeroize │ │ snapshot │ │ Direct │ │ metrics     │  │
│  └─────────┘ └──────────┘ └────────┘ └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Host Adapters (Swift / Kotlin / ArkTS)                  │
│  Platform OS APIs — CallKit, NSE, FCM, HMS, BGTask       │
└──────────────── Platform Layer ─────────────────────────┘
         │                              │
    TLS 1.3 + mTLS                BLE / Wi-Fi Direct
         │                              │
┌────────────────┐            ┌─────────────────────┐
│  VPS Relay     │            │  Mesh Peer Network   │
│  Blind router  │            │  BLE Store-Forward   │
│  Ciphertext    │            │  (offline-only)      │
│  only; no keys │            └─────────────────────┘
└────────────────┘
```

---

## §2 — SYSTEM OVERVIEW

### §2.1 Architecture Overview

| Layer | Technology | Responsibility |
|---|---|---|
| UI Layer | Swift (iOS/macOS), Flutter (Android/Huawei), Tauri (Desktop) | Render only; issues UICommands; processes CoreSignals |
| IPC Bridge | FFI token protocol; SAB / JSI / Dart FFI | Zero-copy data transfer; no raw pointers; ZeroizeOnDrop |
| Rust Core | Shared binary (`libterachat_core.a` / `.so`) | All crypto, DAG, network, storage, policy enforcement |
| Host Adapters | Swift/Kotlin/ArkTS | Platform OS APIs; BLE, CallKit, NSE, FCM, HMS |
| VPS Relay | Rust daemon + Tokio | Blind ciphertext routing; pub/sub fanout; WAL staging |
| Blob Storage | MinIO / Cloudflare R2 / Backblaze B2 | Encrypted chunk storage by `cas_hash`; zero-knowledge |

### §2.2 Data Flow (Total)

```text
Send Path:
  User input → UICommand::SendMessage
    → Rust Core: AES-256-GCM encrypt (Epoch_Key, biometric gate)
    → CRDT_Event appended to hot_dag.db WAL (durable)
    → Online:  TLS 1.3 + mTLS → VPS Relay → wal_staging.db → pub/sub
    → Offline: BLE Control Plane → Mesh Store-and-Forward (≤ 4 KB, text only)
    → CoreSignal::StateChanged → UI viewport refresh

Receive Path:
  VPS Relay pub/sub → client receives ciphertext CRDT_Event
    → Rust Core: MLS decrypt → CRDT merge into hot_dag.db
    → CoreSignal::StateChanged → UI: UICommand::ScrollViewport
    → Core: tera_buf_acquire → Data Plane buffer write (decrypted)
    → UI: render 20-message viewport via token
    → UICommand::ReleaseBuffer → ZeroizeOnDrop (ref_count == 0)
```

### §2.3 Trust Boundaries

| Boundary | What crosses it | What never crosses it |
|---|---|---|
| Rust Core ↔ UI (FFI) | Opaque `u64` token; typed enum signals/commands | Raw pointers; decrypted payloads; key material |
| Rust Core ↔ VPS Relay | AES-256-GCM ciphertext; CRDT_Event (encrypted) | Plaintext; sender identity; group structure |
| Rust Core ↔ WASM sandbox | Sanitized `Vec<ASTNode>`; `sled` namespace writes | MLS key material; raw DAG access; filesystem |
| iOS NSE ↔ Main App | `nse_staging.db`; flag in Shared Keychain | Push_Key (NSE-only keychain group) |
| Client ↔ Blob Storage | Encrypted chunks (AES-256-GCM); `cas_hash` path | Plaintext; file names; sender identity |

### §2.4 Deployment Model

| Tier | VPS Spec | Monthly Cost | Setup Time |
|---|---|---|---|
| Solo (≤ 50 users) | 1 vCPU, 512 MB RAM, 20 GB SSD | $6 + $1 storage | 5 min |
| SME (≤ 500 users) | 2 vCPU, 2 GB RAM, 40 GB SSD | $12 + $5 storage | 10 min |
| Enterprise (≤ 5000 users) | 4 vCPU, 8 GB RAM, 100 GB SSD | $28 + $20 storage | 20 min |
| Gov (air-gapped) | Existing hardware | CAPEX only | 1 hour |

---

## §3 — DATA MODEL

### §3.1 Local Storage Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `cold_state.db` | SQLite, SQLCipher AES-256 | Disk, permanent | Until Remote Wipe or Crypto-Shredding | Key from Secure Enclave; never hardcoded | TERA-CORE §7.1 |
| `cold_state_shadow.db` | SQLite, transient | Disk, temporary | Created on Hydration batch; deleted after atomic rename | Write-locked via `ShadowMigrationLock` (Mutex) during migration | TERA-CORE §7.1 |
| `hot_dag.db` | SQLite WAL | Disk, permanent | Append-only; cleaned via checkpoint | Append-only; tombstones only; no physical deletion | TERA-CORE §7.1 |
| `nse_staging.db` | SQLite WAL, iOS NSE only | Disk | Per push payload; cleared after Main App decryption | NSE-only keychain group access | TERA-CORE §5.5 |
| `wal_staging.db` | SQLite WAL, relay only | Disk | Per event; cleared on `Committed` status | Server-side only; no client key access | TERA-CORE §9.3 |
| `NetworkProfile` | SQLite row | Local config DB | Per network identifier; updated on probe result | mTLS cert fingerprint + SSID hash as network ID | TERA-CORE §9.2 |
| `TappTransientState` | `sled` LSM-Tree rows | RAM + disk, per DID | Per `.tapp` session; cleared on Mesh Mode | AES-256-GCM encrypted | TERA-FEAT §F-07 |
| `metrics_buffer.db` | SQLite | Disk | Max 48h / 500 KB; flushed on reconnect | Aggregate only; no user-correlated data | TERA-FEAT §OBSERVE-01 |

### §3.2 In-Memory Ephemeral Objects

| Object | Type | Location | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `Decrypted_Chunk` | `[u8]` plaintext | RAM, `ZeroizeOnDrop` | Single 2 MB chunk; zeroed after render frame | Must not outlive render frame | TERA-CORE §5.3 |
| `ViewportCursor` | `{top_id: Uuid, bottom_id: Uuid}` | RAM | Duration of scroll session | No sensitive content | TERA-FEAT §F-03 |
| `RingBuffer_2MB` | Circular fixed buffer | User RAM | Reused across media stream sessions | ZeroizeOnDrop between sessions | TERA-FEAT §F-09 |
| `KVCacheSlot` | LZ4-compressed LLM context | RAM | Per `.tapp` session; LZ4-compressed when inactive | No raw PII; alias-mapped via SessionVault | TERA-FEAT §F-10 |
| `MemoryArbiter` | `{allocations: HashMap<ComponentId, usize>}` | RAM | Process lifetime; enforces RAM budget matrix | Allocation denied returns `MemoryDenied` | TERA-CORE §3.3 |

### §3.3 IPC Signal and Command Objects

| Object | Type | Transport | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `CoreSignal` | Typed Rust enum | FFI signal channel | Unidirectional Core → UI; no response expected | No key material; no plaintext content | TERA-CORE §4.2 |
| `UICommand` | Typed Rust enum | FFI command channel | Consumed once by Core; no replay | No key material; plaintext passed only in `SendMessage` | TERA-CORE §4.2 |
| `DataPlane_Payload` | Raw bytes | SAB ring buffer / JSI pointer / Dart FFI | Held until `tera_buf_release(token)` called | Zeroed on release; never held across render frames | TERA-CORE §4.3 |
| `FfiToken` | Opaque `u64` | FFI return value | Valid until `tera_buf_release` called | Carries monotonic `generation` counter; stale generation rejected | TERA-CORE §4.3 |

### §3.4 Push and Notification Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `Push_Key_N` | AES-256-GCM symmetric key | Secure Enclave (iOS) / StrongBox (Android) | Rotated after each MLS Epoch rotation | NSE-only Keychain group (`group.com.terachat.nse`) | TERA-CORE §5.5 |
| `PushKeyVersion` | `u32` | Shared Keychain (iOS) / StrongBox metadata | Incremented on each rotation; also bumped by server-side revocation signal | Read by NSE to match payload header | TERA-CORE §5.5 |
| `NSE_StagedCiphertext` | Raw ciphertext bytes | `nse_staging.db` | Cleared after successful Main App decryption | Ciphertext only; no plaintext at rest | TERA-CORE §5.5 |

### §3.5 WASM Plugin Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `DelegationToken` | `{source_did, target_did, permissions, expires_at, signature}` | RAM + `hot_dag.db` | TTL 30 days; revocable by Admin at any time | Ed25519-signed by DeviceIdentityKey; tamper-evident | TERA-FEAT §F-08 |
| `EgressNetworkRequest` | Protobuf | In-flight | Single request; sanitized by Host Proxy | OPA policy check before execution; no raw TCP/UDP | TERA-CORE §4.1 |
| `XpcJournalEntry` | `{tx_id: Uuid, status: Pending\|Verified\|Committed}` | `hot_dag.db` | Per XPC transaction; cleared on Committed | Persisted with `synchronous=FULL` connection for crash safety | TERA-FEAT §F-07 |

---

## §4 — FEATURE MODEL

### §4.1 Feature Categories

| Category | Features | Section |
|---|---|---|
| Secure Messaging | E2EE send/receive, push notification | F-01, F-02 |
| IPC and State | Bridge, synchronization, memory management | F-03, F-15 |
| Local Storage | Two-tier SQLite, schema migration, hydration | F-04 |
| Survival Mesh | BLE/Wi-Fi Direct, EMDP, role management | F-05 |
| Voice and Video | WebRTC, CallKit, TURN failover | F-06 |
| WASM Plugins | `.tapp` lifecycle, sandbox, XPC recovery | F-07 |
| Plugin IPC | Delegation Tokens, inter-`.tapp` sharing | F-08 |
| Media Transfer | Chunked upload, deduplication, streaming | F-09 |
| AI / SLM | Local inference, PII redaction, cloud routing | F-10 |
| Device Security | Screen protection, clipboard, wipe | F-11 |
| Identity | Enrollment, recovery, geofencing | F-12 |
| Admin Controls | Policy, SCIM, audit, license | F-13 |
| Network Management | ALPN, probe learning, fallback | F-14 |
| Infrastructure | Compute distribution, blob storage, relay health | INFRA-01–06 |
| CI/CD | Build gates, chaos testing, SBOM | CICD-01, INFRA-06 |
| Observability | Client metrics, DAG merge UI | OBSERVE-01, OBSERVE-02 |

### §4.2 Feature ↔ Core Mapping

| Feature ID | Feature Name | Primary Core Modules | TERA-CORE References |
|---|---|---|---|
| F-01 | Secure E2EE Messaging | `crypto/mls_engine.rs`, `crdt/dag.rs` | §5.3, §7.1, §8.1, §4.2, §4.3 |
| F-02 | Push Notification Delivery | `crypto/push_ratchet.rs` | §5.5, §8.3, §4.2 |
| F-03 | IPC Bridge & State Sync | `ffi/ipc_bridge.rs`, `ffi/token_protocol.rs` | §4.2, §4.3, §2.2 |
| F-04 | Local Storage Management | `crdt/dag.rs`, `crdt/snapshot.rs` | §7.1, §7.4, §12.2 (DB-01, DB-02, DB-03) |
| F-05 | Survival Mesh Networking | `mesh/` (all six modules) | §6.1, §6.2, §6.3, §6.4, §6.5, §6.6, §6.7 |
| F-06 | Voice and Video Calls | `infra/relay.rs` (TURN), host adapters | §10.4, §6.4, §9.2, §5.3 |
| F-07 | WASM Plugin Sandbox | `ffi/token_protocol.rs`, platform WASM adapter | §4.1, §4.4, §3.2 |
| F-08 | Inter-`.tapp` IPC | `ffi/ipc_bridge.rs` | §4.2, §4.3, §3.2 |
| F-09 | Media and File Transfer | `crypto/mls_engine.rs`, `infra/relay.rs` | §5.3, §9.5, §7.1, §8.1 |
| F-10 | AI / SLM Integration | `infra/relay.rs` (VPS Enclave) | §3.3, §3.6, §4.4 |
| F-11 | Device Security | `crypto/hkms.rs`, `crypto/zeroize.rs` | §5.1, §5.2, §12.4 (PLT-04) |
| F-12 | Identity and Onboarding | `crypto/hkms.rs`, `crypto/mls_engine.rs` | §5.1, §5.2, §5.3 |
| F-13 | Admin Console | `infra/federation.rs`, `infra/metrics.rs` | §3.2, §5.1, §9.5, §9.6 |
| F-14 | Adaptive Network Management | `infra/relay.rs` | §9.2, §4.2 |
| F-15 | Crash-Safe WAL Management | `crdt/dag.rs`, `infra/wal_staging.rs` | §4.4, §7.1, §9.3, §12.2 |

---

### F-01: Secure E2EE Messaging

**Description:** Send and receive text messages encrypted end-to-end using MLS RFC 9420. The VPS relay receives only ciphertext. DAG merge for large backlogs is time-sliced to prevent mobile ANR.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow:**

1. User types message. UI sends `UICommand::SendMessage { recipient_did, plaintext }` via FFI.
2. Rust Core looks up `Epoch_Key` from RAM `ZeroizeOnDrop` struct.
3. Core encrypts: `AES-256-GCM(Epoch_Key, plaintext)`. Nonce = `Base_Nonce XOR chunk_seq_number`.
4. Core constructs `CRDT_Event`. Ed25519 signature via `DeviceIdentityKey` (biometric gate required).
5. Event appended to `hot_dag.db` WAL atomically before network dispatch.
6. **Online path:** TLS 1.3 + mTLS → VPS Relay → `wal_staging.db` → pub/sub fanout.
7. **Offline path:** BLE Control Plane → Mesh Store-and-Forward (text only, ≤ 4 KB).
8. Core emits `CoreSignal::StateChanged { table: "messages", version }`.
9. UI issues `UICommand::ScrollViewport`. Core returns 20-message viewport snapshot.
10. Plaintext `ZeroizeOnDrop` after render frame.

**DAG Merge (Mobile — ANR Prevention):**

- Mobile hard limit: `MAX_MOBILE_MERGE_EVENTS = 3000`.
- Backlog > 3000: emit `CoreSignal::StateChanged` with `SnapshotRequired`; delegate full merge to Desktop.
- Backlog > 500: `CoreSignal::DagMergeProgress { completed, total }` emitted every 200 ms.
- Mobile merge is time-sliced in batches of 100 events with `tokio::task::yield_now()` between batches.

**Failure Handling:** → §10.4 (Runtime), §10.1 (Network)

---

### F-02: Push Notification Delivery (E2EE)

**Description:** Deliver E2EE-encrypted push notifications to backgrounded devices. Decryption is local — APNs, FCM, and HMS never receive plaintext. A versioned Push Key Ladder handles key rotation without message loss.

**Supported Platforms:** 📱 iOS (NSE), 📱 Android (FCM), 📱 Huawei (HMS), 💻 macOS (daemon), 🖥️ Windows, 🖥️ Linux

**[PATCH Issue-02] iOS NSE RAM Budget — Cumulative Breakdown:**

> **CRITICAL:** The NSE Static Memory Arena is capped at 10 MB. Any ONNX workload is structurally
> prohibited from the NSE build target. Violations will silently exceed the 20 MB OS ceiling and
> cause Jetsam kill with no user-visible error.

| Component | Allocated | Notes |
|---|---|---|
| NSE Static Memory Arena | 10 MB | Pre-allocated at startup |
| MLS decrypt (ciphertext + overhead) | ~2 MB | Per message |
| OS system overhead inside NSE | ~3 MB | dyld, libsystem, stack |
| **Total used** | **~15 MB** | **5 MB margin** |
| ONNX Micro-NER (smallest model) | 8 MB | **PROHIBITED in NSE** |
| Any WASM workload | variable | **PROHIBITED in NSE** |

The 5 MB margin is **insufficient for any ONNX or WASM workload**. The `push_ratchet.rs` module
must be compiled with `features = ["nse-only"]` which strips all ONNX, CRDT Automerge, and
SQLCipher dependencies at link time. A `debug_assert!(NsePolicy::is_onnx_prohibited())` fires at
NSE entry point in both debug and release-with-debug-info builds.

```rust
// NSE build target — Cargo.toml
[features]
nse-only = ["terachat-crypto-minimal"]  # strips MLS, CRDT, SQLCipher, ONNX

// Entry point guard
pub fn nse_entry_point() {
    #[cfg(feature = "nse-only")]
    debug_assert!(
        !cfg!(feature = "onnx"),
        "FATAL: ONNX linked into NSE build — will exceed 20 MB iOS ceiling"
    );
    // ...
}
```

**[PATCH Issue-02] Version-mismatch path:**
On `push_key_version` mismatch, the NSE **defers ALL ML inference to Main App**. No NER, no ONNX,
no model loading in NSE path. The staged ciphertext is forwarded to Main App which handles full
decryption with the 2 GB Main App RAM budget.

**Platform-Specific Behavior:**

| Platform | Push Channel | Process | RAM Constraint |
|---|---|---|---|
| 📱 iOS | APNs `mutable-content: 1` | `UNNotificationServiceExtension` (NSE) | ≤ 20 MB hard (OS) |
| 📱 Android | FCM `priority = "high"` | `FirebaseMessagingService` | No hard limit |
| 📱 Huawei | HMS Push Kit Data Message | HarmonyOS background service | No hard limit |
| 💻 macOS | APNs (LaunchAgent) | `terachat-daemon` (~4.5 MB RAM) | No hard limit |
| 🖥️ Windows | WNS / `terachat-daemon` | Windows Service | No hard limit |
| 🖥️ Linux | `terachat-daemon` | systemd user service | No hard limit |

**User Flow (iOS NSE — primary path):**

1. APNs delivers encrypted payload. iOS wakes NSE (≤ 20 MB RAM enforced).
2. NSE allocates Static Memory Arena (10 MB, pre-allocated at startup, NSE-only build). **No ONNX.**
3. NSE reads `Push_Key_N` from Shared Keychain (Access Group: `group.com.terachat.nse`).
4. NSE reads `push_key_version` from payload header.
5. **Version match:** AES-256-GCM decrypt in arena → display OS notification → `ZeroizeOnDrop` arena.
6. **Version mismatch or payload_size > 4 KB or epoch_delta > 1 (Ghost Push):**
   - Cache raw ciphertext to `nse_staging.db`.
   - Set `main_app_decrypt_needed = true` in Shared Keychain.
   - Send `content-available: 1` wake signal.
   - Main App wakes → rotates `Push_Key` → decrypts `nse_staging.db` → displays notification.
   - **All ML inference deferred to Main App path only.**

**[PATCH Issue-11] Huawei HMS CRL Revocation Fast-Path:**

Huawei CRL refresh baseline is ≤ 4 hours vs ≤ 30 minutes on iOS/Android. This creates a security
window where a revoked Huawei device can decrypt push notifications for up to 4 hours.

**Server-side mitigation:** On SCIM-triggered device revocation, the relay MUST:

1. Immediately increment `push_key_version` for the revoked `device_did` in the server-side push
   key version table.
2. Inject the new version number into all subsequent push payload headers destined for that device.
3. The Huawei device's stale key cannot decrypt the new version → Ghost Push (no content).

```rust
// Relay-side: push key version bump on revocation
async fn revoke_device_push_access(device_did: &DeviceId, db: &Pool) {
    // Atomic increment — forces Ghost Push on stale Huawei keys
    sqlx::query!(
        "UPDATE device_push_versions SET version = version + 1 WHERE device_did = $1",
        device_did.as_str()
    ).execute(db).await?;
    // CRDT event: notify group of revocation for MLS epoch rotation
    emit_mls_remove_member(device_did).await?;
}
```

**CRL SLA disclosure:** Huawei devices have a worst-case 4-hour CRL propagation delay. This must
be disclosed in enterprise SLA documentation. The push key version bump mitigates content exposure
but MLS epoch rotation (full revocation) may take up to 4 hours on Huawei without foreground app.

**[PATCH Issue-12] Android 14+ CDM Permission Revocation Detection:**

Companion Device Manager (CDM) permission can be revoked by the user at any time via
Settings → Apps → Special App Access. When revoked, push notifications drop silently in the
Android 14 "Restricted" battery bucket (≤ 10 FCM messages/hour).

```kotlin
// FirebaseMessagingService — CDM health check on every FCM message receipt
override fun onMessageReceived(message: RemoteMessage) {
    val cdm = getSystemService(CompanionDeviceManager::class.java)
    val associations = cdm.myAssociations
    if (associations.isEmpty()) {
        // CDM permission revoked — notify Core and surface re-grant prompt
        TeraCore.emitComponentFault("fcm_companion", FaultSeverity.Warning)
        showCdmReGrantNotification()  // Deep-link to Settings
    }
    // Proceed with FCM message handling
    TeraCore.handleFcmMessage(message.data)
}

private fun showCdmReGrantNotification() {
    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
        data = Uri.fromParts("package", packageName, null)
    }
    // Persistent banner: "Notification delivery degraded — tap to restore"
    NotificationManagerCompat.from(this).notify(
        NOTIF_CDM_REVOKED,
        buildCdmReGrantNotification(intent)
    )
}
```

**Observability:**

- Metric: `nse_circuit_breaker_trips`, `push_key_version_mismatches` (OBSERVE-01).
- Log: `HUAWEI_CRL_STALE` on Huawei CRL-dependent decryption failure.
- Log: `FCM_CDM_REVOKED` when CDM association missing on Android 14+.
- Signal: `CoreSignal::ComponentFault { component: "fcm_companion", severity: Warning }` on CDM revocation.

**Failure Handling:** → §10.3 (Key Failure)

- NSE OOM: Circuit Breaker terminates NSE gracefully. Sets `main_app_decrypt_needed = true`.
- `Push_Key` not found in Keychain: display generic "New message" notification with no content.
- HMS polling delay (Huawei): server-side push key version bump mitigates exposure; log `HUAWEI_CRL_STALE`.
- CDM revocation (Android 14+): emit `ComponentFault`; show persistent re-grant banner.

---

### F-03: IPC Bridge and State Synchronization

**Description:** All communication between Rust Core and the UI layer routes through a strict unidirectional IPC bridge. No raw pointer crosses the FFI boundary. The Dart FFI `TeraSecureBuffer` wrapper is mandatory on Android/Huawei (PLATFORM-17).

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**Data Plane Transport Selection:**

| Platform | Transport | API | Throughput |
|---|---|---|---|
| 📱 iOS | C++ JSI Shared Memory Pointer | `UniquePtr` + token protocol | ~400 MB/s |
| 📱 Android | Dart FFI TypedData | Zero-copy into C ABI | ~400 MB/s |
| 📱 Huawei | Dart FFI TypedData | Zero-copy into C ABI | ~400 MB/s |
| 💻 macOS | SharedArrayBuffer ring buffer | COOP+COEP headers required | ~500 MB/s |
| 🖥️ Windows | SAB Tier 1 → Named Pipe fallback | Auto-selected at runtime | ~500 / ~200 MB/s |
| 🖥️ Linux | SAB Tier 1 → Named Pipe → stdin fallback | Auto-selected at runtime | ~500 / ~200 / ~50 MB/s |

**Failure Handling:** → §10.4 (Runtime)

- SAB unavailable: auto-downgrade to Named Pipe. Log tier change to audit trail (IPC-02 mandatory).
- Token not found on `ReleaseBuffer`: return `BufferNotFound`; UI re-issues `ScrollViewport`.

---

### F-04: Local Storage Management

**Description:** Manage the two-tier SQLite storage system (`hot_dag.db` + `cold_state.db`): WAL anti-bloat via checkpoint, crash-safe schema migrations, and shadow paging hydration.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**[PATCH Issue-04] WAL Auto-Compaction — Checkpoint-First Policy:**

> **BREAKING CHANGE from v0.4.0:** The primary WAL compaction path is now
> `PRAGMA wal_checkpoint(TRUNCATE)`, not `VACUUM INTO`. The previous
> `VACUUM INTO hot_dag_tmp.db` + POSIX rename pattern introduced a concurrent
> Tokio writer race: writers could append `CRDT_Event` entries to `hot_dag.db`
> WAL between the VACUUM completion and the atomic rename, orphaning those
> events in the old WAL. Since `hot_dag.db` is append-only (no deleted rows),
> VACUUM reclaims nothing — CHECKPOINT is the correct primitive.

**User Flow — WAL Auto-Compaction:**

1. Rust Core monitors WAL file size every 60 s via background Tokio task.
2. If WAL > 50 MB (mobile) or > 200 MB (desktop): trigger checkpoint sequence.
3. Execute `PRAGMA wal_checkpoint(TRUNCATE)` — no rename, no exclusive lock, no race.
   - This operation is concurrent-safe: active readers see a consistent snapshot.
   - Writers are not blocked; they continue appending to the WAL during checkpoint.
4. **`VACUUM INTO` is reserved for explicit admin-triggered defragmentation only:**
   - Protected by `BEGIN EXCLUSIVE TRANSACTION`.
   - Not triggered by background monitoring.
   - Documented as a maintenance-only operation.
5. Emit `CoreSignal::StateChanged` after checkpoint completes.

```rust
// Primary compaction path — safe for concurrent Tokio writers
pub async fn compact_hot_dag(db: &SqlitePool) -> Result<()> {
    // TRUNCATE mode: resets WAL to empty, reclaims disk space
    // Safe: no rename, no exclusive lock, no orphaned entries
    sqlx::query("PRAGMA wal_checkpoint(TRUNCATE)")
        .execute(db).await?;
    Ok(())
}

// Admin-only defragmentation — NEVER called by background monitor
pub async fn defragment_hot_dag_admin_only(db: &SqlitePool) -> Result<()> {
    // BEGIN EXCLUSIVE blocks all readers and writers
    sqlx::query("BEGIN EXCLUSIVE TRANSACTION").execute(db).await?;
    sqlx::query("VACUUM INTO 'hot_dag_defrag_tmp.db'").execute(db).await?;
    sqlx::query("COMMIT").execute(db).await?;
    // Atomic rename only after exclusive lock released
    tokio::fs::rename("hot_dag_defrag_tmp.db", "hot_dag.db").await?;
    Ok(())
}
```

**[PATCH Issue-08] Shadow DB Write Lock — TOCTOU Fix:**

> The previous `ShadowMigrationLock { migration_in_progress: AtomicBool }` was
> susceptible to TOCTOU: iOS NSURLSession background completion handlers run on
> arbitrary libdispatch threads, making the check-then-write compound operation
> non-atomic. Replaced with `Mutex<bool>` to ensure mutual exclusion across
> the entire check-and-write sequence.

```rust
// PATCHED: Mutex<bool> replaces AtomicBool for TOCTOU safety
pub struct ShadowMigrationLock {
    migration_in_progress: tokio::sync::Mutex<bool>,
}

impl ShadowMigrationLock {
    /// NSURLSession completion handler MUST call this before writing.
    /// Holds the lock for the entire check+write to prevent TOCTOU.
    pub async fn write_or_queue_to_hot_dag<F, R>(&self, f: F) -> R
    where
        F: FnOnce(WriteTarget) -> R,
    {
        let guard = self.migration_in_progress.lock().await;
        let target = if *guard {
            WriteTarget::HotDag  // migration in progress — redirect
        } else {
            WriteTarget::ShadowDb
        };
        f(target)
        // guard dropped here — lock released
    }
}
```

```swift
// Swift host adapter — os_unfair_lock wraps the FFI call
// ensures no libdispatch thread races the Rust Mutex
private let shadowLock = os_unfair_lock_s()

func handleNSURLSessionCompletion(_ data: Data, _ url: URL) {
    os_unfair_lock_lock(&shadowLock)
    defer { os_unfair_lock_unlock(&shadowLock) }
    tera_core_write_chunk_safe(data.bytes, data.count)  // FFI checks Mutex internally
}
```

**User Flow — Schema Migration:**

1. On DB open: read `PRAGMA user_version` from `hot_dag.db`.
2. If `user_version < CURRENT_SCHEMA_VERSION`:
   - Create backup: `{db_path}.bak.v{current_version}`.
   - `BEGIN EXCLUSIVE TRANSACTION`.
   - Run migration scripts in version order.
   - `PRAGMA user_version = CURRENT_SCHEMA_VERSION`.
   - `COMMIT`.
3. If `cold_state.db` migration fails: drop file, rebuild from `hot_dag.db` (DB-02). Log `COLD_STATE_REBUILD`.

**User Flow — Shadow Paging Hydration:**

1. Core receives `Snapshot_CAS` reference for a new snapshot.
2. Set `ShadowMigrationLock.migration_in_progress = true` (Mutex-protected).
3. Download snapshot in 2 MB chunks to `cold_state_shadow.db`.
4. Verify `SHA-256(downloaded_content) == cas_uuid`. Reject and restart on mismatch.
5. On full verification: atomic `rename(cold_state_shadow.db → cold_state.db)`.
6. Set `ShadowMigrationLock.migration_in_progress = false`.
7. Emit `CoreSignal::StateChanged { table: "all", version }`.
8. If interrupted: delete `cold_state_shadow.db`; `cold_state.db` unchanged. Resume from `Hydration_Checkpoint`.

**Constraints:**

- `hot_dag.db`: append-only. Physical deletion forbidden. Tombstones only.
- **Primary compaction: `PRAGMA wal_checkpoint(TRUNCATE)` only.** `VACUUM INTO` only under `BEGIN EXCLUSIVE` for admin defrag.
- `PRAGMA wal_autocheckpoint = 1000` enforced on all SQLite databases (DB-03).
- `ShadowMigrationLock` uses `tokio::sync::Mutex<bool>`, not `AtomicBool`.

**Failure Handling:** → §10.2 (Storage Failure)

- WAL bloat > 200 MB (mobile): emit `CoreSignal::MemoryPressureWarning`. UI banner shown.
- Checkpoint fails: log error, retry on next trigger. Do not crash.
- Schema migration fails on `cold_state.db`: drop, rebuild. Log `COLD_STATE_REBUILD`.
- Hydration interrupted: delete shadow, restart from `Hydration_Checkpoint`.

---

### F-05: Survival Mesh Networking

**Description:** When Internet is unavailable, TeraChat activates a BLE 5.0 / Wi-Fi Direct peer-to-peer Mesh for offline text messaging via Store-and-Forward. WASM plugins, AI inference, voice calls, and multi-hop file transfer are suspended.

**Supported Platforms:** 📱 iOS (Leaf/EMDP), 📱 Android (Relay), 📱 Huawei (Relay), 💻 macOS (Super Node), 🖥️ Windows (Super Node), 🖥️ Linux (Super Node)

**[PATCH Issue-15] BLE GATT Pre-Authentication Before ML-KEM Key Exchange:**

> A rogue BLE device can accept a GATT connection and participate in the ML-KEM-768 handshake
> before identity is verified, leaking the ephemeral PQ public key and enabling fingerprinting.
> A 1-RTT GATT-level challenge-response now precedes all key material transmission.

**GATT Pre-Auth Protocol (inserted as step 6.5 between peer discovery and key exchange):**

```text
Step 6.0: BLE Stealth Beacon discovery (identity commitment in 31-byte PDU)
Step 6.5: [NEW] GATT Pre-Authentication:
  a. Connecting peer sends Challenge:
     { slot_rotation_counter: u64, nonce: [u8; 32] }  ← derived from current beacon slot
  b. Responding peer signs with DeviceIdentityKey (Ed25519):
     Proof = Ed25519Sign(DeviceIdentityKey, Challenge || nonce)
  c. Connecting peer verifies Proof against the identity_commitment in the beacon.
  d. Only on successful verification → proceed to ML-KEM key exchange.
  e. GATT connection CLOSED immediately on verification failure.
Step 7.0: ML-KEM-768 + X25519 Hybrid Handshake (only authenticated peers)
```

```rust
// Rust Core GATT pre-auth before key exchange
async fn authenticate_gatt_peer(
    peer_beacon: &BleStealthBeacon,
    gatt_conn: &mut GattConnection,
) -> Result<AuthenticatedPeer, MeshAuthError> {
    let nonce = ring::rand::generate::<[u8; 32]>()?;
    let challenge = GattChallenge {
        slot_rotation_counter: peer_beacon.slot_counter,
        nonce,
    };
    gatt_conn.send(&challenge.encode()).await?;
    
    let proof: GattProof = gatt_conn.recv_timeout(Duration::from_millis(500)).await?;
    
    // Verify against identity_commitment from beacon: HMAC(R, PK_identity)[0:8]
    let expected_pk = peer_beacon.identity_commitment.recover_pubkey()?;
    ed25519_verify(&expected_pk, &challenge.encode(), &proof.signature)?;
    
    Ok(AuthenticatedPeer { peer_id: proof.device_id, pubkey: expected_pk })
}
```

**[PATCH Issue-05] EMDP Key Escrow — Proactive Broadcast & Sudden Desktop Loss:**

> The previous spec required Desktop to transmit `EmdpKeyEscrow` only when going offline.
> In practice, Desktops go offline abruptly (power failure, kernel panic, hard network partition)
> before escrow is transmitted. This leaves the EMDP window of messages permanently unrecoverable.

**Corrected EMDP Key Escrow Protocol:**

```rust
pub struct EmdpKeyEscrow {
    relay_session_key: AesKey256,
    emdp_start_epoch: u64,
    emdp_expires_at: u64,     // now() + 3600
    escrow_generation: u32,   // monotonically increasing; iOS stores latest
}

// Desktop: proactive broadcast on EMDP ACTIVATION (not only on graceful shutdown)
async fn activate_emdp_mode(ios_relay_pubkey: &Curve25519PublicKey) {
    let escrow = EmdpKeyEscrow::new();
    let encrypted = ecies_encrypt(ios_relay_pubkey, &escrow.encode());
    ble_control_plane_send(BleMsg::EmdpKeyEscrow(encrypted)).await;
    
    // Re-broadcast every 5 minutes while EMDP is active
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(300));
        loop {
            interval.tick().await;
            if emdp_state.is_active() {
                ble_control_plane_send(BleMsg::EmdpKeyEscrow(encrypted.clone())).await;
            } else {
                break;
            }
        }
    });
}
```

**Sudden Desktop Loss (Failure Case):**

If the Desktop goes offline before the first escrow broadcast (power failure within the first 30
seconds of EMDP activation), the iOS Tactical Relay enters `CAUSAL_FREEZE`:

```text
Sudden Desktop Loss Before Escrow:
  iOS detects Desktop gone + no EmdpKeyEscrow received
      ↓
  Enter CAUSAL_FREEZE: append-only, no new EMDP relay session started
  UI: "Secure relay key unavailable — messages held locally"
      ↓
  Desktop reconnects:
    if tainted_escrow == true → full MLS Epoch rotation BEFORE DAG merge
    Desktop regenerates session key, transmits fresh EmdpKeyEscrow
    DAG merge proceeds with new epoch context
    tainted_escrow = false
```

```rust
pub struct EmdpState {
    tainted_escrow: bool,  // true if Desktop disconnected before first escrow
    causal_freeze: bool,   // true when no valid escrow available
}

// On Desktop reconnect
fn handle_desktop_reconnect(emdp: &mut EmdpState, dag: &mut DagEngine) {
    if emdp.tainted_escrow {
        // Must rotate epoch BEFORE merging orphaned messages
        dag.trigger_mls_epoch_rotation_mandatory().await;
        emdp.tainted_escrow = false;
    }
    emdp.causal_freeze = false;
    dag.merge_emdp_window_messages().await;
}
```

**User Flow — Activation:**

1. Rust Core detects all three ALPN paths unavailable.
2. Core emits `CoreSignal::TierChanged { new_tier: MeshMode, reason: NoInternet }`.
3. UI transitions to Mesh Mode visual state.
4. User confirms Mesh activation (required: OS BLE permission prompt).
5. Core calls host adapter FFI: `request_mesh_activation()`.
6. Devices within range discover each other via BLE Stealth Beacons.
7. **[PATCH 15]** GATT Pre-Auth challenge-response before any key material exchange.
8. Text messages route via BLE Store-and-Forward (payload ≤ 4 KB per hop).

**Role Assignment:**

```rust
fn assign_role(device: &DeviceInfo) -> MeshRole {
    match device.os_type {
        OsType::iOS => MeshRole::LeafNode,  // always; election_weight = 0
        OsType::MacOS | OsType::Windows | OsType::Linux
            if device.power_source == PowerSource::AC =>
            MeshRole::SuperNode,
        OsType::Android
            if device.available_ram_mb >= 3_072 && device.battery_pct >= 40 =>
            MeshRole::RelayNode,
        _ => MeshRole::LeafNode,
    }
}
```

**Store-and-Forward Quotas:**

| Role | Storage Quota | Message TTL |
|---|---|---|
| Super Node (Desktop) | 500 MB – 1 GB | 48 – 72 h |
| Relay Node (Android) | 100 MB | 24 h |
| Leaf Node (iOS) | 50 MB, receive-only | N/A |
| Tactical Relay (EMDP iOS) | 1 MB, text-only CRDT buffer | 60 min |

**EMDP (Emergency Mobile Dictator Protocol) — Full Protocol:**

- Activation: no Desktop present; Internet unavailable; ≥ 2 iOS devices; battery > 20%.
- Tactical Relay selected by: `max(battery_pct × 100 + (ble_rssi + 100))`.
- **[PATCH 05]** Escrow transmitted proactively on activation + re-broadcast every 5 minutes.
- Hard constraints: text-only, 1 MB buffer, TTL 60 min, no DAG merge, no MLS Epoch rotation.
- TTL extension (at T-10 min): broadcast `EMDP_TTL_EXTENSION_REQUEST`; peer with battery > 30% accepts.
- Sudden Desktop loss before escrow → `CAUSAL_FREEZE`; mandatory epoch rotation on reconnect.

**Observability:**

- Signal: `CoreSignal::TierChanged { new_tier, reason }` on every Mesh activation or ALPN change.
- Signal: `CoreSignal::MeshRoleChanged { new_role }` on role transition.
- Signal: `CoreSignal::EmdpExpiryWarning { minutes_remaining }` at T-10 min and T-2 min.
- Signal: `CoreSignal::EmdpCausalFreeze` when sudden Desktop loss before escrow.

**Failure Handling:** → §10.1 (Network Failure)

- All-iOS Mesh, no EMDP conditions: Causal Freeze (read-only). No DAG writes until non-iOS node joins.
- EMDP TTL expired, no hand-off found: enter SoloAppendOnly mode. Merge deferred.
- Sudden Desktop loss before first escrow: enter `CAUSAL_FREEZE`; mandatory epoch rotation on reconnect.

---

### F-06: Voice and Video Calls (WebRTC)

**Description:** Peer-to-peer encrypted voice and video calls via WebRTC DTLS-SRTP. SDP signaling over MLS E2EE channel. TURN relay is blind.

**Supported Platforms:** 📱 iOS (CallKit required), 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-07: WASM Plugin Sandbox (`.tapp` Lifecycle)

**Description:** Execute untrusted third-party mini-apps inside a WASM sandbox with capability-based isolation.

**Supported Platforms:** 📱 iOS (`wasm3`), 📱 Android (`wasmtime`), 📱 Huawei (`wasmtime`), 💻 macOS (`wasmtime` in XPC Worker), 🖥️ Windows (`wasmtime`), 🖥️ Linux (`wasmtime`)

**[PATCH Issue-06] WasmParity CI Gate — Sprint 1 Blocker:**

> **STATUS CHANGE: "Not implemented" → Sprint 1 Blocker.**
> The WasmParity gate must be operational before ANY `.tapp` Marketplace listing.
> Key behavioral divergences between wasm3 (iOS) and wasmtime (Desktop):
>
> - NaN canonicalization: wasm3 propagates NaN payloads differently from Cranelift
>   `--enable-nan-canonicalization`. Any `.tapp` using floats for scoring or routing
>   produces different outputs on iOS vs Android silently.
> - Linear memory growth failure semantics differ between engines.
> - Per-call latency on wasm3 is 15–20 ms higher; timing-sensitive token bucket logic
>   (50 req/s limit) may spuriously hit circuit breaker on iOS wasm3.

```toml
# Cargo.toml — wasm3 as dev-dependency for CI WasmParity gate
[dev-dependencies]
wasm3 = { version = "0.4", features = ["build-lib"] }  # interpreter for CI parity testing
wasmtime = { version = "18" }

[features]
nse-only = ["terachat-crypto-minimal"]  # NSE build strips ONNX/CRDT/SQLCipher
```

```rust
// tests/wasm_parity.rs — Sprint 1 mandatory gate
#[test]
fn wasm_parity_integer_arithmetic() {
    // Use INTEGER test vectors ONLY — no f32/f64 in initial gate
    // Float vectors added after NaN canonicalization is verified per-engine
    let wasm_bytes = include_bytes!("fixtures/test_plugin.wasm");
    let input = b"\x01\x02\x03\x04";  // deterministic integer input

    let wasm3_out = run_wasm3(wasm_bytes, "test_fn", input);
    let wasmtime_out = run_wasmtime(wasm_bytes, "test_fn", input);

    assert_eq!(wasm3_out, wasmtime_out,
        "WasmParity FAILED: wasm3 vs wasmtime output divergence detected");
}

#[test]
fn wasm_parity_nan_canonicalization() {
    // Verify NaN bit pattern is identical across both runtimes after canonicalization
    let wasm_bytes = include_bytes!("fixtures/test_nan_plugin.wasm");
    let wasm3_out = run_wasm3(wasm_bytes, "nan_test", b"");
    let wasmtime_out = run_wasmtime_with_nan_canon(wasm_bytes, "nan_test", b"");
    assert_eq!(wasm3_out, wasmtime_out, "NaN canonicalization divergence");
}

#[test]
fn wasm_parity_latency_delta() {
    // latency delta must be ≤ 20 ms
    let delta = measure_call_latency_delta_ms();
    assert!(delta <= 20.0, "WasmParity latency delta {} ms exceeds 20 ms ceiling", delta);
}

#[test]
fn wasm_parity_memory_delta() {
    let wasm3_mem = measure_peak_heap_wasm3();
    let wasmtime_mem = measure_peak_heap_wasmtime();
    let delta_mb = (wasm3_mem as i64 - wasmtime_mem as i64).unsigned_abs() / (1024 * 1024);
    assert!(delta_mb <= 5, "WasmParity memory delta {} MB exceeds 5 MB ceiling", delta_mb);
}
```

**[PATCH Issue-07] XPC Transaction Journal — WAL Durability Before PENDING Write:**

> The previous spec wrote `XpcJournalEntry { status: PENDING }` to `hot_dag.db` without
> ensuring WAL durability. Since `wal_autocheckpoint = 1000` flushes only every 1000 pages,
> a SIGKILL during XPC crash could leave the PENDING record un-checkpointed, causing
> silent transaction loss (no user prompt, no `ComponentFault`).

**Fix:** The `XpcJournalEntry` is written using a **dedicated SQLite connection with
`PRAGMA synchronous = FULL`**, guaranteeing fsync before `tera_buf_release` dispatches
to the XPC Worker:

```rust
// hot_dag.db has a second connection for XPC journal — synchronous = FULL
pub async fn write_xpc_pending(
    journal_db: &SqliteConnection,  // synchronous = FULL connection
    tx_id: Uuid,
    payload_hash: [u8; 32],
) -> Result<()> {
    // This fsync ensures PENDING is durable before XPC dispatch
    sqlx::query!(
        "INSERT INTO xpc_journal (tx_id, status, payload_hash) VALUES ($1, 'PENDING', $2)",
        tx_id.to_string(),
        &payload_hash[..],
    )
    .execute(journal_db)  // synchronous=FULL — blocks until fsync completes
    .await?;
    
    // Only AFTER durable PENDING write → dispatch to XPC Worker
    dispatch_to_xpc_worker(tx_id).await
}

// Connection setup
pub fn open_xpc_journal_connection(path: &Path) -> Result<SqliteConnection> {
    let conn = SqliteConnectOptions::new()
        .filename(path)
        .journal_mode(SqliteJournalMode::Wal)
        .synchronous(SqliteSynchronous::Full)  // <-- key: fsync on every write
        .connect()
        .await?;
    Ok(conn)
}
```

**XPC Worker Crash Recovery (corrected):**

```rust
// With durable PENDING: recovery is reliable on all crash scenarios
PENDING   → durable in journal → abort + emit CoreSignal::ComponentFault
            → notify user: "Session interrupted. Please re-sign."
VERIFIED  → idempotent commit from journal (crash-safe; no user action)
COMMITTED → noop (already complete)
```

Retry policy: max 3 attempts, backoff 0 s → 2 s → 8 s. After 3rd failure:
emit `CoreSignal::ComponentFault { severity: Critical }` + `XpcPermanentFailure { support_id: Uuid }`.

**`.tapp` Bundle Format:**

```text
bundle.tapp/
├── logic.wasm          # WASM bytecode (stripped: no wasi-sockets, wasi:io, wasi:filesystem)
├── manifest.json       # publisher_public_key, egress_endpoints, permissions, version_hash (BLAKE3)
├── assets/             # static assets
└── signature.ed25519   # Ed25519 by Publisher Key (Merkle Registry)
```

**Launch Sequence:**

1. Admin installs `.tapp` from Marketplace. Signature verified against Publisher Key.
2. `manifest.json` validated: all required fields present; `egress_endpoints` declared.
3. Platform WASM runtime initialized (wasm3/iOS, wasmtime/others).
4. **[PATCH 06]** WasmParity gate must have passed CI for this `.tapp` version.
5. Sandbox launched: `PROT_READ`-only DAG access.

**Observability:**

- Signal: `CoreSignal::ComponentFault { component, severity }` on sandbox panic or XPC crash.
- Metric: `wasm_sandbox_crashes` (OBSERVE-01).

---

### F-08: Inter-`.tapp` IPC and Delegation Tokens

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-09: Media and File Transfer

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-10: AI / SLM Integration

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-11: Device Security

**Description:** Client-side security controls: screen capture prevention, Protected Clipboard Bridge, biometric screen lock, Remote Wipe, and cryptographic self-destruct.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

#### F-11a: Screen Capture Prevention

| Platform | API | Mechanism |
|---|---|---|
| 📱 iOS | `UIScreen.capturedDidChangeNotification` | Blur overlay on capture |
| 📱 Android | `FLAG_SECURE` in `Activity.onCreate()` | Kernel Compositor blocks capture |
| 💻 macOS | `CGDisplayStream` monitoring | Blur overlay within 1 frame |
| 🖥️ Windows | DXGI duplication detection | Blur overlay |
| 🖥️ Linux | Wayland compositor security hint | Platform best-effort |

#### F-11b: Protected Clipboard Bridge

All clipboard operations route through Rust Core's bridge. Direct OS clipboard API calls: **blocker** (SEC-03).

#### F-11c: Biometric Screen Lock

- All SQLite I/O blocked until biometric gate clears.
- PIN fallback: 6 digits. Transmitted via FFI Pointer — never through UI state buffer.
- Maximum PIN failures: 5. On 5th: Cryptographic Self-Destruct.

**[PATCH Issue-13] Dead Man Switch Deferral — Mandatory Audit Trail:**

> For regulated enterprise and Gov/Military customers, a Dead Man Switch deferral
> (due to active CallKit session) must be auditable. Without a `DeadManDeferralEntry`,
> an insider threat actor could initiate a call to indefinitely defer the Dead Man Switch
> with no auditable trace.

```rust
/// Written to tamper-proof Audit Log BEFORE deferral takes effect — not after.
pub struct DeadManDeferralEntry {
    device_id: DeviceId,
    timestamp_hlc: HlcTimestamp,
    reason: DeferralReason,          // CallKitSessionActive | AdminOverride
    server_counter_at_deferral: u64, // TPM Monotonic Counter from server
    device_counter_at_deferral: u64, // local TPM Monotonic Counter
    counter_delta: i64,              // server_counter - device_counter: shows max unsync window
    session_id: Option<CallKitSessionId>,
    ed25519_sig: Ed25519Signature,   // signed by DeviceIdentityKey
}

// Dead Man Switch deferral — audit BEFORE deferral, then defer
async fn defer_dead_man_switch(reason: DeferralReason, call_session: Option<CallKitSessionId>) {
    let entry = DeadManDeferralEntry {
        device_id: self.device_id.clone(),
        timestamp_hlc: HlcClock::now(),
        reason,
        server_counter_at_deferral: fetch_server_monotonic_counter().await,
        device_counter_at_deferral: tpm_read_counter(),
        counter_delta: server_counter - device_counter,
        session_id: call_session,
        ed25519_sig: secure_enclave_sign(&entry_bytes),
    };
    
    // Write to Ed25519-signed Audit Log BEFORE taking any deferral action
    audit_log_append(AuditEvent::DeadManSwitchDeferred(entry)).await?;
    
    // Deferral takes effect only after audit is durable
    apply_dead_man_switch_deferral().await;
}
```

**Constraint:** `counter_delta` in the `DeadManDeferralEntry` is visible to the CISO in the
Audit Log viewer, enabling determination of the maximum window during which the device was
unsynchronized with the server's monotonic counter.

#### F-11d: Remote Wipe

Trigger: `self.userID` in `removedMembers` of any MLS Commit. Non-interruptible sequence.

#### F-11e: Cryptographic Self-Destruct

- `Failed_PIN_Attempts` counter encrypted with `Device_Key`. Ceiling: 5.
- On 5th failure: Crypto-Shredding of all local DBs + `OIDC_ID_Token` → Factory Reset.

**State Machine:** → §5.6 (Device PIN Failure State Machine)

---

### F-12: Identity, Onboarding, and Recovery

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-13: Admin Console and Enterprise Controls

**Description:** Centralized management interface for workspace administrators.

**Supported Platforms (full access):** 💻 macOS, 🖥️ Windows, 🖥️ Linux, 🗄️ Bare-metal
**Supported Platforms (read-only):** 📱 iOS, 📱 Android, 📱 Huawei

**[PATCH Issue-14] Federation OPA Policy — Schema Version Exemption:**

> OPA Policy bundle distribution was incorrectly gated on schema version compatibility.
> A Branch cluster on schema version N-1 could not receive critical security policies
> (CRL updates, permission revocations, user offboarding) from HQ until it upgraded.
> In Gov/enterprise environments with gated schema upgrades, this could mean a revoked
> user remains in the OPA policy for weeks.

**Corrected Federation Endpoint Routing:**

| Endpoint | Schema Version Gate | Description |
|---|---|---|
| `/federation/data` | ✅ Enforced (±1 minor = read-only; ±1 major = SCHEMA_INCOMPATIBLE) | Data sync, message routing |
| `/federation/policy` | ❌ **Exempt** from schema version check | OPA policy bundles (CRL, revocation, permissions) |

Both endpoints require mTLS. Only `/federation/data` is version-gated.

```rust
// Federation router — policy channel is version-agnostic
async fn route_federation_request(req: FederationRequest) -> Result<Response> {
    match req.endpoint {
        FederationEndpoint::Policy => {
            // Always accept policy updates regardless of schema version
            verify_mtls_and_ca_signature(&req)?;
            apply_opa_policy_bundle(req.payload).await
        }
        FederationEndpoint::Data => {
            // Schema version check enforced for data sync
            verify_schema_compatibility(req.sender_schema_version)?;
            route_data_sync(req).await
        }
    }
}
```

**Admin Console Feature Set:**

| Feature | Description | Access Level |
|---|---|---|
| Device enrollment management | Issue / revoke mTLS certificates | Admin: full |
| User offboarding (SCIM 2.0) | Auto-remove from MLS groups on HR event | Server: auto |
| OPA Policy management | Define and push ABAC policies to devices | Admin: full |
| Remote Wipe | Initiate `removedMembers` MLS Commit | Admin: full |
| Audit Log viewer | Ed25519-signed tamper-proof entries (incl. DeadManDeferral) | Admin: read-only |
| License management | View / renew License JWT; seat count | Admin: full |
| Federation management | Invite / revoke federated clusters; policy channel exempt from schema gate | Admin: full |

---

### F-14: Adaptive Network and Protocol Management

**Description:** Automatic network protocol selection (ALPN), adaptive QUIC probe learning, and graceful fallback.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**ALPN Negotiation Sequence (total < 50 ms):**

```text
Step 1: QUIC / HTTP/3 over UDP:443
        ACK within 50 ms → ONLINE_QUIC (0-RTT, ~30 ms RTT)
        No ACK / firewall DROP → Step 2

Step 2: gRPC / HTTP/2 over TCP:443
        TLS handshake success → ONLINE_GRPC (~80 ms RTT)
        DPI blocks binary framing → Step 3

Step 3: WebSocket Secure over TCP:443
        WS Upgrade success → ONLINE_WSS (~120 ms RTT)
        All three fail → MESH_MODE
```

**[PATCH Issue-03] Adaptive QUIC Probe Learning — Race Fix:**

> **CRITICAL BUG (v0.4.0):** The previous `on_probe_failure` implementation incremented
> `probe_fail_count` for ALL parallel probes that did not win the `tokio::select!` race,
> including gRPC when QUIC succeeded first. Over 3 such races on the same `NetworkProfile`,
> `strict_compliance` was permanently set to true on networks where QUIC works correctly,
> silently adding 50 ms to every connection.

**Corrected implementation — `probe_fail_count` increments only for the protocol that
did not win, and resets to 0 when QUIC wins:**

```rust
/// Corrected adaptive ALPN negotiation — only the LOSER increments fail count.
/// The WINNER resets probe_fail_count to 0 for its protocol.
pub async fn negotiate_alpn_adaptive(
    cert_fp: &[u8],
    ssid_hash: &[u8],
    db: &SqliteConn,
) -> AlpnResult {
    let mut profile = db.get_or_create_network_profile(
        &blake3::hash(&[cert_fp, ssid_hash].concat())
    );

    // Respect established strict_compliance
    if profile.strict_compliance {
        return try_grpc_direct(cert_fp).await;
    }

    // Parallel race — winner determined by first to resolve
    let result = tokio::select! {
        r = try_quic(cert_fp) => Either::Left(r),
        r = try_grpc(cert_fp) => Either::Right(r),
    };

    match result {
        Either::Left(Ok(quic_conn)) => {
            // QUIC won: reset its fail count (no penalty for parallel gRPC attempt)
            profile.quic_probe_fail_count = 0;
            db.save_network_profile(&profile);
            AlpnResult::Quic(quic_conn)
        }
        Either::Left(Err(_)) => {
            // QUIC failed: increment only QUIC's fail count
            profile.quic_probe_fail_count += 1;
            if profile.quic_probe_fail_count >= 3 {
                profile.strict_compliance = true;
                emit_admin_notification("Auto-switched to TCP on this network.");
            }
            db.save_network_profile(&profile);
            // Fall through to gRPC
            try_grpc_or_wss(cert_fp).await
        }
        Either::Right(Ok(grpc_conn)) => {
            // gRPC won race (QUIC timed out): only QUIC fails, gRPC has no penalty
            profile.quic_probe_fail_count += 1;
            db.save_network_profile(&profile);
            AlpnResult::Grpc(grpc_conn)
        }
        Either::Right(Err(_)) => {
            profile.quic_probe_fail_count += 1;
            db.save_network_profile(&profile);
            try_wss_or_mesh(cert_fp).await
        }
    }
}

fn on_network_change(new_cert_fp: &[u8], ssid_hash: &[u8], db: &SqliteConn) {
    let network_id = blake3::hash(&[new_cert_fp, ssid_hash].concat());
    // Reset ALL fail counts on network change
    db.reset_network_profile(network_id.as_bytes());
}
```

**Observability:**

- Signal: `CoreSignal::TierChanged { new_tier, reason }` on every ALPN change.
- Metric: `alpn_fallback_count` (OBSERVE-01).
- Admin notification: auto-emitted when probe learning triggers Strict Compliance.

---

### F-15: Crash-Safe Memory and WAL Management

**Description:** Platform-specific memory protection and crash-safe WAL flush protocols.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**[PATCH Issue-10] Linux AppArmor/SELinux — Full Postinstall Specification:**

> **STATUS CHANGE: "Not implemented" → Required for Sprint 1 Linux deployment.**
> Without the MAC profile, startup crashes on `memfd_create` and `ipc_lock` on all
> enforcing systems (Ubuntu 22.04+ AppArmor enforcing by default; RHEL 8+ SELinux enforcing).

**AppArmor Profile (`/etc/apparmor.d/usr.bin.terachat`):**

```apparmor
#include <tunables/global>

/usr/bin/terachat {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  # Core binary
  /usr/bin/terachat mr,
  /usr/lib/terachat/** mr,
  /usr/share/terachat/** r,

  # Data directories
  owner @{HOME}/.local/share/terachat/** rwkl,
  owner @{HOME}/.config/terachat/** rwkl,
  /tmp/terachat-* rwkl,

  # memfd_create for SharedArrayBuffer (Tauri IPC Data Plane)
  capability sys_admin,       # NOT needed — memfd_create uses memfd capability
  @{PROC}/*/fd/ r,
  @{PROC}/*/mem r,
  # memfd: allowed via kernel path — no explicit AppArmor rule needed in 5.x+

  # ipc_lock for mlock equivalent key protection
  capability ipc_lock,

  # BLE socket access
  /sys/class/bluetooth/ r,
  /sys/bus/usb/devices/ r,
  network bluetooth,
  network inet stream,
  network inet6 stream,
  network inet dgram,

  # ptrace for self-debugging (crash reporter)
  ptrace peer=(comm=terachat),

  # Deny dangerous capabilities
  deny capability net_admin,
  deny capability sys_rawio,
  deny @{PROC}/sysrq-trigger w,
}

/usr/bin/terachat-daemon {
  #include <abstractions/base>
  /usr/bin/terachat-daemon mr,
  owner @{HOME}/.local/share/terachat/** rwkl,
  capability ipc_lock,
  network inet stream,
  network inet6 stream,
  network inet dgram,
  network bluetooth,
}
```

**SELinux Policy Module (`/usr/share/terachat/terachat.te`):**

```te
module terachat 1.0;

require {
    type user_home_t;
    type tmp_t;
    type bluetooth_t;
    type init_t;
    class file { read write create unlink rename lock };
    class sock_file { read write create };
    class capability { ipc_lock };
    class process { execmem };  # required for wasmtime JIT
}

# TeraChat domain
type terachat_t;
type terachat_exec_t;
init_daemon_domain(terachat_t, terachat_exec_t)

# File access
allow terachat_t user_home_t:file { read write create unlink rename lock };
allow terachat_t tmp_t:file { read write create unlink };

# ipc_lock for key material protection
allow terachat_t self:capability { ipc_lock };

# wasmtime JIT requires execmem (mapped writable+executable pages)
allow terachat_t self:process { execmem };

# BLE access
allow terachat_t bluetooth_t:sock_file { read write };
```

**Pre-compiled `.pp` bundles shipped for:**

- RHEL 8 / CentOS Stream 8 (`terachat-rhel8.pp`)
- RHEL 9 / CentOS Stream 9 / AlmaLinux 9 (`terachat-rhel9.pp`)
- Fedora 38+ (`terachat-fedora38.pp`)

**Postinstall Script (`/usr/share/terachat/postinstall.sh`):**

```bash
#!/bin/bash
set -euo pipefail
LOG=/var/log/terachat-install.log

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

# AppArmor
if command -v apparmor_parser &>/dev/null; then
    log "Loading AppArmor profiles..."
    apparmor_parser -r -W /etc/apparmor.d/usr.bin.terachat 2>>"$LOG" || \
        log "WARNING: AppArmor profile load failed — manual load required"
    apparmor_parser -r -W /etc/apparmor.d/terachat-daemon 2>>"$LOG" || \
        log "WARNING: AppArmor daemon profile load failed"
fi

# SELinux
if command -v semodule &>/dev/null; then
    # Detect RHEL/Fedora version for correct .pp selection
    if grep -q "release 9" /etc/redhat-release 2>/dev/null; then
        PP=/usr/share/terachat/terachat-rhel9.pp
    elif grep -q "release 8" /etc/redhat-release 2>/dev/null; then
        PP=/usr/share/terachat/terachat-rhel8.pp
    else
        PP=/usr/share/terachat/terachat-fedora38.pp
    fi
    log "Loading SELinux module: $PP"
    semodule -i "$PP" 2>>"$LOG" || \
        log "WARNING: SELinux module load failed — manual installation required: semodule -i $PP"
fi

# Self-test: verify permissions are correct before starting daemon
log "Running permission self-test..."
if /usr/bin/terachat --check-permissions; then
    log "Permission self-test PASSED"
else
    log "WARNING: Permission self-test FAILED — check $LOG for details"
    echo "NOTICE: TeraChat installed but MAC profile may not be active."
    echo "        Run: /usr/bin/terachat --check-permissions"
    echo "        See: $LOG"
    # Do NOT abort installation — warn only
fi
```

**`terachat --check-permissions` Binary Subcommand:**

```rust
// Binary subcommand — formal exit code 0/1 with human-readable output
pub fn check_permissions() -> ExitCode {
    let mut all_ok = true;

    // Test memfd_create
    match nix::sys::memfd::memfd_create(c"terachat_test", MemFdCreateFlag::MFD_CLOEXEC) {
        Ok(fd) => { println!("✅ memfd_create: OK"); nix::unistd::close(fd).ok(); }
        Err(e) => { eprintln!("❌ memfd_create: FAILED ({e}) — AppArmor/SELinux may be blocking"); all_ok = false; }
    }

    // Test ipc_lock (mlock on small buffer)
    match try_mlock_test_page() {
        Ok(_) => println!("✅ ipc_lock (mlock): OK"),
        Err(e) => { eprintln!("❌ ipc_lock: FAILED ({e}) — capability ipc_lock may be denied"); all_ok = false; }
    }

    // Test BLE socket
    match test_bluetooth_socket() {
        Ok(_) => println!("✅ BLE socket: OK"),
        Err(e) => { eprintln!("⚠️  BLE socket: UNAVAILABLE ({e}) — Mesh mode will not work"); }
        // BLE unavailable is a warning, not a failure — non-Mesh deployments are valid
    }

    if all_ok {
        println!("\nAll required permissions available. TeraChat is ready.");
        ExitCode::SUCCESS
    } else {
        eprintln!("\nSome permissions are missing. See /var/log/terachat-install.log");
        ExitCode::FAILURE
    }
}
```

**Linux Multi-Init Daemon Support (postinstall):**

```bash
if command -v systemctl &>/dev/null && systemctl --version &>/dev/null 2>&1; then
    systemctl enable --now terachat-daemon.service
elif command -v rc-service &>/dev/null; then
    rc-update add terachat-daemon default && rc-service terachat-daemon start
elif command -v runit &>/dev/null; then
    ln -sf /etc/sv/terachat-daemon /var/service/
else
    install -m644 /usr/share/applications/terachat-daemon.desktop \
        ~/.config/autostart/terachat-daemon.desktop
fi
```

**iOS / Android Crash-Safe Checkpoint:**

```swift
NotificationCenter.default.addObserver(
    forName: UIApplication.willTerminateNotification,
    using: { _ in tera_core_flush_io() }  // FFI; ≤ 50 ms
)
```

**Constraints:**

- `tera_core_flush_io()` must complete in ≤ 50 ms on mobile.
- Desktop: 35 s total (30 s checkpoint + 5 s systemd margin). Exit unconditionally after 30 s.
- `PRAGMA wal_autocheckpoint = 1000` enforced on all databases at connection open.
- Linux deployment on AppArmor/SELinux enforcing systems requires the postinstall script.

---

### INFRA-01 through INFRA-06, OBSERVE-01/02

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### CICD-01: CI/CD Pipeline Requirements

> All gates below must pass before merge to `main`. Any failure = **BLOCKER**.

**Security Gates:**

| Gate | Command | Blocker |
|---|---|---|
| FFI-01: No raw pointer in `pub extern C` | `cargo clippy -- -D tera_ffi_raw_pointer` | Yes |
| KEY-02: ZeroizeOnDrop verification | `cargo miri test --test zeroize_verification` | Yes |
| Dependency audit (RUSTSEC) | `cargo audit --deny warnings` | Yes |
| Trivy container scan (CRITICAL CVE) | `trivy image --exit-code 1 --severity CRITICAL` | Yes |
| Secret scan (GitLeaks) | `gitleaks detect --source . --exit-code 1` | Yes |
| **[PATCH 12] GC Finalizer release count = 0** | `cargo test -- --test-output immediate ffi_gc_finalizer` | **Yes** |

**[PATCH Issue-06, Issue-01] WasmParity + Dart FFI Correctness Gates — Sprint 1 Blockers:**

| Gate | Command | Blocker | Sprint |
|---|---|---|---|
| WasmParity (integer vectors, latency, memory) | `cargo test --test wasm_parity -- --timeout 60` | **Yes** | **Sprint 1** |
| WasmParity NaN canonicalization | `cargo test --test wasm_parity_nan -- --timeout 60` | **Yes** | **Sprint 1** |
| Dart FFI GC finalizer count = 0 | `flutter test --tags ffi_gc_audit` | **Yes** | **Sprint 1** |
| Dart FFI `useInTransaction` lint (tera_require_secure_buffer) | `dart analyze --fatal-infos` | **Yes** | **Sprint 1** |

**Correctness Gates:**

| Gate | Command | Blocker |
|---|---|---|
| Unit tests (all platforms) | `cargo nextest run --all-features` | Yes |
| WasmParity CI gate (wasm3 vs wasmtime, delta ≤ 20 ms, memory ≤ 5 MB) | see above | **Yes — Sprint 1** |
| Inbound dedup contract (CRDT) | `cargo test --test crdt_dedup_contract` | Yes |
| **[PATCH 03] ALPN probe race regression** | `cargo test --test alpn_probe_race` | **Yes** |
| **[PATCH 08] Shadow DB TOCTOU** | `cargo test --test shadow_db_concurrent` | **Yes** |
| MLS epoch rotation SLA (≤ 1 s for 100 members) | `cargo bench --bench mls_epoch_rotation` | No (regression tracked) |

**Build & Signing Gates:**

| Gate | Command | Blocker | Platform |
|---|---|---|---|
| Reproducible build verification | `ops/verify-reproducible-build.sh` | Yes | All |
| SBOM generation and signing | `ops/generate-sbom.sh && cosign sign-blob …` | Yes | All |
| **[PATCH 10] Linux AppArmor self-test** | `/usr/bin/terachat --check-permissions` | **Yes** | Linux |
| Windows EV Code Signing | `signtool verify /pa terachat-setup.exe` | Yes | Windows |
| Linux GPG signature on .deb/.rpm | `dpkg-sig --verify terachat_*.deb` | Yes | Linux |

---

### PLATFORM-17: Dart FFI Memory Contract

> **Supersedes PLATFORM-14.** Mandatory — violations = CI fail (blocker).
> Applies to: Android, Huawei (Dart FFI path).
> **[PATCH Issue-01] Updated for double-release race fix.**

**[PATCH Issue-01] Four Mandatory Rules (Updated):**

- **Rule 1:** Every `TeraSecureBuffer` MUST be wrapped by `useInTransaction()`. Direct `.toPointer()` outside wrapper → CI lint error (blocker).
- **Rule 2:** Rust Token Registry does NOT auto-expire/zeroize. On TTL timeout → emit `IpcSignal::TransactionTimeout`.
- **Rule 3:** GC Finalizer is safety net only. **GC release → CI BLOCKER metric (not just warning).** Any `ffi.gc_finalizer_release.count > 0` in CI test run fails the build.
- **Rule 4:** Explicit `releaseNow()` is primary release path. `useInTransaction()` calls it in `finally` automatically.
- **Rule 5 [NEW]:** The Rust Token Registry uses a **monotonic generation counter** per token. Stale tokens (from GC finalizer double-release) are rejected by comparing the token's embedded generation with the registry's current generation. Double-release is a no-op after the first release.

**[PATCH Issue-01] Dart FFI `TeraSecureBuffer` Wrapper — Race-Safe:**

```dart
class TeraSecureBuffer {
  final int _token;
  // PATCHED: Use Dart Isolate-compatible atomic flag
  // Dart isolates are single-threaded, but finalizers run asynchronously.
  // _released is accessed only from the main isolate; finalize() runs in
  // a separate finalizer isolate. We use a Completer to synchronize.
  bool _released = false;
  final _releaseLock = Mutex();  // package:mutex for isolate-safe locking

  static Future<TeraSecureBuffer> acquire(int operationId) async {
    final token = await _teraFfi.tera_buf_acquire(operationId);
    if (token == 0) throw const TeraBufferError('acquire failed — token=0');
    return TeraSecureBuffer._(token);
  }

  /// Primary release path — must be called explicitly.
  Future<void> releaseNow() async {
    await _releaseLock.acquire();
    try {
      if (_released) return;  // idempotent: second call is no-op
      _teraFfi.tera_buf_release(_token);  // Rust registry checks generation counter
      _released = true;
    } finally {
      _releaseLock.release();
    }
  }

  /// Safety net ONLY — should never be the primary release path.
  /// GC finalizer fires in a separate Dart isolate: acquires lock before checking.
  @override
  void finalize() {
    if (!_released) {
      // CI BLOCKER: increment metric — this path must not be reached in production
      MetricsCollector.increment('ffi.gc_finalizer_release.count');
      _logger.error(
        'BLOCKER: TeraSecureBuffer token=$_token released by GC finalizer. '
        'Missing explicit releaseNow() call. This is a CI blocker.'
      );
      // Still call release to prevent memory leak, but flag the code defect
      _teraFfi.tera_buf_release(_token);  // Rust generation counter prevents double-free
      _released = true;
    }
  }
}
```

**[PATCH Issue-01] Rust Token Registry — Monotonic Generation Counter:**

```rust
// Token registry with generation counter — prevents double-release use-after-free
pub struct TokenRegistry {
    // token_id → (generation, ZeroizeOnDropBuffer)
    tokens: HashMap<u64, (u32, ZeroizeOnDropBuffer)>,
    next_generation: AtomicU32,
}

impl TokenRegistry {
    pub fn acquire(&mut self, buffer: ZeroizeOnDropBuffer) -> u64 {
        let generation = self.next_generation.fetch_add(1, Ordering::SeqCst);
        // Encode generation in high 16 bits of token, sequence in low 48 bits
        let token = encode_token(self.next_seq(), generation);
        self.tokens.insert(token, (generation, buffer));
        token
    }

    pub fn release(&mut self, token: u64) -> Result<(), TokenError> {
        let expected_gen = extract_generation(token);
        match self.tokens.get(&token) {
            None => {
                // Token already released — stale token from GC finalizer double-release
                // No-op: generation counter prevents use-after-free
                Err(TokenError::StaleToken { token, expected_gen })
            }
            Some((stored_gen, _)) if *stored_gen != expected_gen => {
                // Generation mismatch — reject stale reference
                Err(TokenError::GenerationMismatch { token, expected_gen, stored_gen: *stored_gen })
            }
            Some(_) => {
                let (_, buffer) = self.tokens.remove(&token).unwrap();
                drop(buffer);  // ZeroizeOnDrop fires here
                Ok(())
            }
        }
    }
}
```

**CI Lint (Rust side — FFI-01 enforcement) and Dart lint rules remain unchanged from v0.4.0.**

**[PATCH Issue-01] Error Handling in `Isolate.addErrorListener`:**

```dart
// Register error listener to catch finalizer-time errors
void initializeTeraFfi() {
  Isolate.current.addErrorListener(RawReceivePort((pair) {
    final List errorAndStackTrace = pair as List;
    final error = errorAndStackTrace.first;
    if (error.toString().contains('TeraSecureBuffer')) {
      // Escalate to crash reporter — FFI contract violation
      CrashReporter.report('TeraSecureBuffer finalizer error: $error');
    }
  }).sendPort);
}
```

---

### PLATFORM-18: ONNX Model Integrity

*(No patches in this version. Content unchanged from v0.4.0.)*

### PLATFORM-19: TeraEdge Client Integration

*(No patches in this version. Content unchanged from v0.4.0.)*

---

## §5 — STATE MACHINE

### §5.1 Network Tier State Machine

**Applies to:** F-05, F-06, F-14

| State | Description |
|---|---|
| `ONLINE_QUIC` | QUIC/HTTP3 over UDP:443 active. ~30 ms RTT. |
| `ONLINE_GRPC` | gRPC/HTTP2 over TCP:443 active. ~80 ms RTT. |
| `ONLINE_WSS` | WebSocket Secure over TCP:443 active. ~120 ms RTT. |
| `MESH_MODE` | All ALPN paths unavailable. BLE/Wi-Fi Direct active. |
| `STRICT_COMPLIANCE` | Admin override: skip QUIC; connect directly via gRPC TCP. |

**[PATCH Issue-03] Transition Table (corrected probe-fail logic):**

| From | To | Trigger |
|---|---|---|
| Any | `ONLINE_QUIC` | QUIC ACK within 50 ms — resets `quic_probe_fail_count = 0` |
| `ONLINE_QUIC` | `ONLINE_GRPC` | QUIC probe timeout; UDP firewall block — increments only `quic_probe_fail_count` |
| `ONLINE_GRPC` | `ONLINE_WSS` | gRPC DPI block |
| `ONLINE_WSS` | `MESH_MODE` | WSS rejected |
| `MESH_MODE` | `ONLINE_QUIC` | Internet restored |
| Any | `STRICT_COMPLIANCE` | Admin push via OPA; ≥ 3 QUIC-specific probe failures on same `NetworkProfile` |
| `STRICT_COMPLIANCE` | `ONLINE_GRPC` | Direct TCP connect |

**Critical:** `probe_fail_count` is per-protocol (only `quic_probe_fail_count` tracked). gRPC
losing the race to QUIC does NOT increment any fail count. See §4 F-14 for implementation.

### §5.2 Mesh Role State Machine

**Applies to:** F-05 — unchanged from v0.4.0.

**[PATCH Issue-05] New State: `CAUSAL_FREEZE`**

| State | Eligible Platforms | Conditions |
|---|---|---|
| `LeafNode` | All | Default for iOS |
| `RelayNode` | Android, Huawei | RAM ≥ 3 GB && battery ≥ 40% |
| `SuperNode` | macOS, Windows, Linux | AC power source |
| `TacticalRelay` | iOS only (EMDP) | No Desktop; Internet unavailable; ≥ 2 iOS; battery > 20% |
| `CAUSAL_FREEZE` | iOS (EMDP) | EMDP active; sudden Desktop loss before escrow transmitted |

`CAUSAL_FREEZE` → `TacticalRelay`: Desktop reconnects and transmits fresh EmdpKeyEscrow.

### §5.3 WASM Sandbox Lifecycle State Machine

Enterprise Registry Access Control:

- .tapp không tự động available cho end users
- IT Admin phải approve từng .tapp trong Admin Console
- Approval push OPA Policy update đến devices trong workspace
- End user thấy .tapp sau khi IT Admin approve — không thể tự cài
- IT Admin có thể revoke bất kỳ lúc nào; effective ≤ 60s

IT Admin Approval Flow:

  1. Admin Console: Tab "Plugin Registry" → Browse available .tapp
  2. Admin xem Security Report: egress domains, permissions, scan results
  3. Admin approve cho workspace (all users hoặc specific groups)
  4. OPA Policy push: {plugin_id: "APPROVED", target_groups: [...]}
  5. Devices nhận policy → .tapp launcher trong app

**WasmParity CI Gate (mandatory before Marketplace listing):**

- Same test vector executed on `wasm3` (iOS reference) and `wasmtime` (Desktop optimized).
- Output: semantically identical. Latency delta: ≤ 20 ms acceptable.
- Memory delta: ≤ 5 MB acceptable.
- CI failure: **blocker for Marketplace launch** (FI-03).

**Mesh Mode Behavior:**

```text
All WASM sandbox processes: terminate immediately
Transient state: snapshot saved to sled LSM-Tree (per-DID namespace)
Network proxy: returns NETWORK_MESH_RESTRICTED for all outbound requests
On Internet restore: sled snapshot restored in < 50 ms (single UI blink)
```

**macOS XPC Worker Crash Recovery:**

```rust
// XpcJournalEntry states persisted in hot_dag.db:
PENDING   → abort + emit CoreSignal::ComponentFault
            → notify user: "Session interrupted. Please re-sign."
VERIFIED  → idempotent commit from journal (crash-safe; no user action needed)
COMMITTED → noop (already complete)
```

Retry policy: max 3 attempts, backoff 0 s → 2 s → 8 s. After 3rd failure: emit `CoreSignal::ComponentFault` with severity `Critical` + `XpcPermanentFailure { support_id: Uuid }`.

**State Machine:** → §5.3 (WASM Sandbox Lifecycle State Machine), §5.4 (XPC Transaction State Machine)

**Transient State Storage (`sled` LSM-Tree):**

- Crate: `sled` ≥ 0.34 (pure Rust; no C FFI; ~2 MB compiled; < 2 MB RAM idle). **Version must be pinned in `Cargo.toml`** (FI-04).
- Rationale for `sled` over RocksDB: RocksDB compiled size exceeds 50 MB WASM heap budget on mobile.
- API: `terachat.storage.persist_keyval(key, value)` → debounce 500 ms → AES-256-GCM encrypt → write.
- Recovery: `terachat.storage.get_transient_state()` → < 50 ms restore.
- Mesh Mode: disabled. RAM/CPU reserved for BLE routing.

**Dependencies:**

- REF: TERA-CORE §4.1 — `ffi/token_protocol.rs`, `ffi/ipc_bridge.rs`
- REF: TERA-CORE §4.4 — Component Fault Isolation, `catch_unwind` at WASM execution entry
- REF: TERA-CORE §3.2 — Platform WASM runtime selection matrix
- REF: TERA-CORE §4.3 — FFI Token Protocol; no raw pointer between Core and sandbox

**Data Interaction:**

- Reads (via Host Proxy only): approved `cold_state.db` namespaces; sanitized external API responses.
- Writes: `sled` LSM-Tree transient state (per-DID, AES-256-GCM). Forbidden: direct writes to `hot_dag.db` or `cold_state.db`.
**Constraints:**

- WASM heap: ≤ 50 MB mobile / ≤ 64 MB desktop. OOM kills sandbox only; Core is unaffected.
- CPU: ≤ 10% sustained. Spike allowed; not > 500 ms. Circuit Breaker: latency > 1,500 ms or CPU spike > 30% → SUSPEND.
- Rate limit: Token Bucket 50 req/s per `.tapp`. Continuous exhaustion → SUSPEND + 60 s cool-down.
- Egress: HTTPS, HTTP/2, Secure WebSocket to declared `egress_endpoints` only. Raw TCP/UDP: forbidden.
- iOS: no dynamic WASM loading. `wasm3` interpreter or AOT-compiled `.dylib` only (PLT-01).
- Huawei: AOT-compiled `.waot` bundles required for AppGallery. No dynamic download (PLT-07).

**Security Notes:**

- SEC-04: WASM sandbox `PROT_READ`-only access to DAG shared memory. Write attempts trigger `SIGSEGV` caught by `catch_unwind`. No exceptions.
- ATD-06: WASM plugins have zero knowledge of MLS key material. They receive only sanitized `Vec<ASTNode>` response objects.
- ATD-08: `DelegationToken` (F-08) does not grant `.tapp` access to raw `cold_state.db`. It grants access to a defined OPA-enforced namespace only.
- Signal: `CoreSignal::XpcHealthDegraded { crash_count, window_secs }` when XPC crash rate exceeds threshold.
- Audit: all OPA policy checks for egress requests.

**Failure Handling:** → §10.4 (Runtime Failure)

- WASM sandbox panic: `catch_unwind` at entry boundary. Emit `CoreSignal::ComponentFault`. Restart after 1 s.
- Heap exhaustion: OOM kills sandbox. Attempt transient state save before kill. Core unaffected.
- Rate limit exhausted: SUSPEND `.tapp`; return `ERR_RATE_LIMIT_EXCEEDED`; resume after 60 s.
- XPC Worker crash (macOS): recover from `XpcJournalEntry` state. Max 3 retries then `XpcPermanentFailure`.
**Description:** Allow two `.tapp` instances to share data with explicit user consent, mediated by Rust Core as Honest Broker. No direct `.tapp`-to-`.tapp` communication channel exists at any layer.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**Mesh Mode behavior:** All Delegation Tokens suspended. Return `ERR_MESH_MODE_DELEGATION_SUSPENDED` for all inter-`.tapp` share attempts.

**User Flow:**

1. `.tapp` A calls `terachat.ipc.share(target_did: DID, payload: Bytes)`.
2. Rust Core checks if a valid, unexpired `DelegationToken` exists for the pair (A → B).
3. **No existing token:** Core displays consent modal: "Allow [`.tapp` A name] to share with [`.tapp` B name]?"
4. User approves: Core issues `DelegationToken` (TTL 30 days; signed by `DeviceIdentityKey`).
5. **Token exists:** auto-grant without prompt.
6. **Enterprise MDM path:** Admin pushes Global Trust Policy. Named `.tapp` pairs set to pre-approved.
**Delegation Token Structure:**
```rust
pub struct DelegationToken {
    source_did:  DID,
    target_did:  DID,
    granted_by:  DeviceId,             // signing device
    permissions: Vec<Permission>,      // read | write | stream
    expires_at:  u64,                  // Unix timestamp
    signature:   Ed25519Signature,     // signed by DeviceIdentityKey in SEP
}
```
**Dependencies:**
- REF: TERA-CORE §4.2 — `UICommand`, `CoreSignal` for IPC mediation
- REF: TERA-CORE §4.3 — Token Protocol; no raw pointer transfer between sandboxes
- REF: TERA-CORE §3.2 — OPA Policy Engine enforces all IPC requests at gateway
**Data Interaction:**
- Reads: `DelegationToken` from `hot_dag.db` KV store.
- Writes: new `DelegationToken` to `hot_dag.db` on user approval.
**Constraints:**
- Maximum auto-grant TTL: 30 days. Longer TTLs require explicit Admin MDM policy.
- Revocation: Admin revokes via Admin Console. Propagates via OPA policy push. Effective within next policy sync (≤ 60 s online).
- Token is signed by `DeviceIdentityKey`. Tampered tokens rejected at Core before any data transfer.
**Failure Handling:** → §10.4 (Runtime Failure)
- Target `.tapp` suspended or terminated: queue payload. Deliver on `.tapp` resume.
- Token expired: return `ERR_DELEGATION_TOKEN_EXPIRED`; prompt user to re-authorize.
- OPA policy change revokes token mid-session: return `ERR_TOKEN_REVOKED`; prompt user.
---
### F-09: Media and File Transfer
**Description:** Send encrypted media files (images, video, documents) via chunked, content-addressable, deduplicated upload. Server stores only ciphertext keyed by `cas_hash`. Receiver downloads on demand via Zero-Byte Stub.
**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux
**User Flow (Send — via INFRA-02 Blob Storage Client):**
1. User selects file. UI sends `UICommand::SendMedia { file_bytes, recipient_did }`.
2. Core: `cas_hash = BLAKE3(file_bytes)`. HEAD request to TeraRelay: `cas_hash` exists? (deduplication — saves 40–60% storage for shared enterprise files).
3. If not exists: chunk file into 2 MB segments.
   - Per chunk: `ChunkKey_i = HKDF(Epoch_Key, "chunk" || cas_hash || i)`.
   - `ciphertext_i = AES-256-GCM(ChunkKey_i, chunk_i, nonce_i)`.
   - `ZeroizeOnDrop` on `ChunkKey_i` and `chunk_i` plaintext after each chunk.
4. Request presigned URLs from TeraRelay (`PUT /v1/presign`). TTL 15 min per URL.
5. Upload chunks (max 3 concurrent) to presigned URLs.
6. Create `CRDT_Event { content_type: MediaStub, payload: ZeroByteStub }` (< 5 KB stub).
7. Append `CRDT_Event` to `hot_dag.db` → broadcast via E2EE channel.
**User Flow (Receive — On-Demand Streaming):**
1. Receiver's UI renders Zero-Byte Stub immediately (BlurHash preview from encrypted thumbnail).
2. User taps to open. Core requests presigned download URLs from TeraRelay. TTL 5 min.
3. Per chunk: download → `ChunkKey_i = HKDF(Epoch_Key, "chunk" || cas_hash || i)` → AES-256-GCM decrypt → `tera_buf_acquire` → write to `RingBuffer_2MB`.
4. `CoreSignal::StateChanged` → UI renders chunk. `ZeroizeOnDrop` on `ChunkKey_i` and plaintext after render.
5. After all chunks: `CoreSignal::MediaComplete { cas_hash }`.
**iOS Background Transfer:**
- Pre-signed URL (TTL 15 min, HMAC-SHA256 bound to device) delegated to `NSURLSession` Background Transfer Service.
- On download complete: iOS wakes app in 30 s window. Core `mmap`-reads and decrypts into VFS.
- `ShadowMigrationLock` prevents race with concurrent DB migration.
**Mesh Mode:** Multi-hop file transfer suspended. P2P Wi-Fi Direct (< 20 m) available. UI: "Files can only be sent when devices are nearby."
**Dependencies:**
- REF: TERA-CORE §5.3 — `ChunkKey` lifecycle, AES-256-GCM chunk encryption, nonce uniqueness
- REF: TERA-CORE §9.5 — MinIO Blind Storage, CAS path (`cas_hash`), Zero-Byte Stub format
- REF: TERA-CORE §7.1 — `CRDT_Event` with `content_type: MediaRef`
- REF: TERA-CORE §8.1 — Outbound message flow (media stub is a CRDT_Event)
- REF: TERA-FEAT §INFRA-02 — Blob Storage Client protocol (presigned URL mechanism)
**Data Interaction:**
- Writes: encrypted chunks to MinIO via presigned URL; `CRDT_Event` stub to `hot_dag.db`.
- Reads: `cas_hash` dedup lookup; encrypted chunks on demand; `ChunkKey` ephemeral in RAM.
**Constraints:**
- Maximum single file: 10 GB (chunked streaming; no full-file in RAM at any point).
- `ChunkKey` must `ZeroizeOnDrop` immediately after each chunk is processed.
- Deduplication uses Salted MLE: `BLAKE3(ciphertext + Channel_Key)`. Server learns nothing from dedup.
- Presigned URL TTL: 15 min (upload), 5 min (download). Expired: request new URL.
- Max concurrent chunk uploads: 3 (avoid saturating mobile bandwidth).
- TeraRelay does not store presigned URLs — stateless HMAC-signed generation.
**Failure Handling:** → §10.1 (Network), §10.2 (Storage)
- Upload interrupted: resume from last successfully uploaded chunk (`Hydration_Checkpoint` in `hot_dag.db`).
- Upload chunk fails: retry max 3 times (1s, 2s, 4s backoff). After 3: `MEDIA_UPLOAD_FAILED`, notify UI.
- Presigned URL expired mid-upload: request new URL for pending chunk. Already-uploaded chunks preserved.
- Decryption failure on receive: display "File could not be decrypted"; log to TeraDiag.
- MinIO node failure: EC+4 auto-recovers. Single-node loss does not affect availability.
### F-10: AI / SLM Integration

**Description:** Local Small Language Model (SLM) inference and cloud LLM routing for `.tapp` plugins. PII is redacted before any data leaves the device. Inference is isolated in a separate process (crash-safe from Rust Core). All ONNX model loads must pass `OnnxModelLoader.load_verified()` (PLATFORM-18).
**Supported Platforms:** 📱 iOS (CoreML), 📱 Android (ONNX), 📱 Huawei (HiAI), 💻 macOS (ONNX/CoreML), 🖥️ Windows (ONNX), 🖥️ Linux (ONNX)
**Mesh Mode behavior:** AI fully disabled. Return `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` for all inference requests.
**Inference Backend Priority (enforced by `resolve_inference_backend()`):**
1. TeraEdge Desktop on LAN (mDNS `_terachat-edge._tcp.local`; latency < 50 ms; load < 80%) → `InferenceBackend::RemoteDesktop`.
2. Local model if RAM sufficient and battery > 30% → `InferenceBackend::Local`.
3. VPS Enclave (cloud, requires Internet) → `InferenceBackend::VpsEnclave`.
4. Downgrade model tier (e.g., Base → Tiny) and retry → lower tier local.
5. All unavailable → `InferenceBackend::Unavailable`.
**Memory Budget Enforcement:**
- ONNX/CoreML allocator: 8 MB hard ceiling (custom allocator returns `AllocError` on overflow → graceful fallback to Flat-search).
- Runtime monitor: `tikv-jemallocator` `malloc_stats_print` polls heap every 5 s. If heap > 6 MB: reduce batch size 32 → 8 vectors/batch.
**Whisper Model Tier Selection:**
pub fn select_whisper_tier(available_ram_mb: u32, battery_pct: u8) -> WhisperModelTier {
    if battery_pct < 20    { return WhisperModelTier::Disabled; }
    if available_ram_mb > 200 { return WhisperModelTier::Base; }  // 74 MB
    if available_ram_mb > 100 { return WhisperModelTier::Tiny; }  // 39 MB
    WhisperModelTier::Disabled
// On Disabled: emit CoreSignal::StateChanged with note "Voice transcription unavailable."
**PII Redaction (Interactive SLM Dual-Masking):**
1. Core runs local NER (ONNX/CoreML, < 1 MB) to identify PII: names, phone numbers, email addresses.
2. PII replaced with aliases: `[REDACTED_PHONE_1]`, `[REDACTED_EMAIL_1]`.
3. Masked prompt sent to LLM (cloud or local).
4. LLM returns response. Core de-tokenizes aliases to real values.
5. `SessionVault` `ZeroizeOnDrop` clears alias map within 100 ms.
**AI Quota Enforcement:**
- Per-`.tapp`: 10,000 tokens/hour.
- Overage: return `ERR_AI_QUOTA_EXCEEDED`. UI presents upgrade prompt.
- Enterprise plan (License JWT `features` field): unlimited.
**KV-Cache Management:**
- Mobile: 1 KV-Cache slot active at a time. Inactive slots: LZ4-compressed to storage.
- Desktop: multiple KV-Cache slots in Hot RAM simultaneously.
**iOS CoreML Parity Path (W^X constraint):**

### §5.4 XPC Transaction State Machine


### §5.5 Push Notification State Machine


### §5.6 Device PIN Failure State Machine


---

## §6 — API / IPC CONTRACT

### §6.1 CoreSignal Catalog (Core → UI)

| Signal | Payload Fields | Trigger Condition |
|---|---|---|
| `StateChanged` | `table: &str, version: u64` | Any DAG mutation or DB state change |
| `ComponentFault` | `component: &str, severity: FaultSeverity` | Any `catch_unwind` caught panic |
| `MeshRoleChanged` | `new_role: MeshRole` | Mesh topology change |
| `EmdpExpiryWarning` | `minutes_remaining: u32` | T-10 min and T-2 min during EMDP TTL |
| `EmdpCausalFreeze` | `reason: CausalFreezeReason` | **[NEW]** Sudden Desktop loss before escrow |
| `DeadManWarning` | `hours_remaining: u32` | T-12 h and T-1 h offline grace period |
| `TierChanged` | `new_tier: NetworkTier, reason: TierChangeReason` | ALPN tier change or AWDL loss |
| `DagMergeProgress` | `completed: u64, total: u64` | Every 200 ms when merge backlog > 500 events |
| `XpcHealthDegraded` | `crash_count: u32, window_secs: u32` | macOS XPC crash rate exceeds threshold |
| `MemoryPressureWarning` | `component: &str, allocated_mb: u32` | `MemoryArbiter` allocated > 80% ceiling |
| `MediaComplete` | `cas_hash: [u8; 32]` | All media chunks downloaded and decrypted |

### §6.2 UICommand Catalog


---

## §7 — PLATFORM MATRIX

### §7.1 Feature Availability Matrix


### §7.2 Platform-Specific Constraints


### §7.3 RAM Budget Enforcement Matrix (Mobile)


### §7.4 Mesh Mode Feature Restrictions


### §7.5 Known Implementation Gaps

| Item | Severity | Reference | Status |
|---|---|---|---|
| WasmParity CI gate (wasm3 vs wasmtime semantic identity, ≤ 20 ms delta) | **Blocker** | F-07, CICD-01 | **Sprint 1 — spec complete, implementation required** |
| CI/CD code signing pipeline (all 5 platforms) | Blocker | `ops/signing-pipeline.md` | Not implemented |
| Dart FFI NativeFinalizer Clippy lint (FFI-01 enforcement) | Blocker | F-03, TERA-CORE §4.3 | **Spec patched in PLATFORM-17 v0.5.0** |
| AppArmor/SELinux postinstall script for Linux | **Blocker** | F-15 | **Sprint 1 — spec complete in §F-15** |
| `sled` crate version pinned in `Cargo.toml` | Medium | F-07 Transient State | Not pinned |
| Border Node auto-detection heuristics (algorithm spec) | Medium | F-05 | Algorithm undefined |
| **[PATCH 09] Windows ARM64 SAB CI gate (WebView2 COOP+COEP)** | **Medium — CI gate required** | F-03 | **CI job required: `aarch64-pc-windows-msvc` with WebView2; assert `crossOriginIsolated == true`** |

**[PATCH Issue-09] Windows ARM64 SAB CI Gate Specification:**

WebView2 on Windows ARM64 has documented issues where `crossOriginIsolated` returns `false`
despite correct `COOP+COEP` headers due to ARM64-specific process sandboxing in some Chromium
versions. This causes silent SAB Tier 1 → Named Pipe fallback without audit trail (IPC-02 violation).

Required CI job:

```yaml
# .github/workflows/windows-arm64-sab.yml
name: Windows ARM64 SAB Validation
on: [push, pull_request]
jobs:
  sab-arm64:
    runs-on: windows-latest  # with ARM64 emulation
    steps:
      - name: Build for aarch64-pc-windows-msvc
        run: cargo build --target aarch64-pc-windows-msvc --features tauri
      - name: Verify SAB availability
        run: |
          # Assert crossOriginIsolated == true in WebView2
          # Assert SharedArrayBuffer construction succeeds
          cargo test --target aarch64-pc-windows-msvc --test sab_availability
      - name: Verify Named Pipe fallback audit trail
        run: cargo test --test sab_fallback_audit_trail
        # Must assert CoreSignal::TierChanged emitted with audit entry on SAB unavailable
```

---

## §8 — NON-FUNCTIONAL REQUIREMENTS

### §8.1 Performance

| Metric | Target | Source |
|---|---|---|
| IPC buffer acquire P99 | < 100 µs | CICD-01 |
| AES-256-GCM throughput regression | < 10% drop | CICD-01 |
| `hot_dag.db` checkpoint P99 | < 10 ms | CICD-01 |
| ALPN negotiation total | < 50 ms | F-14 |
| MLS epoch rotation (100 members) | ≤ 1 s | CICD-01 |
| `sled` transient state restore | < 50 ms | F-07 |
| Screen capture prevention overlay | < 16 ms (at 60 Hz) | F-11a |
| `tera_core_flush_io()` on mobile | ≤ 50 ms | F-15 |
| XPC journal PENDING write (synchronous=FULL) | < 10 ms | F-07 |
| GATT pre-auth challenge-response | < 500 ms | F-05 |

### §8.2 Memory


### §8.3 Latency


### §8.4 Reliability

| Scenario | Requirement | Source |
|---|---|---|
| WAL crash safety | Zero data loss; auto-replay on next open | F-15 |
| Relay restart with 1000 STAGED events | Zero data loss; recovery < 60 s | INFRA-06 (SC-03) |
| Network partition 30 min then rejoin | Zero data loss; recovery < 120 s | INFRA-06 (SC-01) |
| WASM sandbox panic | Restart after 1 s; Core unaffected | F-07 |
| XPC journal PENDING durable | WAL synchronous=FULL; fsync before XPC dispatch | F-07 |
| EMDP sudden Desktop loss before escrow | CAUSAL_FREEZE; mandatory epoch rotation on reconnect | F-05 |
| Dead Man Switch deferral | DeadManDeferralEntry in Audit Log before deferral | F-11 |

---

## §9 — SECURITY MODEL

### §9.1 Key Management


### §9.2 Trust Boundaries


### §9.3 Encryption Model


### §9.4 Attack Surface

| Surface | Threat | Mitigation |
|---|---|---|
| Push key version mismatch | Replay attack on old key | Ghost Push; Main App decrypts with rotated key |
| WASM egress | Unauthorized network access | OPA policy check; declared endpoints only |
| WASM memory | DAG buffer write | `PROT_READ`-only; `SIGSEGV` caught by `catch_unwind` |
| FFI boundary | Raw pointer leakage | Token protocol; Clippy lint enforced (SEC-02) |
| **[PATCH 01] Dart FFI double-release** | Use-after-free on Android | Generation counter in token registry rejects stale tokens |
| **[PATCH 03] ALPN probe race** | Permanent QUIC disable on working networks | Per-protocol fail count; QUIC win resets count |
| **[PATCH 15] BLE GATT pre-auth** | ML-KEM public key fingerprinting | GATT challenge-response before any key material exchange |
| **[PATCH 13] Dead Man Switch deferral** | Insider threat via call-to-defer | DeadManDeferralEntry in tamper-proof Audit Log before deferral |
| LLM prompt injection | Malicious `.tapp` output | AST Sanitizer; 3rd TAINTED → `.tapp` suspend |
| Protocol downgrade | QUIC → WSS forced | QUIC-Pinning State Machine |

### §9.5 Implementation Contract — Security Rules

| Rule ID | Rule | Enforcement |
|---|---|---|
| SEC-01 | No plaintext UI buffer outlives the render frame. | `cargo miri test`. CI failure: blocker. |
| SEC-02 | No `Vec<u8>`, `*const u8`, or `*mut u8` in `pub extern "C"`. | CI Clippy lint. Blocker. |
| SEC-03 | All clipboard operations route through Protected Clipboard Bridge. | Code review + CI. |
| SEC-04 | WASM sandbox: `PROT_READ`-only DAG access. | Runtime enforcement. |
| SEC-05 | iOS Keychain access groups segmented (NSE / Main / Share). | Keychain entitlement. |
| **SEC-06 [NEW]** | **Dead Man Switch deferral: `DeadManDeferralEntry` in Audit Log before deferral.** | **Code review; Audit Log validator.** |
| **SEC-07 [NEW]** | **GATT pre-auth challenge-response before ML-KEM key exchange.** | **Integration test in TestMatrix SC-22.** |

---

## §10 — FAILURE MODEL

### §10.1 Network Failure

| Condition | Detection | Response | Signal |
|---|---|---|---|
| QUIC UDP:443 blocked | 50 ms probe timeout | Auto-downgrade to gRPC; increment only `quic_probe_fail_count` | `CoreSignal::TierChanged` |
| EMDP TTL expired, no hand-off | TTL counter reaches 0 | Enter SoloAppendOnly mode | `CoreSignal::EmdpExpiryWarning` |
| EMDP sudden Desktop loss before escrow | EMDP active + Desktop gone + no escrow received | Enter `CAUSAL_FREEZE` | `CoreSignal::EmdpCausalFreeze` |

### §10.2 Storage Failure

| Condition | Detection | Response | Log Event |
|---|---|---|---|
| WAL > 50 MB (mobile) | Background Tokio task | Trigger `PRAGMA wal_checkpoint(TRUNCATE)` — NOT VACUUM INTO | None |
| Schema migration fails (`cold_state.db`) | Migration error | Drop and rebuild from `hot_dag.db` | `COLD_STATE_REBUILD` |
| Shadow DB write TOCTOU | Mutex<bool> guards compound check+write | No race possible | None |

### §10.3 Key Failure


| Condition | Response | Log Event |
|---|---|---|
| Huawei device revoked | Server bumps push_key_version → Ghost Push on stale key | `HUAWEI_PUSH_KEY_VERSION_BUMPED` |
| Android CDM revocation | Emit `ComponentFault`; show persistent re-grant banner | `FCM_CDM_REVOKED` |

### §10.4 Runtime Failure


| Condition | Component | Response | Signal |
|---|---|---|---|
| XPC Worker crash, PENDING journal missing | macOS | Was: silent loss. Now: impossible — `synchronous=FULL` ensures PENDING is durable | `CoreSignal::ComponentFault` |
| Dart FFI GC finalizer double-release | Android, Huawei | Generation counter in Rust registry → stale token rejected as no-op | CI BLOCKER metric |

---

## §11 — VERSIONING & MIGRATION

### §11.1 Schema Migration Strategy

**`ShadowMigrationLock` type change (v0.4.0 → v0.5.0):**

`ShadowMigrationLock` changed from `AtomicBool` to `tokio::sync::Mutex<bool>`. This is a
Rust-internal type with no schema migration required. Client update will automatically use
the new locking primitive on next app launch.

**`XpcJournalEntry` connection type change:**

The XPC journal table is now accessed via a dedicated `synchronous=FULL` SQLite connection.
No schema change; existing journal entries are fully compatible. The `hot_dag.db` schema
version is NOT bumped for this change.

### §11.2 Backward Compatibility


---

## §12 — OBSERVABILITY

### §12.1 Named Log Events

| Event ID | Condition | Feature | Level |
|---|---|---|---|
| `COLD_STATE_REBUILD` | `cold_state.db` dropped and rebuilt | F-04 | INFO |
| `STRONGBOX_UNAVAILABLE` | Android StrongBox fallback | F-11/F-12 | WARN |
| `HUAWEI_CRL_STALE` | Huawei CRL delay caused deferred decryption | F-02 | WARN |
| `HUAWEI_PUSH_KEY_VERSION_BUMPED` | **[NEW]** Server bumped version on revocation | F-02 | AUDIT |
| `FCM_CDM_REVOKED` | **[NEW]** Android CDM association missing | F-02 | WARN |
| `EMDP_CAUSAL_FREEZE` | **[NEW]** Sudden Desktop loss before escrow | F-05 | WARN |
| `DEAD_MAN_SWITCH_DEFERRED` | **[NEW]** Deferral logged with counter delta | F-11 | AUDIT |
| `ALPN_PROBE_RACE_WIN` | **[NEW]** QUIC won parallel race; gRPC fail count NOT incremented | F-14 | DEBUG |
| `OFFLOAD_HMAC_VIOLATION` | HMAC mismatch on ONNX offload | INFRA-01 | AUDIT |
| `INVALID_RECOVERY_TICKET` | Recovery Ticket Ed25519 invalid | F-12 | AUDIT |
| `MEDIA_UPLOAD_FAILED` | Chunked upload failed after 3 retries | F-09 | ERROR |
| `PIN_COUNTER_CORRUPTED` | Failed_PIN_Attempts counter tampered | F-11e | AUDIT |
| `ONNX_OOM_FALLBACK` | ONNX allocator OOM | F-10 | WARN |

### §12.6 Canary Rollback Metrics


---

## §13 — APPENDIX

### §13.2 Error Code Reference

| Error Code | Condition | Feature |
|---|---|---|
| `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` | Mesh Mode active | F-10 |
| `ERR_MESH_MODE_DELEGATION_SUSPENDED` | Mesh Mode active | F-08 |
| `ERR_EMDP_CAUSAL_FREEZE` | **[NEW]** Sudden Desktop loss before escrow | F-05 |
| `ERR_FFI_STALE_TOKEN` | **[NEW]** Token's generation counter does not match registry | F-03 / PLATFORM-17 |
| `ERR_GATT_PREAUTH_FAILED` | **[NEW]** GATT challenge-response failed | F-05 |
| `ERR_RATE_LIMIT_EXCEEDED` | `.tapp` token bucket exhausted | F-07 |
| `ERR_MNEMONIC_INVALID` | BIP-39 mnemonic incorrect | F-12 |
| `ERR_AI_QUOTA_EXCEEDED` | Token quota exceeded | F-10 |
| `BufferNotFound` | Token not in Core registry | F-03 |

### §13.3 Implementation Contract — Complete Rule Index

**Security Rules (SEC):** → §9.5 (SEC-01 through SEC-07)

**Platform Rules (PLT):**

| Rule ID | Rule |
|---|---|
| PLT-01 | iOS: `wasm3` interpreter only in App Sandbox. No JIT in Main App: **blocker**. |
| PLT-02 | iOS NSE: Static Memory Arena 10 MB. **ONNX prohibited in NSE build.** `debug_assert!(NsePolicy::is_onnx_prohibited())` at entry. |
| PLT-03 | iOS: Voice calls require CallKit. |
| PLT-04 | Linux: Flatpak packaging prohibited. `.deb`/`.rpm` or AppImage + Cosign only. |
| PLT-05 | Linux clipboard: detect display server at runtime. |
| PLT-06 | Android 14+: FCM `priority = "high"` AND CDM `REQUEST_COMPANION_RUN_IN_BACKGROUND`. **Add CDM revocation health check on every FCM receipt.** |
| PLT-07 | Huawei: AOT `.waot` bundles only. CRL delay ≤ 4 h in SLA. **Server-side push key version bump on revocation mitigates 4h window.** |
| PLT-08 **[NEW]** | **Windows ARM64: SAB availability CI gate required. Assert `crossOriginIsolated == true` in WebView2 on `aarch64-pc-windows-msvc`.** |

**Feature Integrity Rules (FI):**

| Rule ID | Rule |
|---|---|
| FI-01 | Every feature maps to at least one TERA-CORE module. Orphan features: **blocker**. |
| FI-02 | Mesh Mode restrictions enforced in Rust Core. UI-side Mesh override: **blocker**. |
| FI-03 | WasmParity CI gate must pass before any `.tapp` Marketplace listing. **Sprint 1 blocker.** |
| FI-04 | `sled` crate pinned in `Cargo.toml`. |
| FI-05 | iOS `election_weight = 0` hardcoded. Any PR modifying: **blocker**. |
| FI-06 **[NEW]** | **`PRAGMA wal_checkpoint(TRUNCATE)` is the sole background WAL compaction path. `VACUUM INTO` only under `BEGIN EXCLUSIVE` for admin defrag.** |
| FI-07 **[NEW]** | **XPC journal PENDING write uses dedicated `synchronous=FULL` SQLite connection. PENDING write without fsync: **blocker**.** |
| FI-08 **[NEW]** | **GATT pre-auth challenge-response must complete before any ML-KEM key material is transmitted over BLE.** |

**IPC Rules (IPC):**

| Rule ID | Rule |
|---|---|
| IPC-01 | State flow unidirectional Core → UI. Bidirectional state channel: **blocker**. |
| IPC-02 | SAB Tier Ladder selection logged to audit trail. Silent tier selection: **blocker**. |
| IPC-03 | `CoreSignal::DagMergeProgress` emitted every 200 ms when merge backlog > 500 events. |
| IPC-04 **[NEW]** | **`FfiToken` carries monotonic generation counter. Stale tokens (e.g. from GC finalizer) rejected by Rust registry as no-op.** |

---

## §14 — CHANGELOG

| Version | Date | Summary |
|---|---|---|
| 0.5.0 | 2026-03-23 | Security audit patch batch: 15 issues fixed. Key changes: PLATFORM-17 Dart FFI generation counter; F-02 NSE RAM table + ONNX prohibition + Huawei revocation fast-path + Android CDM detection; F-04 checkpoint-first WAL + Mutex shadow lock; F-05 EMDP proactive escrow + CAUSAL_FREEZE + GATT pre-auth; F-07 WasmParity Sprint 1 blocker + XPC synchronous=FULL; F-11 DeadManDeferralEntry audit trail; F-13 OPA policy channel schema exemption; F-14 ALPN per-protocol fail count race fix; F-15 full AppArmor/SELinux profiles + --check-permissions subcommand. |
| 0.4.0 | 2026-03-21 | Full restructure to production-grade standard. |
| 0.2.6 | 2026-03-19 | Add OBSERVE-01/02, PLATFORM-17/18/19, INFRA-01–06, CICD-01. |
| 0.2.3 | 2026-03-18 | Complete rewrite. Full alignment with TERA-CORE v2.0. |<!-- markdownlint-disable MD041 -->

```yaml
# DOCUMENT IDENTITY
id:        "TERA-FEAT"
title:     "TeraChat — Feature Technical Specification"
version:   "0.5.0"
status:    "ACTIVE — Implementation Reference"
date:      "2026-03-23"
audience:  "Frontend Engineer, Mobile Engineer, Desktop Engineer, Product Engineer"
purpose:   "Defines all client-facing and system-level features. Maps every feature to a
            verified core module in Core_Spec.md (TERA-CORE). Governs platform-specific
            behavior, OS lifecycle hooks, IPC bridge, WASM runtime, local storage, and
            user interaction contracts."

depends_on:
  - id: "TERA-CORE"

consumed_by:
  - id: "TERA-DESIGN"
  - id: "TERA-MKT"
  - id: "TERA-TEST"

scope: |
  Client-side and system-level features of TeraChat across iOS, Android, Huawei, macOS,
  Windows, and Linux platforms. Includes the IPC bridge, OS lifecycle hooks, WASM runtime,
  local SQLite storage, push notification handling, platform-specific constraints, and
  operational infrastructure (INFRA-01 through INFRA-06, OBSERVE-01/02, CICD-01).

non_goals:
  - MLS cryptographic internals         → TERA-CORE §5
  - CRDT merge algorithms               → TERA-CORE §7
  - Server relay infrastructure         → TERA-CORE §9
  - UI animations and glassmorphism     → TERA-DESIGN
  - Plugin publishing and Marketplace   → TERA-MKT
  - Chaos engineering test scenarios    → TERA-TEST

assumptions:
  - Rust Core is the single source of truth for all business state.
  - UI layer is a pure renderer — holds no crypto keys, no business state.
  - Host adapters (Swift/Kotlin/ArkTS) handle all platform-specific OS APIs.
  - VPS relay has zero-knowledge of plaintext content.
  - TERA-CORE v2.0 is the canonical reference for all Core module contracts.

constraints_global:
  - All plaintext buffers use ZeroizeOnDrop; no plaintext outlives the render frame.
  - No raw pointer crosses the FFI boundary; FFI token protocol mandatory.
  - All cryptographic operations route through TERA-CORE crypto/ modules.
  - Platform-specific code lives in host adapters, never in shared Rust Core.
  - Every feature maps to at least one TERA-CORE module; orphan features are blockers.

breaking_changes_policy: |
  Schema migrations require {db_path}.bak.v{version} backup before execution.
  cold_state.db may be dropped and rebuilt from hot_dag.db at any time (DB-02 safety net).
  CoreSignal and UICommand enum changes: additive only; no removal without deprecation cycle.
  DelegationToken field additions permitted; removals require migration path.
  TERA-CORE §12.2 governs all DB migration rules (DB-01, DB-02, DB-03).

patch_history:
  - version: "0.5.0"
    date: "2026-03-23"
    issues_fixed:
      - "Issue-01: Dart FFI NativeFinalizer double-release race (PLATFORM-17)"
      - "Issue-02: iOS NSE Static Memory Arena additive overflow (F-02)"
      - "Issue-03: QUIC parallel probe race corrupts strict_compliance (F-14)"
      - "Issue-04: VACUUM INTO hot_dag concurrent Tokio writer race (F-04)"
      - "Issue-05: EMDP Key Escrow orphan on sudden Desktop loss (F-05)"
      - "Issue-06: WasmParity CI gate not implemented (F-07, CICD-01)"
      - "Issue-07: XPC Transaction Journal PENDING + unsynced WAL (F-07)"
      - "Issue-08: Shadow DB rename + NSURLSession TOCTOU (F-04)"
      - "Issue-09: Windows ARM64 SAB untested (§7.5)"
      - "Issue-10: Linux AppArmor/SELinux postinstall absent (F-15)"
      - "Issue-11: Huawei HMS CRL 4-hour revocation window (F-02)"
      - "Issue-12: Android 14+ FCM CDM revocation no fallback (F-02)"
      - "Issue-13: Dead Man Switch deferral no audit trail (F-11)"
      - "Issue-14: Federation OPA policy sync blocked by schema version (F-13)"
      - "Issue-15: BLE GATT pre-auth gap for ML-KEM key exchange (F-05)"
```

---

## §1 — EXECUTIVE SUMMARY

TeraChat is a Zero-Knowledge, end-to-end encrypted team messaging platform. The server relay receives only ciphertext and has no access to user identity, message content, or group membership. All cryptography and business logic live in a shared Rust Core binary deployed identically across iOS, Android, Huawei, macOS, Windows, and Linux.

**Architecture in one sentence:** A shared Rust Core (cryptography, CRDT DAG, network, storage) exposes a strict unidirectional IPC bridge to platform UI layers (Flutter/Swift/Tauri), with a blind VPS relay for ciphertext routing only.

### §1.1 Primary Objectives

| Objective | Mechanism |
|---|---|
| Zero-Knowledge E2EE at rest and in transit | MLS RFC 9420; AES-256-GCM; server-blind storage |
| Offline-first survival | BLE 5.0 / Wi-Fi Direct Mesh; CRDT DAG; Store-and-Forward |
| Extensible mini-app platform | WASM `.tapp` sandbox with capability-based isolation |
| Privacy-safe AI inference | Local ONNX/CoreML SLM with PII redaction; no raw prompt leaves device |
| Single-binary operational simplicity | VPS relay: 512 MB RAM; 5-minute setup; no cluster coordination |

### §1.2 Five Critical Features

| Feature | Why Critical |
|---|---|
| F-01: Secure E2EE Messaging | Core value proposition; all other features serve or protect it |
| F-05: Survival Mesh Networking | Differentiator; text messaging survives total Internet loss |
| F-03: IPC Bridge and State Sync | Foundation for all UI interaction; security boundary for key material |
| F-07: WASM Plugin Sandbox | Extensibility layer; untrusted code isolated from Core |
| F-10: AI / SLM Integration | Local inference with PII redaction; no cloud dependency for base tier |

### §1.3 Architecture Overview

```text
┌─────────────────────────────────────────────────────────┐
│  UI Layer (Swift / Flutter / Tauri)                      │
│  Pure renderer — no keys, no business state              │
├──────────────── IPC Bridge (F-03) ──────────────────────┤
│  CoreSignal ← (unidirectional) ← Rust Core             │
│  UICommand  → (commands only)  → Rust Core             │
│  Data Plane: SAB / JSI / Dart FFI (token protocol)     │
├─────────────────────────────────────────────────────────┤
│  Rust Core (shared binary across all platforms)          │
│  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌──────────────┐  │
│  │ crypto/ │ │  crdt/   │ │ mesh/  │ │    infra/    │  │
│  │ MLS,    │ │ hot_dag  │ │ BLE,   │ │ relay, TURN, │  │
│  │ push,   │ │ cold_state│ │ WiFi   │ │ WASM, ONNX  │  │
│  │ zeroize │ │ snapshot │ │ Direct │ │ metrics     │  │
│  └─────────┘ └──────────┘ └────────┘ └──────────────┘  │
├─────────────────────────────────────────────────────────┤
│  Host Adapters (Swift / Kotlin / ArkTS)                  │
│  Platform OS APIs — CallKit, NSE, FCM, HMS, BGTask       │
└──────────────── Platform Layer ─────────────────────────┘
         │                              │
    TLS 1.3 + mTLS                BLE / Wi-Fi Direct
         │                              │
┌────────────────┐            ┌─────────────────────┐
│  VPS Relay     │            │  Mesh Peer Network   │
│  Blind router  │            │  BLE Store-Forward   │
│  Ciphertext    │            │  (offline-only)      │
│  only; no keys │            └─────────────────────┘
└────────────────┘
```

---

## §2 — SYSTEM OVERVIEW

### §2.1 Architecture Overview

| Layer | Technology | Responsibility |
|---|---|---|
| UI Layer | Swift (iOS/macOS), Flutter (Android/Huawei), Tauri (Desktop) | Render only; issues UICommands; processes CoreSignals |
| IPC Bridge | FFI token protocol; SAB / JSI / Dart FFI | Zero-copy data transfer; no raw pointers; ZeroizeOnDrop |
| Rust Core | Shared binary (`libterachat_core.a` / `.so`) | All crypto, DAG, network, storage, policy enforcement |
| Host Adapters | Swift/Kotlin/ArkTS | Platform OS APIs; BLE, CallKit, NSE, FCM, HMS |
| VPS Relay | Rust daemon + Tokio | Blind ciphertext routing; pub/sub fanout; WAL staging |
| Blob Storage | MinIO / Cloudflare R2 / Backblaze B2 | Encrypted chunk storage by `cas_hash`; zero-knowledge |

### §2.2 Data Flow (Total)

```text
Send Path:
  User input → UICommand::SendMessage
    → Rust Core: AES-256-GCM encrypt (Epoch_Key, biometric gate)
    → CRDT_Event appended to hot_dag.db WAL (durable)
    → Online:  TLS 1.3 + mTLS → VPS Relay → wal_staging.db → pub/sub
    → Offline: BLE Control Plane → Mesh Store-and-Forward (≤ 4 KB, text only)
    → CoreSignal::StateChanged → UI viewport refresh

Receive Path:
  VPS Relay pub/sub → client receives ciphertext CRDT_Event
    → Rust Core: MLS decrypt → CRDT merge into hot_dag.db
    → CoreSignal::StateChanged → UI: UICommand::ScrollViewport
    → Core: tera_buf_acquire → Data Plane buffer write (decrypted)
    → UI: render 20-message viewport via token
    → UICommand::ReleaseBuffer → ZeroizeOnDrop (ref_count == 0)
```

### §2.3 Trust Boundaries

| Boundary | What crosses it | What never crosses it |
|---|---|---|
| Rust Core ↔ UI (FFI) | Opaque `u64` token; typed enum signals/commands | Raw pointers; decrypted payloads; key material |
| Rust Core ↔ VPS Relay | AES-256-GCM ciphertext; CRDT_Event (encrypted) | Plaintext; sender identity; group structure |
| Rust Core ↔ WASM sandbox | Sanitized `Vec<ASTNode>`; `sled` namespace writes | MLS key material; raw DAG access; filesystem |
| iOS NSE ↔ Main App | `nse_staging.db`; flag in Shared Keychain | Push_Key (NSE-only keychain group) |
| Client ↔ Blob Storage | Encrypted chunks (AES-256-GCM); `cas_hash` path | Plaintext; file names; sender identity |

### §2.4 Deployment Model

| Tier | VPS Spec | Monthly Cost | Setup Time |
|---|---|---|---|
| Solo (≤ 50 users) | 1 vCPU, 512 MB RAM, 20 GB SSD | $6 + $1 storage | 5 min |
| SME (≤ 500 users) | 2 vCPU, 2 GB RAM, 40 GB SSD | $12 + $5 storage | 10 min |
| Enterprise (≤ 5000 users) | 4 vCPU, 8 GB RAM, 100 GB SSD | $28 + $20 storage | 20 min |
| Gov (air-gapped) | Existing hardware | CAPEX only | 1 hour |

---

## §3 — DATA MODEL

### §3.1 Local Storage Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `cold_state.db` | SQLite, SQLCipher AES-256 | Disk, permanent | Until Remote Wipe or Crypto-Shredding | Key from Secure Enclave; never hardcoded | TERA-CORE §7.1 |
| `cold_state_shadow.db` | SQLite, transient | Disk, temporary | Created on Hydration batch; deleted after atomic rename | Write-locked via `ShadowMigrationLock` (Mutex) during migration | TERA-CORE §7.1 |
| `hot_dag.db` | SQLite WAL | Disk, permanent | Append-only; cleaned via checkpoint | Append-only; tombstones only; no physical deletion | TERA-CORE §7.1 |
| `nse_staging.db` | SQLite WAL, iOS NSE only | Disk | Per push payload; cleared after Main App decryption | NSE-only keychain group access | TERA-CORE §5.5 |
| `wal_staging.db` | SQLite WAL, relay only | Disk | Per event; cleared on `Committed` status | Server-side only; no client key access | TERA-CORE §9.3 |
| `NetworkProfile` | SQLite row | Local config DB | Per network identifier; updated on probe result | mTLS cert fingerprint + SSID hash as network ID | TERA-CORE §9.2 |
| `TappTransientState` | `sled` LSM-Tree rows | RAM + disk, per DID | Per `.tapp` session; cleared on Mesh Mode | AES-256-GCM encrypted | TERA-FEAT §F-07 |
| `metrics_buffer.db` | SQLite | Disk | Max 48h / 500 KB; flushed on reconnect | Aggregate only; no user-correlated data | TERA-FEAT §OBSERVE-01 |

### §3.2 In-Memory Ephemeral Objects

| Object | Type | Location | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `Decrypted_Chunk` | `[u8]` plaintext | RAM, `ZeroizeOnDrop` | Single 2 MB chunk; zeroed after render frame | Must not outlive render frame | TERA-CORE §5.3 |
| `ViewportCursor` | `{top_id: Uuid, bottom_id: Uuid}` | RAM | Duration of scroll session | No sensitive content | TERA-FEAT §F-03 |
| `RingBuffer_2MB` | Circular fixed buffer | User RAM | Reused across media stream sessions | ZeroizeOnDrop between sessions | TERA-FEAT §F-09 |
| `KVCacheSlot` | LZ4-compressed LLM context | RAM | Per `.tapp` session; LZ4-compressed when inactive | No raw PII; alias-mapped via SessionVault | TERA-FEAT §F-10 |
| `MemoryArbiter` | `{allocations: HashMap<ComponentId, usize>}` | RAM | Process lifetime; enforces RAM budget matrix | Allocation denied returns `MemoryDenied` | TERA-CORE §3.3 |

### §3.3 IPC Signal and Command Objects

| Object | Type | Transport | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `CoreSignal` | Typed Rust enum | FFI signal channel | Unidirectional Core → UI; no response expected | No key material; no plaintext content | TERA-CORE §4.2 |
| `UICommand` | Typed Rust enum | FFI command channel | Consumed once by Core; no replay | No key material; plaintext passed only in `SendMessage` | TERA-CORE §4.2 |
| `DataPlane_Payload` | Raw bytes | SAB ring buffer / JSI pointer / Dart FFI | Held until `tera_buf_release(token)` called | Zeroed on release; never held across render frames | TERA-CORE §4.3 |
| `FfiToken` | Opaque `u64` | FFI return value | Valid until `tera_buf_release` called | Carries monotonic `generation` counter; stale generation rejected | TERA-CORE §4.3 |

### §3.4 Push and Notification Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `Push_Key_N` | AES-256-GCM symmetric key | Secure Enclave (iOS) / StrongBox (Android) | Rotated after each MLS Epoch rotation | NSE-only Keychain group (`group.com.terachat.nse`) | TERA-CORE §5.5 |
| `PushKeyVersion` | `u32` | Shared Keychain (iOS) / StrongBox metadata | Incremented on each rotation; also bumped by server-side revocation signal | Read by NSE to match payload header | TERA-CORE §5.5 |
| `NSE_StagedCiphertext` | Raw ciphertext bytes | `nse_staging.db` | Cleared after successful Main App decryption | Ciphertext only; no plaintext at rest | TERA-CORE §5.5 |

### §3.5 WASM Plugin Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `DelegationToken` | `{source_did, target_did, permissions, expires_at, signature}` | RAM + `hot_dag.db` | TTL 30 days; revocable by Admin at any time | Ed25519-signed by DeviceIdentityKey; tamper-evident | TERA-FEAT §F-08 |
| `EgressNetworkRequest` | Protobuf | In-flight | Single request; sanitized by Host Proxy | OPA policy check before execution; no raw TCP/UDP | TERA-CORE §4.1 |
| `XpcJournalEntry` | `{tx_id: Uuid, status: Pending\|Verified\|Committed}` | `hot_dag.db` | Per XPC transaction; cleared on Committed | Persisted with `synchronous=FULL` connection for crash safety | TERA-FEAT §F-07 |

---

## §4 — FEATURE MODEL

### §4.1 Feature Categories

| Category | Features | Section |
|---|---|---|
| Secure Messaging | E2EE send/receive, push notification | F-01, F-02 |
| IPC and State | Bridge, synchronization, memory management | F-03, F-15 |
| Local Storage | Two-tier SQLite, schema migration, hydration | F-04 |
| Survival Mesh | BLE/Wi-Fi Direct, EMDP, role management | F-05 |
| Voice and Video | WebRTC, CallKit, TURN failover | F-06 |
| WASM Plugins | `.tapp` lifecycle, sandbox, XPC recovery | F-07 |
| Plugin IPC | Delegation Tokens, inter-`.tapp` sharing | F-08 |
| Media Transfer | Chunked upload, deduplication, streaming | F-09 |
| AI / SLM | Local inference, PII redaction, cloud routing | F-10 |
| Device Security | Screen protection, clipboard, wipe | F-11 |
| Identity | Enrollment, recovery, geofencing | F-12 |
| Admin Controls | Policy, SCIM, audit, license | F-13 |
| Network Management | ALPN, probe learning, fallback | F-14 |
| Infrastructure | Compute distribution, blob storage, relay health | INFRA-01–06 |
| CI/CD | Build gates, chaos testing, SBOM | CICD-01, INFRA-06 |
| Observability | Client metrics, DAG merge UI | OBSERVE-01, OBSERVE-02 |

### §4.2 Feature ↔ Core Mapping

| Feature ID | Feature Name | Primary Core Modules | TERA-CORE References |
|---|---|---|---|
| F-01 | Secure E2EE Messaging | `crypto/mls_engine.rs`, `crdt/dag.rs` | §5.3, §7.1, §8.1, §4.2, §4.3 |
| F-02 | Push Notification Delivery | `crypto/push_ratchet.rs` | §5.5, §8.3, §4.2 |
| F-03 | IPC Bridge & State Sync | `ffi/ipc_bridge.rs`, `ffi/token_protocol.rs` | §4.2, §4.3, §2.2 |
| F-04 | Local Storage Management | `crdt/dag.rs`, `crdt/snapshot.rs` | §7.1, §7.4, §12.2 (DB-01, DB-02, DB-03) |
| F-05 | Survival Mesh Networking | `mesh/` (all six modules) | §6.1, §6.2, §6.3, §6.4, §6.5, §6.6, §6.7 |
| F-06 | Voice and Video Calls | `infra/relay.rs` (TURN), host adapters | §10.4, §6.4, §9.2, §5.3 |
| F-07 | WASM Plugin Sandbox | `ffi/token_protocol.rs`, platform WASM adapter | §4.1, §4.4, §3.2 |
| F-08 | Inter-`.tapp` IPC | `ffi/ipc_bridge.rs` | §4.2, §4.3, §3.2 |
| F-09 | Media and File Transfer | `crypto/mls_engine.rs`, `infra/relay.rs` | §5.3, §9.5, §7.1, §8.1 |
| F-10 | AI / SLM Integration | `infra/relay.rs` (VPS Enclave) | §3.3, §3.6, §4.4 |
| F-11 | Device Security | `crypto/hkms.rs`, `crypto/zeroize.rs` | §5.1, §5.2, §12.4 (PLT-04) |
| F-12 | Identity and Onboarding | `crypto/hkms.rs`, `crypto/mls_engine.rs` | §5.1, §5.2, §5.3 |
| F-13 | Admin Console | `infra/federation.rs`, `infra/metrics.rs` | §3.2, §5.1, §9.5, §9.6 |
| F-14 | Adaptive Network Management | `infra/relay.rs` | §9.2, §4.2 |
| F-15 | Crash-Safe WAL Management | `crdt/dag.rs`, `infra/wal_staging.rs` | §4.4, §7.1, §9.3, §12.2 |

---

### F-01: Secure E2EE Messaging

**Description:** Send and receive text messages encrypted end-to-end using MLS RFC 9420. The VPS relay receives only ciphertext. DAG merge for large backlogs is time-sliced to prevent mobile ANR.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow:**

1. User types message. UI sends `UICommand::SendMessage { recipient_did, plaintext }` via FFI.
2. Rust Core looks up `Epoch_Key` from RAM `ZeroizeOnDrop` struct.
3. Core encrypts: `AES-256-GCM(Epoch_Key, plaintext)`. Nonce = `Base_Nonce XOR chunk_seq_number`.
4. Core constructs `CRDT_Event`. Ed25519 signature via `DeviceIdentityKey` (biometric gate required).
5. Event appended to `hot_dag.db` WAL atomically before network dispatch.
6. **Online path:** TLS 1.3 + mTLS → VPS Relay → `wal_staging.db` → pub/sub fanout.
7. **Offline path:** BLE Control Plane → Mesh Store-and-Forward (text only, ≤ 4 KB).
8. Core emits `CoreSignal::StateChanged { table: "messages", version }`.
9. UI issues `UICommand::ScrollViewport`. Core returns 20-message viewport snapshot.
10. Plaintext `ZeroizeOnDrop` after render frame.

**DAG Merge (Mobile — ANR Prevention):**

- Mobile hard limit: `MAX_MOBILE_MERGE_EVENTS = 3000`.
- Backlog > 3000: emit `CoreSignal::StateChanged` with `SnapshotRequired`; delegate full merge to Desktop.
- Backlog > 500: `CoreSignal::DagMergeProgress { completed, total }` emitted every 200 ms.
- Mobile merge is time-sliced in batches of 100 events with `tokio::task::yield_now()` between batches.

**Failure Handling:** → §10.4 (Runtime), §10.1 (Network)

---

### F-02: Push Notification Delivery (E2EE)

**Description:** Deliver E2EE-encrypted push notifications to backgrounded devices. Decryption is local — APNs, FCM, and HMS never receive plaintext. A versioned Push Key Ladder handles key rotation without message loss.

**Supported Platforms:** 📱 iOS (NSE), 📱 Android (FCM), 📱 Huawei (HMS), 💻 macOS (daemon), 🖥️ Windows, 🖥️ Linux

**[PATCH Issue-02] iOS NSE RAM Budget — Cumulative Breakdown:**

> **CRITICAL:** The NSE Static Memory Arena is capped at 10 MB. Any ONNX workload is structurally
> prohibited from the NSE build target. Violations will silently exceed the 20 MB OS ceiling and
> cause Jetsam kill with no user-visible error.

| Component | Allocated | Notes |
|---|---|---|
| NSE Static Memory Arena | 10 MB | Pre-allocated at startup |
| MLS decrypt (ciphertext + overhead) | ~2 MB | Per message |
| OS system overhead inside NSE | ~3 MB | dyld, libsystem, stack |
| **Total used** | **~15 MB** | **5 MB margin** |
| ONNX Micro-NER (smallest model) | 8 MB | **PROHIBITED in NSE** |
| Any WASM workload | variable | **PROHIBITED in NSE** |

The 5 MB margin is **insufficient for any ONNX or WASM workload**. The `push_ratchet.rs` module
must be compiled with `features = ["nse-only"]` which strips all ONNX, CRDT Automerge, and
SQLCipher dependencies at link time. A `debug_assert!(NsePolicy::is_onnx_prohibited())` fires at
NSE entry point in both debug and release-with-debug-info builds.

```rust
// NSE build target — Cargo.toml
[features]
nse-only = ["terachat-crypto-minimal"]  # strips MLS, CRDT, SQLCipher, ONNX

// Entry point guard
pub fn nse_entry_point() {
    #[cfg(feature = "nse-only")]
    debug_assert!(
        !cfg!(feature = "onnx"),
        "FATAL: ONNX linked into NSE build — will exceed 20 MB iOS ceiling"
    );
    // ...
}
```

**[PATCH Issue-02] Version-mismatch path:**
On `push_key_version` mismatch, the NSE **defers ALL ML inference to Main App**. No NER, no ONNX,
no model loading in NSE path. The staged ciphertext is forwarded to Main App which handles full
decryption with the 2 GB Main App RAM budget.

**Platform-Specific Behavior:**

| Platform | Push Channel | Process | RAM Constraint |
|---|---|---|---|
| 📱 iOS | APNs `mutable-content: 1` | `UNNotificationServiceExtension` (NSE) | ≤ 20 MB hard (OS) |
| 📱 Android | FCM `priority = "high"` | `FirebaseMessagingService` | No hard limit |
| 📱 Huawei | HMS Push Kit Data Message | HarmonyOS background service | No hard limit |
| 💻 macOS | APNs (LaunchAgent) | `terachat-daemon` (~4.5 MB RAM) | No hard limit |
| 🖥️ Windows | WNS / `terachat-daemon` | Windows Service | No hard limit |
| 🖥️ Linux | `terachat-daemon` | systemd user service | No hard limit |

**User Flow (iOS NSE — primary path):**

1. APNs delivers encrypted payload. iOS wakes NSE (≤ 20 MB RAM enforced).
2. NSE allocates Static Memory Arena (10 MB, pre-allocated at startup, NSE-only build). **No ONNX.**
3. NSE reads `Push_Key_N` from Shared Keychain (Access Group: `group.com.terachat.nse`).
4. NSE reads `push_key_version` from payload header.
5. **Version match:** AES-256-GCM decrypt in arena → display OS notification → `ZeroizeOnDrop` arena.
6. **Version mismatch or payload_size > 4 KB or epoch_delta > 1 (Ghost Push):**
   - Cache raw ciphertext to `nse_staging.db`.
   - Set `main_app_decrypt_needed = true` in Shared Keychain.
   - Send `content-available: 1` wake signal.
   - Main App wakes → rotates `Push_Key` → decrypts `nse_staging.db` → displays notification.
   - **All ML inference deferred to Main App path only.**

**[PATCH Issue-11] Huawei HMS CRL Revocation Fast-Path:**

Huawei CRL refresh baseline is ≤ 4 hours vs ≤ 30 minutes on iOS/Android. This creates a security
window where a revoked Huawei device can decrypt push notifications for up to 4 hours.

**Server-side mitigation:** On SCIM-triggered device revocation, the relay MUST:

1. Immediately increment `push_key_version` for the revoked `device_did` in the server-side push
   key version table.
2. Inject the new version number into all subsequent push payload headers destined for that device.
3. The Huawei device's stale key cannot decrypt the new version → Ghost Push (no content).

```rust
// Relay-side: push key version bump on revocation
async fn revoke_device_push_access(device_did: &DeviceId, db: &Pool) {
    // Atomic increment — forces Ghost Push on stale Huawei keys
    sqlx::query!(
        "UPDATE device_push_versions SET version = version + 1 WHERE device_did = $1",
        device_did.as_str()
    ).execute(db).await?;
    // CRDT event: notify group of revocation for MLS epoch rotation
    emit_mls_remove_member(device_did).await?;
}
```

**CRL SLA disclosure:** Huawei devices have a worst-case 4-hour CRL propagation delay. This must
be disclosed in enterprise SLA documentation. The push key version bump mitigates content exposure
but MLS epoch rotation (full revocation) may take up to 4 hours on Huawei without foreground app.

**[PATCH Issue-12] Android 14+ CDM Permission Revocation Detection:**

Companion Device Manager (CDM) permission can be revoked by the user at any time via
Settings → Apps → Special App Access. When revoked, push notifications drop silently in the
Android 14 "Restricted" battery bucket (≤ 10 FCM messages/hour).

```kotlin
// FirebaseMessagingService — CDM health check on every FCM message receipt
override fun onMessageReceived(message: RemoteMessage) {
    val cdm = getSystemService(CompanionDeviceManager::class.java)
    val associations = cdm.myAssociations
    if (associations.isEmpty()) {
        // CDM permission revoked — notify Core and surface re-grant prompt
        TeraCore.emitComponentFault("fcm_companion", FaultSeverity.Warning)
        showCdmReGrantNotification()  // Deep-link to Settings
    }
    // Proceed with FCM message handling
    TeraCore.handleFcmMessage(message.data)
}

private fun showCdmReGrantNotification() {
    val intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS).apply {
        data = Uri.fromParts("package", packageName, null)
    }
    // Persistent banner: "Notification delivery degraded — tap to restore"
    NotificationManagerCompat.from(this).notify(
        NOTIF_CDM_REVOKED,
        buildCdmReGrantNotification(intent)
    )
}
```

**Observability:**

- Metric: `nse_circuit_breaker_trips`, `push_key_version_mismatches` (OBSERVE-01).
- Log: `HUAWEI_CRL_STALE` on Huawei CRL-dependent decryption failure.
- Log: `FCM_CDM_REVOKED` when CDM association missing on Android 14+.
- Signal: `CoreSignal::ComponentFault { component: "fcm_companion", severity: Warning }` on CDM revocation.

**Failure Handling:** → §10.3 (Key Failure)

- NSE OOM: Circuit Breaker terminates NSE gracefully. Sets `main_app_decrypt_needed = true`.
- `Push_Key` not found in Keychain: display generic "New message" notification with no content.
- HMS polling delay (Huawei): server-side push key version bump mitigates exposure; log `HUAWEI_CRL_STALE`.
- CDM revocation (Android 14+): emit `ComponentFault`; show persistent re-grant banner.

---

### F-03: IPC Bridge and State Synchronization

**Description:** All communication between Rust Core and the UI layer routes through a strict unidirectional IPC bridge. No raw pointer crosses the FFI boundary. The Dart FFI `TeraSecureBuffer` wrapper is mandatory on Android/Huawei (PLATFORM-17).

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**Data Plane Transport Selection:**

| Platform | Transport | API | Throughput |
|---|---|---|---|
| 📱 iOS | C++ JSI Shared Memory Pointer | `UniquePtr` + token protocol | ~400 MB/s |
| 📱 Android | Dart FFI TypedData | Zero-copy into C ABI | ~400 MB/s |
| 📱 Huawei | Dart FFI TypedData | Zero-copy into C ABI | ~400 MB/s |
| 💻 macOS | SharedArrayBuffer ring buffer | COOP+COEP headers required | ~500 MB/s |
| 🖥️ Windows | SAB Tier 1 → Named Pipe fallback | Auto-selected at runtime | ~500 / ~200 MB/s |
| 🖥️ Linux | SAB Tier 1 → Named Pipe → stdin fallback | Auto-selected at runtime | ~500 / ~200 / ~50 MB/s |

**Failure Handling:** → §10.4 (Runtime)

- SAB unavailable: auto-downgrade to Named Pipe. Log tier change to audit trail (IPC-02 mandatory).
- Token not found on `ReleaseBuffer`: return `BufferNotFound`; UI re-issues `ScrollViewport`.

---

### F-04: Local Storage Management

**Description:** Manage the two-tier SQLite storage system (`hot_dag.db` + `cold_state.db`): WAL anti-bloat via checkpoint, crash-safe schema migrations, and shadow paging hydration.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**[PATCH Issue-04] WAL Auto-Compaction — Checkpoint-First Policy:**

> **BREAKING CHANGE from v0.4.0:** The primary WAL compaction path is now
> `PRAGMA wal_checkpoint(TRUNCATE)`, not `VACUUM INTO`. The previous
> `VACUUM INTO hot_dag_tmp.db` + POSIX rename pattern introduced a concurrent
> Tokio writer race: writers could append `CRDT_Event` entries to `hot_dag.db`
> WAL between the VACUUM completion and the atomic rename, orphaning those
> events in the old WAL. Since `hot_dag.db` is append-only (no deleted rows),
> VACUUM reclaims nothing — CHECKPOINT is the correct primitive.

**User Flow — WAL Auto-Compaction:**

1. Rust Core monitors WAL file size every 60 s via background Tokio task.
2. If WAL > 50 MB (mobile) or > 200 MB (desktop): trigger checkpoint sequence.
3. Execute `PRAGMA wal_checkpoint(TRUNCATE)` — no rename, no exclusive lock, no race.
   - This operation is concurrent-safe: active readers see a consistent snapshot.
   - Writers are not blocked; they continue appending to the WAL during checkpoint.
4. **`VACUUM INTO` is reserved for explicit admin-triggered defragmentation only:**
   - Protected by `BEGIN EXCLUSIVE TRANSACTION`.
   - Not triggered by background monitoring.
   - Documented as a maintenance-only operation.
5. Emit `CoreSignal::StateChanged` after checkpoint completes.

```rust
// Primary compaction path — safe for concurrent Tokio writers
pub async fn compact_hot_dag(db: &SqlitePool) -> Result<()> {
    // TRUNCATE mode: resets WAL to empty, reclaims disk space
    // Safe: no rename, no exclusive lock, no orphaned entries
    sqlx::query("PRAGMA wal_checkpoint(TRUNCATE)")
        .execute(db).await?;
    Ok(())
}

// Admin-only defragmentation — NEVER called by background monitor
pub async fn defragment_hot_dag_admin_only(db: &SqlitePool) -> Result<()> {
    // BEGIN EXCLUSIVE blocks all readers and writers
    sqlx::query("BEGIN EXCLUSIVE TRANSACTION").execute(db).await?;
    sqlx::query("VACUUM INTO 'hot_dag_defrag_tmp.db'").execute(db).await?;
    sqlx::query("COMMIT").execute(db).await?;
    // Atomic rename only after exclusive lock released
    tokio::fs::rename("hot_dag_defrag_tmp.db", "hot_dag.db").await?;
    Ok(())
}
```

**[PATCH Issue-08] Shadow DB Write Lock — TOCTOU Fix:**

> The previous `ShadowMigrationLock { migration_in_progress: AtomicBool }` was
> susceptible to TOCTOU: iOS NSURLSession background completion handlers run on
> arbitrary libdispatch threads, making the check-then-write compound operation
> non-atomic. Replaced with `Mutex<bool>` to ensure mutual exclusion across
> the entire check-and-write sequence.

```rust
// PATCHED: Mutex<bool> replaces AtomicBool for TOCTOU safety
pub struct ShadowMigrationLock {
    migration_in_progress: tokio::sync::Mutex<bool>,
}

impl ShadowMigrationLock {
    /// NSURLSession completion handler MUST call this before writing.
    /// Holds the lock for the entire check+write to prevent TOCTOU.
    pub async fn write_or_queue_to_hot_dag<F, R>(&self, f: F) -> R
    where
        F: FnOnce(WriteTarget) -> R,
    {
        let guard = self.migration_in_progress.lock().await;
        let target = if *guard {
            WriteTarget::HotDag  // migration in progress — redirect
        } else {
            WriteTarget::ShadowDb
        };
        f(target)
        // guard dropped here — lock released
    }
}
```

```swift
// Swift host adapter — os_unfair_lock wraps the FFI call
// ensures no libdispatch thread races the Rust Mutex
private let shadowLock = os_unfair_lock_s()

func handleNSURLSessionCompletion(_ data: Data, _ url: URL) {
    os_unfair_lock_lock(&shadowLock)
    defer { os_unfair_lock_unlock(&shadowLock) }
    tera_core_write_chunk_safe(data.bytes, data.count)  // FFI checks Mutex internally
}
```

**User Flow — Schema Migration:**

1. On DB open: read `PRAGMA user_version` from `hot_dag.db`.
2. If `user_version < CURRENT_SCHEMA_VERSION`:
   - Create backup: `{db_path}.bak.v{current_version}`.
   - `BEGIN EXCLUSIVE TRANSACTION`.
   - Run migration scripts in version order.
   - `PRAGMA user_version = CURRENT_SCHEMA_VERSION`.
   - `COMMIT`.
3. If `cold_state.db` migration fails: drop file, rebuild from `hot_dag.db` (DB-02). Log `COLD_STATE_REBUILD`.

**User Flow — Shadow Paging Hydration:**

1. Core receives `Snapshot_CAS` reference for a new snapshot.
2. Set `ShadowMigrationLock.migration_in_progress = true` (Mutex-protected).
3. Download snapshot in 2 MB chunks to `cold_state_shadow.db`.
4. Verify `SHA-256(downloaded_content) == cas_uuid`. Reject and restart on mismatch.
5. On full verification: atomic `rename(cold_state_shadow.db → cold_state.db)`.
6. Set `ShadowMigrationLock.migration_in_progress = false`.
7. Emit `CoreSignal::StateChanged { table: "all", version }`.
8. If interrupted: delete `cold_state_shadow.db`; `cold_state.db` unchanged. Resume from `Hydration_Checkpoint`.

**Constraints:**

- `hot_dag.db`: append-only. Physical deletion forbidden. Tombstones only.
- **Primary compaction: `PRAGMA wal_checkpoint(TRUNCATE)` only.** `VACUUM INTO` only under `BEGIN EXCLUSIVE` for admin defrag.
- `PRAGMA wal_autocheckpoint = 1000` enforced on all SQLite databases (DB-03).
- `ShadowMigrationLock` uses `tokio::sync::Mutex<bool>`, not `AtomicBool`.

**Failure Handling:** → §10.2 (Storage Failure)

- WAL bloat > 200 MB (mobile): emit `CoreSignal::MemoryPressureWarning`. UI banner shown.
- Checkpoint fails: log error, retry on next trigger. Do not crash.
- Schema migration fails on `cold_state.db`: drop, rebuild. Log `COLD_STATE_REBUILD`.
- Hydration interrupted: delete shadow, restart from `Hydration_Checkpoint`.

---

### F-05: Survival Mesh Networking

**Description:** When Internet is unavailable, TeraChat activates a BLE 5.0 / Wi-Fi Direct peer-to-peer Mesh for offline text messaging via Store-and-Forward. WASM plugins, AI inference, voice calls, and multi-hop file transfer are suspended.

**Supported Platforms:** 📱 iOS (Leaf/EMDP), 📱 Android (Relay), 📱 Huawei (Relay), 💻 macOS (Super Node), 🖥️ Windows (Super Node), 🖥️ Linux (Super Node)

**[PATCH Issue-15] BLE GATT Pre-Authentication Before ML-KEM Key Exchange:**

> A rogue BLE device can accept a GATT connection and participate in the ML-KEM-768 handshake
> before identity is verified, leaking the ephemeral PQ public key and enabling fingerprinting.
> A 1-RTT GATT-level challenge-response now precedes all key material transmission.

**GATT Pre-Auth Protocol (inserted as step 6.5 between peer discovery and key exchange):**

```text
Step 6.0: BLE Stealth Beacon discovery (identity commitment in 31-byte PDU)
Step 6.5: [NEW] GATT Pre-Authentication:
  a. Connecting peer sends Challenge:
     { slot_rotation_counter: u64, nonce: [u8; 32] }  ← derived from current beacon slot
  b. Responding peer signs with DeviceIdentityKey (Ed25519):
     Proof = Ed25519Sign(DeviceIdentityKey, Challenge || nonce)
  c. Connecting peer verifies Proof against the identity_commitment in the beacon.
  d. Only on successful verification → proceed to ML-KEM key exchange.
  e. GATT connection CLOSED immediately on verification failure.
Step 7.0: ML-KEM-768 + X25519 Hybrid Handshake (only authenticated peers)
```

```rust
// Rust Core GATT pre-auth before key exchange
async fn authenticate_gatt_peer(
    peer_beacon: &BleStealthBeacon,
    gatt_conn: &mut GattConnection,
) -> Result<AuthenticatedPeer, MeshAuthError> {
    let nonce = ring::rand::generate::<[u8; 32]>()?;
    let challenge = GattChallenge {
        slot_rotation_counter: peer_beacon.slot_counter,
        nonce,
    };
    gatt_conn.send(&challenge.encode()).await?;
    
    let proof: GattProof = gatt_conn.recv_timeout(Duration::from_millis(500)).await?;
    
    // Verify against identity_commitment from beacon: HMAC(R, PK_identity)[0:8]
    let expected_pk = peer_beacon.identity_commitment.recover_pubkey()?;
    ed25519_verify(&expected_pk, &challenge.encode(), &proof.signature)?;
    
    Ok(AuthenticatedPeer { peer_id: proof.device_id, pubkey: expected_pk })
}
```

**[PATCH Issue-05] EMDP Key Escrow — Proactive Broadcast & Sudden Desktop Loss:**

> The previous spec required Desktop to transmit `EmdpKeyEscrow` only when going offline.
> In practice, Desktops go offline abruptly (power failure, kernel panic, hard network partition)
> before escrow is transmitted. This leaves the EMDP window of messages permanently unrecoverable.

**Corrected EMDP Key Escrow Protocol:**

```rust
pub struct EmdpKeyEscrow {
    relay_session_key: AesKey256,
    emdp_start_epoch: u64,
    emdp_expires_at: u64,     // now() + 3600
    escrow_generation: u32,   // monotonically increasing; iOS stores latest
}

// Desktop: proactive broadcast on EMDP ACTIVATION (not only on graceful shutdown)
async fn activate_emdp_mode(ios_relay_pubkey: &Curve25519PublicKey) {
    let escrow = EmdpKeyEscrow::new();
    let encrypted = ecies_encrypt(ios_relay_pubkey, &escrow.encode());
    ble_control_plane_send(BleMsg::EmdpKeyEscrow(encrypted)).await;
    
    // Re-broadcast every 5 minutes while EMDP is active
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(Duration::from_secs(300));
        loop {
            interval.tick().await;
            if emdp_state.is_active() {
                ble_control_plane_send(BleMsg::EmdpKeyEscrow(encrypted.clone())).await;
            } else {
                break;
            }
        }
    });
}
```

**Sudden Desktop Loss (Failure Case):**

If the Desktop goes offline before the first escrow broadcast (power failure within the first 30
seconds of EMDP activation), the iOS Tactical Relay enters `CAUSAL_FREEZE`:

```text
Sudden Desktop Loss Before Escrow:
  iOS detects Desktop gone + no EmdpKeyEscrow received
      ↓
  Enter CAUSAL_FREEZE: append-only, no new EMDP relay session started
  UI: "Secure relay key unavailable — messages held locally"
      ↓
  Desktop reconnects:
    if tainted_escrow == true → full MLS Epoch rotation BEFORE DAG merge
    Desktop regenerates session key, transmits fresh EmdpKeyEscrow
    DAG merge proceeds with new epoch context
    tainted_escrow = false
```

```rust
pub struct EmdpState {
    tainted_escrow: bool,  // true if Desktop disconnected before first escrow
    causal_freeze: bool,   // true when no valid escrow available
}

// On Desktop reconnect
fn handle_desktop_reconnect(emdp: &mut EmdpState, dag: &mut DagEngine) {
    if emdp.tainted_escrow {
        // Must rotate epoch BEFORE merging orphaned messages
        dag.trigger_mls_epoch_rotation_mandatory().await;
        emdp.tainted_escrow = false;
    }
    emdp.causal_freeze = false;
    dag.merge_emdp_window_messages().await;
}
```

**User Flow — Activation:**

1. Rust Core detects all three ALPN paths unavailable.
2. Core emits `CoreSignal::TierChanged { new_tier: MeshMode, reason: NoInternet }`.
3. UI transitions to Mesh Mode visual state.
4. User confirms Mesh activation (required: OS BLE permission prompt).
5. Core calls host adapter FFI: `request_mesh_activation()`.
6. Devices within range discover each other via BLE Stealth Beacons.
7. **[PATCH 15]** GATT Pre-Auth challenge-response before any key material exchange.
8. Text messages route via BLE Store-and-Forward (payload ≤ 4 KB per hop).

**Role Assignment:**

```rust
fn assign_role(device: &DeviceInfo) -> MeshRole {
    match device.os_type {
        OsType::iOS => MeshRole::LeafNode,  // always; election_weight = 0
        OsType::MacOS | OsType::Windows | OsType::Linux
            if device.power_source == PowerSource::AC =>
            MeshRole::SuperNode,
        OsType::Android
            if device.available_ram_mb >= 3_072 && device.battery_pct >= 40 =>
            MeshRole::RelayNode,
        _ => MeshRole::LeafNode,
    }
}
```

**Store-and-Forward Quotas:**

| Role | Storage Quota | Message TTL |
|---|---|---|
| Super Node (Desktop) | 500 MB – 1 GB | 48 – 72 h |
| Relay Node (Android) | 100 MB | 24 h |
| Leaf Node (iOS) | 50 MB, receive-only | N/A |
| Tactical Relay (EMDP iOS) | 1 MB, text-only CRDT buffer | 60 min |

**EMDP (Emergency Mobile Dictator Protocol) — Full Protocol:**

- Activation: no Desktop present; Internet unavailable; ≥ 2 iOS devices; battery > 20%.
- Tactical Relay selected by: `max(battery_pct × 100 + (ble_rssi + 100))`.
- **[PATCH 05]** Escrow transmitted proactively on activation + re-broadcast every 5 minutes.
- Hard constraints: text-only, 1 MB buffer, TTL 60 min, no DAG merge, no MLS Epoch rotation.
- TTL extension (at T-10 min): broadcast `EMDP_TTL_EXTENSION_REQUEST`; peer with battery > 30% accepts.
- Sudden Desktop loss before escrow → `CAUSAL_FREEZE`; mandatory epoch rotation on reconnect.

**Observability:**

- Signal: `CoreSignal::TierChanged { new_tier, reason }` on every Mesh activation or ALPN change.
- Signal: `CoreSignal::MeshRoleChanged { new_role }` on role transition.
- Signal: `CoreSignal::EmdpExpiryWarning { minutes_remaining }` at T-10 min and T-2 min.
- Signal: `CoreSignal::EmdpCausalFreeze` when sudden Desktop loss before escrow.

**Failure Handling:** → §10.1 (Network Failure)

- All-iOS Mesh, no EMDP conditions: Causal Freeze (read-only). No DAG writes until non-iOS node joins.
- EMDP TTL expired, no hand-off found: enter SoloAppendOnly mode. Merge deferred.
- Sudden Desktop loss before first escrow: enter `CAUSAL_FREEZE`; mandatory epoch rotation on reconnect.

---

### F-06: Voice and Video Calls (WebRTC)

**Description:** Peer-to-peer encrypted voice and video calls via WebRTC DTLS-SRTP. SDP signaling over MLS E2EE channel. TURN relay is blind.

**Supported Platforms:** 📱 iOS (CallKit required), 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-07: WASM Plugin Sandbox (`.tapp` Lifecycle)

**Description:** Execute untrusted third-party mini-apps inside a WASM sandbox with capability-based isolation.

**Supported Platforms:** 📱 iOS (`wasm3`), 📱 Android (`wasmtime`), 📱 Huawei (`wasmtime`), 💻 macOS (`wasmtime` in XPC Worker), 🖥️ Windows (`wasmtime`), 🖥️ Linux (`wasmtime`)

**[PATCH Issue-06] WasmParity CI Gate — Sprint 1 Blocker:**

> **STATUS CHANGE: "Not implemented" → Sprint 1 Blocker.**
> The WasmParity gate must be operational before ANY `.tapp` Marketplace listing.
> Key behavioral divergences between wasm3 (iOS) and wasmtime (Desktop):
>
> - NaN canonicalization: wasm3 propagates NaN payloads differently from Cranelift
>   `--enable-nan-canonicalization`. Any `.tapp` using floats for scoring or routing
>   produces different outputs on iOS vs Android silently.
> - Linear memory growth failure semantics differ between engines.
> - Per-call latency on wasm3 is 15–20 ms higher; timing-sensitive token bucket logic
>   (50 req/s limit) may spuriously hit circuit breaker on iOS wasm3.

```toml
# Cargo.toml — wasm3 as dev-dependency for CI WasmParity gate
[dev-dependencies]
wasm3 = { version = "0.4", features = ["build-lib"] }  # interpreter for CI parity testing
wasmtime = { version = "18" }

[features]
nse-only = ["terachat-crypto-minimal"]  # NSE build strips ONNX/CRDT/SQLCipher
```

```rust
// tests/wasm_parity.rs — Sprint 1 mandatory gate
#[test]
fn wasm_parity_integer_arithmetic() {
    // Use INTEGER test vectors ONLY — no f32/f64 in initial gate
    // Float vectors added after NaN canonicalization is verified per-engine
    let wasm_bytes = include_bytes!("fixtures/test_plugin.wasm");
    let input = b"\x01\x02\x03\x04";  // deterministic integer input

    let wasm3_out = run_wasm3(wasm_bytes, "test_fn", input);
    let wasmtime_out = run_wasmtime(wasm_bytes, "test_fn", input);

    assert_eq!(wasm3_out, wasmtime_out,
        "WasmParity FAILED: wasm3 vs wasmtime output divergence detected");
}

#[test]
fn wasm_parity_nan_canonicalization() {
    // Verify NaN bit pattern is identical across both runtimes after canonicalization
    let wasm_bytes = include_bytes!("fixtures/test_nan_plugin.wasm");
    let wasm3_out = run_wasm3(wasm_bytes, "nan_test", b"");
    let wasmtime_out = run_wasmtime_with_nan_canon(wasm_bytes, "nan_test", b"");
    assert_eq!(wasm3_out, wasmtime_out, "NaN canonicalization divergence");
}

#[test]
fn wasm_parity_latency_delta() {
    // latency delta must be ≤ 20 ms
    let delta = measure_call_latency_delta_ms();
    assert!(delta <= 20.0, "WasmParity latency delta {} ms exceeds 20 ms ceiling", delta);
}

#[test]
fn wasm_parity_memory_delta() {
    let wasm3_mem = measure_peak_heap_wasm3();
    let wasmtime_mem = measure_peak_heap_wasmtime();
    let delta_mb = (wasm3_mem as i64 - wasmtime_mem as i64).unsigned_abs() / (1024 * 1024);
    assert!(delta_mb <= 5, "WasmParity memory delta {} MB exceeds 5 MB ceiling", delta_mb);
}
```

**[PATCH Issue-07] XPC Transaction Journal — WAL Durability Before PENDING Write:**

> The previous spec wrote `XpcJournalEntry { status: PENDING }` to `hot_dag.db` without
> ensuring WAL durability. Since `wal_autocheckpoint = 1000` flushes only every 1000 pages,
> a SIGKILL during XPC crash could leave the PENDING record un-checkpointed, causing
> silent transaction loss (no user prompt, no `ComponentFault`).

**Fix:** The `XpcJournalEntry` is written using a **dedicated SQLite connection with
`PRAGMA synchronous = FULL`**, guaranteeing fsync before `tera_buf_release` dispatches
to the XPC Worker:

```rust
// hot_dag.db has a second connection for XPC journal — synchronous = FULL
pub async fn write_xpc_pending(
    journal_db: &SqliteConnection,  // synchronous = FULL connection
    tx_id: Uuid,
    payload_hash: [u8; 32],
) -> Result<()> {
    // This fsync ensures PENDING is durable before XPC dispatch
    sqlx::query!(
        "INSERT INTO xpc_journal (tx_id, status, payload_hash) VALUES ($1, 'PENDING', $2)",
        tx_id.to_string(),
        &payload_hash[..],
    )
    .execute(journal_db)  // synchronous=FULL — blocks until fsync completes
    .await?;
    
    // Only AFTER durable PENDING write → dispatch to XPC Worker
    dispatch_to_xpc_worker(tx_id).await
}

// Connection setup
pub fn open_xpc_journal_connection(path: &Path) -> Result<SqliteConnection> {
    let conn = SqliteConnectOptions::new()
        .filename(path)
        .journal_mode(SqliteJournalMode::Wal)
        .synchronous(SqliteSynchronous::Full)  // <-- key: fsync on every write
        .connect()
        .await?;
    Ok(conn)
}
```

**XPC Worker Crash Recovery (corrected):**

```rust
// With durable PENDING: recovery is reliable on all crash scenarios
PENDING   → durable in journal → abort + emit CoreSignal::ComponentFault
            → notify user: "Session interrupted. Please re-sign."
VERIFIED  → idempotent commit from journal (crash-safe; no user action)
COMMITTED → noop (already complete)
```

Retry policy: max 3 attempts, backoff 0 s → 2 s → 8 s. After 3rd failure:
emit `CoreSignal::ComponentFault { severity: Critical }` + `XpcPermanentFailure { support_id: Uuid }`.

**`.tapp` Bundle Format:**

```text
bundle.tapp/
├── logic.wasm          # WASM bytecode (stripped: no wasi-sockets, wasi:io, wasi:filesystem)
├── manifest.json       # publisher_public_key, egress_endpoints, permissions, version_hash (BLAKE3)
├── assets/             # static assets
└── signature.ed25519   # Ed25519 by Publisher Key (Merkle Registry)
```

**Launch Sequence:**

1. Admin installs `.tapp` from Marketplace. Signature verified against Publisher Key.
2. `manifest.json` validated: all required fields present; `egress_endpoints` declared.
3. Platform WASM runtime initialized (wasm3/iOS, wasmtime/others).
4. **[PATCH 06]** WasmParity gate must have passed CI for this `.tapp` version.
5. Sandbox launched: `PROT_READ`-only DAG access.

**Observability:**

- Signal: `CoreSignal::ComponentFault { component, severity }` on sandbox panic or XPC crash.
- Metric: `wasm_sandbox_crashes` (OBSERVE-01).

---

### F-08: Inter-`.tapp` IPC and Delegation Tokens

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-09: Media and File Transfer

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-10: AI / SLM Integration

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-11: Device Security

**Description:** Client-side security controls: screen capture prevention, Protected Clipboard Bridge, biometric screen lock, Remote Wipe, and cryptographic self-destruct.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

#### F-11a: Screen Capture Prevention

| Platform | API | Mechanism |
|---|---|---|
| 📱 iOS | `UIScreen.capturedDidChangeNotification` | Blur overlay on capture |
| 📱 Android | `FLAG_SECURE` in `Activity.onCreate()` | Kernel Compositor blocks capture |
| 💻 macOS | `CGDisplayStream` monitoring | Blur overlay within 1 frame |
| 🖥️ Windows | DXGI duplication detection | Blur overlay |
| 🖥️ Linux | Wayland compositor security hint | Platform best-effort |

#### F-11b: Protected Clipboard Bridge

All clipboard operations route through Rust Core's bridge. Direct OS clipboard API calls: **blocker** (SEC-03).

#### F-11c: Biometric Screen Lock

- All SQLite I/O blocked until biometric gate clears.
- PIN fallback: 6 digits. Transmitted via FFI Pointer — never through UI state buffer.
- Maximum PIN failures: 5. On 5th: Cryptographic Self-Destruct.

**[PATCH Issue-13] Dead Man Switch Deferral — Mandatory Audit Trail:**

> For regulated enterprise and Gov/Military customers, a Dead Man Switch deferral
> (due to active CallKit session) must be auditable. Without a `DeadManDeferralEntry`,
> an insider threat actor could initiate a call to indefinitely defer the Dead Man Switch
> with no auditable trace.

```rust
/// Written to tamper-proof Audit Log BEFORE deferral takes effect — not after.
pub struct DeadManDeferralEntry {
    device_id: DeviceId,
    timestamp_hlc: HlcTimestamp,
    reason: DeferralReason,          // CallKitSessionActive | AdminOverride
    server_counter_at_deferral: u64, // TPM Monotonic Counter from server
    device_counter_at_deferral: u64, // local TPM Monotonic Counter
    counter_delta: i64,              // server_counter - device_counter: shows max unsync window
    session_id: Option<CallKitSessionId>,
    ed25519_sig: Ed25519Signature,   // signed by DeviceIdentityKey
}

// Dead Man Switch deferral — audit BEFORE deferral, then defer
async fn defer_dead_man_switch(reason: DeferralReason, call_session: Option<CallKitSessionId>) {
    let entry = DeadManDeferralEntry {
        device_id: self.device_id.clone(),
        timestamp_hlc: HlcClock::now(),
        reason,
        server_counter_at_deferral: fetch_server_monotonic_counter().await,
        device_counter_at_deferral: tpm_read_counter(),
        counter_delta: server_counter - device_counter,
        session_id: call_session,
        ed25519_sig: secure_enclave_sign(&entry_bytes),
    };
    
    // Write to Ed25519-signed Audit Log BEFORE taking any deferral action
    audit_log_append(AuditEvent::DeadManSwitchDeferred(entry)).await?;
    
    // Deferral takes effect only after audit is durable
    apply_dead_man_switch_deferral().await;
}
```

**Constraint:** `counter_delta` in the `DeadManDeferralEntry` is visible to the CISO in the
Audit Log viewer, enabling determination of the maximum window during which the device was
unsynchronized with the server's monotonic counter.

#### F-11d: Remote Wipe

Trigger: `self.userID` in `removedMembers` of any MLS Commit. Non-interruptible sequence.

#### F-11e: Cryptographic Self-Destruct

- `Failed_PIN_Attempts` counter encrypted with `Device_Key`. Ceiling: 5.
- On 5th failure: Crypto-Shredding of all local DBs + `OIDC_ID_Token` → Factory Reset.

**State Machine:** → §5.6 (Device PIN Failure State Machine)

---

### F-12: Identity, Onboarding, and Recovery

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### F-13: Admin Console and Enterprise Controls

**Description:** Centralized management interface for workspace administrators.

**Supported Platforms (full access):** 💻 macOS, 🖥️ Windows, 🖥️ Linux, 🗄️ Bare-metal
**Supported Platforms (read-only):** 📱 iOS, 📱 Android, 📱 Huawei

**[PATCH Issue-14] Federation OPA Policy — Schema Version Exemption:**

> OPA Policy bundle distribution was incorrectly gated on schema version compatibility.
> A Branch cluster on schema version N-1 could not receive critical security policies
> (CRL updates, permission revocations, user offboarding) from HQ until it upgraded.
> In Gov/enterprise environments with gated schema upgrades, this could mean a revoked
> user remains in the OPA policy for weeks.

**Corrected Federation Endpoint Routing:**

| Endpoint | Schema Version Gate | Description |
|---|---|---|
| `/federation/data` | ✅ Enforced (±1 minor = read-only; ±1 major = SCHEMA_INCOMPATIBLE) | Data sync, message routing |
| `/federation/policy` | ❌ **Exempt** from schema version check | OPA policy bundles (CRL, revocation, permissions) |

Both endpoints require mTLS. Only `/federation/data` is version-gated.

```rust
// Federation router — policy channel is version-agnostic
async fn route_federation_request(req: FederationRequest) -> Result<Response> {
    match req.endpoint {
        FederationEndpoint::Policy => {
            // Always accept policy updates regardless of schema version
            verify_mtls_and_ca_signature(&req)?;
            apply_opa_policy_bundle(req.payload).await
        }
        FederationEndpoint::Data => {
            // Schema version check enforced for data sync
            verify_schema_compatibility(req.sender_schema_version)?;
            route_data_sync(req).await
        }
    }
}
```

**Admin Console Feature Set:**

| Feature | Description | Access Level |
|---|---|---|
| Device enrollment management | Issue / revoke mTLS certificates | Admin: full |
| User offboarding (SCIM 2.0) | Auto-remove from MLS groups on HR event | Server: auto |
| OPA Policy management | Define and push ABAC policies to devices | Admin: full |
| Remote Wipe | Initiate `removedMembers` MLS Commit | Admin: full |
| Audit Log viewer | Ed25519-signed tamper-proof entries (incl. DeadManDeferral) | Admin: read-only |
| License management | View / renew License JWT; seat count | Admin: full |
| Federation management | Invite / revoke federated clusters; policy channel exempt from schema gate | Admin: full |

---

### F-14: Adaptive Network and Protocol Management

**Description:** Automatic network protocol selection (ALPN), adaptive QUIC probe learning, and graceful fallback.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**ALPN Negotiation Sequence (total < 50 ms):**

```text
Step 1: QUIC / HTTP/3 over UDP:443
        ACK within 50 ms → ONLINE_QUIC (0-RTT, ~30 ms RTT)
        No ACK / firewall DROP → Step 2

Step 2: gRPC / HTTP/2 over TCP:443
        TLS handshake success → ONLINE_GRPC (~80 ms RTT)
        DPI blocks binary framing → Step 3

Step 3: WebSocket Secure over TCP:443
        WS Upgrade success → ONLINE_WSS (~120 ms RTT)
        All three fail → MESH_MODE
```

**[PATCH Issue-03] Adaptive QUIC Probe Learning — Race Fix:**

> **CRITICAL BUG (v0.4.0):** The previous `on_probe_failure` implementation incremented
> `probe_fail_count` for ALL parallel probes that did not win the `tokio::select!` race,
> including gRPC when QUIC succeeded first. Over 3 such races on the same `NetworkProfile`,
> `strict_compliance` was permanently set to true on networks where QUIC works correctly,
> silently adding 50 ms to every connection.

**Corrected implementation — `probe_fail_count` increments only for the protocol that
did not win, and resets to 0 when QUIC wins:**

```rust
/// Corrected adaptive ALPN negotiation — only the LOSER increments fail count.
/// The WINNER resets probe_fail_count to 0 for its protocol.
pub async fn negotiate_alpn_adaptive(
    cert_fp: &[u8],
    ssid_hash: &[u8],
    db: &SqliteConn,
) -> AlpnResult {
    let mut profile = db.get_or_create_network_profile(
        &blake3::hash(&[cert_fp, ssid_hash].concat())
    );

    // Respect established strict_compliance
    if profile.strict_compliance {
        return try_grpc_direct(cert_fp).await;
    }

    // Parallel race — winner determined by first to resolve
    let result = tokio::select! {
        r = try_quic(cert_fp) => Either::Left(r),
        r = try_grpc(cert_fp) => Either::Right(r),
    };

    match result {
        Either::Left(Ok(quic_conn)) => {
            // QUIC won: reset its fail count (no penalty for parallel gRPC attempt)
            profile.quic_probe_fail_count = 0;
            db.save_network_profile(&profile);
            AlpnResult::Quic(quic_conn)
        }
        Either::Left(Err(_)) => {
            // QUIC failed: increment only QUIC's fail count
            profile.quic_probe_fail_count += 1;
            if profile.quic_probe_fail_count >= 3 {
                profile.strict_compliance = true;
                emit_admin_notification("Auto-switched to TCP on this network.");
            }
            db.save_network_profile(&profile);
            // Fall through to gRPC
            try_grpc_or_wss(cert_fp).await
        }
        Either::Right(Ok(grpc_conn)) => {
            // gRPC won race (QUIC timed out): only QUIC fails, gRPC has no penalty
            profile.quic_probe_fail_count += 1;
            db.save_network_profile(&profile);
            AlpnResult::Grpc(grpc_conn)
        }
        Either::Right(Err(_)) => {
            profile.quic_probe_fail_count += 1;
            db.save_network_profile(&profile);
            try_wss_or_mesh(cert_fp).await
        }
    }
}

fn on_network_change(new_cert_fp: &[u8], ssid_hash: &[u8], db: &SqliteConn) {
    let network_id = blake3::hash(&[new_cert_fp, ssid_hash].concat());
    // Reset ALL fail counts on network change
    db.reset_network_profile(network_id.as_bytes());
}
```

**Observability:**

- Signal: `CoreSignal::TierChanged { new_tier, reason }` on every ALPN change.
- Metric: `alpn_fallback_count` (OBSERVE-01).
- Admin notification: auto-emitted when probe learning triggers Strict Compliance.

---

### F-15: Crash-Safe Memory and WAL Management

**Description:** Platform-specific memory protection and crash-safe WAL flush protocols.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**[PATCH Issue-10] Linux AppArmor/SELinux — Full Postinstall Specification:**

> **STATUS CHANGE: "Not implemented" → Required for Sprint 1 Linux deployment.**
> Without the MAC profile, startup crashes on `memfd_create` and `ipc_lock` on all
> enforcing systems (Ubuntu 22.04+ AppArmor enforcing by default; RHEL 8+ SELinux enforcing).

**AppArmor Profile (`/etc/apparmor.d/usr.bin.terachat`):**

```apparmor
#include <tunables/global>

/usr/bin/terachat {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  # Core binary
  /usr/bin/terachat mr,
  /usr/lib/terachat/** mr,
  /usr/share/terachat/** r,

  # Data directories
  owner @{HOME}/.local/share/terachat/** rwkl,
  owner @{HOME}/.config/terachat/** rwkl,
  /tmp/terachat-* rwkl,

  # memfd_create for SharedArrayBuffer (Tauri IPC Data Plane)
  capability sys_admin,       # NOT needed — memfd_create uses memfd capability
  @{PROC}/*/fd/ r,
  @{PROC}/*/mem r,
  # memfd: allowed via kernel path — no explicit AppArmor rule needed in 5.x+

  # ipc_lock for mlock equivalent key protection
  capability ipc_lock,

  # BLE socket access
  /sys/class/bluetooth/ r,
  /sys/bus/usb/devices/ r,
  network bluetooth,
  network inet stream,
  network inet6 stream,
  network inet dgram,

  # ptrace for self-debugging (crash reporter)
  ptrace peer=(comm=terachat),

  # Deny dangerous capabilities
  deny capability net_admin,
  deny capability sys_rawio,
  deny @{PROC}/sysrq-trigger w,
}

/usr/bin/terachat-daemon {
  #include <abstractions/base>
  /usr/bin/terachat-daemon mr,
  owner @{HOME}/.local/share/terachat/** rwkl,
  capability ipc_lock,
  network inet stream,
  network inet6 stream,
  network inet dgram,
  network bluetooth,
}
```

**SELinux Policy Module (`/usr/share/terachat/terachat.te`):**

```te
module terachat 1.0;

require {
    type user_home_t;
    type tmp_t;
    type bluetooth_t;
    type init_t;
    class file { read write create unlink rename lock };
    class sock_file { read write create };
    class capability { ipc_lock };
    class process { execmem };  # required for wasmtime JIT
}

# TeraChat domain
type terachat_t;
type terachat_exec_t;
init_daemon_domain(terachat_t, terachat_exec_t)

# File access
allow terachat_t user_home_t:file { read write create unlink rename lock };
allow terachat_t tmp_t:file { read write create unlink };

# ipc_lock for key material protection
allow terachat_t self:capability { ipc_lock };

# wasmtime JIT requires execmem (mapped writable+executable pages)
allow terachat_t self:process { execmem };

# BLE access
allow terachat_t bluetooth_t:sock_file { read write };
```

**Pre-compiled `.pp` bundles shipped for:**

- RHEL 8 / CentOS Stream 8 (`terachat-rhel8.pp`)
- RHEL 9 / CentOS Stream 9 / AlmaLinux 9 (`terachat-rhel9.pp`)
- Fedora 38+ (`terachat-fedora38.pp`)

**Postinstall Script (`/usr/share/terachat/postinstall.sh`):**

```bash
#!/bin/bash
set -euo pipefail
LOG=/var/log/terachat-install.log

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

# AppArmor
if command -v apparmor_parser &>/dev/null; then
    log "Loading AppArmor profiles..."
    apparmor_parser -r -W /etc/apparmor.d/usr.bin.terachat 2>>"$LOG" || \
        log "WARNING: AppArmor profile load failed — manual load required"
    apparmor_parser -r -W /etc/apparmor.d/terachat-daemon 2>>"$LOG" || \
        log "WARNING: AppArmor daemon profile load failed"
fi

# SELinux
if command -v semodule &>/dev/null; then
    # Detect RHEL/Fedora version for correct .pp selection
    if grep -q "release 9" /etc/redhat-release 2>/dev/null; then
        PP=/usr/share/terachat/terachat-rhel9.pp
    elif grep -q "release 8" /etc/redhat-release 2>/dev/null; then
        PP=/usr/share/terachat/terachat-rhel8.pp
    else
        PP=/usr/share/terachat/terachat-fedora38.pp
    fi
    log "Loading SELinux module: $PP"
    semodule -i "$PP" 2>>"$LOG" || \
        log "WARNING: SELinux module load failed — manual installation required: semodule -i $PP"
fi

# Self-test: verify permissions are correct before starting daemon
log "Running permission self-test..."
if /usr/bin/terachat --check-permissions; then
    log "Permission self-test PASSED"
else
    log "WARNING: Permission self-test FAILED — check $LOG for details"
    echo "NOTICE: TeraChat installed but MAC profile may not be active."
    echo "        Run: /usr/bin/terachat --check-permissions"
    echo "        See: $LOG"
    # Do NOT abort installation — warn only
fi
```

**`terachat --check-permissions` Binary Subcommand:**

```rust
// Binary subcommand — formal exit code 0/1 with human-readable output
pub fn check_permissions() -> ExitCode {
    let mut all_ok = true;

    // Test memfd_create
    match nix::sys::memfd::memfd_create(c"terachat_test", MemFdCreateFlag::MFD_CLOEXEC) {
        Ok(fd) => { println!("✅ memfd_create: OK"); nix::unistd::close(fd).ok(); }
        Err(e) => { eprintln!("❌ memfd_create: FAILED ({e}) — AppArmor/SELinux may be blocking"); all_ok = false; }
    }

    // Test ipc_lock (mlock on small buffer)
    match try_mlock_test_page() {
        Ok(_) => println!("✅ ipc_lock (mlock): OK"),
        Err(e) => { eprintln!("❌ ipc_lock: FAILED ({e}) — capability ipc_lock may be denied"); all_ok = false; }
    }

    // Test BLE socket
    match test_bluetooth_socket() {
        Ok(_) => println!("✅ BLE socket: OK"),
        Err(e) => { eprintln!("⚠️  BLE socket: UNAVAILABLE ({e}) — Mesh mode will not work"); }
        // BLE unavailable is a warning, not a failure — non-Mesh deployments are valid
    }

    if all_ok {
        println!("\nAll required permissions available. TeraChat is ready.");
        ExitCode::SUCCESS
    } else {
        eprintln!("\nSome permissions are missing. See /var/log/terachat-install.log");
        ExitCode::FAILURE
    }
}
```

**Linux Multi-Init Daemon Support (postinstall):**

```bash
if command -v systemctl &>/dev/null && systemctl --version &>/dev/null 2>&1; then
    systemctl enable --now terachat-daemon.service
elif command -v rc-service &>/dev/null; then
    rc-update add terachat-daemon default && rc-service terachat-daemon start
elif command -v runit &>/dev/null; then
    ln -sf /etc/sv/terachat-daemon /var/service/
else
    install -m644 /usr/share/applications/terachat-daemon.desktop \
        ~/.config/autostart/terachat-daemon.desktop
fi
```

**iOS / Android Crash-Safe Checkpoint:**

```swift
NotificationCenter.default.addObserver(
    forName: UIApplication.willTerminateNotification,
    using: { _ in tera_core_flush_io() }  // FFI; ≤ 50 ms
)
```

**Constraints:**

- `tera_core_flush_io()` must complete in ≤ 50 ms on mobile.
- Desktop: 35 s total (30 s checkpoint + 5 s systemd margin). Exit unconditionally after 30 s.
- `PRAGMA wal_autocheckpoint = 1000` enforced on all databases at connection open.
- Linux deployment on AppArmor/SELinux enforcing systems requires the postinstall script.

---

### INFRA-01 through INFRA-06, OBSERVE-01/02

*(No patches in this version. Content unchanged from v0.4.0.)*

---

### CICD-01: CI/CD Pipeline Requirements

> All gates below must pass before merge to `main`. Any failure = **BLOCKER**.

**Security Gates:**

| Gate | Command | Blocker |
|---|---|---|
| FFI-01: No raw pointer in `pub extern C` | `cargo clippy -- -D tera_ffi_raw_pointer` | Yes |
| KEY-02: ZeroizeOnDrop verification | `cargo miri test --test zeroize_verification` | Yes |
| Dependency audit (RUSTSEC) | `cargo audit --deny warnings` | Yes |
| Trivy container scan (CRITICAL CVE) | `trivy image --exit-code 1 --severity CRITICAL` | Yes |
| Secret scan (GitLeaks) | `gitleaks detect --source . --exit-code 1` | Yes |
| **[PATCH 12] GC Finalizer release count = 0** | `cargo test -- --test-output immediate ffi_gc_finalizer` | **Yes** |

**[PATCH Issue-06, Issue-01] WasmParity + Dart FFI Correctness Gates — Sprint 1 Blockers:**

| Gate | Command | Blocker | Sprint |
|---|---|---|---|
| WasmParity (integer vectors, latency, memory) | `cargo test --test wasm_parity -- --timeout 60` | **Yes** | **Sprint 1** |
| WasmParity NaN canonicalization | `cargo test --test wasm_parity_nan -- --timeout 60` | **Yes** | **Sprint 1** |
| Dart FFI GC finalizer count = 0 | `flutter test --tags ffi_gc_audit` | **Yes** | **Sprint 1** |
| Dart FFI `useInTransaction` lint (tera_require_secure_buffer) | `dart analyze --fatal-infos` | **Yes** | **Sprint 1** |

**Correctness Gates:**

| Gate | Command | Blocker |
|---|---|---|
| Unit tests (all platforms) | `cargo nextest run --all-features` | Yes |
| WasmParity CI gate (wasm3 vs wasmtime, delta ≤ 20 ms, memory ≤ 5 MB) | see above | **Yes — Sprint 1** |
| Inbound dedup contract (CRDT) | `cargo test --test crdt_dedup_contract` | Yes |
| **[PATCH 03] ALPN probe race regression** | `cargo test --test alpn_probe_race` | **Yes** |
| **[PATCH 08] Shadow DB TOCTOU** | `cargo test --test shadow_db_concurrent` | **Yes** |
| MLS epoch rotation SLA (≤ 1 s for 100 members) | `cargo bench --bench mls_epoch_rotation` | No (regression tracked) |

**Build & Signing Gates:**

| Gate | Command | Blocker | Platform |
|---|---|---|---|
| Reproducible build verification | `ops/verify-reproducible-build.sh` | Yes | All |
| SBOM generation and signing | `ops/generate-sbom.sh && cosign sign-blob …` | Yes | All |
| **[PATCH 10] Linux AppArmor self-test** | `/usr/bin/terachat --check-permissions` | **Yes** | Linux |
| Windows EV Code Signing | `signtool verify /pa terachat-setup.exe` | Yes | Windows |
| Linux GPG signature on .deb/.rpm | `dpkg-sig --verify terachat_*.deb` | Yes | Linux |

---

### PLATFORM-17: Dart FFI Memory Contract

> **Supersedes PLATFORM-14.** Mandatory — violations = CI fail (blocker).
> Applies to: Android, Huawei (Dart FFI path).
> **[PATCH Issue-01] Updated for double-release race fix.**

**[PATCH Issue-01] Four Mandatory Rules (Updated):**

- **Rule 1:** Every `TeraSecureBuffer` MUST be wrapped by `useInTransaction()`. Direct `.toPointer()` outside wrapper → CI lint error (blocker).
- **Rule 2:** Rust Token Registry does NOT auto-expire/zeroize. On TTL timeout → emit `IpcSignal::TransactionTimeout`.
- **Rule 3:** GC Finalizer is safety net only. **GC release → CI BLOCKER metric (not just warning).** Any `ffi.gc_finalizer_release.count > 0` in CI test run fails the build.
- **Rule 4:** Explicit `releaseNow()` is primary release path. `useInTransaction()` calls it in `finally` automatically.
- **Rule 5 [NEW]:** The Rust Token Registry uses a **monotonic generation counter** per token. Stale tokens (from GC finalizer double-release) are rejected by comparing the token's embedded generation with the registry's current generation. Double-release is a no-op after the first release.

**[PATCH Issue-01] Dart FFI `TeraSecureBuffer` Wrapper — Race-Safe:**

```dart
class TeraSecureBuffer {
  final int _token;
  // PATCHED: Use Dart Isolate-compatible atomic flag
  // Dart isolates are single-threaded, but finalizers run asynchronously.
  // _released is accessed only from the main isolate; finalize() runs in
  // a separate finalizer isolate. We use a Completer to synchronize.
  bool _released = false;
  final _releaseLock = Mutex();  // package:mutex for isolate-safe locking

  static Future<TeraSecureBuffer> acquire(int operationId) async {
    final token = await _teraFfi.tera_buf_acquire(operationId);
    if (token == 0) throw const TeraBufferError('acquire failed — token=0');
    return TeraSecureBuffer._(token);
  }

  /// Primary release path — must be called explicitly.
  Future<void> releaseNow() async {
    await _releaseLock.acquire();
    try {
      if (_released) return;  // idempotent: second call is no-op
      _teraFfi.tera_buf_release(_token);  // Rust registry checks generation counter
      _released = true;
    } finally {
      _releaseLock.release();
    }
  }

  /// Safety net ONLY — should never be the primary release path.
  /// GC finalizer fires in a separate Dart isolate: acquires lock before checking.
  @override
  void finalize() {
    if (!_released) {
      // CI BLOCKER: increment metric — this path must not be reached in production
      MetricsCollector.increment('ffi.gc_finalizer_release.count');
      _logger.error(
        'BLOCKER: TeraSecureBuffer token=$_token released by GC finalizer. '
        'Missing explicit releaseNow() call. This is a CI blocker.'
      );
      // Still call release to prevent memory leak, but flag the code defect
      _teraFfi.tera_buf_release(_token);  // Rust generation counter prevents double-free
      _released = true;
    }
  }
}
```

**[PATCH Issue-01] Rust Token Registry — Monotonic Generation Counter:**

```rust
// Token registry with generation counter — prevents double-release use-after-free
pub struct TokenRegistry {
    // token_id → (generation, ZeroizeOnDropBuffer)
    tokens: HashMap<u64, (u32, ZeroizeOnDropBuffer)>,
    next_generation: AtomicU32,
}

impl TokenRegistry {
    pub fn acquire(&mut self, buffer: ZeroizeOnDropBuffer) -> u64 {
        let generation = self.next_generation.fetch_add(1, Ordering::SeqCst);
        // Encode generation in high 16 bits of token, sequence in low 48 bits
        let token = encode_token(self.next_seq(), generation);
        self.tokens.insert(token, (generation, buffer));
        token
    }

    pub fn release(&mut self, token: u64) -> Result<(), TokenError> {
        let expected_gen = extract_generation(token);
        match self.tokens.get(&token) {
            None => {
                // Token already released — stale token from GC finalizer double-release
                // No-op: generation counter prevents use-after-free
                Err(TokenError::StaleToken { token, expected_gen })
            }
            Some((stored_gen, _)) if *stored_gen != expected_gen => {
                // Generation mismatch — reject stale reference
                Err(TokenError::GenerationMismatch { token, expected_gen, stored_gen: *stored_gen })
            }
            Some(_) => {
                let (_, buffer) = self.tokens.remove(&token).unwrap();
                drop(buffer);  // ZeroizeOnDrop fires here
                Ok(())
            }
        }
    }
}
```

**CI Lint (Rust side — FFI-01 enforcement) and Dart lint rules remain unchanged from v0.4.0.**

**[PATCH Issue-01] Error Handling in `Isolate.addErrorListener`:**

```dart
// Register error listener to catch finalizer-time errors
void initializeTeraFfi() {
  Isolate.current.addErrorListener(RawReceivePort((pair) {
    final List errorAndStackTrace = pair as List;
    final error = errorAndStackTrace.first;
    if (error.toString().contains('TeraSecureBuffer')) {
      // Escalate to crash reporter — FFI contract violation
      CrashReporter.report('TeraSecureBuffer finalizer error: $error');
    }
  }).sendPort);
}
```

---

### PLATFORM-18: ONNX Model Integrity

*(No patches in this version. Content unchanged from v0.4.0.)*

### PLATFORM-19: TeraEdge Client Integration

*(No patches in this version. Content unchanged from v0.4.0.)*

---

## §5 — STATE MACHINE

### §5.1 Network Tier State Machine

**Applies to:** F-05, F-06, F-14

| State | Description |
|---|---|
| `ONLINE_QUIC` | QUIC/HTTP3 over UDP:443 active. ~30 ms RTT. |
| `ONLINE_GRPC` | gRPC/HTTP2 over TCP:443 active. ~80 ms RTT. |
| `ONLINE_WSS` | WebSocket Secure over TCP:443 active. ~120 ms RTT. |
| `MESH_MODE` | All ALPN paths unavailable. BLE/Wi-Fi Direct active. |
| `STRICT_COMPLIANCE` | Admin override: skip QUIC; connect directly via gRPC TCP. |

**[PATCH Issue-03] Transition Table (corrected probe-fail logic):**

| From | To | Trigger |
|---|---|---|
| Any | `ONLINE_QUIC` | QUIC ACK within 50 ms — resets `quic_probe_fail_count = 0` |
| `ONLINE_QUIC` | `ONLINE_GRPC` | QUIC probe timeout; UDP firewall block — increments only `quic_probe_fail_count` |
| `ONLINE_GRPC` | `ONLINE_WSS` | gRPC DPI block |
| `ONLINE_WSS` | `MESH_MODE` | WSS rejected |
| `MESH_MODE` | `ONLINE_QUIC` | Internet restored |
| Any | `STRICT_COMPLIANCE` | Admin push via OPA; ≥ 3 QUIC-specific probe failures on same `NetworkProfile` |
| `STRICT_COMPLIANCE` | `ONLINE_GRPC` | Direct TCP connect |

**Critical:** `probe_fail_count` is per-protocol (only `quic_probe_fail_count` tracked). gRPC
losing the race to QUIC does NOT increment any fail count. See §4 F-14 for implementation.

### §5.2 Mesh Role State Machine

**Applies to:** F-05 — unchanged from v0.4.0.

**[PATCH Issue-05] New State: `CAUSAL_FREEZE`**

| State | Eligible Platforms | Conditions |
|---|---|---|
| `LeafNode` | All | Default for iOS |
| `RelayNode` | Android, Huawei | RAM ≥ 3 GB && battery ≥ 40% |
| `SuperNode` | macOS, Windows, Linux | AC power source |
| `TacticalRelay` | iOS only (EMDP) | No Desktop; Internet unavailable; ≥ 2 iOS; battery > 20% |
| `CAUSAL_FREEZE` | iOS (EMDP) | EMDP active; sudden Desktop loss before escrow transmitted |

`CAUSAL_FREEZE` → `TacticalRelay`: Desktop reconnects and transmits fresh EmdpKeyEscrow.

### §5.3 WASM Sandbox Lifecycle State Machine

**Transitions:**
| Any | `ONLINE_QUIC` | QUIC ACK within 50 ms |
| `ONLINE_QUIC` | `ONLINE_GRPC` | QUIC probe timeout (50 ms); UDP firewall block |
| `ONLINE_GRPC` | `ONLINE_WSS` | gRPC DPI block detected |
| `ONLINE_WSS` | `MESH_MODE` | WSS upgrade rejected; all three steps failed |
| `MESH_MODE` | `ONLINE_QUIC` | Internet restored; ALPN renegotiation |
| Any | `STRICT_COMPLIANCE` | Admin push via OPA policy; ≥ 3 probe failures on same network |
| `STRICT_COMPLIANCE` | `ONLINE_GRPC` | Direct TCP connect on Strict Compliance Mode |

**Probe Learning Trigger:** After 3 probe failures on the same `NetworkProfile` (mTLS cert fingerprint + SSID hash), `strict_compliance = true` is set in the `NetworkProfile` and an admin notification is emitted. Reset on network change.

**Signal:** `CoreSignal::TierChanged { new_tier: NetworkTier, reason: TierChangeReason }` emitted on every transition.
---
**Applies to:** F-05
**States:**
| `LeafNode` | All | Default for iOS; fallback for Android/Desktop |
| `BorderNode` | Any | Auto-assigned: `internet_available == true && ble_active == true` |

**Transitions:**

| From | To | Trigger |
|---|---|---|
| `LeafNode` | `RelayNode` | Android: RAM ≥ 3 GB && battery ≥ 40% |
| `LeafNode` | `SuperNode` | Desktop on AC power |
| `SuperNode` | `LeafNode` | Memory pressure approaching Jetsam (iOS); sends `MeshRoleHandover` |
| `LeafNode` | `TacticalRelay` | EMDP activation conditions met |
| `TacticalRelay` | `LeafNode` | TTL expired; no handoff found; or Desktop reconnects |
| `RelayNode` | `LeafNode` | Battery drops < 40% or RAM < 3 GB |
| Any | `BorderNode` | `internet_available == true && ble_active == true` (auto, concurrent with other roles) |

**Hardcoded constraint:** iOS `election_weight = 0` in `mesh/election.rs`. Any PR modifying this constant: **blocker** (FI-05).
**Signal:** `CoreSignal::MeshRoleChanged { new_role: MeshRole }` on every role transition.

---
**Applies to:** F-07

**States:**

| State | Description |
|---|---|
| `Installing` | Signature verification, manifest validation, runtime initialization |
| `Active` | Sandbox running; CPU ≤ 10% sustained |
| `Suspended` | CPU spike > 30% / latency > 1500 ms / rate limit exhausted; 60 s cooldown |
| `Terminated` | Mesh Mode activated; panic unrecoverable; heap OOM |
| `Crashed` | `catch_unwind` triggered; restart pending |

**Transitions:**

| From | To | Trigger |
|---|---|---|
| `Installing` | `Active` | All validation checks pass |
| `Installing` | `Terminated` | Signature or manifest invalid |
| `Active` | `Suspended` | CPU spike > 30%, latency > 1500 ms, or token bucket exhausted |
| `Active` | `Crashed` | `catch_unwind` at entry boundary |
| `Active` | `Terminated` | Mesh Mode activated (snapshot to sled first) |
| `Active` | `Terminated` | Heap OOM (transient state save attempted) |
| `Suspended` | `Active` | 60 s cooldown elapsed |
| `Crashed` | `Active` | Restart after 1 s (attempt 1 or 2) |
| `Crashed` | `Terminated` | 3rd consecutive crash |
| `Terminated` | `Active` | Internet restored; sled snapshot restored in < 50 ms |

**Signal:** `CoreSignal::ComponentFault { component, severity }` on crash or permanent failure.

---

### §5.4 XPC Transaction State Machine

**Applies to:** F-07 (macOS only)

**States:** `PENDING` → `VERIFIED` → `COMMITTED`

**Transitions:**

| From | To | Trigger |
|---|---|---|
| (new request) | `PENDING` | XPC transaction initiated |
| `PENDING` | `VERIFIED` | Transaction data verified successfully |
| `VERIFIED` | `COMMITTED` | Commit operation complete |

**Crash Recovery:**

| State at Crash | Recovery Action |
|---|---|
| `PENDING` | Abort + emit `CoreSignal::ComponentFault`; notify user "Session interrupted. Please re-sign." |
| `VERIFIED` | Idempotent commit from journal. No user action needed. |
| `COMMITTED` | No-op. Already complete. |

**Retry Policy:** Max 3 attempts. Backoff: 0 s → 2 s → 8 s. After 3rd failure: emit `CoreSignal::ComponentFault { severity: Critical }` + `XpcPermanentFailure { support_id: Uuid }`.

---

### §5.5 Push Notification State Machine

**Applies to:** F-02 (iOS NSE path)

**States:**

| State | Description |
|---|---|
| `Received` | APNs delivered payload; NSE woken |
| `VersionMatch` | `push_key_version` matches `Push_Key_N` in Keychain |
| `VersionMismatch` | Version in payload header does not match available key |
| `Staged` | Ciphertext cached to `nse_staging.db`; `main_app_decrypt_needed = true` |
| `MainAppDecrypting` | Main App woken; rotating `Push_Key`; decrypting staging |
| `Displayed` | OS notification shown to user |
| `Cleared` | `nse_staging.db` entry deleted; arena zeroed |

**Transitions:**

| From | To | Trigger |
|---|---|---|
| `Received` | `VersionMatch` | `push_key_version` matches Keychain key |
| `Received` | `VersionMismatch` | Version mismatch or `payload_size > 4 KB` or `epoch_delta > 1` |
| `VersionMatch` | `Displayed` | AES-256-GCM decrypt in NSE arena succeeds |
| `Displayed` | `Cleared` | `ZeroizeOnDrop` on arena after notification shown |
| `VersionMismatch` | `Staged` | Ciphertext written to `nse_staging.db`; flag set in Shared Keychain |
| `Staged` | `MainAppDecrypting` | `content-available: 1` wakes Main App |
| `MainAppDecrypting` | `Displayed` | Main App decrypts; notification shown |
| `Displayed` | `Cleared` | `nse_staging.db` entry deleted |
| `Received` | `Staged` | NSE OOM: Circuit Breaker terminates; sets `main_app_decrypt_needed = true` |

---

### §5.6 Device PIN Failure State Machine

**Applies to:** F-11c, F-11e

**States:** `Unlocked` | `Failed(n)` where n ∈ {1..4} | `SelfDestructed`

**Transitions:**

| From | To | Trigger |
|---|---|---|
| `Unlocked` | `Failed(1)` | First incorrect PIN |
| `Failed(n)` | `Failed(n+1)` | Another incorrect PIN (n < 4) |
| `Failed(n)` | `Unlocked` | Correct PIN entered; counter reset |
| `Failed(4)` | `SelfDestructed` | 5th incorrect PIN |
| Any | `SelfDestructed` | `Failed_PIN_Attempts` counter corrupted (log `PIN_COUNTER_CORRUPTED`) |

**Self-Destruct Execution:** Crypto-Shredding of all local DBs + `OIDC_ID_Token` + both `DeviceIdentityKey` wrappers → Factory Reset state. Non-interruptible.

---

## §6 — API / IPC CONTRACT

### §6.1 CoreSignal Catalog (Core → UI)

| Signal | Payload Fields | Trigger Condition |
|---|---|---|
| `StateChanged` | `table: &str, version: u64` | Any DAG mutation or DB state change |
| `ComponentFault` | `component: &str, severity: FaultSeverity` | Any `catch_unwind` caught panic |
| `MeshRoleChanged` | `new_role: MeshRole` | Mesh topology change |
| `EmdpExpiryWarning` | `minutes_remaining: u32` | T-10 min and T-2 min during EMDP TTL |
| `EmdpCausalFreeze` | `reason: CausalFreezeReason` | **[NEW]** Sudden Desktop loss before escrow |
| `DeadManWarning` | `hours_remaining: u32` | T-12 h and T-1 h offline grace period |
| `TierChanged` | `new_tier: NetworkTier, reason: TierChangeReason` | ALPN tier change or AWDL loss |
| `DagMergeProgress` | `completed: u64, total: u64` | Every 200 ms when merge backlog > 500 events |
| `XpcHealthDegraded` | `crash_count: u32, window_secs: u32` | macOS XPC crash rate exceeds threshold |
| `MemoryPressureWarning` | `component: &str, allocated_mb: u32` | `MemoryArbiter` allocated > 80% ceiling |
| `MediaComplete` | `cas_hash: [u8; 32]` | All media chunks downloaded and decrypted |

### §6.2 UICommand Catalog

**Emission rules:**

- `CoreSignal` emission is fire-and-forget. Core does not wait for UI acknowledgment.
- `DagMergeProgress` emission rate: every 200 ms when merge backlog > 500 events (IPC-03).
- SAB Tier Ladder selection logged to audit trail. Silent tier selection: **blocker** (IPC-02).

---

### §6.2 UICommand Catalog (UI → Core)

| Command | Payload Fields | Effect in Core |
|---|---|---|
| `SendMessage` | `recipient_did: DeviceId, plaintext: Vec<u8>` | Encrypt and append to DAG |
| `ScrollViewport` | `top_message_id: Uuid, bottom_message_id: Uuid` | Return 20-message viewport snapshot |
| `RequestMeshActivation` | none | Activate BLE scanning via host adapter |
| `ReleaseBuffer` | `token: u64` | `ZeroizeOnDrop` when `ref_count == 0` |
| `CancelTask` | `message_id: Uuid` | Cancel in-flight FFI decrypt task |
| `SendMedia` | `file_bytes: Stream, recipient_did: DeviceId` | Chunk, encrypt, upload, create ZeroByteStub |
| `RequestMedia` | `cas_hash: [u8; 32]` | Trigger on-demand chunk download and decrypt |

---

### §6.3 Data Plane Contract

| Operation | Direction | Token Lifecycle | Cleanup |
|---|---|---|---|
| `tera_buf_acquire(op_id) → u64` | Core → UI | Opens on acquire | — |
| `tera_buf_release(token)` | UI → Core | Closes on release | `ZeroizeOnDrop` when `ref_count == 0` |
| `tera_buf_get_pointer(token) → Ptr` | Core (internal) | Within acquire/release window | Never expose outside `useInTransaction()` |
| `tera_buf_get_length(token) → usize` | Core (internal) | Within acquire/release window | — |

**Buffer valid window:** Between `acquire` and `release`. Never held across UI render frames.

**Transport tier selection (Data Plane):**
| Platform | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| 📱 iOS | JSI Shared Memory Pointer | N/A | N/A |
| 📱 Android / Huawei | Dart FFI TypedData | N/A | N/A |
| 💻/🖥️ Desktop | SAB ring buffer (COOP+COEP) | Named Pipe | Protobuf over stdin |

---

### §6.4 Inter-Module IPC (INFRA-01 Offload)

| Message | Direction | Transport | Auth |
|---|---|---|---|
| `OnnxOffloadRequest` | Mobile → Desktop | E2EE CRDT_Event | HMAC-BLAKE3(Company_Key, request_id \|\| sanitized_prompt) |
| `OnnxOffloadResponse` | Desktop → Mobile | E2EE CRDT_Event to requester_did | Implicit: E2EE channel |
| `MeshRoleHandover` | iOS → Desktop/Android | BLE Control Plane | Implicit: BLE auth |
| `EMDP_TTL_EXTENSION_REQUEST` | TacticalRelay → peers | BLE Control Plane | Implicit: BLE auth |
| `EmdpKeyEscrow` | Desktop → iOS Relay | BLE Data Plane | ECIES/Curve25519 |

---

## §7 — PLATFORM MATRIX

### §7.1 Feature Availability Matrix

> Canonical feature availability and constraint reference.
> Platform-specific behavior details are in §4 Feature Model.

| Feature | 📱 iOS | 📱 Android | 📱 Huawei | 💻 macOS | 🖥️ Win | 🖥️ Linux | 🗄️ BM | ☁️ VPS |
|---|---|---|---|---|---|---|---|---|
| F-01: E2EE Messaging | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | relay |
| F-02: Push Notifications | APNs/NSE | FCM | HMS | APNs daemon | WNS | daemon | N/A | relay |
| F-03: IPC Bridge | ✅ JSI | ✅ FFI | ✅ FFI | ✅ SAB | ✅ SAB | ✅ SAB | N/A | N/A |
| F-04: Local Storage | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |
| F-05: Survival Mesh | ✅ Leaf | ✅ Relay | ✅ Relay | ✅ Super | ✅ Super | ✅ Super | N/A | N/A |
| F-06: Voice/Video | ✅ CallKit | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | TURN |
| F-07: WASM `.tapp` | ✅ wasm3 | ✅ wasmtime | ✅ wasmtime | ✅ XPC | ✅ | ✅ | N/A | Enclave |
| F-08: Inter-`.tapp` IPC | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |
| F-09: Media Transfer | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | storage | storage |
| F-10: AI / SLM | ✅ CoreML | ✅ ONNX | ✅ HiAI | ✅ | ✅ | ✅ | N/A | VPS Enclave |
| F-11: Device Security | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |
| F-12: Identity | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | HSM anchor | N/A |
| F-13: Admin Console | read-only | read-only | read-only | ✅ | ✅ | ✅ | ✅ | ✅ |
| F-14: Network Mgmt | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |
| F-15: Crash-Safe WAL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |

### §7.2 Platform-Specific Constraints

| Constraint | Platform | Feature Impact | Rule |
|---|---|---|---|
| W^X: no JIT WASM in App Sandbox | 📱 iOS | F-07: `wasm3` interpreter only | PLT-01 |
| NSE RAM ≤ 20 MB (OS-enforced) | 📱 iOS | F-02: Ghost Push pattern mandatory | PLT-02 |
| Background network 30 s | 📱 iOS | F-06: CallKit integration mandatory | PLT-03 |
| `mlock()` rejected | 📱 iOS | F-11: Double-Buffer Zeroize required | — |
| AWDL + Hotspot mutually exclusive | 📱 iOS | F-05/F-06: BLE fallback on Hotspot | — |
| Mesh role: Leaf Node always | 📱 iOS | F-05: `election_weight = 0` hardcoded | FI-05 |
| FCM 10/hr throttle (Android 14+) | 📱 Android | F-02: CDM registration + FCM high-priority | PLT-06 |
| StrongBox not universal | 📱 Android | F-11/F-12: TEE-backed AndroidKeyStore fallback | — |
| HMS: no `content-available` push | 📱 Huawei | F-02: 4 h CRL delay; SLA disclosure required | PLT-07 |
| Huawei: no dynamic WASM | 📱 Huawei | F-07: AOT `.waot` bundles required | PLT-07 |
| XPC Worker requires `allow-jit` | 💻 macOS | F-07: Main App `NO allow-jit` enforced | PLT-01 |
| Flatpak incompatible | 🖥️ Linux | F-07: `.deb`/`.rpm` or AppImage + Cosign | PLT-04 |
| AppArmor/SELinux startup crash risk | 🖥️ Linux | F-15: postinstall MAC profile load mandatory | — |
| Linux clipboard: dual backend | 🖥️ Linux | F-11: detect `WAYLAND_DISPLAY` at runtime | PLT-05 |
| ARM64 SAB behavior (Windows) | 🖥️ Win ARM64 | F-03: pre-release SAB validation required | — |
| EV Code Signing required | 🖥️ Windows | SmartScreen reputation; ~$500/yr | — |
| No kernel modules / no eBPF client | ☁️ VPS | F-14: Tokio Token Bucket rate limiting (userspace) | — |

### §7.3 RAM Budget Enforcement Matrix (Mobile)

| Component | RAM ≤ 3 GB device | RAM > 4 GB device | Enforcement |
|---|---|---|---|
| NSE / FCM service | 20 MB hard ceiling | 20 MB hard ceiling | OS-enforced; Circuit Breaker terminates on breach |
| WASM heap per `.tapp` | 50 MB; max 1 pre-warm | 50 MB; max 2 pre-warm | `MemoryArbiter.acquire()` returns `MemoryDenied` on overage |
| Whisper voice model | Disabled | Tiny model (39 MB) | `select_whisper_tier()` checks RAM + battery before load |
| BLE Mesh buffer | 8 MB | 12 MB | `MemoryArbiter` ceiling |
| ONNX / embedding pipeline | 8 MB hard ceiling | 8 MB hard ceiling | Custom allocator returns `AllocError` on overflow |
| **Total ceiling** | **≤ 100 MB** | **≤ 130 MB** | `MemoryArbiter` reads `sysinfo::available_memory()` at startup |

### §7.4 Mesh Mode Feature Restrictions

Enforcement is in Rust Core — not in UI. See §4.2 Mesh Mode Feature Restrictions table for exhaustive list and error codes.

### §7.5 Known Implementation Gaps

| Item | Severity | Reference | Status |
|---|---|---|---|
| WasmParity CI gate (wasm3 vs wasmtime semantic identity, ≤ 20 ms delta) | **Blocker** | F-07, CICD-01 | **Sprint 1 — spec complete, implementation required** |
| CI/CD code signing pipeline (all 5 platforms) | Blocker | `ops/signing-pipeline.md` | Not implemented |
| Dart FFI NativeFinalizer Clippy lint (FFI-01 enforcement) | Blocker | F-03, TERA-CORE §4.3 | **Spec patched in PLATFORM-17 v0.5.0** |
| AppArmor/SELinux postinstall script for Linux | **Blocker** | F-15 | **Sprint 1 — spec complete in §F-15** |
| `sled` crate version pinned in `Cargo.toml` | Medium | F-07 Transient State | Not pinned |
| Border Node auto-detection heuristics (algorithm spec) | Medium | F-05 | Algorithm undefined |
| **[PATCH 09] Windows ARM64 SAB CI gate (WebView2 COOP+COEP)** | **Medium — CI gate required** | F-03 | **CI job required: `aarch64-pc-windows-msvc` with WebView2; assert `crossOriginIsolated == true`** |

**[PATCH Issue-09] Windows ARM64 SAB CI Gate Specification:**

WebView2 on Windows ARM64 has documented issues where `crossOriginIsolated` returns `false`
despite correct `COOP+COEP` headers due to ARM64-specific process sandboxing in some Chromium
versions. This causes silent SAB Tier 1 → Named Pipe fallback without audit trail (IPC-02 violation).

Required CI job:

```yaml
# .github/workflows/windows-arm64-sab.yml
name: Windows ARM64 SAB Validation
on: [push, pull_request]
jobs:
  sab-arm64:
    runs-on: windows-latest  # with ARM64 emulation
    steps:
      - name: Build for aarch64-pc-windows-msvc
        run: cargo build --target aarch64-pc-windows-msvc --features tauri
      - name: Verify SAB availability
        run: |
          # Assert crossOriginIsolated == true in WebView2
          # Assert SharedArrayBuffer construction succeeds
          cargo test --target aarch64-pc-windows-msvc --test sab_availability
      - name: Verify Named Pipe fallback audit trail
        run: cargo test --test sab_fallback_audit_trail
        # Must assert CoreSignal::TierChanged emitted with audit entry on SAB unavailable
```

---

## §8 — NON-FUNCTIONAL REQUIREMENTS

### §8.1 Performance

| Metric | Target | Source |
|---|---|---|
| IPC buffer acquire P99 | < 100 µs | CICD-01 |
| AES-256-GCM throughput regression | < 10% drop | CICD-01 |
| `hot_dag.db` checkpoint P99 | < 10 ms | CICD-01 |
| ALPN negotiation total | < 50 ms | F-14 |
| MLS epoch rotation (100 members) | ≤ 1 s | CICD-01 |
| `sled` transient state restore | < 50 ms | F-07 |
| Screen capture prevention overlay | < 16 ms (at 60 Hz) | F-11a |
| `tera_core_flush_io()` on mobile | ≤ 50 ms | F-15 |
| XPC journal PENDING write (synchronous=FULL) | < 10 ms | F-07 |
| GATT pre-auth challenge-response | < 500 ms | F-05 |

### §8.2 Memory

Engineers must resolve all Blocker items before production ship:

| WasmParity CI gate (wasm3 vs wasmtime semantic identity, ≤ 20 ms delta) | Blocker | F-07, TERA-CORE §11.4 | Not implemented |
| Dart FFI NativeFinalizer Clippy lint (FFI-01 enforcement) | Blocker | F-03, TERA-CORE §4.3 | Not implemented |
| AppArmor/SELinux postinstall script for Linux | High | F-15 | Not implemented |
| Windows ARM64 SAB behavior validation (WebView2) | Medium | F-03 | Not tested |
> All values below are extracted from §4 Feature Model and §10 Implementation Contract.
> No values are invented here. Source sections are cited.

| `hot_dag.db` append P99 | < 10 ms | CICD-01 |
| NSE sled restoration on internet restore | < 50 ms | F-07 |
| License feature restoration on renewal | < 5 s | F-13 |
| Component | Ceiling | Device Scope | Source |
|---|---|---|---|
| NSE Static Memory Arena | 10 MB pre-allocated | iOS only | F-02 |
| NSE / FCM service hard ceiling | 20 MB | Mobile | §7.3 |
| WASM heap per `.tapp` | 50 MB mobile / 64 MB desktop | All | F-07 |
| Whisper Tiny model | 39 MB | RAM > 100 MB | F-10 |
| Whisper Base model | 74 MB | RAM > 200 MB | F-10 |
| ONNX / embedding pipeline | 8 MB hard ceiling | All | F-10 |
| BLE Mesh buffer | 8 MB (≤ 3 GB device) / 12 MB (> 4 GB) | Mobile | §7.3 |
| Total mobile RAM ceiling | ≤ 100 MB (≤ 3 GB) / ≤ 130 MB (> 4 GB) | Mobile | §7.3 |
| Desktop ONNX offload process | 150 MB ceiling | Desktop | INFRA-01 |

### §8.3 Latency

| Path | Target Latency | Source |
|---|---|---|
| QUIC 0-RTT RTT | ~30 ms | F-14 |
| gRPC over TCP RTT | ~80 ms | F-14 |
| WSS over TCP RTT | ~120 ms | F-14 |
| IPC Data Plane (iOS JSI / Android FFI) | ~400 MB/s | §2.2 |
| IPC Data Plane (Desktop SAB Tier 1) | ~500 MB/s | §2.2 |
| IPC Data Plane (Named Pipe Tier 2) | ~200 MB/s | §2.2 |
| IPC Data Plane (stdin Tier 3) | ~50 MB/s | §2.2 |
| TURN failover (Keepalived) | < 3 s | F-06 |
| ONNX offload TTL (mobile → desktop) | 5000 ms primary; 3000 ms retry | INFRA-01 |

### §8.4 Reliability

| Scenario | Requirement | Source |
|---|---|---|
| WAL crash safety | Zero data loss; auto-replay on next open | F-15 |
| Relay restart with 1000 STAGED events | Zero data loss; recovery < 60 s | INFRA-06 (SC-03) |
| Network partition 30 min then rejoin | Zero data loss; recovery < 120 s | INFRA-06 (SC-01) |
| WASM sandbox panic | Restart after 1 s; Core unaffected | F-07 |
| XPC journal PENDING durable | WAL synchronous=FULL; fsync before XPC dispatch | F-07 |
| EMDP sudden Desktop loss before escrow | CAUSAL_FREEZE; mandatory epoch rotation on reconnect | F-05 |
| Dead Man Switch deferral | DeadManDeferralEntry in Audit Log before deferral | F-11 |

---

## §9 — SECURITY MODEL

### §9.1 Key Management

| XPC Worker crash retry budget | Max 3 retries (0 s / 2 s / 8 s) | F-07 |
| Component restart budget (watchdog) | 5 per hour before circuit breaker | INFRA-03 |
| VACUUM operation | Zero downtime (`VACUUM INTO` + atomic rename) | F-04 |
| OPA policy push failure | Device retains last known policy | F-13 |

### §8.5 Scalability

| Dimension | Constraint | Source |
|---|---|---|
| MLS group size / platform count | No hardcoded limits; TERA-CORE §10.3 governs | FD-07 / ATD-09 |
| TURN node capacity | ~50 concurrent HD streams per node | F-06 |
| VPS Solo tier | ≤ 50 users | INFRA-04 |
| VPS SME tier | ≤ 500 users | INFRA-04 |
| VPS Enterprise tier | ≤ 5000 users | INFRA-04 |
| Stale data accumulation | Every feature with persistent data must specify cleanup/expiry (ATD-10) | §9 ATD-10 |
> This section consolidates all security logic scattered across features.
> Features reference here. Definitions are not duplicated in features.

| Key | Algorithm | Storage | Rotation Trigger | Access Scope |
|---|---|---|---|---|
| `DeviceIdentityKey` | Ed25519 (Secure Enclave) | Secure Enclave (iOS/macOS) / StrongBox (Android) / TPM 2.0 (Windows) | Remote Wipe or device re-enrollment | Main App only; biometric gate required |
| `Epoch_Key` | AES-256-GCM derived | RAM, `ZeroizeOnDrop` | MLS Epoch rotation | Rust Core only; never crosses FFI |
| `Push_Key_N` | AES-256-GCM symmetric | Secure Enclave / StrongBox | After each MLS Epoch rotation | NSE-only Keychain group (iOS) |
| `ChunkKey_i` | AES-256-GCM, HKDF-derived | RAM, `ZeroizeOnDrop` per chunk | Single-use; derived per chunk | Rust Core only; zeroed after each chunk |
| `Company_Key` | ECIES/Curve25519 | Delivered via MLS `Welcome_Packet` | On group epoch rotation | MLS group members only |
| `cold_state.db` encryption key | AES-256 (SQLCipher) | Derived from Secure Enclave | On Remote Wipe | Main App only; never hardcoded |
| `Recovery_Key` | BIP39 seed + biometric binding | Derived on demand; never stored | N/A | Single-use recovery operation |

**iOS Keychain Access Groups (SEC-05):**

| Group | Key | Accessible By |
|---|---|---|
| `group.com.terachat.nse` | `push_key` | NSE only |
| `group.com.terachat.main` | `device_identity_key` | Main App only |
| `group.com.terachat.share` | `share_extension_token` | Share Extension only |

Cross-group reads: **blocker** (SEC-05).

### §9.2 Trust Boundaries

| Boundary | Trusted | Untrusted | Enforcement |
|---|---|---|---|
| Rust Core ↔ UI | Rust Core | UI layer | Unidirectional signal/command; no key material in signals |
| Rust Core ↔ VPS Relay | Rust Core | VPS Relay | Zero-knowledge; relay sees only ciphertext |
| Rust Core ↔ WASM sandbox | Rust Core | `.tapp` code | `PROT_READ`-only DAG access; OPA policy on all egress |
| iOS NSE ↔ Main App | Shared Keychain (group-scoped) | Other Keychain groups | Three segmented Keychain groups; cross-group: blocker |
| Client ↔ Blob Storage | Rust Core (presigned URL) | MinIO / R2 / B2 | Clients never have direct credentials; relay signs URLs |
| Desktop ↔ Mobile (ONNX offload) | HMAC-BLAKE3-authenticated | Unauthenticated offload request | HMAC mismatch → log `OFFLOAD_HMAC_VIOLATION`; no response |

### §9.3 Encryption Model

| Layer | Algorithm | Key Source | Scope |
|---|---|---|---|
| MLS group messaging | AES-256-GCM + MLS RFC 9420 | `Epoch_Key` (MLS derived) | E2EE; server-blind |
| Push notifications | AES-256-GCM | `Push_Key_N` (versioned) | E2EE; APNs/FCM/HMS blind |
| Media chunks | AES-256-GCM | `ChunkKey_i = HKDF(Epoch_Key, "chunk" \|\| cas_hash \|\| i)` | E2EE; MinIO blind |
| Voice/Video | DTLS-SRTP (WebRTC) | Negotiated via DTLS | E2EE; TURN relay blind |
| Local DB (`cold_state.db`) | SQLCipher AES-256 | Derived from Secure Enclave | At-rest encryption |
| `sled` transient state | AES-256-GCM | Rust Core managed | Per-DID namespace |
| Transport | TLS 1.3 + mTLS | mTLS cert (TTL 12–24 h) | In-transit; mutual auth |
| ONNX offload | HMAC-BLAKE3 + E2EE CRDT_Event | `Company_Key` | Authenticated; E2EE |

### §9.4 Attack Surface

| Surface | Threat | Mitigation |
|---|---|---|
| Push key version mismatch | Replay attack on old key | Ghost Push; Main App decrypts with rotated key |
| WASM egress | Unauthorized network access | OPA policy check; declared endpoints only |
| WASM memory | DAG buffer write | `PROT_READ`-only; `SIGSEGV` caught by `catch_unwind` |
| FFI boundary | Raw pointer leakage | Token protocol; Clippy lint enforced (SEC-02) |
| **[PATCH 01] Dart FFI double-release** | Use-after-free on Android | Generation counter in token registry rejects stale tokens |
| **[PATCH 03] ALPN probe race** | Permanent QUIC disable on working networks | Per-protocol fail count; QUIC win resets count |
| **[PATCH 15] BLE GATT pre-auth** | ML-KEM public key fingerprinting | GATT challenge-response before any key material exchange |
| **[PATCH 13] Dead Man Switch deferral** | Insider threat via call-to-defer | DeadManDeferralEntry in tamper-proof Audit Log before deferral |
| LLM prompt injection | Malicious `.tapp` output | AST Sanitizer; 3rd TAINTED → `.tapp` suspend |
| Protocol downgrade | QUIC → WSS forced | QUIC-Pinning State Machine |

### §9.5 Implementation Contract — Security Rules

| Rule ID | Rule | Enforcement |
|---|---|---|
| SEC-01 | No plaintext UI buffer outlives the render frame. | `cargo miri test`. CI failure: blocker. |
| SEC-02 | No `Vec<u8>`, `*const u8`, or `*mut u8` in `pub extern "C"`. | CI Clippy lint. Blocker. |
| SEC-03 | All clipboard operations route through Protected Clipboard Bridge. | Code review + CI. |
| SEC-04 | WASM sandbox: `PROT_READ`-only DAG access. | Runtime enforcement. |
| SEC-05 | iOS Keychain access groups segmented (NSE / Main / Share). | Keychain entitlement. |
| **SEC-06 [NEW]** | **Dead Man Switch deferral: `DeadManDeferralEntry` in Audit Log before deferral.** | **Code review; Audit Log validator.** |
| **SEC-07 [NEW]** | **GATT pre-auth challenge-response before ML-KEM key exchange.** | **Integration test in TestMatrix SC-22.** |

---

## §10 — FAILURE MODEL

### §10.1 Network Failure

| Condition | Detection | Response | Signal |
|---|---|---|---|
| QUIC UDP:443 blocked | 50 ms probe timeout | Auto-downgrade to gRPC; increment only `quic_probe_fail_count` | `CoreSignal::TierChanged` |
| EMDP TTL expired, no hand-off | TTL counter reaches 0 | Enter SoloAppendOnly mode | `CoreSignal::EmdpExpiryWarning` |
| EMDP sudden Desktop loss before escrow | EMDP active + Desktop gone + no escrow received | Enter `CAUSAL_FREEZE` | `CoreSignal::EmdpCausalFreeze` |

### §10.2 Storage Failure

| Condition | Detection | Response | Log Event |
|---|---|---|---|
| WAL > 50 MB (mobile) | Background Tokio task | Trigger `PRAGMA wal_checkpoint(TRUNCATE)` — NOT VACUUM INTO | None |
| Schema migration fails (`cold_state.db`) | Migration error | Drop and rebuild from `hot_dag.db` | `COLD_STATE_REBUILD` |
| Shadow DB write TOCTOU | Mutex<bool> guards compound check+write | No race possible | None |

### §10.3 Key Failure

| Push key version mismatch | Replay attack on old key | Ghost Push: no content exposure; Main App decrypts with rotated key |
| WASM egress | Unauthorized network access | OPA policy check on all requests; declared `egress_endpoints` only |
| FFI boundary | Raw pointer leakage | No `Vec<u8>` / `*const u8` in `pub extern "C"`; Clippy lint enforced (SEC-02) |
| LLM prompt injection | Malicious `.tapp` output | AST Sanitizer wraps all LLM responses; 3rd TAINTED → `.tapp` suspend |
| Protocol downgrade | QUIC → WSS forced downgrade | QUIC-Pinning State Machine; 30 s Socket Panic Circuit Breaker |
| Remote Wipe bypass | UI attempt to cancel wipe | Non-interruptible: `autoreleasepool` (iOS) / `try-finally` (Android) |
| Admin Console from mobile | Unauthorized policy mutation | Mobile Admin Console: read-only enforced by Rust Core (FD-02) |
| Model integrity | Tampered ONNX weights | BLAKE3 hash + Ed25519 manifest signature on every load (PLATFORM-18) |
| SEC-01 | No plaintext UI buffer outlives the render frame. `ZeroizeOnDrop` on every struct holding decrypted content. | `cargo miri test`. CI failure: blocker. |
| SEC-02 | No `Vec<u8>`, `*const u8`, or `*mut u8` returned from any `pub extern "C"` function. Token protocol mandatory. | CI Clippy lint `tera_ffi_raw_pointer`. Lint failure: blocker. |
| SEC-03 | All clipboard operations route through Protected Clipboard Bridge (F-11b). Direct OS clipboard API calls from Rust Core: blocker. | Code review + CI. |
| SEC-04 | WASM sandbox: `PROT_READ`-only access to DAG shared memory. Write attempts trigger `SIGSEGV` caught by `catch_unwind`. | Runtime enforcement. |
| SEC-05 | iOS Keychain: `push_key` (NSE only), `device_identity_key` (Main App only), `share_extension_token` (Share Extension only). Cross-group reads: blocker. | Keychain entitlement configuration. |
> All failure conditions extracted from §4 Feature Model.
> Organized by failure category. Features reference this section.

| QUIC UDP:443 blocked | 50 ms probe timeout | Auto-downgrade to gRPC | `CoreSignal::TierChanged` |
| gRPC DPI blocked | TLS handshake or framing rejection | Auto-downgrade to WSS | `CoreSignal::TierChanged` |
| All ALPN paths unavailable | WSS upgrade rejected | Activate Mesh Mode | `CoreSignal::TierChanged { new_tier: MeshMode }` |
| TURN primary failure | DTLS-SRTP keepalive lost | Keepalived Floating IP failover < 3 s | None (transparent) |
| All TURN paths fail | STUN binding failure | Attempt direct P2P STUN; notify "Call quality degraded" | None |
| AWDL disabled (Hotspot/CarPlay) | `NWPathMonitor` interface change | BLE-only Tier 3; voice queue TTL 90 s (CallKit) / 30 s | `CoreSignal::TierChanged` |
| Voice call dropped (90 s no AWDL) | TTL expiry | Call dropped; notification: "Call ended — Hotspot is active." | None |
| Protocol downgrade manipulation | QUIC-Pinning State Machine detection | Refuse new TCP/UDP connections for 30 s (Socket Panic Circuit Breaker) | None |
| EMDP TTL expired, no hand-off | TTL counter reaches 0 | Enter SoloAppendOnly mode; merge deferred | `CoreSignal::EmdpExpiryWarning` |
| Send while offline | Network unavailable at send | Event durable in `hot_dag.db`; retry on reconnect | None |
| Upload chunk failure (3 retries) | Retry budget exhausted | `MEDIA_UPLOAD_FAILED`; notify UI | None |
| WAL > 50 MB (mobile) | Background Tokio task monitoring | Trigger VACUUM sequence | None |
| WAL > 200 MB (mobile) | `MemoryArbiter` monitoring | Emit `CoreSignal::MemoryPressureWarning`; UI banner | None |
| VACUUM fails | `VACUUM INTO` returns error | Log error; retry on next trigger; do not crash | None |
| Schema migration fails (`cold_state.db`) | Migration script error | Drop `cold_state.db`; rebuild from `hot_dag.db` | `COLD_STATE_REBUILD` |
| Hydration interrupted mid-download | Process termination or network loss | Delete `cold_state_shadow.db`; restart from `Hydration_Checkpoint` | None |
| WAL checkpoint timeout (Desktop 30 s) | `timeout()` wrapper | Exit unconditionally; `systemd Restart=on-failure` | None |
| OOM kill before WAL flush (mobile) | OS SIGKILL | SQLite WAL crash-safe; auto-replay on next open | None |
| `sled` transient state unavailable (Mesh Mode) | Mesh Mode active | Transient state persistence disabled; snapshot on Mesh activation | None |

| Condition | Response | Log Event |
|---|---|---|
| Huawei device revoked | Server bumps push_key_version → Ghost Push on stale key | `HUAWEI_PUSH_KEY_VERSION_BUMPED` |
| Android CDM revocation | Emit `ComponentFault`; show persistent re-grant banner | `FCM_CDM_REVOKED` |

### §10.4 Runtime Failure

| `Push_Key` not in Keychain | Display generic "New message" notification; no content preview | None |
| `Push_Key` version mismatch | Ghost Push → cache to `nse_staging.db` → Main App decrypt | None |
| NSE OOM | Circuit Breaker terminates NSE gracefully; set `main_app_decrypt_needed = true` | None |
| `Epoch_Key` unavailable (rejoining group) | UI: "Waiting for key sync…"; message held; delivered after key restored | None |
| StrongBox unavailable (Android) | Fallback to TEE-backed AndroidKeyStore | `STRONGBOX_UNAVAILABLE` |
| DeviceIdentityKey deleted (Remote Wipe) | Factory Reset state; no recovery without Admin Recovery Ticket | None |
| Recovery Ticket invalid/expired | Reject; log; Admin must generate new ticket | `INVALID_RECOVERY_TICKET` |
| BIP-39 phrase incorrect | Return `ERR_MNEMONIC_INVALID`; no attempt limit (biometric gate prevents brute force) | None |
| `Failed_PIN_Attempts` counter corrupted | Treat as 5 failures; initiate Cryptographic Self-Destruct | `PIN_COUNTER_CORRUPTED` |
| Remote Wipe partial (power loss mid-sequence) | On next boot: detect `wipe_in_progress`; complete remaining steps before any UI | None |
| ONNX model BLAKE3 mismatch | Terminate AI worker; emit `ComponentFault { severity: Critical }` | `ModelIntegrityViolation` (Audit) |

| Condition | Component | Response | Signal |
|---|---|---|---|
| XPC Worker crash, PENDING journal missing | macOS | Was: silent loss. Now: impossible — `synchronous=FULL` ensures PENDING is durable | `CoreSignal::ComponentFault` |
| Dart FFI GC finalizer double-release | Android, Huawei | Generation counter in Rust registry → stale token rejected as no-op | CI BLOCKER metric |

---

## §11 — VERSIONING & MIGRATION

### §11.1 Schema Migration Strategy

**`ShadowMigrationLock` type change (v0.4.0 → v0.5.0):**

`ShadowMigrationLock` changed from `AtomicBool` to `tokio::sync::Mutex<bool>`. This is a
Rust-internal type with no schema migration required. Client update will automatically use
the new locking primitive on next app launch.

**`XpcJournalEntry` connection type change:**

The XPC journal table is now accessed via a dedicated `synchronous=FULL` SQLite connection.
No schema change; existing journal entries are fully compatible. The `hot_dag.db` schema
version is NOT bumped for this change.

### §11.2 Backward Compatibility

| WASM sandbox panic | `.tapp` | `catch_unwind`; emit `ComponentFault`; restart after 1 s | `CoreSignal::ComponentFault` |
| WASM heap OOM | `.tapp` | OOM kills sandbox; transient state save attempted; Core unaffected | `CoreSignal::ComponentFault` |
| WASM rate limit exhausted (50 req/s) | `.tapp` | SUSPEND; `ERR_RATE_LIMIT_EXCEEDED`; resume after 60 s | None |
| XPC Worker crash (macOS) | macOS only | Recover from `XpcJournalEntry`; max 3 retries (0 s / 2 s / 8 s) | `CoreSignal::XpcHealthDegraded` |
| XPC 3rd consecutive crash | macOS only | `XpcPermanentFailure { support_id }` | `CoreSignal::ComponentFault { severity: Critical }` |
| ONNX allocator OOM | F-10 | Graceful fallback to Flat-search | `ONNX_OOM_FALLBACK` |
| LLM cloud unreachable | F-10 | `ERR_AI_CLOUD_UNAVAILABLE`; local fallback if available | None |
| AST Sanitizer 3rd TAINTED | F-10 | `.tapp` suspended; `ERR_AI_RESPONSE_TAINTED` | `CoreSignal::ComponentFault` |
| Component heartbeat silent > threshold | INFRA-03 | Watchdog restart with delay | `WatchdogAlert::CircuitBreakerTripped` (after 5/hour) |
| AppArmor/SELinux postinstall fails | F-15 (Linux) | Log to `/var/log/terachat-install.log`; warn console; do not abort install | None |
| Memory pressure (iOS/Android) | F-15 | Zeroize vector caches; pause ONNX; preserve `hot_dag.db` and active session | `CoreSignal::ComponentFault { component: "onnx", severity: Warning }` |
| ONNX offload HMAC mismatch | INFRA-01 | Do not respond to request | `OFFLOAD_HMAC_VIOLATION` (Audit) |
> All policies extracted from §4 and §9. No values invented here.

**Protocol (from F-04):**

1. Read `PRAGMA user_version` from `hot_dag.db` on every DB open.
2. If `user_version < CURRENT_SCHEMA_VERSION`:
   - Create backup: `{db_path}.bak.v{current_version}`.
   - `BEGIN EXCLUSIVE TRANSACTION`.
   - Run migration scripts in version order.
   - `PRAGMA user_version = CURRENT_SCHEMA_VERSION`.
   - `COMMIT`.
3. `cold_state.db` migration failure: drop file; rebuild from `hot_dag.db` (DB-02 safety net). Log `COLD_STATE_REBUILD`.
4. `PRAGMA wal_autocheckpoint = 1000` set on all connections (DB-03).
**Two-DB invariant:** `cold_state.db` is always rebuildable from `hot_dag.db`. `hot_dag.db` is append-only; tombstones only; no physical deletion.
### §11.2 Backward Compatibility
| Contract | Policy |
|---|---|
| `CRDT_Event` format | Immutable after append; must remain deserializable across all future versions |
| `CoreSignal` enum | Additive only; no field removal without deprecation cycle |
| `UICommand` enum | Additive only; no field removal without deprecation cycle |
| `DelegationToken` fields | Additions permitted; removals require migration path |
| `sled` crate version | Must be pinned in `Cargo.toml` (FI-04). Upgrade requires validation against WASM heap budget |
| `NetworkProfile` schema | Additive changes permitted; reset on network change |
### §11.3 Upgrade Path
| Component | Strategy | Downtime |
|---|---|---|
| VPS Relay (server) | Single binary atomic replacement + systemd restart | Zero (< 5 s systemd restart) |
| Client apps | Canary DNS-based traffic splitting: 5% → 25% → 50% → 100% at 2 h intervals | Zero |
| Auto-rollback | Triggered by: error_rate_5xx > 0.5%, crash_rate > 0.2%, dag_merge_p99 > 2000 ms | Zero (DNS weight reset) |
| Per-tenant override | `canary_opt_out: true` in OPA Feature Flags | Zero |
| License renewal | JWT replaced in Admin Console → Rust verifies → features restore within 5 s | Zero; no restart |
| `cold_state.db` rebuild | Drop + rebuild from `hot_dag.db` at any time | Zero for `hot_dag.db` |

---

## §12 — OBSERVABILITY

### §12.1 Named Log Events

| Event ID | Condition | Feature | Level |
|---|---|---|---|
| `COLD_STATE_REBUILD` | `cold_state.db` dropped and rebuilt | F-04 | INFO |
| `STRONGBOX_UNAVAILABLE` | Android StrongBox fallback | F-11/F-12 | WARN |
| `HUAWEI_CRL_STALE` | Huawei CRL delay caused deferred decryption | F-02 | WARN |
| `HUAWEI_PUSH_KEY_VERSION_BUMPED` | **[NEW]** Server bumped version on revocation | F-02 | AUDIT |
| `FCM_CDM_REVOKED` | **[NEW]** Android CDM association missing | F-02 | WARN |
| `EMDP_CAUSAL_FREEZE` | **[NEW]** Sudden Desktop loss before escrow | F-05 | WARN |
| `DEAD_MAN_SWITCH_DEFERRED` | **[NEW]** Deferral logged with counter delta | F-11 | AUDIT |
| `ALPN_PROBE_RACE_WIN` | **[NEW]** QUIC won parallel race; gRPC fail count NOT incremented | F-14 | DEBUG |
| `OFFLOAD_HMAC_VIOLATION` | HMAC mismatch on ONNX offload | INFRA-01 | AUDIT |
| `INVALID_RECOVERY_TICKET` | Recovery Ticket Ed25519 invalid | F-12 | AUDIT |
| `MEDIA_UPLOAD_FAILED` | Chunked upload failed after 3 retries | F-09 | ERROR |
| `PIN_COUNTER_CORRUPTED` | Failed_PIN_Attempts counter tampered | F-11e | AUDIT |
| `ONNX_OOM_FALLBACK` | ONNX allocator OOM | F-10 | WARN |

### §12.6 Canary Rollback Metrics

> All data extracted from §4 Feature Model and §9 Implementation Contract.
> No additional telemetry is defined here.

| `COLD_STATE_REBUILD` | `cold_state.db` dropped and rebuilt from `hot_dag.db` | F-04 | INFO |
| `STRONGBOX_UNAVAILABLE` | Android StrongBox absent; fallback to AndroidKeyStore | F-11/F-12 | WARN |
| `OPA_PUSH_FAILED` | OPA policy push to device failed; retaining last policy | F-13 | WARN |
| `ONNX_OOM_FALLBACK` | ONNX allocator OOM; fallback to Flat-search | F-10 | WARN |
| `OFFLOAD_HMAC_VIOLATION` | HMAC mismatch on ONNX offload; `requester_did` logged | INFRA-01 | AUDIT |
| `INVALID_RECOVERY_TICKET` | Recovery Ticket Ed25519 signature invalid | F-12 | AUDIT |
| `PIN_COUNTER_CORRUPTED` | `Failed_PIN_Attempts` counter tampered; self-destruct initiated | F-11e | AUDIT |
| `LINUX_SCREEN_CAPTURE_UNSUPPORTED` | Wayland compositor does not support security hint | F-11a | INFO |
| `ONNX_RAM_DENIED` | Insufficient RAM for model tier | F-10 / PLATFORM-18 | WARN |
| `ModelIntegrityViolation` | BLAKE3 hash mismatch on ONNX model load | PLATFORM-18 | AUDIT |

### §12.2 Client Metrics (`ClientMetricBatch`)

Full schema: → §4 OBSERVE-01. Summary:

| Category | Fields |
|---|---|
| Performance | `mls_encrypt_p50/p99_ms`, `ipc_buf_acquire_p50/p99_us`, `dag_append_p50_ms`, `dag_merge_events_per_s` |
| Reliability | `wasm_sandbox_crashes`, `nse_circuit_breaker_trips`, `push_key_version_mismatches`, `alpn_fallback_count` |
| Health (bucketed) | `wal_size_mb`, `available_ram_mb`, `battery_pct` |
| Code quality | `ffi.gc_finalizer_release.count` (WARNING: GC release of `TeraSecureBuffer`) |

Push frequency: every 15 min online; buffered in `metrics_buffer.db` (max 48h / 500 KB) when offline.

### §12.3 Server Metrics (Prometheus)

```
terachat_watchdog_restarts_total{component="wal_staging"}
terachat_watchdog_circuit_breaker_trips_total{component="ai_worker"}
terachat_component_health{component="ble_scanner", status="healthy"}
relay_error_rate_5xx
wasm_sandbox_crashes_total_rate
dag_merge_duration_p99_ms
client_reported_crash_rate
```

No user ID, message content, or session data in any metric (Zero-Knowledge metric policy).

### §12.4 IPC Signals

Full catalog: → §6.1 (CoreSignal). Key operational signals:

| Signal | Operational Meaning |
|---|---|
| `CoreSignal::TierChanged` | Network path changed; update HUD indicator |
| `CoreSignal::DagMergeProgress` | Show non-blocking progress banner; disable Send |
| `CoreSignal::ComponentFault` | Display appropriate degraded-mode UI |
| `CoreSignal::MemoryPressureWarning` | Show storage cleanup banner |
| `CoreSignal::XpcHealthDegraded` | Log; notify Admin if persistent |

### §12.5 Audit Trail

- Format: Ed25519-signed entries (tamper-proof).
- Storage: PostgreSQL (TERA-CORE §9.5). Access: Admin Console read-only viewer.
- Events audited: offboarding, Remote Wipe trigger, OPA policy mutation, SAB tier selection, `OFFLOAD_HMAC_VIOLATION`, `ModelIntegrityViolation`, Recovery Ticket operations.
- Retention: governed by TERA-CORE §9.5.
Thresholds that trigger automatic DNS rollback (INFRA-04):

| Metric | Threshold | Window |
|---|---|---|
| `relay_error_rate_5xx` | > 0.5% | 5 min |
| `wasm_sandbox_crashes_total_rate` | > 0.1/min | 5 min |
| `dag_merge_duration_p99_ms` | > 2000 | 10 min |
| `client_reported_crash_rate` | > 0.2% | 15 min |

---

## §13 — APPENDIX

### §13.2 Error Code Reference

| Error Code | Condition | Feature |
|---|---|---|
| `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` | Mesh Mode active | F-10 |
| `ERR_MESH_MODE_DELEGATION_SUSPENDED` | Mesh Mode active | F-08 |
| `ERR_EMDP_CAUSAL_FREEZE` | **[NEW]** Sudden Desktop loss before escrow | F-05 |
| `ERR_FFI_STALE_TOKEN` | **[NEW]** Token's generation counter does not match registry | F-03 / PLATFORM-17 |
| `ERR_GATT_PREAUTH_FAILED` | **[NEW]** GATT challenge-response failed | F-05 |
| `ERR_RATE_LIMIT_EXCEEDED` | `.tapp` token bucket exhausted | F-07 |
| `ERR_MNEMONIC_INVALID` | BIP-39 mnemonic incorrect | F-12 |
| `ERR_AI_QUOTA_EXCEEDED` | Token quota exceeded | F-10 |
| `BufferNotFound` | Token not in Core registry | F-03 |

### §13.3 Implementation Contract — Complete Rule Index

**Security Rules (SEC):** → §9.5 (SEC-01 through SEC-07)

**Platform Rules (PLT):**

| Rule ID | Rule |
|---|---|
| PLT-01 | iOS: `wasm3` interpreter only in App Sandbox. No JIT in Main App: **blocker**. |
| PLT-02 | iOS NSE: Static Memory Arena 10 MB. **ONNX prohibited in NSE build.** `debug_assert!(NsePolicy::is_onnx_prohibited())` at entry. |
| PLT-03 | iOS: Voice calls require CallKit. |
| PLT-04 | Linux: Flatpak packaging prohibited. `.deb`/`.rpm` or AppImage + Cosign only. |
| PLT-05 | Linux clipboard: detect display server at runtime. |
| PLT-06 | Android 14+: FCM `priority = "high"` AND CDM `REQUEST_COMPANION_RUN_IN_BACKGROUND`. **Add CDM revocation health check on every FCM receipt.** |
| PLT-07 | Huawei: AOT `.waot` bundles only. CRL delay ≤ 4 h in SLA. **Server-side push key version bump on revocation mitigates 4h window.** |
| PLT-08 **[NEW]** | **Windows ARM64: SAB availability CI gate required. Assert `crossOriginIsolated == true` in WebView2 on `aarch64-pc-windows-msvc`.** |

**Feature Integrity Rules (FI):**

| Rule ID | Rule |
|---|---|
| FI-01 | Every feature maps to at least one TERA-CORE module. Orphan features: **blocker**. |
| FI-02 | Mesh Mode restrictions enforced in Rust Core. UI-side Mesh override: **blocker**. |
| FI-03 | WasmParity CI gate must pass before any `.tapp` Marketplace listing. **Sprint 1 blocker.** |
| FI-04 | `sled` crate pinned in `Cargo.toml`. |
| FI-05 | iOS `election_weight = 0` hardcoded. Any PR modifying: **blocker**. |
| FI-06 **[NEW]** | **`PRAGMA wal_checkpoint(TRUNCATE)` is the sole background WAL compaction path. `VACUUM INTO` only under `BEGIN EXCLUSIVE` for admin defrag.** |
| FI-07 **[NEW]** | **XPC journal PENDING write uses dedicated `synchronous=FULL` SQLite connection. PENDING write without fsync: **blocker**.** |
| FI-08 **[NEW]** | **GATT pre-auth challenge-response must complete before any ML-KEM key material is transmitted over BLE.** |

**IPC Rules (IPC):**

| Rule ID | Rule |
|---|---|
| IPC-01 | State flow unidirectional Core → UI. Bidirectional state channel: **blocker**. |
| IPC-02 | SAB Tier Ladder selection logged to audit trail. Silent tier selection: **blocker**. |
| IPC-03 | `CoreSignal::DagMergeProgress` emitted every 200 ms when merge backlog > 500 events. |
| IPC-04 **[NEW]** | **`FfiToken` carries monotonic generation counter. Stale tokens (e.g. from GC finalizer) rejected by Rust registry as no-op.** |

---

## §14 — CHANGELOG

| Version | Date | Summary |
|---|---|---|
| 0.5.0 | 2026-03-23 | Security audit patch batch: 15 issues fixed. Key changes: PLATFORM-17 Dart FFI generation counter; F-02 NSE RAM table + ONNX prohibition + Huawei revocation fast-path + Android CDM detection; F-04 checkpoint-first WAL + Mutex shadow lock; F-05 EMDP proactive escrow + CAUSAL_FREEZE + GATT pre-auth; F-07 WasmParity Sprint 1 blocker + XPC synchronous=FULL; F-11 DeadManDeferralEntry audit trail; F-13 OPA policy channel schema exemption; F-14 ALPN per-protocol fail count race fix; F-15 full AppArmor/SELinux profiles + --check-permissions subcommand. |
| 0.4.0 | 2026-03-21 | Full restructure to production-grade standard. |
| 0.2.6 | 2026-03-19 | Add OBSERVE-01/02, PLATFORM-17/18/19, INFRA-01–06, CICD-01. |
| 0.2.3 | 2026-03-18 | Complete rewrite. Full alignment with TERA-CORE v2.0. |
