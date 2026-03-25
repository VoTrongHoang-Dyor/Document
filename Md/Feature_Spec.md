```yaml
# DOCUMENT IDENTITY
id:        "TERA-FEAT"
title:     "TeraChat — Feature Technical Specification"
version:   "0.6.0"
status:    "ACTIVE — Implementation Reference"
date:      "2026-03-25"
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
  operational infrastructure (INFRA-01 through INFRA-09, OBSERVE-01/02, CICD-01).
  Added in v0.6.0: BYOM VPS Secure Engine (INFRA-07), Blind RAG zero-knowledge vector
  search (INFRA-08), VPS Cluster high-availability architecture for SLA 99.999% (INFRA-09).

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
  - TERA-CORE v3.1 is the canonical reference for all Core module contracts.
  - VPS Secure Engine (INFRA-07) operates as a stateless enclave — no log persistence, RAM-only computation.
  - Blind RAG VectorDB (INFRA-08) never receives plaintext documents or queries; only AES-256-GCM encrypted embedding vectors.
  - BYOM model identity is verified via Ed25519-signed manifest before any inference begins.

constraints_global:
  - All plaintext buffers use ZeroizeOnDrop; no plaintext outlives the render frame.
  - No raw pointer crosses the FFI boundary; FFI token protocol mandatory.
  - All cryptographic operations route through TERA-CORE crypto/ modules.
  - Platform-specific code lives in host adapters, never in shared Rust Core.
  - Every feature maps to at least one TERA-CORE module; orphan features are blockers.
  - VPS Secure Engine (INFRA-07) MUST NOT persist any plaintext prompt, response, or intermediate tensor to disk during inference; all computation is RAM-only with ZeroizeOnDrop post-session.
  - Blind RAG (INFRA-08): encrypted embedding vectors stored in VectorDB; plaintext document chunks never leave the client device unencrypted.
  - BYOM model weights delivered over mTLS channel with Ed25519-signed manifest; BLAKE3 hash verified before engine load; tampered weights → immediate engine termination and `SecurityEvent::ModelIntegrityViolation`.

breaking_changes_policy: |
  Schema migrations require {db_path}.bak.v{version} backup before execution.
  cold_state.db may be dropped and rebuilt from hot_dag.db at any time (DB-02 safety net).
  CoreSignal and UICommand enum changes: additive only; no removal without deprecation cycle.
  DelegationToken field additions permitted; removals require migration path.
  TERA-CORE §12.2 governs all DB migration rules (DB-01, DB-02, DB-03).

patch_history:
  - version: "0.6.0"
    date: "2026-03-25"
    issues_fixed:
      - "Issue-16: BYOM VPS Secure Engine isolation architecture not specified (INFRA-07)"
      - "Issue-17: E2EE Prompt Tunneling for stateless cloud AI inference not specified (INFRA-07)"
      - "Issue-18: Blind RAG zero-knowledge vector search architecture not specified (INFRA-08)"
      - "Issue-19: VPS Cluster HA architecture for SLA 99.999% not specified (INFRA-09)"
      - "Issue-20: F-10 AI backend routing table incomplete — BYOM Enclave and vLLM paths missing"
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
| BYOM enterprise AI isolation | Customer-trained model runs in stateless VPS Secure Engine; no external API exposure |
| Zero-knowledge cloud AI (Blind RAG) | VPS stores only encrypted embedding vectors; plaintext never server-side |
| SLA 99.999% at scale | VPS Cluster with HAProxy/Nginx LB, vLLM PagedAttention, Semantic Cache; auto-failover < 3 s |

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
         │  mTLS + Dynamic App Attestation Token
         ▼
┌────────────────────────────────────────────────────────┐
│  VPS Secure Engine Cluster (INFRA-07/08/09)            │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │  BYOM AI Node        │  │  Blind RAG VectorDB    │  │
│  │  vLLM + PagedAttn    │  │  (Encrypted vectors    │  │
│  │  Stateless / RAM     │  │   only; no plaintext)  │  │
│  │  E2EE Prompt Tunnel  │  │  pgvector / Qdrant     │  │
│  └──────────────────────┘  └────────────────────────┘  │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │  Semantic Cache      │  │  HAProxy Load Balancer │  │
│  │  (Redis; no raw PII) │  │  Message Queue (async) │  │
│  └──────────────────────┘  └────────────────────────┘  │
│  Zero-Knowledge: server sees only ciphertext blobs      │
└────────────────────────────────────────────────────────┘
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
| VPS Secure Engine | vLLM + BYOM model (INFRA-07) | Stateless AI inference; RAM-only; E2EE Prompt Tunnel; no log persistence |
| Blind RAG VectorDB | pgvector / Qdrant (INFRA-08) | Stores only AES-256-GCM encrypted embedding vectors; never plaintext |
| VPS Cluster HA | HAProxy + Semantic Cache + Message Queue (INFRA-09) | SLA 99.999%; Continuous Batching; Semantic Caching; async task offload |

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
| Client ↔ VPS Secure Engine (INFRA-07) | E2EE-encrypted prompt blob; mTLS + Dynamic App Attestation Token | Plaintext prompt; System Prompt; raw session context |
| VPS Secure Engine ↔ BYOM Model | In-process RAM pointer (anonymous pipe / IPC); never network socket | Decrypted weights leaving RAM; model output cached to disk |
| Client ↔ Blind RAG VectorDB (INFRA-08) | AES-256-GCM encrypted embedding vector; `vec_hash` query key | Plaintext query text; document content; user identity |

### §2.4 Deployment Model

| Tier | VPS Spec | Monthly Cost | Setup Time |
|---|---|---|---|
| Solo (≤ 50 users) | 1 vCPU, 512 MB RAM, 20 GB SSD | $6 + $1 storage | 5 min |
| SME (≤ 500 users) | 2 vCPU, 2 GB RAM, 40 GB SSD | $12 + $5 storage | 10 min |
| Enterprise (≤ 5000 users) | 4 vCPU, 8 GB RAM, 100 GB SSD | $28 + $20 storage | 20 min |
| Enterprise Cluster (≤ 50 000 users) | ≥ 3 AI Nodes (8 vCPU, 32 GB RAM, GPU optional) + 2 VectorDB Nodes + 1 HAProxy | $200–$800/mo | 1–2 hours |
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

### §3.6 BYOM and Blind RAG Objects

| Object | Type | Storage | Lifecycle | Security Constraint | Core Ref |
|---|---|---|---|---|---|
| `ByomManifest` | `{model_id, blake3_hash, ed25519_sig, max_context_tokens, allowed_tenants[]}` | Delivered via mTLS at engine startup | Per engine session; re-verified on restart | Ed25519-signed by TeraChat Root CA; BLAKE3 hash verified before load; tampered → `SecurityEvent::ModelIntegrityViolation` | TERA-FEAT §INFRA-07 |
| `E2eePromptBlob` | AES-256-GCM ciphertext of `{system_prompt, user_prompt, session_context}` | In-flight only (RAM on VPS Secure Engine) | Single inference request; ZeroizeOnDrop after decryption | Encrypted by client's `Enclave_Session_Key`; never written to VPS disk | TERA-FEAT §INFRA-07 |
| `Enclave_Session_Key` | ECDH Curve25519 ephemeral key | RAM only (client + VPS Enclave RAM) | Per inference session; ZeroizeOnDrop after response received | Derived via X25519 handshake authenticated by mTLS + Dynamic App Attestation Token | TERA-FEAT §INFRA-07 |
| `DynamicAttestationToken` | `{app_hash, timestamp, nonce, ed25519_sig}` | Generated per request; in-flight | Single-use; TTL 60 s; replay detection via nonce | Ed25519-signed by `DeviceIdentityKey` in Secure Enclave; VPS rejects stale or replayed tokens | TERA-FEAT §INFRA-07 |
| `EncryptedEmbeddingVector` | `AES-256-GCM(embedding_vector_f32[], Embedding_Key)` | Blind RAG VectorDB (server-side) | Permanent until user-initiated deletion; indexed by `vec_hash` | Plaintext vector never leaves client device; VectorDB operates exclusively on ciphertext | TERA-FEAT §INFRA-08 |
| `Embedding_Key` | AES-256 symmetric key | Client Secure Enclave / StrongBox | Per document corpus; rotated on membership change | Never transmitted to VectorDB; ZeroizeOnDrop after encryption | TERA-FEAT §INFRA-08 |
| `BlindQueryVector` | `AES-256-GCM(query_embedding_f32[], Query_Session_Key)` | In-flight | Single query session; discarded after results returned | VectorDB performs approximate nearest-neighbour on ciphertext via homomorphic-compatible structure; plaintext query never server-visible | TERA-FEAT §INFRA-08 |
| `SemanticCacheEntry` | `{query_embedding_hash, encrypted_response_blob, ttl}` | Redis (VPS Cluster) | TTL-based eviction; default 10 min | Cache keyed by embedding hash only; response stored as AES-256-GCM ciphertext; Redis never holds plaintext | TERA-FEAT §INFRA-09 |
| `InferenceQueueTask` | `{task_id, encrypted_prompt_blob, priority, enqueued_at}` | Message Queue (RAM; async) | Until worker dequeues and processes; TTL 5 min | Ciphertext only in queue; ZeroizeOnDrop on worker after decryption; no disk persistence | TERA-FEAT §INFRA-09 |

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
| AI / SLM | Local inference, PII redaction, cloud routing, BYOM Enclave | F-10 |
| Device Security | Screen protection, clipboard, wipe | F-11 |
| Identity | Enrollment, recovery, geofencing | F-12 |
| Admin Controls | Policy, SCIM, audit, license | F-13 |
| Network Management | ALPN, probe learning, fallback | F-14 |
| Infrastructure | Compute distribution, blob storage, relay health | INFRA-01–06 |
| BYOM VPS Secure Engine | Stateless AI isolation, E2EE Prompt Tunnel, mTLS App Attestation | INFRA-07 |
| Blind RAG | Zero-knowledge vector search, encrypted embeddings, client-side indexing | INFRA-08 |
| VPS Cluster HA | SLA 99.999%, vLLM Continuous Batching, Semantic Cache, Load Balancing | INFRA-09 |
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
| F-10 | AI / SLM Integration | `infra/relay.rs` (VPS Enclave), `infra/byom_engine.rs` | §3.3, §3.6, §4.4, INFRA-07, INFRA-08 |
| F-11 | Device Security | `crypto/hkms.rs`, `crypto/zeroize.rs` | §5.1, §5.2, §12.4 (PLT-04) |
| F-12 | Identity and Onboarding | `crypto/hkms.rs`, `crypto/mls_engine.rs` | §5.1, §5.2, §5.3 |
| F-13 | Admin Console | `infra/federation.rs`, `infra/metrics.rs` | §3.2, §5.1, §9.5, §9.6 |
| F-14 | Adaptive Network Management | `infra/relay.rs` | §9.2, §4.2 |
| F-15 | Crash-Safe WAL Management | `crdt/dag.rs`, `infra/wal_staging.rs` | §4.4, §7.1, §9.3, §12.2 |
| INFRA-07 | BYOM VPS Secure Engine | `infra/byom_engine.rs`, `crypto/enclave_session.rs` | §3.3, §4.4, §9.1 |
| INFRA-08 | Blind RAG VectorDB | `infra/blind_rag.rs`, `crypto/embedding_key.rs` | §3.3, §9.1 |
| INFRA-09 | VPS Cluster HA | `infra/cluster_ha.rs`, `infra/semantic_cache.rs` | §9.2, §10.1 |

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

### F-04: Local Storage Management (Encrypted Thin-Client & State Sync)

**Description:** Quản lý hệ thống lưu trữ SQLite hai tầng (`hot_dag.db` + `cold_state.db`) được mã hóa toàn phần bằng **SQLCipher (AES-256-GCM)**. Quản lý chống phình to WAL bằng chính sách `TRUNCATE` checkpoint, migration an toàn chống crash, và đồng bộ trạng thái (Shadow paging) để khớp nối với Cụm VPS Blind Storage.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux.

**Cấu trúc 2 tầng (Điều chỉnh theo Hybrid Cloud):**

- **`hot_dag.db` (Lưu trữ Nóng/Tạm thời):** Chứa các `CRDT_Event` mới nhất, `DelegationTokens` (F-08), và `Epoch_Keys`. Tối ưu cho tốc độ ghi cao (Append-only).
- **`cold_state.db` (Bộ đệm Ngữ nghĩa & Tham chiếu):** Chứa Index của Vector nhúng (phục vụ Local BYOM), các `cas_hash` map với dữ liệu mã hóa trên Cụm VPS (F-09), và UI state đã được biên dịch.

**[SECURITY] Mã hóa tại chỗ (Encryption-at-Rest):**

- Toàn bộ file DB phải được bọc bởi SQLCipher.
- Khóa mở DB (Database Key) được sinh ra lúc đăng nhập và lưu trữ vào phần cứng bảo mật của HĐH (Apple Secure Enclave / Android Keystore). RAM chỉ giữ connection pool, khóa sẽ bị xóa (`ZeroizeOnDrop`) khi khóa ứng dụng.

**[PATCH Issue-04] WAL Auto-Compaction — Checkpoint-First Policy:**
Luồng nén WAL (Compaction) sử dụng `PRAGMA wal_checkpoint(TRUNCATE)` thay vì `VACUUM INTO` để tránh Race Condition với các Tokio writers (có thể làm mồ côi các `CRDT_Event`).

- **Hoạt động ngầm:** Rust Core giám sát WAL size mỗi 60s. Vượt 50MB (Mobile) hoặc 200MB (Desktop) -> Kích hoạt `TRUNCATE`. An toàn đồng thời (Concurrent-safe), không khóa độc quyền (No exclusive lock).
- **Admin-only:** `VACUUM INTO` chỉ dùng cho tác vụ chống phân mảnh (defragmentation) thủ công, được bảo vệ bởi `BEGIN EXCLUSIVE TRANSACTION`.

```rust
// Primary compaction path — safe for concurrent Tokio writers
pub async fn compact_hot_dag(db: &SqlitePool) -> Result<()> {
    // TRUNCATE mode: resets WAL to empty, reclaims disk space
    sqlx::query("PRAGMA wal_checkpoint(TRUNCATE)").execute(db).await?;
    Ok(())
}
```

**[PATCH Issue-08] Shadow DB Write Lock — TOCTOU Fix (Cho Mobile Background Sync):**
Thay thế `AtomicBool` bằng `tokio::sync::Mutex<bool>` để chống lỗi Time-of-Check to Time-of-Use (TOCTOU) khi iOS NSURLSession background handlers chạy trên các luồng libdispatch ngẫu nhiên.

```rust
pub struct ShadowMigrationLock {
    migration_in_progress: tokio::sync::Mutex<bool>,
}

