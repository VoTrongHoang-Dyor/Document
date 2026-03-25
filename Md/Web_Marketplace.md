# Web_Marketplace.md — TeraChat Enterprise Plugin Registry

```yaml
# DOCUMENT IDENTITY
id:       "TERA-MKT"
title:    "TeraChat — Enterprise Plugin Registry & .tapp Ecosystem"
version:  "0.3.7"
status:   "ACTIVE — Implementation Reference"
date:     "2026-03-23"
audience: "Platform Engineer, Plugin Developer, IT Admin, Security Auditor"
purpose:  "Đặc tả Enterprise Plugin Registry: vòng đời .tapp, kiểm duyệt bảo mật,
           quy trình phê duyệt IT Admin, WASM sandbox constraints, và developer guidelines."

ai_routing_hint: |
  "Mở file này khi hỏi về phát triển plugin .tapp, Enterprise Plugin Registry,
   WASM sandbox, kiểm duyệt bảo mật plugin, hoặc quy trình IT Admin phê duyệt."

depends_on:
  - id: "TERA-CORE"
    sections: ["§4.1 (Token Protocol)", "§5.24 (EMIP Plugin Integrity)", "§F-11 (WASM Runtime)"]
  - id: "TERA-FEAT"
    sections: ["§F-07 (WASM Plugin Sandbox)", "§F-08 (Inter-.tapp IPC)"]
```

---

## Tổng quan Mô hình

### Đây không phải App Store công khai

Enterprise Plugin Registry là hệ thống **khép kín, do IT Admin kiểm soát** cho phép tổ chức mở rộng TeraChat bằng các workflow tích hợp nghiệp vụ (.tapp plugins). Luồng kiểm soát hoàn toàn khác với marketplace công khai:

```
Publisher nộp .tapp
      ↓
TeraChat Security Review (automated + manual)
      ↓
.tapp được ký bởi TeraChat CA → Xuất hiện trong Registry (private/public)
      ↓
IT Admin của tổ chức duyệt .tapp cho workspace của mình
      ↓
.tapp được triển khai đến devices trong tổ chức đó
      ↓
End user thấy plugin — nhưng không có quyền tự cài / xóa
```

End user không thể:

- Tự duyệt cài plugin
- Truy cập Registry trực tiếp
- Bypass IT Admin policy

---

## CONTRACT: Yêu cầu Bắt buộc Khi Submit .tapp

> Mọi .tapp submit vào Registry phải pass toàn bộ gates dưới đây trước khi được listed.

- [ ] `manifest.json` khai báo đầy đủ: `publisher_public_key`, `egress_endpoints`, `permissions`, `version_hash` (BLAKE3), `host_api_version`
- [ ] WASM bytecode pass Static Analysis Scanner — không có syscall ngoài allowlist
- [ ] Bundle được ký `Ed25519` bởi Publisher Key đã đăng ký
- [ ] RAM usage ≤ 64MB (mobile soft cap) — vượt → OOM-kill không cảnh báo
- [ ] CPU usage ≤ 10% sustained — spike cho phép nhưng không > 500ms
- [ ] WasmParity CI gate pass: wasm3 vs wasmtime semantically identical (≤ 20ms delta)
- [ ] Egress endpoints phải khai báo trong manifest — call ra ngoài danh sách → blocked ở Core

---

## §1. Kiến trúc Phân phối Plugin

### 1.1 Content-Addressed Distribution

Mỗi .tapp bundle được lưu trên Registry CDN theo địa chỉ nội dung:
`CAS_UUID = BLAKE3(bundle_bytes)`

URL tải về là xác định (deterministic) — mọi tổ chức tải cùng UUID nhận byte-for-byte identical bundle. Không thể swap backend silently.

### 1.2 Ed25519 Signature Chain

```
Publisher Key Registration (on TeraChat Registry)
        ↓
Publisher signs: SHA3-256(manifest.json || logic.wasm) → bundle.sig
        ↓
Registry verifies → ký thêm bởi TeraChat_Marketplace_CA_Key (Ed25519)
        ↓
Client (Rust Core) verifies BOTH signatures khi install và mỗi khi egress
```

