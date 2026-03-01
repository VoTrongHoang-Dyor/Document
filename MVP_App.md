<!-- markdownlint-disable MD036 -->
# TeraChat MVP Alpha — Đặc tả Kỹ thuật (Desktop/Laptop)

> **Document Owner:** Lead Architect & Security Expert
> **Audience:** Engineering Team, Security Engineers
> **Scope:** Tài liệu đặc tả kỹ thuật tinh gọn, dành **riêng cho phiên bản Alpha trên Desktop/Laptop (Windows, macOS, Linux)**.
> **Core Objective:** Xây dựng khung ứng dụng nhắn tin bảo mật, Local-First, Mã hóa đầu cuối (E2EE), hiệu năng nội bộ mượt mà như Telegram nhưng áp dụng các tiêu chuẩn an ninh không khoan nhượng.

---

## 1. Kiến trúc Tổng thể (Architecture & Platform)

Kiến trúc của MVP Alpha loại bỏ hoàn toàn các nền tảng Mobile để tập trung tối đa vòng đời phát triển vào môi trường Desktop tĩnh.

* **Platform Stack:** **Tauri + Rust Core + React/TypeScript**.
* **Rust Core (Backend):** Đảm nhiệm 100% logic nghiệp vụ, mật mã học, giao tiếp mạng, và lưu trữ cục bộ.
* **Tauri WebView (Frontend):** Dựa trên tiêu chuẩn HTML5/CSS/JS (WebView2 trên Windows, WebKit trên macOS/Linux). UI chỉ chịu trách nhiệm render trạng thái (dumb view), hoàn toàn không chứa key giải mã hay thực thi business logic nhạy cảm.
* **Data Plane Nguyên Mẫu:** Kiến trúc "Local-First Processing & Blind Routing". Thiết bị trạm đảm nhiệm mọi công việc tính toán nặng nhất (Mã hóa, Lập chỉ mục), trong khi Máy chủ (VPS Cluster) chỉ đóng vai trò trung chuyển gói byte đã rải mã hóa (Blind Storage/Relay).

---

## 2. Giao thức Mã hóa Lõi (Cryptography & Security Engine)

Mạng lưới bảo mật của bản Alpha được tối giản để triển khai nhanh nhưng không hạ thấp mức độ tàng hình và an toàn.

* **Messaging Layer Security (MLS - RFC 9420):** Áp dụng kiến trúc TreeKEM để mã hóa E2EE tin nhắn nhóm. Cấp phát và luân chuyển khóa (Epoch Rotation) ngay lập tức khi danh sách thành viên thay đổi.
* **Bảo vệ Bộ nhớ (RAM Pinning):**
  * Sử dụng API `mlock()` (trên macOS/Linux) và `VirtualLock` (trên Windows) từ Rust FFI để khóa chặt bộ nhớ chứa Private Key và plaintext, ngăn kernel trút dữ liệu ra Swap/Pagefile trên đĩa cứng.
  * Tự động Zeroize nội dung RAM (`memset_s`) ngay sau khi scope kết thúc.
* **Bảo mật Khóa Phần cứng (Hardware-backed Signing):**
  * Private Key của định danh thiết bị không bao giờ chạm vào đĩa cứng dạng trần.
  * Sử dụng **TPM 2.0** trên Windows (tháo tác qua CNG) và **CryptoTokenKit** qua Secure Enclave trên macOS để tạo và xác thực chữ ký số Ed25519 cho mọi giao dịch/handshake của thiết bị.

---

## 3. Cơ sở dữ liệu & Lưu trữ (Client-Side DB & Local-First)

Tư duy lưu trữ đẩy quyền tự chủ về thiết bị người dùng.

* **SQLCipher (Local DB):** Trái tim của Local-First. Toàn bộ lịch sử tin nhắn, cây MLS và dữ liệu cấu hình được ghi nén vào SQLite mã hóa bằng AES-256-RDBMS.
* **Lập chỉ mục Tìm kiếm (Zero-Knowledge Search):**
  * Tách biệt với Mobile, Desktop thiết lập **Local FTS5 Background Worker** trong Rust.
  * Tiến trình ngầm liên tục cày dữ liệu tin nhắn giải mã để xây dựng Full-Text Search Index tốc độ cao trên file SQLCipher. Không có bất kỳ truy vấn hay metadata nào được đẩy lên VPS.
