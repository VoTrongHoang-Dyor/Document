<!-- markdownlint-disable MD041 -->
```yaml
# DOCUMENT IDENTITY
id:        "TERA-FEAT"
title:     "TeraChat — Feature Technical Specification"
version:  "0.2.6"
status:    "ACTIVE — Implementation Reference"
date:      "2026-03-18"
audience:  "Frontend Engineer, Mobile Engineer, Desktop Engineer, Product Engineer"
purpose:   "Defines all client-facing and system-level features. Maps every feature to a
            verified core module in Core_Spec.md. Governs platform-specific behavior,
            OS lifecycle hooks, IPC bridge, WASM runtime, local storage, and user
            interaction contracts."

depends_on:
  - id: "TERA-CORE"   # Cryptographic primitives, MLS, Mesh, CRDT, infrastructure
consumed_by:
  - id: "TERA-DESIGN" # UI state machine reads IPC signals defined here
  - id: "TERA-MKT"    # Plugin sandbox runtime constraints reference this document
  - id: "TERA-TEST"   # Chaos test scenarios validate feature failure behaviors

ai_routing_hint: |
  Route to this document for: client platform IPC bridge, OS hooks (iOS NSE/CallKit,
  Android FCM, Huawei HMS), WASM .tapp sandbox runtime, local SQLite storage lifecycle,
  push notification handling, platform-specific feature constraints, user interaction
  flows, or any feature-to-core module mapping question.

  Do NOT route here for: MLS cryptographic internals (→ TERA-CORE §5), CRDT merge
  algorithms (→ TERA-CORE §7), server relay infrastructure (→ TERA-CORE §9), or UI
  animation specs (→ TERA-DESIGN).
  This document defines WHAT each feature does and HOW it maps to core systems.
  It does not redefine cryptographic internals or server logic.
```

---

## §0 — DATA OBJECT CATALOG (Client-Side)

> Read this section before implementing any client component.
> Every object is an independent data unit with a defined schema, lifecycle, and security
> constraint. Operations in §4–§6 act on these objects — not on raw platform APIs.
> Internal cryptographic object definitions are in TERA-CORE §0.

### §0.1 Local Storage Objects

| Object | Type | Storage | Lifecycle | Core Ref |
| --- | --- | --- | --- | --- |
| `cold_state.db` | SQLite, SQLCipher AES-256 | Disk, permanent | Until Remote Wipe or Crypto-Shredding | TERA-CORE §7.1 |
| `cold_state_shadow.db` | SQLite, transient | Disk, temporary | Created on Hydration batch; deleted after atomic rename | TERA-CORE §7.1 |
| `hot_dag.db` | SQLite WAL | Disk, permanent | Append-only; cleaned via VACUUM | TERA-CORE §7.1 |
| `nse_staging.db` | SQLite WAL, iOS NSE only | Disk | Per push payload; cleared after Main App decryption | TERA-CORE §5.5 |
| `wal_staging.db` | SQLite WAL, relay only | Disk | Per event; cleared on `Committed` status | TERA-CORE §9.3 |
| `NetworkProfile` | SQLite row | Local config DB | Per network identifier; updated on probe result | TERA-CORE §9.2 |
| `TappTransientState` | `sled` LSM-Tree rows | RAM + disk, per DID | Per `.tapp` session; AES-256-GCM encrypted | TERA-FEAT §F-07 |

### §0.2 In-Memory Ephemeral Objects

| Object | Type | Location | Lifecycle | Core Ref |
| --- | --- | --- | --- | --- |
| `Decrypted_Chunk` | `[u8]` plaintext | RAM, `ZeroizeOnDrop` | Single 2 MB chunk; zeroed after render frame | TERA-CORE §5.3 |
| `ViewportCursor` | `{top_id: Uuid, bottom_id: Uuid}` | RAM | Duration of scroll session | TERA-FEAT §F-03 |
| `RingBuffer_2MB` | Circular fixed buffer | User RAM | Reused across media stream sessions | TERA-FEAT §F-09 |
| `KVCacheSlot` | LZ4-compressed LLM context | RAM | Per `.tapp` session; LZ4-compressed when inactive | TERA-FEAT §F-10 |
| `MemoryArbiter` | `{allocations: HashMap<ComponentId, usize>}` | RAM | Process lifetime; enforces RAM budget matrix | TERA-CORE §3.3 |

### §0.3 IPC Signal and Command Objects

| Object | Type | Transport | Lifecycle | Core Ref |
| --- | --- | --- | --- | --- |
| `CoreSignal` | Typed Rust enum | FFI signal channel | Unidirectional Core → UI; no response expected | TERA-CORE §4.2 |
| `UICommand` | Typed Rust enum | FFI command channel | Consumed once by Core; no replay | TERA-CORE §4.2 |
| `DataPlane_Payload` | Raw bytes | SAB ring buffer / JSI pointer / Dart FFI | Held until `tera_buf_release(token)` called | TERA-CORE §4.3 |
| `FfiToken` | Opaque `u64` | FFI return value | Valid until `tera_buf_release` called | TERA-CORE §4.3 |

### §0.4 Push and Notification Objects

| Object | Type | Storage | Lifecycle | Core Ref |
| --- | --- | --- | --- | --- |
| `Push_Key_N` | AES-256-GCM symmetric key | Secure Enclave (iOS) / StrongBox (Android) | Rotated after each MLS Epoch rotation | TERA-CORE §5.5 |
| `PushKeyVersion` | `u32` | Shared Keychain (iOS) / StrongBox metadata | Incremented on each rotation | TERA-CORE §5.5 |
| `NSE_StagedCiphertext` | Raw ciphertext bytes | `nse_staging.db` | Cleared after successful Main App decryption | TERA-CORE §5.5 |

### §0.5 WASM Plugin Objects

| Object | Type | Storage | Lifecycle | Core Ref |
| --- | --- | --- | --- | --- |
| `DelegationToken` | `{source_did, target_did, permissions, expires_at, signature}` | RAM + `hot_dag.db` | TTL 30 days; revocable by Admin at any time | TERA-FEAT §F-08 |
| `EgressNetworkRequest` | Protobuf | In-flight | Single request; sanitized by Host Proxy | TERA-CORE §4.1 |
| `XpcJournalEntry` | `{tx_id: Uuid, status: Pending\|Verified\|Committed}` | `hot_dag.db` | Per XPC transaction; cleared on Committed | TERA-FEAT §F-07 |

---

## 1. FEATURE OVERVIEW

### 1.1 Scope

This document specifies all client-side and system-level features of TeraChat across five platform environments. Every feature definition includes: supported platforms, user flow, dependency mapping to `Core_Spec.md` (TERA-CORE), data interactions, constraints, and failure handling.

**Feature categories:**

| Category | Features | Section |
| --- | --- | --- |
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

**Out-of-scope for this document:**

- MLS cryptographic internals → TERA-CORE §5
- CRDT merge algorithms → TERA-CORE §7
- Server relay infrastructure → TERA-CORE §9
- UI animations and glassmorphism → TERA-DESIGN
- Plugin publishing and Marketplace review → TERA-MKT
- Chaos engineering test scenarios → TERA-TEST

### 1.2 Platform Environment Summary

| Environment | WASM Runtime | UI Framework | Key Constraints |
| --- | --- | --- | --- |
| 📱 iOS | `wasm3` (no JIT) | Swift + Dart FFI → Rust Core | W^X, NSE ≤ 20 MB, background 30 s, Leaf Node only |
| 📱 Android | `wasmtime` JIT | Kotlin + Dart FFI → Rust Core | Android 14 battery buckets, StrongBox not universal |
| 📱 Huawei | `wasmtime` JIT | ArkTS + Dart FFI → Rust Core | HMS Push Kit, no dynamic WASM, CRL ≤ 4 h lag |
| 💻 macOS | `wasmtime` (XPC Worker) | Swift + Tauri → Rust Core | XPC isolation, AWDL conflicts, SEP key binding |
| 🖥️ Windows | `wasmtime` JIT | Tauri → Rust Core | TPM 2.0, WFP, EV Code Sign via Cloud HSM |
| 🖥️ Linux | `wasmtime` JIT | Tauri → Rust Core | AppArmor/SELinux MAC, seccomp-bpf, .deb/.rpm only |
| 🗄️ Bare-metal | N/A (server) | Rust daemon | HSM PKCS#11, PostgreSQL primary, Shamir quorum |
| ☁️ VPS | N/A (server) | Rust daemon + Tokio | 512 MB RAM min, no kernel modules, no eBPF client-side |

---

## 2. DESIGN PRINCIPLES

### 2.1 Feature Design Invariants

| ID | Invariant | Enforcement |
| --- | --- | --- |
| FD-01 | Every feature maps to exactly one or more Core modules in TERA-CORE | §5 mapping table; orphan features are blockers |
| FD-02 | UI layer holds no crypto keys and no business state | Rust Core is single source of truth; UI is pure renderer |
| FD-03 | Platform-specific code lives in host adapters (Swift/Kotlin), never in Rust Core | `MeshTransport` trait pattern enforces the separation line |
| FD-04 | No feature bypasses the FFI token protocol | `tera_buf_acquire` / `tera_buf_release` on all buffer transfers |
| FD-05 | Every plaintext buffer uses `ZeroizeOnDrop` | Verified by `cargo miri test` in CI; no exceptions |
| FD-06 | Feature degradation is graceful and explicit | Every feature has a defined Failure Handling clause; silent failures are blockers |
| FD-07 | Mesh/Survival mode has a strict, closed feature set | Only text messaging and BLE control signals; list in §8.2 is exhaustive |

### 2.2 IPC Bridge Architecture