Không có chữ ký TeraChat CA → Rust Core từ chối load. Không có ngoại lệ.

### 1.3 OPA Policy Compilation

Khi IT Admin approve một .tapp:

1. Manifest được compile thành OPA Rego Policy
2. Policy bundle được ký bởi Enterprise CA của tổ chức (M-of-N: 2/3 CISO + CTO + Legal)
3. Policy được push xuống devices qua OPA update channel
4. Client enforce locally — không round-trip server

### 1.4 Publisher Trust Tiers

| Tier | Yêu cầu | Egress Privilege | Badge |
|------|---------|-----------------|-------|
| **Unverified** | Ed25519 key đã đăng ký | HTTP GET only, < 1KB payload | 🔵 Community |
| **Verified** | KYC + Key + Security Review | File < 10MB, standard consent | ✅ Verified |
| **Enterprise** | SOC2/ISO27001 cert | Full file egress, custom consent | 🏢 Enterprise |
| **TeraChat Native** | First-party .tapp | Unrestricted (subject to OPA) | ⭐ Native |

---

## §2. Vòng đời .tapp Trong Tổ chức

### 2.1 Luồng IT Admin Approval

```
[Registry] Có .tapp mới phù hợp với use case
         ↓
[IT Admin] Tìm kiếm trong Admin Console → Tab "Plugin Registry"
         ↓
[IT Admin] Xem Security Report: egress domains, permissions, scan results
         ↓
[IT Admin] Approve cho workspace → chọn target groups/devices
         ↓
[Rust Core] OPA Policy push đến devices trong 60s
         ↓
[Device] .tapp xuất hiện trong launcher — user thấy và dùng được
```

IT Admin có thể:

- Approve/revoke bất kỳ lúc nào (revoke effective ≤ 60s)
- Restrict .tapp cho specific user groups
- Set egress rate limits theo policy
- View audit log của tất cả .tapp activity

### 2.2 .tapp Lifecycle States

```
PENDING_REVIEW → SECURITY_REVIEWED → REGISTRY_LISTED
                                            ↓
                                   IT Admin Approves
                                            ↓
                              DEPLOYED (trong workspace)
                              ↙              ↘
                       SUSPENDED          REVOKED
                       (violation)        (permanent)
```

### 2.3 Vòng đời Trên Thiết bị

1. **Install**: Download, BLAKE3 verify, signature verify
2. **Verify DID**: Publisher DID xác thực trước Sandbox launch
3. **Instantiate**: Virtual Memory + Guard Pages + Ring Buffer allocated
4. **Execute**: Trong WASM Sandbox, mọi I/O qua Host Proxy
5. **Suspend**: Snapshot AES-256-GCM encrypted → sled LSM-Tree
6. **Terminate**: RAM freed, Capability Tokens revoked, KV-Cache cleared

---

## §3. WASM Sandbox Security Model

### 3.1 W^X Compliance và Dual-Runtime

| Platform | Runtime | Mode |
|---------|---------|------|
| 📱 iOS | `wasm3` pure interpreter | W^X compliant; +15-20ms/call |
| 📱 Android | `wasmtime` JIT (Cranelift) | CFI enforcement |
| 📱 Huawei | `wasmtime` JIT + AOT fallback | AppGallery: `.waot` bundle bắt buộc |
| 💻 macOS | `wasmtime` JIT trong XPC Worker | Main App: NO allow-jit |
| 🖥️ Windows/Linux | `wasmtime` JIT | Maximum throughput |

**WasmParity Rule**: `wasm3` = reference runtime. `wasmtime` phải produce semantically identical output. Verified by CI gate trước mọi Marketplace listing.

### 3.2 Resource Limits (Hard — Không Exceptions)

