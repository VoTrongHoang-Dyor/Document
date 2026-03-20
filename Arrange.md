
### 1. Bỏ vào file `BusinessPlan.md` (Pháp lý, SLA & Niềm tin khách hàng)

**Vị trí đề xuất:** Thêm vào cuối mục **"2.6 AI Risk Governance (Lợi thế Quản trị Rủi ro AI)"** hoặc tạo một mục mới **"2.10 Trách nhiệm Pháp lý & Quản trị Rủi ro AI Tự trị"**.

**Nội dung bổ sung:**

```markdown
### 2.10 Trách nhiệm Pháp lý & Quản trị Rủi ro AI Tự trị (Autonomous AI Liability)
Khi AI trở thành lực lượng lao động chính và xử lý dữ liệu nhạy cảm (tài chính, hệ thống),TeraChat giải quyết bài toán niềm tin của ban lãnh đạo doanh nghiệp bằng nguyên tắc: **"TeraChat xây dựng rào cản, Doanh nghiệp giữ chùm chìa khóa."**

* **Ranh giới Trách nhiệm (Liability Shift):** TeraChat không cam kết AI hoàn hảo 100% (bởi AI không có tư cách pháp nhân). TeraChat chịu trách nhiệm cung cấp nền tảng Zero-Trust không có lỗ hổng lõi. Tuy nhiên, nếu Admin chủ động cấp quyền tối cao (root) cho AI bỏ qua các cảnh báo của hệ thống, trách nhiệm thuộc về pháp nhân doanh nghiệp.
* **Yêu cầu Tuân thủ Khách hàng:** Khuyến nghị các khách hàng Enterprise (Đặc biệt khối Tài chính/Ngân hàng) tham gia các gói Bảo hiểm An ninh mạng (Cyber Insurance) đối với các rủi ro ủy quyền AI ngoài ý muốn.
* **Hợp đồng SLA & ToS Minh bạch:** Mọi điều khoản SLA đều làm rõ: AI là một "Siêu trợ lý" bị giới hạn bởi OPA Policy. Các hành động mang tính phá hủy (xóa dữ liệu, chuyển tiền) nếu không đi qua luồng MFA do con người duyệt sẽ bị TeraChat Core từ chối ở cấp độ hệ thống.
```

### 2. Bỏ vào file `Function.md` (Quy trình vận hành & Tính năng)

**Vị trí đề xuất:** Bổ sung vào mục **"1. Chức năng dành cho Quản trị viên (Admin) -> Thiết lập Chính sách Bảo mật (OPA Policy & DLP)"** và mục **"2. Chức năng dành cho Người dùng cuối -> Quản lý Tin nhắn và Tài liệu"**.

**Nội dung bổ sung:**

```markdown
* **Quy trình "Human-in-the-Loop" (Con người trong vòng lặp) cho AI:**
  * **Smart Proposal:** AI tự trị (ClawBot/OpenClaw) có thể tự động soạn thảo hợp đồng, tổng hợp hóa đơn hoặc thiết lập lệnh chuyển tiền. Tuy nhiên, AI **không có quyền** thực thi cuối cùng (Execution).
  * **Mandatory Biometric Approval:** Mọi quyết định nhạy cảm do AI đề xuất bắt buộc phải tạo thành một thẻ `Smart Approval`. Một nhân sự cấp cao (VD: Kế toán trưởng) phải bấm nút "Duyệt" kèm xác thực sinh trắc học (FaceID/TouchID) hoặc mã PIN/YubiKey.
* **Nguyên tắc Đặc quyền Tối thiểu (Principle of Least Privilege cho AI):**
  * Quản trị viên thiết lập OPA Policy giới hạn quyền của từng AI Agent (Ví dụ: AI CSKH chỉ được đọc lịch sử mua hàng, tuyệt đối mù (blind) với số thẻ tín dụng).
  * **Thiết lập Hạn mức (Anomaly Detection Thresholds):** Admin buộc phải thiết lập hạn mức rủi ro cho các Agent có quyền tự trị. Ví dụ: Khóa quyền thực thi nếu AI giải ngân vượt 1,000,000 VNĐ/giao dịch hoặc tần suất lệnh vượt quá 50 lệnh/phút.
```

### 3. Bỏ vào file `Core_Spec.md` (Lõi Kỹ thuật & Dấu vết Kiểm toán)

**Vị trí đề xuất:** Thêm vào mục **"8. Non-Repudiation Egress Telemetry & Signed Audit Logs"** và mục **"3.2 Backend Services -> OPA/ABAC Policy Engine"**.

**Nội dung bổ sung:**

```markdown
#### Kiến trúc "Cầu dao tự động" đối với AI Tự trị (AI Autonomous Circuit Breaker)
* ☁️🗄️ **Anomaly Detection (Cảnh báo Bất thường Lõi):** Lõi Rust duy trì một state machine theo dõi tần suất và khối lượng API call của các `.tapp` AI. Bất kỳ giao dịch nào có dấu hiệu bất thường (như AI cố tình gọi lệnh API thanh toán liên tục, hoặc chuyển tiền khác dải IP thông thường) sẽ lập tức bị Circuit Breaker đóng băng (Freeze) toàn bộ tiến trình của AI đó và bắn cảnh báo đỏ (Priority 0) về máy của CISO.
* 🗄️ **Tamper-Proof AI Audit Logging (Nhật ký không thể chối bỏ):** - Mọi thao tác "Trao chìa khóa" (Cấp quyền API cho AI) từ Admin đều phải được ký bằng `Device_Key` (Ed25519).
  - Mọi luồng suy luận và lệnh gọi của AI Agent đều được băm (BLAKE3) và lưu vào chuỗi CRDT Audit Log cục bộ không thể sửa xóa.
  - **Mục đích pháp lý:** Nếu một sự cố xảy ra (VD: Hacker thao túng AI), CISO có thể trích xuất chính xác theo mili-giây: Ai là người đã cấp quyền, AI đã lấy dữ liệu từ đâu, và con người nào đã bấm "Approve" cho lệnh đó. Log này đủ tiêu chuẩn làm bằng chứng số (Digital Forensics).
```

---

## Mục Mới: Hybrid Infrastructure Client Behavior [ARCHITECTURE] [PLATFORM]

### HYBRID-01: Client-Side Relay Discovery & Connection Logic

> **Nguyên tắc:** Client không biết sự tồn tại của dedicated Core server. Client chỉ biết VPS relay endpoints. Toàn bộ routing logic nằm trong Lõi Rust — UI không tham gia.

- 📱💻🖥️ **Relay Endpoint Discovery:** Lõi Rust đọc relay endpoint list từ `config.yaml` (on-premise) hoặc từ DNS SRV record `_terachat._udp.relay.terachat.io` (cloud). Endpoint list được ký Ed25519 bởi `TeraChat_Internal_CA` — client verify signature trước khi sử dụng.
- 📱💻🖥️ **QUIC Connection Establishment:**

```text
  Client Rust Core
       │ 1. Resolve relay endpoint (DNS SRV / config.yaml)
       │ 2. QUIC 0-RTT handshake tới VPS node gần nhất
       │ 3. ALPN: "terachat/1.0" — từ chối nếu server không hỗ trợ
       │ 4. Certificate verify: SPKI pin vs bundled hash
       │ 5. Gửi E2EE ciphertext stream — không biết VPS forward sang đâu
       ▼
  VPS Relay (transparent to client)
       │ WireGuard + mTLS tunnel → Dedicated Core
```

- 📱💻🖥️ **SPKI Pin cho Relay Endpoint:** `manifest.yaml` / hardcoded trong binary chứa `sha256(SubjectPublicKeyInfo)` của relay TLS cert. Rustls từ chối kết nối nếu pin không match — ngay cả CA-signed cert hợp lệ cũng bị reject nếu không match pin.
- 📱💻🖥️ **Relay Failover (Client-Side):** Lõi Rust maintain ordered list relay endpoints theo RTT đo được. Nếu endpoint hiện tại trả về lỗi (503 `RELAY_CORE_UNREACHABLE` hoặc TCP reset):
  1. Thử relay endpoint tiếp theo trong list (< 100ms)
  2. Nếu tất cả relay fail → ALPN fallback state machine (§4.3 gRPC → WSS)
  3. Nếu tất cả transports fail → Survival Mesh Mode (BLE/Wi-Fi Direct)

### HYBRID-02: Circuit Breaker UX — Transparent Failure Handling

> **Nguyên tắc:** Khi Core unreachable (Circuit Breaker OPEN), client không được trải nghiệm silent failure. Lỗi phải rõ ràng và actionable.

- 📱💻🖥️ **503 Response Handling:** Khi VPS relay trả về `RELAY_CORE_UNREACHABLE`:
  - Lõi Rust emit `NetworkEvent::RelayCircuitOpen { retry_after_ms: u64 }`
  - UI hiển thị: banner amber *"Máy chủ đang khởi động lại. Tin nhắn sẽ gửi sau ~30 giây."*
  - Lõi Rust queue outgoing messages vào `hot_dag.db` local với trạng thái `PENDING_RELAY`
  - Auto-retry sau `retry_after_ms` — không cần user action
- 📱💻🖥️ **Message Queue trong Circuit Open Window:**

```rust
  // core/src/relay/circuit_breaker.rs
  pub enum MessageQueueBehavior {
      /// Tin nhắn text: queue vào hot_dag.db, retry khi relay phục hồi
      QueueForRetry { max_queue_size_kb: usize },
      /// File > 10MB: block và hiện thông báo, không queue
      BlockLargePayload,
      /// Emergency SOS: bypass circuit breaker, thử mọi path kể cả Mesh
      EmergencyBypass,
  }
```

- 📱💻🖥️ **UI State Mapping:**

```
  NetworkEvent::RelayCircuitOpen   → Banner amber "Đang kết nối lại..."
  NetworkEvent::RelayCircuitHalfOpen → Banner amber mờ "Đang kiểm tra..."  
  NetworkEvent::RelayCircuitClosed  → Banner tắt, flush pending queue
  NetworkEvent::AllRelaysFailed     → Kích hoạt Survival Mesh prompt
```

### HYBRID-03: WireGuard/mTLS Cert Lifecycle — Client-Transparent

> **Phần này đặc tả hành vi của relay daemon và Core — không có client-facing behavior. Ghi vào đây để developer relay daemon tham chiếu.**

- ☁️ **Relay Daemon Cert Auto-Renewal:**

```bash
  # /etc/terachat/relay/renew_certs.sh
  # Chạy hàng ngày lúc 02:00 UTC qua systemd timer
  
  CERT_DAYS_REMAINING=$(openssl x509 -noout -enddate -in /etc/terachat/relay/client.pem \
    | awk -F= '{print $2}' | xargs -I{} date -d {} +%s \
    | xargs -I{} echo "( {} - $(date +%s) ) / 86400" | bc)
  
  if [ "$CERT_DAYS_REMAINING" -lt 30 ]; then
    # Request new cert từ Vault PKI engine của Core
    vault write pki/issue/relay-nodes \
      common_name="relay-${REGION}.internal.terachat.io" \
      ttl="90d" \
      > /tmp/new_cert.json
    
    # Atomic swap: không restart daemon, sử dụng SIGHUP reload
    jq -r .data.certificate /tmp/new_cert.json > /etc/terachat/relay/client.pem
    jq -r .data.private_key /tmp/new_cert.json > /etc/terachat/relay/client.key
    kill -HUP $(cat /var/run/terachat-relay.pid)
    
    # Verify new cert loaded
    openssl s_client -connect core.internal:8443 -cert /etc/terachat/relay/client.pem 2>&1 \
      | grep "Verify return code: 0" || { echo "CERT_RELOAD_FAILED" | logger; exit 1; }
  fi
```

- ☁️ **Zero-Downtime Cert Reload:** Relay daemon hỗ trợ `SIGHUP` để reload TLS config mà không drop existing connections. QUIC connections đang active tiếp tục dùng old cert cho đến khi kết thúc gracefully. New connections dùng cert mới ngay sau reload.

### HYBRID-04: Sovereign Deployment Mode — Client Configuration

> **Khi enterprise tự host toàn bộ infrastructure (không có TeraChat cloud VPS), client cần cấu hình để trỏ về internal relay nodes.**

- 💻🖥️ **Admin-provided `config.yaml`:**

```yaml
  # /etc/terachat/config.yaml — on-premise sovereign deployment
  
  relay_endpoints:
    - address: "relay-01.corp.acme.vn:443"
      spki_pin: "sha256/BASE64_OF_SPKI_HASH"
      region: "HAN"
      priority: 1
    - address: "relay-02.corp.acme.vn:443"
      spki_pin: "sha256/BASE64_OF_SPKI_HASH_2"
      region: "HCM"
      priority: 2
  
  # Bắt buộc đặt false nếu relay internal không có Internet access
  telemetry_enabled: false
  
  # CRL update: manual import thay vì auto-fetch
  crl_update_mode: "manual"  # hoặc "auto" (default, cần Internet)
  
  # Sovereign: tắt hoàn toàn DNS SRV discovery
  relay_discovery_mode: "static"  # hoặc "dns_srv" (default)
  
  # Offline TTL override cho GovMilitary tier
  offline_ttl_hours: 720  # 30 ngày
```

- 💻🖥️ **Enterprise MDM Distribution:** `config.yaml` được push qua MDM (Microsoft Intune, Jamf) đến tất cả thiết bị trong organization. Lõi Rust đọc `config.yaml` tại startup, verify Ed25519 signature của file (ký bởi `Enterprise_Config_Signing_Key`) trước khi áp dụng.
- 📱 **Mobile (iOS/Android) — MDM Profile:**

