Tôi sẽ viết trực tiếp toàn bộ nội dung — đây là output lớn, tôi sẽ chia làm hai phần rõ ràng.

---

# PHẦN 1 — `Core_Spec.md` — Các Section Mới & Cập Nhật

---

## CHANGELOG (bổ sung vào bảng hiện có)

```markdown
| v0.4.0 | 2026-03-19 | Add §16 Observability Layer; §17 Schema Versioning; §19 HSM HA;
|         |            | §20 TeraEdge Device; Update §5.15 EpochId split-brain fix;
|         |            | Update §5.9.3 C_trunc 8B→16B; Update §10.6 RotatingCrlFilter |
```

---

## §16 — Observability Layer

```markdown
## 16. [ARCHITECTURE] [IMPLEMENTATION] Observability Layer

> **Nguyên tắc Zero-Knowledge Observability:** Metrics và traces KHÔNG
> chứa plaintext message, User_ID thật, key material, hay bất kỳ thông tin
> có thể deanonymize user. Mọi telemetry content-free và pseudonymous.
> Đây là hard constraint, không phải best-practice.

---

### 16.1 [ARCHITECTURE] Stack Overview

```text
[Rust Daemon / Client Metrics]
         │ OTLP gRPC (port 4317)
         ▼
[OTEL Collector — VPS local]
    ├──▶ Loki (logs, port 3100)
    ├──▶ Prometheus (metrics, port 9090)
    └──▶ Tempo (traces, port 3200)
         │
         ▼
    [Grafana — port 3000]
    (dashboards + alerting)
         │
         ▼
    [Alertmanager — port 9093]
    (PagerDuty / Slack routing)
```

Toàn bộ stack chạy trên cùng VPS với TeraRelay dưới dạng
`docker compose up -d` — không cần infrastructure riêng biệt.

> **Resilience note:** Khi VPS OOM-Kill xảy ra, observability stack cũng
> bị kill. Mitigation: Rust Daemon buffer metrics locally trong
> `metrics_buffer.db` (SQLite, tối đa 24h) và flush khi stack recovery.
> Không cần separate VPS cho SME tier. Enterprise tier nên deploy
> observability trên VPS riêng ($6/tháng thêm).

---

### 16.2 [IMPLEMENTATION] Structured Logging

☁️📱💻🖥️ **Zero-Knowledge Log Schema:**

```rust
/// Mọi component PHẢI dùng struct này — không log freeform string
#[derive(serde::Serialize)]
pub struct TeraLogEntry<'a> {
    // REQUIRED
    pub timestamp:    &'a str,           // RFC3339 nanosecond
    pub level:        LogLevel,          // ERROR | WARN | INFO | DEBUG
    pub component:    Component,         // enum, không phải string tự do
    pub event:        &'a str,           // machine-readable, snake_case

    // CONTEXT — pseudonymous only
    pub session_hash: Option<&'a str>,   // BLAKE3(session_id)[0:8] hex
    pub tenant_hash:  Option<&'a str>,   // BLAKE3(tenant_id)[0:8] hex
    pub device_class: Option<DeviceClass>,

    // OPTIONAL
    pub trace_id:     Option<&'a str>,   // OTEL hex
    pub span_id:      Option<&'a str>,   // OTEL hex
    pub duration_ms:  Option<f64>,
    pub message:      &'a str,           // human-readable
}

// CẤMTUYỆT ĐỐI log các field sau — CI lint rule enforce:
// user_id, message_content, *_key, plaintext_*, raw_payload
```

☁️📱💻🖥️ **Event Catalog chuẩn hóa** — mọi component chỉ được dùng
events trong enum sau, không được tự tạo string mới:

```rust
pub enum TeraEvent {
    // MLS Core
    MlsEpochRotated       { sequence: u64, group_size: u32 },
    MlsDecryptFailed      { reason: DecryptFailReason },
    MlsSplitBrainDetected { local_seq: u64, remote_seq: u64 },
    MlsAddMember          { success: bool, duration_ms: f64 },

    // Mesh
    MeshNodeDiscovered  { transport: Transport, rssi_dbm: i8 },
    MeshRoleChanged     { from: MeshRole, to: MeshRole },
    MeshPartition       { island_size: u32 },
    MeshHandover        { to_node_hash: String },

    // Storage
    WalCheckpoint       { pages: u32, duration_ms: f64 },
    DagMerge            { events: u32, duration_ms: f64, platform: Platform },
    HydrationQueued     { queue_depth: u32, tenant_hash: String },
    HydrationCompleted  { success: bool, duration_ms: f64 },
    SnapshotPublished   { events_covered: u64 },

    // WASM
    WasmStarted         { tapp_hash: String, init_ms: f64 },
    WasmEgressBlocked   { reason: EgressBlockReason, bytes: u32 },
    WasmKillSwitch      { tapp_hash: String },

    // Security
    ZeroizeTriggered    { component: &'static str, bytes: u64 },
    CrlRevocation       { method: String },
    TokenTimeout        { age_ms: u64 },
    OnnxModelInvalid    { model: OnnxModel, reason: String },
    FfiBufferGcRelease  { },  // WARNING: developer bug

    // Push
    PushDecrypt         { success: bool, latency_ms: f64 },
    PushKeyDesync       { expected: u32, actual: u32 },

    // Relay (server-side)
    ClientConnected     { protocol: Protocol },
    ClientDisconnected  { reason: DisconnectReason },
    BlobIndexed         { size_bytes: u64 },
    FederationBridge    { direction: BridgeDir, success: bool },
}
```

☁️ **Log Pipeline config:**

```yaml
# /etc/tera-relay/otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: "0.0.0.0:4317" }
      http: { endpoint: "0.0.0.0:4318" }

processors:
  batch:
    timeout: 5s
    send_batch_size: 1000
  # Drop bất kỳ log nào vô tình chứa sensitive fields
  filter/security:
    logs:
      exclude:
        match_type: regexp
        bodies: ["user_id=", "message_content=", "_key=", "plaintext_"]

exporters:
  loki:
    endpoint: "http://localhost:3100/loki/api/v1/push"
  prometheus:
    endpoint: "0.0.0.0:9464"
  otlp/tempo:
    endpoint: "localhost:4317"
    tls: { insecure: true }

service:
  pipelines:
    logs:    { receivers: [otlp], processors: [batch, filter/security], exporters: [loki] }
    metrics: { receivers: [otlp], processors: [batch], exporters: [prometheus] }
    traces:  { receivers: [otlp], processors: [batch], exporters: [otlp/tempo] }
```

---

### 16.3 [IMPLEMENTATION] Metrics

☁️📱💻🖥️ **Rust integration** — thêm vào `Cargo.toml`:

```toml
opentelemetry        = { version = "0.22", features = ["metrics","trace"] }
opentelemetry_sdk    = { version = "0.22", features = ["rt-tokio"] }
opentelemetry-otlp   = { version = "0.15", features = ["tonic","metrics"] }
tracing              = "0.1"
tracing-opentelemetry = "0.23"
tracing-subscriber   = { version = "0.3", features = ["env-filter","json"] }
```

☁️📱💻🖥️ **Core metrics struct:**

```rust
pub struct TeraMetrics {
    // Histograms (latency)
    pub msg_e2e_latency_ms:       Histogram<f64>,
    pub crypto_duration_ms:       Histogram<f64>,
    pub dag_merge_duration_ms:    Histogram<f64>,
    pub wasm_cold_start_ms:       Histogram<f64>,
    pub onnx_inference_ms:        Histogram<f64>,

    // Counters (throughput / errors)
    pub messages_total:           Counter<u64>,
    pub mls_decrypt_errors:       Counter<u64>,
    pub egress_blocked_total:     Counter<u64>,
    pub wal_checkpoints_total:    Counter<u64>,
    pub push_decrypt_total:       Counter<u64>,
    pub ffi_gc_release_total:     Counter<u64>,   // developer bug detector