**Data Plane transport selection and throughput:**

| Platform | Transport | API | Throughput |
| --- | --- | --- | --- |
| 📱 iOS | C++ JSI Shared Memory Pointer | `UniquePtr` + token protocol | ~400 MB/s |
| 📱 Android | Dart FFI TypedData | Zero-copy into C ABI | ~400 MB/s |
| 📱 Huawei | Dart FFI TypedData | Zero-copy into C ABI | ~400 MB/s |
| 💻 macOS | SharedArrayBuffer ring buffer | COOP+COEP headers required | ~500 MB/s |
| 🖥️ Windows | SAB Tier 1 → Named Pipe fallback | Auto-selected at runtime | ~500 / ~200 MB/s |
| 🖥️ Linux | SAB Tier 1 → Named Pipe → stdin fallback | Auto-selected at runtime | ~500 / ~200 / ~50 MB/s |

**Desktop Tauri IPC Tier Ladder (automatic, no configuration):**

```text
Tier 1: SharedArrayBuffer (COOP+COEP verified)      → ~500 MB/s
Tier 2: Named Pipe (Windows; or SAB unavailable)    → ~200 MB/s
Tier 3: Protobuf over stdin (last resort)           → ~50 MB/s
```

Rust Core detects SAB availability at init and selects the highest tier. UI is unaware of tier. Tier selection is written to the audit trail.

### 2.3 Unidirectional State Flow Contract

State flows in exactly one direction: **Rust Core → UI**. The UI never writes state to Core.

```text
Core mutation (e.g., new CRDT_Event appended to hot_dag.db)
  │  emit CoreSignal::StateChanged { table: "messages", version: u64 }
  ▼
UI receives signal
  │  send UICommand::ScrollViewport { top_message_id, bottom_message_id }
  ▼
Core:
  1. Fetch viewport snapshot from cold_state.db (20 messages)
  2. tera_buf_acquire(operation_id) → opaque u64 token
  3. Write decrypted snapshot to Data Plane buffer
  ▼
UI:
  1. Read buffer using token reference
  2. Render viewport
  3. tera_buf_release(token) → Core ZeroizeOnDrop when ref_count == 0
```

UI never holds decrypted payloads beyond the render frame. Violation is a **blocker**.

---

## 3. PLATFORM SEGMENTATION

### 3.1 Feature Availability Matrix

| Feature | 📱 iOS | 📱 Android | 📱 Huawei | 💻 macOS | 🖥️ Win | 🖥️ Linux | 🗄️ BM | ☁️ VPS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
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

### 3.2 Platform Constraint Reference

**📱 iOS:**

- WASM: `wasm3` interpreter exclusively. No JIT allowed in App Sandbox (W^X).
- NSE RAM: 20 MB hard ceiling (OS-enforced). Ghost Push pattern mandatory for oversized payloads.
- Background network: 30-second window. Voice calls require `CallKit` or network is killed.
- `mlock()`: rejected. Double-Buffer Zeroize pattern required.
- Mesh role: Leaf Node always. Tactical Relay under EMDP only (text-only, TTL 60 min).
- AWDL: disabled when Personal Hotspot or CarPlay is active.
- Keychain: three segmented access groups (NSE-only, Main App-only, Share Extension-only).
- AI: CoreML `.mlmodelc` bundles only. No dynamic WASM AI modules.

**📱 Android:**

- WASM: `wasmtime` JIT.
- Android 14+: FCM throttled to 10/hour in Restricted bucket. Mitigation: FCM `priority = "high"` + Companion Device Manager.
- StrongBox: not universal. Fall back to TEE-backed AndroidKeyStore; log `STRONGBOX_UNAVAILABLE`.
- Mesh: Relay Node eligible if RAM ≥ 3 GB and battery ≥ 40%.

**📱 Huawei HarmonyOS:**

- WASM: `wasmtime` JIT (no W^X restriction).
- Push: HMS Push Kit. No `content-available` background push.
- CRL refresh: ≤ 4 h (foreground polling). Must be disclosed in enterprise SLA.
- Distribution: AppGallery. No dynamic WASM downloads. AOT `.waot` bundles required.

**💻 macOS:**

- WASM: `wasmtime` in XPC Worker (`allow-jit`). Main App entitlement: `NO allow-jit`.
- XPC Worker crash: recovery via `XpcTransactionJournal` (PENDING → VERIFIED → COMMITTED).
- AWDL: same conflict behavior as iOS on Hotspot/CarPlay.

**🖥️ Windows:**

- Signing: EV Code Signing Certificate via Cloud HSM (DigiCert KeyLocker, ~$500/yr).
- SmartScreen reputation: 30+ days of clean submissions required.
- ARM64 (Surface Pro X, Copilot+ PCs): SAB behavior on WebView2 ARM64 requires pre-release validation.

**🖥️ Linux:**

- Flatpak: prohibited (bubblewrap + seccomp conflict). Use `.deb`/`.rpm` (Tier 1) or AppImage + Cosign (Tier 2).
- AppArmor (Ubuntu) / SELinux (RHEL): postinstall script must auto-detect and load MAC profile. Without it: startup crash on `memfd_create` and `ipc_lock` denial.
- Clipboard backend: Wayland → `wl-clipboard`; X11 → `xclip`/`xsel`. Detection via `WAYLAND_DISPLAY` env var at runtime.

### 3.3 RAM Budget Enforcement Matrix (Mobile)

| Component | RAM ≤ 3 GB device | RAM > 4 GB device | Enforcement |
| --- | --- | --- | --- |
| NSE / FCM service | 20 MB hard ceiling | 20 MB hard ceiling | OS-enforced; Circuit Breaker terminates gracefully on breach |
| WASM heap per `.tapp` | 50 MB; max 1 pre-warm | 50 MB; max 2 pre-warm | `MemoryArbiter.acquire()` returns `MemoryDenied` on overage |
| Whisper voice model | Disabled | Tiny model (39 MB) | `select_whisper_tier()` checks RAM + battery before load |
| BLE Mesh buffer | 8 MB | 12 MB | `MemoryArbiter` ceiling |
| ONNX / embedding pipeline | 8 MB hard ceiling | 8 MB hard ceiling | Custom allocator returns `AllocError` on overflow |
| **Total ceiling** | **≤ 100 MB** | **≤ 130 MB** | `MemoryArbiter` reads `sysinfo::available_memory()` at startup |

---

## 4. FEATURE CATALOG

---

### F-01: Secure E2EE Messaging

<!-- INSERTED PATCH: Chunked DAG Merger & Progress UI -->
- 📱 Mobile environments execute `ChunkedDagMerger` logic wrapping hard boundaries over a maximum count allocation limits explicitly set to `MAX_MOBILE_MERGE_EVENTS = 3000`.
- 📱 Excess triggers dispatch an asynchronous payload containing an isolated `SnapshotRequired` IPC signalling spec execution to offload processing to the Desktop layer.
- 📱 Computations expanding boundaries wider than 500 events natively trigger Core progression flags via mapped IPC signals explicitly structured using `DagMergeProgress` schemas.
- 📱 **Mobile UI:** Linear completion bars output mapped text representations limiting block impacts scaling: "Synchronizing [X]% — [Y] messages remaining". Non-blocking background parameters correctly maintain user interactions cleanly.
- 💻🖥️ **Desktop UI:** Embedded mapping renders a subtle background marker positioned on the corner status bar. Eliminating central processing modals inherently respects high desktop background computational bounds.


**Description:** Send and receive text messages encrypted end-to-end using MLS RFC 9420. The VPS relay receives only ciphertext — it has zero access to plaintext, sender identity, or content.

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

**Dependencies:**

- REF: TERA-CORE §5.3 — MLS encrypt/decrypt, `Epoch_Key`, Ed25519 signing
- REF: TERA-CORE §7.1 — `CRDT_Event` schema, `hot_dag.db` append, nonce uniqueness
- REF: TERA-CORE §4.2 — `UICommand::SendMessage`, `CoreSignal::StateChanged`
- REF: TERA-CORE §9.2 — VPS relay, ALPN protocol selection
- REF: TERA-CORE §4.3 — FFI token protocol for viewport buffer transfer

**Data Interaction:**

- Writes: `CRDT_Event` to `hot_dag.db` WAL; `WalStagingEntry` to `wal_staging.db` (relay).
- Reads: `Epoch_Key` from RAM; `cold_state.db` viewport for render.

**Constraints:**

- Plaintext never reaches server under any condition.
- Message delivery order determined by `HLC_Timestamp`, not server receipt time.
- Maximum unpadded plaintext before chunking: 4,096 bytes.
- Biometric authentication required to unlock `DeviceIdentityKey` for every signing operation.
- `CRDT_Event` immutable after append. No update or delete of raw events.

**Failure Handling:**

- Network unavailable at send time: event is durable in `hot_dag.db`. Retry transmits on reconnect.
- MLS Epoch mismatch on receive: Core triggers Peer-Assisted Epoch Re-induction (TERA-CORE §5.3). Delivery retried after `Welcome_Packet` received.
- `Epoch_Key` unavailable (device rejoining group): UI displays "Waiting for key sync…". Message held in `hot_dag.db`. Delivered after epoch key restored.

---

### F-02: Push Notification Delivery (E2EE)

<!-- INSERTED PATCH: Zero-Knowledge Push Notification -->
- ☁️ Struct modifications inside `Push_Key` require standard `version: u32` allocation mapping limits.
- ☁️ NSE routines implement a strict read validation from the payload header configuration parsing keys specifically matched to precise parameter alignment as outlined across `TERA-CORE §17.2`.


**Description:** Deliver E2EE-encrypted push notifications to backgrounded devices. Decryption is local — APNs, FCM, and HMS never receive plaintext.

