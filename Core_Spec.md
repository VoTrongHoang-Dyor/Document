# Core_Spec.md — TeraChat V0.2.2

> **Audience:** DevOps · Backend · Security Engineer
> **Scope:** Infrastructure, Security & Cryptography, Network Protocols — Implementation-level only.

---

## 0. Data Object Catalog (Danh mục Đối tượng Dữ liệu)

> Mỗi object liệt kê dưới đây là một **đơn vị dữ liệu** độc lập có schema, vòng đời, và ràng buộc bảo mật rõ ràng. Các thuật toán (xem Section 4–5) chỉ là *operations* tác động lên những object này.

### 🔑 Domain: Cryptographic Identity

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `DeviceIdentityKey` | Ed25519 Key Pair | Secure Enclave / StrongBox | Permanent (hardware-bound) | §4.3 |
| `Company_Key` | AES-256-GCM Root Key | HKMS (wrapped by DeviceKey) | Per-workspace, rotated on member exit | §4.1 |
| `Epoch_Key` | MLS Leaf Key | In-memory only (`mlock`) | Per MLS Epoch, zeroized on rotation | §4.2 |
| `ChunkKey` | AES-256-GCM Ephemeral | Rust `ZeroizeOnDrop` struct | Alive for 1 chunk (~2MB), then zeroized | §5.18 |
| `Session_Key` | ECDH Curve25519 Derived | RAM (ephemeral) | Per session, zeroized after disconnect | §5.10.2 |

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

### 1.1.2 Peer-to-Peer Social Escrow — Offline Device Recovery (Phục hồi Thiết bị Ngoại tuyến)

> **Bài toán:** Nhân viên mất thiết bị khi Zone 1 (máy chủ) đang sập và không có iCloud Keychain. Không có luồng nào ở 1.1.1 giải quyết được trường hợp này.

**Cơ chế Mạng lưới Niềm tin Ngang hàng (Social Escrow):**

- 📱 **Phân mảnh khóa tự nguyện:** User khởi tạo tính năng Social Escrow trong Settings → Lõi Rust phân mảnh `Device_Key` bằng **Shamir Secret Sharing (M-of-N, mặc định 3-of-5)** → mỗi mảnh được gói E2EE bằng public key của đồng nghiệp được chọn → phân phối ngầm qua BLE + AES-256-GCM khi hai thiết bị ở gần nhau.
- 📱 **Hardware-bound Trust Token:** Mỗi đồng nghiệp lưu mảnh Key của bạn dưới dạng **Offline Trust Token** bên trong Secure Enclave của họ. Dữ liệu được `mlock()`'d và không thể đọc được plaintext kể cả với chính họ.
- 📱 **Luồng Phục hồi BLE SOS:**
  1. Thiết bị mới cài TeraChat → phát beacon BLE `RECOVER_DEVICE` (chứa `user_id` đã ký bởi Enterprise CA).
  2. Đồng nghiệp lân cận nhận ToastNotification: *"[Tên] yêu cầu phục hồi khóa — Bấm để phê duyệt"*.
  3. Đồng nghiệp xác nhận bằng Biometrics (FaceID/TouchID) trên máy của họ.
  4. Khi đủ **ngưỡng M** phê duyệt (mặc định 3), Lõi Rust thu thập đủ mảnh → tái cấu trúc `Device_Key_old` → sinh `Device_Key_new` ràng buộc với phần cứng mới → tự động hủy `Device_Key_old` và phân phối mảnh Escrow mới.
  5. Toàn bộ luồng diễn ra **100% offline** — không cần Zone 1 (máy chủ) khả dụng.
- ☁️ **Fallback Admin (khi Server khả dụng trở lại):** Admin Console → User Management → `[Revoke Device_Key cũ]` + `[Re-provision]` → Lõi Rust cấp Identity mới qua SCIM 2.0.
- 📱 **Bảo vệ chống lạm dụng:** Beacon BLE SOS phải được ký bởi chứng chỉ Enterprise CA hợp lệ. Đồng nghiệp chỉ thấy yêu cầu từ người trong cùng **organizational unit (OU)**. Mỗi `user_id` chỉ được phép phát SOS **1 lần/24h** để chống replay attack.

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
| **TEE** | Trusted Execution Environment (Intel SGX / AWS Nitro). AI Worker chạy isolated — Cloud provider không đọc được. |

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

### 2.3 Phân rã Lõi (Dynamic Micro-Core Loading)

- 📱💻 Khai thác Dynamic Library Loading (DLL/dylib) điều phối nạp/rút các phân hệ linh động theo từng ngữ cảnh giao tiếp.
- 📱💻 Khởi động cơ chế Just-In-Time (JIT) Micro-Core nhằm đè bẹp dung lượng RAM thường trực của lõi hệ thống xuống mức tối thiểu tuyệt đối.
- 📱💻🖥️ Áp dụng Engine mã hóa hậu lượng tử Kyber768 bảo đảm tương lai an toàn trước kỷ nguyên Shor Algorithm (Thuật toán Shor).

### 2.4 Trạng thái Ảo hóa (Cloud-Edge TEE-Backed Stateless Ephemeral Client)

- ☁️ Điều hướng luồng trạng thái dữ liệu ủy quyền sang vùng thực thi tin cậy TEE Enclave (Intel SGX / AWS Nitro) đặt tại Cloud-Edge.
- 📱 Kiến nối kênh truyền E2EE Tunneling chọc thẳng từ thiết bị di động vào bộ nhớ RAM cấu trúc TEE mà không chạm đĩa cứng máy chủ.
- 📱 Loại bỏ triệt để SSD I/O bottleneck nội bộ máy qua mô thức Zero-Local-Storage, biên dịch trọn vẹn trạng thái App vào luồng Virtual Memory.

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

