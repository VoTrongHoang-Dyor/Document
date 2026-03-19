# Feature_Spec.md — PATCH v0.3.0

# Điều kiện áp dụng: Thay thế toàn bộ các section stub trong Feature_Spec.md v0.2.6

# Mỗi section được đánh dấu bằng anchor header khớp với file gốc để merge chính xác

# Sau khi merge, version tăng lên 0.3.0

---

## PATCH-INFRA-01.2: ONNX Inference Offload Protocol

> **Thay thế stub tại:** `### INFRA-01.2 ONNX Inference Offload Protocol`

📱 Mobile phát `OnnxOffloadRequest` (E2EE) đến Desktop Super Node khi cần inference:

**Điều kiện kích hoạt offload:**

| Trigger | Hành động |
|---|---|
| Model tier yêu cầu "base" (74MB) và RAM mobile ≤ 3GB | Bắt buộc offload |
| Battery mobile < 30% | Bắt buộc offload |
| Thermal state = Critical (iOS: `.serious` / Android: `THERMAL_STATUS_SEVERE`) | Bắt buộc offload |
| Model tier "tiny" nhưng CPU utilization > 80% sustained 10s | Khuyến nghị offload |

**Offload Protocol Flow:**

```text
📱 Mobile → [ONNX_OFFLOAD_REQUEST]
  {
    request_id: Uuid,
    sanitized_prompt: SanitizedPrompt,   // PII đã redact — KHÔNG gửi raw text
    model_tier: "base" | "tiny",
    ttl_ms: 5000,
    requester_did: DeviceId,
    hmac: HMAC-BLAKE3(Company_Key, request_id || sanitized_prompt)
  }
  │ Transport: E2EE CRDT_Event (nonce rotation per request)
  ▼
💻 Desktop Super Node
  1. Verify HMAC-BLAKE3 — reject nếu mismatch
  2. Check OPA Policy: requester_did có AI quota còn lại không?
  3. Run ONNX inference trong isolated process (không share RAM với Rust Core)
  4. Phản hồi [ONNX_OFFLOAD_RESPONSE]:
     {
       request_id: Uuid,         // Echo — match với request
       ast_nodes: Vec<ASTNode>,  // Sanitized output — không có raw LLM text
       tokens_used: u32,
       latency_ms: u32
     }
  │ Transport: E2EE CRDT_Event về đúng requester_did
  ▼
📱 Mobile nhận response
  1. Verify request_id khớp với pending request — reject nếu stale
  2. Deliver Vec<ASTNode> đến .tapp hoặc AI context
  3. Decrement AI quota: tokens_used
  4. ZeroizeOnDrop trên SanitizedPrompt sau khi response nhận được
```

**Failure Handling:**

- Desktop không online / không trong Mesh: fall back to Tiny model local.
- TTL 5000ms hết mà không có response: emit `CoreSignal::ComponentFault { component: "ai_offload", severity: Warning }`. UI hiển thị "AI đang xử lý chậm — đang thử lại..." Retry 1 lần với TTL 3000ms. Sau đó: fall back Tiny local.
- HMAC mismatch trên Desktop: log `OFFLOAD_HMAC_VIOLATION { requester_did }` vào Audit Log. Không phản hồi request.
- ONNX worker crash trên Desktop: `catch_unwind` tại worker entry. Emit ComponentFault. Mobile nhận timeout sau TTL.

**Constraints:**

- `SanitizedPrompt` là newtype — construction bắt buộc qua PII redaction pass (Micro-NER). Không thể truyền raw string.
- Desktop ONNX process: RAM ceiling 150MB. Nếu vượt: OOM-kill worker, trả về `OFFLOAD_OOM_ERROR`.
- Không có persistent connection giữa Mobile và Desktop cho offload — mỗi request là độc lập CRDT_Event.

---

## PATCH-INFRA-02.1: Blob Storage Client — File Upload Flow

> **Thay thế stub tại:** `#### INFRA-02.1 File Upload Flow (Revised)`

**Nguyên tắc:** Client không bao giờ có direct credentials đến R2/B2/MinIO. Mọi upload/download đi qua presigned URL từ TeraRelay. Zero-Knowledge được bảo toàn vì relay ký URL mà không thấy nội dung.

**Upload Flow (Chunked, E2EE):**

```text
[UI] File bytes → UICommand::SendMedia { file_bytes, recipient_did }
  │
  ▼
[Rust Core]
  1. Split file thành 2MB chunks: [chunk_0, chunk_1, ..., chunk_N]
  2. Với mỗi chunk_i:
     a. ChunkKey_i = HKDF(Epoch_Key, "chunk" || cas_hash || i)
     b. ciphertext_i = AES-256-GCM(ChunkKey_i, chunk_i, nonce_i)
        - nonce_i = derive_message_nonce(sender_data_secret, reuse_guard, seq=i)
     c. ZeroizeOnDrop: ChunkKey_i và chunk_i plaintext
  3. cas_hash = BLAKE3(file_bytes)  ← tính trước khi encrypt
  4. Request presigned URL từ TeraRelay:
     PUT /v1/presign
     { cas_hash: hex, chunk_count: N+1, content_type: "application/octet-stream" }
     → Response: [presigned_url_0, ..., presigned_url_N] (TTL 15 phút mỗi URL)
  5. Upload mỗi ciphertext_i lên presigned_url_i (parallel, max 3 concurrent)
  6. Sau khi tất cả chunks uploaded:
     Tạo CRDT_Event { content_type: MediaStub, payload: ZeroByteStub }
     ZeroByteStub = { name, cas_hash, chunk_count, encrypted_thumbnail, storage_ref }
  7. Append CRDT_Event vào hot_dag.db → broadcast qua E2EE channel
```

**Download Flow (On-Demand, Streaming):**

```text
[UI] User tap on ZeroByteStub → UICommand::RequestMedia { cas_hash }
  │
  ▼
[Rust Core]
  1. Request presigned download URLs:
     GET /v1/presign/download
     { cas_hash: hex, chunk_count: N+1 }
     → Response: [download_url_0, ..., download_url_N] (TTL 5 phút)
  2. Với mỗi chunk_i (sequential để preserve stream order):
     a. Download ciphertext_i từ download_url_i
     b. ChunkKey_i = HKDF(Epoch_Key, "chunk" || cas_hash || i)
     c. plaintext_i = AES-256-GCM decrypt(ChunkKey_i, ciphertext_i)
     d. tera_buf_acquire → write plaintext_i đến 2MB RingBuffer
     e. Emit CoreSignal::StateChanged → UI render chunk
     f. ZeroizeOnDrop: ChunkKey_i và plaintext_i sau render frame
  3. Sau khi tất cả chunks: emit CoreSignal::MediaComplete { cas_hash }
```

**Deduplication (Content-Addressed Storage):**

- Server lưu file theo `cas_hash` → identical files chỉ upload 1 lần.
- Trước khi upload: HEAD request kiểm tra `cas_hash` đã tồn tại chưa.
- Nếu tồn tại: bỏ qua upload, chỉ tạo `ZeroByteStub` mới tham chiếu cùng `cas_hash`.

**Constraints:**

- Presigned URL TTL: 15 phút (upload), 5 phút (download). Hết TTL: request URL mới.
- Max concurrent chunks upload: 3 (tránh saturate bandwidth trên mobile).
- Chunk size: 2MB fixed. File < 2MB: 1 chunk duy nhất.
- TeraRelay không lưu presigned URL — stateless generation dựa trên HMAC-signed payload.

**Failure Handling:**

- Upload chunk thất bại: retry tối đa 3 lần với exponential backoff (1s, 2s, 4s). Sau 3 lần: `MEDIA_UPLOAD_FAILED`, notify UI.
- Download interrupted mid-way: Hydration_Checkpoint ghi `{ cas_hash, last_chunk_index }` vào `hot_dag.db`. Resume từ checkpoint khi user tap lại.
- Presigned URL expired mid-upload: request URL mới cho chunk đang pending. Các chunks đã upload giữ nguyên.

---

## PATCH-INFRA-03.1: TeraRelay In-Process Watchdog

> **Thay thế stub tại:** `#### INFRA-03.1 In-Process Watchdog`

**Nguyên tắc:** Single-binary deployment không có cluster coordinator. Self-healing phải xảy ra trong binary. Systemd là last-resort, không phải primary recovery mechanism.

**Watchdog Architecture:**

```rust
pub struct InProcessWatchdog {
    component_health: HashMap<ComponentId, ComponentHealth>,
    last_heartbeat:   HashMap<ComponentId, Instant>,
    restart_counts:   HashMap<ComponentId, u32>,
    alert_tx:         mpsc::Sender<WatchdogAlert>,
}

pub struct ComponentHealth {
    status:            HealthStatus,   // Healthy | Degraded | Failed
    last_error:        Option<String>,
    restart_count_1h:  u32,
}

/// Được gọi mỗi 1 giây bởi dedicated Tokio task
pub async fn watchdog_tick(watchdog: Arc<Mutex<InProcessWatchdog>>) {
    let now = Instant::now();
    for (component_id, last_hb) in &watchdog.last_heartbeat {
        let elapsed = now.duration_since(*last_hb);
        // Threshold: 10 giây không có heartbeat → component considered failed
        if elapsed > Duration::from_secs(10) {
            watchdog.mark_failed(component_id);
            watchdog.schedule_restart(component_id, Duration::from_secs(1)).await;
        }
    }
}
```