impl ShadowMigrationLock {
    pub async fn write_or_queue_to_hot_dag<F, R>(&self, f: F) -> R
    where
        F: FnOnce(WriteTarget) -> R,
    {
        let guard = self.migration_in_progress.lock().await;
        let target = if *guard { WriteTarget::HotDag } else { WriteTarget::ShadowDb };
        f(target)
        // guard dropped here — lock released
    }
}
```

**User Flow — Schema Migration (Cập nhật cấu trúc DB):**

1. Mở DB bằng khóa SQLCipher. Đọc `PRAGMA user_version`.
2. Nếu `< CURRENT_SCHEMA_VERSION`:
   - Tạo backup: `{db_path}.bak.v{current_version}`.
   - `BEGIN EXCLUSIVE TRANSACTION`.
   - Chạy migration scripts. Cập nhật `user_version`. `COMMIT`.
3. Nếu migration `cold_state.db` lỗi: Xóa file, build lại từ `hot_dag.db` và **đồng bộ lại các `cas_hash` từ VPS Cluster**. Ghi log `COLD_STATE_REBUILD`.

**User Flow — Shadow Paging Hydration (Đồng bộ State từ VPS):**
Khi thiết bị online lại hoặc cài app mới, cần tải lại State từ VPS (Chỉ tải các Stub và `cas_hash`, không tải toàn bộ file media/document).

1. Core nhận tham chiếu `Snapshot_CAS` từ VPS.
2. Khóa Mutex: `ShadowMigrationLock.migration_in_progress = true`.
3. Tải snapshot (các bảng index mã hóa) vào `cold_state_shadow.db`.
4. Verify `BLAKE3(downloaded_content) == cas_uuid`.
5. Rename nguyên tử (Atomic rename) `cold_state_shadow.db` -> `cold_state.db`.
6. Mở khóa Mutex `migration_in_progress = false`. Bắn tín hiệu UI render.

**Constraints (Ràng buộc hệ thống):**

- `hot_dag.db` chỉ được ghi nối (Append-only). Cấm xóa vật lý (Chỉ dùng Tombstones).
- Cấm lưu trữ bản rõ (Plaintext) của tin nhắn, prompt AI hay file đa phương tiện trong DB (Mọi thứ phải là Ciphertext hoặc Vector).
- Bắt buộc `PRAGMA wal_autocheckpoint = 1000` trên mọi DB.

**Failure Handling:** → §10.2 (Storage Failure)

- WAL phình > 200 MB (Mobile) mà `TRUNCATE` thất bại: Bắn `CoreSignal::MemoryPressureWarning`. UI hiện cảnh báo.
- Mất khóa SQLCipher (Lỗi OS Keystore): Không thể đọc dữ liệu cũ. Ép đăng xuất, yêu cầu người dùng nhập lại Recovery Phrase để tạo phiên mới và kéo dữ liệu mồi (Hydration) từ VPS.
- Hydration bị ngắt quãng giữa chừng: Xóa file shadow, tải tiếp từ `Hydration_Checkpoint` lưu trong `hot_dag.db`.

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

### F-06: Voice and Video Calls (WebRTC & Zero-Knowledge AI Assistant)

**Description:** Cuộc gọi thoại và video ngang hàng (P2P) được mã hóa đầu cuối thông qua WebRTC DTLS-SRTP. Tín hiệu SDP được trao đổi qua kênh MLS E2EE. Các máy chủ chuyển tiếp (TURN relays) được tích hợp trực tiếp vào **Cụm VPS Cluster**, hoạt động hoàn toàn "mù" (chỉ chuyển tiếp gói tin UDP đã mã hóa). Đặc biệt, hỗ trợ tích hợp "Thư ký AI" (Tóm tắt cuộc họp thời gian thực) thông qua luồng Stateless Enclave của F-10.

**Supported Platforms:** 📱 iOS (bắt buộc CallKit), 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux.

**Mesh Mode behavior:** Cuộc gọi thoại/video không khả dụng qua sóng BLE do giới hạn băng thông. Tự động chuyển sang giao thức **P2P Wi-Fi Direct / LAN (mDNS)** nếu các thiết bị ở gần nhau. Giao diện (UI) hiển thị: *"Mesh Mode: Cuộc gọi chỉ khả dụng qua mạng LAN/Wi-Fi Direct cục bộ."*

**User Flow (Luồng Gọi & Tích hợp AI):**

1. **Khởi tạo:** Người gọi nhấn nút. UI gửi `UICommand::SendMessage` với `content_type: CallOffer`.
2. **Bắt tay tín hiệu (Signaling):** Trao đổi SDP offer/answer qua kênh MLS E2EE (cùng kênh với tin nhắn văn bản).
3. **Kết nối:** Thu thập ICE candidates từ Pre-warmed ICE Pool. Độ trễ thiết lập cảm nhận: ~0 giây. Lập phiên DTLS-SRTP.
4. **AI Meeting Assistant (Tùy chọn - Tích hợp F-10):**
   - Nếu người dùng bật tính năng "Thư ký cuộc họp", luồng âm thanh (Audio stream) sẽ được chia nhánh.
   - TeraChat Core sử dụng Whisper Model (chạy ở Local BYOM hoặc gửi qua E2EE Tunnel lên VPS Enclave) để chuyển đổi giọng nói thành văn bản (Speech-to-Text) theo thời gian thực.
   - Bản text được gửi cho mô hình LLM (F-10) để sinh biên bản cuộc họp (Meeting Minutes). Toàn bộ quá trình xử lý trên RAM, ngắt cuộc gọi là `ZeroizeOnDrop` xóa sạch bộ nhớ.
5. **Kết thúc cuộc gọi:** Hủy phiên DTLS-SRTP; dọn dẹp ICE pool; trả về kết quả tóm tắt cuộc họp (nếu có) dưới dạng `Vec<ASTNode>`. Tuyệt đối không có thao tác ghi log/ghi đĩa (persistent write) đối với luồng Media.

**VPS Cluster Integration (Nâng cấp hạ tầng TURN):**

- Thay vì chạy các node TURN riêng lẻ, TURN server nay được triển khai dưới dạng các container phân tán trong **Cụm VPS**.
- **Global Load Balancing:** Sử dụng Anycast IP hoặc Geo-DNS để định tuyến luồng WebRTC đến Node TURN gần người dùng nhất, giảm thiểu độ trễ (latency < 50ms).
- **High Availability (SLA 99.999%):** Nếu một Node TURN vật lý trong cụm bị sập, luồng UDP lập tức được chuyển hướng (failover) sang node khác thông qua Keepalived Floating IP trong vòng < 3 giây.

**iOS Specifics (Giữ nguyên cấu trúc bảo vệ hệ điều hành):**

- **CallKit & Dual TURN Preconnect:** Khi ứng dụng iOS chuẩn bị vào nền (background), Rust Core chủ động kết nối trước với một TURN phụ trong Cụm VPS. Rơi mạng rớt gói (user-perceived drop) = 0s.
- **Xung đột AWDL/Hotspot:** `NWPathMonitor` phát hiện bật Hotspot -> tự động hạ cấp kết nối xuống BLE Tier 3 (F-09 Mesh) và ngắt cuộc gọi nếu không thể khôi phục WebRTC qua mạng di động sau 90 giây.

**Dependencies:**

- REF: TERA-CORE §5.3 — SDP signaling qua kênh MLS E2EE.
- REF: TERA-CORE §6.4 — Cơ chế CallKit iOS và xử lý xung đột AWDL.
- REF: TERA-FEAT §F-10 — Giao tiếp với Stateless Enclave / Local BYOM để chạy mô hình Whisper STT và LLM Tóm tắt.

**Data Interaction:**

- **Reads:** `Epoch_Key` để mã hóa SDP; cấu hình hạ tầng mạng.
- **Writes:** Không có dữ liệu lưu trữ vĩnh viễn (chỉ tồn tại trạng thái ICE/DTLS tạm thời trên RAM). Nếu bật AI, văn bản tóm tắt được ghi vào `.tapp` quản lý cuộc họp.

**Constraints:**

- **Bảo mật TURN:** Các Node TURN trong Cụm VPS là Zero-Knowledge, tuyệt đối không giữ khóa giải mã (DTLS keys chỉ tồn tại ở 2 thiết bị đầu cuối).
- **Năng lực hạ tầng:** 1 Node TURN tiêu chuẩn trong cụm (4 vCPUs, 8 GB RAM, 1 Gbps NIC) gánh ~150 luồng HD đồng thời (đã tối ưu so với 50 luồng của thiết kế cũ nhờ kiến trúc Cluster).

**Failure Handling:** → §10.1 (Network Failure)

- **TURN Failover:** Tự động chuyển mạch Node trong Cụm VPS.
- **Mất kết nối hoàn toàn với Cluster:** Thử thiết lập kết nối STUN P2P trực tiếp giữa 2 thiết bị. UI hiển thị cảnh báo: "Chất lượng cuộc gọi có thể bị suy giảm."
- **Lỗi xử lý AI (OOM / Quá tải):** Luồng AI STT tự động bị ngắt để bảo vệ chất lượng cuộc gọi (Audio/Video luôn được ưu tiên cao nhất). UI báo: "Thư ký AI tạm thời bị gián đoạn."

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

### F-08: Inter-`.tapp` IPC and Delegation Tokens (Zero-Knowledge & Taint-Aware)

**Description:** Cơ chế cho phép hai plugin (`.tapp`) chia sẻ dữ liệu hoặc tham chiếu ngữ cảnh với sự đồng ý rõ ràng của người dùng, được trung gian bởi Rust Core (Honest Broker). Tuyệt đối không có kênh giao tiếp trực tiếp nào giữa các `.tapp`. Tích hợp khả năng **Taint Tracking (Theo dõi dữ liệu bẩn)** từ F-10 và **Blind References (Tham chiếu mù)** từ F-09 để đảm bảo an toàn bộ nhớ và E2EE.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux.

**Mesh Mode behavior:** Giao tiếp IPC thuần túy cục bộ (Local IPC) vẫn hoạt động bình thường vì không cần Internet. Tuy nhiên, bất kỳ payload nào yêu cầu phân giải qua VPS (như truy vấn Vector) sẽ trả về `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED`.

**User Flow (Luồng cấp quyền & Giao tiếp):**

1. `.tapp` A gọi `terachat.ipc.share(target_did: DID, payload: IpcPayload)`.
    - *Lưu ý:* `IpcPayload` có thể là Bytes nhỏ (< 1MB) hoặc các `cas_hash` (tham chiếu tài liệu F-09).
2. Rust Core kiểm tra xem một `DelegationToken` hợp lệ, chưa hết hạn có tồn tại cho cặp (A → B) hay không.
3. **Chưa có Token:** Core hiển thị hộp thoại Consent UI: *"Cho phép [Tên .tapp A] chia sẻ dữ liệu ngữ cảnh với [Tên .tapp B]?"*
4. Người dùng chấp thuận: Core phát hành `DelegationToken` (TTL 30 ngày; được ký bởi `DeviceIdentityKey` cục bộ).
5. **Đã có Token:** Tự động cấp quyền (Auto-grant) không cần hỏi lại.
6. **Enterprise MDM path:** Quản trị viên đẩy Global Trust Policy. Các cặp `.tapp` được chỉ định (VD: CRM nội bộ và AI nội bộ) sẽ được pre-approved (duyệt trước).

**Delegation Token Structure (Cập nhật thêm Taint Tracking):**

```rust
pub struct DelegationToken {
    source_did:  DID,
    target_did:  DID,
    granted_by:  DeviceId,             // Ký bởi thiết bị cục bộ
    permissions: Vec<Permission>,      // read | write | stream | ai_context
    expires_at:  u64,                  // Unix timestamp
    signature:   Ed25519Signature,     // Ký bởi DeviceIdentityKey trong SEP
}