```
RAM:     ≤ 64MB mobile / ≤ 64MB desktop    → vượt: OOM-kill, không warning
CPU:     ≤ 10% sustained                   → spike ≤ 500ms; vượt: SUSPEND
Egress:  4096 bytes/call hard limit         → vượt: Circuit Breaker trip
Session: 512KB cumulative egress/session    → vượt: suspend + Admin alert
Rate:    50 req/s token bucket per .tapp    → exhausted: SUSPEND 60s cooldown
```

### 3.3 Capability Declaration (Manifest Whitelist)

| Capability | Điều kiện cấp phép | Default |
|-----------|------------------|---------|
| `network.egress` | Domain list trong manifest | ❌ Blocked |
| `clipboard.read` | User consent per-session | ❌ Blocked |
| `file.read` | Explicit user file picker | ❌ Blocked |
| `crypto.sign` | Publisher Ed25519 identity proof | ❌ Blocked |
| `push.notify` | IT Admin whitelist per-workspace | ❌ Blocked |
| `storage.persist` | Per-DID sled namespace only | ❌ Blocked |

**Không có Capability nào được cấp mặc định. Không có "request at runtime".**

### 3.4 Data Diode Architecture

```
[Rust Core — Company_Key] ── push masked data ──▶ [WASM Sandbox]
                                                         │
                                              write to Egress_Outbox
                                                         │
                                         [Egress Daemon — separate process]
                                              OPA check → BLAKE3 verify
                                                         │
                                                 URLSession / HTTP
                                                         ▼
                                              Partner API (declared only)
```

Company_Key **không bao giờ** vào WASM sandbox. WASM nhận chỉ masked, sanitized data.

---

## §4. Chống Data Exfiltration

### 4.1 Byte-Quota Circuit Breaker

```
Mỗi egress call > 4KB → Circuit Breaker trip ngay lập tức
  → Log: EgressQuotaExceeded {plugin_id, bytes_attempted, timestamp}
  → Append to Tamper-Proof Audit Log (Ed25519 signed)

3 vi phạm / session → plugin terminate + quarantine
Session total > 512KB → suspend + Admin Console alert
```

### 4.2 Runtime Schema Validation

Trước khi dispatch HTTP request, Egress Daemon:

1. Deserialize payload
2. Validate against JSON Schema khai báo trong manifest
3. Check `additionalProperties: false` (enforced ngay cả khi developer quên)
4. Compute BLAKE3(validated_payload) → match với hash Core cấp trước đó

Mismatch → tampering detected → block + alert ngay lập tức.

### 4.3 Timing Covert Channel Defense

- 5ms Fixed-Interval Dispatch Metronome (che khuất traffic pattern)
- ChaCha20 Cryptographic Noise Padding (obfuscate payload size)
- Constant-Rate Egress Shaper (loại bỏ timing side-channel)

---

## §5. IT Admin Operations

### 5.1 Admin Console — Plugin Management UI

| Action | Mô tả |
|--------|-------|
| Browse Registry | Tìm kiếm plugins theo category, vendor, permission scope |
| Security Review | Xem automated scan results, egress domains, permission manifest |
| Approve | Deploy cho all users hoặc specific groups |
| Configure | Set resource limits, egress restrictions per workspace |
| Monitor | Real-time metrics: egress bytes, CPU usage, crash count |
| Revoke | Immediate revocation (effective ≤ 60s trên mọi device online) |

### 5.2 Revocation

Khi IT Admin revoke một .tapp:

1. OPA Policy push với `{plugin_id: "REVOKED"}` đến toàn bộ fleet
2. Devices nhận policy trong ≤ 60s (online) hoặc khi next online (offline)
3. Rust Core disable .tapp execution ngay lập tức khi nhận policy
4. Transient state (sled) được purge
5. Audit log entry: `PLUGIN_REVOKED {plugin_id, admin_id, timestamp, reason}`

---

## §6. Developer Guidelines

### 6.1 manifest.json Contract