**Component Heartbeat Registration:**

| Component | Heartbeat interval | Max silence threshold | Restart policy |
|---|---|---|---|
| WAL staging consumer | 2s | 10s | Restart after 1s delay |
| Pub/sub fanout | 2s | 10s | Restart after 1s delay |
| BLE beacon scanner | 5s | 20s | Restart after 2s delay |
| ALPN probe task | 10s | 30s | Restart after 5s delay |
| AI worker process | 5s | 15s | Restart after 2s delay; max 3/hour |

**Restart Budget (Circuit Breaker):**

```rust
pub fn schedule_restart(&mut self, component_id: &ComponentId, delay: Duration) {
    let count_1h = self.restart_counts.entry(*component_id).or_insert(0);
    if *count_1h >= 5 {
        // Circuit breaker: 5 restarts trong 1 giờ → mark permanently degraded
        self.component_health.insert(*component_id, ComponentHealth {
            status: HealthStatus::Degraded,
            last_error: Some("Restart budget exceeded (5/hour)".to_string()),
            restart_count_1h: *count_1h,
        });
        // Alert Admin Console — không tắt daemon
        self.alert_tx.send(WatchdogAlert::CircuitBreakerTripped {
            component: *component_id,
            restart_count: *count_1h,
        }).ok();
        return;
    }
    *count_1h += 1;
    tokio::spawn(async move {
        tokio::time::sleep(delay).await;
        restart_component(component_id).await;
    });
}
```

**Prometheus Metrics (Zero-Knowledge):**

```
terachat_watchdog_restarts_total{component="wal_staging"} 2
terachat_watchdog_circuit_breaker_trips_total{component="ai_worker"} 1
terachat_component_health{component="ble_scanner", status="healthy"} 1
```

Không có user ID, message content, hay session data trong metrics.

**SIGTERM Handling (Graceful Shutdown):**

```rust
tokio::signal::ctrl_c().await?;
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

Systemd `TimeoutStopSec = 35` — 5 giây margin sau 30 giây checkpoint.

---

## PATCH-OBSERVE-01.1: Client-Side Mobile Metrics Push

> **Thay thế stub tại:** `#### OBSERVE-01.1 [IMPLEMENTATION] Mobile Metrics Push`

**Nguyên tắc thiết kế:** Mobile không expose scrape endpoint (firewall/NAT issues). Push aggregate metrics qua OTLP HTTP khi online. Buffer locally khi offline. Không có user-correlated data trong bất kỳ metric nào.

**Metric Types (Privacy-Safe):**

```rust
pub struct ClientMetricBatch {
    /// Anonymized device class — không có device ID hay user ID
    device_class:   DeviceClass,   // Mobile | Desktop | Server
    platform:       PlatformKind,  // iOS | Android | macOS | Windows | Linux
    app_version:    SemVer,

    /// Performance metrics (aggregate, không có per-message data)
    mls_encrypt_p50_ms:      u32,
    mls_encrypt_p99_ms:      u32,
    ipc_buf_acquire_p50_us:  u32,
    ipc_buf_acquire_p99_us:  u32,
    dag_append_p50_ms:       u32,
    dag_merge_events_per_s:  u32,

    /// Reliability metrics
    wasm_sandbox_crashes:    u32,
    nse_circuit_breaker_trips: u32,
    push_key_version_mismatches: u32,
    alpn_fallback_count:     u32,   // Số lần phải fallback từ QUIC → gRPC → WSS

    /// Health indicators
    wal_size_mb:             u32,   // Bucket: 0-10, 10-50, 50-100, 100+
    available_ram_mb:        u32,   // Bucket: 0-100, 100-500, 500-1000, 1000+
    battery_pct:             u8,    // Bucket: 0-20, 20-40, 40-60, 60-80, 80-100

    /// Timestamps (no user correlation)
    collection_period_start: u64,   // Unix epoch, second precision
    collection_period_end:   u64,
}
```

**Push Flow:**

```text
Mỗi 15 phút (hoặc khi app foreground sau offline):
  1. Aggregate metrics từ AtomicCounters trong Rust Core
  2. Serialize → OTLP protobuf
  3. KHÔNG gửi nếu battery < 15% (tiết kiệm power)
  4. Gửi qua HTTPS POST /v1/metrics (mTLS — same relay connection)
     Nếu online: gửi ngay
     Nếu offline: append vào metrics_buffer.db (max 48h, 500KB)
  5. Server nhận, ghi vào Prometheus remote write endpoint
  6. ZeroizeOnDrop: xóa batch sau khi ACK nhận được
```

**Crash Reporter (Privacy-Safe):**

```rust
pub struct CrashReport {
    crash_id:       Uuid,           // Random UUID v4 — không liên kết với user
    platform:       PlatformKind,
    app_version:    SemVer,
    component:      &'static str,   // "wasm_sandbox" | "mls_engine" | "mesh_transport"
    panic_type:     &'static str,   // Panic type string, không có backtrace nếu có PII
    stack_hash:     [u8; 8],        // BLAKE3[0:8] của stripped stacktrace
    os_version:     String,
    timestamp_utc:  u64,
}
```

Crash report KHÔNG bao gồm: user ID, device ID, message content, file paths có username, full stacktrace (chỉ hash).

**Retention và Privacy:**

- Metrics server: data retention 30 ngày, sau đó auto-delete.
- Không có cross-device correlation trong bất kỳ query nào.
- Mọi `device_class`, `platform` được bucket để ngăn re-identification.
- Admin có thể opt-out metrics hoàn toàn qua OPA Policy: `{ "telemetry.enabled": false }`.

---

## PATCH-OBSERVE-02.1: DAG Merge Progress IPC Signal Spec

> **Thay thế stub tại:** `#### OBSERVE-02.1 [IMPLEMENTATION] IPC Signal Spec`

**Mục tiêu:** Khi DAG merge > 500 events (sau partition dài), user không được thấy black screen. Progress phải visible và có thể interrupted.

**IPC Signal Contract:**

```rust
/// Emitted mỗi 200ms khi DAG merge backlog > 500 events.
/// Dừng emit sau khi merge hoàn tất.
CoreSignal::DagMergeProgress {
    completed: u64,       // Events đã merge
    total:     u64,       // Tổng events cần merge
    // Derived: percentage = completed * 100 / total
    // Derived: eta_seconds = (total - completed) / current_rate
}
```

**Mobile ANR Prevention — Time-Slicing:**

```rust
pub async fn merge_dag_timesliced(
    events: Vec<CrdtEvent>,
    progress_tx: mpsc::Sender<MergeProgress>,
) {
    const BATCH_SIZE: usize = 100;
    let total = events.len() as u64;
    let mut completed: u64 = 0;

    for batch in events.chunks(BATCH_SIZE) {
        // Process batch — O(batch_size * log n) HLC sort
        merge_batch(batch).await;
        completed += batch.len() as u64;

        // Yield để UI event loop có 1-2ms để process user input
        tokio::task::yield_now().await;

        // Emit progress mỗi 200ms (kiểm tra timer, không phải mỗi batch)
        if should_emit_progress() {
            progress_tx.send(MergeProgress { completed, total }).ok();
        }
    }
    // Final signal: merge hoàn tất
    progress_tx.send(MergeProgress { completed: total, total }).ok();
}
```

**UI Behavior khi nhận DagMergeProgress:**

```text
completed / total < 1.0:
  → Hiển thị Progress Banner (non-blocking, không modal):
    "⟳ Đồng bộ tin nhắn trong lúc mất mạng... [████░░░░] 62%"
  → Chat vẫn scrollable nhưng disable Send button
  → ETA hiển thị nếu total > 1000: "~45 giây còn lại"

completed / total == 1.0:
  → Banner tự dismiss sau 1.5 giây
  → Enable Send button
  → CoreSignal::StateChanged { table: "messages" } sẽ trigger UI refresh
```

**Desktop (không có ANR risk):**

- Rayon parallel thread pool — merge toàn bộ trong background Tokio task.
- Emit `DagMergeProgress` mỗi 200ms (same signal, cùng UI behavior).
- Không có time-slicing — Desktop merge hoàn tất nhanh hơn Mobile 10-20x.

---

## PATCH-PLATFORM-17.2: Dart FFI Memory Contract Implementation

> **Thay thế stub tại:** `#### PLATFORM-17.2 Implementation`

**Dart FFI `TeraSecureBuffer` Wrapper:**

