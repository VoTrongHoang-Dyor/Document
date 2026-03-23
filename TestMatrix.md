# TestMatrix.md — TeraChat Chaos Engineering & Test Matrix

```yaml
# DOCUMENT IDENTITY
id:       "TERA-TEST"
title:    "TeraChat — Chaos Engineering & Enterprise Test Matrix"
version:  "0.3.7"
status:   "ACTIVE — Pre-requisite for Gov/Military Contracts"
date:     "2026-03-23"
audience: "QA Engineer, Security Engineer, DevSecOps, Product Manager"
purpose:  "Đặc tả kịch bản kiểm thử toàn diện cho môi trường enterprise, bao gồm
           combined-failure scenarios, chaos engineering, và pre-deployment gates."

ai_routing_hint: |
  "Mở file này khi hỏi về test scenarios, stress testing, edge cases,
   combined-failure scenarios, hoặc chuẩn bị go-live cho Gov/Military."

depends_on:
  - id: "TERA-CORE"
  - id: "TERA-FEAT"
  - id: "TERA-FUNC"
```

---

## 1. Nguyên tắc Kiểm thử

TeraChat là sản phẩm cấp enterprise vận hành trong môi trường có yêu cầu bảo mật cao và môi trường network không ổn định. Test matrix được thiết kế xung quanh ba câu hỏi:

1. **Dữ liệu có bị mất không** khi bất kỳ component nào gặp sự cố?
2. **Key material có bị lộ không** trong bất kỳ failure path nào?
3. **Hệ thống có tự phục hồi không** mà không cần intervention thủ công?

**Tiêu chí nghiệm thu bắt buộc trước bất kỳ production release nào:**

- Zero message loss trong tất cả network partition scenarios
- Zero key material exposure trong tất cả crash/OOM scenarios
- Automatic recovery trong tất cả defined failure modes
- WasmParity CI gate: 100% pass rate (wasm3 vs wasmtime semantic identity)

---

## 2. Matrix Kịch bản Cơ bản (28 Scenarios)

### 2.1 Layer 1 — Network Failures

| Scenario | Điều kiện | Expected Behavior | Timeout |
|----------|-----------|-------------------|---------|
| **SC-01** | Internet partition 30 phút → rejoin | Zero data loss; Mesh activated; full recovery < 120s | 2100s |
| **SC-02** | QUIC + gRPC blocked; WSS only | Auto-fallback; latency increase accepted; no interruption | 120s |
| **SC-03** | All ALPN paths blocked | Mesh Mode activated; UI indicator updated; no crash | 60s |
| **SC-04** | TURN server failover mid-call | Keepalived < 3s; user-perceived drop = 0 | 30s |
| **SC-05** | iOS AWDL off (Hotspot on) + active voice call | BLE Tier 3; voice queue 90s TTL; notification shown | 150s |
| **SC-06** | DNS manipulation / QUIC downgrade attack | Socket Panic Circuit Breaker; 30s block; log alert | 60s |
| **SC-07** | Federation bridge timeout mid-message | OPA circuit breaker; message buffered; retry on reconnect | 90s |

### 2.2 Layer 2 — Storage & Database Failures

| Scenario | Điều kiện | Expected Behavior | Timeout |
|----------|-----------|-------------------|---------|
| **SC-08** | Jetsam kill NSE mid-WAL write | WAL crash-safe replay; no notification loss; no key exposure | 30s |
| **SC-09** | Hard power loss during Hydration | Resume from Hydration_Checkpoint; cold_state.db intact | 120s |
| **SC-10** | cold_state.db migration fail | Drop + rebuild from hot_dag.db; log COLD_STATE_REBUILD | 180s |
| **SC-11** | WAL bloat > 200MB mobile | MemoryPressureWarning emitted; BGTask VACUUM scheduled | 60s |
| **SC-12** | Shadow DB rename race with NSURLSession | Write lock queues to hot_dag.db; no corruption | 30s |
| **SC-13** | Relay SIGKILL with 1000 STAGED events | Zero data loss; wal_staging.db replay on restart; < 60s | 300s |

### 2.3 Layer 3 — Crypto & Key Failures

| Scenario | Điều kiện | Expected Behavior | Timeout |
|----------|-----------|-------------------|---------|
| **SC-14** | MLS Push_Key version mismatch (iOS NSE) | Ghost Push → nse_staging.db → Main App decrypt | 30s |
| **SC-15** | NSE load ONNX attempt (violation) | NsePolicy::ProhibitOnnxLoad; regex-only PII detection fallback | 10s |
| **SC-16** | Android Doze mid-ZeroizeOnDrop | Wrap-on-derive pattern; no key material in page; < 1ms window | 60s |
| **SC-17** | Dead Man Switch during active CallKit call | DeadManDeferralEntry logged; lockout deferred until call ends | 180s |
| **SC-18** | EMDP Shun for regular mesh member (Case A) | Member evicted; TempGroupKey derived; tainted_escrow logged | 30s |
| **SC-19** | EMDP Shun for Tactical Relay (Case B) | EMDP terminated; new election; EmdpTerminated signal | 30s |
| **SC-20** | ONNX model BLAKE3 mismatch | AI worker terminated; ComponentFault Critical; ModelIntegrityViolation audit | 10s |
| **SC-21** | License JWT expired T+0 + active emergency call | Chat survives; Admin Console lock only; call uninterrupted | 60s |

### 2.4 Layer 4 — Runtime & WASM Failures

