# TeraChat V0.2.1 — Platform Boundary Specification (PlatformSpec)

> **Vai trò tài liệu:** Technical Documentation Architect — phân loại ranh giới kỹ thuật theo nền tảng.
> **Nguyên tắc:** Mọi phân loại dựa trên **bản chất kỹ thuật**: môi trường chạy, hạn chế phần cứng, OS, cách triển khai thực tế — không phân loại cảm tính hay theo tên gọi.
> **Nguồn:** Phân tích từ `TechSpec.md` v0.2.1.

---

## TABLE OF CONTENTS

1. [Bảng A — Kỹ thuật dành riêng cho Desktop / PC](#bảng-a--kỹ-thuật-dành-riêng-cho-desktop--pc)
2. [Bảng B — Kỹ thuật dành riêng cho Mobile / Smartphone / Tablet](#bảng-b--kỹ-thuật-dành-riêng-cho-mobile--smartphone--tablet)
3. [Bảng C — Kỹ thuật dành riêng cho Server / Cluster / Backend](#bảng-c--kỹ-thuật-dành-riêng-cho-server--cluster--backend)
4. [Bảng D — Kỹ thuật dùng chung (tách C1: Desktop / C2: Mobile)](#bảng-d--kỹ-thuật-dùng-chung)

---

## Bảng A — Kỹ thuật dành riêng cho Desktop / PC

> Các công nghệ này chỉ có thể hoạt động đúng chức năng trên môi trường Desktop (Windows / macOS / Linux). Mobile không thể triển khai do giới hạn OS sandbox, RAM, hoặc API bị Apple/Google cấm.

| Công nghệ | Hệ điều hành | Ngữ cảnh sử dụng | Lý do không phù hợp Mobile |
|---|---|---|---|
| **SQLite FTS5 Full-Text Search (Background Worker)** | Windows / macOS / Linux | Desktop Background Process lập chỉ mục toàn bộ lịch sử tin nhắn đã giải mã trong suốt phiên dài | iOS/Android sandbox không cho phép background process chạy vô thời hạn. Mobile cắt background process sau vài phút |
| **Local Edge RAG (Embedding WASM/Rust)** | Windows / macOS / Linux | Chạy embedding model cục bộ để báo cáo phức tạp — Local AI inference không cần Server | Model embedding cần 4–8GB RAM. Điện thoại không đủ RAM; iOS cứng kill process > 1.2–1.5GB |
| **Tauri Desktop Shell** | Windows / macOS / Linux | Desktop app container — WASM WebView + Rust Core Native qua IPC | Tauri là framework Desktop-only. Không có phiên bản Mobile runtime |
| **WASM + OPFS (Origin Private FileSystem) — đã loại, thay bằng VFS Bridge** | -- | Đã bị loại bỏ (Fix Alpha #1) vì file lock conflict | Không áp dụng — đã thay VFS Bridge |
| **SharedArrayBuffer + Protobuf IPC (Control Plane / Data Plane)** | Windows / macOS / Linux | Vùng nhớ dùng chung giữa WASM và Rust Core — Zero-Copy SAB Ring Buffer | iOS WebKit cấm `SharedArrayBuffer` trong WKWebView không có COOP/COEP headers. Mobile runtime cần JSON fallback |
| **`.tapp` WASM Sandbox (Full Runtime)** | Windows / macOS / Linux | Enterprise Utility Tools chạy WASM trong Tauri WebView với VFS Bridge đầy đủ | iOS cấm dynamic WASM JIT. Mobile `.tapp` chỉ nhận được JSON Adaptive Cards |
| **Desktop TURN Server (HA Cluster Call)** | Windows / macOS / Linux | Máy trạm Desktop tham gia cuộc gọi WebRTC trực tiếp với TURN relay không giới hạn thời gian | Mobile có giới hạn background execution. Desktop không bị giới hạn |
| **TPM 2.0 Health Attestation** | Windows 10+ | Remote Attestation xác minh tính toàn vẹn thiết bị (PCR check + BitLocker ON) | TPM 2.0 là module phần cứng PC. iOS dùng DCAppAttestService; Android dùng Play Integrity |
| **BitLocker (Full-Disk Encryption tầng OS)** | Windows (Enterprise) | Chứng minh disk encryption bật khi Remote Attestation | Tương đương mobile: iOS Data Protection / Android FDE — khác API hoàn toàn |
| **WASM Doctor Script (Client-side Debug)** | Windows / macOS / Linux | Blind Observability: debug crash tại Client, không gửi nội dung lên Server | Mobile không có exposed WASM runtime để chạy debug script tùy ý |
| **Legacy Vault / Slack Import (`.sqlite.enc`)** | Windows / macOS / Linux | Export Slack lịch sử → mã hóa Archive_Key → lưu local → FTS5 tìm kiếm trong Tab Archive | File `.sqlite.enc` có thể hàng GB. Mobile không đủ storage quota và background processing |
| **Wi-Fi Direct Soft-AP Host (Android ở đây là Desktop-equivalent trong context này)** | Windows / Android (Tablet/PC) | Tạo Soft-AP ẩn để làm Access Point cho QR Wi-Fi Direct transfer — Bước chủ động | iOS bị Apple cấm tạo Soft-AP. Chỉ Windows và Android có `WifiManager.startLocalOnlyHotspot()` |
| **Offline Double Ratchet — TCP Server Socket** | Windows / macOS / Linux | Mở TCP port lắng nghe khi nhận file LAN (peer kết nối tới) | iOS sandbox cấm bind TCP port tùy ý. Mobile chỉ kết nối outbound |

---

## Bảng B — Kỹ thuật dành riêng cho Mobile / Smartphone / Tablet

> Các công nghệ này tồn tại vì trình duyệt/OS Mobile có hạn chế đặc thù mà Desktop không gặp, hoặc tận dụng phần cứng riêng của thiết bị di động.

| Công nghệ | Hệ điều hành | Ngữ cảnh sử dụng | Lý do không phù hợp Desktop |
|---|---|---|---|
| **UNNotificationServiceExtension (NSE)** | iOS 10+ | Extension riêng biệt nhận APNS Push → giải mã preview text ≤ 4KB push payload bằng Push_Key | Cơ chế này là đặc thù iOS. macOS dùng APNs nhưng không có NSE giới hạn 24MB RAM |
| **APNS (Apple Push Notification Service)** | iOS / macOS | Đánh thức app khi bị Force Kill — `mutable-content: 1` | macOS dùng APNS cho Mac apps, nhưng không bị Force Kill limitation. Windows/Linux có FCM hoặc WebSocket |
| **FCM Data Message (Firebase Cloud Messaging)** | Android | Background wake-up thay thế TCP persistent connection | Desktop Linux/Windows không có FCM. Dùng WebSocket long-polling hoặc TCP keep-alive |
| **Android FirebaseMessagingService** | Android | Background service giải mã payload bằng Rust FFI + StrongBox Keymaster | Không tồn tại trên Desktop — Android-specific foreground/background service lifecycle |
| **iOS DCAppAttestService** | iOS 14+ | Remote Attestation xác minh app không bị modify, thiết bị không Jailbreak | API độc quyền của Apple. Desktop dùng TPM 2.0 + Windows Health Attestation |
| **Android Play Integrity API** | Android 5+ | Remote Attestation yêu cầu `MEETS_STRONG_INTEGRITY` (Hardware-backed Keystore) | Google-specific API. Desktop Windows dùng TPM Health Attestation |
| **iOS Secure Enclave (SEP)** | iPhone / iPad | Lưu Private Key, ký giao dịch, thực thi `biometricPrompt` với Secure Enclave Processor | SEP là chip vật lý riêng trong Apple Silicon / A-series. Desktop dùng TPM chip |
| **Android StrongBox Keymaster** | Android 9+ | Lưu Private Key trong Secure Element riêng biệt, không thể extract ngay cả khi Root | StrongBox là chip tamper-proof riêng biệt trên Android. Desktop dùng TPM hoặc software HSM |
| **Hardware Monotonic Counter (iOS Secure Enclave)** | iOS | Dead Man Switch — Counter++ mỗi lần unlock DB, chống Time-Travel Attack (clone snapshot) | iOS Secure Enclave Processor cung cấp Monotonic Counter hardware. PC TPM cũng có nhưng khác API |
| **`BiometricPrompt` (System-Managed UI)** | Android | Smart Approval signing — vẽ trên System UI (không thể bị overlay tấn công) | Desktop không có touch fingerprint sensor phổ biến. macOS Touch ID dùng khác API (`LocalAuthentication`) |
| **`LocalAuthentication` + `LAContext`** | iOS / macOS | Face ID / Touch ID cho phê duyệt giao dịch | macOS có LAContext nhưng Flow khác: không chạy trong constrained background như iOS |
| **iOS Network Extension API** | iOS | Join Wi-Fi Direct theo SSID/password từ mã QR — bắt buộc để peer với máy A qua Soft-AP | API đặc quyền Apple. Android/Windows kết nối Wi-Fi theo cách khác (`WifiNetworkSuggestion`) |
| **`.tapp` Mobile Adaptive Cards (JSON Renderer)** | iOS / Android | iOS cấm WASM JIT → `.tapp` trả JSON Adaptive Cards; React Native/Flutter làm renderer tĩnh | Desktop chạy full WASM sandbox trong Tauri — không cần Adaptive Cards fallback |
| **NSE Micro-Crypto Build Target** | iOS | Build riêng biệt cho NSE: chỉ AES-256-GCM + Ed25519, loại bỏ MLS/CRDT/SQLCipher write | Kỹ thuật build riêng này chỉ tồn tại do giới hạn 24MB RAM của NSE — Desktop không có giới hạn này |
| **`mlock()` trên Mobile RAM (AI Worker Standard Mode)** | Android / iOS (limited) | Ngăn OS swap Channel_Key ra ổ cứng khi xử lý AI request | Desktop cũng dùng `mlock()` nhưng hệ quả khác: Mobile OS swap thường xuyên hơn do RAM ít hơn |
| **BLE 5.0 Discovery / Advertisement** | iOS / Android | Phát hiện peer trong Survival Link Mesh khi mất mạng hoàn toàn (không cần router) | Desktop không có BLE hardware standard (laptop mới có nhưng OS API không expose cho third-party apps như mobile) |

---

## Bảng C — Kỹ thuật dành riêng cho Server / Cluster / Backend

> Chỉ chạy trên Server infrastructure — Client không bao giờ chạy các thành phần này.

| Công nghệ | OS / Cloud | Ngữ cảnh sử dụng | Lý do không chạy trên Client |
|---|---|---|---|
| **Federated Private Cluster (3–5 Nodes + Erasure Coding)** | Linux (Ubuntu/Debian) VPS / Bare-metal | Lưu trữ Encrypted Log, định tuyến tin nhắn, TURN server cho WebRTC | Cluster yêu cầu static IP, persistent storage, high-bandwidth uplink |
| **Erasure Coding (Sharding)** | Linux Cluster | Phân tán dữ liệu — 1 node sập, tự phục hồi từ mảnh còn lại | Cần 3–5 nodes vật lý riêng biệt |
| **HA TURN / STUN Server (Floating IP + Failover 3s)** | Linux | WebRTC relay cho Voice/Video call khi NAT không xuyên qua được | TURN Server cần bandwidth cao + IP tĩnh — không thể chạy trên thiết bị di động |
| **PostgreSQL (Primary Cluster DB)** | Linux | Enterprise user table, PKI bindings, revocation triggers, SCIM sync | RDBMS trọng yếu chạy server-side — Client dùng SQLite |
| **Redis (Rate Limiting ZSET + Session)** | Linux | Sliding Window Rate Limiting, Ephemeral Token store | In-memory cache server — không deploy trên Client |
| **OPA (Open Policy Agent) Server** | Linux | ABAC policy enforcement: department, geo, role. GeoHash lookup | OPA là daemon độc lập. Client chỉ gửi request, không tự enforce |
| **Keycloak / Dex (Identity Broker)** | Linux | OIDC/SAML SSO bridge giữa TeraChat và Azure AD/Google/Okta | Identity Broker là server infrastructure — Client redirect đến, không host |
| **SCIM 2.0 Listener** | Linux | Nhận webhook từ Azure AD/Okta để sync nhân sự realtime | Listener HTTP server — chạy server-side |
| **MLS Backbone (Cluster-side)** | Linux | Phân phối KeyPackages, lưu Encrypted Commit Messages cho MLS Group | MLS state lớn được lưu server-side; Client chỉ giữ local epoch state |
| **TEE — AWS Nitro Enclaves** | AWS EC2 (Nitro-compatible) | AI Worker Enterprise Mode: Channel_Key không bao giờ rời Enclave RAM | Nitro Enclave yêu cầu phần cứng AWS Nitro — không deploy local |
| **TEE — Azure DCsv3 (SGX)** | Azure VM (SGX-enabled) | AI Worker Enterprise Mode: SGX Enclave bảo vệ Channel_Key khỏi Root Admin host OS | Phần cứng đặc thù Cloud — không deploy trên thiết bị người dùng |
| **Intel SGX / AMD SEV (On-Premise TEE option)** | Linux Bare-metal SGX/SEV | AI Gateway tách rời cho doanh nghiệp tự host | Yêu cầu CPU Intel Xeon SGX hoặc AMD EPYC SEV — không có trên laptop/phone |
| **Enterprise CA (PKI Server)** | Linux | Phát hành và thu hồi Certificate cho thiết bị doanh nghiệp | CA server phải luôn available cho CRL check — không thể chạy trên Client |
| **DLP Quarantine Queue (Message Queue)** | Linux | Giữ file bị OPA intercept cho đến khi đủ M-of-N Supervisor signatures | Queue persistent server-side — cần đảm bảo durability |
| **Federation Bridge (mTLS + Sealed Sender relay)** | Linux | Định tuyến tin nhắn xuyên tổ chức TeraChat ↔ TeraChat | Server-to-server bridge — Client chỉ biết final MLS ciphertext |
| **Cluster Interop Hub** | Linux | Gateway E2EE cho SAP/Jira/CRM — nhận dữ liệu bên ngoài, wrap thành E2EE trước khi push Client | Cần expose public HTTPS endpoint — không deploy Client-side |
| **AI Egress Worker (Docker Hardened / Standard Mode)** | Linux Docker | Gọi LLM API ngoài (OpenAI/Claude/Gemini) — mlock + zeroize <50ms | Worker VPS/Docker cần network egress policy, seccomp profile — không chạy trên Client |
| **Z3 SMT Solver CI/CD Pipeline** | Linux CI Server | Kiểm chứng formal OPA Policy + Approval Logic trước mỗi Deploy | Công cụ offline verification — CI/CD infrastructure only |
| **LibFuzzer / AFL++ Fuzzing Infrastructure** | Linux CI Server | Continuous Fuzzing: Packet Parser, Crypto Handshake, File Processing | Fuzzing cần máy chủ 24/7, LLVM Sanitizers — không trên Client |

---

## Bảng D — Kỹ thuật dùng chung

> Các công nghệ sau chạy trên CẢ Desktop VÀ Mobile, nhưng **triển khai khác nhau, giới hạn khác nhau, và cách vận hành khác nhau** giữa hai nền tảng.

---

### D.1 — Triển khai trên Desktop / PC

| Công nghệ | Cách triển khai | Giới hạn | Ví dụ thực tế |
|---|---|---|---|
| **MLS E2EE (RFC 9420 / TreeKEM)** | Rust Core xử lý toàn bộ MLS state máy tính — TreeKEM O(log n), không giới hạn group size | Không giới hạn RAM đặc biệt. Epoch Rotation xử lý background | Desktop Client của nhân viên văn phòng join nhóm 5000 người |
| **SQLite (WatermelonDB / SQLCipher)** | SQLCipher mã hóa toàn bộ DB lịch sử. FTS5 full-text index cho toàn bộ lịch sử (không giới hạn window) | SSD của máy trạm. 50GB+ lịch sử → cần quản lý write throughput | Tìm kiếm "Hợp đồng Q3" trong 2 năm lịch sử chat |
| **Rust Core (Crypto + Business Logic)** | Biên dịch native binary cho Windows (`.exe`), macOS (`.app`), Linux (`.so`). Không JIT, không Sandbox bên ngoài | Truy cập đầy đủ OS syscall. RAM không bị giới hạn cứng | Giải mã MLS message, HKDF key derivation, AES-256-GCM |
| **WebRTC Voice / Video** | Desktop app tích hợp WebRTC SDK. TURN Cluster relay. Không giới hạn thời gian call | CPU/GPU xử lý encoding video — nặng nhưng không bị OS kill | Cuộc họp video 8 giờ liên tục trong hội trường |
| **Ed25519 / X25519 Key Pair** | Private Key lưu trong File-based Key Store được mã hóa bằng TPM-derived key hoặc mã hóa password | Private Key chỉ bảo vệ bởi software nếu không có TPM | Key binding thiết bị lúc onboarding |
| **AES-256-GCM** | Native CPU instruction (AES-NI). Không giới hạn data size per session | Throughput ~1–3GB/s với AES-NI | Mã hóa file 5GB gửi qua LAN |
| **E2EE File Transfer (Salted MLE / Strict E2EE)** | Upload full ciphertext lên Cluster không giới hạn size. Background upload không bị OS interrupt | Network bandwidth của máy trạm | Gửi file CAD 2GB đến khách hàng |
| **Offline TTL Session Guard** | Rust Core kiểm tra Monotonic time từ System Clock. Freeze sau 24h không ping Server | System Clock có thể bị chỉnh → workaround: Server timestamp check khi online | Máy tính nhân viên bị đuổi bị lock sau 24h offline |
| **Gossip CRL (BLE/Wi-Fi relay)** | Desktop Node relay CRL qua Wi-Fi Direct khi làm Desktop Super Node trong Mesh | Desktop không có BLE native API stable — relay chủ yếu qua Wi-Fi LAN | Máy trạm A online → sync CRL → lan sang 49 máy trong mạng nội bộ |
| **Hybrid STUN / Signaling (LAN P2P)** | Desktop gửi ICE Candidate lên Private Cluster Intranet. TCP punch-through AP Isolation | Phụ thuộc Private Cluster Intranet còn hoạt động | Nhân viên VP gửi file 500MB cho kế toán cùng văn phòng khi đứt WAN |
| **ChaCha20-Poly1305 (LAN Streaming)** | Native Rust crypto — tốc độ ~300MB/s với NEON/AVX2 optimizations | Intel AES-NI thường nhanh hơn ChaCha trên Desktop. Desktop ưu tiên AES-GCM | File streaming qua Wi-Fi Direct giữa 2 máy trạm |
| **Double Ratchet (O-DR) LAN Session** | TCP Server Socket mở trên Desktop để nhận kết nối từ peer. Full LanRatchetSession state | Phụ thuộc firewall Desktop không block TCP inbound | Desktop A mở TCP:48320, Desktop B kết nối → trao đổi khóa → file transfer |
| **Zero-Knowledge Search (FTS5)** | Background Worker chạy 24/7 index toàn bộ tin nhắn đã giải mã. Full history không giới hạn | Disk I/O write khi index. SSD life ảnh hưởng nếu history quá lớn | Tìm "phê duyệt ngân sách" trong lịch sử 3 năm < 100ms |
| **HKDF Key Derivation** | Rust native: HKDF-SHA256, không giới hạn. Chạy đồng bộ trong foreground | Không có giới hạn đặc biệt trên Desktop | Derive Static_Dedup_Key, Push_Key, per-app DB key |
| **DLP Smart Clipboard** | Hook vào OS clipboard API (Win32 / macOS Pasteboard). Phát hiện destination app | Desktop có nhiều cửa sổ → cần monitor mọi clipboard event | Ngăn copy hợp đồng R&D vào Zalo Desktop |
| **TeraVault VFS (Local Cache)** | Full folder tree cache trên SSD. Background sync không giới hạn. Tiers 1/2/3 đầy đủ | SSD quota phụ thuộc máy trạm | Admin pin toàn bộ folder dự án → tự động sync về Desktop |

---

### D.2 — Triển khai trên Mobile / Smartphone / Tablet

| Công nghệ | Cách triển khai | Giới hạn | Ví dụ thực tế |
|---|---|---|---|
| **MLS E2EE (RFC 9420 / TreeKEM)** | Rust Core biên dịch thành static library (`.xcframework` iOS / `.aar` Android). Xử lý MLS trong foreground | RAM ≤ 1.5GB (iOS). Background MLS processing không được phép — phải defer | iPhone nhận MLS Commit khi mở app → decrypt message |
| **SQLite (WatermelonDB / SQLCipher)** | SQLCipher chạy trên thiết bị. FTS5 index giới hạn theo window lịch sử (1–3 tháng gần nhất) | Storage limited (32–128GB). iOS App Storage quota. Background write bị restrict | Tìm trong 3 tháng lịch sử gần nhất trên iPhone |
| **Rust Core (Crypto + Business Logic)** | Biên dịch cross-compile → iOS static lib (arm64/arm64e) / Android .so (arm64-v8a, armeabi-v7a). Gọi qua FFI từ Swift/Kotlin | iOS cấm `mmap` executable → không thể JIT. Rust chạy AOT. Memory limit cứng | Giải mã tin nhắn khi nhận notification trên iPhone |
| **WebRTC Voice / Video** | iOS/Android WebRTC SDK. Background audio call được phép (Background Mode: audio). Video call foreground only | iOS background execution: 30 phút audio. Video call bị suspend khi background | Cuộc gọi thoại khi khóa màn hình iPhone |
| **Ed25519 / X25519 Key Pair** | Private Key lưu trong iOS Secure Enclave (hardware) hoặc Android Keystore (StrongBox) | iOS: không thể extract key dù root. Android: phụ thuộc StrongBox availability | Key signing khi phê duyệt giao dịch bằng Face ID |
| **AES-256-GCM** | Dùng Apple CryptoKit (`AES.GCM`) hoặc Android Conscrypt. ARM chip có AES-NI hardware | Throughput ~500MB/s–1.5GB/s trên Apple Silicon. Điện thoại tầm thấp ~200MB/s | Giải mã file ảnh vừa nhận trong notification |
| **E2EE File Transfer (Salted MLE / Strict E2EE)** | Upload background: iOS background URLSession (tối thiểu 3 phút). Android có JobScheduler | iOS: Upload lớn (>1GB) phải có explicit background task. Suspend nếu user lock screen | Gửi file báo cáo 50MB từ iPhone |
| **Offline TTL Session Guard** | Rust Core kiểm tra thời gian. iOS Secure Enclave có Monotonic Counter chống clock chỉnh | Nếu iOS ở Low Power Mode → Rust Core bị throttle CPU → check chậm hơn | iPhone nhân viên bị đuổi: sau 24h offline Mesh, Session frozen |
| **Gossip CRL (BLE relay)** | Mobile là node Gossip chính qua BLE 5.0 — gửi/nhận CRL packet nhỏ (<512 bytes BLE MTU). Fragmentation nếu CRL lớn | BLE range ~30–100m. Packet fragmentation nếu revoke list lớn. Pin consumption | iPhone A bắt được 4G → tải CRL → BLE broadcast → 49 máy trong mesh cập nhật trong 30s |
| **Hybrid STUN / Signaling (LAN P2P)** | Mobile gửi ICE Candidate lên Private Cluster qua Intranet Wi-Fi. WebRTC punch-through | iOS WKWebView có COOP/COEP issue với WebRTC → cần native WebRTC SDK | iPhone gửi file 500MB cho laptop đồng nghiệp qua Wi-Fi Direct sau STUN signaling |
| **ChaCha20-Poly1305 (LAN Streaming)** | **Ưu tiên hơn AES-GCM** trên Mobile do không phụ thuộc AES-NI. ARM NEON optimizations sẵn | ARM64 iPhone/Android: ~300MB/s ChaCha20. Tốt hơn AES Software mode trên điện thoại tầm thấp | iPhone gửi file 2GB qua Wi-Fi Direct — dùng ChaCha20 thay AES |
| **Double Ratchet (O-DR) LAN Session** | Mobile chỉ kết nối **outbound** TCP tới peer Desktop/Mac. Không mở TCP server port (iOS sandbox cấm) | iOS: không bind TCP port listen. Chỉ initiate kết nối ra ngoài | iPhone quét QR của Desktop A → kết nối TCP outbound → LanRatchetSession |
| **Zero-Knowledge Search (FTS5)** | FTS5 index giới hạn window ~1–3 tháng. Index chỉ chạy khi app foreground hoặc background fetch ngắn | iOS background fetch: ~30s mỗi vài giờ. Index không đầy đủ như Desktop | Tìm "hợp đồng" trên iPhone — chỉ trong 3 tháng gần nhất |
| **HKDF Key Derivation** | Rust native on-device. Giống Desktop nhưng phải hoàn thành trước khi OS suspend background task | iOS `beginBackgroundTask` cho phép ~3 phút background → đủ cho HKDF | Derive Push_Key lúc NSE Extension wake up |
| **DLP Smart Clipboard** | iOS: `UIPasteboard` monitoring. Android: `ClipboardManager`. OS giới hạn đọc clipboard của app khác | iOS 14+: chặn app đọc clipboard background, chỉ read khi foreground. Android 12+ tương tự | Phát hiện user copy từ TeraChat sang Zalo Mobile — cảnh báo |
| **TeraVault VFS (Local Cache)** | Tầng 1 (Auto) và Tầng 2 (On-demand) hoạt động. Tầng 3 (Make Offline) bị giới hạn quota app storage | iOS App iCloud storage / Local storage bị giới hạn. Background sync bị OS throttle | iPhone Manager toggle "Make Available Offline" cho folder dự án → sync trong nền |

---

## Tổng kết phân loại

| Nhóm | Số lượng công nghệ | Ghi chú |
|---|---|---|
| **Desktop-only** | 13 | Chủ yếu do OS sandbox, phần cứng (TPM), background execution không giới hạn |
| **Mobile-only** | 16 | Chủ yếu do API đặc thù Apple/Google, chip Secure Enclave/StrongBox, Push Notification |
| **Server/Backend-only** | 18 | Infrastructure: Cluster, TEE Cloud, CI/CD, Database |
| **Shared (Desktop + Mobile)** | 17 | Cùng tên, nhưng implementation/giới hạn khác nhau hoàn toàn |
| **Tổng** | **64** | |

> **Quy tắc phân loại tóm gọn:**
> - Nếu OS API bị cấm trên Mobile (TCP bind, WASM JIT, SharedArrayBuffer) → Desktop-only
> - Nếu API chỉ tồn tại trên Apple/Google ecosystem (NSE, DCAppAttestService, Play Integrity, Secure Enclave) → Mobile-only
> - Nếu cần static IP / persistent storage / high bandwidth egress → Server-only
> - Nếu cùng tên nhưng Memory, Background Execution, Crypto Hardware khác nhau → Shared / tách C1-C2

---

*Tài liệu này bổ sung cho `TechSpec.md` (implementation details), `Function.md` (feature breakdown), `PRD.md` (user flows).*