// Payload bọc ngoài khi truyền dữ liệu thực tế
pub struct IpcMessage {
    token: DelegationToken,
    payload: Vec<u8>,                  // Data hoặc CAS Hash
    is_tainted: bool,                  // Kế thừa cờ TAINTED từ F-10 (AST Sanitizer)
}
```

**Tương tác với Kiến trúc Mới (F-09 & F-10 Integration):**

- **Blind Context Sharing (Chia sẻ ngữ cảnh mù):** Thay vì truyền toàn bộ nội dung file qua IPC gây nặng RAM, `.tapp` A chỉ cần gửi `cas_hash` (Tham chiếu mã hóa). `.tapp` B sẽ dùng `cas_hash` này để yêu cầu AI đọc trực tiếp thông qua luồng Blind RAG của F-09/F-10.
- **Taint Propagation (Lan truyền thẻ phạt):** Nếu dữ liệu mà `.tapp` A chia sẻ có nguồn gốc từ một phản hồi AI bị đánh dấu `TAINTED` (do chứa mã độc HTML/Prompt Injection theo F-10), cờ `is_tainted` sẽ đi kèm sang `.tapp` B. Nếu `.tapp` B thực thi nội dung này và bị lỗi, hệ thống sẽ biết nguồn gốc độc hại xuất phát từ `.tapp` A để đình chỉ chính xác.
- **IPC Rate Limiting:** Áp dụng cơ chế bảo vệ phần cứng. Tối đa **100 messages/giây** giữa 2 `.tapp`. Vượt quá sẽ trả về `ERR_IPC_RATE_LIMITED` để chống Spam/DDoS nội bộ.

**Dependencies:**

- REF: TERA-CORE §4.2 — `UICommand`, `CoreSignal` cho IPC mediation.
- REF: TERA-CORE §4.3 — Token Protocol; không truyền con trỏ thô (raw pointer) giữa các sandboxes.
- REF: TERA-CORE §3.2 — OPA Policy Engine thực thi tại cổng giao tiếp.
- REF: TERA-FEAT §F-09 — Tích hợp `cas_hash` vào luồng chia sẻ file.
- REF: TERA-FEAT §F-10 — Kế thừa AST Sanitizer và trạng thái `TAINTED`.

**Data Interaction:**

- **Reads:** Đọc `DelegationToken` từ bộ lưu trữ KV `hot_dag.db`.
- **Writes:** Ghi `DelegationToken` mới vào `hot_dag.db` khi có sự chấp thuận.
- **RAM:** Dữ liệu IPC đi qua RAM luôn được bọc trong bộ đệm an toàn và tự động giải phóng bởi Rust Ownership, không ghi vào ổ cứng (trừ tham chiếu Hash).

**Constraints:**

- Maximum auto-grant TTL: 30 ngày. Thời hạn dài hơn yêu cầu chính sách MDM của Admin.
- Revocation: Admin thu hồi qua Admin Console. Áp dụng qua OPA policy push (Hiệu lực trong vòng ≤ 60s khi online).
- Token bị can thiệp (sai chữ ký Ed25519) sẽ bị Core từ chối ngay lập tức trước khi dữ liệu kịp truyền đi.

**Failure Handling:** → §10.4 (Runtime Failure)

- Target `.tapp` đang bị đình chỉ (F-10) hoặc đã tắt: Lưu payload vào hàng đợi (queue) cục bộ. Phân phối lại khi `.tapp` hoạt động.
- Token hết hạn: Trả về `ERR_DELEGATION_TOKEN_EXPIRED`; kích hoạt lại hộp thoại yêu cầu người dùng cấp quyền.
- OPA policy thay đổi đột ngột giữa phiên: Trả về `ERR_TOKEN_REVOKED`; ngắt kết nối IPC ngay lập tức.

---

### F-09: Media and File Transfer (E2EE & Blind RAG Optimized)

**Description:** Trình quản lý truyền tải và lưu trữ tệp tin đa phương tiện/tài liệu dựa trên kiến trúc Zero-Knowledge. Hỗ trợ băm nhỏ tệp (chunking), mã hóa E2EE theo luồng, và tải lên thông qua URL được ký trước (Presigned URLs) lên Cụm VPS (Blind Storage). Các tệp tài liệu (PDF, Word) tải lên sẽ tự động kích hoạt luồng trích xuất Vector nội bộ phục vụ cho Blind RAG (F-10).

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux.

**Mesh Mode behavior:** Tính năng truyền tệp qua Cụm VPS bị vô hiệu hóa. Tự động chuyển sang P2P Wi-Fi Direct (phạm vi < 20m) thông qua mDNS. Giao diện (UI) hiển thị: *"Mesh Mode: Tệp tin chỉ được gửi trực tiếp giữa các thiết bị ở gần."*

**Luồng Xử lý Gửi (Send Flow — Dual Pipeline):**
Hệ thống phân loại luồng dựa trên loại tệp: *Media (Ảnh/Video)* hoặc *Document (PDF/DOCX cho AI)*.

1. **Chuẩn bị & Băm nhỏ (Chunking):** * User chọn tệp. Core chia tệp thành các đoạn nhỏ (chunks) 2 MB.
2. **Mã hóa Cục bộ (E2EE Local Encryption):**
    - Mỗi chunk được mã hóa: `ciphertext_i = AES-256-GCM(ChunkKey_i, chunk_i, nonce_i)`.
    - Cơ chế `ZeroizeOnDrop` dọn sạch `ChunkKey_i` và `chunk_i` bản rõ (plaintext) khỏi RAM ngay sau khi mã hóa xong.
3. **Khử trùng lặp an toàn (Workspace-Scoped Deduplication):**
    - Để bảo vệ Zero-Knowledge, VPS *không được phép* biết mã Hash của file gốc.
    - Hash khử trùng lặp được tính dựa trên bản mã hóa: `cas_hash = BLAKE3(ciphertext_1 || ... || ciphertext_n)`. VPS chỉ đối chiếu `cas_hash` này để tiết kiệm dung lượng (rất hiệu quả trong môi trường Enterprise khi nhân viên forward cùng một file đã mã hóa trong một nhóm).
4. **Tải lên (Upload):**
    - Yêu cầu Presigned URLs từ VPS Cluster (`PUT /v1/presign`). URL sống (TTL) trong 15 phút.
    - Tải lên tối đa 3 chunks đồng thời để tránh nghẽn băng thông Mobile.
5. **Tạo mỏ neo (Stubbing):** * Sinh ra `CRDT_Event { content_type: MediaRef, payload: ZeroByteStub }` (chứa BlurHash cho ảnh, hoặc metadata tài liệu) và ghi vào `hot_dag.db` để đồng bộ.
6. **Blind RAG Trigger (Chỉ dành cho Documents):**
    - Ngay trong lúc upload, máy cục bộ sẽ trích xuất text, nhúng Vector và gửi lên VectorDB theo đặc tả của F-10.

**Luồng Xử lý Nhận/Đọc (Receive & Stream Flow):**

1. **Hiển thị Tức thì:** UI của người nhận/hoặc UI của sổ chat AI lập tức render Zero-Byte Stub (Ảnh BlurHash hoặc icon PDF) mà không cần tải file thật.
2. **Streaming theo yêu cầu (On-Demand):** Người dùng bấm mở hoặc AI cần đọc file -> Core xin Presigned URLs từ Cụm VPS (TTL 5 phút).
3. **Giải mã & Kết xuất:** Tải chunk -> `AES-256-GCM` giải mã trên RAM -> đưa vào `RingBuffer_2MB` để UI render hoặc AI đọc. `ZeroizeOnDrop` xóa sạch RAM ngay sau khi xử lý.

**iOS Background Transfer (Bảo đảm SLA cho Mobile):**

- URL được ủy quyền cho `NSURLSession Background Transfer Service` của iOS.
- Khi tải xong, iOS đánh thức App trong cửa sổ 30s. Core dùng `mmap` đọc và giải mã vào Hệ thống tệp ảo (VFS).
- Sử dụng `ShadowMigrationLock` để tránh xung đột dữ liệu nếu ứng dụng đang chạy nền.

**Data Interaction & Integration:**

- **Storage Node (VPS):** Chỉ lưu trữ các đoạn `ciphertext` không thể đọc được. (Blind Storage).
- **F-10 Integration:** F-09 chịu trách nhiệm lưu trữ nguyên bản tài liệu mã hóa. Khi Blind RAG (F-10) tìm thấy Vector tương đồng, nó sẽ gọi F-09 tải chính xác chunk chứa nội dung đó về máy cục bộ để giải mã và đưa cho mô hình AI.

**Constraints (Giới hạn hệ thống):**

- **Kích thước file tối đa:** 10 GB (Stream theo chunk, không bao giờ load toàn bộ file vào RAM để chống OOM).
- **Bảo mật bộ nhớ:** `ChunkKey` bắt buộc gọi `ZeroizeOnDrop` ở cấp độ Rust Core.
- **VPS Stateless:** VPS không lưu trữ vĩnh viễn Presigned URLs; chúng được tạo bằng HMAC stateless và tự hủy khi hết hạn.

**Failure Handling (Xử lý sự cố Runtime):**

- **Mất kết nối giữa chừng:** Hỗ trợ Resume (Tiếp tục) từ chunk upload thành công cuối cùng dựa vào `Hydration_Checkpoint` lưu trong `hot_dag.db` cục bộ.
- **Lỗi 1 Chunk tải lên:** Thử lại tối đa 3 lần (Backoff: 1s, 2s, 4s). Quá 3 lần: Báo `MEDIA_UPLOAD_FAILED` cho UI.
- **Lỗi Node Lưu trữ (VPS):** Cụm MinIO/Storage sử dụng cấu hình **Erasure Coding (EC+4)**. Việc sập 1-2 node lưu trữ vật lý hoàn toàn không ảnh hưởng đến dữ liệu (Đảm bảo SLA 99.999%).

---

---

### F-10: AI / SLM Integration (Hybrid Cloud & Blind AI)

**Description:** Trình suy luận Hybrid Language Model hỗ trợ kiến trúc Bring Your Own Model (BYOM). TeraChat Core hoạt động như một client siêu nhẹ, định tuyến luồng suy luận một cách bảo mật đến **Stateless Secure Engine** (Cụm VPS) thông qua E2EE Prompt Tunneling, hoặc đến **Local Engine** bị cô lập hoàn toàn. Toàn bộ tiến trình xử lý AI được cách ly nghiêm ngặt (không cấp quyền truy cập API/Terminal từ bên ngoài) nhằm bảo vệ System Prompts và tài sản trí tuệ (IP).

**Supported Platforms:** 📱 iOS (CoreML/Cloud), 📱 Android (ONNX/Cloud), 💻 macOS, 🖥️ Windows, 🖥️ Linux.

**Mesh Mode behavior:** AI tự động chuyển về chạy hoàn toàn trên Local Engine (nếu BYOM đã được cấu hình và thiết bị còn đủ RAM). Nếu không có mô hình cục bộ nào khả dụng, AI sẽ bị vô hiệu hóa và trả về `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED`.

**Security & Connection Enforcement (Bảo mật Kết nối & Cách ly):**

- **Local Engine:** Giao tiếp giữa TeraChat Core và mô hình AI sử dụng **Anonymous Pipes/IPC** ở cấp độ hệ điều hành để đảm bảo tính cô lập tuyệt đối.
- **VPS Cluster:** Giao tiếp bên ngoài sử dụng **mTLS (Mutual TLS)** kết hợp **Dynamic App Attestation** (Xác thực ứng dụng sinh động). Chỉ các tệp thực thi (binaries) của TeraChat client đã được xác minh tính toàn vẹn mới có thể thiết lập kết nối.

**Inference Backend Priority (Được thực thi bởi `resolve_inference_backend()`):**

1. **VPS Stateless Enclave (Cloud):** Động cơ chính cho các tính năng quy mô doanh nghiệp. Sử dụng E2EE Prompt Tunneling. Việc định tuyến Node được quản lý bởi các Load Balancer (HAProxy/Nginx). → `InferenceBackend::VpsCluster`
2. **Local BYOM (Custom User Model):** Thực thi cục bộ qua IPC nếu người dùng có sẵn mô hình và RAM khả dụng > 200MB. → `InferenceBackend::LocalIsolated`
3. **TeraEdge Desktop on LAN:** Nút mạng nội bộ (mDNS `_terachat-edge._tcp.local`; latency < 50 ms). → `InferenceBackend::RemoteDesktop`
4. Tất cả đều không khả dụng → `InferenceBackend::Unavailable`.

**E2EE Prompt Tunneling & PII Handling (Xử lý Dữ liệu Nhạy cảm E2EE):**

1. **Mã hóa (Encryption):** Câu hỏi của người dùng (User prompt) và System Prompt được TeraChat Core mã hóa cục bộ (AES-256) bằng khóa phiên (session keys).
2. **Xử lý trên RAM (In-Memory Processing):** Cụm VPS nhận Ciphertext (Dữ liệu đã mã hóa), giải mã trực tiếp **trên RAM** bên trong một Stateless Enclave và tiến hành sinh text bằng AI.
3. **Không để lại dấu vết (Zero-Trace):** Ngay sau khi sinh xong kết quả, VPS xóa sạch vùng RAM đó. Không có bất kỳ Log hay Database cache nào được ghi lại (Kích hoạt `ZeroizeOnDrop` phía cluster).
4. **Kết quả:** Trả về payload AST đã được mã hóa cho client cục bộ để client tự giải mã và hiển thị.

**Blind RAG & Data Management (Tìm kiếm Mù & Quản lý Dữ liệu):**

- **Vector hóa (Vectorization):** Client cục bộ tự động băm nhỏ tài liệu (Word, PDF) và tạo ra các vector nhúng (semantic vector embeddings).
- **Lưu trữ Mã hóa (Encrypted Storage):** Các đoạn text thô (raw chunks) được mã hóa cục bộ (AES-256) và lưu trữ dưới dạng Ciphertext trên ổ cứng của Cụm VPS.
- **Tìm kiếm Mù (Blind Search):** Client *chỉ gửi* vector của câu hỏi lên VectorDB của VPS. VPS thực hiện đối chiếu độ tương đồng (sử dụng các Node RAG độc lập qua `vLLM`) và trả về các đoạn tài liệu mã hóa tương ứng. Client nhận về, tự giải mã cục bộ để cung cấp ngữ cảnh (context) cho LLM.

**VPS Cluster Optimization (Tối ưu hạ tầng để đạt SLA 99.999%):**

- **Continuous Batching & PagedAttention:** Vận hành bởi `vLLM` để quản lý hàng trăm KV Caches cùng lúc một cách hiệu quả, tránh tràn VRAM (OOM) và tăng thông lượng (throughput) lên gấp 5 lần.
- **Semantic Caching:** Giảm độ trễ xuống mức mili-giây cho các câu hỏi bị lặp lại hoặc có ý nghĩa ngữ nghĩa tương đồng mà không cần kích hoạt lại GPU để tính toán.

**Plugin Rate Limiting & Hardware Protection (Bảo vệ phần cứng & Chống Spam):**

- **Token Quota:** Hoàn toàn **KHÔNG GIỚI HẠN (Unlimited)** đối với `InferenceBackend::LocalIsolated` và cấu hình VPS tự lưu trữ (BYOM) của doanh nghiệp.
- **`.tapp` Rate Limiting:** Để ngăn các plugin (`.tapp`) sinh ra các vòng lặp vô hạn gây treo máy, hệ thống giới hạn request:
  - Tối đa **50 inference requests / phút** trên mỗi `.tapp`.
  - Vượt ngưỡng: Trả về lỗi `ERR_TAPP_RATE_LIMITED` và tạm ngưng `.tapp` đó trong 60 giây.
- **Auto-Kill (Bảo vệ RAM/VRAM):** Nếu một phiên suy luận do `.tapp` gọi tiêu thụ quá 90% tài nguyên được cấp (RAM cục bộ hoặc VRAM trên Node RAG), TeraChat Core sẽ lập tức ngắt tiến trình (SIGKILL qua IPC) và trả về `ERR_RESOURCE_EXHAUSTED`.

**iOS CoreML Parity Path (Ràng buộc W^X trên iOS):**

- Hệ điều hành iOS tuân thủ nghiêm ngặt App Store Rule 2.5.2. Local BYOM trên iOS sẽ phụ thuộc vào việc import các gói CoreML (`.mlmodelc`) hợp lệ.
- Các tác vụ nặng mặc định được đẩy lên E2EE VPS Cluster để bảo vệ RAM và thời lượng pin của thiết bị.

**Prompt Injection Defense:**

- Rust Core bọc kết quả LLM (đã giải mã) trong `Vec<ASTNode>` (AST Sanitizer). Cố tình chèn mã HTML thô hoặc mã thực thi sẽ bị từ chối.
- Nếu vi phạm flag `TAINTED` lần thứ 3 trong cùng một phiên: Đình chỉ `.tapp` vi phạm và phát ra `CoreSignal::ComponentFault`.

**Data Interaction:**

- **Reads:** Ngữ cảnh tin nhắn người dùng (chỉ đọc ở cục bộ); Phản hồi API LLM đã được giải mã.
- **Writes:** Kết quả suy luận gửi đến `.tapp` thông qua chuỗi `Vec<ASTNode>` đã được khử trùng (sanitized).
- **Storage:** Mọi tương tác dữ liệu ra bên ngoài (remote) chỉ lưu trữ dưới dạng Ciphertext (Mã hóa) hoặc Vector embeddings.

**Failure Handling (Xử lý sự cố Runtime):**

- VPS Cluster không thể truy cập / mTLS lỗi: Trả về `ERR_AI_CLUSTER_UNAVAILABLE`. Tự động gọi Local BYOM (nếu có).
- AST Sanitizer từ chối phản hồi: Trả về `ERR_AI_RESPONSE_TAINTED`.
- Xác thực ứng dụng thất bại (App Attestation Failure): Đóng kết nối lập tức; phát ra `CoreSignal::ComponentFault { severity: Critical }`. Ghi log `AuditEvent::AttestationViolation`.

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

*(No patches in this version. Content unchanged from v0.5.0.)*

---

### INFRA-07: BYOM VPS Secure Engine

**Description:** A stateless VPS-hosted AI inference engine that executes customer-supplied (Bring Your Own Model) LLM/SLM weights in complete isolation. The engine communicates exclusively with the TeraChat application binary via mTLS + Dynamic App Attestation Token. No external tool, API client, or terminal can directly probe the model endpoint. All inference occurs on RAM; no prompt, response, or intermediate tensor is persisted to disk. After each session, RAM is wiped via `ZeroizeOnDrop`.

**Supported Platforms:** ☁️ VPS Cluster Nodes (Linux, dedicated AI Node tier)

**Dependencies:** INFRA-09 (Load Balancer routes requests to available Engine nodes), `crypto/enclave_session.rs`, `infra/byom_engine.rs`, TERA-CORE §5.1 (Ed25519), TERA-CORE §9.1 (Crypto primitives)

**Core Security Properties:**

| Property | Mechanism |
|---|---|
| External API isolation | Model worker behind Anonymous Pipe / Unix domain socket with `SOCK_CLOEXEC`; no TCP/UDP listener |
| Anti-spoofing (curl/Postman) | `DynamicAttestationToken` (Ed25519-signed, 60 s TTL, nonce-protected); VPS validates on every request |
| Zero plaintext persistence | All computation in RAM; session key ZeroizeOnDrop after response; no log files written |
| Model integrity | BLAKE3 hash + Ed25519-signed `ByomManifest` verified before engine load; mismatch → `SecurityEvent::ModelIntegrityViolation` |
| Tenant isolation | Each tenant BYOM model runs in a separate Linux cgroup + seccomp sandbox; inter-tenant RAM isolation enforced |

**User Flow — BYOM Model Deployment:**

1. Enterprise IT Admin uploads signed BYOM model package (`.tera-model` bundle) via Admin Console.
2. TeraChat Root CA countersigns `ByomManifest` (model_id, BLAKE3 hash, allowed_tenants).
3. VPS Secure Engine node downloads model over mTLS; verifies Ed25519 signature + BLAKE3 hash before extracting.
4. Engine spawns isolated model worker process: `prctl(PR_SET_NO_NEW_PRIVS)` + seccomp allowlist (Linux) or AppContainer (Windows).
5. Communication between Engine and Worker: anonymous pipe (no network socket).
6. Engine registers model as available in Cluster Load Balancer (INFRA-09).

**User Flow — E2EE Inference Request:**

1. Client Rust Core generates `DynamicAttestationToken` (signed by `DeviceIdentityKey` in Secure Enclave, TTL 60 s, CSPRNG nonce).
2. Client performs X25519 handshake with VPS Secure Engine (authenticated by mTLS cert) → derives `Enclave_Session_Key`.
3. Client runs local PII redaction (dual-mask NER) on prompt.
4. Client AES-256-GCM encrypts masked prompt + `Enclave_Session_Key` → `E2eePromptBlob`.
5. Client sends `{ E2eePromptBlob, DynamicAttestationToken }` over mTLS to `/v1/byom/infer`.
6. VPS Engine validates `DynamicAttestationToken` (Ed25519 verify + TTL + nonce dedup). Reject on any failure → `ERR_ATTESTATION_INVALID`.
7. Engine decrypts `E2eePromptBlob` in RAM → passes plaintext to model worker via anonymous pipe.
8. Model worker tokenizes → forward pass → detokenizes → returns response bytes over pipe.
9. Engine AES-256-GCM encrypts response with `Enclave_Session_Key` → returns `E2eeResponseBlob`.
10. Client decrypts response → de-tokenizes PII aliases → ZeroizeOnDrop session key.
11. VPS Engine ZeroizeOnDrop: session key, plaintext prompt, model activation tensors.

```text
VPS Secure Engine Lifecycle per Request:
  mTLS Accept → Attestation Verify → X25519 Handshake
      │
      ▼ (RAM only; no disk I/O)
  Decrypt Prompt → Pipe to Worker → Inference → Pipe Response
      │
      ▼
  Encrypt Response → Return → ZeroizeOnDrop(session_key, prompt, activations)
