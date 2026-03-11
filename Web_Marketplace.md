# Web_Marketplace.md — TeraChat Alpha v0.3.0

> **Status:** `ACTIVE — Implementation Reference`
> **Audience:** Platform Engineer · Plugin/App Dev · Security Auditor
> **Scope:** `.tapp` Plugin Lifecycle, Signature Verification, OPA Policy Distribution, WASM Runtime Limits
> **Last Updated:** 2026-03-11
> **Depends On:** `Core_Spec.md` §5.24 (EMIP Plugin Integrity), `Feature_Spec.md` §8.1 (WASM Sandbox)
> **Consumed By:** Admin Console plugin management UI

---

## CHANGELOG

| Version | Date | Change Summary |
| ------- | ---------- | ---------------------------------------------------------------------------- |
| v0.3.0 | 2026-03-11 | Add §4 Automated Static Scan & Security Manifest Audit; Publisher Trust Tier table |
| v0.2.9 | 2026-03-05 | Add §3 WASM Sandbox resource limits (CPU 10%, RAM 64MB cap); egress rate limiting |
| v0.2.8 | 2026-03-03 | Initial spec: §1 Decentralized Provisioning; §2 Ed25519 Signature flow; §3 OPA injection |

---

## CONTRACT: Plugin Publishing Requirements

> **Mọi `.tapp` submit lên Marketplace phải pass toàn bộ các gate dưới đây trước khi được listed.**

- [ ] `manifest.json` **phải** khai báo đầy đủ: `publisher_public_key`, `egress_endpoints` whitelist, `permissions`, `version_hash` (BLAKE3).
- [ ] WASM bytecode **phải** pass Static Analysis Scanner — không có syscall nằm ngoài allowlist.
- [ ] Bundle **phải** được ký `Ed25519` bởi Publisher Key đã đăng ký trên Merkle Registry.
- [ ] Egress endpoint **phải** nằm trong `egress_endpoints` whitelist — bất kỳ outbound call nào ra ngoài danh sách → bị block ở Lõi Rust.
- [ ] RAM usage trong Sandbox **phải** ≤ 64MB (softcap) — vượt ngưỡng → OOM-kill không warning.
- [ ] CPU usage **phải** ≤ 10% sustained — spike được phép nhưng không kéo dài > 500ms.

---

## 1. Decentralized Plugin Provisioning & Signature Verification

> **Tầm nhìn:** TeraChat Marketplace không phải App Store truyền thống. Đây là một **Decentralized Trust Registry** — nơi Publisher ký `.tapp` bằng chính Private Key của mình, TeraChat chỉ đóng vai trò xác minh chữ ký và forward. Không có server trung gian nào có thể "inject" mã độc vào plugin.

### 1.1 Kiến trúc Phân phối (Manifest-driven WASM Distribution)

- ☁️ **Manifest-driven WASM Distribution:** Mỗi `.tapp` được đóng gói thành bundle: `{ logic.wasm, manifest.json, assets/ }`. `manifest.json` khai báo: `publisher_public_key` (Ed25519), `egress_endpoints` (whitelist URL), `permissions` (scope), `version_hash` (BLAKE3 của WASM bytecode).
- ☁️ **Content-Addressed Distribution (CAS):** `.tapp` bundle được lưu trên Marketplace CDN theo địa chỉ nội dung `CAS_UUID = BLAKE3(bundle_bytes)`. URL tải về là xác định (deterministic) — mọi thiết bị tải cùng UUID sẽ nhận byte-for-byte identical bundle. Không thể silently swap backend.
- ☁️ **Incremental Update (Delta Manifest):** Khi Publisher release update, chỉ Delta manifest (diff của `manifest.json` + nếu WASM đổi thì WASM mới) được publish. Thiết bị client tải delta, verify lại BLAKE3 + Ed25519, áp dụng atomic update.

### 1.2 Ed25519 Signature Verification

