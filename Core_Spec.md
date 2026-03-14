# Core_Spec.md — TeraChat Alpha v0.3.0

> **Status:** `ACTIVE — Implementation Reference`
> **Audience:** Backend Engineer · DevOps · Security / Cryptography Engineer
> **Scope:** Infrastructure, Security, Cryptography, Network Protocols — Implementation-level only.
> **Last Updated:** 2026-03-11
> **Depends On:** *(root spec — no external deps)*
> **Consumed By:** `Feature_Spec.md` · `Design.md` · `Web_Marketplace.md`

---

## CHANGELOG

| Version | Date | Change Summary |
| ------- | ---------- | ---------------------------------------------------------------------------- |
| v0.3.6 | 2026-03-13 | Deprecate eBPF/XDP, Hardware TEE (SGX/SEV), mlock() Pinning, and Envoy Sidecar to resolve deployment bottlenecks on shared VPS. |
| v0.3.5 | 2026-03-13 | Add §3.5 Lightweight Micro-Core Relay; §4.6 Soft-Enclave WASM Isolation; §3.4.2 SQLite OOM Prevention |
| v0.3.0 | 2026-03-11 | Remove ODES/Blind Shard → E2EE Cloud Backup (§9.1); Remove JCAS 3D-A* + Power Analysis NOPs; §5.9 simplified → Gossip Broadcast + iBeacon only |
| v0.2.9 | 2026-03-05 | Add §5.35 Hierarchical Crypto-Shredding; §5.36 SSA Retroactive Taint; Anti-Snapshot TPM 2.0 Monotonic Counter |
| v0.2.8 | 2026-03-04 | Add §9.2 Constant-time Memory Access; §5.24 EMIP Plugin Integrity; §6.13 TeraVault VFS |

---

## CONTRACT: Implementation Requirements

> **Đọc toàn bộ §0 Data Object Catalog trước khi implement bất kỳ thứ gì.**
> Vi phạm bất kỳ ràng buộc dưới đây là **blocker** — không merge.

- [ ] Mọi Private Key **phải** nằm trong Secure Enclave (iOS/macOS) hoặc StrongBox (Android) hoặc TPM 2.0 (Desktop). Không được lưu key trên disk dưới dạng plaintext.
- [ ] Mọi ephemeral plaintext buffer **phải** dùng `ZeroizeOnDrop` (RAII). Không để plaintext tồn tại sau khi scope kết thúc.
- [ ] Mọi network I/O giữa client–server **phải** qua TLS 1.3 + mTLS. Không có channel không mã hóa.
- [ ] Mọi thay đổi schema DB **phải** backward-compatible với WAL replay. Migration script bắt buộc.
- [ ] Mọi cryptographic operation **phải** dùng thư viện `ring` hoặc `RustCrypto` — không implement crypto tự làm.
- [ ] Mọi operation ghi vào Audit Log **phải** ký `Ed25519` trước khi persist. Log unsigned = bị từ chối.

---

## 0. Data Object Catalog (Danh mục Đối tượng Dữ liệu)

> Mỗi object liệt kê dưới đây là một **đơn vị dữ liệu** độc lập có schema, vòng đời, và ràng buộc bảo mật rõ ràng. Các thuật toán (xem Section 4–5) chỉ là *operations* tác động lên những object này.

### 🔑 Domain: Cryptographic Identity

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `DeviceIdentityKey` | Ed25519 Key Pair | Secure Enclave / StrongBox | Permanent (hardware-bound) | §4.3 |
| `Company_Key` | AES-256-GCM Root Key | HKMS (wrapped by DeviceKey) | Per-workspace, rotated on member exit | §4.1 |
| `Epoch_Key` | MLS Leaf Key | RAM (Userspace) | Per MLS Epoch, zeroized on rotation | §4.2 |
| `ChunkKey` | AES-256-GCM Ephemeral | Rust `ZeroizeOnDrop` struct | Alive for 1 chunk (~2MB), then zeroized | §5.18 |
| `Session_Key` | ECDH Curve25519 Derived | RAM (Userspace) | Per session, zeroized after disconnect | §5.10.2 |

### 📦 Domain: MLS Session Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `KeyPackage` | MLS RFC 9420 Struct | Server (public) / Local DB | Refreshed periodically | §4.2 |
| `Welcome_Packet` | ECIES-encrypted payload | Encrypted in-flight | Single use, consumed on join | §5.10.2 |
| `TreeKEM_Update_Path` | MLS tree delta | In-memory, broadcast | Per epoch rotation | §5.14, §5.15 |
| `Epoch_Ratchet` | Sequence counter | `hot_dag.db` | Monotonically increasing | §4.2 |

### 🌐 Domain: Mesh Network Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `BLE_Stealth_Beacon` | 31-byte BLE Adv PDU | Broadcast-only (air) | Ephemeral per scan cycle | §5.9.3 |
| `Identity_Commitment` | `HMAC(R, PK_identity)[0:8]` | Embedded in Beacon | Per session nonce | §5.9.3 |
| `Shun_Record` | `{Node_ID, Ed25519_Sig, HLC}` | `hot_dag.db` broadcast | Until node is rehabilitated | §5.10 |
| `MergeCandidate` | `{Node_ID, BLAKE3_Hash, HLC}` | RAM only | Duration of Split-brain resolution | §5.12, §5.16 |
| `Hash_Frontier` | `{Vector_Clock, Root_Hash}` | `hot_dag.db` | Updated on every Gossip round | §5.15 |

### 📊 Domain: DAG State Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `CRDT_Event` | Typed append-only log entry | `hot_dag.db` (WAL) | Permanent (Append-Only) | §5.10.1 |
| `HLC_Timestamp` | `{wall_clock, logical_counter}` | Embedded in every Event | Attached to event, immutable | §5.14 |
| `Tombstone_Stub` | `{entity_id, hlc, type=DELETED}` | `cold_state.db` | Permanent (never physically deleted) | §5.10.1, §5.17 |
| `Proof_Bundle` | `{Ed25519_Sig, HLC, Evidence}` | Encrypted broadcast | Until dispute resolved | §5.10.3 |

### 🔧 Domain: Recovery & Audit Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `Snapshot_CAS` | Content-Addressable Hash | `TeraVault VFS` | Permanent | §5.10.2, §6.13 |
| `Hydration_Checkpoint` | `{Snapshot_CAS_UUID, last_chunk_index}` | `hot_dag.db` | Overwritten on each successful chunk | §6.14.1 |
| `Monotonic_Counter` | TPM 2.0 hardware counter | TPM chip register | Hardware-bound, tamper-evident | §4.5 |

---

## 1. System Overview

### 1.1 Feature Requirements (Zero-Knowledge, E2EE)

- **E2EE tuyệt đối:** Mọi payload mã hóa tại thiết bị đầu cuối bằng `Company_Key` trước khi rời thiết bị.
- **Zero-Knowledge Server:** ☁️ Server chỉ thấy ciphertext blob — không biết sender thực, nội dung, từ khóa tìm kiếm.
- **Hardware Root of Trust:** Private Key giam trong chip vật lý (Secure Enclave/StrongBox/TPM 2.0). Không bao giờ rời chip.
- **Forward Secrecy:** MLS Epoch Rotation — khóa cũ bị hủy khi thành viên rời nhóm.

### 1.1.1 Hardware Root of Trust & Anti-Extraction (Chống Xâm nhập Vật lý)

- 📱 **Xác thực Mật mã Ràng buộc Sinh trắc học phần cứng (Biometric-Bound Cryptographic Handshake):** Khởi tạo khóa E2EE `Device_Key` trong Secure Enclave/StrongBox đi kèm cờ kiểm soát truy cập `kSecAccessControlBiometryCurrentSet` ép buộc xác thực sinh trắc học (FaceID/TouchID). Kích hoạt cơ chế `ZeroizeOnDrop` ghi đè `0x00` lên vùng nhớ chứa `OIDC_ID_Token` để tiêu hủy dữ liệu ngay khi nhận tín hiệu lỗi từ phần cứng. Lõi Rust Ký số (Sign) `OIDC_ID_Token` bằng Private Key vừa sinh để tạo chứng nhận `Proof_of_Identity_and_Device` đệ trình lên máy chủ TeraChat.
- 📱💻🖥️ **Enterprise PIN Độc lập & Kỹ thuật Bọc Khóa Kép (Dual-Wrapped KEK):** Thuật toán Argon2id tinh chỉnh độ trễ (0.5s CPU) để sinh `Fallback_KEK` chống bẻ khóa bằng GPU/ASIC. Nhân bản và bọc `Device_Key` thành hai bản độc lập (Bản 1 qua Secure Enclave/StrongBox, Bản 2 qua `Fallback_KEK`). Hàm `Drop()` kết hợp cơ chế Zeroize xóa sạch mã PIN và KEK khỏi bộ nhớ RAM ngay sau thao tác bọc khóa.
- 📱💻🖥️ **Luồng Fallback Mật mã qua FFI Pointer (Cryptographic PIN Fallback):** Truyền mã PIN 6 số từ UI Native xuống Lõi Rust thông qua con trỏ bộ nhớ (FFI Pointer) nhằm tránh rò rỉ trên UI state. Tái tạo `Fallback_KEK` để mở khóa Bản bọc 2 và trích xuất `Device_Key` hợp lệ. Ký số trực tiếp lên `OIDC_ID_Token` bằng Private Key để xác thực định danh với máy chủ, sau đó ghi đè `0x00` lên vùng RAM chứa PIN thô bằng `ZeroizeOnDrop`.
- 📱💻🖥️ **Cơ chế Tự hủy Mật mã (Ruthless Cryptographic Self-Destruct):** Bộ đếm trạng thái `Failed_PIN_Attempts` lưu trữ mã hóa cấp thấp với giới hạn tối đa 5 lần thử sai liên tiếp. Khi vượt hạn mức, lệnh Wipe thực thi xóa trắng (Crypto-Shredding) toàn bộ Local Database và thẻ `OIDC_ID_Token`. Tiêu hủy (Băm nát) vĩnh viễn 2 bản bọc của `Device_Key` để ép ứng dụng quay về trạng thái Factory Reset.

### 1.1.2 Hierarchical Multi-Sig Escrow — Offline Device Recovery (Phục hồi Thiết bị Ngoại tuyến)

> **Bài toán:** Nhân viên mất thiết bị khi Zone 1 (máy chủ) đang sập và không có iCloud Keychain. Không có luồng nào ở 1.1.1 giải quyết được trường hợp này.

**Cơ chế Phục hồi Phân cấp (Hierarchical Multi-Sig Escrow):**

- ☁️ **Hierarchical Multi-Sig Escrow:** Hệ thống thay thế chia sẻ ngang hàng bằng `Enterprise_Escrow_Key`. Khóa này sinh ra từ lúc KMS Bootstrap, bị chia nhỏ bằng thuật toán Shamir's Secret Sharing (m-of-n) và phân phát vào Secure Enclave của các thiết bị có Role: Admin và Role: HR.
- 📱💻🖥️ **Threshold Cryptography (m-of-n):** Để khôi phục tài khoản cho nhân viên mất máy, yêu cầu tối thiểu 2/3 thiết bị quản trị quét mã QR khôi phục của nhân viên qua BLE/Wi-Fi Direct.
- 🗄️ **Tamper-Proof Escrow Log:** Mọi thao tác ghép khóa khôi phục sinh ra một Ed25519 Signature ghi đè lên Append-Only Audit Log trên server, đảm bảo Admin không thể lạm quyền khôi phục lén lút (Non-Repudiation).
- ☁️ **Fallback Admin (khi Server khả dụng trở lại):** Admin Console → User Management → `[Revoke Device_Key cũ]` + `[Re-provision]` → Lõi Rust cấp Identity mới qua SCIM 2.0.
- 📱 **Bảo vệ chống lạm dụng:** Beacon BLE SOS phải được ký bởi chứng chỉ Enterprise CA hợp lệ. Đồng nghiệp chỉ thấy yêu cầu từ người trong cùng **organizational unit (OU)**. Mỗi `user_id` chỉ được phép phát SOS **1 lần/24h** để chống replay attack.

### 1.1.3 Giao thức Giải cứu (Disaster Recovery Protocols)

- 🗄️💻 **CTAP2 Hardware Challenge:** Khi cắm YubiKey vào thiết bị mới, Lõi Rust phát sinh Challenge nội bộ. YubiKey thực thi giải mã ngay trong Secure Element. Ràng buộc cứng: Bắt buộc cấu hình FIDO2 UV = Required (Yêu cầu nhập mã PIN 6 số hoặc Sinh trắc học trực tiếp trên YubiKey) để chống kẻ gian nhặt được chìa khóa.
- ☁️💻 **Intermittent Sync Engine:** Đối với điều kiện mạng "lúc on lúc off", Lõi Rust duy trì một Delta-State CRDT Buffer. Ngay khi thiết bị mới quét được mạng (dù chỉ vài giây), nó lập tức bắn gói tin Broadcast báo hiệu "Thiết bị cũ đã bị vô hiệu hóa" và tải cục bộ danh bạ Mesh, sau đó có thể hoạt động offline hoàn toàn.
- 💻📱 **Self-Revocation & Epoch Rotation (Dành cho TH2):** Khi mất 1 thiết bị, thiết bị còn lại sẽ tự động sinh `Epoch_Key` mới, cập nhật lên Merkle Tree và ký bằng `DeviceIdentityKey`. Bất kỳ yêu cầu kết nối nào từ thiết bị đã mất đều bị mạng Mesh hoặc Server từ chối tức khắc ở tầng giao thức.

| In-Scope | Out-of-Scope |
|---|---|
| Messaging E2EE (MLS IETF RFC 9420) | Lưu plaintext trên Server |
| P2P Survival Mesh (BLE/Wi-Fi Direct) | Routing qua Public Cloud |
| WASM Sandbox cho `.tapp` | Remote Code Execution ngoài WASM |
| Blind Storage (MinIO + Erasure Coding) | Server-side search trên plaintext |
| Federation Bridge (mTLS + Sealed Sender) | Dùng CA công cộng cho Federation |

### 1.3 Core Terminology

| Thuật ngữ | Định nghĩa |
|---|---|
| `.tapp` | Gói tiện ích: `logic.wasm` + JSON Schema UI. Chạy trong WASM Sandbox trên thiết bị — không thực thi trên Server. |
| `Company_Key` | Khóa cấp Tenant, sinh khi Onboarding. Không rời thiết bị thành viên. Mã hóa mọi payload trước khi lên Cluster. |
| **Blind Relay** | Server chỉ chuyển tiếp ciphertext — không nắm key giải mã. Áp dụng cho Messaging (MLS), File (MinIO CAS), Voice (TURN). |
| **TreeKEM** | Cấu trúc cây nhị phân trong MLS, phân phối khóa nhóm O(log n). Tăng tốc sync 100× cho nhóm 5000+ user. |
| **HKMS** | Hierarchical Key Management System — Master Key → KEK → DEK. Master Key giam trong HSM/Secure Enclave. |
| **Sealed Sender** | Server biết gói tin đi đến đâu, nhưng không biết từ ai. |
| `cas_hash` | SHA-256 của ciphertext dùng cho CAS path và dedup. Server tra hash, không tra nội dung. |
| **Crypto-Shredding** | Xóa KEK thay vì xóa dữ liệu vật lý. Ciphertext còn trên disk nhưng trở thành garbage. |

---

## 2. Architectural Approach

### 2.1 Shared Core Philosophy — Lõi Rust Độc Tài

- ☁️📱💻🖥️ **Lõi Rust (TeraChat Core)** nắm giữ 100% sinh mệnh: MLS E2EE, SQLCipher I/O, P2P Mesh, CRDT Sync. Biên dịch ra native binary cho mọi platform.
- 📱💻🖥️ **Tầng UI (React Native / Flutter / Tauri):** Pure Renderer — cấm tuyệt đối port Crypto/Business Logic lên JS/Dart Thread.
- 📱💻🖥️ **IPC — Tách Control/Data Plane:**
  - *Control Plane:* Protobuf qua JSI HostObject / Dart FFI — lệnh nhỏ \<1KB.
  - *Data Plane:* `SharedArrayBuffer` (Desktop) / C++ Shared Memory via JSI (iOS) / Dart FFI TypedData (Android) — Zero-Copy, throughput ~400–500MB/s.
- 📱💻🖥️ **Unidirectional State Sync:** Rust bắn signal `StateChanged(table, version)` qua IPC. UI kéo snapshot tại thời điểm rảnh — không polling, không push JSON cục.

### 2.2 Blind Routing & Zero-Knowledge

- ☁️ Server là **Blind Relay** — chỉ thấy: `destination_device_id`, `blob_size`, `timestamp`.
- ☁️ **Sealed Sender:** Header người gửi mã hóa bằng public key người nhận — Server không biết who-to-whom.
- ☁️ **Oblivious CAS Routing:** Batch 4–10 `Fake_CAS_Hashes` khi gửi hash query (Chaffing). Tra qua Mixnet Proxy Endpoint, không đính `User_ID`.
- 🗄️☁️ **MinIO Blind Storage:** Lưu file theo `cas_hash` path — không biết tên file thực.
- ☁️ **VPS Blind Storage & Zero-Knowledge Binary Block Routing:** Các Chunk mã hóa được đẩy lên VPS. VPS hoàn toàn mù (Zero-Knowledge) về nội dung file lẫn Policy_Packet, chỉ lưu trữ dưới dạng các block nhị phân vô nghĩa và phân phối chúng đến các thành viên trong nhóm.

### 2.3 Phân rã Lõi (Dynamic Micro-Core Loading)

- 📱💻 Khai thác Dynamic Library Loading (DLL/dylib) điều phối nạp/rút các phân hệ linh động theo từng ngữ cảnh giao tiếp.
- 📱💻 Khởi động cơ chế Just-In-Time (JIT) Micro-Core nhằm đè bẹp dung lượng RAM thường trực của lõi hệ thống xuống mức tối thiểu tuyệt đối.
- 📱💻🖥️ Áp dụng Engine mã hóa hậu lượng tử Kyber768 bảo đảm tương lai an toàn trước kỷ nguyên Shor Algorithm (Thuật toán Shor).

### 2.5 Lõi Cập nhật Minh bạch & Rào chắn Sandbox (Rogue Admin & Sandboxing Defenses)

#### Xác thực Chữ ký Gốc (Root CA Binary Transparency) — Không tin Admin

- 📱💻🖥️ Mọi bản build (Native App, Rust Core, `.tapp`) đều được ký số bằng **TeraChat Root CA Key** lưu trong hầm lạnh offline của TeraChat HQ. Admin không thể tạo ra chữ ký này.
- 📱💻🖥️ Lõi Rust trên Client hard-code sẵn Public Key của TeraChat. Khi tải bản cập nhật từ VPS nội bộ, Lõi Rust **bắt buộc kiểm tra chữ ký Ed25519** trước khi thực thi. Sửa 1 bit → chữ ký vỡ → Drop + Báo động đỏ.
- 📱💻🖥️ Xác minh `signature_ed25519` tận sâu tầng Lõi Rust nhằm vô hiệu hóa tức thời mọi bản cập nhật đơn phương (kể cả Admin nội bộ).

> **Phân vai rõ ràng:** FROST Quorum chỉ áp dụng cho phê duyệt tài liệu nội bộ và giải mã dữ liệu Escrow. Không dùng cho việc ký xác nhận cài đặt App.

#### Cờ Chống Hạ cấp (Anti-Rollback Monotonic Counter)

- 📱💻🖥️ Mỗi bản build đớu chứa `Version_Sequence` (số nguyên tăng đơn đặt trong header).
- 📱💻🖥️ Lõi Rust lưu `Current_Sequence` vào SQLite được mã hóa. Nếu VPS đẩy xuống bản build có `Sequence < Current_Sequence` → Drop tức thì, chống hạ cấp (Downgrade Attack).

#### Global CVE Heartbeat qua DNS TXT Records (Out-of-Band Revocation)

- 📱💻🖥️ Tra cứu bản ghi DNS TXT Out-of-Band định kỳ mỗi 24h trỏ về `security.terachat.com` — vô hình trước các tường lửa HTTP/TCP truyền thống.
- 📱💻🖥️ Sử dụng **DNS-over-HTTPS (DoH)** qua Cloudflare/Google để xuyên thủng DPI Firewall nội bộ, chống chặn DNS.
- 📱💻🖥️ Xác thực chữ ký điện tử **Ed25519** từ TeraChat Global CA trước khi nạp `Version_Sequence_Blacklist` — chống DNS Spoofing và DNS Hijacking.

#### Atomic IPC Security Lock & RSOD (Cơ chế Khóa Ứng dụng khẩn cấp)

- 📱💻🖥️ Sử dụng cờ **Atomic** (`ATOMIC_SECURITY_LOCK`) để khóa toàn bộ luồng IPC Data Plane ngay khi phát hiện phiên bản bị thu hồi (CVE Blacklist match).
- 📱💻🖥️ Kích hoạt giao diện **Red Screen of Death (RSOD)** thông qua luồng tín hiệu từ Lõi Rust lên UI (React Native/Tauri) — người dùng không thể đóng hộp thoại này.
- 📱💻🖥️ Thực thi giao thức **Zeroize RAM** tiêu hủy tức khắc khóa Root và tàn dư vùng nhớ nhạy cảm khi nhận lệnh khóa.

#### Phân rã Kênh Cập nhật (Dual-Track OTA Distribution)

- 📱 **Mobile (Signal-Only Update):** VPS chỉ phát cờ lệnh `"V0.3.0 là bắt buộc"`. App iOS/Android nhận lệnh → Khóa UI → Hiển thị nút *"Đến App Store / CH Play để cập nhật"*. quá trình tải app vẫn phải đi qua server Apple/Google. VPS không chứa `.ipa/.apk`.
- 💻🖥️ **Desktop (LAN P2P Update và Tauri Updater):** VPS chỉ "mồi" bản cập nhật cho 10 máy Super Nodes. Sau đó, các máy Desktop tự dùng **LAN P2P (Survival Mesh)** phân phối Binary cho các máy còn lại, giải phóng 99% tải băng thông của VPS, tránh bão mạng LAN.

#### Tấn công Cập nhật Mục tiêu lén lút (Distributed Binary Transparency - DBT)

- 📱💻🖥️ Ấn định sổ cái bất biến Global_Update_Log đổ khuôn trên kiến trúc cốt lõi Append-Only CRDT Log.
- 📱💻 Đồng bộ mã băm (Hash) xuyên suốt mọi bản cập nhật JMM qua giao thức Gossip lan truyền trên toàn tuyến mạng Mesh.
- 📱💻 Khóa chặt cờ No-Exception Rule buộc Lõi Rust đối soát đối xứng Hash của JMM với sổ cái chung trước thời khắc nạp module.

#### Thực thi Mã độc trong Module Mật mã (WASM Capability-Based Sandboxing)

> ⚠️ **Kiến trúc WASM Runtime Kép (Dual-Engine WASM):** iOS áp đặt chính sách `W^X` (Write XOR Execute) nghiêm cấm JIT Runtime. Lõi Rust PHẢI tự động phát hiện Platform và chọn Engine phù hợp.

- 📱 **iOS (W^X-Compliant):** Tuyệt đối **không dùng `wasmtime` JIT**. Hai lựa chọn được chấp thuận:
  - **AOT (Ahead-of-Time):** File `.wasm` được biên dịch thành `.dylib` tĩnh tại CI/CD Pipeline, phân phối cùng App Bundle. Không sinh JIT page ở runtime.
  - **Interpreter `wasm3`** (~10KB binary, zero `malloc` JIT page): Dùng khi cần load `.tapp` động. Latency tăng ~15-20ms/lần gọi — chi phí chấp nhận được, đổi lại **Reliability 100%** và tuân thủ App Store Guidelines.
  - Điều kiện switch: `#[cfg(target_os = "ios")]` tại compile-time.
- 📱 **Android, 💻🖥️ Desktop/Server:** Tiếp tục dùng `wasmtime` (JIT/Cranelift) để tối đa Throughput.
- 📱💻🖥️ Mọi Engine đều chạy ở chế độ Deny-by-Default, nghẹt con trỏ (Pointer) chứa `Company_Key` truyền ngược vào module.
- 📱💻🖥️ Tước bỏ triệt để Network Socket Capabilities phong ấn hoàn toàn kẽ hở dữ liệu rò rỉ ra cầu nối Internet mở.
- 📱💻🖥️ Kích nổ cơ chế Blind Return kèm Zeroize tiêu hủy tàn dư vùng nhớ RAM của WASM ngay tắp lự sau vạch kết thúc thực thi.

#### AST Opcode Filtering & Fixed-point Arithmetic Enforcement (Bất tất định FPU)

- 📱💻🖥️ Sử dụng thư viện `wasmparser` để phân tích tĩnh (Static Analysis) và chặn đứng các opcode `f32/f64` gây bất tất định.
- 📱💻🖥️ Cưỡng ép sử dụng toán học số nguyên (Fixed-point) hoặc Soft-float thay cho Float phần cứng ở cấp độ biên dịch.
- 📱💻🖥️ Phân loại `execution_profile` trong cấu trúc Manifest để cô lập an toàn các tác vụ `consensus_critical`.

#### Engine-level Canonical NaN Normalization (Sai lệch vi kiến trúc)

- 💻🖥️ Kích hoạt cờ `cranelift_nan_canonicalization` trong Wasmtime để chuẩn hóa mọi bit pattern của biến thể NaN hiểm hóc.
- 📱💻🖥️ Vô hiệu hóa `relaxed_simd` và phần cứng SIMD để nhổ bỏ tận rễ các phép toán phụ thuộc vi kiến trúc vật lý.
- 📱 Thực thi `js-flags` (`--no-wasm-simd`) qua JSI để đồng bộ cứng hành vi runtime chuẩn xác trên nền tảng Mobile.

#### Dictator Choke-Point via Host-Binding Proxy (Sandbox Network Escape)

- 📱💻🖥️ Tước đoạt hoàn toàn năng lực `wasi-sockets` của WASM Runtime để phong tỏa khả năng Direct Socket Access.
- 📱💻🖥️ Chuyển hướng mọi yêu cầu mạng qua Polyfilled `fetch()` và cấu trúc IPC Protobuf `EgressNetworkRequest`.
- 📱💻 Thiết lập Lõi Rust (Data Plane) đóng vai trò Forward Proxy duy nhất để kiểm soát luồng TLS vật lý.

#### Custom DNS-over-HTTPS (DoH) & Bogon Filtering (DNS Rebinding)

- 📱💻🖥️ Rust Core tự phân giải DNS qua giao thức DoH trỏ về Enterprise DNS nhằm bypass bộ đệm hệ điều hành.
- 📱💻🖥️ Áp dụng thuật toán Bogon Space Validation đối chiếu IP trả về với dải `127.0.0.0/8`, `10.0.0.0/8` ngăn chặn SSRF xâm nhập nội bộ.
- 📱💻🖥️ Kích hoạt kỹ thuật IP Pinning cố định địa chỉ đích ngay tại tầng Socket để triệt tiêu chiến thuật đổi IP giữa chừng.

#### Air-Gapped Linear Memory Isolation & W^X Strict Compliance

- 📱💻🖥️ Áp dụng cơ chế **Software-defined Memory Isolation**: Sử dụng RAII `zeroize::ZeroizeOnDrop` để tiêu hủy tuyệt đối plaintext khỏi heap/stack ngay khi struct trượt khỏi scope, ngăn chặn Memory Dump hiệu quả mà không cần `mlock()`.
- 📱💻🖥️ Kích hoạt Rào chắn cấu trúc nhị phân (Executable & Memory Layout): Phân bổ vùng RAM tĩnh tuân thủ triệt để nguyên lý W^X (Write XOR Execute) của CPU C-Level: Vùng nhớ dành cho E2EE Decryption Buffer không bao giờ khả thi chạy code (`PROT_READ | PROT_WRITE`), và vùng chứa logic Rust Executable không bao giờ cho phép ghi chèn (`PROT_READ | PROT_EXEC`). Chống lại 100% các cuộc tấn công tiêm mã nhị phân cơ bản (Buffer Overflow / Return-Oriented Programming).
- 📱 Tách biệt Address Space Randomization (KASLR/ASLR): Bố trí Layout con trỏ JSI tách rời hoàn toàn khỏi Cây thư mục cấp phát động của WebKit/V8. App có bị xâm nhập RCE trên lớp JS thì pointer chọc xuống Rust Box vẫn sẽ chạm SEGFAULT (Segmentation Fault) và sụp đổ chủ động.

#### OPA-driven IPC Bridge & Manifest Control (Kiểm soát I/O trái phép)

- 📱💻🖥️ Sử dụng giao thức IPC Protobuf qua SharedArrayBuffer làm cầu nối giao tiếp duy nhất cho mọi hành vi I/O (Network, File System, Database).
- ☁️📱💻🖥️ Tích hợp OPA Engine (Open Policy Agent) tại Lõi Rust để đối chiếu quyền hạn khai báo trong Manifest của `.tapp` với quyền hiện tại của User.
- 💻🖥️ Trả dữ liệu Plaintext ngược vào RAM của WASM mà tuyệt đối không cấp quyền truy cập trực tiếp vào File Handle gốc của OS.

#### Blind Cryptography & KDF Storage Sandboxing (Mã hóa Lưu trữ Ẩn danh)

- 📱💻🖥️ Dẫn xuất khóa phụ `Tapp_Sandbox_Key` từ khóa gốc `Device_Key` thông qua thuật toán KDF (Key Derivation Function) tại Lõi Rust.
- 📱💻🖥️ Mã hóa AES-256-GCM toàn bộ payload JSON và lưu xuống SQLite WAL bảo đảm tiện ích hoàn toàn "mù" về khóa mã hóa.
- 📱💻 Tự động giải mã và bơm Plaintext trả lại Sandbox khi tiện ích gọi API đọc dữ liệu hợp lệ.

#### Host-Binding Network Deprivation & Strict E2EE Routing (Chống tuồn dữ liệu ra mạng ngoài)

- 📱💻🖥️ Chặn (Block) toàn bộ khả năng truy cập API mạng tự do (như HTTP Socket/TCP Socket) từ bên trong WASM Sandbox.
- 📱💻🖥️ Ép buộc mọi luồng đồng bộ dữ liệu phải đi qua Data Plane của TeraChat dưới dạng payload E2EE.
- ☁️📱💻🖥️ Bọc gói tin trong giao thức Federation mTLS để kiểm soát và đảm bảo đích đến luôn là máy chủ nội bộ được cấp phép.

### 2.6 Lõi Mật mã Kháng Kênh kề (Hardware-Level Cryptography Defenses)

#### Kiến trúc Lai Kép (Hybrid PQ-KEM) với ML-KEM-768 (Tấn công Store Now, Decrypt Later (SNDL) và Đe dọa Lượng tử)

- 📱💻🖥️☁️🗄️ Kết hợp song song mật mã học cổ điển `X25519` và mật mã học kháng lượng tử `ML-KEM` (Kyber768) để đảm bảo an toàn kể cả khi một trong hai thuật toán bị bẻ gãy.
- 📱💻🖥️☁️🗄️ Hàm dẫn xuất khóa $Final\_Session\_Key = HKDF(X25519\_Shared \parallel Kyber768\_Shared)$ tuân thủ tiêu chuẩn CNSA 2.0.
- ☁️ Triển khai cấu trúc cây nhị phân MLS (TreeKEM) để phân phối khóa nhóm kháng lượng tử với độ phức tạp $O(log\ n)$.

#### Quantum Checkpoints & Symmetric Ratcheting (Quá tải Băng thông và Pin trên thiết bị di động)

