# Feature_Spec.md — TeraChat V0.2.2

> **Audience:** App Dev Mobile/Desktop/Laptop · FFI Integrator
> **Scope:** Client Data Plane, IPC, Local Storage, Native OS, WASM Ecosystem — Implementation-level only.

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

#### Split-Payload Pipeline (Chống Trễ IPC và Rớt khung hình)

- 📱💻🖥️ **Skeleton Extraction:** Giới hạn lượng dữ liệu hiển thị trích xuất chỉ ~10KB (gồm `message_id`, `text_preview`) để bảo đảm ngân sách thời gian xử lý chặn ở mức $16\text{ms}$, duy trì tốc độ 60/120fps.
- 📱💻🖥️ **Phân tách rạch ròi:** Quy hoạch Control Plane và Data Plane độc lập qua schema `terachat_ipc.proto`.
- 📱💻🖥️ **Unidirectional State Sync:** Giao diện UI chủ động kéo (pull) snapshot trạng thái thay vì hứng JSON đẩy (push) trực tiếp mệt mỏi từ Lõi.

#### Truyền tải Vector Embedding (Background Zero-Copy Memory Pumping)

- 📱 **JSI C++ Native Pointer (iOS):** Bắn thẳng con trỏ bộ nhớ vật lý chứa 3MB Vector Embeddings vào Background Thread xuyên qua JSI, bypass hoàn toàn cổ chai Bridge của React Native.
- 💻🖥️ **SharedArrayBuffer (Desktop/Web):** Sử dụng `mmap` vật lý cho phép hệ Web Worker truy cập Zero-copy trực diện vào kho dữ liệu 3MB.
- 📱💻🖥️ **Cô lập tác vụ AI:** Điều hướng Web Worker / Dart Isolate gánh vác các phép toán Vector ngoài luồng Main Thread để chống đóng băng UI giao diện.

#### Desktop — SharedArrayBuffer + Protobuf

- 💻🖥️ **Control Plane:** Protobuf schema `terachat_ipc.proto` qua WASM/Rust channel — lệnh, metadata, SQL, offset pointer. Kích thước \<50 bytes/message.
- 💻🖥️ **Data Plane:** `SharedArrayBuffer` (mmap vật lý) — file chunk, record bulk, AI input. Ring Buffer cố định 10MB, chunk 2MB, throughput ~500MB/s.
- 💻🖥️ **Zero-Copy Flow:** WASM ghi I/O nhị phân vào SAB → Rust đọc con trỏ vật lý, validate CRC32, AES-256-GCM encrypt → ghi ciphertext vào offset khác trong SAB → WASM lấy kết quả. Không copy buffer.
- 💻🖥️ **Security Contract:**
  - ACL per-.tapp: mọi `UtilityAction` qua ACL Policy tại Rust Core trước khi xử lý.
  - `Company_Key` / `Channel_Key` tuyệt đối không truyền qua Protobuf lên WASM. WASM chỉ gửi data vào SAB, Rust tự dùng Key đang `mlock`'d.
  - Rust kiểm tra `offset + length ≤ SAB_SIZE` + validate CRC32. Vi phạm → `SIGSEGV` trap + panic.

#### Custom URI Protocol Interceptor & Security Header Injection (Tê liệt SharedArrayBuffer)

- 💻🖥️ Can thiệp trực tiếp vào Tauri Builder Protocol Interceptor để kiểm soát luồng phản hồi phân phối tĩnh cục bộ.
- 💻🖥️ Tiêm (Inject) cưỡng bức Header `Cross-Origin-Opener-Policy: same-origin` ngay tại cấp độ mạng của WebView.
- 💻🖥️ Tiêm Header `Cross-Origin-Embedder-Policy: require-corp` để kích hoạt trạng thái Cross-Origin Isolation, cho mượn SharedArrayBuffer.

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

#### Dual-Plane

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

---

### 6.13 Zero-Knowledge Snapshot Sync — Cold State Bootstrapping (Chống Lạc trôi Nhân quả & Orphan DAG)

> **Bài toán:** Thiết bị offline dài ngày sẽ có DAG lỗi thời (hàng nghìn event sau Causal Stability Frontier). Replay toàn bộ event log tốn RAM và thời gian $O(N)$ — không khả thi trên Mobile. Cold State Bootstrap giải quyết bằng $O(1)$ từ Snapshot.