**Supported Platforms:** 📱 iOS (NSE), 📱 Android (FCM), 📱 Huawei (HMS), 💻 macOS (daemon), 🖥️ Windows (WNS/daemon), 🖥️ Linux (systemd daemon)

**Platform-Specific Behavior:**

| Platform | Push Channel | Process | RAM Constraint |
| --- | --- | --- | --- |
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

**Failure Handling:**

- NSE OOM: Circuit Breaker terminates NSE gracefully. Sets `main_app_decrypt_needed = true`. Main App handles on next foreground transition.
- `Push_Key` not found in Keychain: display generic "New message" notification with no content preview.
- HMS polling delay (Huawei): CRL-dependent decryptions may fail within 4 h window. Log `HUAWEI_CRL_STALE` and defer decrypt to next foreground with refreshed CRL.

---

### F-03: IPC Bridge and State Synchronization

<!-- INSERTED PATCH: Dart FFI Contract — Mandatory Enforcement -->
> **Note: Supersedes PLATFORM-14.** Mandatory contract mapping explicitly tied directly to CI/CD compilation blocks yielding compiler drops upon internal constraint violation sequences.
1. 🔗 Extracted pointers via natively structured `TeraSecureBuffer` elements ALWAYS mandate encapsulation logic specifically run exactly inside `useInTransaction()`.
2. 🔗 The Core Rust Token Registry logic actively bypasses internal zeroization sequence flags over TTL limit bounds directly preferring manual interaction states explicitly invoking `releaseNow()`.
3. 🔗 TTL timeout boundaries crossing limits trigger asynchronous internal structures broadcasting `IpcSignal::TransactionTimeout` flags yielding mapped parameter modals alerting: "Timeout boundary reached, require explicit re-initiation sequences".
4. 🔗 Routine Garbage Collector parsing is heavily depreciated only mapping inside limits specifically structured uniquely as safety-net fallback variables maintaining detailed log tracking capabilities.


**Description:** All communication between Rust Core and the UI layer routes through a strict unidirectional IPC bridge. Core emits typed `CoreSignal` enums; UI sends typed `UICommand` enums. No raw pointer crosses the FFI boundary.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow:**

1. Rust Core completes a DAG update.
2. Core emits `CoreSignal::StateChanged { table: &str, version: u64 }`.
3. UI issues `UICommand::ScrollViewport { top_message_id, bottom_message_id }`.
4. Core fetches 20-message viewport from `cold_state.db`.
5. Core calls `tera_buf_acquire(operation_id)` → returns opaque `u64` token.
6. Core writes decrypted snapshot to Data Plane buffer (SAB ring buffer / JSI pointer / Dart FFI TypedData).
7. UI reads via token reference. Renders viewport.
8. UI calls `UICommand::ReleaseBuffer { token }` → Core `ZeroizeOnDrop` when `ref_count == 0`.

**CoreSignal Catalog (Core → UI, complete):**

| Signal | Payload Fields | Trigger Condition |
| --- | --- | --- |
| `StateChanged` | `table: &str, version: u64` | Any DAG mutation or DB state change |
| `ComponentFault` | `component: &str, severity: FaultSeverity` | Any `catch_unwind` caught panic |
| `MeshRoleChanged` | `new_role: MeshRole` | Mesh topology change |
| `EmdpExpiryWarning` | `minutes_remaining: u32` | T-10 min and T-2 min during EMDP TTL |
| `DeadManWarning` | `hours_remaining: u32` | T-12 h and T-1 h offline grace period |
| `TierChanged` | `new_tier: NetworkTier, reason: TierChangeReason` | ALPN tier change or AWDL loss |
| `DagMergeProgress` | `completed: u64, total: u64` | Every 200 ms when merge backlog > 500 events |
| `XpcHealthDegraded` | `crash_count: u32, window_secs: u32` | macOS XPC crash rate exceeds threshold |
| `MemoryPressureWarning` | `component: &str, allocated_mb: u32` | `MemoryArbiter` allocated > 80% ceiling |

**UICommand Catalog (UI → Core, complete):**

| Command | Payload Fields | Effect in Core |
| --- | --- | --- |
| `SendMessage` | `recipient_did: DeviceId, plaintext: Vec<u8>` | Encrypt and append to DAG |
| `ScrollViewport` | `top_message_id: Uuid, bottom_message_id: Uuid` | Return viewport snapshot |
| `RequestMeshActivation` | none | Activate BLE scanning via host adapter |
| `ReleaseBuffer` | `token: u64` | `ZeroizeOnDrop` when `ref_count == 0` |
| `CancelTask` | `message_id: Uuid` | Cancel in-flight FFI decrypt task |

**Dependencies:**

- REF: TERA-CORE §4.2 — `CoreSignal` and `UICommand` enum definitions, unidirectional contract
- REF: TERA-CORE §4.3 — FFI Token Protocol (`tera_buf_acquire` / `tera_buf_release`)
- REF: TERA-CORE §2.2 — Shared Rust Core principle, Data Plane throughput targets, SAB Tier Ladder

**Data Interaction:**

- Reads: `cold_state.db` for viewport snapshots.
- Buffer transfers: `DataPlane_Payload` via SAB / JSI pointer / Dart FFI.
- No writes: IPC bridge is read-only at the feature layer.

**Constraints:**

- No `Vec<u8>`, `*const u8`, or `*mut u8` returned from any `pub extern "C"` function. Enforced by CI Clippy lint. Lint failure is a **blocker — do not merge**.
- SAB Tier 1 requires `COOP+COEP` HTTP headers on Desktop. Auto-downgrade to Tier 2 on failure.
- UI never holds decrypted payloads beyond the render frame.
- `CoreSignal` emission is fire-and-forget. Core does not wait for UI acknowledgment.

**Failure Handling:**

- SAB unavailable (missing COOP headers): auto-downgrade to Named Pipe (~200 MB/s). Log tier change to audit trail.
- Named Pipe unavailable: downgrade to Protobuf-over-stdin (~50 MB/s). Log tier change.
- Token not found in Core on `ReleaseBuffer`: return `BufferNotFound` error; UI re-issues `ScrollViewport`.

---

### F-04: Local Storage Management

<!-- INSERTED PATCH: Two-Tier State Squashing & Stream-based Hydration -->
- 🗄️ Explicit protocol specification: The 7-day hot DAG structural eviction trigger is explicitly **suspended** when the `Mesh_Partition_Active` parameter returns `true`.
- 🗄️ Standard eviction clears ONLY trigger after the `tombstone.clock ≤ MVC` requirement fully satisfies constraints mapped across `TERA-CORE §17.1`.
- 🌐 Hydration capabilities route through variables mapping across `HydrationScheduler` load balancers.
- 🌐 Connected endpoints strictly implement mathematical exponential backoff procedures structured tightly via execution jitter limits initiating hydration slot calls.


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
   a. Create backup: `{db_path}.bak.v{current_version}`.
   b. `db.execute_batch("BEGIN EXCLUSIVE TRANSACTION")`.
   c. Run migration scripts in version order.
   d. `PRAGMA user_version = CURRENT_SCHEMA_VERSION`.
   e. `COMMIT`.
3. If `cold_state.db` migration fails: **drop file and rebuild from `hot_dag.db`**. Never abort without a recovery path.

**User Flow — Shadow Paging Hydration:**

1. Core receives `Snapshot_CAS` reference for a new snapshot.
2. Download snapshot in 2 MB chunks to `cold_state_shadow.db`.
3. Verify: `SHA-256(downloaded_content) == cas_uuid`. Reject and restart on mismatch.
4. On full verification: atomic `rename(cold_state_shadow.db → cold_state.db)`.
5. Emit `CoreSignal::StateChanged { table: "all", version }`.
6. If download interrupted mid-way: delete `cold_state_shadow.db`; `cold_state.db` unchanged. Resume from last `Hydration_Checkpoint`.

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
- `PRAGMA wal_autocheckpoint = 1000` enforced on all SQLite databases.
- `VACUUM INTO` guarantees zero downtime: creates clean copy, then atomic swap. Reads and writes are never blocked.
- BGTask execution is at iOS scheduler's discretion. Foreground opportunistic VACUUM is the primary reliability path.

**Failure Handling:**

- WAL bloat > 200 MB (mobile): emit `CoreSignal::MemoryPressureWarning`. UI displays banner: "Storage cache is full — TeraChat will clean up when charging."
- VACUUM fails: log error, retry on next trigger. Do not crash.
- Schema migration fails on `cold_state.db`: drop file, rebuild from `hot_dag.db`. Log `COLD_STATE_REBUILD`.
- Hydration interrupted: delete `cold_state_shadow.db`; restart from `Hydration_Checkpoint` in `hot_dag.db`.

---

### F-05: Survival Mesh Networking

**Description:** When Internet is unavailable, TeraChat activates a BLE 5.0 / Wi-Fi Direct peer-to-peer Mesh for offline text messaging via Store-and-Forward. WASM plugins, AI inference, voice calls, and file transfer (except P2P direct) are suspended.

**Supported Platforms:** 📱 iOS (Leaf/EMDP), 📱 Android (Relay), 📱 Huawei (Relay), 💻 macOS (Super Node), 🖥️ Windows (Super Node), 🖥️ Linux (Super Node)

**User Flow — Activation:**