```xml
  <!-- MDM profile: com.terachat.relay-config -->
  <key>TeraChat_RelayConfig</key>
  <dict>
    <key>relay_endpoint_1</key>
    <string>relay-01.corp.acme.vn:443</string>
    <key>spki_pin_1</key>
    <string>sha256/BASE64_OF_SPKI_HASH</string>
    <key>discovery_mode</key>
    <string>static</string>
    <key>offline_ttl_hours</key>
    <integer>720</integer>
  </dict>
```

### HYBRID-05: Observability Client-Side Hooks

- 📱💻🖥️ **Trace ID Propagation:** Lõi Rust sinh `trace_id = UUID_v7()` cho mỗi outgoing message. `trace_id` được embed vào QUIC stream header (không vào QUIC payload — để tránh làm phình ciphertext). VPS relay và Core forward `trace_id` trong OTLP span. Admin Console có thể tìm message theo `trace_id` để debug latency.
- 📱💻🖥️ **Client-Side Relay Metrics (Local Only):**

```rust
  // Metrics được giữ local, không gửi về TeraChat cloud
  // Chỉ available trong Admin Console của chính tenant
  pub struct RelayMetrics {
      pub current_relay_endpoint: String,
      pub current_relay_latency_ms: f64,
      pub circuit_breaker_state: CircuitBreakerState,
      pub pending_messages_count: usize,   // queue khi circuit open
      pub last_successful_forward_at: HLC,
      pub fallback_transport: Option<Transport>, // gRPC/WSS nếu QUIC blocked
  }
```

- 📱💻🖥️ **UI Indicator — Relay Health Badge:**
  - Online (relay healthy): indicator xanh bình thường — không hiển thị relay detail
  - Circuit Half-Open: indicator amber nhỏ (dot, không phải banner)
  - Circuit Open: banner amber (xem HYBRID-02)
  - Sovereign mode: indicator xanh với badge nhỏ *"Private"* — cho user biết đang dùng on-prem relay

### HYBRID-06: Cost Cap Enforcement — Relay Tier

- ☁️ **Admin Console — Infrastructure Budget:**
  Admin có thể đặt `max_relay_nodes: 10` trong Admin Console. Khi Terraform auto-scaling chạm limit → alert + block provision thêm node. Đảm bảo không có "runaway scaling" do traffic spike bất thường.
- ☁️ **Traffic-based Auto-Scale Policy:**

```hcl
  # terraform/modules/autoscale/policy.tf
  resource "terachat_autoscale_policy" "relay" {
    min_nodes     = 2   # Tối thiểu 2 node HA
    max_nodes     = 10  # Giới hạn từ Admin Console
    scale_up_at   = 0.70  # 70% CPU hoặc bandwidth saturation
    scale_down_at = 0.30
    cooldown_minutes = 10
    
    # Cost guard
    monthly_budget_usd = 600
    on_budget_exceeded = "alert_and_hold"  # không scale thêm, chỉ alert
  }
```

### HYBRID-07: Dart FFI / JSI — Relay-Aware IPC Changes

> **Thay đổi so với kiến trúc trước:** Client IPC giờ có thêm `relay_status` field trong Control Plane signal. UI phải xử lý trạng thái này để hiển thị banner đúng.

- 📱💻🖥️ **Updated `terachat_ipc.proto` — Control Plane:**

```protobuf
  // Bổ sung vào terachat_ipc.proto
  
  message NetworkStatusUpdate {
    enum RelayState {
      RELAY_HEALTHY = 0;
      RELAY_DEGRADED = 1;    // latency cao nhưng vẫn forward được
      RELAY_CIRCUIT_OPEN = 2; // Core unreachable, queueing messages
      RELAY_ALL_FAILED = 3;  // Tất cả relay fail, chuyển Mesh
    }
    
    RelayState relay_state = 1;
    string active_relay_endpoint = 2;  // e.g. "relay-HCM.terachat.io"
    uint32 relay_latency_ms = 3;
    uint32 pending_message_count = 4;  // số message đang queue
    uint64 retry_after_ms = 5;         // khi relay_state = CIRCUIT_OPEN
    Transport fallback_transport = 6;  // QUIC / GRPC / WSS / MESH
  }
```

- 📱 **Flutter Dart — Relay State Handler:**

```dart
  // Dart layer: xử lý NetworkStatusUpdate từ Rust Core
  void _handleNetworkStatusUpdate(NetworkStatusUpdate update) {
    switch (update.relayState) {
      case RelayState.RELAY_HEALTHY:
        _networkBannerController.hide();
        break;
      case RelayState.RELAY_CIRCUIT_OPEN:
        _networkBannerController.showAmber(
          message: 'Đang kết nối lại máy chủ... (${update.pendingMessageCount} tin nhắn đang chờ)',
          retryAfterMs: update.retryAfterMs,
        );
        break;
      case RelayState.RELAY_ALL_FAILED:
        _networkBannerController.showMeshPrompt();
        // Đề xuất kích hoạt Survival Mesh
        break;
    }
  }
```

- 📱💻🖥️ **Backward Compatibility:** Nếu client version cũ (không có relay state handling) kết nối vào relay tier, relay daemon không gửi `NetworkStatusUpdate` — chỉ gửi standard error codes. Client cũ fallback về ALPN state machine bình thường. Không có breaking change.

### HYBRID-08: WasmParity Gate — Relay-Transparent (Không thay đổi)

> **Xác nhận:** WasmParity CI gate (→ `PLATFORM-02`) không bị ảnh hưởng bởi relay tier. `.tapp` WASM execution xảy ra hoàn toàn tại client-side — relay chỉ forward ciphertext stream của `.tapp` egress sau khi đã qua `tera_egress_daemon`. Không cần thay đổi WasmParity spec.

### HYBRID-09: Dart FFI NativeFinalizer — Relay Buffer Safety

> **Vấn đề kế thừa từ `PLATFORM-14`:** Khi Circuit Breaker OPEN, Lõi Rust buffer outgoing messages trong `PENDING_RELAY` queue. Nếu Dart GC collect `TeraSecureBuffer` handle trước khi message được flush, có thể tạo dangling reference sang Rust-side queue.

- 📱 **Giải pháp — Relay Queue Keepalive:**

```dart
  class PendingRelayMessage {
    final TeraSecureBuffer _payloadBuffer;
    final String messageId;
    bool _flushed = false;
    
    // Keepalive: buffer không được release đến khi relay ACK
    void markFlushed() {
      _flushed = true;
      _payloadBuffer.releaseNow();  // explicit release sau khi relay ACK
    }
    
    // Finalizer chỉ là safety net, KHÔNG phải primary release path
    // Primary: Rust Core emit RelayACK → Dart gọi markFlushed()
  }
```

- 📱 **Rust Core — Relay ACK Signal:**

```rust
  // Khi relay thực sự forward message thành công:
  // Emit qua IPC Control Plane:
  // StateChanged { table: "pending_relay", version: new_v, event: RelayACK { message_id } }
  // Dart layer nhận và gọi message.markFlushed()
```

# TeraChat — High Latency Resolution for Remote Users

## Problem Analysis

Khi user ở xa VPS công ty (ví dụ: Hà Nội → TP.HCM, hoặc Vietnam → Singapore), có 4 root causes chính:

| Root Cause | Tác động | Severity |
|---|---|---|
| **Geographic RTT** | VPS đặt tại công ty → user phải route qua nhiều hop ISP | 🔴 Khẩn cấp |
| **Single-VPS SPOF** | Không có edge relay → mọi traffic dồn về 1 điểm | 🔴 Khẩn cấp |
| **Mobile Network Jitter** | 4G/5G packet loss cao → QUIC chưa tận dụng multipath | 🟡 Vừa |
| **WebRTC ICE Cold Start** | ICE Pool không được pre-warm cho vùng địa lý xa | 🟡 Vừa |
| **MLS TreeKEM Epoch Sync** | Epoch rotation cần round-trip về VPS gốc | 🟢 Nhẹ |

**Latency baseline ước tính:**

```
User (Di Linh) → Company VPS (HCM):  ~80ms RTT (lý tưởng)
User (Hà Nội)  → Company VPS (HCM):  ~40ms RTT (lý tưởng)
Thực tế mobile 4G với jitter:         ×3-5 = 120-400ms perceived
WebRTC ICE cold start:                +300-800ms additional
```

---

## Technical Solutions

### Solution A — GeoDNS + Lightweight Edge Relay (Khuyến nghị)

Triển khai **Micro-Relay Node** (~512MB VPS) tại các vùng địa lý chiến lược (Hà Nội, Đà Nẵng, Singapore). Node này chỉ là **Blind Relay** — không decrypt, không lưu trữ, chỉ forward ciphertext.

```
[User Mobile — Di Linh]
        │
        ▼ QUIC/UDP:443 (nearest edge)
[Edge Micro-Relay — Đà Nẵng]  ←── 20ms RTT
        │
        ▼ mTLS gRPC tunnel (persistent)
[Company VPS — HCM]           ←── 15ms RTT (backbone)
        │
        ▼
[Boss/Team Devices]
```

**Ưu điểm:** Giảm perceived latency ~60-70%. Edge node không cần HSM hay full crypto stack.
**Nhược điểm:** Chi phí thêm ~$10-20/tháng/node. Cần certificate pinning cho edge.

---

### Solution B — QUIC Multipath + Adaptive Codec

Tận dụng QUIC Connection Migration để bind nhiều network path đồng thời (4G + Wi-Fi khi có). Kết hợp adaptive codec cho voice.

```rust
// Rust Core: Multipath QUIC config
QuicConfig {
    multipath: true,
    path_probing_interval_ms: 500,
    initial_max_streams_bidi: 32,
    enable_0rtt: true,
}
```

**Voice Codec Ladder:**

| Network Condition | Codec | Bitrate | Latency |
|---|---|---|---|
| 4G Strong (>10Mbps) | Opus 128kbps | 128kbps | 20ms |
| 4G Moderate (2-10Mbps) | Opus 32kbps | 32kbps | 30ms |
| 4G Weak (<2Mbps) | AMR-NB | 4.75kbps | 40ms |
| BLE Mesh fallback | Text-only | N/A | 200ms |

---

### Solution C — Priority Message Queue + Offline-First Sync

Tin nhắn khẩn cấp (tagged `PRIORITY_URGENT`) được xử lý trước trong bounded MPSC channel, bypass queue thông thường.

---

## Product/UX Enhancements

### Feature: TeraSprint Mode (Chế độ Di chuyển Khẩn cấp)

Khi Rust Core phát hiện latency > 300ms sustained 10s → tự động kích hoạt:

1. **Auto-Relay Selection:** Ping tất cả known relay endpoints → chọn lowest RTT
2. **Message Priority Escalation:** Tin nhắn từ `PRIORITY_CONTACTS` list lên P0 queue
3. **Adaptive Media Quality:** Voice tự downgrade codec, video tự giảm resolution
4. **Predictive Pre-fetch:** Khi có kết nối mạnh (WiFi sân bay), pre-fetch 50 tin nhắn pending

### Feature: Network Resilience HUD

UI hiển thị real-time:

```
📍 Relay: Đà Nẵng Edge  |  RTT: 45ms  |  Path: 4G + WiFi  |  Mode: TeraSprint
```

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TERACHAT GEO-RESILIENT TOPOLOGY                  │
│                                                                     │
│  📱 Remote User                                                      │
│  (Di Linh/4G)                                                       │
│      │                                                              │
│      │ QUIC Multipath (4G primary + WiFi secondary)                 │
│      ▼                                                              │
│  ┌────────────────────┐   GeoDNS         ┌──────────────────────┐  │
│  │  Edge Relay Node   │ ─────────────── ▶│  Edge Relay Node     │  │
│  │  (Đà Nẵng / HN)   │                  │  (Singapore)         │  │
│  │  ~512MB RAM        │                  │  for intl roaming    │  │
│  │  Blind Relay Only  │                  └──────────────────────┘  │
│  └─────────┬──────────┘                                             │
│            │ mTLS Persistent Tunnel                                 │
│            ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Company VPS (HCM) — Control Plane              │    │
│  │  MLS Backbone · PostgreSQL · TURN HA · OPA Engine           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│            │                                                        │
│            ▼                                                        │
│  💻🖥️ Boss + Team Devices (LAN — <5ms internal)                      │
└─────────────────────────────────────────────────────────────────────┘
```

**WebRTC Call Path (TeraSprint Active):**

```
📱 Remote User
    │ SRTP via Edge TURN Relay (Đà Nẵng)
    ▼
[Edge TURN — Đà Nẵng]  ──── mTLS ────▶  [HA TURN — Company VPS]
                                                 │
                                         💻 Boss Device