    // Gauges (state)
    pub mesh_nodes_active:        ObservableGauge<u64>,
    pub wal_size_bytes:           ObservableGauge<u64>,
    pub hydration_queue_depth:    ObservableGauge<u64>,
    pub wasm_instances_active:    ObservableGauge<u64>,
    pub ffi_tokens_active:        ObservableGauge<u64>,
    pub relay_connections_active: ObservableGauge<u64>,
}

// Offline buffer — flush khi OTEL stack recovery
pub struct MetricsBuffer {
    db: SqliteConnection,  // metrics_buffer.db, max 24h
}

impl MetricsBuffer {
    pub fn record(&self, metric: BufferedMetric) -> Result<()> {
        // Ghi vào SQLite khi OTEL collector không reachable
        self.db.execute(
            "INSERT INTO buffer (ts, name, value, labels) VALUES (?1,?2,?3,?4)",
            (unix_now(), metric.name, metric.value, metric.labels_json()),
        )
    }

    pub async fn flush_to_otel(&self, exporter: &OtlpExporter) -> Result<usize> {
        let pending = self.db.query("SELECT * FROM buffer ORDER BY ts")?;
        let count = pending.len();
        exporter.export_batch(pending).await?;
        self.db.execute("DELETE FROM buffer")?;
        Ok(count)
    }
}
```

---

### 16.4 [IMPLEMENTATION] Distributed Tracing

☁️📱💻🖥️ **Trace design — pseudonymous only:**

```rust
// Trace một message qua toàn pipeline
// KHÔNG include: user_id, sender, recipient, message content
#[instrument(
    fields(
        session_hash = %blake3_short(session_id),
        tenant_hash  = %blake3_short(tenant_id),
        payload_bytes = payload.len(),
    )
)]
pub async fn trace_message_pipeline(
    payload:    &EncryptedPayload,
    session_id: &SessionId,
    tenant_id:  &TenantId,
) -> Result<()> {
    // Child span: MLS decrypt
    let _s = tracing::info_span!("mls.decrypt").entered();
    let plaintext = mls_decrypt(payload).await?;
    drop(_s);

    // Child span: DAG write
    let _s = tracing::info_span!("dag.write",
        dag_events = dag_current_size()
    ).entered();
    write_to_dag(&plaintext).await?;
    drop(_s);

    // Child span: IPC dispatch
    let _s = tracing::info_span!("ipc.dispatch",
        transport = "dart_ffi"
    ).entered();
    dispatch_to_ui().await
}
```

☁️ **tokio-console** — development/staging ONLY:

```toml
# Cargo.toml
[features]
tokio-console = ["dep:console-subscriber"]

[dependencies]
console-subscriber = { version = "0.2", optional = true }
```

```rust
// main.rs
#[cfg(feature = "tokio-console")]
fn init_dev_tools() { console_subscriber::init(); }
#[cfg(not(feature = "tokio-console"))]
fn init_dev_tools() {}
```

**Không được enable `tokio-console` trong production binary.**

---

### 16.5 [ARCHITECTURE] SLO Definitions

| SLO ID | Metric | Target | Window | Error Budget |
|--------|--------|--------|--------|--------------|
| SLO-01 | Message delivery availability | 99.9% | 30d | 43.8 min/month |
| SLO-02 | Message E2E latency Online P99 | < 200ms | 30d | — |
| SLO-03 | Message E2E latency Mesh P99 | < 2000ms | 30d | — |
| SLO-04 | Push notification delivery | 99.5% | 30d | 3.6 h/month |
| SLO-05 | MLS decrypt error rate | < 0.01% | 30d | — |
| SLO-06 | Relay uptime | 99.9% | 30d | 43.8 min/month |

**SLA tiers:**

- Community: 99% best-effort, no SLA
- Enterprise: SLO-01 + SLO-02 + SLO-06 với 4h support response
- Gov/Military: SLO-01 through SLO-06, 1h response, Chaos Engineering verified

---

### 16.6 [IMPLEMENTATION] Alert Rules

```yaml
# /etc/tera-relay/alert-rules.yaml
groups:
  - name: terachat.critical
    rules:
      - alert: MessageDeliverySLOBreach
        expr: |
          rate(terachat_messages_total{status="success"}[5m])
          / rate(terachat_messages_total[5m]) < 0.999
        for: 5m
        labels: { severity: critical }
        annotations:
          summary: "Message delivery below 99.9% SLO"
          runbook: "https://docs.terachat.internal/runbooks/msg-delivery"

      - alert: VpsOomImminent
        expr: (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) < 0.10
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "VPS RAM < 10% — OOM-Kill imminent"

      - alert: HydrationQueueSaturated
        expr: terachat_hydration_queue_depth > 50
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Hydration queue {{ $value }} — thundering herd"

      - alert: MlsDecryptSpike
        expr: rate(terachat_mls_decrypt_errors[5m]) > 0.01
        for: 2m
        labels: { severity: critical }
        annotations:
          summary: "MLS decrypt errors {{ $value | humanizePercentage }} — possible split-brain"

  - name: terachat.warning
    rules:
      - alert: DagMergeLatencyHigh
        expr: |
          histogram_quantile(0.95,
            rate(terachat_dag_merge_duration_ms_bucket[5m])
          ) > 2000
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "DAG merge P95 {{ $value }}ms — ANR risk"

      - alert: WalSizeGrowing
        expr: terachat_wal_size_bytes > 50000000
        for: 10m
        labels: { severity: warning }
        annotations:
          summary: "WAL {{ $value | humanizeBytes }} — checkpoint needed"

      - alert: PushKeyDesync
        expr: rate(terachat_push_key_desync_total[5m]) > 0
        for: 1m
        labels: { severity: warning }
        annotations:
          summary: "Push key version mismatch — notification risk"

      - alert: FfiBufferGcRelease
        expr: rate(terachat_ffi_gc_release_total[1h]) > 0
        labels: { severity: warning, team: mobile }
        annotations:
          summary: "Dart FFI buffer released by GC — developer bug"
          description: "Check useInTransaction() usage in Flutter code"

      - alert: OnnxModelIntegrityFailed
        expr: rate(terachat_onnx_model_invalid_total[1h]) > 0
        labels: { severity: warning, team: security }
        annotations:
          summary: "ONNX model integrity check failed — possible poisoning"

  - name: terachat.slo_burn
    rules:
      - alert: ErrorBudget50Percent
        expr: |
          (1 - (rate(terachat_messages_total{status="success"}[1h])
                / rate(terachat_messages_total[1h]))) > 0.0005
        for: 0m
        labels: { severity: warning }
        annotations:
          summary: "Error budget burning at 50%+ rate"

      - alert: ErrorBudget90Percent
        expr: |
          (1 - (rate(terachat_messages_total{status="success"}[6h])
                / rate(terachat_messages_total[6h]))) > 0.0009
        for: 0m
        labels: { severity: critical }
        annotations:
          summary: "Error budget 90% consumed — SLO breach imminent"
```

---

### 16.7 [IMPLEMENTATION] Docker Compose Deployment

```yaml
# /etc/tera-relay/observability.compose.yaml
# Chạy: docker compose -f observability.compose.yaml up -d

services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.96.0
    volumes:
      - ./otel-collector-config.yaml:/etc/otel/config.yaml:ro
    ports: ["4317:4317", "4318:4318", "9464:9464"]
    restart: unless-stopped
    mem_limit: 128m

  prometheus:
    image: prom/prometheus:v2.50.0
    volumes:
      - ./prometheus.yaml:/etc/prometheus/prometheus.yaml:ro
      - ./alert-rules.yaml:/etc/prometheus/alert-rules.yaml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yaml'
      - '--storage.tsdb.retention.time=90d'
    restart: unless-stopped
    mem_limit: 256m

  loki:
    image: grafana/loki:2.9.5
    volumes:
      - ./loki-config.yaml:/etc/loki/config.yaml:ro
      - loki_data:/var/loki
    restart: unless-stopped
    mem_limit: 256m

  tempo:
    image: grafana/tempo:2.4.0
    volumes:
      - ./tempo-config.yaml:/etc/tempo/config.yaml:ro
      - tempo_data:/var/tempo
    restart: unless-stopped
    mem_limit: 256m

  grafana:
    image: grafana/grafana:10.3.0
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_AUTH_ANONYMOUS_ENABLED=false
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
    ports: ["3000:3000"]
    restart: unless-stopped
    mem_limit: 128m

  alertmanager:
    image: prom/alertmanager:v0.27.0
    volumes:
      - ./alertmanager.yaml:/etc/alertmanager/config.yaml:ro
    restart: unless-stopped
    mem_limit: 64m

