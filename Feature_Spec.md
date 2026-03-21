<!-- markdownlint-disable MD041 -->

```yaml
# DOCUMENT IDENTITY
id:        "TERA-FEAT"
title:     "TeraChat — Feature Technical Specification"
version:   "0.4.0"
status:    "ACTIVE — Implementation Reference"
date:      "2026-03-21"
audience:  "Frontend Engineer, Mobile Engineer, Desktop Engineer, Product Engineer"
purpose:   "Defines all client-facing and system-level features. Maps every feature to a
            verified core module in Core_Spec.md (TERA-CORE). Governs platform-specific
            behavior, OS lifecycle hooks, IPC bridge, WASM runtime, local storage, and
            user interaction contracts."

depends_on:
  - id: "TERA-CORE"   # Cryptographic primitives, MLS, Mesh, CRDT, infrastructure

consumed_by:
  - id: "TERA-DESIGN" # UI state machine reads IPC signals defined here
  - id: "TERA-MKT"    # Plugin sandbox runtime constraints reference this document
  - id: "TERA-TEST"   # Chaos test scenarios validate feature failure behaviors

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

ai_routing_hint: |
  Route to this document for: client platform IPC bridge, OS hooks (iOS NSE/CallKit,
  Android FCM, Huawei HMS), WASM .tapp sandbox runtime, local SQLite storage lifecycle,
  push notification handling, platform-specific feature constraints, user interaction
  flows, feature-to-core module mapping, ONNX offload protocol, canary deployment,
  SBOM requirements, chaos engineering framework, or client observability.

  Do NOT route here for: MLS cryptographic internals (→ TERA-CORE §5), CRDT merge
  algorithms (→ TERA-CORE §7), server relay infrastructure (→ TERA-CORE §9), or UI
  animation specs (→ TERA-DESIGN).
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

> Cross-references: TERA-CORE §2 (shared Rust Core), §4 (IPC bridge), §9 (relay infrastructure).

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

Media Path:
  File → Core chunk (2 MB) → AES-256-GCM per chunk → presigned URL → MinIO
    → CRDT_Event (ZeroByteStub) → distributed to recipients
    → Receive: tap ZeroByteStub → on-demand download → stream decrypt → render

Push Path (iOS):
  APNs → NSE (≤ 20 MB) → AES-256-GCM decrypt (Push_Key_N)
    → version match: display → ZeroizeOnDrop arena
    → version mismatch: cache → nse_staging.db → wake Main App
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

Single Rust binary deployment. No cluster coordination. Self-healing via in-process watchdog (INFRA-03).

---

## §3 — DATA MODEL

> This section is the authoritative definition of every client-side data object.
> Operations in §4 (Feature Model) act on these objects — not on raw platform APIs.
> Internal cryptographic object definitions are in TERA-CORE §0.
> Each object is defined exactly once here. All other sections reference by name.

### §3.1 Local Storage Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `cold_state.db` | SQLite, SQLCipher AES-256 | Disk, permanent | Until Remote Wipe or Crypto-Shredding | Key from Secure Enclave; never hardcoded | TERA-CORE §7.1 |
| `cold_state_shadow.db` | SQLite, transient | Disk, temporary | Created on Hydration batch; deleted after atomic rename | Write-locked via `ShadowMigrationLock` during migration | TERA-CORE §7.1 |
| `hot_dag.db` | SQLite WAL | Disk, permanent | Append-only; cleaned via VACUUM | Append-only; tombstones only; no physical deletion | TERA-CORE §7.1 |
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
| `FfiToken` | Opaque `u64` | FFI return value | Valid until `tera_buf_release` called | No semantic meaning outside Core; opaque to UI | TERA-CORE §4.3 |

### §3.4 Push and Notification Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `Push_Key_N` | AES-256-GCM symmetric key | Secure Enclave (iOS) / StrongBox (Android) | Rotated after each MLS Epoch rotation | NSE-only Keychain group (`group.com.terachat.nse`) | TERA-CORE §5.5 |
| `PushKeyVersion` | `u32` | Shared Keychain (iOS) / StrongBox metadata | Incremented on each rotation | Read by NSE to match payload header | TERA-CORE §5.5 |
| `NSE_StagedCiphertext` | Raw ciphertext bytes | `nse_staging.db` | Cleared after successful Main App decryption | Ciphertext only; no plaintext at rest | TERA-CORE §5.5 |

### §3.5 WASM Plugin Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `DelegationToken` | `{source_did, target_did, permissions, expires_at, signature}` | RAM + `hot_dag.db` | TTL 30 days; revocable by Admin at any time | Ed25519-signed by DeviceIdentityKey; tamper-evident | TERA-FEAT §F-08 |
| `EgressNetworkRequest` | Protobuf | In-flight | Single request; sanitized by Host Proxy | OPA policy check before execution; no raw TCP/UDP | TERA-CORE §4.1 |
| `XpcJournalEntry` | `{tx_id: Uuid, status: Pending\|Verified\|Committed}` | `hot_dag.db` | Per XPC transaction; cleared on Committed | Persisted for crash-safe recovery | TERA-FEAT §F-07 |

---

## §4 — FEATURE MODEL

> **Read §3 (Data Model) before implementing any feature.**
> Every feature references objects defined in §3. Feature sections do not redefine objects.
> State machines extracted from features are centralized in §5.
> API contracts for CoreSignal / UICommand are in §6.
> Security rules and failure handling are consolidated in §9 and §10.

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

> A feature with no Core mapping is an **orphan — blocker, do not ship**.
> Verified against TERA-CORE v2.0.

| Feature ID | Feature Name | Primary Core Modules | TERA-CORE References |
|---|---|---|---|
| F-01 | Secure E2EE Messaging | `crypto/mls_engine.rs`, `crdt/dag.rs` | §5.3, §7.1, §8.1, §4.2, §4.3 |
| F-02 | Push Notification Delivery | `crypto/push_ratchet.rs` | §5.5, §8.3, §4.2 |
| F-03 | IPC Bridge & State Sync | `ffi/ipc_bridge.rs`, `ffi/token_protocol.rs` | §4.2, §4.3, §2.2 |
| F-04 | Local Storage Management | `crdt/dag.rs`, `crdt/snapshot.rs` | §7.1, §7.4, §12.2 (DB-01, DB-02, DB-03) |
| F-05 | Survival Mesh Networking | `mesh/` (all six modules) | §6.1, §6.2, §6.3, §6.4, §6.5, §6.6, §6.7 |
| F-06 | Voice and Video Calls | `infra/relay.rs` (TURN), host adapters | §10.4, §6.4, §9.2, §5.3 |
| F-07 | WASM Plugin Sandbox | `ffi/token_protocol.rs`, platform WASM adapter | §4.1, §4.4, §3.2 (Table §3.1) |
| F-08 | Inter-`.tapp` IPC | `ffi/ipc_bridge.rs` | §4.2, §4.3, §3.2 |
| F-09 | Media and File Transfer | `crypto/mls_engine.rs`, `infra/relay.rs` | §5.3, §9.5, §7.1, §8.1 |
| F-10 | AI / SLM Integration | `infra/relay.rs` (VPS Enclave) | §3.3, §3.6, §4.4 |
| F-11 | Device Security | `crypto/hkms.rs`, `crypto/zeroize.rs` | §5.1, §5.2, §12.4 (PLT-04) |
| F-12 | Identity and Onboarding | `crypto/hkms.rs`, `crypto/mls_engine.rs` | §5.1, §5.2, §5.3 |
| F-13 | Admin Console | `infra/federation.rs`, `infra/metrics.rs` | §3.2, §5.1, §9.5, §9.6 |
| F-14 | Adaptive Network Management | `infra/relay.rs` | §9.2, §4.2 |
| F-15 | Crash-Safe WAL Management | `crdt/dag.rs`, `infra/wal_staging.rs` | §4.4, §7.1, §9.3, §12.2 |

**Orphan Feature Verification:** All 15 features have verified Core mappings. Zero orphan features.

---

### F-01: Secure E2EE Messaging

**Description:** Send and receive text messages encrypted end-to-end using MLS RFC 9420. The VPS relay receives only ciphertext — it has zero access to plaintext, sender identity, or content. DAG merge for large backlogs is time-sliced to prevent mobile ANR.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow:**

1. User types message. UI sends `UICommand::SendMessage { recipient_did, plaintext }` via FFI.
2. Rust Core looks up `Epoch_Key` from RAM `ZeroizeOnDrop` struct.
3. Core encrypts: `AES-256-GCM(Epoch_Key, plaintext)`. Nonce = `Base_Nonce XOR chunk_seq_number`.
4. Core constructs `CRDT_Event { id, parents, hlc, author_did, payload, signature }`. Ed25519 signature via `DeviceIdentityKey` in Secure Enclave (biometric gate required).
5. Event appended to `hot_dag.db` WAL atomically before network dispatch.
6. **Online path:** TLS 1.3 + mTLS → VPS Relay → `wal_staging.db` → pub/sub fanout.
7. **Offline path:** BLE Control Plane → Mesh Store-and-Forward (text only, ≤ 4 KB).
8. Core emits `CoreSignal::StateChanged { table: "messages", version }`.
9. UI issues `UICommand::ScrollViewport`. Core returns 20-message viewport snapshot.
10. Plaintext `ZeroizeOnDrop` after render frame.

**DAG Merge (Mobile — ANR Prevention):**

- Mobile hard limit: `MAX_MOBILE_MERGE_EVENTS = 3000`.
- Backlog > 3000: emit `CoreSignal::StateChanged` with `SnapshotRequired`; delegate full merge to Desktop via CRDT sync.
- Backlog > 500: `CoreSignal::DagMergeProgress { completed, total }` emitted every 200 ms. UI renders non-blocking progress banner. See OBSERVE-02 for full UI spec.
- Mobile merge is time-sliced in batches of 100 events with `tokio::task::yield_now()` between batches.
- Desktop: Rayon parallel merge in background Tokio task. No time-slicing needed.

**Dependencies:**

- REF: TERA-CORE §5.3 — MLS encrypt/decrypt, `Epoch_Key`, Ed25519 signing
- REF: TERA-CORE §7.1 — `CRDT_Event` schema, `hot_dag.db` append, nonce uniqueness
- REF: TERA-CORE §4.2 — `UICommand::SendMessage`, `CoreSignal::StateChanged`
- REF: TERA-CORE §9.2 — VPS relay, ALPN protocol selection
- REF: TERA-CORE §4.3 — FFI token protocol for viewport buffer transfer
- REF: TERA-FEAT §OBSERVE-02 — DAG merge progress UI contract

**Data Interaction:**

- Writes: `CRDT_Event` to `hot_dag.db` WAL; `WalStagingEntry` to `wal_staging.db` (relay).
- Reads: `Epoch_Key` from RAM; `cold_state.db` viewport for render.

**Constraints:**

- Plaintext never reaches server under any condition.
- Message delivery order determined by `HLC_Timestamp`, not server receipt time.
- Maximum unpadded plaintext before chunking: 4,096 bytes.
- Biometric authentication required to unlock `DeviceIdentityKey` for every signing operation.
- `CRDT_Event` immutable after append. No update or delete of raw events.

**Observability:**

- Signal: `CoreSignal::StateChanged { table: "messages", version }` on every DAG mutation.
- Signal: `CoreSignal::DagMergeProgress { completed, total }` every 200 ms when backlog > 500.
- Metric: `dag_merge_events_per_s`, `dag_append_p50_ms` (via OBSERVE-01 `ClientMetricBatch`).

**Failure Handling:** → §10.4 (Runtime), §10.1 (Network)

- Network unavailable at send: event durable in `hot_dag.db`. Retry on reconnect.
- MLS Epoch mismatch: Peer-Assisted Epoch Re-induction (TERA-CORE §5.3). Retry after `Welcome_Packet`.
- `Epoch_Key` unavailable: UI displays "Waiting for key sync…". Message held in `hot_dag.db`.

---

### F-02: Push Notification Delivery (E2EE)

**Description:** Deliver E2EE-encrypted push notifications to backgrounded devices. Decryption is local — APNs, FCM, and HMS never receive plaintext. A versioned Push Key Ladder handles key rotation without message loss.

**Supported Platforms:** 📱 iOS (NSE), 📱 Android (FCM), 📱 Huawei (HMS), 💻 macOS (daemon), 🖥️ Windows (WNS/daemon), 🖥️ Linux (systemd daemon)

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
2. NSE allocates Static Memory Arena (10 MB, pre-allocated at startup). All operations use arena.
3. NSE reads `Push_Key_N` from Shared Keychain (Access Group: `group.com.terachat.nse`).
4. NSE reads `push_key_version` from payload header.
5. **Version match:** AES-256-GCM decrypt in arena → display OS notification → `ZeroizeOnDrop` arena.
6. **Version mismatch (Versioned Key Ladder):**
   - Cache raw ciphertext to `nse_staging.db`.
   - Set `main_app_decrypt_needed = true` in Shared Keychain.
   - Send `content-available: 1` wake signal.
   - Main App wakes → rotates `Push_Key` → decrypts `nse_staging.db` → displays notification → clears staging.

**User Flow (Desktop daemon):**

1. Relay delivers encrypted payload to `terachat-daemon`.
2. Daemon decrypts payload preview using cached `Epoch_Key`.
3. Daemon triggers OS-native notification (macOS `UNUserNotificationCenter` / Windows Toast / Linux libnotify).
4. Plaintext zeroed immediately after notification dispatch.
5. Full DB sync occurs only when Tauri UI process is active.

**Ghost Push Skeleton (NSE payload too large):**

- Trigger: `payload_size > 4 KB` OR `epoch_delta > 1`.
- NSE displays "Decrypting securely…" notification (no content).
- Sets `main_app_decrypt_needed = true` in Shared Keychain.
- Main App handles full decryption in foreground (2 GB RAM; no NSE constraints).

**State Machine:** → §5.5 (Push Notification State Machine)

**Dependencies:**

- REF: TERA-CORE §5.5 — Push Key Ratchet, Versioned Key Ladder, NSE RAM budget protocol
- REF: TERA-CORE §5.3 — MLS Epoch, `Push_Key` rotation after epoch change
- REF: TERA-CORE §8.3 — iOS NSE inbound message flow
- REF: TERA-CORE §4.2 — `CoreSignal::StateChanged` after Main App decryption

**Data Interaction:**

- Reads: `Push_Key_N` from Secure Enclave / StrongBox / Shared Keychain.
- Writes (iOS mismatch path): raw ciphertext to `nse_staging.db`; flag in Shared Keychain.
- Clears: `nse_staging.db` entry after successful Main App decrypt.

**Constraints:**

- iOS NSE: Static Memory Arena 10 MB. All decryption reuses arena buffers.
- Android 14+: FCM `priority = "high"` AND Companion Device Manager `REQUEST_COMPANION_RUN_IN_BACKGROUND`. Both required — either alone is insufficient.
- Huawei: CRL refresh delay ≤ 4 h vs ≤ 30 min on iOS/Android. Must be disclosed in enterprise SLA documentation.
- iOS Keychain access group `group.com.terachat.nse` accessible by NSE only. Main App and Share Extension cannot read `Push_Key` from this group.

**Security Notes:**

- `Push_Key` version must be read from payload header before any decryption attempt.
- `Push_Key` struct modifications require `version: u32` field; NSE validates version before use.
- `Push_Key` accessible only from `group.com.terachat.nse` keychain group. Cross-group read: **blocker** (SEC-05).

**Observability:**

- Metric: `nse_circuit_breaker_trips`, `push_key_version_mismatches` (OBSERVE-01).
- Log: `HUAWEI_CRL_STALE` on Huawei CRL-dependent decryption failure.

**Failure Handling:** → §10.3 (Key Failure)

- NSE OOM: Circuit Breaker terminates NSE gracefully. Sets `main_app_decrypt_needed = true`. Main App handles on next foreground.
- `Push_Key` not found in Keychain: display generic "New message" notification with no content preview.
- HMS polling delay (Huawei): log `HUAWEI_CRL_STALE` and defer decrypt to next foreground with refreshed CRL.

---

### F-03: IPC Bridge and State Synchronization

**Description:** All communication between Rust Core and the UI layer routes through a strict unidirectional IPC bridge. Core emits typed `CoreSignal` enums; UI sends typed `UICommand` enums. No raw pointer crosses the FFI boundary. The Dart FFI `TeraSecureBuffer` wrapper is mandatory on Android/Huawei (PLATFORM-17).

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

**Desktop Tauri IPC Tier Ladder (automatic):**

```text
Tier 1: SharedArrayBuffer (COOP+COEP verified)      → ~500 MB/s
Tier 2: Named Pipe (Windows; or SAB unavailable)    → ~200 MB/s
Tier 3: Protobuf over stdin (last resort)           → ~50 MB/s
```

Rust Core detects SAB availability at init and selects the highest tier. UI is unaware of tier. Tier selection is written to the audit trail (IPC-02).

**User Flow:**

1. Rust Core completes a DAG update.
2. Core emits `CoreSignal::StateChanged { table: &str, version: u64 }`.
3. UI issues `UICommand::ScrollViewport { top_message_id, bottom_message_id }`.
4. Core fetches 20-message viewport from `cold_state.db`.
5. Core calls `tera_buf_acquire(operation_id)` → returns opaque `u64` token.
6. Core writes decrypted snapshot to Data Plane buffer.
7. UI reads via token reference. Renders viewport.
8. UI calls `UICommand::ReleaseBuffer { token }` → Core `ZeroizeOnDrop` when `ref_count == 0`.

**Dart FFI Contract (PLATFORM-17 — mandatory, supersedes PLATFORM-14):**

- Every `TeraSecureBuffer` MUST be wrapped by `useInTransaction()`. Direct `.toPointer()` outside wrapper → CI lint error (blocker).
- Rust Token Registry does NOT auto-expire/zeroize tokens. On TTL timeout: emit `IpcSignal::TransactionTimeout`. UI displays: "Session expired — please retry."
- GC Finalizer is safety net only. GC release → WARNING metric (`ffi.gc_finalizer_release.count`) + log. Not primary path.
- Explicit `releaseNow()` is the primary release path. `useInTransaction()` calls it in `finally` block.

**CoreSignal and UICommand catalogs:** → §6.1 and §6.2

**Dependencies:**

- REF: TERA-CORE §4.2 — `CoreSignal` and `UICommand` enum definitions, unidirectional contract
- REF: TERA-CORE §4.3 — FFI Token Protocol (`tera_buf_acquire` / `tera_buf_release`)
- REF: TERA-CORE §2.2 — Shared Rust Core principle, Data Plane throughput targets, SAB Tier Ladder
- REF: TERA-FEAT §PLATFORM-17 — Dart FFI `TeraSecureBuffer` wrapper spec

**Data Interaction:**

- Reads: `cold_state.db` for viewport snapshots.
- Buffer transfers: `DataPlane_Payload` via SAB / JSI pointer / Dart FFI.
- No writes: IPC bridge is read-only at the feature layer.

**Constraints:**

- No `Vec<u8>`, `*const u8`, or `*mut u8` returned from any `pub extern "C"` function. Enforced by CI Clippy lint (SEC-02). Lint failure: **blocker**.
- SAB Tier 1 requires `COOP+COEP` HTTP headers on Desktop. Auto-downgrade to Tier 2 on failure.
- UI never holds decrypted payloads beyond the render frame.
- `CoreSignal` emission is fire-and-forget. Core does not wait for UI acknowledgment.

**Security Notes:**

- SEC-02: No raw pointer in `pub extern "C"`. Enforced by custom Clippy lint `tera_ffi_raw_pointer`.
- IPC-01: State flow unidirectional Core → UI. Bidirectional state channel: **blocker**.
- IPC-02: SAB Tier Ladder selection logged to audit trail. Silent tier selection: **blocker**.
- IPC-03: `CoreSignal::DagMergeProgress` emitted every 200 ms when merge backlog > 500 events.

**Observability:**

- Metric: `ipc_buf_acquire_p50_us`, `ipc_buf_acquire_p99_us` (OBSERVE-01).
- Metric: `ffi.gc_finalizer_release.count` — WARNING indicator; GC release is a code smell.
- Audit: SAB tier selection written to audit trail on every `CoreSignal::TierChanged`.

**Failure Handling:** → §10.4 (Runtime)

- SAB unavailable: auto-downgrade to Named Pipe (~200 MB/s). Log tier change to audit trail.
- Named Pipe unavailable: downgrade to Protobuf-over-stdin (~50 MB/s). Log tier change.
- Token not found on `ReleaseBuffer`: return `BufferNotFound`; UI re-issues `ScrollViewport`.

---

### F-04: Local Storage Management

**Description:** Manage the two-tier SQLite storage system (`hot_dag.db` + `cold_state.db`): WAL anti-bloat, crash-safe schema migrations, and shadow paging hydration.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow — WAL Auto-Compaction:**

1. Rust Core monitors WAL file size every 60 s via background Tokio task.
2. If WAL > 50 MB (mobile) or > 200 MB (desktop): trigger VACUUM sequence.
3. **Mobile:** Register BGTask (iOS) / WorkManager (Android). Execute when device is charging AND screen is off.
4. **Foreground opportunistic path (primary reliability path):** If app idle > 60 s and WAL > 50 MB, spawn low-priority Tokio task. Execute `VACUUM INTO hot_dag_tmp.db`. Atomic POSIX `rename()` swap. Task self-cancels on user interaction within 5 s.
5. Emit `CoreSignal::StateChanged` after VACUUM completes.

**User Flow — Schema Migration:**

1. On DB open: read `PRAGMA user_version` from `hot_dag.db`.
2. If `user_version < CURRENT_SCHEMA_VERSION`:
   - a. Create backup: `{db_path}.bak.v{current_version}`.
   - b. `db.execute_batch("BEGIN EXCLUSIVE TRANSACTION")`.
   - c. Run migration scripts in version order.
   - d. `PRAGMA user_version = CURRENT_SCHEMA_VERSION`.
   - e. `COMMIT`.
3. If `cold_state.db` migration fails: **drop file and rebuild from `hot_dag.db`** (DB-02). Never abort without a recovery path.

**User Flow — Shadow Paging Hydration:**

1. Core receives `Snapshot_CAS` reference for a new snapshot.
2. Download snapshot in 2 MB chunks to `cold_state_shadow.db`.
3. Verify: `SHA-256(downloaded_content) == cas_uuid`. Reject and restart on mismatch.
4. On full verification: atomic `rename(cold_state_shadow.db → cold_state.db)`.
5. Emit `CoreSignal::StateChanged { table: "all", version }`.
6. If download interrupted mid-way: delete `cold_state_shadow.db`; `cold_state.db` unchanged. Resume from last `Hydration_Checkpoint`.

**Hot DAG Eviction Policy:**

- 7-day structural eviction trigger is **suspended** when `Mesh_Partition_Active == true`.
- Standard eviction triggers only after `tombstone.clock ≤ MVC` (TERA-CORE §17.1).
- Hydration batch scheduling uses exponential backoff with jitter on `HydrationScheduler`.

**Shadow DB Write Lock Protocol (iOS race prevention):**

```rust
pub struct ShadowMigrationLock {
    migration_in_progress: AtomicBool,
}
// NSURLSession completion handler checks lock before writing.
// If migration in progress: queue write to hot_dag.db instead of cold_state_shadow.db.
// Guarantees no race between atomic shadow rename and NSURLSession background write.
```

**Dependencies:**

- REF: TERA-CORE §7.1 — `hot_dag.db` and `cold_state.db` structure, migration protocol, append-only invariant
- REF: TERA-CORE §7.4 — Materialized Snapshot, CAS verification, O(1) recovery bootstrap
- REF: TERA-CORE §12.2 — DB-01 (migration), DB-02 (rebuild safety net), DB-03 (autocheckpoint)

**Data Interaction:**

- Writes: `CRDT_Event` to `hot_dag.db`; materialized state to `cold_state.db`; chunks to shadow during hydration.
- Reads: `cold_state.db` for all viewport rendering; `hot_dag.db` for DAG operations and recovery.

**Constraints:**

- `cold_state.db`: SQLCipher AES-256. Key derived from Secure Enclave — never hardcoded, never stored in plaintext.
- `hot_dag.db`: append-only. Physical deletion forbidden. Tombstones only.
- `PRAGMA wal_autocheckpoint = 1000` enforced on all SQLite databases (DB-03).
- `VACUUM INTO` guarantees zero downtime: creates clean copy, then atomic swap. Reads and writes are never blocked.
- BGTask execution at iOS scheduler's discretion. Foreground opportunistic VACUUM is primary reliability path.

**Versioning:** → §11 (Versioning & Migration)

**Observability:**

- Signal: `CoreSignal::MemoryPressureWarning` when WAL > 200 MB (mobile).
- Signal: `CoreSignal::StateChanged { table: "all" }` after VACUUM or hydration.
- Metric: `wal_size_mb` (bucketed) via OBSERVE-01.
- Log: `COLD_STATE_REBUILD` when cold_state.db is dropped and rebuilt.

**Failure Handling:** → §10.2 (Storage Failure)

- WAL bloat > 200 MB (mobile): emit `CoreSignal::MemoryPressureWarning`. UI banner: "Storage cache is full — TeraChat will clean up when charging."
- VACUUM fails: log error, retry on next trigger. Do not crash.
- Schema migration fails on `cold_state.db`: drop file, rebuild from `hot_dag.db`. Log `COLD_STATE_REBUILD`.
- Hydration interrupted: delete `cold_state_shadow.db`; restart from `Hydration_Checkpoint`.

---

### F-05: Survival Mesh Networking

**Description:** When Internet is unavailable, TeraChat activates a BLE 5.0 / Wi-Fi Direct peer-to-peer Mesh for offline text messaging via Store-and-Forward. WASM plugins, AI inference, voice calls, and multi-hop file transfer are suspended.

**Supported Platforms:** 📱 iOS (Leaf/EMDP), 📱 Android (Relay), 📱 Huawei (Relay), 💻 macOS (Super Node), 🖥️ Windows (Super Node), 🖥️ Linux (Super Node)

**User Flow — Activation:**

1. Rust Core detects all three ALPN paths unavailable.
2. Core emits `CoreSignal::TierChanged { new_tier: MeshMode, reason: NoInternet }`.
3. UI transitions to Mesh Mode visual state.
4. User confirms Mesh activation (required: OS BLE permission prompt).
5. Core calls host adapter FFI: `request_mesh_activation()`. Swift/Kotlin starts BLE advertising and scanning.
6. Devices within range discover each other via BLE Stealth Beacons.
7. Text messages route via BLE Store-and-Forward (payload ≤ 4 KB per hop).
8. Files and media: P2P Wi-Fi Direct only, < 20 m range. UI: "Send files only when nearby."

**Role Assignment (deterministic — no voting rounds):**

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
// Border Node: auto-assigned to any device with both internet_available == true
//              and ble_active == true. No explicit assignment required.
```