```

**BYOM Model Bundle Format (`.tera-model`):**

```text
bundle.tera-model/
├── weights/            # Model weights (GGUF / SafeTensors format)
├── tokenizer.json      # Tokenizer config
├── manifest.json       # {model_id, blake3_hash, max_ctx_tokens, allowed_tenants[], version}
└── manifest.ed25519    # Ed25519 signature by TeraChat Root CA
```

**Constraints:**

- Model worker process has NO outbound network access: `seccomp` blocks `socket()`, `connect()`, `sendmsg()`.
- Maximum model size: 70 B parameters (quantized to 4-bit = ~40 GB); larger models require dedicated bare-metal nodes.
- Inference timeout: 120 s per request; exceeded → kill worker, ZeroizeOnDrop, return `ERR_INFERENCE_TIMEOUT`.
- BYOM feature requires `License_JWT.features` to include `"byom_enclave"`.

**Observability:**

- Signal: `SecurityEvent::ModelIntegrityViolation` on BLAKE3 mismatch during model load.
- Signal: `SecurityEvent::AttestationRejected { reason }` on invalid `DynamicAttestationToken`.
- Metric: `byom_inference_latency_p99_ms`, `byom_session_zeroize_count`, `byom_attestation_failures_total`.
- Log: `BYOM_MODEL_LOADED { model_id, tenant_id }` (Audit, INFO).
- Log: `BYOM_INFERENCE_TIMEOUT { model_id, request_id }` (ERROR).

**Failure Handling:** → §10.4 (Runtime Failure)

- `DynamicAttestationToken` invalid / expired: return `ERR_ATTESTATION_INVALID`; do not proceed to decryption.
- Model worker crash: ZeroizeOnDrop pipe buffers; return `ERR_BYOM_WORKER_CRASHED`; restart worker for next request.
- RAM pressure on VPS node: INFRA-09 Load Balancer routes new requests to least-loaded node; current request continues.
- Model integrity check fails at load: emit `SecurityEvent::ModelIntegrityViolation`; engine refuses to serve; Admin Console alert.

---

### INFRA-08: Blind RAG — Zero-Knowledge Vector Search

**Description:** Enables Retrieval-Augmented Generation (RAG) over enterprise documents without the VPS ever seeing plaintext content. The client device performs all text extraction and embedding generation locally. Only AES-256-GCM encrypted embedding vectors are stored in the server-side VectorDB. Query results are returned as ciphertext; the client decrypts locally. The VectorDB node operates as a "blind index" — it stores and searches encrypted numerical arrays with no semantic knowledge of the underlying documents.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux (client-side embedding), ☁️ VPS VectorDB Node (server-side blind index)

**Dependencies:** INFRA-07 (BYOM Enclave provides inference over retrieved context), INFRA-09 (VectorDB node in Cluster), `infra/blind_rag.rs`, `crypto/embedding_key.rs`, TERA-CORE §9.1

**Zero-Knowledge Guarantee:**

```text
Client Device                      VPS VectorDB
─────────────                      ────────────
Plaintext chunk                    (never sees plaintext)
    │
    ▼
Local embedding model              Stores:
(ONNX/CoreML/HiAI)                 - AES-256-GCM(embedding_vector, Embedding_Key)
    │                              - vec_hash = BLAKE3(encrypted_vector)
    ▼