volumes:
  prometheus_data:
  loki_data:
  tempo_data:
  grafana_data:

# Tổng RAM footprint: ~1GB
# Khuyến nghị: VPS 2GB RAM cho relay+observability cùng node
# Hoặc: VPS riêng $6/tháng cho observability (Enterprise tier)
```

```

---

## §17 — Schema Versioning Protocol

```markdown
## 17. [ARCHITECTURE] [IMPLEMENTATION] Schema Versioning Protocol

> **Nguyên tắc:** Mọi data schema có cross-component dependency PHẢI có
> formal versioning. Breaking changes chỉ được phép trong major version.
> Migration phải backward-compatible và có automated rollback.

---

### 17.1 [IMPLEMENTATION] hot_dag.db Schema Versioning

```rust
// Đọc version hiện tại qua SQLite pragma
pub const HOT_DAG_SCHEMA_VERSION: u32 = 1;
pub const HOT_DAG_MIN_COMPATIBLE: u32 = 1;

pub struct DagSchemaMeta {
    pub version:         u32,
    pub min_compatible:  u32,
    pub created_at:      u64,
    /// BLAKE3 của schema DDL — detect tampering
    pub schema_hash:     [u8; 32],
}

pub struct MigrationRunner {
    migrations: Vec<Box<dyn Migration>>,
}

impl MigrationRunner {
    pub async fn run(&self, conn: &SqliteConnection) -> Result<()> {
        let current: u32 = conn
            .pragma_query_value(None, "user_version", |r| r.get(0))?;

        for m in self.migrations.iter().filter(|m| m.version() > current) {
            // 1. Backup trước khi migrate
            let backup = format!("{}.bak.v{}", db_path, current);
            conn.backup(DatabaseName::Main, &backup, None)?;

            // 2. Migrate trong transaction duy nhất
            conn.execute_batch("BEGIN EXCLUSIVE")?;
            m.up(conn)?;
            conn.pragma_update(None, "user_version", m.version())?;
            conn.execute_batch("COMMIT")?;

            info!(event = "schema.migrated",
                  from = current, to = m.version());
        }
        Ok(())
    }
}

// Safety net: cold_state.db có thể rebuild từ hot_dag.db bất kỳ lúc nào
// Nếu cold_state.db migration fail → drop + rebuild
pub async fn rebuild_cold_from_hot(
    hot: &SqliteConnection,
    cold_path: &Path,
) -> Result<()> {
    if cold_path.exists() { tokio::fs::remove_file(cold_path).await?; }
    let cold = SqliteConnection::open(cold_path).await?;
    materialize_hot_to_cold(hot, &cold).await
}
```

---

### 17.2 [IMPLEMENTATION] Push Key Version Alignment

**Vấn đề đã xác định:** `push_key_version (u32)` trong Feature_Spec
PLATFORM-04 không được phản ánh trong `Push_Key` struct của Core_Spec §4.2.
Đây là nguồn gốc của silent notification loss khi key rotation.

**Fix:**

```rust
// Core_Spec §4.2 — OOB Symmetric Push Ratchet — UPDATED
// Push_Key struct bắt buộc include version field

#[derive(Clone, ZeroizeOnDrop)]
pub struct PushKeyEntry {
    /// Monotonic, per chat_id. NSE đọc field này TRƯỚC khi decrypt.
    pub version:          u32,
    /// AES-256-GCM key material
    pub key_material:     [u8; 32],
    /// MLS epoch khi key được derive — cho audit trail
    pub derived_at_epoch: u64,
    /// Expiry: now() + 7 * 24 * 3600
    pub valid_until:      u64,
}

// Shared Keychain key format (iOS App Group / Android StrongBox):
// "terachat.push.v{version}.{chat_id_hash}" → PushKeyEntry

// NSE lookup logic (Core_Spec §5.1):
pub fn get_push_key_for_version(
    chat_id: &ChatId,
    payload_version: u32,
) -> Result<PushKeyEntry> {
    // Đọc đúng version từ Keychain — không assume latest
    let key_id = format!("terachat.push.v{}.{}", payload_version, chat_id.hash());
    keychain_read(&key_id)
        .map_err(|_| PushError::KeyVersionNotFound { version: payload_version })
}
```

---

### 17.3 [IMPLEMENTATION] EpochId với Tree Fingerprint

**Vấn đề:** Khi 2 Mesh islands đều rotate lên Epoch 11 với TreeKEM tree
state khác nhau, decrypt trên island khác sẽ fail silently vì cùng
sequence number nhưng keys khác nhau.

```rust
// Core_Spec §5.15 — Split-Brain Reconciliation — UPDATED

#[derive(Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct EpochId {
    /// Monotonic sequence — tăng mỗi lần Epoch Rotation
    pub sequence:         u64,
    /// BLAKE3(TreeKEM_root_state)[0:16]
    /// Uniquely identifies WHICH tree state → detect split-brain
    pub tree_fingerprint: [u8; 16],
    /// HLC timestamp của epoch creation — dùng làm canonical tiebreaker
    pub created_at:       HybridLogicalTimestamp,
}

impl EpochId {
    pub fn is_split_brain_conflict(&self, other: &Self) -> bool {
        self.sequence == other.sequence &&
        self.tree_fingerprint != other.tree_fingerprint
    }

    /// Canonical election: epoch với HLC timestamp nhỏ hơn thắng
    /// Tie-break: BLAKE3(tree_fingerprint) lexicographic
    pub fn elect_canonical<'a>(a: &'a Self, b: &'a Self) -> &'a Self {
        match a.created_at.cmp(&b.created_at) {
            std::cmp::Ordering::Less    => a,
            std::cmp::Ordering::Greater => b,
            std::cmp::Ordering::Equal   =>
                if a.tree_fingerprint <= b.tree_fingerprint { a } else { b },
        }
    }
}

// MLS message header — thêm EpochId
pub struct MlsMessageHeader {
    pub epoch_id:          EpochId,       // ADDED — replaces plain epoch_sequence
    pub sender_device_id:  DeviceId,
    pub sealed_sender:     Vec<u8>,
}

// Receiver: detect split-brain khi nhận message với conflicting epoch
pub fn on_receive_mls_message(
    header: &MlsMessageHeader,
    local_epoch: &EpochId,
) -> ReceiveAction {
    if header.epoch_id.is_split_brain_conflict(local_epoch) {
        // Emit metric + alert
        metrics().mls_split_brain.increment(1);
        warn!(event = "MlsSplitBrainDetected",
              local_seq = local_epoch.sequence,
              remote_seq = header.epoch_id.sequence);

        // Elect canonical và trigger reconciliation
        let canonical = EpochId::elect_canonical(&header.epoch_id, local_epoch);
        ReceiveAction::TriggerReconciliation { canonical: canonical.clone() }
    } else {
        ReceiveAction::Proceed
    }
}
```

---

### 17.4 [IMPLEMENTATION] Tombstone Vacuum — Disambiguation Rule

**Vấn đề:** Feature_Spec §6.12 nói "7-day eviction" nhưng Core_Spec §5.10.1
nói "vacuum chỉ khi `tombstone.clock ≤ MVC`". Hai điều kiện có thể conflict
khi Mesh partition đang active.

**Rule rõ ràng:**

```rust
// Core_Spec §5.10.1 — UPDATED with explicit priority rule