```

---

## Document Changes

Dưới đây là nội dung bổ sung dạng Markdown cho từng file:

---

### `Core_Spec.md` — Bổ sung §3.6 và §5.43

````markdown
### 3.6 [ARCHITECTURE] [IMPLEMENTATION] Geo-Resilient Edge Relay Network

> **Bài toán:** User di chuyển xa VPS công ty gặp latency cao (>300ms), ảnh hưởng nghiêm trọng đến voice call và real-time messaging trong tình huống khẩn cấp.

#### Edge Micro-Relay Node Architecture

- ☁️ **Blind Relay Only:** Edge node KHÔNG decrypt, KHÔNG lưu trữ persistent data. Chỉ forward TLS ciphertext blob giữa client và Company VPS. Zero-Knowledge tuyệt đối tại edge.
- ☁️ **Single-Binary Rust Daemon (Edge Profile):** Build riêng binary `terachat-edge-relay` với `feature = ["relay_only"]` — loại bỏ MLS Backbone, PostgreSQL, OPA Engine. RAM footprint < 128MB trên VPS $10/tháng.
- ☁️ **GeoDNS Routing (Latency-Based):** DNS resolver trả về IP của edge node gần nhất dựa trên Anycast latency measurement. Fallback về Company VPS nếu tất cả edge node offline.
- ☁️ **mTLS Persistent Tunnel (Edge → Company VPS):** Edge node duy trì 1 kết nối mTLS gRPC persistent tới Company VPS — tránh TLS handshake overhead mỗi message. Connection re-established tự động với exponential backoff.
- ☁️ **Edge TURN Relay:** Edge node chạy coturn instance nhẹ cho WebRTC relay. SRTP traffic được forward qua mTLS tunnel về HA TURN cluster tại Company VPS.

#### Edge Node Deployment Topology

```text
[GeoDNS — latency-based routing]
         │
         ├──▶ [Edge Node — Hà Nội]    (~$10/mo VPS, 1 vCPU, 512MB RAM)
         │       └─ Blind Relay + coturn-lite
         ├──▶ [Edge Node — Đà Nẵng]   (~$10/mo VPS)
         │       └─ Blind Relay + coturn-lite  
         ├──▶ [Edge Node — Singapore] (~$15/mo VPS — cho roaming quốc tế)
         │       └─ Blind Relay + coturn-lite
         └──▶ [Company VPS — HCM]     (fallback, Control Plane chính)
                  └─ Full Stack
```

#### Edge Node Security Contract

- ☁️ **Certificate Pinning:** Lõi Rust trên client hard-code SPKI hash của Edge Node certificate. Edge node không thể impersonate Company VPS.
- ☁️ **No Persistent Storage:** Edge node chạy với `--no-disk-write` flag. Mọi buffer chỉ tồn tại trong RAM ephemeral pipe. Restart edge → không mất data (data đã ở Company VPS).
- ☁️ **Rate Limiting tại Edge:** Token Bucket per client-IP tại edge layer — chống DDoS trước khi traffic chạm Company VPS.
- ☁️ **Health Check & Auto-failover:** Company VPS ping edge nodes mỗi 10s. Edge node không respond trong 30s → GeoDNS tự remove khỏi rotation.

---

### 5.44 [SECURITY] [IMPLEMENTATION] TeraSprint Mode — Adaptive Network Resilience Engine

> **Bài toán:** User di chuyển xa, mạng không ổn định, cần duy trì liên lạc khẩn cấp với sếp/team mà không cần cấu hình thủ công.

#### Latency Detection & TeraSprint Trigger

- 📱💻🖥️ **Continuous RTT Monitoring:** Rust Core gửi QUIC PING frame mỗi 5s tới active relay endpoint, đo RTT. Kết quả lưu trong sliding window 30s (6 samples). `avg_rtt = sum(samples) / 6`.
- 📱💻🖥️ **TeraSprint Activation Threshold:**
  - `avg_rtt > 300ms` sustained 10s → kích hoạt `TeraSprint::Degraded`
  - `avg_rtt > 500ms` hoặc `packet_loss > 5%` → kích hoạt `TeraSprint::Critical`
  - `connection_timeout` → kích hoạt `TeraSprint::Survival` (Mesh Mode)
- 📱💻🖥️ **Relay Re-selection (Sub-50ms):** Khi TeraSprint kích hoạt, Rust Core parallel-probe tất cả known edge endpoints với TTL 200ms. Chọn endpoint có RTT thấp nhất. Swap kết nối trong < 50ms — UI không cảm nhận gián đoạn.

#### QUIC Multipath Binding

- 📱💻 **Simultaneous Path Probing:** Rust Core (sử dụng `quinn` crate) mở QUIC connection trên cả 4G interface và WiFi interface đồng thời. Path có RTT thấp hơn được dùng cho P0/P1 traffic. Path còn lại giữ warm làm standby.
- 📱💻 **QUIC Connection Migration:** Khi user chuyển từ WiFi → 4G (lên tàu, xe), QUIC Connection ID không đổi — kết nối migrate seamlessly. Không cần re-handshake. Latency spike < 100ms.
- 📱 **iOS Network.framework Integration:** Sử dụng `NWConnection` với `NWParameters.multipathServiceType = .handover` để iOS OS quản lý multipath tại system level, Rust Core nhận DataStream qua FFI.

#### Priority Message Queue (P0 Escalation)

```rust
pub enum MessagePriority {
    P0,  // Key Updates, SOS, Emergency — bypass all queues
    P1,  // Text từ PRIORITY_CONTACTS — latency < 200ms target  
    P2,  // Media, file transfer — best effort
}

pub struct TeraSprint {
    pub mode: TeraSprinted,
    pub active_relay: RelayEndpoint,
    pub rtt_ms: u32,
    pub priority_contacts: Vec<UserId>,  // pre-configured by user
}
```

- 📱💻🖥️ **PRIORITY_CONTACTS List:** User pre-configure danh sách (Boss, HR, Emergency contacts). Tin nhắn từ/đến list này tự động escalate lên P1. Admin có thể push PRIORITY_CONTACTS list qua OPA Policy cho toàn tenant.
- 📱💻🖥️ **P0 Bypass:** Tin nhắn tagged `EMERGENCY_FLAG` (SOS, Key Update, Critical Alert) bypass hoàn toàn rate limiting và queue — trực tiếp vào network socket. Consistent với §5.2 `EMERGENCY_SOS_FLAG QoS Bypass`.
````

---

### `Feature_Spec.md` — Bổ sung §PLATFORM-17 và §8.26

````markdown
### PLATFORM-17: TeraSprint Mode — Client Behavior

- 📱💻🖥️ **Auto-Relay Selection UI:** Khi TeraSprint kích hoạt, Network HUD trong status bar cập nhật:
  ```
  📍 Relay: Đà Nẵng Edge  |  RTT: 45ms  |  TeraSprint: Active
  ```
  Không có dialog — user tiếp tục làm việc không bị gián đoạn.

- 📱 **iOS QUIC Multipath (Network.framework FFI):**
  ```swift
  // Swift layer: expose multipath config xuống Rust
  let params = NWParameters.quic(alpn: ["h3"])
  params.multipathServiceType = .handover
  // FFI bridge: Rust nhận NWConnection handle, quản lý QUIC streams
  ```

- 📱 **Codec Auto-Downgrade (Voice Call):**
  - `rtt < 150ms` → Opus 128kbps (full quality)
  - `150ms < rtt < 300ms` → Opus 32kbps (acceptable)
  - `rtt > 300ms` || `packet_loss > 3%` → AMR-NB 4.75kbps (survival)
  - `TeraSprint::Survival` → Text-only, Whisper AI transcription nếu có RAM

- 📱 **Pre-fetch on Strong Connection:** Khi user kết nối WiFi mạnh (airport, hotel), Rust Core detect `rtt < 50ms` && `bandwidth > 5Mbps` → trigger background pre-fetch 100 pending messages + file stubs vào `hot_dag.db`. Chuẩn bị cho lúc di chuyển.

- 📱💻🖥️ **TeraSprint Persistent Config:** User setting "TeraSprint Priority Contacts" lưu trong `cold_state.db` (SQLCipher), sync qua E2EE Cloud Backup. Cấu hình một lần, hoạt động trên mọi thiết bị.

---

### 8.26 [IMPLEMENTATION] Predictive Network Switching & Relay Warm-up

> **Bài toán:** Khi user đang trên tàu/xe, mạng thay đổi liên tục. Cold start kết nối tới relay mới tốn 200-500ms — không chấp nhận được trong cuộc họp khẩn cấp.

- 📱💻 **Proactive Relay Warm-up:** Rust Core duy trì QUIC connection "warm" tới top-3 relay endpoints (theo RTT ranking). Connection idle nhưng alive — khi cần switch, không cần handshake mới. Cost: ~3 QUIC PING frames/30s per relay = negligible bandwidth.

- 📱 **NWPathMonitor Integration:** Lắng nghe `NWPathMonitor` để phát hiện network change trước khi latency tăng:
  ```swift
  pathMonitor.pathUpdateHandler = { path in
      if path.status == .satisfied {
          // Notify Rust Core qua FFI: new path available
          terachat_core_network_hint(path.availableInterfaces)
      }
  }
  ```
  Rust Core nhận hint → proactively probe relay endpoints trên interface mới → sẵn sàng migrate trước khi connection cũ drop.

- 📱💻 **Optimistic Message Send (Store-and-Forward Hybrid):** Trong TeraSprint mode, text message được commit vào `hot_dag.db` local NGAY LẬP TỨC (optimistic write) và hiển thị "Sent" trên UI. Rust Core retry gửi lên relay với exponential backoff. Khi deliver thành công → update delivery receipt. User không thấy "pending" spinner — UX liền mạch.

- 📱💻 **WebRTC ICE Pre-warming (TeraSprint):** Khi TeraSprint active, Rust Core proactively gather ICE candidates từ edge TURN server (không cần user initiate call). Khi user bấm "Call Boss", ICE candidates đã sẵn sàng → connection time < 500ms thay vì 2-3s.
````

---

### `Design.md` — Bổ sung §DESIGN-TERASPRINT-01

````markdown
### DESIGN-TERASPRINT-01: TeraSprint Mode Visual System

#### Network Resilience HUD (Status Bar Component)

| TeraSprint State | HUD Display | Color | Animation |
|---|---|---|---|
| **Inactive** (RTT < 150ms) | `● Online — 45ms` | `#24A1DE` Blue | Static dot |
| **Degraded** (150-300ms) | `⚡ TeraSprint — Đà Nẵng Edge — 180ms` | `#F59E0B` Amber | Pulse 1s |
| **Critical** (>300ms) | `⚡ TeraSprint Critical — 420ms` | `#EF4444` Red | Pulse 0.5s |
| **Switching Relay** | `↻ Finding best route...` | `#94A3B8` Gray | Spinner |
| **Survival (Mesh)** | `📡 Survival Mesh Active` | `#0F172A` Dark | Radar pulse |

```css
/* TeraSprint HUD Component */
.terasprint-hud {
  backdrop-filter: blur(8px);
  background: rgba(245, 158, 11, 0.15);  /* Amber glass */
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 20px;
  padding: 4px 12px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.5px;
}

.terasprint-pulse {
  animation: terasprint-pulse 1s ease-in-out infinite;
}

@keyframes terasprint-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
```

#### Voice Call Quality Indicator (In-Call UI)

Trong màn hình call, hiển thị codec hiện tại:

| Codec | Badge | Màu |
|---|---|---|
| Opus 128kbps | `HD Voice` | Xanh lục |
| Opus 32kbps | `Standard` | Xanh lam |
| AMR-NB | `Low Bandwidth` | Cam |
| Degraded | `⚠ Unstable` | Đỏ + pulse |

#### Priority Contact Indicator

Tin nhắn từ PRIORITY_CONTACTS hiển thị badge nhỏ:

```
🔴 [Priority]  Boss Nguyen Van A
   "Họp 3h chiều nay confirm chưa?"
   14:32  ✓✓
```

Badge `🔴 [Priority]` chỉ hiện khi TeraSprint active — không làm noise khi mạng bình thường.
````

---

### `Function.md` — Bổ sung §FUNC-12

````markdown
### FUNC-12: TeraSprint Emergency Communication Flow

**Kịch bản:** Nhân viên đang trên xe khách Hà Nội → Đà Nẵng, cần tham gia cuộc họp video khẩn cấp với sếp tại HCM.

**Luồng tự động:**

1. **T-0: Detect high latency**
   - Rust Core phát hiện `avg_rtt = 340ms` (sustained 10s)
   - Kích hoạt `TeraSprint::Degraded`
   - Parallel-probe 3 edge endpoints

2. **T+50ms: Relay selected**
   - Edge Đà Nẵng: 45ms RTT ← winner
   - Edge Hà Nội: 65ms RTT
   - Company VPS HCM: 340ms RTT ← bypass
   - HUD update: `⚡ TeraSprint — Đà Nẵng Edge — 45ms`

3. **T+100ms: ICE pre-warm triggered**
   - WebRTC ICE candidates gathered từ edge TURN Đà Nẵng
   - Candidates cached — ready for instant call

4. **T+?: User initiates video call**
   - ICE candidates already warm → connection < 500ms
   - Codec: Opus 32kbps (phù hợp 4G trên đường)
   - Video: 360p (adaptive — có thể 720p nếu mạng cho phép)

5. **T+?: Network drops (tunnel)**
   - QUIC Connection Migration triggered
   - Brief spike 50-100ms → auto-recover
   - User thấy slight glitch, không bị disconnect

6. **T+?: WiFi available (quán cà phê dừng chân)**
   - NWPathMonitor detect WiFi interface
   - QUIC migrate sang WiFi path
   - Codec upgrade: Opus 128kbps
   - HUD: `● Online — 18ms` (TeraSprint deactivated)
````

---

### `BusinessPlan.md` — Bổ sung §BIZ-EDGE-08

````markdown
### BIZ-EDGE-08: Edge Relay Network — Cost Model & Competitive Moat

**Infrastructure Cost (Edge Network):**

| Deployment Scale | Edge Nodes | Monthly Cost | Latency Improvement |
|---|---|---|---|
| Vietnam Only | 3 nodes (HN, ĐN, HCM) | ~$30/mo | 60-70% reduction |
| SEA Coverage | +Singapore, +Bangkok | +$25/mo | International roaming |
| Enterprise Custom | On-premise edge at client site | $0 (client hardware) | <10ms for internal |

**Competitive Differentiation:**