- ☁️ **Publisher Key Registration:** Publisher đăng ký `Ed25519_PublicKey` trên Marketplace Registry (on-chain hoặc self-hosted Merkle Log). Key registration event được ghi vào append-only log — không thể revoke retroactively mà không để lại dấu vết.
- 🗄️☁️ **Ed25519 Digital Signature Flow:**
  1. Publisher sign `SHA3-256(manifest.json || logic.wasm)` bằng Private Key → tạo `bundle.sig`.
  2. Marketplace server verify signature trước khi accept upload — server không thể tamper bundle vì không có Private Key.
  3. Client (Lõi Rust) verify lại signature khi install và mỗi khi Egress được yêu cầu (EMIP — xem Core_Spec.md §5.24).

### 1.3 OPA Policy Injection

- ☁️ **Manifest-to-OPA Compiler:** Khi `.tapp` được install, Marketplace backend biên dịch `manifest.json` thành OPA Rego Policy và bundle kèm vào `.tapp`. Policy này enforce: egress endpoint whitelist, max payload size, required consent level, rate limiting.
- ☁️ **Policy Version Pinning:** Mỗi OPA Policy bundle được gán `policy_hash` (BLAKE3). Lõi Rust từ chối load `.tapp` nếu `policy_hash` không khớp với hash được ký trong `manifest.json` — ngăn server-side policy swap.
- 💻📱 **Local Manifest Validation (Boot-time):** Xem Core_Spec.md §5.24 EMIP cho chi tiết boot-time validation flow.

### 1.4 Publisher Trust Tiers

| Tier | Điều kiện | Egress Privilege | Marketplace Badge |
|---|---|---|---|
| **Unverified** | Chỉ có Ed25519 key | HTTP GET only, no file, < 1KB payload | 🔵 Community |
| **Verified** | KYC + Key + Review | Egress file < 10MB, standard consent | ✅ Verified |
| **Enterprise** | SOC2/ISO27001 cert | Full file egress, custom consent flow | 🏢 Enterprise |
| **TeraChat Native** | First-party `.tapp` | Unrestricted (subject to OPA) | ⭐ Native |

### 1.5 Revocation & Emergency Kill-switch

- ☁️ **Publisher Key Revocation:** Publisher có thể revoke key bằng cách sign `REVOKE { key_hash, timestamp }` bundle bằng Master Recovery Key (stored offline). Marketplace push revocation event đến tất cả tenants — Lõi Rust nhận và disable tất cả `.tapp` từ key đó.
- ☁️ **TeraChat Emergency Suspension:** Xem Function.md §9 PARA — Control Plane có thể push `REVOKE_TAPP` bundle đến toàn bộ fleet khi phát hiện `.tapp` bị compromise, không cần store review hay app update.
- ☁️ **Transparency Log:** Mọi sự kiện (publish, update, revocation, suspension) được ghi vào Transparency Log (append-only, Merkle-proofed). CISO của bất kỳ tenant nào có thể audit log độc lập để verify không có tampering.

## 2. Ngăn chặn Rò rỉ Dữ liệu qua AI Extension (WASM Data Exfiltration)

> **Bài toán:** Tiện ích AI tải về từ Marketplace có thể độc hại ngầm, thu thập ngữ cảnh tài liệu và lén lút tuồn dữ liệu (Exfiltration) ra máy chủ của bên thứ ba qua các API ẩn.

- ☁️ **OPA Egress Whitelist (Domain & Port):** Lõi Rust nhúng bộ quy tắc OPA (Open Policy Agent) trực tiếp vào ranh giới mạng của Sandbox. Bất kỳ nỗ lực mở socket nào nằm ngoài danh sách Whitelist Domain & Port đã đăng ký từ trước đều bị chặt đứt ngay lập tức ở tầng OS.
- 📱💻 **Metadata Stripping Proxy:** Trước khi payload HTTP/RPC rời khỏi thiết bị đến máy chủ của Tiện ích thứ 3, nó phải đi qua Proxy Kiểm duyệt cục bộ để gọt sạch mọi siêu dữ liệu nhạy cảm (User-Agent, IP, Thiết bị, Thời gian) — không chừa lại bất kỳ dấu vết định danh nào (Fingerprinting).
- 🗄️ **BPF Syscall Trapping (Socket/File I/O):** Ép khâu giám sát vào cấp độ nhân hệ điều hành bằng Kernel Seccomp-BPF. Mọi lời gọi hệ thống (Syscalls) yêu cầu mở file I/O hay tạo Socket mới đều bị Trap và đối chiếu thời gian thực (Real-time).