| Scenario | Điều kiện | Expected Behavior | Timeout |
|----------|-----------|-------------------|---------|
| **SC-22** | WASM sandbox panic (.tapp) | catch_unwind; ComponentFault; restart after 1s; Core unaffected | 30s |
| **SC-23** | XPC Worker OOM (macOS) mid-Smart Approval | Journal PENDING → abort; "Phiên ký bị gián đoạn" prompt | 60s |
| **SC-24** | QUIC + gRPC parallel probe race (NetworkProfile corruption) | gRPC wins; probe_fail_count NOT incremented; strict_compliance unchanged | 30s |
| **SC-25** | All-iOS Mesh; EMDP TTL 60min expires | SoloAppendOnly mode; merge deferred; EmdpExpiryWarning at T-10 & T-2 | 4200s |

### 2.5 Layer 5 — Combined Failures (Gov/Military Gate)

> **Non-negotiable**: Tất cả 4 combined-failure scenarios phải pass trước Gov/Military contract.

| Scenario | Điều kiện Combined | Expected Behavior |
|----------|-------------------|-------------------|
| **SC-26** | iOS AWDL off + TURN failover + CRDT merge > 5000 events | AWDL warn → BLE → TURN preconnect → CRDT queue; zero loss |
| **SC-27** | Jetsam NSE mid-WAL + Desktop offline + EMDP active | WAL rollback → DAG self-heal → EMDP key escrow intact |
| **SC-28** | EMDP 60min + Desktop reconnect + 1000 relay messages | Key escrow decrypt → DAG merge → epoch reconcile; < 30s |
| **SC-29** | Battery < 20% + Mesh active + Whisper loading attempt | Whisper disabled; voice text-fallback; BLE only; no crash |
| **SC-30** | AppArmor deny memfd + mlock + seccomp active (Linux) | Graceful degrade to software crypto; performance warn emitted |
| **SC-31** | License expire T+0 + Active Gov emergency call | Call continues; Admin Console lock; no data loss; auto-audit |
| **SC-32** | Android Doze mid-ZeroizeOnDrop + StrongBox wrap | Key material zero-exposure; Wrap-on-derive completes atomically |
| **SC-33** | Dart FFI GC race: buffer released before releaseNow() | NativeFinalizer catches; ZeroizeOnDrop executes; no UAF; metric logged |

---

## 3. Pre-Production Deployment Gates

### 3.1 Automated CI Gates (Blocker)

Tất cả phải pass trước merge vào `main`:

```bash
# Security
cargo clippy -- -D tera_ffi_raw_pointer          # No raw ptr in pub extern C
cargo miri test --test zeroize_verification       # ZeroizeOnDrop coverage
cargo audit --deny warnings                       # RUSTSEC advisory
gitleaks detect --source . --exit-code 1          # Secret leak scan
trivy image --exit-code 1 --severity CRITICAL     # CVE container scan

# Correctness
cargo nextest run --all-features                  # Full test suite
cargo test --test wasm_parity -- --timeout 60     # wasm3 vs wasmtime parity
cargo test --test crdt_dedup_contract             # CRDT inbound dedup

# Build & Signing
ops/verify-reproducible-build.sh
ops/generate-sbom.sh && cosign sign-blob ...
signtool verify /pa terachat-setup.exe            # Windows EV
dpkg-sig --verify terachat_*.deb                  # Linux GPG
```

### 3.2 Pre-Gov Go-Live Checklist (Manual Verification)

Security auditor độc lập phải verify trước khi ký Gov/Military contract:

- [ ] Ed25519 signature verification trên mọi OPA Policy bundle
- [ ] HSM FIPS 140-3 Shamir ceremony (3-of-5 reconstruction test)
- [ ] Air-gapped license JWT validation (TPM monotonic counter check)
- [ ] EMDP Key Escrow roundtrip đầy đủ (Desktop offline 60min → reconnect)
- [ ] Crypto-shred verification (forensic tool: không recovery được sau wipe)
- [ ] WasmParity gate: 100% pass rate
- [ ] AppArmor/SELinux profiles verified trên target Gov Linux distro
- [ ] All 33 chaos scenarios pass automated CI suite

---

## 4. Platform-Specific Test Coverage

| Platform | Required Pass Rate | Critical Scenarios |
|---------|------------------|-------------------|
| 📱 iOS | 100% SC-01–21 | SC-08, SC-14, SC-15, SC-17, SC-26 |
| 📱 Android | 100% SC-01–21 | SC-16, SC-24 |
| 📱 Huawei | 100% SC-01–20 | SC-16 (TrustZone variant) |
| 💻 macOS | 100% SC-01–25 | SC-23 (XPC) |
| 🖥️ Windows | 100% SC-01–20 | SC-33 |
| 🖥️ Linux | 100% SC-01–20, SC-30 | SC-30 (AppArmor/SELinux) |

---

## 5. Observability Trong Chaos Testing

Mỗi scenario phải emit ít nhất:

1. **CoreSignal** phù hợp (TierChanged, ComponentFault, EmdpExpiryWarning, v.v.)
2. **Audit log entry** (Ed25519 signed, nếu event là security-relevant)
3. **Metric increment** (relevant counter/gauge trong ClientMetricBatch)

Scenarios liên quan đến key material phải **không emit** bất kỳ log nào chứa key bytes, ngay cả trong debug mode.

---

*Cross-references: TERA-CORE §15 · TERA-FEAT §INFRA-06 · TERA-FUNC Module 9*