Đây là lợi thế cạnh tranh không thể copy nhanh của Slack/Teams:
- Slack/Teams phụ thuộc vào AWS/Azure multi-region (chi phí cao, data leaves Vietnam)
- TeraChat Edge Relay: **data stays encrypted, node có thể đặt tại data center Viettel/VNPT** — đáp ứng yêu cầu data residency của Gov/Banking Việt Nam

**Sales Pitch cho Enterprise:**
> *"Nhân viên field sales của bạn ở Tây Nguyên vẫn họp video HD với sếp ở HCM — không lag, không mất kết nối, không cần VPN phức tạp."*

**TeraSprint như một Premium Feature:**
- Community: GeoDNS routing (best-effort)
- Enterprise: Dedicated edge relay + priority queue + SLA 99.9% uptime
- GovMilitary: On-premise edge node deployment + air-gapped support
````

---
Dưới đây là phân tích kiến trúc trước khi viết spec. Ba vấn đề có một gốc rễ chung: **state boundary violation** — mỗi câu hỏi đều xuất phát từ việc một component cố gắng giữ state mà theo design nó không nên giữ. Giải pháp đúng là đẩy state về đúng owner của nó.

Giải pháp Q1 dùng `tokio::sync::watch` (không phải broadcast hay CancellationToken đơn lẻ) vì watch là single-value channel — đúng với semantics "cert generation hiện tại là gì". Q2 từ chối VPS journal hoàn toàn, đẩy EMDP state về client (đúng owner) và dùng Survival Mesh làm courier. Q3 tái kích hoạt eBPF/XDP trên dedicated server (đã deprecated chỉ cho shared VPS, không phải cho bare-metal), kết hợp mTLS device certificate làm primary cryptographic allowlist.---

## Nội dung bổ sung vào `Core_Spec.md`

```markdown
---

## 18. [SECURITY] [IMPLEMENTATION] QUIC Cert Generation Watch Protocol — Emergency Revocation in <500ms

> **Phạm vi:** Giải quyết vấn đề long-lived QUIC connections tồn tại với cert đã bị revoke sau `SIGHUP` reload. Áp dụng cho VPS Relay Daemon (→ §16). Không liên quan đến client-side cert hay `DeviceIdentityKey`.
>
> **Quyết định kiến trúc:** Dùng `tokio::sync::watch` (không phải `broadcast` hay `CancellationToken` đơn lẻ). Lý do: `watch` là single-value channel — semantics chính xác cho "cert generation hiện tại là gì". `broadcast` có thể drop messages khi receiver lag. `CancellationToken` không mang state (generation nào bị revoke). `AtomicU64` đơn lẻ không wake sleeping tasks.

### 18.1 [IMPLEMENTATION] Cert Generation State Machine

```rust
// core/src/relay/cert_revocation.rs

use std::sync::atomic::{AtomicU64, Ordering};
use tokio::sync::watch;

/// Thế hệ cert hiện đang hợp lệ. Tăng mỗi lần rotate hoặc revoke.
/// AtomicU64 cho phép per-packet check O(1) không cần lock.
pub static CURRENT_VALID_CERT_GEN: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Debug, PartialEq)]
pub enum CertRevocationEvent {
    /// Cert bình thường — giá trị là generation hợp lệ hiện tại
    Valid { generation: u64 },
    /// Cert bị revoke — generation cũ bị vô hiệu, generation mới đã load
    /// old_gen: generation bị compromise
    /// deadline_ms: thời gian drain tối đa (mặc định 450ms)
    Revoked { old_gen: u64, new_gen: u64, deadline_ms: u64 },
}

/// Sender nằm trong relay daemon main thread.
/// Receivers được clone cho mỗi connection task khi spawn.
pub struct CertRevocationBroadcaster {
    sender: watch::Sender<CertRevocationEvent>,
}

impl CertRevocationBroadcaster {
    pub fn new() -> (Self, watch::Receiver<CertRevocationEvent>) {
        let (tx, rx) = watch::channel(CertRevocationEvent::Valid { generation: 1 });
        (Self { sender: tx }, rx)
    }

    /// Gọi khi nhận SIGUSR2 (emergency revoke — khác SIGHUP rotate bình thường).
    /// Atomic update đảm bảo mọi task thấy new_gen ngay lập tức sau watch notify.
    pub fn emergency_revoke(&self, old_gen: u64, new_gen: u64) {
        CURRENT_VALID_CERT_GEN.store(new_gen, Ordering::SeqCst);
        // watch::send() wake tất cả receivers đang pending đồng thời — O(receivers)
        let _ = self.sender.send(CertRevocationEvent::Revoked {
            old_gen,
            new_gen,
            deadline_ms: 450,
        });
        tracing::warn!(
            security_event = "CERT_EMERGENCY_REVOKED",
            old_gen, new_gen,
            "Cert revocation broadcast to all connection tasks"
        );
    }
}
```

### 18.2 [IMPLEMENTATION] Connection Task — Drain Protocol

```rust
// core/src/relay/connection_handler.rs

use tokio::time::{timeout, Duration};
use zeroize::ZeroizeOnDrop;

/// State của một QUIC connection trong relay daemon.
/// cert_gen_at_spawn bất biến — gắn với cert đã dùng khi handshake.
pub struct RelayConnection {
    quic_conn: quinn::Connection,
    cert_gen_at_spawn: u64,
    revocation_rx: watch::Receiver<CertRevocationEvent>,
    // TLS session material: zeroize khi connection đóng
    tls_session_key: ZeroizingSessionKey,
}

#[derive(ZeroizeOnDrop)]
struct ZeroizingSessionKey(Vec<u8>);

impl RelayConnection {
    pub async fn run(mut self) {
        loop {
            tokio::select! {
                // Nhánh 1: xử lý QUIC packet bình thường
                result = self.quic_conn.accept_bi() => {
                    match result {
                        Ok((send, recv)) => {
                            // Per-packet validation: check AtomicU64 trước khi process
                            // Không cần lock — O(1) memory fence
                            let current_gen = CURRENT_VALID_CERT_GEN.load(Ordering::Acquire);
                            if current_gen != self.cert_gen_at_spawn {
                                // Cert đã bị rotate bình thường (SIGHUP)
                                // Connection này vẫn valid — tiếp tục với cert cũ
                                // cho đến khi drain hoặc client reconnect tự nhiên
                            }
                            tokio::spawn(forward_stream(send, recv));
                        }
                        Err(e) => {
                            tracing::debug!("QUIC connection closed: {}", e);
                            break;
                        }
                    }
                }

                // Nhánh 2: watch channel — wakes NGAY KHI sender update
                _ = self.revocation_rx.changed() => {
                    let event = self.revocation_rx.borrow().clone();
                    if let CertRevocationEvent::Revoked { old_gen, deadline_ms, .. } = event {
                        if old_gen == self.cert_gen_at_spawn {
                            // Cert của connection này bị revoke — bắt đầu drain
                            self.drain_and_close(Duration::from_millis(deadline_ms)).await;
                            break;
                        }
                        // old_gen khác cert_gen_at_spawn: revocation không liên quan
                        // Connection này dùng cert khác — tiếp tục bình thường
                    }
                }
            }
        }
        // ZeroizeOnDrop tự động ghi đè 0x00 lên tls_session_key khi self drop
    }

    /// Drain: dừng nhận stream mới, chờ stream cũ hoàn thành, force-close sau deadline.
    /// "Gracefully" = không corrupt in-flight ciphertext đang forward về Core.
    async fn drain_and_close(&mut self, deadline: Duration) {
        tracing::warn!(
            security_event = "CERT_REVOKE_DRAIN_START",
            cert_gen = self.cert_gen_at_spawn,
            deadline_ms = deadline.as_millis(),
        );

        // Phase 1: Đóng direction nhận — không accept stream mới
        // Streams đang mở (in-flight) vẫn tiếp tục forward
        self.quic_conn.close(
            0u32.into(),
            b"cert_revoked_draining",
        );

        // Phase 2: Chờ in-flight streams tự hoàn thành với deadline
        // Forward stream rất nhanh (chỉ cần đẩy bytes sang Core)
        // Thực tế: hầu hết drain xong trong <50ms
        let drain_result = timeout(deadline, async {
            // Tokio task tracker theo dõi active forward_stream tasks
            // Khi tất cả forward tasks done -> drain complete
            ACTIVE_FORWARD_TASKS.wait().await;
        }).await;

        match drain_result {
            Ok(_) => tracing::info!(
                security_event = "CERT_REVOKE_DRAIN_COMPLETE",
                "All in-flight packets forwarded before deadline"
            ),
            Err(_) => tracing::warn!(
                security_event = "CERT_REVOKE_DRAIN_TIMEOUT",
                "Drain deadline exceeded — forcing close. Some in-flight packets may be lost."
            ),
        }

        // Phase 3: ZeroizeOnDrop chạy tự động khi self drop sau break
        // tls_session_key bị ghi đè 0x00 trước khi OS reclaim memory
    }
}
```

### 18.3 [IMPLEMENTATION] Signal Handling — SIGUSR2 vs SIGHUP Phân biệt

> **Nguyên tắc phân vai:** `SIGHUP` = rotate cert bình thường (zero-downtime, không force-close connection cũ). `SIGUSR2` = emergency revoke (force-close tất cả connections dùng cert cũ trong 500ms).

```rust
// core/src/relay/signal_handler.rs

pub async fn run_signal_handler(broadcaster: Arc<CertRevocationBroadcaster>) {
    use tokio::signal::unix::{signal, SignalKind};

    let mut sighup  = signal(SignalKind::hangup()).unwrap();
    let mut sigusr2 = signal(SignalKind::user_defined2()).unwrap();

    loop {
        tokio::select! {
            _ = sighup.recv() => {
                // Rotate bình thường: load cert mới, connections cũ tiếp tục
                // Không broadcast revocation — connection cũ tự nhiên kết thúc
                let old_gen = CURRENT_VALID_CERT_GEN.load(Ordering::SeqCst);
                let new_gen = old_gen + 1;
                reload_tls_config(new_gen).await;
                CURRENT_VALID_CERT_GEN.store(new_gen, Ordering::SeqCst);
                tracing::info!(event = "CERT_ROTATED", old_gen, new_gen);
                // Không gọi broadcaster.emergency_revoke()
            }

            _ = sigusr2.recv() => {
                // Emergency revoke: private key bị compromise
                // PHẢI force-close tất cả connections dùng cert cũ
                let old_gen = CURRENT_VALID_CERT_GEN.load(Ordering::SeqCst);
                let new_gen = old_gen + 1;
                reload_tls_config(new_gen).await;
                // Broadcast → wake tất cả connection tasks đồng thời
                broadcaster.emergency_revoke(old_gen, new_gen);
                // 500ms sau: audit log confirm tất cả connections closed
                tokio::time::sleep(Duration::from_millis(550)).await;
                log_revocation_complete(old_gen).await;
            }
        }
    }
}
```

### 18.4 [SECURITY] Budget Phân Tích — 500ms Deadline

| Phase | Cơ chế | Thời gian |
|---|---|---|
| Signal nhận + watch update | OS signal delivery + `watch::send()` | ~0ms |
| Tokio scheduler wake tất cả tasks | Tokio runtime scheduling | 0-10ms |
| Stop accepting new QUIC streams | `conn.close()` | ~1ms |
| Drain in-flight streams (ciphertext forward) | Bytes đã buffered trong QUIC → Core | 10-100ms |
| Force-close timeout | `tokio::time::timeout(450ms)` | 0-450ms |
| `ZeroizeOnDrop` TLS session keys | SIMD ghi đè 0x00 | <2ms |
| **Tổng worst case** | | **~453ms < 500ms** |

- ☁️ **Audit Log Entry (Ed25519 signed):** Mỗi `CERT_EMERGENCY_REVOKED` event được ghi vào append-only audit log với: `{event_type, old_gen, new_gen, timestamp_hlc, connections_at_revoke: u32, connections_drained: u32, connections_force_closed: u32, relay_node_id}`, ký bằng relay node's `DeviceIdentityKey`.

---

## 19. [SECURITY] [IMPLEMENTATION] EMDP Zero-Loss Architecture — Client-Side Journal + Mesh Courier

> **Quyết định kiến trúc: KHÔNG dùng VPS-side EMDP journal.** Ba lý do không thể bỏ qua:
>
> 1. Vi phạm stateless invariant của VPS Relay Tier (→ §16.1). Thêm state vào VPS = tăng attack surface, phức tạp hóa ops.
> 2. Metadata leakage không thể ngăn: dù payload E2EE, traffic pattern "VPS đang buffer N entries" tiết lộ thời điểm failover và volume EMDP operations cho adversary quan sát network.
> 3. EMDP là low-frequency operation (device recovery scenario, ~1 lần/tháng/user) — không cần buffering optimization. Cost của VPS journal không tương xứng với lợi ích.
>
> **Giải pháp đúng:** Client đã có `hot_dag.db` với pattern `PENDING_RELAY` cho outgoing messages. EMDP_Journal là một table trong cùng database, cùng pattern, cùng SQLCipher protection.

### 19.1 [IMPLEMENTATION] EMDP_Journal Schema

```sql
-- Thêm vào hot_dag.db migration v2