pub fn should_vacuum_tombstone(
    tombstone: &TombstoneStub,
    mvc: &MergedVectorClock,
    partition_active: bool,
    age_days: u64,
) -> VacuumDecision {
    // Rule 1 (HARD): Không bao giờ vacuum khi đang Mesh partition
    // Nguy cơ: node offline có thể replay DELETE như event mới
    if partition_active {
        return VacuumDecision::Defer { reason: "mesh_partition_active" };
    }

    // Rule 2 (HARD): MVC condition PHẢI được thỏa mãn trước
    // Đảm bảo tất cả peers đã acknowledge event DELETE này
    if !mvc.has_seen(&tombstone.hlc_timestamp) {
        return VacuumDecision::Defer { reason: "mvc_not_satisfied" };
    }

    // Rule 3 (SOFT): 7-day TTL chỉ apply SAU khi Rule 1+2 pass
    if age_days >= 7 {
        return VacuumDecision::Vacuum;
    }

    VacuumDecision::Defer { reason: "ttl_not_reached" }
}
// Priority: Rule1 > Rule2 > Rule3
// "7 ngày" là minimum, không phải trigger
```

```

---

## §18 — Hydration Scheduler (Thundering Herd Protection)

```markdown
## 18. [ARCHITECTURE] [IMPLEMENTATION] Hydration Scheduler

> **Bài toán:** >50 clients reconnect đồng thời sau outage →
> concurrent WAL hydration → OOM-Kill VPS.
> Giải pháp: global semaphore + per-tenant rate limit + exponential backoff.

```rust
use governor::{Quota, RateLimiter};
use tokio::sync::Semaphore;
use std::num::NonZeroU32;

pub struct HydrationScheduler {
    /// Global cap: floor(available_ram_mb / 64)
    /// VPS 512MB → 8; VPS 2GB → 32
    global_semaphore: Arc<Semaphore>,
    /// Per-tenant: max 10 hydrations/second với jitter
    tenant_limiters:  DashMap<TenantId, Arc<DefaultDirectRateLimiter>>,
}

impl HydrationScheduler {
    pub fn new(available_ram_mb: u32) -> Self {
        let max = (available_ram_mb / 64).max(4) as usize;
        Self {
            global_semaphore: Arc::new(Semaphore::new(max)),
            tenant_limiters:  DashMap::new(),
        }
    }

    pub async fn acquire(
        &self,
        tenant_id: TenantId,
    ) -> Result<SemaphorePermit, HydrationError> {
        // Step 1: Per-tenant rate limit (10/s + up to 500ms jitter)
        let limiter = self.tenant_limiters
            .entry(tenant_id)
            .or_insert_with(|| {
                Arc::new(RateLimiter::direct(
                    Quota::per_second(NonZeroU32::new(10).unwrap())
                ))
            });
        limiter.until_ready_with_jitter(
            governor::Jitter::up_to(Duration::from_millis(500))
        ).await;

        // Step 2: Global semaphore với hard timeout
        tokio::time::timeout(
            Duration::from_secs(30),
            self.global_semaphore.clone().acquire_owned(),
        )
        .await
        .map_err(|_| HydrationError::QueueTimeout)?
        .map_err(|_| HydrationError::SemaphoreClosed)
    }
}

// Sử dụng — bắt buộc cho mọi client reconnection
pub async fn handle_client_reconnect(
    client_id: ClientId,
    tenant_id:  TenantId,
    scheduler:  Arc<HydrationScheduler>,
) -> Result<()> {
    let _permit = scheduler.acquire(tenant_id).await?;
    // permit giữ đến khi hydration xong — Drop tự động release semaphore

    hydrate_client(client_id).await?;

    metrics().hydration_queue_depth
        .record(scheduler.queue_depth() as u64, &[]);
    Ok(())
}
```

**WAL Checkpoint Isolation** — tránh fsync storm:

```rust
// Checkpoint chạy trong dedicated blocking thread pool
// KHÔNG dùng Tokio async thread — fsync block không được async-cancel
pub async fn checkpoint_wal(db_path: PathBuf) -> Result<()> {
    tokio::task::spawn_blocking(move || {
        let conn = rusqlite::Connection::open(&db_path)?;
        // PASSIVE: không block readers, không force
        conn.execute_batch("PRAGMA wal_checkpoint(PASSIVE);")?;
        Ok::<_, rusqlite::Error>(())
    })
    .await?
}
```

```

---

## §19 — HSM High Availability

```markdown
## 19. [ARCHITECTURE] [SECURITY] HSM High Availability

> **Vấn đề:** Single HSM = single point of failure cho License JWT signing
> và KMS Bootstrap. HSM failure → không issue được license mới → revenue block.

---

### 19.1 [ARCHITECTURE] Dual-HSM Setup

```text
PRIMARY HSM (online)        BACKUP HSM (cold standby)
┌─────────────────────┐     ┌─────────────────────┐
│ HSM FIPS 140-3 L4   │     │ HSM FIPS 140-3 L4   │
│ - License CA key    │     │ - License CA key     │
│ - KMS root key      │     │   (sync từ primary)  │
│ - Shamir shards sig │     │ - Offline, sealed    │
└────────┬────────────┘     └──────────────────────┘
         │ (mTLS, air-gapped network)
         │ Key sync: one-way, daily ceremony
         │ (không tự động — yêu cầu 2/3 C-Level approve)
```

### 19.2 [IMPLEMENTATION] Failover Procedure (Runbook)

**Trigger:** Primary HSM unreachable > 15 phút hoặc hardware failure.

**Bước 1 — Xác nhận failure (≤ 5 phút):**

```bash
$ tera-relay hsm-status
# Output: ❌ PRIMARY unreachable: Connection timeout (900s)
#         ✅ BACKUP sealed, ready for activation
```

**Bước 2 — M-of-N approval (≤ 15 phút):**

- Cần 2/3 C-Level quét QR activation code trên thiết bị vật lý
- QR code nằm trong physical vault của doanh nghiệp
- BLE Physical Presence Verification: 2 thiết bị phải trong vòng 2m

**Bước 3 — Activate Backup (≤ 5 phút):**

```bash
$ tera-relay hsm-failover --backup --quorum-tokens token_a token_b
# Backup HSM becomes active
# License JWT signing continues from backup key
# Audit log entry: Ed25519 signed với timestamp
```

**Bước 4 — Post-recovery:**

- Primary HSM gửi repair, reload keys từ backup
- Không tự động failback — yêu cầu manual approval lần nữa

### 19.3 [IMPLEMENTATION] License JWT Offline Cache

```rust
// Relay cache license JWT locally — không phone-home mỗi request
pub struct LicenseCache {
    jwt:          LicenseJwt,
    cached_at:    Instant,
    /// Từ JWT field offline_ttl_hours
    offline_ttl:  Duration,
}

impl LicenseCache {
    pub fn is_valid(&self) -> bool {
        // Check 1: Cache chưa expire
        if self.cached_at.elapsed() > self.offline_ttl {
            return false;
        }
        // Check 2: JWT valid_until chưa qua (dùng Monotonic Counter, không wall clock)
        let counter = tpm_monotonic_counter();
        counter < self.jwt.valid_until_counter
    }

    pub async fn refresh_if_needed(&mut self, hsm: &HsmClient) -> Result<()> {
        if self.cached_at.elapsed() > self.offline_ttl / 2 {
            // Refresh trước khi expire — eager refresh, không lazy
            let new_jwt = hsm.sign_new_jwt(&self.jwt.claims).await?;
            self.jwt = new_jwt;
            self.cached_at = Instant::now();
        }
        Ok(())
    }
}
```

```

---

## §20 — TeraEdge Device Architecture

```markdown
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

```text
TeraEdge = TeraRelay + Desktop Super Node chạy trên cùng hardware

Chức năng đảm nhận:
├── TeraRelay: Blind routing, presence, push gateway, blob index
├── ONNX inference: all-MiniLM-L6-v2 + DeBERTa-v3-xsmall (8GB RAM đủ)
├── DAG merge Dictator: O(N log N), không ANR risk
├── CRDT Snapshot publisher: publish cho Mobile Leaf Nodes
├── FTS5 full-history indexing: local search
└── Blob storage: local NVMe (option C — NAS S3 API via MinIO)