#### Air-Gapped Linear Memory Isolation (Chống trích xuất khóa từ RAM)

- 📱💻🖥️ Cấp phát dải bộ nhớ ảo (Linear Memory) hoàn toàn độc lập và cách ly cho WASM Sandbox để ngăn chặn con trỏ (pointer) thoát luồng.
- 📱💻🖥️ Khóa cứng vùng nhớ chứa `Company_Key` và `Device_Key` bằng lệnh `mlock()` tại Lõi Rust để chống quét (scan) hoặc trích xuất (dump) RAM của hệ thống.

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

- 📱💻🖥️ Sinh cặp khóa PQ trên phân vùng RAM được bảo vệ bởi `mlock()` và `MAP_CONCEAL` để ngăn chặn rò rỉ vào file Swap.
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

#### Tấn công Phân tích Điện năng (Power Analysis)

- 📱💻🖥️ Chèn ngẫu nhiên **Lệnh giả (Dummy Instructions/NOPs)** vào giữa luồng xử lý mã hóa làm nhiễu loạn biểu đồ tiêu thụ điện áp vật lý.
- 📱💻🖥️ Xáo trộn luồng tính toán qua **Instruction Shuffling** với các phép toán vô nhân quả để tước đoạt khả năng tìm điểm khớp Correlation.
- 📱💻🖥️ Áp dụng **Dithering** cường độ cao nhằm vô hiệu hóa hoàn toàn kỹ thuật Differential Power Analysis (DPA) nhắm vào CPU.

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
         ├──> [Zone 1A: Enterprise Private Cluster — Dell/HPE/IBM On-Prem]
         │      ├─ K8s Control Plane (HA: 3 Master Nodes)
         │      ├─ TEE Enclave (Intel SGX / AWS Nitro) — AI Worker
         │      ├─ MinIO Storage (Erasure Coding: EC+4)
         │      └─ PostgreSQL HA (pgRepmgr + PgPool)
         ├──> [Zone 2: Federation Bridge]
         │      ├─ mTLS Mutual Auth (không dùng CA công cộng)
         │      ├─ Sealed Sender Protocol
         │      └─ Cluster A ↔ Cluster B giao tiếp an toàn
         └──> [Zone 1B: VPS Cluster — Vultr / DigitalOcean / Linode]
                ├─ Standard Hardened Docker (CAP_IPC_LOCK enforced)
                ├─ MinIO Storage (S3-Compatible)
                └─ HA TURN Array (WebRTC Relay, Floating IP)
```

| Quy mô | Topology | Storage |
|---|---|---|
| 10k Users | Single K8s Cluster (3–5 Nodes) | MinIO Local |
| 100k Users | Geo-Federated Clusters | PostgreSQL Geo-Partitioning + HA TURN Array |
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

### 3.3 Cơ sở Hạ tầng & Triển khai DevOps (Infrastructure & DevOps Deployments)

#### Triển khai VPS/Server Vật lý 1 Chạm (Enterprise B2B)

- ☁️🗄️ **Immutability & Docker Compose:** Đóng gói nguyên cụm Server (Blind Relay Server, PostgreSQL quản lý metadata, NATS Pub/Sub) vào duy nhất một tệp `docker-compose.yml`.
- ☁️🗄️ **1-Touch Scripting:** Khách hàng doanh nghiệp hoặc MSP chỉ cần chạy lệnh `curl -sSL https://terachat.io/install.sh | bash` trên Ubuntu. Tiến trình tự tải cấu hình, xin Let's Encrypt SSL/TLS, và dựng trọn vẹn cụm hạ tầng an toàn trong 45 giây.

#### Thiết quân luật Hệ điều hành (OS Hardening)

- ☁️🗄️ Tắt hoàn toàn phân vùng Swap trên cấp độ OS nhằm triệt tiêu độ trễ, đảm bảo tiến trình Kubelet vận hành ổn định không gián đoạn.
- ☁️🗄️ Nạp bắt buộc các cấu trúc Kernel Modules (`br_netfilter`, `overlay`) và kích hoạt `bridge-nf-call-iptables = 1` mở đường cho năng lực lọc luồng mạng nội bộ K8s.
- ☁️🗄️ Đẩy giới hạn `fs.inotify.max_user_instances` lên trần áp suất (512+) tránh rủi ro tràn bộ nhớ đệm khi Longhorn và MinIO quản trị hàng triệu mảnh tệp tin li ti.
- 🖥️ Lập trình lá chắn `kernel.kptr_restrict=2` và `kernel.panic_on_oops` ngăn chặn hành vi Memory Dump và che giấu địa chỉ con trỏ lõi (Kernel Pointers) khỏi User Space.
- 🖥️ Củng cố hệ thống khởi tạo (tera-init) rà soát chuỗi Entropy ngẫu nhiên tinh khiết từ `/dev/urandom` và đối chiếu tập lệnh phần cứng AES-NI rễ trước vạch xuất phát.

#### Truyền thông nội bộ VPS (Secure Overlay)

- ☁️🗄️ Cấu hình mạng riêng ảo WireGuard theo dải Full-Mesh đục thông các đường hầm P2P trực tiếp rẽ nhánh giữa mọi VPS trong cụm.
- ☁️🗄️ Chấp pháp chính sách Default Deny thông qua Network Policy (Calico/Cilium) khóa chặt mọi đường truyền Container-to-Container, chỉ thông hành các kết nối được whitelist tường minh.