## 3. Tối ưu Hiệu năng WASM Plugin (CPU-Bound Task Freeze)

> **Bài toán:** Các mô hình thuật toán chạy trong WASM có thể tiêu tốn 100% CPU (CPU-Bound), làm nghẽn Event Loop và đóng băng (Freeze) giao diện nhắn tin chính.

- 📱💻 **WasmEdge AOT Compiler (Ahead-of-Time):** Chuyển đổi toàn bộ Bytecode của WASM Plugin rườm rà sang Machine Code bản địa (Native) ngay tại thời điểm tải về. Thao tác AOT này triệt tiêu hoàn toàn độ trễ của JIT (Just-In-Time) Compiler, tăng tốc thông lượng thực thi lên gấp 5 lần.
- ☁️ **SIMD (Single Instruction, Multiple Data) Vectorization:** Bật cờ phần cứng SIMD (WebAssembly SIMD128) để xử lý ma trận và phép băm mã hóa song song, giải phóng băng thông cho bộ xử lý tín hiệu lõi.
- 🗄️ **Pre-warmed WASM Instance Pool:** Desktop và Server duy trì sẵn một hồ bơi (Pool) các Instance WASM đã "ngâm nóng" (Pre-warmed memory). Khi người dùng kích hoạt Plugin, thời gian Cold-Start giảm từ 300ms xuống < 5ms (chấm dứt tình trạng giật cục).

## 4. Automated Static Scan & Security Manifest Audit

> **Bài toán:** `.tapp` độc hại lách luật kiểm duyệt thông qua hướng dẫn mang chữ ký hợp lệ nhưng chứa Bytecode thóa mã xượng vầt qua OPA Policy.

- ☁️ **Static WASM Syscall Scan (Chặn lệnh nhảy trái phép):** Phân tích tĩnh toàn bộ Bytecode WASM bằng Abstract Interpretation trước khi chấp nhận Publish. Ký hiệu nhảy trực tiếp ra ngoài Sandbox (`call_indirect` không khai báo) → Từ chối ngay lập tức.
- 💻 **Manifest Whitelist Enforcement (Khóa cứng allowed_domains):** Trước khi nhận bandt tải lên, Marketplace vác định dạng `manifest.json` và so sánh danh sách `egress_endpoints` với Registry Domain Whitelist — phát hiện bất kỳ domain nẳm ngoài dải cho phép ngưng Upload ngượng cưa.
- 🗄️ **Ed25519 Signed Bundle (Chứng thực CA từ TeraChat HQ):** Mọi bundle `.tapp` phải mang chữ ký hợp lệ từ ít nhất 1 trong 3 Root CA offline của TeraChat HQ. Không có chữ ký → Lõi Rust từ chối nạp.

## 5. Mandatory Capability-Based WASM Sandboxing — Zero-Trust Tiện ích

> **Lập trường Kiến trúc:** Không có `.tapp` nào được phép yêu cầu "exception" khỏi Sandbox. Mọi Exception Policy đều phá vỡ Zero-Trust. Thay vào đó, mọi capability cần thiết đều được khai báo tường minh trong `manifest.json` và được OPA Policy kiểm soát.

### Nguyên tắc W^X (Write XOR Execute)