**State Machine:** → §5.2 (Mesh Role State Machine), §5.1 (Network Tier State Machine)

**Store-and-Forward Quotas:**

| Role | Storage Quota | Message TTL |
|---|---|---|
| Super Node (Desktop) | 500 MB – 1 GB | 48 – 72 h |
| Relay Node (Android) | 100 MB | 24 h |
| Leaf Node (iOS) | 50 MB, receive-only | N/A |
| Tactical Relay (EMDP iOS) | 1 MB, text-only CRDT buffer | 60 min |

**iOS Super Node Handover (Jetsam prevention):**

1. iOS detects memory pressure approaching Jetsam threshold.
2. Core broadcasts `MeshRoleHandover { candidate_node_id }` via BLE Control Plane to Desktop/Android.
3. Receiving node assumes Super Node role immediately.
4. iOS reverts to Leaf Node.
5. Core emits `CoreSignal::MeshRoleChanged { new_role: LeafNode }`.
6. UI displays: "Relay role transferred to [device name]."

**EMDP (Emergency Mobile Dictator Protocol):**

- Activation: no Desktop present; Internet unavailable; ≥ 2 iOS devices; battery > 20%.
- Tactical Relay selected by: `max(battery_pct × 100 + (ble_rssi + 100))`.
- Hard constraints: text-only, 1 MB buffer, TTL 60 min, no DAG merge, no MLS Epoch rotation.
- TTL extension (at T-10 min): broadcast `EMDP_TTL_EXTENSION_REQUEST`; peer with battery > 30% accepts; encrypted CRDT buffer transferred via BLE Data Plane; new Tactical Relay assumes role with TTL reset.
- Key Escrow: before Desktop goes offline, it encrypts `EmdpKeyEscrow { relay_session_key, emdp_start_epoch, expires_at }` for iOS Relay via ECIES/Curve25519, transmitted over BLE. On Desktop reconnect: decrypt and merge orphaned messages into main DAG.