- 📱 Sử dụng cơ chế "Quantum Checkpoints": Chỉ đính kèm PQ-KEM payload (~1.18KB) vào các pha Handshake hoặc định kỳ sau mỗi 10.000 tin nhắn để tiết kiệm 99.9% băng thông.
- 📱💻🖥️ Luồng dữ liệu hàng ngày sử dụng mật mã đối xứng AES-256-GCM, vốn có khả năng kháng lượng tử tự nhiên trước thuật toán Grover (duy trì độ bảo mật tương đương 128-bit).
- 📱💻 Phân đoạn gói tin (Fragmentation) cho mạng Mesh offline để xử lý giới hạn MTU 512 bytes của BLE 5.0 khi truyền tải khóa lượng tử cồng kềnh.

#### Hardware-Backed Key Wrapping (Lồng khóa mật mã cho PQC)

- 📱💻🖥️ Sinh cặp khóa PQ trên phân vùng RAM được bảo vệ bởi `MAP_CONCEAL` để ngăn chặn rò rỉ vào file Swap.
- 📱 Sử dụng cơ chế "Lồng khóa": Mã hóa Private Key của ML-KEM bằng khóa đối xứng `Hardware_Wrap_Key` được neo giữ trong chip vật lý (Secure Enclave/StrongBox).
- 📱💻🖥️ Áp dụng `ZeroizeOnDrop` (RAII) để ghi đè $0x00$ lên bản rõ của khóa trong RAM ngay sau khi thực hiện xong tính toán KEM.

#### Pre-fetched PQ Roster (Đồng bộ danh bạ khóa trước cho PQC Mesh)

- 📱💻 Tải trước và lưu trữ `KeyPackage` (X25519 + ML-KEM-768) vào SQLite cục bộ thông qua WAL mode khi có kết nối Internet.
- 📱💻 Xây dựng cơ chế truy vấn tối giản qua `Key_Hash` (16 bytes) để kích hoạt Hybrid Handshake mà không hao tốn băng thông truyền khóa qua rào cản BLE.
- 📱💻 Giao thức Zero-Knowledge Key Management đảm bảo khóa Private tuyệt đối không bao giờ rời khỏi vùng an toàn Hardware Root of Trust.

#### Lazy Quantum Ratchet (Nâng cấp lượng tử trì hoãn trong Mesh)

- 📱 Tận dụng X25519 Fast Handshake (<100 bytes) cho phép thiết lập kênh E2EE cổ điển ngay trong 1 gói tin BLE duy nhất để chớp thời cơ kết nối khẩn cấp (SOS).
- 📱 Kích hoạt cơ chế MLS Epoch Rotation để hòa trộn ML-KEM-768 Secret vào Master Secret ngay sau khi hoàn tất tải dữ liệu ngầm.
- 📱 Tận dụng Worker nền của Lõi Rust để tối ưu hóa quá trình đồng bộ khóa PQC mà không phong tỏa luồng tác vụ SOS khẩn cấp.

#### RaptorQ (Fountain Codes) Forward Error Correction (Tin cậy dữ liệu Mesh P2P)

- 📱💻🖥️ Triển khai thuật toán RaptorQ (RFC 6330) tại tầng Rust Data Plane để mã hóa khóa PQC 1.2KB thành các "giọt" dữ liệu đa chiều.
- 📱💻🖥️ Phân mảnh dữ liệu thành các khối 200 bytes để lách qua rào cản vật lý MTU của BLE 5.0 và tránh nút thắt nghẽn mạng cục bộ.
- 📱💻🖥️ Dựng cơ chế loại bỏ ACK/NACK truyền thống giúp triệt tiêu hoàn toàn hiện tượng "Bão Broadcast" cộng hưởng trong cấu trúc mạng Mesh multi-hop.

#### Tấn công Kênh kề Thời gian (Timing Attack)

- 📱💻🖥️ Áp đặt kiến trúc **Constant-time Logic Enforcement** qua thư viện `subtle` của Rust, triệt tiêu toàn bộ lệnh rẽ nhánh `if/else` nhạy cảm dữ liệu.
- 📱💻🖥️ Thi hành kỹ thuật **Bit-masking** (AND, OR, XOR, NOT) buộc mọi phép tính mật mã tiêu tốn cùng một số chu kỳ xung nhịp CPU bất kể bit khóa là 0 hay 1.

#### Phân tích Hành vi theo Lưu lượng (Traffic Pattern Analysis)

- 📱💻🖥️ Kích hoạt **Fixed-size Padding** đắp dữ liệu rác để mọi TCP/UDP payload xuất xưởng đạt mức cố định (ví dụ: 4096 Bytes), che giấu chủng loại tệp.
- 📱💻🖥️ Duy trì nhịp **Heartbeat Dummy Traffic** bắt buộc để bảo toàn lưu lượng mạng đồng nhất không đứt gãy dù mạng lưới đang thả nổi (Idle) hay quá tải luồng Chat.
- ☁️📱💻🖥️ Pha trộn **Oblivious CAS Routing** và trạm Batch Requests (<1KB) làm mù lộ trình dữ liệu qua cụm Mixnet Proxy.

#### Rò rỉ Dữ liệu qua Tầng Phần mềm (Software Leakage)

- 📱💻🖥️ Cưỡng ép **Hardware-Accelerated Primitive Hardening** ưu tiên đẩy luồng tính toán thẳng tới tập lệnh **AES-NI** (Intel/AMD) hoặc **ARM NEON** nguyên khối trong tinh thể bán dẫn.
- 📱💻🖥️ Trưng dụng Hardware Root of Trust (**Secure Enclave/TPM 2.0**) chuyên trách giải nén và phong ấn khóa E2EE, không rò rỉ tín hiệu vỡ trên tầng RAM.
- 📱💻 Tối ưu hóa hiệu năng giải ma trận kháng lượng tử Kyber768 thông qua gia tốc NPU hoặc Crypto Engine chuyên dụng trên SoC di động.

#### Side-Channel Mitigation via Timer Degradation & Thread Limiting

- 📱💻🖥️ Làm mờ đồng hồ hệ thống (Timer Degradation) xuống 5-10ms kết hợp nhiễu Jitter để phá bỏ phép đo độ trễ RAM.
- 📱💻🖥️ Giới hạn luồng (Thread Concurrency) và vô hiệu hóa `Atomics.wait` nếu không khai báo trong Permission Manifest.
- 📱💻🖥️ Ràng buộc cơ chế Host-Binding kiểm duyệt nghiêm ngặt mọi lệnh gọi ra từ Sandbox.

#### OPA-driven IPC Compartmentalization (Phân rã dữ liệu qua OPA)

- 📱💻🖥️ Áp dụng IPC Authentication sử dụng `Tapp_Token` định danh duy nhất cho mỗi instance sandbox.
- 📱💻🖥️ OPA Policy Engine thực thi luật Namespace để ngăn chặn .tapp truy cập bảng dữ liệu không thuộc thẩm quyền.
- 📱💻🖥️ Giới hạn Byte-Quota tại Edge và Sandbox IPC để chống thất thoát dữ liệu hàng loạt (Bulk Exfiltration).

---

## 3. Infrastructure & Control Plane

### 3.1 Deployment Topologies

```text
[Global Edge / GeoDNS Routing]
         │
         ├──> [Zone 1: Enterprise Relay Cluster — Dedicated VPS]
         │      ├─ Double-O-Relay (Rust Control Plane)
         │      ├─ SQLite WAL Storage (Local SSD)
         │      └─ PostgreSQL (Metadata only)
         ├──> [Zone 2: Federation Bridge]
         │      ├─ mTLS Mutual Auth (không dùng CA công cộng)
         │      ├─ Sealed Sender Protocol
         │      └─ Cluster A ↔ Cluster B giao tiếp an toàn
         └──> [Zone 1B: VPS Cluster — Vultr / DigitalOcean / Linode]
                ├─ Single-Binary Rust Daemon (Relay)
                ├─ Local SSD Storage
                └─ HA TURN Array (WebRTC Relay, Floating IP)
```

### 3.5 Lightweight Micro-Core Relay

- ☁️ **Single-Binary Rust Daemon:** Binary được tối ưu hoá cực hạn (`opt-level='z'`, `panic='abort'`, Link-Time Optimization) để hoạt động ổn định trên Share-Hosting VPS chỉ từ 512MB RAM.
- ☁️ **Tokio Async Userspace Filter:** Thay thế toàn bộ Kernel-level eBPF bằng bộ lọc lưu lượng tại Userspace sử dụng thuật toán Token Bucket, kiểm soát Rate-limit và chống tấn công DoS mà không cần đặc quyền CAP_SYS_ADMIN.
- 📱💻☁️ **Protocol Versioning:** Sử dụng ALPN để đàm phán phiên bản giao thức linh hoạt (QUIC/gRPC/WS), đảm bảo khả năng tương thích ngược (Backward Compatibility) và nâng cấp nóng (Hot-reload) mà không gây gián đoạn kết nối.

### 3.6 Zero-Access Diagnostics (TeraDiag)

- 📱 **WASM Sandbox (ReadOnly Partition):** TeraDiag vận hành trong một instance WASM Sandbox biệt lập, được cấp quyền `PROT_READ` tối thiểu đối với phân vùng `diag_logs` để thu thập log trạng thái mà không thể truy xuất dữ liệu tin nhắn hay Database chính.
- 📱 **XChaCha20-Poly1305 Pipeline:** Toàn bộ log chẩn đoán được mã hoá stream-based qua pipeline XChaCha20-Poly1305 trước khi đẩy vào kênh đồng bộ, đảm bảo tính toàn vẹn và bí mật tuyệt đối kể cả khi log bị thất lạc.
- 📱 **Wi-Fi Direct (Log Sync over Mesh):** Tận dụng giao thức Wi-Fi Direct để thiết lập kết nối P2P tức thời, cho phép đồng bộ Log chẩn đoán giữa các thiết bị trong mạng Mesh khi mất kết nối Internet, hỗ trợ kỹ thuật viên ứng cứu sự cố tại chỗ.

| Quy mô | Topology | Storage |
|---|---|
| 10k Users | Single-Node Rust Relay (Small VPS) | Local SSD |
| 100k Users | Geo-Federated Clusters (Dedicated VPS) | PostgreSQL Geo-Partitioning + HA TURN Array |
| 1M+ Users | Multi-Cloud Active-Active (Federation Bridge) | Data Mule + NTN Satellite routing |

### 3.2 Backend Services

#### Gateway & Identity Broker

- ☁️ **API Gateway:** Rate Limiting (Sliding Window Log — Redis ZSET), OPA Policy trên mọi request.
- ☁️ **Identity Broker (Keycloak/Dex):** Cầu nối OIDC/SAML — Azure AD / Google Workspace / Okta / OneLogin.
- ☁️ **Enterprise CA (PKI nội bộ):** Chỉ tin tưởng Key ký bởi CA nội bộ. Không CA công cộng.
- ☁️ **SCIM Listener:** Lắng nghe sự kiện SCIM 2.0 — tự động offboarding nhân viên.

#### OPA/ABAC Policy Engine

- ☁️ Mọi request đi qua **OPA (Open Policy Agent)** — kiểm tra tại API Gateway.
- ☁️ **GeoHash Indexing:** Tọa độ → GeoHash prefix string. OPA so sánh String thay vì Haversine — O(1) lookup.
- ☁️ **Formal Verification:** OPA Policy → SMT Model → **Z3 Solver** → Block Deploy nếu có kẽ hở.

#### OPA-Driven UI State Enforcement (Launchpad Access Control)

- 📱💻🖥️ Rút trích quyền truy cập UI thông qua OPA Policy Engine vận hành trực tiếp tại lõi Core.
- 📱💻🖥️ Áp dụng cơ chế Manifest-driven Permission Model nhằm rà soát và giới hạn quyền hạn của Launchpad plugin ngay trước quá trình thực thi.
- 📱💻🖥️ Đảm bảo WASM Sandbox Runtime Isolation để ngăn cấm quá trình vượt quyền của bất kì plugin nào tích hợp vào mạng lưới UI.

#### ZKP-based Attribute Routing & VOPRF Token

- ☁️ Áp dụng Zero-Knowledge Proofs (zk-SNARKs) để OPA xác thực Policy mà không cần giải mã danh tính.
- ☁️📱💻🖥️ Thiết lập hệ thống VOPRF (Verifiable Oblivious Pseudorandom Function) sinh Blind Tokens nhằm cấp quyền Rate Limit ẩn danh.
- ☁️ Triển khai Homomorphic Encryption (Mã hóa đồng cấu) để đánh giá metadata định tuyến trực tiếp trên ciphertext.

#### Cluster 4-trong-1

| Component | Chức năng |
|---|---|
| **MLS Backbone** | Phân phối khóa & định tuyến nhóm 5000+. Encrypted Log Streams (Zero-Knowledge). |
| **HA TURN Cluster** | Floating IP, failover 3s. WebRTC Relay HD/Video Conference. |
| **Execution Environment** | VPS Egress Proxy backend — dữ liệu chỉ trên RAM, không persist. |
| **Interop Hub** | Gateway E2EE hóa dữ liệu SAP/Jira/CRM trước khi đẩy xuống Client. |

#### Xử lý Đồng thời Lớn (Concurrency) trên Server

- ☁️🗄️ **Asynchronous Rust + io_uring:** Loại bỏ hoàn toàn mô hình "1 Thread / 1 Connection" cũ kỹ trên hệ thống VPS. Kích hoạt Runtime Tokio kết hợp API io_uring của Linux kernel để tối ưu I/O.
- ☁️🗄️ **Siêu Đồng thời Siêu nhẹ:** Mỗi kết nối WebSocket mã hóa từ Client chỉ chiếm khoảng ~2KB RAM hờ. Máy chủ chỉ giải quyết việc nhận mảng byte mã hóa (Ciphertext) và định tuyến nó qua hàng đợi Pub/Sub (Redis hoặc NATS JetStream), cho phép một VPS 4GB RAM gánh ~500.000 kết nối đồng thời.

#### Blind Relay Egress Gateway (Mode E2)

- ☁️🗄️ Cấu trúc Egress Proxy (Mode E2) luân chuyển dữ liệu qua Ephemeral Pipe trong không gian RAM máy chủ.
- 📱💻 Mã hóa E2EE gói tin Egress bằng khóa `Server_Egress_Key` trước khi rời thiết bị hạn chế Device IP Exposure.
- ☁️ Đặt Exit Nodes tại vùng phi quân sự (DMZ) của VPS Cluster để che giấu hoàn toàn danh tính người dùng cuối khỏi Internet.

#### Hierarchical QoS & Multi-Runtime Isolation (Ngăn chặn Cạn kiệt Tài nguyên)

- ☁️ Phân tách luồng xử lý độc lập thành `core-messaging-runtime` (ưu tiên cao) và `heavy-io-runtime` (trọng tải `.tapp`) thông qua cấu trúc Bounded MPSC Channels.
- 📱💻🖥️ Áp đặt OPA Policy Engine quản trị Byte-Quota và Rate Limiting nghiêm ngặt đối với từng tiến trình chạy ngầm của tiện ích.
- ☁️ Tự động kích hoạt trạng thái "Suspend" (Circuit Breaker) cho các ứng dụng vi phạm Latency >1500ms hoặc ngưỡng CPU Spike >30%.

#### 3.4.2 Xử lý OOM-Kill do SQLite WAL Hydration (VPS Resource Constraints)

> **Bài toán:** Trên các VPS giới hạn tài nguyên, việc nạp (Hydration) dữ liệu từ SQLite WAL có thể gây ra hiện tượng tràn bộ nhớ (OOM-Kill).

- ☁️ **Micro-batching DB Lock Yielding:** Chia nhỏ quá trình ghi (Commit) WAL thành các batch cực nhỏ. Lõi Rust tự động nhường (Yield) khóa Database sau mỗi 1000 hàng để tránh treo hệ thống I/O.
- ☁️ **Zero-Copy Atomic Rename:** Sử dụng hàm `renameat2()` của Linux với cờ `RENAME_WHITEOUT` (hoặc tương đương POSIX) để tráo đổi tệp vfs-journal mà không cần sao chép dữ liệu qua User-space, giảm 90% áp lực RAM khi xoay vòng WAL.
- ☁️ **SQLite WAL Autocheckpoint:** Cưỡng chế `wal_autocheckpoint=1000` để giữ kích thước file WAL luôn ở ngưỡng kiểm soát được.

### 3.5 Lightweight Micro-Core Relay

> **Giải pháp:** Sử dụng relay siêu nhẹ chạy trực tiếp trên VPS phổ thông, loại bỏ các thành phần phức tạp không cần thiết.

- ☁️ **Single-Binary Rust Daemon:** Đóng gói toàn bộ Control Plane của relay vào một tệp nhị phân Rust duy nhất (tối ưu `opt-level='z'` và `O-LLVM`).
- ☁️ **Tokio Async Userspace Filter:** Sử dụng bộ lọc mạng chạy hoàn toàn tại không gian người dùng (Userspace) dựa trên Tokio Async. Áp dụng thuật toán **Token Bucket** để kiểm soát tốc độ (Rate Limiting) theo từng phòng ban.
- 📱 💻 ☁️ **Protocol Versioning:** Đàm phán giao thức linh hoạt (Graceful ALPN) giữa QUIC, gRPC và WebSocket, cho phép các thiết bị cũ và mới giao tiếp xuyên suốt qua relay.

#### Khởi tạo Zero-Knowledge (Bootstrap)

- 💻🖥️🗄️ Admin cấu hình **Static IP/DNS** của Master Node thông qua file `config.yaml` tại thời điểm triển khai On-Premise. Không phụ thuộc vào Cloud Provider Metadata API.
- ☁️ Kết hợp **Gossip-based Discovery** (Memberlist) để Worker động tìm nún Cluster WireGuard LAN ảo sau khi Bootstrap thành công.
- ☁️ Thỏa thuận trao đổi **Pre-shared Key (PSK)** phân mảnh qua `inventory.ini` thiết lập đường hầm xác thực nguyên thủy.

#### (Section Deprecated: Hardware-Attested mTLS, Remote Attestation (DCAP), and eBPF Kernel Filters removed to ensure VPS compatibility)

#### Enclave-Bound Master Key (Hardware Pinning)

- 📱💻🖥️ Master Key (`.terakey`) được sinh ra và gói gọn (wrapped) trực tiếp bên trong không gian Secure Enclave/StrongBox, tuyệt đối không bao giờ được phép export sang filesystem hay RAM của OS.
- 📱 Yêu cầu **User Presence** (Biometric/PIN) mỗi khi cần ký giải mã Bootstrap Token, vô hiệu hóa việc sử dụng khóa tự động kể cả khi thiết bị đã được mở khóa.
- 📱💻 Định danh chéo thiết bị thông qua Hardware-ID Binding để ràng buộc Master Key chỉ có hiệu lực duy nhất trên phần cứng thiết bị Admin chỉ định.
- 📱💻🖥️ Kích hoạt lính canh **Zeroize RAM** tiêu hủy tức khắc khóa Root trên vùng nhớ động vừa nạp ngay khoảnh khắc chuyển giao vĩnh viễn vào **Secure Enclave/TPM 2.0**.
- ☁️🗄️ Khởi tạo môi trường MinIO Provisioning đính kèm cơ chế Server-Side Encryption (SSE-KMS) sử dụng vỏ bọc bao ngoài xẻ từ `Company_Key`.
- ☁️🗄️ Quản lý Server ở trạng thái giữ "chìa khóa đã bị khóa", ép buộc thao tác mở khóa dịch vụ phải nhận tín hiệu chứng thực E2EE trực tiếp từ thiết bị cầm tay.

- 📱💻🖥️ **Rust Local Micro-NER & Dynamic Vaulting (Bảo mật Dữ liệu AI Khách):** Triển khai bộ máy Regex kết hợp thuật toán Micro-NER tĩnh (<1MB) tại Lõi Rust để bóc tách dữ liệu định danh (PII/PCI/PHI) trước khi rời thiết bị. Khởi tạo Bảng ánh xạ tạm thời trên RAM bảo vệ bằng `ZeroizeOnDrop` để quản lý phiên xử lý cục bộ; áp dụng Tokenization Động thay thế Plaintext thành các Token ngữ nghĩa (vd: `[TOKEN_ACCOUNT_01]`) nhằm bảo toàn cấu trúc câu cho AI.
- ☁️🗄️ **Software-Based Isolation Sandbox (Chống Rò rỉ Weights/KV Cache):** Cô lập tiến trình xử lý Masked Prompt bên trong Rust-Wasm Sandbox. Ép buộc SLM/LLM xử lý suy luận mù (Blind Inference) hoàn toàn trên Token đại diện, ngăn chặn tuyệt đối việc nạp dữ liệu doanh nghiệp vào Weights hoặc KV Cache.
- 📱💻🖥️ **Prompt Rehydration & RAII Zeroization (Phục hồi ngữ cảnh an toàn):** Thực thi De-tokenization đối chiếu kết quả trả về từ Sandbox với Hash Map cục bộ để lấp Plaintext vào đúng vị trí Token. Kích hoạt vòng đời `Drop()` của Rust kết hợp `ZeroizeOnDrop` ghi đè toàn bộ vùng nhớ chứa Session Vault và Bảng ánh xạ bằng các byte `0x00` để triệt tiêu vĩnh viễn dấu vết Plaintext trên RAM ngay khi trả kết quả về UI Native.

- 🖥️ Thiết lập gông cùm **Atomic Security State Validation** tự động đối chiếu PCR State (nếu có) và vô hiệu phiên (Session Invalidation) chặn đứng mọi mưu đồ Snapshot/Cloning ảo hóa vật lý.
- 🖥️ Trực chiến lính gác **Micro-architectural Drift Watchdog** nạp luồng Rust RT-priority theo dõi độ trễ `rdtsc` Sampling, giáng đòn `ZeroizeOnDrop` quét sạch nội hàm RAM nếu vi kiến trúc bộc lộ dấu hiệu Hypervisor Pause.
- 🖥️ Nhồi nhịp đập mã hóa **Remote Attestation Heartbeat** gộp chữ ký AIK (Attestation Identity Key) và Hardware Quote độc bản.
- 📱💻🖥️ Liên đới giao thức **"Poison Pill" Mesh Revocation** trên mạng lưới Survival Mesh gạch bỏ vĩnh viễn danh tính bất đồng bộ, đập tan âm mưu Offline Brute-force/VPS Cloning.
- 🖥️ Thiết lập vành đai **Anti-Snapshot Deployment Hardening** trói cứng luồng xử lý qua CPU Hard-pinning (Core isolation) và áp đặt vòng đời KMS Key_TTL tự xoay mỗi 10 phút.
- ☁️ Đính kèm cơ chế **Blind Wipe** gắn nhãn metadata ảo cho MinIO và kích hoạt quy trình SharedArrayBuffer Immediate Zeroing xóa trắng thung lũng bộ nhớ cấu hình tại mỗi hồi nhịp Tự hủy (Self-destruct) `🖥️`.

### 3.4 Database Layer

#### PostgreSQL HA

- ☁️🗄️ pgRepmgr + PgPool — Failover tự động, streaming replication.
- ☁️🗄️ Geo-Partitioning cho quy mô 100k+ user.

#### MinIO Blind Storage

- ☁️🗄️ **Erasure Coding (EC+4):** Sharding 3–5 Nodes. 1 Node sập → tự phục hồi.
- ☁️ Lưu file theo `cas_hash` path (CAS). Server không biết tên file thực.
- ☁️ **Zero-Byte Stub:** Client nhận Stub \<5KB (`file_name`, `cas_hash`, `encrypted_thumbnail`, `storage_ref`). File thực tải khi user yêu cầu.

---

## 4. Security & Cryptography Engine

### 4.1 Key Management System (HKMS)

```text
[Master Key]  — HSM / TPM / Secure Enclave (không rời chip)
      └──> [KEK]  — giải mã trong RAM, ZeroizeOnDrop protected
                └──> [DEK]  — mã hóa nội dung thực tế
                          └──> [DB / File / Channel / API Key]
```