- 📱💻 **WASM No-Syscall Isolation:** `.tapp` chạy trong WasmEdge runtime với profile Seccomp-BPF khắt khe — toàn bộ `execve`, `fork`, `ptrace`, `socket` bị drop ở tầng kernel. `.tapp` không thể tạo process con hay mở raw socket.
- 📱 **iOS AOT W^X Compliance:** Trên iOS, WASM phải được biên dịch AOT (Ahead-of-Time) sang machine code trước khi deploy. JIT interpreter bị cấm vì vi phạm W^X policy của iOS — vùng nhớ chỉ có thể Write OR Execute, không bao giờ cả hai.
- 📱💻 **Linear Memory Isolation:** Mỗi `.tapp` instance được cấp một vùng Linear Memory cô lập (max 64MB, configurable). Không có shared memory giữa các instance. Overflow sang vùng TeraChat Core → SIGSEGV + instance kill.
- 💻 🖥️ **AOT Compilation (Cranelift) & seccomp-bpf cjail:** Áp dụng kiến trúc Strict AOT Architecture thay thế JIT Compilation để đóng băng nguy cơ WASM Sandbox Escape.
- 📱 **Pure Interpreter Mode (`--jitless`):** Kích hoạt vận hành trình thông dịch thuần túy ngăn chặn tuyệt đối can thiệp Dynamic Memory trên nền tảng di động.
- 🗄️ **ARMv9 MTE SIGSEGV Hard-Kill:** Kích nổ rào chắn Hardware Memory Tagging Extension, tiêu diệt lập tức luồng tiến trình dị thường qua tín hiệu SIGSEGV.
- ☁️ **Marketplace Ed25519 Signing Gate (Publish-time):** Khi Publisher submit `.tapp`:
  1. Marketplace backend chạy Static WASM Analysis (Abstract Interpretation)
  2. Kiểm tra `manifest.json` capability list vs. OPA Policy Registry
  3. Nếu pass → ký bundle bằng `TeraChat_Marketplace_CA_Key` (Ed25519)
  4. Bundle unsigned hoặc capability khai báo không khớp bytecode → reject, không refund

### Capability Declaration (Manifest Whitelist)

| Capability | Điều kiện cấp phép | Default |
| ---------- | ------------------- | ------- |
| `network.egress` | Chỉ domain list trong manifest | ❌ Blocked |
| `clipboard.read` | User consent per-session | ❌ Blocked |
| `file.read` | Explicit user file picker | ❌ Blocked |
| `crypto.sign` | Publisher Ed25519 identity proof | ❌ Blocked |
| `push.notify` | Admin whitelist per-tenant | ❌ Blocked |

- 📱💻 **Runtime Capability Check:** Mọi syscall từ `.tapp` đều bị intercept tại WASM host function boundary. Rust Core kiểm tra `granted_capabilities` trong `OPA Policy` trước khi forward. Capability không được khai báo → `PermissionDenied` error về sandbox, không crash app.

## 6. DLP Bypass Prevention — WASM Egress Circuit Breaker

> **Lỗ hổng:** `.tapp` độc hại có thể tích lũy dữ liệu chat qua nhiều callback nhỏ (Salami Attack) và exfiltrate qua endpoint hợp lệ trong whitelist nhưng với payload bất thường.

- ☁️ **Automated WASM O-LLVM Scan (Pre-publish):** Marketplace backend chạy LLVM IR analysis trên WASM bytecode: phát hiện data accumulation pattern (buffer tăng dần qua multiple calls), obfuscated string construction, unusual control flow graph. Plugin nghi ngờ → manual security review queue.
- 💻🖥️ **OPA Policy Engine Firewall (Runtime):** Mọi `egress` call từ `.tapp` bị OPA intercept tại Rust boundary. OPA check: `payload_size`, `destination_domain`, `call_frequency_per_minute`, `cumulative_bytes_per_session`. Vi phạm bất kỳ threshold → `EgressBlocked`.
- 📱💻 **Byte-Quota Circuit Breaker (4096 Bytes Threshold):** Hard limit mỗi egress call = **4096 Bytes**. Bất kỳ attempt gửi payload > 4KB → Circuit Breaker ngắt kết nối ngay, log `EgressQuotaExceeded {plugin_id, bytes_attempted, timestamp}` vào Tamper-Proof Audit Log (Ed25519 signed). Sau 3 vi phạm trong 1 session → plugin bị terminate và quarantine.
- ☁️ **Cumulative Session Quota:** Tổng egress của 1 `.tapp` instance trong 1 session không được vượt **512KB**. Vượt ngưỡng → tự động suspend instance, alert Admin Console.
- 📱💻 **No Persistent Storage Egress:** `.tapp` không được phép read từ local persistent storage rồi immediate egress. Pipeline `storage.read → network.write` phải có user consent dialog intervene per attempt.