#### Phân tán hóa Cụm điều khiển (Orchestration)

- ☁️🗄️ Triển khai phi phân quyền lõi Kubernetes qua nền tảng RKE2 (Rancher Next Generation) áp đặt quy chuẩn bảo mật cao nhất hiện nay.
- ☁️🗄️ Khắc phục kịch bản sập phân nửa số trạm bằng cách lên lịch snapshot dữ liệu `etcd` tự động sao lưu lên vũng lưu trữ dị địa (S3/NAS) mỗi 1 giờ.
- ☁️🗄️ Loại trừ bề mặt tấn công Attack Surface của Docker bằng việc thắt chặt hệ sinh thái Runtime Security thông qua giao thức CRI-O/Containerd.

#### Lưu trữ phân tán (Persistence)

- ☁️🗄️ Căng dãn Longhorn Block Storage kích hoạt Synchronous Replication (Replicas=3) bảo vệ tính toàn vẹn đa luồng của Database (SQLite/PostgreSQL).
- ☁️🗄️ Trải chuỗi MinIO Object Storage qua cơ chế Erasure Coding (EC) bảo toàn dữ liệu E2EE Blobs ngay cả khi thất thoát 1-2 ổ cứng vật lý.

#### Công khai Dịch vụ & TLS (Ingress)

- ☁️🗄️ Áp đặt hạ tầng khóa công khai Enterprise PKI thông qua `step-ca` bảo chứng định danh nội bộ khép kín.
- ☁️🗄️ Phong tỏa lưới Microservices bằng giao thức Mutual TLS (mTLS) yêu cầu xác nhận chứng chỉ chéo hai chiều (vd: Blind Relay ↔ MinIO) chặn đứng nguy cơ leo thang đặc quyền.

#### Khởi tạo Zero-Knowledge (Bootstrap)

- 💻🖥️🗄️ Admin cấu hình **Static IP/DNS** của Master Node thông qua file `config.yaml` tại thời điểm triển khai On-Premise. Không phụ thuộc vào Cloud Provider Metadata API.
- ☁️ Kết hợp **Gossip-based Discovery** (Memberlist) để Worker động tìm nún Cluster WireGuard LAN ảo sau khi Bootstrap thành công.
- ☁️ Thỏa thuận trao đổi **Pre-shared Key (PSK)** phân mảnh qua `inventory.ini` thiết lập đường hầm xác thực nguyên thủy.

#### Hardware-Attested mTLS Tunneling (Đường hầm mTLS Bootstrap)

- 📱💻☁️ Thiết lập đường hầm mTLS hai chiều sử dụng Root CA doanh nghiệp đã ghim (pinned) trong Secure Enclave/TPM thiết bị Admin.
- 📱💻☁️ Tích hợp cơ chế **Remote Attestation** (qua Apple App Attest / Android Play Integrity) để đảm bảo chỉ những thiết bị nguyên bản (không root/jailbreak) mới được quyền thiết lập kênh truyền tin với VPS.
- 📱 Sử dụng mã QR **chỉ để truyền tải** cấu hình định tuyến (IP/Port). Tuyệt đối không chứa dữ liệu nhạy cảm hay Token bên trong QR code để khóa chặt rủi ro giả mạo OOB.

#### Enclave-Bound Master Key (Hardware Pinning)

- 📱💻🖥️ Master Key (`.terakey`) được sinh ra và gói gọn (wrapped) trực tiếp bên trong không gian Secure Enclave/StrongBox, tuyệt đối không bao giờ được phép export sang filesystem hay RAM của OS.
- 📱 Yêu cầu **User Presence** (Biometric/PIN) mỗi khi cần ký giải mã Bootstrap Token, vô hiệu hóa việc sử dụng khóa tự động kể cả khi thiết bị đã được mở khóa.
- 📱💻 Định danh chéo thiết bị thông qua Hardware-ID Binding để ràng buộc Master Key chỉ có hiệu lực duy nhất trên phần cứng thiết bị Admin chỉ định.
- 📱💻🖥️ Kích hoạt lính canh **Zeroize RAM** tiêu hủy tức khắc khóa Root trên vùng nhớ động vừa nạp ngay khoảnh khắc chuyển giao vĩnh viễn vào **Secure Enclave/TPM 2.0**.
- ☁️🗄️ Khởi tạo môi trường MinIO Provisioning đính kèm cơ chế Server-Side Encryption (SSE-KMS) sử dụng vỏ bọc bao ngoài xẻ từ `Company_Key`.
- ☁️🗄️ Quản lý Server ở trạng thái giữ "chìa khóa đã bị khóa", ép buộc thao tác mở khóa dịch vụ phải nhận tín hiệu chứng thực E2EE trực tiếp từ thiết bị cầm tay.

#### Phòng thủ Control Plane & Giám sát Hạt nhân K8s (Kubernetes Security)

- ☁️ Ngăn chặn tuyệt đối giả mạo Container Image tại Master Node bằng kiến trúc **Supply Chain Integrity** kết hợp **Sigstore/Cosign** ký số tệp nhị phân ngay tại CI/CD Pipeline biệt lập.
- ☁️ Yêu cầu Kubelet xác thực Digital Signature đối xứng công khai phân phối sẵn trước khi kéo Image nhằm vô hiệu hóa nỗ lực tiêm mã độc vào nguồn gốc.

#### Container Signature Pinning via Sigstore/Cosign (Supply Chain MITM)