AES-256-GCM encrypt ─────────────► Blind index by vec_hash
(Embedding_Key in Secure Enclave)
                                   Query:
Blind query vector ───────────────► ANN search on encrypted vectors
(AES-256-GCM encrypted query)      Returns top-K vec_hashes
                                        │
Client decrypts ◄────────────── Encrypted chunk references
  → plaintext context
  → send to BYOM Enclave (F-10)
```

**User Flow — Document Indexing:**

1. User selects document (PDF, Word, text) for RAG indexing in Admin Console or chat UI.
2. Rust Core reads file locally; text extraction via `pdf-extract` / `docx-rs` crates.
3. Core splits into semantic chunks (~512 tokens each).
4. Core runs local embedding model (ONNX/CoreML) → `Vec<f32>` per chunk (e.g., 768 dimensions).
5. Core derives `Embedding_Key` from `Company_Key + "rag-embed-v1" + doc_id` via HKDF.
6. Core AES-256-GCM encrypts each `embedding_vector` with `Embedding_Key` → `EncryptedEmbeddingVector`.
7. Core computes `vec_hash = BLAKE3(EncryptedEmbeddingVector)` for deduplication.
8. Core stores `(vec_hash, EncryptedEmbeddingVector, encrypted_chunk_ref)` in VectorDB over mTLS.
9. VectorDB node indexes by `vec_hash` and approximate spatial structure of encrypted vectors. Plaintext chunk content never transmitted.
10. Emit `CoreSignal::StateChanged { table: "rag_index", version }`.

**User Flow — RAG Query:**

1. User asks a question in chat with RAG context enabled.
2. Rust Core embeds the query locally → `query_vector: Vec<f32>`.
3. Core derives `Query_Session_Key` (ephemeral, ZeroizeOnDrop) → AES-256-GCM encrypt `query_vector`.
4. Core sends `BlindQueryVector` + `DynamicAttestationToken` to VectorDB over mTLS.
5. VectorDB performs approximate nearest-neighbour (ANN) search in encrypted space → returns top-K `vec_hashes`.
6. Core fetches corresponding `EncryptedEmbeddingVector` + `encrypted_chunk_ref` entries.
7. Core decrypts chunk references with `Embedding_Key` (from Secure Enclave) → plaintext context chunks.
8. Core assembles RAG context prompt (plaintext, client-side only) → feeds to F-10 BYOM Enclave pipeline.
9. BYOM Enclave generates response over E2EE Prompt Tunnel.
10. `Query_Session_Key` ZeroizeOnDrop after step 7.

**Embedding Model Selection:**

| Platform | Model | Dimensions | Size | Notes |
|---|---|---|---|---|
| 📱 iOS | CoreML `MiniLM-L6-v2` port | 384 | ~22 MB | W^X compliant; loaded via `MLModel` |
| 📱 Android / Huawei | ONNX `MiniLM-L6-v2` | 384 | ~22 MB | ONNX Runtime; HiAI delegate on Huawei |
| 💻🖥️ Desktop | ONNX `all-mpnet-base-v2` | 768 | ~420 MB | Higher quality for enterprise docs |
| ☁️ VPS (optional) | BYOM custom embedding | configurable | configurable | Tenant-specific via INFRA-07 |

**VectorDB Backend:**

- Primary: `pgvector` extension on PostgreSQL (available in existing TERA-CORE §9 PostgreSQL HA cluster).
- Alternative: `Qdrant` for dedicated high-throughput deployments (> 10M vectors).
- ANN algorithm: HNSW (Hierarchical Navigable Small World) — O(log N) query time.
- Encryption: stored vectors are opaque AES-256-GCM blobs; VectorDB computes ANN on raw bytes without decryption (approximate distance computed via `vec_hash` locality-preserving scheme; precision is intentionally reduced to prevent inference attacks).

**Constraints:**

- Maximum corpus size: 10 GB of plaintext (embeddings ~10% of source size).
- Embedding `Embedding_Key` never transmitted to VectorDB; stored only in Secure Enclave / StrongBox.
- Mesh Mode: RAG indexing and querying disabled. Return `ERR_SURVIVAL_MODE_ACTIVE_RAG_DISABLED`.
- `Query_Session_Key` ZeroizeOnDrop immediately after chunk decryption in step 7.

**Observability:**

- Metric: `blind_rag_index_chunks_total`, `blind_rag_query_latency_p99_ms`, `blind_rag_top_k_hit_rate`.
- Log: `BLIND_RAG_INDEX_COMPLETE { doc_id, chunk_count, tenant_id }` (INFO).
- Log: `BLIND_RAG_EMBEDDING_KEY_MISSING { doc_id }` (WARN) — triggers re-index prompt.

**Failure Handling:**

- Embedding model OOM: fallback to keyword search (Rust `tantivy` local FTS index); emit `CoreSignal::ComponentFault { component: "rag_embed", severity: Warning }`.
- VectorDB unreachable: return stale results from local `hot_dag.db` RAG cache (last 100 queries); emit `CoreSignal::TierChanged`.
- `Embedding_Key` missing (device re-enrollment): re-index required; emit `CoreSignal::StateChanged { table: "rag_index", version: NEEDS_REINDEX }`.

---

### INFRA-09: VPS Cluster High-Availability Architecture (SLA 99.999%)

**Description:** Specifies the cluster-level infrastructure for serving > 400 concurrent AI inference requests at SLA 99.999% (~5 min downtime/year). The architecture separates AI inference nodes from VectorDB nodes, uses HAProxy/Nginx for load balancing, vLLM with Continuous Batching and PagedAttention for GPU/CPU throughput maximization, and a Semantic Cache layer to serve repeated queries without GPU computation.

**Supported Platforms:** ☁️ VPS Cluster (multi-node, Linux bare-metal or dedicated VPS)

**Reference Deployment (Enterprise Cluster — 5000 users, ~400 concurrent AI sessions):**

```text
Internet
    │ TLS 1.3 + mTLS
    ▼
┌──────────────────────────────────────────────────────────┐
│  HAProxy Load Balancer (Active/Standby, Keepalived)       │
│  Algorithm: Least-Connections; health check /v1/health    │
│  Failover: 3 s (Keepalived VRRP Floating IP)             │
└─────────────────────────┬────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  AI Node 1   │  │  AI Node 2   │  │  AI Node 3   │
│  vLLM engine │  │  vLLM engine │  │  vLLM engine │
│  BYOM model  │  │  BYOM model  │  │  BYOM model  │
│  8 vCPU      │  │  8 vCPU      │  │  8 vCPU      │
│  32 GB RAM   │  │  32 GB RAM   │  │  32 GB RAM   │
│  (GPU opt.)  │  │  (GPU opt.)  │  │  (GPU opt.)  │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼                             ▼
┌──────────────────┐          ┌──────────────────────┐
│  VectorDB Node 1 │          │  Semantic Cache       │
│  pgvector/Qdrant │          │  Redis Cluster        │
│  (Blind RAG)     │          │  (encrypted blobs;    │
│  Replication →   │          │   keyed by embed hash)│
│  VectorDB Node 2 │          └──────────────────────┘
└──────────────────┘
          │
┌──────────────────┐
│  Message Queue   │
│  (Async tasks:   │
│  heavy doc RAG   │
│  indexing jobs)  │
└──────────────────┘
```

**vLLM Continuous Batching + PagedAttention:**

vLLM is the inference engine on each AI Node. Its two key optimizations address the primary bottleneck of serving many concurrent users:

- **Continuous Batching:** Instead of processing one request at a time (offline batching), vLLM processes multiple requests simultaneously, interleaving token generation. New requests join the batch mid-flight. This increases GPU utilization from ~20% (naive) to ~80%+ and multiplies throughput by 5–10×.
- **PagedAttention:** LLM KV-Cache (the memory of previous tokens in a conversation) is managed like OS virtual memory paging. Instead of pre-allocating a contiguous block per session (wasting VRAM when sessions differ in length), PagedAttention allocates KV-Cache in non-contiguous pages. Result: near-zero VRAM fragmentation, supporting 5× more concurrent sessions on the same hardware.

```text
vLLM PagedAttention — KV-Cache Memory Model:
  
  Traditional:       [Session A: 4096 tokens reserved] [Session B: 4096] [wasted]
  PagedAttention:    [A:512][B:512][A:512][C:512][A:512][B:512] ← packed, no waste
  
  Benefit: 1× GPU can serve 5× more concurrent sessions
```

**Semantic Cache Layer (Redis):**

Identical or semantically near-identical queries (cosine similarity > 0.95 on embedding vector) are served from the Redis cache without invoking the GPU. Cache entries store AES-256-GCM encrypted response blobs keyed by the embedding hash.

```rust
pub async fn query_with_semantic_cache(
    query_vector: &[f32],
    cache: &SemanticCache,
    engine: &ByomEngine,
    session_key: &EnclaveSessionKey,
) -> Result<PlaintextResponse> {
    let embed_hash = blake3::hash(&encode_f32_array(query_vector));

    // Cache hit: decrypt and return without GPU inference
    if let Some(cached_blob) = cache.get(&embed_hash).await? {
        let plaintext = aes256gcm_decrypt(&session_key.key, &cached_blob)?;
        return Ok(PlaintextResponse::from_bytes(&plaintext)?);
    }

    // Cache miss: invoke BYOM Enclave
    let response = engine.infer(query_vector, session_key).await?;

    // Store encrypted response in cache (TTL 10 min)
    let encrypted = aes256gcm_encrypt(&session_key.key, response.as_bytes())?;
    cache.set_with_ttl(&embed_hash, &encrypted, Duration::from_secs(600)).await?;

    Ok(response)
}
```

**Message Queue (Async Heavy Tasks):**

Document indexing jobs (large PDF, > 50 pages) are processed asynchronously via the Message Queue to prevent blocking the synchronous inference path:

- Queue backend: Redis Streams (reuses existing Redis cluster) or dedicated RabbitMQ.
- Task types: `RagIndexDocument { doc_id, encrypted_chunks[], tenant_id }`.
- Worker concurrency: 4 indexing workers per VectorDB node.
- Dead-letter queue: failed tasks after 3 retries → `INFRA_QUEUE_DEAD_LETTER` audit log.

**HAProxy Configuration:**

```haproxy
frontend ai_frontend
    bind *:443 ssl crt /etc/ssl/terachat.pem
    default_backend ai_nodes

backend ai_nodes
    balance leastconn
    option httpchk GET /v1/health
    server ai-node-1 10.0.1.10:8080 check inter 2s fall 2 rise 3
    server ai-node-2 10.0.1.11:8080 check inter 2s fall 2 rise 3
    server ai-node-3 10.0.1.12:8080 check inter 2s fall 2 rise 3