**Mesh Mode Feature Restrictions (hard limits, enforced by Rust Core — not UI):**

| Feature | Mesh Mode Status | Error Code |
|---|---|---|
| WASM `.tapp` execution | Terminate immediately; snapshot to sled | N/A |
| AI / SLM inference | Disabled | `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` |
| Voice and video calls | Suspended | N/A |
| File transfer (multi-hop) | Suspended | N/A |
| File transfer (P2P Wi-Fi Direct, < 20 m) | Available | N/A |
| Inter-`.tapp` Delegation Tokens | Suspended | `ERR_MESH_MODE_DELEGATION_SUSPENDED` |
| Transient state persistence | Disabled | N/A |
| MLS Epoch rotation | Suspended (EMDP mode) | N/A |
| DAG merge | Deferred to Desktop reconnect | N/A |

**Dependencies:**

- REF: TERA-CORE §6.1 — `MeshTransport` trait, platform adapters, payload routing
- REF: TERA-CORE §6.2 — Mesh topology, role assignment, Store-and-Forward quotas
- REF: TERA-CORE §6.3 — BLE Stealth Beaconing, duty cycle, MAC rotation
- REF: TERA-CORE §6.4 — iOS AWDL conflict resolution, pre-emptive warning
- REF: TERA-CORE §6.5 — BLAKE3 Dictator Election, Causal Freeze, failover
- REF: TERA-CORE §6.6 — Byzantine quarantine, PoW anti-spam, Shun propagation
- REF: TERA-CORE §6.7 — EMDP full protocol, Key Escrow handshake, TTL Extension

**Data Interaction:**

- Writes: `CRDT_Event` (text) to `hot_dag.db`; `EmdpKeyEscrow` via BLE Data Plane (encrypted).
- Reads: `BLE_Stealth_Beacon`; `Shun_Record` from `hot_dag.db` (to reject quarantined peers).

**Constraints:**

- iOS `election_weight = 0`. Hardcoded in `mesh/election.rs`. Never changed. Any PR modifying: **blocker** (FI-05).
- BLE MTU: 512 bytes. PQ-KEM key exchange requires RaptorQ (RFC 6330) fragmentation.
- SOS messages: exempt from all PoW. Zero latency cost.
- Unsigned Shun Records: silently dropped (prevents false-flag Byzantine attacks).

**Observability:**

- Signal: `CoreSignal::TierChanged { new_tier, reason }` on every Mesh activation or ALPN change.
- Signal: `CoreSignal::MeshRoleChanged { new_role }` on role transition.
- Signal: `CoreSignal::EmdpExpiryWarning { minutes_remaining }` at T-10 min and T-2 min.
- Signal: `CoreSignal::DeadManWarning { hours_remaining }` at T-12 h and T-1 h offline.

**Failure Handling:** → §10.1 (Network Failure)

- All-iOS Mesh, no EMDP conditions: Causal Freeze (read-only). No DAG writes until non-iOS node joins.
- iOS AWDL disabled (Hotspot/CarPlay): downgrade to BLE-only Tier 3; queue voice packets (TTL 90 s if CallKit session active; 30 s otherwise); emit `CoreSignal::TierChanged`.
- EMDP TTL expired, no hand-off found: enter SoloAppendOnly mode. Merge deferred.
- Byzantine Shun received for own `Node_ID`: verify Enterprise CA signature before applying. Unsigned Shun Records are dropped.

---

### F-06: Voice and Video Calls (WebRTC)

**Description:** Peer-to-peer encrypted voice and video calls via WebRTC DTLS-SRTP. SDP signaling is exchanged over the MLS E2EE channel — no separate signaling server. The TURN relay is blind (relays encrypted UDP only).

**Supported Platforms:** 📱 iOS (CallKit required), 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow:**

1. Caller presses call button. UI sends `UICommand::SendMessage` with `content_type: CallOffer`.
2. SDP offer/answer exchanged over MLS E2EE channel (same channel as text messages).
3. ICE candidates gathered from Pre-warmed ICE Pool. Setup perceived latency: ~0 s.
4. DTLS-SRTP session established. Call active.
5. iOS: `CXProvider` (CallKit) keeps audio session alive regardless of background state.
6. On call end: DTLS-SRTP torn down; ICE candidates cleared from pool; no persistent write.

**iOS Dual TURN Preconnect:**

When a CallKit session is active and app is about to enter background:

1. `CXCallObserver` FFI callback detects upcoming background transition.
2. Rust Core proactively connects to secondary TURN server as backup.
3. Primary TURN failure → immediate failover to secondary. User-perceived drop: 0 s.

**iOS AWDL/Hotspot Conflict During Active Call:**

1. `NWPathMonitor` detects tethering interface appearing (1–2 s window before AWDL drops).
2. Core emits `CoreSignal::TierChanged { reason: HotspotConflictImminent }`.
3. UI presents: "Enabling Hotspot will interrupt the Mesh call — continue?" (3 s auto-dismiss).
4. If user proceeds (or auto-dismiss): downgrade to BLE-only Tier 3; queue voice packets TTL 90 s.
5. After 90 s with no AWDL recovery: call drops. Notification: "Call ended — Hotspot is active."

**Mesh Mode behavior:** Voice calls not available in Mesh Mode. BLE cannot carry audio stream. UI: "Voice calls require an Internet connection."

**Dependencies:**

- REF: TERA-CORE §5.3 — SDP signaling over MLS E2EE channel
- REF: TERA-CORE §6.4 — iOS AWDL conflict, pre-emptive warning, CallKit exception
- REF: TERA-CORE §10.4 — TURN HA sizing (Keepalived Floating IP, 3 s failover), Dual TURN Preconnect
- REF: TERA-CORE §9.2 — ALPN negotiation for TURN path selection

**Data Interaction:**

- Reads: `Epoch_Key` for SDP exchange encryption; ICE candidate pool from Core network state.
- Writes: none persistent (ephemeral ICE/DTLS state only; no DB writes during call).

**Constraints:**

- iOS: `CallKit` integration is mandatory. Without it, iOS kills network after 30 s background (PLT-03).
- TURN server: relays encrypted UDP only — holds no decryption keys.
- TURN node sizing: 1 node ~50 concurrent HD streams (4 vCPUs, 8 GB RAM, 1 Gbps NIC).

**Failure Handling:** → §10.1 (Network Failure)

- TURN failover: Keepalived Floating IP activates in < 3 s. Dual preconnect eliminates user-perceived drop.
- All TURN paths fail: attempt direct P2P STUN connection. Notify user "Call quality degraded."
- CallKit session interrupted by system event: `CXProvider` handles audio session restoration; Core re-establishes DTLS-SRTP.

---

### F-07: WASM Plugin Sandbox (`.tapp` Lifecycle)

**Description:** Execute untrusted third-party mini-apps (`.tapp`) inside a WASM sandbox with capability-based isolation. Sandbox has no direct access to network, filesystem, or DAG buffer. All outbound requests route through Rust Core's Host Proxy.

**Supported Platforms:** 📱 iOS (`wasm3`), 📱 Android (`wasmtime`), 📱 Huawei (`wasmtime`), 💻 macOS (`wasmtime` in XPC Worker), 🖥️ Windows (`wasmtime`), 🖥️ Linux (`wasmtime`)

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
3. Platform WASM runtime initialized:
   - iOS: `wasm3` interpreter. No JIT. No dynamic code generation.
   - Android / Huawei / Desktop: `wasmtime` JIT (Cranelift backend).
   - macOS: `wasmtime` in XPC Worker (`com.apple.security.cs.allow-jit = true`). Main App: `NO allow-jit`.
4. Sandbox launched: `PROT_READ`-only access to DAG shared memory. Write attempts to DAG buffer trigger `SIGSEGV` caught by `catch_unwind`.
5. Host Bindings established: all WASM network access routes through `terachat_proxy_request()` → OPA policy check → Rust Core Tokio client → sanitized `Vec<ASTNode>` response.

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

**Observability:**

- Signal: `CoreSignal::ComponentFault { component, severity }` on sandbox panic or XPC crash.
- Signal: `CoreSignal::XpcHealthDegraded { crash_count, window_secs }` when XPC crash rate exceeds threshold.
- Metric: `wasm_sandbox_crashes` (OBSERVE-01).
- Audit: all OPA policy checks for egress requests.

**Failure Handling:** → §10.4 (Runtime Failure)

- WASM sandbox panic: `catch_unwind` at entry boundary. Emit `CoreSignal::ComponentFault`. Restart after 1 s.
- Heap exhaustion: OOM kills sandbox. Attempt transient state save before kill. Core unaffected.
- Rate limit exhausted: SUSPEND `.tapp`; return `ERR_RATE_LIMIT_EXCEEDED`; resume after 60 s.
- XPC Worker crash (macOS): recover from `XpcJournalEntry` state. Max 3 retries then `XpcPermanentFailure`.

---

### F-08: Inter-`.tapp` IPC and Delegation Tokens

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

---

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

```rust
pub fn select_whisper_tier(available_ram_mb: u32, battery_pct: u8) -> WhisperModelTier {
    if battery_pct < 20    { return WhisperModelTier::Disabled; }
    if available_ram_mb > 200 { return WhisperModelTier::Base; }  // 74 MB
    if available_ram_mb > 100 { return WhisperModelTier::Tiny; }  // 39 MB
    WhisperModelTier::Disabled
}
// On Disabled: emit CoreSignal::StateChanged with note "Voice transcription unavailable."
```

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

- iOS cannot load dynamic WASM AI modules (App Store Rule 2.5.2).
- AI features shipped as `.mlmodelc` CoreML bundles inside the app binary.
- Marketplace "install": OPA Policy JSON pushed to unlock the pre-bundled CoreML module.
- Unlock latency: < 1 s. User experience identical to Android/Desktop.

**Prompt Injection Defense:**

- Rust Core wraps LLM response in `Vec<ASTNode>` (AST Sanitizer). Raw HTML, inline Markdown with external image tracking URLs, and executable content are rejected.
- On 3rd `TAINTED` flag within a session: suspend the offending `.tapp` and emit `CoreSignal::ComponentFault`.

**ONNX Model Integrity (PLATFORM-18):** → §4 PLATFORM-18

All ONNX model loads MUST pass `OnnxModelLoader.load_verified()`: manifest Ed25519 signature check → RAM availability check → BLAKE3 hash verification → isolated ORT session initialization → `ZeroizeOnDrop` on model bytes.

**ONNX Offload Protocol (INFRA-01):** → §4 INFRA-01

Mobile offloads ONNX to Desktop Super Node via E2EE `CRDT_Event` with HMAC-BLAKE3 authentication.

**Dependencies:**

- REF: TERA-CORE §3.3 — `MemoryArbiter`, RAM budget matrix, Whisper tier protocol
- REF: TERA-CORE §3.6 — AI infrastructure, Micro-NER, `SessionVault` `ZeroizeOnDrop`
- REF: TERA-CORE §4.4 — `catch_unwind` boundary at AI worker entry; crash isolation
- REF: TERA-FEAT §PLATFORM-18 — ONNX Model Integrity verification spec
- REF: TERA-FEAT §INFRA-01 — Mobile ONNX offload protocol