- 📱💻 **Final Materialized State Snapshot (Squashed Event Logs):** Server hoặc Super Node định kỳ xuất **Snapshot** — bản chụp `cold_state.db` tại thời điểm Causal Stability Frontier — không chứa CRDT event thô, chỉ chứa final materialized state của từng entity. Thiết bị reconnect tải Snapshot thay vì replay toàn bộ log.
- 📱💻 **TeraVault VFS (Content-Addressable Storage / CAS UUID):** Mỗi Snapshot được định danh bằng `CAS_UUID = SHA-256(snapshot_content)` và lưu trong TeraVault VFS. Thiết bị chỉ cần verify hash để xác nhận tính toàn vẹn mà không cần tải lại nếu đã có local cache trùng UUID.
- ☁️📱💻🖥️ **Epoch-Keyed Parquet/SQLite Backups:** Snapshot được export theo định dạng Parquet (lớn, dành cho Desktop/Server) hoặc SQLite (compact, dành cho Mobile), đặt tên theo `epoch_N.snapshot`. Thiết bị chỉ tải `epoch_current.snapshot` → bỏ qua toàn bộ intermediate history.
- 📱💻🖥️ **Độ phức tạp Phục hồi $O(1)$:** Sau khi tải Snapshot, Lõi Rust ghi trực tiếp vào `cold_state.db` qua `INSERT OR REPLACE` trong một transaction duy nhất. Tổng thời gian bootstrap cố định bất kể số lượng event lịch sử.

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

### 6.2 Local Storage & State Sync

#### SQLite WAL + Sliding Window

- 📱💻🖥️ Bắt buộc chế độ **WAL (Write-Ahead Logging)** cho mọi SQLite instance. Không gọi `VACUUM` (rủi ro Corrupt trên Mobile Doze/Jetsam).
- 📱 **Mobile Window:** 7 ngày hoặc 2.000 tin nhắn gần nhất (Cold Data nằm trên Cluster).
- 💻🖥️ **Desktop Window:** 30 ngày hoặc 10.000 tin nhắn gần nhất.
- ☁️ **Cold Data:** Fetch on-demand khi user cuộn lên hoặc tìm kiếm \>30 ngày.

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

- 📱 **Pha 1 — Write (NSE, realtime):** Khởi chạy Rust Core Lightweight Mode (chỉ nạp module Cryptography) để kìm hãm RAM footprint < 10MB dưới ngưỡng an toàn NSE. Chỉ ghi Blob vào `inbox.sqlite` với `is_indexed = false`. Tuyệt đối không gọi bất kỳ FTS5 API nào.
- 📱 **Pha 2 — Index (Main App, deferred):** Thiết lập cơ chế Shared App Group đồng bộ SQLite giữa NSE và Main App. Gán cờ `is_vectorized` đánh dấu dữ liệu chờ AI. Lắng nghe trigger `BGProcessingTask` để batch-index âm thầm khi thiết bị idle, với Circuit Breaker tự `Suspend()` khi RAM > 80%.

#### Inbox Queue Architecture (Kiến trúc Hộp thư đến tách biệt)

- 📱 Khởi tạo cơ sở dữ liệu phụ `inbox.sqlite` dạng Append-Only nhằm cô lập tuyệt đối luồng ghi của tiến trình NSE hạn hẹp.
- 📱 Tận dụng Shared App Group để thiết lập vùng đệm dữ liệu trung gian giữa Extension Service và hệ quản trị Main App.
- 📱 Áp dụng cơ chế Consumer Pattern tại Main App để hút và đồng bộ triệt để khối dữ liệu vào `main.sqlite` ngay khi ứng dụng mở lại ở Foreground.

#### Android — Xử lý Doze / WorkManager

- 📱 **FTS5 Indexing:** Batch nhỏ, chỉ khi App Active. Index Window: 30 ngày. Tìm kiếm cũ hơn → Encrypted Blind Search (giống iOS).
- 📱 **Background Delegate:** Giao URL cho `WorkManager` (Android, `NetworkType.UNMETERED`) — OS tự tải lúc cắm sạc/Wi-Fi mạnh.
- 📱 **Wake-and-Strip:** Rust `mmap` + ARM NEON giải mã, `unlink` file tạm; Hard Deadline \<3 giây (tránh vi phạm Background Time Limit).
- 📱 **StrongBox Keymaster:** Lưu Symmetric Push Key (FCM). Key sinh trong chip, không export.

### 6.5 Lean Edge Caching

#### Mesh-Aware Radar Pulse Visualization (Trực quan hóa Trạng thái Mesh)

- 📱 **Radar Pulse Scan:** Hiệu ứng Radar Pulse màu `#0F172A` quét từ dưới lên trên UI, báo hiệu trực quan cho người dùng rằng dữ liệu đang được đồng bộ hóa từ mạng lưới P2P/Offline Mesh thay vì Cloud.
- 📱💻🖥️ **Control Plane Signals (`StateChanged`):** Lõi Rust áp dụng Unidirectional State Sync, chỉ bắn tín hiệu `StateChanged` qua IPC thay vì đẩy toàn bộ cục JSON cồng kềnh. Giao diện (Renderer) sẽ tự động trigger fetch phần dữ liệu thay đổi để giữ độ mượt mà tuyệt đối.
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

#### AI Consent / Opt-in (Bắt buộc)

- Mọi lần AI truy cập dữ liệu ghi vào **Tamper-Proof Audit Log**.
- AI không bao giờ có thể truy cập `Channel_Key` hay `Company_Key` — chỉ nhận alias đã tokenized.

---