```

**Node Sizing Reference:**

| Component | Min Spec (CPU inference) | Recommended (GPU-accelerated) | Max Concurrent Sessions |
|---|---|---|---|
| AI Node (CPU) | 8 vCPU, 32 GB RAM | 16 vCPU, 64 GB RAM | ~50 concurrent |
| AI Node (GPU) | 8 vCPU, 32 GB RAM, 1× A100 40 GB | 16 vCPU, 64 GB RAM, 2× A100 | ~400 concurrent |
| VectorDB Node | 4 vCPU, 16 GB RAM, 200 GB NVMe | 8 vCPU, 32 GB RAM, 1 TB NVMe | 10M+ vectors |
| Redis Cache | 2 vCPU, 8 GB RAM | 4 vCPU, 16 GB RAM | N/A |
| HAProxy | 2 vCPU, 4 GB RAM (Active) + Standby | 4 vCPU, 8 GB RAM | N/A |

**Reliability — SLA 99.999% Mechanism:**

| Failure Scenario | Detection | Recovery | Downtime |
|---|---|---|---|
| AI Node crash | HAProxy health check fail (2 consecutive, 2 s interval) | Remove node from pool; remaining nodes absorb load | < 4 s |
| HAProxy primary failure | Keepalived VRRP monitor (1 s interval) | Floating IP migrates to Standby HAProxy | < 3 s |
| VectorDB Node failure | pgRepmgr / Qdrant replication health | Standby promotes to primary; `pgRepmgr switchover` | < 30 s |
| Redis Cache failure | Redis Sentinel (3-node quorum) | Sentinel promotes replica; cache miss falls through to AI Node | 0 s (graceful degradation) |
| GPU OOM on AI Node | vLLM OOM handler | Evict lowest-priority KV-Cache pages (PagedAttention); retry | 0 s (handled in-process) |

**Auto-Scaling Trigger (Cloud deployments):**

- Scale out: AI Node CPU > 80% for > 60 s OR inference queue depth > 50 tasks → add node.
- Scale in: AI Node CPU < 20% for > 300 s AND queue depth = 0 → remove node (min 2 nodes always retained).
- VectorDB: scale by storage only; no auto-scale on CPU (ANN queries are I/O-bound).

**Constraints:**

- Minimum 2 AI Nodes required at all times for HA (single node = SLA 99.9% only).
- vLLM requires Linux with glibc ≥ 2.31 (Ubuntu 20.04+); Windows/macOS not supported for AI Node role.
- Semantic Cache TTL must not exceed `License_JWT.session_timeout_minutes` to prevent stale enterprise context.
- Redis must have `maxmemory-policy allkeys-lru` to prevent OOM eviction of critical security tokens.

**Observability:**

- Metric: `cluster_ai_node_count`, `cluster_inference_queue_depth`, `semantic_cache_hit_rate`, `vllm_gpu_utilization_pct`, `haproxy_backend_active_servers`.
- Metric: `cluster_p99_inference_latency_ms` (target: < 3000 ms for 7B model on CPU; < 500 ms with GPU).
- Log: `CLUSTER_NODE_REMOVED { node_id, reason }` (WARN).
- Log: `CLUSTER_SCALE_OUT_TRIGGERED { trigger_metric, current_value }` (INFO).
- Log: `INFRA_QUEUE_DEAD_LETTER { task_id, attempts, error }` (ERROR, Audit).

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

### §5.2 Mesh Role State Machine (Offline Survival / Hybrid Cloud Fallback)

**Applies to:** F-05 (Mesh Network) & F-01 (Causal Consistency)
**Description:** Máy trạng thái định tuyến luồng giao tiếp P2P nội bộ khi thiết bị mất kết nối với Cụm VPS (Internet Unavailable). Đảm bảo tính nhất quán dữ liệu E2EE thông qua cơ chế khóa nhân quả (`CAUSAL_FREEZE`) nhằm ngăn chặn xung đột mạng (Split-Brain) trước khi đồng bộ lại lên Cloud.

**States (Danh sách Trạng thái):**

| State | Eligible Platforms | Conditions |
|---|---|---|
| `LeafNode` | All | Trạng thái mặc định cho iOS; trạng thái dự phòng (fallback) cho Android/Desktop khi yếu pin/RAM. |
| `RelayNode` | Android, Huawei | RAM ≥ 3 GB && battery ≥ 40%. Đóng vai trò chuyển tiếp tín hiệu BLE/Wi-Fi Direct. |
| `SuperNode` | macOS, Windows, Linux | Có nguồn điện AC (Cắm sạc). Xử lý định tuyến nặng và kết nối mạng diện rộng. |
| `TacticalRelay` | iOS only (EMDP) | Không có Desktop; Internet sập; có ≥ 2 thiết bị iOS trong mạng; battery > 20%. |
| `BorderNode` | Any | Tự động gán: `internet_available == true && ble_active == true`. Đóng vai trò Cầu nối (Gateway) để đồng bộ dữ liệu từ Mesh lên VPS Cluster. |
| **`CAUSAL_FREEZE`** | **iOS (EMDP)** | **[PATCH Issue-05]:** EMDP đang kích hoạt; đột ngột mất tín hiệu Desktop trước khi Key Escrow được truyền tải. |

**Transitions (Các chuyển đổi Trạng thái):**

| From | To | Trigger |
|---|---|---|
| `LeafNode` | `RelayNode` | Android: RAM ≥ 3 GB && battery ≥ 40% |
| `LeafNode` | `SuperNode` | Desktop được cắm nguồn AC |
| `SuperNode` | `LeafNode` | Sắp cạn RAM/sắp bị iOS Jetsam kill; tự động phát tín hiệu `MeshRoleHandover` |
| `LeafNode` | `TacticalRelay` | Đủ điều kiện kích hoạt EMDP (Mạng nội bộ iOS thuần) |
| `TacticalRelay` | `LeafNode` | Hết TTL; không tìm thấy node nhận handoff; HOẶC Desktop kết nối lại |
| `RelayNode` | `LeafNode` | Battery < 40% hoặc RAM < 3 GB |
| `LeafNode` / `Tactical` | **`CAUSAL_FREEZE`** | Đột ngột rớt mạng Desktop giữa tiến trình EMDP (Ngăn chặn Split-Brain) |
| **`CAUSAL_FREEZE`** | `TacticalRelay` | Desktop kết nối lại và truyền tải thành công `EmdpKeyEscrow` mới |
| **`CAUSAL_FREEZE`** | `LeafNode` | Timeout sau 60s không thấy Desktop (Hủy EMDP, chờ khởi tạo lại) |
| Any | `BorderNode` | `internet_available == true && ble_active == true` (Tự động kích hoạt song song với các role khác để đẩy `.hot_dag` lên VPS) |

**Constraints (Ràng buộc hệ thống):**

- **iOS JetSam Defense:** Hardcoded `election_weight = 0` tại `mesh/election.rs` đối với iOS. (iOS không bao giờ được chọn làm Relay/SuperNode chính thức do hệ điều hành giới hạn background). Bất kỳ PR nào cố tình sửa hằng số này sẽ bị đánh dấu là **BLOCKER (FI-05)**.
- **Causal Freeze Safety:** Khi một thiết bị rơi vào `CAUSAL_FREEZE`, toàn bộ thao tác ghi mới (ghi `CRDT_Event` vào `hot_dag.db`) từ người dùng sẽ bị tạm xếp hàng (queued). UI hiển thị thông báo: *"Đang đồng bộ mạng cục bộ..."* để tránh sinh ra dữ liệu rác không có khóa Escrow.

**Signals:**

- Phát ra `CoreSignal::MeshRoleChanged { new_role: MeshRole }` trên mỗi lần chuyển đổi trạng thái để UI phản hồi kịp thời.
- Khi thoát Mesh để lên lại Cloud qua `BorderNode`, phát ra `CoreSignal::CloudSyncResumed`.

---

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
8. Receiver's UI renders Zero-Byte Stub immediately (BlurHash preview from encrypted thumbnail).
9. User taps to open. Core requests presigned download URLs from TeraRelay. TTL 5 min.
10. Per chunk: download → `ChunkKey_i = HKDF(Epoch_Key, "chunk" || cas_hash || i)` → AES-256-GCM decrypt → `tera_buf_acquire` → write to `RingBuffer_2MB`.
11. `CoreSignal::StateChanged` → UI renders chunk. `ZeroizeOnDrop` on `ChunkKey_i` and plaintext after render.
12. After all chunks: `CoreSignal::MediaComplete { cas_hash }`.
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

**Description:** Local Small Language Model (SLM) inference and cloud LLM routing for `.tapp` plugins. PII is redacted before any data leaves the device. Inference is isolated in a separate process (crash-safe from Rust Core). All ONNX model loads must pass `OnnxModelLoader.load_verified()` (PLATFORM-18). Cloud inference routes through the BYOM VPS Secure Engine (INFRA-07) via E2EE Prompt Tunneling; the VPS never sees plaintext prompts.

**Supported Platforms:** 📱 iOS (CoreML), 📱 Android (ONNX), 📱 Huawei (HiAI), 💻 macOS (ONNX/CoreML), 🖥️ Windows (ONNX), 🖥️ Linux (ONNX), ☁️ VPS Secure Engine (BYOM/vLLM)

**Mesh Mode behavior:** AI fully disabled. Return `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` for all inference requests.

**Inference Backend Priority (enforced by `resolve_inference_backend()`):**

1. TeraEdge Desktop on LAN (mDNS `_terachat-edge._tcp.local`; latency < 50 ms; load < 80%) → `InferenceBackend::RemoteDesktop`.
2. Local model if RAM sufficient and battery > 30% → `InferenceBackend::Local`.
3. BYOM VPS Secure Engine (INFRA-07) via E2EE Prompt Tunnel (requires Internet + valid `DynamicAttestationToken`) → `InferenceBackend::ByomEnclave`.
4. Generic VPS Enclave (shared cloud, PII redacted) → `InferenceBackend::VpsEnclave`.
5. Downgrade model tier (e.g., Base → Tiny) and retry → lower tier local.
6. All unavailable → `InferenceBackend::Unavailable`.

**[NEW v0.6.0] E2EE Prompt Tunneling to BYOM VPS Secure Engine:**

The BYOM Secure Engine is the primary cloud AI backend for Enterprise tenants. It operates as a stateless enclave: no logs, no disk persistence, RAM-only inference. The client maintains zero-knowledge: the VPS sees only ciphertext blobs.

```rust
pub async fn invoke_byom_enclave(
    prompt: &PlaintextPrompt,
    enclave_pubkey: &Curve25519PublicKey,
    attestation_token: &DynamicAttestationToken,
    session_key: &mut EnclaveSessionKey,
) -> Result<PlaintextResponse, ByomError> {
    // Step 1: PII redaction before any encryption
    let masked = pii_redact_dual_mask(prompt)?;

    // Step 2: Encrypt with ephemeral Enclave_Session_Key
    let nonce = ring::rand::generate::<[u8; 12]>()?;
    let blob = aes256gcm_encrypt(&session_key.key, &nonce, masked.as_bytes())?;

    // Step 3: Wrap blob + attestation token; send over mTLS
    let req = E2eePromptRequest {
        encrypted_blob: blob,
        nonce,
        attestation_token: attestation_token.clone(),
        tenant_id: session_key.tenant_id.clone(),
    };
    let raw_response = mtls_post("/v1/byom/infer", &req).await?;

    // Step 4: Decrypt response in RAM; ZeroizeOnDrop on session key after use
    let plaintext_response = aes256gcm_decrypt(&session_key.key, &raw_response.nonce, &raw_response.blob)?;
    session_key.zeroize();

    // Step 5: De-tokenize PII aliases back to real values
    Ok(pii_detokenize(&plaintext_response, &masked.alias_map)?)
}
```

**[NEW v0.6.0] Dynamic App Attestation Token — Anti-Spoofing:**

The VPS Secure Engine rejects any request not carrying a valid `DynamicAttestationToken`. This prevents direct API access via `curl`, Postman, or any tool that is not the genuine TeraChat application binary.

```rust
#[derive(ZeroizeOnDrop)]
pub struct DynamicAttestationToken {
    pub app_binary_hash: [u8; 32],   // BLAKE3(app binary at runtime)
    pub timestamp_hlc:   HlcTimestamp,
    pub nonce:           [u8; 32],   // CSPRNG; prevents replay
    pub tenant_id:       TenantId,
    pub ed25519_sig:     Ed25519Signature, // signed by DeviceIdentityKey in Secure Enclave
}

impl DynamicAttestationToken {
    /// Token valid for 60 seconds. Nonce prevents replay within the window.
    pub fn generate(enclave: &SecureEnclave) -> Result<Self> {
        let app_hash = blake3::hash(current_binary_bytes());
        let nonce = ring::rand::generate::<[u8; 32]>()?;
        let payload = TokenPayload { app_binary_hash: app_hash, timestamp_hlc: HlcClock::now(), nonce, tenant_id: enclave.tenant_id() };
        let sig = enclave.ed25519_sign(&payload.encode())?;
        Ok(DynamicAttestationToken { ed25519_sig: sig, ..payload.into() })
    }
}
```

**[NEW v0.6.0] BYOM Model Isolation — Anonymous Pipe / IPC:**

When running locally on a Gov air-gap node or on-premise VPS, the BYOM model process is isolated via anonymous pipe (not a network socket), preventing all external API access:

```text
TeraChat Secure Engine Process
    │ Anonymous Pipe / IPC (OS kernel — no network socket)
    ▼
BYOM Model Worker Process (sandboxed, no network access)
    │ Tokenize → Forward pass → Detokenize
    ▼
Response bytes → back over anonymous pipe → Secure Engine
```

- On Linux: `pipe()` / `socketpair(AF_UNIX, SOCK_STREAM, 0)` with `SOCK_CLOEXEC`.
- On macOS/Windows: `std::os::unix::net::UnixStream` / Named Pipe with restricted ACL.
- Model worker process: `prctl(PR_SET_NO_NEW_PRIVS)` + seccomp allowlist (Linux) / AppContainer (Windows).
- External probes (`curl http://localhost:PORT`) → refused; no listening TCP/UDP socket exposed.

**Memory Budget Enforcement:**

- ONNX/CoreML allocator: 8 MB hard ceiling (custom allocator returns `AllocError` on overflow → graceful fallback to Flat-search).
- Runtime monitor: `tikv-jemallocator` `malloc_stats_print` polls heap every 5 s. If heap > 6 MB: reduce batch size 32 → 8 vectors/batch.
- VPS Secure Engine RAM: 150 MB ceiling per inference session; enforced by Rust `MemoryArbiter`; session ZeroizeOnDrop on completion.

**Whisper Model Tier Selection:**

```rust
pub fn select_whisper_tier(available_ram_mb: u32, battery_pct: u8) -> WhisperModelTier {
    if battery_pct < 20    { return WhisperModelTier::Disabled; }
    if available_ram_mb > 200 { return WhisperModelTier::Base; }  // 74 MB
    if available_ram_mb > 100 { return WhisperModelTier::Tiny; }  // 39 MB
    WhisperModelTier::Disabled
    // On Disabled: emit CoreSignal::StateChanged with note "Voice transcription unavailable."
}
```

**PII Redaction (Interactive SLM Dual-Masking):**