- ☁️🗄️ Kích hoạt **Sigstore/Cosign Admission Controller** trên cụm K8s nội bộ xác minh Image Signature tại thời điểm khởi tạo Pod.
- ☁️🗄️ Đối soát mã băm **SHA256 tĩnh** của Container Image — cấm dùng tag `latest` để chống Supply Chain Attack kiểu "chết cá" im lặng.
- ☁️🗄️ Cơ chế chặn khởi tạo Pod (`ImagePullBackOff`) nếu chữ ký không khớp với **TeraChat HQ Public Key**, kết hợp cảnh báo tập trung qua Falco + OPA.
- ☁️ Dựng chốt chặn **Zero-Trust API Admission Gatekeeping** sử dụng Validating Admission Webhook kết hợp **Kyverno/OPA Gatekeeper** sàng lọc toàn bộ các tệp định tuyến `kubectl apply`.
- ☁️🗄️ Thiết lập Security Context Constraints khắt khe, áp đặt cờ `readOnlyRootFilesystem: true` và Immutable Root Filesystem khóa cứng khả năng ghi đè hệ điều hành lõi.
- ☁️ Cưỡng ép quy chuẩn Pod Security Standards (PSS) vào chế độ `restricted` với `allowPrivilegeEscalation: false` tước bỏ 100% đặc quyền Root của Container.
- ☁️🗄️ Đẩy lùi nguy cơ trích xuất dữ liệu nhạy cảm từ `etcd` bằng cơ chế **Hardware-Backed Envelope Encryption** qua KMS Plugin nối trực tiếp với chip bảo mật.
- ☁️🗄️ Giam cầm Key Encryption Key (KEK) vào **TPM 2.0** hoặc **Secure Enclave** vật lý, khiến kho báu `etcd` hoàn toàn vô nghĩa đối với bất kỳ ai nắm giữ ổ cứng nhưng thiếu hụt chip giải mã.
- ☁️ Chống can thiệp tầng Kernel và Binary bằng lá chắn **eBPF-Based Runtime Surveillance** sử dụng **Falco** giám sát Syscall cực đoan theo thời gian thực.
- ☁️ Nhận diện tức thì mọi hành vi ghi tệp trái phép vào thung lũng `/etc/kubernetes` qua màng lọc Extended Berkeley Packet Filter.
- 📱💻🖥️☁️ Thiết đặt tín hiệu **Self-Destruct Signal** cắt đứt toàn diện kết nối mTLS và ra lệnh OPA/Kyverno thiêu rụi dữ liệu (Sandbox Escape Self-Destruct) ngay tại khoảnh khắc eBPF đánh tín hiệu xâm nhập.

#### Điện toán Bảo mật Phần cứng (Confidential Computing) & AI Privacy Pipeline

- ☁️🗄️ Mã hóa 100% dung lượng bộ nhớ động qua tính năng **Hardware-level RAM Encryption (AMD SEV-SNP)** biến mọi dữ liệu RAM vật lý thành Ciphertext vô nghĩa đối với bất kì Hypervisor nào.
- ☁️ Tách biệt luồng **Memory Isolation** và giao phó khóa giải mã nội bộ duy nhất cho vi xử lý **AMD Secure Processor** quản lý.
- ☁️ Thiết lập cổng gác **Remote Attestation Protocol** xác nhận tính vẹn toàn qua chữ ký Quote từ chip phần cứng trước khi chắp nối đường hầm lưới mTLS `📱💻🖥️☁️`.
- 📱💻🖥️ Tích hợp Engine **Hardware Signature Verification** tại Lõi Rust để thẩm định chữ ký gốc cung cấp bởi nhà xuất xưởng phần cứng silicon (AMD/Intel).
- ☁️🗄️ Vận hành dịch vụ trọng yếu (Blind Relay, Vault Store) khép kín vào luồng **Confidential Containers (CoCo)** bọc quanh bởi khu cách ly **Intel TDX** hoặc **SGX Enclaves**.
- ☁️ Ngăn chặn tuyệt đối can thiệp đọc/ghi trộm từ Cloud Provider láng giềng nhắm tới CPU Register/Cache theo chuẩn **TEE-Based Processing**.
- ☁️ Triển khai phi tập trung cấu trúc **Specialized Confidential VM** độc lập chạy trên dải máy chủ CPU AMD EPYC gen 3+ kết hợp **TPM 2.0/Secure Enclave**.
- 📱💻🖥️ **Rust Local Micro-NER & Dynamic Vaulting (Bảo mật Dữ liệu AI Khách):** Triển khai bộ máy Regex kết hợp thuật toán Micro-NER tĩnh (<1MB) tại Lõi Rust để bóc tách dữ liệu định danh (PII/PCI/PHI) trước khi rời thiết bị. Khởi tạo Bảng ánh xạ tạm thời trên RAM bảo vệ bằng cờ `mlock()` để quản lý phiên xử lý cục bộ; áp dụng Tokenization Động thay thế Plaintext thành các Token ngữ nghĩa (vd: `[TOKEN_ACCOUNT_01]`) nhằm bảo toàn cấu trúc câu cho AI.
- ☁️🗄️ **Blind Execution trong TEE Sandbox (Chống Rò rỉ Weights/KV Cache):** Cô lập tiến trình xử lý Masked Prompt bên trong TEE (Intel SGX/AWS Nitro). Ép buộc SLM/LLM xử lý suy luận mù (Blind Inference) hoàn toàn trên Token đại diện, ngăn chặn tuyệt đối việc nạp dữ liệu doanh nghiệp vào Weights hoặc KV Cache.
- 📱💻🖥️ **Prompt Rehydration & RAII Zeroization (Phục hồi ngữ cảnh an toàn):** Thực thi De-tokenization đối chiếu kết quả trả về từ TEE với Hash Map cục bộ để lấp Plaintext vào đúng vị trí Token. Kích hoạt vòng đời `Drop()` của Rust kết hợp `ZeroizeOnDrop` ghi đè toàn bộ vùng nhớ chứa Session Vault và Bảng ánh xạ bằng các byte `0x00` để triệt tiêu vĩnh viễn dấu vết Plaintext trên RAM ngay khi trả kết quả về UI Native.