**Data Interaction:**

- Reads: user message context (local, not uploaded to server); LLM API response.
- Writes: inference result to `.tapp` via sanitized `Vec<ASTNode>`; alias map in `SessionVault` (RAM, `ZeroizeOnDrop`).

**Failure Handling:** → §10.4 (Runtime)

- ONNX allocator OOM: graceful fallback to Flat-search. Log `ONNX_OOM_FALLBACK`.
- LLM cloud unreachable: return `ERR_AI_CLOUD_UNAVAILABLE`. Surface local-only fallback if available.
- AST Sanitizer rejects response: return `ERR_AI_RESPONSE_TAINTED`. `.tapp` suspended after 3rd violation.
- BLAKE3 hash mismatch on model load: terminate AI worker; emit `CoreSignal::ComponentFault { severity: Critical }`. Log `AuditEvent::ModelIntegrityViolation`.
- `InsufficientRam` for model tier: log `ONNX_RAM_DENIED`; select lower tier or disable AI for session.

---

### F-11: Device Security

**Description:** Client-side security controls: screen capture prevention, Protected Clipboard Bridge, biometric screen lock, Remote Wipe, and cryptographic self-destruct.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

#### F-11a: Screen Capture Prevention

| Platform | API | Mechanism |
|---|---|---|
| 📱 iOS | `UIScreen.capturedDidChangeNotification` | On `isCaptured == true`: apply `UIBlurEffect(.dark)` over all content |
| 📱 Android | `WindowManager.LayoutParams.FLAG_SECURE` in `Activity.onCreate()` | Kernel-level Compositor blocks all capture; returns black frame |
| 📱 Huawei | HarmonyOS `WindowManager` secure flag | Same mechanism as Android |
| 💻 macOS | `CGDisplayStream` monitoring | On capture detected: blur overlay applied within 1 frame (< 16 ms) |
| 🖥️ Windows | DXGI duplication detection | On capture detected: blur overlay |
| 🖥️ Linux | Wayland compositor security hint | Platform best-effort; log `LINUX_SCREEN_CAPTURE_UNSUPPORTED` if not available |

#### F-11b: Protected Clipboard Bridge

All clipboard operations route through Rust Core's bridge. Direct OS clipboard API calls from Core: **blocker** (SEC-03).

| Platform | Backend | Detection Mechanism |
|---|---|---|
| 📱 iOS | `UIPasteboard` | N/A |
| 📱 Android | `ClipboardManager` | N/A |
| 📱 Huawei | HarmonyOS PasteBoard | N/A |
| 💻 macOS | `NSPasteboard` | N/A |
| 🖥️ Windows | Win32 `SetClipboardData` | N/A |
| 🖥️ Linux Wayland | `wl-clipboard` (`wl-copy`/`wl-paste`) | `WAYLAND_DISPLAY` env var present |
| 🖥️ Linux X11 | `xclip` / `xsel` | `WAYLAND_DISPLAY` env var absent |

On copy: Core writes to OS clipboard via bridge. Clipboard cleared after 60 s automatically.

#### F-11c: Biometric Screen Lock

- All SQLite I/O blocked until biometric gate clears (iOS `kSecAccessControlBiometryCurrentSet` / Android `BiometricPrompt`).
- PIN fallback: 6 digits. Transmitted via FFI Pointer — never through UI state buffer. `ZeroizeOnDrop` after each digit.
- Maximum PIN failures: 5. On 5th: Cryptographic Self-Destruct.

**State Machine:** → §5.6 (Device PIN Failure State Machine)

#### F-11d: Remote Wipe

Trigger: `self.userID` in `removedMembers` of any MLS Commit.

**Execution sequence (non-interruptible):**

1. Delete `DeviceIdentityKey` from Secure Enclave / StrongBox / TPM 2.0.
2. Drop all tables in `hot_dag.db` and `cold_state.db`.
3. Delete all WASM sandbox storage files.
4. Wrapped in `autoreleasepool` (iOS) / `try-finally` (Android). Cannot be interrupted by user process.

#### F-11e: Cryptographic Self-Destruct

- `Failed_PIN_Attempts` counter encrypted with `Device_Key`. Ceiling: 5.
- On 5th failure: Crypto-Shredding of all local DBs + `OIDC_ID_Token` + both `DeviceIdentityKey` wrappers → Factory Reset state.

**Dependencies:**

- REF: TERA-CORE §5.1 — Remote Wipe execution, Dead Man Switch, self-destruct trigger
- REF: TERA-CORE §5.2 — Biometric-bound key init, Double-Buffer Zeroize, Dual-Wrapped KEK
- REF: TERA-CORE §12.4 — PLT-04 (clipboard bridge mandate)

**Constraints:**

- Screen capture prevention overlay: applied within 1 frame (< 16 ms at 60 Hz).
- Clipboard bridge is mandatory for all platforms. Direct OS clipboard calls from Core: **blocker** (SEC-03).
- Linux clipboard: detect display server at runtime (`WAYLAND_DISPLAY`). Hardcoded single backend: **blocker** (PLT-05).

**Failure Handling:** → §10.3 (Key Failure)

- Biometric sensor unavailable: fall back to Enterprise PIN. 5-attempt maximum.
- Remote Wipe partial execution (power loss mid-sequence): on next boot, detect `wipe_in_progress` flag in secure storage; complete remaining steps before presenting any UI.
- `Failed_PIN_Attempts` counter corrupted: treat as 5 failures; initiate self-destruct. Log `PIN_COUNTER_CORRUPTED` to TeraDiag before wipe.

---

### F-12: Identity, Onboarding, and Recovery

**Description:** Device enrollment into a TeraChat workspace, identity verification, and recovery flows for lost or replaced devices.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow — Initial Enrollment:**

1. Admin generates enrollment token (mTLS Certificate, TTL 12–24 h).
2. New device: user scans QR code or enters token.
3. Device generates `DeviceIdentityKey` inside Secure Enclave / StrongBox (biometric required).
4. Device submits `Proof_of_Identity_and_Device` (signed `OIDC_ID_Token`) to server.
5. Server issues mTLS certificate. Device added to workspace MLS group.
6. `Company_Key` delivered via MLS `Welcome_Packet` (ECIES/Curve25519-encrypted for new device).

**User Flow — Recovery (Admin-Approved QR):**

1. Admin authenticates biometrically on their device.
2. Admin generates `Ed25519 Signed Recovery Ticket` (single-use, TTL 15 min).
3. New device scans QR. Rust Core verifies Ed25519 signature before any action.
4. New device generates fresh `DeviceIdentityKey`.
5. Core downloads encrypted `cold_state.db` backup. Decrypts with new `DeviceIdentityKey` (backup re-keyed to new device during ticket validation).

**User Flow — Recovery (BIP-39 Mnemonic Fallback):**

1. User enters 24-word BIP-39 mnemonic AND biometric authentication (both required).
2. Core derives: `Recovery_Key = BIP39_seed(mnemonic) || biometric_binding`.
3. `DeviceIdentityKey` reconstructed locally from `Recovery_Key`.
4. Restore `cold_state.db` from local backup (if available) or full sync on next connection.

**Geofencing and Network Fencing:**

- Short-lived mTLS certificates (TTL 12–24 h) act as implicit network fencing.
- On mTLS cert expiry or VPN disconnect: Rust Core automatically disables Relay role.
- No UI prompt required; role change emits `CoreSignal::MeshRoleChanged`.

**Dependencies:**

- REF: TERA-CORE §5.1 — KMS Bootstrap, `Company_Key` derivation, `Welcome_Packet` delivery
- REF: TERA-CORE §5.2 — `DeviceIdentityKey` generation, biometric binding, `Proof_of_Identity_and_Device`
- REF: TERA-CORE §5.3 — MLS group join, `Re-Add_Member` handshake for returning devices

**Data Interaction:**

- Writes: `DeviceIdentityKey` to Secure Enclave/StrongBox; `CRDT_Event` of type `GroupOp:MemberAdd` to `hot_dag.db`.
- Reads: Recovery Ticket Ed25519 signature; `cold_state.db` backup; mTLS certificate store.

**Constraints:**

- Recovery Ticket: single-use, TTL 15 min. Expired tickets rejected by Core.
- BIP-39 recovery requires mnemonic AND biometric — neither is sufficient alone.
- Short-lived mTLS certificates must be renewed within their TTL window. Expired cert = Relay role disabled.

**Failure Handling:** → §10.3 (Key Failure)

- Enrollment token expired (> 12–24 h): Admin generates new token.
- Recovery Ticket signature invalid: reject; log `INVALID_RECOVERY_TICKET` to Audit Log.
- BIP-39 phrase incorrect: return `ERR_MNEMONIC_INVALID`. No attempt count limit (brute force protected by mandatory biometric gate).

---

### F-13: Admin Console and Enterprise Controls

**Description:** Centralized management interface for workspace administrators: policy, device management, user offboarding, audit, and license management. Client-side observability integration is defined in OBSERVE-01.

**Supported Platforms (full access):** 💻 macOS, 🖥️ Windows, 🖥️ Linux, 🗄️ Bare-metal
**Supported Platforms (read-only):** 📱 iOS, 📱 Android, 📱 Huawei

**Admin Console Feature Set:**

| Feature | Description | Access Level |
|---|---|---|
| Device enrollment management | Issue / revoke mTLS certificates | Admin: full |
| User offboarding (SCIM 2.0) | Auto-remove from MLS groups on HR event | Server: auto |
| OPA Policy management | Define and push ABAC policies to devices | Admin: full |
| Remote Wipe | Initiate `removedMembers` MLS Commit | Admin: full |
| Audit Log viewer | Ed25519-signed tamper-proof entries | Admin: read-only |
| License management | View / renew License JWT; seat count | Admin: full |
| Mesh topology view | Real-time node roles and connectivity | Admin: read-only |
| Software crypto warning | Alert when device uses SW backend | Auto: emit on detect |
| Dead Man Switch policy | Configure grace period per user group | Admin: full |
| Federation management | Invite / revoke federated clusters | Admin: full |
| Whisper tier dashboard | Shows which devices have AI disabled | Admin: read-only |
| Observability opt-out | Disable telemetry via OPA: `{"telemetry.enabled": false}` | Admin: full |

**SCIM 2.0 Auto-Offboarding Flow:**

1. HR system sends `SCIM DELETE /Users/{id}` to TeraChat SCIM Listener.
2. Core emits MLS `removedMembers` Commit for all of user's enrolled devices.
3. Remote Wipe triggered on all devices (F-11d execution sequence).
4. Audit Log records offboarding event with Ed25519 signature.
5. Admin receives Admin Console notification.

**License Lockout Behavior:**

- T+0 (expiry): active calls and messaging continue. Admin Console features lock.
- T+90 days: relay rejects new bootstraps. Running sessions survive until restart.
- On renewal: JWT replaced in Admin Console → Rust verifies → all features restore within 5 s. No restart required.

**Dependencies:**

- REF: TERA-CORE §5.1 — Remote Wipe, Dead Man Switch policy configuration
- REF: TERA-CORE §3.2 — Backend Services, OPA/ABAC, SCIM Listener
- REF: TERA-CORE §9.5 — Audit Log (PostgreSQL), TERA-CORE §9.6 — Operational Metrics
- REF: TERA-FEAT §OBSERVE-01 — Client-side observability integration

**Constraints:**

- Mobile Admin Console: read-only. No policy changes from mobile. Policy mutations require Desktop.
- License lockout at T+0 does NOT interrupt active calls or messaging.

**Failure Handling:**

- SCIM event delivery failure: retry with exponential backoff (max 3 retries, 60 s max). Alert Admin on persistent failure.
- OPA policy push fails on device: device retains last known policy. Retry on next connection. Log `OPA_PUSH_FAILED`.

---

### F-14: Adaptive Network and Protocol Management

**Description:** Automatic network protocol selection (ALPN), adaptive QUIC probe learning, and graceful fallback to ensure connectivity across enterprise firewalls and restrictive networks.

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

**State Machine:** → §5.1 (Network Tier State Machine)

**Strict Compliance Mode:**

- Activated by Admin in CISO Console. Propagated via OPA policy push.
- Client skips Step 1. Connects directly via gRPC TCP.
- Saves 50 ms probe timeout on known UDP-blocked networks.

**Adaptive QUIC Probe Learning:**

```rust
fn on_probe_failure(mTLS_cert_fp: &[u8], ssid_hash: &[u8], db: &SqliteConn) {
    let network_id = blake3::hash(&[mTLS_cert_fp, ssid_hash].concat());
    let mut profile = db.get_or_create_network_profile(network_id.as_bytes());
    profile.probe_fail_count += 1;
    if profile.probe_fail_count >= 3 {
        profile.strict_compliance = true;
        emit_admin_notification("Auto-switched to TCP on this network.");
    }
    db.save_network_profile(&profile);
}

fn on_network_change(new_cert_fp: &[u8], ssid_hash: &[u8], db: &SqliteConn) {
    // Different network: reset probe count and strict_compliance flag
    let network_id = blake3::hash(&[new_cert_fp, ssid_hash].concat());
    db.reset_network_profile(network_id.as_bytes());
}
```

**HUD indicator:** QUIC / gRPC / WSS / Mesh icon updates in top status bar on every `CoreSignal::TierChanged`. No dialog interruption.

