import re

def insert_after(content, anchor_regex, text_to_insert):
    match = re.search(anchor_regex, content)
    if not match:
        print(f"FAILED to find {anchor_regex}")
        return content
    idx = match.end()
    # ensure newlines
    insertion = f"\n\n{text_to_insert}\n"
    return content[:idx] + insertion + content[idx:]

def replace_chunk(content, anchor_regex, replacement_regex, new_text):
    pass

core = open("Core_Spec.md").read()

# Patches for Core_Spec.md
core_patches = [
    (r"### 7\.1 DAG Structure and Storage", """<!-- INSERTED PATCH: SQLite WAL Hydration & Tombstone Vacuum -->
- ☁️ Reference `HydrationScheduler §18.1` for global cross-session concurrency controls.
- ☁️ Clients MUST implement exponential backoff with jitter prior to requesting a hydration slot.
- ☁️ Per-tenant rate limit is strictly enforced at a maximum of 10 clients per second.
- 🗄️ Clarification on 7-day hot DAG eviction and the `tombstone.clock ≤ MVC` condition: The 7-day eviction mechanism is triggered strictly AFTER the MVC condition is satisfied.
- 🗄️ During an active Mesh Network partition (Mesh_Partition_Active = true), eviction protocols are strictly suspended."""),

    (r"### 5\.5 Out-of-Band Push Key Ratchet", """<!-- INSERTED PATCH: MLS — OOB Push Ratchet -->
- ☁️ Reference `§17.2` for key versioning protocols.
```rust
pub struct PushKeyEntry {
    pub version: u32,           // Monotonic identification, per chat_id
    pub key_material: [u8; 32], // AES-256-GCM session key
    pub derived_at_epoch: u64,  // MLS epoch correlation when key was derived
    pub valid_until: u64,       // Unix timestamp bounds
}
```"""),

    (r"### 6\.3 BLE Stealth Beaconing", """<!-- INSERTED PATCH: Stealth Wake-up Protocol -->
- 🌐 `IdentityCommitment` structure updated to utilize a 16-byte `c_trunc` instead of 8 bytes to establish 128-bit collision resistance.
- 🌐 Backward-compatibility dual parsing is mandatory to support legacy 8-byte beacon configurations simultaneously with newer 16-byte setups. Deprecation of legacy format scheduled post 90 days.

```rust
pub struct IdentityCommitment {
    /// REVISED: 16 bytes payload (upgraded from 8 bytes)
    /// Guarantees 128-bit security making brute-forcing infeasible across GPU clusters
    c_trunc: [u8; 16],
}
```"""),

    (r"### 6\.5 Dictator Election \(Split-Brain Resolution\)", """<!-- INSERTED PATCH: Split-Brain Resolution -->
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
```"""),

    (r"### 7\.3 Split-Brain Reconciliation", """<!-- INSERTED PATCH: Split-Brain — Causal Fast-Forward -->
- 🖥️ The Canonical Epoch Election specifies `HLC timestamp` as the primary deterministic key.
- 🖥️ `tree_fingerprint` serves as the explicit tie-breaker fallback mechanism ensuring uniform network progression regardless of partition divergence origins.
- 📱 Desktop architectures utilize chunking without yield delays; Mobile forces chunks with yields for frame drops."""),

    (r"### 5\.1 Key Management System \(HKMS\)", """<!-- INSERTED PATCH: Bloom Filter CRL -->
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
```"""),

    (r"### 4\.3 FFI Token Protocol", """<!-- INSERTED PATCH: Formal IPC Memory Ownership Contract -->
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
```"""),

    (r"### 6\.7 Emergency Mobile Dictator Protocol \(EMDP\)", """<!-- INSERTED PATCH: EMDP Key Escrow -->
- 💻 The Desktop client MUST finalize and emit the active security escrow state parameters *before* triggering network disconnection logic.
- 💻 Exception fallback: If the Desktop disconnects non-gracefully prior to generating the escrow, standard Timeout constraints govern connection collapse handling."""),

    (r"### 9\.6 Operational Metrics", """<!-- INSERTED PATCH: Observability Layer -->
> **Principle:** Zero-Knowledge Observability — metrics and traces MUST NOT contain plaintext content, actual User IDs, or exact key materials. All telemetry must be content-free and pseudonymous.
- ☁️📱💻🖥️ **Log Format (OTEL-compatible JSON):** Applications emit structured JSON via the `TeraLogEntry` schema enforcing `session_hash` (pseudonymous). Strict prohibition of `user_id`, `message_content`, or `*_key`.
- ☁️ **Log Pipeline:** OTEL Collector (VPS-local) → Loki → Grafana. Strict 90-day retention policies (extendable to 7 years in Compliance tier).
- ☁️ **Per-tenant Isolation:** Partitioned structurally via `tenant_hash` protecting against any cross-tenant log pollution.
- 💻📱 **Client-side Metrics:** Abstracted exports pipeline via TeraDiag triggering OTLP pushes strictly when online capacity allows, bypassing client-side real-time polling."""),

    (r"### 9\.7 Distributed Tracing \(OpenTelemetry\)", """<!-- INSERTED PATCH: Distributed Tracing additions -->
- ☁️ **Tracing Stack:** OpenTelemetry SDK → OTLP exporter → Tempo. Sampling: 100% error traces, 1% success traces (production environment).
- ☁️ **Trace Boundaries:** Root spanning mapped globally to message pipeline executions. Supported Child Spans inclusive up to `mls.decrypt`, `dag.write`, `ipc.dispatch`, and `network.egress`."""),

    (r"### 9\.5 Database Layer", """<!-- INSERTED PATCH: Schema Versioning Protocol -->
> **Principle:** All structured data schemas require formal deterministic versioning limits. Breaking structural changes belong strictly inside designated major updates maintaining strict reverse compatibility profiles.

```rust
pub const HOT_DAG_SCHEMA_VERSION: u32 = 1;

pub struct DagSchemaMetadata {
    pub version: u32,
    pub created_at: u64,        // Unix timestamp anchor
    pub min_compatible: u32,    // Bound mapping minimum Core compatibility requirements 
    pub blake3_schema_hash: [u8; 32],  // Structural verification hash footprint
}
```

- 🗄️ Standard migration executions require transactional atomic wrappers: Backup → `BEGIN EXCLUSIVE` → Apply Schema Delta → `PRAGMA user_version` → `COMMIT`. Rollback utilizes exact reverse restoration execution.
- 🗄️ If `cold_state.db` structural migrations encounter unrecoverable states, safe default dictates a hard drop executing full materialization from `hot_dag.db`."""),

    (r"### 7\.1 DAG Structure and Storage", """<!-- INSERTED PATCH: Hydration Scheduler & Thundering Herd Protection -->
- ☁️ Reconnecting clients MUST funnel through the global `HydrationScheduler` queue boundary prior to triggering direct WAL hydration workloads.
- **Constraints:** Max concurrency configuration limits mathematically map to `floor(available_ram_mb / 64)`. Per-tenant limits cap at exactly 10 clients/second handling a 30-second rejection queue timeout.
- 🗄️ Background WAL checkpoints execute parallel to decoupled dedicated thread pools bypassing the core Tokio runtime logic entirely. Utilizes `PRAGMA wal_checkpoint(PASSIVE)` yielding to read constraints smoothly avoiding fsync blocks."""),
]