- 🖥️ Thiết lập gông cùm **TPM 2.0 Monotonic Counter Sealing** áp góc `TPM2_Seal`/`TPM2_Unseal` logic, tự động đối chiếu PCR State Validation và vô hiệu phiên (Session Invalidation) chặn đứng mọi mưu đồ Snapshot/Cloning ảo hóa vật lý.
- 🖥️ Trực chiến lính gác **Micro-architectural Drift Watchdog** nạp luồng Rust RT-priority theo dõi độ trễ `rdtsc` Sampling, giáng đòn `mlock()`/`ZeroizeOnDrop` quét sạch nội hàm RAM nếu vi kiến trúc bộc lộ dấu hiệu Hypervisor Pause.
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
      └──> [KEK]  — giải mã trong RAM, mlock'd / ZeroizeOnDrop
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

### 4.3 Hardware Isolation & Crypto-Shredding

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

#### Chống trùng lặp dữ liệu vật lý (Storage Bloat)

- ☁️🗄️ **Content-Addressable Storage (CAS) Deduplication:** Khai thác mã băm BLAKE3 để định danh `CAS_Hash` nguyên bản của từng thực thể vật lý, ngăn chặn khởi tạo lại tài nguyên lưu trữ.
- ☁️🗄️ Quản lý lưu trữ tập trung khối `Encrypted_Blob` trên nền tảng Blind Storage (MinIO) dựa hoàn toàn trên chuỗi hash thay vì đường dẫn định tuyến tĩnh như hệ thống truyền thống.
- ☁️🗄️ Vận hành cơ chế Deduplication tự động đối chiếu băm nhằm trực tiếp cắt giảm mạnh mẽ 40–60% dung lượng lưu trữ thực tế trên toàn bộ cụm Server.

#### Memory Defense

- 💻🖥️ **Desktop/Server:** `VirtualLock()` / `mlock()`. Kiểm tra BitLocker/FileVault khi khởi động — từ chối nếu không bật.
- 📱 **Mobile:** ZeroizeOnDrop (RAII) — không dùng `mlock()`. Plaintext RAM \<50ms, ghi đè `0x00` ngay sau scope.

#### Zeroize & Deferred Task Suspension

- 📱💻 Áp dụng `ZeroizeOnDrop` (RAII) để ghi đè $0x00$ lên vùng nhớ `Decrypted Secure Arena` ngay khi giao dịch bị hủy.
- 📱 Tích hợp iOS Background Delegate (`BGTask.setTaskCompleted`) và Android `WorkManager` retry để đưa tác vụ JIT Indexing vào hàng đợi thực thi lại khi thiết bị mở khóa.
- 📱 Giải phóng triệt để vùng nhớ `mlock()` để lách qua và tránh JetSam OOM-Kill trong trạng thái nền.

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

---

## 5. Network & Communication Protocols

### 5.1 Real-time Messaging

#### WebSocket E2EE Relay

- ☁️ Server relay ciphertext blob — không giải mã. Rate Limiting (Redis ZSET Sliding Window). OPA throttle theo phòng ban.

#### E2EE Push Notification — iOS (NSE)

- 📱 `UNNotificationServiceExtension` + `mutable-content: 1` (chuẩn Signal/WhatsApp).
- 📱 **NSE Micro-Crypto Build Target:** Loại bỏ 100% MLS, CRDT Automerge, SQLCipher. Chỉ giữ AES-256-GCM decrypt + Shared Keychain read. Footprint ~4MB (safe dưới 24MB Apple limit).
- 📱 **Push Payload ≤ 4KB:** fields: `chat_id`, `sender_display`, `preview_ct` (AES-256-GCM), `has_attachment`, `epoch`. Không HTTP GET trong NSE.
- 📱 **Push Key Rotation:** Đồng bộ với MLS Epoch. Key per-chat trong Shared Keychain (App Group).
- 📱 **Key Desync Fallback:** Không tìm thấy Key → fallback text an toàn, không crash.

#### E2EE Push Notification — Android (FCM)

- 📱 Data Message → `FirebaseMessagingService` → giải mã Rust FFI. `StrongBox Keymaster` lưu Symmetric Push Key.

#### Desktop Background Daemon

- 💻🖥️ **`terachat-daemon`** ~4.5MB RAM — tách biệt khỏi Tauri UI.
- 💻 Windows Service (`sc create`) / macOS `launchd` LaunchAgent / 🖥️ Linux `systemd` user service.
- 💻🖥️ Nhận E2EE payload → giải mã preview → OS Native Notification → xóa plaintext. DB sync chỉ khi Tauri UI mở.

### 5.2 Survival Mesh Network (P2P, BLE 5.0, Wi-Fi Direct)

| Layer | Protocol | Tốc độ | Phạm vi |
|---|---|---|---|
| **Signal Plane** | BLE 5.0 Advertising | ~2 Mbps | ~10–100m |
| **Data Plane** | Wi-Fi Direct / AWDL | ~200 Mbps | ~50–100m |

#### Mesh Network kiểu Bitchat/Briar (Delay-Tolerant Networking - DTN)