CREATE TABLE IF NOT EXISTS emdp_journal (
    tx_id           TEXT PRIMARY KEY,           -- UUID v7 (monotonic, sortable)
    operation_type  TEXT NOT NULL,              -- 'KEY_ESCROW_SHARD' | 'EPOCH_RE_INDUCTION' | 'DEVICE_REVOKE'
    payload_enc     BLOB NOT NULL,              -- AES-256-GCM(DeviceIdentityKey-derived, serialized_emdp_op)
    recipient_device_pubkey BLOB NOT NULL,      -- Curve25519 pubkey của device nhận Welcome_Packet
    hlc_created     TEXT NOT NULL,              -- HLC timestamp khi tạo
    hlc_expires     TEXT NOT NULL,              -- HLC TTL: 30 ngày cho GovMilitary, 72h cho Standard
    status          TEXT NOT NULL DEFAULT 'PENDING_REPLAY',
                                                -- 'PENDING_REPLAY' | 'PENDING_MESH' | 'REPLAYED' | 'EXPIRED'
    ed25519_sig     BLOB NOT NULL,              -- Sign(DeviceIdentityKey, hash(tx_id || payload_enc || hlc_created))
    retry_count     INTEGER NOT NULL DEFAULT 0,
    last_attempt_hlc TEXT
);

-- Index cho replay order và TTL cleanup
CREATE INDEX IF NOT EXISTS idx_emdp_status_hlc ON emdp_journal(status, hlc_created);
CREATE INDEX IF NOT EXISTS idx_emdp_expires    ON emdp_journal(hlc_expires, status);
```

### 19.2 [IMPLEMENTATION] Write Path — Ghi Journal khi Core Unreachable

```rust
// core/src/emdp/journal.rs

pub struct EmdpJournal<'db> {
    db: &'db SqlCipherConnection,
}

impl EmdpJournal<'_> {
    /// Gọi khi Core tunnel circuit breaker đang OPEN
    /// và có EMDP operation cần thực hiện.
    pub fn enqueue(
        &self,
        op: EmdpOperation,
        recipient_pubkey: &Curve25519PublicKey,
        device_key: &DeviceIdentityKey,  // Never leaves Secure Enclave — only used for KDF + sign
        ttl_profile: OfflineTTLProfile,
    ) -> Result<Uuid, EmdpError> {
        let tx_id = Uuid::now_v7();
        let hlc_now = HybridLogicalClock::now();
        let hlc_expires = hlc_now + ttl_profile.emdp_ttl_duration();

        // Derive encryption key từ DeviceIdentityKey — không lưu key, chỉ dùng để encrypt
        // Secure Enclave thực hiện KDF operation, không export private key
        let enc_key = secure_enclave::derive_key(
            device_key,
            &format!("emdp-journal-{}", tx_id),
        )?;
        let payload_enc = aes_256_gcm_encrypt(&enc_key, &op.serialize()?)?;
        enc_key.zeroize(); // ZeroizeOnDrop — key tồn tại < 1ms

        // Sign để chống tamper khi replay
        let sig_input = blake3::hash(&[
            tx_id.as_bytes(),
            &payload_enc,
            hlc_now.as_bytes(),
        ].concat());
        let ed25519_sig = secure_enclave::sign(device_key, sig_input.as_bytes())?;

        self.db.execute(
            "INSERT INTO emdp_journal
             (tx_id, operation_type, payload_enc, recipient_device_pubkey,
              hlc_created, hlc_expires, status, ed25519_sig)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'PENDING_REPLAY', ?7)",
            rusqlite::params![
                tx_id.to_string(),
                op.type_name(),
                payload_enc,
                recipient_pubkey.as_bytes(),
                hlc_now.to_string(),
                hlc_expires.to_string(),
                ed25519_sig.as_bytes(),
            ],
        )?;

        tracing::info!(
            event = "EMDP_JOURNAL_ENQUEUED",
            tx_id = %tx_id,
            op_type = op.type_name(),
            expires = %hlc_expires,
        );
        Ok(tx_id)
    }
}
```

### 19.3 [IMPLEMENTATION] Replay Path — Gửi lại khi Core Kết nối lại

```rust
// core/src/emdp/replay.rs

/// Chạy tự động khi NetworkEvent::RelayCircuitClosed được emit.
/// Replay theo thứ tự HLC để đảm bảo causality.
pub async fn replay_pending_journal(
    db: &SqlCipherConnection,
    core_client: &CoreRelayClient,
    device_key: &DeviceIdentityKey,
) -> Result<ReplayReport, EmdpError> {
    let pending = db.query_map(
        "SELECT tx_id, operation_type, payload_enc, recipient_device_pubkey,
                hlc_created, ed25519_sig
         FROM emdp_journal
         WHERE status = 'PENDING_REPLAY'
           AND hlc_expires > ?1
         ORDER BY hlc_created ASC",
        rusqlite::params![HybridLogicalClock::now().to_string()],
        EmdpJournalRow::from_row,
    )?;

    let mut report = ReplayReport::default();

    for row in pending {
        // Bước 1: Verify Ed25519 signature trước khi làm bất cứ điều gì
        let sig_input = blake3::hash(&[
            row.tx_id.as_bytes(),
            &row.payload_enc,
            row.hlc_created.as_bytes(),
        ].concat());
        if !device_key.verify_signature(&row.ed25519_sig, sig_input.as_bytes())? {
            // Entry bị tamper — đánh dấu FAILED và audit log
            db.execute("UPDATE emdp_journal SET status='TAMPERED' WHERE tx_id=?1",
                rusqlite::params![row.tx_id])?;
            report.tampered += 1;
            continue;
        }

        // Bước 2: Decrypt payload — key tồn tại trong RAM < 5ms
        let dec_key = secure_enclave::derive_key(device_key, &format!("emdp-journal-{}", row.tx_id))?;
        let plaintext = {
            let result = aes_256_gcm_decrypt(&dec_key, &row.payload_enc)?;
            dec_key.zeroize();
            result
        }; // ZeroizeOnDrop khi plaintext ra khỏi scope sau khi gửi

        // Bước 3: Gửi về Core qua tunnel
        match core_client.send_emdp_operation(&plaintext).await {
            Ok(ack) => {
                // Bước 4: Cập nhật status + ZeroizeOnDrop plaintext
                db.execute(
                    "UPDATE emdp_journal SET status='REPLAYED', last_attempt_hlc=?2 WHERE tx_id=?1",
                    rusqlite::params![row.tx_id, HybridLogicalClock::now().to_string()],
                )?;
                plaintext.zeroize(); // Explicit: không để plaintext tồn tại sau ACK
                report.replayed += 1;
            }
            Err(e) => {
                db.execute(
                    "UPDATE emdp_journal SET retry_count=retry_count+1, last_attempt_hlc=?2 WHERE tx_id=?1",
                    rusqlite::params![row.tx_id, HybridLogicalClock::now().to_string()],
                )?;
                plaintext.zeroize();
                report.failed += 1;
                tracing::warn!(event = "EMDP_REPLAY_FAILED", tx_id = %row.tx_id, error = %e);
            }
        }
    }
    Ok(report)
}
```

### 19.4 [SECURITY] [IMPLEMENTATION] Mesh Courier — GovMilitary Fallback

> **Bài toán:** Core unreachable kéo dài (>72h, ví dụ: natural disaster, siege scenario). Client A cần thực hiện EMDP Key Escrow nhưng cả Core lẫn Internet đều không khả dụng. Tuy nhiên, Client B trong cùng khu vực VẪN có đường kết nối về Core qua đường truyền khác (satellite, backup ISP).

```text
Client A (Core unreachable)
    │
    │ EMDP op in emdp_journal (status=PENDING_MESH)
    │
    │ BLE/Wi-Fi Direct — Survival Mesh (§5.2)
    ▼
Client B (has Core connectivity)
    │ Nhận EmdpMeshCourierPacket — verify signature
    │ Forward về Core thay cho A
    ▼
Dedicated Core
    │ ACK → relay qua Mesh về A
    ▼
Client A: update status='REPLAYED', ZeroizeOnDrop
```

- 📱💻🖥️ **EmdpMeshCourierPacket:** Đây là một CRDT event đặc biệt, được xử lý qua Survival Mesh bình thường. Packet chứa: `{tx_id, payload_enc_for_core, recipient_pubkey, courier_ed25519_sig}`. `payload_enc_for_core` được mã hóa bằng Core's public key (không thể đọc bởi courier). Courier B chỉ forward blob — không thể đọc nội dung.
- 📱💻🖥️ **Courier Accountability:** Mỗi lần một device làm courier, event được ghi vào CRDT audit log với chữ ký Ed25519 của courier device. Non-repudiation cho cả A (requester) và B (courier).
- 📱 **iOS/Android Lifecycle Safe:** `PENDING_MESH` operations được giữ trong `emdp_journal` qua các app restarts. Không có in-memory state cần bảo tồn — chỉ cần `hot_dag.db` survive.

### 19.5 [IMPLEMENTATION] TTL GC và EXPIRED Handling

```rust
// Chạy trong BGProcessingTask (iOS) / WorkManager (Android) — hàng ngày
pub fn garbage_collect_expired_emdp(db: &SqlCipherConnection) -> Result<usize> {
    let now = HybridLogicalClock::now().to_string();
    // Expired entries: không thể replay, không thể mesh courier
    // Mark EXPIRED — không DELETE vật lý (audit trail yêu cầu)
    let affected = db.execute(
        "UPDATE emdp_journal SET status='EXPIRED'
         WHERE status IN ('PENDING_REPLAY', 'PENDING_MESH')
           AND hlc_expires < ?1",
        rusqlite::params![now],
    )?;
    if affected > 0 {
        tracing::warn!(
            event = "EMDP_JOURNAL_ENTRIES_EXPIRED",
            count = affected,
            "EMDP operations expired before Core reconnection. Manual recovery required."
        );
        // Emit SecurityEvent::EmdpExpired → Admin Console alert
    }
    Ok(affected)
}
```

---

## 20. [SECURITY] [ARCHITECTURE] [IMPLEMENTATION] Sovereign Core Direct-Access Defense Protocol

> **Context:** Khi enterprise/gov client triển khai full sovereign mode (không có VPS Relay Tier), client devices kết nối thẳng đến Dedicated Core Server. Toàn bộ DDoS shield, IP masking của VPS tier biến mất. Spec này định nghĩa các lớp bảo vệ được thiết kế cho bare-metal dedicated server — không phụ thuộc cloud infrastructure.
>
> **Lưu ý về eBPF/XDP:** `CHANGELOG v0.3.6` deprecated eBPF/XDP để giải quyết deployment bottleneck trên **shared VPS** (không có `CAP_SYS_ADMIN`, noisy neighbor, shared NIC). Trên **dedicated bare-metal sovereign server** do enterprise sở hữu, eBPF/XDP là valid và được RE-ENABLE trong spec này. Hai trường hợp hoàn toàn khác nhau.

### 20.1 [ARCHITECTURE] Defense-in-Depth: 4 Lớp

```text
Internet / Client Devices
         │
         ▼
[Lớp 1] XDP Hook tại NIC driver — drop trước kernel TCP/IP stack
         │ Chỉ cho qua: QUIC/UDP từ IP có valid Proof-of-Work
         ▼
[Lớp 2] mTLS Client Certificate — cryptographic allowlist
         │ Chỉ cho qua: DeviceIdentityKey cert ký bởi Enterprise_CA (trong HSM)
         ▼
[Lớp 3] Tokio Application Rate Limiter — per-device token bucket
         │ Ngăn enrolled-but-compromised device flood
         ▼
[Lớp 4] QUIC Connection Migration Validator — chống IP spoofing
         │ Validate path challenge bằng DeviceIdentityKey signature
         ▼
Dedicated Core — hot_dag.db / MLS / KMS
```

### 20.2 [IMPLEMENTATION] Lớp 1 — eBPF/XDP Packet Filter (Re-enabled cho Sovereign)

> **Điều kiện bật:** `config.yaml` có `deployment_mode: "sovereign_direct"`. Relay mode (có VPS) không cần XDP vì VPS đã là shield.

```c
// bpf/xdp_quic_guard.c
// Biên dịch: clang -O2 -target bpf -c xdp_quic_guard.c -o xdp_quic_guard.o
// Load: ip link set dev eth0 xdp obj xdp_quic_guard.o

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/udp.h>
#include <bpf/bpf_helpers.h>

// Map: IP → token bucket state (refill rate, current tokens)
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 65536); // Tối đa 65536 unique source IPs
    __type(key, __u32);         // Source IP (IPv4)
    __type(value, struct token_bucket);
} ip_rate_map SEC(".maps");

// Map: IP → deny (True/False) — admin-managed denylist
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 4096);
    __type(key, __u32);
    __type(value, __u8);
} ip_denylist SEC(".maps");

struct token_bucket {
    __u64 last_refill_ns;
    __u32 tokens;
    __u32 refill_rate; // tokens per second
};