1. Rust Core detects all three ALPN paths unavailable.
2. Core emits `CoreSignal::TierChanged { new_tier: MeshMode, reason: NoInternet }`.
3. UI transitions to Mesh Mode visual state.
4. User confirms Mesh activation (required: OS BLE permission prompt).
5. Core calls host adapter FFI: `request_mesh_activation()`. Swift/Kotlin starts BLE advertising and scanning.
6. Devices within range discover each other via BLE Stealth Beacons.
7. Text messages route via BLE Store-and-Forward (payload ≤ 4 KB per hop).
8. Files and media: P2P Wi-Fi Direct only, < 20 m range. UI shows "Send files only when nearby."

**Role Assignment (deterministic, no voting rounds):**

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

**Store-and-Forward Quotas:**

| Role | Storage Quota | Message TTL |
| --- | --- | --- |
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

**Mesh Mode feature restrictions (hard limits, enforced by Rust Core — not UI):**

| Feature | Mesh Mode Status |
| --- | --- |
| WASM `.tapp` execution | Terminate immediately; snapshot saved to sled |
| AI / SLM inference | Disabled; return `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` |
| Voice and video calls | Suspended (BLE cannot carry audio stream) |
| File transfer (multi-hop) | Suspended |
| File transfer (P2P Wi-Fi Direct, < 20 m) | Available |
| Inter-`.tapp` Delegation Tokens | Suspended |
| Transient state persistence | Disabled |
| MLS Epoch rotation | Suspended (EMDP mode) |
| DAG merge | Deferred to Desktop reconnect |

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

- iOS `election_weight = 0`. Hardcoded in `mesh/election.rs`. Never changed.
- BLE MTU: 512 bytes. PQ-KEM key exchange requires RaptorQ (RFC 6330) fragmentation.
- SOS messages: exempt from all PoW. Zero latency cost.
- Unsigned Shun Records: silently dropped (prevents false-flag Byzantine attacks).

**Failure Handling:**

- All-iOS Mesh, no EMDP conditions: Causal Freeze (read-only). No DAG writes until non-iOS node joins.
- iOS AWDL disabled (Hotspot/CarPlay): downgrade to BLE-only Tier 3; queue voice packets (TTL 90 s if CallKit session active; 30 s otherwise); emit `CoreSignal::TierChanged`.
- EMDP TTL expired, no hand-off found: enter SoloAppendOnly mode. Merge deferred to next Desktop/Android contact.
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

**iOS AWDL/Hotspot conflict during active call:**

1. `NWPathMonitor` detects tethering interface appearing (1–2 s window before AWDL drops).
2. Core emits `CoreSignal::TierChanged { reason: HotspotConflictImminent }`.
3. UI presents: "Enabling Hotspot will interrupt the Mesh call — continue?" (3 s auto-dismiss).
4. If user proceeds (or auto-dismiss): downgrade to BLE-only Tier 3; queue voice packets TTL 90 s.
5. After 90 s with no AWDL recovery: call drops. Notification: "Call ended — Hotspot is active."

**Mesh Mode behavior:** Voice calls are not available in Mesh Mode. BLE cannot carry an audio stream. UI displays: "Voice calls require an Internet connection."

**Dependencies:**

- REF: TERA-CORE §5.3 — SDP signaling over MLS E2EE channel
- REF: TERA-CORE §6.4 — iOS AWDL conflict, pre-emptive warning, CallKit exception
- REF: TERA-CORE §10.4 — TURN HA sizing (Keepalived Floating IP, 3 s failover), CallKit integration, Dual TURN Preconnect
- REF: TERA-CORE §9.2 — ALPN negotiation for TURN path selection

**Data Interaction:**

- Reads: `Epoch_Key` for SDP exchange encryption; ICE candidate pool from Core network state.
- Writes: none persistent (ephemeral ICE/DTLS state only; no DB writes during call).

**Constraints:**

- iOS: `CallKit` integration is mandatory. Without it, iOS kills network after 30 s background.
- TURN server: relays encrypted UDP only — holds no decryption keys.
- TURN node sizing: 1 node ~50 concurrent HD streams (4 vCPUs, 8 GB RAM, 1 Gbps NIC).

**Failure Handling:**

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

- Same test vector executed on `wasm3` (iOS reference runtime) and `wasmtime` (Desktop optimized runtime).
- Output: semantically identical. Latency delta: ≤ 20 ms acceptable.
- CI failure: block merge. **This gate is a blocker for Marketplace launch.**

**Mesh Mode behavior:**

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

**Transient State Storage (sled LSM-Tree):**

- Crate: `sled` ≥ 0.34 (pure Rust; no C FFI; ~2 MB compiled; < 2 MB RAM idle).
- Rationale for `sled` over RocksDB: RocksDB compiled size exceeds 50 MB WASM heap budget on mobile.
- API: `terachat.storage.persist_keyval(key, value)` → debounce 500 ms → AES-256-GCM encrypt → write.
- Recovery: `terachat.storage.get_transient_state()` → < 50 ms restore.
- Mesh Mode: disabled. RAM/CPU reserved for BLE routing.

**Dependencies:**

- REF: TERA-CORE §4.1 — `ffi/token_protocol.rs`, `ffi/ipc_bridge.rs`
- REF: TERA-CORE §4.4 — Component Fault Isolation, `catch_unwind` at WASM execution entry
- REF: TERA-CORE §3.2 — Platform WASM runtime selection matrix (Table §3.1)
- REF: TERA-CORE §4.3 — FFI Token Protocol; no raw pointer between Core and sandbox

**Data Interaction:**

- Reads (via Host Proxy only): approved `cold_state.db` namespaces; sanitized external API responses.
- Writes: `sled` LSM-Tree transient state (per-DID, AES-256-GCM). Forbidden: direct writes to `hot_dag.db` or `cold_state.db`.

**Constraints:**

- WASM heap: ≤ 50 MB mobile / ≤ 64 MB desktop. OOM kills sandbox only; Core is unaffected.
- CPU: ≤ 10% sustained. Spike allowed; not > 500 ms. Circuit Breaker: latency > 1,500 ms or CPU spike > 30% → SUSPEND.
- Rate limit: Token Bucket 50 req/s per `.tapp`. Continuous exhaustion → SUSPEND + 60 s cool-down.
- Egress: HTTPS, HTTP/2, Secure WebSocket to declared `egress_endpoints` only. Raw TCP/UDP: forbidden.
- iOS: no dynamic WASM loading. `wasm3` interpreter or AOT-compiled `.dylib` only.
- Huawei: AOT-compiled `.waot` bundles required for AppGallery. No dynamic download.

**Failure Handling:**

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

**Delegation Token structure:**

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

**Failure Handling:**

- Target `.tapp` suspended or terminated: queue payload. Deliver on `.tapp` resume.
- Token expired: return `ERR_DELEGATION_TOKEN_EXPIRED`; prompt user to re-authorize.
- OPA policy change revokes token mid-session: return `ERR_TOKEN_REVOKED`; prompt user.

---

### F-09: Media and File Transfer

**Description:** Send encrypted media files (images, video, documents) via chunked, content-addressable, deduplicated upload. Server stores only ciphertext keyed by `cas_hash`. Receiver downloads on demand via Zero-Byte Stub.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

**User Flow (send):**

1. User selects file in UI.
2. Core computes `cas_hash = BLAKE3(ciphertext)`. Checks if `cas_hash` exists on server (deduplication saves 40–60% storage for shared enterprise files).
3. If not exists: chunk file into 2 MB segments. AES-256-GCM encrypt each chunk with ephemeral `ChunkKey`. Nonce = `Base_Nonce XOR chunk_seq_number`. `ChunkKey` `ZeroizeOnDrop` after each chunk.
4. Upload chunks to MinIO Blind Storage at path `cas_hash`. Server never knows file name.
5. Core sends `CRDT_Event { content_type: MediaRef, payload: {file_name, cas_hash, encrypted_thumbnail, storage_ref} }` (< 5 KB stub).

**User Flow (receive):**

1. Receiver's UI renders Zero-Byte Stub immediately (BlurHash preview from encrypted thumbnail).
2. User taps to open file. Core downloads and decrypts chunks on demand.
3. Stream decryption: AES-256-GCM chunk by chunk. No full-file RAM buffer at any point.

**iOS background transfer:**

- Pre-signed URL (TTL 15 min, HMAC-SHA256 bound to device) delegated to `NSURLSession` Background Transfer Service.
- On download complete: iOS wakes app in 30 s window. Core `mmap`-reads and decrypts into VFS.
- `ShadowMigrationLock` prevents race with concurrent DB migration.

**Mesh Mode:** Multi-hop file transfer suspended. P2P Wi-Fi Direct (< 20 m) available for direct transfers. UI shows "Files can only be sent when devices are nearby."

**Dependencies:**

- REF: TERA-CORE §5.3 — `ChunkKey` lifecycle, AES-256-GCM chunk encryption, nonce uniqueness
- REF: TERA-CORE §9.5 — MinIO Blind Storage, CAS path (`cas_hash`), Zero-Byte Stub format
- REF: TERA-CORE §7.1 — `CRDT_Event` with `content_type: MediaRef`
- REF: TERA-CORE §8.1 — Outbound message flow (media stub is a CRDT_Event)

**Data Interaction:**

- Writes: encrypted chunks to MinIO; `CRDT_Event` stub to `hot_dag.db`.
- Reads: `cas_hash` dedup lookup; encrypted chunks on demand; `ChunkKey` ephemeral in RAM.

**Constraints:**

- Maximum single file: 10 GB (chunked streaming; no full-file in RAM at any point).
- `ChunkKey` must `ZeroizeOnDrop` immediately after each chunk is processed.
- Deduplication uses Salted MLE: `BLAKE3(ciphertext + Channel_Key)`. Server learns nothing from dedup.

**Failure Handling:**