- 📱💻🖥️ **Store-and-Forward Gossip Protocol (Text):** Khi mất mạng lưới (Offline), tin nhắn CRDT (<1KB) mã hóa bằng khóa bảo mật đích được truyền đa bước ("nhảy cóc") qua các Router Trung gian (Mesh Nodes). Node bị cấm đọc nội dung nhưng cho phép lưu trữ tạm thời và phát kết tiếp thông lượng cho đến đỉnh đích.
- 📱💻🖥️ **Direct-Link Only Media (File/Video):** Trong `Mesh Mode`, Lõi Rust đóng băng công năng định tuyến multi-hop đối với mọi tệp tin nặng nề. Dữ liệu băng thông cao bắt buộc giao dịch P2P Wi-Fi Aware khép kín chỉ khi 2 máy chạm bán kính trực diện (< 20 mét). Khung UI hiển thị "Chỉ gửi file khi ở gần".
- 📱 **Passive Network Sensing (Cảm biến Mạng Thụ động):** Vận dụng bộ ngắm OS Native (`NWPathMonitor` iOS / `ConnectivityManager` Android) để bắt sự kiện luồng sóng tắt / mở Baseband. Đánh thức Tầng Logic Swift/Kotlin thay vì rượt vòng lặp dò quét tiêu pin điên cuồng ở lớp Lõi Rust, kéo mức Base Energy Consumption sát 0.
- 📱💻🖥️ **BLE Duty-Cycle Management:** Răm rắp duy trì thuật toán vắt kiệt cường độ xung quét BLE: Tỉnh lược 200ms Advertising/Scanning xen lẫn 800ms chu kỳ Sleep để giảm hỏa 80% công suất tải ăn nguồn. Kết cấu Heartbeat Advertising rời rạc kết nạp linh động MTU Fragmentation cực hẹp.

#### Tối ưu hóa Băng thông Mạng lưới Sinh tồn (Hybrid Multipath Transport Plane)

#### Phân tách kênh Truyền dẫn và Gossip Discovery (Hybrid Multipath Transport Plane)

- 📱💻 Phân định **Cấp độ 1 (Tối ưu Sinh tồn - Background):** Sử dụng duy nhất giao thức **BLE L2CAP CoC** (Control Plane) cho phép ứng dụng truyền tải ngầm payload nhỏ (<500KB) như tin nhắn SOS/văn bản mà không cần người dùng cấp quyền OS liên tục.
- 📱💻🖥️ **Gossip Discovery & L2CAP Chunked Transmission:** Trao đổi Vector trạng thái (Hash) qua thuật toán Gossip để nhận diện phiên bản mới khả dụng trong Mesh. Payload OTA được phân mảnh (Chunking) thành các block 512 bytes truyền tải qua kênh L2CAP CoC cực kì ổn định để tránh phân mảnh MTU.
- 📱💻🖥️ Bắt buộc chuyển sang **Cấp độ 2 (Truyền tải nặng - Foreground):** Kích hoạt **Wi-Fi Direct / LAN / SoftAP** (Data Plane) phục vụ truyền tải tệp tin đa phương tiện và bản cập nhật nhị phân (.exe/.dmg) lớn nhờ sự điều phối băng thông của các Super Nodes. Yêu cầu popup xác nhận từ người dùng để tránh vi phạm background policy của Apple.
- 📱 Cơ chế Opportunistic Tear-down ngắt kênh Data Plane ngay sau khi truyền tệp thành công nhằm bảo toàn năng lượng pin thiết bị.

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

#### Định tuyến Đồ thị Nhận thức Không gian (JCAS Spatial-Aware Routing (3D-A* Pathfinding))

- 📱💻🖥️ Đánh giá tín hiệu suy hao RSSI & Round-Trip Time (chuẩn IEEE 802.11mc) đúc kết bản đồ 3D thực tế ánh xạ trực tiếp trên RAM hệ thống.
- 📱💻🖥️ Triển khai thuật toán 3D-A* Pathfinding quét tọa độ và tính toán Shortest Path vượt qua các Node đang nhịp thức theo chu kỳ.
- 📱💻🖥️ Thiết lập giao thức Zero-Wake cô lập nghiêm ngặt các thiết bị nằm ngoài quỹ đạo luồng định tuyến nhằm phong tỏa hao hụt pin rác.

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

### 5.9 Tiết kiệm Năng lượng Mạng Mesh (JCAS Spatial-Aware Routing & iBeacon Stealth Mode)

- 📱 Cưỡng ép đóng gói tín hiệu mạng Mesh vào giao thức iBeacon Ranging (CoreLocation) nhằm lách hạn chế ngầm định của iOS, duy trì chu kỳ quét Background.
- 📱💻 Áp dụng thuật toán JCAS Spatial-Aware Routing (A*) thiết lập biểu đồ 3D tọa độ thiết bị trực tiếp trên RAM để tối ưu hóa nút mạng, giảm thiểu tình trạng "phát sóng rác".
- 📱💻 Điều tiết cấu hình Opportunistic Wakeup chủ động kích hoạt năng lượng định tuyến khi payload có nhu cầu di chuyển tệp thực, hạ tần suất Beacon xuống 1 lần/5 phút ở trạng thái Standby.

### 5.9.1 Single-Frame Binary Serialization for Mesh Recovery (Chống Phân mảnh BLE 5.0)

> **Bài toán:** BLE 4.2 MTU tối đa 251 bytes buộc phải phân mảnh L2CAP nếu payload lớn hơn — gây mất gói, thứ tự sai và tăng overhead. Trong kịch cảnh khôi phục khẩn cấp (SOS Beacon, Social Escrow shard), mỗi byte thừa đều là rủi ro.

