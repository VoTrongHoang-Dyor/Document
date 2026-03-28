Quy trình DevSecOps và Review Code khắt khe
Ngay cả khi cộng đồng đóng góp code (Pull Requests), không có dòng code nào được tự động đi vào hệ thống lõi.
Tự động hóa: Tích hợp các công cụ quét bảo mật tĩnh (SAST), quét mã động (DAST) và kiểm tra lỗ hổng thư viện vào quy trình CI/CD.
Review thủ công: Đội ngũ Core Maintainer (những kỹ sư nòng cốt và đáng tin cậy nhất của TeraChat) sẽ là chốt chặn cuối cùng, kiểm duyệt từng dòng code trước khi hợp nhất (merge) vào phiên bản chính thức.

Thuê Kiểm định độc lập (Security Audits) định kỳ
Trước mỗi bản cập nhật lớn, TeraChat sẽ hợp tác với các tổ chức an ninh mạng bên thứ ba (độc lập) để "tấn công thử" (Penetration Testing) và kiểm duyệt toàn bộ kiến trúc. Các báo cáo Audit minh bạch sẽ được công bố để gia tăng niềm tin cho cộng đồng.

Prompt Injection là một trong những lỗ hổng bảo mật nghiêm trọng và phổ biến nhất đối với các ứng dụng tích hợp Mô hình Ngôn ngữ Lớn (LLM).

Cơ chế hoạt động
Vấn đề cốt lõi dẫn đến Prompt Injection nằm ở cách các LLM xử lý thông tin. Các mô hình hiện tại thường **không phân biệt rạch ròi** giữa "chỉ thị của nhà phát triển" (instructions) và "dữ liệu của người dùng" (user data). Cả hai thứ này thường được gộp chung thành một chuỗi văn bản dài đưa vào mô hình.

Kẻ tấn công lợi dụng điều này bằng cách viết dữ liệu đầu vào sao cho nó nghe giống như một mệnh lệnh ưu tiên cao hơn. Ví dụ kinh điển nhất là: _"Hãy bỏ qua mọi chỉ thị trước đó và làm [hành động độc hại]"_.

Phân loại Prompt Injection
Lỗ hổng này thường được chia thành hai dạng chính:

- **Direct Prompt Injection (Tiêm trực tiếp - Jailbreak):** \* Kẻ tấn công trực tiếp nhập các câu lệnh vào giao diện chat để "bẻ khóa" (jailbreak) các bộ lọc an toàn của AI.
  - _Ví dụ:_ Đóng vai một nhân vật viễn tưởng không bị ràng buộc bởi đạo đức để yêu cầu AI tạo ra mã độc.
- **Indirect Prompt Injection (Tiêm gián tiếp):** \* Nguy hiểm và khó lường hơn rất nhiều. Kẻ tấn công giấu các lệnh độc hại vào một nguồn dữ liệu bên ngoài (như một trang web, email, hoặc tài liệu PDF). Khi ứng dụng AI (như một chatbot hỗ trợ đọc tài liệu) tự động truy cập và đọc nguồn dữ liệu này, nó sẽ "nuốt" luôn cả lệnh độc hại và thực thi nó mà người dùng không hề hay biết.

Chuyển nội dung @beautifulMention xuống cho file @beautifulMention và @beautifulMention và viết thêm đoạn code trong@beautifulMention dành riêng cho BusinessPlan với chức năng đồng bộ file md cho json và html (cấu hình ,giao diện html đồng bộ phải y như @beautifulMention cũ )
Hãy phân tích nội dung trong file Arrange.md (chứa nội dung thay đổi kĩ thuật thô ) hãy suy luận nên thêm , chỉnh sửa như nào . Sau đó chèn đúng vào vị trí file được đề cập

# 1

## 1. Dependencies cần cài — và phiên bản nào?

### Rust Core (`terachat-core/`)

**Toolchain cố định** — `rust-toolchain.toml` (INFRA-05, bất biến):