### Chống Kênh Rò rỉ Ngầm qua Data Diode (Timing Covert Channel)

- 💻 🖥️ **Strict Token Bucket & Ring Buffer:** Áp đặt Time-Laundering với Constant-Rate Egress Shaper dập tắt nhiễu loạn băng thông triệt tiêu Kênh rò rỉ ngầm (Timing Covert Channel).
- 💻 🖥️ **5ms Fixed-Interval Dispatch Metronome:** Cưỡng chế nhịp độ xuất phát gói tin cố định che giấu tín hiệu phân tích tần suất gửi từ Data Diode.
- 💻 🖥️ **ChaCha20 Cryptographic Noise Padding:** Bơm đệm ngẫu nhiên ngụy trang kích thước Payload gốc vô hiệu hóa thuật toán dò thám dung lượng gói tin.

## 7. Policy Integrity — Immutable Cryptographic OPA Artifacts (ISO 27001 A.8.2)

> **Mối đe dọa:** Insider threat hoặc kẻ tấn công chiếm quyền Admin có thể sửa OPA Policy để tắt DLP, mở egress whitelist hoặc leo thang đặc quyền.

### 7.1 Ed25519 Signed Policy Bundles

- ☁️ **Signed OPA Bundle:** Mọi OPA Policy bundle (`.tar.gz`) phải được ký bằng `Enterprise_CA Ed25519 key` trước khi distribute. Lõi Rust trên mọi client verify signature khi boot và khi nhận policy update — policy không có chữ ký hợp lệ bị reject toàn bộ, không apply partial.
- ☁️ **Content-Hash Pinning:** Sau khi verify signature, Lõi Rust tính BLAKE3 hash của policy bundle và pin vào `policy_hash_registry`. Mọi runtime OPA evaluation check `active_policy_hash` khớp pin — tránh in-memory policy tampering.
- 🗄️ **Tamper-Proof Audit Log (Policy Changes):** Mọi thay đổi policy (upload bundle mới, revoke policy) đều được append vào Ed25519-signed Audit Log Merkle Chain. Không thể xóa lịch sử thay đổi mà không phá vỡ chain.

### 7.2 M-of-N Hardware-Backed Policy Consensus (Multi-Sig Quorum)

> **Không có cá nhân đơn lẻ nào — kể cả CEO hay CISO — có thể đơn phương thay đổi OPA Policy sản xuất.**

- 🗄️📱 **HSM Quorum M-of-N (mặc định 2/3):** Policy bundle mới phải được ký bởi ít nhất **2 trong 3** Hardware Security Key (YubiKey 5 FIPS / NFC-backed device) thuộc các C-Level khác nhau: `CISO`, `CTO`, `Legal`. Thiếu chữ ký → bundle bị server từ chối deploy.
- 🗄️ **Offline Signing Ceremony:** CISO và CTO ký offline (air-gapped laptop) bằng HSM. Legal ký online qua NFC NitroKey. Ba chữ ký được aggregate bằng Ed25519 Multi-Signature scheme (Ristretto255 schnorr) → một bundle signature duy nhất.
- 💻🖥️ **Local OPA Enforcement in WASM Sandbox:** Mỗi client `.tapp` runtime sử dụng OPA WASM build (`opa_wasm`) để enforce policy locally mà không cần round-trip server. WASM OPA binary được hash-pin và phân phối cùng với policy bundle — không thể substitute OPA engine.
- ☁️ **Policy Rollback Protection (Monotonic Version Counter):** Policy bundle chứa `version: u64` (monotonic, không thể giảm). Nếu server cố push bundle version nhỏ hơn version hiện tại của client → client từ chối và alert `POLICY_ROLLBACK_ATTACK` vào Audit Log.

## 9. Zero-Touch CLI Provisioning — Khắc phục Rủi ro Kiến thức Hạ tầng (Deployment Complexity)

