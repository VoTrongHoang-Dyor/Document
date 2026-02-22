# TeraChat Enterprise OS - Task Assignment Document

> **Version:** V0.2.1 Alpha  
> **Last Updated:** 2026-02-06  
> **Status:** Planning Phase

---

## 📋 Tổng Quan Dự Án

**TeraChat Enterprise OS** là hệ thống giao tiếp doanh nghiệp với kiến trúc **Desktop-First**, **Federated Clusters**, và tích hợp **Web3 (Blockchain/Crypto)**. Tài liệu này phân công nhiệm vụ chi tiết cho từng bộ phận kỹ thuật qua **4 giai đoạn phát triển**.

---

## 🗓️ Giai Đoạn Phát Triển

| Phase | Tên Giai Đoạn | Timeline | Focus |
|-------|---------------|----------|-------|
| **Phase 1** | Pre-Alpha (Foundation) | 8-10 weeks | Core Architecture + Security Foundation |
| **Phase 2** | Alpha (Features) | 10-12 weeks | User Features + Integration |
| **Phase 3** | Beta (Hardening) | 6-8 weeks | Security Hardening + Testing |
| **Phase 4** | Release Candidate | 4-6 weeks | Production Ready + Deployment |

---

# 📦 PHASE 1: PRE-ALPHA (Foundation)

> **Mục tiêu:** Xây dựng nền tảng kiến trúc cốt lõi, bảo mật cơ bản, và infrastructure.

---

## Front-End Team

### 1.1 Tauri Desktop Shell Setup
- [ ] **FE-1.1.1** Khởi tạo project Tauri V2 với React/TypeScript
- [ ] **FE-1.1.2** Thiết lập cấu trúc thư mục theo monorepo (apps/desktop-shell)
- [ ] **FE-1.1.3** Cấu hình build pipeline cho Windows/macOS/Linux
- [ ] **FE-1.1.4** Tích hợp Rust Core Bridge (`tauri::command`)

### 1.2 Base UI Components
- [ ] **FE-1.2.1** Design System foundation (CSS Variables, Typography, Colors)
- [ ] **FE-1.2.2** Core components: Button, Input, Modal, Toast
- [ ] **FE-1.2.3** Navigation/Sidebar layout skeleton
- [ ] **FE-1.2.4** Theme switching (Light/Dark mode)

### 1.3 Security UI Integration
- [ ] **FE-1.3.1** Integrate Screenshot Protection API (`SetWindowDisplayAffinity` Windows / `sharingType = .none` macOS)
- [ ] **FE-1.3.2** Implement Dynamic Watermark overlay (User ID + Time + Random position)
- [ ] **FE-1.3.3** Input Jammer integration for sensitive views (chặn Global Hooks)

**Dependencies:** Backend - Rust Core module ready  
**Review:** Security Engineering - Verify anti-screenshot implementation

---

## Back-End Team

### 1.4 Rust Core Engine
- [ ] **BE-1.4.1** Khởi tạo Rust workspace với Cargo
- [ ] **BE-1.4.2** Implement Memory-Safe data structures với `Zeroize` + `Secrecy`
- [ ] **BE-1.4.3** Build Secure Enclave/TPM Bridge layer
- [ ] **BE-1.4.4** Implement RAM Pinning (`mlock()` / `VirtualLock()`)

### 1.5 Protocol Core (packages/1-protocol-core)
- [ ] **BE-1.5.1** Định nghĩa Protobuf schemas cho messages
- [ ] **BE-1.5.2** Setup `buf generate` pipeline cho TypeScript + Rust
- [ ] **BE-1.5.3** Implement MLS (RFC 9420) TreeKEM structure
- [ ] **BE-1.5.4** Epoch Rotation mechanism cho Key management

### 1.6 Local Database Layer
- [ ] **BE-1.6.1** SQLite + SQLCipher integration
- [ ] **BE-1.6.2** DEK/KEK encryption hierarchy implementation
- [ ] **BE-1.6.3** Crypto-Shredding deletion mechanism
- [ ] **BE-1.6.4** Database schema cho enterprise_users và pki_bindings