**Security Hardening:**

- QUIC-Pinning State Machine blocks protocol downgrade attacks (QUIC → WSS).
- Socket Panic Circuit Breaker: on detected downgrade manipulation, refuse new TCP/UDP connections for 30 s.

**Dependencies:**

- REF: TERA-CORE §9.2 — ALPN negotiation protocol, Strict Compliance Mode, Adaptive Probe Learning
- REF: TERA-CORE §4.2 — `CoreSignal::TierChanged`, `NetworkTier` enum

**Data Interaction:**

- Reads/Writes: `NetworkProfile` in SQLite local config DB (per network identifier).

**Constraints:**

- ALPN selection is automatic. Admin can override to Strict Compliance Mode only.
- Adaptive learning resets on network change (different mTLS cert fingerprint).

**Observability:**

- Signal: `CoreSignal::TierChanged { new_tier, reason }` on every ALPN change.
- Metric: `alpn_fallback_count` (OBSERVE-01).
- Admin notification: auto-emitted when probe learning triggers Strict Compliance.

**Failure Handling:** → §10.1 (Network Failure)

- All three ALPN steps fail: activate Mesh Mode. Emit `CoreSignal::TierChanged { new_tier: MeshMode }`.
- Adaptive auto-switch false positive: Admin can reset in Settings. Network change auto-resets.

---

### F-15: Crash-Safe Memory and WAL Management

**Description:** Platform-specific memory protection and crash-safe WAL flush protocols to prevent key material exposure and data loss on unexpected process termination.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**iOS / Android Crash-Safe Checkpoint:**

```swift
// iOS Swift layer (host adapter) → FFI → Rust Core
NotificationCenter.default.addObserver(
    forName: UIApplication.willTerminateNotification,
    using: { _ in tera_core_flush_io() }   // FFI; completes in ≤ 50 ms
)
```

```kotlin
// Android Kotlin layer (host adapter)
override fun onTrimMemory(level: Int) {
    if (level >= TRIM_MEMORY_RUNNING_CRITICAL) tera_core_flush_io()
}
```

**Memory Pressure Response (iOS/Android):**

1. Receive OS memory warning callback.
2. Rust Core immediately: zeroize all vector caches; pause ONNX pipeline.
3. Priority preserved: `hot_dag.db` and active chat session.
4. Emit `CoreSignal::ComponentFault { component: "onnx", severity: Warning }`.

**Desktop WAL Checkpoint on Shutdown:**

- `terachat-daemon` registers SIGTERM handler.
- On SIGTERM: `PRAGMA wal_checkpoint(TRUNCATE)` with 30 s timeout.
- Exit unconditionally after 30 s regardless of checkpoint result.
- systemd `TimeoutStopSec = 35`.

**Linux Multi-Init Daemon Support (postinstall script):**

```bash
#!/bin/bash
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
# terachat-daemon writes PID file → any init system can monitor via PID
```

**AppArmor / SELinux MAC Profile Auto-Load (postinstall):**

```bash
if command -v apparmor_parser &>/dev/null; then
    apparmor_parser -r -W /etc/apparmor.d/usr.bin.terachat
    apparmor_parser -r -W /etc/apparmor.d/terachat-daemon
elif command -v semodule &>/dev/null; then
    semodule -i /usr/share/terachat/terachat.pp
fi
# Verify: terachat --check-permissions (built-in self-test)
```

Without this script: startup crash on `memfd_create` and `ipc_lock` denial on enforcing systems.

**Dependencies:**

- REF: TERA-CORE §4.4 — SIGTERM handler, `wal_checkpoint`, `TimeoutStopSec = 35`
- REF: TERA-CORE §7.1 — WAL anti-bloat, VACUUM protocol
- REF: TERA-CORE §12.2 — DB-03 (`wal_autocheckpoint = 1000`)
- REF: TERA-CORE §9.3 — `wal_staging.db` replay on restart

**Constraints:**

- `tera_core_flush_io()` must complete in ≤ 50 ms on mobile (OS kill timer fires at ~500 ms).
- Desktop: 35 s total (30 s checkpoint + 5 s systemd margin). Exit unconditionally after 30 s.
- `PRAGMA wal_autocheckpoint = 1000` enforced on all databases at connection open.

**Failure Handling:** → §10.2 (Storage Failure), §10.4 (Runtime Failure)

- WAL checkpoint timeout (Desktop): exit regardless. `systemd Restart=on-failure` handles restart. `wal_staging.db` replay covers in-flight events on next start.
- OOM kill before WAL flush (iOS/Android): SQLite WAL is crash-safe by design. WAL replays automatically on next open. No data loss.
- AppArmor/SELinux postinstall script fails: log to `/var/log/terachat-install.log`; print warning; do not abort installation. Alert: "Manual MAC profile load required."

---

### INFRA-01: Client Compute Distribution

> **Principle:** Mobile devices are not compute nodes. Desktop is the compute cluster. VPS is a blind router. Computation goes where resources exist — not where it is architecturally convenient.

#### INFRA-01.1 Mobile Compute Constraints (Hard Rules)

The following operations MUST NOT run on Mobile (📱):

| Operation | Reason Prohibited | Alternative |
|---|---|---|
| ONNX 80 MB model inference | Thermal spike +4°C, 15% battery/op | Desktop offload |
| DAG merge > 3000 events | ANR risk > 5 s | Snapshot sync |
| FTS5 full-history index | Storage > 300 MB | Desktop-hosted search |
| CRDT full-state storage | `hot_dag.db` > 300 MB | Delta-only + snapshot |
| BLAKE3 full-file hash (> 100 MB) | CPU spike blocks UI | Desktop computation |

#### INFRA-01.2 ONNX Inference Offload Protocol

📱 Mobile emits `OnnxOffloadRequest` (E2EE) to Desktop Super Node when inference is required.

**Offload Trigger Conditions:**

| Trigger | Action |
|---|---|
| Model tier requires "base" (74 MB) and mobile RAM ≤ 3 GB | Mandatory offload |
| Mobile battery < 30% | Mandatory offload |
| Thermal state = Critical (iOS: `.serious` / Android: `THERMAL_STATUS_SEVERE`) | Mandatory offload |
| Model tier "tiny" but CPU utilization > 80% sustained 10 s | Recommended offload |

**Offload Protocol Flow:**

```text
📱 Mobile → [ONNX_OFFLOAD_REQUEST]
  {
    request_id: Uuid,
    sanitized_prompt: SanitizedPrompt,   // PII redacted — never raw text
    model_tier: "base" | "tiny",
    ttl_ms: 5000,
    requester_did: DeviceId,
    hmac: HMAC-BLAKE3(Company_Key, request_id || sanitized_prompt)
  }
  │ Transport: E2EE CRDT_Event (nonce rotation per request)
  ▼
💻 Desktop Super Node
  1. Verify HMAC-BLAKE3 — reject on mismatch (log OFFLOAD_HMAC_VIOLATION)
  2. Check OPA Policy: requester_did AI quota remaining?
  3. Run ONNX inference in isolated process (no RAM share with Rust Core)
  4. Respond [ONNX_OFFLOAD_RESPONSE]:
     {
       request_id: Uuid,         // Echo — match with request
       ast_nodes: Vec<ASTNode>,  // Sanitized output — no raw LLM text
       tokens_used: u32,
       latency_ms: u32
     }
  │ Transport: E2EE CRDT_Event to requester_did
  ▼
📱 Mobile
  1. Verify request_id matches pending request — reject if stale
  2. Deliver Vec<ASTNode> to .tapp or AI context
  3. Decrement AI quota: tokens_used
  4. ZeroizeOnDrop on SanitizedPrompt after response received
```

**Constraints:**

- `SanitizedPrompt` is a newtype — construction mandatory via PII redaction pass (Micro-NER). Raw string cannot be passed.
- Desktop ONNX process: RAM ceiling 150 MB. On breach: OOM-kill worker, return `OFFLOAD_OOM_ERROR`.
- No persistent connection between Mobile and Desktop for offload — each request is an independent CRDT_Event.

**Failure Handling:**

- Desktop offline / not in Mesh: fall back to Tiny model local.
- TTL 5000 ms exceeded without response: emit `CoreSignal::ComponentFault { component: "ai_offload", severity: Warning }`. UI: "AI processing is slow — retrying…" Retry once with TTL 3000 ms. Then: Tiny local fallback.
- HMAC mismatch on Desktop: log `OFFLOAD_HMAC_VIOLATION { requester_did }` to Audit Log. Do not respond.
- ONNX worker crash on Desktop: `catch_unwind` at worker entry. Emit `ComponentFault`. Mobile receives timeout after TTL.

---

### INFRA-02: Blob Storage Client

> Clients interact with blob storage ONLY via TeraRelay's presigned URL mechanism.
> Clients NEVER have direct credentials to R2/B2/MinIO.
> Zero-Knowledge preserved: relay signs URLs without seeing content.

The upload and download flows for this module are fully specified in F-09.

**Key Invariants:**

- `cas_hash = BLAKE3(file_bytes)` computed before encryption.
- `ChunkKey_i = HKDF(Epoch_Key, "chunk" || cas_hash || i)`.
- Presigned URLs: TTL 15 min (upload), 5 min (download). Stateless HMAC-signed generation by TeraRelay.
- Chunk deduplication: HEAD request on `cas_hash` before upload. Server learns nothing from dedup (Salted MLE).
- `ZeroizeOnDrop` on `ChunkKey_i` and chunk plaintext after each chunk.
- Max 3 concurrent chunk uploads.

---

### INFRA-03: TeraRelay Health & Self-Healing

> Single-binary deployment means no cluster coordination.
> Self-healing must happen within the binary itself.
> Systemd is last-resort, not the primary recovery mechanism.

**In-Process Watchdog:**

```rust
pub struct InProcessWatchdog {
    component_health: HashMap<ComponentId, ComponentHealth>,
    last_heartbeat:   HashMap<ComponentId, Instant>,
    restart_counts:   HashMap<ComponentId, u32>,
    alert_tx:         mpsc::Sender<WatchdogAlert>,
}
```

**Component Heartbeat Table:**

| Component | Heartbeat Interval | Max Silence Threshold | Restart Policy |
|---|---|---|---|
| WAL staging consumer | 2 s | 10 s | Restart after 1 s delay |
| Pub/sub fanout | 2 s | 10 s | Restart after 1 s delay |
| BLE beacon scanner | 5 s | 20 s | Restart after 2 s delay |
| ALPN probe task | 10 s | 30 s | Restart after 5 s delay |
| AI worker process | 5 s | 15 s | Restart after 2 s delay; max 3/hour |

**Restart Budget (Circuit Breaker):** 5 restarts per hour per component. On breach: mark component `Degraded`; alert Admin Console; do not terminate daemon.

**Prometheus Metrics (Zero-Knowledge):**

```
terachat_watchdog_restarts_total{component="wal_staging"} 2
terachat_watchdog_circuit_breaker_trips_total{component="ai_worker"} 1
terachat_component_health{component="ble_scanner", status="healthy"} 1
```

No user ID, message content, or session data in any metric.

**SIGTERM Handling (Graceful Shutdown):**

```rust
// 1. Stop accepting new connections
// 2. Signal all components via watchdog to flush
watchdog.initiate_shutdown().await;
// 3. WAL checkpoint (30s timeout)
let _ = timeout(Duration::from_secs(30),
    db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
).await;
// 4. Exit unconditionally
process::exit(0);
```

systemd `TimeoutStopSec = 35` — 5 s margin after 30 s checkpoint.

---

### INFRA-04: Canary Deployment Strategy

> No Kubernetes, no service mesh. DNS-based traffic splitting + per-tenant feature flags.

**DNS Traffic Splitting:**

```text
relay.terachat.com
  ├── 95% → relay-stable.terachat.com  (current stable version)
  └── 5%  → relay-canary.terachat.com  (new version under validation)
```

Clients do not know which track they are on — same TLS cert, same API surface.

**Canary Promotion Gate (automated):**

```yaml
canary_validation:
  initial_traffic_pct: 5
  promotion_steps: [5, 25, 50, 100]
  promotion_interval_hours: 2

  auto_rollback_triggers:
    - metric: "relay_error_rate_5xx"
      threshold: "> 0.5%"
      window_minutes: 5
    - metric: "wasm_sandbox_crashes_total_rate"
      threshold: "> 0.1/min"
      window_minutes: 5
    - metric: "dag_merge_duration_p99_ms"
      threshold: "> 2000"
      window_minutes: 10
    - metric: "client_reported_crash_rate"
      threshold: "> 0.2%"
      window_minutes: 15

  required_gates:
    - name: "WasmParity CI gate passed"
      source: "ci_result"
    - name: "SBOM signature verified"
      source: "ops/sbom-verification.sh"
    - name: "Security scan clean"
      source: "trivy_result"
```

**Per-Tenant Feature Flags (Emergency Override):**

```rust
// Admin Console → OPA Policy → pushed down to clients
{
  "feature_flags": {
    "canary_opt_out": true,
    "ai_inference_enabled": false,
    "mesh_mode_enabled": true,
    "max_file_size_mb": 100
  }
}
```

**Rollback Procedure (< 5 min):**

```bash
tera-ops dns set-weight --target relay-canary --weight 0
tera-ops dns set-weight --target relay-stable --weight 100
# Alert: PagerDuty incident + Slack notification
# Log rollback event with timestamp and triggering metric
```