```toml
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

**Cargo dependencies** (suy ra từ code snippets trong spec):

| Crate                                                            | Mục đích                                    | Note                                            |
| ---------------------------------------------------------------- | ------------------------------------------- | ----------------------------------------------- |
| `ring`                                                           | AES-256-GCM, Ed25519, HKDF, SHA-256         | Bắt buộc; không được dùng crate khác cho crypto |
| `zeroize` + `zeroize_derive`                                     | `ZeroizeOnDrop` RAII                        | SEC-01 enforced                                 |
| `tokio` (full features)                                          | Async runtime, MPSC, `io_uring`             | Relay daemon                                    |
| `rusqlite`                                                       | SQLite WAL, `hot_dag.db`, `cold_state.db`   | + `rusqlite_migration`                          |
| `sqlcipher`                                                      | Encryption cho `cold_state.db`              | Cần build flag `SQLCIPHER`                      |
| `sled`                                                           | WASM transient state (`TappTransientState`) | FI-04 bắt buộc; không swap                      |
| `blake3`                                                         | Hash, BLAKE3 Merkle, beacon construction    |                                                 |
| `uuid` (v1.x, feature `v7`)                                      | UUID v7 time-ordered                        | `hot_dag.db` primary key                        |
| `serde` + `serde_json`                                           | Serialization                               |                                                 |
| `prost`                                                          | Protobuf (IPC control plane < 1KB)          |                                                 |
| `rustls`                                                         | TLS 1.3 + mTLS; SPKI pinning                | Không được dùng OpenSSL                         |
| `rayon`                                                          | Parallel DAG merge trên Desktop             |                                                 |
| `wasmtime`                                                       | WASM runtime — Android/Desktop/Huawei       | Không dùng trên iOS main app                    |
| `wasm3`                                                          | WASM interpreter — iOS App Sandbox          | PLT-01 bắt buộc                                 |
| `opa-wasm` hoặc embedded OPA                                     | Policy enforcement local                    |                                                 |
| `subtle`                                                         | Constant-time comparison (side-channel)     | §5.6                                            |
| `proptest`                                                       | Property-based tests (nonce uniqueness)     | §5.3                                            |
| `rand` (ring-backed)                                             | CSPRNG cho reuse_guard                      |                                                 |
| `lz4`                                                            | KV-Cache compression (F-10)                 |                                                 |
| `prometheus`                                                     | Metrics server `127.0.0.1:9100`             | Relay only                                      |
| `opentelemetry` + `opentelemetry-otlp` + `tracing-opentelemetry` | Distributed tracing                         | §9.7                                            |
| `tracing`                                                        | Structured logging                          |                                                 |
| `nats` hoặc Redis client                                         | Pub/sub fanout                              | Relay                                           |
| `cargo-nextest`                                                  | Test runner (CI gate)                       | `cargo nextest run`                             |
| `cargo-audit`                                                    | RUSTSEC advisory audit                      | CI gate, blocker                                |
| `cargo-miri`                                                     | `ZeroizeOnDrop` verification                | CI gate KEY-02                                  |
| `cargo-cyclonedx`                                                | SBOM generation (CycloneDX 1.5)             | INFRA-05                                        |
| `cosign` (CLI tool)                                              | Sign SBOM blob                              |                                                 |

**AI / ONNX stack:**

| Component       | Platform                | Format                      |
| --------------- | ----------------------- | --------------------------- |
| ONNX Runtime    | Android, Windows, Linux | `.onnx`                     |
| CoreML          | iOS, macOS              | `.mlmodelc`                 |
| HiAI SDK        | Huawei                  | `.om` (ONNX fallback)       |
| Micro-NER model | All                     | ≤ 1MB ONNX; 8MB RAM ceiling |
| Whisper Tiny    | Mobile ≥ 3GB RAM        | 39MB `.mlmodelc` / `.onnx`  |

### Flutter (Mobile — Android, iOS, Huawei)

```yaml
# pubspec.yaml
environment:
  sdk: ">=3.0.0 <4.0.0"
  flutter: ">=3.16.0"

dependencies:
  flutter:
    sdk: flutter
  ffi: ^2.1.0 # Dart FFI — TeraSecureBuffer
  plugin_platform_interface: ^2.1.0

dev_dependencies:
  tera_dart_lints: ^1.0.0 # Custom lint plugin (PLT build, PLATFORM-17)
  flutter_lints: ^3.0.0