**Dependencies:** DevOps - CI/CD pipeline, Security - Key management review  
**Critical:** Phải pass Security review trước khi merge

---

## DevOps Team

### 1.7 Monorepo Infrastructure
- [ ] **DO-1.7.1** Setup Turborepo với workspace configuration
- [ ] **DO-1.7.2** Configure GitHub Actions cho Lint + Build + Test
- [ ] **DO-1.7.3** Setup Private Registry (Artifactory/Harbor) cho dependencies
- [ ] **DO-1.7.4** Implement Supply Chain Security (SBOM generation)

### 1.8 Development Environment
- [ ] **DO-1.8.1** Docker Compose cho local development
- [ ] **DO-1.8.2** Pre-commit hooks (Lint, Format, Security scan)
- [ ] **DO-1.8.3** Secrets management với Vault integration
- [ ] **DO-1.8.4** Documentation deployment (docs/ folder)

**Security Gate:** Mọi dependency phải được scan CVE trước khi approve

---

## UI/UX Team

### 1.9 Design System Foundation
- [ ] **UX-1.9.1** Color palette definition (CSS Variables)
- [ ] **UX-1.9.2** Typography scale và spacing system
- [ ] **UX-1.9.3** Icon library selection và integration
- [ ] **UX-1.9.4** Component library documentation (Storybook)

### 1.10 Critical User Flows (Wireframes)
- [ ] **UX-1.10.1** Onboarding flow (BYOI - Bring Your Own Identity)
- [ ] **UX-1.10.2** Chat interface skeleton
- [ ] **UX-1.10.3** Security warning overlays ("Digital Bunker" mode)
- [ ] **UX-1.10.4** Biometric prompt UI guidelines

**Deliverable:** Figma/Sketch files + Component specs

---

## Security Engineering Team

### 1.11 Threat Modeling
- [ ] **SEC-1.11.1** STRIDE analysis cho tất cả features
- [ ] **SEC-1.11.2** Attack surface mapping document
- [ ] **SEC-1.11.3** Security RFC drafts cho mỗi module
- [ ] **SEC-1.11.4** Risk Priority Matrix update

### 1.12 Cryptography Foundation
- [ ] **SEC-1.12.1** Ed25519 + X.509 Binding implementation review
- [ ] **SEC-1.12.2** Post-Quantum (Kyber/Dilithium) research spike
- [ ] **SEC-1.12.3** Key Hierarchy design (Master Key → KEK → DEK)
- [ ] **SEC-1.12.4** Hardware Counter verification logic

### 1.13 Fuzzing Infrastructure Setup
- [ ] **SEC-1.13.1** Setup cargo-fuzz với libFuzzer
- [ ] **SEC-1.13.2** Fuzzing targets: Packet Parser, Crypto Handshake
- [ ] **SEC-1.13.3** LLVM Sanitizers integration (ASan, MSan, UBSan)
- [ ] **SEC-1.13.4** CI gate: 10-minute smoke fuzz cho PRs

**Veto Power:** Security có quyền block mọi deployment nếu Fuzzing Gate fail

---

## Full-Stack Lead (Senior Oversight)

### 1.14 Architecture Review
- [ ] **FS-1.14.1** Review và approve Protobuf definitions
- [ ] **FS-1.14.2** Cross-team dependency coordination
- [ ] **FS-1.14.3** RFC approval process enforcement
- [ ] **FS-1.14.4** Code review cho security-critical modules

### 1.15 Technical Debt Management
- [ ] **FS-1.15.1** Establish coding standards document
- [ ] **FS-1.15.2** Define module boundaries và interfaces
- [ ] **FS-1.15.3** Setup technical decision log (ADR)

### 1.16 Documentation Updates
- [x] **DOC-1.16.1** Update Tech Spec with Web-based Installer (Launcher) design

---

# 📦 PHASE 2: ALPHA (Features)

> **Mục tiêu:** Triển khai các tính năng người dùng chính, integration với enterprise systems.

---

## Front-End Team