- Upload interrupted: resume from last successfully uploaded chunk (last `Hydration_Checkpoint` in `hot_dag.db`).
- Decryption failure on receive: display "File could not be decrypted" and log error to TeraDiag.
- MinIO node failure: EC+4 auto-recovers. Single-node loss does not affect availability.

---

### F-10: AI / SLM Integration

<!-- INSERTED PATCH: Edge ONNX Embedding Engine & Model Integrity Protocol -->
- ⚙️ ONNX operational execution heavily relies on the architectural limits set functionally inside `PLATFORM-18`.
- ⚙️ Initial model allocation parsing mandatorily executes through `OnnxModelLoader.load_verified()` pipeline wrappers to ensure BLAKE3 + Ed25519 signature integrity.
> **Mandatory Model Integrity Rules:**
1. ⚙️ Signature verification structurally relies precisely against specific endpoints maintaining `Ed25519` values routed perfectly inside the central TeraChat Model Signing Root nodes checking isolated `model_name.sig` blocks.
2. ⚙️ BLAKE3 hashing specifications require internal compilation hard-coding paths executing cleanly directly bounded inside `build.rs` targets locking binary bounds preventing network lookup risks natively.
3. ⚙️ Linear sequence execution locks strict bounds dropping precisely scaling: BLAKE3 hash execution validation → Ed25519 signature constraint bounds → active ONNX session loading calls. Error mapping enforces functional quarantine limits backing down dynamically to keyword mapping.
4. ⚙️ Host retrieval pipelines exclusively demand natively enforced DoH (DNS-over-HTTPS) bounds bundled inside TLS wrappers utilizing mapped SPKI pinning parameters natively bouncing standard DNS limits rejecting open DNS queries directly.


**Description:** Local Small Language Model (SLM) inference and cloud LLM routing for `.tapp` plugins. PII is redacted before any data leaves the device. Inference is isolated in a separate process (crash-safe from Rust Core).

**Supported Platforms:** 📱 iOS (CoreML), 📱 Android (ONNX), 📱 Huawei (HiAI), 💻 macOS (ONNX/CoreML), 🖥️ Windows (ONNX), 🖥️ Linux (ONNX)

**Mesh Mode behavior:** AI fully disabled. Return `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` for all inference requests.

**Memory budget enforcement:**

- ONNX/CoreML allocator: 8 MB hard ceiling (custom allocator returns `AllocError` on overflow → graceful fallback to Flat-search).
- Runtime monitor: `tikv-jemallocator` `malloc_stats_print` polls heap every 5 s. If heap > 6 MB: reduce batch size 32 → 8 vectors/batch.

**Whisper model tier selection:**

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

**AI Quota enforcement:**

- Per-`.tapp`: 10,000 tokens/hour.
- Overage: return `ERR_AI_QUOTA_EXCEEDED`. UI presents upgrade prompt.
- Enterprise plan (License JWT `features` field): unlimited.

**KV-Cache management:**

- Mobile: 1 KV-Cache slot active at a time. Inactive slots: LZ4-compressed to storage.
- Desktop: multiple KV-Cache slots in Hot RAM simultaneously.

**iOS CoreML parity path (W^X constraint):**

- iOS cannot load dynamic WASM AI modules (App Store Rule 2.5.2).
- AI features shipped as `.mlmodelc` CoreML bundles inside the app binary.
- Marketplace "install": OPA Policy JSON pushed to unlock the pre-bundled CoreML module.
- Unlock latency: < 1 s. User experience identical to Android/Desktop.

**Prompt Injection Defense:**

- Rust Core wraps LLM response in `Vec<ASTNode>` (AST Sanitizer). Raw HTML, inline Markdown with external image tracking URLs, and executable content are rejected.
- On 3rd `TAINTED` flag within a session: suspend the offending `.tapp` and emit `CoreSignal::ComponentFault`.

**Dependencies:**

- REF: TERA-CORE §3.3 — `MemoryArbiter`, RAM budget matrix, Whisper tier protocol
- REF: TERA-CORE §3.6 — AI infrastructure, Micro-NER, `SessionVault` `ZeroizeOnDrop`
- REF: TERA-CORE §4.4 — `catch_unwind` boundary at AI worker entry; crash isolation from Core

**Data Interaction:**

- Reads: user message context (local, not uploaded to server); LLM API response.
- Writes: inference result to `.tapp` via sanitized `Vec<ASTNode>`; alias map in `SessionVault` (RAM, `ZeroizeOnDrop`).

**Failure Handling:**

- ONNX allocator OOM: graceful fallback to Flat-search (no NLP). Log `ONNX_OOM_FALLBACK`.
- LLM cloud unreachable: return `ERR_AI_CLOUD_UNAVAILABLE`. Surface local-only fallback if available.
- AST Sanitizer rejects response (malformed / injection detected): return `ERR_AI_RESPONSE_TAINTED`. `.tapp` suspended after 3rd violation in session.

---

### F-11: Device Security

**Description:** Client-side security controls: screen capture prevention, Protected Clipboard Bridge, biometric screen lock, Remote Wipe, and cryptographic self-destruct.

**Supported Platforms:** 📱 iOS, 📱 Android, 📱 Huawei, 💻 macOS, 🖥️ Windows, 🖥️ Linux

#### F-11a: Screen Capture Prevention

| Platform | API | Mechanism |
| --- | --- | --- |
| 📱 iOS | `UIScreen.capturedDidChangeNotification` | On `isCaptured == true`: apply `UIBlurEffect(.dark)` over all content |
| 📱 Android | `WindowManager.LayoutParams.FLAG_SECURE` in `Activity.onCreate()` | Kernel-level Compositor blocks all capture; returns black frame |
| 📱 Huawei | HarmonyOS `WindowManager` secure flag | Same mechanism as Android |
| 💻 macOS | `CGDisplayStream` monitoring | On capture detected: blur overlay applied within 1 frame (< 16 ms) |
| 🖥️ Windows | DXGI duplication detection | On capture detected: blur overlay |
| 🖥️ Linux | Wayland compositor security hint | Platform best-effort; log `LINUX_SCREEN_CAPTURE_UNSUPPORTED` if not available |

#### F-11b: Protected Clipboard Bridge

All clipboard operations route through Rust Core's bridge. Direct OS clipboard API calls from Core: **blocker**.

| Platform | Backend | Detection Mechanism |
| --- | --- | --- |
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
- Clipboard bridge is mandatory for all platforms. Direct OS clipboard calls from Core: **blocker**.

**Failure Handling:**

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

**Failure Handling:**

- Enrollment token expired (> 12–24 h): Admin generates new token.
- Recovery Ticket signature invalid: reject; log `INVALID_RECOVERY_TICKET` to Audit Log.
- BIP-39 phrase incorrect: return `ERR_MNEMONIC_INVALID`. No attempt count limit (brute force protected by mandatory biometric gate).

---

### F-13: Admin Console and Enterprise Controls

<!-- INSERTED PATCH: Client-Side Observability Integration -->
### Client-Side Observability Integration
- 📱 **OTEL Push (khi online):** Core logic exports mapped metrics strictly functioning out over OTLP HTTP POST payload limits routing to VPS operational endpoints strictly within 60s intervals. Data parsing exclusively utilizes the `TeraDiagMetrics` protobuf schema.
- 📱 **Offline Buffer:** Metrics load and cache directly into local variables mapping inside isolation wrappers marked fully as `metrics_buffer.db` bounded strictly at 24 hours. Connective limits flush buffers dynamically tracking immediate network reconnections.
- 📱 **Battery-Aware Export:** Detection constraints drop metric transmission intervals structurally back over 300s when power levels detect constraints < 20%. Suspensions drop cleanly at ≤ 10%.
- 💻🖥️ **Prometheus Node Exporter:** Standard node routing parses direct exposure inside the local `/metrics` host parameter set cleanly limiting access exclusively bounded to `localhost:9092`.
- 💻🖥️ **OTLP Push Fallback:** Alternate bounds revert exactly parsing metrics to the native VPS OTEL Collector pipelines mapped standard from internal Mobile specifications.
- 📱💻 **GC Release Warning:** Warning metrics trigger functionally mapping when automated GC boundaries execute a garbage cache reduction over `TeraSecureBuffer` parameter instances sidestepping typical `releaseNow()` explicit paths.


**Description:** Centralized management interface for workspace administrators: policy, device management, user offboarding, audit, and license management.

**Supported Platforms (full access):** 💻 macOS, 🖥️ Windows, 🖥️ Linux, 🗄️ Bare-metal
**Supported Platforms (read-only):** 📱 iOS, 📱 Android, 📱 Huawei

**Admin Console Feature Set:**

| Feature | Description | Access Level |
| --- | --- | --- |
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

**Security hardening:**

- QUIC-Pinning State Machine blocks protocol downgrade attacks (QUIC → WSS).
- Socket Panic Circuit Breaker: on detected downgrade manipulation, refuse new TCP/UDP connections for 30 s.

**Dependencies:**

- REF: TERA-CORE §9.2 — ALPN negotiation protocol, Strict Compliance Mode, Adaptive Probe Learning
- REF: TERA-CORE §4.2 — `CoreSignal::TierChanged`, `NetworkTier` enum

**Data Interaction:**

- Reads/Writes: `NetworkProfile` in SQLite local config DB (per network identifier).

**Constraints:**

- ALPN selection is automatic. Admin can override to Strict Compliance Mode only — no other configuration.
- Adaptive learning resets on network change (different mTLS cert fingerprint).

**Failure Handling:**

- All three ALPN steps fail: activate Mesh Mode. Emit `CoreSignal::TierChanged { new_tier: MeshMode }`.
- Adaptive auto-switch false positive: Admin can reset in Settings. Network change also auto-resets.

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

**Memory pressure response (iOS/Android):**