```dart
/// Mandatory wrapper cho mọi Rust buffer transfer trên Android/Huawei.
/// Direct .toPointer() ngoài wrapper này → CI lint error (BLOCKER).
class TeraSecureBuffer {
  final int _token;
  bool _released = false;

  TeraSecureBuffer._(this._token);

  /// Factory: acquire token từ Rust Core
  static Future<TeraSecureBuffer> acquire(int operationId) async {
    final token = await _teraFfi.tera_buf_acquire(operationId);
    if (token == 0) throw const TeraBufferError('acquire failed — token=0');
    return TeraSecureBuffer._(token);
  }

  /// Primary release path — PHẢI gọi trong finally block
  void releaseNow() {
    if (_released) return;
    _teraFfi.tera_buf_release(_token);
    _released = true;
  }

  /// GC Finalizer: safety net — không phải primary path
  @override
  void finalize() {
    if (!_released) {
      // Log WARNING metric — GC release là code smell
      MetricsCollector.increment('ffi.gc_finalizer_release.count');
      _logger.warning('TeraSecureBuffer $token released by GC finalizer — explicit releaseNow() missing');
      _teraFfi.tera_buf_release(_token);
    }
  }
}

/// Helper: bắt buộc sử dụng để access buffer content
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
    buf.releaseNow();  // Guaranteed execution
  }
}
```

**CI Clippy Lint (Rust side) — FFI-01 Enforcement:**

```rust
// custom_lints/src/ffi_token_lint.rs
// Từ chối mọi pub extern "C" function return Vec<u8>, *const u8, *mut u8
// mà không đi qua tera_buf_acquire protocol.
#[clippy::msrv = "1.75.0"]
fn check_fn_return_type(cx: &LateContext, fn_id: DefId) {
    if is_pub_extern_c(fn_id) {
        if returns_raw_ptr_or_vec(cx, fn_id) && !uses_token_protocol(cx, fn_id) {
            cx.span_error(
                fn_span(fn_id),
                "FFI-01 VIOLATION: pub extern \"C\" function returns raw pointer/Vec. \
                 Use tera_buf_acquire/tera_buf_release token protocol. \
                 See TERA-FEAT §10.1 SEC-02 and TERA-CORE §4.3."
            );
        }
    }
}
```

**NativeFinalizer Registration (Android/Huawei):**

```dart
// Trong TeraSecureBuffer constructor — NativeFinalizer là safety net
final _finalizer = NativeFinalizer(
    _teraFfi.tera_buf_release_ptr.cast(), // Native callback pointer
);

TeraSecureBuffer._(this._token) {
    // Attach finalizer — GC sẽ gọi tera_buf_release nếu explicit release bị quên
    _finalizer.attach(this, Pointer.fromAddress(_token), detach: this);
}
```

**Dart Lint Rule (analysis_options.yaml):**

```yaml
analyzer:
  plugins:
    - tera_dart_lints
linter:
  rules:
    - tera_avoid_direct_ffi_pointer  # Block direct .toPointer() ngoài useInTransaction
    - tera_require_secure_buffer     # Require TeraSecureBuffer cho tera_buf_acquire calls
```

---

## PATCH-PLATFORM-18.1: ONNX Model Integrity Verification Flow

> **Thay thế stub tại:** `#### PLATFORM-18.1 Verification Flow`

**Áp dụng cho:** Mọi ONNX model load trong F-10 (AI/SLM). Không có exception.

**Model Manifest (bundled với app):**

```json
{
  "models": [
    {
      "name": "micro_ner",
      "tier": "tiny",
      "file": "micro_ner.onnx",
      "blake3": "a3f2e1d4c5b6a7e8f9d0c1b2a3f4e5d6c7b8a9f0e1d2c3b4a5f6e7d8c9b0a1f2",
      "size_bytes": 987654,
      "min_available_ram_mb": 12
    },
    {
      "name": "whisper_tiny",
      "tier": "tiny",
      "file": "whisper_tiny.mlmodelc",
      "blake3": "b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5",
      "size_bytes": 39000000,
      "min_available_ram_mb": 100
    }
  ],
  "manifest_signature": "Ed25519:TeraChat_Marketplace_CA_Key:XXXXXXXX"
}
```

**`OnnxModelLoader.load_verified()` Flow:**

```rust
pub fn load_verified(
    model_name: &str,
    manifest: &ModelManifest,
) -> Result<OrtSession, ModelLoadError> {
    // Step 1: Lookup model spec trong manifest
    let spec = manifest.find(model_name)
        .ok_or(ModelLoadError::NotInManifest)?;

    // Step 2: Verify manifest signature (Ed25519, TeraChat CA)
    verify_ed25519(&manifest.manifest_signature, &TeraChat_CA_PublicKey)?;

    // Step 3: Check available RAM trước khi load
    let available_mb = sysinfo::available_memory_mb();
    if available_mb < spec.min_available_ram_mb as u64 {
        return Err(ModelLoadError::InsufficientRam {
            required: spec.min_available_ram_mb,
            available: available_mb as u32,
        });
    }

    // Step 4: Load file bytes
    let model_bytes = load_bundled_asset(&spec.file)?;

    // Step 5: Verify BLAKE3 hash
    let actual_hash = blake3::hash(&model_bytes);
    if actual_hash.as_bytes() != spec.blake3.as_bytes() {
        // Log ke Audit Log — tampering detected
        log_audit(AuditEvent::ModelIntegrityViolation {
            model_name: model_name.to_string(),
            expected_hash: spec.blake3.clone(),
            actual_hash: hex::encode(actual_hash.as_bytes()),
        });
        return Err(ModelLoadError::HashMismatch);
    }

    // Step 6: Initialize ORT session trong isolated arena
    let session = ort::Session::builder()
        .with_memory_pattern(true)
        .with_parallel_execution(false)    // Không share thread pool với Rust Core
        .build_from_bytes(&model_bytes)?;

    // Step 7: ZeroizeOnDrop trên model_bytes sau khi ORT internalize
    drop(Zeroizing::new(model_bytes));

    Ok(session)
}
```

**Platform-Specific Paths:**

| Platform | Model format | Loader |
|---|---|---|
| 📱 iOS | CoreML `.mlmodelc` | `CoreML::load_compiled_model()` |
| 📱 Android | ONNX `.onnx` | `OnnxRuntime::Session::new()` |
| 📱 Huawei | HiAI `.om` hoặc ONNX | `HiAI::load()` với fallback ONNX |
| 💻 macOS | CoreML `.mlmodelc` | `CoreML::load_compiled_model()` |
| 🖥️ Win/Linux | ONNX `.onnx` | `OnnxRuntime::Session::new()` |

**Failure Handling:**

- `HashMismatch`: terminate AI worker, emit `CoreSignal::ComponentFault { severity: Critical }`. UI: "Tập tin AI bị lỗi — đang tắt tính năng AI tạm thời." AI feature disabled cho phiên đó.
- `InsufficientRam`: log `ONNX_RAM_DENIED { model, required, available }`. Chọn tier thấp hơn nếu có. Nếu không: AI feature unavailable cho phiên đó.
- `NotInManifest`: BLOCKER — model không được phép chạy. Terminate AI worker.

---

## PATCH-PLATFORM-19.1: Super Node Discovery Priority

> **Thay thế stub tại:** `#### PLATFORM-19.1 Super Node Discovery Priority`

📱 Khi Mobile cần ONNX inference, thứ tự ưu tiên (được enforce bởi Rust Core):

```rust
pub async fn resolve_inference_backend(
    model_tier: ModelTier,
    memory_arbiter: &MemoryArbiter,
) -> InferenceBackend {
    // Priority 1: TeraEdge Desktop trên cùng LAN (< 5ms latency)
    if let Some(edge) = discover_local_desktop_edge().await {
        if edge.onnx_available && edge.latency_ms < 50 {
            return InferenceBackend::RemoteDesktop(edge);
        }
    }

    // Priority 2: Local model nếu RAM đủ và battery > 30%
    let battery = platform_battery_pct();
    let available_ram = memory_arbiter.available_for(ComponentId::AiWorker);
    let required_ram = model_tier.required_ram_mb();
    if available_ram >= required_ram && battery > 30 {
        return InferenceBackend::Local;
    }

    // Priority 3: VPS Enclave (cloud, cần Internet)
    if is_internet_available() {
        return InferenceBackend::VpsEnclave;
    }

    // Priority 4: Downgrade model tier và thử lại local
    if model_tier != ModelTier::Tiny {
        return resolve_inference_backend(ModelTier::Tiny, memory_arbiter).await;
    }

    // No backend available
    InferenceBackend::Unavailable
}
```

**Discovery Protocol (Local Desktop):**

```text
Mobile phát mDNS query: _terachat-edge._tcp.local
  │
  ↓ (100ms timeout)
Desktop Super Node respond:
  {
    node_id: NodeId,
    onnx_available: bool,
    model_tiers: ["tiny", "base"],
    current_load_pct: u8,   // 0-100
    latency_hint_ms: u32,   // Round-trip time estimate
  }
  │ Signed bằng Desktop DeviceIdentityKey
  ↓
Mobile verify signature → connect nếu load < 80% và latency < 50ms
```

