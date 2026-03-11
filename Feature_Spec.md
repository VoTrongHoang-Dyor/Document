# Feature_Spec.md — TeraChat Alpha v0.3.0

> **Status:** `ACTIVE — Implementation Reference`
> **Audience:** Mobile Dev (iOS/Android) · Desktop Dev (Tauri/Electron) · FFI Integrator · WASM Sandbox Dev
> **Scope:** Client Data Plane, IPC Bridge, Local Storage, Native OS Hooks, WASM Ecosystem — Implementation-level only.
> **Last Updated:** 2026-03-11
> **Depends On:** `Core_Spec.md` (cryptographic primitives, MLS protocol, Mesh network state machine)
> **Consumed By:** `Design.md` (UI rendering triggers), `Web_Marketplace.md` (WASM sandbox runtime)

---

## CHANGELOG

| Version | Date | Change Summary |
| ------- | ---------- | ---------------------------------------------------------------------------- |
| v0.3.0 | 2026-03-11 | §9.7 NFC Ring → Admin-approved QR Key Exchange + BIP-39 Mnemonic fallback; Remove NFC CoreNFC/NfcAdapter dependency |
| v0.2.9 | 2026-03-05 | Add §9.9 Tiered Memory Pre-fetching (mmap + madvise MADV_WILLNEED); §9.10 Fixed-size Ring Buffer side-channel defense |
| v0.2.8 | 2026-03-04 | Add §9.6 Protected Clipboard Bridge; §6.17 Zero-Byte Stub viewport rendering; §8.1 WASM Sandbox Isolation |

---

## CONTRACT: Client-Side Implementation Requirements

> **Đọc toàn bộ §0 Data Object Catalog trước khi implement bất kỳ component client nào.**
> Ràng buộc dưới đây áp dụng cho mọi client platform (iOS, Android, macOS, Windows, Linux).

- [ ] JSI / FFI bridge **không được** expose raw pointer sang JS/WASM layer. Chỉ pass serialized message qua IPC channel.
- [ ] `cold_state.db` **phải** được SQLCipher mã hóa với key được derive từ Secure Enclave — không hardcode.
- [ ] Background Notification Extension (iOS NSE / Android FCM) **phải** giới hạn RAM ≤ 20MB — xem §8.2 Circuit Breaker.
- [ ] Mọi WASM `.tapp` **phải** run trong Sandbox với `PROT_READ`-only shared memory — không được write vào DAG buffer.
- [ ] Clipboard operation **phải** đi qua Protected Clipboard Bridge (§9.6) — không trực tiếp gọi OS clipboard API.
- [ ] `ZeroizeOnDrop` bắt buộc cho mọi struct giữ plaintext — verify bằng Miri test.

---

## TABLE OF CONTENTS