---

### INFRA-05: SBOM & Reproducible Builds

> Enterprise/Gov customers require SBOM for compliance audit.

**SBOM Generation (CycloneDX 1.5):**

```bash
cargo cyclonedx --format json --output terachat-sbom.json
cosign sign-blob \
    --key release-key.pem \
    --output-signature terachat-sbom.json.sig \
    terachat-sbom.json
```

**Reproducible Builds:**

```dockerfile
FROM rust:1.75.0-slim-bookworm AS builder
RUN apt-get install -y --no-install-recommends \
    libclang-dev=1:15.0-56 \
    pkg-config=1.8.1-1
ENV SOURCE_DATE_EPOCH=1700000000
RUN cargo build --release --locked
```

```toml
# rust-toolchain.toml
[toolchain]
channel = "1.75.0"
components = ["rustfmt", "clippy"]
targets = [
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin"
]
```

**Customer Verification:**

```bash
cosign verify-blob \
    --key https://releases.terachat.com/cosign-pub.pem \
    --signature terachat-sbom.json.sig \
    terachat-sbom.json
```

---

### INFRA-06: Automated Chaos Engineering

> TestMatrix.md defines 28 scenarios. This section specifies the implementation framework.
> Goal: automated CI test suite, not just manual runbook.
> Gov/Military tier: must pass all 28 before contract is signed.

**Framework:**

```rust
pub struct ChaosScenario {
    pub id:            &'static str,
    pub name:          &'static str,
    pub fault_inject:  Box<dyn FaultInjector>,
    pub expected:      ExpectedBehavior,
    pub timeout_s:     u32,
    pub platforms:     Vec<PlatformKind>,
}

pub struct ExpectedBehavior {
    pub max_data_loss_events:  u32,
    pub max_recovery_time_s:   u32,
    pub min_mesh_nodes_active: u32,
    pub ui_degraded_ok:        bool,
}
```

**Core Chaos Scenarios (representative subset — 4 of 28):**

| Scenario | Fault | Expected | Timeout |
|---|---|---|---|
| SC-01 | Network partition 30 min then rejoin | Zero data loss; recovery < 120 s; Mesh UI acceptable | 2100 s |
| SC-02 | EMDP: Desktop offline, iOS-only Mesh, TTL expiry at T+60 min | Zero data loss; recovery < 30 s post-reconnect | 4200 s |
| SC-03 | Relay restart: 1000 in-flight STAGED events (SIGKILL) | Zero data loss; recovery < 60 s; UI fully recovered | 300 s |
| SC-06 | Dead Man Switch fires during active CallKit voice call | Lockout deferred until call ends; recovery < 10 s after call | 180 s |

**CI Integration:** Scheduled daily at 02:00 UTC; also triggered on `workflow_dispatch`. Runs in staging environment via docker-compose. Results published as JUnit XML artifact.

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

**Correctness Gates:**

| Gate | Command | Blocker |
|---|---|---|
| Unit tests (all platforms) | `cargo nextest run --all-features` | Yes |
| WasmParity CI gate (wasm3 vs wasmtime, delta ≤ 20 ms, memory ≤ 5 MB) | `cargo test --test wasm_parity -- --timeout 60` | Yes |
| Inbound dedup contract (CRDT) | `cargo test --test crdt_dedup_contract` | Yes |
| MLS epoch rotation SLA (≤ 1 s for 100 members) | `cargo bench --bench mls_epoch_rotation` | No (regression tracked) |

**Build & Signing Gates:**

| Gate | Command | Blocker | Platform |
|---|---|---|---|
| Reproducible build verification | `ops/verify-reproducible-build.sh` | Yes | All |
| SBOM generation and signing | `ops/generate-sbom.sh && cosign sign-blob …` | Yes | All |
| iOS: fastlane match cert validation | `bundle exec fastlane match nuke --dry-run` | No | iOS |
| Windows: EV Code Signing | `signtool verify /pa terachat-setup.exe` | Yes | Windows |
| Linux: GPG signature on .deb/.rpm | `dpkg-sig --verify terachat_*.deb` | Yes | Linux |
| Linux AppImage: Cosign verification | `cosign verify-blob --key terachat-root.pub` | Yes | Linux AppImage |

**Performance Budget Gates (non-blocking — regression alerts):**

| Gate | Threshold |
|---|---|
| IPC buffer acquire P99 | < 100 µs |
| AES-256-GCM throughput regression | < 10% drop |
| `hot_dag.db` append P99 | < 10 ms |

---

### OBSERVE-01: Client-Side Observability

> Mobile does not expose a Prometheus scrape endpoint.
> Instead: push aggregate metrics via OTLP HTTP when online, buffer locally when offline.
> No user-correlated data in any metric.

**Metric Types (`ClientMetricBatch`):**

```rust
pub struct ClientMetricBatch {
    device_class:   DeviceClass,   // Mobile | Desktop | Server (no device ID)
    platform:       PlatformKind,
    app_version:    SemVer,
    // Performance
    mls_encrypt_p50_ms:      u32,
    mls_encrypt_p99_ms:      u32,
    ipc_buf_acquire_p50_us:  u32,
    ipc_buf_acquire_p99_us:  u32,
    dag_append_p50_ms:       u32,
    dag_merge_events_per_s:  u32,
    // Reliability
    wasm_sandbox_crashes:    u32,
    nse_circuit_breaker_trips: u32,
    push_key_version_mismatches: u32,
    alpn_fallback_count:     u32,
    // Health (bucketed to prevent re-identification)
    wal_size_mb:             u32,   // Buckets: 0-10, 10-50, 50-100, 100+
    available_ram_mb:        u32,   // Buckets: 0-100, 100-500, 500-1000, 1000+
    battery_pct:             u8,    // Buckets: 0-20, 20-40, 40-60, 60-80, 80-100
    collection_period_start: u64,
    collection_period_end:   u64,
}
```

**Push Flow:**

- Every 15 min (or on foreground after offline): aggregate → OTLP protobuf → HTTPS POST `/v1/metrics` (mTLS).
- Battery < 15%: skip push.
- Offline: append to `metrics_buffer.db` (max 48h / 500 KB). Flush on reconnect.
- Retention: 30 days, then auto-delete. No cross-device correlation.
- Admin opt-out: OPA Policy `{ "telemetry.enabled": false }`.
- Battery < 20%: push interval extends to 300 s. At ≤ 10%: suspend entirely.

**Desktop Prometheus:**

- Prometheus Node Exporter: local exposure at `localhost:9092/metrics`.
- OTLP Push Fallback: push to VPS OTEL Collector.

**Privacy-Safe Crash Reporter:**

```rust
pub struct CrashReport {
    crash_id:       Uuid,           // Random UUID v4 — not linked to user
    platform:       PlatformKind,
    app_version:    SemVer,
    component:      &'static str,
    panic_type:     &'static str,   // No backtrace if PII risk
    stack_hash:     [u8; 8],        // BLAKE3[0:8] of stripped stacktrace
    os_version:     String,
    timestamp_utc:  u64,
}
```

**GC Release Warning:** When GC Finalizer releases a `TeraSecureBuffer` instead of explicit `releaseNow()`: increment `ffi.gc_finalizer_release.count` metric + log WARNING. This is a code quality signal, not a security event.

---

### OBSERVE-02: DAG Merge Progress UI

> When merge > 500 events, the user MUST see progress — no black screen.

**IPC Signal Contract:**

```rust
/// Emitted every 200 ms when DAG merge backlog > 500 events.
/// Stops emitting after merge completes.
CoreSignal::DagMergeProgress {
    completed: u64,
    total:     u64,
    // Derived by UI: percentage = completed * 100 / total
    // Derived by UI: eta_seconds = (total - completed) / current_rate
}
```

**Mobile ANR Prevention (Time-Slicing):**

```rust
pub async fn merge_dag_timesliced(events: Vec<CrdtEvent>, progress_tx: mpsc::Sender<MergeProgress>) {
    const BATCH_SIZE: usize = 100;
    let total = events.len() as u64;
    let mut completed: u64 = 0;
    for batch in events.chunks(BATCH_SIZE) {
        merge_batch(batch).await;
        completed += batch.len() as u64;
        tokio::task::yield_now().await;   // Yield 1-2 ms for UI event loop
        if should_emit_progress() {
            progress_tx.send(MergeProgress { completed, total }).ok();
        }
    }
    progress_tx.send(MergeProgress { completed: total, total }).ok();
}
```

**UI Behavior:**

- `completed / total < 1.0`: show non-blocking Progress Banner; disable Send button; show ETA if total > 1000.
- `completed / total == 1.0`: dismiss banner after 1.5 s; enable Send button; `CoreSignal::StateChanged` triggers UI refresh.

**Desktop behavior:** Rayon parallel merge in background Tokio task. Same `DagMergeProgress` signal emitted every 200 ms. No time-slicing needed. Desktop merges 10–20× faster than Mobile.

---

### PLATFORM-17: Dart FFI Memory Contract

> **Supersedes PLATFORM-14.** Mandatory — violations = CI fail (blocker).
> Applies to: Android, Huawei (Dart FFI path).

**Four Mandatory Rules:**

- **Rule 1:** Every `TeraSecureBuffer` MUST be wrapped by `useInTransaction()`. Direct `.toPointer()` outside wrapper → CI lint error (blocker).
- **Rule 2:** Rust Token Registry does NOT auto-expire/zeroize. On TTL timeout → emit `IpcSignal::TransactionTimeout`. UI: "Session expired — please retry."
- **Rule 3:** GC Finalizer is safety net only. GC release → WARNING metric + log. Never silent.
- **Rule 4:** Explicit `releaseNow()` is primary release path. `useInTransaction()` calls it in `finally` automatically.

**Dart FFI `TeraSecureBuffer` Wrapper:**

```dart
class TeraSecureBuffer {
  final int _token;
  bool _released = false;

  static Future<TeraSecureBuffer> acquire(int operationId) async {
    final token = await _teraFfi.tera_buf_acquire(operationId);
    if (token == 0) throw const TeraBufferError('acquire failed — token=0');
    return TeraSecureBuffer._(token);
  }

  void releaseNow() {
    if (_released) return;
    _teraFfi.tera_buf_release(_token);
    _released = true;
  }

  @override
  void finalize() {
    if (!_released) {
      MetricsCollector.increment('ffi.gc_finalizer_release.count');
      _logger.warning('TeraSecureBuffer $token released by GC finalizer — explicit releaseNow() missing');
      _teraFfi.tera_buf_release(_token);
    }
  }
}

Future<T> useInTransaction<T>(
    int operationId,
    Future<T> Function(Pointer<Uint8> data, int length) fn,
) async {
  final buf = await TeraSecureBuffer.acquire(operationId);
  try {
    final ptr = _teraFfi.tera_buf_get_pointer(buf._token);
    final len = _teraFfi.tera_buf_get_length(buf._token);
    return await fn(ptr, len);
  } finally {
    buf.releaseNow();
  }
}
```

**CI Clippy Lint (Rust side — FFI-01 enforcement):**

```rust
fn check_fn_return_type(cx: &LateContext, fn_id: DefId) {
    if is_pub_extern_c(fn_id) {
        if returns_raw_ptr_or_vec(cx, fn_id) && !uses_token_protocol(cx, fn_id) {
            cx.span_error(fn_span(fn_id),
                "FFI-01 VIOLATION: pub extern \"C\" function returns raw pointer/Vec. \
                 Use tera_buf_acquire/tera_buf_release token protocol. \
                 See TERA-FEAT §10.1 SEC-02 and TERA-CORE §4.3."
            );
        }
    }
}
```

**Dart Lint Rule:**

```yaml
analyzer:
  plugins:
    - tera_dart_lints
linter:
  rules:
    - tera_avoid_direct_ffi_pointer
    - tera_require_secure_buffer
```

---

### PLATFORM-18: ONNX Model Integrity

> Applies to: F-10 (AI/SLM) — all platforms. No exceptions.
> Every ONNX model load MUST pass `OnnxModelLoader.load_verified()`.

**Model Manifest (bundled with app):**

```json
{
  "models": [
    {
      "name": "micro_ner",
      "tier": "tiny",
      "file": "micro_ner.onnx",
      "blake3": "a3f2e1d4...",
      "size_bytes": 987654,
      "min_available_ram_mb": 12
    },
    {
      "name": "whisper_tiny",
      "tier": "tiny",
      "file": "whisper_tiny.mlmodelc",
      "blake3": "b4c5d6e7...",
      "size_bytes": 39000000,
      "min_available_ram_mb": 100
    }
  ],
  "manifest_signature": "Ed25519:TeraChat_Marketplace_CA_Key:XXXXXXXX"
}
```

**`OnnxModelLoader.load_verified()` — Verification Sequence:**

1. Lookup model spec in manifest → `Err(NotInManifest)` if absent (BLOCKER).
2. Verify manifest Ed25519 signature (TeraChat CA public key).
3. Check available RAM ≥ `spec.min_available_ram_mb` → `Err(InsufficientRam)` if insufficient.
4. Load model bytes from bundled asset.
5. Verify `BLAKE3(model_bytes) == spec.blake3` → if mismatch: log `AuditEvent::ModelIntegrityViolation`; return `Err(HashMismatch)`.
6. Initialize ORT session in isolated arena (`parallel_execution: false` — no thread pool share with Rust Core).
7. `ZeroizeOnDrop` on `model_bytes` after ORT internalizes.