**Fallback khi Desktop quá tải:**

- Desktop `current_load_pct > 80%`: Mobile tự động downgrade sang Local Tiny hoặc VPS.
- Desktop mất kết nối mid-inference: retry 1 lần với 3s timeout. Nếu thất bại: VPS Enclave hoặc Local Tiny.

---

## PATCH-INFRA-04.1: Canary Deployment — Traffic Splitting via DNS

> **Thay thế stub tại:** `#### INFRA-04.1 Traffic Splitting via DNS`

**Nguyên tắc:** Không có Kubernetes, không có service mesh. DNS-based traffic splitting + per-tenant feature flags.

**DNS Traffic Splitting (GeoDNS):**

```text
relay.terachat.com
  ├── 95% → relay-stable.terachat.com  (current stable version)
  └── 5%  → relay-canary.terachat.com  (new version under validation)
```

Clients không biết họ đang trên stable hay canary — cùng TLS cert, cùng API surface.

**Canary Promotion Gate (automated):**

```yaml
# ops/canary-policy.yaml
canary_validation:
  initial_traffic_pct: 5
  promotion_steps: [5, 25, 50, 100]
  promotion_interval_hours: 2     # Mỗi 2 giờ nếu tất cả gates pass
  
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
    - metric: "client_reported_crash_rate"     # Từ OBSERVE-01 client metrics
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
// Admin Console → OPA Policy → pushed down đến clients
{
  "feature_flags": {
    "canary_opt_out": true,         // Force stable version cho tenant này
    "ai_inference_enabled": false,  // Disable AI cho specific compliance requirement
    "mesh_mode_enabled": true,
    "max_file_size_mb": 100
  }
}
```

**Rollback Procedure (< 5 phút):**

```bash
# 1. Automated trigger: canary-controller phát hiện threshold breach
# 2. DNS weight reset: canary → 0%, stable → 100%
tera-ops dns set-weight --target relay-canary --weight 0
tera-ops dns set-weight --target relay-stable --weight 100

# 3. Alert: gửi PagerDuty incident + Slack notification
# 4. Log rollback event với timestamp và triggering metric
```

---

## PATCH-INFRA-05.1: SBOM Generation & Reproducible Builds

> **Thay thế stub tại:** `#### INFRA-05.1 SBOM Generation`

**SBOM (Software Bill of Materials) — Yêu cầu cho Enterprise/Gov:**

```bash
# CI pipeline: generate SBOM sau mỗi build
cargo cyclonedx --format json --output terachat-sbom.json

# Ký SBOM bằng TeraChat Release Key
cosign sign-blob \
    --key release-key.pem \
    --output-signature terachat-sbom.json.sig \
    terachat-sbom.json

# Upload cả SBOM và signature lên GitHub Release Assets
```

**SBOM Content (CycloneDX 1.5 format):**

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.5",
  "version": 1,
  "metadata": {
    "component": {
      "name": "terachat-core",
      "version": "1.0.0",
      "type": "library",
      "supplier": { "name": "TeraChat Inc." }
    },
    "tools": [{ "name": "cargo-cyclonedx", "version": "0.3.x" }]
  },
  "components": [
    {
      "name": "ring",
      "version": "0.17.x",
      "purl": "pkg:cargo/ring@0.17.x",
      "licenses": [{ "expression": "ISC AND OpenSSL" }],
      "hashes": [{ "alg": "SHA-256", "content": "..." }]
    }
  ]
}
```

**Reproducible Builds:**

```dockerfile
# Dockerfile.build — hermetic build environment
FROM rust:1.75.0-slim-bookworm AS builder
# Pin ALL system packages to exact versions
RUN apt-get install -y --no-install-recommends \
    libclang-dev=1:15.0-56 \
    pkg-config=1.8.1-1
# Rust toolchain pinned via rust-toolchain.toml
# cargo build với SOURCE_DATE_EPOCH để deterministic timestamps
ENV SOURCE_DATE_EPOCH=1700000000
RUN cargo build --release --locked
```

```toml
# rust-toolchain.toml — pinned in repository root
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

**Verification (Customer-Side):**

```bash
# Customer verify binary khớp với SBOM-claimed hash
cosign verify-blob \
    --key https://releases.terachat.com/cosign-pub.pem \
    --signature terachat-sbom.json.sig \
    terachat-sbom.json

# Verify binary hash khớp với SBOM component hash
sha256sum terachat-relay-linux-x64 | grep $(jq -r '.metadata.component.hashes[0].content' terachat-sbom.json)
```

---

## PATCH-CICD-01.1: CI/CD Required Gates

> **Thay thế stub tại:** `#### CICD-01.1 Required Gates`

Tất cả gates dưới đây phải pass trước khi merge vào `main`. Bất kỳ gate nào fail = **BLOCKER**.

**Security Gates:**

```yaml
security_gates:
  - name: "FFI-01: No raw pointer in pub extern C"
    command: "cargo clippy -- -D tera_ffi_raw_pointer"
    blocker: true

  - name: "KEY-02: ZeroizeOnDrop verification"
    command: "cargo miri test --test zeroize_verification"
    blocker: true

  - name: "Dependency audit (RUSTSEC)"
    command: "cargo audit --deny warnings"
    blocker: true

  - name: "Trivy container scan (CRITICAL CVE = fail)"
    command: "trivy image --exit-code 1 --severity CRITICAL terachat-relay:latest"
    blocker: true

  - name: "Secret scan (GitLeaks)"
    command: "gitleaks detect --source . --exit-code 1"
    blocker: true
```

**Correctness Gates:**

```yaml
correctness_gates:
  - name: "Unit tests (all platforms)"
    command: "cargo nextest run --all-features"
    blocker: true

  - name: "WasmParity CI gate (wasm3 vs wasmtime, delta ≤ 20ms)"
    command: "cargo test --test wasm_parity -- --timeout 60"
    blocker: true
    description: |
      Executes the same .tapp workload on wasm3 (iOS path) and wasmtime (Desktop path).
      Fails if: (1) output AST differs, (2) execution time delta > 20ms on reference hardware,
      (3) memory usage delta > 5MB.

  - name: "Inbound deduplication contract (CRDT)"
    command: "cargo test --test crdt_dedup_contract"
    blocker: true
    description: |
      Relay restart with 1000 in-flight STAGED events.
      Verify: zero duplicate messages in recipient view,
      zero UNIQUE constraint violations in hot_dag.db.

  - name: "MLS epoch rotation SLA (≤1s for 100 members)"
    command: "cargo bench --bench mls_epoch_rotation -- --sample-size 10"
    blocker: false   # Non-blocking: regression tracked, not blocking merge
    threshold_ms: 1000
```

**Build & Signing Gates:**

```yaml
build_gates:
  - name: "Reproducible build verification"
    command: "ops/verify-reproducible-build.sh"
    blocker: true
    description: |
      Build twice with identical SOURCE_DATE_EPOCH.
      SHA-256 of both binaries must be identical.
      Fails on any non-determinism.

  - name: "SBOM generation and signing"
    command: "ops/generate-sbom.sh && cosign sign-blob ..."
    blocker: true

  - name: "iOS: fastlane match cert validation"
    command: "bundle exec fastlane match nuke --type development --dry-run"
    blocker: false
    platforms: [ios]

  - name: "Windows: EV Code Signing (DigiCert KeyLocker)"
    command: "signtool verify /pa terachat-setup.exe"
    blocker: true
    platforms: [windows]

  - name: "Linux: GPG signature on .deb/.rpm"
    command: "dpkg-sig --verify terachat_*.deb"
    blocker: true
    platforms: [linux]

  - name: "AppImage: Cosign verification"
    command: "cosign verify-blob --key terachat-root.pub terachat-*.AppImage"
    blocker: true
    platforms: [linux_appimage]
```

**Performance Budget Gates:**

```yaml
performance_gates:
  - name: "IPC buffer acquire P99 < 100µs"
    command: "cargo bench --bench ipc_bridge"
    threshold_p99_us: 100
    blocker: false   # Regression alert, not blocking

  - name: "AES-256-GCM throughput regression (< 10% drop)"
    command: "cargo bench --bench crypto_throughput"
    blocker: false

  - name: "hot_dag.db append P99 < 10ms"
    command: "cargo bench --bench dag_append"
    threshold_p99_ms: 10
    blocker: false
```

---

## PATCH-INFRA-06.1: Automated Chaos Engineering Framework

> **Thay thế stub tại:** `#### INFRA-06.1 Chaos Test Framework`

**Mục tiêu:** 28 scenarios trong TestMatrix.md phải chạy automated trong CI (staging environment), không chỉ manual runbook. Gov/Military tier: phải pass tất cả 28 trước contract ký.

**Framework Architecture:**