Không đảm nhận:
├── BLE mesh (không có Bluetooth hardware đủ mạnh)
└── Wi-Fi Direct (infrastructure device, không cần P2P)
```

### 20.3 [IMPLEMENTATION] TeraEdge Install (1 command)

```bash
# Tương tự tera-relay install, thêm flag --edge-mode
curl -sL install.terachat.com/relay | bash --edge-mode

# Installer detect hardware:
# - Nếu RAM ≥ 4GB → enable Super Node role + ONNX
# - Nếu NVMe present → offer local blob storage
# - Nếu power = AC → auto-promote to Super Node

# Kết quả: TeraEdge chạy 3 services:
# 1. tera-relay.service (blind router)
# 2. tera-supernode.service (ONNX + DAG)
# 3. minio.service (nếu chọn local storage)
```

### 20.4 [ARCHITECTURE] Deployment Topology với TeraEdge

```text
FULLY-REMOTE ENTERPRISE:
                                                    
📱📱📱 Mobile workers (remote, qua Internet)
        │
        │ QUIC/WSS (Internet)
        ▼
☁️ TeraRelay VPS (blind router only, $6/month)
        │
        │ QUIC/WSS (LAN hoặc VPN)
        ▼
🟦 TeraEdge Mini (on-premise, office/server room)
        ├── ONNX inference host
        ├── DAG merge Dictator
        ├── Snapshot publisher
        └── Blob storage (local NVMe)

FIELD OPERATIONS (không có VPS):
        
📱📱 Field devices (BLE/Wi-Fi Direct mesh)
        │
        │ Wi-Fi (local network)
        ▼
🟦 TeraEdge Nano (field kit, battery-powered option)
        ├── TeraRelay (local routing — không cần Internet)
        ├── ONNX inference
        └── Blob storage (SD card / USB)

Khi TeraEdge Nano có Internet:
        └── Sync với TeraRelay VPS (federation mode)
```

### 20.5 [IMPLEMENTATION] TeraEdge — Super Node Auto-Promotion

```rust
// TeraEdge tự động đăng ký là Super Node khi khởi động
impl TeraEdge {
    pub async fn startup(&self) -> Result<()> {
        // Announce Super Node availability qua Relay
        self.relay_client
            .announce_super_node(SuperNodeCapabilities {
                onnx_models: vec![OnnxModel::AllMiniLm, OnnxModel::DeBertaXsmall],
                ram_available_mb: self.measure_available_ram(),
                dag_capacity_events: u64::MAX, // Edge có NVMe, không giới hạn
                power_source: PowerSource::AcPowered,
                device_class: DeviceClass::TeraEdge,
            })
            .await?;

        // Start ONNX inference server (lắng nghe offload requests từ Mobile)
        self.onnx_server.start().await?;

        // Start DAG merge service
        self.dag_dictator.start().await?;

        info!(event = "TeraEdgeStarted",
              ram_mb = self.measure_available_ram(),
              onnx_ready = true);
        Ok(())
    }
}
```

```

---

# PHẦN 2 — `Feature_Spec.md` — Các Section Mới & Cập Nhật

---

## CHANGELOG (bổ sung)

```markdown
| v0.4.0 | 2026-03-19 | Add OBSERVE-01/02 client observability; PLATFORM-17/18/19/20;
|         |            | INFRA-01/02/03/04/05/06; CICD-01/02; Update PLATFORM-14→17 |
```

---

## OBSERVE-01 — Client-Side Observability Integration

```markdown
## OBSERVE-01: [IMPLEMENTATION] Client-Side Observability

> Clients không expose Prometheus scrape endpoint.
> Thay vào đó: push aggregate metrics qua OTLP HTTP khi online,
> buffer locally khi offline.

---

### OBSERVE-01.1 [IMPLEMENTATION] Mobile Metrics Push

📱 **OTLP Push khi online:**

```rust
pub struct MobileMetricsPusher {
    buffer_db:    SqliteConnection,  // metrics_buffer.db
    otel_endpoint: Url,              // https://relay.company.io:4318/v1/metrics
    push_interval: Duration,         // 60s online, 300s nếu battery < 20%
}

impl MobileMetricsPusher {
    pub async fn push_periodic(&self) -> Result<()> {
        let metrics = self.collect_device_metrics();

        // Thử push online
        match self.push_otlp(&metrics).await {
            Ok(_) => {
                self.flush_buffer().await?;  // Flush offline buffer nếu có
            },
            Err(_) => {
                // Offline: buffer locally
                self.buffer_db.insert_metric(&metrics)?;
            }
        }
        Ok(())
    }

    fn collect_device_metrics(&self) -> DeviceMetrics {
        DeviceMetrics {
            wal_size_bytes:         measure_wal_size(),
            mesh_node_count:        count_mesh_nodes(),
            push_success_rate_1h:   calc_push_success_rate(),
            dag_merge_last_ms:      last_dag_merge_duration(),
            active_wasm_instances:  count_wasm_instances(),
            battery_pct:            get_battery_level(),
            thermal_state:          get_thermal_state() as u32,
            onnx_offload_rate:      calc_onnx_offload_ratio(),
            // KHÔNG include: message content, user_id, session_id
        }
    }
}
```

📱 **Battery-aware push interval:**

| Battery | Thermal | Push interval |
|---------|---------|---------------|
| > 20% | Normal | 60s |
| > 20% | Hot | 120s |
| ≤ 20% | Any | 300s |
| ≤ 10% | Any | Suspend push |

📱 **Offline buffer limit:** tối đa 24h metrics, sau đó GC oldest entries.
Buffer size: ~500KB/24h cho 1 device.

---

### OBSERVE-01.2 [IMPLEMENTATION] Desktop Metrics

💻🖥️ Desktop expose `/metrics` endpoint localhost:9092 khi IT Admin
muốn scrape local. Đồng thời push OTLP giống Mobile.

```rust
// Desktop: cả hai mode chạy song song
impl DesktopMetricsService {
    pub async fn start(&self) -> Result<()> {
        // Mode 1: Prometheus scrape (nếu IT Admin có local stack)
        let prom_handle = prometheus_exporter::start("0.0.0.0:9092")?;

        // Mode 2: OTLP push về VPS (default)
        let pusher = OtlpPusher::new(&self.relay_otlp_endpoint);
        tokio::spawn(async move {
            loop {
                pusher.push_metrics().await.ok();
                tokio::time::sleep(Duration::from_secs(60)).await;
            }
        });

        // Mode 3: Super Node thêm DAG/ONNX metrics
        if self.is_super_node() {
            self.start_super_node_metrics().await?;
        }

        Ok(())
    }
}
```

---

### OBSERVE-01.3 [IMPLEMENTATION] FFI Buffer Release Telemetry

📱💻 Khi `TeraSecureBuffer` bị release bởi GC Finalizer thay vì
explicit `releaseNow()`, PHẢI:

1. Tăng counter `ffi_gc_release_total`
2. Log WARN event `FfiBufferGcRelease`
3. Alert trigger khi > 0 in 1h → notify mobile team Slack

Mục đích: detect developer bug, không block functionality.

```

---

## OBSERVE-02 — DAG Merge Progress UI

```markdown
## OBSERVE-02: [IMPLEMENTATION] DAG Merge Progress UI

> Khi merge > 500 events, user PHẢI thấy progress — không black screen.

---

### OBSERVE-02.1 [IMPLEMENTATION] IPC Signal Spec

```rust
// Rust Core emit via IPC khi merge > 500 events
pub enum DagMergeProgress {
    Started   { total: u32 },
    Progress  { done: u32, total: u32, elapsed_ms: u64 },
    Completed { total: u32, duration_ms: u64 },
    FallbackToSnapshot { reason: String },
}
```

### OBSERVE-02.2 [UI] Rendering Rules

| Platform | Merge size | UI behavior |
|----------|-----------|-------------|
| 📱 Mobile | > 500 events | Linear progress bar top of screen + text "Đang đồng bộ X%" |
| 📱 Mobile | > 3000 events | "Yêu cầu snapshot từ thiết bị khác..." + spinner |
| 💻🖥️ Desktop | Any | Status bar indicator, không block user |
| 📱💻🖥️ Any | Completed | Progress dismisses với 500ms fade |

User KHÔNG bị block khỏi UI trong khi merge. Message mới vẫn hiển thị
(có thể chưa sorted đúng vị trí — re-sort sau khi merge xong).

```