```json
{
  "tapp_id":        "acme-crm-integration-v2",
  "publisher":      "Acme Corp",
  "publisher_public_key": "ed25519:...",
  "host_api_version":     "1.3.0",
  "min_host_api_version": "1.0.0",
  "max_host_api_version": "2.0.0",
  "permissions": ["network.egress", "storage.persist"],
  "egress_schemas": [
    {
      "endpoint":          "api.acme.com/crm",
      "method":            "POST",
      "tls_pin":           "sha256/XXXXXXX",
      "max_payload_bytes": 4096,
      "schema": {
        "type": "object",
        "properties": {
          "contact_ref": {"type": "string", "maxLength": 64},
          "action":      {"type": "string", "enum": ["lookup", "update"]}
        },
        "required": ["contact_ref", "action"],
        "additionalProperties": false
      }
    }
  ],
  "version_hash": "blake3:a3f2e1d4..."
}
```

### 6.2 Host Function ABI

```rust
// Crypto (offloaded to Rust Core — WASM không tự chạy crypto)
fn host_blake3_hash(data: *const u8, len: usize, out: *mut u8) -> i32;
fn host_ed25519_sign(key_id: u64, msg: *const u8, msg_len: usize, sig_out: *mut u8) -> i32;
fn host_aes256gcm_encrypt(key_id: u64, nonce: *const u8, pt: *const u8, pt_len: usize, ct_out: *mut u8) -> i32;

// Network (via Egress_Outbox — không direct socket)
fn host_egress_write(endpoint_id: u64, payload: *const u8, len: usize) -> i32;
// Returns: 0=OK, 1=QuotaExceeded, 2=SchemaViolation, 3=OPADeny, 4=MeshRestricted

// Storage (scoped per .tapp DID namespace)
fn host_storage_get(key: *const u8, key_len: usize, out: *mut u8, out_max: usize) -> i32;
fn host_storage_set(key: *const u8, key_len: usize, val: *const u8, val_len: usize) -> i32;
```

### 6.3 ABI Versioning & Deprecation

- Breaking changes chỉ trong **major version**
- Minor version: additive-only (backward compatible)
- TeraChat support **2 major versions đồng thời**
- Deprecation window: **12 tháng** từ ngày announce
- `.tapp` với `host_api_version` ngoài range → **rejected at install**

### 6.4 Platform-Specific Distribution

| Platform | Format | Notes |
|---------|--------|-------|
| 📱 iOS | `.wasm` (interpreted by wasm3) | AOT `.dylib` option trong XPC Worker (macOS only) |
| 📱 Android | `.wasm` | JIT via wasmtime |
| 📱 Huawei | `.waot` bundle | **Bắt buộc** cho AppGallery review; JIT-with-AOT-fallback runtime |
| 💻 Desktop | `.wasm` | JIT via wasmtime |

---

## §7. Security Audit & Registry Transparency

### 7.1 Transparency Log

Mọi sự kiện Registry được ghi vào Transparency Log (append-only, Merkle-proofed):

- Plugin publish, update, revocation
- Security scan results
- IT Admin approval/rejection events

IT Admin của bất kỳ workspace nào có thể audit log độc lập.

### 7.2 Emergency Kill-Switch

TeraChat có thể push `KILL_DIRECTIVE` cho bất kỳ .tapp nào bị phát hiện compromise:

- Không cần app update hoặc store review
- Effective trong < 60s trên toàn bộ fleet online
- Audit log entry được tạo với justification và evidence hash
- IT Admin nhận notification với full technical report

### 7.3 Automated Static Analysis (Pre-listing)

Trước khi accept upload:

1. WASM bytecode: Abstract Interpretation → detect buffer overflow, forbidden syscall, data accumulation patterns
2. Manifest: egress domain validation, schema completeness check
3. LLVM IR analysis: detect obfuscated string construction, unusual CFG
4. Dependency audit: check third-party WASM imports
5. WasmParity test: run against wasm3 + wasmtime test vector suite

Plugin nghi ngờ → **manual security review queue** (không auto-approve).

---

*Cross-references: TERA-CORE §F-11 (WASM Runtime) · TERA-FEAT §F-07 (Plugin Sandbox) · TERA-FEAT §F-08 (Inter-.tapp IPC)*