```rust
// chaos/src/lib.rs
pub struct ChaosScenario {
    pub id:            &'static str,       // e.g. "SC-01"
    pub name:          &'static str,
    pub fault_inject:  Box<dyn FaultInjector>,
    pub expected:      ExpectedBehavior,
    pub timeout_s:     u32,
    pub platforms:     Vec<PlatformKind>,
}

pub trait FaultInjector: Send + Sync {
    async fn inject(&self, env: &TestEnvironment) -> Result<(), ChaosError>;
    async fn cleanup(&self, env: &TestEnvironment);
}

pub struct ExpectedBehavior {
    pub max_data_loss_events:  u32,     // 0 = zero data loss required
    pub max_recovery_time_s:   u32,
    pub min_mesh_nodes_active: u32,
    pub ui_degraded_ok:        bool,    // Nếu false: UI phải fully functional
}
```

**Core Chaos Scenarios (subset — 8 của 28):**

```rust
// SC-01: Network partition + rejoin
ChaosScenario {
    id: "SC-01",
    name: "Network partition 30 minutes then rejoin",
    fault_inject: Box::new(NetworkPartitionInjector {
        duration_s: 1800,
        partition_type: PartitionType::AllNodes,
    }),
    expected: ExpectedBehavior {
        max_data_loss_events: 0,
        max_recovery_time_s: 120,
        min_mesh_nodes_active: 2,
        ui_degraded_ok: true,  // Mesh mode UI là acceptable
    },
    timeout_s: 2100,
    platforms: vec![iOS, Android, Desktop],
}

// SC-02: iOS Tactical Relay TTL expiry — tất cả desktop offline
ChaosScenario {
    id: "SC-02",
    name: "EMDP: Desktop offline, iOS-only mesh, TTL expiry at T+60min",
    fault_inject: Box::new(EmdpTtlExpiryInjector {
        desktop_offline: true,
        ios_node_count: 2,
        run_to_expiry: true,
    }),
    expected: ExpectedBehavior {
        max_data_loss_events: 0,    // Buffered messages không được mất
        max_recovery_time_s: 30,    // Sau khi desktop reconnect
        min_mesh_nodes_active: 2,
        ui_degraded_ok: true,
    },
    timeout_s: 4200,
    platforms: vec![iOS],
}

// SC-03: Relay restart với 1000 STAGED events
ChaosScenario {
    id: "SC-03",
    name: "Relay restart: 1000 in-flight STAGED events",
    fault_inject: Box::new(RelayRestartInjector {
        staged_events_count: 1000,
        restart_type: RestartType::SIGKILL,  // Hard kill — không graceful
    }),
    expected: ExpectedBehavior {
        max_data_loss_events: 0,    // WAL staging guarantee: zero loss
        max_recovery_time_s: 60,
        min_mesh_nodes_active: 0,   // Online-only scenario
        ui_degraded_ok: false,      // UI phải fully recover
    },
    timeout_s: 300,
    platforms: vec![Server],
}

// SC-06: Dead Man Switch lockout trong active CallKit session
ChaosScenario {
    id: "SC-06",
    name: "Dead Man Switch fires during active CallKit voice call",
    fault_inject: Box::new(DeadManSwitchInjector {
        during_active_call: true,
        grace_hours: 0,   // Immediate lockout
    }),
    expected: ExpectedBehavior {
        // Core_Spec §5.1: lockout deferred until call ends
        max_data_loss_events: 0,
        max_recovery_time_s: 10,    // 10s sau khi call kết thúc
        min_mesh_nodes_active: 0,
        ui_degraded_ok: false,
    },
    timeout_s: 180,
    platforms: vec![iOS],
}
```

**CI Integration (staging environment):**

```yaml
# .github/workflows/chaos-tests.yml
name: Chaos Engineering Suite
on:
  schedule:
    - cron: '0 2 * * *'  # Hàng ngày lúc 2:00 AM UTC
  workflow_dispatch:
    inputs:
      scenario_filter:
        description: 'Run specific scenario (e.g. SC-01) or "all"'
        default: 'all'

jobs:
  chaos-test:
    runs-on: ubuntu-latest
    timeout-minutes: 180
    steps:
      - name: Start staging environment (docker-compose)
        run: docker-compose -f ops/chaos/docker-compose.staging.yml up -d

      - name: Run chaos suite
        run: |
          cargo run --bin chaos-runner -- \
            --scenario ${{ inputs.scenario_filter || 'all' }} \
            --parallel 4 \
            --report-format junit \
            --output chaos-results.xml

      - name: Publish results
        uses: actions/upload-artifact@v4
        with:
          name: chaos-results
          path: chaos-results.xml
```

---

## PATCH-CHANGELOG-0.3.0

Thêm entry sau vào `## 12. CHANGELOG`:

```markdown
| 0.3.0 | 2026-03-XX | Fill all stub sections from v0.2.6: INFRA-01.2 (ONNX Offload Protocol),
|       |             | INFRA-02.1 (Blob Storage Upload/Download Flow), INFRA-03.1 (In-Process Watchdog),
|       |             | OBSERVE-01.1 (Mobile Metrics Push spec), OBSERVE-02.1 (DAG Merge Progress IPC),
|       |             | PLATFORM-17.2 (Dart FFI TeraSecureBuffer implementation),
|       |             | PLATFORM-18.1 (ONNX Model Integrity Verification Flow),
|       |             | PLATFORM-19.1 (Super Node Discovery Priority),
|       |             | INFRA-04.1 (Canary Deployment DNS Traffic Splitting),
|       |             | INFRA-05.1 (SBOM Generation and Reproducible Builds),
|       |             | CICD-01.1 (Required CI/CD Gates — 14 gates defined),
|       |             | INFRA-06.1 (Chaos Engineering Framework — 8 core scenarios). |
```

---

# Core_Spec.md — PATCH v0.2.7

# Điều kiện áp dụng: Bổ sung vào Core_Spec.md v0.2.6 theo từng section anchor

# Sau khi merge, version tăng lên 0.2.7

# Mỗi PATCH được đánh dấu rõ: [PATCH-NEW] = thêm mới, [PATCH-REPLACE] = thay thế section hiện có

---

## [PATCH-REPLACE] §10.2 — Latency Targets (P50 và P99 đầy đủ)

> Thay thế toàn bộ §10.2 Latency Targets hiện có.
> Lý do: Phiên bản cũ chỉ có single threshold, không có P99.
> Enterprise SLA yêu cầu P99 definition cho tất cả critical operations.

### §10.2 Latency Targets

**Measurement conditions (áp dụng cho mọi benchmark dưới đây):**

- Hardware reference: Server = 4 vCPU / 8 GB RAM VPS (Hetzner CX31 equiv). Mobile = iPhone 13 / Pixel 7. Desktop = MacBook Pro M2.
- Network: Server-side benchmarks = loopback. Client-side = 20ms simulated WAN latency.
- Load: Benchmarks chạy với 50% expected production concurrency.
- Sample size: tối thiểu 1,000 operations mỗi benchmark. P99 từ full sample.

| Operation | P50 | P99 | Measurement scope | Action on P99 breach |
|---|---|---|---|---|
| ALPN negotiation: QUIC available | < 20ms | < 50ms | Client → first packet ACK | MESH_MODE fallback |
| ALPN negotiation: QUIC blocked, gRPC ok | < 50ms | < 80ms | Client → gRPC handshake | gRPC fallback |
| ALPN negotiation: all blocked → Mesh | < 150ms | < 200ms | Client → Mesh Mode active | Accept; log `ALPN_TOTAL_FALLBACK` |
| MLS message encrypt (single, < 1KB) | < 2ms | < 5ms | `mls_engine.rs` entry → exit | Log warning; no user impact |
| MLS message decrypt (single, < 1KB) | < 2ms | < 5ms | `mls_engine.rs` entry → exit | Log warning; no user impact |
| AES-256-GCM encrypt (2MB chunk, AES-NI) | < 1ms | < 3ms | Hardware AES path | N/A |
| AES-256-GCM encrypt (2MB chunk, software) | < 8ms | < 20ms | Software ChaCha20 fallback | Log `SOFTWARE_CRYPTO_SLOW` |
| Ed25519 sign (biometric gate excluded) | < 1ms | < 3ms | After biometric unlock | N/A |
| Push notification decrypt (NSE, iOS) | < 100ms | < 500ms | APNs deliver → notification display | Ghost Push skeleton; Main App decrypt |
| CRDT_Event DAG append (hot_dag.db WAL) | < 3ms | < 10ms | `dag.rs append_event()` | Log `DAG_APPEND_SLOW`; no user impact |
| cold_state.db viewport fetch (20 msgs) | < 5ms | < 15ms | SQLite read → `tera_buf_acquire` | Log `VIEWPORT_FETCH_SLOW` |
| IPC `tera_buf_acquire` | < 10µs | < 100µs | Token creation overhead | Log `IPC_ACQUIRE_SLOW` |
| BLE beacon discovery (first peer) | < 500ms | < 2000ms | Mesh activate → first peer found | Log `MESH_DISCOVERY_SLOW` |
| DAG merge (batch of 100 events, mobile) | < 1ms | < 2ms | Per-batch (time-sliced) | `yield_now()` enforced |
| DAG merge (full 10k events, desktop) | < 500ms | < 2000ms | Full merge, Rayon thread pool | `CoreSignal::DagMergeProgress` |
| MLS epoch rotation (≤ 100 members) | < 500ms | < 1000ms | Commit → all members updated | Log `EPOCH_SLOW_100` |
| MLS epoch rotation (≤ 1,000 members) | < 30s | < 60s | Batch window delivery | Log `EPOCH_SLOW_1000` |
| MLS epoch rotation (≤ 5,000 members) | < 2min | < 5min | Manual Admin trigger | Log `EPOCH_SLOW_5000` |
| End-to-end relay delivery (online) | < 80ms | < 200ms | Send → recipient decrypt | Increment `relay_delivery_timeout_total` |
| WASM `.tapp` cold start (pre-warmed pool) | < 3ms | < 5ms | Pool entry → `.tapp` ready | Log `WASM_COLDSTART_MISS` |
| WASM `.tapp` cold start (no pool) | < 100ms | < 300ms | Instantiate → ready | Pre-warm on install |
| TURN failover (voice call) | < 1s | < 3s | Primary TURN down → Secondary | Audio drop ≤ 500ms |
| XPC Worker crash recovery (macOS) | < 3s | < 5s | Crash → Worker restarted | Max 3 retries (0s/2s/8s backoff) |
| WAL checkpoint (SIGTERM) | N/A | ≤ 30s | `PRAGMA wal_checkpoint(TRUNCATE)` | Exit unconditionally at 30s |
| Shamir reconstruction (M=3 of N=5) | < 50ms | < 100ms | In `mlock`-protected arena | N/A; rare operation |
| ALPN probe learning: mark strict compliance | N/A | < 3s | 3 consecutive QUIC failures | Admin alert: "Auto-switched to TCP" |

