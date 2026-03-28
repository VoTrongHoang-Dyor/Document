# Function.md — TeraChat Function & Capability Blueprint

```yaml
# DOCUMENT IDENTITY
id: "TERA-FUNC"
title: "TeraChat — Enterprise Function & Capability Blueprint"
version: "1.2.0"
status: "ACTIVE"
date: "2026-03-25"
audience: "Product Manager, Enterprise Sales, Solution Architect, C-Suite, Investor"
purpose: "Mô tả toàn bộ năng lực chức năng của TeraChat từ góc độ doanh nghiệp: access model, modules, enterprise controls, và giá trị kinh doanh."

ai_routing_hint: |
  "Mở file này khi hỏi về TeraChat làm được gì, role-based permissions,
   enterprise business flows, AI integration, federation, hay .tapp ecosystem."
```

---

## 1. Hệ thống Truy cập

- 📋 Giới hạn truy cập toàn diện theo license doanh nghiệp (Workspace-gated).
- 📋 Chặn hoàn toàn việc đăng ký hoặc cài đặt tài khoản cá nhân độc lập ngoài luồng doanh nghiệp.

---

## 2. Lõi Mật mã & Quản lý Khóa (Module 1)

> **Technical Spec:** Core_Spec.md §5 (Crypto), §5.1 (HKMS), §5.3 (MLS) · Feature_Spec.md §F-01

- 🗄️ Phân mảnh `Enterprise_Escrow_Key` thành 5 mảnh cấu trúc Shamir (3-of-5) cho C-Level (cần 3 giám đốc để tái tạo khóa).
- 📱💻🖥️ Thực thi `ZeroizeOnDrop` để dọn sạch RAM (ghi đè 0x00) cho mọi struct chứa plaintext khi thoát scope.
- 🖥️ Đóng băng session (Dead Man Switch) qua bộ đếm monotonic TPM 2.0 khi lưu trữ vượt giới hạn TTL offline.
- 📱💻🖥️ Quản lý tối đa 10,000 thành viên một nhóm E2EE qua giao thức MLS RFC 9420.
- 📱💻🖥️ Xoay khóa (Epoch Rotation) gốc tự động khi member thao tác rời hoặc định kỳ 24h.
- 📱💻🖥️ Kháng mã hóa lượng tử thông qua giao thức Post-Quantum Hybrid (ML-KEM-768 + X25519) đạt chuẩn CNSA 2.0.
- 📱 Ủy quyền quản lý khóa cho Secure Enclave (Face ID/Touch ID) trên iOS / macOS.
- 📱 Gắn chặt storage vào StrongBox Keymaster HAL (BiometricPrompt) trên Android.
- 📱 Trữ key tại TrustZone TEE trên thiết bị Huawei.
- 🖥️ Phân bổ master key vào TPM 2.0 (CNG Provider trên Windows / tpm2-pkcs11 trên Linux).
- 🗄️ Cố định Master Key gốc tại HSM FIPS 140-3 chuẩn quân đội cho hệ thống Bare-Metal.

---

## 3. Nhắn tin, Cộng tác & Thoại/Video (Module 2)

> **Technical Spec:** Core_Spec.md §7 (CRDT), §8 (Messaging) · Feature_Spec.md §F-01, §F-06, §F-09

- 📱💻🖥️ Triển khai E2EE đa phương thức tại local client cho toàn bộ tin nhắn, tài liệu và voice/video.
- 📱💻🖥️ Hợp nhất state nhất quán không cần server phối hợp thông qua mảng CRDT DAG.
- 📱💻🖥️ Tra cứu tin nhắn nội bộ qua SQLite FTS5 (cô lập phía client) ngăn server soi dữ liệu.
- 📱💻🖥️ Sinh lệnh Crypto-Shredding hủy dữ liệu vĩnh viễn đúng hạn TTL tin nhắn, duy trì `Tombstone_Stub` rỗng để cấu trúc DAG.
- 📱💻🖥️ Phát luồng HD Voice & Video mã hóa DTLS-SRTP E2EE.
- 📱💻🖥️ Pre-warm luồng ICE proxy sẵn sàng ngay khi người dùng mở khung chat.
- ☁️ Điều tiết luồng HA failover mạng TURN < 3s bằng IP động (Keepalived Floating).
- 📱 Kéo dài Dead Man Switch để không gián đoạn cuộc gọi qua iOS CallKit và log `DeadManDeferralEntry` cẩn mật trực tiếp.
- 📱 Streaming nguyên bản từ Native-to-Rust Bridge vào trình phát ExoPlayer/AVPlayer tránh tốn RAM.
- 📋 Áp quyền thao tác Role-Based View → Commenter → Editor trên file Smart Document độc quyền phòng ban.
- 📋 Triển khai luồng Proposal Flow nội bộ theo kiểu Pull-Request duyệt qua Editor.
- 📋 Ký số chứng thực hành pháp lý nội bộ thông qua thuật toán sinh trắc học Ed25519.
- 🗄️ Đính Zero-Byte Stub vào TeraVault VFS nhằm loại bỏ rác cache dư thừa cho video/tệp kích thước lớn.