SEC("xdp")
int xdp_quic_guard(struct xdp_md *ctx) {
    // 1. Parse Ethernet + IP + UDP
    // (standard BPF parsing — elided for brevity)
    __u32 src_ip = iph->saddr;

    // 2. Bogon space validation — drop RFC1918 spoofed packets từ Internet
    // (không áp dụng nếu sovereign server trong private network)
    if (is_bogon(src_ip) && !is_internal_subnet(src_ip)) {
        return XDP_DROP;
    }

    // 3. Admin denylist — drop ngay tại NIC
    __u8 *denied = bpf_map_lookup_elem(&ip_denylist, &src_ip);
    if (denied && *denied) return XDP_DROP;

    // 4. Token bucket rate limiting — 1000 packets/s per IP (configurable)
    struct token_bucket *bucket = bpf_map_lookup_elem(&ip_rate_map, &src_ip);
    if (!bucket) {
        struct token_bucket new_bucket = {
            .last_refill_ns = bpf_ktime_get_ns(),
            .tokens = 1000,
            .refill_rate = 1000,
        };
        bpf_map_update_elem(&ip_rate_map, &src_ip, &new_bucket, BPF_ANY);
    } else {
        // Refill tokens theo thời gian đã qua
        __u64 now = bpf_ktime_get_ns();
        __u64 elapsed_ns = now - bucket->last_refill_ns;
        __u32 new_tokens = (elapsed_ns * bucket->refill_rate) / 1000000000ULL;
        bucket->tokens = min(bucket->tokens + new_tokens, bucket->refill_rate);
        bucket->last_refill_ns = now;

        if (bucket->tokens == 0) return XDP_DROP; // Rate limit exceeded
        bucket->tokens--;
    }

    // 5. Pass sang kernel — mTLS sẽ xử lý tiếp
    return XDP_PASS;
}
```

- 🗄️ **Admin Denylist Management:** Rust Core quản lý `ip_denylist` BPF map qua `libbpf-rs`. Khi phát hiện anomaly tại Lớp 3 hoặc 4, tự động thêm IP vào denylist với TTL 15 phút.
- 🗄️ **Throughput:** XDP drop trước kernel TCP/IP stack → ~10-15M packets/s trên NIC 10Gbps. Volumetric DDoS dưới 10Gbps bị absorb tại NIC mà không ảnh hưởng CPU hay memory của Rust Core.

### 20.3 [SECURITY] [IMPLEMENTATION] Lớp 2 — mTLS Cryptographic Allowlist

> **Đây là primary defense quan trọng nhất trong sovereign mode.** Kẻ tấn công không có `DeviceIdentityKey` cert được ký bởi `Enterprise_CA` (stored in HSM FIPS 140-3) không thể hoàn thành QUIC/TLS handshake — bị reject trước khi bất kỳ byte application data nào được xử lý.

```rust
// core/src/sovereign/mtls_verifier.rs

use rustls::{ServerConfig, server::ClientCertVerifier};

pub struct EnterpriseDeviceCertVerifier {
    /// Enterprise CA cert — loaded từ HSM, verify bằng SPKI pin
    enterprise_ca: CertificateDer<'static>,
    /// CRL cache — update 4h một lần hoặc khi nhận GOSSIP_CRL event
    crl_cache: Arc<RwLock<RevocationList>>,
}

impl ClientCertVerifier for EnterpriseDeviceCertVerifier {
    fn verify_client_cert(
        &self,
        end_entity: &CertificateDer,
        _intermediates: &[CertificateDer],
        _now: UnixTime,
    ) -> Result<ClientCertVerified, rustls::Error> {
        // Bước 1: Verify chain về Enterprise_CA (không phải public CA)
        let cert = parse_cert(end_entity)?;
        verify_cert_chain(&cert, &self.enterprise_ca)?;

        // Bước 2: Check CRL — device có bị revoke không?
        let crl = self.crl_cache.read();
        if crl.is_revoked(cert.serial_number()) {
            tracing::warn!(
                security_event = "DEVICE_CERT_REVOKED_AT_HANDSHAKE",
                serial = %cert.serial_number(),
            );
            return Err(rustls::Error::General("device certificate revoked".into()));
        }

        // Bước 3: Verify DeviceIdentityKey binding
        // Cert phải chứa extension OID 1.3.6.1.4.1.99999.1 (TeraChat DeviceID)
        // giá trị = Blake3(DeviceIdentityKey.public_bytes)
        let device_id_ext = cert.extension(TERACHAT_DEVICE_ID_OID)
            .ok_or(rustls::Error::General("missing device ID extension".into()))?;
        // Verify binding này trong Core — đảm bảo cert khớp với device đã enroll
        verify_device_id_binding(device_id_ext)?;

        Ok(ClientCertVerified::assertion())
    }
}

/// Tích hợp vào quinn (QUIC library)
pub fn build_sovereign_server_config(
    verifier: Arc<EnterpriseDeviceCertVerifier>,
    server_cert: CertificateDer,
    server_key: PrivateKeyDer,
) -> Result<ServerConfig> {
    ServerConfig::builder()
        .with_client_cert_verifier(verifier)  // Require client cert — no anonymous
        .with_single_cert(vec![server_cert], server_key)
}
```

- 🗄️ **CRL Update trong Sovereign Air-Gapped:** CRL được push từ HSM Admin Console vào Core qua authenticated IPC. Không cần Internet OCSP. Admin HSM ký CRL mới với `Enterprise_CA` private key — Core verify signature trước khi update `crl_cache`.
- 🗄️ **Enrollment:** New device enrollment yêu cầu Admin approve bằng YubiKey + Biometric tại HSM terminal. `DeviceIdentityKey` cert được HSM ký, deliver về device qua QR Key Exchange (→ Function.md §1 Offline Recovery Flow). Kẻ tấn công không thể self-enroll.

### 20.4 [IMPLEMENTATION] Lớp 3 — Tokio Application Rate Limiter (Sovereign Mode Config)

```rust
// core/src/sovereign/rate_limiter.rs
// Extends §3.5 Lightweight Micro-Core Relay với sovereign-specific config

pub struct SovereignRateLimiter {
    // Per-DeviceIdentityKey token bucket (không phải per-IP — mTLS đã verify identity)
    device_buckets: DashMap<DeviceId, TokenBucket>,
    config: SovereignRateLimitConfig,
}

pub struct SovereignRateLimitConfig {
    // Enrolled device: generous limit
    enrolled_device_rps: u32,       // default: 500 requests/s
    enrolled_device_burst: u32,     // default: 2000 burst

    // Anomaly threshold: enrolled nhưng behaving suspicious
    anomaly_rps_threshold: u32,     // default: 1000 rps trong 10s window
    anomaly_action: AnomalyAction,  // ADD_TO_XDP_DENYLIST | LOG_ONLY

    // Emergency: tất cả device limits được tighten khi phát hiện attack
    emergency_mode_rps: u32,        // default: 100 rps
    emergency_mode_trigger: u32,    // default: 5 devices hit anomaly trong 60s
}

impl SovereignRateLimiter {
    /// Gọi sau mTLS verify, trước khi route QUIC stream về Core
    pub fn check_and_consume(
        &self,
        device_id: &DeviceId,
        now: Instant,
    ) -> Result<(), RateLimitError> {
        let mut bucket = self.device_buckets.entry(device_id.clone())
            .or_insert_with(|| TokenBucket::new(self.config.enrolled_device_rps));

        if !bucket.try_consume(1, now) {
            // Rate limit hit — log và optionally add to XDP denylist
            self.handle_rate_limit_exceeded(device_id);
            return Err(RateLimitError::Throttled);
        }

        // Anomaly detection: moving average RPS
        if bucket.current_rps() > self.config.anomaly_rps_threshold as f64 {
            self.trigger_anomaly_action(device_id);
        }

        Ok(())
    }
}
```

### 20.5 [SECURITY] [IMPLEMENTATION] Lớp 4 — QUIC Connection Migration Validation

> **Attack surface:** QUIC Connection Migration cho phép client đổi IP/port mà không teardown connection (ví dụ: WiFi → 4G). Kẻ tấn công có thể gửi PATH_CHALLENGE với IP giả mạo để hijack connection của victim device.

```rust
// core/src/sovereign/quic_migration_guard.rs

/// Gắn vào quinn connection event handler
pub async fn validate_migration(
    conn: &quinn::Connection,
    new_path: SocketAddr,
    device_key: &DevicePublicKey,
    pending_challenge: &[u8; 8], // PATH_CHALLENGE data
) -> Result<(), MigrationError> {
    // Bước 1: Gửi PATH_CHALLENGE tới new_path
    // (quinn tự động làm theo RFC 9000 §9.3)

    // Bước 2: Yêu cầu device ký PATH_CHALLENGE bằng DeviceIdentityKey
    // Đây là extension của TeraChat trên top of standard QUIC migration
    let challenge_sig_request = ChallengeSignRequest {
        challenge_bytes: *pending_challenge,
        new_path_addr: new_path,
        hlc_timestamp: HybridLogicalClock::now(),
    };
    // Gửi qua existing QUIC stream (vẫn active trên old path)
    send_migration_sig_request(conn, &challenge_sig_request).await?;

    // Bước 3: Nhận signature từ device
    let sig_response = timeout(
        Duration::from_millis(500),
        recv_migration_sig_response(conn),
    ).await??;

    // Bước 4: Verify — chỉ DeviceIdentityKey thật mới ký được
    device_key.verify_signature(
        &sig_response.signature,
        &challenge_sig_request.serialize(),
    ).map_err(|_| {
        tracing::warn!(
            security_event = "QUIC_MIGRATION_SPOOFING_ATTEMPT",
            claimed_new_path = %new_path,
        );
        MigrationError::InvalidSignature
    })?;

    // Bước 5: Verify địa chỉ mới không phải bogon/spoofed
    if is_bogon_or_blocked(new_path.ip()) {
        return Err(MigrationError::BlockedAddress);
    }

    tracing::info!(
        event = "QUIC_MIGRATION_VALIDATED",
        new_path = %new_path,
        device_id = %device_key.device_id(),
    );
    Ok(())
}
```

### 20.6 [ARCHITECTURE] Defense Matrix — Sovereign vs Hybrid Mode

| Threat | Hybrid Mode (VPS tier có) | Sovereign Mode (direct connect) |
|---|---|---|
| Volumetric DDoS | VPS IP absorbs, Core ẩn | eBPF/XDP drop tại NIC (Lớp 1) |
| Unauthenticated flood | VPS stateless forward | mTLS reject tại TLS handshake (Lớp 2) |
| Enrolled device abuse | VPS Token Bucket | Tokio rate limiter (Lớp 3) |
| QUIC migration hijack | Minimal risk (VPS shield) | Challenge-sign validation (Lớp 4) |
| Core IP enumeration | Core IP ẩn hoàn toàn | Admin network policy: QUIC port 443 chỉ từ known subnets |
| BGP hijacking | Anycast mitigates | Enterprise BGP-sec (out-of-scope TeraChat) |

- 🗄️ **Network Policy khuyến nghị:** Trên sovereign server, `iptables`/`nftables` rule: chỉ accept UDP/443 (QUIC) từ IP range của employee network (VPN, office, known mobile APN). Không accept từ Internet chung. XDP handle traffic từ authorized range — DDoS từ ngoài range bị firewall block trước khi chạm NIC rule.
- 🗄️ **Deployment flag:** `config.yaml`:

  ```yaml
  deployment_mode: "sovereign_direct"  # Bật eBPF/XDP, bắt buộc mTLS client cert
  xdp_enabled: true                    # Yêu cầu: dedicated server, CAP_SYS_ADMIN
  mtls_require_device_cert: true       # KHÔNG tắt trong sovereign mode
  rate_limit_config: "sovereign"       # Tighter limits so với relay mode
  ```

```

---

## Nội dung bổ sung vào `Feature_Spec.md`