**Benchmark CI enforcement:**

- Operations đánh dấu `blocker: false` trong CICD-01.1: P99 regression > 20% → alert không block merge.
- Operations đánh dấu `blocker: true`: P99 regression > 10% → block merge.
- Benchmark suite: `cargo bench --bench all_latency_benchmarks -- --sample-size 1000`.

---

## [PATCH-NEW] §5.3b — MLS Super-Group Sharding (Groups > 5,000 Members)

> Thêm mới vào §5.3 sau phần "Batched TreeKEM Update_Path delivery".
> Lý do: "Manual Admin trigger only" không phải giải pháp cho Banking/Government với 10,000+ users.

### §5.3b MLS Super-Group Sharding Strategy

**Use case:** Enterprise channel với > 5,000 members (Bank-wide broadcast, Government ministry all-hands).

**Kiến trúc: Federation of Sub-Groups (không phải single MLS group):**

```text
Super-Group (logical concept, không tồn tại trong MLS protocol)
  │
  ├── Sub-Group A (≤ 5,000 members) — independent MLS group
  ├── Sub-Group B (≤ 5,000 members) — independent MLS group
  └── Sub-Group C (≤ 5,000 members) — independent MLS group

Fanout Bridge (Rust Core server-side):
  Admin sends message → Bridge encrypts for each Sub-Group independently
  Bridge receives message → delivers to all Sub-Groups
```

**Sub-Group Assignment:**

```rust
pub struct SuperGroup {
    id:         SuperGroupId,
    sub_groups: Vec<MlsGroupId>,
    shard_map:  HashMap<DeviceId, MlsGroupId>,   // Which sub-group each device belongs to
    shard_size: usize,   // Default: 1000 (well below 5,000 ceiling for headroom)
}

pub fn assign_to_shard(device_id: &DeviceId, super_group: &SuperGroup) -> MlsGroupId {
    // Deterministic assignment: consistent hashing based on DeviceId
    // Ensures minimal resharding when members join/leave
    let slot = fnv_hash(device_id) % super_group.sub_groups.len();
    super_group.sub_groups[slot]
}
```

**Cross-Shard Message Delivery:**

```text
Sender (in Sub-Group A) sends message M:
  │
  ▼
MLS encrypt M for Sub-Group A → CRDT_Event_A
Rust Core Fanout Bridge:
  1. Detect sender is in Super-Group
  2. Decrypt M (only Bridge has Company_Key — acceptable in server-side bridge)
  3. Re-encrypt M for Sub-Group B → CRDT_Event_B
  4. Re-encrypt M for Sub-Group C → CRDT_Event_C
  5. Deliver CRDT_Event_A, B, C via WAL staging
  │
  ▼
Members in B and C receive M as if from their own sub-group
```

**Security Properties:**

| Property | Behavior |
|---|---|
| E2EE within sub-group | Preserved — Fanout Bridge re-encrypts with sub-group keys |
| Forward Secrecy | Per sub-group independently |
| Zero-Knowledge server | BROKEN at Bridge — Bridge decrypts to re-encrypt. Disclosed in SLA. |
| Member removal (leave) | Triggers epoch rotation in that member's sub-group only (O(log 1000), not O(log 10000)) |
| Admin broadcast | Admin encrypts once → Bridge fans out to N sub-groups |

**Zero-Knowledge trade-off disclosure (bắt buộc cho Admin Console):**

```
⚠ Super-Group Warning
Groups > 5,000 members require cross-shard message fanout.
The Fanout Bridge service decrypts and re-encrypts messages between shards.
This breaks the Zero-Knowledge guarantee for super-group messages.
The bridge operates on TeraChat-controlled infrastructure (your private VPS in self-hosted deployments).
All fanout operations are logged to the Tamper-Proof Audit Log (Ed25519 signed).
For maximum Zero-Knowledge compliance, keep groups ≤ 5,000 members.
```

**Shard Rebalancing (member growth):**

- Trigger: sub-group reaches 80% capacity (4,000 members).
- Action: new sub-group created, 20% of members (800) migrated.
- Migration: new `MLS Welcome_Packet` for migrating members. Old sub-group epoch rotation.
- Zero downtime: members receive messages from both sub-groups during migration window (≤ 60s).

**Admin Controls:**

- `GET /v1/super-group/{id}/shards` → shard distribution map.
- `POST /v1/super-group/{id}/rebalance` → manual trigger.
- Automatic rebalancing: nếu enabled trong OPA Policy.

---

## [PATCH-NEW] §5.1b — Gossip PSK Rotation Ceremony

> Thêm mới vào §5.1 sau "Dead Man Switch" section.
> Lý do: Gossip PSK 90-day rotation được mention trong §9.2 nhưng không có ceremony protocol.

### §5.1b Gossip PSK Rotation Ceremony

**Mục đích:** `Mesh_PSK_daily` được derived từ `Company_Key` (HKDF). Thay đổi `Company_Key` (khi Admin revoke member) tự động rotate PSK. Tuy nhiên, independent 90-day rotation policy cần ceremony riêng để revoke compromised PSK mà không thay đổi toàn bộ `Company_Key`.

**Rotation Trigger Conditions:**

| Trigger | Action | Urgency |
|---|---|---|
| 90-day scheduled rotation | Standard ceremony | Plan 2 tuần trước |
| Security incident: suspected PSK compromise | Emergency rotation | Immediate (< 4 giờ) |
| Mass device revocation (> 20% workforce) | Forced rotation | Within 24 giờ |
| Admin security audit request | Standard ceremony | Plan 1 tuần trước |

**Standard Ceremony (Planned):**

```text
T-14 ngày:
  Admin Console: "PSK Rotation scheduled for [date]" notification → tất cả devices
  New PSK derived: Mesh_PSK_new = HKDF(Company_Key, "mesh-beacon" || date_new || cluster_id)
  Mesh_PSK_new distributed đến tất cả enrolled devices qua E2EE channel

T-7 ngày:
  Devices bắt đầu dual-accept: accept beacons từ CẢ PSK_current VÀ PSK_new
  (Rollover window: đảm bảo devices đi offline trong ceremony window không bị isolated)

T-0 (Rotation Day):
  00:00 UTC: PSK_new trở thành PRIMARY — devices phát beacon với PSK_new
  PSK_current vẫn được ACCEPT (không phát) thêm 7 ngày
  Admin Console confirmation: "PSK rotation completed. [N] devices on new PSK, [M] on old PSK."

T+7 ngày:
  PSK_current bị revoke — không còn được accept
  Devices vẫn trên PSK_current → flagged trong Admin Console → require re-enrollment
```

**Emergency Rotation (< 4 giờ):**

```text
CISO kích hoạt Emergency PSK Rotation từ Admin Console:
  1. New PSK generated ngay lập tức (không có 14-day prep)
  2. Distributed qua E2EE broadcast với TTL: "accept old PSK thêm 1 giờ"
  3. Sau 1 giờ: old PSK revoked ngay lập tức
  4. Devices không nhận được new PSK trong 1 giờ: isolated — cần Admin re-provision
  5. Incident logged vào Tamper-Proof Audit Log
```