---

## PLATFORM-17 — Dart FFI Contract (Mandatory)

```markdown
## PLATFORM-17: [IMPLEMENTATION] Dart FFI Memory Contract

> **Supersedes PLATFORM-14.** Đây là contract bắt buộc — vi phạm = CI fail.

---

### PLATFORM-17.1 Quy tắc bắt buộc

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

### PLATFORM-17.2 Implementation

```dart
class TeraSecureBuffer {
  final int _tokenId;
  bool _released = false;

  /// PRIMARY pattern — bắt buộc dùng cái này
  T useInTransaction<T>(T Function(Pointer<Uint8> ptr, int len) fn) {
    if (_released) throw StateError('TeraSecureBuffer already released');
    try {
      return fn(_toPointer(), _length);
    } finally {
      _releaseInternal(via: ReleaseMethod.explicit);
    }
  }

  void releaseNow() => _releaseInternal(via: ReleaseMethod.explicit);

  void _releaseInternal({required ReleaseMethod via}) {
    if (_released) return;
    _released = true;
    if (via == ReleaseMethod.gcFinalizer) {
      // Bug detector — developer forgot useInTransaction
      _reportGcRelease();
    }
    TeraFFI.tera_buf_release(_tokenId);
  }

  void _reportGcRelease() {
    TeraMetrics.ffiGcReleaseCounter.increment();
    debugPrint('[WARN] TeraSecureBuffer $_tokenId released by GC. '
               'Use useInTransaction() instead.');
  }

  static final _finalizer = Finalizer<int>((tokenId) {
    // Safety net only — should never fire in correct code
    TeraFFI.tera_buf_release_warn(tokenId);
  });

  TeraSecureBuffer(this._tokenId, this._length) {
    _finalizer.attach(this, _tokenId, detach: this);
  }

  final int _length;
  Pointer<Uint8> _toPointer() => TeraFFI.tera_buf_ptr(_tokenId);
}

enum ReleaseMethod { explicit, gcFinalizer }
```

---

### PLATFORM-17.3 CI Lint Rule

```yaml
# analysis_options.yaml
analyzer:
  plugins:
    - terachat_lint
custom_lint:
  rules:
    - name: tera_buffer_must_use_transaction
      message: "TeraSecureBuffer must be used via useInTransaction()"
      severity: error
    - name: tera_buffer_pointer_outside_transaction
      message: "Direct .toPointer() call outside useInTransaction() is forbidden"
      severity: error
```

Build fail nếu có vi phạm. Không exception.

```

---

## PLATFORM-18 — ONNX Model Integrity Protocol

```markdown
## PLATFORM-18: [SECURITY] [IMPLEMENTATION] ONNX Model Integrity

> **Áp dụng cho:** §5.27 Edge ONNX, §8.19 EICB, §5.33 EDES, §9.3 Dual-Mask.
> Mọi ONNX model load PHẢI qua `OnnxModelLoader.load_verified()`.

---

### PLATFORM-18.1 Verification Flow

```rust
pub struct OnnxModelLoader {
    /// Embedded tại build time — không runtime lookup
    expected_hash:   [u8; 32],  // BLAKE3 của model bytes
    signing_pubkey:  ed25519_dalek::VerifyingKey,
    cdn_spki_pin:    [u8; 32],  // SHA-256 của CDN cert SPKI
}

impl OnnxModelLoader {
    pub fn load_verified(&self, path: &Path) -> Result<OrtSession> {
        let bytes = std::fs::read(path)?;

        // Step 1: BLAKE3 integrity
        let hash = blake3::hash(&bytes);
        if hash.as_bytes() != &self.expected_hash {
            std::fs::remove_file(path).ok(); // Quarantine
            metrics().onnx_model_invalid.increment(1);
            return Err(ModelError::HashMismatch);
        }

        // Step 2: Ed25519 signature
        let sig_bytes = std::fs::read(path.with_extension("sig"))?;
        let sig = ed25519_dalek::Signature::from_bytes(
            &sig_bytes.try_into().map_err(|_| ModelError::SigInvalid)?
        );
        self.signing_pubkey.verify_strict(&bytes, &sig)
            .map_err(|_| ModelError::SigVerifyFailed)?;

        // Step 3: Load ONNX
        let session = ort::SessionBuilder::new()?
            .with_optimization_level(ort::GraphOptimizationLevel::All)?
            .commit_from_memory(&bytes)?;

        drop(bytes); // ZeroizeOnDrop nếu wrapped
        Ok(session)
    }
}
```

---

### PLATFORM-18.2 Build-Time Hash Embedding

```rust
// build.rs — chạy tự động khi build
fn main() {
    let models = [
        ("all-minilm-l6-v2", "models/all-minilm-l6-v2.onnx"),
        ("deberta-v3-xsmall", "models/deberta-v3-xsmall.onnx"),
        ("ner-xsmall",        "models/ner-xsmall.onnx"),
    ];

    for (name, path) in &models {
        if std::path::Path::new(path).exists() {
            let bytes = std::fs::read(path).unwrap();
            let hash = blake3::hash(&bytes);
            println!("cargo:rustc-env=MODEL_HASH_{}={}",
                name.to_uppercase().replace('-', "_"),
                hex::encode(hash.as_bytes()));
        }
    }
}

// Trong source:
const MODEL_HASH_ALL_MINILM_L6_V2: &str =
    env!("MODEL_HASH_ALL_MINILM_L6_V2");
```

---

### PLATFORM-18.3 Fallback khi Model Invalid

| Scenario | Fallback behavior |
|----------|-------------------|
| Hash mismatch | Quarantine, log WARN, use keyword-only scan |
| Sig verify fail | Quarantine, log WARN, use keyword-only scan |
| Model not found | Download từ CDN (với SPKI pin + DoH) |
| CDN unreachable | Use TinyBERT (bundled, 6MB, no sig needed) |

**Keyword-only fallback** = Aho-Corasick pattern matching (§5.33 EDES)
vẫn hoạt động mà không cần ONNX. DLP không bị tắt hoàn toàn.

```

---

## PLATFORM-19 — TeraEdge Client Behavior

```markdown
## PLATFORM-19: [IMPLEMENTATION] TeraEdge Client Integration

> Mobile tự động detect TeraEdge trên LAN và ưu tiên dùng
> thay vì ONNX inference local hoặc VPS relay.

---

### PLATFORM-19.1 Super Node Discovery Priority

📱 Khi Mobile cần ONNX inference, thứ tự ưu tiên:

```rust
pub enum ComputeTarget {
    TeraEdgeLan(TeraEdgeNode),      // Priority 1: TeraEdge trên LAN (< 5ms)
    DesktopSuperNodeLan(Desktop),   // Priority 2: Desktop cùng LAN (< 10ms)
    TeraEdgeViaRelay(TeraEdgeNode), // Priority 3: TeraEdge qua VPS (< 60ms)
    DesktopViaRelay(Desktop),       // Priority 4: Desktop qua VPS (< 80ms)
    LocalTinyBert,                  // Fallback: TinyBERT bundled (< 50ms, lower quality)
}

impl MobileOnnxClient {
    pub async fn resolve_compute_target(&self) -> ComputeTarget {
        // mDNS discovery trong LAN
        if let Some(edge) = self.discover_tera_edge_lan().await {
            return ComputeTarget::TeraEdgeLan(edge);
        }
        if let Some(desktop) = self.discover_desktop_lan().await {
            return ComputeTarget::DesktopSuperNodeLan(desktop);
        }
        // Via relay (nếu online)
        if let Some(edge) = self.relay_client.get_online_edge().await.ok().flatten() {
            return ComputeTarget::TeraEdgeViaRelay(edge);
        }
        // Fallback
        ComputeTarget::LocalTinyBert
    }
}
```

---

### PLATFORM-19.2 Mobile Storage Profile với TeraEdge

Khi TeraEdge available, Mobile có thể giảm local storage thêm:

| Component | Không có TeraEdge | Có TeraEdge |
|-----------|------------------|-------------|
| hot_dag.db | 25MB (delta 7 ngày) | 10MB (delta 3 ngày) |
| ONNX model | TinyBERT 6MB | Không cần (offload) |
| FTS5 index | 7-day window | 3-day window (TeraEdge giữ full) |
| File cache | VFS stub 5KB | VFS stub 5KB (không đổi) |

📱 **Snapshot sync** từ TeraEdge thay vì Desktop:
TeraEdge publish CRDT snapshot mỗi 500 events (giống Desktop Super Node).
Mobile nhận snapshot O(1) — không cần full DAG sync.

```