---

## 4. Survival Mesh Network (Module 3)

> **Technical Spec:** Core_Spec.md §6 (Mesh) · Feature_Spec.md §F-05

- ☁️ Định tuyến băng thông cao 100 Mbps qua protocol QUIC/gRPC/WSS (Tier 1).
- 💻 Gắn kết thiết bị LAN tốc độ 500 MB/s qua Wi-Fi Direct / AWDL ở chế độ No-Internet (Tier 2).
- 📱 Duy trì control plane siêu nhẹ (~50ms latency) bằng BLE 5.0 (Tier 3).
- 📱 Kích hoạt truyền Text-only tầm xa (BLE Long Range) lúc mạng sụp dưới giao thức EMDP.
- 🔌 Đẩy lệnh hạ cấp codec (Opus -> AMR-NB) khi thiết bị ngắt IP nhảy vào Mesh giảm tải lưu lượng.
- 🖥️ Tổ chức node Desktop cấu hình mạnh hoạt động làm Super Node (kết nối 48-72h / xử lý DAG dictator).
- 📱 Chọn lọc node Android > 3GB RAM hoạt động với vai trò Relay Node tải 100MB / 24h.
- 📱 Đóng đinh iOS làm Leaf Node hoặc Tactical Relay ngắn 60 phút - cấm làm Dictator.
- 📱💻🖥️ Giao chìa khóa (Export Session Key) từ Desktop qua iOS bằng dạng mã hóa ECIES trước khi ngắt mạng EMDP.
- 🖥️ Đồng bộ lại (Reconcile) và ghép DAG mượt mà từ mã Escrow iOS khi Desktop kết nối mạng trở lại.

---

## 5. AI Privacy Shield (Module 4)

> **Technical Spec:** Core_Spec.md §3.3 (Memory), §4.4 (Component Isolation) · Feature_Spec.md §F-10, §INFRA-07, §INFRA-08

- 🤖 Lọc PII triệt để trực tiếp tại client thông qua mô hình Micro-NER ONNX < 1MB on-device.
- 🤖 Gắn bí danh alias (vd: [MASK_01]) ẩn Tên/Email vào vault bộ nhớ RAM.
- 🤖 Cắt tiến trình SLM Worker ra khỏi lõi OS để tránh sập app cục bộ.
- 🤖 Chặn chèn lệnh (Injection Defense) qua mã hóa cây cú pháp AST Sanitizer kiểm định trước khi in HTML/Markdown.
- ☁️ Đẩy outbound data thông qua Consent-Driven Bridge tích hợp mã hóa TLS 1.3 chuyên dụng.
- ☁️ Thay IP danh tính thành spoofed data tại Gateway cho mọi luồng gọi ngoại vi AI API.
- 📱 Tối ưu SLM CoreML engine cho iOS để vượt qua ràng buộc W^X constraint trên store.
- 📱 Khởi kích inference ONNX Runtime cho mọi client Android và desktop.
- 📋 Set quota cứng theo tier (Unlimited cho Enterprise / 50K giới hạn cho Tier SME/Business).

---

## 6. Enterprise Plugin Ecosystem (.tapp) (Module 5)

> **Technical Spec:** Core_Spec.md §4.1 (Sandbox), §4.4 (Fault Isolation) · Feature_Spec.md §F-07, §F-08

- 📋 Gom lệnh cài mới/approve .tapp về đầu mối duy nhất là IT Admin.
- 🔌 Đóng hộp cấu hình RAM ≤ 64MB; vượt rào RAM bị xử lý OOM-kill không thông báo.
- 🔌 Quản chế mức trần tải CPU plugin ở mức 10% sustained throughput.
- 🔌 Kẹp định mức Egress Network 4KB thao tác, khóa chặn mạng 512KB mọi kết nối ra ngoài.
- 🔌 Cắt mạng TCP/UDP trần; chỉ whitelist luồng gọi HTTPS/WSS khai báo trước.
- 🗄️ Phân phối không gian lưu trữ cho sled KV AES-256-GCM ở vùng isolation data theo mỗi DID.
- 📱 Đẩy Egress network retry ngầm vào Egress_Outbox chạy nền qua WorkManager.
- 📱 Hủy cưỡng chế (terminate) plugin khi nhảy sang Mesh Mode để bảo vệ tiến trình dẫn đường BLE.

---

## 7. Identity, RBAC & Enterprise Controls (Module 6)

> **Technical Spec:** Core_Spec.md §5.1 (Identity), §5.2 (Key Hierarchy) · Feature_Spec.md §F-11, §F-12, §F-13