### 2.1 Secure Workspace UI
- [ ] **FE-2.1.1** Chat interface với MLS encryption indicator
- [ ] **FE-2.1.2** Group management UI (Create, Invite, Kick)
- [ ] **FE-2.1.3** File attachment với progress indicator
- [ ] **FE-2.1.4** Offline mode indicator và sync status

### 2.2 Code Sandbox (Mini-App)
- [ ] **FE-2.2.1** WASM Sandbox container integration
- [ ] **FE-2.2.2** Code viewer với Watermark overlay
- [ ] **FE-2.2.3** Copy protection (disabled clipboard)
- [ ] **FE-2.2.4** Ephemeral view (auto-close + memory wipe)

### 2.3 Smart Approval UI (Web3)
- [ ] **FE-2.3.1** `/approve` command parser
- [ ] **FE-2.3.2** Smart Contract summary card
- [ ] **FE-2.3.3** Biometric trigger integration (Windows Hello / TouchID)
- [ ] **FE-2.3.4** Transaction confirmation với Randomized Keyboard

### 2.4 Admin Panel
- [ ] **FE-2.4.1** User management dashboard
- [ ] **FE-2.4.2** Revoke Access button với confirmation
- [ ] **FE-2.4.3** Audit log viewer
- [ ] **FE-2.4.4** Group policy configuration

**Dependencies:** Backend API ready, Security - WYSIWYS review

---

## Back-End Team

### 2.5 Federated Relay Server
- [ ] **BE-2.5.1** Enterprise Relay binary (apps/enterprise-relay)
- [ ] **BE-2.5.2** MLS Delivery Service implementation
- [ ] **BE-2.5.3** Sealed Sender routing (To without From)
- [ ] **BE-2.5.4** Log Streams (Kafka P2P) integration

### 2.6 Identity & Access Management
- [ ] **BE-2.6.1** Keycloak/Dex broker integration
- [ ] **BE-2.6.2** SCIM listener cho Azure AD sync
- [ ] **BE-2.6.3** PKI Binding database operations
- [ ] **BE-2.6.4** Auto-revoke trigger khi user deactivated

### 2.7 OPA Policy Engine
- [ ] **BE-2.7.1** packages/3-policy-engine setup
- [ ] **BE-2.7.2** Rego rules cho department-based access
- [ ] **BE-2.7.3** Geofencing policy implementation
- [ ] **BE-2.7.4** Policy evaluation service endpoint

### 2.8 WebRTC Calling
- [ ] **BE-2.8.1** Signaling server (WebSocket)
- [ ] **BE-2.8.2** TURN cluster configuration (Coturn)
- [ ] **BE-2.8.3** DTLS-SRTP encryption setup
- [ ] **BE-2.8.4** SAS (Short Authentication String) generation

### 2.9 Smart Contract (TON)
- [ ] **BE-2.9.1** packages/2-smart-contracts workspace
- [ ] **BE-2.9.2** ProjectBudgetVault contract (Tact)
- [ ] **BE-2.9.3** Jetton Transfer integration
- [ ] **BE-2.9.4** Replay protection với queryId

**Critical:** Smart Contract phải pass Formal Verification trước deploy

---

## DevOps Team

### 2.10 Kubernetes Infrastructure
- [ ] **DO-2.10.1** Helm Charts cho Relay, Signaling, IAM
- [ ] **DO-2.10.2** HPA (Horizontal Pod Autoscaler) configuration
- [ ] **DO-2.10.3** Pod Anti-Affinity rules
- [ ] **DO-2.10.4** Resource limits tuning

### 2.11 Database HA
- [ ] **DO-2.11.1** PostgreSQL HA với Repmgr
- [ ] **DO-2.11.2** Redis Sentinel setup
- [ ] **DO-2.11.3** Backup automation (daily/hourly)
- [ ] **DO-2.11.4** Disaster recovery testing

### 2.12 Observability Stack
- [ ] **DO-2.12.1** Prometheus metrics collection
- [ ] **DO-2.12.2** Loki log aggregation
- [ ] **DO-2.12.3** Tempo distributed tracing
- [ ] **DO-2.12.4** Grafana dashboards