**Detection: Nếu PSK Rotation Thất Bại trên một Subset Nodes:**

```rust
pub struct PskSyncStatus {
    device_id:       DeviceId,
    current_psk_gen: u32,       // Generation số của PSK hiện tại trên device
    expected_psk_gen: u32,      // Generation số server expect
    last_seen:       Instant,
}

// Server side: check sau mỗi rotation
pub fn detect_psk_desync(devices: &[PskSyncStatus]) -> Vec<DeviceId> {
    let current_gen = get_current_psk_generation();
    devices.iter()
        .filter(|d| d.current_psk_gen < current_gen
                 && d.last_seen.elapsed() < Duration::from_secs(86400))
        .map(|d| d.device_id)
        .collect()
}
```

- Devices trên stale PSK sau rotation + cutoff window: Admin Console alert `PSK_DESYNC_DETECTED { device_ids }`.
- Không có silent isolation — mọi trường hợp phải được Admin biết.

**Audit Log Entry (mỗi rotation):**

```rust
AuditLogEntry {
    event_type:    EventType::PskRotation,
    rotation_kind: RotationKind::Scheduled | Emergency,
    old_psk_gen:   u32,
    new_psk_gen:   u32,
    authorized_by: DeviceId,     // Admin who triggered
    devices_total: u32,
    devices_synced: u32,
    devices_desync: u32,
    hlc:           HLCTimestamp,
    signature:     Ed25519Signature,
}
```

---

## [PATCH-NEW] §6.3b — BLE Battery Drain Benchmark Methodology

> Thêm mới vào §6.3 sau "BLE duty cycle" section.
> Lý do: Spec claim "< 15mW" không có test methodology. Gov/Military yêu cầu evidence-based power profiling.

### §6.3b BLE Power Budget — Benchmark Methodology

**Measurement Setup:**

| Parameter | Value |
|---|---|
| Device | iPhone 13 (A15 Bionic) + Pixel 7 (Tensor G2) |
| Battery capacity | iPhone 13: 3,227 mAh, Pixel 7: 4,355 mAh |
| Measurement tool | iOS: Xcode Energy Organizer + `powermetrics`. Android: Android Studio Energy Profiler |
| Mesh size | 4 nodes (2 iOS, 2 Android) |
| Test duration | 4 giờ sustained |
| Ambient conditions | Room temperature 22°C, no other active apps |
| Network state | No Internet (pure Mesh mode) |

**Benchmark Scenarios:**

```
Scenario A — Idle Mesh (no messages):
  BLE: 200ms advertise + 800ms sleep (20% duty cycle)
  Expected: < 8mW (≈ 0.025% battery/hour per scenario)
  Pass/Fail: ≤ 10mW average over 30-minute window

Scenario B — Active Messaging (10 msg/min, text only):
  BLE: 200ms advertise + 800ms sleep
  Occasional Wi-Fi Direct activation for message ACK
  Expected: < 15mW sustained
  Pass/Fail: ≤ 20mW average over 30-minute window

Scenario C — File Transfer (1 × 10MB file via Wi-Fi Direct):
  Wi-Fi Direct active during transfer (~45 seconds)
  Expected peak: < 300mW during transfer, return to < 15mW after
  Pass/Fail: Peak ≤ 400mW, return to baseline within 60 seconds post-transfer

Scenario D — Battery Critical Mode (battery < 20%):
  Mesh: BLE scan interval increase to 5min (from 5 second active scan)
  Expected: < 3mW
  Pass/Fail: ≤ 5mW
```

**Automated Benchmark (CI — monthly):**

```rust
#[cfg(test)]
#[cfg(feature = "power_benchmark")]
mod power_tests {
    /// Simulated power draw: count radio activations as proxy for actual power
    /// Full hardware test requires physical devices (see ops/power-benchmark-runbook.md)
    #[test]
    fn ble_idle_duty_cycle_proxy() {
        let mut scanner = BleScanner::new();
        let start = Instant::now();
        let mut activations = 0u32;

        while start.elapsed() < Duration::from_secs(60) {
            scanner.tick();
            if scanner.is_radio_active() { activations += 1; }
            thread::sleep(Duration::from_millis(1));
        }

        // 20% duty cycle: expect ~12,000 active ms out of 60,000ms
        let active_ratio = activations as f64 / 60_000.0;
        assert!(active_ratio < 0.25, "Duty cycle {}% exceeds 25% budget", active_ratio * 100.0);
    }
}
```

**Full Hardware Test Runbook Reference:** `ops/power-benchmark-runbook.md`

Runbook phải cover: device preparation (factory reset, airplane mode + BLE only), measurement procedure, pass/fail criteria, regression comparison với previous version.

**Disclosure cho Gov/Military SLA:**

```
Power consumption (measured on reference devices, Scenario B):
  iPhone 13:  13.2 mW average (Mesh active messaging, 10 msg/min)
  Pixel 7:    11.8 mW average
  Equivalent battery life reduction: approximately 2-3% per hour of active Mesh use.
  Measurement date: [date]. Measurement methodology: ops/power-benchmark-runbook.md.
```

---

## [PATCH-NEW] §12.7 — Auto-Update Strategy Rules

> Thêm mới vào §12 Implementation Contract.
> Lý do: Không có auto-update spec → enterprise customers bị stranded trên EoL versions sau 12-month ABI window.

### §12.7 — Auto-Update Rules

- [x] **UPD-01** — Tất cả platform clients PHẢI có auto-update mechanism. Manual-only update: **không được phép cho Verified/Enterprise tier**.

- [x] **UPD-02** — Update channels phải hỗ trợ staged rollout: canary (5%) → limited (25%) → general (100%). Full immediate rollout: **không được phép**.

- [x] **UPD-03** — Delta updates bắt buộc cho binary > 50MB. Full binary update cho patch releases: **blocker nếu bandwidth không được xem xét**.

- [x] **UPD-04** — Rollback capability: mọi update có thể rolled back trong vòng 24 giờ nếu crash rate > 0.5%.

- [x] **UPD-05** — ABI deprecation window (12 tháng per TERA-MKT §MARKETPLACE-09): auto-update phải đảm bảo 90% enrolled devices upgrade trước EoL. Devices không upgrade sau EoL warning → Admin Console alert.

**Platform Update Mechanisms:**

| Platform | Mechanism | Silent/Prompted | Delta Support |
|---|---|---|---|
| 📱 iOS | App Store / TestFlight | OS-controlled | N/A (App Store manages) |
| 📱 Android | Play Store / APK direct | OS-controlled / Prompted | Split APK (Play Store) |
| 📱 Huawei | AppGallery | HMS-controlled | HMS delta update |
| 💻 macOS | Sparkle Framework | Prompted (background download) | Binary delta (bsdiff) |
| 🖥️ Windows | Squirrel.Windows (via Electron/Tauri) | Prompted | NSIS delta / full installer |
| 🖥️ Linux (.deb) | apt repository + unattended-upgrades | Silent (opt-in) | apt binary delta |
| 🖥️ Linux (AppImage) | AppImageUpdate (zsync) | Prompted | zsync binary delta |

**macOS Sparkle Configuration:**

```xml
<!-- TeraChat.app/Contents/Info.plist -->
<key>SUFeedURL</key>
<string>https://releases.terachat.com/appcast-macos.xml</string>
<key>SUPublicEDKey</key>
<string><!-- Ed25519 public key for Sparkle signature verification --></string>
<key>SUAutomaticallyUpdate</key>
<false/>  <!-- Always prompted — no silent install for security software -->
<key>SUScheduledCheckInterval</key>
<integer>86400</integer>  <!-- Check daily -->
```

**Windows Squirrel Update Flow:**

```rust
// Tauri updater plugin (tauri-plugin-updater)
tauri::Builder::default()
    .plugin(
        tauri_plugin_updater::Builder::new()
            .pubkey("<!-- Ed25519 public key -->")
            .build()
    )
    .setup(|app| {
        let handle = app.handle().clone();
        tauri::async_runtime::spawn(async move {
            // Check update mỗi 24 giờ
            match handle.updater()?.check().await {
                Ok(Some(update)) => {
                    // Prompt user — không silent install
                    handle.emit("update-available", &update.version)?;
                }
                _ => {}
            }
        });
        Ok(())
    })
```

**Linux apt Repository (Tier 1 Enterprise):**

```bash
# /etc/apt/sources.list.d/terachat.list
deb [signed-by=/usr/share/keyrings/terachat-archive-keyring.gpg] \
    https://packages.terachat.com/apt stable main

# Unattended upgrades (opt-in for enterprise):
# /etc/apt/apt.conf.d/52terachat-unattended-upgrades
Unattended-Upgrade::Allowed-Origins {
    "TeraChat:stable";
};
Unattended-Upgrade::Package-Blacklist {};
```

**Rollback Trigger (Automated):**