1. Core runs local NER (ONNX/CoreML, < 1 MB) to identify PII: names, phone numbers, email addresses.
2. PII replaced with aliases: `[REDACTED_PHONE_1]`, `[REDACTED_EMAIL_1]`.
3. Masked prompt encrypted via `Enclave_Session_Key` and sent to BYOM Enclave or VPS Enclave.
4. LLM returns encrypted response. Core decrypts and de-tokenizes aliases to real values.
5. `SessionVault` `ZeroizeOnDrop` clears alias map within 100 ms.

**AI Quota Enforcement:**

- Per-`.tapp`: 10,000 tokens/hour on shared VPS Enclave.
- BYOM Enclave (INFRA-07): quota defined in `License_JWT.features.byom_tokens_per_hour`; unlimited on Enterprise plan.
- Overage: return `ERR_AI_QUOTA_EXCEEDED`. UI presents upgrade prompt.

**KV-Cache Management:**

- Mobile: 1 KV-Cache slot active at a time. Inactive slots: LZ4-compressed to storage.
- Desktop: multiple KV-Cache slots in Hot RAM simultaneously.
- VPS Secure Engine: KV-Cache managed by vLLM PagedAttention (see INFRA-09); never persisted to disk.

**iOS CoreML Parity Path (W^X constraint):** CoreML model loaded only in Main App process via `MLModel(contentsOf:)`. No WASM, no ONNX in NSE path (see PLATFORM-18). BYOM Enclave path not available from NSE; deferred to Main App wakeup.

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
| `EmdpCausalFreeze` | `reason: CausalFreezeReason` | **[NEW v0.5.0]** Sudden Desktop loss before escrow |
| `DeadManWarning` | `hours_remaining: u32` | T-12 h and T-1 h offline grace period |
| `TierChanged` | `new_tier: NetworkTier, reason: TierChangeReason` | ALPN tier change or AWDL loss |
| `DagMergeProgress` | `completed: u64, total: u64` | Every 200 ms when merge backlog > 500 events |
| `XpcHealthDegraded` | `crash_count: u32, window_secs: u32` | macOS XPC crash rate exceeds threshold |
| `MemoryPressureWarning` | `component: &str, allocated_mb: u32` | `MemoryArbiter` allocated > 80% ceiling |
| `MediaComplete` | `cas_hash: [u8; 32]` | All media chunks downloaded and decrypted |
| `ByomInferenceComplete` | `session_id: Uuid, latency_ms: u32` | **[NEW v0.6.0]** BYOM Enclave returned encrypted response |
| `ByomAttestationRejected` | `reason: AttestationRejectReason` | **[NEW v0.6.0]** VPS rejected `DynamicAttestationToken` |
| `BlindRagIndexComplete` | `doc_id: Uuid, chunk_count: u32` | **[NEW v0.6.0]** Document indexed in VectorDB |
| `BlindRagQueryComplete` | `query_id: Uuid, top_k: u8, latency_ms: u32` | **[NEW v0.6.0]** RAG query returned top-K results |
| `ClusterNodeDegraded` | `node_id: &str, reason: &str` | **[NEW v0.6.0]** HAProxy removes AI Node from pool |

### §6.2 UICommand Catalog

---

## §7 — PLATFORM MATRIX

### §7.1 Feature Availability Matrix

> Canonical feature availability and constraint reference.

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
| F-10: AI / SLM | ✅ CoreML | ✅ ONNX | ✅ HiAI | ✅ | ✅ | ✅ | N/A | BYOM Enclave |
| F-11: Device Security | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |
| F-12: Identity | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | HSM anchor | N/A |
| F-13: Admin Console | read-only | read-only | read-only | ✅ | ✅ | ✅ | ✅ | ✅ |
| F-14: Network Mgmt | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |
| F-15: Crash-Safe WAL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | N/A | N/A |
| INFRA-07: BYOM Engine | client trigger | client trigger | client trigger | client trigger | client trigger | client trigger | ✅ (on-prem) | ✅ VPS Node |
| INFRA-08: Blind RAG | ✅ embed local | ✅ embed local | ✅ embed local | ✅ embed local | ✅ embed local | ✅ embed local | VectorDB local | VectorDB cluster |
| INFRA-09: Cluster HA | N/A | N/A | N/A | N/A | N/A | N/A | ✅ | ✅ |

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
| BYOM E2EE Prompt Tunnel round-trip (CPU inference, 7B model) | < 3000 ms P99 | INFRA-07 |
| BYOM E2EE Prompt Tunnel round-trip (GPU inference, 7B model) | < 500 ms P99 | INFRA-07 |
| `DynamicAttestationToken` generation (Secure Enclave sign) | < 50 ms | INFRA-07 |
| Blind RAG local embedding (MiniLM-L6-v2, 512 tokens) | < 150 ms mobile; < 30 ms desktop | INFRA-08 |
| Blind RAG VectorDB ANN query (pgvector HNSW, 1M vectors) | < 50 ms | INFRA-08 |
| Semantic Cache lookup (Redis, encrypted blob) | < 5 ms | INFRA-09 |
| HAProxy node failover | < 4 s (2 health checks × 2 s interval) | INFRA-09 |
| Keepalived VRRP floating IP failover | < 3 s | INFRA-09 |

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
| BYOM AI Node crash | HAProxy removes node < 4 s; remaining nodes absorb load; no user-visible error | INFRA-09 |
| HAProxy primary failure | Keepalived VRRP failover < 3 s; Standby assumes Floating IP | INFRA-09 |
| VectorDB primary node failure | pgRepmgr standby promotion < 30 s; RAG queries degrade to stale cache | INFRA-08/09 |
| Redis Semantic Cache failure | Cache miss falls through to AI Node; 0 s degradation (graceful) | INFRA-09 |
| BYOM model integrity check fail at load | Engine refuses to serve; Admin Console alert; `SecurityEvent::ModelIntegrityViolation` | INFRA-07 |
| BYOM inference timeout (> 120 s) | Worker killed; ZeroizeOnDrop; `ERR_INFERENCE_TIMEOUT` returned to client | INFRA-07 |

### §8.5 Scalability

| Dimension | Constraint | Source |
|---|---|---|
| MLS group size / platform count | No hardcoded limits; TERA-CORE §10.3 governs | FD-07 / ATD-09 |
| TURN node capacity | ~50 concurrent HD streams per node | F-06 |
| VPS Solo tier | ≤ 50 users | INFRA-04 |
| VPS SME tier | ≤ 500 users | INFRA-04 |
| VPS Enterprise tier | ≤ 5000 users | INFRA-04 |
| VPS Enterprise Cluster tier | ≤ 50 000 users; ≥ 3 AI Nodes + 2 VectorDB Nodes + HAProxy | INFRA-09 |
| BYOM model max size | 70 B parameters (4-bit quantized, ~40 GB); larger = dedicated bare-metal | INFRA-07 |
| Blind RAG corpus max | 10 GB plaintext per tenant; pgvector supports 10M+ vectors per node | INFRA-08 |
| Concurrent AI inference (CPU cluster) | ~50 sessions per node × N nodes | INFRA-09 |
| Concurrent AI inference (GPU cluster, A100) | ~400 sessions per node × N nodes (vLLM PagedAttention) | INFRA-09 |
| Semantic Cache hit rate target | > 30% for enterprise repetitive queries (reduces GPU load by 30%+) | INFRA-09 |
| Stale data accumulation | Every feature with persistent data must specify cleanup/expiry (ATD-10) | §9 ATD-10 |

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
| Dart FFI double-release | Use-after-free on Android | Generation counter in token registry rejects stale tokens |
| ALPN probe race | Permanent QUIC disable on working networks | Per-protocol fail count; QUIC win resets count |
| BLE GATT pre-auth | ML-KEM public key fingerprinting | GATT challenge-response before any key material exchange |
| Dead Man Switch deferral | Insider threat via call-to-defer | DeadManDeferralEntry in tamper-proof Audit Log before deferral |
| LLM prompt injection | Malicious `.tapp` output | AST Sanitizer; 3rd TAINTED → `.tapp` suspend |
| Protocol downgrade | QUIC → WSS forced | QUIC-Pinning State Machine |
| **[NEW v0.6.0] BYOM direct API probe** | `curl`/Postman bypasses TeraChat to query model directly; exfiltrates System Prompt | Anonymous Pipe isolation (no TCP/UDP listener); `DynamicAttestationToken` required on every request; no token = no decryption |
| **[NEW v0.6.0] DynamicAttestationToken replay** | Attacker captures valid token and replays within TTL window | CSPRNG nonce in token payload; VPS maintains nonce dedup set per 60 s TTL window; replayed nonce → `ERR_ATTESTATION_INVALID` |
| **[NEW v0.6.0] BYOM model exfiltration** | Attacker extracts model weights from VPS disk | Model weights loaded into RAM only; not persisted to VPS disk; `prctl(PR_SET_NO_NEW_PRIVS)` + seccomp on worker; no `ptrace` access |
| **[NEW v0.6.0] Blind RAG embedding inference attack** | Attacker queries VectorDB with many crafted vectors to infer plaintext document content | AES-256-GCM encrypted vectors stored; VectorDB has no decryption key; approximate distance on ciphertext yields near-zero semantic information |
| **[NEW v0.6.0] Semantic Cache poisoning** | Malicious tenant stores crafted encrypted response to redirect future queries | Cache keyed by BLAKE3(embedding_vector); each tenant's `Embedding_Key` is unique; cross-tenant cache hit structurally impossible |
| **[NEW v0.6.0] VPS Secure Engine memory dump** | Attacker gains root on VPS node; dumps RAM to find plaintext prompts | ZeroizeOnDrop immediately after inference; `MADV_DONTDUMP` on sensitive allocations; session key never written to swap |

### §9.5 Implementation Contract — Security Rules

| Rule ID | Rule | Enforcement |
|---|---|---|
| SEC-01 | No plaintext UI buffer outlives the render frame. | `cargo miri test`. CI failure: blocker. |
| SEC-02 | No `Vec<u8>`, `*const u8`, or `*mut u8` in `pub extern "C"`. | CI Clippy lint. Blocker. |
| SEC-03 | All clipboard operations route through Protected Clipboard Bridge. | Code review + CI. |
| SEC-04 | WASM sandbox: `PROT_READ`-only DAG access. | Runtime enforcement. |
| SEC-05 | iOS Keychain access groups segmented (NSE / Main / Share). | Keychain entitlement. |
| SEC-06 | Dead Man Switch deferral: `DeadManDeferralEntry` in Audit Log before deferral. | Code review; Audit Log validator. |
| SEC-07 | GATT pre-auth challenge-response before ML-KEM key exchange. | Integration test in TestMatrix SC-22. |
| **SEC-08 [NEW v0.6.0]** | **BYOM VPS Secure Engine: model worker process MUST NOT have any network socket (TCP/UDP). All IPC via anonymous pipe or Unix domain socket only. Any PR adding `socket()` or `bind()` to worker: blocker.** | **seccomp policy CI test; `strace` socket call audit.** |
| **SEC-09 [NEW v0.6.0]** | **`DynamicAttestationToken` nonce MUST be CSPRNG-generated per request. Token reuse, static nonce, or predictable nonce: blocker.** | **CI randomness audit; token nonce entropy test.** |
| **SEC-10 [NEW v0.6.0]** | **Blind RAG `Embedding_Key` MUST NOT be transmitted to VectorDB node in any form. Violation: immediate blocker.** | **Network trace CI test; no `Embedding_Key` bytes in VectorDB connection traffic.** |
| **SEC-11 [NEW v0.6.0]** | **VPS Secure Engine inference RAM MUST apply `MADV_DONTDUMP` to session key and plaintext prompt allocations. Core dump must not contain decryptable prompt content.** | **coredump analysis CI test on crash simulation.** |

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
| `Embedding_Key` missing (Blind RAG, device re-enrolled) | Re-index required; emit `CoreSignal::StateChanged { table: "rag_index", version: NEEDS_REINDEX }` | `BLIND_RAG_EMBEDDING_KEY_MISSING` |
| `Enclave_Session_Key` expired mid-session (BYOM) | Perform new X25519 handshake; retry inference; ZeroizeOnDrop stale key | None (transparent retry) |

### §10.4 Runtime Failure