* **Blind Storage (VPS):** Hệ thống cụm máy chủ chỉ nhận và lưu ciphertext. VPS tuyệt đối không thể giải mã các file, tin nhắn do thiếu `Company_Key` và Private Key tại trạm.

---

## 4. Giao tiếp & Mạng (Network & Routing)

Tập trung vào vùng "Intranet" tinh khiết, chưa yêu cầu khả năng liên kết liên công ty hay Mesh Network.

* **Persistent Protocol:** Sử dụng một WebSocket/MQTT persistent connection duy nhất kết nối trực lưu với Private Cluster (Zone 1).
* **Blind Relay:** Mọi gói dữ liệu (chat nội bộ, tải file) đều được bao bọc ở Tầng ứng dụng rồi mới stream đi. Server không đọc được "Who talks to whom" trừ các siêu metadata định tuyến cơ bản nhất.
* **Rate Limiting & Tối ưu Ping:** Giữ vững kết nối real-time cho hàng ngàn TCP socket đồng thời với overhead siêu nhỏ.

---

## 5. Ghép nối Giao diện & Lõi (IPC Bridge)

Xử lý sự cố "Nghẽn cổ chai" giữa Rust Core (bùn máy) và React UI (bề mặt).

* **SharedArrayBuffer + Protobuf:**
  * Truyền tải file lớn (Video, ISO, Zip) hoặc lô (batch) sự kiện CRDT qua lại giữa WebView và Rust.
  * Thay vì dùng Base64 IPC (gây sưng RAM và drop frame WebView2), Core cấp phát một vùng nhớ chung bằng SharedArrayBuffer. Phân giải/đọc nhị phân dựa trên cấu trúc Protobuf. UI vẫn chạy mượt ở 60fps ngay khi back-end xử lý stream file GBs.

---

## 6. Tiện ích Phụ trợ (TeraVault VFS)

Đơn giản hóa Quản lý tài liệu (Virtual File System) mà không nạp quá tải băng thông của thiết bị.

* **Zero-byte Stubs:** Metadata file được đồng bộ về SQLite cục bộ với kích thước < 1KB (gồm `file_name`, `cas_hash`...). Giả lập cây thư mục Explorer hoàn chỉnh. Nội dung gốc vẫn nằm ẩn ở trạng thái ciphertext rải rác trên hệ thống.
* **Auto-Mapping (Tải On-demand):** Chuột phải/click vào file => Rust Core mới nối Stream tải và giải mã vào RAM ngay lập tức. Hiệu quả tuyệt đối cho phân bổ bộ nhớ lưu trữ ổ đĩa máy Laptop.

---

## 7. Các Luồng Thực Thi Cốt Lõi (Core Execution Flows)

Bên cạnh nền tảng vững chắc, bản Alpha cần bổ sung 4 luồng thực thi (execution flows) sau để team Dev có thể tiến hành code:

### 7.1. Cụm VPS "1-Chạm" (DevOps & Infrastructure)

Viết sẵn môi trường triển khai Docker Compose "1-chạm" tối giản làm Server trung chuyển, bao gồm:

* **Signaling & Relay Node:** Một service WebSocket/MQTT làm đường ống truyền dẫn mù (Blind Relay).
* **Storage Node (BYOS):** Một container **MinIO (S3-compatible)** quản lý và lưu trữ các cụm ciphertext (đặc biệt là file đính kèm).
* **Identity DB:** Một container **PostgreSQL** cực nhẹ để duy trì trạng thái `Invite Token` danh tính và xác thực Public Key cho thiết bị.

### 7.2. Cơ chế Khởi tạo Danh tính & Đăng nhập (Onboarding Flow via Invite Token)

Trong kiến trúc TeraChat, chúng ta từ bỏ hoàn toàn mô hình "Username/Password" truyền thống để tránh nguy cơ rò rỉ cơ sở dữ liệu xác thực tại Server. Giai đoạn Alpha sử dụng cơ chế **Invite Token (JWT)** một lần để Bootstrapping Trust (thiết lập niềm tin) và sinh khóa bảo mật tại thiết bị (Client-Side Key Generation).

#### A. Luồng thực thi kỹ thuật (Execution Flow)

Luồng Onboarding phải tuân thủ nghiêm ngặt 5 bước sau. **Ngoại lệ = Bị reject PR ngay lập tức.**

1. **Cấp phát Token (Admin Side):**
   * Admin hệ thống tạo một `Invite Token` dưới định dạng **Signed JWT (EdDSA)**.
   * Payload của JWT chứa: `Org_ID`, `User_Role`, `Timestamp` (Hết hạn trong 24h), và `Blind_Signature` của Admin.
   * Token này được giao cho nhân viên (User) qua kênh an toàn (trực tiếp, SMS...).