- 📱💻🖥️ **Protobuf Binary Encoding (Không Metadata):** Mọi Mesh Recovery payload (SOS Beacon, `Welcome_Packet`, Shun command) được serialize bằng Protobuf Binary (không phải JSON/CBOR) với schema tối giản — chỉ giữ các field bắt buộc. Ví dụ: một Social Escrow shard request chỉ ~80 bytes (Node_ID 16B + Epoch 8B + Signature 64B + padding), nằm gọn trong một BLE frame đơn.
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

#### Micro-Proof-of-Work Adaptive Throttle — Argon2id (Chống DoS Vắt kiệt Tài nguyên Mesh)

> **Nâng cấp so với SHA-256 Hashcash:** SHA-256 có thể bị GPU/ASIC giải nonce hàng loạt với chi phí thấp, không đủ ngưỡng ngăn chặn kẻ tấn công có phần cứng chuyên dụng. Argon2id yêu cầu cả CPU + RAM, phù hợp môi trường bị ràng buộc tài nguyên của Mesh.

- 📱 **Argon2id CPU-bound Challenge:** Trước khi broadcast bất kỳ Control Plane packet nào (Route Advertisement, CRDT Push, File Discovery), node phải giải một Argon2id challenge (`m=1MB, t=2, p=1`) — tốn ~50ms/challenge để ngăn spam hàng loạt, nhưng chấp nhận được với người dùng bình thường.
- 💻📱 **Deterministic Transaction Cost:** Chi phí mPoW cố định theo loại giao dịch: Mesh Announcement = 50ms, File Chunk Relay = 10ms, Emergency SOS = 0ms (miễn phí để ưu tiên cứu hộ). Lõi Rust xác thực proof tại Layer 5 với $O(1)$ mà không cần lưu state.
- 📱 **Thermal Throttling Feedback Loop:** Lõi Rust liên tục đọc giá trị nhiệt độ CPU (iOS: `ProcessInfo.thermalState`, Android: `ThermalStatus`) → nếu thiết bị đang nóng (Serious/Critical), tự động tăng Argon2id time parameter `t` thêm 1 bước, giảm gánh nặng cho tầng Data Plane.
- 💻📱 **Rate-limiting Ring Buffer:** Mỗi `Node_ID` được phân bổ một Ring Buffer 32-entry trong RAM của Lõi Rust, theo dõi timestamp của 32 gói tin gần nhất. Nếu khoảng cách trung bình `< 100ms` trong Ring Buffer → tự động Quarantine node vào Denylist tạm thời 15 phút.

#### Objective Cryptographic Proof of Malfeasance — OCPM (Chống Tấn công Vu khống / Chỉ điểm Giả)

> **Bài toán:** Trong Mesh không có Server trọng tài, kẻ tấn công có thể tung bằng chứng giả (fabricated log) hoặc vu khống node lành để kích hoạt Shun. OCPM đảm bảo mọi cáo buộc đều phải kèm bằng chứng mật mã không thể làm giả.

- 📱 **Hardware-bound Non-repudiation (Secure Enclave/StrongBox):** Mỗi sự kiện vi phạm (malformed packet, signature mismatch, ACL violation) được node phát hiện ký ngay bằng `Device_Key` đang `mlock()`'d trong Secure Enclave — tạo ra bằng chứng gắn chặt với phần cứng, không thể bị giả mạo bởi bên thứ ba.
- 💻📱 **Ed25519 Digital Signature Bundling:** Toàn bộ chuỗi bằng chứng được đóng gói thành `Proof_Bundle` gồm: raw packet bytes + timestamp HLC + `Node_ID` của bên vi phạm + chữ ký Ed25519 của node phát hiện. Bundle này không thể bị tái sử dụng cho node khác vì `Node_ID` được embed trực tiếp.
- 💻📱 **Immutable Evidence Encapsulation:** `Proof_Bundle` được lưu vào SQLite WAL với cờ `READ_ONLY` ngay lập tức sau khi ghi — không thể sửa đổi hay xóa. Lõi Rust từ chối bất kỳ request nào cố truncate hoặc overwrite bảng Evidence.
- 💻📱 **Multi-party Cryptographic Attribution:** Trước khi kích hoạt Byzantine Shun, hệ thống yêu cầu **tối thiểu 2 Proof_Bundle độc lập** từ 2 node khác nhau cùng cáo buộc một `Node_ID`. Tránh False-Flag Attack chỉ từ một node tấn công đơn lẻ.

#### HLC-Epoch Temporal Binding (Chống Tấn công Phát lại Bằng chứng Cũ)

> **Bài toán:** Kẻ tấn công thu thập Proof_Bundle hoặc CRDT event hợp lệ từ epoch cũ và phát lại để kích hoạt hành vi không mong muốn (Shun giả, state rollback). Binding theo thời gian đảm bảo bằng chứng cũ bị vô hiệu hóa tự động.