1. Receive OS memory warning callback.
2. Rust Core immediately: zeroize all vector caches; pause ONNX pipeline.
3. Priority preserved: `hot_dag.db` and active chat session.
4. Emit `CoreSignal::ComponentFault { component: "onnx", severity: Warning }`.

**Desktop WAL checkpoint on shutdown:**

- `terachat-daemon` registers SIGTERM handler.
- On SIGTERM: `PRAGMA wal_checkpoint(TRUNCATE)` with 30 s timeout.
- Exit unconditionally after 30 s regardless of checkpoint result.
- systemd `TimeoutStopSec = 35`.

**Linux multi-init daemon support (postinstall script):**

```bash
#!/bin/bash
# postinstall script (included in .deb and .rpm packages)
if command -v systemctl &>/dev/null && systemctl --version &>/dev/null 2>&1; then
    systemctl enable --now terachat-daemon.service
elif command -v rc-service &>/dev/null; then
    rc-update add terachat-daemon default && rc-service terachat-daemon start
elif command -v runit &>/dev/null; then
    ln -sf /etc/sv/terachat-daemon /var/service/
else
    # XDG autostart fallback for non-standard init
    install -m644 /usr/share/applications/terachat-daemon.desktop \
        ~/.config/autostart/terachat-daemon.desktop
fi
# terachat-daemon writes PID file → any init system can monitor via PID
```

**AppArmor / SELinux MAC profile auto-load (postinstall):**

```bash
# Detect and load MAC profile before first launch
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

**Failure Handling:**

- WAL checkpoint timeout (Desktop): exit regardless. `systemd Restart=on-failure` handles restart. `wal_staging.db` replay covers in-flight events on next start.
- OOM kill before WAL flush (iOS/Android): SQLite WAL is crash-safe by design. WAL replays automatically on next open. No data loss.
- AppArmor/SELinux postinstall script fails: log to `/var/log/terachat-install.log`; print warning on console; do not abort installation. Alert: "Manual MAC profile load required. See /var/log/terachat-install.log."

---



### INFRA-01: [ARCHITECTURE] Client Compute Distribution

> **Nguyên tắc:** Mobile devices không phải là compute nodes.
> Desktop devices là compute cluster. VPS là blind router.
> Computation đi đến nơi có resource — không phải nơi thuận tiện architecturally.

#### INFRA-01.1 Mobile Compute Constraints (Hard Rules)

Các operation sau TUYỆT ĐỐI KHÔNG chạy trên Mobile (📱):

| Operation | Lý do cấm | Alternative |
|---|---|---|
| ONNX 80MB model inference | Thermal spike +4°C, 15% battery/op | Desktop offload |
| DAG merge > 3000 events | ANR risk > 5s | Snapshot sync |
| FTS5 full-history index | Storage > 300MB | Desktop-hosted search |
| CRDT full-state storage | hot_dag.db > 300MB | Delta-only + snapshot |
| BLAKE3 full-file hash (>100MB) | CPU spike blocks UI | Desktop computation |

#### INFRA-01.2 ONNX Inference Offload Protocol

📱 Mobile phát `OnnxOffloadRequest` (E2EE) đến Desktop Super Node:

### INFRA-02: [IMPLEMENTATION] Blob Storage Client

> TeraChat clients interact with blob storage ONLY via TeraRelay's presigned URL mechanism.
> Clients NEVER have direct credentials to R2/B2/MinIO.
> This maintains Zero-Knowledge: relay signs URLs without seeing content.

#### INFRA-02.1 File Upload Flow (Revised)

### INFRA-03: [IMPLEMENTATION] TeraRelay Health & Self-Healing

> Single-binary deployment means no cluster coordination.
> Self-healing must happen within the binary itself.

#### INFRA-03.1 In-Process Watchdog

### PLATFORM-19: One-Touch Relay Deployment

#### PLATFORM-19.1 Deployment Requirements (Revised)

| Tier | VPS Spec | Monthly Cost | Admin Skill Required | Setup Time |
|---|---|---|---|---|
| Solo (≤50 users) | 1 vCPU, 512MB RAM, 20GB SSD | $6 + $1 storage | None | 5 min |
| SME (≤500 users) | 2 vCPU, 2GB RAM, 40GB SSD | $12 + $5 storage | None | 10 min |
| Enterprise (≤5000 users) | 4 vCPU, 8GB RAM, 100GB SSD | $28 + $20 storage | Basic | 20 min |
| Gov (air-gapped, any size) | Existing hardware | CAPEX only | IT Admin | 1 hour |

#### PLATFORM-19.2 `tera-relay` CLI Commands

### OBSERVE-01: [IMPLEMENTATION] Client-Side Observability

> Clients không expose Prometheus scrape endpoint.
> Thay vào đó: push aggregate metrics qua OTLP HTTP khi online,
> buffer locally khi offline.

---

#### OBSERVE-01.1 [IMPLEMENTATION] Mobile Metrics Push

📱 **OTLP Push khi online:**

### OBSERVE-02: [IMPLEMENTATION] DAG Merge Progress UI

> Khi merge > 500 events, user PHẢI thấy progress — không black screen.

---

#### OBSERVE-02.1 [IMPLEMENTATION] IPC Signal Spec

### PLATFORM-17: [IMPLEMENTATION] Dart FFI Memory Contract

> **Supersedes PLATFORM-14.** Đây là contract bắt buộc — vi phạm = CI fail.

---

#### PLATFORM-17.1 Quy tắc bắt buộc

**Rule 1:** Mọi `TeraSecureBuffer` PHẢI được wrap bởi `useInTransaction()`.
Direct `.toPointer()` bên ngoài wrapper → CI lint error.

**Rule 2:** Rust Token Registry KHÔNG tự expire/zeroize token.
Khi timeout → Rust emit `IpcSignal::TransactionTimeout`.
UI hiển thị: *"Phiên xử lý đã hết hạn — vui lòng thực hiện lại."*

**Rule 3:** GC Finalizer chỉ là safety net.
GC release → WARNING metric + log. Không silent.

**Rule 4:** Explicit `releaseNow()` là primary release path.
`useInTransaction()` gọi `releaseNow()` trong `finally` block tự động.

---

#### PLATFORM-17.2 Implementation

### PLATFORM-18: [SECURITY] [IMPLEMENTATION] ONNX Model Integrity

> **Áp dụng cho:** §5.27 Edge ONNX, §8.19 EICB, §5.33 EDES, §9.3 Dual-Mask.
> Mọi ONNX model load PHẢI qua `OnnxModelLoader.load_verified()`.

---

#### PLATFORM-18.1 Verification Flow

### PLATFORM-19: [IMPLEMENTATION] TeraEdge Client Integration

> Mobile tự động detect TeraEdge trên LAN và ưu tiên dùng
> thay vì ONNX inference local hoặc VPS relay.

---

#### PLATFORM-19.1 Super Node Discovery Priority

📱 Khi Mobile cần ONNX inference, thứ tự ưu tiên:

### INFRA-04: [IMPLEMENTATION] Canary Deployment Strategy

> **Bài toán:** Không có staged rollout = bad release ảnh hưởng 100% customers.
> Giải pháp: DNS-based traffic splitting + feature flag per-tenant.

---

#### INFRA-04.1 Traffic Splitting via DNS

### INFRA-05: [IMPLEMENTATION] SBOM & Reproducible Builds

> Enterprise/Gov customers yêu cầu SBOM cho compliance audit.
> Reproducible builds cần thiết cho binary transparency claims.

---

#### INFRA-05.1 SBOM Generation

### CICD-01: [IMPLEMENTATION] CI/CD Pipeline Requirements

> Danh sách gates bắt buộc — tất cả phải pass trước khi merge vào main.

---

#### CICD-01.1 Required Gates

### INFRA-06: [TEST] [IMPLEMENTATION] Automated Chaos Engineering

> TestMatrix.md định nghĩa 28 scenarios. File này spec implementation.
> Mục tiêu: automated CI test suite, không chỉ manual runbook.

---

#### INFRA-06.1 Chaos Test Framework

## 5. FEATURE ↔ CORE MAPPING (CRITICAL)

> Every feature maps to one or more modules in Core_Spec.md.
> A feature with no Core mapping is an **orphan — blocker, do not ship**.
> Mappings verified against TERA-CORE v2.0.

| Feature ID | Feature Name | Primary Core Modules | TERA-CORE References |
| --- | --- | --- | --- |
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

**Orphan Feature Verification:** All 15 features have verified Core mappings. Zero orphan features in this document.

---

## 6. USER FLOW & INTERACTION MODEL

### 6.1 Message Send → Render Lifecycle

```text
[User input]
     │  UICommand::SendMessage { recipient_did, plaintext }
     ▼
[Rust Core]
  1. Lookup Epoch_Key (RAM, ZeroizeOnDrop)
  2. AES-256-GCM encrypt plaintext
  3. Build CRDT_Event with Ed25519 signature (biometric gate)
  4. Append to hot_dag.db WAL (durable before network dispatch)
     │
     ├── Online: TLS 1.3 + mTLS → VPS → wal_staging → pub/sub
     └── Offline: BLE Control Plane → Mesh Store-and-Forward
     │
  5. Emit CoreSignal::StateChanged { table: "messages", version }
     ▼
[UI]
  1. Issue UICommand::ScrollViewport
  2. Core: tera_buf_acquire → Data Plane buffer write
  3. UI reads via token → renders 20 messages
  4. UICommand::ReleaseBuffer → Core ZeroizeOnDrop