---

## UI/UX Team

### 2.13 Feature UI Design
- [ ] **UX-2.13.1** Code Sandbox visual design
- [ ] **UX-2.13.2** Smart Approval transaction card
- [ ] **UX-2.13.3** Calling UI (video/voice)
- [ ] **UX-2.13.4** Admin panel layouts

### 2.14 Adaptive Cards System
- [ ] **UX-2.14.1** Card component library
- [ ] **UX-2.14.2** Interactive button states
- [ ] **UX-2.14.3** Form inputs trong cards
- [ ] **UX-2.14.4** Enterprise notification templates

---

## Security Engineering Team

### 2.15 Biometric Security
- [ ] **SEC-2.15.1** WYSIWYS vulnerability mitigation
- [ ] **SEC-2.15.2** System-Managed Trusted UI verification
- [ ] **SEC-2.15.3** Anti-Overlay Detection service
- [ ] **SEC-2.15.4** Rate limiting cho signing requests

### 2.16 Endpoint Trust
- [ ] **SEC-2.16.1** Remote Attestation flow (TPM 2.0)
- [ ] **SEC-2.16.2** DCAppAttestService (iOS) integration
- [ ] **SEC-2.16.3** Play Integrity API (Android) verification
- [ ] **SEC-2.16.4** MEETS_STRONG_INTEGRITY enforcement

### 2.17 Formal Verification
- [ ] **SEC-2.17.1** Z3 SMT Solver integration
- [ ] **SEC-2.17.2** Tact → SMT-LIB converter
- [ ] **SEC-2.17.3** Invariant definitions (Solvency, Access Control)
- [ ] **SEC-2.17.4** CI gate: Block deploy nếu SAT

---

## Full-Stack Lead (Senior Oversight)

### 2.18 Integration Testing
- [ ] **FS-2.18.1** packages/4-integration-tests setup
- [ ] **FS-2.18.2** E2E scenarios definition
- [ ] **FS-2.18.3** Cross-module testing framework
- [ ] **FS-2.18.4** Performance benchmarks

---

# 📦 PHASE 3: BETA (Hardening)

> **Mục tiêu:** Hardening bảo mật, stress testing, và chuẩn bị production.

---

## Front-End Team

### 3.1 Binary Hardening
- [ ] **FE-3.1.1** O-LLVM obfuscation integration
- [ ] **FE-3.1.2** Control Flow Flattening pass
- [ ] **FE-3.1.3** String Encryption (XOR) với obfstr
- [ ] **FE-3.1.4** Tamper Detection (Self-Checksumming)

### 3.2 Performance Optimization
- [ ] **FE-3.2.1** Bundle size reduction
- [ ] **FE-3.2.2** Lazy loading cho heavy components
- [ ] **FE-3.2.3** Memory profiling và leak detection
- [ ] **FE-3.2.4** Startup time optimization

---

## Back-End Team

### 3.3 Dead Man Switch
- [ ] **BE-3.3.1** Hardware Monotonic Counter integration
- [ ] **BE-3.3.2** Server-side "Last Valid Counter Value" storage
- [ ] **BE-3.3.3** Offline Grace Period (72h) logic
- [ ] **BE-3.3.4** Self-Destruct trigger mechanism

### 3.4 Remote Wipe Implementation
- [ ] **BE-3.4.1** Epoch Rotation event listener
- [ ] **BE-3.4.2** KeyStore.deleteKeys() integration
- [ ] **BE-3.4.3** Database reset mechanism
- [ ] **BE-3.4.4** File system cleanup

### 3.5 Mesh Network Hardening
- [ ] **BE-3.5.1** Node rotation for MITM prevention
- [ ] **BE-3.5.2** Byzantine fault tolerance
- [ ] **BE-3.5.3** Traffic padding (PADME protocol)
- [ ] **BE-3.5.4** Cover traffic generation

---

## DevOps Team

### 3.6 Chaos Engineering
- [ ] **DO-3.6.1** Chaos Mesh integration
- [ ] **DO-3.6.2** Pod kill scenarios
- [ ] **DO-3.6.3** Network partition testing
- [ ] **DO-3.6.4** "War Room" drill documentation