```markdown
---

## Mục Mới: Cert Revocation, EMDP Journal & Sovereign Defense — Client Behavior [SECURITY] [PLATFORM]

### HYBRID-10: Cert Revocation — Client-Side Reconnection Protocol

> **Client không biết về cert generation hay SIGUSR2.** Client chỉ thấy: connection bị đóng với QUIC error code `0x0` và message `cert_revoked_draining`. Spec này định nghĩa behavior của Lõi Rust trên client khi nhận disconnect này.

- 📱💻🖥️ **Phân biệt QUIC disconnect types:**
  ```rust
  // core/src/relay/client_connection.rs
  pub fn classify_disconnect(error: quinn::ConnectionError) -> DisconnectReason {
      match error {
          // Relay gửi close với message "cert_revoked_draining"
          quinn::ConnectionError::ApplicationClosed(app_close)
              if app_close.reason.as_ref() == b"cert_revoked_draining"
          => DisconnectReason::CertRevocation,

          // Relay gửi close với message "cert_revoked_draining" + code 0
          quinn::ConnectionError::ApplicationClosed(app_close)
              if app_close.reason.as_ref() == b"relay_core_unreachable"
          => DisconnectReason::CircuitBreakerOpen,

          // Mất kết nối thông thường
          quinn::ConnectionError::TimedOut |
          quinn::ConnectionError::Reset     => DisconnectReason::NetworkLoss,

          _ => DisconnectReason::Unknown,
      }
  }
  ```

- 📱💻🖥️ **Reconnect behavior theo disconnect reason:**

  ```rust
  match classify_disconnect(err) {
      DisconnectReason::CertRevocation => {
          // Relay đang drain và load cert mới.
          // Chờ 600ms (drain deadline 450ms + buffer) rồi reconnect với cert mới.
          // SPKI pin sẽ được fetch fresh từ DNS TXT record.
          tokio::time::sleep(Duration::from_millis(600)).await;
          reconnect_with_pin_refresh().await;
      }
      DisconnectReason::CircuitBreakerOpen { retry_after_ms } => {
          // Core unreachable — KHÔNG reconnect ngay, activate EMDP Journal
          activate_emdp_journal_mode().await;
          tokio::time::sleep(Duration::from_millis(retry_after_ms)).await;
          try_reconnect().await;
      }
      DisconnectReason::NetworkLoss => {
          // Standard ALPN fallback (§4.3 ALPN State Machine)
          run_alpn_fallback().await;
      }
  }
  ```

- 📱💻🖥️ **SPKI Pin Refresh khi cert rotate:** Khi relay cert được rotate (SIGHUP bình thường), SPKI pin cũ vẫn valid trong grace period 7 ngày (→ §HYBRID-03). Khi cert bị revoke (SIGUSR2 emergency), pin mới được publish vào DNS TXT record `_terachat-pin.relay.<region>.terachat.io` bởi TeraChat Ops (ký Ed25519). Client fetch pin mới qua DoH sau khi reconnect.

- 📱💻🖥️ **UI signal:** `DisconnectReason::CertRevocation` KHÔNG hiển thị error banner cho user — xảy ra và reconnect trong <1 giây, transparent. Nếu reconnect thất bại sau 3 lần → hiện banner amber "Đang kết nối lại..." như `CircuitBreakerOpen`.

### HYBRID-11: EMDP_Journal — Client Platform Implementation

> **Extension của §19 (Core_Spec.md):** Spec client-side cho từng platform.

- 📱💻🖥️ **Trigger conditions — khi nào ghi journal:**

  ```rust
  // EMDP operation cần ghi journal nếu:
  pub fn should_queue_to_journal(
      relay_state: &RelayCircuitState,
      op: &EmdpOperation,
  ) -> bool {
      matches!(relay_state, RelayCircuitState::Open | RelayCircuitState::HalfOpen)
      // Không journal khi circuit CLOSED — gửi thẳng về Core
  }
  ```

- 📱 **iOS — Journal persistence qua app restart:**
  - `emdp_journal` nằm trong `hot_dag.db` (SQLCipher). File này có `NSFileProtectionCompleteUntilFirstUserAuthentication` — accessible sau unlock lần đầu dù app background.
  - Replay trigger: `UIApplicationDidBecomeActiveNotification` + `NetworkEvent::RelayCircuitClosed`.
  - Background replay: đăng ký `BGProcessingTaskRequest` với identifier `com.terachat.emdp-replay`. iOS schedule khi device idle + sạc.

- 📱 **Android — Foreground Service cho replay:**

  ```kotlin
  // EMDP replay chạy trong WorkManager với constraint NetworkType.CONNECTED
  val replayWork = OneTimeWorkRequestBuilder<EmdpReplayWorker>()
      .setConstraints(Constraints.Builder()
          .setRequiredNetworkType(NetworkType.CONNECTED)
          .build())
      .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
      .build()
  WorkManager.getInstance(context).enqueueUniqueWork(
      "emdp_replay",
      ExistingWorkPolicy.KEEP,  // Không duplicate nếu đang chạy
      replayWork
  )
  ```

- 💻🖥️ **Desktop — Daemon-level replay:** `terachat-daemon` (§6.3 Desktop Native OS) xử lý EMDP replay độc lập với Tauri UI. Khi daemon detect tunnel reconnect, trigger replay ngay mà không cần UI mở.

- 📱💻🖥️ **UI indicator cho EMDP pending state:**

  ```
  Trạng thái journal           → UI signal
  ─────────────────────────────────────────
  0 PENDING_REPLAY entries     → Không hiển thị gì
  1-5 PENDING_REPLAY entries   → Dot nhỏ màu amber trên account avatar
  >5 PENDING_REPLAY entries    → Banner amber: "X thao tác đang chờ đồng bộ"
  EXPIRED entries xuất hiện    → Banner đỏ: "X thao tác hết hạn, cần Admin hỗ trợ"
  ```

- 📱💻🖥️ **Mesh Courier Request — UI flow:**
  Khi `PENDING_MESH` entries tồn tại và có Mesh peer khả dụng:
  1. Lõi Rust detect peer B có Core connectivity (qua Mesh heartbeat)
  2. Hỏi user: modal "Yêu cầu [Tên thiết bị B] chuyển tiếp thao tác bảo mật về máy chủ?"
  3. User approve → gửi `EmdpMeshCourierRequest` qua Survival Mesh
  4. Khi ACK nhận được: update status 'REPLAYED', ZeroizeOnDrop, banner biến mất

### HYBRID-12: Sovereign Mode — Client Detection & Adaptation

> **Client tự phát hiện sovereign mode từ `config.yaml` hoặc MDM profile — không phải từ server signal.** Thay đổi behavior dựa trên detection.

- 📱💻🖥️ **Sovereign Mode Detection:**

  ```rust
  pub enum DeploymentMode {
      /// VPS Relay + Dedicated Core — cloud/hybrid
      HybridCloud {
          relay_endpoints: Vec<RelayEndpoint>,
          spki_pins: HashMap<String, SpkiPin>,
      },
      /// Direct connect — enterprise sovereign on-premise
      SovereignDirect {
          core_endpoint: SocketAddr,
          // mTLS: present DeviceIdentityKey cert trực tiếp cho Core
          require_device_cert: bool,  // luôn true trong sovereign mode
          // XDP protection ở server side — client không cần làm gì khác
          // nhưng cần biết để disable relay-specific retry logic
          xdp_server_side: bool,
      },
  }
  ```

- 📱💻🖥️ **mTLS Client Certificate Presentation (Sovereign Mode):**

  Trong hybrid mode, client connect đến VPS relay — không cần present device cert (VPS không verify). Trong sovereign mode, client connect thẳng đến Core — Core REQUIRES client cert (Lớp 2 §20.3).

  ```rust
  // core/src/sovereign/client_tls.rs
  pub fn build_sovereign_client_config(
      device_cert: CertificateDer,
      device_key_ref: SecureEnclaveKeyRef, // Key không rời Secure Enclave
  ) -> Result<ClientConfig> {
      // Sử dụng hardware-backed key signing — private key ở Secure Enclave/TPM
      let signing_key = HardwareBackedSigningKey::new(device_key_ref);

      ClientConfig::builder()
          .with_root_certificates(enterprise_ca_store())
          .with_client_auth_cert(vec![device_cert], signing_key)
  }
  ```

- 📱 **iOS — Secure Enclave Key cho mTLS:** Trên iOS, `device_key_ref` là reference đến key trong Secure Enclave (không export raw bytes). TLS handshake yêu cầu biometric authentication lần đầu mỗi 12h (`kSecAccessControlBiometryCurrentSet`).

- 📱 **Android — StrongBox Keymaster cho mTLS:** Tương tự — `device_key_ref` là `KeyStore.PrivateKey` từ StrongBox. TLS signing xảy ra trong StrongBox hardware.

- 💻🖥️ **Desktop — TPM 2.0 NCrypt cho mTLS:** `NCryptSignHash` với `Microsoft Platform Crypto Provider`. Key bound với device TPM.

- 📱💻🖥️ **QUIC Migration Validation — Client Side:**

  Khi client thực hiện QUIC Connection Migration (đổi IP/port):

  ```rust
  // Nhận ChallengeSignRequest từ Core (§20.5)
  pub async fn handle_migration_challenge(
      request: ChallengeSignRequest,
      device_key: &SecureEnclaveKeyRef,
  ) -> Result<MigrationSigResponse> {
      // Verify request hợp lệ: timestamp HLC trong 5s window
      let age = HybridLogicalClock::now() - request.hlc_timestamp;
      if age > Duration::from_secs(5) {
          return Err(MigrationError::StaleChallenge);
      }

      // Ký bằng DeviceIdentityKey trong Secure Enclave
      let signature = secure_enclave::sign(
          device_key,
          &request.serialize(),
      )?;

      Ok(MigrationSigResponse { signature })
  }
  ```

- 📱💻🖥️ **Sovereign Mode UI Indicator:** Settings > Network > chế độ kết nối hiển thị badge **"Private (Sovereign)"** thay vì cloud endpoint. Admin Console hiển thị topology diagram xác nhận zero external hops. Không có UI thay đổi cho user thông thường — trải nghiệm giống hệt hybrid mode.

- 📱💻🖥️ **Fallback khi mTLS cert expire trong Sovereign Mode:**

  Trong hybrid mode, cert expire chỉ ảnh hưởng relay tunnel — client vẫn connect được (cert chỉ là identity proof cho relay). Trong sovereign mode, cert expire = client bị lock out khỏi Core.

  ```rust
  // Kiểm tra cert expiry mỗi 6h — emit warning sớm
  pub fn check_device_cert_expiry(cert: &CertificateDer) -> CertExpiryStatus {
      let days_remaining = cert_days_until_expiry(cert);
      match days_remaining {
          d if d < 0  => CertExpiryStatus::Expired,
          d if d < 7  => CertExpiryStatus::Critical(d),  // Admin PHẢI renew
          d if d < 30 => CertExpiryStatus::Warning(d),   // Nên renew
          d           => CertExpiryStatus::Ok(d),
      }
  }
  // Critical → Admin Console RSOD-style alert + block non-admin operations
  // Warning  → Banner vàng: "Chứng chỉ thiết bị hết hạn sau X ngày. Liên hệ Admin."
  ```

```

---

## Bảng định vị — 3 giải pháp, 2 file, mapping đầy đủ

| Vấn đề | Core_Spec.md section | Feature_Spec.md section |
|---|---|---|
| Q1 — QUIC Cert Revocation <500ms | §18 — protocol, watch channel, drain state machine | HYBRID-10 — client disconnect classification, reconnect logic, UI |
| Q2 — EMDP Zero-Loss (no VPS journal) | §19 — schema, write path, replay path, Mesh Courier, GC | HYBRID-11 — iOS/Android/Desktop trigger, Mesh courier UI flow |
| Q3 — Sovereign Core Defense | §20 — eBPF XDP, mTLS verifier, rate limiter, QUIC migration guard | HYBRID-12 — client detection, cert presentation per-platform, migration challenge |
Excellent. Now I have a thorough understanding of both the OpenClaw/NemoClaw analysis and all 8 TeraChat documents. Let me synthesize this into a comprehensive strategic response.

---

# 🦀 TeraChat × OpenClaw × NemoClaw — Chief AI Architect Innovation Brief

## Tổng quan Chiến lược: Điểm Hội tụ Lịch sử

Sau khi đọc toàn bộ báo cáo phân tích, tôi nhận ra một điều: **TeraChat không cần "tích hợp" OpenClaw hay NemoClaw — TeraChat cần *hấp thụ* triết lý của cả hai và trở thành tầng điều phối tác tử duy nhất mà không ai khác trên thị trường có thể làm được.**

OpenClaw giải quyết bài toán *linh hoạt*. NemoClaw giải quyết bài toán *kiểm soát*. TeraChat đã có sẵn cái mà cả hai thiếu: **kênh giao tiếp được mã hóa đầu cuối, mạng Mesh sinh tồn, và Hardware Root of Trust.** Đây là vũ khí chiến lược không thể sao chép.

---

## 🔑 Key Ideas (Ý tưởng Cốt lõi)

### Cluster A — Agentic Mesh: AI Agents chạy trên Survival Network

- **Zero-Internet Agent Execution:** Tác tử AI hoạt động hoàn toàn trong mạng BLE/Wi-Fi Direct Mesh — không cần Cloud, không cần VPS. Khả năng này là **độc nhất vô nhị** trên thị trường. Không OpenClaw, không NemoClaw, không Slack AI, không Teams Copilot nào có thể làm điều này.
- **Soul.md → Encrypted soul.db:** Thay vì file `soul.md` plaintext của OpenClaw, TeraChat lưu agent context trong `soul.db` — một SQLite được mã hóa AES-256-GCM bằng `Device_Key`, ZeroizeOnDrop, và đồng bộ qua CRDT DAG. Agent "nhớ" mọi thứ mà không rò rỉ ra ngoài.
- **Tapp-Agent Fusion:** File `.tapp` không còn chỉ là "mini-app UI" — nó trở thành **autonomous agent** có vòng đời riêng. `.tapp` có thể chạy background tasks (cron jobs), watch triggers, và tự khởi tạo hành động mà không cần user `@mention`.

### Cluster B — TeraShell: NemoClaw nhưng native trong Rust Core

- **TeraShell = NemoClaw Done Right:** Thay vì Docker container của NemoClaw (cần 8GB RAM, Linux only, NVIDIA lock-in), TeraShell là một WASM Sandbox tích hợp sẵn trong Lõi Rust — chạy trên mọi platform (iOS, Android, Huawei, Desktop), không cần VM, không cần container.
- **Policy-as-Code trong manifest.json:** Thay vì `openclaw-sandbox.yaml` của NemoClaw phải cấu hình thủ công, TeraShell biên dịch manifest `.tapp` thành OPA Rego rules tại publish time. Agent tự biết được phép làm gì.
- **Hardware-Attested Agent Identity:** Mỗi tác tử chạy trong TeraShell được gắn một `Agent_DID` được ký bởi `DeviceIdentityKey` trong Secure Enclave. Không thể giả mạo agent, không thể replay agent session.

### Cluster C — Multi-Agent Orchestration trong Chat

- **Agent Conversation:** Thay vì chỉ user chat với AI, TeraChat cho phép **nhiều agent chat với nhau** trong một MLS group — mỗi agent là một MLS member với Epoch Key riêng. Human supervisor chỉ cần `@approve` hoặc `@reject` kết quả.
- **Causal Agent Chain:** Dùng CRDT DAG để ghi lại toàn bộ chuỗi quyết định của multi-agent workflow. Mỗi action được ký Ed25519 — không thể phủ nhận, không thể rewrite lịch sử. Đây là **Non-Repudiation cho AI Actions** — thứ mà không một nền tảng nào có hiện nay.
- **Blind Agent Execution:** Agent xử lý dữ liệu nhạy cảm mà không bao giờ thấy plaintext. Lõi Rust decrypt → mask PII → đưa vào agent context. Agent trả về kết quả → Lõi Rust de-tokenize → ghi vào DAG. Agent chỉ là một "black box xử lý" — Zero-Knowledge Agent Architecture.

### Cluster D — Edge AI Native