**Platform-Specific Model Formats:**

| Platform | Model Format | Loader |
|---|---|---|
| 📱 iOS | CoreML `.mlmodelc` | `CoreML::load_compiled_model()` |
| 📱 Android | ONNX `.onnx` | `OnnxRuntime::Session::new()` |
| 📱 Huawei | HiAI `.om` or ONNX | `HiAI::load()` with ONNX fallback |
| 💻 macOS | CoreML `.mlmodelc` | `CoreML::load_compiled_model()` |
| 🖥️ Win/Linux | ONNX `.onnx` | `OnnxRuntime::Session::new()` |

**Failure Handling:**

- `HashMismatch`: terminate AI worker; emit `CoreSignal::ComponentFault { severity: Critical }`; log `ModelIntegrityViolation`. UI: "AI file integrity error — AI disabled for this session."
- `InsufficientRam`: log `ONNX_RAM_DENIED`; select lower tier if available. If none: AI unavailable for session.
- `NotInManifest`: BLOCKER — terminate AI worker immediately.

---

### PLATFORM-19: TeraEdge Client Integration

> Mobile auto-detects TeraEdge on LAN and prioritizes it over local ONNX inference or VPS relay.

**Super Node Discovery Priority:** → INFRA-01.2 (full `resolve_inference_backend()` function)

**Local Desktop Discovery Protocol:**

```text
Mobile emits mDNS query: _terachat-edge._tcp.local (100 ms timeout)
  │
Desktop Super Node responds:
  {
    node_id: NodeId,
    onnx_available: bool,
    model_tiers: ["tiny", "base"],
    current_load_pct: u8,
    latency_hint_ms: u32,
  }
  │ Signed by Desktop DeviceIdentityKey
  ↓
Mobile verifies signature → connect if load < 80% && latency < 50 ms
```

**Fallback When Desktop Overloaded:**

- Desktop `current_load_pct > 80%`: Mobile automatically downgrades to Local Tiny or VPS.
- Desktop connection lost mid-inference: retry once with 3 s timeout. If failed: VPS Enclave or Local Tiny.

---

---

## §5 — STATE MACHINE

> State logic extracted from feature definitions. Each feature that references a state machine has a pointer here.
> States, transitions, and trigger conditions are defined once; features reference by section.

### §5.1 Network Tier State Machine

**Applies to:** F-05, F-06, F-14

**States:**

| State | Description |
|---|---|
| `ONLINE_QUIC` | QUIC/HTTP3 over UDP:443 active. ~30 ms RTT. |
| `ONLINE_GRPC` | gRPC/HTTP2 over TCP:443 active. ~80 ms RTT. |
| `ONLINE_WSS` | WebSocket Secure over TCP:443 active. ~120 ms RTT. |
| `MESH_MODE` | All ALPN paths unavailable. BLE/Wi-Fi Direct active. |
| `STRICT_COMPLIANCE` | Admin override: skip QUIC; connect directly via gRPC TCP. |

**Transitions:**

| From | To | Trigger |
|---|---|---|
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

### §5.2 Mesh Role State Machine

**Applies to:** F-05

**States:**

| State | Eligible Platforms | Conditions |
|---|---|---|
| `LeafNode` | All | Default for iOS; fallback for Android/Desktop |
| `RelayNode` | Android, Huawei | RAM ≥ 3 GB && battery ≥ 40% |
| `SuperNode` | macOS, Windows, Linux | AC power source |
| `TacticalRelay` | iOS only (EMDP) | No Desktop; Internet unavailable; ≥ 2 iOS; battery > 20% |
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

### §5.3 WASM Sandbox Lifecycle State Machine

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

> This section is the authoritative interface contract for all IPC objects.
> Object definitions are in §3.3. Usage examples are in §4 Feature Model.
> State flow: Core → UI is unidirectional. UI sends Commands only (IPC-01).

### §6.1 CoreSignal Catalog (Core → UI)

| Signal | Payload Fields | Trigger Condition |
|---|---|---|
| `StateChanged` | `table: &str, version: u64` | Any DAG mutation or DB state change |
| `ComponentFault` | `component: &str, severity: FaultSeverity` | Any `catch_unwind` caught panic |
| `MeshRoleChanged` | `new_role: MeshRole` | Mesh topology change |
| `EmdpExpiryWarning` | `minutes_remaining: u32` | T-10 min and T-2 min during EMDP TTL |
| `DeadManWarning` | `hours_remaining: u32` | T-12 h and T-1 h offline grace period |
| `TierChanged` | `new_tier: NetworkTier, reason: TierChangeReason` | ALPN tier change or AWDL loss |
| `DagMergeProgress` | `completed: u64, total: u64` | Every 200 ms when merge backlog > 500 events |
| `XpcHealthDegraded` | `crash_count: u32, window_secs: u32` | macOS XPC crash rate exceeds threshold |
| `MemoryPressureWarning` | `component: &str, allocated_mb: u32` | `MemoryArbiter` allocated > 80% ceiling |
| `MediaComplete` | `cas_hash: [u8; 32]` | All media chunks downloaded and decrypted |

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

> Canonical feature availability and constraint reference.
> Platform-specific behavior details are in §4 Feature Model.

### §7.1 Feature Availability Matrix

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

Engineers must resolve all Blocker items before production ship:

| Item | Severity | Reference | Status |
|---|---|---|---|
| WasmParity CI gate (wasm3 vs wasmtime semantic identity, ≤ 20 ms delta) | Blocker | F-07, TERA-CORE §11.4 | Not implemented |
| CI/CD code signing pipeline (all 5 platforms) | Blocker | `ops/signing-pipeline.md` | Not implemented |
| Dart FFI NativeFinalizer Clippy lint (FFI-01 enforcement) | Blocker | F-03, TERA-CORE §4.3 | Not implemented |
| AppArmor/SELinux postinstall script for Linux | High | F-15 | Not implemented |
| `sled` crate version pinned in `Cargo.toml` | Medium | F-07 Transient State | Not pinned |
| Border Node auto-detection heuristics (algorithm spec) | Medium | F-05 | Algorithm undefined |
| Windows ARM64 SAB behavior validation (WebView2) | Medium | F-03 | Not tested |

---

## §8 — NON-FUNCTIONAL REQUIREMENTS

> All values below are extracted from §4 Feature Model and §10 Implementation Contract.
> No values are invented here. Source sections are cited.

### §8.1 Performance

| Metric | Target | Source |
|---|---|---|
| IPC buffer acquire P99 | < 100 µs | CICD-01 |
| AES-256-GCM throughput regression | < 10% drop | CICD-01 |
| `hot_dag.db` append P99 | < 10 ms | CICD-01 |
| ALPN negotiation total | < 50 ms | F-14 |
| MLS epoch rotation (100 members) | ≤ 1 s | CICD-01 |
| `sled` transient state restore | < 50 ms | F-07 |
| Screen capture prevention overlay | < 16 ms (at 60 Hz) | F-11a |
| `tera_core_flush_io()` on mobile | ≤ 50 ms | F-15 |
| NSE sled restoration on internet restore | < 50 ms | F-07 |
| License feature restoration on renewal | < 5 s | F-13 |

### §8.2 Memory

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

---

## §9 — SECURITY MODEL

> This section consolidates all security logic scattered across features.
> Features reference here. Definitions are not duplicated in features.

### §9.1 Key Management

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
| Push key version mismatch | Replay attack on old key | Ghost Push: no content exposure; Main App decrypts with rotated key |
| WASM egress | Unauthorized network access | OPA policy check on all requests; declared `egress_endpoints` only |
| WASM memory | DAG buffer write | `PROT_READ`-only; `SIGSEGV` caught by `catch_unwind` |
| FFI boundary | Raw pointer leakage | No `Vec<u8>` / `*const u8` in `pub extern "C"`; Clippy lint enforced (SEC-02) |
| LLM prompt injection | Malicious `.tapp` output | AST Sanitizer wraps all LLM responses; 3rd TAINTED → `.tapp` suspend |
| Protocol downgrade | QUIC → WSS forced downgrade | QUIC-Pinning State Machine; 30 s Socket Panic Circuit Breaker |
| Remote Wipe bypass | UI attempt to cancel wipe | Non-interruptible: `autoreleasepool` (iOS) / `try-finally` (Android) |
| Admin Console from mobile | Unauthorized policy mutation | Mobile Admin Console: read-only enforced by Rust Core (FD-02) |
| Model integrity | Tampered ONNX weights | BLAKE3 hash + Ed25519 manifest signature on every load (PLATFORM-18) |

### §9.5 Implementation Contract — Security Rules

| Rule ID | Rule | Enforcement |
|---|---|---|
| SEC-01 | No plaintext UI buffer outlives the render frame. `ZeroizeOnDrop` on every struct holding decrypted content. | `cargo miri test`. CI failure: blocker. |
| SEC-02 | No `Vec<u8>`, `*const u8`, or `*mut u8` returned from any `pub extern "C"` function. Token protocol mandatory. | CI Clippy lint `tera_ffi_raw_pointer`. Lint failure: blocker. |
| SEC-03 | All clipboard operations route through Protected Clipboard Bridge (F-11b). Direct OS clipboard API calls from Rust Core: blocker. | Code review + CI. |
| SEC-04 | WASM sandbox: `PROT_READ`-only access to DAG shared memory. Write attempts trigger `SIGSEGV` caught by `catch_unwind`. | Runtime enforcement. |
| SEC-05 | iOS Keychain: `push_key` (NSE only), `device_identity_key` (Main App only), `share_extension_token` (Share Extension only). Cross-group reads: blocker. | Keychain entitlement configuration. |

---

## §10 — FAILURE MODEL

> All failure conditions extracted from §4 Feature Model.
> Organized by failure category. Features reference this section.

### §10.1 Network Failure

| Condition | Detection | Response | Signal |
|---|---|---|---|
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

### §10.2 Storage Failure

| Condition | Detection | Response | Log Event |
|---|---|---|---|
| WAL > 50 MB (mobile) | Background Tokio task monitoring | Trigger VACUUM sequence | None |
| WAL > 200 MB (mobile) | `MemoryArbiter` monitoring | Emit `CoreSignal::MemoryPressureWarning`; UI banner | None |
| VACUUM fails | `VACUUM INTO` returns error | Log error; retry on next trigger; do not crash | None |
| Schema migration fails (`cold_state.db`) | Migration script error | Drop `cold_state.db`; rebuild from `hot_dag.db` | `COLD_STATE_REBUILD` |
| Hydration interrupted mid-download | Process termination or network loss | Delete `cold_state_shadow.db`; restart from `Hydration_Checkpoint` | None |
| WAL checkpoint timeout (Desktop 30 s) | `timeout()` wrapper | Exit unconditionally; `systemd Restart=on-failure` | None |
| OOM kill before WAL flush (mobile) | OS SIGKILL | SQLite WAL crash-safe; auto-replay on next open | None |
| `sled` transient state unavailable (Mesh Mode) | Mesh Mode active | Transient state persistence disabled; snapshot on Mesh activation | None |

### §10.3 Key Failure

| Condition | Response | Log Event |
|---|---|---|
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

### §10.4 Runtime Failure

| Condition | Component | Response | Signal |
|---|---|---|---|
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

---

## §11 — VERSIONING & MIGRATION

> All policies extracted from §4 and §9. No values invented here.

### §11.1 Schema Migration Strategy

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

> All data extracted from §4 Feature Model and §9 Implementation Contract.
> No additional telemetry is defined here.

### §12.1 Named Log Events

| Event ID | Condition | Feature | Level |
|---|---|---|---|
| `COLD_STATE_REBUILD` | `cold_state.db` dropped and rebuilt from `hot_dag.db` | F-04 | INFO |
| `STRONGBOX_UNAVAILABLE` | Android StrongBox absent; fallback to AndroidKeyStore | F-11/F-12 | WARN |
| `HUAWEI_CRL_STALE` | Huawei CRL delay caused deferred decryption | F-02 | WARN |
| `OPA_PUSH_FAILED` | OPA policy push to device failed; retaining last policy | F-13 | WARN |
| `ONNX_OOM_FALLBACK` | ONNX allocator OOM; fallback to Flat-search | F-10 | WARN |
| `OFFLOAD_HMAC_VIOLATION` | HMAC mismatch on ONNX offload; `requester_did` logged | INFRA-01 | AUDIT |
| `INVALID_RECOVERY_TICKET` | Recovery Ticket Ed25519 signature invalid | F-12 | AUDIT |
| `MEDIA_UPLOAD_FAILED` | Chunked upload failed after 3 retries | F-09 | ERROR |
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

### §12.6 Canary Rollback Metrics

Thresholds that trigger automatic DNS rollback (INFRA-04):

| Metric | Threshold | Window |
|---|---|---|
| `relay_error_rate_5xx` | > 0.5% | 5 min |
| `wasm_sandbox_crashes_total_rate` | > 0.1/min | 5 min |
| `dag_merge_duration_p99_ms` | > 2000 | 10 min |
| `client_reported_crash_rate` | > 0.2% | 15 min |

---

## §13 — APPENDIX

### §13.1 Glossary