| Thiết bị | Nơi lưu Private Key | Cơ chế |
|---|---|---|
| 📱 iOS | Secure Enclave | Không extract. Ký/Giải mã yêu cầu biometric. |
| 📱 Android | StrongBox Keymaster (HAL) | Key sinh trong chip, không export. |
| 💻🖥️ Desktop | TPM 2.0 (NCrypt / macOS SEP) | Key binding với device. |
| 🗄️ Server | HSM Software (PKCS#11) | CA / Cluster signing key. |

#### KMS Bootstrap

- ☁️🗄️ Khởi tạo Workspace → App sinh `terachat_master_<domain>.terakey` (Master Key bọc AES-256 bằng Admin password).
- Lõi Rust **Block** tạo Database cho đến khi Admin lưu hoặc in file Key Backup.

#### Dead Man Switch

- 📱💻🖥️ Monotonic Hardware Counter (iOS Secure Enclave / Android StrongBox) — chống Time Travel Attack.
- Mỗi unlock DB → Counter++. Server lưu "Last Valid Counter". `Counter < Server's Value` → từ chối + Self-Destruct.
- **Offline Grace:** Tối đa 72h offline, sau đó bắt buộc verify online.

#### Remote Wipe

- 📱💻🖥️ `self.userID` trong `removedMembers` → xóa Private Key trong SE → Drop bảng chat → Quét xóa Sandbox files. Thực thi trong `autoreleasepool` (iOS) / `try-finally` (Android) — không thể bị User chặn.

### 4.2 Message Layer Security (MLS — IETF RFC 9420)

#### Kiến trúc Hạ cấp tại Nguồn (Sender Downgrade Mode) chống Xung đột phiên bản

- 📱💻🖥️ Tích hợp Extension `TeraChat_App_Version` vào gói `KeyPackage` của giao thức MLS để đàm phán năng lực khả dụng giữa các thành viên.
- 📱💻🖥️ Triển khai thuật toán quét Min-Version Roster để tự động kích hoạt Chế độ Hạ cấp Serialization khi phát hiện có thiết bị cũ trong mạng lưới.
- 📱 Xây dựng cơ chế mờ hóa tính năng (UI Feature Gray-out) dựa trên siêu dữ liệu phiên bản để ngăn chặn người dùng vô tình tạo ra payload không tương thích.

- ☁️ **TreeKEM:** Mã hóa O(log n) cho nhóm 5000+ user.
- ☁️ **Self-Healing:** Epoch Rotation khi member rời — Forward Secrecy.
- ☁️ **Sealed Sender:** Server không biết người gửi.
- ☁️ **Multi-Device Queue:** N bản copy (1/device). Device ACK → xóa bản đó. TTL 14 ngày → Crypto-Shred KEK.
- ☁️ **Enterprise Escrow KEM:** Shamir's Secret Sharing — M-of-N Recovery Key cho Supervisors. Audit Log bắt buộc (HIPAA/SOC2).

#### Legal Hold & Kiểm toán Bất biến — Shamir's Secret Sharing Distributed Escrow

> **Mục đích:** Đảm bảo khả năng phục hồi E2EE message khi có yêu cầu pháp lý (Court Order, Regulatory Audit) mà không trao Master Key cho bất kỳ cá nhân đơn lẻ nào.

- 🗄️ **Shamir's Secret Sharing (M-of-N Shard Orchestration):** `Enterprise_Escrow_Key` được sinh một lần trong KMS Bootstrap, chia thành N mảnh (Shard) bằng GF(2^256) polynomial. Mỗi Shard được mã hóa với public key riêng của từng Shard Holder (C-Level, Legal, HR). Default: M=3, N=5. Không Quorum → không phục hồi.
- 📱💻 **NFC/FIDO2 Shard Authentication (YubiKey / Secure Enclave):** Shard Holder prove possession bằng FIDO2 challenge-response (YubiKey hoặc Secure Enclave). Shard chỉ được decrypt tạm thời trong RAM — không bao giờ persisted sang disk.
- 🗄️ **Rust Lagrange Interpolator (Secure Arena):** Khi đủ M Shard được submit, Lõi Rust chạy nội suy Lagrange trực tiếp trong vùng nhớ Userspace. Phép tính nội suy diễn ra hoàn toàn trong Secure Arena — plaintext `Escrow_Key` chỉ tồn tại trong RAM < 100ms.
- 📱💻 **Ed25519 Signed Recovery Audit Trail:** Mỗi Recovery Event được ký `Ed25519(Device_Key, {event_id, shard_holder_ids, timestamp, target_message_hashes})` và ghi vào append-only CRDT log. Court Order reference number bắt buộc được ghi vào field `legal_basis`. Không thể xóa.
- ☁️ **Distributed Shard Storage (No Single Point):** Shards không được lưu tập trung trên 1 server. Mỗi Shard holder tự giữ Shard của mình trong Secure Enclave / YubiKey cá nhân — TeraChat server chỉ lưu encrypted Shards thứ cấp với TTL, xóa sau 90 ngày không được đọc.

- 🗄️ **CPU Registers Ephemeral Key Storage:** Các chìa khóa tạm thời (Ephemeral Key) chỉ được phép nạp trực tiếp vào các thanh ghi CPU (Register-level) mà không cấp phát xuống RAM, miễn nhiễm hoàn toàn với các cuộc tấn công khai thác DMA (Direct Memory Access) hay nhổ RAM vật lý.
- 💻📱 **Inline RAM Scrambling (ChaCha8 Keystream XOR):** Chống lại Trích xuất RAM lạnh (Cold Boot Attack) bằng thiết kế Software-defined RAM Scrambling. Bất kỳ Plaintext nào tồn tại quá 1ms trong mảng nhớ cấp phát sẽ bị mã hóa tức thời (XORed) bằng một dòng chảy ngẫu nhiên (Keystream) ChaCha8. Điều này làm cho kẻ tấn công dù có đóng băng RAM và can thiệp bằng Nitơ lỏng cũng chỉ thu thập được đống dữ liệu rác vô nghĩa.

#### 4.6 Soft-Enclave WASM Isolation & RAM Scrambling (Cold Boot Defense)

> **Giải pháp:** Bảo vệ RAM và dữ liệu nhạy cảm khi không có phần cứng TEE (SGX/SEV) chuyên dụng.

- ☁️ **Wasmtime Cranelift JIT Isolation:** Tạo ra một "Soft-Enclave" bằng cách cô lập toàn bộ logic xử lý khóa bên trong Sandbox WASM (sử dụng Cranelift JIT). Dữ liệu leak ra ngoài sandbox sẽ lập tức bị chặn bởi ranh giới Linear Memory.
- ☁️ **ChaCha8 Ephemeral Key Scrambling:** Sử dụng dòng dữ liệu ngẫu nhiên CSPRNG (ChaCha8) để XOR liên tục vùng RAM chứa khóa. Khóa thực (Plaintext) chỉ xuất hiện trong thanh ghi CPU (Registers) trong micro-giây khi thực hiện phép tính, sau đó biến mất.
- ☁️ **RAII ZeroizeOnDrop:** Cưỡng ép tiêu hủy dữ liệu ngay khi biến trượt khỏi tầm vực (Scope) bằng trait `ZeroizeOnDrop`, đảm bảo vùng nhớ RAM được ghi đè `0x00` tức thì. (Thay thế hoàn toàn cho mlock() và TEE hardware locking).

#### OOB Symmetric Push Ratchet song song với TreeKEM (Push Notification siêu nhẹ)

- 📱💻 **Mục tiêu:** Tách hoàn toàn luồng khóa dùng cho Push Notification ra khỏi cây MLS TreeKEM cồng kềnh, tránh kéo cả cấu trúc `TreeKEM_Update_Path` vào các tiến trình footprint thấp như iOS NSE / Android FCM Service.
- 📱 `Push_Key` là khóa đối xứng AES-256-GCM dãn xuất từ `HKDF(Company_Key, "push-ratchet" || chat_id || push_epoch)` theo chuỗi hash-chain một chiều (`push_epoch` tăng dần), hoạt động **song song** với `Epoch_Key` của MLS nhưng không phụ thuộc vào cấu trúc cây.
- 📱 `Push_Key` được lưu trong vùng bảo mật phần cứng (Shared Keychain trên iOS, StrongBox/Keystore trên Android) với RAM footprint tối thiểu; Main App khi Foreground chịu trách nhiệm thực hiện bước ratchet tiếp theo (tăng `push_epoch`, derive `Push_Key_new`) sau khi nhận signal MLS Epoch Rotation.
- 📱 **NSE/FCM Service không bao giờ tái dựng TreeKEM:** Khi push đến, tiến trình nhẹ chỉ cần đọc `Push_Key_current` từ vùng chia sẻ, giải mã payload CBOR/AES-GCM với $O(1)$ RAM (< 5MB), hiển thị Notification, rồi `ZeroizeOnDrop` để tránh Crypto Blindness và Desync trạng thái giữa MLS Epoch và lớp Notification.

### 4.3 Hardware Isolation & Crypto-Shredding

#### §4.4 Hardware-Bound Memory Guard & IOMMU Posture Enforcement (Chống DMA Attack)

> **Mối đe dọa:** Kẻ tấn công cắm thiết bị PCIe/Thunderbolt độc hại vào laptop để thực hiện DMA (Direct Memory Access) đọc RAM plaintext trực tiếp, bypass CPU và OS access control (Cold DMA Attack, Thunderspy).

- 💻🖥️ **Hardware Security Posture Assessment (VT-d/AMD-Vi Check):** Khi Lõi Rust khởi động, kiểm tra IOMMU trạng thái qua `sysfs` (Linux: `/sys/kernel/iommu_groups/`) hoặc Windows DXGI `D3D12_PROTECTED_RESOURCE_SESSION`. Nếu IOMMU disabled → hiển thị `CRITICAL: DMA_PROTECTION_DISABLED` → từ chối load `Company_Key` vào RAM.
- 💻🖥️ **Rust IOMMU Integrity Check (Runtime):** Mỗi 60 giây, Lõi Rust gọi hàm platform-native để verify IOMMU group membership của PCI bus chứa NIC và storage — nếu device mới join group mà không qua boot-time enumeration → `SecurityEvent::DMA_INTRUSION` → trigger Crypto-Shredding của `Session_Key` + lockscreen immediate.
- 💻🖥️ **Thunderbolt/USB4 Lock (Pre-auth Requirement):** Yêu cầu OS bật `Thunderbolt Security Level ≥ 2` (User Authorization). Nếu Thunderbolt Security = OFF → Lõi Rust từ chối mở kết nối Server, chạy ở Degraded Mode (chỉ local read).
- ☁️ **MDM/Intune DMA Compliance Policy:** Terraform module `mdm-dma-policy.tf` push Group Policy yêu cầu `Kernel DMA Protection: ON` trên Windows 11 + `Boot IOMMU: Enabled` trên BIOS. Thiết bị không pass compliance → MDM revoke `device_certificate` → Lõi Rust nhận revocation signal → Session terminated.
- 💻🖥️ **Critical Alert UI (Design §1.5):** Khi phát hiện DMA violation, UI render full-screen modal `SecurityCriticalAlert` với nền `#1A0000` dark red, icon shield `⚠️`, text `"DMA Intrusion Detected — Session Terminated"`, countdown 10s auto-lockout. Không có nút Dismiss — chỉ có nút `Report to CISO` (auto-compose Ed25519-signed incident report).

#### §Network Obfuscation & Anti-Tracking — HMAC BLE Beaconing (ISO 27001 A.8.20)

> **Vấn đề ISO 27001:** Phát broadcast `Merkle Root Hash` dạng plaintext qua BLE cho phép Wardriving/Tracking định vị nhân viên từ bên ngoài.

- 📱 **iOS/Android — Random MAC Rotation (5min):** Gọi OS API (`CBCentralManagerRestorationOptionScanResults` / `BluetoothAdapter.startDiscovery()` với random address flag) để rotate địa chỉ MAC Bluetooth mỗi **5 phút**. MAC không bao giờ expose địa chỉ hardware thực.
- 📱💻🖥️ **HMAC-Wrapped BLE Advertising:** Root Hash không được phát dạng plaintext. Lõi Rust bọc hash bằng `HMAC-BLAKE3(Mesh_PreShared_Key_daily, root_hash || timestamp_5min_bucket)`. Chỉ thiết bị share `Company_Key`-derived `Mesh_PSK` mới decode được. Passive sniffer chỉ thấy 31 bytes entropy ngẫu nhiên.
- 📱💻 **Mesh PreShared Key (Daily Rotation):** `Mesh_PSK = HKDF(Company_Key, "mesh-beacon" || date_utc || cluster_id)` — xoay vòng mỗi 24h. Key không persist sang ngày mới, Mesh cần re-derive khi resume.
- 💻🖥️ **BLE Payload Compaction (31-byte MTU):** Do BLE Advertising packet giới hạn 31 bytes, HMAC được cắt xuống 16 bytes (128-bit security). Format: `[4B: timestamp_bucket | 16B: HMAC-BLAKE3-128 | 11B: encrypted_delta_hint]`. Đủ để authenticate nhưng không lộ topology.

#### §4.5 Application-Layer Priority Multiplexing — Chống HoLB trên TCP Fallback

> **Vấn đề:** Khi ALPN fallback về gRPC/HTTP2 (TCP), Head-of-Line Blocking xảy ra nếu large file transfer chiếm toàn bộ TCP window, block tin nhắn text nhỏ phía sau.

- 📱💻🖥️ **Rust Priority Scheduler (P0/P1/P2):** Lõi Rust phân loại mọi egress payload vào 3 priority queue: `P0` (Key Updates, Ed25519 Sigs, BFT Consensus — latency-critical), `P1` (Text messages, CRDT Delta-State), `P2` (File transfer chunks, DB Hydration). Scheduler luôn drain P0 và P1 trước khi inject P2 chunk.
- ☁️ **Micro-Chunk Interleaving (64KB slices):** File transfer bị slice thành đơn vị 64KB. Sau mỗi 64KB slice gửi đi, Scheduler kiểm tra P0/P1 queue — nếu có pending → gửi P0/P1 trước khi tiếp tục 64KB tiếp theo. Text message không bao giờ chờ >1 chunk = <50ms delay.
- 🗄️ **BLAKE3 Segmented Merkle Tree (Chunk Integrity):** Mỗi 64KB chunk có BLAKE3 hash riêng, tổ chức thành Merkle Tree. Receiver verify từng chunk độc lập — corrupt chunk chỉ cần requeset lại chunk đó, không cần retransmit toàn bộ file.
- 📱💻🖥️ **Chunk Nonce Progression (AES-256-GCM):** Mỗi chunk được mã hóa bằng `AES-256-GCM` với Nonce tăng dần `nonce_n = Base_Nonce XOR chunk_seq_number`. Decrypt-and-verify từng chunk độc lập — không phụ thuộc chunk trước.

#### Hardware-Backed Signing

| Platform | API | Mechanism |
|---|---|---|
| 📱 iOS | `LAContext` | `SecKeyCreateSignature` + `.biometryCurrentSet` |
| 📱 Android | `BiometricPrompt` | `setUserAuthenticationRequired(true)` + Hardware Keystore |
| 💻 macOS | `CryptoTokenKit` | `kSecAttrTokenIDSecureEnclave` |
| 💻🖥️ Windows | `CNG` | `Microsoft Platform Crypto Provider (TPM 2.0)` + `NCryptSignHash` |
| 🗄️ Gov-Grade | PKCS#11 | SafeNet/Viettel/VNPT CA — Rust `pkcs11` crate |

#### Tiêu hủy DB cũ an toàn: Zeroize & Crypto-Shredding (Xóa sạch dấu vết)

- 📱💻🖥️ **Integrity Validation:** Chỉ sau khi `last_migrated_id` khớp với bản ghi cuối cùng của V1, hệ thống mới kích hoạt lệnh kiểm tra băm (Hash) toàn cục để xác nhận V2 đã sẵn sàng.
- 📱💻 **Physical Zeroization:** Kích hoạt lệnh intrinsics (SIMD/Neon) để ghi đè mã `0x00` lên toàn bộ vùng vật lý của DB cũ trên ổ cứng trong 1-2 ms.
- 📱💻🖥️ **Crypto-Shredding:** Thực hiện xóa Key Encryption Key (KEK) của DB cũ trong Secure Enclave/TPM, biến các byte còn sót lại thành dữ liệu rác không thể giải mã. Tuyệt đối không gọi `VACUUM`.
- 📱💻 **Storage Ring-Buffer (TeraVault VFS):** Pre-allocated blob (`TeraCache.blob` — 500MB Mobile, 5GB Desktop). Crypto-Shredding đánh dấu offset = `FREE_SPACE`. File mới overwrite trực tiếp — Zero I/O Delete, Zero Wear-Leveling.

#### Latency Target: < 30ms end-to-end cho Online Mode (QUIC 0-RTT + co-located VPS). Đạt SLA 99.999% với Anti-Entropy Merkle Sync fallback

#### ALPN & Graceful Network Fallback — Protocol State Machine

> **Nguyên tắc không vi phạm:** TeraChat **không** sử dụng bất kỳ kỹ thuật Bypass Tunnel hay Shadow IT nào. Thay vào đó, Lõi Rust thực thi State Machine đàm phán giao thức (ALPN — Application-Layer Protocol Negotiation) minh bạch, tuân thủ mọi Firewall Enterprise (Palo Alto, Fortinet, F5).

```text
ALPN Protocol State Machine (Auto-negotiation, < 50ms total)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1 │ QUIC/HTTP3 over UDP:443
       │ ◉ ACK within 50ms → ONLINE_QUIC (0-RTT, ~30ms)
       │ ✗ No ACK / Firewall DROP → fallback Step 2
       ▼
Step 2 │ gRPC over HTTP/2 (TCP:443)
       │ ◉ TLS handshake OK → ONLINE_GRPC (1-RTT, ~80ms)
       │ ✗ DPI rejects binary framing → fallback Step 3
       ▼
Step 3 │ WebSocket Secure (wss:// over TCP:443)
       │ ◉ WS Upgrade OK → ONLINE_WSS (1-RTT, ~120ms)
       │ ✗ All transports fail → MESH_MODE (BLE/Wi-Fi Direct)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

- ☁️📱💻 **Step 1 — QUIC/HTTP3 (UDP 443, ưu tiên cao nhất):** Lõi Rust luôn khởi tạo kết nối bằng QUIC. Nếu trong vòng **50ms** không nhận được gói ACK hợp lệ (dấu hiệu Firewall DROP gói UDP) → hủy phiên, chuyển ngay Step 2. Toàn bộ quá trình thử-và-hủy diễn ra hoàn toàn trong nền — người dùng không cảm nhận gián đoạn.
- ☁️📱💻 **Step 2 — gRPC over HTTP/2 (TCP 443, Fallback chuẩn):** `grpc-rs` (Rust binding) thiết lập TLS 1.3 over TCP Port 443 — hoàn toàn hợp lệ với mọi Firewall. Dữ liệu tuân thủ `Content-Type: application/grpc` chuẩn. Firewall Deep Packet Inspection chấp nhận vì không có dấu hiệu bất thường. Latency 1-RTT (~80ms).
- ☁️📱💻 **Step 3 — WebSocket Secure (TCP 443, Fallback cuối cùng):** Khi Firewall bóc tách cả HTTP/2 binary framing, chuyển sang WebSocket `Upgrade` request — trông giống hoàn toàn HTTPS thông thường với Firewall. Lõi Rust dùng `tungstenite` crate, keep-alive ping mỗi 30s để tránh idle timeout.
- 📱💻 **Fast Fallback < 50ms (UI Transparent):** Toàn bộ Step 1→2→3 được thực hiện song song (parallel probe) với TTL riêng biệt, không phải tuần tự — tổng thời gian chuyển đổi < 50ms. HUD QUIC Status cập nhật icon tương ứng (QUIC/gRPC/WSS) mà không hiện dialog.
- ☁️🗄️ **Terraform/Helm Chart cho IT Admin:** TeraChat cung cấp sẵn file `terraform/network-policy.tf` và `helm/values-network.yaml` khai báo rõ: `udp_port_443: optional` + `tcp_port_443: required` + Token Bucket Rate-Limit config chống UDP Amplification. IT Admin của Ngân hàng có toàn quyền quyết định enable UDP hay không — TeraChat không lách luật.
- 📱💻 **Strict Compliance Mode (No UDP Probe):** Khi Admin kích hoạt `Strict Compliance Network Mode` trên CISO Console, Client bỏ qua Step 1 hoàn toàn, kết nối thẳng bằng gRPC TCP — tiết kiệm 50ms probe time trong môi trường Firewall đã biết chắc DROP UDP.
- ☁️ Áp dụng QUIC-Pinning State Machine ở chế độ Strict Compliance Mode chặn Protocol Downgrade Attack (QUIC → WSS).
- ☁️ **Strict ALPN Enclave & HTTP/3 QUIC (ISO 27001 A.14.1.2):** Để chống Tấn công giáng cấp mạng (Downgrade Attack) trên Custom Socket, cô lập quá trình ngầm định danh (Handshake) thông qua tầng Strict ALPN với thông số `h3` hoặc giao thức siêu nhẹ `Noise_XX_25519_ChaChaPoly_BLAKE2s`. Sự bất đối xứng trong khai báo đầu cuối sẽ đá văng mọi máy chủ mạo danh.
- ☁️ **SHA-256 Certificate Pinning (rustls Strict Compliance):** Khóa cứng (HPKP) dấu vân tay SHA-256 của chứng chỉ vào cấu trúc nhị phân của Lõi Rust. Phân tử `rustls` sẽ lập tức Reject kết nối nếu Server dâng lên chứng thư ngoại lai, dù cho Root CA đó có hợp pháp ở cấp độ OS.
- 💻 **Socket Panic Circuit Breaker:** Khi phát hiện có dấu hiệu giáng cấp mạng hoặc Handshake bị thao túng liên tục, Cầu dao (Circuit Breaker) cắt đứng luồng Socket Panic, từ chối cấp phát kết nối TCP/UDP mới trong 30 giây để bảo toàn Plaintext.
- ☁️ Kích hoạt Network Circuit Breaker để vứt bỏ các kết nối có dấu hiệu tấn công.
- ☁️ Sử dụng HTTP/3 Stream QUIC Tunneling bảo mật để ngụy trang lưu lượng mạng.

#### sqlite-vss (DiskANN) — Vector Embeddings có mã hóa (TeraVault VFS Extension)

> **Mục đích:** Thay thế việc nạp toàn bộ tin nhắn vào RAM để chạy NLP bằng K-Nearest Neighbors (KNN) search trực tiếp từ Disk — RAM footprint ≤ 50MB bất kể 1 triệu tin nhắn.

- 💻🖥️📱 **sqlite-vss Integration:** Tích hợp `sqlite-vss` extension vào Lõi Rust như một VFS module, cho phép lưu trữ và truy vấn Vector Embeddings trực tiếp từ SQLite database file. API: `vss_search(embedding_vector, k=10)` trả về Top-K tin nhắn liên quan.
- 💻🖥️ **DiskANN (Graph-based ANN):** Trên Desktop/Server, sử dụng thuật toán DiskANN để build Graph Index từ Embeddings trực tiếp trên Disk (mmap `O(log N)` truy vấn). Index không cần nằm hoàn toàn trong RAM — SSD I/O đủ nhanh cho latency < 20ms per query.
- 📱 **Mobile (Compact IVF Index):** Trên Mobile, sử dụng Inverted File Index (IVF) nhỏ gọn — quantize Embeddings xuống `int8` (4x giảm kích thước). Index file ≤ 100MB trên disk. RAM footprint khi query < 5MB.
- 📱💻🖥️ **AES-256-GCM Encryption (Company_Key):** Mọi Vector Embedding block bắt buộc được mã hóa bằng `AES-256-GCM` với `Company_Key` trước khi ghi xuống Disk qua TeraVault VFS. Không có Embedding nào tồn tại dạng plaintext trên Disk.
- 📱💻🖥️ **Incremental Index Build:** Embedding mới được sinh ra khi nhận tin nhắn (background thread, priority `SCHED_IDLE`). Không block UI thread. Index được append incrementally — không rebuild toàn bộ.

#### Chống trùng lặp dữ liệu vật lý (Storage Bloat) & Tấn công KPA

- ☁️🗄️ **Content-Addressable Storage (CAS) Deduplication:** Khai thác mã băm BLAKE3 để định danh `CAS_Hash` nguyên bản của từng thực thể vật lý, ngăn chặn khởi tạo lại tài nguyên lưu trữ và cắt giảm 40–60% dung lượng.
- 📱💻🖥️ **Salted Message-Locked Encryption (Salted MLE):** Sử dụng thuật toán `BLAKE3` kết hợp `Channel_Key` (từ cây MLS) để sinh khóa hội tụ có muối (Salted MLE) nhằm ngăn chặn dự đoán mã băm trên cụm MinIO.
- 📱💻 **Ownership Proof MAC:** Triển khai cơ chế `Ownership_Proof_MAC` sử dụng `HMAC-BLAKE3` ràng buộc chặt chẽ với `Company_Key` trong Secure Enclave để xác thực quyền sở hữu tệp tin một cách an toàn.
- ☁️ **Policy Enforcement:** OPA Engine thực thi kiểm tra chính sách (Policy check) ngặt nghèo trên Server cho mọi lệnh ghim file (`pin_file`).
- 📱💻🖥️ **AES-256-GCM Armor:** Lớp giáp mã hóa AES-256-GCM đảm bảo dữ liệu thô (Encrypted_Blob) trở nên vô dụng nếu kẻ tấn công không nắm giữ khóa giải mã nhóm.

#### Memory Defense

- 💻🖥️ **Desktop/Server:** Kích hoạt `ZeroizeOnDrop` và Inline RAM Scrambling. Kiểm tra BitLocker/FileVault khi khởi động — từ chối nếu không bật.
- 📱 **Mobile:** ZeroizeOnDrop (RAII). Plaintext RAM <50ms, ghi đè `0x00` ngay sau scope.

#### ECRP AI Context — Memory Management (Per Platform)

> **Áp dụng cho toàn bộ pipeline ECRP:** Decrypt → NER Masking → SessionVault → De-tokenize.

- 💻 **macOS / Windows / Linux:** Biến chứa Context Plaintext (`EgressContextBuffer`) phải được bảo vệ bằng `ZeroizeOnDrop`. Toàn bộ struct phải implement trait `Drop { fn drop(&mut self) { self.zeroize(); } }` — đảm bảo không có window nào giữa scope end và ghi đè `0x00`.
- 📱 **iOS / Android:** Sử dụng `ZeroizeOnDrop` trên Heap. `EgressContextBuffer` phải được giải phóng trong vòng < 500ms kể từ khi được cấp phát. Mọi thao tác Masking qua FFI/JSI phải hoàn thành trong window đó — không được hold biến qua async boundary.
- 📱💻🖥️ **SessionVault (Bảng ánh xạ MASK→Real):** Tồn tại tối đa ≤ 1 HTTP Request lifecycle. Bị `ZeroizeOnDrop` ngay sau De-tokenize — **trước khi** `StateChanged` IPC event được emit lên UI. Không persist, không log, không core dump.
- 📱💻🖥️ **Byte-Quota Guard (Circuit Breaker):** Rust Core kiểm tra `payload_size ≤ 4096 bytes` tại thời điểm serialize Protobuf — trước khi mở bất kỳ TCP connection nào. Vượt ngưỡng → `ZeroizeOnDrop` `EgressContextBuffer` ngay lập tức, trả lỗi `EgressError::QuotaExceeded`.

#### Blind Architecture — Write-Only FFI Mandate

> **Nguyên tắc cứng:** Lõi Rust phải được thiết kế theo mô hình "Write-Only Memory" đối với UI. Không một FFI/JSI endpoint nào được phép trả về `Vec<u8>` (Byte Array) nếu liên quan đến khóa hoặc plaintext Context.

- 📱💻🖥️ **FFI Endpoint chuẩn:** UI chỉ được gọi `invoke_ai_context(message_ids: Vec<String>)`. Lõi Rust tự trỏ vào SQLite, lấy Ciphertext, dùng `Session_Key` (bảo vệ bởi `ZeroizeOnDrop`) để giải mã trong RAM, che PII, và chỉ emit `Masked_String` lên UI qua `StateChanged`.
- 📱💻🖥️ **Cấm tuyệt đối:** Bất kỳ FFI/JSI endpoint nào có signature dạng `fn get_session_key() -> Vec<u8>` hay `fn get_plaintext_context() -> String` phải bị xóa khỏi ABI. Code review cần kiểm tra luật này bằng CI lint rule.
- 📱💻🖥️ **ZeroizeOnDrop bắt buộc:** Mọi struct xử lý Context AI (`EgressContextBuffer`, `SessionVault`, `PlaintextArena`) bắt buộc `#[derive(ZeroizeOnDrop)]`. Ngay khi block kết thúc (out of scope), RAM vùng đó bị ghi đè `0x00` trước khi OS Garbage Collector can thiệp.

#### OOM Guard — Sliding Window Byte-Quota (Mobile Specific)

- 📱 **Jetsam Risk:** Nhồi 50–100 tin nhắn vào RAM để chạy ONNX Local trên iOS/Android chắc chắn trigger Jetsam OOM-Kill. **Tuyệt đối cấm** load toàn bộ context buffer cùng lúc.
- 📱 **Sliding Window Tokenizer:** Lõi Rust đọc từng dòng từ `hot_dag.db` (SQLite WAL) — không load toàn bộ. Hard Limit Buffer = **4096 Bytes (~4KB)**. Khi chuỗi vượt ngưỡng, Circuit Breaker ngắt luồng đọc, giữ lại 4KB gần nhất.
- 📱 **`MaybeUninit` Allocation:** Biến phục vụ ONNX Local Model phải khai báo bằng `std::mem::MaybeUninit<T>` — OS không cấp phát bộ nhớ phụ cho uninitialized data, giảm peak RAM.
- 💻🖥️ **Desktop:** Sliding Window áp dụng tương tự nhưng Window có thể lớn hơn (configurable per Admin Policy, default 16KB). Bảo vệ RAM bằng `ZeroizeOnDrop` cho buffer.

#### Non-Repudiation Audit Log — BLAKE3 + Ed25519 (Tamper-Proof)

> **Rủi ro Khẩn cấp:** ONNX Local NER có thể có False Negative (bỏ sót PII). Cơ chế này đảm bảo dù rò rỉ xảy ra, CISO vẫn có bằng chứng mật mã học để quy trách nhiệm.

- 📱💻🖥️ **Pre-Egress Hashing:** Trước khi Lõi Rust serialize `EgressNetworkRequest`, toàn bộ khối Plaintext (dù đã mask hay chưa) bắt buộc được băm bằng **BLAKE3** (`payload_hash = blake3::hash(plaintext_bytes)`).
- 📱💻🖥️ **Ed25519 Signing (Secure Enclave / TPM 2.0):** Lõi Rust dùng `Device_Key` (Ed25519 — nằm trong Secure Enclave iOS / Android StrongBox / TPM 2.0 Desktop) ký lên `payload_hash`, tạo `Audit_Log_Entry = {device_id, timestamp, payload_hash, ed25519_sig}`.
- 📱💻🖥️ **CRDT Local Audit Chain:** `Audit_Log_Entry` được ghi append-only vào chuỗi CRDT cục bộ. Không thể xóa hay sửa mà không phá vỡ chữ ký liên kết.
- ☁️🗄️ **Admin/CISO Verification:** Khi Admin truy xuất qua TeraChat Console, hệ thống đối chiếu chữ ký Ed25519 của từng Entry. Nếu API đối tác thứ ba (vd: OpenAI) bị lộ dữ liệu, Admin có Cryptographic Proof xác định chính xác: thiết bị nào, người dùng nào, thời điểm nào đã trigger Egress — không thể chối bỏ.

#### Zeroize & Deferred Task Suspension

- 📱💻 Áp dụng `ZeroizeOnDrop` (RAII) để ghi đè $0x00$ lên vùng nhớ `Decrypted Secure Arena` ngay khi giao dịch bị hủy.
- 📱 Tích hợp iOS Background Delegate (`BGTask.setTaskCompleted`) và Android `WorkManager` retry để đưa tác vụ JIT Indexing vào hàng đợi thực thi lại khi thiết bị mở khóa.
- 📱 Giải phóng triệt để vùng nhớ `ZeroizeOnDrop` để lách qua và tránh JetSam OOM-Kill trong trạng thái nền.

#### Remote Attestation

| Platform | API | Yêu cầu |
|---|---|---|
| 📱 iOS | `DCAppAttestService` | App gốc, không Jailbreak |
| 📱 Android | `Play Integrity API` | `MEETS_STRONG_INTEGRITY` |
| 💻🖥️ Windows | `TPM 2.0 Health Attestation` | PCR check + BitLocker ON |

- ☁️ Chỉ `MEETS_BASIC_INTEGRITY` hoặc Root → từ chối + Remote Wipe.

#### Binary Hardening & Fuzzing

- 📱💻🖥️ Control Flow Flattening (O-LLVM), Bogus Control Flow, Instruction Substitution, Compile-time String Encryption.
- App tự hash `.text section` khi khởi chạy. Hash thay đổi → Silent Crash.
- ☁️ **Smoke Fuzz (PR Gate):** 10 phút / Crash → Block Merge. **Deep Fuzz (Nightly):** 24h LibFuzzer + AFL++ + Stateful MLS Fuzzing. LLVM Sanitizers: ASan, MSan, UBSan.

#### Cắt bỏ Cục bộ & Tự phục hồi DAG (Surgical Amputation & DAG Self-Healing)

- 📱 **Surgical Amputation (Xử lý SIGKILL):** Tình huống iOS "chém đứt" (SIGKILL) tiến trình NSE trong lúc ghi dở vào SQLite WAL là kịch bản rủi ro cao. Nếu sự cố xảy ra tạo ra các file database lỗi, cơ chế Atomic Drain tại Main App có khả năng nhận biết Transaction hỏng (Incomplete WAL Frame) và thực hiện cắt bỏ cục bộ (Surgical Amputation) đoạn bị hỏng, ngăn ngừa cascading failure sang `hot_dag.db` chính.
- 📱 **DAG Self-Healing (Tự phục hồi Cấu trúc Hash Chain):** Nếu một mắt xích (Message Block) bị lỗi/thiếu do SIGKILL NSE, Lõi Rust phát hiện lỗ hổng chuỗi (Missing Vector Clock / Missing Hash Parent) khi dựng lại DAG. Ngay lập tức, thuật toán Self-Healing tự động gửi tín hiệu Sync-Request (qua P2P hoặc Server) để lấy lại dung sai (Delta) chính xác bị khuyết để hàn gắn cây Hash Chain của giao thức MLS, duy trì vẹn toàn thông điệp thay vì panic đổ vỡ toàn cục.

---

## 5. Network & Communication Protocols

### 5.1 Real-time Messaging

#### WebSocket E2EE Relay

- ☁️ Server relay ciphertext blob — không giải mã. Rate Limiting (Redis ZSET Sliding Window). OPA throttle theo phòng ban.

#### E2EE Push Notification — iOS (NSE)

- 📱 `UNNotificationServiceExtension` + `mutable-content: 1` (chuẩn Signal/WhatsApp).
- 📱 **NSE Micro-Crypto Build Target:** Loại bỏ 100% MLS, CRDT Automerge, SQLCipher. Chỉ giữ AES-256-GCM decrypt + Shared Keychain read. Footprint ~4MB (safe dưới 24MB Apple limit).
- 📱 **Push Payload ≤ 4KB:** fields: `chat_id`, `sender_display`, `preview_ct` (AES-256-GCM), `has_attachment`, `push_epoch`. Không HTTP GET trong NSE.
- 📱 **OOB Symmetric Push Ratchet (Tách khỏi MLS TreeKEM):** `Push_Key` là khóa đối xứng siêu nhẹ (AES-256-GCM) được dãn xuất từ `HKDF(Company_Key, "push-ratchet" || chat_id || push_epoch)` theo chuỗi hash-chain một chiều, **hoàn toàn độc lập với cây khóa MLS TreeKEM**.
- 📱 `Push_Key` được lưu trong Shared Keychain (App Group) dưới dạng bản sao tối thiểu, chỉ chứa material cần thiết cho AES-256-GCM; Main App khi ở Foreground chịu trách nhiệm đồng bộ/rotate `Push_Key` mới sau mỗi lần thay đổi MLS Epoch hoặc khi nhận tín hiệu Key Desync, NSE chỉ đọc `Push_Key` hiện tại và giải mã payload trong vòng RAM < 5MB theo độ phức tạp $O(1)$ rồi `ZeroizeOnDrop`.
- 📱 **Key Desync Fallback:** Không tìm thấy Key → fallback text an toàn, không crash.

#### E2EE Push Notification — Android (FCM)

- 📱 Data Message → `FirebaseMessagingService` → giải mã Rust FFI. `StrongBox Keymaster` lưu Symmetric Push Key.

#### Desktop Background Daemon

- 💻🖥️ **`terachat-daemon`** ~4.5MB RAM — tách biệt khỏi Tauri UI.
- 💻 Windows Service (`sc create`) / macOS `launchd` LaunchAgent / 🖥️ Linux `systemd` user service.
- 💻🖥️ Nhận E2EE payload → giải mã preview → OS Native Notification → xóa plaintext. DB sync chỉ khi Tauri UI mở.

### 5.2 Survival Mesh Network (P2P, BLE 5.0, Wi-Fi Direct)

#### Platform-Agnostic Transport: `MeshTransport` Trait

> **Attack Surface (Trước):** Lõi Rust gọi trực tiếp OS Wi-Fi module → Apple **Reject** vì vi phạm sandbox rule, Android cần `CHANGE_WIFI_STATE` nguy hiểm.
> **Attack Surface (Sau):** Rust Core không biết platform. Chỉ nhận `DataStream<u8>` từ FFI. Host Layer (Swift/Kotlin) chịu trách nhiệm phân phối transport đúng OS.

```
trait MeshTransport: Send + Sync {
    fn send(&self, payload: &[u8], peer_id: &PeerId) -> Result<(), MeshError>;
    fn recv_stream(&self) -> impl Stream<Item = (PeerId, Vec<u8>)>;
    fn discover_peers(&self) -> impl Stream<Item = PeerId>;
}
```

- ☁️🗄️ **Nguyên tắc thiết kế:** Lõi Rust **không** trực tiếp gọi bất kỳ Wi-Fi/BLE module nào. Rust Core nhận `DataStream` từ FFI Bridge. Host Layer (Swift/Kotlin) chịu quyết định dùng transport nào dựa trên OS context.
- 📱 **iOS — `MultipeerConnectivityAdapter`:** Implement `MeshTransport` bằng Apple `MultipeerConnectivity` (MCSession) thay vì Wi-Fi Direct để giữ nguyên khả năng P2P mà không bị Apple Reject. MCSession tự động dùng BLE + AWDL (Apple Wireless Direct Link) — tốc độ tương đương Wi-Fi Direct (~200 Mbps) mà hoàn toàn hợp lệ theo App Review Guidelines Rule 2.5.
- 💻🖥️ Android / Desktop: Dùng `WifiDirectAdapter` (Android) và `LocalSocketAdapter` (Desktop) implement cùng trait `MeshTransport`.

| Layer | Protocol | iOS | Android/Desktop |
|---|---|---|---|
| **Signal Plane** | BLE 5.0 Advertising | `CoreBluetooth` | `BluetoothLeAdvertiser` |
| **Data Plane** | Wi-Fi P2P | `MultipeerConnectivity (AWDL)` | `Wi-Fi Direct` |

#### Mesh Network kiểu Bitchat/Briar (Delay-Tolerant Networking - DTN)

- 📱💻🖥️ **Store-and-Forward Gossip Protocol (Text):** Khi mất mạng lưới (Offline), tin nhắn CRDT (<1KB) mã hóa bằng khóa bảo mật đích được truyền đa bước ("nhảy cóc") qua các Router Trung gian (Mesh Nodes). Node bị cấm đọc nội dung nhưng cho phép lưu trữ tạm thời và phát kết tiếp thông lượng cho đến đỉnh đích.
- 📱💻🖥️ **Direct-Link Only Media (File/Video):** Trong `Mesh Mode`, Lõi Rust đóng băng công năng định tuyến multi-hop đối với mọi tệp tin nặng nề. Dữ liệu băng thông cao bắt buộc giao dịch P2P Wi-Fi Aware khép kín chỉ khi 2 máy chạm bán kính trực diện (< 20 mét). Khung UI hiển thị "Chỉ gửi file khi ở gần".
- 📱 **Passive Network Sensing (Cảm biến Mạng Thụ động):** Vận dụng bộ ngắm OS Native (`NWPathMonitor` iOS / `ConnectivityManager` Android) để bắt sự kiện luồng sóng tắt / mở Baseband. Đánh thức Tầng Logic Swift/Kotlin thay vì rượt vòng lặp dò quét tiêu pin điên cuồng ở lớp Lõi Rust, kéo mức Base Energy Consumption sát 0.
- 📱💻🖥️ **BLE Duty-Cycle Management:** Răm rắp duy trì thuật toán vắt kiệt cường độ xung quét BLE: Tỉnh lược 200ms Advertising/Scanning xen lẫn 800ms chu kỳ Sleep để giảm hỏa 80% công suất tải ăn nguồn. Kết cấu Heartbeat Advertising rời rạc kết nạp linh động MTU Fragmentation cực hẹp.
- 📱 💻 **Store-and-Forward Routing & Gossip Protocol:** Thực thi Asynchronous Data Muling định tuyến phi đồng bộ giải phóng ách tắc Phân mảnh Mesh Island do chia cắt vật lý.
- 📱 **E2EE MLS Merkle DAG Diffs (Zstandard) qua Wi-Fi Direct:** Trao đổi gói nén trạng thái dị biệt đa thức đảm bảo kết nối mạng ngang hàng.
- 💻 **UI Mesh Mode Radar Bridge Synced Event:** Đồng bộ hóa tín hiệu biến tập hợp hiển thị giao diện tức thời nối liền đảo mạng.

#### Tối ưu hóa Băng thông Mạng lưới Sinh tồn (Hybrid Multipath Transport Plane)

#### Phân tách kênh Truyền dẫn và Gossip Discovery (Hybrid Multipath Transport Plane)

- 📱💻 Phân định **Cấp độ 1 (Tối ưu Sinh tồn - Background):** Sử dụng duy nhất giao thức **BLE L2CAP CoC** (Control Plane) cho phép ứng dụng truyền tải ngầm payload nhỏ (<500KB) như tin nhắn SOS/văn bản mà không cần người dùng cấp quyền OS liên tục.
- 📱💻🖥️ **Gossip Discovery & L2CAP Chunked Transmission:** Trao đổi Vector trạng thái (Hash) qua thuật toán Gossip để nhận diện phiên bản mới khả dụng trong Mesh. Payload OTA được phân mảnh (Chunking) thành các block 512 bytes truyền tải qua kênh L2CAP CoC cực kì ổn định để tránh phân mảnh MTU.
- 📱💻🖥️ Bắt buộc chuyển sang **Cấp độ 2 (Truyền tải nặng - Foreground):** Kích hoạt **Wi-Fi Direct / LAN / SoftAP** (Data Plane) phục vụ truyền tải tệp tin đa phương tiện và bản cập nhật nhị phân (.exe/.dmg) lớn nhờ sự điều phối băng thông của các Super Nodes. Yêu cầu popup xác nhận từ người dùng để tránh vi phạm background policy của Apple.
- 📱 Cơ chế Opportunistic Tear-down ngắt kênh Data Plane ngay sau khi truyền tệp thành công nhằm bảo toàn năng lượng pin thiết bị.

#### Asymmetric Hierarchical Mesh — Desktop=SuperNode (Backbone), Mobile=Leaf Node

> **Kiến trúc Mạng lưới Bất đối xứng:** iOS không thể duy trì background socket và có RAM hạn chế. Android không bị giới hạn background nhưng pin yếu hơn Desktop. Giải pháp: phân cấp vai trò theo năng lực phần cứng thay vì đối xứng đồng đều.

- 💻🖥️ **Desktop/Laptop làm Super Node (Backbone):** Lõi Rust tự động thăng cấp các thiết bị Desktop/Server thành "Trạm Trung chuyển" (Store-and-Forward Router) khi phát hiện `os_type = "macos" | "windows" | "linux"` và `battery_status = "AC powered"`. Super Nodes giữ toàn bộ Causal Graph lịch sử, không giới hạn kích thước, và hoạt động background 24/7.
- 📱 **Mobile làm Leaf Node (Delta-only Satellite):** Mobile tuyệt đối không giữ toàn bộ lịch sử DAG khi offline. Lõi Rust trên Mobile chỉ duy trì **Delta-State CRDT Pending Buffer** (tối đa 50MB trên disk). Khi iOS bị OS đưa vào Suspended, Super Node tự động archive gói tin chờ. Khi iOS đánh thức qua iBeacon hoặc MultipeerConnectivity discovery, Super Node chỉ push delta nhỏ (≤ 2MB) — không bao giờ push full DAG.
- 📱💻🖥️ **Auto-Promotion Logic:** Nếu không có Super Node nào khả dụng trong Mesh (ví dụ: chỉ có Mobile trong phòng), Lõi Rust bầu chọn thiết bị Android có RAM khả dụng cao nhất làm Temporary Super Node. iOS tuyệt đối không được bầu làm Super Node do giới hạn Background Execution.

#### Split-Brain Dictator Election — iOS Exclusion từ Quorum Candidacy

> **Nợ kỹ thuật:** Bầu chọn Dictator qua `BLAKE3 Hash` để sáp nhập DAG sau Split-Brain yêu cầu $O(N \log N)$ RAM và CPU. Nếu node được bầu là Mobile đang yếu pin → tiến trình sáp nhập sập máy → Deadlock toàn Mesh.

- 💻🖥️ **Desktop-First Candidacy Policy:** Dictator Election chỉ xem xét các node có `device_class = "desktop" | "server"` như ứng viên hợp lệ. Lõi Rust gắn `election_weight = 0` cố định cho mọi node có `device_class = "mobile"` — loại bỏ hoàn toàn khả năng Mobile được bầu làm Dictator.
- 📱 **Mobile Read-only Observer:** Sau khi Dictator (Desktop) hoàn thành DAG merge $O(N \log N)$, Lõi Rust trên Dictator xuất **Materialized Snapshot** (squashed state, không chứa raw CRDT events) và phân phát về các Leaf Node Mobile. Mobile chỉ cần apply Snapshot — $O(1)$ thay vì $O(N \log N)$.
- ☁️ **Quorum Fallback (Không có Desktop):** Nếu toàn Mesh chỉ có Android, bầu node có `available_ram_mb` cao nhất. Nếu toàn Mesh chỉ có iOS, Dictator Election bị hoãn lại và hệ thống kích hoạt trạng thái "Causal Freeze" — không merge, không ghi, chỉ đọc — cho đến khi có Desktop hoặc Android gia nhập Mesh.

#### Shadow-Drop via System-level Steganography (Chống OPA chặn tố giác)

- 📱💻🖥️ Nhúng payload mã hóa chứa bằng chứng hoặc tin nhắn tố giác vào cấu trúc gói tin `CRDT_Garbage_Collection_Log` hoặc `System_Telemetry`.
- 📱💻🖥️ Tận dụng đường hầm mTLS Federation Bridge để đẩy dữ liệu xuyên qua lớp chặn lọc OPA tại Gateway của chi nhánh.
- ☁️ Màng lọc "Magic Bytes" tại máy chủ HQ thực hiện bóc tách (De-capsulation) dữ liệu tố giác khỏi luồng hệ thống.

#### Slotted Mesh & Synchronized Duty Cycle (Đồng bộ chu kỳ Slot Mesh)

- 📱💻🖥️ Thuật toán Time-Division Multiplexing (TDM) kết hợp Hybrid Logical Clock (HLC) để đồng bộ thời gian thức/ngủ giữa các node.
- 📱 Duy trì 1% Duty Cycle (chỉ thức 200ms mỗi 20s) để tối ưu hóa thời gian anten BLE ở trạng thái Deep Sleep.
- 📱 Cơ chế Extended Connection Event chỉ kích hoạt khi xác nhận có Payload lớn cần trao đổi.

#### Companion Device Manager (CDM) Integration (Chống Android Doze)

- 📱 Đăng ký đặc quyền `REQUEST_COMPANION_RUN_IN_BACKGROUND` để duy trì luồng quét BLE vĩnh viễn không bị ngắt quãng.
- 📱 Định nghĩa Hardware Mesh-ID giả lập làm Thiết bị đồng hành (Companion Device) nhằm lách rào cản App Standby Buckets hà khắc.
- 📱 Kích hoạt cơ chế Hardware BLE Scan Hardware-offloaded nhằm tối ưu hóa tối đa năng lượng tiêu thụ trong chế độ ngủ sâu Doze.

#### Asymmetric Mesh Handshake & SoftAP Hybrid Data Plane (Đứt gãy P2P Đa nền tảng)

- 📱 Điều phối Android tự động kích hoạt SoftAP ẩn với WP2 ngẫu nhiên để làm cầu nối trung tâm.
- 📱 Sử dụng API `NEHotspotConfiguration` trên iOS để gia nhập mạng cục bộ của Android thông qua tín hiệu BLE Handshake.
- 📱 Tận dụng giao thức `BLE L2CAP CoC` (Connection-oriented Channels) làm luồng vận chuyển SOS dự phòng rủi ro đứt gãy kết nối Wi-Fi Direct.

#### Thực thi mật mã trì hoãn (Deferred Cryptographic Execution)

- 📱 Cơ chế "Write-Only mmap" để ghi dữ liệu RaptorQ thô vào SQLite mà không thực hiện giải mã toán học ở Background.
- 📱 Trì hoãn việc giải hệ phương trình ma trận và ML-KEM JIT cho đến khi App chuyển sang Foreground (Just-In-Time Evaluation).
- 📱 Tận dụng NPU/Multi-threading để xử lý dồn tích khối lượng công việc ngay khi người dùng mở màn hình.
- 📱 Áp dụng ZeroizeOnDrop (RAII) để xóa sạch dữ liệu trung gian ngay sau khi giải mã thành công.

#### Phân cấp Nút mạng Mesh Bất đối xứng (Asymmetric Hierarchical Role Delegation)

- 💻🖥️ Triển khai cơ cấu Super Nodes trên nền tảng Desktop/Laptop đảm trách vai trò Backbone vững chắc cho tiến trình Store-and-Forward vòng định tuyến.
- 📱 Cơ động hóa Relay Nodes tận dụng chuẩn Android Foreground Service thiết lập trạm chuyển tiếp Data Mule tịnh tiến gói tin E2EE.
- 📱 Ràng buộc giới hạn Leaf Nodes hoạt động thụ động trên nền tảng iOS iBeacon Ranging chuyên trách rình rập và nhận gói tin để lách rào cản Jetsam do OS khóa nền.

#### Offline PKI Defense

- **Offline TTL (24h):** App tự đóng băng Session nếu mất Server \>TTL — kể cả Mesh vẫn hoạt động.
- **Gossip CRL:** 1 node bắt Internet → tải CRL delta → ký Enterprise CA → Gossip BLE sang toàn Mesh ~30s → node revoked bị evict khỏi MLS Group, kích hoạt Key Rotation.
- **Replay Protection:** Monotonic Version Counter + CA Signature + Timestamp Window (48h).

#### Opportunistic Mesh Wakeup & Asynchronous Store-and-Forward

- 📱 Tận dụng giao thức iBeacon Ranging (CoreLocation) để lách giới hạn của hệ điều hành, duy trì khả năng quét BLE ở chế độ Background.
- 💻🖥️📱 Cấu hình Định tuyến Bất đồng bộ (Asynchronous DAG Routing) kết hợp cơ chế Store-and-Forward trên các Super Node nội bộ.
- 📱💻🖥️ Triển khai mạng lưới Causal Graph kết hợp Pending Buffer nhằm xử lý tối ưu độ trễ và các gói tin Out-of-Order.

### 5.6 Clustered Mesh Topology & Super Node Silent Election (Chống Broadcast Storm)

- 💻🖥️📱 Phân quyền kiến trúc mạng nhện sinh tồn (Hierarchical Mesh Topology): ấn định Desktop làm Super Node và iOS làm Leaf Node tuân thủ thuật toán định tuyến A*.
- 💻🖥️📱 **Thuật toán Silent Election:** Tự động thăng cấp các thiết bị có chỉ số Pin/CPU mạnh nhất lên làm Super Nodes để điều phối mạng lưới khi Offline.
- 💻🖥️📱 Phân tách luồng giao tiếp: Leaf Nodes (Mobile) gắn kết qua BLE Point-to-Point, trong khi Super Nodes (Desktop) kết nối tầng trên qua Wi-Fi Direct/AWDL băng thông rộng.
- 📱💻 Cơ chế **Gossip Rate Limiting** kết hợp nén `zstd` để giảm thiểu mật độ gói tin dư thừa tràn qua rào cản băng thông BLE hẹp.
- 📱 Triển khai tín hiệu iBeacon Ranging trên CoreLocation nhằm cưỡng chế sóng BLE ở chế độ Background, lách qua rào cản đánh thức từ hệ điều hành.
- 📱 Kiến tạo cầu nối vật lý (Data Mule) tự động chuyển phát chéo gói tin thông qua chu trình Android Foreground Service.

### 5.7 Dò tìm Nội dung Tất định Blind Content-Addressable (Oblivious Bloom Filter)

- 📱💻🖥️ Tổ chức khối nén phân tán Distributed Bloom Filters (Compressed) cấu trúc hóa đại diện kho `cas_ref` nội bộ thiết bị.
- 📱💻 Phát tán tín hiệu quảng bá định danh "CAS-HIT" thông qua nền tảng BLE 5.0 Advertising, tuyệt đối giấu kín gốc danh tính User_ID.
- 📱💻🖥️ Xác định linh hoạt vị trí tệp tin trong mạng nhện Mesh thông qua thuật toán Gossip với độ trễ truy vấn < 500ms.

### 5.8 Truyền tải File đa kênh mạng Mesh (TeraLink Multipath Data Mule)

- 📱💻 Tách biệt luồng điểu khiển Control Plane (BLE 5.0) và luồng dữ liệu Data Plane (Wi-Fi Direct/AWDL) nhằm cực tiểu hóa hao hụt năng lượng.
- 📱💻🖥️ Đánh giá chiều hướng vector RSSI và RTT kết hợp thuật toán A* để định tuyến đường đi vật lý ngắn nhất tới Super Node hoặc thiết bị trung chuyển (Mule).
- 📱💻 Phân rã mã hóa tải trọng (Segmented Fragmentation) thành các phân mảnh siêu nhỏ 400 bytes, lách qua rào cản nút thắt cổng MTU của giao thức BLE.

### 5.9 Tiết kiệm Năng lượng Mạng Mesh (iBeacon Stealth Mode & Gossip Broadcast)

- 📱 Cưỡng ép đóng gói tín hiệu mạng Mesh vào giao thức iBeacon Ranging (CoreLocation) nhằm lách hạn chế ngầm định của iOS, duy trì chu kỳ quét Background.
- 📱💻 Sử dụng **Gossip-based Broadcast** để lan tỏa dữ liệu giữa các thiết bị lân cận — loại bỏ overhead của thuật toán định tuyến không gian 3D phức tạp.
- 📱💻 Điều tiết cấu hình Opportunistic Wakeup chủ động kích hoạt năng lượng định tuyến khi payload có nhu cầu di chuyển tệp thực, hạ tần suất Beacon xuống 1 lần/5 phút ở trạng thái Standby.

### 5.9.1 Single-Frame Binary Serialization for Mesh Recovery (Chống Phân mảnh BLE 5.0)

> **Bài toán:** BLE 4.2 MTU tối đa 251 bytes buộc phải phân mảnh L2CAP nếu payload lớn hơn — gây mất gói, thứ tự sai và tăng overhead. Trong kịch cảnh khôi phục khẩn cấp (SOS Beacon, Multi-Sig Escrow shard), mỗi byte thừa đều là rủi ro.

- 📱💻🖥️ **Protobuf Binary Encoding (Không Metadata):** Mọi Mesh Recovery payload (SOS Beacon, `Welcome_Packet`, Shun command) được serialize bằng Protobuf Binary (không phải JSON/CBOR) với schema tối giản — chỉ giữ các field bắt buộc. Ví dụ: một Multi-Sig Escrow shard request chỉ ~80 bytes (Node_ID 16B + Epoch 8B + Signature 64B + padding), nằm gọn trong một BLE frame đơn.
- 📱 **Native BLE Extended Advertising (Zero Fragmentation):** Trên thiết bị hỗ trợ BLE 5.0, Lõi Rust yêu cầu OS sử dụng **Extended Advertising PDU** (payload tối đa 255 bytes/frame, không cần L2CAP chunking) thay vì Legacy Advertising. Payload Recovery được nhét vào một PDU duy nhất → loại bỏ hoàn toàn xác suất mất mảnh.
- 📱💻🖥️ **Hardware-bound Ed25519 Signing (Secure Enclave / StrongBox):** Mỗi Recovery frame được ký bằng `Device_Identity_Key` trực tiếp trong Secure Enclave/StrongBox — signature 64 bytes append vào cuối payload trước khi gửi. Receiver xác thực signature trước khi decode bất kỳ byte nào khác, ngăn frame giả mạo tiêu tốn CPU.

### 5.9.2 Zero-Knowledge Metadata Masking in Mesh Broadcast (Chống Rò rỉ Siêu dữ liệu qua Sóng vô tuyến)

> **Bài toán:** Mọi BLE Advertising đều broadcast `Node_ID` hoặc `Device_ID` dưới dạng plaintext trong Manufacturer Specific Data — kẻ tấn công có thể thu thập traffic, map danh tính người dùng mà không cần bẻ mã hóa nội dung.

- 📱 **Blinded Device_ID (16-byte Physical Identifier):** Thay vì dùng Device MAC hoặc `Node_ID` thật, Lõi Rust sinh một `Blinded_ID = HMAC-SHA256(Device_Identity_Key, Epoch_Slot_Index)[0:16]` — thay đổi mỗi 5 phút theo `Epoch_Slot_Index`. Kẻ quan sát ngoài không thể link hai Beacon từ cùng thiết bị giữa hai Epoch.
- 📱💻🖥️ **Curve25519 Identity Public Key Exchange:** Khi hai thiết bị muốn xác thực lẫn nhau (không phải broadcast mở), Lõi Rust thực hiện ECDH Curve25519 One-Pass — trao đổi ephemeral public key qua BLE Scan Response, giải ECDH ra `Shared_Secret`, dùng làm channel key cho phiên L2CAP kế tiếp. Không bao giờ dùng static key trong giao tiếp Layer 2.
- 📱 **Sealed Sender Protocol for Mesh Signal Plane:** Mọi CRDT event, Shun command, và SOS payload gửi qua Mesh được bọc trong **Sealed Sender** — receiver chỉ biết nội dung sau khi giải mã, không biết sender trước khi mở gói. Kẻ relay trung gian (Super Node) forward blindly mà không đọc được `Node_ID` của người gửi thật.

### 5.9.3 Stealth Wake-up Protocol — Metadata Anonymization (Chống Rò rỉ Ngữ cảnh & Vị trí Vật lý)

> **Bài toán:** Ngay cả khi nội dung BLE Advertising được mã hóa, định danh thiết bị (MAC address, static `Node_ID`) vẫn lộ ra trong Layer 2 header. Kẻ tấn công thu thập Beacon theo thời gian có thể vẽ bản đồ vị trí vật lý của toàn bộ nhân viên trong tòa nhà.

- 📱 **Resolvable Private Address (RPA) — OS-level MAC Rotation:** Lõi Rust yêu cầu CoreBluetooth / BluetoothLeScanner sử dụng **Resolvable Private Address** theo chuẩn BT spec 5.3: MAC vật lý xoay vòng mỗi 15 phút, được dẫn xuất từ `IRK` (Identity Resolving Key) lưu trong Secure Enclave. Peer được ủy quyền giải `RPA` → `real MAC` bằng `IRK` — kẻ ngoài không thể track.
- 💻📱 **Identity Commitment ($C = \text{HMAC}(R, PK_{identity})$):** Thay vì broadcast `Node_ID` thật, thiết bị tính `C = HMAC-SHA256(R, PK_identity)[0:8]` (8 bytes truncated), trong đó `R` là Nonce ngẫu nhiên mỗi phiên. `C` đại diện cho danh tính ngắn hạn — peer biết `PK_identity` có thể verify, kẻ ngoài không thể link `C` với người dùng thật vì `R` thay đổi liên tục.
- 💻📱 **Ephemeral Key Derivation (Per-session):** Cho mỗi phiên phát sóng mới, Lõi Rust sinh `EphemeralKey_session = HKDF(Device_Identity_Key, R || Session_Index)`. Khóa này chỉ sống trong RAM (không ghi disk) và tự hủy sau 5 phút hoặc khi phiên kết thúc — đảm bảo Forward Secrecy tại Layer 2.
- 📱 **Single-frame Stealth Payload (`Nonce + C_trunc + Ciphertext`):** Payload BLE Advertising có cấu trúc cố định 3 trường: `[8B Nonce R] + [8B C_trunc] + [N bytes Ciphertext]`. Tổng ≤ 31B cho Legacy Advertising hoặc ≤ 255B cho Extended Advertising. Không có field nào chứa thông tin định danh tĩnh.

### 5.9.4 Darknet Signal Plane — Ghost Mesh (Chống Tấn công Theo dõi & Phân tích Lưu lượng)

> **Bài toán:** Kẻ tấn công tinh vi có thể phân tích pattern lưu lượng (timing, frequency, payload size) ngay cả khi không giải mã được nội dung — từ đó suy ra ai đang giao tiếp với ai, khi nào, tại đâu.

- 📱 **White Noise via Continuous Nonce Rotation:** Lõi Rust phát đều đặn **Dummy Beacon** (payload ngẫu nhiên, kích thước ngẫu nhiên trong [20, 80] bytes) xen kẽ với Beacon thật theo tỉ lệ configurable (mặc định 3 Dummy : 1 Real). Nonce `R` thay đổi mỗi Beacon — kẻ quan sát không thể phân biệt Beacon thật với nhiễu trắng.
- 📱 **Sealed Sender Extended to Physical Mesh Layer:** Áp dụng Sealed Sender không chỉ ở Layer 5 (CRDT / App) mà xuống tận Layer 2 BLE: mỗi BLE packet chỉ chứa `C_trunc` (identity commitment) làm "địa chỉ gửi" — không có trường `from_node_id` dưới bất kỳ hình thức nào trong Advertising PDU.
- 💻📱 **O(1) Edge Noise Filter (trước Rust Pipeline):** Tại điểm tiếp nhận BLE, một bộ lọc Bloom Filter nhỏ (4KB) kiểm tra nhanh `C_trunc` — nếu không khớp bất kỳ entry nào trong danh bạ đã biết → Drop ngay tại tầng Edge mà không nạp vào Rust Pipeline. Chi phí lọc $O(1)$, không tiêu tốn CPU cho Dummy Beacons.
- 📱 **Static Identity Elimination trong mọi Broadcast:** Audit toàn bộ BLE Advertising PDU: nghiêm cấm xuất hiện `Device_MAC thật`, `Node_ID`, `User_ID`, `Company_ID` dưới bất kỳ encoding nào (hex, base64, protobuf field). CI pipeline tự động scan Advertising payload template để phát hiện static field trước khi merge.

### 5.10 Mesh Anti-Spam & DoS Resilience

#### Tấn công Sybil trên mạng Mesh (Chống Spam & OOM)

- 📱💻🖥️ **Fixed-Size Relay Ring Buffer:** Cố định bộ đệm dạng vòng tròn tĩnh trên Shared Memory giới hạn RAM chuyên chứa tin nhảy cóc đa chiều, ngăn chặn phình to tràn bộ nhớ (OOM).
- 📱💻🖥️ **Identity-Bound QoS & Edge Defense:** Áp ráp OPA Engine tự quy chiếu hạn ngạch tốc độ (Rate Limiting) theo định lượng tín nhiệm người dùng. Lớp bảo hệ MAC ngoại biên được xác thực bởi Sealed Sender + MLS khóa chặt yêu cầu bừa bãi.
- 📱💻🖥️ Tự động lọc các gói Data cồng kềnh qua QoS (loại trừ tệp/file/video) tại Hop số 2+ trong chế độ nhảy cóc P2P thuần túy.

#### Chống Sybil & Broadcast Storm qua mPoW (Micro Proof-of-Work Hashcash Defense)

- 📱💻🖥️ Áp dụng thuật toán SHA-256 Hashcash ép buộc thiết bị giải Nonce khớp tiền tố 12 bit 0 trước khi phát sóng tín hiệu.
- 📱💻🖥️ Thi hành cơ chế Spam Toll cưỡng chế tiêu hao năng lượng tính toán vật lý để dập tắt các truy vấn Control Plane độc hại.
- 📱💻🖥️ Giải phóng tốc độ xác thực băm với độ phức tạp $O(1)$ tại Node đầu nhận nhằm duy trì hiệu năng mạng chéo.

#### T-UUID (Time-based Rotating Service UUIDs) chống Sleep Deprivation

- 📱💻 Sử dụng hàm $HMAC-SHA256$ để băm `Mesh_Epoch_Key` cùng `Time_Slot_Index` sinh ra UUID động mỗi 5 phút.
- 📱 Cấp quyền Pre-emptive Registration cho phép Lõi Rust đăng ký trước danh sách UUID với OS Daemon (CoreBluetooth/BluetoothLeScanner) trước khi chuyển trạng thái Suspend.
- 📱 Tự động thực hiện Hardware-level Drop tại lớp Baseband nếu UUID không khớp khung thời gian (Time Window).

#### Hardware-Offloaded MAC Filtering (Bit-pattern Masking) chống Wake-up ảo

- 📱💻🖥️ Nhúng khóa xác thực SipHash-24 (4 bytes) vào trường Manufacturer Specific Data của quảng bá BLE.
- 📱 Thiết lập Bit-mask filter (ScanFilter) cho Anten Bluetooth vật lý để chỉ chấp nhận trọn vẹn các hình thái bit (Bit-pattern) hợp lệ.
- 📱 Cơ chế lọc phần cứng đè bẹp mầm mống rác chạm vào tầng phần mềm, bảo toàn 0% CPU khi có nhiễu sóng xung quanh.

#### Dynamic Quarantine & IPC Circuit Breaker (Chống nội gián)

- 📱💻🖥️ Áp đặt Rate Limiting dựa trên `Node_ID` và tần suất gửi gói tin khẩn cấp tại tầng Rust Data Plane.
- 📱💻🖥️ Xác thực chặt chẽ Sequence Counter và Timestamp bên trong payload mã hóa để tóm gọn tấn công phát lại (Replay Attack).
- 📱 Mở luồng IPC khẩn cấp để tống khứ địa chỉ MAC vật lý của kẻ tấn công vào Hardware Denylist của hệ điều hành.

#### Byzantine Quarantine & Gossip Poison Pill Protocol (Chống Phát tán Mã độc Phân tán)

> **Bài toán:** Một node bị compromised có thể phát tán CRDT event độc hại, forward payload giả mạo hoặc âm mưu phá hoại topology qua Gossip. Không có cơ chế eviction nhanh sẽ khiến toàn bộ Mesh nhiễm độc.

- ☁️📱 **Gossip Shunning Mechanism:** Khi Lõi Rust phát hiện node vi phạm (đủ bằng chứng bất thường: > 3 sai số chữ ký / 10s), phát ngay **Poison Pill packet** — một gói tin Gossip đặc biệt được ký bởi Enterprise CA — lan truyền cờ `SHUN: Node_ID` tới toàn Mesh trong ~30s.
- 💻📱 **Node_ID / MAC Blacklisting:** Lõi Rust tự động thêm `Node_ID` bị shunned vào **Local Denylist** (lưu trong SQLite WAL dưới dạng Append-Only log). Mọi gói tin BLE / Wi-Fi Direct từ địa chỉ này bị Drop tại tầng Hardware MAC Filter — không tiêu tốn CPU.
- ☁️📱 **Digital Signature-based Poison Pill Verification:** Trước khi áp dụng lệnh Shun từ Gossip, mỗi node bắt buộc xác thực chữ ký Enterprise CA trên Poison Pill packet. Node không có chữ ký CA hoặc bị hết hạn TTL (30 phút) → lệnh Shun bị bỏ qua, chống lại tấn công "False Flag" giả mạo lệnh cô lập.
- 📱 **Peer-to-Peer Isolation (Layer 2/3):** Sau khi Shun được xác nhận, Lõi Rust thông báo OS ngắt kết nối Layer 2 (BLE disconnect) và Layer 3 (xóa routing entry trong P2P routing table) đối với node bị cô lập. Node cô lập không thể reappear cho đến khi Admin revoke Shun list từ Admin Console.

#### Deterministic State Reconciliation — Đối chiếu Trạng thái Tất định (Chống Lệch Đồng bộ DAG sau Xóa DB Tạm)

> **Bài toán:** Sau khi `nse_staging.db` bị Crypto-Shredding, `hot_dag.db` của client mất đồng bộ với Mesh. Không thể replay toàn bộ DAG log từ server — quá tốn RAM và băng thông. Cần cơ chế "chỉ tải đúng phần thiếu" một cách tất định (Deterministic).

- 📱 **Hydration_Checkpoint Extraction (`Snapshot_CAS_UUID`):** Khi phát hiện DAG lệch, Lõi Rust trích xuất `{Snapshot_CAS_UUID, vector_clock_frontier}` từ bảng `hydration_checkpoints` trong `hot_dag.db`. Đây là điểm tham chiếu tất định xác định chính xác "client biết đến đâu" — không cần scan toàn bộ event log.
- 📱☁️ **State Vector Clock Summary (Lightweight Gossip Probe):** Client tạo bản tóm tắt Vector Clock (chỉ chứa `{Node_ID: max_seq_seen}` cho mỗi peer, < 2KB) và phát tín hiệu `GossipStateRequest` siêu nhẹ đến Super Nodes lân cận. Super Nodes phản hồi với tập hợp `Missing_CAS_UUIDs` — danh sách các Delta-State client chưa có.
- ☁️ **Server-side Gap Computation & Targeted Delivery:** VPS/Super Node thực hiện set difference `(current_frontier_UUIDs) \ (client_known_UUIDs)` và chỉ gửi đúng các Delta-State thiếu này. Bandwidth tiêu thụ tỉ lệ với khoảng gap, không phải tổng lịch sử DAG — $O(\text{gap})$ thay vì $O(N)$.

#### Zero-Trust Cryptographic Verification Pipeline & BFT Quarantine — Chống Malicious State Injection từ Compromised Super Node

> **Bài toán:** Super Node trung gian (bị compromise) có thể nhào nặn Delta-State trước khi relay về client — thêm backdoor CRDT event, thay đổi nội dung tin nhắn, hoặc inject rogue DAG branch. Client không thể tin tưởng bất kỳ Super Node nào.

- 📱💻🖥️ **Cryptographic Proof-of-Origin (RAM-only Verification):** Lõi Rust xác thực chữ ký số `Ed25519` của `DeviceIdentityKey` gốc (người gửi ban đầu) ngay trên vùng nhớ RAM được bảo vệ đối với từng `Delta-State` độc lập. Không một intermediary Super Node nào có thể tái ký payload với identity của người gửi gốc — mọi Delta-State bị nhào nặn sẽ fail signature verification và bị `ZeroizeOnDrop` tức thời.
- 💻☁️ **Merkle Proof Verification (Leaf-to-Root Path):** Trước khi hợp nhất bất kỳ Delta-State nào vào `hot_dag.db`, Lõi Rust đối soát độc lập toàn bộ Hash Path từ Leaf Node lên Root Hash của Segmented Merkle Tree do server cung cấp. Bất kỳ sai lệch hash nào ở bất kỳ tầng nào → kích hoạt `ZeroizeOnDrop` tiêu hủy payload tức thời trước khi chạm vào database.
- 📱🖥️ **BFT Quarantine Threshold (Byzantine Fault Tolerance Cục bộ):** Lõi Rust duy trì bảng tín nhiệm `{Super_Node_ID: malice_score}`. Mỗi lần Super Node gửi Delta-State không qua được Merkle Proof hoặc Signature Verification → `malice_score++`. Khi `malice_score ≥ f` (ngưỡng BFT tolerance, mặc định `f = 3`): tự động Blacklist MAC Address / IP, ngắt socket, và phát `GossipStateRequest` sang Super Node thay thế.

#### Gas-Metered Ephemeral Quarantine & PoM Epidemic Broadcast — Chống Sandbox Escape Zero-day từ Compromised Hardware

> **Bài toán:** Kẻ tấn công kiểm soát phần cứng có thể khai thác lỗ hổng zero-day trong WASM Sandbox để thực thi native code, chiếm quyền kiểm soát Lõi Rust, và inject trực tiếp vào `hot_dag.db` mà không qua Merkle Proof Verification.

- 📱💻🖥️ **Control Flow Integrity (CFI) & OLLVM Obfuscation:** Lõi Rust được biên dịch với CFI (Control Flow Integrity) — mỗi indirect call/jump được xác thực tại runtime, triệt tiêu kỹ thuật ROP Chain (Return-Oriented Programming) và JOP (Jump-Oriented Programming) ngay cả khi kẻ tấn công vượt qua WASM Sandbox. OLLVM Obfuscation được áp dụng ở mức compiler để làm rối binary, tăng chi phí reverse engineering.
- 📱💻🖥️ **Gas-Metered Ephemeral Validation Sandbox:** Mỗi Delta-State từ bên ngoài được "kích nổ" (detonated) bên trong một WASM Runtime partition "dùng một lần" hoàn toàn cô lập trước khi cho phép tiếp xúc với `hot_dag.db`. Sandbox tích hợp Gas-metering — mỗi instruction tiêu thụ gas quota; vượt quota → sandbox bị killed. Mọi Syscall trái phép hoặc buffer overflow trong sandbox → kích hoạt `ZeroizeOnDrop`, hủy vùng nhớ tức thời.
- 📱🖥️ **Proof of Malfeasance (PoM) Epidemic Broadcast:** Ngay khi Validation Sandbox ghi nhận hành vi khai thác, node nạn nhân lập tức: (1) đóng băng socket với node tấn công, (2) trích xuất `BLAKE3(malicious_payload)` làm PoM fingerprint, (3) phát tán PoM đa hướng qua Survival Mesh. Các node lân cận nhận PoM → đối chiếu hash của payload chúng đang nhận → nếu match → tự động Blacklist `DeviceIdentityKey` kẻ tấn công tại tầng Network Interface **mà không cần phân tích lại payload**.

#### Micro-Proof-of-Work Adaptive Throttle — Argon2id (Chống DoS Vắt kiệt Tài nguyên Mesh)

> **Nâng cấp so với SHA-256 Hashcash:** SHA-256 có thể bị GPU/ASIC giải nonce hàng loạt với chi phí thấp, không đủ ngưỡng ngăn chặn kẻ tấn công có phần cứng chuyên dụng. Argon2id yêu cầu cả CPU + RAM, phù hợp môi trường bị ràng buộc tài nguyên của Mesh.

- 📱 **Argon2id CPU-bound Challenge:** Trước khi broadcast bất kỳ Control Plane packet nào (Route Advertisement, CRDT Push, File Discovery), node phải giải một Argon2id challenge (`m=1MB, t=2, p=1`) — tốn ~50ms/challenge để ngăn spam hàng loạt, nhưng chấp nhận được với người dùng bình thường.
- 💻📱 **Deterministic Transaction Cost:** Chi phí mPoW cố định theo loại giao dịch: Mesh Announcement = 50ms, File Chunk Relay = 10ms, Emergency SOS = 0ms (miễn phí để ưu tiên cứu hộ). Lõi Rust xác thực proof tại Layer 5 với $O(1)$ mà không cần lưu state.
- 📱 **Thermal Throttling Feedback Loop:** Lõi Rust liên tục đọc giá trị nhiệt độ CPU (iOS: `ProcessInfo.thermalState`, Android: `ThermalStatus`) → nếu thiết bị đang nóng (Serious/Critical), tự động tăng Argon2id time parameter `t` thêm 1 bước, giảm gánh nặng cho tầng Data Plane.
- 💻📱 **Rate-limiting Ring Buffer:** Mỗi `Node_ID` được phân bổ một Ring Buffer 32-entry trong RAM của Lõi Rust, theo dõi timestamp của 32 gói tin gần nhất. Nếu khoảng cách trung bình `< 100ms` trong Ring Buffer → tự động Quarantine node vào Denylist tạm thời 15 phút.

#### Objective Cryptographic Proof of Malfeasance — OCPM (Chống Tấn công Vu khống / Chỉ điểm Giả)

> **Bài toán:** Trong Mesh không có Server trọng tài, kẻ tấn công có thể tung bằng chứng giả (fabricated log) hoặc vu khống node lành để kích hoạt Shun. OCPM đảm bảo mọi cáo buộc đều phải kèm bằng chứng mật mã không thể làm giả.

- 📱 **Hardware-bound Non-repudiation (Secure Enclave/StrongBox):** Mỗi sự kiện vi phạm (malformed packet, signature mismatch, ACL violation) được node phát hiện ký ngay bằng `Device_Key` đang được bảo vệ trong Secure Enclave — tạo ra bằng chứng gắn chặt với phần cứng, không thể bị giả mạo bởi bên thứ ba.
- 💻📱 **Ed25519 Digital Signature Bundling:** Toàn bộ chuỗi bằng chứng được đóng gói thành `Proof_Bundle` gồm: raw packet bytes + timestamp HLC + `Node_ID` của bên vi phạm + chữ ký Ed25519 của node phát hiện. Bundle này không thể bị tái sử dụng cho node khác vì `Node_ID` được embed trực tiếp.
- 💻📱 **Immutable Evidence Encapsulation:** `Proof_Bundle` được lưu vào SQLite WAL với cờ `READ_ONLY` ngay lập tức sau khi ghi — không thể sửa đổi hay xóa. Lõi Rust từ chối bất kỳ request nào cố truncate hoặc overwrite bảng Evidence.
- 💻📱 **Multi-party Cryptographic Attribution:** Trước khi kích hoạt Byzantine Shun, hệ thống yêu cầu **tối thiểu 2 Proof_Bundle độc lập** từ 2 node khác nhau cùng cáo buộc một `Node_ID`. Tránh False-Flag Attack chỉ từ một node tấn công đơn lẻ.

#### HLC-Epoch Temporal Binding (Chống Tấn công Phát lại Bằng chứng Cũ)

> **Bài toán:** Kẻ tấn công thu thập Proof_Bundle hoặc CRDT event hợp lệ từ epoch cũ và phát lại để kích hoạt hành vi không mong muốn (Shun giả, state rollback). Binding theo thời gian đảm bảo bằng chứng cũ bị vô hiệu hóa tự động.

- 💻📱 **Hybrid Logical Clock (HLC) Causality:** Mọi packet (CRDT event, Proof_Bundle, Shun command) phải mang `hlc_timestamp` và `vector_clock`. Lõi Rust kiểm tra: `|hlc_now - hlc_packet| < DRIFT_THRESHOLD (5s)`. Nếu packet đến trễ quá ngưỡng → `TEMPORAL_VIOLATION`, drop không process.
- ☁️📱 **MLS Epoch-bound Forward Secrecy:** Mỗi Shun command và Proof_Bundle bị ràng buộc với MLS Epoch hiện tại. Khi MLS Key Rotation xảy ra (epoch tăng), toàn bộ bằng chứng từ epoch cũ trở thành **invalid** — không thể recycled để cáo buộc trong epoch mới.
- 💻📱 **24h Temporal Validation Window:** Lõi Rust duy trì một Bloom Filter lưu `Evidence_Hash` trong 24h. Bất kỳ `Proof_Bundle` có hash đã tồn tại trong Bloom Filter → từ chối ngay với lỗi `EVIDENCE_REPLAYED`. Bloom Filter tự xóa sạch mỗi 24h để tránh tích lũy bộ nhớ.
- 📱 **Monotonic Hardware Counter Binding:** Trên iOS (Secure Enclave), mỗi `Proof_Bundle` được gắn thêm giá trị từ **Monotonic Counter** của Secure Enclave — bộ đếm phần cứng không thể đặt lại (rollback-proof). Nếu Counter trong Proof_Bundle thấp hơn giá trị hiện tại của thiết bị phát hiện → cờ `COUNTER_ROLLBACK`, reject.
- 📱 💻 🖥️ **Physical Time Bounded Drift Truncation (± 5s):** Đóng gói biên độ Bounded Drift Tolerance loại bỏ bóc tách Time-Drift Attack đánh sập HLC Timestamp.
- 📱 💻 🖥️ **Merkle DAG Topological Override:** Triển khai cưỡng chế DAG Topological Enforcement niêm phong trật tự đồ thị dữ liệu trước âm mưu tua ngược thời gian.
- 📱 💻 🖥️ **Byzantine_Fault Hash-Chain Validation:** Xác thực chuỗi băm chống nhiễu loạn Byzantine chặn đứng các Node phát hành Timestamp giả mạo.

#### Quản lý Danh tính & Hạn mức Mesh (Hardware-bound Offline Trust Tokens)

- 📱💻🖥️ Neo chặn chữ ký số Ed25519 trực tiếp vào phần cứng (Secure Enclave/StrongBox) bảo vệ định danh mạng Mesh nguyên thủy.
- 📱💻🖥️ Ràng buộc bước kiểm chứng Admin_Public_Key cấp phát Token niềm tin chuyên biệt cho từng phiên Epoch di động.
- 📱💻🖥️ Tích hợp chu trình Token-burning đánh dấu trực tiếp vào gói tin Mesh nhằm ngắt ngọn tần suất Broadcast Spam.

#### Chốt chặn Cách ly & Lọc gói tin sớm (3ms Early-Drop Quarantine Filter)

- 📱💻🖥️ Đẩy mạnh khả năng Rust Core Early-Drop tiêu hủy gói tin rác ngay trên RAM trước khi chạm vào UI hoặc tiến trình giải mã E2EE.
- 📱💻🖥️ Cấu trúc In-memory Blacklist thông qua Bloom Filter hoặc Hash Map bóng ma hóa "Ghosting" mọi truy cập từ thiết bị lây nhiễm.
- 📱💻🖥️ Điều tiết vòng lặp Leaky Bucket tự động làm mới nhịp Reset danh sách đen định kỳ theo thời gian thực.

#### Bảo vệ Tài nguyên & Chống DoS (Zero-Context Switch DoS Resilience)

- 📱💻🖥️ Xóa sổ gói tin xâm nhập ngay tại vách nối Kernel/Rust Interface triệt tiêu hoàn toàn chi phí Context Switch lên ranh giới User-space.
- 📱💻 Quản trị vũng nhớ Memory Arena ép dung lượng tiêu thụ pin xuống mức < 0.01% kể cả khi bị dội bom hàng vạn gói tin rác.
- ☁️📱💻🖥️ Đính kèm chốt xác thực VOPRF/Nullifier phong tỏa tận gốc rễ biến thể tấn công Replay trong cấu trúc phi tập trung.

---

### 5.10.1 Local Tombstone Vacuum & Merged Vector Clock (Toàn vẹn DAG & Chống Mất dữ liệu)

> **Bài toán:** Khi message bị xóa, entry DELETE (Tombstone) tích lũy mãi trong DAG mà không bị dọn dẹp, gây phình to database. Đồng thời, nếu Tombstone bị xóa quá sớm, một node offline có thể replay event DELETE đó như một sự kiện mới.

- 💻📱🖥️ **Merged_Vector_Clock (Causal Root Anchoring):** Lõi Rust duy trì một `Merged_Vector_Clock` (MVC) hợp nhất từ Vector Clock của tất cả peer đã kết nối. MVC đại diện cho trạng thái nhân quả tối thiểu mà toàn bộ DAG phải biết. Tombstone chỉ được Vacuum khi `tombstone.clock ≤ MVC` — tức là toàn bộ peer đã xác nhận biết về sự kiện xóa này.
- 📱 **Zero-Byte Stub Transformation (Chống Replay Attack):** Thay vì xóa Tombstone hoàn toàn, sau Vacuum, Lõi Rust chuyển Tombstone thành **Zero-Byte Stub** — một record chỉ giữ `(entity_id, hlc_timestamp, type=DELETED)` không có payload. Nếu có node cố replay DELETE event, Stub sẽ trả về `ALREADY_TOMBSTONED` thay vì xử lý như event mới.
- 📱 **Garbage Collection (GC) dựa trên Mesh ACK:** Lõi Rust chỉ khởi động GC Tombstone sau khi: (1) nhận đủ ACK từ ≥M peer trong Mesh Mode, HOẶC (2) thiết bị kết nối lại Server và nhận xác nhận global sync. Không bao giờ GC khi đang trong trạng thái Partitioned (không có ACK quorum).
- 📱💻 **Proactive 7-Day Hot DAG Eviction (App Size < 300MB):** `hot_dag.db` chỉ giữ tin nhắn/metadata trong **7 ngày gần nhất**. Lõi Rust chạy GC scheduler mỗi 24h (khi app background + máy đang sạc): chunk dữ liệu cũ hơn 7 ngày được AEAD-encrypt → push lên `cold_state.db` trên VPS → `DELETE + VACUUM` local. Mục tiêu: App size giữ < **300MB** trên mobile. *Không dùng cơ chế "chờ đến khi đầy" như trước.*
- 📱 **Zero-Byte Stub Aggressive Eviction (File/Media):** File và ảnh trên Mobile chỉ tồn tại dưới dạng **Zero-Byte Stub** (thumbnail cực thấp + metadata). Dữ liệu gốc nằm trên VPS. Khi user tap vào → On-Demand Fetch → decrypt → throw vào RAM (không lưu file vật lý). Sau 30 phút không tương tác → Stub evict RAM, không còn dấu vết local.

#### §Enclave Remote Attestation (DCAP) — Client-to-Enclave E2EE (Elite License)

> **Yêu cầu:** Đối với gói Elite, `.tapp Heavyweight` và Local LLM chạy trên VPS Enclave. Client phải xác minh VPS Enclave là sạch (chưa bị IT Admin can thiệp) và chống Side-Channel Attacks/Queue leakage.

- ☁️🗄️ **Software-based Attestation & Ephemeral Kyber-Hybrid KEM:** Xác minh tính vẹn toàn VPS thông qua quy trình đối soát Certificate và App Attestation. Sau khi verify thành công, kênh truyền được khóa bằng ☁️ Hybrid PQ-KEM (X25519 + Kyber768), thiết lập liên kết TLS chống lại mối đe dọa từ máy tính lượng tử trong tương lai.
- 📱💻 **PFS (12h TTL Key Rotation):** Keys sinh ra từ Kyber-Hybrid có vòng đời cực ngắn: 📱💻 PFS với 12h TTL Key Rotation. Hết hạn 12h, Client phải drop connection và force Remote Attestation từ đầu để tái lập Session KEM ngẫu nhiên.
- ☁️ **Client-to-Enclave Session Key:** Khóa derivation hoàn toàn độc lập với `Company_Key`. Enclave không nhận được root key mà chỉ nhận cipher data đã Masked PII. Thất bại attestation → alert `ENCLAVE_ATTESTATION_FAILED`.
- ☁️ **ZeroizeOnDrop trong Enclave:** Sau khi Enclave hoàn thành computation, tất cả plaintext data trong protected memory được gọi hàm `ZeroizeOnDrop` — Enclave không duy trì bất cứ artifacts nào trên memory.
- 📱💻 **Queue Isolation (Hardware-Bound Ephemeral Encryption):** Trước khi data bắn lên Enclave, mọi log pending tại thiết bị (nằm ở `tapp_egress.db`) đều chịu sự giám sát của `Tapp_Queue_Key`. Đây là Ephemeral Encryption (📱💻 AES-256-GCM One-time key) bị ràng buộc phần cứng bởi 📱 iOS Secure Enclave hoặc 📱 Android StrongBox. Ngay khi đẩy đi thành công, phần cứng hủy khóa, biến các queue chunks thành dead ciphertext.
- ☁️ **Enclave Throughput:** RTT overhead của Remote Attestation ~200ms (1 lần/12h). Mỗi compute request cộng thêm ~20-50ms RTT mượt mà, phù hợp truy vấn thời gian thực.
- 📱 **Phân loại .tapp (Mobile vs VPS Enclave):**
  - `type: "lightweight"` trong `manifest.json` → Lõi Rust execute locally trên Mobile WASM Sandbox (`wasm3` / `wasmtime`).
  - `type: "heavyweight"` → Lõi Rust tự động route Egress tới VPS Enclave (require Elite License). Nếu không có Elite License → `.tapp` hiển thị `"Tính năng này yêu cầu TeraChat Elite"` và disable.

- 💻📱🖥️ **Unidirectional State Sync (Rust Core → UI):** Toàn bộ cập nhật DAG (kể cả Vacuum/Stub) chỉ chảy theo một chiều từ Lõi Rust xuống UI Native. UI không được phép gửi ngược state lên Rust Core — đảm bảo Rust Core là single source of truth, không có UI state pollution.

### 5.10.2 Peer-Assisted Epoch Re-induction — MLS TreeKEM (Chống Mù Mật mã Sau Đồng bộ)

> **Bài toán:** Thiết bị offline trong thời gian dài có thể bị bỏ lại ở MLS Epoch cũ sau nhiều lần Key Rotation. Thiết bị không thể tự giải mã message mới vì không có `Epoch_Key` hiện tại — kể cả khi Server đã online trở lại.

- 📱💻🖥️ **MLS TreeKEM Add_Member Handshake (Epoch Rotation):** Khi thiết bị reconnect, Lõi Rust gửi `Re-Add_Member` proposal theo chuẩn MLS TreeKEM — không cần Server làm trung gian trong Mesh Mode. Peer đang online nhận proposal, thực hiện Commit → sinh ra `Welcome_Packet` mang `Epoch_Key` hiện tại được mã hóa cho thiết bị mới reconnect.
- 📱💻🖥️ **Wake-up Beacon ký bằng Device_Identity_Key (Hardware Root of Trust):** Thiết bị phát tín hiệu `WAKEUP_BEACON` qua BLE, ký bằng `Device_Identity_Key` cố định trong Secure Enclave. Peer xác thực beacon này để đảm bảo thiết bị reconnect là hợp lệ trước khi gửi `Welcome_Packet` — tránh kẻ tấn công giả mạo thiết bị offline để lấy `Epoch_Key`.
- 📱💻🖥️ **Welcome Packet Encryption via ECIES/Curve25519:** `Welcome_Packet` được encrypt bằng ECIES sử dụng Curve25519 Public Key của thiết bị target (lấy từ MLS KeyPackage đã đăng ký). End-to-end: chỉ thiết bị đúng mới giải mã được, peer relay không thể đọc nội dung.
- 📱💻🖥️ **Peer-to-Peer Identity Validation:** Sau khi nhận `Welcome_Packet`, Lõi Rust xác thực `Device_Identity_Key` qua cross-reference với `Enterprise_CA` certificate đã lưu local. Nếu Certificate hết hạn hoặc đã revoked (Shun List) → từ chối induction, yêu cầu Admin re-provision.

### 5.11 WebRTC Blind Relay (TURN)

- 📱💻🖥️ **Signaling:** Trao đổi SDP qua kênh chat MLS (E2EE channel).
- ☁️ **Transport:** SRTP — E2EE Audio/Video. TURN Server chỉ relay UDP mã hóa — không nắm Key.
- ☁️ **HA:** Keepalived Floating IP, failover 3 giây. Sizing: 1 Node ~ 50 HD streams, 4 vCPUs, 8GB RAM, 1 Gbps.
- ☁️ **Hybrid STUN qua Private Cluster:** Vượt AP/Client Isolation bằng WebRTC Data Channel mồi từ VPS nội bộ.

### 5.4 OOB Mesh Ratchet (Double Ratchet vs Data Mule)

- 📱💻 Phân tách Data Plane State Machine để chống lệch con trỏ (ratchet out-of-sync) trên các thiết bị.
- 📱💻 Cấu hình `Online_Ratchet_Tree`: Ràng buộc định tuyến qua TCP/WebSocket. Xoay khóa TLS/MLS liên tục, hardcode `Max_Gap = 2000` messages.
- 📱💻 Cấu hình `OOB_Mesh_Ratchet`: Bypass luồng online nếu `Is_Mesh = True`. Sinh `Mesh_Session_Key` qua quá trình X3DH đã thiết lập trước.
- 📱💻 Thiết lập CRDT Vector Clock. Khi reconnect Internet, trigger hàm Rust hợp nhất (merge) Mesh State vào Online State. Zeroize RAM ngay sau khi merge để chống OOM do jump KDF.
- 📱 💻 **Noise Protocol Framework & Double Ratchet (PFS):** Triển khai Perfect Forward Secrecy bảo vệ Device_Key trước rủi ro trích xuất khóa qua Spectre/Meltdown v2 — mỗi phiên sinh một luồng Ephemeral Key hoàn toàn mới.
- 📱 💻 **X25519 Ephemeral Keypair in RAM:** Cấp phát cặp khóa X25519 ngắn hạn độc lập trên heap RAM, không lưu vào disk hay Secure Enclave, ngắt hoàn toàn attack surface vật lý.
- 📱 💻 **Ephemeral Key Zeroization (0x00):** Cưỡng chế ghi đè toàn bộ vùng nhớ khóa phiên bằng byte 0x00 ngay sau khi phiên kết thúc, triệt phá khả năng phục hồi qua cold-boot hay DMA dump.

### 5.12 Phân xử Phi tập trung Hậu phân mảnh mạng (Tie-Breaker Hash Election)

> **Bài toán:** Khi mạng bị phân mảnh (Split-brain) và sau đó kết nối lại, cần có một cơ chế bầu chọn tự động (Leader Election) để quyết định ai là người điều phối việc merge dữ liệu mà không cần sự can thiệp của Server trung tâm.

- 📱💻🖥️ **Tie-Breaker Hash Election (Bầu cử Dictator Tất định):** Sử dụng BLAKE3 Hashing để định danh trọng số Node. Node có mã băm cao nhất (Max Hash) sẽ được thăng cấp làm Merge Dictator điều phối quá trình sáp nhập. Quyết định này là tất định (deterministic) trên mọi node, không cần vòng lặp vote tốn thời gian.
- 📱💻🖥️ **Failover Cơ chế Listener Kế nhiệm:** Giám sát liên tục trạng thái của Dictator. Nếu Dictator rớt mạng (timeout), node có trọng số Hash cao thứ hai sẽ lập tức takeover vai trò Listener kế nhiệm trong thời gian <10ms, đảm bảo tiến trình sáp nhập không bị gián đoạn.

### 5.13 Rust Asynchronous Concurrency Architecture (Ngăn chặn Đóng băng UI / ANR)

> **Bài toán:** Khi nhận và sáp nhập hàng lượng lớn sự kiện DAG từ Mesh, nếu tải quá nặng sẽ gây treo UI (ANR trên Android, khựng frame trên iOS). Cần phân rã triệt để luồng tính toán lõi ra khỏi luồng render.

- 📱💻🖥️ **Tokio Runtime Xử lý IPC/IO (<5ms/loop):** Lõi Rust nhúng bộ lập lịch Tokio async runtime để hứng luồng sự kiện I/O và IPC siêu nhẹ. Giao tiếp qua SharedArrayBuffer (Desktop) hoặc JSI (Mobile), mỗi vòng lặp Event Loop chỉ chiếm <5ms, không bao giờ block.
- 💻🖥️ **Rayon Thread Pool Thực thi Tính toán DAG Đa lõi:** Đối với các tác vụ sáp nhập CRDT phức tạp ($O(N \log N)$), Lõi Rust đẩy xuống Rayon xử lý song song trên nhiều CPU bounds. Tránh nghẽn một nhân, tối đa hóa thông lượng thuật toán duyệt đồ thị.
- 📱💻🖥️ **Hardware Crypto Acceleration (AES-NI / ARM NEON):** Luồng MLS Crypto Worker được phân lập riêng biệt, truy xuất trực tiếp tập lệnh phần cứng để mã hóa/giải mã. Không tranh chấp tài nguyên với luồng xử lý I/O và UI rendering.

### 5.14 Deterministic State Convergence (Hội tụ Trạng thái Toàn mạng lưới)

> **Bài toán:** Trong môi trường phân tán P2P, các bản cập nhật có thể đến không theo thứ tự. Tới cuối cùng, toàn bộ các node bắt buộc phải hội tụ về một trạng thái thống nhất một cách tuyệt đối (Strong Eventual Consistency).

- 📱💻🖥️ **Hybrid Logical Clocks (HLC) & Hash(Node_ID) Last-Write-Wins:** Kết hợp đồng hồ lai HLC và hàm băm `Hash(Node_ID)` làm cơ chế phân xử LWW (Last-Write-Wins) khi xảy ra xung đột đồng thời. Đảm bảo kết quả merge luôn giống hệt nhau trên mọi thiết bị tham gia.
- 📱💻🖥️ **Ed25519 Digital Signature Xác thực Bản vá Sáp nhập:** Mỗi thao tác thay đổi state (merge patch) đều phải kèm chữ ký mã hóa Ed25519 của người tạo. Các node khác xác thực chữ ký trước khi apply vào DAG cục bộ, ngăn chặn chèn trạng thái độc hại.
- 📱💻🖥️ **TreeKEM Update Path Tái cấu trúc Cây khóa Epoch N+2:** Sau khi trạng thái DAG hội tụ thành công, Lõi Rust phát yêu cầu Update Path để tái cấu trúc lại nhóm bảo mật MLS ở Epoch mới (N+2), phục hồi tính Forward Secrecy kịp thời hậu phân mảnh mạng.

### 5.15 Split-Brain Đa cấp và Tụt hậu Epoch (Causal Fast-Forward & Frontier Discovery)

#### Xử lý Xung đột Não lặp (Split-Brain Reconciliation)

- 📱💻🖥️ **Deterministic Causal Merge:** Quy chuẩn lai Hybrid Logical Clocks (HLC) song hành cùng Vector Clocks neo giữ tính bền vững nhân quả (Causality) dẫu phần cứng đồng hồ của hệ thống bị sai lệch thời gian nghiêm trọng.
- 📱💻🖥️ Đóng chốt chu vi phân xử qua thuật toán Tie-breaker `Hash(Node_ID)` Linearization, chọn duy nhất đường thẳng một chiều thông suốt có tính tất định tuyệt đối để dàn xếp hội tụ mạng DAG.
- 📱💻🖥️ **MLS Epoch Stitching:** Khởi chạy Merge Commit bằng thủ tục O(log n) trực tiếp thông qua cây TreeKEM, thiết lập mới nhất thể Kỷ Nguyên (Epoch) kiên cố bao trùm toàn bộ nhóm hậu sự cố chẻ đảo.
- 📱 Triển khai O(1) Memory Metadata Exchange qua BLE/Wi-Fi Direct hỗ trợ Asymmetric CRDT State-Squashing.
- 📱 Giải quyết Split-Brain lập tức bằng LWW-Element-Set kết hợp HLC_Timestamp & Node_ID Lexicographical Tie-Breaker.
- 📱 Áp dụng Lazy Evaluation với Zstandard Orphan_Blob để tối ưu bộ nhớ tải P2P trong môi trường Mobile-Only.

> **Bài toán:** Khi mạng tách làm nhiều đảo (Split-brain), mỗi đảo tiến hóa state DAG và xoay khóa MLS Epoch độc lập. Khi nối lại, các node bị tụt hậu quá sâu không thể giải mã lịch sử chặn giữa và phân xử xung đột.

- 📱💻🖥️ **Gossip Protocol Lan truyền Vector Clock (Frontier Discovery):** Các node liên tục trao đổi Vector Clock qua giao thức Gossip để nhận diện "Frontier" (biên giới cập nhật mới nhất) của các hòn đảo mạng.
- 📱💻🖥️ **Xác định Hash_Frontier Cao nhất:** Thông qua việc so sánh độ ưu tiên của Hybrid Logical Clocks (HLC) giữa các đảo, hệ thống tìm ra `Hash_Frontier` mang Vector Clock trội nhất làm mốc hội tụ.
- 📱💻🖥️ **Cryptographic Fast-Forward nhảy vọt Epoch N+2:** Cho phép các node bị tụt hậu (từ Epoch N-k) bỏ qua việc giải mã tuần tự từng tin nhắn chặn giữa. Thay vào đó, node tái đồng bộ DAG state mới nhất (Fast-Forward), sau đó trực tiếp hấp thụ `Update_Path` của MLS TreeKEM để cập nhật ngay lập tức lên Epoch hiện tại (N+2).

### 5.16 Phân nhánh Dữ liệu Ghost Merge (Tie-Breaker V2)

> **Bài toán:** Quá trình merge hai nhánh DAG khổng lồ (Ví dụ: Nhánh 1 từ Desktop, Nhánh 2 từ Mobile) đòi hỏi năng lực tính toán cực lớn. Giao phó cho 1 node yếu có thể làm OOM toàn bộ tiến trình.

- 📱💻🖥️ **Tie-Breaker Hash Election (Bầu Leader V2):** Thay vì bầu 1 leader duy nhất cho toàn mạng, Tie-Breaker V2 dùng thuật toán BLAKE3 deterministic để bầu chọn *cục bộ* giữa 2 nhánh đang merge. Node chịu tải sẽ là node có năng lực phần cứng phù hợp nhất theo phân bổ Hash.
- 📱💻🖥️ **Deterministic Merge (Sáp nhập Nhánh N & N+2):** Thuật toán tự động sáp nhập Nhánh 1 (Epoch N+2) và Nhánh 2 (Epoch N) dựa trên quan hệ nhân quả (causality) của đồ thị DAG, loại bỏ hoàn toàn các event trùng lặp (Idempotent Merge).
- 💻🖥️ **Rayon Thread Pool Xử lý Đa luồng:** Phân rã tiến trình duyệt đồ thị DAG và tính toán HLC conflict resolution xuống Thread Pool của Rayon. Giúp tận dụng 100% tài nguyên CPU đa nhân trên Desktop/Server, tránh nghẽn luồng chính (Main Event Loop) của Lõi Rust.

### 5.17 Bảo toàn Tính vẹn toàn Audit Trail (Append-Only Immutable Hash Chain)

> **Bài toán:** Các cuộc gộp nhánh DAG (merge) thường phải tổ chức lại lịch sử. Kẻ tấn công có thể lợi dụng lúc merge để chèn, xóa hoặc thay đổi (rollback) nhật ký thao tác (Audit Log) nhằm che giấu dấu vết.

- 📱💻🖥️ **Append-Only Tuyệt đối không Rollback:** Mọi sự kiện (Tin nhắn, Xóa, Sửa, Rời nhóm, Đổi quyền) đều là các mắt xích gắn chặt vào chuỗi băm (Hash Chain) một chiều. Cơ chế Append-Only cấm tuyệt đối việc rollback hay chỉnh sửa dữ liệu quá khứ.
- 📱💻🖥️ **Cấu trúc DAG Tham chiếu Phân nhánh (Tombstone References):** Các phân nhánh đứt gãy hoặc sự kiện bị xóa không bao giờ bị xóa bỏ vật lý khỏi DB ngay lập tức. Chúng được lưu dưới dạng các nút tham chiếu mới (Tombstone Stub) móc nối vào DAG, bảo toàn hoàn hảo đường đi của dữ liệu.
- 📱💻🖥️ **Byzantine Fault Tolerance Hồi phục Frontier Hợp lệ:** Mạng duy trì một "Frontier" hợp lệ và có khả năng tự chữa lành (Self-healing). Mọi thao tác dối trá bẻ cong lịch sử sẽ lập tức bị mạng lật tẩy và reject thông qua việc xác thực bắt buộc bằng chữ ký Ed25519 của tác giả trên từng mắt xích.
- ☁️ **Ed25519 Cryptographic Signature Audit Log (ISO 27001 A.10.1.1):** Ký số bất đối xứng Ed25519 trên mọi entry nhật ký Audit Log — đảm bảo tính nguyên vẹn tuyệt đối của mọi sự kiện, chống giả mạo và thao túng lịch sử Audit bởi Insider Threat.
- ☁️ **HLC Real-time Time-stamping:** Gắn nhãn thời gian HLC (Hybrid Logical Clock) thời gian thực cho mọi entry nhật ký, đảm bảo thứ tự nhân quả bất biến dù Server clock bị thao túng.

### 5.18 Chống Rò rỉ `Company_Key` qua WASM Sandbox — Kiến trúc Data Diode (ISO 27001 A.6.1.2 / A.13.1.3)

> **Bài toán:** Mini-App (.tapp) chạy trong WASM Sandbox là mã nguồn bên ngoài (3rd party). Nếu cấp thẳng `Company_Key` vào Sandbox để Mini-App tự giải mã Data, mã độc có thể lén lút tuồn Key ra ngoài. Kiến trúc **Host-Binding Proxy** (để Lõi Crypto làm Forward Proxy cho .tapp) bị loại bỏ — vi phạm § Segregation of Duties (A.6.1.2): Lõi mật mã không parse HTTP/network traffic của bên thứ ba.

#### §4.4 Zero-Knowledge Memory Protection (RAII ZeroizeOnDrop)

- 📱💻🖥️☁️ **Memory Zeroization purely via RAII:** Sử dụng `zeroize::ZeroizeOnDrop` để tiêu hủy tuyệt đối plaintext khỏi heap/stack ngay khi struct trượt khỏi scope. Chấm dứt việc cưỡng ép khóa tệp hoán đổi (Disable Swap) và loại bỏ yêu cầu cờ CAP_IPC_LOCK (mlock) nhằm đảm bảo khả năng triển khai trên mọi môi trường VPS/Server phổ thông.
- 📱 **Mobile & Cloud Optimization:** Kết hợp `kCFAllocatorMallocZone` (iOS) để che giấu allocation khỏi Crash Dump. Window rò rỉ RAM < 5ms.
- 📱💻🖥️ **ZeroizeOnDrop (Bắt buộc cho mọi platform):** Trait `ZeroizeOnDrop` là hard requirement. Mọi struct chứa key material phải implement trait này. Nếu không: CI/CD pipeline fail build.
- 💻 📱 🖥️ **sqlite3_vfs Custom Wrapper (Ephemeral VFS RAM-Drive & Memory Locking):** Triển khai `sqlite3_vfs` tùy chỉnh định hướng toàn bộ I/O vào RAM-Drive (Volatile Memory) kết hợp Memory Locking — loại bỏ hoàn toàn rủi ro Forensic Extraction khai thác qua NAND Wear-Leveling (ISO 27001 A.8.3.2).
- 💻 📱 🖥️ **mmap() MAP_ANONYMOUS | MAP_PRIVATE Volatile Memory:** Dữ liệu SQLite được neo thẳng vào RAM qua mapping ẩn danh Private. Đảm bảo DB sống 100% trên bộ nhớ khả biến mà không dây dưa tới physical disk blocks.
- 💻 🖥️ **ZeroizeOnDrop Anti-Swap/Page-out:** Khóa chặt phân vùng RAM chứa VFS này bằng `ZeroizeOnDrop` ngay lập tức để OS tuyệt đối không Swap/Page-out DB xuống Disk.
- 💻 **Linux / Android memfd RAM-Drive:** Tạo vùng nhớ vô danh `memfd_create()` qua libc — DB session không bao giờ chạm đến NAND và biến mất khi tiến trình kết thúc.
- 💻 📱 **macOS / iOS MAP_ANON | MAP_SHARED:** Lật ngược giới hạn Sandbox bằng mmap anonymous ẩn giấu DB trong RAM Volatile, chặn đứng đường tấn công Forensic qua iTunes Backup.
- 🗄️ **ZeroizeOnDrop Hardware Memory Purge:** Kết hợp `ZeroizeOnDrop` RAII với tín hiệu phá hủy phần cứng (Secure Enclave Wipe) thực hiện purge tầng vật lý, triệt phá mọi dấu vết plaintext trên DRAM ngay cả khi bị cold-boot.

#### Data Diode Architecture — Tách vật lý Crypto Core khỏi .tapp Network

> **Nguyên tắc:** Lõi Rust = **Producer** (đẩy data đã mask vào .tapp). Lõi Rust = **KHÔNG BAO GIỜ Consumer** (không hứng network payload từ .tapp). Một chiều tuyệt đối.

```text
[Lõi Rust - Crypto Core] ──Push Masked Data──▶ [WASM Sandbox .tapp]
                                                          │
                                            (không có callback ngược)
                                                          │
                                              Write ──▶ [Egress_Outbox]
                                                          │
                               [tera_egress_daemon / OS Background Service]
                                   (Separate process, không share memory với Lõi Rust)
                                                          │
                                          OPA DLP Check + Hash Verify
                                                          │
                               URLSession (iOS) / Cronet (Android) / HTTP (Desktop)
                                                          ▼
                                                    Internet / Partner API
```

- 📱💻🖥️ **WASM Air-Gap (No wasi-sockets):** `.tapp` bị tước vĩnh viễn `wasi-sockets`. Không có FFI socket binding. Không có raw TCP. Không có DNS resolution. Sandbox "mù, câm, điếc" về network — hoàn toàn.
- 📱💻🖥️ **Egress_Outbox (Shared Memory Ring Buffer — 2MB max):** `.tapp` ghi kết quả vào `Egress_Outbox` — một vùng ring buffer chia sẻ 1 chiều (Write-only từ phía .tapp, Read-only từ phía Egress Daemon). Giới hạn cứng **2MB** để ngăn buffer overflow attack từ .tapp. Vượt 2MB → Outbox sealed, `.tapp` instance terminate.
- 📱 **Mobile Egress — OS Background Service:** `URLSession` (iOS) / `Cronet` (Android) chạy như OS-level background service **độc lập** với Lõi Rust process. Service đọc Outbox, verify BLAKE3 hash đối chiếu bản gốc Lõi Rust cấp, quét OPA DLP Policy, rồi dispatch HTTP request. Nếu hash sai lệch → `EXFILTRATION_ATTEMPT_DETECTED` → drop + audit log Ed25519 signed.
- 💻🖥️ **Desktop Egress — `tera_egress_daemon` (Least Privilege):** Micro-process `tera_egress_daemon` chạy ở user space với privilege `nobody` (Linux) / Restricted SID (Windows). Không share memory heap với Lõi Rust. Lõi Rust → Egress_Outbox qua named pipe. Daemon đọc, OPA check, gọi `reqwest` với TLS HPKP.
- ☁️ **Cloud/Server Egress — Multi-process Isolation:** `.tapp` trên Server gửi request mTLS cục bộ qua Named Pipe sang Egress Daemon biệt lập. Daemon check OPA policy và route ra Internet. Loại bỏ Envoy Sidecar để giảm footprint tài nguyên.
- 🗄️ **BLAKE3 DLP Hash Chain:** Trước khi Lõi Rust đẩy dữ liệu vào Outbox, tính `BLAKE3(masked_payload)` và lưu trong protected registry. Egress Daemon tính lại hash của Outbox content trước khi send — mismatch → block + alert. Ngăn `.tapp` nhồi thêm Company_Key vào payload.

#### Dual-Engine WASM Compilation (Cross-Platform JIT/AOT)

> **Xung đột W^X (Write XOR Execute):** iOS cấm JIT hoàn toàn. Android/Desktop cho phép JIT nhưng có attack surface. Giải pháp: Dual-Engine.

- 📱 **iOS — `wasm3` Interpreter + CoreML AOT:** `.tapp` logic chạy qua `wasm3` (interpreter thuần túy, không JIT — pass Apple App Store review). AI Model nặng (embedding, NLP) được pre-compile thành `.dylib` với `CoreML Compiler` — biên dịch sẵn, không runtime JIT. Overhead: +15-20ms latency cho `.tapp` execution — chấp nhận để đổi lấy 100% compliance.
- 📱 **Android — `wasmtime` JIT (Cranelift backend):** Android cho phép JIT với W^X protection. `wasmtime::Config::new().cranelift_opt_level(OptLevel::Speed)` — JIT nhưng có sandbox CFI.
- 💻🖥️ **Desktop (Tauri) — `wasmtime` JIT:** JIT thực thi trong sandbox người dùng, chặn đứng các nỗ lực RCE thông qua Application-level CFI. Loại bỏ Seccomp-BPF filters để tối ưu khả năng tương thích kernel.

### 5.19 Shadow DAG Protocol & Conflict Resolution

- ☁️🗄️ **Shadow DAG Protocol:** Thay vì Force-Merge khi có xung đột, Lõi Rust triển khai kiến trúc "Nhánh Bóng" (Shadow Branching). Lệnh PROPOSE_CHANGE được khởi tạo thay vì UPDATE, chứa payload: [Encrypted_Delta_Content] + [Index_ID] + [Ed25519_Signature].
- 📱💻 **Cryptographic Non-Repudiation (Chống chối bỏ):** Mọi hành động "Accept" hay "Reject" trên một Shadow Node bắt buộc phải được ký bằng DeviceIdentityKey (nằm trong Hardware Enclave). Không một ai có thể giả mạo quyết định gộp dữ liệu.
- ☁️ **Tamper-Proof Audit Trail:** Trạng thái gộp cuối cùng kèm chữ ký số được đẩy vào Append-Only Log trên máy chủ để phục vụ thanh tra tuân thủ (Admin/CISO có thể truy vết người phê duyệt).
- ☁️🗄️ **Server-Side Proposal Aggregation (SSPA):** Gánh nặng lưu trữ các Shadow Node (PROPOSE_CHANGE) được đẩy hoàn toàn cho VPS. VPS đóng vai trò là "Bộ đệm xung đột" (Conflict Buffer), tách biệt hoàn toàn khỏi Local Client DB.
- ☁️ **Token Bucket Group-Based Rate Limiting & Edge-Level Malicious Packet Dropping:** VPS duy trì Token Bucket cho mỗi Index_ID. Khi nhận gói PROPOSE_CHANGE, VPS kiểm tra tần suất. Nếu vượt ngưỡng (vd: 50 Đề xuất/phút), VPS rớt (drop) gói tin ngay tại biên mạng (Edge), bảo vệ thiết bị khác khỏi tấn công DoS bằng Shadow DAG.
- 📱 **Mesh Mode Offline Constraint & DAG Fragmentation Prevention:** Nếu thiết bị đang ở trong Mesh Mode không có tín hiệu mạng chạm tới VPS, Lõi Rust tự động vô hiệu hóa quyền Editor và Commenter. Trạng thái UI chuyển sang "Read-Only (Offline)" để đảm bảo không xảy ra phân mảnh DAG diện rộng mà Server không thể tổng hợp.

### 5.20 Streaming Cryptography & Memory Bounds — Large File Transfer (10GB+)

### 5.21 Adaptive Payload Gating — 3-Tier Spatial Connectivity (Cổng lọc Dữ liệu Tương thích)

> **Kiến trúc:** Lõi Rust tích hợp `Network_State_Machine` liên tục đo lường **RSSI** (Cường độ tín hiệu), **RTT** (Độ trễ vòng) và **Protocol** (BLE/Wi-Fi/TCP) để tự động phân loại kết nối vào 1 trong 3 Tier. **Nguyên tắc bất biến:** Khả năng vật lý quyết định Đặc quyền dữ liệu — không UI, không người dùng có thể bypass.

#### Per-Platform Gating Rules

- 🗄️ **Server/Cloud (Tier 1 — Always Full):** Bỏ qua Payload Gating. Route toàn bộ luồng chunking 2MB tiêu chuẩn. Throughput 300–500MB/s.
- 💻🖥️ **Desktop/Laptop (Tier 2/3 — Relay Node):** Desktop được thăng cấp làm **Relay Node**. RAM lớn cho phép Desktop nhận File (< 10MB) từ Mobile ở Tier 2, lưu vào `hot_dag.db`, giữ đó cho đến khi mạng Tier 1 phục hồi. Desktop không bị cắt giảm tính năng ở Tier 2 — chỉ Mobile áp dụng Gating nghiêm.
- 📱 **Android (Tier 2 — Tactical Mesh):** Sử dụng `WifiP2PManager` thiết lập kênh 250Mbps cục bộ. Cho phép: Text + Voice AMR-NB + File < 10MB. Từ chối: Video Stream + File nặng. Codec tự động hạ từ Opus 128kbps → AMR-NB 4.75kbps.
- 📱 **iOS (Tier 2 — AWDL Unstable):** Sử dụng `Network.framework` kết hợp Apple AWDL. **Nợ kỹ thuật:** Băng thông AWDL không ổn định — Lõi Rust phải liên tục monitor `TCP window_size`. Nếu `window_size < 64KB` trong 3 giây liên tiếp → tự động fallback về BLE (Tier 3).
- 📱💻 **Cross-Platform Tier 3 — Survival Overlay:** Lõi Rust kích hoạt nén cực độ: Tin nhắn văn bản được đóng gói vào BLE Advertisement Packet < 500 bytes (OLLVM Obfuscation + Delta CRDT payload). Mọi con trỏ trỏ tới File/Voice trong Queue bị Drop ngay lập tức. Trạng thái đánh dấu `PENDING_NETWORK_UPGRADE` — sẽ tự động xả khi Tier nâng cấp.

#### Voice-Text Hybrid Fallback — iOS/Android Asymmetry Fix

- 📱 **Kịch bản:** iOS đang nhận file ghi âm (Tier 2 / Offline Near) → người dùng khóa màn hình → iOS rơi xuống Tier 3 / Offline Far, AWDL bị Apple tắt.
- 📱 **Giải pháp:** Lõi Rust trên máy **gửi** (Android/Mac) phát hiện timeout AWDL → gọi mô hình **Whisper AI cục bộ** (Local NLP — chạy tại biên, không cần Internet) để phiên dịch file ghi âm thành Text → chỉ bắn Text E2EE qua BLE Long Range sang iPhone. Người nhận iOS vẫn nhận được thông tin khẩn cấp dưới dạng chữ, đảm bảo tính đồng nhất chức năng với Android.

### 5.22 Dynamic Agent Routing (DAR) — Universal Agentic Bridge qua WASM

> **Kiến trúc UAB (Universal Agentic Bridge):** Thay vì hardcode whitelist AI trong `Manifest.json`, Lõi Rust cung cấp một **HTTP Client được quản lý** cho WASM Sandbox, cho phép bất kỳ `.tapp` nào gọi API Agent bên ngoài — nhưng phải đi qua cổng kiểm soát của Rust Core.

#### WASM-Rust IPC Bridge

- 📱💻 **WASM không tự mở socket:** `.tapp` gọi FFI `send_agent_request(payload, external_endpoint)` — WASM không có capability `wasi-sockets`. Lõi Rust là người duy nhất thực thi TLS handshake ra ngoài.
- 💻🖥️ **Local DLP & Context Hydration:** Trước khi gửi, Lõi Rust chặn payload, chạy qua **Local OPA Policy Engine** (`payload_size`, `data_classification`, `user_consent_token`). Nếu Policy PASS → Rust thực thi TLS tới `api.openclaw.com`. Nếu FAIL → trả lỗi về WASM, không rò rỉ byte nào.
- 📱💻🖥️ **Context Throughput:** `~150MB/s` truyền tải context text thuần túy trong RAM qua `SharedArrayBuffer` (Desktop) hoặc Zero-Copy JSI (Mobile).
- ☁️ **Attack Surface — SSRF Mitigation:** Rủi ro Server-Side Request Forgery (SSRF) và Data Exfiltration nếu AI Agent bị compromise. Giảm nhẹ (Mitigated) bằng: (1) User-Consent Modal mỗi phiên, (2) Egress Domain Allowlist trong OPA Policy, (3) `payload_size < 4KB` hard limit.
- ☁️ **Latency:** < 10ms cho IPC Bridge WASM → Rust. Egress Latency phụ thuộc nhà cung cấp AI.

### 5.23 Local Dual-Mask Protocol & PII Metadata Sanitization

> **Bài toán:** AI Agent bên ngoài nhận được prompt có thể chứa PII (Số thẻ tín dụng, CMND, Email) — vi phạm GDPR/PDPA và phơi lộ dữ liệu nhạy cảm ra ngoài perimeter.

- 📱💻🖥️ **Local Micro-NER Masking:** Trước khi Lõi Rust đẩy bất kỳ payload nào ra External AI, một thư viện NER (Named Entity Recognition) nhẹ chạy hoàn toàn tại biên thiết bị (không cần Internet) tự động phát hiện và mặt nạ hóa (mask) các thực thể nhạy cảm theo mô hình phân loại cục bộ.
- 📱💻🖥️ **`[REDACTED]` Tokenization:** Các thực thể được thay thế bằng token định danh chuẩn hóa (`[REDACTED_CC]`, `[REDACTED_ID]`, `[REDACTED_EMAIL]`). Token này đủ ngữ nghĩa để AI Agent trả lời đúng context nhưng không thể suy ngược ra giá trị gốc.
- 📱💻🖥️ **ZeroizeOnDrop (RAII):** Plaintext gốc (trước khi mask) được giữ trong vùng nhớ RAM được bảo vệ bởi RAM Scrambling & `ZeroizeOnDrop`. Sau khi tạo ra masked copy, RAM gốc bị ghi đè `0x00` ngay lập tức qua RAII destructor — không có window nào cho Memory Dump Attack.

### 5.24 Ed25519-backed Manifest Integrity Protocol (EMIP)

> **Bài toán:** Kẻ tấn công có thể giả mạo hoặc sửa `Manifest.json` của `.tapp` để leo thang quyền Egress, inject endpoint độc hại.

- 🗄️ **Ed25519 Digital Signature:** Mỗi `Manifest.json` được ký bằng Private Key của Publisher (Ed25519). Lõi Rust xác minh chữ ký tại boot-time và mỗi khi `.tapp` yêu cầu Egress mới. Manifest bị giả mạo → `.tapp` bị terminate ngay lập tức.
- ☁️ **Manifest-to-OPA Compiler:** Manifest hợp lệ được biên dịch thành Policy Rego Rule và nạp vào Local OPA Engine. Mọi lời gọi `send_agent_request` được đối chiếu với Rule này tại runtime — zero runtime overhead vì rule đã được compile sẵn.
- 💻📱 **Boot-time Manifest Validation:** Khi khởi động TeraChat, Lõi Rust load toàn bộ `.tapp` đã cài và thực hiện EMIP check hàng loạt (Batch Verify). `.tapp` nào fail verification bị quarantine — không load vào bộ nhớ, không cấp quyền UI.

### 5.25 Hardened SPKI Pinning & Rustls Custom Verifier

> **Bài toán:** MITM attack hoặc DNS poisoning có thể redirect `api.openclaw.com` sang server giả mạo, đánh cắp prompt + response E2EE.

- ☁️ **SPKI Hash Pinning:** Lõi Rust hardcode `SHA-256(SubjectPublicKeyInfo)` của certificate hợp lệ cho mỗi Egress endpoint trong `Manifest.json`. Rustls từ chối bất kỳ certificate nào không khớp SPKI hash — kể cả CA-signed certificate hợp lệ từ CA trung gian bị compromise.
- 💻📱 **Rustls Custom Certificate Verifier:** Triển khai `trait ServerCertVerifier` tùy chỉnh trong Rustls. Verifier thực hiện 3 bước: (1) Standard TLS chain validation, (2) SPKI hash comparison, (3) OCSP Stapling check nếu available. Bất kỳ bước nào fail → `TlsError::InvalidCertificate` → connection dropped, zero data leaked.
- ☁️ **DNS-over-HTTPS (DoH) Client-side Resolution:** Trước khi mở TLS connection tới External AI, Lõi Rust resolve DNS qua DoH endpoint (`cloudflare-dns.com/dns-query` hoặc self-hosted) — ngăn chặn DNS poisoning ở ISP/router level. IP kết quả được đối chiếu với IP whitelist trong Manifest.

### 5.26 Zero-Footprint Streaming Egress (ZFSE) — OOM Prevention cho AI File Transfer

> **Bài toán:** Khi AI Agent yêu cầu file 1GB làm context (VD: phân tích video), Monolithic Load → RAM → Egress gây OOM-Kill ngay lập tức.

- 📱💻 **Iterative Chunk Decryption (2MB/chunk):** Lõi Rust không đọc toàn bộ file vào RAM. Engine ZFSE mở file qua `mmap`, giải mã từng chunk 2MB bằng AEAD, đẩy chunk qua TLS stream tới AI endpoint, rồi zeroize ngay. RAM max = 2 chunks (~4MB) tại mọi thời điểm.
- 📱💻 **ZeroizeOnDrop (RAII) theo chunk:** Mỗi chunk được bọc trong RAII struct. Khi chunk đã được đẩy qua TLS và ACK nhận được, destructor tự động kích hoạt `zeroize()` ghi đè RAM — không để lại plaintext tàn dư.
- 📱💻 **Rust-native HTTP/2 Multipart Streaming:** Sử dụng HTTP/2 multiplexed streams (không phải HTTP/1.1 chunked) để giữ một connection duy nhất nhưng pipeline nhiều chunk song song — giảm RTT overhead và tránh request timeout trên mạng di động chập chờn.

### 5.27 Edge-Native ONNX Embedding Engine — Vectorization tại Biên

> **Bài toán:** RAG (Retrieval-Augmented Generation) yêu cầu vector embedding để tìm kiếm ngữ nghĩa. Nếu gửi plaintext lên Cloud để embed → rò rỉ nội dung chat. Nếu không embed → RAG quality thấp.

- 📱💻 **Edge ONNX Runtime (all-MiniLM-L6-v2):** Lõi Rust tích hợp `ort` crate (ONNX Runtime bindings) để chạy **`all-MiniLM-L6-v2`** (22M params, 80MB) trực tiếp tại biên. Model này đủ nhỏ để chạy trên mobile (<500ms per batch) nhưng đủ tốt cho semantic search tiếng Anh/Việt.
- 📱💻 **NPU/CPU Hardware Acceleration:** Trên iOS, model chạy qua **CoreML** (Apple Neural Engine — ~3x speedup). Trên Android, chạy qua **NNAPI** (Qualcomm Hexagon DSP). Trên Desktop, sử dụng AVX2/NEON SIMD instructions. Lõi Rust tự động phát hiện hardware và chọn backend (`ort::ExecutionProvider::CoreML` / `ort::ExecutionProvider::Nnapi`).
- 📱💻 **Rust-native Tokenization:** Tokenizer (`tokenizers` crate, Hugging Face) chạy embedded trong binary — không cần Python runtime. Tokenization latency < 5ms cho đoạn chat 200 tokens.

### 5.28 Ephemeral In-memory Vector Shield — Bảo mật RAM cho Vector Index

> **Bài toán:** HNSW/Flat vector index chứa embedding bắt nguồn từ nội dung E2EE — nếu bị dump RAM hoặc swap, embedding có thể dùng để reconstruct partial plaintext ngữ nghĩa.

- 📱💻 **Protected RAM Arena:** Toàn bộ vector index được cấp phát trong một arena được bảo vệ bởi `ZeroizeOnDrop` — OS không được phép swap page này ra disk. Trên iOS/Android, dùng `madvise(MADV_DONTDUMP)` để ngăn core dump.
- 📱💻 **ZeroizeOnDrop (RAII) cho Vector Arena:** Khi phiên chat kết thúc hoặc người dùng đóng `.tapp`, RAII destructor xóa toàn bộ arena bằng `zeroize()`. Không có vector embedding nào tồn tại sau khi session ends.
- 📱💻 **In-memory HNSW/Flat Index:** Sử dụng `hnswlib-rs` (port Rust của hnswlib) hoặc Flat Cosine Similarity search cho corpus nhỏ (< 10,000 vectors). Entire index sống hoàn toàn trong RAM — không persist xuống disk (`hot_dag.db`) trừ khi người dùng bấm "Save Semantic Index".

### 5.29 Tiered Hardware-Aware Resource Governance (THARG)

> **Bài toán:** ONNX embedding + vector search có thể ăn quá nhiều CPU/RAM trên thiết bị cấp thấp, gây ANR (Android) hoặc Jetsam (iOS) và ảnh hưởng đến luồng chat chính.

- 📱💻 **`sysinfo` Hardware Profiling:** Lõi Rust sử dụng `sysinfo` crate để đo `available_memory`, `cpu_count`, và `cpu_frequency` tại boot. Từ đó phân loại thiết bị vào 3 tier: Low (< 2GB RAM), Mid (2-6GB), High (> 6GB). Mỗi tier có config ONNX thread count và chunk size khác nhau.
- 📱 **Rust Thermal Governor (Thread Yielding):** Trên mobile, Lõi Rust monitor CPU temperature thông qua `sysfs` (Android) / `IOKit` (iOS). Nếu temp > 45°C, embedding pipeline tự động giảm thread count và tăng `sleep_between_batches` để tránh thermal throttling và bảo vệ battery.
- 📱 **Android LMK Mitigation (OOM Score Adjustment):** Trên Android, Lõi Rust điều chỉnh `oom_score_adj` của tiến trình embedding xuống thấp hơn (ưu tiên giữ lại) so với background processes — tránh LMK (Low Memory Killer) terminated worker thread giữa chừng quá trình index.

### 5.30 Opportunistic Background Checkpointing (OBC)

> **Bài toán:** iOS có thể suspend app bất kỳ lúc nào. Nếu ONNX indexing đang chạy bị interrupt, 30-60 giây embedding work mất sạch — user experience tệ.

- 📱 **iOS `BGProcessingTaskRequest`:** Lõi Rust đăng ký `BGProcessingTaskRequest` với identifier `com.terachat.onnx-indexing` sau khi hoàn thành 30% index. iOS được quyền schedule background window (thường khi cắm điện + Wi-Fi) để tiếp tục indexing.
- 📱 **Android `ForegroundService` (Sticky):** Trên Android, embedding worker chạy dưới dạng `ForegroundService` với notification persistent — tránh bị OS kill khi app background. Dùng `START_STICKY` để OS restart service nếu bị kill do low memory.
- 📱💻 **Delta-State Serialization (Atomic Commit):** Sau mỗi batch 100 vectors, Lõi Rust thực hiện `checkpoint_write()` — serialize Delta-State (partial index snapshot) vào file tạm (không phải `hot_dag.db`). Nếu bị interrupt, resume từ checkpoint thay vì restart từ đầu. Checkpoint được xóa và merge vào main index khi hoàn thành.

### 5.31 Strict AST Sanitization Bridge (SASB) — Anti-XSS từ AI Response

> **Bài toán:** AI Agent response chứa Markdown/HTML. Nếu render trực tiếp qua WebView hoặc innerHTML, kẻ tấn công có thể poison AI response với `<script>`, `javascript:` URI, hay malicious iframe — XSS tấn công ngay trong giao diện chat.

- 💻📱 **Rust-native AST Parsing (`pulldown-cmark`):** Tất cả AI response được parse thành AST (Abstract Syntax Tree) bằng `pulldown-cmark` crate trực tiếp trong Lõi Rust — trước khi truyền về UI. Parser chạy ở tầng Rust, không phải JS.
- 💻📱 **AST Node Pruning (Strict Whitelist):** SASB áp dụng whitelist cực kỳ nghiêm ngặt: chỉ cho phép `Text`, `Heading`, `Paragraph`, `Code`, `CodeBlock`, `Strong`, `Emphasis`, `List`, `ListItem`, `Link` (kiểm tra scheme). Mọi node khác (`Html`, `Script`, `Iframe`, custom component) bị prune khỏi AST ngay lập tức.
- 💻📱 **Protobuf-driven Pure Rendering:** AST đã-clean được serialize thành Protobuf và truyền qua IPC bridge về UI. UI renderer chỉ nhận `Vec<ASTNode>` — không bao giờ nhận raw HTML string. Không có code path nào từ AI response đến `dangerouslySetInnerHTML` hay WebView `loadHTMLString`.

### 5.32 Deterministic Unicode Canonicalization & Zero-Width Scrubbing

> **Bài toán:** Kẻ tấn công inject ký tự Unicode ẩn (Zero-Width Joiner, BOM, Homoglyph) vào tin nhắn để bypass keyword filter hoặc tạo payload độc hại trông vô hại với mắt thường.

- 📱💻 **Rust `unicode-normalization` (NFC/NFKD Form):** Trước khi bất kỳ tin nhắn nào được đẩy vào pipeline xử lý (Intent Classification, DLP, Egress), Lõi Rust áp dụng NFKD normalization (Compatibility Decomposition) → sau đó NFC recompose. Tất cả các biến thể homoglyph sẽ được fold về canonical form — "рasswоrd" (Cyrillic) == "password" (Latin) dưới góc nhìn của bộ lọc.
- 📱💻 **Invisible Character Regex Stripping (ZWJ/ZWNJ/BOM):** Sau normalization, Lõi Rust chạy regex strip loại bỏ toàn bộ invisible/control characters: `[\u{200B}\u{200C}\u{200D}\u{FEFF}\u{00AD}\u{2060}]` và các codepoint nguy hiểm khác trong Unicode category Cf (Format). Kết quả: payload hoàn toàn "opaque-free" trước khi đến các lớp semantic.
- 📱💻 **Homoglyph Confusable Mapping:** Lõi Rust tích hợp bảng tra cứu Confusables (theo Unicode Security Mechanisms TR39) được compile sẵn thành perfect hash map Rust. Mỗi ký tự input được map về representative form — tiêu diệt mọi chiến thuật Typosquatting hoặc Identity Spoofing qua Unicode.

### 5.33 Edge Deterministic Entity Scanner (EDES) — Nhận diện Thực thể Cục bộ

> **Bài toán:** NER model nặng (ONNX DeBERTa) quá chậm để scan real-time từng keystroke trong luồng chat. Cần một fast-path scanner.

- 📱💻 **Aho-Corasick Regex Engine (Rust):** Lõi Rust triển khai `aho-corasick` crate — multi-pattern search đạt O(n) thay vì O(n×m). Toàn bộ Banned Lexicon, PII pattern (số thẻ ngân hàng, CMND regex), và Known-Bad Entity list được compile thành Aho-Corasick automaton tại boot-time. Scan throughput: **~500MB/s** trên một core duy nhất.
- 📱💻 **Local NER Whitelist/Blacklist:** Lõi Rust maintain hai lookup table: `ENTITY_WHITELIST` (các entity được phép egress nguyên bản) và `ENTITY_BLACKLIST` (entity bị block hoàn toàn). Admin cập nhật list qua OPA Policy — không cần app update.
- 📱💻 **Zero-copy Memory Scanning:** Aho-Corasick engine operate trực tiếp trên plaintext buffer được bảo vệ bởi `ZeroizeOnDrop` — không tạo copy. Kết quả trả về là danh sách `(byte_offset, entity_id, scan_hit)` — EDES không decode hay extract giá trị thực của entity, giảm attack surface trong chính engine scanner.

### 5.34 Semantic Quarantine & Entity Masking — Cách ly Thực thể Nguy hiểm

> **Bài toán:** Sau khi EDES phát hiện entity nguy hiểm, cần cô lập chúng khỏi luồng Egress mà không phá vỡ ngữ cảnh cho AI Agent.

- 📱💻 **Runtime Entity Masking (`[BLOCKED_BY_GUARDRAIL]`):** Tại mỗi byte offset mà EDES báo hit, Lõi Rust thực hiện in-place replacement bằng token chuẩn hóa `[BLOCKED_BY_GUARDRAIL_{entity_id}]`. Token đủ thông tin để AI Agent biết "có gì đó bị chặn tại đây" nhưng không thể reconstruct giá trị gốc.
- 📱💻 **Rust-native AST Node Replacement:** Sau khi mask ở tầng plaintext, AST được rebuild. Node bị masked được đánh tag `quarantined=true` trong AST schema — cho phép UI render `[BLOCKED_BY_GUARDRAIL]` placeholder với màu sắc khác biệt (liên kết với §GSNI Design.md §21).
- 📱💻 **ZeroizeOnDrop (Sensitive Buffer):** Plaintext buffer chứa entity gốc (trước khi mask) bị `zeroize()` ngay lập tức sau khi quá trình mapping hoàn thành. Không có window nào để side-channel attack đọc entity từ RAM.

### 5.35 Hierarchical Crypto-Shredding & Atomic State Purge — Checkpoint Residue Elimination

> **Bài toán:** ONNX indexing checkpoint persist trên disk. Nếu thiết bị bị tịch thu hoặc crack, checkpoint chứa embedding vectors có thể dùng để reconstruct partial plaintext ngữ nghĩa.

- 📱💻 **Key Wrapping (Epoch-bound):** Mỗi Checkpoint file được mã hóa bằng `Epoch_Checkpoint_Key = HKDF(Session_Master_Key, epoch_id || timestamp)`. Key này không được lưu — chỉ derive được nếu có `Session_Master_Key` và epoch_id. Khi Session kết thúc, `Session_Master_Key` bị `zeroize()` → mọi Checkpoint từ session đó trở nên vô nghĩa về mặt mật mã (Crypto-locked).
- 📱💻 **Atomic Disk Wipe (`shred`):** Khi Checkpoint GC trigger (TTL hết hạn hoặc session kết thúc), Lõi Rust không chỉ `unlink()` file — mà thực hiện **3-pass shred**: ghi đè `0x00`, rồi `0xFF`, rồi random bytes, cuối cùng `unlink()`. Trên SSD với FTL, Lõi Rust sử dụng `TRIM/DISCARD` syscall để request firmware xóa flash block.
- 🗄️ **Secure Enclave Session Revocation:** Khi Admin kích hoạt Remote Wipe (ARP — xem Function.md §11), Secure Enclave trên iOS/Android nhận lệnh delete `Session_Master_Key` khỏi hardware-protected storage. Không có key = không access được bất kỳ Checkpoint nào còn tồn đọng trên disk.

### 5.36 Stateful Semantic Accumulator (SSA) & Retroactive Taint — Chống Salami Attack

> **Bài toán:** AI Agent bị hack thực hiện "Semantic Fragmentation Attack" (Salami Attack): chia thông tin lừa đảo thành 10-20 tin nhắn vô hại riêng biệt. Mỗi tin nhắn pass qua EDES và Intent Classification. Nhưng khi concatenate lại trong phiên hội thoại, chúng hoàn thành mục tiêu Social Engineering.

- 📱💻 **Sliding Context Window (Protected Memory):** Lõi Rust maintain một **Sliding Context Buffer (SCB)** — circular buffer được bảo vệ bởi `ZeroizeOnDrop` lưu trữ N tin nhắn gần nhất (default N=20, configurable). SCB được cập nhật incremental sau mỗi tin nhắn. Không persist xuống disk.
- 📱💻 **Lazy Triggered ONNX Inference:** Việc chạy ONNX DeBERTa trên toàn bộ SCB sau mỗi tin nhắn sẽ quá tốn tài nguyên. Thay vào đó, Lõi Rust áp dụng **Lazy Trigger**: chạy ONNX scan toàn bộ SCB chỉ khi EDES flagged ≥ 2 "borderline entities" trong cửa sổ 5 tin nhắn liên tiếp — tức là khi pattern điệu có dấu hiệu escalation.
- 📱💻 **Retroactive Taint Propagation:** Nếu ONNX inference trên SCB phát hiện semantic pattern nguy hiểm (điểm `Intent_Score[SOCIAL_ENGINEERING] > 0.75`), Lõi Rust thực hiện **retroactive taint**: đánh dấu TAINTED không chỉ tin nhắn hiện tại mà còn N-3 tin nhắn trước đó trong SCB. Toàn bộ conversation thread bị seal (Conversation Sealing — xem Function.md §12). UI kích hoạt Magnetic Collapse animation (xem Design.md §25).

### 5.37 Full-Context Passthrough (FCP) Tunnel — Kiến trúc "Unchained AI"

> **Bối cảnh:** Khi Admin đã ký `Security Manifest Consent` (xác thực bằng YubiKey/Biometric + typed `"I_ACCEPT_LIABILITY"`), Lõi Rust kích hoạt cờ `FCP_Enabled = true` trong Local OPA Policy. Nguyên tắc: **Nhượng bộ về Data Confidentiality, KHÔNG nhượng bộ về Execution Integrity.**

- 💻🖥️ **Bypass Local Scrubbing:** Khi `FCP_Enabled = true`, Lõi Rust rẽ nhánh Data Pipeline tại FCP Gate. Thay vì đưa Context vào EDES / O-LLVM / Micro-NER queue, Lõi Rust đẩy nguyên khối Plaintext (được bảo vệ bởi `ZeroizeOnDrop`) thẳng vào `TlsStream` trỏ tới AI endpoint. TTFB giảm từ ~300ms xuống < 10ms (chỉ TLS handshake overhead). AI nhận 100% raw context, không bị "thiến".
- 📱💻 **Strict Execution Boundary (Ingress vẫn bất khả xâm phạm):** Dù Egress là 100% raw, Ingress từ OpenClaw **bắt buộc** đi qua SASB (§5.31). OpenClaw có toàn quyền đọc nhưng **tuyệt đối 0% khả năng** inject XSS/HTML/Code về lại giao diện TeraChat. Execution Integrity của Lõi Rust = bất biến.
- 📱💻🖥️ **Zero-Knowledge Non-Repudiation Log (FCP):** Mỗi lần `unrestricted_stream` hoặc FCP egress được trigger, Lõi Rust ghi vào SQLite WAL: `[FCP_TRIGGERED | UTC_Timestamp | Payload_Hash(BLAKE3) | Agent_Endpoint_Hash | Device_Ed25519_Signature]`. Không lưu nội dung Prompt. Đây là bằng chứng Non-Repudiation: TeraChat miễn nhiễm pháp lý vì có chữ ký số của chính Admin kích hoạt FCP.
- 📱💻 **FCP Scope Isolation:** FCP chỉ áp dụng cho `.tapp` cụ thể được Admin duyệt — không phải toàn bộ hệ thống. Các `.tapp` khác trong cùng tenant vẫn chạy với full EDES/NER protection. Admin có thể revoke FCP bất kỳ lúc nào; revocation được broadcast qua CRDT Mesh đến tất cả thiết bị.

> **Crash Report:** Mã hóa nguyên khối (Monolithic Encryption) một file 10GB đòi hỏi cấp phát mảng byte 10GB trong RAM — lập tức bị iOS Jetsam/Android OOM-Kill (Crash giây thứ 2). SQLite `SQLITE_TOOBIG` lỗi khi cố nhét BLOB > 2GB vào `hot_dag.db`. HTTP Keep-alive 30 phút trên mạng di động không khả thi (Timeout).

#### Kiến trúc Streaming Chunker — Zero RAM Overhead

- 📱💻🖥️ **Hard Chunk Size = 2MB:** Lõi Rust **KHÔNG BAO GIỜ** đọc toàn bộ file vào RAM. Engine Streaming chia file thành các `Chunk_2MB` qua syscall `pread(fd, buf, 2MB, offset)`. RAM tiêu thụ cực đại tại mọi thời điểm: **~10MB** (Double Buffer: 1 chunk đang mã hóa + 1 chunk đang đẩy lên S3). OOM-Kill bị triệt tiêu hoàn toàn.
- 📱💻🖥️ **mmap + ZeroizeOnDrop Pipeline:** Mỗi `Chunk_2MB` được `mmap` vào vùng RAM được bảo vệ bởi `ZeroizeOnDrop`. Sau khi mã hóa AEAD và đẩy lên S3 Multipart, Lõi Rust chạy `ZeroizeOnDrop` ghi đè `0x00` lên toàn bộ vùng đó trước khi giải phóng. Plaintext video không bao giờ tồn tại trong RAM lâu hơn thời gian xử lý 1 chunk (~50ms trên NVMe).
- 📱💻🖥️ **Chunk-Level Deterministic Key Derivation:** Mỗi chunk nhận `Chunk_Key = HKDF(Session_Key, File_ID || Chunk_Index || Byte_Offset)`. Key mỗi chunk là duy nhất, đảm bảo mã hóa cô lập — tấn công replay một chunk không ảnh hưởng các chunk khác.

#### BLAKE3 Segmented Merkle Tree — Kiểm tra Toàn vẹn Phi tập trung

- 📱💻🖥️ **Leaf Hash Per Chunk:** Mỗi `Chunk_2MB` sau khi mã hóa → sinh `Leaf_Hash = BLAKE3(Ciphertext_Chunk || Chunk_Key || Chunk_Index)`. Các Leaf Hash được tổng hợp thành `Merkle_Root_Hash` đại diện cho toàn bộ file.
- 📱💻🖥️ **Pipelined Verification:** Client nhận `Merkle_Root_Hash` từ Control Plane TRƯỚC khi nhận payload. Mỗi chunk nhận về được kiểm tra `BLAKE3(received_chunk) == Leaf_Hash` tức thì — phát hiện corruption giữa chừng ngay lập tức, không cần chờ tải xong file.
- 📱💻🖥️ **Fault Tolerance (Resume):** Nếu đứt mạng ở chunk thứ 4999/5000 (9.998GB/10GB), Lõi Rust kiểm tra Merkle Tree, xác định đúng chunk lỗi, chỉ yêu cầu S3 Multipart Re-upload đúng **2MB** đó. Toàn bộ 9.998GB trước đó được giữ nguyên — không upload lại từ đầu.
- ☁️ **Root Hash Anchoring:** `Merkle_Root_Hash` cuối cùng được ký bằng `Ed25519_DeviceKey` và lưu lên Append-Only Audit Log. CISO/Admin có thể verify toàn vẹn bất kỳ lúc nào mà không cần giải mã file.

#### S3 Multipart Upload Protocol

- ☁️🗄️ **Salted MLE via MinIO S3 Multipart:** Các `Chunk_2MB` ciphertext được đẩy qua `S3 CreateMultipartUpload` API. Mỗi Part = 1 Chunk. VPS/MinIO chỉ nhận Ciphertext thuần túy — không có khả năng giải mã. Nếu đứt mạng: `S3 AbortMultipartUpload` tự động dọn sạch parts dở dang sau 24h.
- ☁️🗄️ **Throughput:** Đạt 300–500MB/s trên SSD/NVMe. Latency từ lúc chọn file → bắt đầu upload < 50ms (overhead: chỉ là thời gian sinh `Merkle_Root_Hash` của chunk đầu tiên).
- ☁️ **Anti-`413 Request Entity Too Large`:** Mỗi Part = 2MB, không bao giờ vi phạm `client_max_body_size` của Nginx/Ingress (thường giới hạn 100MB). Giải quyết hoàn toàn lỗi HTTP 413.

#### iOS Background Delegation — Chống App Suspension

- 📱 **Pre-signed URL Per Chunk:** Lõi Rust sinh trước danh sách `Pre_signed_URL[0..N]` (mỗi URL TTL 15 phút, HMAC-SHA256 bound to device), sau đó bàn giao toàn bộ danh sách cho `NSURLSession Background Transfer`.
- 📱 **OS-Managed Socket:** Apple OS tự quản lý duy trì socket, báo cáo progress `URLSession didSendBodyData`, và xử lý retry khi mạng phục hồi. App không cần thức (Awake) — vượt qua hoàn toàn rào cản 30 giây App Suspension.
- 📱 **Android WorkManager:** Tương đương `NSURLSession` trên Android: `WorkManager` Chained Task `[Encrypt_Chunk → S3_Upload_Chunk → ZeroizeOnDrop]` per chunk. Constraint: `NetworkType.CONNECTED`, `requiresBatteryNotLow()`.

### 5.41 Bảo vệ WASM Sandbox & Chống Escaping (RCE)

> **Attack Surface:** Lỗ hổng JIT Compiler bên trong WasmEdge có thể dẫn đến trốn thoát WASM Sandbox (RCE) và chiếm quyền điều khiển tiến trình Host.

- 🗄️ **Rust-native Syscall Filtering:** Sử dụng thư viện lọc syscall tại tầng ứng dụng để hạn chế bề mặt tấn công.
- ☁️ **Userspace I/O Egress Proxy:** Lõi Rust đóng vai trò Forward Proxy duy nhất để kiểm soát luồng TLS, loại bỏ hoàn toàn việc sử dụng BPF/Seccomp tại tầng kernel.
- ☁️ **Application Guardrail (OPA):** Kích hoạt OPA Guardrail kiểm duyệt RPC Whitelist ở tầng Application. Bất kỳ RPC payload nào ra khỏi Sandbox đều bị OPA chặn nếu không có chữ ký uỷ quyền hợp lệ.
- 💻 **Buffer Overflow Mitigation:** Áp dụng Memory Isolation tuyến tính đối với không gian địa chỉ WASM, kết hợp `ZeroizeOnDrop` (RAII) nhằm tước bỏ hoàn toàn năng lực tràn bộ đệm vượt biên giới Sandbox.

### 5.43 Giải pháp: Time-Based Cryptographic Hardening & State Machine Rate-Limiting (Chống Head-of-Line Blocking & Downgrade Attack)

- 📱💻🖥️ **ISO 27001 A.14.1.2 Secure Engineering:** Thiết lập các quy tắc kỹ thuật bảo mật khắt khe đúc kết vòng đời an toàn, ngăn chặn các tấn công hạ cấp giao thức (Protocol Downgrade Attack) ngay ở tầng ứng dụng bằng cách ghim chặt phiên bản tối thiểu.
- ☁️ **AEAD Payload Decoupling:** Tách rời (Decouple) tải trọng mạng và mã hoá xác thực AEAD để giải quyết dứt điểm tắc nghẽn ở đầu hàng đợi (Head-of-Line Blocking), cho phép các gói tin không phụ thuộc nhau được xử lý song song.
- 🗄️ **Adaptive Protocol State Machine:** Máy trạng thái giao thức thích ứng tự động kiểm soát băng thông (Rate-Limiting) và phát hiện các nỗ lực đàm phán độc hại bằng các hình phạt leo thang mã nguồn ứng dụng (App-level), loại bỏ BPF filters.

---

### 4.4 Hybrid PQ-KEM (Kyber768) — Điểm Neo Lượng tử

- 📱💻🖥️☁️🗄️ **Kiến trúc Lai ghép Kép (Hybrid KEM):** Lõi Rust chạy song song `X25519` và `ML-KEM/Kyber768`. `Final_Session_Key = HKDF(X25519_Shared || Kyber768_Shared)`. X25519 chống tấn công cổ điển; Kyber768 chống Shor Algorithm (máy tính lượng tử).
- 📱 **Quantum Checkpoints:** ML-KEM payload cồng kềnh (~1.18KB vs X25519 ~32 bytes) chỉ đính kèm vào `KeyPackage` MLS Handshake hoặc tick định kỳ (24h / 10.000 tin). Luồng hàng ngày chạy thuần AES-256-GCM (\<1KB) — tiết kiệm 99.9% băng thông.
- 📱 **Survival Mesh Fragmentation:** BLE 5.0 MTU ~512 bytes. Khi offline, Rust Core băm nhỏ Kyber blob 1.18KB thành mảnh 400 bytes + Sequence ID + FEC. Selective ACK yêu cầu lại mảnh rớt — chặn tràn bộ đệm chip viễn thông.
- Đáp ứng chuẩn **NSA CNSA 2.0**, miễn nhiễm tấn công **HNDL (Harvest Now, Decrypt Later)**.

### 4.5 Threshold FIDO2 Recovery (Quorum-based Recovery)

Khi doanh nghiệp yêu cầu Cold Recovery:

- 📱💻🖥️ **Hardware Vault:** Admin neo giữ KEK (Key Encryption Key) trong YubiKey sử dụng chuẩn FIDO2 `hmac-secret` (PRF extension). Đảm bảo không ai có thể giải mã nếu thiếu thiết bị vật lý.
- 📱💻🖥️ **M-of-N Fragmentation:** Thiết lập cơ chế Shamir's Secret Sharing phân mảnh Recovery Key để chống điểm lỗi đơn lẻ. Hệ thống chỉ phục hồi khi đạt Quorum (Ví dụ: 3/5 YubiKey của Hội đồng quản trị cùng cắm vào điểm truy cập).
- 🖥️ **Monotonic Counter Sealing:** Áp dụng niêm phong TPM 2.0 Monotonic Counter. Mỗi nỗ lực gõ sai mã PIN hoặc tháo gỡ phần cứng sẽ làm thay đổi Counter, vô hiệu hóa ngay lập tức mọi nỗ lực Clone hoặc Snapshot VM của thiết bị phục hồi.
- **Master Wrapping Key:** `KEK_deterministic` chịu sự bảo vệ trực tiếp từ YubiKey thay vì Software Enclave thuần túy.

### 4.6 Phân mảnh Hạ tầng Chữ ký & Phục hồi (Hybrid Cross-Signing & Cloud Escrow)

- 📱 Áp dụng mô hình Hybrid Multi-Device Cross-Signing cho phép xác thực chéo thiết bị thông qua tín hiệu BLE/LAN nội bộ.
- 📱 Cấu hình mã hóa `KEK_deterministic` trực tiếp lên iCloud Keychain áp đặt quy chuẩn Advanced Data Protection (Cloud Escrow Fallback).
- 📱 Thiết lập giao thức phục hồi ngoại vi tuân thủ chuẩn lưu trữ BIP39 thông qua sơ đồ 24-word Recovery Key.

### 4.7 Bảo vệ Toàn vẹn & Chống Replay trong mạng Mesh (BLAKE3 & Merkle)

- 📱💻🖥️ Vận hành Pipelined Segmented Merkle phân rã tệp tin thành các Macro-Block 64MB cho phép CPU xử lý tính toán băm xác thực song song.
- 📱💻🖥️ Gắn kết nhãn Cryptographic Offset Binding (`AD = [File_ID] || [Chunk_Index] || [Byte_Offset]`) vào từng mảnh nhằm ngăn chặn sự đánh cắp hoặc dịch chuyển thứ tự (Displacement Attack).
- 📱💻🖥️ Sinh Deterministic Nonce từ khóa luồng `Channel_Key` đảm bảo quyền hạn giải mã và xác thực được khoanh vùng độc quyền cho thành viên cùng nhóm.

### 4.8 Thảm họa "Zero-Access" & Rogue Admin (Multi-Party Enterprise Escrow KEM)

- ☁️📱💻🖥️ Giải quyết rủi ro Rogue Admin bằng Hệ thống Ký quỹ Khóa Đa bên, áp dụng thuật toán Shamir's Secret Sharing (M-of-N Quorum) phân mảnh Recovery Key giao cho Hội đồng quản trị.
- ☁️📱💻🖥️ Ràng buộc cơ chế Cryptographic Wrapping (Bọc chéo) thông qua Escrow Public Key ngay tại thời điểm Bootstrap KMS.
- ☁️📱💻🖥️ Ép buộc ghi nhận Audit Log chuẩn HIPAA/SOC2 đối với mọi thao tác giải mã của Admin.

### 4.9 Giao thức Đóng băng Phân xử Ký quỹ E2EE & Khóa thời gian

> **Bài toán:** Khi xảy ra tranh chấp hoặc nghi ngờ Rogue Admin lạm dụng quyền giải mã Escrow, hệ thống cần một cơ chế "câu giờ" và lưu vết bằng chứng nhân quả mà không tiết lộ nội dung.

- 📱 **Bằng chứng Tiên nghiệm (A Priori Evidentiary Extraction):** Trích xuất thông tin kết hợp Back-traversal DAG Hash Chain để bảo toàn ngữ cảnh nhân quả xung quanh thời điểm tranh chấp.
- ☁️ **Two-Phase HTLC (Hashed Time-Lock Contract):** Triển khai Hợp đồng Khóa thời gian Hai pha để tự động mở rộng Grace Period (Cửa sổ ân hạn) bằng chữ ký PoD (Proof of Delivery), chặn Time-Racing attack.
- 💻 **Cryptographic Selective Disclosure:** Đóng gói bằng chứng hé lộ chọn lọc (Selective Disclosure) bằng `Admin_Escrow_PubKey` nhằm đảm bảo nguyên tắc Zero-Knowledge trong suốt quá trình phân xử.

### 4.9 Tấn công Memory Dump/Extraction (Synchronous Zeroize Safe Pipeline & Hardware Isolation)

#### Rò rỉ Plaintext từ Vector Embeddings trong RAM (Tự hủy bộ nhớ tàn bạo)

- 📱💻🖥️ **Ruthless Memory Self-Destruct:** Cấu trúc `ZeroizeOnDrop` (RAII) lập tức ghi đè liên tục `0x00` xóa sạch vùng Shared Memory ngay giây khắc bộ máy AI Sandbox tiêu thụ xong luồng Vector Embeddings.
- 💻🖥️ **Memory Protection via ZeroizeOnDrop:** Đảm bảo vùng nhớ nhạy cảm chứa dữ liệu AI được ghi đè `0x00` ngay sau khi sử dụng, ngăn chặn rò rỉ qua swap mà không cần cờ CAP_IPC_LOCK.
- 📱💻🖥️ **Luồng Xử lý Cách ly Kép:** Độc lập tiến trình giải mật (CPU Bound) ngăn vách cực đoan khỏi mọi kết cấu hệ thống truyền dẫn chéo I/O mạng lưới.

- 📱 Kích hoạt luồng ZeroizeOnDrop (RAII) để ghi đè `0x00` lên không gian bộ nhớ ngay khi thoát khỏi scope, khống chế vòng đời của plaintext key <2ms.
- 📱💻🖥️ Đẩy luồng ký/giải mã KEK nội bộ xuống Hardware Root of Trust (Secure Enclave/TPM 2.0/StrongBox) tuyệt đối không nạp Private Key vào RAM.
- 📱💻🖥️ Thiết lập Compiler-Level Guard ngắt mã kích hoạt trait `Send` và `Sync`, ngăn chặn rò rỉ khóa mã hóa qua thread boundary hoặc khi vượt điểm `.await`.

#### Giải pháp: Ephemeral VFS RAM-Drive & SIMD Zeroization (Chống Lỗ hổng SSD Plaintext Leak từ SQLite WAL & SHM)

- 📱 **iOS kCFAllocatorMallocZone VFS:** Sử dụng allocator tùy chỉnh trên iOS để thiết lập một VFS (Virtual File System) thuần túy trong RAM, tránh rò rỉ WAL/SHM xuống bộ nhớ flash vật lý.
- 💻 **Linux memfd_create RAM-Drive:** Áp dụng kĩ thuật tạo file tàng hình `memfd_create` trên Linux, đẩy `.db-wal` và `.db-shm` hoàn toàn vào phân mảnh bộ nhớ RAM tàng hình.
- 💻 **SIMD/Neon Intrinsics ZeroizeOnDrop:** Khai thác tập lệnh vector (SIMD/Neon) để tăng tốc độ ghi đè `0x00` tiêu hủy trang nhớ ngay trong tích tắc (ZeroizeOnDrop) trước khi ngắt tiến trình.
- 🗄️ **PRAGMA cipher_memory_security = ON:** Bắt buộc kích hoạt cờ bảo mật này kết hợp với VFS cấp thấp, đảm bảo mọi cache page của SQLCipher không bao giờ bị Paging OS dội xuống SSD Swap.
- 💻 **macOS FileVault Integration:** Trên macOS, các thành phần tệp phụ trợ phải nằm trong thư mục được FileVault 2 (XTS-AES-128) mã hóa, cộng thêm lớp SQLCipher bên trên (Double Encryption layer).
- 📱 **OOM-Kill Prevention (Atomic Flush Threshold):** Để giải quyết bài toán OOM-Kill do Ephemeral VFS nuốt RAM trên các thiết bị cũ, triển khai API `sqlite3_wal_checkpoint_v2` với luồng `SQLITE_CHECKPOINT_TRUNCATE` giới hạn ở mức 16MB. Khi WAL rượt tới ngưỡng này, hệ thống sẽ chốt và xả dữ liệu dứt khoát.
- 📱 **XChaCha20-Poly1305 Chunking Encryption:** Chia nhỏ khối dữ liệu RAM-Drive thành các Chunk mã hóa XChaCha20-Poly1305 tốc độ cao, ngăn chặn việc phân bổ RAM cục bộ nguyên mảng lớn.
- 📱 **SIMD 0x00 Ring Buffer Memory Pool:** Tái sử dụng lại các trang nhớ thông qua kỹ thuật Ring Buffer Memory Pool, kết hợp lệnh SIMD để xóa vết nguyên khối (`0x00`) với chi phí O(1) ngay trước khi trả lại Heap, đảm bảo vòng xoay bộ nhớ không làm nổ GC.

### 4.10 Giao diện Ký số Vật lý (Hybrid Multi-Device Cross-Signing & ZKP Delegation)

- 📱💻 Phát hành Delegation Certificate (Chứng thư ủy quyền) thời hạn định đoạt ngắn từ mạng lưới Desktop có USB Token bảo chuẩn sang thiết bị di động.
- 📱 Triển khai Multi-Device Cross-Signing cho phép Private Key nằm rải rác trong Secure Enclave của iOS ký xác thực thay mặt mỏ neo USB Token gốc.
- 📱💻 Sử dụng bằng chứng bảo mật Zero-Knowledge Proof (ZKP) để chứng minh quyền hạn phê duyệt hợp lệ mà không cần truy xuất trực tiếp khóa vật lý PKCS#11.

### 4.11 Chế độ Kiosk (Ephemeral Session Vault & RAII Zeroization)

- 📱 Cấp phát độc lập Khóa Phiên Tạm thời (Ephemeral Session Key) tách biệt hoàn toàn ranh giới RAM cho mỗi nhân viên trong ca làm việc.
- 📱 Áp dụng chu trình ZeroizeOnDrop (RAII) tự động trích xuất và ghi đè `0x00` lên toàn bộ vùng nhớ chứa KEK ngay khi tài khoản đăng xuất hoặc qua 5 phút bất động.
- 📱 Sử dụng Store Key Pair neo giữ vĩnh viễn định danh chi nhánh trong chip bảo mật phần cứng (Secure Enclave/StrongBox).

---

### 4.10 Ephemeral Session Provisioning & Role-Based Vault (Kiosk Mode)

- 📱💻 Áp dụng Giao thức Cấp phát Khóa Phiên Tạm thời (Ephemeral Session Key) thông qua cơ chế ủy quyền từ thiết bị của Quản lý đã xác thực YubiKey.
- ☁️🗄️📱 Ứng dụng thuật toán Shamir's Secret Sharing (SSS) để phân mảnh khóa Recovery chuyên dụng cho các trạm Kiosk.
- 📱 Tích hợp kỹ thuật ZeroizeOnDrop đảm bảo giải phóng toàn bộ KEK khỏi RAM ngay khi ca làm việc kết thúc.

### 4.6 ZKP Rate-Limiting & Bảng Nullifier VOPRF — Chống Spam Ẩn danh

- 📱💻🖥️ **Cấp phát Token Mù (Blind Signatures / VOPRF):** Mỗi chu kỳ 1h, Lõi Rust kết nối Auth Server qua Mixnet, nhận rổ 100 Anonymous Token. Auth Server ký bằng phép nhân vô hướng Elliptic Curve — không nhìn thấy Serial Number (Mù hóa 100%).
- ☁️🗄️ **Nullifier Edge Table:** Khi gửi gói Onion, nhúng 1 Token đã giải mù vào header. Exit Node xác thực: VOPRF signature hợp lệ + Bloom Filter O(1) kiểm tra Double-Spending. PASSed → deliver. FAIL/Trùng → DROP tại Edge Boundary — không đánh thức Disk I/O.
- 📱💻🖥️ **Client-Side Triage (Zero-Disk I/O):** Payload E2EE đáng ngờ vào Ring Buffer RAM (<2MB). Lõi gỡ E2EE lấy Sender ID thật đối chiếu Local Trust Graph. Rating thấp → Quarantine, không Write SQLite.
- ⚠️ Constraint: VOPRF xác thực tại Exit Node < 0.2ms/packet. Nullifier Table: 100M entries < 150MB RAM tĩnh.

### 4.11 Cryptographic Nullifier Sets & IdP-Linked Token Revocation

- ☁️ Quản lý danh sách chặn token ẩn danh thông qua Blind Nullifier Sets vận hành tại OPA Gateway.
- ☁️ Kích hoạt MLS `remove_member` Trigger để tự động xoay khóa nhóm và loại trừ thành viên bị cách ly.
- ☁️📱💻🖥️ Áp dụng kỹ thuật Behavioral Fingerprinting trên lớp Blind Metadata nhằm phát hiện mẫu hành vi bất thường phân tuyến theo Role/Dept.

### 4.7 Nghịch lý Mã nguồn Mở và Compiler-Level Guards

- 📱💻🖥️ **Lõi Rust (Open-Core):** Loại bỏ hoàn toàn giải pháp làm rối O-LLVM và Bogus Control Flow gây lãng phí tài nguyên. Tập trung bảo vệ bằng Compiler-Level Guards.
- 📱💻🖥️ **Zeroize Safe Pipeline:** Tách biệt hoàn toàn luồng mã hóa (Synchronous/CPU Bound) và luồng mạng (Async/I/O Bound). Plaintext Key (`Zeroizing<Vec<u8>>`) chỉ tồn tại trong Synchronous Scope. RAII `Drop` ghi đè `0x00` trước khi spawn `tokio::task`.
- 📱💻🖥️ **Compiler-Level Guard:** Plaintext Key Struct **cố tình không implement** trait `Send` và `Sync`. Trình biên dịch Rust báo Compile Error nếu developer vô tình truyền Key qua thread boundary hoặc giữ qua điểm `.await` — Attack Surface = 0 tại compile time.
- 💻🖥️☁️🗄️ **Zero-Knowledge Memory Safety:** Sử dụng `mmap` anonymous và memory tracking để bảo vệ RAM khỏi việc rò rỉ dữ liệu trong khoảng thời gian tồn tại ngắn của Key. Phế bỏ mlock() cưỡng bách.

#### HQ-Audit Zero-Knowledge Identity (Bảo vệ người tố giác)

- 📱💻 Thiết lập Hardcoded `HQ_Audit_PubKey` tại Client để mã hóa dữ liệu tố giác ngay từ nguồn.
- 📱💻 Kích hoạt cơ chế sinh Ephemeral Keypair (Khóa dùng một lần) để loại bỏ hoàn toàn `User_ID` và `Device_ID` khỏi gói tin.
- ☁️ Lưu trữ `HQ_Audit_PrivateKey` trong HSM/Secure Enclave biệt lập tại Ban Kiểm soát HQ.

#### Out-of-Band Domain Fronting & Mesh Fallback (Chống Firewall DPI/Ngắt ngầm)

- 📱💻 Áp dụng kỹ thuật Domain Fronting ngụy trang SNI/Host header qua các CDN lớn (Cloudflare/Microsoft) để bypass DPI.
- 📱💻 Tự động chuyển đổi định tuyến sang mạng Wi-Fi/4G cá nhân (Mesh-to-Internet Fallback) khi phát hiện Federation Bridge bị admin ngắt.
- 📱💻 Phân đoạn tệp tin (Chunking) kết hợp mã hóa AEAD để thay đổi hình thái gói tin trước các bộ lọc kích thước dữ liệu.

### 4.8 Identity & Key Escrow — Sovereignty-First Key Recovery

- 📱💻 **Loại bỏ iCloud Escrow:** Không đẩy Ciphertext lên iCloud Keychain — bảo toàn nguyên tắc **Enterprise Data Sovereignty**. Mọi khóa chỉ rời thiết bị qua các luồng được E2EE bảo vệ.
- 📱💻 Duy trì **Multi-Device Cross-Signing** xác thực chéo giữa các thiết bị trong Vòng tin tưởng Device Ring của tổ chức.
- 📱💻 **Physical Vaulting (BIP39 24-word Recovery Key):** Lưu trữ Recovery Key trong két sắt quản trị vật lý; không có phương án lưu trữ Online nào khác.
- 📱 Cấm lưu private key vào Secure Enclave nếu thiếu FIDO2 attestation. Luôn verify signature list trước khi cấp quyền giải mã local.

### 4.9 Searchable Symmetric Encryption (SSE) & Forward Secrecy

- 🗄️☁️ Xây dựng SSE phân mảnh theo Epoch để giải quyết bài toán xoay khóa trên TEE.
- 💻🖥️☁️ Cấu hình Rust Core sinh `Search_Subkey_Epoch_N` thông qua KDF Chain mỗi khi kích hoạt hàm xoay khóa (nhân sự đổi quyền).
- 📱💻🖥️ Lập trình hàm tạo Blind Index tại Client, bắt buộc đính kèm tag `Epoch_ID`.
- 🗄️☁️ Tại query-time, Rust Core cung cấp mảng `Historic_Tokens` cho TEE Server. Server thực hiện đối chiếu O(1) Token-to-Index. Cấm re-index toàn bộ database.

#### LSH (Locality-Sensitive Hashing) & Garbled Circuits cho TEE

- 📱💻🖥️ Thuật toán MinHash/SimHash để chuyển đổi từ khóa thành mã băm bảo toàn khoảng cách Hamming.
- ☁️🗄️ Mạch xáo trộn (Garbled Circuits) để tính toán khoảng cách giữa các Token trên RAM mã hóa của TEE mà không lộ Plaintext.
- ☁️🗄️ Cơ chế Compaction Index theo Epoch để tối ưu hóa bộ nhớ RAM tĩnh.

#### Encrypted Blind Search qua Soft-Enclave WASM Isolation

- 📱☁️ Token hóa luồng từ khóa thông qua thuật toán băm $HMAC-SHA256(Company\_Search\_Key, keyword)$.
- 📱☁️ Phân mảnh cấu trúc chỉ mục theo định danh Epoch ID phục vụ quá trình xoay vòng khóa (Epoch Rotation).
- ☁️🗄️ Cấu hình truy vấn $O(1)$ Token-to-Index trực diện trên vùng nhớ đã mã hóa bên trong WASM Soft-Enclave, loại bỏ phụ thuộc phần cứng TEE.

---

## 6. API Secret Management

### 6.1 E2EE API Secret Vault & Cryptographic Binding

- ☁️🗄️ **Blind Vault Storage (VPS):** Admin nhập `{name: "OpenAI", value: "sk-xxx"}` → Rust sinh `Vault_Key (AES-256)` chỉ sync giữa Admin devices qua E2EE → `encrypted_blob = AES-256-GCM(Vault_Key, api_key)` → đẩy lên VPS. VPS lưu label + ciphertext — **không biết giá trị thực.**
- 📱💻🖥️ **Cryptographic Binding (Zero-Server):** Admin bấm [+] cấp key cho Bot: Client kéo blob → giải mã trong RAM (<100ms) → `Bot_Bound_Blob = Curve25519_ECIES.encrypt(Bot_Public_Key, api_key)` → DROP(api_key) → đẩy `Bot_Bound_Blob` lên VPS. VPS chỉ mở được bằng `Bot_Private_Key` — không bao giờ rời chip.
- ☁️ **Instant Revoke:** Admin đổi key gốc trong Vault → Rust chạy ngầm `rebind_all_bots()` mã hóa lại toàn bộ `Bot_Bound_Blob` trong < 2 giây.
- ☁️🗄️ **BYOK (Bring Your Own Key):** API Key lưu trong Secure Enclave / OS Keychain — không bao giờ plaintext trên Server.

### 6.2 Phân xử Nội dung trong Môi trường Zero-Knowledge (Blind DAG Store)

- ☁️🗄️ Chỉ đạo Sever xây dựng cấu trúc đồ thị dựa trên Metadata Plaintext (HLC, parents_HLC) hoàn toàn mù với dữ liệu nội dung.
- 📱💻🖥️ Gán mã hóa E2EE cho `Encrypted_payload` từ phía thiết bị để đảm bảo tính Zero-Knowledge lưu trữ.
- 📱💻🖥️ Áp dụng chữ ký số Ed25519 trực tiếp lên từng Node của lưới DAG nhằm neo chặn tính toàn vẹn (Tamper-proof).

### 6.3 Xung đột Audit Log không nhất quán (Split-Brain Resolution)

- 📱💻🖥️ Triển khai cơ cấu san phẳng đồ thị tất định (HLC Deterministic Flattening) bằng sự kết hợp giữa Physical Time và Logical Counter bảo vệ tính nhân quả.
- 📱💻🖥️ Kích hoạt Thuật toán Tie-breaker phán xử qua chuỗi băm Node_ID (Hash MAC) để phân định thứ tự cho các sự kiện xảy ra song song.
- 📱💻🖥️ Ràng buộc cấu trúc Hash Chain nối rễ chuỗi nhằm duy trì tính toàn vẹn tuyến tính của Audit Log phục vụ quá trình truy vết độc lập.

### 6.4 Asynchronous TreeKEM với Epoch Forking & Deterministic Merge (Đứt gãy MLS)

- 📱💻🖥️ Khởi tạo bộ nhớ Keyring State đa nhánh lưu trữ đồng thời nhiều Epoch trong RAM tạm nhằm giải mã các luồng chia tách (Fork) diễn ra song song do Mesh bị phân mảnh.
- 📱💻🖥️ Neo chặn (Anchor) Update Path của phân vùng TreeKEM vào cấu trúc Vector Clock của CRDT nhằm nhận diện chính xác nhánh mã hóa tương ứng.
- 📱💻🖥️ Thuật toán **Tie-breaker (Hash Node_ID)**: Phân xử phi tập trung để chỉ định duy nhất một Super Node thực hiện Merge Commit, kéo toàn mạng lưới sang Epoch nhất quán (Epoch N+2) khi các nhánh hội tụ.
- 📱💻🖥️ Khẩn trương thực thi thủ tục phát tán MLS TreeKEM nhằm tái cấu trúc nhóm bảo mật ngay sau bước sáp nhập Trạng thái CRDT.

### 6.5 Hiệu năng Xử lý Đồ thị tại Biên (Client-Side In-Memory DAG)

- 📱💻🖥️ Đẩy luồng trích xuất dữ liệu thô (In-memory DAG Reconciliation) xuống Client với giới hạn độ phức tạp $O(N \log N)$ cho thao tác xếp đặt HLC.
- ☁️🗄️ Giải tỏa nút thắt IOPS tại cụm trung tâm bằng mô thức Pub/Sub trao đổi siêu dữ liệu đồ thị dạng mù (Zero-Knowledge).
- 📱💻🖥️ Ghi chuỗi Atomic Write đồng bộ trực tiếp xuống bảng SQLite FTS ở bước cuối để chốt khóa trạng thái hợp nhất cục bộ.

---

## 7. Cross-Cluster Federation & Enterprise Deployment

### 7.1 Cross-Cluster Federation Handshake Protocol

- ☁️ **mTLS Mutual Auth (không dùng CA công cộng):** Thiết lập kênh truyền tin cậy giữa các cụm máy chủ HQ và Chi nhánh bằng PKI nội bộ, loại bỏ hoàn toàn sự phụ thuộc vào Certificate Authority công cộng.
- ☁️ **Signed JWT Federation_Invite_Token:** Xác thực lời mời kết nối thông qua Identity Broker (Keycloak/Dex) để ngăn chặn rò rỉ lời mời và giả mạo thông tin kết nối liên cụm.
- ☁️ **Federation Trust Registry:** Lưu trữ Public Key của các Cluster liên kết vào sổ cái PKI nội bộ (`federation_trust_registry`) để định danh vĩnh viễn; cập nhật bất đồng bộ qua CRDT Gossip.
- ☁️ **Sealed Sender Protocol:** Mã hóa header người gửi bằng Public Key người nhận để Server Chi nhánh không thể biết danh tính thực của cấp quản lý HQ — bảo vệ siêu dữ liệu liên cụm.
- ☁️ **Identity Broker (OIDC/SAML):** Keycloak/Dex liên kết định danh OIDC/SAML giữa Tổng công ty và Chi nhánh, cho phép SSO xuyên Cluster mà không cần đồng bộ toàn bộ User Directory.

### 7.2 Federated OPA Policy Engine & Circuit Breaker

- ☁️ **OPA (Open Policy Agent) ABAC tại API Gateway:** Thực thi chính sách ABAC dựa trên `sender_role` và trạng thái `allow_reply` để lọc gói tin liên cụm — chặn Spam và kiểm soát quyền truy cập xuyên tổ chức.
- ☁️ **Rate Limiting (Redis ZSET Sliding Window):** Tự động kích hoạt Circuit Breaker khi tần suất tin nhắn liên cụm vượt ngưỡng an toàn cấu hình; trạng thái OPEN fail-fast về UI trong < 1s.
- ☁️ **Z3 Formal Verification trên Federated Policy:** OPA Policy liên cụm được chạy qua SMT Model → Z3 Solver để phát hiện xung đột chính sách trước khi triển khai.

### 7.3 Immutable Infrastructure-as-Code (IaC) Orchestration — B2B 1-Touch

- ☁️ **Hardened Docker Compose (CAP_IPC_LOCK):** Đóng gói toàn bộ hạ tầng (Blind Relay, PostgreSQL, Redis, NATS) thành một khối bất biến với cơ chế `CAP_IPC_LOCK` bảo vệ vùng nhớ nhạy cảm không bị swap xuống đĩa.
- ☁️ **TeraChat Blind Relay (Rust):** Xử lý định tuyến mù, mã hóa E2EE và thực thi các giao thức mTLS/WebSocket — không lưu bất kỳ Plaintext nào trên disk.
- ☁️ **MinIO Erasure Coding (EC+4):** Sharding dữ liệu trên 3–5 nodes cho phép tự phục hồi khi mất 1 node và tối ưu dung lượng lưu trữ Blind Storage.
- ☁️ **PostgreSQL HA (pgRepmgr + PgPool):** Đảm bảo tính sẵn sàng cao và failover tự động thông qua Streaming Replication; WAL Archiving hỗ trợ Point-in-Time Recovery.
- ☁️ **HA TURN Array (Floating IP):** Đảm bảo độ trễ thấp cho các cuộc gọi WebRTC trong môi trường VPS Cluster với cơ chế Floating IP failover < 3s.

### 7.4 Secure Workspace Bootstrap & HKMS

- 📱💻🖥️☁️ **HKMS (Hierarchical Key Management System):** Phân cấp Master Key thành các KEK (Key Encryption Key) và DEK (Data Encryption Key) để mã hóa database và file trong toàn bộ hệ sinh thái. Sơ đồ: `Master Key → KEK → DEK → [DB / File / Channel / API Key]`.
- 📱💻🖥️☁️ **Master Key Binding (Hardware Enclave):** Giam khóa Master trong Hardware Enclave (HSM/TPM 2.0/Secure Enclave) của Admin; yêu cầu lưu trữ file `.terakey` ngoại vi trên thiết bị vật lý. Master Key không bao giờ rời chip.
- ☁️ **Zero-Knowledge Blind Storage (MinIO):** Lưu trữ ciphertext theo đường dẫn `cas_hash` để triệt tiêu mọi thông tin về tên file thực tế — Server không biết gì về nội dung hay metadata file.
- 📱💻🖥️ **KMS Bootstrap Ritual:** Khởi tạo Workspace kích hoạt xuất mảnh khóa ra các thiết bị phần cứng FIDO2 (YubiKey/Smartcard); Lõi Rust Block tạo Database cho đến khi Admin xác nhận lưu Key Backup thành công.

### 7.5 Push Key Rotation & Hardware-Backed Key Storage

- 📱☁️ **Push Key Rotation đồng bộ MLS Epoch:** Mỗi lần MLS Epoch Rotation xảy ra, Push Notification Key được rotate đồng bộ để đảm bảo tính Forward Secrecy cho mọi thông báo — kẻ tấn công có Key cũ không giải mã được Push cũ.
- 📱 **Shared Keychain (iOS App Group):** NSE (Notification Service Extension) truy cập khóa giải mã thông báo trong trạng thái Background thông qua Shared Keychain mà không cần can thiệp sinh trắc học — giữ footprint < 24MB.
- 📱 **StrongBox Keymaster (Android):** Lưu trữ Symmetric Push Key tại cấp phần cứng StrongBox, ngăn chặn việc xuất khóa trái phép kể cả khi Root/ADB.

---

## 8. AI Infrastructure Security & Legal Compliance

### 8.1 Soft-Enclave Isolation — AI Worker Security

- ☁️🗄️ **Software-based Isolation (Wasmtime):** Cô lập vùng nhớ AI Worker bằng WASM Sandbox cấp độ phần mềm; ngăn chặn trích xuất bộ nhớ trái phép mà không yêu cầu phần cứng Intel SGX / AWS Nitro chuyên dụng.
- ☁️ **Thread-Pool Isolation (Bounded MPSC Channel):** Phân tách `core-messaging-runtime` (ưu tiên cao) và `ai-heavy-io-runtime` (trọng tải AI) qua Bounded MPSC Channel để bảo vệ hiệu năng hệ thống messaging khỏi quá tải AI.
- ☁️ **Circuit Breaker (AI Latency p99 > 1500ms):** Tự động chuyển trạng thái OPEN và fail-fast về UI nếu AI Latency p99 > 1500ms hoặc Packet Loss > 5% trong 10s — bảo vệ throughput messaging core.

### 8.2 Threshold Cryptography Escrow (Trích xuất Pháp lý Không Backdoor)

- 📱💻🖥️☁️ **Shamir's Secret Sharing (SSS):** Băm nát Private Key thành $N$ mảnh phân tán, loại bỏ điểm yếu Master Key đơn điểm; mặc định 3-of-5 hoặc cấu hình M-of-N theo chính sách doanh nghiệp.
- 💻🖥️ **Lagrange Interpolation tái tạo Escrow_Private_Key:** Thực hiện nội suy Lagrange trực tiếp trong vùng nhớ RAM được bảo vệ bởi ZeroizeOnDrop; plaintext Key chỉ tồn tại trong RAM < 100ms.
- ☁️ **Escrow Ciphertext Blob:** Lưu trữ khóa phiên (Session Key) được mã hóa bằng cơ chế KEM tại Server — Server chỉ thấy ciphertext, không thể tự giải mã mà không có đủ mảnh khóa.

### 8.3 KMS Bootstrap Ritual & Multi-Sig Hardware Fragments

- 📱💻🖥️ **KMS Bootstrap + FIDO2 YubiKey/Smartcard:** Khởi tạo Workspace và xuất mảnh khóa ra các thiết bị phần cứng FIDO2 (YubiKey hoặc Smartcard); yêu cầu xác thực vật lý để tái hợp nhất khóa.
- 📱💻🖥️☁️ **Master Key trong HSM/Secure Enclave (Hardware Root of Trust):** Khóa Master không bao giờ rời chip vật lý; mọi thao tác ký/giải mã đều diễn ra trong Enclave với xác thực sinh trắc học bắt buộc.
- 📱💻🖥️ **ZeroizeOnDrop (RAII):** Thực hiện ghi đè `0x00` xóa sạch dấu vết khóa trong RAM ngay sau khi phiên giải mã kết thúc; không có window nào để key tồn tại trên heap.

### 8.4 Immutable Audit Log & Append-Only Hash Chain

- ☁️ **HIPAA/SOC2 Compliant Audit Log:** Ghi lại bắt buộc mọi hành vi trích xuất dữ liệu nhạy cảm với timestamp chống giả mạo; log được lưu trên Append-Only storage không thể sửa đổi ngược.
- 📱💻🖥️☁️ **Ed25519 Digital Signature:** Xác thực tính nguyên bản và chống chối bỏ (Non-Repudiation) cho toàn bộ lịch sử chat được trích xuất; mỗi entry Audit Log mang chữ ký Ed25519 độc lập.
- 📱💻 **Dead Man Switch (Monotonic Hardware Counter):** Kết hợp Monotonic Hardware Counter (TPM 2.0/Secure Enclave) với timestamp để chống tấn công quay ngược thời gian (Time Travel Attack) trên Audit Log; `Counter < Server's Value` → từ chối + Self-Destruct.

## 9. Lưu trữ và Khôi phục Định danh E2EE (Cloud/Private Server Sync)

### 9.1 Đồng bộ hóa Dữ liệu Mã hóa (E2EE Cloud Backup)

- ☁️🗄️ **E2EE Cloud Backup (Zero-Knowledge):** Lõi Rust mã hóa `cold_state.db` bằng `Device_Key` (Secure Enclave/StrongBox) trước khi đẩy lên Cloud (hoặc Private Server nội bộ). Server chỉ thấy Ciphertext — không có plaintext nào rời thiết bị.
- 📱💻 **Khôi phục Định danh (Biometric-backed Restore):** Khi thiết bị mới được kích hoạt, người dùng xác thực bằng FaceID/TouchID hoặc TPM 2.0. Lõi Rust tải Ciphertext về và giải mã cục bộ — không cần thiết bị phần cứng ngoại vi.
- 📱💻 **Recovery Phrase (BIP-39 Mnemonic):** Khi thiết lập lần đầu, hệ thống phát sinh 24-word Mnemonic (BIP-39 chuẩn). Người dùng ghi offline và lưu an toàn. Dùng Mnemonic + Biometric để khôi phục `Device_Key` trong mọi kịch bản mất máy.

### 9.2 Truy cập Bộ nhớ Thời gian Hằng số (Side-Channel Timing Attack & Memory Dump Defense)

> **Mối đe dọa:** Biến động độ trễ truy cập nhớ tin rầy (Cache Timing) tiết lộ khóa mật mã qua kênh kề (Side-Channel).

- 💻📱 **Fixed-Size Ring Buffer (Constant-time Flattening):** Sử dụng Fixed-Size Ring Buffer để làm phẳng (flatten) dao động độ trễ Page Fault. Kiến trúc đếm địa chỉ truy cập đồng nhất với $O(1)$ bất kể ngữa ép: Không lập biểu Âm mưu của Cache-miss-based Spy.
- 💻📱 **`madvise()` + Monotonic Clocking (ISO 27001):** Ràng buộc `madvise(MADV_SEQUENTIAL | MADV_WILLNEED)` kết hợp Monotonic Hardware Clock để loại bỏ hiệu ứng phân nhiễu (Jitter); ghi nhận timestamp theo chuẩn ISO 27001 đe dệ audit thời gian truy cập nhớ.
- 💻📱 **`ZeroizeOnDrop` (RAII) trước `munmap()`:** Thực thi ghi đè `0x00` toàn bộ nội dung vùng nhớ cục bộ vật lý trước khi trả về qua `munmap()` — ngăn chặn Memory Dump ngầu nhiên ở mọi thời điểm sau Secure Scope Exit.

### 9.3 Lock-Free Seqlock (Chống DoS Futex từ .tapp)

> **Mối đe dọa:** `.tapp` độc hại có thể giữ Mutex lock vĩnh viễn, triệt tiêu khả năng ghi của Lõi Rust (DoS Futex Deadlock).

- 🗄️ **Sequence Counter AtomicU32 (Header Slot):** Đặt Header 8-byte chứa `AtomicU32` Sequence Counter tại vị trí đầu mọi Shared Memory Slot. Giá trị lẻ = đang ghi; giá trị chữn = sẵn sàng đọc.
- ☁️ **Preemptive Write Bypass (Quyền ghi tuyệt đối):** Lõi Rust tăng Counter (+1), thực hiện ghi dữ liệu, tăng Counter (+1) lần nữa — không đợi WASM Sandbox. WASM chỉ là Reader; không có Mutex lock nào được phép chiếm giữ qua ranh giới.
- 💻 **Lock-free Fast-path Read (Retry Loop):** Phía WASM Reader kiểm tra Counter trước và sau khi đọc; nếu không khớp → Retry Loop tự động. Reader không bao giờ nắm giữ Kernel Resource.

### 9.4 Generational Seqlock + Futex Synchronization (Use-After-Free Defense)

> **Mối đe dọa:** Lỗ hổng Use-After-Free (UAF) và Memory Corruption tại ranh giới Rust–WASM do tham chiếu con trỏ củ sau khi slot bộ nhớ đã được tái sử dụng.

- 🗄️ **Header 8-byte AtomicU32 Sequence Counter:** Mỗi Shared Memory Slot mang một đồng hồ thế hệ (Generation Count) bất biến khóa chặt vào Header. Giá trị chỉ tăng — không bao giờ giảm.
- 💻 **`Atomics.load` Polling (User Space Fast-path):** Phía WASM Reader thực hiện `Atomics.load` kiểm tra `Header.generation == expected_generation` trước mỗi chu kỳ đọc — phát hiện lệch pha thế hệ ngay tại User Space mà không cần toi Syscall.
- ☁️ **`ZeroizeOnDrop` Crypto-Shredding trước tái cấp phát Slot:** Lõi Rust thực thi Crypto-Shredding (ghi đè `0x00`) và tăng Generation Counter trước khi tái sử dụng Slot bao giờ.

### 9.5 Gian lận Logic Giấy phép (Cryptographic Entanglement & O-LLVM Obfuscation)

> **Mối đe dọa:** Kẻ tấn công vá trực tiếp nhị phân Kiểm tra License để bỏ qua ngưỡng xác thực (License Patching).

- 🗄️ **Cryptographic Entanglement (Vướng vít Mật mã):** Ràng buộc License vào hàm dẫn xuất khóa: $KDF(\text{DeviceIdentityKey} + \text{License\_Token\_Signature} + \text{Current\_Epoch}) = \text{Master\_Unlock\_Key}$. Thiếu bất kỳ yếu tố nào → Lõi Rust tạo sai khóa → mọi dữ liệu giải mã AEAD đều rác ngay lập tức.
- 💻 **O-LLVM Control Flow Flattening:** Làm phẳng (flatten) và xáo trộn toàn bộ State Machine kiểm tra License — biến cấu trúc CFG thành mê cung phi tuyến đưa các công cụ dịch ngược như IDA Pro/Ghidra vào trạng thái mù hòa.
- 🖥️ **Bogus Control Flow (Dead Code Injection):** Bơm mã chết (Dead Code) sinh động vào binary để tăng gấp đôi độ phức tạp phân tích CFG, triệt tiêu khả năng cụ thể hóa (concretize) các nánh điều kiện của State Machine.

### 9.6 Tấn công Quay ngược Thời gian (Monotonic Counter Hardware-Backed Validation)

> **Mối đe dọa:** Kẻ tấn công chỉnh giờ (Clock Rollback) và hồi phục Snapshot (Time-Travel Attack) bằng cách giả mạo thời gian hệ thống.

- 🗄️ **TPM 2.0 / Secure Enclave Monotonic Counter:** Truy vấn Monotonic Counter phần cứng — giá trị chỉ tăng, không được reset bằng phần mềm. Trên iOS sử dụng Secure Enclave Counter; trên Desktop dùng TPM 2.0 NvCounter.
- 📱 **`Last_Seen_Timestamp` bất biến:** Duy trì biến `Last_Seen_Timestamp` trong vi mạch bảo mật; nếu OS_Time < Hardware_Counter → cảnh báo hệ thống ngay lập tức.
- 💻 **Crypto-Shredding & Session_Key Wipe:** Khi phát hiện sai lệch thời gian ($OS\_Time < Hardware\_Counter$), Lõi Rust thực hiện `ZeroizeOnDrop` xóa sạch `Session_Key` — dữ liệu kích hoạt tự hủy trước khi rơi vào tay tấn công.

### 9.7 Khôi phục Ngoại tuyến và Chống Nhân bản (HSM Sub-CA Anti-Cloning)

> **Mối đe dọa:** Kẻ tấn công Sao chép (Clone) kých hoạt các `DeviceIdentityKey` vào nhiều thiết bị, qua mặt cơ chế Quota.

- 🗄️ **HSM Sub-CA (FIPS 140-3 Level 4):** Hardware Security Module chuẩn FIPS 140-3 Level 4 thực hiện ký `DeviceIdentityKey` mới — khóa Private Key của Sub-CA không bao giờ rời chip.
- 🗄️ **Decrementing Monotonic Counter (Hard Quota):** Mỗi lần ký chứng chỉ mới, HSM giảm biến đếm ngoài tuyến không đảo ngược; khi biến đếm = 0, HSM từ chối mọi yêu cầu phát hành chứng chỉ mới — chống nhân bản ở tầng Silicon.
- 🖥️ **Offline Ed25519 Signing (Hầm ngầm):** Ký thắng `DeviceIdentityKey` mới tại Hầm ngầm không kết nối mạng; chỉ truyền Signed Certificate ra ngoài qua USB mãt mã.

### 9.8 Tấn công Freeze-and-Restore (TPM2_Quote Liveness Challenge)

> **Mối đe dọa:** Kẻ tấn công chụp Snapshot trạng thái TPM và nạp lại (Replay) nhằm giả mạo định danh phần cứng đã được xác thực.

- 🗄️ **256-bit Random Nonce in `TPM2_Quote`:** Chèn 256-bit `Random_Nonce` mới hoàn toàn vào lệnh `TPM2_Quote` mỗi phiên xác thực. Snapshot Replay không bao giờ tái tạo được Nonce hiện tại — kiểm tra tất bại ngay.
- ☁️ **EK Certificate Validation (Nhà sản xuất):** Xác thực Attestation Certificate với Public Key EK do Nhà sản xuất TPM (Infineon/STMicro) cung cấp — chứng minh thiết bị vật lý thật, không phải SW emulator.
- 🗄️ **PCR Binding vào KDF:** Ràng buộc trạng thái thanh ghi PCR (Platform Configuration Registers) lúc Boot vào hàm $KDF$ sinh `Session_Key`; PCR thay đổi (do Rollback/Tamper) → KDF sinh sai khóa → toàn bộ cơ sở dữ liệu nhắm dướng (decryption failed).

### 9.9 Blind Relay Isolation (Bảo vệ Toàn vẹn Dữ liệu tại Biên)

> **Mối đe dọa:** Server giả mạo (Rogue Server) nắm giữ Source of Truth có thể sửa Hash Chain để che giấu tấn công phân tầng.

- ☁️ **Tước bỏ Source of Truth:** Server Blind Relay chỉ truyền Ciphertext opaque — không có đầu ra API nào dụng lại dữ liệu plaintext. Source of Truth nằm Hoàn toàn trên thiết bị đầu cuối.
- 🗄️ **Audit Log Ed25519 độc lập:** Mọi thay đổi trạng thái (State Transition) được ghi kèm chữ ký Ed25519 riêng của Client — Server không thể can thiệp vào cột chữ ký mà không phá vỡ tính toàn vẹn Hash Chain.
- 💻 **ZeroizeOnDrop khi phát hiện Hash Chain bị gãy:** Khi `Root_Hash` local ≠ Root_Hash quốc hội (Quorum), Lõi Rust tự động thực thi `ZeroizeOnDrop` xóa sạch khóa giải mã — vô hiệu hóa bất kỳ cuộc tấn công khai thác dữ liệu sau đó.

### 9.10 Giao thức Bằng chứng Ém nhẹm (Proof of Withholding)

> **Mối đe dọa:** Server độc hại cố tình giữ lại (Withholding) một phần DAG Branch nhằm che khuất thông tin khẩn cấp trong môi trường nội bộ.

- 📱 **Wi-Fi Direct / JSI Delta-State Sync:** Khi phát hiện DAG Branch bị thiếu, Cliển t lập tức mở kênh Wi-Fi Direct / JSI để tải đoạn Branch bị thiếu từ Peer xung quanh — không qua Server.
- 💻 **Ed25519 Signature Branch Verification:** Kiểm tra từng Node trong Branch tải về; từ chối merge nếu chữ ký không khớp với `DeviceIdentityKey` của người gử.
- 🖥️ **Circuit Breaker Socket Egress:** Sau 3 lần Server liên tiếp trả Delta rỗng trong khi Peer Gossip xác nhận dữ liệu hiện tại → Circuit Breaker cắt kết nối vật lý thiết bị khỏi Server đó và chuyển sang Mesh Mode.

---

*Xem `Feature_Spec.md` cho App-layer. Xem `Function.md` cho Product flows.*

---

*Xem `Feature_Spec.md` cho App-layer. Xem `Function.md` cho Product flows.*