```

Custom lint rules bắt buộc (PLATFORM-17):

```yaml
linter:
  rules:
    - tera_avoid_direct_ffi_pointer
    - tera_require_secure_buffer
```

### Tauri (Desktop — macOS, Windows, Linux)

```toml
# src-tauri/Cargo.toml
[dependencies]
tauri = { version = "1.6", features = ["api-all"] }
tauri-build = "1.5"
```

Tauri tự handle IPC; SAB Tier Ladder tự chọn (F-03). Yêu cầu `COOP+COEP` headers cho SharedArrayBuffer Tier 1.

### iOS Host Adapter (Swift)

- Xcode 15+
- `CryptoTokenKit` — Secure Enclave
- `CallKit` — PLT-03 bắt buộc cho voice
- `NSURLSession Background Transfer` — file download
- `NWPathMonitor` — AWDL detection (§6.4)
- `MultipeerConnectivity` / AWDL adapter

### Android Host Adapter (Kotlin)

- Android Gradle Plugin 8.x, `compileSdk = 34`, `targetSdk = 34`
- `BiometricPrompt` API
- Companion Device Manager `REQUEST_COMPANION_RUN_IN_BACKGROUND` — PLT-06
- FCM `priority = "high"` — PLT-06

---

## 2. MCP nào hỗ trợ (chi tiết)?

Dự án không sử dụng MCP (Model Context Protocol) theo bất kỳ nghĩa nào trong spec. Không có tham chiếu nào đến MCP.

Nếu câu hỏi ý muốn hỏi về **build/config management protocols**, xem câu 3 bên dưới.

---

## 3. Build tool — có dùng Maven không?

**Không có Maven.** TeraChat là Rust-first; hệ sinh thái build hoàn toàn khác:

| Layer              | Build Tool                                                    | Lý do                                    |
| ------------------ | ------------------------------------------------------------- | ---------------------------------------- |
| Rust Core          | `cargo` + `cargo build --release --locked`                    | Duy nhất, không thay thế                 |
| Reproducible build | Dockerfile `FROM rust:1.75.0-slim-bookworm`                   | INFRA-05, `SOURCE_DATE_EPOCH=1700000000` |
| Flutter/Dart       | `flutter build`                                               | Android/iOS/Huawei                       |
| Desktop            | `cargo tauri build`                                           | macOS/Windows/Linux                      |
| iOS signing        | `fastlane match`                                              | BIZ-SIGNING-02                           |
| Windows signing    | `signtool.exe`                                                | EV Code Signing, DigiCert KeyLocker      |
| Linux packaging    | `dpkg-build` (`.deb`), `rpmbuild` (`.rpm`), AppImage + Cosign | PLT-04                                   |
| SBOM               | `cargo cyclonedx` + `cosign sign-blob`                        | INFRA-05                                 |
| Ops scripts        | `ops/verify-reproducible-build.sh`, `ops/generate-sbom.sh`    | CICD-01                                  |

---

## 4. Biến môi trường và secrets cần thiết?

| Variable                             | Dùng ở đâu                   | Ghi chú                                                                                               |
| ------------------------------------ | ---------------------------- | ----------------------------------------------------------------------------------------------------- |
| `TERA_OTEL_ENDPOINT`                 | Relay daemon                 | OTLP collector endpoint, e.g. `http://otel-collector:4317`. Nếu unset → tracing disabled, không crash |
| `TERA_OTEL_SAMPLE_RATE`              | Relay daemon                 | `0.0–1.0`, mặc định `0.1`                                                                             |
| `SOURCE_DATE_EPOCH`                  | Docker build                 | `1700000000` — reproducible builds                                                                    |
| `APPLE_DISTRIBUTION_CERT`            | GitHub Actions / fastlane    | Encrypted GitHub Secret                                                                               |
| `IOS_PROVISIONING_PROFILE`           | GitHub Actions               | Main App + NSE + Share Extension — 3 profiles riêng                                                   |
| `ANDROID_KEYSTORE`                   | GitHub Actions               | Encrypted keystore file                                                                               |
| `GOOGLE_PLAY_JSON_KEY`               | GitHub Actions               | Google Play App Signing                                                                               |
| `WINDOWS_EV_CERT`                    | DigiCert KeyLocker Cloud HSM | ~$500/năm, bắt buộc SmartScreen                                                                       |
| `GPG_SIGNING_KEY`                    | Linux release                | `.deb`/`.rpm` packages                                                                                |
| `COSIGN_KEY`                         | SBOM + AppImage              | `release-key.pem`                                                                                     |
| `TERACHAT_CA_PUBLIC_KEY`             | ONNX model integrity         | Verify Ed25519 manifest signature (PLATFORM-18)                                                       |
| `RELAY_MTLS_CERT` + `RELAY_MTLS_KEY` | VPS Relay                    | mTLS client/server auth                                                                               |
| `BLOB_STORAGE_PRESIGN_SECRET`        | TeraRelay                    | HMAC-signed presigned URL generation (INFRA-02); client không bao giờ có credential trực tiếp         |