---

## INFRA-04 — Canary Deployment

```markdown
## INFRA-04: [IMPLEMENTATION] Canary Deployment Strategy

> **Bài toán:** Không có staged rollout = bad release ảnh hưởng 100% customers.
> Giải pháp: DNS-based traffic splitting + feature flag per-tenant.

---

### INFRA-04.1 Traffic Splitting via DNS

```bash
# TeraRelay hỗ trợ 2 versions chạy song song
# DNS CNAME routing: 5% → canary, 95% → stable

# tera-relay canary deploy
tera-relay deploy --version 0.4.0 --canary-percent 5
# → Start v0.4.0 on port 8443
# → Update DNS weight: relay.company.io 95% → :443, 5% → :8443
# → Monitor SLO-01 and SLO-05 for 30 minutes
# → If degraded: auto-rollback
# → If healthy: promote to 100%
```

---

### INFRA-04.2 Automated Rollback

```rust
pub struct CanaryMonitor {
    stable_version:   String,
    canary_version:   String,
    rollback_trigger: RollbackTrigger,
}

pub struct RollbackTrigger {
    /// Canary error rate vượt 2× stable error rate
    error_rate_multiplier: f64,         // default: 2.0
    /// Canary P99 latency vượt 150% của stable
    latency_multiplier: f64,            // default: 1.5
    /// Observation window trước khi rollback
    observation_window: Duration,       // default: 5 minutes
}

impl CanaryMonitor {
    pub async fn watch_and_rollback(&self) -> Result<()> {
        loop {
            let stable = self.query_metrics(&self.stable_version).await?;
            let canary = self.query_metrics(&self.canary_version).await?;

            let should_rollback =
                canary.error_rate > stable.error_rate * self.rollback_trigger.error_rate_multiplier
                || canary.p99_latency > stable.p99_latency * self.rollback_trigger.latency_multiplier;

            if should_rollback {
                warn!(event = "CanaryRollback",
                      canary_error = canary.error_rate,
                      stable_error = stable.error_rate);

                self.execute_rollback().await?;
                alert_oncall("Canary rolled back automatically").await;
                break;
            }

            tokio::time::sleep(Duration::from_secs(60)).await;
        }
        Ok(())
    }
}
```

---

### INFRA-04.3 Rollout Schedule

| Phase | Percent | Duration | Rollback condition |
|-------|---------|----------|-------------------|
| Canary | 1% | 30 min | Any error rate spike |
| Early | 10% | 2 hours | Error rate > 2× baseline |
| Majority | 50% | 4 hours | Error rate > 1.5× baseline |
| Full | 100% | — | P99 latency > 150% baseline |

`tera-relay deploy --auto` thực hiện toàn bộ schedule tự động.
Admin nhận Slack notification mỗi phase transition.

```

---

## INFRA-05 — SBOM và Reproducible Builds

```markdown
## INFRA-05: [IMPLEMENTATION] SBOM & Reproducible Builds

> Enterprise/Gov customers yêu cầu SBOM cho compliance audit.
> Reproducible builds cần thiết cho binary transparency claims.

---

### INFRA-05.1 SBOM Generation

```yaml
# .github/workflows/release.yaml — thêm step sau build

- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    path: ./target/release/tera-relay
    format: spdx-json
    output-file: tera-relay-${{ github.ref_name }}.sbom.json

- name: Sign SBOM
  run: |
    # Ed25519 sign SBOM với TeraChat Release Key
    cosign sign-blob \
      --key env://TERACHAT_RELEASE_KEY \
      --output-signature tera-relay-${{ github.ref_name }}.sbom.sig \
      tera-relay-${{ github.ref_name }}.sbom.json

- name: Publish SBOM
  # Upload to releases.terachat.com/sbom/
  # Customers verify: cosign verify-blob --key terachat-release.pub ...
```

---

### INFRA-05.2 Reproducible Builds

```toml
# Cargo.toml
[profile.release]
opt-level     = "z"
lto           = true
codegen-units = 1
panic         = "abort"
strip         = "symbols"
```

```bash
# build-reproducible.sh — CI script
#!/bin/bash
# SOURCE_DATE_EPOCH: tất cả timestamp trong binary = commit timestamp
export SOURCE_DATE_EPOCH=$(git log -1 --format=%ct)
export RUSTFLAGS="-C link-arg=-Wl,--build-id=none"

# Loại bỏ path trong binary (khác nhau giữa các máy)
export CARGO_HOME=/tmp/cargo-home-fixed
cargo build --release --locked

# Verify reproducibility
sha256sum target/release/tera-relay > build-hash.txt
echo "Build hash: $(cat build-hash.txt)"
```

---

### INFRA-05.3 Binary Transparency Log

☁️ Mọi release binary được đăng ký vào append-only transparency log:

```rust
// Khi TeraRelay khởi động, verify binary đã được logged
pub async fn verify_binary_transparency() -> Result<()> {
    let binary_hash = blake3_self_hash();

    // Query transparency log (public, append-only)
    let entry = transparency_log_client
        .lookup(&binary_hash)
        .await?;

    if entry.is_none() {
        // Binary không có trong log = không được deploy
        error!(event = "BinaryTransparencyFail",
               hash = hex::encode(&binary_hash));
        std::process::exit(1);
    }

    info!(event = "BinaryTransparencyVerified",
          hash = hex::encode(&binary_hash[..8]));
    Ok(())
}
```

```

---

## CICD-01 — CI Pipeline Requirements

```markdown
## CICD-01: [IMPLEMENTATION] CI/CD Pipeline Requirements

> Danh sách gates bắt buộc — tất cả phải pass trước khi merge vào main.

---

### CICD-01.1 Required Gates

```yaml
# .github/workflows/ci.yaml

jobs:
  security-lint:
    steps:
      # Gate 1: FFI Buffer contract
      - run: dart analyze --fatal-infos
        # Fail nếu có TeraSecureBuffer vi phạm PLATFORM-17

      # Gate 2: Forbidden log fields
      - run: |
          grep -r "user_id\|message_content\|plaintext_" \
            src/ --include="*.rs" | grep "log!\|info!\|warn!\|error!" \
            && echo "FAIL: Forbidden field in log" && exit 1 \
            || echo "OK: No forbidden log fields"

      # Gate 3: ZeroizeOnDrop compliance
      - run: |
          # Mọi struct có field _key, _secret, _plaintext phải derive ZeroizeOnDrop
          cargo check 2>&1 | grep "does not implement ZeroizeOnDrop" \
            && exit 1 || exit 0

  wasm-parity:
    steps:
      # Gate 4: wasm3 vs wasmtime output identical
      - run: |
          cargo test --features wasm3-tests -- wasm_parity
          # Fail nếu semantic output khác nhau (latency delta OK)

  onnx-integrity:
    steps:
      # Gate 5: Model hash cập nhật nếu model thay đổi
      - run: |
          cargo build 2>&1 | grep "MODEL_HASH" > /dev/null \
            || (echo "FAIL: build.rs model hash not embedded" && exit 1)

  schema-version:
    steps:
      # Gate 6: Schema version bump nếu có migration
      - run: |
          if git diff HEAD~1 -- src/storage/migrations/ | grep "^+" | grep -q "fn up"; then
            cargo test -- schema_version_incremented
          fi

  chaos-tests:
    # Chạy weekly trên staging (không phải mỗi PR)
    schedule: "0 2 * * 1"  # Monday 2AM
    steps:
      - run: cargo test --features chaos-tests -- sc_01 sc_02 sc_03 sc_04 sc_05 sc_06 sc_07