| Term | Definition |
|---|---|
| ALPN | Application-Layer Protocol Negotiation. Selection sequence: QUIC → gRPC → WSS. |
| ANR | Application Not Responding. Android 5 s UI freeze detection. |
| BLE | Bluetooth Low Energy 5.0. Used in F-05 Survival Mesh. |
| CAS | Content-Addressed Storage. Server stores encrypted chunks by `BLAKE3(file)`. |
| CRDT | Conflict-Free Replicated Data Type. Append-only DAG of `CRDT_Event` objects. |
| DTLS-SRTP | Datagram TLS + Secure Real-time Transport Protocol. WebRTC encryption (F-06). |
| EMDP | Emergency Mobile Dictator Protocol. iOS-only Tactical Relay when Desktop offline. |
| Epoch_Key | Per-epoch AES-256-GCM key derived by MLS. Held only in RAM (`ZeroizeOnDrop`). |
| FFI | Foreign Function Interface. Rust ↔ Swift/Kotlin/Dart bridge layer. |
| HLC | Hybrid Logical Clock. Used for deterministic `CRDT_Event` ordering. |
| HSM | Hardware Security Module. Used in Gov/Military bare-metal tier. |
| IPC | Inter-Process Communication. Governed by §6. |
| Jetsam | iOS memory pressure killer. Trigger for iOS Super Node handover in F-05. |
| JSI | JavaScript Interface. C++ memory sharing API used for iOS Data Plane. |
| MLS | Messaging Layer Security (RFC 9420). Group E2EE protocol in F-01. |
| mTLS | Mutual TLS. Both client and server present certificates. |
| NER | Named Entity Recognition. Local ONNX model for PII detection in F-10. |
| NSE | Notification Service Extension. iOS process for E2EE push decryption in F-02. |
| ONNX | Open Neural Network Exchange. AI model format used on Android/Desktop. |
| OPA | Open Policy Agent. ABAC enforcement for WASM egress and inter-`.tapp` IPC. |
| PII | Personally Identifiable Information. Redacted before any cloud AI call in F-10. |
| QUIC | UDP-based transport protocol (HTTP/3). Primary ALPN path in F-14. |
| SAB | SharedArrayBuffer. Desktop IPC Tier 1 transport in F-03. |
| SCIM | System for Cross-domain Identity Management 2.0. HR offboarding integration in F-13. |
| SDP | Session Description Protocol. WebRTC signaling exchanged over MLS E2EE channel. |
| SEP | Secure Enclave Processor. Apple hardware key storage. |
| SLM | Small Language Model. Local inference tier in F-10 (< Whisper Base size). |
| sled | Pure-Rust LSM-Tree crate. Mandated for WASM transient state (FI-04). |
| STUN | Session Traversal Utilities for NAT. P2P fallback when TURN unavailable. |
| `.tapp` | TeraChat app bundle format. WASM plugin unit (F-07). |
| TURN | Traversal Using Relays around NAT. WebRTC relay for voice/video (F-06). |
| VPS | Virtual Private Server. Blind relay deployment target. |
| WAL | Write-Ahead Log. SQLite durability mechanism used in `hot_dag.db`. |
| WASM | WebAssembly. Plugin runtime for `.tapp` execution (F-07). |
| W^X | Write XOR Execute. iOS App Sandbox memory protection; prohibits JIT. |
| ZeroizeOnDrop | Rust trait that securely overwrites memory on struct drop. Enforced by SEC-01. |
| ZeroByteStub | Media message stub (< 5 KB) referencing encrypted content by `cas_hash`. |

### §13.2 Error Code Reference

| Error Code | Condition | Feature |
|---|---|---|
| `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` | Mesh Mode active; AI inference disabled | F-10 |
| `ERR_MESH_MODE_DELEGATION_SUSPENDED` | Mesh Mode active; inter-`.tapp` tokens suspended | F-08 |
| `ERR_RATE_LIMIT_EXCEEDED` | `.tapp` token bucket (50 req/s) exhausted | F-07 |
| `ERR_DELEGATION_TOKEN_EXPIRED` | DelegationToken TTL exceeded | F-08 |
| `ERR_TOKEN_REVOKED` | OPA policy revoked DelegationToken mid-session | F-08 |
| `ERR_MNEMONIC_INVALID` | BIP-39 mnemonic incorrect | F-12 |
| `ERR_AI_QUOTA_EXCEEDED` | 10,000 tokens/hour per-`.tapp` quota exceeded | F-10 |
| `ERR_AI_CLOUD_UNAVAILABLE` | Cloud LLM endpoint unreachable | F-10 |
| `ERR_AI_RESPONSE_TAINTED` | AST Sanitizer rejected LLM response | F-10 |
| `BufferNotFound` | Token not in Core registry on `ReleaseBuffer` | F-03 |
| `OFFLOAD_OOM_ERROR` | Desktop ONNX process RAM ceiling (150 MB) exceeded | INFRA-01 |
| `NETWORK_MESH_RESTRICTED` | WASM egress blocked in Mesh Mode | F-07 |
| `MemoryDenied` | `MemoryArbiter.acquire()` rejected allocation | F-07/F-10 |
| `TeraBufferError('acquire failed — token=0')` | `tera_buf_acquire()` returned null token | F-03 / PLATFORM-17 |

### §13.3 Implementation Contract — Complete Rule Index

**Security Rules (SEC):** → §9.5

**Platform Rules (PLT):**

| Rule ID | Rule |
|---|---|
| PLT-01 | iOS: `wasm3` interpreter only in App Sandbox. `wasmtime` permitted in XPC Worker only. No JIT in Main App: **blocker**. |
| PLT-02 | iOS NSE: Static Memory Arena 10 MB. Circuit Breaker terminates on 20 MB breach. |
| PLT-03 | iOS: Voice calls require CallKit. Without it, network killed after 30 s background. Non-CallKit voice on iOS: **blocker**. |
| PLT-04 | Linux: Flatpak packaging prohibited. `.deb`/`.rpm` or AppImage + Cosign only. |
| PLT-05 | Linux clipboard: detect display server at runtime (`WAYLAND_DISPLAY`). Hardcoded single backend: **blocker**. |
| PLT-06 | Android 14+: FCM `priority = "high"` AND Companion Device Manager `REQUEST_COMPANION_RUN_IN_BACKGROUND`. Both required. |
| PLT-07 | Huawei: no dynamic WASM from Marketplace. AOT `.waot` bundles only. CRL delay ≤ 4 h must be in enterprise SLA. |

**Feature Integrity Rules (FI):**

| Rule ID | Rule |
|---|---|
| FI-01 | Every feature maps to at least one TERA-CORE module. Orphan features: **blocker**. |
| FI-02 | Mesh Mode restrictions enforced in Rust Core. UI-side Mesh override: **blocker**. |
| FI-03 | WasmParity CI gate must pass before any `.tapp` Marketplace listing. Gate failure: **blocker**. |
| FI-04 | `sled` crate is mandated for WASM transient state. Switching without budget validation: **blocker**. |
| FI-05 | iOS `election_weight = 0` hardcoded in `mesh/election.rs`. Any PR modifying this constant: **blocker**. |

**IPC Rules (IPC):**

| Rule ID | Rule |
|---|---|
| IPC-01 | State flow unidirectional: Core → UI. UI sends Commands only. Bidirectional state channel: **blocker**. |
| IPC-02 | SAB Tier Ladder selection logged to audit trail. Silent tier selection: **blocker**. |
| IPC-03 | `CoreSignal::DagMergeProgress` emitted every 200 ms when merge backlog > 500 events. |

**Anti-Technical-Debt Rules (ATD):**

| Rule ID | Rule |
|---|---|
| ATD-01 | No feature implements logic belonging to another feature. |
| ATD-02 | No feature accesses `hot_dag.db` or `cold_state.db` directly from the UI layer. |
| ATD-03 | No feature implements cryptographic operations. All crypto routes through TERA-CORE `crypto/`. |
| ATD-04 | Platform-specific code lives exclusively in host adapter layers. Mixed-platform logic in shared modules: **blocker**. |
| ATD-05 | Features communicate through typed `CoreSignal` and `UICommand` enums. Ad-hoc FFI calls between feature modules: **blocker**. |
| ATD-06 | WASM plugins have zero knowledge of MLS key material. Any code path exposing key material to WASM: **blocker**. |
| ATD-07 | The IPC bridge (F-03) has no semantic knowledge of message content. It transfers opaque bytes. |
| ATD-08 | `DelegationToken` grants access to an OPA-enforced namespace only — not to raw `cold_state.db`. |
| ATD-09 | No feature hardcodes platform count or MLS group size. These parameters come from TERA-CORE §10.3. |
| ATD-10 | Every feature that persists data specifies a cleanup/expiry path. No indefinite accumulation of stale data. |
| ATD-11 | Features with battery impact must implement a power budget. F-05 BLE duty cycle, F-10 Whisper tier, F-15 BGTask are reference implementations. |
| ATD-12 | Every feature's Failure Handling clause must correspond to a test case in TERA-TEST. Untested failure paths are not accepted for production. |
| ATD-13 | Features with platform-specific behavior must have test coverage on each variant. Parity gaps tracked in §7.5. |
| ATD-14 | WasmParity CI gate (§4 CICD-01) must pass for every `.tapp` before Marketplace listing. Semantic divergence between `wasm3` and `wasmtime` is a **blocker for Marketplace launch**. |

### §13.4 Architecture Trade-Offs

**What We Gain:**

| Benefit | Quantified Impact |
|---|---|
| Infrastructure cost | $240/month → $7–48/month (80–97% reduction) |
| Setup time | 1–2 days → 5–20 minutes |
| Mobile thermal | −4°C average (ONNX offloaded) |
| Mobile battery | −35% drain (ONNX offload + reduced DAG sync) |
| Mobile storage | 300 MB → 25 MB (`hot_dag.db`) |
| Deployment failures | Reduced 90% (single binary vs 5-node coordination) |
| Zero-downtime upgrade | Single binary atomic replacement |

**What We Accept (Residual Risks):**

| Risk | Severity | Mitigation |
|---|---|---|
| Desktop must be online for ONNX offload | Medium | TinyBERT local fallback always available |
| Single relay VPS = single point of failure | Medium | Health monitoring + 5-min restart via systemd + DNS failover |
| Managed R2/B2 = external dependency | Low | Provider stores only ciphertext → Zero-Knowledge preserved |
| No PostgreSQL on VPS = no complex queries | Low | Relay only needs routing table — SQLite sufficient |
| Desktop snapshot = delayed consistency | Low | 500-event or 24 h interval — acceptable for enterprise |

**What Does NOT Change:**

- Zero-Knowledge security model: intact
- E2EE with MLS: intact
- Survival Mesh (BLE/Wi-Fi Direct): intact
- Air-gapped deployment option: intact (Gov/Military tier)
- Shamir Secret Sharing / KMS Bootstrap: intact
- All cryptographic guarantees: intact

---

## §14 — CHANGELOG

| Version | Date | Summary |
|---|---|---|
| 0.4.0 | 2026-03-21 | Full restructure to production-grade standard. Added §1 Executive Summary, §5 State Machine (6 state machines extracted from features), §8 Non-Functional Requirements, §9 Security Model (consolidated), §10 Failure Model (consolidated by category), §11 Versioning & Migration, §12 Observability. Removed INSERTED PATCH garbled blocks; technical content integrated into proper sections (PLATFORM-17/18/OBSERVE-01/02/INFRA-01 subsections). Fixed duplicate INFRA-04/INFRA-05 code blocks. Resolved PLATFORM-19 naming conflict (TeraEdge vs One-Touch Relay). Added §0 missing fields: scope, non_goals, assumptions, constraints_global, breaking_changes_policy. All IDs, REFs, rule codes preserved. |
| 0.2.6 | 2026-03-19 | Add OBSERVE-01/02 client observability; PLATFORM-17/18/19/20; INFRA-01/02/03/04/05/06; CICD-01/02; Update PLATFORM-14→17. |
| 0.2.3 | 2026-03-18 | Complete rewrite from scratch. Full alignment with Core_Spec.md v2.0 (TERA-CORE). 15 features with mandatory Feature Definition Standard. §5 Feature ↔ Core Mapping table. §0 Client-side Data Object Catalog. §9 Anti-Technical-Debt Rules (ATD-01–ATD-14). §10 Implementation Contract (SEC-01–SEC-05, PLT-01–PLT-07, FI-01–FI-05, IPC-01–IPC-03). Platform constraint matrix. Known implementation gaps table. |
| 0.2.1 | 2026-03-13 | Legacy iterative updates. Deprecated React Native → Flutter unified mobile. Added PLATFORM-01 through PLATFORM-16. |
| 0.1.1 | 2026-03-04 | Initial feature spec. Added WASM Sandbox Isolation, Protected Clipboard Bridge, Zero-Byte Stub rendering, NSE Circuit Breaker. |

---

*Cross-references:*

- *MLS cryptographic internals, CRDT algorithms, server infrastructure → `TERA-CORE` (`Core_Spec.md`)*
- *UI animation, glassmorphism state machine → `TERA-DESIGN` (`Design.md`)*
- *Plugin publishing, Marketplace review, `.tapp` signing → `TERA-MKT` (`Web_Marketplace.md`)*
- *Combined-failure chaos test scenarios → `TERA-TEST` (`TestMatrix.md`)*
- *Code signing pipeline, certificate rotation → `ops/signing-pipeline.md`*
- *PostgreSQL PITR recovery, Shamir ceremony → `ops/db-recovery.md`, `ops/shamir-bootstrap.md`*