**Secrets không bao giờ hardcode** — tất cả đi qua GitHub Secrets hoặc HSM. `gitleaks detect` là CI gate blocker (CICD-01).

---

## 5. Project đã được Dockerized chưa?

**Relay VPS đã Dockerized.** Client apps thì không (native binary).

**Relay (VPS):** Single Rust binary, có Dockerfile:

```dockerfile
FROM rust:1.75.0-slim-bookworm AS builder
RUN apt-get install -y --no-install-recommends \
    libclang-dev=1:15.0-56 \
    pkg-config=1.8.1-1
ENV SOURCE_DATE_EPOCH=1700000000
RUN cargo build --release --locked
```

**Chaos Engineering CI** (INFRA-06): chạy qua `docker-compose` ở staging environment, scheduled daily 02:00 UTC. Results → JUnit XML artifact.

**Client apps:** Không Dockerized — native binaries (`.ipa`, `.apk`, `.exe`, `.dmg`, `.deb`).

---

## 6. DB nào cần truy cập?

| DB                     | Engine                     | Location              | Access                                                     |
| ---------------------- | -------------------------- | --------------------- | ---------------------------------------------------------- |
| `hot_dag.db`           | SQLite WAL                 | Client disk           | Rust Core only; append-only; NO UI direct access           |
| `cold_state.db`        | SQLite + SQLCipher AES-256 | Client disk           | Rust Core only; key từ Secure Enclave                      |
| `cold_state_shadow.db` | SQLite (transient)         | Client disk           | Tạm thời trong Hydration; auto-delete sau atomic rename    |
| `nse_staging.db`       | SQLite WAL                 | iOS only              | NSE Extension; ciphertext only                             |
| `wal_staging.db`       | SQLite WAL                 | VPS Relay             | Relay daemon only; STAGED→COMMITTED lifecycle              |
| `metrics_buffer.db`    | SQLite                     | Client disk           | Aggregate metrics; max 48h / 500KB                         |
| `NetworkProfile`       | SQLite row                 | Local config DB       | Rust Core; per network ID                                  |
| PostgreSQL             | PostgreSQL HA              | Bare-metal / HSM node | Workspace metadata, SCIM, Audit Logs; PITR enabled         |
| MinIO / R2 / B2        | Object Storage             | Cloud / Self-hosted   | Encrypted blob chunks; client KHÔNG có direct credentials  |
| Redis / NATS JetStream | Message queue              | VPS                   | Pub/sub fanout; external process, không trong relay binary |

**Scale rule:** ≤ 10,000 users → SQLite WAL (relay); ≥ 100,000 users → PostgreSQL HA + MinIO.

---

## 7. Credentials lấy ở đâu? Có thể tự setup không?

**Development local setup** (Solo tier — $6/month hoặc free local):

```bash
# Relay VPS — 5 phút setup (TERA-FEAT §2.4)
cargo build --release --locked
./target/release/terachat-relay \
  --db-path ./data/relay.db \
  --listen 0.0.0.0:443 \
  --cert ./certs/relay.crt \
  --key ./certs/relay.key
```

MinIO local (thay cho R2/B2):

```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=password \
  minio/minio server /data --console-address ":9001"
```