*Tài liệu này chỉ chứa App-layer implementation. Xem `Core_Spec.md` cho Infrastructure/Security. Xem `Function.md` cho Product flows.*

---

## 8. Large File Handling & Advanced Sync

### 8.1 Xử lý File Khổng lồ — mmap + BLAKE3 Segmented Merkle + Native-to-Rust Media DataSource Bridge

#### Zero-Copy I/O qua Virtual Memory (mmap)

- 📱💻🖥️ Lõi Rust gọi `mmap()` ánh xạ file vật lý trực tiếp lên vùng nhớ ảo. Page Fault nạp từng mảnh on-demand — không dùng `read/write` qua vRAM Buffer. RAM footprint < 10MB bất kể file nặng hàng GB.
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
- 📱💻🖥️ Triển khai JIT (Just-In-Time) Fetching nhằm cơ động tải trực giác đúng Chunk cần thiết dựa trên vị trí Byte Offset của thanh tiến trình (Seek bar); mọi plaintext trong Ring Buffer được đánh dấu `ZeroizeOnDrop`/RAII và Memory Footprint giữ ổn định < 8MB bất kể file gốc hàng GB.
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

---

## 9. Federation Client Sync & Privacy Pipeline

### 9.1 Unidirectional Federated State Sync

- 📱💻🖥️ **Unidirectional State Sync (StateChanged Signal):** Bắn tín hiệu `StateChanged(table, version)` qua IPC để UI chủ động kéo snapshot thay vì Rust đẩy JSON cục bộ — tránh tình trạng treo thread do push data lớn từ các cụm Federation.
- 📱💻🖥️ **IPC Bridge Zero-Copy (~500MB/s):** Sử dụng JSI C++ Shared Memory (iOS) hoặc `SharedArrayBuffer` (Desktop) đạt tốc độ ~500MB/s cho các payload lớn — đảm bảo không có bottleneck khi đồng bộ trạng thái liên cụm.
- 📱💻🖥️ **Lazy UI Hydration (Sliding Window):** Giới hạn việc nạp dữ liệu trong viewport hiện tại (20 tin nhắn gần nhất); phần còn lại tải qua Infinite Scroll — giảm thiểu RAM footprint khi nhận tin nhắn batch từ Federation.

### 9.2 Zero-Knowledge Push Notification & JIT Decryption

- 📱 **Notification Service Extension (NSE — iOS):** Sử dụng `UNNotificationServiceExtension` + `mutable-content: 1` để đánh thức tiến trình con xử lý ciphertext mà không hiển thị trực tiếp Plaintext lên hệ điều hành.
- 📱 **Data Messages (Android):** FCM Data Message → `FirebaseMessagingService` → giải mã Rust FFI trong tiến trình con cô lập, không để APNs/FCM server thấy nội dung thông báo.
- 📱 **Micro-Crypto Build Target (Rust FFI ~4MB):** Loại bỏ các module nặng (MLS full, CRDT Automerge, SQLCipher) khỏi NSE build — chỉ giữ AES-256-GCM decrypt + Shared Keychain read; duy trì footprint ~4MB dưới ngưỡng 24MB giới hạn của iOS NSE.
- 📱☁️ **Blind Payload Architecture (CBOR + Dummy Alert):** Sử dụng ciphertext nén bằng chuẩn CBOR kết hợp chuỗi Dummy Alert tĩnh để ngăn chặn Apple/Google thu thập Business Intelligence từ nội dung thông báo.
- 📱 **ZeroizeOnDrop sau NSE:** Thực thi ghi đè `0x00` xóa sạch plaintext khỏi RAM ngay sau khi trả kết quả thông báo cho Native OS — không có window nào để key hay plaintext bị trích xuất.

### 9.3 Client-Side Dual-Mask Protocol (Dynamic PII Tokenization)

- 📱💻🖥️ **Local NER (ONNX/WASM < 10MB):** Sử dụng mô hình NLP ONNX/WASM siêu nhẹ (< 10MB) thực thi trực tiếp tại biên thiết bị để nhận diện thực thể nhạy cảm (PII/PCI/PHI) trước khi gửi Prompt lên AI.
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

### 9.6 Trạng thái Mạng chập chờn (Intermittent Network State Machine)

- 📱💻 Thay vì chỉ có On/Off, hệ thống áp dụng trạng thái **Zombie_Sync**. Nếu Sếp ở TH1 vừa dùng YubiKey khôi phục máy tính mới, thiết bị sẽ chuyển sang chế độ gom nhặt dữ liệu (Hydration) theo từng khối (Chunk) nhỏ qua BLE từ các nhân viên đi cùng, hoặc bắt từng nhịp sóng Wi-Fi yếu để kéo `hot_dag.db` về mà không làm hỏng file.

### 9.7 NFC Ring Khôi phục Mobile

- 📱 Thiết bị Mobile không có cổng USB-A, hệ thống sử dụng module Native OS (`CoreNFC` trên iOS, `NfcAdapter` trên Android) để đọc ISO 7816 Smart Card Applet từ NFC Ring.