for anchor, patch in core_patches:
    core = insert_after(core, anchor, patch)

with open("Core_Spec.md", "w") as f:
    f.write(core)

feature = open("Feature_Spec.md").read()

feature_patches = [
    (r"### F-10: AI / SLM Integration", """<!-- INSERTED PATCH: Edge ONNX Embedding Engine & Model Integrity Protocol -->
- ⚙️ ONNX operational execution heavily relies on the architectural limits set functionally inside `PLATFORM-18`.
- ⚙️ Initial model allocation parsing mandatorily executes through `OnnxModelLoader.load_verified()` pipeline wrappers to ensure BLAKE3 + Ed25519 signature integrity.
> **Mandatory Model Integrity Rules:**
1. ⚙️ Signature verification structurally relies precisely against specific endpoints maintaining `Ed25519` values routed perfectly inside the central TeraChat Model Signing Root nodes checking isolated `model_name.sig` blocks.
2. ⚙️ BLAKE3 hashing specifications require internal compilation hard-coding paths executing cleanly directly bounded inside `build.rs` targets locking binary bounds preventing network lookup risks natively.
3. ⚙️ Linear sequence execution locks strict bounds dropping precisely scaling: BLAKE3 hash execution validation → Ed25519 signature constraint bounds → active ONNX session loading calls. Error mapping enforces functional quarantine limits backing down dynamically to keyword mapping.
4. ⚙️ Host retrieval pipelines exclusively demand natively enforced DoH (DNS-over-HTTPS) bounds bundled inside TLS wrappers utilizing mapped SPKI pinning parameters natively bouncing standard DNS limits rejecting open DNS queries directly."""),

    (r"### F-04: Local Storage Management", """<!-- INSERTED PATCH: Two-Tier State Squashing & Stream-based Hydration -->
- 🗄️ Explicit protocol specification: The 7-day hot DAG structural eviction trigger is explicitly **suspended** when the `Mesh_Partition_Active` parameter returns `true`.
- 🗄️ Standard eviction clears ONLY trigger after the `tombstone.clock ≤ MVC` requirement fully satisfies constraints mapped across `TERA-CORE §17.1`.
- 🌐 Hydration capabilities route through variables mapping across `HydrationScheduler` load balancers.
- 🌐 Connected endpoints strictly implement mathematical exponential backoff procedures structured tightly via execution jitter limits initiating hydration slot calls."""),

    (r"### F-01: Secure E2EE Messaging", """<!-- INSERTED PATCH: Chunked DAG Merger & Progress UI -->
- 📱 Mobile environments execute `ChunkedDagMerger` logic wrapping hard boundaries over a maximum count allocation limits explicitly set to `MAX_MOBILE_MERGE_EVENTS = 3000`.
- 📱 Excess triggers dispatch an asynchronous payload containing an isolated `SnapshotRequired` IPC signalling spec execution to offload processing to the Desktop layer.
- 📱 Computations expanding boundaries wider than 500 events natively trigger Core progression flags via mapped IPC signals explicitly structured using `DagMergeProgress` schemas.
- 📱 **Mobile UI:** Linear completion bars output mapped text representations limiting block impacts scaling: "Synchronizing [X]% — [Y] messages remaining". Non-blocking background parameters correctly maintain user interactions cleanly.
- 💻🖥️ **Desktop UI:** Embedded mapping renders a subtle background marker positioned on the corner status bar. Eliminating central processing modals inherently respects high desktop background computational bounds."""),

    (r"### F-02: Push Notification Delivery \(E2EE\)", """<!-- INSERTED PATCH: Zero-Knowledge Push Notification -->
- ☁️ Struct modifications inside `Push_Key` require standard `version: u32` allocation mapping limits.
- ☁️ NSE routines implement a strict read validation from the payload header configuration parsing keys specifically matched to precise parameter alignment as outlined across `TERA-CORE §17.2`."""),

    (r"### F-03: IPC Bridge and State Synchronization", """<!-- INSERTED PATCH: Dart FFI Contract — Mandatory Enforcement -->
> **Note: Supersedes PLATFORM-14.** Mandatory contract mapping explicitly tied directly to CI/CD compilation blocks yielding compiler drops upon internal constraint violation sequences.
1. 🔗 Extracted pointers via natively structured `TeraSecureBuffer` elements ALWAYS mandate encapsulation logic specifically run exactly inside `useInTransaction()`.
2. 🔗 The Core Rust Token Registry logic actively bypasses internal zeroization sequence flags over TTL limit bounds directly preferring manual interaction states explicitly invoking `releaseNow()`.
3. 🔗 TTL timeout boundaries crossing limits trigger asynchronous internal structures broadcasting `IpcSignal::TransactionTimeout` flags yielding mapped parameter modals alerting: "Timeout boundary reached, require explicit re-initiation sequences".
4. 🔗 Routine Garbage Collector parsing is heavily depreciated only mapping inside limits specifically structured uniquely as safety-net fallback variables maintaining detailed log tracking capabilities."""),
    
    (r"### F-13: Admin Console and Enterprise Controls", """<!-- INSERTED PATCH: Client-Side Observability Integration -->
### Client-Side Observability Integration
- 📱 **OTEL Push (khi online):** Core logic exports mapped metrics strictly functioning out over OTLP HTTP POST payload limits routing to VPS operational endpoints strictly within 60s intervals. Data parsing exclusively utilizes the `TeraDiagMetrics` protobuf schema.
- 📱 **Offline Buffer:** Metrics load and cache directly into local variables mapping inside isolation wrappers marked fully as `metrics_buffer.db` bounded strictly at 24 hours. Connective limits flush buffers dynamically tracking immediate network reconnections.
- 📱 **Battery-Aware Export:** Detection constraints drop metric transmission intervals structurally back over 300s when power levels detect constraints < 20%. Suspensions drop cleanly at ≤ 10%.
- 💻🖥️ **Prometheus Node Exporter:** Standard node routing parses direct exposure inside the local `/metrics` host parameter set cleanly limiting access exclusively bounded to `localhost:9092`.
- 💻🖥️ **OTLP Push Fallback:** Alternate bounds revert exactly parsing metrics to the native VPS OTEL Collector pipelines mapped standard from internal Mobile specifications.
- 📱💻 **GC Release Warning:** Warning metrics trigger functionally mapping when automated GC boundaries execute a garbage cache reduction over `TeraSecureBuffer` parameter instances sidestepping typical `releaseNow()` explicit paths.""")
]

for anchor, patch in feature_patches:
    feature = insert_after(feature, anchor, patch)

with open("Feature_Spec.md", "w") as f:
    f.write(feature)

print("Applied Patches successfully!")