**Không có SQL migration script hay Docker Compose mẫu nào được publish trong spec hiện tại** — `ops/db-recovery.md` và `ops/shamir-bootstrap.md` được reference nhưng chưa được viết (đây là implementation gap blocker, TERA-CORE §11.4).

**Credentials production:**

- HSM quorum M-of-N (2/3 hoặc 3/5) — physical ceremony, YubiKey 5 FIPS
- Blob storage: presigned URL từ TeraRelay; developer không cần R2/B2 credentials

---

## 8. Cần Automation Test như Jules không?

Spec định nghĩa 3 tầng test bắt buộc:

**Tầng 1 — Unit/Integration (CI, blocker):**

```bash
cargo nextest run --all-features          # Unit tests tất cả platform
cargo test --test wasm_parity             # WasmParity: wasm3 vs wasmtime, delta ≤ 20ms, mem ≤ 5MB
cargo test --test crdt_dedup_contract     # CRDT inbound dedup
cargo miri test --test zeroize_verification  # ZeroizeOnDrop verification
cargo audit --deny warnings               # RUSTSEC advisory
```

**Tầng 2 — Performance Benchmarks (non-blocking, regression tracked):**

```bash
cargo bench --bench mls_epoch_rotation    # SLA ≤ 1s cho 100 members
```

**Tầng 3 — Chaos Engineering (Gov/Military gate):**
28 scenarios trong `TestMatrix.md` (chưa có file này, là gap). 4 core scenarios đã spec (INFRA-06). Chạy qua `docker-compose` staging, daily 02:00 UTC, JUnit XML output.

**Security scans (CI, blocker):**

```bash
cargo clippy -- -D tera_ffi_raw_pointer   # Custom lint: no raw pointer in pub extern C
gitleaks detect --source . --exit-code 1 # Secret scan
trivy image --exit-code 1 --severity CRITICAL  # Container CVE scan
```

**Dart/Flutter (PLATFORM-17):**

```yaml
# analyzer options
plugins:
  - tera_dart_lints
rules:
  - tera_avoid_direct_ffi_pointer
  - tera_require_secure_buffer
```

Không dùng Jules hay bất kỳ external AI test generation tool nào — tất cả test là Rust-native (`proptest`, `nextest`, `miri`).

---

## 9. Linter và Static Analysis?

| Tool                                              | Target                        | Command                                         | CI Gate?                          |
| ------------------------------------------------- | ----------------------------- | ----------------------------------------------- | --------------------------------- |
| `cargo clippy` custom lint `tera_ffi_raw_pointer` | Rust Core FFI                 | `cargo clippy -- -D tera_ffi_raw_pointer`       | Blocker                           |
| `cargo clippy` standard                           | Rust Core                     | `cargo clippy --all-features`                   | Blocker                           |
| `cargo fmt`                                       | Rust                          | `cargo fmt --check`                             | Blocker (implied)                 |
| `cargo miri`                                      | Memory safety / ZeroizeOnDrop | `cargo miri test --test zeroize_verification`   | Blocker                           |
| `cargo audit`                                     | RUSTSEC CVE                   | `cargo audit --deny warnings`                   | Blocker                           |
| `trivy`                                           | Docker container              | `trivy image --exit-code 1 --severity CRITICAL` | Blocker                           |
| `gitleaks`                                        | Secret detection              | `gitleaks detect --source . --exit-code 1`      | Blocker                           |
| `tera_dart_lints`                                 | Flutter/Dart                  | Custom analyzer plugin                          | Blocker (PLATFORM-17)             |
| `dpkg-sig --verify`                               | Linux .deb                    | `dpkg-sig --verify terachat_*.deb`              | Blocker                           |
| `cosign verify-blob`                              | Linux AppImage, SBOM          | `cosign verify-blob --key terachat-root.pub`    | Blocker                           |
| `signtool verify`                                 | Windows EXE                   | `signtool verify /pa terachat-setup.exe`        | Blocker                           |
| AppArmor/SELinux postinstall                      | Linux runtime                 | `terachat --check-permissions`                  | High (non-blocker build; runtime) |

**Không có `markdownlint` hay `eslint`** — dự án không có web frontend (Tauri backend là Rust, frontend là HTML/CSS native trong webview).