- **Survival Agent Mode:** Khi Internet mất, các tác tử không bị tắt — chúng chuyển sang **Mesh Agent Mode**, tiếp tục thực hiện tasks được cache sẵn, đồng bộ kết quả khi có kết nối trở lại qua CRDT merge.
- **PicoClaw-inspired TeraAgent Nano:** Lấy cảm hứng từ PicoClaw (<10MB RAM), xây dựng **TeraAgent Nano** — một agent runtime <5MB viết thuần Rust, có thể chạy trên Raspberry Pi, industrial IoT gateway, hay băng thông satellite. Target: nhà máy, khu mỏ, tàu biển.
- **NPU-Accelerated Local Inference:** Tận dụng Apple Neural Engine (iOS), Qualcomm Hexagon (Android), MediaTek APU — chạy mô hình SLM 7B tại biên với latency <100ms mà không cần GPU server.

---

## 🏗️ Architecture Vision

```

╔══════════════════════════════════════════════════════════════════╗
║              TERACHAT AGENTIC ARCHITECTURE v2.0                  ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐    ║
║  │              AGENT ORCHESTRATION LAYER                   │    ║
║  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │    ║
║  │  │ Agent A  │  │ Agent B  │  │ Agent C  │  (MLS Members)│    ║
║  │  │ DID:xxx  │  │ DID:yyy  │  │ DID:zzz  │              │    ║
║  │  └────┬─────┘  └────┬─────┘  └────┬─────┘              │    ║
║  │       └──────────────┴──────────────┘                   │    ║
║  │                      │ CRDT DAG (Causal Chain)           │    ║
║  └──────────────────────┼──────────────────────────────────┘    ║
║                         │                                        ║
║  ┌──────────────────────▼──────────────────────────────────┐    ║
║  │                  TERASHELL (WASM Sandbox)                 │    ║
║  │  Manifest → OPA Policy │ Landlock LSM │ Egress Control   │    ║
║  │  Capability-Based Sandboxing │ Network Namespace          │    ║
║  │  BLAKE3 Integrity │ Ed25519 Agent Identity                │    ║
║  └──────────────────────┬──────────────────────────────────┘    ║
║                         │                                        ║
║  ┌──────────────────────▼──────────────────────────────────┐    ║
║  │              RUST CORE (Crypto Engine)                    │    ║
║  │  MLS E2EE │ ZeroizeOnDrop │ PII Masking (NER)            │    ║
║  │  soul.db (Encrypted) │ CRDT DAG │ Hardware Root of Trust  │    ║
║  │  Blind Agent Execution │ Non-Repudiation Audit            │    ║
║  └──────────────────────┬──────────────────────────────────┘    ║
║                         │                                        ║
║  ┌───────────┬───────────┴──────────────────────────────────┐   ║
║  │  ONLINE   │         SURVIVAL MESH                         │   ║
║  │  QUIC/gRPC│  BLE 5.0 + Wi-Fi Direct + AWDL              │   ║
║  │  VPS Relay│  Agent tasks: cached & deferred              │   ║
║  └───────────┴──────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════╝

```

### 3 lớp kỹ thuật then chốt cần xây dựng mới:

**Lớp 1 — Agent Identity & Lifecycle Manager (Rust)**
```rust
pub struct TeraAgent {
    did: AgentDID,              // gắn với DeviceIdentityKey
    soul_db: EncryptedSoulDB,   // thay soul.md
    epoch_key: EpochKey,        // MLS member
    sandbox: TeraShellInstance, // WASM runtime
    capabilities: OPAPolicy,    // từ manifest
    status: AgentStatus,        // Active/Suspended/MeshMode
}
```

**Lớp 2 — Multi-Agent Conversation Protocol (MCP over MLS)**

Agent giao tiếp với nhau qua Model Context Protocol (MCP) được wrap trong MLS E2EE channel. Mỗi agent message là một CRDT event được ký và persist vào `hot_dag.db`. Human supervisor có thể audit toàn bộ decision chain.

**Lớp 3 — TeraShell Security Boundary**

| Capability | OpenClaw | NemoClaw (OpenShell) | TeraShell |
|---|---|---|---|
| Filesystem | Full OS access | Read-only except /sandbox | WASM Linear Memory only |
| Network egress | Unrestricted | Whitelist via yaml | OPA Manifest-compiled rules |
| Platform | Any Node.js | Linux only (Docker) | iOS/Android/Desktop/HarmonyOS |
| RAM overhead | ~50MB | ~8GB+ | ~64MB (WASM sandbox) |
| Hardware attestation | ❌ | Partial (DCAP) | ✅ Secure Enclave/StrongBox |
| Offline support | ❌ | ❌ | ✅ Survival Mesh Agent Mode |

---

## 📦 Product Strategy

### Tier 1 — Consumer: "Your Sovereign AI Assistant"

**Target:** Chuyên gia, freelancer, nhà quản lý muốn AI assistant không rò rỉ dữ liệu.

**Killer Features:**

- **TeraAssist** — AI assistant chạy 100% local trên thiết bị, đồng bộ qua E2EE. Không một byte nào lên Cloud của OpenAI hay Anthropic nếu user không muốn.
- **Persistent Memory** — `soul.db` được mã hóa. Assistant "nhớ" sở thích, lịch làm việc, ngữ cảnh dự án — không bao giờ bị reset dù đổi thiết bị.
- **Offline-First Agent** — Đặt lịch, phân tích tài liệu, gửi tin nhắn theo schedule — tất cả chạy khi không có Internet nhờ Mesh Agent Mode.

**Pricing:** Bao gồm trong Standard tier ($15/tháng). AI token usage minh bạch, user tự quyết BYOM (Bring Your Own Model).

### Tier 2 — Enterprise: "The Secure Agentic Workspace"

**Target:** Ngân hàng, chính phủ, bệnh viện, doanh nghiệp sản xuất (Manufacturing).

**Killer Features:**

- **Compliance-Ready Agent Orchestration** — Multi-agent workflows với Causal Audit Chain. Mỗi quyết định của AI được ký Ed25519, không thể xóa, không thể chối bỏ. Đáp ứng HIPAA, SOC2, ISO 27001, Nghị định 13/VN.
- **TeraShell Enterprise** — Agent sandbox với Landlock LSM + OPA Policy + Hardware Attestation. Mạnh hơn NemoClaw (không cần Docker, không cần Linux chuyên dụng, không lock-in NVIDIA).
- **Blind Agent Processing** — Agent xử lý data nhạy cảm (hợp đồng, hồ sơ bệnh nhân, giao dịch tài chính) mà không bao giờ thấy plaintext. Zero-Knowledge Agent Architecture.

**Pricing:** Enterprise $500-$8,000/tháng. Professional Services: $50K-200K/deployment.

### Tier 3 — Telecom / Edge AI: "Intelligence at the Network Node"

**Target:** Nhà mạng viễn thông (Viettel, VNPT, Mobifone), nhà máy, cảng biển, khu mỏ.

**Killer Features:**

- **TeraAgent Edge** — Agent runtime <5MB (inspired by PicoClaw) chạy trực tiếp trên edge gateway, industrial router, hay Raspberry Pi. Không cần Cloud inference.
- **AI-RAN Agent** — Tác tử quản lý phân bổ tài nguyên phổ tần 5G theo thời gian thực — đây chính xác là use case mà NemoClaw nhắm đến nhưng TeraChat có thể làm tốt hơn với Mesh redundancy.
- **Disaster Recovery Mesh** — Khi cơ sở hạ tầng mạng sập (thiên tai, tấn công), các agent tiếp tục điều phối thông tin liên lạc khẩn cấp qua BLE/Wi-Fi Direct Mesh — use case mà không có nền tảng nào khác có thể làm.

---

## 🏰 Competitive Moat (Lợi thế Cạnh tranh Bền vững)

### Moat 1: Hardware-Bound Agent Identity (Bất khả xâm phạm)

OpenClaw agent có thể bị clone, bị giả mạo. NemoClaw phụ thuộc DCAP attestation phức tạp. **TeraAgent DID được neo vào Secure Enclave/StrongBox — không thể tách khỏi phần cứng**. Đây là lợi thế không thể sao chép bằng phần mềm thuần túy.

### Moat 2: Offline Agent Execution (Độc quyền thực tế)

Không một nền tảng AI nào — không Slack AI, không Teams Copilot, không OpenClaw — có khả năng thực thi agent tasks khi không có Internet. **TeraChat là nền tảng duy nhất** có thể cam kết "AI không bao giờ ngừng hoạt động dù cơ sở hạ tầng sập." Đây là lợi thế tuyệt đối với Chính phủ, Quân đội, và các ngành Critical Infrastructure.

### Moat 3: Causal Non-Repudiation Audit Chain (Pháp lý không thể phủ nhận)

CRDT DAG + Ed25519 signing tạo ra một chuỗi bằng chứng mật mã cho mọi quyết định AI. Khi AI agent gây ra một quyết định sai trong giao dịch tài chính, TeraChat có thể **chứng minh trước tòa** rằng quyết định đó được thực hiện bởi AI nào, do người dùng nào authorize, vào lúc nào. Không một nền tảng nào có điều này.

### Moat 4: Zero-Knowledge Agent Processing

Agent không bao giờ thấy dữ liệu gốc — chỉ thấy tokenized output từ INES (Integrated NER Engine). Đây là **triển khai Zero-Knowledge AI đầu tiên trên thế giới** ở cấp độ production-ready. Đáp ứng trực tiếp yêu cầu GDPR Article 25 (Privacy by Design).

### Moat 5: WASM-Native TeraShell vs Docker-based NemoClaw

| | NemoClaw | TeraShell |
|---|---|---|
| Nền tảng | Linux only | iOS/Android/Desktop/Huawei |
| RAM tối thiểu | 8GB | 64MB |
| Khởi động | 30-60s (Docker) | <50ms (WASM AOT) |
| Hardware | NVIDIA GPU preferred | Mọi chip (ARM, x86, RISC-V) |
| Offline | ❌ | ✅ Mesh Mode |

---

## 🚀 Future Roadmap

### Year 1 (2026): Foundation — "TeraAgent Alpha"

**Q2 2026:**

- `soul.db` Encrypted Agent Memory — thay thế soul.md của OpenClaw
- TeraShell v1.0 — WASM Sandbox với OPA Policy Engine
- Tapp-Agent Fusion — `.tapp` có thể chạy background cron jobs
- MCP (Model Context Protocol) integration trong MLS E2EE channel

**Q3 2026:**

- Multi-Agent Conversation Protocol — nhiều agent trong cùng MLS group
- Blind Agent Execution Pipeline (NER → Mask → Agent → De-tokenize)
- Causal Audit Chain UI — visualize decision chain trong chat

**Q4 2026:**

- TeraAgent Nano — agent runtime <5MB cho Edge/IoT
- Marketplace `.tapp-agent` tier — publisher có thể submit autonomous agents
- OpenClaw Skills compatibility layer — import skills từ ClawHub vào TeraShell

### Year 2 (2027): Scale — "Agentic Enterprise OS"

- **TeraAgent Enterprise Console** — Admin dashboard quản lý fleet of agents
- **AI-RAN Agent Module** — telecom use case với NDA pilot với Viettel/VNPT
- **Multi-Region Agent Federation** — agent tasks sync qua federated clusters
- **Agent Marketplace Revenue** — 30% cut trên agent subscriptions (B2B)
- **Confidential Computing Integration** — agent tasks trong Intel TDX/AMD SEV cho Elite tier

### Year 3 (2028): Moonshots — "Sovereign AI Infrastructure"

**Moonshot 1 — TeraAgent swarm trong thiên tai:**
Triển khai fleet of TeraAgent Nano trên drone/UAV phân phối kết nối Mesh cho khu vực thảm họa. Agents điều phối cứu hộ, phân bổ nguồn lực, liên lạc với gia đình nạn nhân — hoàn toàn offline. **Market: UN, FEMA, Quân đội Việt Nam.**

**Moonshot 2 — Causal AI Contracts:**
Smart Contracts được thực thi bởi AI agents với Non-Repudiation Audit Chain. Không cần blockchain — chỉ cần CRDT DAG + Ed25519 signatures. **Agent ký hợp đồng thay con người, với bằng chứng mật mã không thể phủ nhận.** Market: FinTech, Legal Tech, Real Estate.

**Moonshot 3 — Zero-Knowledge AI Healthcare:**
Agent xử lý hồ sơ bệnh nhân mà không bao giờ expose plaintext — ngay cả với bác sĩ đang sử dụng agent. Chỉ output summary và recommendations được hiển thị. **Đây là HIPAA compliance tuyệt đối đầu tiên trên thế giới.** Market: Hospital Systems toàn cầu.

---

## 📊 Risk Classification Matrix

| Rủi ro | Mức độ | Mitigation |
|---|---|---|
| OpenClaw Skills import tạo attack surface mới | **Khẩn cấp 🔴** | EMIP scanning + static analysis bắt buộc cho mọi import |
| soul.db sync qua CRDT tạo ra privacy leak nếu DAG bị compromise | **Vừa 🟡** | ZeroizeOnDrop + Epoch-bound encryption của soul.db |
| Multi-agent decision chain quá phức tạp, user mất kiểm soát | **Vừa 🟡** | Human-in-the-loop mandatory cho critical actions (Smart Approval) |
| TeraAgent Nano trên IoT bị physical attack | **Vừa 🟡** | Hardware Monotonic Counter + Poison Pill Mesh Revocation |
| Agent WASM sandbox escape trên iOS (wasm3 interpreter) | **Nhẹ 🟢** | EMIP boot-time check + Linear Memory Isolation + CFI |
| NVIDIA lock-in nếu dùng NemoClaw API trực tiếp | **Nhẹ 🟢** | Không cần dùng NemoClaw API — TeraShell tự làm được |
| OpenClaw community skills có malware (tỷ lệ 20%) | **Khẩn cấp 🔴** | Zero-trust: mọi skill phải pass Ed25519 CA + WASM static scan trước khi load |

---