2. **Xác thực nội bộ tại Thiết bị (Rust Core Validation):**
   * User dán (paste) Token vào Tauri UI (React). UI lập tức đẩy Token xuống Rust Core qua IPC. UI không được phép lưu Token vào bất kỳ state nào lâu hơn 1 mili-giây.
   * **Rust Core** kiểm tra chữ ký JWT bằng Hardcoded Public Key của tổ chức. Nếu hợp lệ, chuyển sang bước 3.

3. **Sinh Khóa Độc lập (Client-side Key Generation):**
   * Rust Core sử dụng `ring` hoặc `ed25519-dalek` để sinh ra hai bộ khóa:
     * **Identity Keypair (Ed25519):** Dùng để ký định danh thiết bị.
     * **MLS Pre-Keys (X25519):** Dùng để thiết lập session mã hóa E2EE cho tin nhắn.
   * **Nguyên tắc thép:** Private Key VĨNH VIỄN không rời khỏi thiết bị.

4. **Bảo vệ Khóa bằng Phần cứng (Hardware-backed Sealing):**
   * Trước khi ghi vào SQLCipher (Local DB), Private Key phải được bọc (wrap) bằng API bảo mật của Hệ điều hành:
     * **Windows:** Gọi Windows CNG / TPM 2.0 API.
     * **macOS:** Gọi Keychain Services (liên kết Secure Enclave).
     * **Linux:** Giao tiếp qua Secret Service API (libsecret).
   * Sau khi bọc, lưu Master Key bọc cục bộ vào SQLCipher (file DB này cũng được mã hóa bằng thuật toán AES-256-GCM).

5. **Đăng ký với Máy chủ (Blind Registration):**
   * Rust Core đóng gói **Public Keys** (Tuyệt đối không gửi Private Key), kèm theo `Invite Token` gốc làm bằng chứng (Proof of Authorization).
   * Payload được mã hóa đường truyền (TLS 1.3) đẩy lên Identity DB của VPS Cluster.
   * VPS xác thực Token hợp lệ, lưu Public Key của thiết bị vào Database, và trả về `Session_ID`. Lúc này, thiết bị đã chính thức tham gia mạng lưới mù (Blind Relay) và sẵn sàng nhận/gửi tin nhắn E2EE.

#### B. Ràng buộc Kỹ thuật & Bảo mật (Security Constraints)

* **Anti-Replay Attack:** Máy chủ PostgreSQL tại VPS phải ghi nhận Token ID (JTI) ngay khi đăng ký thành công. Bất kỳ nỗ lực dùng lại `Invite Token` lần 2 sẽ bị reject ở tầng gRPC.
* **Memory Zeroing:** Trong Rust Core, mọi biến chứa `Invite Token` hoặc `Private Key` sau khi sinh xong phải được implement trait `Drop` kết hợp crate `zeroize` để xóa sạch dữ liệu khỏi RAM ngay lập tức, chống dump RAM (Cold Boot Attack).

### 7.3. Kiến trúc UI State Management (React ↔ Rust)

Triển khai mô hình Event-Driven triệt để để giảm tải ngốn CPU:

* **Không Polling:** Phía UI (React) tuyệt đối không liên tục gọi vòng lặp kéo (polling) xuống Rust để hỏi có tin nhắn hay không.
* **Push-based Tauri Events:** Rust Core sẽ chủ động bắn `Tauri Event` thẳng lên Window ngay khi bắt được gói tin qua WebSocket và xử lý SQLite thành công.
* **State Management:** React sử dụng Global State (Zustand/Redux) để bắt event và render trạng thái UI tại chỗ.

### 7.4. Cơ chế Upload File (Convergent Encryption / Salted MLE)

Thiết kế luồng tải file bảo mật và tiết kiệm băng thông Server cho Desktop:

* Thiết lập **Salted MLE**, sử dụng `Static_Dedup_Key` làm salt tính hash trước khi chia nhỏ (chunk) đẩy file lên MinIO.
* Đảm bảo cơ chế Deduplication ở Server đạt mức lưu trữ tối thiểu ngay trong bản Alpha nhưng VPS vẫn "mù" do bị Zero-Knowledge. Lấy Zero-byte Stub về máy con thể hiện đã upload/download thành công.