```

### 6.2 Network Mode Transition

```text
Internet available
  ├── QUIC OK  → ONLINE_QUIC
  ├── gRPC OK  → ONLINE_GRPC
  ├── WSS OK   → ONLINE_WSS
  └── All fail → MESH_MODE
                   │
                   ├── BLE + Wi-Fi Direct active
                   ├── F-07 WASM: terminate + sled snapshot
                   ├── F-10 AI: disabled
                   └── F-06 Voice: suspended

Internet restored
  │
  ├── ALPN renegotiation → highest available tier
  ├── F-07 WASM: restore from sled snapshot (< 50 ms)
  ├── F-05 DAG sync: CRDT merge via Dictator Election
  └── F-01 MLS: Peer-Assisted Epoch Re-induction if needed
```

### 6.3 Device Enrollment Flow

```text
Admin generates enrollment token (mTLS cert, TTL 12–24 h)
  │
  ▼
New device scans QR / enters token
  │
  ▼
DeviceIdentityKey generated in Secure Enclave / StrongBox (biometric required)
  │
  ▼
Proof_of_Identity_and_Device submitted → server → mTLS cert issued
  │
  ▼
MLS Welcome_Packet received → Company_Key available
  │
  ▼
Device operational
cold_state.db hydration begins in background (F-04 Hydration flow)
```

### 6.4 iOS Push Notification Flow (Versioned Key Ladder)

```text
APNs delivers push payload
  │
  ├── Version match → NSE Arena decrypt → OS notification → ZeroizeOnDrop
  │
  └── Version mismatch
        │
        ├── Cache ciphertext to nse_staging.db
        ├── Set main_app_decrypt_needed = true (Shared Keychain)
        └── Send content-available:1
              │
              ▼
            Main App wakes
              │
              ├── Rotate Push_Key
              ├── Decrypt nse_staging.db entry
              ├── Display notification
              └── Clear nse_staging.db
```

---

## 7. DATA CONTRACTS (HIGH-LEVEL)

> This section defines what data flows between feature modules and Rust Core.
> Detailed cryptographic schemas reside in TERA-CORE §0 (Data Object Catalog).
> This section governs the feature-layer interface only.

### 7.1 Message Data Contract

| Direction | Object | Format | Max Size | Encryption |
| --- | --- | --- | --- | --- |
| UI → Core (send) | `UICommand::SendMessage.plaintext` | Raw bytes | 4,096 B (before padding) | None (Core encrypts) |
| Core → UI (render) | Viewport snapshot | `Vec<CrdtEvent>` decrypted | 20 msgs × ~2 KB | `ZeroizeOnDrop` after render |
| Core → Server | `CRDT_Event.payload` | AES-256-GCM ciphertext | Variable | E2EE (server-blind) |

### 7.2 Media Data Contract

| Direction | Object | Format | Max Size | Encryption |
| --- | --- | --- | --- | --- |
| UI → Core (send) | Raw file bytes | Stream | 10 GB | None (Core encrypts in 2 MB chunks) |
| Core → Server | Encrypted chunks | AES-256-GCM | 2 MB each | E2EE (server-blind) |
| Core → UI (stub) | Zero-Byte Stub | `{name, cas_hash, thumbnail, ref}` | < 5 KB | E2EE |
| Core → UI (download) | Decrypted chunk | Raw bytes | 2 MB per chunk | `ZeroizeOnDrop` per chunk |

### 7.3 WASM Plugin Data Contract

| Direction | Object | Format | Encryption |
| --- | --- | --- | --- |
| `.tapp` → Core (outbound) | `EgressNetworkRequest` | Protobuf | TLS 1.3 enforced by Core |
| Core → `.tapp` (response) | Sanitized response | `Vec<ASTNode>` | None (sanitized by Core before delivery) |
| `.tapp` → Core (state write) | `persist_keyval(key, value)` | Raw bytes | AES-256-GCM by Core |
| Core → `.tapp` (state restore) | `get_transient_state()` | Raw bytes | Decrypted by Core; `ZeroizeOnDrop` after delivery |

### 7.4 Push Notification Contract

| Direction | Object | iOS | Android | Size Limit |
| --- | --- | --- | --- | --- |
| Server → Device | Encrypted payload | APNs `mutable-content: 1` | FCM Data Message | < 4 KB for NSE inline decrypt |
| Core → OS | Notification content | `UNNotificationContent` | `RemoteMessage` | OS-enforced |

### 7.5 IPC Buffer Contract

| Primitive | Direction | Token Lifecycle | Cleanup |
| --- | --- | --- | --- |
| `tera_buf_acquire(op_id) → u64` | Core → UI | Opens on acquire | — |
| `tera_buf_release(token)` | UI → Core | Closes on release | `ZeroizeOnDrop` when `ref_count == 0` |
| Buffer valid window | — | Between acquire and release | Never held across UI render frames |

---

## 8. CONSTRAINTS & LIMITATIONS

### 8.1 Platform Hard Constraints

| Constraint | Platform | Feature Impact |
| --- | --- | --- |
| W^X: no JIT WASM in App Sandbox | 📱 iOS | F-07: `wasm3` interpreter only |
| NSE RAM ≤ 20 MB (OS-enforced) | 📱 iOS | F-02: Ghost Push pattern mandatory |
| Background network 30 s | 📱 iOS | F-06: CallKit integration mandatory |
| `mlock()` rejected | 📱 iOS | F-11: Double-Buffer Zeroize required |
| AWDL + Hotspot mutually exclusive | 📱 iOS | F-05/F-06: BLE fallback on Hotspot |
| FCM 10/hr throttle (Android 14+) | 📱 Android | F-02: CDM registration + FCM high-priority |
| StrongBox not universal | 📱 Android | F-11/F-12: TEE-backed AndroidKeyStore fallback |
| HMS: no content-available push | 📱 Huawei | F-02: 4 h CRL delay; polling fallback; SLA disclosure |
| XPC Worker OOM crash atomicity | 💻 macOS | F-07: XpcTransactionJournal required |
| Flatpak incompatible | 🖥️ Linux | F-07: .deb/.rpm or AppImage only |
| AppArmor/SELinux startup crash | 🖥️ Linux | F-15: postinstall MAC profile load mandatory |
| ARM64 SAB behavior (Windows) | 🖥️ Win ARM64 | F-03: pre-release SAB validation required |
| No kernel modules / no eBPF client | ☁️ VPS | F-14: Tokio Token Bucket rate limiting (userspace) |

### 8.2 Mesh Mode Feature Restrictions (Exhaustive List)

The following are disabled in Mesh Mode. Enforcement is in Rust Core — not in UI:

| Feature | Status | Error Code |
| --- | --- | --- |
| WASM `.tapp` execution | Terminate + snapshot | N/A |
| AI / SLM inference | Disabled | `ERR_SURVIVAL_MODE_ACTIVE_AI_DISABLED` |
| Voice and video calls | Suspended | N/A |
| Multi-hop file transfer | Suspended | N/A |
| Inter-`.tapp` Delegation Tokens | Suspended | `ERR_MESH_MODE_DELEGATION_SUSPENDED` |
| Transient state persistence | Disabled | N/A |
| MLS Epoch rotation | Suspended (EMDP) | N/A |
| DAG merge | Deferred to Desktop reconnect | N/A |

### 8.3 Known Implementation Gaps (Open Items)

Engineers must resolve all Blocker items before production ship:

| Item | Severity | Reference | Status |
| --- | --- | --- | --- |
| WasmParity CI gate (wasm3 vs wasmtime semantic identity, ≤ 20 ms delta) | Blocker | F-07, TERA-CORE §11.4 | Not implemented |
| CI/CD code signing pipeline (all 5 platforms) | Blocker | `ops/signing-pipeline.md` | Not implemented |
| Dart FFI NativeFinalizer Clippy lint (FFI-01 enforcement) | Blocker | F-03, TERA-CORE §4.3 | Not implemented |
| AppArmor/SELinux postinstall script for Linux | High | F-15 | Not implemented |
| `sled` crate version pinned in `Cargo.toml` | Medium | F-07 Transient State | Not pinned |
| Border Node auto-detection heuristics (algorithm spec) | Medium | F-05 | Algorithm undefined |
| Windows ARM64 SAB behavior validation (WebView2) | Medium | F-03 | Not tested |

---

## 9. ANTI-TECHNICAL-DEBT RULES

### 9.1 Feature Responsibility Boundaries

- **ATD-01:** No feature implements logic that belongs to another feature. F-02 (Push) reads keys managed by F-01 (Messaging) via TERA-CORE §5.5. F-02 does not implement key rotation logic.
- **ATD-02:** No feature accesses `hot_dag.db` or `cold_state.db` directly from the UI layer. All DB access routes through Rust Core module interfaces.
- **ATD-03:** No feature implements cryptographic operations. All crypto routes through `crypto/` modules in TERA-CORE.
- **ATD-04:** Platform-specific code lives exclusively in host adapter layers (Swift/Kotlin) or in Rust `#[cfg(target_os = "...")]` blocks. Mixed-platform logic in shared modules: **blocker**.

### 9.2 Anti-Coupling Rules

- **ATD-05:** Features communicate through typed `CoreSignal` and `UICommand` enums. Ad-hoc FFI calls between feature modules: **blocker**.
- **ATD-06:** WASM plugins have zero knowledge of MLS key material. They receive only sanitized `Vec<ASTNode>` response objects. Any code path that exposes key material to WASM: **blocker**.
- **ATD-07:** The IPC bridge (F-03) has no semantic knowledge of message content. It transfers opaque bytes. Content interpretation is the UI layer's responsibility.
- **ATD-08:** `DelegationToken` (F-08) does not grant `.tapp` access to raw `cold_state.db`. It grants access to a defined OPA-enforced namespace only.

### 9.3 Scalability Rules