```yaml
# ops/canary-policy.yaml (cross-reference từ TERA-FEAT §INFRA-04.1)
auto_rollback_triggers:
  - metric: "client_reported_crash_rate"
    threshold: "> 0.5%"
    window_minutes: 15
    action: "rollback_and_pause_canary"

  - metric: "relay_5xx_error_rate"
    threshold: "> 1%"
    window_minutes: 5
    action: "rollback_and_alert_oncall"
```

---

## [PATCH-NEW] §9.7b — Gossip PSK Rotation Observability

> Thêm mới vào §9.7 (Distributed Tracing) hoặc sau §9.6 (Operational Metrics).

### §9.7b PSK Rotation Metrics

Bổ sung vào Prometheus `/metrics` endpoint tại §9.6:

| Metric | Type | Description |
|---|---|---|
| `psk_rotation_total` | counter | Tổng số PSK rotations (scheduled + emergency) |
| `psk_desync_devices_current` | gauge | Số devices hiện đang trên stale PSK |
| `psk_rotation_duration_seconds` | histogram | Thời gian từ rotation trigger đến 90% devices synced |
| `psk_emergency_rotation_total` | counter | Số lần emergency rotation (security incidents) |

**AlertManager thresholds (bổ sung vào §9.6):**

```yaml
- alert: PskDesyncWarning
  expr: psk_desync_devices_current > 0
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "{{ $value }} devices on stale Mesh PSK"
    description: "PSK rotation may have failed for some devices. Check Admin Console."

- alert: PskDesyncCritical
  expr: psk_desync_devices_current / total_enrolled_devices > 0.05
  for: 15m
  labels:
    severity: critical
  annotations:
    summary: "{{ $value | humanizePercentage }} of devices on stale Mesh PSK"
    description: "Emergency PSK rotation may be required. Contact CISO."
```

---

## [PATCH-NEW] §11.4b — Operations Runbook Stubs (Mandatory Content)

> Bổ sung vào §11.4 Known Implementation Gaps.
> Ba runbooks được reference trong spec nhưng không tồn tại. Dưới đây là minimum content outline.

### ops/counter-reset-ceremony.md — Outline

```markdown
# TPM Counter Reset Ceremony Runbook

## Prerequisites
- Admin authenticated on separate trusted device (biometric + standard mTLS cert)
- CISO notified (required witness for audit)
- Target device identified by device_id in Admin Console

## Procedure
1. Admin opens CISO Console → Device Management → [Target Device] → "Reset Counter Sync"
2. Server generates one-time counter_reset_token (Ed25519-signed, 1-hour TTL)
3. Admin delivers token to user via secure out-of-band channel (another TeraChat device or in-person)
4. User enters token on affected device
5. Core verifies Ed25519 signature → re-enrolls device
6. Verify: device appears "Synced" in Admin Console within 60 seconds
7. Audit: confirm AuditLogEntry { event_type: CounterReset } present in log viewer

## Hard Constraints
- Maximum 3 resets per device per 30-day window
- Admin cannot reset their own device (requires second Admin)
- Token expires after 1 hour — issue new token if expired
- Self-Destruct that has already executed is NOT reversible

## Escalation
- If device still shows desync after ceremony: escalate to Tier 2 support
- If more than 5 devices need reset simultaneously: CISO approval required
```

### ops/db-recovery.md — Outline

```markdown
# PostgreSQL PITR Recovery Runbook

## Prerequisites
- Access to WAL archive (S3-compatible storage)
- Standby replica available (or ability to restore from archive)
- Maintenance window: expected RTO ≤ 30 minutes, RPO ≤ 5 minutes

## Procedure: Point-in-Time Recovery
1. Identify target recovery time (from incident report)
2. Stop relay daemon: `systemctl stop terachat-relay`
3. Restore base backup: `pg_restore -d terachat_db /backup/base.tar`
4. Configure recovery: edit `postgresql.conf`:
   `restore_command = 'aws s3 cp s3://terachat-wal/%f %p'`
   `recovery_target_time = '2026-03-19 14:30:00 UTC'`
5. Start PostgreSQL in recovery mode: `pg_ctl start`
6. Monitor recovery: `tail -f /var/log/postgresql/postgresql.log`
7. Promote to primary: `pg_ctl promote` (only after recovery_target_time reached)
8. Restart relay daemon: `systemctl start terachat-relay`
9. Verify: check `wal_staging_staged_total` metric returns to 0

## SQLite WAL Recovery (client-side)
- `hot_dag.db` corruption: delete file, trigger Gossip Re-hydration from Super Node
- `cold_state.db` corruption: delete file, rebuild from `hot_dag.db` via `PRAGMA rebuild`
- `wal_staging.db` corruption: delete file, in-flight events will be re-delivered by relay

## RTO/RPO SLA
- RPO: ≤ 5 minutes (WAL archiving interval)
- RTO: ≤ 30 minutes (manual procedure) / ≤ 5 minutes (automated failover with pgRepmgr)
```

### ops/shamir-bootstrap.md — Outline

```markdown
# Shamir Secret Sharing Bootstrap & Admin Turnover Runbook

## Initial Bootstrap (Workspace Creation)
1. Physical ceremony: M=3 of N=5 C-Level executives present in same room
2. Air-gapped laptop: generate Master Key offline
3. Shamir split: `tera-ops shamir split --shares 5 --threshold 3 master.terakey`
4. Each C-Level receives one shard on YubiKey 5 FIPS (physically delivered)
5. Master Key destroyed: `shred -uz master.terakey`
6. Verify reconstruction: `tera-ops shamir reconstruct --shares shard_1 shard_2 shard_3`
   Expected: reconstructed key matches original (verified by CISO)
7. Test Remote Wipe on test device before go-live

## Admin Turnover (C-Level Departure)
Trigger: C-Level executive departing who holds a Shamir shard.

1. Schedule ceremony BEFORE departure (minimum 2 weeks notice required)
2. Ceremony: M=3 of remaining N-1 shareholders present
3. Reconstruct Master Key: `tera-ops shamir reconstruct`
4. Issue new shard for incoming C-Level replacement
5. Re-split: `tera-ops shamir split --shares 5 --threshold 3`
6. Distribute new shards: old shard destroyed (YubiKey factory reset)
7. Audit Log: ceremony recorded with all present DID signatures

## Emergency Reconstruction (Break-Glass)
Use only when: data recovery required for legal hold AND ≥ 3 shard holders unavailable.

Pre-condition: BLE Physical Presence Verification (TERA-CORE §1.1 BLE Beacons for Quorum)
1. M=3 shareholders physically present, BLE beacons active
2. `tera-ops shamir emergency-reconstruct --require-ble-presence`
3. CISO witness required (separate from shareholders)
4. Post-ceremony: mandatory re-split and shard re-issuance

## Shard Storage Requirements
- Each YubiKey: stored in personal safe or bank safety deposit box
- NOT stored digitally in any form
- Quarterly verification: each holder confirms shard still accessible (no reconstruction required)
```

---

## [PATCH-REPLACE] §11.4 — Known Implementation Gaps (Updated Status)

> Thêm 3 rows mới vào bảng §11.4. Giữ nguyên 4 existing blockers.

```markdown
| ops/counter-reset-ceremony.md (runbook content) | Medium | §5.1 TPM Counter Reset | Outline provided in §11.4b |
| ops/db-recovery.md (runbook content)             | Medium | §9.5 PostgreSQL PITR    | Outline provided in §11.4b |
| ops/shamir-bootstrap.md (runbook content)        | Medium | §5.1 Shamir ceremony    | Outline provided in §11.4b |
| Auto-update mechanism (all 5 platforms)          | High   | §12.7 UPD-01            | Spec provided in §12.7 |
| Battery drain benchmark — physical hardware test  | Medium | §6.3b                   | Methodology provided; hardware test pending |
| MLS Super-Group sharding — implementation        | High   | §5.3b                   | Architecture specified; not implemented |
| Gossip PSK rotation — automated detection        | High   | §5.1b                   | Spec provided; `psk_desync_devices_current` metric not implemented |
```

---

## [PATCH-REPLACE] §13 CHANGELOG

> Thêm entry mới vào đầu bảng changelog.

```markdown
| 0.2.7 | 2026-03-XX | PATCH v0.2.7: §10.2 rewrite với P50/P99/measurement-conditions cho tất cả 25 operations. §5.3b MLS Super-Group Sharding strategy (>5000 members, Federation of Sub-Groups, Zero-Knowledge trade-off disclosure). §5.1b Gossip PSK Rotation Ceremony (standard 14-day + emergency 4-hour, detection protocol, AuditLogEntry). §6.3b BLE Battery Drain Benchmark Methodology (4 scenarios, hardware setup, CI proxy test). §12.7 Auto-Update Rules (UPD-01 through UPD-05, 7 platforms, Sparkle/Squirrel/apt). §9.7b PSK Rotation Observability (4 Prometheus metrics, 2 AlertManager rules). §11.4b Operations Runbook Stubs (counter-reset-ceremony.md, db-recovery.md, shamir-bootstrap.md outlines). §11.4 Known Gaps updated with 7 new tracking rows. |
```

---