- 💻📱 **Hybrid Logical Clock (HLC) Causality:** Mọi packet (CRDT event, Proof_Bundle, Shun command) phải mang `hlc_timestamp` và `vector_clock`. Lõi Rust kiểm tra: `|hlc_now - hlc_packet| < DRIFT_THRESHOLD (5s)`. Nếu packet đến trễ quá ngưỡng → `TEMPORAL_VIOLATION`, drop không process.
- ☁️📱 **MLS Epoch-bound Forward Secrecy:** Mỗi Shun command và Proof_Bundle bị ràng buộc với MLS Epoch hiện tại. Khi MLS Key Rotation xảy ra (epoch tăng), toàn bộ bằng chứng từ epoch cũ trở thành **invalid** — không thể recycled để cáo buộc trong epoch mới.
- 💻📱 **24h Temporal Validation Window:** Lõi Rust duy trì một Bloom Filter lưu `Evidence_Hash` trong 24h. Bất kỳ `Proof_Bundle` có hash đã tồn tại trong Bloom Filter → từ chối ngay với lỗi `EVIDENCE_REPLAYED`. Bloom Filter tự xóa sạch mỗi 24h để tránh tích lũy bộ nhớ.
- 📱 **Monotonic Hardware Counter Binding:** Trên iOS (Secure Enclave), mỗi `Proof_Bundle` được gắn thêm giá trị từ **Monotonic Counter** của Secure Enclave — bộ đếm phần cứng không thể đặt lại (rollback-proof). Nếu Counter trong Proof_Bundle thấp hơn giá trị hiện tại của thiết bị phát hiện → cờ `COUNTER_ROLLBACK`, reject.

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

### 5.18 Chống Rò rỉ `Company_Key` qua WASM Sandbox (Off-Sandbox Decryption)

> **Bài toán:** Mini-App (.tapp) chạy trong WASM Sandbox là mã nguồn bên ngoài (3rd party). Nếu cấp thẳng `Company_Key` vào Sandbox để Mini-App tự giải mã Data, mã độc có thể lén lút tuồn Key ra ngoài qua các API fetch ngầm.

- 💻🖥️ **`mlock()` Ngăn chặn Swap xuống Đĩa:** Lõi Rust ghim cứng (pin) vùng nhớ chứa plaintext Key vào RAM vật lý bằng lệnh syscall `mlock()`, chống lại cơ chế Paging của OS lén ghi tạm Key xuống ổ cứng (nơi Malware dễ dàng rà quét).
- 📱💻🖥️ **OPA Policy Engine Đánh giá Quyền truy cập:** Lõi Rust chặn toàn bộ quyền tự giải mã của .tapp. Mọi yêu cầu truy xuất dữ liệu từ Sandbox phải đi qua OPA (Open Policy Agent). OPA đối chiếu Manifest của .tapp với Data Classification trước khi Lõi Rust đứng ra *giải mã hộ*.
- 📱💻🖥️ **ZeroizeOnDrop (RAII) Ghi đè 0x00:** Ngay sau khi Lõi Rust giải mã xong vùng dữ liệu được cấp phép, mọi biến nhớ chứa Plaintext Key dùng trong phiên đó sẽ tự động kích hoạt zeroize (hủy diệt bằng chuỗi số `0x00`) ngay khoảnh khắc ra khỏi scope, xóa sạch tàn dư khỏi RAM.

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

### 4.9 Tấn công Memory Dump/Extraction (Synchronous Zeroize Safe Pipeline & Hardware Isolation)

#### Rò rỉ Plaintext từ Vector Embeddings trong RAM (Tự hủy bộ nhớ tàn bạo)

- 📱💻🖥️ **Ruthless Memory Self-Destruct:** Cấu trúc `ZeroizeOnDrop` (RAII) lập tức ghi đè liên tục `0x00` xóa sạch vùng Shared Memory ngay giây khắc bộ máy AI Sandbox tiêu thụ xong luồng Vector Embeddings.
- 💻🖥️ **Hardware Anti-Swapping:** Khởi động UNIX API `mlock()` trên Desktop ngăn chặn hệ điều hành cày xới và đẩy Swap phân mảng dữ liệu AI siêu nhạy cảm xuống phân vùng đĩa cứng vật lý hở.
- 📱💻🖥️ **Luồng Xử lý Cách ly Kép:** Độc lập tiến trình giải mật (CPU Bound) ngăn vách cực đoan khỏi mọi kết cấu hệ thống truyền dẫn chéo I/O mạng lưới.

- 📱 Kích hoạt luồng ZeroizeOnDrop (RAII) để ghi đè `0x00` lên không gian bộ nhớ ngay khi thoát khỏi scope, khống chế vòng đời của plaintext key <2ms.
- 📱💻🖥️ Đẩy luồng ký/giải mã KEK nội bộ xuống Hardware Root of Trust (Secure Enclave/TPM 2.0/StrongBox) tuyệt đối không nạp Private Key vào RAM.
- 📱💻🖥️ Thiết lập Compiler-Level Guard ngắt mã kích hoạt trait `Send` và `Sync`, ngăn chặn rò rỉ khóa mã hóa qua thread boundary hoặc khi vượt điểm `.await`.

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
- 💻🖥️☁️🗄️ **mlock() Hardening:** Desktop/Server dùng `mmap` + cờ `MAP_LOCKED | MAP_CONCEAL`. Bảo vệ RAM khỏi Swap file trong khoảng 2ms tồn tại của Key.

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

#### Encrypted Blind Search qua TEE kết hợp Hybrid SSE

- 📱☁️ Token hóa luồng từ khóa thông qua thuật toán băm $HMAC-SHA256(Company\_Search\_Key, keyword)$.
- 📱☁️ Phân mảnh cấu trúc chỉ mục theo định danh Epoch ID phục vụ quá trình xoay vòng khóa (Epoch Rotation).
- ☁️🗄️ Cấu hình truy vấn $O(1)$ Token-to-Index trực diện trên vùng nhớ đã mã hóa của hạt nhân TEE.

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

*Xem `Feature_Spec.md` cho App-layer. Xem `Function.md` cho Product flows.*