- **ATD-09:** No feature hardcodes platform count or MLS group size. These parameters come from TERA-CORE §10.3 Scaling Ceilings.
- **ATD-10:** Every feature that persists data specifies a cleanup/expiry path. No indefinite accumulation of stale data is acceptable.
- **ATD-11:** Features with battery impact must implement a power budget. F-05 BLE duty cycle, F-10 Whisper tier selection, F-15 BGTask constraints are the reference implementations.

### 9.4 Testability Rules

- **ATD-12:** Every feature's Failure Handling clause must correspond to a test case in TERA-TEST. Untested failure paths are not accepted for production.
- **ATD-13:** Features with platform-specific behavior must have test coverage on each variant. Parity gaps are tracked in §8.3.
- **ATD-14:** WasmParity CI gate (§8.3) must pass for every `.tapp` before Marketplace listing. Semantic divergence between `wasm3` and `wasmtime` is a **blocker for Marketplace launch**.

---

## 10. IMPLEMENTATION CONTRACT

> **Read §0 (Data Object Catalog) before implementing any feature.**
> Violating any rule below is a **BLOCKER — do not merge.**

### §10.1 Security Rules

- [x] **SEC-01** — No plaintext UI buffer outlives the render frame. `ZeroizeOnDrop` on every struct holding decrypted content. Verified with `cargo miri test`. CI failure: blocker.

- [x] **SEC-02** — No `Vec<u8>`, `*const u8`, or `*mut u8` returned from any `pub extern "C"` function. Token protocol mandatory. CI Clippy lint enforced. Lint failure: blocker.

- [x] **SEC-03** — All clipboard operations route through Protected Clipboard Bridge (F-11b). Direct OS clipboard API calls from Rust Core: **blocker**.

- [x] **SEC-04** — WASM sandbox: `PROT_READ`-only access to DAG shared memory. Write attempts outside sandbox boundary trigger `SIGSEGV` caught by `catch_unwind`. No exceptions.

- [x] **SEC-05** — iOS Keychain access groups: `push_key` accessible by NSE only (`group.com.terachat.nse`); `device_identity_key` by Main App only (`group.com.terachat.main`); `share_extension_token` by Share Extension only (`group.com.terachat.share`). Cross-group reads: **blocker**.

### §10.2 Platform Rules

- [x] **PLT-01** — iOS: `wasm3` interpreter only in App Sandbox. `wasmtime` permitted in XPC Worker (`allow-jit` entitlement) only. No JIT in Main App: **blocker**.

- [x] **PLT-02** — iOS NSE: Static Memory Arena 10 MB. Circuit Breaker terminates NSE gracefully on 20 MB breach. Never crash without cleanup.

- [x] **PLT-03** — iOS: Voice calls require `CallKit` integration. Without it, network killed after 30 s background. Non-CallKit voice on iOS: **blocker**.

- [x] **PLT-04** — Linux: Flatpak packaging is prohibited (bubblewrap/seccomp conflict). `.deb`/`.rpm` or AppImage + Cosign only.

- [x] **PLT-05** — Linux clipboard: detect display server at runtime (`WAYLAND_DISPLAY`). Wayland: `wl-clipboard`. X11: `xclip`/`xsel`. Hardcoded single backend: **blocker**.

- [x] **PLT-06** — Android 14+: FCM `priority = "high"` AND Companion Device Manager `REQUEST_COMPANION_RUN_IN_BACKGROUND`. Both are required. Either alone is insufficient.

- [x] **PLT-07** — Huawei: no dynamic WASM from Marketplace. AOT `.waot` bundles only. CRL delay ≤ 4 h must be documented in enterprise SLA.

### §10.3 Feature Integrity Rules

- [x] **FI-01** — Every feature maps to at least one TERA-CORE module (§5 mapping table verified). Orphan features: **blocker**.

- [x] **FI-02** — Mesh Mode restrictions (§8.2) are enforced in Rust Core. UI cannot re-enable restricted features by bypassing Core. UI-side Mesh override: **blocker**.

- [x] **FI-03** — WasmParity CI gate must pass before any `.tapp` is listed on Marketplace. Gate failure: **blocker for Marketplace launch**.

- [x] **FI-04** — `sled` crate is the mandated LSM-Tree for WASM transient state (F-07). RocksDB on mobile exceeds 50 MB heap budget. Switching without budget validation: **blocker**.

- [x] **FI-05** — iOS `election_weight = 0` is hardcoded in `mesh/election.rs`. Any PR modifying this constant: **blocker**.

### §10.4 IPC Rules

- [x] **IPC-01** — State flow unidirectional: Core → UI. UI sends Commands only. Bidirectional state channel: **blocker**.

- [x] **IPC-02** — SAB Tier Ladder selection (Tier 1/2/3) logged to audit trail. Silent tier selection: **blocker**.

- [x] **IPC-03** — `CoreSignal::DagMergeProgress` emitted every 200 ms when merge backlog > 500 events. Required for mobile ANR prevention.

---

## 11. ARCHITECTURE TRADE-OFFS

### What We Gain
| Benefit | Quantified Impact |
|---|---|
| Infrastructure cost | $240/month → $7-48/month (80-97% reduction) |
| Setup time | 1-2 days → 5-20 minutes |
| Mobile thermal | -4°C average (ONNX offloaded) |
| Mobile battery | -35% drain (ONNX + reduced DAG sync) |
| Mobile storage | 300MB → 25MB (hot_dag.db) |
| Deployment failures | Reduced 90% (single binary vs. 5-node coordination) |
| Upgrade fear | Eliminated (zero-downtime single binary upgrade) |
| Admin skill required | DevOps → None (non-technical admin can operate) |

### What We Accept (Residual Risks)

| Risk | Severity | Mitigation |
|---|---|---|
| Desktop must be online for ONNX offload | Medium | TinyBERT local fallback always available |
| Single relay VPS = single point of failure | Medium | Health monitoring + 5-min restart via systemd + DNS failover |
| Managed R2/B2 = external dependency | Low | Provider stores only ciphertext → Zero-Knowledge preserved |
| No PostgreSQL = no complex queries | Low | Relay only needs routing table — SQLite su
fficient |
| Desktop snapshot = delayed consistency | Low | 500-event or 24h interval — acceptable for enterprise |

### What Does NOT Change
- Zero-Knowledge security model: intact
- E2EE with MLS: intact
- Survival Mesh (BLE/Wi-Fi Direct): intact
- Air-gapped deployment option: intact (Gov/Military tier)
- Shamir Secret Sharing / KMS Bootstrap: intact
- All cryptographic guarantees: intact

## 12. CHANGELOG

| Version | Date | Summary |
| --- | --- | --- |
| 0.2.6 | 2026-03-19 | Add OBSERVE-01/02 client observability; PLATFORM-17/18/19/20;
|         |            | INFRA-01/02/03/04/05/06; CICD-01/02; Update PLATFORM-14→17 |
| 0.2.3 | 2026-03-18 | Complete rewrite from scratch. Full alignment with Core_Spec.md v2.0 (TERA-CORE). 15 features with mandatory Feature Definition Standard (platforms, user flow, Core dependencies, data interaction, constraints, failure handling). §5 Feature ↔ Core Mapping table with explicit TERA-CORE references for all 15 features. §0 Client-side Data Object Catalog with Core cross-references for every object. §9 Anti-Technical-Debt Rules (ATD-01 through ATD-14). §10 Implementation Contract with unique rule IDs (SEC-01–SEC-05, PLT-01–PLT-07, FI-01–FI-05, IPC-01–IPC-03). Platform constraint matrix with feature impact column. Known implementation gaps table with severity and status. Incorporated from all architecture sessions: WasmParity CI gate (F-07, §8.3), Dart FFI NativeFinalizer Clippy lint (F-03, §10.1 SEC-02), iOS AWDL conflict resolution (F-05/F-06), EMDP Key Escrow Handshake (F-05), Versioned Push Key Ladder (F-02), Double-Buffer Zeroize (F-11), `sled` crate pin for transient state (F-07, §10.3 FI-04), Border Node auto-detection (F-05), Linux multi-init daemon + AppArmor/SELinux postinstall (F-15), Huawei CRL delay SLA disclosure (F-02/§8.1), Adaptive QUIC Probe Learning (F-14), XPC Journal crash recovery (F-07), Shadow DB Write Lock Protocol (F-04), iOS CoreML parity path (F-10), `MemoryArbiter` RAM budget enforcement (§3.3), SAB Tier Ladder audit trail (§10.4 IPC-02). |
| 0.2.1 | 2026-03-13 | Legacy iterative updates (see TERA-CORE §13 for aligned changelog context). Deprecated React Native → Flutter unified mobile. Added PLATFORM-01 through PLATFORM-16 sections (now fully integrated into feature definitions above). |
| 0.1.1 | 2026-03-04 | Initial feature spec. Added WASM Sandbox Isolation, Protected Clipboard Bridge, Zero-Byte Stub rendering, NSE Circuit Breaker. |

---

*Cross-references:*

- *MLS cryptographic internals, CRDT algorithms, server infrastructure → `TERA-CORE` (`Core_Spec.md`)*
- *UI animation, glassmorphism state machine → `TERA-DESIGN` (`Design.md`)*
- *Plugin publishing, Marketplace review, `.tapp` signing → `TERA-MKT` (`Web_Marketplace.md`)*
- *Combined-failure chaos test scenarios → `TERA-TEST` (`TestMatrix.md`)*
- *Code signing pipeline, certificate rotation → `ops/signing-pipeline.md`*
- *PostgreSQL PITR recovery, Shamir ceremony → `ops/db-recovery.md`, `ops/shamir-bootstrap.md`*