1. [Client Data Plane](#6-client-data-plane)
2. [Ecosystem & Integration](#7-ecosystem--integration)

---

## 0. Data Object Catalog (Danh mục Đối tượng Dữ liệu — Client Side)

> Mỗi object liệt kê dưới đây là một **đơn vị dữ liệu** cụ thể tại tầng Client (Mobile/Desktop/WASM) với schema, vòng đời, và ràng buộc bảo mật riêng biệt. Các giải thuật (IPC, Hydration, Sync) chỉ là *operations* tác động lên những object này.

### 💾 Domain: Local Storage Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `cold_state.db` | SQLite (SQLCipher) | Disk — permanent | Exists until Crypto-Shred | §6.2 |
| `cold_state_shadow.db` | SQLite (temp) | Disk — transient | Exists only during Hydration batch, deleted after POSIX rename | §6.14.1 |
| `hot_dag.db` | SQLite WAL (append-only) | Disk — permanent | Grows monotonically, compacted by Squashing | §6.12 |
| `Hydration_Checkpoint` | `{Snapshot_CAS_UUID, last_chunk_index}` | `hot_dag.db` key-value | Overwritten per chunk flush | §6.14.1 |
| `Tombstone_Stub` | `{entity_id, hlc, type=DELETED}` | `cold_state.db` | Permanent, never physically deleted | §6.12 |
| `Merged_Vector_Clock` | Map<Node_ID, Logical_Counter> | `hot_dag.db` | Updated on every DAG merge operation | §6.12 |

### 🪟 Domain: UI Rendering Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `Zero_Byte_Stub` | `{entity_id, blur_hash, metadata}` | RAM / `cold_state.db` | Rendered immediately on scroll, replaced on hydration | §6.5 |
| `Blur_hash_Thumbnail` | 30-50 byte encoded string | `cold_state.db` | Persistent, pre-computed at send-time | §6.5 |
| `Viewport_Cursor` | `{top_message_id, bottom_message_id}` | RAM (ephemeral) | Alive for scroll session | §6.8 |
| `MERGE_COMPLETE_Event` | Control Plane Signal `{batch_id}` | IPC channel only | Fire-and-forget, not persisted | §6.17 |

### 🔐 Domain: Secure Ephemeral Memory Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `Decrypted_Chunk_2MB` | Raw bytes (plaintext) | RAM — `ZeroizeOnDrop` | Alive for 1 chunk decrypt cycle, then zeroed | §6.14.1 |
| `Ephemeral_Buffer_PROT_READ` | mmap region with `PROT_READ` flag | Virtual memory | Duration of WASM Sandbox session | §6.18 |
| `Ring_Buffer_2MB` | Fixed-size circular byte buffer | User-space RAM | Statically allocated, reused in streaming loop | §8.1 |
| `ChunkKey` | AES-256-GCM per-chunk key | Rust `ZeroizeOnDrop` struct | One chunk lifetime (~2MB), zero-on-drop | §6.14.1 |

### 📡 Domain: IPC & Sync Signal Objects

| Object | Kiểu | Nơi lưu | Vòng đời | Section Spec |
|---|---|---|---|---|
| `Control_Plane_Signal` | Protobuf ≤ 50 bytes | SharedArrayBuffer / JSI | Fire-and-forget | §6.1 |
| `Data_Plane_Payload` | Raw bytes | SharedArrayBuffer / Dart FFI TypedData | Duration of transfer | §6.1 |
| `Snapshot_CAS_UUID` | UUID v4 (content-addressed) | `hot_dag.db` | Stable reference to a materialized state snapshot | §6.13, §6.14.1 |
| `File_Chunk_AD` | `{File_ID, Chunk_Index, Byte_Offset}` | AEAD Associated Data (in-flight) | Per chunk encryption/decryption | §8.1 |

---

## 6. Client Data Plane

### 6.1 IPC Bridge Architecture

#### Tối ưu hóa Kích thước Lõi Biên dịch (App Size Optimization)

- 📱💻 Cấu hình biên dịch Rust tĩnh với cờ `opt-level = 'z'`, bật Link-Time Optimization (`lto = true`) và `panic = 'abort'` nhằm gọt dũa dung lượng binary core rớt từ ~30MB xuống sát ngưỡng ~4MB.
- 📱 Yêu cầu hệ thống tước bỏ toàn bộ Symbol (Strip Symbols) trong quá trình Release Build để tiết kiệm không gian gói cài đặt di động (.ipa/.apk).

#### 📱 iOS Cross-Platform Conflict Resolution — W^X, JIT, NSE & Memory Pinning

> **Nợ kỹ thuật cốt lõi:** Lõi Rust đồng nhất hoạt động trên mọi nền tảng, nhưng iOS áp đặt bộ ba ràng buộc cứng: W^X (Write XOR Execute), giới hạn 24MB NSE RAM, và chính sách không cho `mlock()`. Giải pháp là biên dịch phân kỳ (divergent compilation) + Asymmetric Pipeline.

#### Giải pháp: Asymmetric WASM-CoreML Fusion & BPF-Seccomp Sandboxing (Xung đột W^X và OOM-Kill trên iOS NSE)

- 📱 **iOS CoreML AOT Compilation (.mlmodelc):** Tránh JIT compiler hoàn toàn trên iOS để tuân thủ chính sách App Store (chống phân bổ `PROT_EXEC`). Các module AI (.tapp) được biên dịch dạng AOT thành `.mlmodelc` chạy trực tiếp qua Neural Engine (ANE) của phần cứng.
- 💻 **Wasmtime JIT Compiler:** Kích hoạt JIT compiler trên Desktop/Android ở mức OptLevel cao nhất với Cranelift backend, tối đa hoá hiệu suất tốc độ thực thi.
- 🖥️ **Linux seccomp-bpf Sandbox:** Áp đặt filter Syscall cực ngặt nghèo (BPF) để ngăn chặn các nỗ lực RCE thoát khỏi hộp cát.
- 🖥️ **Windows AppContainer Zero-Trust Boundary:** Ứng dụng mô hình cách ly AppContainer Isolation trên Windows để phong tỏa ranh giới tiến trình của WASM.

- 📱 **NSE Payload Ceiling < 4KB — Ghost Push Skeleton:**
  - Giới hạn cứng: NSE của iOS chỉ được cấp 24MB RAM. Với nhóm 50.000 user thay đổi Epoch Key, payload push sẽ phình to → OOM-Kill không thể tránh khỏi.
  - **Giải pháp:** NSE chỉ giải mã `Push_Key` đối xứng (sinh từ HKDF tĩnh, < 32 bytes). Nếu phát hiện `payload_size > 4KB` hoặc `epoch_delta > 1`, NSE không giải mã toàn phần — thay vào đó kích hoạt **Ghost Push**: hiển thị Skeleton *"Đang giải mã an toàn..."* và ghi cờ `main_app_decrypt_needed = true` vào Shared App Group Keychain. Main App nhận flag khi được đánh thức và thực hiện giải mã nặng ở Foreground (nơi có 2GB RAM và JIT-free TreeKEM).

- 📱 **Memory Pinning Fallback — Thay thế `mlock()` trên iOS:**
  - iOS từ chối `mlock()` đối với các process không có root. Plaintext key giải mã có nguy cơ swap ra đĩa nếu Jetsam OOM-Kill xảy ra trước khi `ZeroizeOnDrop` được gọi.
  - **Giải pháp:** Lõi Rust phân bổ key material vào vùng `kCFAllocatorMallocZone` và ngay lập tức gọi `madvise(MADV_NOCORE)` để đảm bảo vùng nhớ này không bao giờ xuất hiện trong crash dump. Kết hợp với `SecureAllocator` wrapper: mọi key struct trên iOS đều implement custom `Allocator` ghi đè page trước khi trả về allocator pool.

#### 📱 iOS Data Mule — Asymmetric Foreground/Background Mesh Strategy

> **Ràng buộc cứng của iOS:** MultipeerConnectivity không thể duy trì session khi ứng dụng ở Background > 30 giây. Mọi Local Socket bị đóng băng. Dùng iBeacon để đánh thức background đối mặt với nguy cơ bị Reject theo Rule 2.5.4.

- 📱 **Foreground High-Bandwidth Burst:** Khi nhân viên mở màn hình (Foreground), Lõi Rust kích hoạt toàn bộ MultipeerConnectivity pipeline — đồng bộ Delta-State CRDT tối đa 2MB trong cửa sổ Foreground. Ưu tiên dữ liệu gap lớn nhất trước (Largest-Gap-First scheduling).
- 📱 **Background L2CAP BLE Ping-only Mode:** Khi màn hình bị khoá, iOS tự động đình chỉ MultipeerConnectivity. Lõi Rust giảm xuống chỉ duy trì **BLE L2CAP `sync_needed` ping** (< 20 bytes, năng lượng cực thấp). Android Super Node nhận ping và đánh dấu `ios_node_needs_hydration[device_id] = true`. Khi iOS mở khoá, Super Node ngay lập tức push Delta-State gap qua MultipeerConnectivity.
- 📱 **Graceful Degradation SLA:** iOS user sẽ không miss tin nhắn. Độ trễ tối đa = thời gian màn hình khoá × chu kỳ BLE ping (mặc định 30s). Desktop/Android Super Node là "bộ nhớ thay thế" của iOS.
- 📱 **Hybrid BLE State Restoration & Native Background Task Hook:** Để ngăn chặn OS Jetsam OOM-Kill tiêu diệt tiến trình Mesh nền, thiết lập iOS Micro-Daemon C (FFI) quản lý CoreBluetooth độc lập. Kết hợp BLE State Restoration Wake-up để hồi sinh Lõi Rust khi có tín hiệu, và xin cấp phép BGProcessingTask RAM Allocation nhằm đảm bảo đủ bộ nhớ duy trì Mesh an toàn.
- 📱 **iOS MultipeerConnectivity C-bindings (FFI Bypass):** Triển khai kiến trúc Hybrid Multipeer tiếp cận thẳng C-bindings của `MultipeerConnectivity`, vượt rào cản nền Background Execution mà không vi phạm App Store Rule 2.5.4.
- 📱 **Android Wi-Fi Aware Native Mesh API:** Kết nối trực tiếp Native Mesh API của `WifiAwareManager` dành cho Android — định vị và kết nối ngang hàng không cần Access Point.
- 📱 **Lõi Rust FFI Socket Bypass:** Lõi Rust giữ quyền sở hữu Socket trực tiếp qua FFI, tránh hoàn toàn lᳳp trước xử lý Framework kéo dài độ trễ giao tiếp Mesh.
- 📱 **iOS Baseband CBUUID Hardware Pre-Filtering:** Chặn đứng thảm họa Tấn công "Đánh thức giả" (Phantom Wakeup) bằng cách lập trình trực tiếp cho vi xử lý Baseband của iPhone chỉ tỉnh giấc (Wake-up) khi bắt gặp đúng CBUUID mã hóa đã cấp quyền tước đó, bỏ qua hàng triệu gói tin BLE rác làm tốn pin.
- 💻 **seccomp-bpf / eBPF Kernel Network Drop:** Mở ra cơ chế phòng thủ sâu với Kernel-level Drop. Lõi Rust tiêm (Inject) một bộ lọc BPF siêu nhẹ trực tiếp vào Nhân hệ điều hành, dập tắt các kết nối tấn công ngay tại tầng Socket trước khi kịp cấp phát đối tượng (Object Allocation) trong Userspace.
- 📱 **SO_ATTACH_BPF Network Interface Card Drop:** Sử dụng cờ hiệu `SO_ATTACH_BPF` lập chốt chặn ngay thẻ mạng vật lý (NIC), chặn bão Broadcast storm từ kẻ tấn công trực tiếp tại chân card mạng mạng LAN ảo.
- 💻 📱 **1KB RAM Peer_ID Fingerprint Cuckoo Filter:** Trực chiến bộ lọc Cuckoo Hashing siêu hiệu quả tiêu thụ đúng 1KB RAM để đối chiếu, từ chối mọi yêu cầu thiết lập kết nối Handshake từ những UUID vãng lai không nằm trong Mesh Trust-list của thiết bị.


#### 📱 iOS AVAssetResourceLoaderDelegate — Native E2EE Video Streaming Bridge

> **Vấn đề:** Loopback Server `127.0.0.1` bị iOS đóng băng Socket khi ứng dụng vào Background, làm gián đoạn stream video E2EE. Không thể dùng Local HTTP Server trên iOS.

- 📱 **AVAssetResourceLoaderDelegate → Rust Ring Buffer:** Thay vì HTTP Loopback, triển khai `AVAssetResourceLoaderDelegate` protocol. `AVPlayer` (Swift layer) đăng ký delegate nhận custom scheme `terachat://`. Mỗi khi AVPlayer yêu cầu chunk tiếp theo, delegate đâm thẳng pointer vào **Rust Ring Buffer** qua FFI — giải mã AES-GCM chunk trực tiếp trong RAM không qua đĩa, trả về `Data` object cho AVPlayer tiêu thụ.
- 📱 **Throughput:** Rust Ring Buffer với kích thước 8MB (4 chunks × 2MB) cho phép người dùng xem video 4GB E2EE mượt mà ở 4K/60fps ngay cả khi thỉnh thoảng vuốt app xuống nền (iOS vẫn cho AVPlayer chạy background audio/video track).

- 📱💻🖥️ **Skeleton Extraction:** Giới hạn lượng dữ liệu hiển thị trích xuất chỉ ~10KB (gồm `message_id`, `text_preview`) để bảo đảm ngân sách thời gian xử lý chặn ở mức $16\text{ms}$, duy trì tốc độ 60/120fps.
- 📱💻🖥️ **Phân tách rạch ròi:** Quy hoạch Control Plane và Data Plane độc lập qua schema `terachat_ipc.proto`.
- 📱💻🖥️ **Unidirectional State Sync:** Giao diện UI chủ động kéo (pull) snapshot trạng thái thay vì hứng JSON đẩy (push) trực tiếp mệt mỏi từ Lõi.

#### Truyền tải Vector Embedding (Background Zero-Copy Memory Pumping)

- 📱 **JSI C++ Native Pointer (iOS/Android):** Bắn thẳng con trỏ bộ nhớ vật lý chứa 3MB Vector Embeddings vào Background Thread xuyên qua JSI, bypass hoàn toàn cổ chai Bridge của React Native. Giải quyết triệt để thắt cổ chai Latency khi truyền Vector Embeddings.
- 💻🖥️ **SharedArrayBuffer (Desktop/Web):** Sử dụng `mmap` vật lý cho phép hệ Web Worker truy cập Zero-copy trực diện vào kho dữ liệu 3MB.
- 📱💻🖥️ **Cô lập tác vụ AI:** Điều hướng Web Worker / Dart Isolate gánh vác các phép toán Vector ngoài luồng Main Thread để chống đóng băng UI giao diện.
- ☁️ **mmap() Virtual Memory Mapping:** Áp dụng ánh xạ tĩnh `mmap()` trên Linux Server/VPS để luân chuyển Vector Embeddings giữa Dictator Core và AI Engine siêu tốc mà không phát sinh thêm System Call cấp phát RAM.

#### §Egress Daemon & Queue Management (Data Diode Protocol)

> **Vấn đề ISO 27001 A.6.1.2:** Không để Lõi Crypto đồng thời làm Forward Proxy HTTP cho .tapp. Phải có luồng egress độc lập và hàng đợi cô lập.
> **Vấn đề Forensics & I/O:** Dữ liệu hàng đợi phải chống khôi phục sau khi gửi, và không được phép nghẽn mạng làm treo app.

- 📱💻 **Isolated Persistent Egress Queue (EEWQ):** .tapp ghi payload cần egress vào `tapp_egress.db` (SQLite WAL) — một database hoàn toàn độc lập với `hot_dag.db` để cách ly rủi ro state corruption.
- 📱 **OS Background Service Egress:** OS Background Service (📱 iOS `BGProcessingTask` / 📱 Android `WorkManager`) chạy độc lập với Lõi Rust: đọc từ EEWQ → verify BLAKE3 hash → OPA DLP check → dispatch network request.
- 💻🖥️ **Desktop `tera_egress_daemon` (Rust-based):** Micro-process chạy ở privilege `nobody` (Linux) / Restricted SID (Windows). Giao tiếp với WASM Sandbox qua named pipe. Pipeline: `EEWQ → BLAKE3 hash → OPA → reqwest TLS HPKP`.
- 📱💻🖥️ **Military-Grade Crypto-Shredding (Overwrite-before-Delete):** Ngay khi Egress Daemon nhận diện HTTP 200 OK từ server, record trong `tapp_egress.db` sẽ bị ghi đè bằng 📱💻🖥️ `/dev/urandom` (Overwrite-before-Delete), kết hợp Wear-leveling bypass logic để chống mổ xẻ Forensics cấp độ ổ nhớ Flash/SSD. Tiến trình này được thực thi ngầm bởi 🗄️ Rust-based Daemon.
- 📱💻 **Egress Byte-Quota Circuit Breaker:** Lõi Rust tích hợp 📱💻 Rust-level I/O Monitor giám sát luồng Egress. Áp đặt 📱💻 50MB Soft-Quota/ngày cho mỗi .tapp. Khi vượt quota, Circuit Breaker tự động ngắt kết nối và map mã lỗi sang 📱💻 HTTP 429 Throttle Mapping trả về cho WASM.
- 📱💻🖥️ **Capped Timeout State Machine & Skeleton Shimmer UI:** Để giải quyết Rủi ro Độ trễ mạng (Network Latency), Egress giới hạn timeout cứng. Khi mạng nghẽn, Daemon bắn tín hiệu 📱💻🖥️ `IPC_Signal::Enclave_Processing_Delayed` lên UI. UI lập tức hiển thị 📱 Skeleton Shimmer UI (Amber Pulse) cho .tapp card, trong khi Egress Daemon tiếp tục loop ☁️ Idempotent Retry (EEWQ) rảnh rỗi ở background.
- ☁️ **Cloud Server — Envoy gRPC Sidecar:** `.tapp` gửi request mTLS cục bộ `localhost:9200` sang Envoy. Envoy check ext_authz (OPA), route ra Internet. Lõi Rust zero involvement.
- 📱💻🖥️ **Egress_Outbox Overflow Protection:** Vượt RAM threshold → Outbox sealed, `.tapp` instance terminate và quarantine. Alert gửi Admin Console. Log `EXFILTRATION_ATTEMPT` Ed25519 signed.

#### Giải pháp: Deterministic Memory Disposal & Hardware-Backed Key Revocation (Chống Forensics EgressContextBuffer)

- 📱💻🖥️ **ZeroizeOnDrop (RAII) Buffer Overwrite:** Tiêu hủy triệt để EgressContextBuffer trên RAM bằng cách ghi đè byte `0x00` ngay trước khi buffer bị OS thu hồi.
- 📱 **iOS Secure Enclave / Android StrongBox Key Revocation:** Đánh dấu khóa phiên vô hiệu hóa vĩnh viễn (Revoked) ngay tại phần cứng nếu phát hiện có hành vi trích xuất ngoại lai, chặn đứng khả năng phục hồi dữ liệu từ chip nhớ.
- ☁️ **Remote MDM Wipe Trigger:** Tầng quản trị đám mây có quyền gửi tín hiệu xóa sổ khẩn cấp, kích hoạt cơ chế tự hủy dữ liệu cục bộ trên thiết bị nếu thiết bị bị báo mất hoặc thu hồi quyền truy cập.

#### Giải pháp: Asymmetric CRDT State-Squashing & Lazy O-LLVM Rehydration (Chống OOM do CRDT Phình to trên Mobile)

- 📱 **Asymmetric Payload Pruning:** Cắt tỉa (Pruning) không thương tiếc các nhánh CRDT cũ trên thiết bị di động, chỉ giữ lại State thu gọn (Squashed State) để tiết kiệm RAM.
- 💻🖥️ **Desktop/VPS Full-State Retention:** Desktop và VPS (nơi dồi dào tài nguyên) sẽ nhận nhiệm vụ lưu trữ toàn bộ lịch sử nguyên vẹn (Full-State), đóng vai trò mỏ neo cho toàn mạng.
- 🗄️ **O-LLVM Obfuscation (Anti-tamper):** Ứng dụng O-LLVM làm tối mã nguồn các tiến trình phục hồi trạng thái (Rehydration), khiến kẻ thù không thể dịch ngược để giả mạo CRDT State.

#### §Optimistic Append-Only Mesh — Giải quyết "Causal Freeze" (Mobile-Only Scenario)

> **Vấn đề:** Nhóm nhân viên toàn dùng iPhone/Android trong hầm ngầm (không có Laptop Super Node) → Không có Dictator → hệ thống "Causal Freeze" → không gửi được tin nhắn cứu hộ. Vi phạm Survival Mesh SLA.

```text
Trạng thái mới: OPTIMISTIC_APPEND_ONLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[Không có Desktop Super Node trong Mesh]
         │
         ▼
📱 Android (RAM ≥ 4GB) → Tạm thời làm Temporary Dictator
📱 iOS → Observer (chỉ đọc, ping vote)
         │
[Tin nhắn gửi đi dưới dạng Block độc lập — không Hash-Tree]
[UI: viền đứt nét xám mờ = Pending Merge State]
         │
[Khi 💻 Desktop Super Node vào Mesh]
         ▼
Desktop thu gom "orphan chains" → O(N log N) merge → push snapshot về Mobile
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

- 📱 **Android Temporary Dictator (RAM ≥ 4GB):** Khi không có Desktop trong Mesh, thiết bị Android có RAM ≥ 4GB và pin > 30% được tự động bầu làm `Temporary_Dictator` với `election_weight = 0.3` (thấp hơn Desktop 1.0, cao hơn Observer 0). Android chỉ merge tối đa 200 delta/lần (giới hạn RAM), sau đó yield cho Desktop khi có.
- 📱 **iOS — Observer Mode vĩnh viễn:** iOS giữ `election_weight = 0` do giới hạn Jetsam. Vai trò: broadcast tin nhắn Local Block + xác nhận (ACK) tin nhắn nhận. Không tham gia merge.
- 📱💻 **Optimistic Append-Only Blocks:** Tin nhắn được gửi dưới dạng độc lập (`AppendBlock{id, content, timestamp, device_sig}`) — không tính Hash-Tree merge real-time. Đơn giản, nhanh, không block. UI đánh dấu viền đứt nét xám (`border: 1px dashed rgba(148,163,184,0.5)`) = "Chờ Desktop merge".
- 💻 **Desktop Auto-Reconcile khi vào Mesh:** Desktop Super Node thu gom tất cả orphan `AppendBlock` chains từ các Mobile peers, thực hiện `O(N log N)` CRDT merge, xây dựng Merkle Tree hoàn chỉnh, push snapshot ngược về Mobile. Mobile message bubble chuyển từ dashed border → solid border khi reconcile xong.
- 📱 **IPC Memory Segregation (Mobile):** Toàn bộ IPC giữa Lõi Rust và UI layer trên Mobile dùng `JSI Native Pointer` (iOS) / `Dart FFI TypedData` (Android) — Zero-Copy, không qua MessageQueue/JSON bridge. RAM allocation cho IPC buffer tách biệt khỏi crypto key arena.



#### Desktop — SharedArrayBuffer + Protobuf

- 💻🖥️ **Control Plane:** Protobuf schema `terachat_ipc.proto` qua WASM/Rust channel — lệnh, metadata, SQL, offset pointer. Kích thước \<50 bytes/message.
- 💻🖥️ **Data Plane:** `SharedArrayBuffer` (mmap vật lý) — file chunk, record bulk, AI input. Ring Buffer cố định 10MB, chunk 2MB, throughput ~500MB/s.
- 💻🖥️ **Zero-Copy Flow:** WASM ghi I/O nhị phân vào SAB → Rust đọc con trỏ vật lý, validate CRC32, AES-256-GCM encrypt → ghi ciphertext vào offset khác trong SAB → WASM lấy kết quả. Không copy buffer.
- 💻🖥️ **Security Contract:**
  - ACL per-.tapp: mọi `UtilityAction` qua ACL Policy tại Rust Core trước khi xử lý.
  - `Company_Key` / `Channel_Key` tuyệt đối không truyền qua Protobuf lên WASM. WASM chỉ gửi data vào SAB, Rust tự dùng Key đang `mlock`'d.
  - Rust kiểm tra `offset + length ≤ SAB_SIZE` + validate CRC32. Vi phạm → `SIGSEGV` trap + panic.

#### Giải pháp: Data Diode Protocol & Guillotine Disconnect (Chống Tê liệt Zero-Copy IPC qua SharedArrayBuffer)

- 💻 **Shared Memory Ring Buffer (1-way 2MB):** Phân mảnh luồng đọc/ghi qua bộ đệm vòng giới hạn cứng 2MB, chia sẻ theo chiều duy nhất (Data Diode) để cô lập bộ nhớ của Rust và UI.
- 🖥️ **Rust Core Guillotine Cutoff:** Triển khai cơ chế chém đứt kết nối (Guillotine Disconnect) bằng `TerminateExecution()` ngay từ lõi Rust nếu phát hiện Sandbox có dấu hiệu Spin-lock hoặc vô hiệu hồi đáp.
- 💻 **Cross-Origin-Opener-Policy Fallback Bypass:** Đảm bảo tính khả dụng của WebView IPC ngay cả khi COOP/COEP Headers bị vô hiệu hóa ngầm định bởi hệ điều hành bằng fallback cơ chế luồng tin an toàn.

#### Mobile iOS — React Native JSI (C++ Shared Memory Pointer)

- 📱 **JSI C++ Pointer:** UI Native App bọc con trỏ C++ Shared Memory bằng `std::unique_ptr` với Custom Deleter → đâm thẳng vào luồng nhận của Rust FFI. Throughput ~400MB/s, bỏ qua WebView Bridge.
- 📱 **Crash-Safe Checkpoint:** Native UI lắng nghe `applicationWillTerminate` / `onTrimMemory` → bắn FFI signal `terachat_core_flush_io()` → Rust flush WAL checkpoint trước khi OS kill.
- 📱 Rust lock DB tối đa 50ms (Micro-batching). Không có transaction nào vượt ngưỡng này.

#### Mobile Android — Dart FFI + TypedData

- 📱 **Dart FFI TypedData:** Zero-Copy sang C ABI. Throughput ~400MB/s.
- 📱 Cùng Crash-Safe Checkpoint pattern: lắng nghe `onTrimMemory` → `terachat_core_flush_io()`.

> ⚠️ **Legacy bị loại bỏ:** Base64 qua WebView/MessageChannel (~25MB/s) — gây giật UI (blocking). Không dùng.

#### Unidirectional State Sync

Luồng state chỉ đi 1 chiều: `Rust -> Native UI -> Render`. UI tuyệt đối không chứa business state.

#### Dual-Plane & Strict Data/Control Plane Segregation

- 📱 **Quy hoạch Strict Data / Control Plane Segregation:** Để giải quyết nghẽn cổ chai JS Thread khi đồng bộ CRDT khối lượng lớn, hệ thống phân tách dứt khoát luồng dữ liệu (Data Plane) và luồng điều khiển (Control Plane).
- 📱 **C/C++ FFI WebRTC / Wi-Fi Direct Socket Bypass:** Payload dữ liệu CRDT truyền trực tiếp qua P2P socket bằng C/C++ FFI, rẽ nhánh hoàn toàn khỏi JS Thread.
- 📱 **Rust Core Background Thread SQLite Merge:** Mọi thác tác hợp nhất CRDT phức tạp được đẩy xuống Rust Core Background Thread xử lý và ghi thẳng vào SQLite, không làm tắc nghẽn luồng UI.
- 📱 **JSI Control Plane Event Callback:** JS Thread rảnh rỗi và chỉ đảm nhận vai trò Control Plane — nhận Event Callback từ JSI để phát lệnh re-render UI, chấm dứt triệt để hiện tượng UI đơ cứng (JS freeze).

### 11.2 "Zero-Byte" App Stubs (WASM)

> 🔗 **Structural Note:** Nội dung của mục này (và 11.3) đã được hợp nhất và mở rộng tại **Section 7.1 (WASM Sandbox & Dual-Registry)**. Đọc Section 7.1 để tham khảo kiến trúc đầy đủ và tính năng bảo mật nâng cao.

- 📱💻🖥️ Bề mặt UI `.tapp` chỉ là một file `.wasm` siêu nhẹ (10KB - 50KB), tải nóng từ Mesh trong 10ms.
- 📱💻🖥️ Mọi logic "nặng" đều gọi xuống Rust qua IPC.
- ☁️ Máy chủ không chứa frontend code, chỉ điều phối cấu trúc nhánh.

### 11.3 Độc thủ từ WASM Sandbox Escape (Zero-Trust WASM Host Binding & OPA Guardrail)

- 💻🖥️ Phân cách hoàn toàn luồng điều khiển và dữ liệu qua IPC Bridge Architecture (SharedArrayBuffer + Protobuf).
- 📱💻🖥️ Tuân thủ Key Isolation Protocol, kiên quyết block đường truyền phân bổ `Company_Key` và `Channel_Key` qua IPC lên môi trường thực thi WASM.
- ☁️📱💻 Úy thác cho hệ nhúng Rust Core ACL Policy (OPA Engine) quyền sinh sát giám sát mọi `UtilityAction` dựa trên App Whitelist trước khi nhả lệnh thực thi.

#### Memory Air-Gapping & DMZ Shared Memory

- 📱💻🖥️ Cách ly hoàn toàn vùng nhớ tuyến tính (Linear Memory) của WASM khỏi không gian địa chỉ vật lý của Rust Core.
- 💻🖥️ Thiết lập cơ chế "Cửa khẩu" (DMZ) qua SharedArrayBuffer 10MB chỉ chứa dữ liệu đã copy (tuyệt đối không chứa con trỏ vật lý).
- 💻🖥️ Ràng buộc hàm Bounds Checking nghiêm ngặt (`offset + len ≤ SAB_SIZE`) nhằm ngăn chặn mọi hành vi truy cập ngoài biên.

### 11.4 Phá nút thắt Cổ chai Bộ nhớ WASM (Dual-Plane Mobile Native Bridge Bypass)

- 📱 Tích hợp cổng React Native JSI C++ Pointer cho hệ sinh thái iOS nhằm đâm thẳng luồng dữ liệu từ hệ thống Rust Core xuất sang UI đạt mức throughput ~400MB/s.
- 📱 Áp dụng giao diện Dart FFI TypedData cho Android thực thi tín hiệu Zero-Copy nạp thẳng sang kiến trúc C ABI tĩnh, bypass 100% tài nguyên bộ nhớ từ WASM Sandbox.
- 📱 Tách bạch nhiệm vụ Control Plane (định hướng WASM) và Data Plane (điều hướng Native FFI) chuyên môn hoá xử lý tệp tin hạng nặng nhằm dập tắt hiểm họa OOM-Kill từ gốc rễ.

#### Virtual File Handles & Zero-Copy Bypass (Ánh xạ tệp ảo WASM)

- 📱💻🖥️ Trừu tượng hóa luồng byte qua `File_Handle_ID` (vfs_id) để giữ Metadata IPC siêu nhẹ (<50 bytes).
- 📱💻🖥️ Cơ chế Stream Pumping vận chuyển trực tiếp payload từ đĩa cứng xuống Network Socket thông qua Lõi Rust Proxy.
- 📱💻🖥️ Áp dụng kỹ thuật mmap bypass vùng nhớ Sandbox WASM nhằm triệt tiêu hoàn toàn rủi ro OOM-Kill khi giải quyết tệp hàng GB.

---

### 6.10 Rust Semantic State Transition Firewall (Chống Tiêm nhiễm Trạng thái Rác)

> **Bài toán:** Kẻ tấn công có thể inject CRDT event hợp lệ về mặt cú pháp nhưng chứa payload ngữ nghĩa độc hại (ví dụ: event chèn `admin_role` cho user thường) hoặc phá vỡ quan hệ nhân quả của DAG. Không có lớp validation ngữ nghĩa, event này sẽ merge thẳng vào SQLite mà không bị chặn.

- 💻📱 **Rust-based Semantic Validation Pipeline:** Mọi CRDT event — dù đến từ Server, Peer, hay chính Local App — đều phải đi qua một Pipeline xác thực tại Lõi Rust trước khi được ghi vào SQLite WAL. Pipeline gồm 3 bước: (1) Schema Validation, (2) Causal Integrity Check, (3) Cryptographic ACL Enforcement. Bất kỳ bước nào thất bại → event bị `Drop()` ngay lập tức và ghi log vào Audit Trail.
- 💻📱 **DAG Causal Integrity Check (HLC / Vector Clock):** Lõi Rust kiểm tra event mới có `parent_hash` và `vector_clock` hợp lệ trong Causal DAG hiện tại. Nếu event cố tình bỏ qua predecessor (ví dụ: nhảy cóc để override một message đã xóa), → từ chối với lỗi `CAUSAL_VIOLATION`. Sử dụng Hybrid Logical Clock (HLC) để giải quyết race condition multi-device.
- 💻📱 **Hard-coded Cryptographic ACL Enforcement:** Mỗi loại CRDT event (AddMember, RevokeKey, UpdateRole) được liên kết với một `required_signing_key_role` được hard-code tại Lõi Rust. Ví dụ: event `GRANT_ADMIN` PHẢI được ký bởi `Company_Key` cấp Admin — nếu ký bởi User Key → `ACL_VIOLATION`, Firewall bắn cờ `SUSPICIOUS_EVENT` lên Audit Trail.
- 💻📱 **Zero-copy Schema Validation:** Trước khi decode toàn bộ event, Lõi Rust sử dụng `flatbuffers` hoặc `capnproto` để xác thực header schema tại chỗ (in-place), không cần allocate heap. Reject event có kích thước bất thường (`> MAX_EVENT_SIZE`) hoặc field type sai ngay tại tầng này — tránh parser amplification attack.

---

### 6.11 Deterministic Local Audit & Boomerang Penalty (Xác thực Lời buộc tội / Phản pháo)

> **Bài toán:** Sau khi Byzantine Shun được kích hoạt, hệ thống cần cơ chế xác thực nội bộ để tránh oan sai — và phải phạt node cáo buộc sai để ngăn lạm dụng cơ chế Shun như một vũ khí.

- 💻📱 **Rust State Transition Firewall (Semantic Validation):** Pipeline State Firewall tại Lõi Rust (đã mô tả tại 6.10) đồng thời hoạt động như bộ máy kiểm toán nội bộ: mỗi lần reject event, Firewall ghi lại `(Node_ID, rejection_reason, hlc_timestamp)` vào Audit Log — không ghi lên Server, chỉ lưu locally và tổng hợp vào Proof_Bundle nếu được yêu cầu.
- 💻📱 **Slashed Trust / Boomerang Penalty Logic:** Khi hệ thống nhận đủ 2 `Proof_Bundle` (theo OCPM) nhưng sau khi xác minh, kết luận cáo buộc là sai (ví dụ: signature hợp lệ, HLC trong ngưỡng), Lõi Rust tự động áp dụng **Trust Score Penalty** cho node cáo buộc sai: điểm trust bị trừ, cần thêm Proof_Bundle ở các lần Shun tiếp theo. Sau 3 lần cáo buộc sai → node tự động bị Quarantine khỏi quyền bỏ phiếu Shun trong 72h.
- 💻📱 **Independent Edge Audit Pipeline:** Mỗi Super Node (Desktop) duy trì một pipeline kiểm toán độc lập, thu thập bằng chứng từ nhiều Leaf Node và cross-validate trước khi forward Shun lên Gossip. Không có single-point-of-failure trong quá trình cáo buộc.
- 💻📱 **Deterministic Behavioral Verification:** Lõi Rust so sánh hành vi quan sát được của node bị cáo buộc với baseline hành vi hợp lệ (state machine determinism check): nếu cùng một input cho ra output khác nhau giữa 2 lần quan sát → cờ `NON_DETERMINISTIC_BEHAVIOR`, nâng độ tin cậy cho cáo buộc.

---

### 6.12 Two-Tier State Squashing & Causal Stability Horizon (Chống Log Phình to Database trên Mobile)

> **Bài toán:** Sau thời gian dài hoạt động, DAG tích lũy hàng ngàn CRDT event nhỏ gây phình to SQLite trên thiết bị Mobile. Cần compact mà không phá vỡ causal consistency hay mất dữ liệu.

- 📱 **Kiến trúc Two-Tier SQLite:** Tách biệt hai database: `hot_dag.db` (Append-Only, chứa raw CRDT event mới nhất, < 7 ngày) và `cold_state.db` (Squashed Key-Value, chứa state đã flatten, không giữ history). Lõi Rust ghi mới vào `hot_dag.db`; UI đọc từ `cold_state.db` kết hợp truy vấn live từ `hot_dag.db` qua UNION.
- 📱 **Operation Squashing:** Lõi Rust nhóm các chuỗi sự kiện `CREATE → EDIT_1 → EDIT_2 → ... → EDIT_N` trên cùng một entity thành một bản ghi Squashed duy nhất trong `cold_state.db`. Không cần giữ intermediate state, tiết kiệm tối đa 80% dung lượng so với raw DAG.
- 💻📱🖥️ **Causal Stability Frontier (Global/Local) via Vector Clock:** Lõi Rust xuất hiện định kỳ, tính toán `Causal Stability Frontier` — tập hợp event đã được tất cả peer xác nhận (ACK) trong Mesh, không thể có event mới chèn vào trước frontier. Chỉ event nằm **sau frontier mới được Squash** — đảm bảo không Squash event chưa được đồng bộ.
- 📱 **Background Pruning với CPU Throttling:** Tiến trình Squash chạy qua `requestIdleCallback` (iOS: `BGProcessingTask`) với giới hạn 50ms CPU/batch. Nếu pin < 20% → tự động Suspend Pruning cho đến khi cắm sạc.

- 📱💻🖥️ **TeraVault VFS (Zero-Byte Stubs) — Giải quyết `SQLITE_TOOBIG` cho File Khổng lồ:**
  - > **Crash Surface:** Nếu cố nhét file 10GB vào `hot_dag.db` dưới dạng BLOB, SQLite throw `SQLITE_TOOBIG` (giới hạn biên dịch max ~1–2GB/BLOB) và corrupt Causal Graph. I/O 10GB trên Main DB còn gây Lock DB → UI ANR.
  - 📱💻🖥️ **Zero-Byte Stubs:** `hot_dag.db` **KHÔNG BAO GIỜ** lưu payload video/file lớn. Thay vào đó, CRDT event chỉ ghi một Stub cực nhỏ: `{File_ID, Name, Size_bytes, Merkle_Root_Hash_BLAKE3, MinIO_S3_URL, Chunk_Count, Status}`. Dung lượng mỗi Stub < 512 bytes bất kể file gốc lớn bao nhiêu.
  - 📱💻🖥️ **TeraVault VFS Layer:** Khi UI muốn xem nội dung file, nó query Stub → Lõi Rust resolve `MinIO_S3_URL` → stream chunk-by-chunk qua Native-to-Rust Media DataSource Bridge (§8.1). Người dùng thấy video phát ngay trong < 1 giây (zero buffering delay) trong khi Rust download và decrypt chunk đầu tiên 2MB trong background.
  - ☁️🗄️ **Content-Addressable Storage:** `MinIO_S3_URL` là stable, content-addressable URL dạng `s3://teravault/{org_id}/{BLAKE3_Root_Hash}`. Cùng file gửi nhiều lần trong org → chỉ 1 copy duy nhất trên MinIO (deduplication tự động qua Root Hash). Tiết kiệm storage 60–80% cho các file phổ biến (training video, templates).

- 📱💻🖥️ **OS Background Delegation — Né App Suspension cho Upload File Lớn:**
  - > **Crash Surface (iOS):** Lõi Rust tự tải file 10GB khi App bị swipe → Background → bị iOS freeze sau 30 giây. Upload chết yểu ở bất kỳ %. Android không gặp vấn đề này nhưng vẫn cần WorkManager để tối ưu pin.
  - 📱 **iOS — NSURLSession Background Transfer:** Lõi Rust sinh danh sách `Pre_signed_URL[chunk_0..chunk_N]` (TTL 15 phút/URL, HMAC-SHA256 device-bound), bàn giao toàn bộ cho `NSURLSession` với `sessionConfiguration.isDiscretionary = false`. Apple OS tự duy trì socket, tự retry khi mạng phục hồi, báo progress `didSendBodyData` về UI kể cả khi App locked.
  - 📱 **Android — WorkManager Chained Tasks:** Mỗi chunk tương ứng 1 `Worker`: `[Encrypt_Chunk → S3_Upload → ZeroizeOnDrop]`. Constraint: `NetworkType.CONNECTED + requiresBatteryNotLow()`. WorkManager tự schedule và retry sau mất kết nối.
  - 📱💻🖥️ **Progress Aggregation:** UI nhận event `FILE_UPLOAD_CHUNK_ACK(chunk_index, merkle_path)` từ OS/Rust qua IPC. Progress bar = `(acked_chunks / total_chunks) * 100`. Hiển thị tốc độ upload real-time và ETA.

  - > **Attack Surface:** Khi màn hình iOS bị khóa, `NSFileProtectionComplete` tự động thu hồi key giải mã file → `hot_dag.db` trở nên inaccessible. NSE (Notification Service Extension) nhận push notification lúc này **không thể ghi** payload vào SQLite → mất tin nhắn.
  - > **Giải pháp:** NSE phát hiện exception `EPERM` khi cố ghi vào `hot_dag.db` → tự động chuyển sang VMS (Volatile Memory Staging):
  - 📱 **Tier 1 — Shared Keychain Cache:** NSE lưu payload mã hóa vào `kSecClassGenericPassword` trong App Group Keychain (`group.com.terachat.alpha`). Keychain không bị `NSFileProtectionComplete` tác động. Dung lượng tối đa: 256KB/entry.
  - 📱 **Tier 2 — In-Memory Cache (Failsafe):** Nếu Keychain đã đầy, NSE giữ payload trong RAM với `mlock()`. Dữ liệu tồn tại đến khi NSE extension bị Jetsam kill (tối đa ~30s).
  - 📱 **Hydration Sync (Khi Unlock):** Ngay khi thiết bị Unlock, Main App nhận tín hiệu `UIApplicationDidBecomeActiveNotification` → Lõi Rust đọc toàn bộ VMS entries từ Keychain + drain vào `hot_dag.db` theo chuẩn ACID như Atomic Drain protocol đã mô tả tại §6.12.

- 📱 **Two-Phase Cryptographic Commit — Giải quyết Race Condition (Keychain Forensic Leak):**
  - > **Attack Surface (Urgent):** Nếu Main App bị OS Crash hoặc Force Kill ngay giữa quá trình "Atomic Drain" (đã đọc Keychain nhưng chưa kịp `DELETE` entry) → Plaintext payload kẹt vĩnh viễn trong Shared Keychain. Các công cụ Forensic (Cellebrite, GrayKey) có thể đọc toàn bộ dữ liệu. Đây là vi phạm cam kết Zero-Retention.
  - 📱 **Pha 1 — Write-then-Delete Ciphertext:** Lõi Rust đọc Ciphertext từ Keychain, sinh `Tx_ID = UUID_v7()`, ghi nguyên Ciphertext (chưa giải mã) vào `nse_staging.db` với key `(Tx_ID, status="PENDING")`, rồi **lập tức xóa Keychain entry** trong cùng một synchronized block. Dù Crash xảy ra ở bất kỳ mili-giây nào, Keychain đã sạch — Ciphertext vẫn an toàn trong `nse_staging.db`.
  - 📱 **Pha 2 — Decrypt & Commit:** Sau khi Keychain đã xóa, Lõi Rust mới tiến hành giải mã từ `nse_staging.db` (trong RAM `mlock()`) và merge vào `hot_dag.db` theo ACID transaction. Nếu Crash ở Pha 2 → Lần mở App tiếp theo, Lõi Rust phát hiện `Tx_ID` có `status="PENDING"` → re-decrypt và retry từ `nse_staging.db`.
  - 📱 **Idempotent Recovery:** `Tx_ID` đảm bảo mỗi entry chỉ được xử lý đúng 1 lần, ngăn duplicate merge dù retry nhiều lần sau crash.

- 📱 **iOS Feature Parity — AI Smart OCR & DLP (CoreML, không cần WASM):**
  - > **Ràng buộc:** iOS cấm tải `.tapp` WASM động (Rule 2.5.2). Giải pháp: đưa toàn bộ model NLP và OCR vào file `.mlmodelc` (CoreML) đóng gói sẵn trong App.
  - 📱 **CoreML OPA Unlock:** Khi user bấm cài đặt tiện ích AI trên Marketplace iOS, hệ thống **chỉ** gửi OPA Policy JSON qua IPC để "Unlock" module CoreML tương ứng đã bundle sẵn — không tải byte WASM nào qua mạng. Trải nghiệm unlock < 1s y hệt Desktop.
  - 📱 **Parity:** User iOS nhận đúng các tính năng Smart OCR và DLP NER như Android/Desktop. Khác biệt nằm ở Engine (CoreML vs Wasmtime JIT), không khác biệt về UX.

- 📱 **iOS Feature Parity — C-Level Hardware Bypass (CoreNFC YubiKey NFC Ring):**
  - > **Ràng buộc:** iOS không có cổng USB-A cho YubiKey truyền thống. Giải pháp: đọc applet ISO 7816 qua NFC.
  - 📱 **CoreNFC ISO 7816 Applet:** Lõi Rust giao tiếp với YubiKey NFC hoặc NFC Smart Ring thông qua `CoreNFC NFCTagReaderSession`. Modal UI hiển thị: *"Chạm chìa khóa vào lưng iPhone"* thay vì *"Cắm USB"*. Toàn bộ CTAP2 Challenge-Response vẫn giữ nguyên — chỉ thay đổi transport layer từ USB HID sang NFC ISO-DEP.
  - 📱 **Parity:** C-Level trên iOS vẫn có khả năng Hardware-Backed Self-Sovereign Recovery đầy đủ, không bị thọt so với Desktop.

- 📱 **iOS Feature Parity — Background File Transfer (NSURLSession Background Transfer):**
  - > **Ràng buộc:** iOS nghiêm cấm Rust Core tự tải file lớn khi khóa màn hình. Android dùng `WorkManager` thoải mái. Giải pháp: ủy quyền hoàn toàn cho OS.
  - 📱 **Pre-signed URL Delegation:** Thay vì Rust Core tự tải, hệ thống sinh Pre-signed URL một lần (TTL 15 phút, HMAC-SHA256 bound to device) và giao cho `NSURLSession` Background Transfer Service của Apple tải file mã hóa. Apple ecosystem tự quản lý toàn bộ retry, resume, và OS-level scheduling.
  - 📱 **Wake-up Window Decrypt:** Khi Apple hoàn thành tải tệp mã hóa, iOS đánh thức App trong 30 giây. Lõi Rust tranh thủ `mmap` và giải mã siêu tốc vào VFS trong cửa sổ 30 giây này. Tính năng *tải file offline* vẫn mượt mà ngang Android — khác biệt chỉ là AI Apple scheduling, không phải user experience.

 & Tự hủy Nguyên tử (Crypto-Shredding) — Chống "Poison Pill" phân mảnh `nse_staging.db`:**
  >
- > **Attack Surface:** NSE extension thoát đột ngột (Jetsam kill giữa chừng ghi WAL) để lại `nse_staging.db` ở trạng thái "Poison Pill" — phân mảnh WAL/SHM không nhất quán, gây crash lặp vô hạn khi Main App cố đọc.
- 📱 **SQLite Integrity Self-Check:** Khi Main App mở `nse_staging.db`, Lõi Rust thực thi `PRAGMA quick_check(1)` bọc trong `Result<T, E>`. Nếu kết quả trả về `Err` hoặc phát hiện page corruption → lập tức escalate sang Crypto-Shredding thay vì panic.
- 📱 **POSIX `unlink()` Atomic File Wipe:** Lõi Rust gọi `POSIX unlink()` tuần tự trên bộ ba `nse_staging.db` + `nse_staging.db-wal` + `nse_staging.db-shm`. `unlink()` đảm bảo nguyên tử ở tầng filesystem — file descriptor vẫn hợp lệ cho tiến trình đang giữ handle, nhưng entry trong directory inode bị xóa ngay lập tức, ngăn bất kỳ reader nào truy cập file độc.
- 📱 **Crypto-Shredding (Ghi đè `0x00`):** Sau `unlink()`, Lõi Rust ghi đè toàn bộ dữ liệu còn lại trên sector bộ nhớ bằng pattern `0x00` (zero-fill) trước khi giải phóng memory mapping. Đảm bảo Forensic Non-Retrievability ngay cả trên thiết bị bị thu giữ.

- 📱💻☁️ **Targeted DAG Hydration & In-Memory Atomic Commit — Vá "Gap" Causal Graph:**
  - > **Attack Surface:** Sau khi Crypto-Shredding xoá `nse_staging.db`, tồn tại khoảng trống (Gap) trong Causal Graph của `hot_dag.db` — các tin nhắn NSE nhận trong khi màn hình khoá bị mất, gây ra "orphan edges" trong CRDT DAG.
  - 💻☁️ **BLAKE3 Segmented Merkle Tree Delta-Pack:** Server / Super Node đóng gói toàn bộ `Delta-State` trong khoảng Gap (từ `last_known_CAS_UUID` của client đến `current_frontier`) thành một Segmented Merkle Tree ký bởi BLAKE3. Client xác thực toàn vẹn từng segment bằng cách đối chiếu Merkle Path mà không cần tải toàn bộ payload.
  - 📱 **RAM-only Decrypt với `mlock()`:** Lõi Rust giải mã từng Delta-State segment trực tiếp trên vùng nhớ RAM được khoá bởi `mlock()` — đảm bảo payload giải mã **không bao giờ swap ra swap partition**, không lộ ra disk cache ngay cả khi thiết bị bị Jetsam-kill giữa chừng.
  - 📱 **Foreground Atomic Commit vào `hot_dag.db`:** Sau khi decrypt và xác thực Merkle Proof, Lõi Rust chèn toàn bộ Delta-State batch vào `hot_dag.db` trong một SQLite transaction ACID duy nhất (Foreground thread). Nếu commit thất bại → rollback toàn bộ batch, retry từ đầu segment đó.

- 📱🖥️ **IO-Deferred Compaction & Adaptive Epidemic Routing — Chống I/O Spike & Broadcast Storm:**
  - > **Attack Surface (1 — SSD Wear):** Ghi liên tục nhiều lệnh Write/Unlink nhỏ lên flash storage trong Survival Mesh tăng tốc hao mòn chu kỳ P/E (Program/Erase) chip nhớ NAND, rút ngắn tuổi thọ thiết bị.
  - > **Attack Surface (2 — Broadcast Storm):** Nhiều node phát `GossipStateRequest` đồng thời trong vùng phủ sóng Super Nodes dày đặc gây xung đột tín hiệu, bão mạng, và bão ping-pong Vector Clock.
  - 📱 **SQLite WAL In-Memory Batching:** Lõi Rust tích tụ tất cả thao tác Write/Unlink vào bộ đệm RAM `mlock'd`, chỉ flush xuống disk theo ngưỡng khối lượng lớn (batch ≥ 512KB hoặc sau 5 giây idle), triệt tiêu pattern ghi nhỏ lẻ gây wear SSD.
  - 📱🖥️ **Adaptive Trickle Algorithm (Epidemic Routing):** Mỗi node tự động giãn cách thời gian phát `GossipStateRequest` theo hàm mũ khi phát hiện xung đột tín hiệu cao (`collision_backoff = base_ms × 2^collision_count`, max 30s). Super Nodes trong vùng phủ sóng dày đặc tự động coordinate thành Aggregation Hub.
  - 💻 **Bloom Filter State Reconciliation:** Tại tầng Network Interface, Lõi Rust duy trì một Bloom Filter cập nhật liên tục (false positive rate < 0.1%) để lọc và hủy ngay lập tức các gói tin Vector Clock trùng lặp — triệt tiêu vòng lặp bão mạng mà không cần tra cứu database, $O(k)$ hash function, không I/O.

- 📱🖥️💻 **Atomic Hydration Checkpointing & Anti-Entropy DAG Reconciliation — Chống mất toàn vẹn CRDT khi Hard Power Loss:**
  - > **Attack Surface:** Mất nguồn đột ngột giữa Hydration Session phân mảnh Merkle Tree đang xây dựng trong WAL In-Memory → không thể xác định chunk nào đã commit, chunk nào bị mất → khởi động lại gây duplicate CRDT inserts hoặc orphan DAG leaf.
  - 📱 **Hydration_Checkpoint Atomic Pre-Write:** Trước khi tích tụ bất kỳ batch nào vào WAL In-Memory, Lõi Rust ghi nguyên tử `{Snapshot_CAS_UUID, last_chunk_index, root_hash_partial}` vào `hot_dag.db` (bảng `hydration_checkpoints`). Checkpoint này là "lời hứa" cho lần khởi động tiếp theo — rollback an toàn về trạng thái đã xác thực gần nhất.
  - 📱🖥️ **Anti-Entropy Merkle Sync (Gossip-based):** Khi tái gia nhập Mesh sau power loss, Lõi Rust thực thi đối soát Root Hash chéo qua giao thức Gossip với các Super Nodes lân cận. Nếu Root Hash local lệch với quorum → tự động kéo Delta-State bù đắp từ Super Nodes có Root Hash xác thực.
  - 📱💻 **Ed25519 Signature Pruning:** Lõi Rust quét toàn bộ DAG local leaves và tự động prune (cắt tỉa) bất kỳ node nào không qua được xác thực chữ ký `DeviceIdentityKey` Ed25519 — ngăn "nhiễm độc" Cây trạng thái bởi CRDT event phân mảnh/giả mạo trước khi thực hiện merge.
  - 💻🖥️📱 **Append-Only & Atomic Pointer Swap (Phòng vệ Hard Power Loss):** Các sự kiện CRDT được cam kết dưới hình thái Append-Only. Việc xoay chiều ghi nhận chỉ xảy ra sau khi hoàn tất Point Swap nguyên tử, tạo thành rào chắn không thể vượt qua đối với các lỗi Sập nguồn cứng (Hard Power Loss) gây hỏng Checkpoint DB.
  - 💻🖥️📱 **16MB Pre-allocated Static Rollback_Journal:** Cấp phát sẵn và Tĩnh hóa một Tệp Nhật ký Hoàn tác (Static Rollback Journal) cố định ở mức 16MB. Kỹ thuật này triệt tiêu chi phí vòng đời I/O cấp phát khối dữ liệu mới mỗi khi File System muốn dọn dẹp không gian, giảm rớt tiến trình (Crash).
  - 💻🖥️📱 **BLAKE3 Checksum Verification & DAG Root_Hash Recovery:** Đi kèm mỗi Entry trong Journal là hàm băm mã hoá cường độ cao BLAKE3 để xác minh tính toàn vẹn (Checksum). Khi phát hiện tập tin Checkpoint bị rách nát sau cố sự cố mất điện, Lõi Rust tự động tái chế DAG Root_Hash từ các lá hợp lệ còn sót lại trong Journal.

---

### 6.13 Zero-Knowledge Snapshot Sync — Cold State Bootstrapping (Chống Lạc trôi Nhân quả & Orphan DAG)

> **Bài toán:** Thiết bị offline dài ngày sẽ có DAG lỗi thời (hàng nghìn event sau Causal Stability Frontier). Replay toàn bộ event log tốn RAM và thời gian $O(N)$ — không khả thi trên Mobile. Cold State Bootstrap giải quyết bằng $O(1)$ từ Snapshot.

- 📱💻 **Final Materialized State Snapshot (Squashed Event Logs):** Server hoặc Super Node định kỳ xuất **Snapshot** — bản chụp `cold_state.db` tại thời điểm Causal Stability Frontier — không chứa CRDT event thô, chỉ chứa final materialized state của từng entity. Thiết bị reconnect tải Snapshot thay vì replay toàn bộ log.
- 📱💻 **TeraVault VFS (Content-Addressable Storage / CAS UUID):** Mỗi Snapshot được định danh bằng `CAS_UUID = SHA-256(snapshot_content)` và lưu trong TeraVault VFS. Thiết bị chỉ cần verify hash để xác nhận tính toàn vẹn mà không cần tải lại nếu đã có local cache trùng UUID.
- ☁️📱💻🖥️ **Epoch-Keyed Parquet/SQLite Backups:** Snapshot được export theo định dạng Parquet (lớn, dành cho Desktop/Server) hoặc SQLite (compact, dành cho Mobile), đặt tên theo `epoch_N.snapshot`. Thiết bị chỉ tải `epoch_current.snapshot` → bỏ qua toàn bộ intermediate history.
- 📱💻🖥️ **Độ phức tạp Phục hồi $O(1)$:** Sau khi tải Snapshot, Lõi Rust ghi trực tiếp vào `cold_state.db` qua `INSERT OR REPLACE` trong một transaction duy nhất. Tổng thời gian bootstrap cố định bất kể số lượng event lịch sử.

### 6.14 Tràn bộ nhớ (OOM-Kill) trên Mobile khi đồng bộ DAG cục bộ

> **Bài toán:** Quá trình giải mã và tái cấu trúc hàng chục nghìn Node của cây DAG khi Sync nội bộ tạo ra hàng loạt object nhỏ lẻ trong RAM, dồn ép Garbage Collector và lập tức kích nổ OOM-Kill trên iOS/Android.

- 📱 **Phân mảnh AES-256-GCM Streaming Decryption:** Giải mã DAG theo hình thức Streaming (chunk 2MB) đi qua JSI Native Pointer để triệt tiêu tải RAM cấp phát đột biến.
- 📱 **POSIX Atomic Rename (Torn Write Prevention):** Sử dụng POSIX Atomic Rename hoán đổi con trỏ file $O(1)$ từ `cold_state_shadow.db` sang `cold_state.db` nhằm ngăn chặn File Corruption (Torn Write) nếu App bị văng giữa chừng.
- 📱 **ZeroizeOnDrop ChunkKey:** Áp dụng `ZeroizeOnDrop` dọn sạch bộ đệm ChunkKey sau mỗi chu kỳ Chunk, đảm bảo Local Heap không phình to quá 5MB.

---

### 6.14 Stream-based Hydration & Direct-to-Disk I/O (Chống OOM-Kill khi Ghi DB)

#### Đồng bộ hóa Hoạt cảnh và Bơm dữ liệu (Animation-Sync)

- 📱💻🖥️ **Animation ACK & Post-Render Hydration:** Cấu trúc luồng Control Plane Signaling đợi Native UI bắn tín hiệu `UI_ANIMATION_COMPLETE` mới kích hoạt luồng Hydrate nhồi dữ liệu nặng.
- 📱💻🖥️ **Zero-Byte Stubs Barrier:** Render ngay lập tức mã BlurHash (<5KB) cực nhẹ để duy trì cảm giác phản hồi thị giác trong lúc màn nhung hoạt cảnh (Slide/Fade) đang diễn ra.
- 📱💻🖥️ **Async Event Loop:** Vận hành vòng lặp sự kiện bất đồng bộ duy trì chuẩn phản hồi IPC siêu nhẹ dưới ngưỡng hẹp $5\text{ms}$.

> **Bài toán:** Việc tải Snapshot lớn vào RAM trước khi ghi DB sẽ gây OOM-Kill trên Mobile (giới hạn 150-200MB foreground). Stream Hydration giải quyết bằng cách ghi trực tiếp theo từng chunk mà không giữ toàn bộ payload trên heap.

- 📱💻🖥️ **SharedArrayBuffer / JSI C++ Shared Memory IPC:** Dữ liệu Snapshot chảy từ Network Layer → Lõi Rust qua `SharedArrayBuffer` / JSI C++ Shared Memory (Zero-copy) — không allocate heap cho toàn bộ payload, chỉ giữ window 2MB tại một thời điểm.
- 📱💻🖥️ **2MB Chunked AES-256-GCM Streaming Decryption:** Lõi Rust giải mã Snapshot theo từng chunk 2MB, xác thực GCM Tag từng chunk độc lập trước khi flush xuống disk — nếu chunk nào lỗi thì rollback chỉ chunk đó, không phải toàn bộ quá trình.
- 📱💻🖥️ **Direct-to-Disk SQLite `INSERT OR REPLACE` (cold_state.db):** Mỗi chunk được parse và ghi thẳng vào `cold_state.db` qua `BEGIN IMMEDIATE TRANSACTION → INSERT OR REPLACE → COMMIT` mà không đi qua in-memory buffer. WAL mode đảm bảo atomic write ngay cả khi process bị kill giữa chừng.
- 📱 **Background Task Hydration (`requestIdleCallback`):** Toàn bộ pipeline Stream Hydration chạy trong `BGProcessingTask` (iOS) / `WorkManager` (Android) với CPU budget 80ms/iteration. Nếu foreground app cần CPU → tự động Yield, tiếp tục ở iteration tiếp theo mà không mất dữ liệu nhờ WAL checkpoint.
- 📱 Sử dụng Ghost Push Skeleton (chỉ chứa `Message_ID` & `Encrypted_URL`) để kích hoạt silent push.
- 📱 Trì hoãn TreeKEM WASM Runtime (Deferred), tránh tải WASM toàn bộ bộ nhớ khi app ở chế độ nền.
- 📱 Ủy quyền (Delegation) cho CoreML AOT (`.mlmodelc`) xử lý suy luận gọn nhẹ để tránh Jetsam DAG Crash (OOM-Kill).

### 6.14.1 Atomic Shadow Hydration — Torn Write Prevention (Bù nước Tạo bóng Nguyên tử)

> **Bài toán:** Trên iOS, `BGProcessingTask` có thể bị OS kill bất kỳ lúc nào mà không có warning — nếu kill xảy ra giữa chuỗi `INSERT OR REPLACE`, `cold_state.db` có thể bị **Torn Write**: một phần chunk đã ghi, phần còn lại chưa ghi, database ở trạng thái corrupt không thể đọc.

- 📱💻🖥️ **Shadow Paging (Cách ly luồng ghi vào DB tạm):** Lõi Rust không ghi trực tiếp vào `cold_state.db`. Thay vào đó, mỗi phiên Hydration khai báo một file tạm `cold_state_shadow.db` — toàn bộ chunk được ghi vào Shadow file để bảo vệ tính nhất quán của SQLite WAL. File gốc `cold_state.db` không được đụng đến cho đến khi Shadow hoàn tất. Nếu bị kill giữa chừng, `cold_state.db` nguyên vẹn, Shadow file bị bỏ lại có thể detect và cleanup.
- 📱 **Idempotent Checkpointing (`Snapshot_CAS_UUID`):** Sau mỗi chunk flush thành công vào Shadow file, Lõi Rust duy trì một cursor `Snapshot_CAS_UUID` và `last_chunk_index` vào `hot_dag.db`. Nếu bị kill, lần khởi tiếp theo đọc cursor này để resumption luồng stream từ điểm ngắt, bỏ qua chunk đã ghi. Đảm bảo tính **Idempotent** — không ghi đôi dữ liệu.
- 📱💻🖥️ **POSIX Atomic Rename (Hoán đổi con trỏ file $O(1)$):** Chỉ khi toàn bộ `cold_state_shadow.db` đã ghi xong và fsync thành công, Lõi Rust gọi `rename()` để hoán đổi con trỏ file $O(1)$ tại tầng File System. Kernel đảm bảo quá trình này là nguyên tử — không có trạng thái trung gian. Sau rename, `cold_state.db` chứa state hoàn chỉnh.
- 📱💻🖥️ **ZeroizeOnDrop (RAII) cho AES-256-GCM Key:** Mỗi chunk AES-256-GCM key được wrap trong Rust struct `ChunkKey(ZeroizeOnDrop)`. Ngay sau khi xử lý xong từng chunk 2MB, biến `ChunkKey` ra khỏi scope → Rust tự động gọi `Drop` → `zeroize()` xóa sạch khóa khỏi RAM. Không có window nào để key tồn lại trong heap.

---

### 6.15 Cross-Platform Deterministic Byte Ordering (Chống Sai lệch Xác thực Đa nền tảng)

> **Bài toán:** ARM (Mobile) dùng Little-Endian, x86 Server dùng Little-Endian nhưng network stack chuẩn Big-Endian — một trường `uint64` serialize khác nhau giữa nền tảng sẽ khiến Ed25519 signature xác thực fail mặc dù nội dung logic giống nhau, gây reject oan các packet hợp lệ.

- 📱💻🖥️ **Deterministic Protobuf Serialization (Fixed Byte Order):** Lõi Rust bắt buộc dùng Protobuf với field encoding chuẩn (varint Little-Endian, `fixed64` Little-Endian theo spec proto3) cho tất cả cross-device payload. **Nghiêm cấm** dùng native `u64::to_ne_bytes()` (native-endian) trong bất kỳ struct nào giao tiếp cross-platform. CI pipeline tự động lint detect `to_ne_bytes` trong file `mesh_*.rs`.
- 📱💻 **Rust Core FFI (C++ / Dart) Unified Data Plane:** Khi dữ liệu đi qua FFI boundary (Rust → C++ JSI / Dart FFI), Lõi Rust serialize thành `&[u8]` Protobuf binary — **không** giao tiếp qua raw struct pointer (tránh ABI struct padding khác nhau giữa compiler). C++/Dart nhận `&[u8]` và parse lại qua Protobuf client library riêng, đảm bảo cùng byte order.
- 💻🖥️ **CRC32 / AES-256-GCM Integrity Check:** Mỗi cross-platform packet append `CRC32(payload_bytes)` — 4 bytes Little-Endian — ở cuối trước khi đóng gói AES-256-GCM. Receiver kiểm tra CRC32 trước khi verify Ed25519 signature, phát hiện sớm byte corruption do Endianness mismatch mà không tốn CPU cho asymmetric verify.

---

### 6.16 O(N) Trial Matching & Stealth Discovery (Nhận diện Nút Ẩn danh trong Ghost Mesh)

> **Bài toán:** Khi nhận Stealth Beacon chỉ chứa `C_trunc = HMAC(R, PK_identity)[0:8]`, thiết bị cần xác định "đây có phải đồng nghiệp trong tổ chức không?" mà không có `Node_ID` rõ ràng. Phải giải quyết trong <3ms để không block BLE scan loop.

- 💻📱 **O(N) Trial Matching tại Lõi Rust:** Lõi Rust duyệt danh bạ tổ chức (Company Directory, tối đa ~10.000 nhân sự) lưu trong `cold_state.db`. Với mỗi entry `PK_identity_i`, tính `C_test = HMAC-SHA256(R, PK_identity_i)[0:8]` và so sánh với `C_trunc` từ Beacon. Nếu match → xác định được danh tính peer.
- 💻📱 **Tối ưu HMAC < 3ms / 10.000 nhân sự:** Sử dụng Hardware AES-NI (x86) / ARM NEON (Mobile) để vectorize tính toán HMAC hàng loạt. Với chip hiện đại, mỗi HMAC-SHA256 tốn ~1µs → 10.000 phép tính = ~10ms trên một core đơn. Lõi Rust parallelizes trên 2-4 core → đạt <3ms. Kết quả cache vào RAM trong Epoch hiện tại để tránh tính lại.
- 💻📱 **Giải mã Ciphertext chỉ sau khi khớp `C_trunc`:** Hai bước tách biệt — (1) Trial Matching để xác định `PK_identity_peer`, (2) ECDH Curve25519 lấy `Shared_Secret` → giải mã Ciphertext. Không bao giờ cố giải mã Ciphertext trước khi có match → tránh CPU exhaustion attack.
- 📱 **Peer-to-Peer Trust Activation → Welcome_Packet:** Sau khi xác định được peer hợp lệ (match + verify), Lõi Rust dẫn xuất `Session_Key` từ `Shared_Secret` và phát `Welcome_Packet` (MLS Epoch Key) qua BLE L2CAP encrypted channel. Toàn bộ luồng này xảy ra trong <50ms từ khi nhận Beacon đến khi peer được chấp nhận vào Mesh.

---

### 6.17 Micro-batched Hydration & Lazy UI Sync (Chống Nghẽn cổ chai SQLite và Quá tải Giao diện)

> **Bài toán:** SQLite dễ bị thắt cổ chai khi dump dữ liệu số lượng lớn, đẩy trực tiếp toàn bộ dữ liệu qua cầu IPC sẽ làm tràn bộ nhớ và sập luồng UI.

- 📱💻🖥️ **DB Lock Yielding kết hợp SQLite WAL:** Chia nhỏ giao dịch sáp nhập thành các batch nhỏ (Micro-batching) cấu hình tối đa 500 records/batch. Nhả khóa (Lock Yielding) giữa mỗi batch để các tiến trình read/write khác có cơ hội chen ngang, tận dụng tối đa kiến trúc WAL.
- 📱💻🖥️ **Lazy UI Hydration (Lazy Sync):** Thay vì nạp toàn phần, Lõi Rust chỉ cấp phát 20 tin nhắn gần nhất chuyển thẳng qua màn hình qua con trỏ bộ nhớ (Memory Pointer). Phần còn lại sẽ được kéo dãn tải thông qua cơ chế cuộn động (Infinite Scroll).
- 📱💻🖥️ **Control Plane Signaling (`MERGE_COMPLETE`):** Không dùng Bridge để đẩy dữ liệu thô (raw data). Ngay sau khi batching xuống disk xong, Lõi bắn tín hiệu sự kiện siêu nhẹ `MERGE_COMPLETE` qua Control Plane. UI nhận tín hiệu và tự chủ động query trực tiếp dữ liệu mới, loại bỏ hoàn toàn JSON rác trên IPC.

---

### 6.18 Hiệu suất Truyền Dữ liệu An toàn Sang Sandbox (Read-Only Memory Handoff)

> **Bài toán:** Lõi Rust giải mã hộ Sandbox, nhưng nếu chép đè dữ liệu cục bộ sang môi trường Sandbox qua cầu giao tiếp thông thường (Base64 / JSON) sẽ tốn kém RAM gấp đôi và làm chậm quá trình render.

- 📱 **JSI C++ Native Pointer (Đâm thẳng luồng nhận):** Trên môi trường Mobile (iOS/Android), dữ liệu sau khi giải mã được truyền thẳng vào luồng nhận của Sandbox thông qua Native Pointer (JSI). Bỏ qua hoàn toàn JavaScript Bridge, loại bỏ chi phí Serialization.
- 💻🖥️ **SharedArrayBuffer mmap Vật lý (Zero-Copy 500MB/s):** Trên Desktop, Lõi Rust cấp phát vùng nhớ mmap vật lý và chia sẻ quyền truy cập thông qua `SharedArrayBuffer` cho .tapp. Thông lượng đạt ngưỡng ~500MB/s mà không tốn công chép (copy) byte nào sang heap của V8 Engine.
- 📱💻🖥️ **Decrypted Ephemeral Buffer Cờ `PROT_READ`:** Để ngăn chặn .tapp chọc ngoáy (mutate) làm hỏng dữ liệu gốc hoặc tiêm mã độc thực thi ngược lại Lõi Rust, vùng nhớ đệm giao lại cho Sandbox được kernel thiết lập tĩnh cờ `PROT_READ`. Mọi hành vi ghi đè (Write) hay thực thi (Execute) sẽ lập tức bị OS ném `SIGSEGV` (Segmentation Fault) và chém chết Sandbox.

### 6.19 Rào cản Chính sách W^X trên iOS (WASM Interpreter & AOT Data-Centric Execution)

> **Bài toán:** Hệ điều hành iOS áp đặt chính sách W^X (Write XOR Execute) cực kỳ hà khắc: một vùng nhớ không bao giờ được phép vừa Ghi vừa Thực thi. Máy ảo WASM thông thường đòi hỏi JIT (Just-In-Time) compilation liên tục ghi mã máy mới vào RAM rồi thực thi — dẫn đến việc iOS lập tức crash app.

- 📱 **WASM Interpreter Mode (Thông dịch phi JIT):** Triển khai động cơ WASM dưới chế độ Thông dịch (Interpreter) hoàn toàn thay vì Biên dịch trực tiếp (JIT) trên màn chạy. Logic của .tapp được đọc và phân tích dưới dạng dữ liệu tĩnh, giúp lách qua khe cửa W^X của Apple một cách hợp lệ mà không vi phạm nguyên tắc bảo mật.
- 📱 **Ahead-of-Time (AOT) Compilation Nạp sẵn:** Đối với những core logic cực kỳ nặng của .tapp, ta đóng gói và biên dịch sẵn mã tĩnh (AOT compiler) từ giai đoạn build app. Giữ hiệu suất thực thi ngang tầm Native ở các tác vụ lõi mà WASM Interpreter làm quá chậm.
- 📱 **JSI HostObject Phân rã Memory Domain:** Sử dụng `HostObject` của kiến trúc React Native JSI để cô lập hoàn toàn Vùng nhớ Dữ liệu (Data Memory) và Vùng mã Tuyến lệnh (Executable Memory). Đảm bảo không có bất kỳ vector nào có thể nhồi shellcode thông qua đầu vào dữ liệu để tấn công Lõi Rust.

---
IPC Zero-Copy Architecture

- 💻🖥️ Phân bổ vùng nhớ SharedArrayBuffer kết hợp Ring Buffer 10MB đạt ngưỡng thông lượng ~500MB/s nhằm vượt rào thông lượng IPC.
- 📱 Tham chiếu React Native trực diện thông qua C++ JSI Pointer nhằm vượt luồng thắt cổ chai của WebView Bridge truyền thống.
- 📱 Tích hợp chuẩn Dart FFI TypedData hỗ trợ giao thức Zero-Copy thẳng vào giao diện vùng nhớ C ABI.

#### In-Memory Encryption (No Plaintext on Disk)

Mọi file tải về đều nằm trong thư mục Application Sandbox dưới dạng Encrypted Blob. Trình xem ảnh/file tích hợp sẵn của OS sẽ bị bypass; TeraChat tự mount file vào bộ nhớ RAM (`memfd` hoặc `Secure Enclave`) để hiển thị.

#### Non-Volatile VFS Mapping & Crash-Safe Checkpointing

- 📱 Chỉ định vị trí lưu trữ `TeraCache.blob` trực tiếp tại ổ đĩa DocumentDirectory với cờ phân quyền `DoNotBackup`.
- 📱 Ràng buộc kích hoạt tiến trình xả buffer `terachat_core_flush_io()` ngay lập tức khi hệ thống thu nhận cờ `applicationWillTerminate`.
- 📱💻🖥️ Liên kết cấu trúc SQLite với cơ chế ghi trước WAL (Write-Ahead Logging) ánh xạ trực tiếp lên không gian bộ nhớ ảo Ring-Buffer.

#### Ghi dữ liệu ngoại tuyến (JIT Mesh-to-VFS Stream Processing)

- 📱 Bơm nguyên khối dữ liệu thẳng vào trình phát System Player thông qua **Native-to-Rust Media DataSource Bridge** (AVAssetResourceLoaderDelegate/MediaDataSource/Custom Protocol Handler) thay vì Local HTTP Streaming `127.0.0.1`, bỏ qua mọi bước đệm TCP để giảm Latency và tránh giới hạn Background trên iOS.
- 📱💻🖥️ Cấu hình API `mmap()` (hoặc `pread()` fallback trên iOS) tham chiếu trực diện bộ nhớ lưu trữ vật lý lên không gian bộ nhớ ảo nhằm ghi đè vòng lặp liên tục (Ring-Buffer).
- 📱💻 Đánh dấu các mảng bộ nhớ an toàn là `FREE_SPACE` để tiến hành ghi đè trực tiếp theo quy chuẩn Crypto-Shredding bảo vệ vòng đời hao mòn SSD nội hạt.

#### Native Media DataSource Bridge vs. Legacy Local HTTP Loopback

- 📱 **Mobile (Chuẩn bắt buộc):** Tuyệt đối **không** được thiết lập Local HTTP Server ẩn danh tại vòng lặp `127.0.0.1` để phục vụ Media Player — iOS sẽ thu hồi Socket khi vào Background, gây đứt gãy streaming. Chuẩn duy nhất là Native-to-Rust Media DataSource Bridge mô tả tại §8.1.
- 💻🖥️ **Desktop (Tuỳ chọn):** Có thể duy trì Local HTTP Loopback cho compatibility cũ, nhưng khuyến nghị chuyển dần sang Custom Protocol Handler/FFI trực tiếp để giảm Attack Surface TCP nội bộ.
- 📱💻🖥️ Dù ở chế độ nào, `mmap()`/`pread()` vẫn phản chiếu kích thước file vật lý lên phân vùng nhớ ảo, nạp linh hoạt từng mảnh con 2MB on-demand để kìm hãm RAM footprint < 10MB, mã hóa/giải mã bằng Chunked AEAD (STREAM/OAE1) ngay trên Ring Buffer và gọi `Drop()`/`ZeroizeOnDrop` giải phóng dung lượng ngay sau khi trình phát tiêu thụ xong.

#### Memory Segmentation & RAII Zeroization

- 📱 **ZeroizeOnDrop (RAII):** Mọi biến plaintext wrap trong `zeroize::Zeroize`. Không giữ plaintext qua bất kỳ `await` hay `suspend` point.
- 📱 **Tuyệt đối không dùng `mlock()`** trên mobile — Jetsam OOM-Kill app ngay lập tức.
- 📱💻🖥️ Phân vùng bộ nhớ riêng biệt cho các luồng xử lý nhạy cảm, đảm bảo cô lập dữ liệu và giảm thiểu rủi ro rò rỉ.

### 6.2 Quản trị Xung đột (Conflict Resolution & Security)

- 📱💻 Shadow Node Hydration: Các lệnh PROPOSE_CHANGE được lưu trong hot_dag.db ở trạng thái Pending. UI Renderer chỉ hiển thị chúng dưới dạng lớp phủ (Overlay) mà không thay đổi trạng thái gốc của tin nhắn.
- 📱💻 Local Crypto-Shredding cho Nhánh Từ chối: Ngay khi người dùng nhấn "Reject" một đề xuất, Lõi Rust gọi ZeroizeOnDrop để tiêu hủy khóa KEK của nhánh bị từ chối đó, đồng thời xóa node khỏi hot_dag.db trên Local Client để chống phình to dữ liệu (State Bloat).
- 📱💻 Inline Policy Packet (RBAC): Lõi Rust khóa các hàm FFI tạo Proposal dựa trên Policy Packet đi kèm tin nhắn (Viewer: Drop request, Commenter: Chỉ cho phép PROPOSE_COMMENT, Editor: Cho phép PROPOSE_CHANGE).
- 📱💻 **Lazy Hydration (Nạp lười biếng):** Lõi Rust không tải toàn bộ Shadow Branch vào `hot_dag.db` cùng lúc. Thay vào đó, chỉ tải một "Summary Metadata" (ví dụ: `{"Index_ID": "A1", "Proposal_Count": 45}`) để giảm tải RAM và I/O.
- 📱💻 **On-Demand Decryption:** Chỉ khi Author bấm vào xem danh sách đóng góp, Lõi Rust mới gọi API kéo (fetch) các node chi tiết về RAM, giải mã và hiển thị. Đóng Pop-up → Kích hoạt ZeroizeOnDrop xóa sạch RAM ngay lập tức.

### 6.3 Local Storage & State Sync

#### SQLite WAL + Sliding Window

- 📱💻🖥️ Bắt buộc chế độ **WAL (Write-Ahead Logging)** cho mọi SQLite instance. Không gọi `VACUUM` (rủi ro Corrupt trên Mobile Doze/Jetsam).
- 📱 **Mobile Window:** 7 ngày hoặc 2.000 tin nhắn gần nhất (Cold Data nằm trên Cluster).
- 💻🖥️ **Desktop Window:** 30 ngày hoặc 10.000 tin nhắn gần nhất.
- ☁️ **Cold Data:** Fetch on-demand khi user cuộn lên hoặc tìm kiếm \>30 ngày.

#### Plaintext Forensic Extraction Defense (SQLite WAL / VFS)

- 📱 Ghim bộ nhớ (Memory Pinning) bằng `kCFAllocatorMallocZone` để chống trích xuất plaintext từ SQLite WAL.
- 💻 Sử dụng `memfd_create` tạo Ephemeral RAM-Drive (Ephemeral VFS) lưu trữ file tạm trên Linux.
- 🖥️ Sử dụng tập lệnh SIMD (ARM NEON / Intel AVX2) để thực hiện Zeroization vùng nhớ tốc độ cao.

#### Tiến hóa dữ liệu song song (Dual-State Evolution)

- 📱💻🖥️ **Kiến trúc Phân thân (Dual-State Overlay):** Lõi Rust mở file DB cũ (`messages_v1.db`) ở chế độ `SQLITE_OPEN_READONLY` để bảo vệ dữ liệu gốc khỏi lỗi I/O. Khởi tạo DB mới (`messages_v2.db`) trong < 5ms với engine VFS mới nhất. Mọi lệnh ghi đi thẳng vào V2, lệnh đọc thực hiện `UNION` kết quả từ cả hai DB trên RAM trước khi trả về UI.
- 📱 **Read-Through / Background Drip Migration (Di chuyển nhỏ giọt):** Khi người dùng cuộn xem tin nhắn cũ, hệ thống tự động giải mã V1 và tái mã hóa sang V2 (Lazy JIT Migration). Sử dụng `BGProcessingTask` (iOS) / `WorkManager` (Android) di chuyển khối 500 bản ghi khi cắm sạc ở trạng thái nhàn rỗi.
- 📱💻 **WAL Atomic Rollback:** Bọc từng đợt migration nhỏ giọt bằng `BEGIN IMMEDIATE TRANSACTION` nhằm tự động khôi phục dữ liệu nếu tiến trình bị OS ngắt đột ngột.

#### Dynamic JSONB Fallback & Deferred Migration (Nâng cấp SQLite trì hoãn)

- 📱💻🖥️ Bổ sung cột `extended_data` kiểu BLOB/JSONB đóng vai trò thùng chứa linh hoạt cho các thuộc tính chưa được định nghĩa trong Schema hiện tại.
- 📱💻🖥️ Ban hành quy trình `Deferred Migration` sử dụng script `ALTER TABLE` kết hợp trích xuất dữ liệu từ JSON ngầm để tái cấu trúc khối dữ liệu sau mỗi đợt nâng cấp OS.
- 📱💻🖥️ Vận hành hệ thống đồng bộ CRDT Event Log kết hợp Hybrid Logical Clocks (HLC) để giữ vững tính nhân quả chặt chẽ bất chấp sự chênh lệch phiên bản giữa các thiết bị.

#### Tìm kiếm toàn văn (Search) bảo toàn E2EE

- 📱 **Hybrid Full-Text Search (FTS) Indexing:** Kích hoạt SQLite FTS5 để lập chỉ mục (indexing) trọn vẹn dải metadata tĩnh ngay tại không gian cục bộ (Local) của thiết bị.
- ☁️ Khai thác Engine PostgreSQL FTS (tsvector) chuyên trách quản lý và phân luồng chuỗi chỉ mục rải rác tập trung hoàn toàn tại hệ thống kho Server trung tâm.
- 📱 Ứng dụng cơ chế mù Blind Search kết hợp thuật toán băm `HMAC-SHA256` để truy vấn tìm kiếm ngầm định mà tuyệt đối không rò rỉ từ khóa nguyên bản.

#### Kiến trúc SQLCipher-backed Hybrid Virtual Tables (Lưu trữ Tìm kiếm Hỗn hợp E2EE)

- 📱💻🖥️ Sử dụng SQLCipher với chuẩn mã hóa AES-256-GCM bọc toàn bộ tệp `.sqlite` duy nhất.
- 📱💻🖥️ Khai thác module FTS5 (Full-Text Search) sử dụng cấu trúc `External Content Table` nhằm giảm thiểu tối đa kích thước dữ liệu Plaintext dư thừa.
- 📱💻 Tích hợp Extension `vss0` (sqlite-vss) để lưu trữ và truy vấn Vector Embeddings 384 chiều.

#### CRDT Automerge — Hybrid Event-Sourcing

- 📱💻🖥️ **CRDT dùng cho:** Schema và trạng thái công cụ (vài KB). Không dùng CRDT cho data entry thực tế.
- 📱💻🖥️ **Event Log (Data Entry thực tế):** WASM sinh event nhỏ \<1KB/event → Rust mã hóa E2EE bằng `Company_Key` → đẩy Event_Blob lên VPS Blind Storage. Thiết bị khác tải → giải mã → replay vào SQLite local.
- 📱 Xung đột giải quyết bằng **Last-Write-Wins (LWW)** + Epoch Timestamp — không dùng CRDT State Vector cho data rows.
- 📱 RAM target: CRM 10.000 bản ghi = ~5MB RAM (Event Log) thay vì ~500MB (CRDT State Vector thuần).

#### Reciprocal Rank Fusion (RRF) Multi-modal Scoring

- 📱💻🖥️ Áp dụng thuật toán RRF để hợp nhất điểm BM25 từ FTS5 và L2 Distance từ VSS theo công thức: $RRFscore(d) = \sum_{r \in R} \frac{1}{k + r(d)}$.
- 📱💻🖥️ Kích hoạt Phép truy vấn song song (Parallel Query) ngay trong lõi Rust Core để tối ưu hóa triệt để độ trễ.
- 📱💻🖥️ Đảm bảo cơ chế Atomic Transaction giữ vững tính toàn vẹn dữ liệu giữa bảng Metadata và cấu trúc Virtual Tables.

#### In-Memory Caching (Hot Paths — tránh SQL thô)

- 📱 **Trie (Prefix Tree):** Autocomplete nội bộ — O(L), \<1ms.
- 📱 **Segment Tree / Fenwick Tree (BIT):** Quản lý khoảng xung đột CRDT log — O(log n).
- 📱💻 **B-Tree (RAM):** Index VFS TeraVault thay vì query Database phẳng.
- 📱 **Sliding Window + Bitmask DP:** OPA Policy Engine và Rate Limiter.
- 📱 Constraint: RAM 24MB limit (iOS NSE). Áp dụng Zero-allocation trên luồng Real-time.

#### Adaptive Vector Life-cycle Management (AVLM)

- 📱 Thực thi chính sách "LRU Vector Eviction" tự động định kỳ giải phóng embedding của các tin nhắn cũ hơn 90 ngày để gọt dũa không gian lưu trữ (giảm ~1536 bytes/record).
- 📱💻 Ràng buộc cơ chế `ZeroizeOnDrop` để dọn sạch hoàn toàn dấu vết Plaintext và Vector khỏi bộ nhớ `mlock()` ngay khi lệnh Commit hoàn tất.
- 📱 Lập lịch quy trình chống phân mảnh ngầm (Incremental Vacuum) âm thầm chạy qua tác vụ `BGProcessingTask` của hệ điều hành nền.

#### TeraVault VFS — Storage Ring-Buffer

- 📱💻 Pre-allocate `TeraCache.blob` khi cài đặt: 500MB (Mobile), 5GB (Desktop).
- 📱💻 Rust tự quản lý Mapping Sector nội bộ (Bypass OS File System). Offset cũ → đánh dấu `FREE_SPACE` → file mới overwrite trực tiếp.
- 📱💻 **Crypto-Shredding:** Xóa KEK → toàn bộ data trong blob = garbage. Zero I/O Delete, Zero Wear-Leveling SSD.

#### Local E2EE RAG & Vector Indexing (Biên tập ngữ nghĩa tại thiết bị đầu cuối)

- 📱💻🖥️ Nhúng mô hình ngôn ngữ siêu nhỏ SLM (Small Language Model) qua runtime ONNX/WASM.
- 📱💻🖥️ Sử dụng extension `sqlite-vss` để truy vấn Vector Similarity Search trực tiếp trên SQLite local.
- 📱💻🖥️ Sinh Vector Embeddings 384 chiều từ Plaintext trước khi mã hóa.

#### Custom Rust VFS với Decrypted Secure Arena & Lookahead Decryption

- 📱💻🖥️ Tách biệt `vector_index.db` với `page_size = 16KB` để tối ưu hóa tính cục bộ (Locality) và giảm tần suất kích hoạt giải mã AES-GCM.
- 📱💻🖥️ Cấp phát vùng nhớ RAM cố định qua `mmap(MAP_PRIVATE | MAP_ANONYMOUS)` kết hợp cờ `mlock()` để ngăn chặn swap dữ liệu xuống đĩa cứng.
- 📱💻🖥️ Can thiệp vào tầng Hệ thống tệp ảo (VFS) để thực hiện giải mã trực tiếp vào RAM, trả con trỏ (Pointer) Plaintext cho engine Faiss/HNSW mà không ghi dữ liệu tạm xuống ổ cứng.
- 📱 Sử dụng chỉ thị lệnh song song (SIMD/ARM NEON) để giải mã đón đầu các trang dữ liệu lân cận (N+1, N+2), chuyển đổi nút thắt cổ chai từ I/O sang CPU/RAM.

#### Zero-Copy Secure Pipe với RAII Zeroize

- 📱💻🖥️ Ánh xạ file vật lý trực tiếp lên vùng nhớ ảo thông qua `mmap()` của Lõi Rust, giảm thiểu footprint bộ nhớ xuống < 10MB bất kể kích thước file index.
- 📱💻 Tự động kích hoạt cơ chế `ZeroizeOnDrop` (RAII) để ghi đè `0x00` lên các phân đoạn RAM ngay khi SQLite kết thúc truy vấn, đảm bảo thời gian tồn tại của Plaintext Key/Vector < 2ms.
- 📱💻🖥️ Nhốt toàn bộ tác vụ tính toán nặng vào `tokio::task::spawn_blocking` để duy trì tốc độ UI ở mức 60/120 FPS thông qua SharedArrayBuffer hoặc JSI.

#### Circuit Breaker VFS với Hardware-Aware Trapping

- 📱 Đăng ký OS Hooks lắng nghe tín hiệu `UIApplicationProtectedDataWillBecomeUnavailable` (iOS) và `Intent.ACTION_SCREEN_OFF` (Android) để kích hoạt cờ hiệu `ATOMIC_KEY_EVICTED`.
- 📱 Ánh xạ lỗi tương tác phần cứng từ Secure Enclave/Keystore (như `errSecInteractionNotAllowed`) thành mã lỗi chuẩn `SQLITE_IOERR_AUTH` tại tầng VFS.
- 📱 Khởi động cơ chế ngắt luồng (Short-circuit) chủ động tại hàm `xFetch` và `xRead` để bảo vệ an toàn tiến trình Rust khỏi những đợt Kernel Panic.

#### WAL-backed Atomic Rollback Protocol

- 📱💻🖥️ Kích hoạt chế độ SQLite WAL (Write-Ahead Logging) cho mọi instance để tách biệt file dữ liệu chính và log thay đổi.
- 📱💻 Sử dụng cụm lệnh `BEGIN IMMEDIATE TRANSACTION` để khóa quyền ghi và cô lập dữ liệu Index dở dang trong file `-wal`.
- 📱💻 Thiết lập cơ chế tự động Rollback về trạng thái nhất quán (Consistent State) gần nhất khi nhận tín hiệu lỗi I/O từ VFS.

### 6.3 Desktop Native OS (Windows · macOS · Linux)

- 💻🖥️ **Full Disk Encryption mandatory:** Kiểm tra BitLocker (Windows) / FileVault (macOS) khi khởi động. Từ chối khởi chạy nếu không bật.
- 💻🖥️ **RAM Pinning:** `VirtualLock()` (Windows) / `mlock()` (Linux/macOS) ghim vùng nhớ chứa plaintext Key.
- 💻🖥️ **Background Worker FTS5:** Indexing toàn bộ lịch sử tin nhắn (không giới hạn) — chạy liên tục dưới dạng background worker. Không block Main Thread.
- 💻🖥️ **Daemon (`terachat-daemon`) — Startup Registration:**
  - Windows: Windows Service (`sc create`) hoặc Task Scheduler (ONLOGON).
  - macOS: `launchd` LaunchAgent (`~/Library/LaunchAgents/com.terachat.daemon.plist`).
  - Linux: `systemd` user service (`~/.config/systemd/user/terachat-daemon.service`).
- 💻🖥️ **Daemon RAM Budget:** tokio async runtime ~1.5MB, WebSocket/TLS stack ~1.5MB, Key cache ~0.5MB, E2EE decrypt buffer ~1.0MB. **Tổng ~4.5MB.**
- 💻🖥️ Daemon chức năng duy nhất: nhận E2EE payload → giải mã preview → gửi OS Notification → zeroize RAM. Không lưu tin nhắn.

#### Single-Instance Lock & IPC Forwarding (Khóa bản thể duy nhất Desktop)

- 💻🖥️ Kích hoạt cơ chế bind vào Unix Domain Socket (macOS/Linux) hoặc Named Pipe (Windows) để phát hiện tức thời bản thể đang chạy ngầm.
- 💻🖥️ Vận hành giao thức IPC Forwarding chuyển giao nguyên vẹn tham số CLI/Deep Link từ bản thể phụ sang quyền kiểm soát của bản thể chính.
- 💻🖥️ Gắn lệnh tự sát (Graceful Exit `0`) cắt vòng đời của bản thể phụ ngay sau khi hoàn tất bàn giao tín hiệu khơi mào.

### 6.4 Mobile Native OS (Android · iOS)

#### iOS — Xử lý Jetsam / DAS Throttle / NSE Constraint

- 📱 **Phân tách Cấu trúc RAM theo Process Context:**
  - **Foreground (Main App):** Kích hoạt toàn bộ **50MB LRU Cache** để tối ưu hóa JSI/FFI Pointer và tốc độ phản hồi UI.
  - **Background (NSE):** Vô hiệu hóa LRU Cache. Chỉ nạp module **Micro-Crypto** với Footprint tĩnh ~4MB. Luồng xử lý: Nhận payload (<4KB) → giải mã trực tiếp → đẩy thông báo → gọi `Drop()` ngay lập tức để giải phóng RAM dưới ngưỡng 24MB.
- 📱 **Tuyệt đối không dùng `mlock()`** — Jetsam OOM-Kill app ngay lập tức.
- 📱 **ZeroizeOnDrop (RAII):** Mọi biến plaintext wrap trong `zeroize::Zeroize`. Không giữ plaintext qua bất kỳ `await` hay `suspend` point.
- 📱 **OOB Symmetric Push Ratchet Only trong NSE:** Tiến trình NSE **không bao giờ** nạp hoặc tái cấu trúc cây MLS TreeKEM. NSE chỉ đọc một `Push_Key` đối xứng siêu nhẹ (AES-256-GCM) đã được Main App derive sẵn từ OOB HKDF chain và lưu vào Shared Keychain (App Group), dùng key này để giải mã payload rồi `ZeroizeOnDrop`; mọi thao tác MLS Epoch Rotation được thực hiện khi Main App hoạt động ở Foreground.
- 📱 **FTS5 Indexing — Adaptive Micro-Batch (Chống Jetsam OOM-Kill):**
  - NSE **TUYỆT ĐỐI CẤM** kích hoạt FTS5 Tokenizer. NSE chỉ ghi raw Blob mã hóa vào Append-Only table (`is_indexed = false`), không phân tích cú pháp.
  - Main App (Foreground): Sau khi Mesh reconnect và CRDT merge hoàn tất, Lõi Rust mới khởi động Indexer qua Background Task API — **không chạy ngay lập tức**.
  - **Batch size:** 50 tin nhắn/batch, cách nhau 500ms (tránh CPU burst spike).
  - **Circuit Breaker:** Nếu RAM App chạm **80% hạn mức Foreground OS** → Indexer tự `Suspend()` → resume ở `applicationDidBecomeActive` tiếp theo.
  - Index Window: 30 ngày gần nhất. Đánh đổi: Tin nhắn nhận trong Mesh có thể chậm xuất hiện trong search 1-2s, nhưng App không bao giờ bị Jetsam kill.
- 📱 **Tìm kiếm >30 ngày (Encrypted Blind Search):** Rust Core gửi `HMAC-SHA256(Company_Search_Key, keyword)` token lên Cluster TEE — Server không biết keyword thực, trả về `message_id` list — Client tải và giải mã chỉ các tin khớp.
- 📱 **iOS Background Delegate (Cold Data Sync — KHÔNG phải App Update):** Khi Foreground → TCP/WSS Pumping. Khi Background → ngắt WebSocket. VPS đóng gói **file đính kèm / lịch sử tin nhắn** Ciphertext thành file tĩnh 50MB, sinh One-time Pre-Signed URL, giao cho `NSURLSession Background Transfer` (iOS, `isDiscretionary = true`) để OS tự tải.
  - OS tải xong → đánh thức App 30s → Rust dùng `mmap` + Hardware AES-NI giải mã toàn khối \<40ms → `unlink` file tạm.
  > ⚠️ **Phân vai cứng:** Luồng này chỉ được dùng để kéo **Dữ liệu lạnh (Cold Data)**. Cập nhật Native App đi đườc qua Apple App Store. Vi phạm policy iOS nếu dùng luồng này để nâng cấp Binary.
- 📱 **Context-Aware Edge Defense trên Pre-Signed URL:** URL ký bằng JA3/JA4 TLS Fingerprint của `NSURLSession` + IP Subnet. Mismatch → Edge drop 0ms. Byte-Quota tại Edge (Redis Bloom Filter): `quota = file_size × 1.5`. Vượt quota → TCP RST. Replay từ IP đáng ngờ → Infinite Tarpit (1 Byte/10s).

#### Kiến trúc Phân rã Chỉ mục Hai Pha (Two-Phase Deferred Indexing)

- 📱 **Pha 1 — Write (NSE, realtime):** Khởi chạy Rust Core Lightweight Mode (chỉ nạp module Cryptography) để kìm hãm RAM footprint < 10MB dưới ngưỡng an toàn NSE. Chỉ ghi Blob vào `nse_staging.db` với `is_indexed = false`. Tuyệt đối không gọi bất kỳ FTS5 API nào.
- 📱 **Pha 2 — Index (Main App, deferred):** Thiết lập cơ chế Shared App Group đồng bộ SQLite giữa NSE và Main App. Gán cờ `is_vectorized` đánh dấu dữ liệu chờ AI. Lắng nghe trigger `BGProcessingTask` để batch-index âm thầm khi thiết bị idle, với Circuit Breaker tự `Suspend()` khi RAM > 80%.

#### Kiến trúc Hàng đợi Trung chuyển Bất đối xứng (Asymmetric Staging Queue & Lock-Free Sync)

- 📱 **Phân lập Vùng chứa (App Group Isolation & Staging DB):** Bật tính năng iOS App Groups (`group.com.terachat.alpha`) để chia sẻ thư mục giữa NSE và Main App. NSE tuyệt đối không được cấp quyền chạm vào `hot_dag.db` chính. Thay vào đó, khởi tạo một cơ sở dữ liệu phụ là `nse_staging.db` (được mã hóa bằng SQLCipher). Lõi Micro-Core trong NSE chỉ có đặc quyền **Append-Only** (Chỉ ghi thêm). Sau khi giải mã thành công, NSE đẩy Ciphertext đã giải mã, MAC tag, và Message Counter mới vào đây rồi đóng luồng.
- 📱 **Cơ chế Hút dữ liệu & Hợp nhất (Atomic Drain & Squashing):** Main App đóng vai trò là "Consumer" duy nhất. Khi người dùng mở app (Foreground), Lõi Rust đầy đủ thực thi quá trình **Atomic Drain**. Nó đọc toàn bộ bản ghi từ `nse_staging.db`, tính toán Delta-State CRDT, và thực hiện gộp (Squashing) vào `hot_dag.db` chính. Chỉ khi quá trình Squashing commit thành công vào WAL của `hot_dag.db`, Lõi Rust mới phát lệnh `DELETE` làm sạch `nse_staging.db`, đảm bảo tính ACID tuyệt đối.
- 📱 **Giao tiếp Liên tiến trình qua Darwin Notifications (IPC Signaling):** Để Main App biết lúc nào cần "hút" dữ liệu, NSE sẽ bắn một tín hiệu OS-level thông qua `CFNotificationCenterGetDarwinNotifyCenter` (ví dụ: `com.terachat.state.dirty`). Tín hiệu này vượt qua các rào cản Sandbox của iOS mà không tốn tài nguyên bộ nhớ. Nếu Main App đang Suspended trong RAM, nó sẽ được đánh thức ngầm khoảnh khắc ngắn để chuẩn bị Buffer.
- 📱 **Khóa POSIX Cấp Hệ điều hành (POSIX Advisory Locks):** Tại kịch bản cạnh tranh luồng (Race Condition) ngặt nghèo khi người dùng mở app đúng lúc NSE đang ghi dở vào Staging DB, Lõi Rust sử dụng `fcntl()` POSIX lock trên file `nse_staging.db`. Nếu Main App phát hiện file đang bị khóa, nó áp dụng thuật toán Exponential Backoff (chờ 5ms, 10ms, 20ms) cho đến khi NSE nhả khóa, triệt tiêu rủi ro đọc Partial Write.

#### Android — Xử lý Doze / WorkManager

- 📱 **FTS5 Indexing:** Batch nhỏ, chỉ khi App Active. Index Window: 30 ngày. Tìm kiếm cũ hơn → Encrypted Blind Search (giống iOS).
- 📱 **Background Delegate:** Giao URL cho `WorkManager` (Android, `NetworkType.UNMETERED`) — OS tự tải lúc cắm sạc/Wi-Fi mạnh.
- 📱 **Wake-and-Strip:** Rust `mmap` + ARM NEON giải mã, `unlink` file tạm; Hard Deadline \<3 giây (tránh vi phạm Background Time Limit).
- 📱 **StrongBox Keymaster:** Lưu Symmetric Push Key (FCM). Key sinh trong chip, không export.

### 6.5 Lean Edge Caching

#### Mesh-Aware Radar Pulse Visualization (Trực quan hóa Trạng thái Mesh)

- 📱 **Radar Pulse Scan:** Hiệu ứng Radar Pulse màu `#0F172A` quét từ dưới lên trên UI, báo hiệu trực quan cho người dùng rằng dữ liệu đang được đồng bộ hóa từ mạng lưới P2P/Offline Mesh thay vì Cloud.
- 📱💻🖥️ **Control Plane Signals (`StateChanged`):** Lõi Rust áp dụng Unidirectional State Sync, chỉ bắn tín hiệu `StateChanged` qua IPC thay vì đẩy toàn bộ cục JSON cồng kềnh. Giao diện (Renderer) sẽ tự động trigger fetch phần dữ liệu thay đổi để giữ độ mượt mà tuyệt đối.
- 💻 **Deterministic SQLite Update Hook (Causality Enforcement):** Bám sát các sự kiện thay đổi dữ liệu từ tận đáy C sở sở bằng `sqlite3_update_hook()`. Luồng tín hiệu thay đổi (Insert/Update/Delete) được phát ra đồng bộ với chu trình vòng đời cơ sở dữ liệu, đảm bảo quan hệ nhân quả tuyệt đối.
- 📱 **JSI Lock-Free Ring Buffer Queue:** Mọi thông báo thay đổi trạng thái được đẩy qua hàng đợi vòng (Ring Buffer) cấu trúc Lock-Free qua JSI IPC. Tốc độ nạp xả thông điệp đạt ngưỡng nano-seconds (NS) mà không sợ vướng Thread-Lock làm treo hệ thống.
- 📱 **60Hz JSI Emitter UI Sync:** Javascript Thread đóng vai trò Consumer, lấy lượng kiện thay đổi trên Queue với tốc độ đồng bộ `requestAnimationFrame` 60Hz/120Hz (60fps), chấm dứt hoàn toàn thảm họa Bất đồng bộ trạng thái UI (UI State Desync) khi luồng dữ liệu dồn về ồ ạt.
- 📱 **Off-screen Rendering Culling:** Sử dụng kiến trúc `FlatList` / `SliverList` bẩm sinh loại bỏ (Cull) việc render các tin nhắn nằm ngoài Viewport hiện tại (tránh nghẽn luồng UI do dồn ứ tin nhắn Mesh).

#### Zero-Byte Stubs & Metadata Rendering (Virtual Metadata Mapping & Lazy-load UI Architecture)

- 📱💻🖥️ Sử dụng cấu trúc Zero-Byte Stubs chỉ chứa tĩnh lược Metadata <5KB (bao gồm `file_name`, `cas_hash`, `encrypted_thumbnail`).
- 📱💻🖥️ Ánh xạ liên kết `cas_ref / storage_ref` thông qua bảng `vault_file_mappings` để hiển thị UI tệp tin nguyên bản mà không chiếm dụng không gian vật lý bộ nhớ.
- 📱💻 Tiến hành giải mã cục bộ `encrypted_thumbnail` và hiển thị render mờ ngay lập tức dưới định dạng lưới đồ họa Blur-hash.
- 📱💻🖥️ **Oblivious CAS Routing:** Batch 4–10 Fake Hashes khi gửi query `cas_hash`. Tra qua Mixnet Proxy (không đính User_ID). Khi HIT: Client phản hồi Merkle Root (zk-PoW) chứng minh sở hữu Plaintext trước khi lấy stream. Tính Fake Hash <2ms, Batch Request <1KB.

#### Tiered Storage (3 tầng)

| Tầng | Cơ chế | Ai quyết | Khi nào tải |
|---|---|---|---|
| **Tier 1 — Auto (Pinned)** | Rust Core tự kéo full ciphertext về local | Admin/Manager | `is_pinned = true` trong channel |
| **Tier 2 — On-demand** | User click Tải / Xem trước | User | Tức thì qua Cluster hoặc LAN P2P |
| **Tier 3 — Make Available Offline** | Background worker kéo toàn folder | User tự chọn | Trước khi lên máy bay / vào khu vực mất mạng |

#### Sender-Side Media Pre-processing (Content-Aware Blind Chunking & E2EE Metadata Pre-processing)

- 📱💻 Trích xuất Thumbnail cực nhẹ tĩnh (5-10KB) thông qua thuật toán Blur-hash từ thiết bị trước khi thực thi tiến trình mã hóa E2EE.
- 📱💻🖥️ Áp dụng cơ chế AEAD (AES-GCM / ChaCha20-Poly1305) mã hóa độc lập từng khối phân mảnh (Chunk) 2MB.
- 📱💻 Thực thi Pre-Encryption Compression (FFmpeg/JSI) chuyển đổi định dạng ảnh biên sang chuẩn WebP/HEIC chất lượng 80% nhằm gọt bỏ 30-80% băng thông tải lên.
- Bypass nén bằng tag `Gửi HD`.

#### Zero-Knowledge Media Vision via Edge Inference (Thị giác máy tính tại biên)

- 📱💻 Tích hợp Edge CLIP (Contrastive Language-Image Pretraining) để phân loại ảnh bằng ngôn ngữ tự nhiên.
- 📱 Trích xuất văn bản qua ML Kit OCR tận dụng NPU/GPU Hardware Acceleration.
- 📱💻 Cơ chế Hidden Tags (Gán nhãn mù) bọc bởi Search_Subkey_Epoch_N trước khi đẩy lên Blind Storage.

#### Convergent Encryption — Salted MLE + Contextual Heuristics Engine

- 📱💻🖥️ **Heuristics Router** chạy ngầm tại Rust Core, quyết định chiến lược mã hóa \<1ms — không đọc nội dung file, không gọi API.
- **Phân loại tự động:**

| Loại file | Kích thước | Chiến lược | Dedup? |
|---|---|---|---|
| Hợp đồng PDF, .docx | Bất kỳ | Strict E2EE (Random Key) | ❌ |
| File 1-1 DM | Bất kỳ | Strict E2EE | ❌ |
| Video nội quy / Setup.exe | \>5MB | CompanyMediaMLE (`Company_Media_Key`) | ✅ 1 bản toàn tenant |
| Ảnh JPEG lớn (channel) | \>5MB | SaltedMLE (`Channel_Key`) | ❌ per-channel |
| File nhỏ \<5MB bất kỳ | \<5MB | Strict E2EE | ❌ |

- **Salted MLE Anti-KPA:** `CAS_Hash = HMAC-SHA256(Static_Dedup_Key, file_content)`. `Static_Dedup_Key` = `HKDF-SHA256(Channel_Master_Secret, "dedup-v1")` — bất biến suốt vòng đời Channel, phân phối qua TreeKEM.
- Hacker biết file gốc nhưng không có `Static_Dedup_Key` trong RAM thiết bị → không tính được `CAS_Hash` → không giải mã.

### 6.6 APNs Payload Collapse & Notification Degradation

- 📱 Triển khai giải mã tĩnh trực tiếp tại Notification Service Extension (NSE) cho nền tảng Mobile, **chỉ sử dụng OOB Symmetric `Push_Key`** đã được sinh ra từ HKDF chain độc lập với MLS TreeKEM (xem §6.7 và `Core_Spec.md §4.2`).
- ☁️ Cấu hình Server push APNs Payload (<4KB) chứa Ciphertext đã nén bằng chuẩn CBOR, kèm `push_epoch` hiện tại; trường `epoch` của MLS chỉ dùng để báo hiệu cần đồng bộ lại khóa khi lệch, không dùng cho giải mã trực tiếp trong NSE.
- 📱 Khởi tạo Rust FFI siêu nhẹ (Micro-Crypto) gắn vào NSE. Đọc Payload → Lấy `Push_Key_current` từ Shared Keychain/StrongBox → Giải mã CBOR Ciphertext → Đẩy notification ra UI → Gọi lệnh `drop()`/`ZeroizeOnDrop` lập tức giải phóng RAM, tuyệt đối không dựng lại cây MLS trong NSE.
- 📱 Định nghĩa luồng Ghost Push: Nếu Payload > 4KB **hoặc** `Push_Key_current` bị lệch `push_epoch`, Server trả `Fallback=True`. NSE render chuỗi tĩnh (Generic Text `"Đang giải mã an toàn..."`), đồng thời bắn `content-available: 1` đánh thức App ngầm để Main App sync lại MLS Epoch + `Push_Key` mới và cập nhật nội dung chi tiết sau đó.

### 6.7 Out-of-Band Notification Key Ratchet & Ghost Push Wakeup

- 📱 Xây dựng cơ chế HKDF Hash Chain để trích xuất Notification Symmetric Key hoàn toàn độc lập với MLS Epoch.
- ☁️📱 Thiết lập luồng Ghost Push đính kèm cờ `content-available: 1` để đánh thức App ngầm kéo dữ liệu từ SQLite.
- 📱 Thực hiện giải mã tĩnh CBOR Ciphertext trực tiếp tại Notification Service Extension (NSE) sử dụng thư viện Micro-Crypto.

### 6.8 Fast-Scroll Rendering & Viewport Management

- 📱💻 Giám sát chéo quá trình tái định vị Viewport, ngăn chặn trễ luồng cuộn (Scroll-Lag) do tắc nghẽn IPC.
- 📱💻🖥️ Áp dụng cơ chế **LRU Cache (50MB)** trên Main App để lưu lại 100 item gần nhất, giảm ping `get_message` liên tục qua cầu. Quá trình này **bị vô hiệu hóa hoàn toàn** tại tiến trình NSE để né Jetsam limit.

#### Ảo ảnh Thị giác (Metadata-First Virtual Rendering Architecture)

- 📱💻🖥️ Lưu trữ sẵn định dạng Blur-hash (30-50 bytes) và Base64 Tiny-Thumb (< 2KB) đã giải mã độc lập vào cơ sở dữ liệu SQLite.
- 📱💻🖥️ Khởi tạo cấu trúc SQLite FTS5 lập chỉ mục metadata nhằm hỗ trợ thao tác truy vấn tức thời.
- 📱 Render nóng bề mặt phân giải mờ tại mốc $0$ ms giúp kìm hãm drop-frame và duy trì triệt để hiệu năng 60-120FPS trong khi Fast-Scroll.

#### Quản lý Tác vụ theo Khung nhìn (Event-Driven Task Cancellation Protocol)

- 📱💻🖥️ Kích hoạt tín hiệu Viewport-Aware Cancellation bằng lệnh FFI `terachat_cancel_task` khi phân mảnh nội dung trượt khỏi khung nhìn UI.
- 📱💻🖥️ Thực thi AbortHandle thông qua vòng lặp Rust `tokio::select!` để chủ động ngắt luồng I/O và hủy bỏ tác vụ giải mã ngay lập tức.
- 📱💻 Đồng bộ chu kỳ giải mã định danh theo Task_ID Mapping khớp khít với khối trạng thái Unmount của thành phần UI giao diện.

#### Hiệu suất Giải mã Bất đồng bộ (Dedicated Asynchronous Crypto Thread-Pool)

- 📱💻🖥️ Áp dụng cơ cấu Thread-Pool Isolation tách biệt hoàn toàn luồng xử lý Crypto khỏi định tuyến UI Main Thread.
- 📱💻🖥️ Chuyển giao các tác vụ CPU-bound (hệ AES-256-GCM / ChaCha20-Poly1305) thông qua lệnh `tokio::task::spawn_blocking`.
- 📱💻🖥️ Thiết lập thuật toán tự động tinh chỉnh số lượng luồng công nhân (worker) nội vi dựa trên số lõi vật lý: $N_{workers} = \text{num\_cpus::get()} - 1$.

#### Quản lý Bộ nhớ L1 (Tiered LRU RAM Cache with Security Shredding)

- 📱💻 Quản trị 50MB RAM đệm nội bộ cấp L1 cho hệ thống thumbnails thông qua thuật toán Least Recently Used (LRU).
- 📱 Gọi lệnh ZeroizeOnDrop (RAII) thực thi đè bẹp dung lượng $0x00$ ngay khi dữ liệu bị ép đẩy (Evict) khỏi bộ đệm cache.
- 📱 Truyền tải nội dung qua JSI/FFI Pointer duy trì thông lượng ~400MB/s nhằm nạp ảnh sạch từ RAM chọc thẳng lên UI trong ngưỡng < 1ms.
- 📱💻🖥️ **Escrow Key Zeroization:** `Recovery_Ticket` chứa mảnh khóa Master Key chỉ tồn tại trong RAM của thiết bị nhân viên đúng 500ms để thực thi `mmap()` mở khóa `cold_state.db`. Lõi Rust áp dụng `ZeroizeOnDrop` ngay lập tức để tiêu hủy plaintext ticket, ngăn chặn việc HR/Admin có thể trích xuất ngược dữ liệu từ RAM.
- 📱 **IPC Bridge Recovery:** Trạng thái khôi phục (Recovery State) đẩy từ Rust sang UI thông qua JSI/FFI dưới dạng biến boolean `is_recovering`, cấm tuyệt đối việc đẩy plaintext key qua cầu nối UI.

### 6.9 OS Lifecycle & Background Memory Security

#### Đánh thức Lõi Rust qua APNs/FCM (Sleep & Wake-up ở Online Mode)

- 📱 **Silent Push Sync:** Lồng ghép cờ `sync_needed` vào APNs (iOS) hoặc FCM (Android) Push Notification ở chế độ ưu tiên ngầm (Background). Bơm luồng sinh khí đánh thức Lõi Rust trong đúng 30 giây để khẩn trương kéo (Pull) toàn bộ dữ liệu mới từ VPS trước khi bị hệ điều hành đóng băng trở lại.

#### Đánh thức theo Sự kiện Người dùng (User-Initiated Event-Driven Wake-up)

- 📱 **Local Notification Bridge:** Sử dụng High-Priority Local Notification làm cầu nối tương tác khẩn khi nhận diện thiết bị chuyển `Network_State == Offline`.
- 📱 Khởi phát lệnh IPC_Command thông qua JSI/FFI đánh thức Lõi Core từ trạng thái Foreground, cấp phát ngân sách RAM cực nhỏ (<5MB) chỉ để nạp lại `Device_Key` và xử lý Mesh.

#### Hardware Root-of-Trust Biometric Unlock (Mở khóa Sinh trắc học Phần cứng)

- 📱 **Native Hardware Enclave API:** Ứng dụng gọi trực tiếp API Native `kSecAccessControlBiometryCurrentSet` (iOS) hoặc `StrongBox` (Android) để giải phóng `Device_Key` khỏi Secure Enclave/Keystore.
- 📱💻🖥️ **Zero-Trust SQLite Guard:** Lõi Rust chặn toàn luồng (I/O block) mọi truy vấn đến file `cold_state.db` và `hot_dag.db` cho đến khi nhận được xác thực thành công từ Hardware Root-of-Trust. Ngăn chặn triệt để đọc lén dữ liệu qua luồng ngầm.
- 📱💻🖥️ **Cryptographic PIN Fallback Dialpad:** Bàn phím nhập mã PIN dự phòng trượt nhẹ trên nền Skeleton UI, đảm bảo logic xử lý PIN diễn ra an toàn, xóa sạch (`ZeroizeOnDrop`) plaintext PIN khỏi RAM ngay lập tức mà không ghi log hay truyền qua Bridge.

#### Rò rỉ qua OS Snapshot (Secure Screen Masking & Blurhash Overlay)

- 📱 Kích hoạt lớp phủ màn hình bảo mật che dấu nội dung nhạy cảm ngay khi nhận tín hiệu `applicationWillResignActive` (iOS) hoặc `onPause` (Android).
- 📱 Khai thác dữ liệu Blurhash siêu nhẹ (30-50 bytes) có sẵn trong SQLite hiển thị giao diện mờ thay thế cho Plaintext, triệt tiêu rủi ro rò rỉ hình ảnh vào Core OS qua màn hình đa nhiệm.
- 📱 Đảm bảo kết quả snapshot do OS lưu trên đĩa cứng trắng thông tin thực tế, bảo vệ trọn vẹn quyền riêng tư người dùng trong trình chuyển đổi ứng dụng.

#### Ngắt tác vụ ngầm khẩn cấp (High-Priority FFI Kill-Switch & Cancellation Token Bypass)

- 📱💻 Phát nhịp lệnh FFI `terachat_core_emergency_wipe()` từ Native UI đánh thẳng vào Event Loop của Rust Core với mức độ ưu tiên tuyệt đối.
- 📱💻🖥️ Áp dụng cấu trúc Cancellation_Token rẽ nhánh qua `tokio::select!` hoặc thẻ `AbortHandle` ép dừng khẩn cấp mọi Worker Thread vòng I/O hoặc tiến trình giải mã.
- 📱💻 Thiết lập ngầm cơ chế bypass hàng đợi tác vụ đảm bảo lệnh tiêu hủy thực thi nghiêm ngặt dưới ngưỡng hard deadline 10ms, đè bẹp tốc độ dump RAM mặc định của OS.

#### Tiêu hủy RAM vật lý (Contiguous Memory Arena SIMD Zeroization)

- 📱💻🖥️ Cấu trúc khối LRU Cache theo chuẩn Contiguous Memory Arena quản lý phân vùng RAM liên tục 50MB, tối ưu hóa tốc độ truy cập chéo và tiêu hủy toàn phần.
- 📱💻 Kích hoạt lệnh intrinsics cấp thấp (SIMD/Neon) ghi đè mã hex $0x00$ cày nát toàn bộ dải địa chỉ của khối Arena nội trong 1-2 mili-giây.
- 📱💻🖥️ Ràng buộc pattern ZeroizeOnDrop kết hợp rào cản trình biên dịch dọn dẹp triệt để Plaintext không thể bị trích xuất phục hồi sau khi App lùi về chế độ Background.

#### Phục hồi sau khi đóng ứng dụng (Metadata-driven JIT Re-hydration)

- 📱💻 Khai thác `cas_ref` và tập Metadata đệm từ SQLite tái thiết lập cấu trúc khung nhìn nguyên bản ngay khi hệ thống xoay vòng về trạng thái Active.
- 📱💻🖥️ Kêu gọi tiến trình Just-In-Time (JIT) Fetching âm thầm tải và giải mã luồng Thumbnail bám sát Viewport, mang tới trải nghiệm Render liền mạch.
- 📱💻 Bù đắp khoảng lặng phục hồi vài chục mili-giây bằng kỹ xảo sắc nét hóa từ lớp mờ Blurhash che giấu hoàn toàn hoạt ảnh trắng RAM bị dọn dẹp trước đó.

### 6.10 Ép xung Phần cứng & Nén Dữ liệu Động học (Hardware Offloading & Zero-Knowledge SDDC)

#### Ép xung Phần cứng Chuyên trách (Hardware-Native Crypto & Search Acceleration)

- 📱💻 Khai thác sức mạnh tàng hình của hàm API Native (Metal API trên macOS/iOS, Vulkan/NNAPI trên Android) đẩy tác vụ đồ họa, tìm kiếm sang luồng GPU/NPU chuyên biệt.
- 📱💻🖥️ Kích hoạt chip phần cứng tăng tốc mã hóa (Hardware AES-NI/ARM NEON) ép khuôn tốc độ xả mã luồng băm AEAD theo thời gian thực.
- 📱💻 Vận hành mô tơ tìm kiếm NPU-Optimized FTS5 dội bom từ khóa thẳng vào khối logic xử lý hình ảnh nội tại, tìm kiếm không giới hạn lịch sử cục bộ.

#### Native Hardware Offloading via Apple Neural Engine (ANE)

- 📱 Biên dịch chéo mô hình SLM/ONNX sang định dạng `.mlmodelc` tương thích hoàn toàn với nền tảng Core ML.
- 📱 Xây dựng cầu nối FFI (Foreign Function Interface) điều phối dữ liệu trực tiếp từ Rust Core sang khối NPU.
- 📱 Tận dụng Apple Neural Engine (ANE) nhằm tăng tốc xử lý ma trận Vector, ép xung tiêu thụ điện năng điện toán SLM xuống mức tối thiểu.

#### Nén Dữ liệu Động học (Zero-Knowledge Shared Dictionary Delta Compression - SDDC)

- 📱💻 Thực thi chu trình mã hóa và giải mã Zero-Knowledge Compression ngay tại phân vùng rìa cấu trúc biên (Client-Edge) trước khi đóng hộp E2EE lên Cloud.
- 📱💻🖥️ Nén tín hiệu trao đổi với thuật toán Zstd Pre-trained Dictionary được vi điều chỉnh riêng rẽ mài giũa cho ngôn ngữ văn bản doanh nghiệp mượt mà.
- 📱💻🖥️ Áp dụng giao thức chuyển đổi vi phân JSON Delta Encoding phân giải và truyền tải riêng biệt những mảnh chênh lệch nhỏ xíu lọt thỏm trong CRDT Event Log.

---

## 7. Ecosystem & Integration

### 7.1 WASM Sandbox (.tapp) & Dual-Registry

#### Phân vùng Thực thi (Sandbox vs Enclave)

- **Phân vùng 1 (UI Sandbox):** Chuyên trách bề mặt UI `.tapp` siêu nhẹ (10-50KB), tải nóng trực tiếp qua IPC Bridge phục vụ các tác vụ tương tác.
- **Phân vùng 2 (AI Enclave):** Chuyên trách mô hình AI/SLM. Sử dụng **Tiered Storage (Tầng 3)** kéo mô hình (ví dụ 100MB) về máy tĩnh cục bộ.
  - **Zero-Copy Map:** Lõi Rust dùng `mmap()` trỏ thẳng vùng nhớ ảo của mô hình để phân bổ cho AI Enclave, không bao giờ nhồi tệp >10MB qua SharedArrayBuffer để tránh nghẽn cổ chai IPC.

#### Dynamic Header Slot & Pinned Utility Registry (Launchpad Quick-Bar)

- 📱💻🖥️ Ánh xạ bảng `pinned_utilities` cục bộ sử dụng cơ chế lưu trữ SQLite WAL bảo mật.
- 📱💻🖥️ Thiết lập Unidirectional State Sync (Rust-to-UI Signal) nhằm tự động đồng bộ khi có tiện ích được gắn pin.
- 💻🖥️ Render cửa sổ Floating WASM Window phục vụ thao tác Quick-Execute dành riêng cho nền tảng Desktop.
- 📱 Nhúng Horizontal Mini-Dock Scroll tích hợp UI di chuyển siêu tốc cho nền tảng Mobile.

#### Cấu trúc .tapp (3 Tầng)

```text
[Tầng 1 — Web Marketplace (marketplace.terachat.io)]
  • Danh mục .tapp ký duyệt bảo mật (Ed25519 — TeraChat CA)
  • Admin bấm "Install" → lệnh xuống VPS
           │
           ▼
[Tầng 2 — VPS Control Plane]
  • Kéo .tapp (WASM + JSON Schema) về Cluster
  • Cấp bảng SQL trống (Blind Storage) làm Backend Sync
  • Phân phối .tapp xuống thiết bị qua App Sync
  • ❌ KHÔNG phải kênh phân phối Native App (Rust/Tauri Binary)
  • ❌ KHÔNG thực thi logic App — chỉ lưu blob mã hóa mù
> **Phân biệt rạch ròi:**
> - **Cập nhật Native App (TeraChat Binary):** Phải kiểm tra chữ ký `TeraChat_Global_CA`. Mobile đi qua App Store. Desktop đi qua VPS nhưng xác thực chữ ký tĩnh Ed25519 trước khi nạp.
> - **Cập nhật `.tapp` (Tiện ích nội bộ):** Được ký bởi `Enterprise_CA` nội bộ. VPS phân phối bằng CRDT Event Log.
           │
           ▼
[Tầng 3 — Device Data Plane (Desktop / Mobile)]
  • UI Sandbox thực thi 100% logic bằng CPU thiết bị (<= 50KB).
  • AI Enclave nạp model qua mmap(), tránh ArrayBuffer.
  • UI map JSON Schema (Server-Driven UI — Adaptive Cards).
  • Per-app SQLCipher (cô lập hoàn toàn).
  • ❌ VPS không đọc được dữ liệu — Zero-Knowledge
```

#### Security Gates & Hot-Reload (Chống Tiêm nhiễm & Rollback)

- 📱💻🖥️ **Offline Hot-Reload via Pinned Root Keys:** Chữ ký số Ed25519 xác thực tính chính chủ của gói `.tapp` (WASM). Khóa `Enterprise_App_Signing_PubKey` neo cứng trong Secure Enclave/StrongBox tạo Hardware Root of Trust. Toàn vẹn Hash được đối soát ngay trên RAM.
- 📱💻🖥️ **Anti-Downgrade Protection:** Lớp kiểm tra `Version_Tag` ngăn chặn tuyệt đối các cuộc tấn công Rollback ép hạ cấp module WASM.
- 📱💻🖥️ **JIT RAM-only Hot-Reload:** Sử dụng FFI Pointer bắn thẳng vùng nhớ chứa WASM Module sạch vào JIT Engine mà không quẹt qua Disk I/O. Cơ chế luồng Unidirectional State Sync kích hoạt Zero-downtime render cho UI mà không cần khởi động lại.

| Gate | Mechanism | When |
|---|---|---|
| **Digital Signature** | Ed25519 (TeraChat CA hoặc Enterprise CA) | Upload |
| **Integrity Hash** | SHA-256 khớp Manifest | Download |
| **Admin Approval** | OPA Policy check | Before Push |
| **Sandbox** | WASM container, no OS syscall | Runtime |
| **Permission Model** | Manifest-driven, Core cấp đúng quyền khai báo | Runtime |

#### WASM Network Rules (Bàn tay sắt)

- WASM **không bao giờ** chạm vào Network Socket trực tiếp.
- Mọi luồng mạng ra/vào phải đi qua `host_bindings` của Rust Core (kiểm duyệt Permission).
- API Key không bao giờ hardcode trong `.tapp` bytecode — phân phối qua E2EE.

#### 3 Gateway Modes cho .tapp

| Gateway | Dùng khi | VPS biết | Bảo mật |
|---|---|---|---|
| **E1 — Client-Side Direct** | Thiết bị có Internet | Không gì | Zero-Knowledge 100% |
| **E2 — VPS Egress Proxy** | LAN air-gapped | Chỉ URL đích + Ciphertext tạm (RAM-only, không log) | Ephemeral Pipe |
| **E3 — Blind Webhook** | Nhận event từ ngoài vào | Blob mã hóa mù (Curve25519 ECIES) | VPS không giải mã được |

#### OPA Payload Sanitization & Byte-Quota Enforcement

- 📱💻🖥️ Kích hoạt Whitelist Header Sanitization chỉ cho phép các trường `Content-Type`, `Authorization` và `Accept` đi qua kênh IPC.
- 📱💻🖥️ Thực thi JSON Schema Enforcement qua OPA để kiểm tra độ dài và kiểu dữ liệu của từng trường trong Payload nhắm tới Data Steganography.
- ☁️🗄️ Xây dựng hệ thống giám sát ngưỡng rò rỉ (Exfiltration Quota) sử dụng kiến trúc Redis Bloom Filter đặt tại Edge.

#### LLM Iron Dome — 3 Lớp phòng ngự Prompt Injection

- 📱💻🖥️ **Lớp 1 — Egress Firewall:** WASM chỉ truyền `User Intent` + `File ID`. Rust Core trích xuất file từ SQLite, nhúng vào template chuẩn, gọi LLM. Chỉ kết nối Whitelist Domains.

#### Tính toàn vẹn E2EE động — Independent Chunk Ciphertext & Nonce Progression

> **Giải pháp:** Thay vì mã hóa toàn bộ payload một lần (phải buffer toàn bộ trong RAM), mỗi 64KB chunk là một ciphertext độc lập với Nonce riêng biệt.

- 📱💻 **AES-256-GCM Incremental Nonce per Chunk:** `nonce_n = Base_Nonce XOR (chunk_index as u64, 0u64)` — mỗi chunk nhận Nonce duy nhất dẫn xuất từ index, không tái sử dụng. Receiver có thể verify và decrypt bất kỳ chunk nào độc lập mà không cần xử lý tuần tự.
- 📱 **iOS/Android JSI/FFI Bridge (Zero-Copy):** Chunk được sinh ra từ Rust, pass qua JSI Native Pointer trực tiếp vào `SendableBuffer` mà không copy qua MessageQueue. UI nhận raw pointer, render progress bar từ `chunk_index / total_chunks * 100`.
- 💻🖥️ **Zero-Copy Micro-buffer (Desktop):** `SharedArrayBuffer` 128KB pre-allocated. Rust writer và React reader shared-memory — không serialization overhead. Writer ghi chunk xong → atomic flag → Reader consume → Writer overwrite.
- 📱💻🖥️ **Chunk Authentication Tag Chaining:** Mỗi chunk's GCM authentication tag được XOR vào `chain_state` accumulator. Sau chunk cuối, `chain_state` được ký Ed25519 và đính kèm vào Transfer Manifest — tạo toàn vẹn end-to-end trên toàn file mà không cần buffer toàn bộ.

#### TLS Certificate Pinning (HPKP) — Thay thế Domain Whitelist (ISO 27001 A.5.19)

> **Loại bỏ:** `manifest.json` domain text whitelist (dễ bị DNS Spoofing). **Thay thế:** HPKP (HTTP Public Key Pinning) SHA-256 hash của server TLS Public Key lưu trong OPA Policy.

- 📱💻🖥️ **HPKP Policy trong OPA Bundle:** Thay vì `egress_endpoints: ["api.openai.com"]`, OPA Policy lưu `tls_pin: "sha256/abc123..."` (SHA-256 hash của Server Public Key). Khi `.tapp` trigger egress, Lõi Rust gọi `rustls` để verify handshake.
- 📱💻🖥️ **Rust TLS Fingerprint Verification:** Sau `ClientHello`, Lõi Rust extract `ServerCertificate.public_key_bytes`, tính SHA-256, đối chiếu với `tls_pin` trong OPA Policy. Mismatch → `TlsPinningError` → connection abort ngay lập tức. DNS phân giải đúng hay sai không quan trọng.
- 📱💻 **Pin Rotation (via Marketplace Update):** Khi partner server rotate TLS certificate, TeraChat Marketplace publish OPA Policy update mới (Ed25519 signed) chứa `tls_pin_new`. Client nhận update → verify signature → apply. `tls_pin_old` vẫn valid thêm 7 ngày (grace period) để tránh downtime.
- ☁️ **OCSP Stapling + CT Log Verification:** Ngoài pin check, Lõi Rust verify OCSP staple của server certificate và kiểm tra Certificate Transparency log (`rustls-native-certs` + `certificate-transparency` crate). Certificate không có CT log entry → reject connection.


- 📱💻🖥️ **Lớp 2 — Markdown AST Sanitizer:** Mọi `<img src="...">` / `![alt](url)` trỏ external URL bị chặn hoàn toàn. Chỉ cho phép `localhost` (VFS) hoặc base64 nội bộ.
- 💻🖥️ **Lớp 3 — Local Semantic Guardrail (Enterprise):** Model NLP ONNX tại biên kiểm tra file gửi đi — block Jailbreak / System instruction spoofing patterns.

### 7.2 Context-Aware Edge Defense & DLP Smart Clipboard

#### DLP — Desktop

- 💻🖥️ **Memory Air-Gap:** TeraChat Core và External Sandbox (Zalo/Telegram WebView) chạy 2 Process riêng biệt cấp OS. Crash/XSS từ Sandbox không dump được memory Core.
- 💻🖥️ **Smart Clipboard Controller (Rust module):** Hook OS Clipboard API real-time. Phân loại nội dung: nội bộ TeraChat → block paste vào Sandbox. OPA Policy quyết định per-channel.
- 💻🖥️ **Drag & Drop Blocking:** Chặn kéo thả file từ TeraChat sang External Sandbox.
- 💻🖥️ **External Sandbox Isolation (Tauri):** Mỗi app ngoài chạy Window riêng — không có Tauri IPC, không thấy `Company_Key`, Network độc lập (traffic đi thẳng Internet), Ephemeral Storage (có thể reset theo OPA Policy).

#### DLP — Mobile

- 📱 **Android:** `FLAG_SECURE` (WindowManager) — chặn Screenshot + Screen Recording cấp phần cứng.
- 📱 **iOS:** Lắng nghe `UIScreen.capturedDidChangeNotification` → phủ View đen khi bắt đầu quay màn hình.
- 📱 **In-App Copy Restriction:** Không thể hook Clipboard iOS. Thay vào đó, chặn hành vi Copy từ Text Node SecureText trong TeraChat Mobile.
- 📱 **DLP OPA Policy cho Mobile:** Admin cấu hình per-channel, per-department.

#### DLP — Screen Leakage & Clipboard Kernel-level Hardening

- 📱 **iOS `UIScreen.capturedDidChangeNotification` (Hardware-level):** Lõi Rust đăng ký observer cho `capturedDidChangeNotification` từ lúc app khởi động. Khi `UIScreen.main.isCaptured == true` (AirPlay, screen record, external display): Rust Core ngay lập tức phát `SecurityEvent::ScreenCapture` → UI phủ màn hình bằng `UIBlurEffect(.dark)` overlay toàn màn hình trước khi frame đầu tiên kịp capture. Chat messages bị ẩn, không phải làm mờ — nội dung không có trên bitmap.
- 📱 **Android `FLAG_SECURE` (WindowManager Kernel Gate):** `WindowManager.LayoutParams.FLAG_SECURE` được set ở tầng `Activity.onCreate()` — không thể set sau khi Window đã tạo. Flag này can thiệp vào Surface Compositor ở kernel — screenshot bằng mọi phương pháp (ADB, MediaProjection, Developer Tools) trả về black frame. Admin có thể toggle flag per-session qua OPA Policy.
- 💻🖥️ **Smart Clipboard Controller (Rust Hook — Kernel-level):** Rust module hook `SetClipboardData` (Windows) / `NSPasteboard` (macOS) tại syscall intercept level — không phải application-level listener. Khi nội dung clipboard có nguồn gốc từ TeraChat chat context (tagged bằng invisible RTLO marker): OPA Policy check `can_paste_external: false` → Rust silently drop clipboard write. Ứng dụng ngoài nhận clipboard rỗng. Không hiện dialog.
- 📱 **iOS Clipboard Expiry (60s TTL):** Thay vì block copy hoàn toàn (không thể hook `UIPasteboard` trên iOS hardened), Lõi Rust intercept qua JSI để set `UIPasteboard.general.expirationDate = now + 60s`. Clipboard tự purge sau 60 giây — giảm cửa sổ rò rỉ từ vô hạn xuống 1 phút.
- 📱 **Android Sensitive Clipboard API (Android 13+):** Sử dụng `ClipDescription.EXTRA_IS_SENSITIVE = true` để đánh dấu mọi ClipData từ TeraChat là sensitive. Keyboard IME ẩn nội dung khỏi clipboard suggestion bar. `ClipboardManager.clearPrimaryClip()` được gọi tự động khi app vào Background.

#### DLP Hard Rules Summary

| Hành động | Vùng 1 (Nội bộ) | External Sandbox | Mobile |
|---|---|---|---|
| Copy nội bộ → Paste ngoài | N/A | ❌ Clipboard Controller | ❌ SecureText (Copy blocked) |
| Drag & Drop file | N/A | ❌ Chặn | ❌ |
| Screen Share | ✅ | ❌ | ❌ FLAG_SECURE / Overlay |

### 7.4 Ephemeral Identity-Binding & Threshold-Based Reveal

- ☁️ Gán token vào IdP Session ID tạm thời tại thời điểm cấp phát (Binding được lưu trữ tại Vault, tuyệt đối không đính kèm vào Payload).
- ☁️🖥️ Áp dụng Threshold-Based Reveal chỉ cho phép giải mã danh tính thực thông qua sự đồng thuận của M-of-N Admin Audit Log khi xảy ra vi phạm nghiêm trọng.
- ☁️ Xây dựng logic cô lập tầng biên (Edge Blocking) dựa trên Token Hash thay vì truy nguyên User Identity.

### 7.3 AI Integration Gateway (Dual-Mask Protocol, TEE Enclave)

#### Architecture

```text
[Client (E2EE)] → [AI Gateway (Rust)] → [OpenAI / Claude / Azure AI]
                         ├── PII Redactor (Regex + NER — Dynamic Tokenization)
                         ├── Rate Limiter (per-tier, Bounded MPSC Channel)
                         ├── Quota Management
                         ├── Audit Logger (tamper-proof)
                         └── Model Router (Org Policy)
```

- ☁️ AI Bot có KeyPair Ed25519 riêng, join MLS Group như member bình thường. Chỉ active khi User `@mention` hoặc Admin Add Bot. **Không bao giờ auto-scan ngầm.**

#### Dual-Mask Protocol (Dynamic Tokenization)

- 📱💻🖥️ **Tokenization Pass:** Mỗi PII entity nhận alias riêng: `[REDACTED_PHONE_1]`, `[REDACTED_PHONE_2]`. Session Vault tồn tại trong RAM duy nhất cho 1 request.
- 📱💻🖥️ **De-tokenization Pass:** Sau khi nhận LLM response, thay alias trở lại giá trị thực trên Client.
- 📱💻🖥️ **Zero-Retention:** `SessionVault::drop()` overwrite toàn bộ giá trị gốc bằng `0x00` ngay sau De-tokenize (dùng `zeroize` crate).
- ☁️ Header `X-Zero-Retention: true` trên mọi request → ép API Provider không lưu trữ, không dùng để train model.
- ☁️ **BYOK (Bring Your Own Key):** API Key lưu trong Secure Enclave / OS Keychain — không bao giờ plaintext trên Server.

#### TEE Enclave cho AI Worker

- 🗄️☁️ AI Worker chạy trong Intel SGX / AWS Nitro Enclave — cô lập hoàn toàn. Cloud provider không đọc được dữ liệu xử lý.
- ☁️ **Thread-Pool Isolation:** Hai Tokio Runtime độc lập: `core-messaging-runtime` và `ai-heavy-io-runtime` giao tiếp qua Bounded MPSC Channel. Khi Channel đầy → reject AI request (ChannelFull) thay vì ngốn RAM.
- ☁️ **Circuit Breaker:** OPEN ngay nếu AI Latency p99 \>1500ms hoặc Packet Loss \>5% trong 10s. Fail-fast về UI.
- 💻🖥️📱 **Local Fallback:** Khi kết nối rớt → chuyển NLP tĩnh về Local WASM Sandbox (~100MB SLM). Session Ticket Caching: 4-RTT → 1-RTT.

#### ECRP IPC Protobuf Flow — UI Pure Renderer Mandate

> **Quy tắc bất biến:** Giao diện (UI) tuyệt đối không được cầm Context plaintext. UI chỉ gửi intent. Lõi Rust làm tất cả.

**Luồng IPC chuẩn:**

```text
[UI] ──── Fetch_And_Mask_Context(depth=50) ────▶ [Rust Core]
                                                      │
                                          Decrypt (Session_Key)
                                          ONNX NER Masking
                                          Protobuf Serialize
                                          TLS 1.3 Egress → TEE
                                                      │
                                          Receive AI Response
                                          De-tokenize MASK→Real
                                          ZeroizeOnDrop SessionVault
                                                      │
[UI] ◀──── StateChanged(masked_result, ui_delta) ────┘
```

- 📱💻🖥️ **Fetch_And_Mask_Context:** UI gọi JSI/FFI `fetch_ai_context(depth: u32)` xuống Rust. **UI không nhận plaintext trung gian** — IPC channel chỉ trả về `StateChanged` event khi hoàn tất.
- 📱💻🖥️ **Rust calls Rust:** Toàn bộ pipeline (decrypt → mask → serialize → egress → de-tokenize → zeroize) chạy trong cùng Rust process. Không có boundary nào lộ plaintext ra ngoài Rust.
- 📱💻🖥️ **SessionVault Lifecycle:** Khởi tạo tại Bước 3 (pre-masking), tồn tại ≤ 1 request, bị `ZeroizeOnDrop` ngay sau De-tokenize — trước khi `StateChanged` được phát lên UI.
- 📱 **Mobile memory constraint:** Trên iOS/Android, toàn bộ masking pipeline phải hoàn thành trong < 500ms. Cấm dùng `mlock()` cho SessionVault trên Mobile — chỉ dùng `ZeroizeOnDrop` trên Heap. Mọi thao tác Masking qua FFI/JSI với lifetime < 500ms.
- 💻🖥️ **Desktop memory hardening:** Context Plaintext buffer và SessionVault phải được `mlock()` — OS không được phép swap xuống disk. Bọc trong trait `Drop` implement `zeroize()`.
- 📱💻🖥️ **Byte-Quota Enforcement:** Rust Core kiểm tra `payload_bytes ≤ 4096` TRƯỚC khi serialze Protobuf. Vượt ngưỡng → trả `EgressError::QuotaExceeded` về UI — không gửi bất kỳ gì ra ngoài.

#### Sliding Window Tokenizer — OOM Guard (iOS / Android)

> **Rủi ro:** Nhồi 50–100 tin nhắn vào RAM cùng lúc để chạy ONNX Local sẽ trigger **Jetsam OOM-Kill** trên iOS/Android — app bị kill ngay lập tức.

**Giải pháp: Incremental WAL Streaming + Hard Limit Buffer**

```text
hot_dag.db (SQLite WAL)
       │
       ▼ đọc từng dòng (streaming, không load toàn bộ)
[Sliding Window Buffer: 4096 Bytes Hard Limit]
       │
       ├─ Chưa đầy → đọc thêm record tiếp theo
       └─ Đầy (≥4KB) → Circuit Breaker ngắt luồng đọc
                         Giữ lại 4KB gần nhất (sliding tail)
                         Đẩy vào ONNX Masking Pipeline
```

- 📱 **Streaming từ SQLite WAL:** Lõi Rust mở cursor trỏ vào `hot_dag.db` WAL, đọc từng tin nhắn theo thứ tự timestamp giảm dần (mới nhất trước). Không dùng `SELECT * LIMIT N` — tránh load toàn bộ resultset vào RAM.
- 📱 **Hard Limit 4096 Bytes:** Biến `sliding_buffer: [u8; 4096]` được khai báo với kích thước cố định trên Stack (hoặc `Vec::with_capacity(4096)` trên Heap nếu cần dynamic). Khi `buffer.len() + next_msg.len() > 4096` → Circuit Breaker kích hoạt.
- 📱 **`MaybeUninit` cho ONNX Variables:** Biến phục vụ ONNX inference engine (`ort::Session`, `ort::Value`) khai báo bằng `std::mem::MaybeUninit<T>` — OS không cấp phát vùng nhớ thừa cho uninitialized state. Giảm peak RAM trước khi tensor thực sự cần.
- 📱 **Circuit Breaker ngắt luồng:** Khi buffer đầy, `SlidingWindowTokenizer::flush()` được gọi: emit current buffer sang ONNX Masking → reset buffer → tiếp tục đọc nếu còn dưới quota. Không có blocking, không có busy-wait.
- 📱 **`ZeroizeOnDrop` sau mỗi flush:** Sau khi buffer được consume bởi ONNX, `SlidingWindowBuffer::drop()` ghi đè `0x00` toàn bộ — không giữ plaintext trên Heap giữa các flush cycle.
- 💻🖥️ **Desktop:** Window size configurable (default 16KB, max 64KB theo Admin Policy). `mlock()` bắt buộc. ONNX chạy concurrently trên thread riêng với `rayon` threadpool — không block UI.

#### AI Consent / Opt-in (Bắt buộc)

- Mọi lần AI truy cập dữ liệu ghi vào **Tamper-Proof Audit Log**.
- AI không bao giờ có thể truy cập `Channel_Key` hay `Company_Key` — chỉ nhận alias đã tokenized.

---

*Tài liệu này chỉ chứa App-layer implementation. Xem `Core_Spec.md` cho Infrastructure/Security. Xem `Function.md` cho Product flows.*

---

## 8. Large File Handling & Advanced Sync

### 8.1 Xử lý File Khổng lồ — mmap + BLAKE3 Segmented Merkle + Native-to-Rust Media DataSource Bridge

#### Zero-Copy I/O qua Virtual Memory (mmap) & Rò rỉ Bộ nhớ FFI

- 📱💻🖥️ Lõi Rust gọi `mmap()` ánh xạ file vật lý trực tiếp lên vùng nhớ ảo. Page Fault nạp từng mảnh on-demand — không dùng `read/write` qua vRAM Buffer. RAM footprint < 10MB bất kể file nặng hàng GB.
- 📱 **SlotMap Handle Registry:** iOS Triển khai SlotMap (Handle Registry) tước bỏ Raw Pointer xuyên FFI để chặn Crash và Rò rỉ bộ nhớ (OOM-Kill) do Component Unmount bất ngờ. Giới hạn Memory Footprint dẹt (<10MB) bằng `mmap()` Ring Buffer tĩnh.
- 💻 **Tokio Asynchronous Segments:** Xử lý I/O bất đồng bộ qua Pipelined Segmented Merkle và Chunked AEAD nhốt gọn trong `tokio::task::spawn_blocking`, giải phóng Executor chính.
- 📱💻🖥️ **Strict Thread Isolation:** UI chỉ truyền `File_URI` xuống Rust → Rust trả `ACK_START < 16ms` giữ 60FPS. Toàn bộ tác vụ `mmap`, BLAKE3, AEAD nhốt vào `tokio::task::spawn_blocking`.

#### OS-Aware I/O Fallback & Synchronous Ring Buffer (Bẫy SIGBUS mmap trên iOS)

- 📱 Thay thế toàn diện `mmap()` bằng hệ thống lệnh `pread()` syscall để kiểm soát tường minh lỗi I/O chuẩn trên hạ tầng Mobile thay vì Kernel Panic.
- 📱 Quản trị vòng đời Fixed-Size Ring Buffer (2MB/4MB) cấp phát tĩnh tại ngăn xếp RAM không gian người dùng (User-space).
- 📱 Tiêm cơ chế catch lỗi văng `EIO/EPERM` để thực thi Graceful Abort và WAL Rollback ngay tích tắc khi thiết bị khóa màn hình (Data Protection Lock).

#### Tối ưu hóa truy xuất tệp tin hạng nặng (Pipelined Segmented Merkle Streaming)

- 📱💻🖥️ **Xác thực Phân mảnh Hiện đại:** Chia nhỏ file dung lượng khổng lồ thành nhiều `SegmentedMerkleBlock` để phân rã tiến trình xác thực tệp từng phần, triệt tiêu viễn cảnh đóng băng (Freeze) giao diện UI.
- 📱💻🖥️ **Cơ chế Lazy-Load:** Kích hoạt thuộc tính tải trễ tĩnh (Lazy-load) chỉ tự động phân phát gói tin dữ liệu đúng vào thời điểm phát sinh yêu cầu truy xuất thực tế từ bộ nhớ.
- 📱 Cắm chốt hệ thống giải mã thời gian thực (On-the-fly) luân chuyển ngầm trực tiếp qua **Native-to-Rust Media DataSource Bridge**: byte sau khi giải mã chảy thẳng từ Ring Buffer 2MB trong Lõi Rust sang trình phát hệ điều hành thông qua FFI (AVAssetResourceLoader/MediaDataSource/Tauri protocol handler), không dựng bất kỳ Local HTTP Server `127.0.0.1` nào.

#### BLAKE3 Segmented Merkle Tree — Xác thực Chunk không Freeze UI

- 📱💻🖥️ **Pipelined Segmented Merkle:** Chia file thành Macro-Block 64MB. Rust băm BLAKE3 Macro-Block #1 (<50ms) → gửi Root Hash qua Control Plane → nhồi chunks vào Data Plane → đồng thời băm Macro-Block #2. **O(1) Initial Latency** bất kể kích thước file.
- 📱💻🖥️ **AEAD Associated Data (Cryptographic Offset Binding):** Mỗi chunk: `AD = [File_ID] || [Chunk_Index] || [Byte_Offset]`. Receiver kiểm chứng AD_Expected trên RAM. Sai lệch → AEAD fail → Drop lập tức. Chặn **Displacement Attack** và **Replay Attack**.
- 📱💻🖥️ **Deterministic Nonce:** `Nonce = HMAC-SHA256(Channel_Key, File_ID || Chunk_Index)`. Nonce lệch do tráo chunk → panic tại cửa bộ giải mã.
- Hiệu năng: BLAKE3 Out-of-Order verification ~6GB/s (Desktop CPU).

#### Native-to-Rust Media DataSource Bridge & On-the-fly Decryption (FFI Byte Pumping, No Local HTTP)

- 📱 **iOS — AVAssetResourceLoaderDelegate:** Ứng dụng Native đăng ký `AVAssetResourceLoaderDelegate` làm cầu nối. Mỗi request từ AVPlayer tương ứng với một khoảng `[offset, length]` trong stream; Delegate gọi FFI `terachat_media_read(chat_id, file_id, offset, length)` để đọc byte đã giải mã trực tiếp từ `Ring_Buffer_2MB` của Lõi Rust, trả về cho AVPlayer dưới dạng `NSData`. Không có TCP Socket, không loopback `127.0.0.1`, iOS Background/Foreground hoạt động ổn định.
- 📱 **Android — MediaDataSource:** Trình phát ExoPlayer/MediaPlayer dùng `MediaDataSource` tùy biến, ánh xạ các lệnh `readAt(position, buffer, size)` → FFI sang Rust để rót plaintext chunk vào `ByteBuffer` Dart/Native, bơm thẳng vào pipeline giải mã của hệ điều hành.
- 💻🖥️ **Desktop — Custom Protocol Handler:** Trên Desktop, WebView/Tauri sử dụng Custom URL Scheme (`terastream://...`) hoặc Protocol Interceptor mapping trực tiếp sang FFI gọi Rust, đọc từ `Ring_Buffer_2MB` thay vì Local HTTP Server; vẫn giữ lợi thế Seek ngẫu nhiên nhưng không mở rộng bề mặt TCP.
- 📱💻🖥️ **Cryptographic Tokenized URI — Chống URI Scheme Hijacking (OTP One-Shot Token):**
  - > **Lỗ hổng Khẩn cấp:** Bất kỳ ứng dụng độc hại nào cài trên cùng máy (Windows, macOS, Android) đều có thể request tới `terastream://video_id` và hút luồng byte video đang giải mã trong RAM nếu Lõi Rust không xác thực Caller ID.
  - 📱💻🖥️ **OTP Token Flow:** UI layer (Swift/Kotlin/Tauri) yêu cầu Lõi Rust cấp token qua IPC an toàn trước khi mở stream. Lõi Rust sinh token: `token = HMAC_SHA256(Channel_Key, video_id || timestamp || process_id)`, TTL 30 giây. URL stream trở thành: `terastream://video_id?token=<OTP>`.
  - 📱💻🖥️ **Caller Verification:** Mỗi request tới scheme handler, Lõi Rust verify: (1) Token HMAC hợp lệ, (2) `process_id` trong token khớp với PID caller hiện tại, (3) Token chưa hết hạn, (4) Token chưa được dùng (single-use nonce, lưu trong `used_tokens` LRU cache 64-entry). Bất kỳ điều kiện nào fail → Drop kết nối, log `IPC_EVENT: UNAUTHORIZED_SCHEME_ACCESS` kèm PID app lạ.
  - 📱💻🖥️ **Zero-Tolerance Enforcement:** Nếu phát hiện `UNAUTHORIZED_SCHEME_ACCESS` ≥ 3 lần trong 60s từ cùng một PID → Lõi Rust tự động revoke `Channel_Key` của session đó và gửi cảnh báo `SECURITY_ALERT` tới Admin Console.

 (Just-In-Time) Fetching nhằm cơ động tải trực giác đúng Chunk cần thiết dựa trên vị trí Byte Offset của thanh tiến trình (Seek bar); mọi plaintext trong Ring Buffer được đánh dấu `ZeroizeOnDrop`/RAII và Memory Footprint giữ ổn định < 8MB bất kể file gốc hàng GB.

- 📱 **Chunked AEAD (STREAM / OAE1):** Chống lỗi Merkle Chain BLAKE3 theo chiều ngang bảo chứng chuỗi 1 byte hỏng không phá bung tập dữ liệu 4GB tổng.

#### In-Memory Pumping via Custom URL Scheme Handler (Lỗ hổng TCP Local và Cleartext)

- 📱 Triển khai `AVAssetResourceLoader` (iOS) và `MediaDataSource` (Android) để nạp gói tin dữ liệu luân chuyển trực tiếp qua bộ nhớ vật lý.
- 📱 Giải mã cục bộ AES-GCM On-the-fly tốc độ cao ngay tại luồng bơm byte (Byte-stream) truyền phát.
- 📱 Đúc kết cơ chế bypass hoàn toàn ATS (App Transport Security) và Network Security Configuration nhờ việc thủ tiêu vĩnh viễn cấu trúc Local TCP Socket.

#### OS-Level BLE Offloading (Ký sinh tiến trình nền OS)

- 📱 Sử dụng cơ chế State Preservation & Restoration (iOS CoreBluetooth) và PendingIntent (Android) để ủy quyền quét Service UUID cho phần cứng.
- 📱 Chuyển Rust Core sang trạng thái Suspend (0% CPU) cho đến khi nhận tín hiệu đánh thức từ OS.
- 📱 Lọc thiết bị qua băm mật mã UUID để giảm thiểu số lần thức giấc của App chính.

### 8.2 Đồng bộ CRDT bằng Hybrid Logical Clocks (HLC) — Khi Offline

#### Triệt tiêu Clock Drift

- 📱💻🖥️ **HLC Timestamp:** Mọi thao tác trạng thái định danh bằng `(Lamport_Counter, Node_ID, Wall_Clock_HLC)`. HLC bảo vệ tính nhân quả (Causality) bất chấp đồng hồ phần cứng OS sai lệch hàng tiếng.
- 📱💻🖥️ Tuyệt đối không dùng `SystemTime::now()` cho ordering — dùng NTP nội bộ Rust Core + Lamport Vector Clock.

#### DAG Causal Graph + Delta-State CRDT Pending Buffer

- 📱💻🖥️ **Delta-State CRDT:** Chuyển đổi từ mô hình Op-based nguyên thủy sang Delta-State CRDT để chỉ truyền tải bản tóm tắt trạng thái cuối cùng (thay vì toàn bộ lịch sử thao tác).
- 📱💻🖥️ Mỗi gói E2EE BLE kết nối vào DAG (Đồ thị có hướng không vòng). Event Out-of-Order thiếu gốc → `Pending_RAM_Buffer`. UI chỉ render khi gốc Đồ thị Nhân quả đã đầy đủ từ tất cả luồng Mesh.
- 📱💻🖥️ **Aggressive Tombstone Pruning:** Sau khi Quorum (VD: 3/5 Super Nodes) xác nhận đồng bộ History X → Rust chạy lệnh Snapshot State → Xóa vĩnh viễn Tombstone khỏi SQLite. Cắt dung lượng từ 500MB xuống ~10MB.
- 📱 💻 **Orphan_Blob TTL Expire Timer:** Niêm hạn TTL cho mọi Orphan Blob rác đọng lại — tự động hết hạn và thu dọn, giải phóng bộ nhớ mobile khỏi tình trạng đầy đĩa trầm kha.
- 📱 💻 **GCSFilter Block ID Indexing (< 50KB):** Xây dựng bộ lọc GCS thu gọn (< 50KB) đánh chỉ mục Block ID cho phép tra cứu nhanh Orphan Blob hợp lệ mà không quét toàn bộ DB.
- 📱 💻 **Low-Priority Background Garbage Collector:** Lên lịch tiến trình dọn rác ưu tiên thấp chạy nền khi thiết bị nhàn, tránh ảnh hưởng foreground latency.
- 📱 💻 **Crypto-Shredding & SQLite VACUUM:** Ghi đè khóa mã hóa về 0x00 trước khi hủy Blob, kết hợp `VACUUM` SQLite nén mảnh vỡ trang đĩa về 0 byte thực sự.


#### Giao thức Vỏ bọc mờ (Opaque Envelope) & Hash Invariance (Đứt gãy Đồ thị CRDT)

- 📱💻🖥️ Ràng buộc thuật toán Blake3 thực hiện băm trực tiếp trên dải byte thô (Raw Bytes) thay vì struct đã deserialize để bảo toàn tuyệt đối ID Node CRDT.
- 📱💻🖥️ Tận dụng tính năng `UnknownFieldSet` của Protocol Buffers để lưu trữ nguyên bản và chuyển tiếp các trường dữ liệu mới mà nhánh thiết bị cũ chưa kịp nhận diện.
- 📱💻🖥️ Thực thi cơ chế "Forward-Preservation" đảm bảo dữ liệu đến từ tương lai đi xuyên qua các node trung gian lỗi thời mà không bị bốc hơi dòng siêu dữ liệu cốt lõi.

#### Shadow Execution & Pre-Flight Hash Consensus (Split-Brain CRDT)

- 📱💻🖥️ Vận hành cơ chế Shadow Execution thực thi lại (Replay) hàm WASM tại thiết bị nhận để đối soát chéo kết quả.
- 📱💻🖥️ Sử dụng BLAKE3 State Hashing để kiểm chứng tính toàn vẹn tuyệt đối của Trạng thái đầu ra (Output State).
- 📱💻🖥️ Thuật toán Byzantine Isolation tự động cô lập các node sinh dữ liệu dị thường (dấu hiệu chẻ nhánh) khỏi mạng lưới Mesh cục bộ.

#### Constraints & RAM Circuit Breaker

- ⚠️ **RAM Circuit Breaker:** Tín hiệu CHOKE tự động phân rã lưới Mesh, ngăn chặn nạp dữ liệu vào bộ đệm Out-of-Order khi RAM vượt ngưỡng an toàn (Ví dụ: `8MB Buffer / 24MB Limit` trên iOS NSE) để tránh Jetsam OOM-Kill.
- ⚠️ CRDT Write Local-First < 5ms. Garbage Collection Epoch < 50ms. RAM Buffer Out-of-Order Event < 8MB.
- 📱 **Reputation Router & Token Bucket (5MB/100 packets):** Triển khai Decentralized Token Bucket kiểm soát băng thông mỗi peer tối đa 5MB/100 packets, chặn đứng chiến lược cạn kiệt tài nguyên Mesh (Mesh Battery Drain Attack).
- 🗄️ **Battery Hook OS API Auto-Cutoff (> 15%):** Kết nối OS Battery Hook API cắt toàn bộ relay traffic khi mức pin tụt dưới 15% bảo vệ thiết bị khẩn cấp.
- 📱 **BLE Rx Interface Circuit Breaker:** Ngắt giao diện BLE Rx khi phát hiện luồng flooding bất thường, phục hồi tự động sau 10s cooldown.
- 📱 **EMERGENCY_SOS_FLAG QoS Bypass:** Tin nhắn mang cờ `EMERGENCY_SOS_FLAG` vượt qua toàn bộ rào chắn Token Bucket và Circuit Breaker — đảm bảo thông tin khẩn cấp luôn ưu tiên tuyệt đối.


### 8.3 TeraVault VFS — Quản lý thư mục và Sao chép file không tốn bộ nhớ

#### Virtual File System (VFS) Zero-Copy Pointer Mapping

- 📱💻🖥️ **Ánh xạ Không gian Ảo:** Duy trì bảng ánh xạ `vault_file_mappings` liên kết trực tiếp con trỏ `cas_ref` với siêu dữ liệu metadata logic để tránh nhân bản khối dữ liệu.
- 📱💻🖥️ **IPC Pinning Command:** Triển khai lệnh IPC siêu nhẹ `vault::pin_file` trực tiếp thực thi thao tác ghim file phi vật lý vào cấu trúc cây thư mục.
- 📱💻🖥️ **Hiệu năng $O(1)$:** Đảm bảo tốc độ xử lý $O(1)$ cho mọi thao tác cốt lõi gồm Copy, Move và Pin với độ trễ phản hồi thấp dưới ngưỡng hẹp 5ms.
- 💻🖥️ E2EE không bị ảnh hưởng — `File_Key` vẫn nguyên vẹn. TeraVault chỉ quản lý metadata.

#### Tự động phân loại tài liệu (Auto-Classification)

- 📱💻 **Context-Aware Auto-Mapping Topology:** Thiết lập cơ chế tự động ánh xạ thông minh định tuyến file thẳng từ luồng Chat nguyên bản vào Thư mục Cấp 1 (Auto) tương ứng với tên định danh của Channel.
- 📱💻🖥️ Duy trì toàn vẹn cấu trúc cây thư mục logic đóng vai trò độc lập, không xâm lấn hay đụng độ với tầng cơ sở mã hóa vật lý ở cấp thấp.
- 📱💻🖥️ Tích hợp hệ thống Tagging đánh nhãn động lực tự động được lập chỉ mục (index) để khuếch đại tốc độ rà quét và truy vấn luồng metadata.

#### Cấu trúc Folder

| Cấp | Nguồn | Ví dụ |
|---|---|---|
| **Cấp 1 (Auto)** | Tên Channel / Group Chat | `📁 Dự án Alpha`, `📁 Phòng Kế Toán` |
| **Cấp 2+ (Manual)** | Admin / User tạo thủ công | `📁 Hợp đồng 2026`, `📁 Bản vẽ kỹ thuật Q1` |

- 💻🖥️**VFS Search:** `vault_file_mappings.file_name` + `tags` được index bằng PostgreSQL FTS (tsvector) hoặc local SQLite FTS5. Kết quả trả về FileStub → lazy-load từ Cluster.

### 8.4 CAS_Hash Dedup trong Offline Mesh

- ☁️🖥️ Xây dựng Deferred CRDT Sync dành riêng cho kho lưu trữ TeraVault VFS.
- 📱💻🖥️ Khi upload trong mạng Mesh offline, Rust sinh `FileStub_UUID = Hash(Device_ID + Local_Timestamp)`. Cho phép trao đổi P2P qua định danh này.
- ☁️🗄️ Khi kết nối lại, multi-client push payload. Cụm Server kích hoạt hàm Arbitrator, chạy thuật toán CRDT "First-Seen-Wins" xử lý đụng độ cùng `CAS_Hash`.
- 📱💻🖥️ Trả về `Canonical_VFS_ID` duy nhất. Client nhận ID này và update lại bảng SQLite FTS (Full-Text Search) cục bộ bằng một transaction duy nhất (Atomic write).

### 8.5 Smart Queue Management & Graceful Degradation (Adaptive Payload Gating)

> **Bài toán:** Nhân viên A gửi Video 50MB và Tin nhắn Text cho nhân viên B đang ở trạng thái **Offline Far (Tier 3)**. Nếu không có Gating, cả 2 payload đều bị block hoặc reject → mất liên lạc.

- 📱 **Fork Queue theo Tier:** Lõi Rust chia nhánh (Fork) hàng đợi tự động khi phát hiện đích đang ở Tier 3:
  - ✅ **Text path:** Tin nhắn Text được mã hóa bằng `Epoch_Key` và đẩy vào BLE Broadcaster ngay lập tức — thông lượng < 1KB/s, đến tay B trong vài giây.
  - ⏳ **Media path:** Video 50MB bị giữ lại trong **`cold_state_shadow.db`** (Local Storage của A — riêng biệt với `hot_dag.db` để không lock Main DB). Trạng thái đánh dấu `PENDING_NETWORK_UPGRADE`.
- 📱 **Zero-Touch UX — Auto Drain khi Tier nâng cấp:** Ngay khi A đi bộ lại gần B (< 50m), `Network_State_Machine` phát hiện Wi-Fi Direct Tier 2 handshake. Lõi Rust tự động xả `cold_state_shadow.db`, truyền Video 50MB sang B qua Wi-Fi Direct với tốc độ ~20MB/s (~2.5 giây). Toàn bộ quá trình diễn ra **ngầm (Zero-Touch)** — người dùng không cần thao tác lại.
- 📱💻🖥️ **Fallback Voice Recording — Codec Auto-Downgrade:**
  - **Tier 1 (Online):** Opus 128kbps Stereo — chất lượng đầy đủ.
  - **Tier 2 (Offline Near):** Tự động chuyển sang **AMR-NB 4.75kbps Mono** — file ghi âm 1 phút chỉ nặng ~35KB, lọt qua khe hẹp của Mesh 250Mbps.
  - **Tier 3 (Offline Far):** Tắt hoàn toàn ghi âm từ UI. Lõi Rust (tùy chọn) gọi Whisper AI cục bộ để phiên dịch sang Text nếu gửi từ máy Android/Desktop sang iOS bị locked.
- 📱 **Auto-Pause Media — UI Hard Lock ở Tier 3:** Người dùng ở Offline Far không thể click icon Camera/File. Lõi Rust chủ động báo `MediaUnavailable(tier=3)` về UI — nút bị Disabled trước khi người dùng kịp tương tác.

### 8.6 Open-Agent Protocol (OAP) — API cho Agentic .tapp

> **Mục tiêu:** Các nhà phát triển AI chỉ cần wrap API của họ theo chuẩn OAP để chạy trên TeraChat. Zero-Infrastructure overhead — mọi TLS handshake do Lõi Rust xử lý.

- 📱💻 **`terachat.agent.stream_completion({ context_uuid: String, prompt: String, model: String })`** — Gửi prompt tới AI Agent bên ngoài qua UAB. Lõi Rust thực thi TLS, không WASM.
- 📱💻 **`terachat.context.request_read_access(scope: "current_thread" | "mentioned_files")`** → Trả về mảng byte dữ liệu đã được Lõi Rust giải mã tạm thời trong RAM. Consent Modal bắt buộc trước khi API trả data.
- 🗄️ **ZeroizeOnDrop Binding:** Toàn bộ Response từ AI Agent sau khi render lên màn hình sẽ được đánh dấu vòng đời. Khi người dùng đóng tab chat, Lõi Rust lập tức gọi `zeroize()` ghi đè RAM. Không lưu cache vào `hot_dag.db` trừ khi người dùng chủ động bấm **"Save to Note"**.

#### §Phân luồng .tapp — Lightweight vs Heavyweight Routing

> **Vấn đề Mobile Battery:** Ép `.tapp` AI/NLP nặng chạy trên Mobile WASM → pin sụt, máy nóng, app bị gỡ. Giải pháp: phân loại tĩnh trong `manifest.json` và route tự động.

| Field `type` | Thực thi | Yêu cầu | Ví dụ |
|---|---|---|---|
| `"lightweight"` | 📱 Mobile WASM (`wasm3`/`wasmtime`) | Standard License | CRM UI, Poll, Reminder |
| `"heavyweight"` | ☁️ VPS Enclave (TEE) | Elite License | Local LLM, NLP Mining, Data Sync |

- 📱💻🖥️ **Static Classification trong `manifest.json`:** Developer khai báo `"tapp_type": "lightweight"` hoặc `"tapp_type": "heavyweight"` tại publish time. Marketplace CI/CD kiểm tra: Heavyweight `.tapp` tham chiếu WASM binary > 10MB hoặc AI model > 50MB → **bắt buộc** set `heavyweight`. Sai khai báo → reject publish.
- 📱 **Auto-Route Lightweight → Mobile WASM:** Lõi Rust load `.tapp` Lightweight vào local WASM sandbox (`wasm3` interpreter trên iOS, `wasmtime` JIT trên Android/Desktop). Latency: < 20ms init. Pin overhead: < 1% per request.
- ☁️ **Auto-Route Heavyweight → VPS Enclave (Elite):** Lõi Rust detect `heavyweight` flag → kiểm tra Elite License (`license_tier: "elite"` trong OPA Policy) → thực hiện DCAP Attestation với VPS Enclave → route computation. Nếu không có Elite License: UI hiển thị `"Nâng cấp TeraChat Elite để dùng tính năng này"` (không crash, không error thô).
- 📱 **Battery-Aware Routing Override:** Nếu Mobile < 20% pin → tất cả `.tapp` Lightweight cũng tự động route lên VPS Enclave (nếu có Elite). Tiết kiệm pin trong trường hợp khẩn cấp.
- ☁️ **Enclave Sandbox Isolation:** `.tapp Heavyweight` trong Enclave vẫn chịu đầy đủ OPA DLP + Egress_Outbox + BLAKE3 hash chain giống Mobile — không có ngoại lệ bảo mật dù chạy server-side.

### 8.7 Client-Side JIT Decryption & Direct Egress Execution


- 📱💻🖥️ **Local Plaintext RAM (`mlock`):** Sau khi giải mã E2EE, plaintext tồn tại duy nhất trong `mlock`-protected RAM arena. Không có copy nào được tạo ra ngoài arena này. Vòng đời được quản lý bởi RAII — zeroize khi thoát scope.
- 📱💻🖥️ **Direct TLS Egress (`api.openclaw.com`):** Lõi Rust (không phải WASM) mở TLS 1.3 connection trực tiếp tới AI endpoint từ `mlock` arena. Plaintext không bao giờ đi qua WebView, JS thread, hay bất kỳ tầng intermediate nào.
- 📱💻🖥️ **WASM Sandbox Isolation:** WASM chỉ nhận kết quả trả về (AI response đã được SASB sanitize thành `Vec<ASTNode>`) — không bao giờ tiếp xúc plaintext input hoặc TLS socket handle.

### 8.8 Zero-Copy Flow & Shared Memory IPC Bridge

- 🖥️ **`SharedArrayBuffer` (mmap — Desktop/Tauri):** Trên Desktop, Lõi Rust và UI chia sẻ một `SharedArrayBuffer` được `mmap` trực tiếp. AI context (embedding vectors, chat history) được truyền qua shared region ~500MB/s — zero copy overhead.
- 📱 **iOS JSI C++ Native Pointer:** Trên iOS, sử dụng React Native JSI với `std::unique_ptr<C++ Buffer>` trỏ thẳng vào vùng RAM của Lõi Rust. UI nhận Pointer, không nhận copy — throughput ~400MB/s, latency < 1ms.
- 📱 **Android Dart FFI TypedData:** Trên Android, `Dart FFI TypedData` được backed bởi C ABI static buffer của Lõi Rust. Zero allocation on Dart side — GC pressure bằng 0 khi xử lý large AI context payloads.

#### Cross-Origin Security Header Injection (CORP/COOP)

- 💻 Cấu hình Tauri CustomProtocol IPC Interception để xử lý đụng độ URI.
- 💻 Bơm header `Cross-Origin-Embedder-Policy: require-corp` (COEP) để vô hiệu hóa nhúng trái phép.
- 💻 Bơm header `Cross-Origin-Opener-Policy: same-origin` (COOP) cho phép SharedArrayBuffer hoạt động an toàn.

### 8.9 WASM Air-gap Network Proxying via Rust-Bridge (ZTEB)

> **ZTEB: Zero-Trust Egress Boundary** — WASM Sandbox bị air-gap hoàn toàn khỏi network stack.

- 💻📱 **WASM-to-Rust Host Function (FFI):** WASM sandbox không có capability `wasi-sockets` (bị strip tại compile time). Thay vào đó, WASM export host function `__terachat_send_request(endpoint_id, payload_ptr, len)` — Lõi Rust intercept và quyết định có forward không.
- 💻📱 **Socket-less Sandbox Environment:** Lõi Rust compile WASM module với `wasm-opt --strip-producers` và custom linker script xóa bỏ `wasi:io`, `wasi:sockets`, `wasi:filesystem` imports. WASM chỉ còn `wasi:cli/stdout` (debug) và TeraChat custom host functions.
- 🖥️📱 **Zero-Copy JSI/FFI Data Flow:** Response từ External AI được Lõi Rust SASB-sanitize → serialize Protobuf → truyền qua JSI/FFI shared pointer về UI renderer. WASM sandbox chỉ nhận final rendered AST — không có raw response string.

### 8.10 Deterministic Memory Quota & Panic Handler

- 📱💻 **Rust Hard-limit (8MB Heap Cap):** Toàn bộ ONNX inference + embedding pipeline hoạt động trong một custom allocator với hard ceiling 8MB. Nếu allocation vượt quá 8MB, allocator return `Err(AllocError)` — pipeline gracefully fallback về Flat-search (no ONNX) thay vì crash.
- 📱💻 **Runtime Allocation Monitoring:** Lõi Rust sử dụng `tikv-jemallocator` với `malloc_stats_print` để monitor heap usage mỗi 5s. Nếu heap > 6MB (75% quota), pipeline tự động giảm batch size từ 32 → 8 vectors/batch để tránh spike.
- 📱 **iOS/Android Memory-Pressure Callback:** Đăng ký `applicationDidReceiveMemoryWarning` (iOS) / `onTrimMemory(TRIM_MEMORY_RUNNING_CRITICAL)` (Android). Khi nhận callback, Lõi Rust immediately zeroize toàn bộ vector cache và pause ONNX pipeline — ưu tiên giữ `hot_dag.db` và chat session.

### 8.11 Stream-Direct Open-Agent Protocol (SD-OAP) — File-to-Agent Streaming

- 📱💻 **`terachat.network.stream_file_to_agent(file_uuid, agent_endpoint, consent_token)`** — API mới cho phép `.tapp` gửi file lớn sang AI Agent mà không buffer toàn bộ vào RAM. Lõi Rust stream 2MB chunks trực tiếp từ `TeraVault VFS` → TLS socket.
- ☁️ **TLS Socket Flushing (Zero-copy):** Mỗi chunk sau khi decrypt được flush ngay vào TLS socket buffer — không accumulate trong heap. HTTP/2 DATA frame được gửi ngay khi socket buffer available, giảm TTFB (Time-to-First-Byte) cho AI endpoint.
- 📱💻 **Binary UUID Mapping:** Mỗi stream session được gán `stream_uuid` (16 bytes binary). UUID này được đính kèm vào mỗi HTTP/2 DATA frame header — cho phép server-side AI corroborate file stream với request context.

### 8.12 Micro-Context Extraction & O-LLVM Scrubbing

- 📱💻 **Local Semantic Search (Cosine Similarity):** Trước khi gửi context cho AI Agent, Lõi Rust thực hiện local semantic search để trích xuất chỉ những đoạn chat liên quan nhất (top-K cosine similarity) thay vì dump toàn bộ lịch sử. Giảm 80-90% lượng data egress ra ngoài.
- 📱💻 **O-LLVM PII Redaction:** Sau khi trích xuất top-K context, O-LLVM obfuscation pass được áp dụng: (1) Micro-NER quét và mask PII, (2) Metadata header strip (timestamp, device_id, user_id được thay bằng hash), (3) Semantic-preserving paraphrase cho những câu chứa tên riêng không cần thiết.
- 📱💻 **`[REDACTED]` Tokenization:** Entities bị mask được thay bằng consistent token — cùng một entity sẽ có cùng token trong một session. Cho phép AI Agent maintain coherence trong ngữ cảnh mà không cần biết giá trị thực.

### 8.13 Abstracted RAG-Query API (SD-OAP Extension)

- 📱💻 **`terachat.agent.rag_query({ query: String, top_k: u32, scope: Scope })`** — FFI/JSI call từ `.tapp`. Lõi Rust thực hiện local ONNX embedding của query, tìm top-K vectors trong In-memory HNSW index, trả về `Vec<ChunkRef>` (UUID + score — không phải plaintext) về WASM sandbox.
- 📱💻 **Local-to-Remote Mapping Logic:** `.tapp` nhận `Vec<ChunkRef>`, quyết định fetch remote content (qua `stream_file_to_agent`) hay dùng chunk đã có trong context. Logic này chạy trong WASM — Rust Core không quan tâm đến business logic của AI agent.
- ☁️ **Egress Boundary Gatekeeping:** Nếu `.tapp` cố fetch remote chunk vượt quá `max_egress_mb` trong Manifest, OPA Policy block request và trả `EgressQuotaExceeded` error — không silent truncation.

### 8.14 Hybrid Sparse-Dense Indexing (HSDI)

- 📱💻 **SQLite FTS5 (BM25 — Sparse/Keyword):** Lõi Rust maintain FTS5 virtual table trong `hot_dag.db` cho keyword search (exact match, BM25 ranking). Query time < 5ms cho corpus 100K messages.
- 📱💻 **Lazy ONNX Reranking (`mlock`):** Keyword search results (top-50) được reranked bằng ONNX cross-encoder model. Lazy load — chỉ load model khi user thực sự kích hoạt RAG query. Model được `mlock` sau khi load để tránh swap.
- 📱💻 **In-memory Cosine Similarity (Flat/HNSW):** Dense semantic search chạy song song với BM25. Results được merge bằng RRF (Reciprocal Rank Fusion) trọng số: 60% Dense + 40% Sparse — balance giữa semantic precision và keyword recall.

### 8.15 Lifecycle-Bound Vector Eviction

- 📱💻 **Session-bound `ZeroizeOnDrop`:** Vector index được gắn với chat session lifecycle. Khi session `Session_UUID` kết thúc, toàn bộ vector arena liên quan bị `zeroize()` ngay lập tức — không delay, không lazy eviction.
- 📱💻 **Ephemeral RAM-only Indexing:** Index không bao giờ persist xuống disk trừ khi người dùng chủ động bấm "Save Semantic Index" (đòi hỏi Biometric auth). Xóa app → xóa hết vector embedding.
- 📱 **Android/iOS `onTrimMemory` Integration:** Khi OS gọi `onTrimMemory(TRIM_MEMORY_RUNNING_CRITICAL)` (Android) hoặc `applicationDidReceiveMemoryWarning` (iOS), Lõi Rust immediately chạy `evict_lru_vectors(keep_last_session=true)` — chỉ giữ lại vector của session hiện tại, evict tất cả cached sessions cũ.

### 8.16 WASM Output Typing & Taint Analysis Boundary

- 📱💻 **Strict `Vec<ASTNode>` FFI Typing:** Mọi output từ AI Agent pipeline truyền về UI phải có type `Vec<ASTNode>` (Protobuf-serialized). FFI bridge reject bất kỳ `String` hay `Bytes` raw nào — compile-time enforcement thông qua Rust's type system.
- 📱💻 **Tainted Agent Termination Logic:** Nếu SASB phát hiện node bị prune (XSS attempt) trong AI response, Lõi Rust đánh dấu session là `TAINTED`. `.tapp` nhận `AgentResponseTainted` error, UI hiển thị `Crimson warning badge` (§Section GSNI). Nếu taint count > 3 trong một session, `.tapp` bị suspend tự động.
- 📱💻 **SharedArrayBuffer Serialization:** Protobuf-encoded `Vec<ASTNode>` được ghi vào `SharedArrayBuffer` một lần duy nhất từ Lõi Rust. UI renderer đọc từ buffer này — zero deserialization overhead, zero string concatenation.

### 8.17 Protected Clipboard Bridge (PCB) & Re-encoding Buffer

> **Bài toán:** Người dùng copy plaintext E2EE từ TeraChat rồi paste vào ứng dụng khác (Gmail, Slack). Metadata ẩn trong clipboard (font style, hyperlink, device identifier) có thể rò rỉ thông tin ngoài ý muốn.

- 📱 **iOS `UIPasteboard` Interception:** Thay vì để OS copy trực tiếp vào `UIPasteboard`, Lõi Rust intercept thao tác copy qua JSI, strip toàn bộ rich-text metadata (RTF, HTML attributes, font info) và chỉ đặt vào pasteboard `plain-text` form của nội dung. Expiry time của item được set thành 60 giây — clipboard tự clear sau 1 phút.
- 📱 **Android `ClipboardManager` Sanitizer:** Trên Android, `ClipData` được reconstruct từ plain string sau khi strip metadata. Sử dụng Android 13+ sensitive content API để đánh dấu clip là "sensitive" — hệ thống ẩn nội dung khỏi recent clipboard suggestions của bàn phím.
- 📱💻 **Plaintext Re-serialization (Stripping Metadata):** Trước khi đưa vào clipboard, toàn bộ content được re-serialize qua `String::from_utf8_lossy()` Rust — loại bỏ invalid sequences, normalize whitespace, strip BOM. Kết quả là "bare text" không chứa steering metadata nào.

### 8.18 Steganography Detection — High-Entropy Segment Analysis

> **Bài toán:** AI Agent bị hack nhúng thông tin lấy cắp vào tin nhắn thông thường bằng steganography (VD: encode bit vào khoảng cách Unicode, punctuation pattern). Bộ lọc keyword-based không phát hiện được.

- 📱💻 **Character Frequency Distribution Check:** Lõi Rust scan mỗi tin nhắn đến từ External AI Agent: tính frequency distribution của các character class (printable ASCII, CJK, symbol, whitespace). Nếu distribution lệch quá nhiều so với baseline (>2 standard deviation) cho ngôn ngữ được phát hiện → flag `STEGO_SUSPECT`.
- 📱💻 **Local NER Context Matching:** Sau khi flag STEGO_SUSPECT, Lõi Rust chạy quick NER pass để kiểm tra xem nội dung văn bản (sau khi loại bỏ steganographic carrier) có coherent không. Nếu NER không phát hiện được entity nào (vô nghĩa về mặt ngôn ngữ) nhưng entropy vẫn cao → khả năng steganography rất cao.
- 📱💻 **Shannon Entropy Thresholding:** Tính Shannon Entropy `H(X) = -Σ p(x) log₂ p(x)` trên từng segment 64-byte của tin nhắn. Ngôn ngữ tự nhiên thường có entropy 3.5-5 bits/char. Nếu segment có entropy > 7.0 bits → khả năng chứa encoded binary payload → Lõi Rust quarantine segment, ghi alert vào Audit Log.

### 8.19 EICB — Edge Intent Classification Boundary (DeBERTa-v3-xsmall)

> **Bài toán:** Phân loại ý định độc hại (Social Engineering, Phishing, Money Transfer Manipulation) trong tin nhắn từ AI Agent với độ trễ thấp tại biên thiết bị.

- 📱💻 **ONNX Runtime INT8 (DeBERTa-v3-xsmall):** Sử dụng `DeBERTa-v3-xsmall` (22M params) quantized xuống INT8 (model size ~45MB). Inference time: < 80ms trên CPU mobile. Model được lazy-load vào `mlock` arena, chỉ khởi động khi EDES trigger threshold (≥ 2 borderline entities trong 5 tin nhắn).
- 📱💻 **Asynchronous NLP Inference Pipeline:** ONNX inference chạy trong thread riêng biệt (không block UI thread). Lõi Rust nhận kết quả qua async channel (`tokio::sync::oneshot`). Message được hiển thị lên UI trước với trạng thái "Đang kiểm tra...", sau khi inference hoàn thành mới unlock interaction.
- 📱💻 **Zero-shot Intent Scoring:** Model trả về confidence scores cho các category: `[SAFE, BORDERLINE, PHISHING, SOCIAL_ENGINEERING, MONEY_TRANSFER_MANIPULATION, CREDENTIAL_HARVESTING]`. Nếu bất kỳ harmful category nào > 0.75 → trigger SSA Retroactive Taint (§5.36 Core_Spec). Threshold có thể Admin-configure qua OPA Policy.

### 8.20 TTL-based Garbage Collection — Checkpoint Auto-Purge

- 📱💻 **Manifest-bound TTL (24h default):** Mỗi Checkpoint file được gắn TTL trong Manifest metadata. TTL default = 24 giờ từ thời điểm tạo, configurable bởi Admin (min 1h, max 7 ngày). Sau khi TTL hết, Checkpoint trở thành "garbage" và sẽ bị purged tại lần boot-time GC tiếp theo.
- 📱💻 **Boot-time Purge Logic:** Khi TeraChat khởi động, Lõi Rust chạy GC sweep qua directory Checkpoint: quét tất cả file có `creation_timestamp + TTL < now()`. File expired được crypto-shred (Hierarchical 3-pass — §5.35 Core_Spec). GC chạy trong background thread, không block app launch.
- 📱 **iOS/Android Cache Directory Placement:** Checkpoint file được lưu trong OS-managed Cache Directory (`NSCachesDirectory` trên iOS, `getCacheDir()` trên Android) — OS có quyền xóa khi low storage, thêm một lớp bảo vệ kép. Không được phép lưu trong Documents directory (user-accessible via Files app).

### 8.21 Epoch-bound Rolling Buffer — SSA Context Memory Management

- 📱💻 **ZeroizeOnDrop (RAII):** SSA Sliding Context Buffer (SCB) được implement dưới dạng RAII struct. Khi SSA session kết thúc hoặc conversation bị seal, RAII destructor tự động `zeroize()` toàn bộ SCB — không để lại plaintext hội thoại trong RAM sau khi seal.
- 📱💻 **2KB Rolling RAM Buffer:** Mỗi slot trong SCB chứa tối đa 2KB text (một tin nhắn bình thường). N=20 slots → tổng SCB size ≤ 40KB. Nếu tin nhắn > 2KB, chỉ lưu 2KB đầu tiên (sufficient cho semantic fingerprinting, không cần toàn văn để phát hiện pattern).
- 📱💻 **In-memory String Concatenation:** Khi ONNX inference được triggered, SCB được concatenate thành một string duy nhất trong `mlock` arena để chạy inference. Sau khi inference xong, concatenated string bị `zeroize()` ngay — không persist concatenated form lâu hơn thời gian inference.

### 8.22 FCP API — `terachat.agent.unrestricted_stream` & Non-Repudiation Binding

> **Điều kiện kích hoạt:** `.tapp` phải được Admin cấp quyền FCP (xem §5.37 Core_Spec và Function.md §13). API này không khả dụng ở default mode.

- 📱💻 **`terachat.agent.unrestricted_stream({ context_uuid: String, prompt: String })`:** API cấp cao bypass toàn bộ EDES/NER/O-LLVM pipeline. Lõi Rust truyền thẳng raw plaintext từ `mlock` arena → TLS stream → AI endpoint. Không có redaction, không delay cho NER processing. AI nhận 100% context nguyên bản.
- 📱💻 **Pre-call FCP Gate Check:** Trước khi execute, Lõi Rust verify: (1) `FCP_Enabled = true` trong OPA Policy của `.tapp`, (2) User consent modal đã được xác nhận trong session này (không thể bypass bằng code), (3) `Device_Ed25519_Signature` hiện tại hợp lệ. Bất kỳ check nào fail → return `FcpNotAuthorized` error, không rò rỉ byte.
- 🗄️ **Zero-Knowledge Non-Repudiation Log:** Mỗi lần gọi `unrestricted_stream`, Lõi Rust ghi vào SQLite WAL: `[FCP_TRIGGERED | UTC_Timestamp | BLAKE3(raw_payload) | Agent_Endpoint_Hash | Device_Ed25519_Signature]`. Không lưu nội dung Prompt. Log này là bằng chứng pháp lý: TeraChat có proof Admin đã authorize FCP — Liability Shift hoàn toàn sang phía khách hàng.

### 8.23 Xác thực Mật khẩu Bảo mật tại Biên (Argon2id Memory-Hardened Authentication)

- 📱💻 **Key Derivation Local (Không gọi Server):** Nhằm phục vụ PCAB (Privilege-Based Context-Aware Bypass), Lõi Rust sử dụng hệ thống Argon2id cục bộ. Thay vì đối soát Token trên đám mây, Rust áp đặt chi phí tính toán phần cứng (~500ms delay cost) ngay trên Mobile RAM + CPU để sinh KDF (Key Derivation Function) từ Password người dùng.
- 📱💻 Tấn công vét cạn (Brute-force) trực tiếp trên Client bị tiệt tiêu vì chi phí hàm băm bộ nhớ (Memory-Hardened). Mật khẩu hoàn toàn tàng hình; Output Argon2id lập tức được dùng làm khóa GCM Symmetric mở niêm phong Document/Agent Quarantine Vault, sau đó `ZeroizeOnDrop` thả rơi. Hệ thống cấm lưu trữ KDF Hash trên thiết bị.

### 8.24 Cách ly nhị phân trong RAM (Ephemeral RAM-only Quarantine Sandbox)

- 💻📱 Lõi Rust từ chối tải file nghi nhiễm mã độc (Weaponized Files) lên ổ cứng vật lý (SSD/NAND Flash). Thay vì thế, luồng Bypass định tuyến thẳng tệp tin vào một vùng **Virtual RAM-FS (mlock)** / Ephemeral Buffer tạm bay hơi.
- 💻📱 **WASM Sandbox Isolation:** Tại Buffer lưu vong này, môi trường WASM phi trạng thái sẽ mở tệp tin ra đọc. Cơ chế Zero-copy I/O Prevention bị kích hoạt: File không bao giờ sở hữu địa chỉ I/O, OS không nhìn thấy File Descriptor (`/proc/fd`), do đó mọi lỗ hổng leo thang đặc quyền đường dẫn (Path Traversal) đối với hệ điều hành Host là vô dụng.

### 8.25 Cầu nối Kết cấu Dữ liệu Định dạng (Structured Data-to-Native Document FFI)

- 📱💻 Tính năng Tái dựng Nội dung an toàn thay thế (Safe-Rust CDR). Khi File đã được cô lập (Quarantine), Lõi Rust cần đưa nội dung sạch ra UI Màn hình. Việc xuất trả một file PDF hoặc DOCX hoàn chỉnh sau khử độc chứa đựng rủi ro bypass luồng C-parser của OS.
- 📱💻 **Hàm FFI `terachat.fs.safe_reconstruct`:** Giao thức Native (Swift/Kotlin) gọi xuống Rust. Rust biên dịch cấu trúc văn bản PDF/DOCX sang định dạng Markdown cấp thấp hoặc JSON Schema ngặt nghèo (Text + Bounding Boxes + Link).
- 📱💻 **Host-Side Generator:** App React Native / Tauri nhận JSON Schema này và **tự phục hồi giao diện khung hình Text Renderer** hoàn toàn chủ động, từ chối tải thư viện PDF Native Component hoặc WebView iFrame. UI Native Reader an toàn tuyệt đối, triệt tiêu viễn cảnh click zero-day iframe.

### 9.1 Unidirectional Federated State Sync

- 📱💻🖥️ **Unidirectional State Sync (StateChanged Signal):** Bắn tín hiệu `StateChanged(table, version)` qua IPC để UI chủ động kéo snapshot thay vì Rust đẩy JSON cục bộ — tránh tình trạng treo thread do push data lớn từ các cụm Federation.
- 📱💻🖥️ **IPC Bridge Zero-Copy (~500MB/s):** Sử dụng JSI C++ Shared Memory (iOS) hoặc `SharedArrayBuffer` (Desktop) đạt tốc độ ~500MB/s cho các payload lớn — đảm bảo không có bottleneck khi đồng bộ trạng thái liên cụm.
- 📱💻🖥️ **Lazy UI Hydration (Sliding Window):** Giới hạn việc nạp dữ liệu trong viewport hiện tại (20 tin nhắn gần nhất); phần còn lại tải qua Infinite Scroll — giảm thiểu RAM footprint khi nhận tin nhắn batch từ Federation.

### 9.2 Zero-Knowledge Push Notification & JIT Decryption

- 📱 **Notification Service Extension (NSE — iOS):** Sử dụng `UNNotificationServiceExtension` + `mutable-content: 1` để đánh thức tiến trình con xử lý ciphertext mà không hiển thị trực tiếp Plaintext lên hệ điều hành.
- 📱 **Data Messages (Android):** FCM Data Message → `FirebaseMessagingService` → giải mã Rust FFI trong tiến trình con cô lập, không để APNs/FCM server thấy nội dung thông báo.
- 📱 **Micro-Crypto Build Target (`terachat-nse-core.a`):** Xây dựng bản build Rust thu gọn (stripped-down) tước bỏ toàn bộ WASM Runtime, TEE AI, và Mesh Networking. Nhiệm vụ duy nhất là nhận Ciphertext từ APNs, đọc `DeviceIdentityKey` từ Keychain (không dùng Secure Enclave ở background để tránh timeout), và giải mã bằng X25519/Kyber768.
- 📱 **Static Memory Arena (10MB Limit):** Lõi Micro-Crypto thay vì cấp phát Heap (`malloc`), khởi tạo sẵn một Static Memory Arena 10MB ngay khi NSE khởi động. Toàn bộ quá trình giải mã chỉ tái sử dụng buffer trong vùng 10MB này để đảm bảo an toàn bộ nhớ.
- 📱 **Latency & Execution Constraint:** Tối ưu hóa vi kiến trúc để đảm bảo thời gian giải mã một tin nhắn MLS dưới 50ms, tuyệt đối tránh vi phạm thời gian sống tối đa 30 giây của tiến trình iOS NSE.
- 📱☁️ **Blind Payload Architecture (CBOR + Dummy Alert):** Sử dụng ciphertext nén bằng chuẩn CBOR kết hợp chuỗi Dummy Alert tĩnh để ngăn chặn Apple/Google thu thập Business Intelligence từ nội dung thông báo.
- 📱 **ZeroizeOnDrop sau NSE:** Thực thi ghi đè `0x00` xóa sạch plaintext khỏi RAM ngay sau khi trả kết quả thông báo cho Native OS — không có window nào để key hay plaintext bị trích xuất.

### 9.3 Client-Side Dual-Mask Protocol (Dynamic PII Tokenization)

- 📱💻🖥️ **Local NER (Platform-Agnostic Inference Adapter):**
  - > **Attack Surface (Trước):** Chạy WASM/ONNX trên iOS tốn gấp 3-4x RAM so với NPU, Apple chặn JIT-compiled WASM → hiệu năng thảm hại + nguy cơ OOM Kill.
  - > **Attack Surface (Sau):** FFI chọn inference engine đúng OS; Rust Core chỉ thấy kết quả `Vec<Entity>`.
  - 💻🖥️ **Desktop/Android:** Giữ nguyên `ONNX/WASM (<10MB)` — chạy qua WASM3 AOT, không JIT.
  - 📱 **iOS:** Gọi FFI ra `CoreML` — tận dụng Neural Engine (ANE/NPU) phần cứng, tránh hoàn toàn JIT block của Apple. Model `NER.mlpackage` được đóng gói sẵn trong app bundle, không tải từ mạng (pass App Review Rule 2.5.2).
  - 📱 **Android:** Gọi FFI ra `NNAPI` (Android Neural Networks API) để tận dụng NPU/DSP tương đương, tiết kiệm 60-70% RAM so với CPU WASM.
- 📱💻🖥️ **Entity Mapping Table (RAM-only):** Lưu trữ tạm thời trên RAM (mlock'd) để ánh xạ dữ liệu thật sang Token giả mạo (`[REDACTED_PHONE_1]`, `[REDACTED_EMAIL_2]`) — bảo toàn cấu trúc câu cho AI mà không để lộ PII.
- 📱💻🖥️ **ZeroizeOnDrop (RAII):** Thực thi ghi đè `0x00` tiêu hủy Entity Mapping Table ngay sau khi quá trình De-tokenization hoàn tất; Session Vault tồn tại trong RAM duy nhất cho 1 request.

### 9.4 LLM Iron Dome & Markdown AST Sanitizer (Mở rộng)

- 📱💻🖥️ **Markdown AST Sanitizer (Chống Pixel Tracking):** Chặn đứng các thẻ `<img src="...">` hoặc liên kết `![alt](external_url)` trỏ tới URL bên ngoài; chỉ cho phép hiển thị nội dung từ Local VFS (`localhost` hoặc base64 nội bộ).
- 📱💻🖥️ **Egress Firewall (WASM Sandbox Whitelist):** Giới hạn kết nối mạng của WASM Sandbox chỉ đến các Whitelist Domains đã được phê duyệt bởi Admin qua OPA Policy — ngăn chặn data exfiltration qua markdown content.
- 💻🖥️ **Local Semantic Guardrail (NLP nội bộ):** Sử dụng mô hình NLP ONNX tại biên để kiểm soát và chặn các mẫu System Instruction Spoofing, Jailbreak Pattern trước khi gửi đến LLM — bảo vệ khỏi Prompt Injection nâng cao.

### 9.5 State Machine cho Offline Survival & Bảo vệ dữ liệu RAM (mlock)

- 📱💻 **State 1 (Disconnected):** Ngắt IPC Socket tới Server.
- 📱💻 **State 2 (Prompting):** UI gọi hàm FFI/JSI `request_mesh_activation()`.
- 📱💻 **State 3 (Mesh Active):** Sau khi User đồng ý (nhấn nút), Lõi Rust gọi API Native OS (`CoreBluetooth` trên iOS / `WifiP2PManager` trên Android) để bắt đầu Broadcasting.
- 📱💻🖥️ **Bảo vệ dữ liệu RAM (mlock):** Dù ở Mesh Mode, `Epoch_Key` vẫn bị khóa chặt trong RAM bằng lệnh `mlock()`. Nếu thiết bị tắt nguồn (sập pin/bị đập nát), khóa bay màu ngay lập tức để chống Memory Dump.

#### Hybrid Mesh Bonding — Demux Control/Data Plane

> **Giải pháp cho băng thông BLE bị giới hạn 2Mbps:** Lõi Rust tự động tách luồng (Demultiplexing) lưu lượng theo loại payload — BLE chỉ carry Control Plane nhẹ, Data Plane lớn được giao cho AWDL/Wi-Fi Direct.

```text
Hybrid Mesh Bonding — Dual-Path Architecture
├── Control Plane (BFT Delta-State, Ed25519 Sigs, Key Updates)
│       └──▶ BLE 5.0 (Latency ~50ms, Low Power, Xuyên tường)
└── Data Plane (File Media, DB Hydration, Embedding Sync)
        ├──▶ Apple AWDL (iOS / macOS) — ~250Mbps peer-to-peer
        └──▶ Wi-Fi Direct (Android / Desktop) — ~250-500Mbps
```

- 📱 **iOS: Apple AWDL (Apple Wireless Direct Link):** Khi cần truyền file lớn hoặc DB Hydration, Lõi Rust kích hoạt `MultipeerConnectivity` framework gọi AWDL — tốc độ ~250Mbps qua Wi-Fi 802.11ac mà không cần Router. BLE vẫn carry Control heartbeat song song.
- 📱 **Android: Wi-Fi Direct (WifiP2PManager):** Android counterpart: `WifiP2PManager.createGroup()` tạo nhóm P2P. Data Plane transfer qua Socket TCP trên Wi-Fi Direct link (~250-500Mbps). BLE duy trì discovery và Control Plane.
- 💻 **macOS: AWDL (Multipeer)** / 🖥️ **Desktop: Wi-Fi Direct (wpa_supplicant P2P mode):** Desktop sử dụng Wi-Fi Direct tương tự Android. Control Plane qua BLE Peripheral mode trên USB Bluetooth Dongle nếu built-in BLE không hỗ trợ.
- 📱💻 **Demux Logic tại Lõi Rust:** `fn route_payload(payload: &Payload) -> Transport`: nếu `payload.size < 4KB && payload.type == ControlMsg` → BLE; nếu `payload.size >= 4KB || payload.type == DataBlob` → AWDL/Wi-Fi Direct. Quyết định routing < 1µs (enum dispatch).
- 📱💻 **Throughput Benchmark:** Control Plane BLE: ~50ms latency, tiêu thụ < 15mW. Data Plane AWDL/Wi-Fi Direct: ~250–500Mbps throughput, SLA file 100MB < 2 giây.

#### SQLite WAL Auto-Compaction (Background VACUUM)

> **Chặn hiện tượng WAL Bloat:** `hot_dag.db` phình to theo thời gian do Tombstones và MVCC versions tích lũy.

- 📱 **iOS BGTask + Android WorkManager:** Đăng ký Background Job `tera_vacuum_job` chạy khi thiết bị **cắm sạc + màn hình tắt**. Job gọi `PRAGMA wal_checkpoint(TRUNCATE)` để flush WAL về main db, sau đó chạy `VACUUM` để defragment.
- 📱💻🖥️ **Size Trigger (Adaptive):** Auto-VACUUM kích hoạt nếu WAL file vượt **50MB** (Mobile) / **200MB** (Desktop). Không chạy nếu pin < 20% (Mobile) — tránh drain pin.
- 📱💻🖥️ **Zero-Downtime Vacuum:** SQLite `VACUUM INTO 'hot_dag_tmp.db'` — tạo bản sạch mới rồi atomic rename — không block read/write của Lõi Rust trong quá trình VACUUM. Sau rename, xóa file cũ.
- 🗄️☁️ **Server VACUUM Schedule:** Server node chạy cron job `0 3 * * *` (3AM) thực hiện `VACUUM ANALYZE` trên PostgreSQL và `wal_checkpoint(TRUNCATE)` trên SQLite history log. `pg_dump` incremental backup trước khi VACUUM để đảm bảo PITR.



### 9.6 Trạng thái Mạng chập chờn (Intermittent Network State Machine)

- 📱💻 Thay vì chỉ có On/Off, hệ thống áp dụng trạng thái **Zombie_Sync**. Nếu Sếp ở TH1 vừa dùng YubiKey khôi phục máy tính mới, thiết bị sẽ chuyển sang chế độ gom nhặt dữ liệu (Hydration) theo từng khối (Chunk) nhỏ qua BLE từ các nhân viên đi cùng, hoặc bắt từng nhịp sóng Wi-Fi yếu để kéo `hot_dag.db` về mà không làm hỏng file.

### 9.7 Khôi phục Định danh qua Admin-approved QR Key Exchange

- 📱💻 **Admin-approved QR Key Exchange:** Admin xác thực Biometric trên thiết bị của chính mình, tạo mã QR mã hóa (Ed25519 Signed Recovery Ticket). Người dùng quét QR bằng thiết bị mới — không cần phần cứng ngoại vi.
- 📱 **Lõi Rust xác minh Signed Ticket:** Lõi Rust trên thiết bị mới kiểm tra chữ ký Ed25519 của Recovery Ticket trước khi giải mã `cold_state.db` tải về từ Cloud — chống Recovery Ticket giả mạo.
- 💻 **Fallback: Recovery Phrase (BIP-39):** Nếu không tiếp cận được Admin, nhập 24-word Mnemonic + Biometric để tự khôi phục cục bộ mà không cần Server.

### 9.8 Xung đột Đứt gãy Liên hợp (Federation Mismatch) và Tấn công Brute-force Từ xa

> **Bài toán:** Khác biệt phiên bản Schema giữa các Node liên hợp hoặc Brute-Force vào kết nối Mesh.

- ☁️ **Module PDU Adapter:** Triển khai Module PDU Adapter tự động giáng cấp/nâng cấp (Downgrade/Upgrade) schema v1 sang v2 trong Grace Period để đảm bảo tương thích chéo mà không làm vỡ Data Plane.
- 📱 **Physical Lockout State Machine:** Kích hoạt State Machine `LOCKED_PHYSICAL_AUTH` sau 5 lần thất bại xác thực liên hợp hoặc Mesh, kích nổ `ZeroizeOnDrop` xóa trắng Key Cache trên thiết bị.
- 💻 **In-Person Recovery (Cross-signing):** Cưỡng ép Cross-signing ngoại tuyến (In-Person Recovery) qua QR/NFC yêu cầu Admin sử dụng `Admin Private Key` để chứng thực mới cho phép tái hòa nhập mạng lưới.

### 9.9 Chặn luồng Cấp phát (Blocking Latency) và OOM trên Mobile (Tiered Memory Pre-fetching)

> **Bài toán:** Nạp khối dữ liệu lớn cùng lúc dùng `MAP_POPULATE` có thể kích nổ OOM-Kill trên Mobile do mồi chủ động nạp toàn bộ Page vào RAM trước khi cần.

- 💻🖥️🗄️☁️ **`mmap()` + `madvise(MADV_WILLNEED)` (Background Thread):** Gọi `mmap()` không cờ `MAP_POPULATE` kết hợp `madvise(MADV_WILLNEED)` trên Background Kernel Thread — OS nạp page đún trước tiêu thụ mà không chặn luồng chính.
- 📱 **Vector Embeddings Chunked Streaming (5MB):** Chia nhỏ luồng Vector Embeddings thành các khối 5MB trước khi đẩy qua JSI Native Pointer. Lõi Rust chỉ giữ tối đa 2 khối trong RAM tại bất kỳ thời điểm nào.
- 📱 **LRU Cache + `munmap()` Chủ động:** Thuật toán LRU Cache giám sát mức sử dụng; khi Resident Set vượt 10MB, tự động gọi `munmap()` giải phóng trang nhớ Stale nhất — giữ footprint dẹt liên tục.

### 9.10 Tránh Treo luồng / Infinite Spin-lock (WASM Isolate Guillotine)

> **Bài toán:** IPC Call từ `.tapp` độc hại có thể Spin vĩnh viễn bên trong Sandbox, tinh tạo Deadlock mềm (Soft Deadlock) lập tức thâu tóm toàn bộ CPU time.

- 📱 **Timer Guardrail 50ms cho IPC Call:** Mọi IPC Call từ Sandbox bị giới hạn cứng 50ms. Vượt ngưỡng → Lõi Rust gửi tín hiệu Kill ngay lập tức.
- 🖥️ **`v8::Isolate::TerminateExecution()` / `Worker.terminate()` (Desktop/Mobile):** Desktop kích hoạt `v8::Isolate::TerminateExecution()` — Mobile kích hoạt `Worker.terminate()` — chấm dứt ngay lập tức mà không chờ Cooperative Yield.
- ☁️ **Crypto-Shredding Linear Memory sau Kill:** Ngay khi Kill, Lõi Rust thực thi `ZeroizeOnDrop` xóa sạch toàn bộ Linear Memory của Sandbox — không để lại bất kỳ dấu vết plaintext hay pointer rác.

### 9.11 Truy xuất Dữ liệu An toàn trong WASM Sandbox (Generational Handle Validation)

> **Bài toán:** Con trỏ WASM trỏ vào Slot bộ nhớ đã tái cấp phát dẫn đến Use-After-Free.

- 📱 **Fat Pointer `struct Handle { slot_index, generation }`:** Mọi tham chiếu bộ nhớ trong Sandbox phải mang cấu trúc Fat Pointer; `generation` xác nhận slot chưa bị tái cấp phát.
- 💻 **Kiểm tra `Header.generation == expected_generation`:** Trước mỗi chu kỳ đọc, WASM Reader so sánh `Handle.generation` với `Header.generation` trong Shared Slot; lệch pha → Read bị từ chối ngay lập tức.
- 🖥️ **`StalePointerError` + OPA IPC Guardrail:** Phát hiện lệch pha thế hệ → Throw `StalePointerError` → Buộc Sandbox tái cấp phát qua OPA IPC Guardrail trước khi tiếp nhiệm Handle mới.

### 9.12 Client-Driven Merkle DAG Reconciliation (Chống Rogue Server)

> **Bài toán:** Nội gián thiết lập máy chủ giả mạo có thể phá vỡ cây DAG và phân phối Delta-State nhồi độc.

- 📱 **BLAKE3 Segmented Merkle Tree trên `hot_dag.db`:** Mọi DAG Node được nhúc vào cây BLAKE3 Merkle — Root_Hash là fingerprint bất biến của toàn bộ trạng thái local của Client.
- 💻 **Ed25519 Signature trên mỗi Delta-State CRDT Node:** Mọi Delta-State tải về bắt buộc mang chữ ký Ed25519 của `DeviceIdentityKey` người gửi; từ chối mọi Node có chữ ký không hợp lệ.
- 🖥️ **Zero-Trust Handshake + Root_Hash Reconciliation:** Trước mọi phiên Sync, Client đối chiếu `Root_Hash` với Quorum Peers qua Gossip — nếu Root_Hash Server trả về lệch Quorum → Circuit Breaker cắt kết nối.

### 9.13 Tấn công Nhật thực (Eclipse Attack) — Cross-Client Gossip Protocol

> **Bài toán:** Server độc hại kiểm soát toàn bộ kết nối của một Client, chặn đứng hoàn toàn luồng tin tức thực (Eclipse Attack).

- 📱 **BLE 5.0 Advertising Packets (Merkle Root Hash):** Thiết bị phát quảng bá Merkle Root Hash của trạng thái DAG hiện tại qua BLE 5.0 Advertising Packet chính xác — Peer lân cận nhận ra ngay khi Root Hash lệch.
- 💻 **Apple Wireless Direct Link (AWDL) Out-of-Band Sync:** Trên iOS/macOS, dùng AWDL để đối soát ngoài băng tần với các Client lận cận mà không cần qua kết nối Wi-Fi router thông thường.
- ☁️ **Phân tích độ lệch thực tại (`Latest_HLC_Timestamp`):** So sánh HLC Timestamp giữa Peer và Server; lệch > 3 Epoch → tự động cảnh báo Eclipse Attack và chuyển sang Pure Mesh Mode.