```

---

### CICD-01.2 Code Signing Pipeline

```yaml
  sign-and-publish:
    needs: [security-lint, wasm-parity, onnx-integrity, schema-version]
    if: github.ref_type == 'tag'
    steps:
      # iOS: fastlane match + Apple Notarization
      - run: fastlane ios release

      # macOS: Developer ID + notarytool
      - run: |
          codesign -s "Developer ID Application: TeraChat Inc" \
            --hardened-runtime --timestamp \
            target/release/tera-relay-macos
          xcrun notarytool submit tera-relay-macos.dmg \
            --apple-id $APPLE_ID --team-id $TEAM_ID --wait

      # Windows: EV Code Signing via DigiCert KeyLocker (Cloud HSM)
      - run: |
          smctl sign --keypair-alias terachat-ev \
            --input target/release/tera-relay.exe

      # Linux: GPG sign .deb + .rpm
      - run: |
          dpkg-sig --sign builder tera-relay_*.deb
          rpm --addsign tera-relay-*.rpm

      # AppImage: cosign
      - run: |
          cosign sign-blob --key env://COSIGN_KEY \
            --output-signature tera-relay.AppImage.sig \
            tera-relay.AppImage

      # SBOM generation (từ INFRA-05)
      - uses: anchore/sbom-action@v0
```

```

---

## INFRA-06 — Chaos Engineering Implementation

```markdown
## INFRA-06: [TEST] [IMPLEMENTATION] Automated Chaos Engineering

> TestMatrix.md định nghĩa 28 scenarios. File này spec implementation.
> Mục tiêu: automated CI test suite, không chỉ manual runbook.

---

### INFRA-06.1 Chaos Test Framework

```rust
// tests/chaos/framework.rs

pub struct ChaosScenario {
    pub id:          &'static str,   // SC-01 .. SC-28
    pub conditions:  Vec<Condition>,
    pub expected:    ExpectedBehavior,
    pub timeout:     Duration,
}

pub enum Condition {
    IosAwdlOff,
    TurnFailover,
    JetsamKillNse,
    DesktopOffline,
    EmdpActive { ttl_minutes: u32 },
    XpcWorkerOom,
    SmartApprovalPending,
    BatteryLow { pct: u8 },
    MeshActive,
    WhisperLoading,
    AppArmorDenyMemfd,
    LicenseExpired,
    ThunderingHerd { client_count: u32 },
    ConcurrentEpochRotation { islands: u32 },
    OnnxModelCorrupted,
    WalFsyncStorm { concurrent: u32 },
    PoisonedModel { model: OnnxModel },
    BloomFilterFalsePositive,
    MaliciousDeltaState,
    SplitBrainTwoIslands,
    EmdpDesktopReconnect { relay_messages: u32 },
}

// Runner
pub struct ChaosRunner {
    env: TestEnvironment,
}

impl ChaosRunner {
    pub async fn run(&self, scenario: &ChaosScenario) -> ChaosResult {
        // 1. Apply conditions
        for cond in &scenario.conditions {
            self.apply_condition(cond).await;
        }

        // 2. Wait and observe
        let result = tokio::time::timeout(
            scenario.timeout,
            self.observe_behavior(),
        ).await;

        // 3. Cleanup
        self.reset_environment().await;

        // 4. Verify expected behavior
        self.verify(&scenario.expected, result)
    }
}
```

---

### INFRA-06.2 Tier 1 — Infrastructure (SC-01 to SC-07)

```rust
// Các scenarios đã có trong TestMatrix.md — cần automated implementation

#[tokio::test]
#[cfg(feature = "chaos-tests")]
async fn sc_01_ios_awdl_off_turn_failover_crdt_merge() {
    let env = TestEnvironment::new().await;
    let runner = ChaosRunner::new(env);

    let result = runner.run(&ChaosScenario {
        id: "SC-01",
        conditions: vec![
            Condition::IosAwdlOff,
            Condition::TurnFailover,
        ],
        expected: ExpectedBehavior {
            ui_state: Some(UiState::TierChangedWarning),
            ble_fallback: true,
            no_crash: true,
            crdt_queue_not_lost: true,
        },
        timeout: Duration::from_secs(120),
    }).await;

    assert!(result.passed, "SC-01 failed: {}", result.failure_reason.unwrap_or_default());
}

#[tokio::test]
#[cfg(feature = "chaos-tests")]
async fn sc_02_jetsam_kill_nse_mid_wal() {
    // Simulate iOS kill NSE at 50% WAL write
    let env = TestEnvironment::new().await;
    env.inject_jetsam_at_wal_progress(0.5).await;

    let result = env.run_scenario("SC-02").await;
    assert!(result.wal_rolled_back);
    assert!(result.dag_self_healed);
    assert!(result.no_data_loss);
}
```

---

### INFRA-06.3 Tier 2 — Concurrency (SC-08 to SC-14)

```rust
#[tokio::test]
#[cfg(feature = "chaos-tests")]
async fn sc_08_thundering_herd_100_clients() {
    let env = TestEnvironment::with_vps_512mb().await;

    // Simulate 100 clients reconnecting simultaneously
    let reconnect_tasks: Vec<_> = (0..100)
        .map(|i| {
            let env = env.clone();
            tokio::spawn(async move {
                env.client(i).simulate_reconnect().await
            })
        })
        .collect();

    let results = futures::future::join_all(reconnect_tasks).await;
    let all_success = results.iter().all(|r| r.as_ref().map(|r| r.success).unwrap_or(false));

    // VPS must NOT OOM-kill
    assert!(!env.vps_oom_killed(), "VPS OOM-killed during thundering herd");
    // All clients eventually connected (may take up to 30s)
    assert!(all_success, "Some clients failed to reconnect");
    // Queue depth stayed bounded
    assert!(env.max_hydration_queue_depth() <= 50);
}

#[tokio::test]
#[cfg(feature = "chaos-tests")]
async fn sc_09_concurrent_epoch_rotation_two_islands() {
    let env = TestEnvironment::new().await;

    // Partition network into 2 islands
    env.create_mesh_partition(2).await;

    // Both islands rotate epoch independently
    env.island(0).rotate_mls_epoch("alice_left").await;
    env.island(1).rotate_mls_epoch("bob_left").await;

    // Heal partition
    env.heal_partition().await;

    // Verify split-brain detected and resolved
    let metrics = env.collect_metrics().await;
    assert!(metrics.mls_split_brain_detected > 0,
            "Split-brain not detected");
    assert_eq!(metrics.mls_decrypt_errors_post_reconciliation, 0,
               "Still getting decrypt errors after reconciliation");
}

#[tokio::test]
#[cfg(feature = "chaos-tests")]
async fn sc_13_onnx_model_corrupted() {
    let env = TestEnvironment::new().await;

    // Corrupt model file
    env.corrupt_onnx_model(OnnxModel::AllMiniLm).await;

    // Trigger ONNX load
    let result = env.trigger_semantic_search("test query").await;

    // Should fallback to keyword-only, not crash
    assert!(result.used_fallback, "Should have fallen back to keyword search");
    assert!(!result.crashed, "System should not crash on model corruption");
    assert!(env.metrics().onnx_model_invalid_total > 0);
}
```

---

### INFRA-06.4 Running Chaos Tests

```bash
# Chạy full suite trên staging (weekly)
cargo test --features chaos-tests -- sc_ --test-threads=1

# Chạy specific tier
cargo test --features chaos-tests -- sc_0  # Tier 1 only
cargo test --features chaos-tests -- sc_1  # Tier 2 only
cargo test --features chaos-tests -- sc_2  # Tier 3 only (security)

# Chạy pre-Gov-Go-Live suite
cargo test --features chaos-tests -- \
  sc_01 sc_02 sc_03 sc_04 sc_05 sc_06 sc_07 \
  sc_08 sc_09 sc_10 sc_11 sc_12 sc_13 sc_14 \
  -- --nocapture
```

```

---