| Condition | Component | Response | Signal |
|---|---|---|---|
| XPC Worker crash, PENDING journal missing | macOS | Impossible — `synchronous=FULL` ensures PENDING is durable before dispatch | `CoreSignal::ComponentFault` |
| Dart FFI GC finalizer double-release | Android, Huawei | Generation counter in Rust registry → stale token rejected as no-op | CI BLOCKER metric |
| BYOM inference worker crash | VPS Secure Engine | ZeroizeOnDrop pipe buffers; return `ERR_BYOM_WORKER_CRASHED`; spawn new worker for next request | `CoreSignal::ByomAttestationRejected` (if attestation-related) |
| BYOM inference timeout (> 120 s) | VPS Secure Engine | Kill worker process; ZeroizeOnDrop session key; return `ERR_INFERENCE_TIMEOUT` | `BYOM_INFERENCE_TIMEOUT` log |
| BYOM model integrity failure at load | VPS Secure Engine | Engine refuses to serve BYOM requests; emit `SecurityEvent::ModelIntegrityViolation`; Admin Console alert | `BYOM_MODEL_INTEGRITY_VIOLATION` |
| `DynamicAttestationToken` invalid | VPS Secure Engine | Return `ERR_ATTESTATION_INVALID` immediately; do not proceed to X25519 handshake or decryption | `BYOM_ATTESTATION_REJECTED` log |
| All BYOM AI Nodes unhealthy (HAProxy) | VPS Cluster | Return `ERR_CLUSTER_NO_HEALTHY_NODES`; fallback to `InferenceBackend::Local` if available | `CLUSTER_NODE_REMOVED` for each node |
| VectorDB node unreachable (Blind RAG) | VPS Cluster | Serve stale results from local `hot_dag.db` RAG cache (last 100 queries); emit `TierChanged` | `BLIND_RAG_VECTORDB_UNREACHABLE` |
| Semantic Cache (Redis) failure | VPS Cluster | Cache miss falls through to AI Node; 0 s user impact; log degradation | None (graceful) |
| Async indexing task dead-letter (3 retries) | Message Queue | Emit Admin Console alert; require manual re-index via `UICommand::ReindexDocument` | `INFRA_QUEUE_DEAD_LETTER` |

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

**[NEW v0.6.0] INFRA-07 BYOM Engine — No client schema migration required:**

BYOM Secure Engine is a server-side infrastructure feature. No `hot_dag.db` or `cold_state.db`
schema changes on the client. The `ByomManifest` and `DynamicAttestationToken` are in-memory
only; they are never persisted to local SQLite.

**[NEW v0.6.0] INFRA-08 Blind RAG VectorDB — New `rag_index` table on client:**

A new `rag_index` table is added to `hot_dag.db` to track indexed document metadata:

```sql
-- v0.6.0 migration — additive; no existing data affected
CREATE TABLE IF NOT EXISTS rag_index (
    doc_id       TEXT PRIMARY KEY,
    tenant_id    TEXT NOT NULL,
    chunk_count  INTEGER NOT NULL,
    vec_hash_root BLOB NOT NULL,       -- BLAKE3 Merkle root of all vec_hashes
    indexed_at   INTEGER NOT NULL,     -- HLC timestamp
    embedding_key_epoch INTEGER NOT NULL  -- epoch of Embedding_Key used; detect staleness
);
```

Migration: `ALTER TABLE`-based additive migration; `PRAGMA user_version` bumped from 5 to 6. No
data loss. `cold_state.db` rebuild from `hot_dag.db` safe as always (DB-02 invariant holds).

**[NEW v0.6.0] INFRA-09 Cluster HA — Server-side only:**

`device_push_versions` table, `pgvector` extension, and Redis cluster are server-side
infrastructure. No client schema migration required. Client detects cluster availability via
existing ALPN negotiation path (INFRA-07 endpoint resolves to cluster HAProxy VIP).

### §11.2 Backward Compatibility

| Contract | Policy |
|---|---|
| `CRDT_Event` format | Immutable after append; must remain deserializable across all future versions |
| `CoreSignal` enum | Additive only; no field removal without deprecation cycle |
| `UICommand` enum | Additive only; no field removal without deprecation cycle |
| `DelegationToken` fields | Additions permitted; removals require migration path |
| `sled` crate version | Must be pinned in `Cargo.toml` (FI-04) |
| `NetworkProfile` schema | Additive changes permitted; reset on network change |
| `rag_index` table (v0.6.0) | Additive; `cold_state.db` rebuild safe; no breaking change |
| `ByomManifest` / `DynamicAttestationToken` | In-memory only; not persisted; no migration needed |
| BYOM inference API (`/v1/byom/infer`) | Versioned endpoint; `min_api_version` in `ByomManifest`; server negotiates |

---

## §12 — OBSERVABILITY

### §12.1 Named Log Events

| Event ID | Condition | Feature | Level |
|---|---|---|---|
| `COLD_STATE_REBUILD` | `cold_state.db` dropped and rebuilt | F-04 | INFO |
| `STRONGBOX_UNAVAILABLE` | Android StrongBox fallback | F-11/F-12 | WARN |
| `HUAWEI_CRL_STALE` | Huawei CRL delay caused deferred decryption | F-02 | WARN |
| `HUAWEI_PUSH_KEY_VERSION_BUMPED` | Server bumped version on revocation | F-02 | AUDIT |
| `FCM_CDM_REVOKED` | Android CDM association missing | F-02 | WARN |
| `EMDP_CAUSAL_FREEZE` | Sudden Desktop loss before escrow | F-05 | WARN |
| `DEAD_MAN_SWITCH_DEFERRED` | Deferral logged with counter delta | F-11 | AUDIT |
| `ALPN_PROBE_RACE_WIN` | QUIC won parallel race; gRPC fail count NOT incremented | F-14 | DEBUG |
| `OFFLOAD_HMAC_VIOLATION` | HMAC mismatch on ONNX offload | INFRA-01 | AUDIT |
| `INVALID_RECOVERY_TICKET` | Recovery Ticket Ed25519 invalid | F-12 | AUDIT |
| `MEDIA_UPLOAD_FAILED` | Chunked upload failed after 3 retries | F-09 | ERROR |
| `PIN_COUNTER_CORRUPTED` | Failed_PIN_Attempts counter tampered | F-11e | AUDIT |
| `ONNX_OOM_FALLBACK` | ONNX allocator OOM | F-10 | WARN |
| `BYOM_MODEL_LOADED` | BYOM model loaded and verified on VPS Secure Engine | INFRA-07 | AUDIT |
| `BYOM_MODEL_INTEGRITY_VIOLATION` | BLAKE3 hash mismatch on BYOM model load | INFRA-07 | AUDIT |
| `BYOM_ATTESTATION_REJECTED` | `DynamicAttestationToken` invalid/expired/replayed | INFRA-07 | AUDIT |
| `BYOM_INFERENCE_TIMEOUT` | Inference exceeded 120 s; worker killed | INFRA-07 | ERROR |
| `BYOM_WORKER_CRASHED` | BYOM model worker process crashed unexpectedly | INFRA-07 | ERROR |
| `BLIND_RAG_INDEX_COMPLETE` | Document indexed in VectorDB | INFRA-08 | INFO |
| `BLIND_RAG_EMBEDDING_KEY_MISSING` | `Embedding_Key` not found; re-index required | INFRA-08 | WARN |
| `BLIND_RAG_VECTORDB_UNREACHABLE` | VectorDB node unreachable; fallback to local FTS | INFRA-08 | WARN |
| `CLUSTER_NODE_REMOVED` | HAProxy health check failed; AI Node removed from pool | INFRA-09 | WARN |
| `CLUSTER_SCALE_OUT_TRIGGERED` | Auto-scaling added new AI Node | INFRA-09 | INFO |
| `INFRA_QUEUE_DEAD_LETTER` | Async indexing task failed after 3 retries | INFRA-09 | ERROR |

### §12.6 Canary Rollback Metrics

---

## §13 — APPENDIX

### §13.2 Error Code Reference

| Error Code | Condition | Feature |
|---|---|---|
| `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` | Mesh Mode active | F-10 |
| `ERR_SURVIVAL_MODE_ACTIVE_RAG_DISABLED` | Mesh Mode active | INFRA-08 |
| `ERR_MESH_MODE_DELEGATION_SUSPENDED` | Mesh Mode active | F-08 |
| `ERR_EMDP_CAUSAL_FREEZE` | Sudden Desktop loss before escrow | F-05 |
| `ERR_FFI_STALE_TOKEN` | Token's generation counter does not match registry | F-03 / PLATFORM-17 |
| `ERR_GATT_PREAUTH_FAILED` | GATT challenge-response failed | F-05 |
| `ERR_RATE_LIMIT_EXCEEDED` | `.tapp` token bucket exhausted | F-07 |
| `ERR_MNEMONIC_INVALID` | BIP-39 mnemonic incorrect | F-12 |
| `ERR_AI_QUOTA_EXCEEDED` | Token quota exceeded | F-10 |
| `BufferNotFound` | Token not in Core registry | F-03 |
| `ERR_ATTESTATION_INVALID` | `DynamicAttestationToken` rejected (invalid sig / expired / replayed) | INFRA-07 |
| `ERR_BYOM_WORKER_CRASHED` | BYOM model worker process crashed | INFRA-07 |
| `ERR_BYOM_FEATURE_NOT_LICENSED` | `License_JWT.features` does not include `"byom_enclave"` | INFRA-07 |
| `ERR_INFERENCE_TIMEOUT` | BYOM inference exceeded 120 s limit | INFRA-07 |
| `ERR_BLIND_RAG_EMBEDDING_KEY_MISSING` | `Embedding_Key` not available; re-index required | INFRA-08 |
| `ERR_BLIND_RAG_VECTORDB_UNREACHABLE` | VectorDB node unreachable; fallback active | INFRA-08 |
| `ERR_CLUSTER_NO_HEALTHY_NODES` | All AI Nodes failed HAProxy health check | INFRA-09 |

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
| FI-06 **[NEW v0.5.0]** | **`PRAGMA wal_checkpoint(TRUNCATE)` is the sole background WAL compaction path. `VACUUM INTO` only under `BEGIN EXCLUSIVE` for admin defrag.** |
| FI-07 **[NEW v0.5.0]** | **XPC journal PENDING write uses dedicated `synchronous=FULL` SQLite connection. PENDING write without fsync: blocker.** |
| FI-08 **[NEW v0.5.0]** | **GATT pre-auth challenge-response must complete before any ML-KEM key material is transmitted over BLE.** |
| FI-09 **[NEW v0.6.0]** | **BYOM VPS Secure Engine MUST NOT listen on any TCP/UDP port accessible to external clients. Model worker communicates only via anonymous pipe / Unix domain socket.** |
| FI-10 **[NEW v0.6.0]** | **`DynamicAttestationToken` required on every BYOM inference request. VPS MUST reject any request missing or with invalid token. Token TTL ≤ 60 s.** |
| FI-11 **[NEW v0.6.0]** | **Blind RAG `Embedding_Key` never transmitted to VectorDB. Key lives only in Secure Enclave / StrongBox. Violation = blocker.** |
| FI-12 **[NEW v0.6.0]** | **VPS Secure Engine RAM must be ZeroizeOnDrop after each inference session. No intermediate tensor, prompt, or session key may persist to disk.** |
| FI-13 **[NEW v0.6.0]** | **Semantic Cache (INFRA-09) stores only AES-256-GCM encrypted response blobs. Plaintext LLM responses never written to Redis.** |

**IPC Rules (IPC):**

| Rule ID | Rule |
|---|---|
| IPC-01 | State flow unidirectional Core → UI. Bidirectional state channel: **blocker**. |
| IPC-02 | SAB Tier Ladder selection logged to audit trail. Silent tier selection: **blocker**. |
| IPC-03 | `CoreSignal::DagMergeProgress` emitted every 200 ms when merge backlog > 500 events. |
| IPC-04 **[NEW v0.5.0]** | **`FfiToken` carries monotonic generation counter. Stale tokens (e.g. from GC finalizer) rejected by Rust registry as no-op.** |
| IPC-05 **[NEW v0.6.0]** | **`DynamicAttestationToken` must be generated fresh per BYOM inference request. Token reuse across requests: blocker.** |

---

## §14 — CHANGELOG

| Version | Date | Summary |
|---|---|---|
| 0.6.0 | 2026-03-25 | Architecture expansion: BYOM VPS Secure Engine (INFRA-07) — stateless AI isolation, E2EE Prompt Tunneling, mTLS + DynamicAttestationToken anti-spoofing, Anonymous Pipe model isolation; Blind RAG (INFRA-08) — client-side embedding, AES-256-GCM encrypted VectorDB; VPS Cluster HA (INFRA-09) — HAProxy, vLLM Continuous Batching + PagedAttention, Semantic Cache, SLA 99.999%; F-10 BYOM backend routing expanded; new CoreSignals; FI-09 through FI-13 contract rules. |
| 0.5.0 | 2026-03-23 | Security audit patch batch: 15 issues fixed. Key changes: PLATFORM-17 Dart FFI generation counter; F-02 NSE RAM table + ONNX prohibition + Huawei revocation fast-path + Android CDM detection; F-04 checkpoint-first WAL + Mutex shadow lock; F-05 EMDP proactive escrow + CAUSAL_FREEZE + GATT pre-auth; F-07 WasmParity Sprint 1 blocker + XPC synchronous=FULL; F-11 DeadManDeferralEntry audit trail; F-13 OPA policy channel schema exemption; F-14 ALPN per-protocol fail count race fix; F-15 full AppArmor/SELinux profiles + --check-permissions subcommand. |
| 0.4.0 | 2026-03-21 | Full restructure to production-grade standard. |
| 0.2.6 | 2026-03-19 | Add OBSERVE-01/02, PLATFORM-17/18/19, INFRA-01–06, CICD-01. |