- 📋 Giới hạn sửa policy/hệ thống quản trị bằng HSM Quorum cho cấp lãnh đạo (CISO/Admin).
- 📋 Tạo luồng backup dành riêng HR Recovery Officer không thể giải mã tin nhắn.
- 📋 Dừng Editor/Viewer ở quyền hạn đọc-duyệt an toàn bằng Shadow Branch và Zeroize.
- 🗄️ Đưa toàn bộ cấu hình vào OPA Rego Policy Engine - không có API bypass.
- 📱💻 Tự động chặn gửi tin lệch cấp trừ khi qua phê duyệt Request/Approval do OPA điều tiết.
- 📋 Set cơ chế Enrollment Token từ IT Admin TTL 12–24h cho máy đời mới.
- 📱 Quét Recovery QR bằng Rust Core verify checksum signature trước luồng fetch DB backup.
- 📱 Yêu cầu phục hồi BIP-39 bắt buộc bằng 24-word + biometric check sinh trắc học thiết bị song song.
- ☁️ Đồng bộ ID broker ngoài (Okta, Azure AD) xử lý cấp/xóa token SCIM 2.0.
- 📱💻🖥️ Giật Remote Wipe tức thì dưới 30s với máy trạm offboarded bằng luồng `removedMembers`.

---

## 8. Federation & Cross-Org Communication (Module 7)

> **Technical Spec:** Core_Spec.md §9.6 (Federation) · Feature_Spec.md §F-13

- ☁️ Triển khai Private Cluster thiết bị vành đai mã hóa tách biệt cho các phân vùng doanh nghiệp.
- ☁️ Phát tin cậy tin nhắn mTLS "Sealed Sender" giấu tung tích người viết phía đối tác bên ngoài.
- 🗄️ Lọc Policy rules qua OPA Distribution bất chấp kết nối Federation lệch schema an toàn.
- ☁️ Giám sát từ chối kết nối `SCHEMA_INCOMPATIBLE` nếu version API văng ngoài ngưỡng ±1 major.

---

## 9. Compliance, DLP & Audit (Module 8)

> **Technical Spec:** Core_Spec.md §12.4 (Compliance) · Feature_Spec.md §F-11, §F-13

- 💻 Chặn mọi luồng data kết xuất trích IP ảo ngoài OPA Egress Whitelist OS.
- 🔌 Block ngay tài khoản vi phạm Byte-Quota ngốn 100% Session quota (Khóa mạng egress 24h & hú còi CISO).
- 📱💻 White-lit tước quyền đăng định dạng dị biệt, chỉ cấp upload PDF, JPEG, DOCX.
- 🗄️ Siết chuẩn Audit Log bắt nhận diện chữ ký rành mạch Ed25519 cho mọi sự kiện.
- 🗄️ Bọc chuỗi sự kiện bằng Merkle Chain để khóa chết thao tác tẩy xóa (Ngăn chặn Insider threat).
- 📋 Phê duyệt Conversation Sealing (SSA) khóa chức năng ghi tin nhắn khi phát hiện Social Engineer.
- 🔌 Đổ mã kill (Emergency Kill) giết gọn mọi .tapp khai thác lỗi < 60s.

---

## 10. Infrastructure, Deployment & Licensing (Module 9)

> **Technical Spec:** Core_Spec.md §9 (Infrastructure) · Feature_Spec.md §INFRA-01–09

- ☁️ Phát hành bằng Core duy nhất Rust binary không dùng Kubernetes.
- ☁️ Đo điểm benchmark tốc độ mã hóa thư dưới 10ms.
- ☁️ Reset kết nối ALPN negotiation trong dưới 50ms cho mọi mạng ngoài/trong.
- 📋 Hỗ trợ Air-Gapped License offline 100% triệt để tại cấp Enterprise+/Gov.
- 📋 Khớp chuẩn cấu hình Chaos Engineering Cert cho dòng mạng cấp Gov.
- 📋 Mãnh liệt đẩy retention Policy Compliance từ bản ghi 90 ngày lên mốc vô hạn / 7 năm.
- 🗄️ Chỉ đạo phân phối nguồn mở theo dạng `terachat-core` AGPLv3.
- 🗄️ Ấn định code kiểm soát license `terachat-license-guard` nằm kín chuẩn BSL.
- 💻 Mở source Frontend `terachat-ui` ở mã MIT/Apache 2.0 thoải mái tích hợp.

---

## 11. Platform Hard Constraints

- 📱 Giới hạn iOS: Import module bằng wasm3 interpreter tránh rào cản W^X chặn JIT Apple.
- 📱 Giới hạn iOS: Buộc tách Ghost Push ra ngoài Main App dẹp luật iOS rào 20MB NSE.
- 📱 Tính toán iOS: Giam ngầm kết nối Mesh sang BLE thay vì AWDL khi gặp cấm CarPlay.
- 📱 Android OS: Đạp ưu tiên Doze mode qua Android FCM/CDM high-priority.
- 📱 Huawei: Mồi request định kỳ bằng HMS polling thay vì content-available push hụt.
- 🖥️ Linux: Dán Cosign chứng thư tệp `.deb`/`.rpm`/`AppImage` thay thế Flatpak hỏng seccomp-bpf.

---

_TeraChat — Hệ điều hành Công việc Chủ quyền._
_TERA-FUNC v1.2.0 · 2026-03-25_