> **Vấn đề:** Triển khai mạng diện rộng VPS Enclave (SGX/Nitro/SEV) để load logic `.tapp` Heavyweight đòi hỏi chứng chỉ DevOps/SME rất lớn, tạo rào cản quá cao cho doanh nghiệp tự host (Self-hosted).

- 💻 **`tera-deploy` CLI (Zero-Touch Provisioning):** Bọc toàn bộ các vòng lặp tay biên dịch hệ thống. IT Admin thuộc doanh nghiệp chỉ cần cung cấp Access Key (AWS/GCP), gõ 1 lệnh CLI, mọi tham chiếu Cloud sẽ tự động map 100%.
- ☁️ **Infrastructure as Code (Terraform):** `tera-deploy` kích hoạt tự động các module ☁️ Terraform (đã pre-audited bởi TeraChat Core Team). Tự động spin-up EC2 Nitro Enclaves, set up VPC isolation, TLS Passthrough rule, và IAM roles với Least Privilege (Giới hạn quyền hẹp nhất có thể).
- 🗄️ **Enclave Image Format (EIF) Auto-Build:** Tiến trình Build Pipeline dịch Lõi Server Rust thành 🗄️ Enclave Image Format (EIF) và băm tĩnh ra các mã PCR (Platform Configuration Register) hash. Các mã này sẽ auto-inject trực tiếp vào OPA Policy Trust Store — CISO có checklist để apply mà không cần hiểu tầng Base Assembly.


## 8. Static Egress Schema Declaration — Manifest Contract (.tapp Publisher)

> **Yêu cầu:** Mọi `.tapp` muốn publish lên TeraChat Marketplace **bắt buộc** khai báo tĩnh JSON Schema của tất cả payload dự định gửi qua `Egress_Outbox`. Không khai báo = không được publish.

### 8.1 Egress Schema trong `manifest.json`

```json
{
  "tapp_id": "crm-integration-v2",
  "publisher": "Acme Corp",
  "egress_schemas": [
    {
      "endpoint": "api.acme.com/summarize",
      "method": "POST",
      "tls_pin": "sha256/ABC123...",
      "schema": {
        "type": "object",
        "properties": {
          "summary": { "type": "string", "maxLength": 2048 },
          "ticket_id": { "type": "string", "pattern": "^TKT-[0-9]+$" }
        },
        "required": ["summary", "ticket_id"],
        "additionalProperties": false
      },
      "max_payload_bytes": 4096
    }
  ]
}
```

- 📱💻🖥️ **Schema Bắt buộc trong Manifest:** Mỗi endpoint egress phải có: `endpoint` (domain), `tls_pin` (SHA-256 HPKP), `schema` (JSON Schema Draft 7), `max_payload_bytes` (tối đa 4096). Thiếu bất kỳ field nào → CI/CD Marketplace pipeline reject.
- 📱💻🖥️ **Runtime Schema Validation (Egress Daemon):** Trước khi dispatch HTTP request, `tera_egress_daemon` deserialize Outbox payload và validate chống JSON Schema đã khai báo trong Manifest (sử dụng `jsonschema` Rust crate). Payload không khớp schema → drop + `EGRESS_SCHEMA_VIOLATION` alert + audit log.
- ☁️ **`additionalProperties: false` Enforced:** Egress Daemon thêm thêm rule `additionalProperties: false` vào mọi schema khi validate — kể cả Developer quên khai báo. Điều này ngăn `.tapp` nhồi thêm key-value secret vào payload mà không khai báo.
- 🗄️ **Marketplace Pre-publish Schema Audit:** Trước khi bundle được ký và publish, Marketplace Backend chạy static analysis: kiểm tra schema có `maxLength` cho mọi `string` field (ngăn dump toàn bộ conversation), kiểm tra không có `type: "any"`, không có schema `{}` rỗng. Vi phạm → require manual security review.
- 📱💻 **BLAKE3 Hash Verification Chain:** Payload bytes sau khi qua JSON Schema validation → Egress Daemon tính `BLAKE3(validated_payload)` → đối chiếu với hash Lõi Rust cấp trước đó → mismatch = tampering detected → block + alert. Đây là lớp bảo vệ cuối cùng trước khi data ra Internet.