### 3.7 Load Testing
- [ ] **DO-3.7.1** 5000 CCU stress test
- [ ] **DO-3.7.2** SLA verification (99.9% uptime, <200ms latency)
- [ ] **DO-3.7.3** Auto-scaling validation
- [ ] **DO-3.7.4** Failover time measurement

### 3.8 Air-Gapped Deployment
- [ ] **DO-3.8.1** Offline bundle creation (docker save)
- [ ] **DO-3.8.2** Harbor private registry setup guide
- [ ] **DO-3.8.3** Delta patching (BSDiff) implementation
- [ ] **DO-3.8.4** MDM configuration templates

---

## Security Engineering Team

### 3.9 Penetration Testing
- [ ] **SEC-3.9.1** Internal pen test execution
- [ ] **SEC-3.9.2** External audit preparation
- [ ] **SEC-3.9.3** Bug bounty program design
- [ ] **SEC-3.9.4** Vulnerability remediation tracking

### 3.10 Deep Fuzzing
- [ ] **SEC-3.10.1** 24h continuous fuzzing run
- [ ] **SEC-3.10.2** Third-party library fuzzing
- [ ] **SEC-3.10.3** Stateful protocol fuzzing
- [ ] **SEC-3.10.4** Crash triage và fix

### 3.11 RASP Implementation
- [ ] **SEC-3.11.1** Runtime protection layer
- [ ] **SEC-3.11.2** Anti-debug mechanisms
- [ ] **SEC-3.11.3** Memory dump prevention
- [ ] **SEC-3.11.4** UEBA baseline establishment

---

# 📦 PHASE 4: RELEASE CANDIDATE

> **Mục tiêu:** Production-ready, documentation, và deployment.

---

## All Teams

### 4.1 Documentation
- [ ] **DOC-4.1.1** API documentation (OpenAPI spec)
- [ ] **DOC-4.1.2** Deployment guide
- [ ] **DOC-4.1.3** Operations runbook
- [ ] **DOC-4.1.4** Incident response playbook

### 4.2 Production Deployment
- [ ] **DO-4.2.1** values-production-5k.yaml finalization
- [ ] **DO-4.2.2** Helm install procedure
- [ ] **DO-4.2.3** GitOps workflow (ArgoCD)
- [ ] **DO-4.2.4** Rollback procedures

### 4.3 Final Security Audit
- [ ] **SEC-4.3.1** Security checklist pass
- [ ] **SEC-4.3.2** Reproducible builds verification
- [ ] **SEC-4.3.3** SBOM publication
- [ ] **SEC-4.3.4** Compliance documentation (GDPR)

### 4.4 Go-Live Checklist
- [ ] **FS-4.4.1** RFC compliance verification
- [ ] **FS-4.4.2** All Fuzzing gates pass
- [ ] **FS-4.4.3** Chaos drill success confirmation
- [ ] **FS-4.4.4** SLA metrics achieved

---

# 📊 Cross-Functional Protocols (Bắt Buộc)

> Các quy tắc **BẮT BUỘC** tuân thủ theo GEMINI.md và user_rules

## RFC Mandate
- Mọi feature phải có RFC được approve bởi **Security + Backend + Frontend** trước khi code

## Contract-First Locking
- Frontend/Backend **CẤM** viết JSON structs thủ công
- Phải dùng `buf generate` từ Protobuf

## Red Button Veto
- Security có quyền **veto tuyệt đối** với deployment
- Fuzzing Gate / Z3 Proof fail = Block deployment

## War Room Drills
- Mỗi major release phải qua "Chaos Game Day"
- DevOps trigger failures, QA verify recovery

---

# 📝 Legend

| Status | Meaning |
|--------|---------|
| `[ ]` | Chưa bắt đầu |
| `[/]` | Đang thực hiện |
| `[x]` | Hoàn thành |
| `[!]` | Blocked |

---

> **Note:** File này là living document, cập nhật liên tục theo tiến độ dự án.
