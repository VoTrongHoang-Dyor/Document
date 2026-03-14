# Function.md — TeraChat: Khả năng Hành động của Từng Vai trò

> *"Bảo mật thực sự không bắt người dùng thay đổi hành vi. Nó bảo vệ họ ngầm, trong khi họ tiếp tục làm việc nhanh hơn, hiệu quả hơn so với bất kỳ công cụ nào họ từng dùng."*
>
> — CEO, TeraChat

TeraChat không chỉ là ứng dụng nhắn tin — đây là **Hệ điều hành Công việc** cho doanh nghiệp đòi hỏi Bảo mật không thỏa hiệp. Mỗi vai trò trong tổ chức — từ Admin, đến nhân viên, đến đối tác liên tổ chức — được trao đúng quyền, đúng công cụ, và đúng mức độ kiểm soát. Không ai có nhiều hơn những gì họ cần. Không ai có ít hơn những gì họ đòi hỏi.

> **Audience:** Product Manager · CEO · Sales Engineer · Customer Success
> **Scope:** Feature capabilities per role — Admin, User, Federation, AI Governance
> **Last Updated:** 2026-03-11

---

### 1. Chức năng dành cho Quản trị viên (Admin)

Admin nắm giữ đặc quyền cấu hình, quản lý vòng đời dữ liệu và thiết lập các hàng rào bảo mật. Các chức năng chính bao gồm:

* **Quản lý Khóa và Định danh (KMS & Identity):**
  * Thiết lập ban đầu với `KMS Bootstrap`, trong đó Admin phải quản lý `Master Key` (in ra giấy / lưu file `.terakey` / YubiKey) để tránh thảm họa "Zero-Access".
  * Phát hành `Invite Token` (Signed JWT) cho nhân viên mới và thực hiện thu hồi quyền (Revoke), tự động kích hoạt `Epoch Rotation` và `Remote Wipe` (xóa dữ liệu từ xa) trên thiết bị nhân viên nghỉ việc.
  * Nắm giữ `Enterprise Escrow Key` (Recovery Key) để giải mã dữ liệu phục vụ điều tra nội bộ hoặc tuân thủ pháp lý.
  * **Thu hồi & Cấp lại Định danh (HR Recovery Delegation):** Admin có thể ủy quyền cấp phát thiết bị mới cho bộ phận HR thông qua SCIM 2.0. HR được cấp role `HR_Recovery_Officer`.
  * **Offline Recovery Flow:** Nhân viên mất máy cầm thiết bị mới đến phòng HR hoặc liên hệ Admin trực tuyến. Admin xác thực Biometric trên thiết bị của chính mình và tạo **Admin-approved QR Key Exchange** (Recovery Ticket đã ký của Ed25519). Người dùng quét QR bằng thiết bị mới, Lõi Rust xác minh Ticket và giải mã `cold_state.db` tải về từ Cloud — không cần mạng Internet hay phần cứng ngoại vi. Nếu không tiếp cận được Admin, dùng **Recovery Phrase (BIP-39 Mnemonic)** làm fallback.
  * **Quy trình Xử lý Khủng hoảng Thiết bị (Device Loss Scenarios):**
    * 💻 ** TH1 (Mất CẢ Laptop & Điện thoại)
      * Multi-Sig Shamir's Secret Sharing Quorum:*

      * 🗄️ **HSM Quorum M-of-N (mặc định 3/5):** `Enterprise_Escrow_Key` được chia thành 5 mảnh Shamir's SSS. Mỗi mảnh giao cho 1 C-Level khác nhau (CEO, CFO, CISO, COO, Legal). Cần đúng **3 mảnh hợp lệ** mới tái tạo được `Escrow_Key`.
      * 📱 **BLE Physical Presence Verification:** Khi CEO khởi tạo Break-glass, thiết bị CEO phát `BreakglassRequest` BLE beacon (Ed25519 signed). Ít nhất **2 thiết bị C-Level khác** phải xác thực sinh trắc học (FaceID/TouchID) và phát `BreakglassApproval` beacon trong phạm vi **< 2m** — chứng minh sự hiện diện vật lý, không thể remote approve.
      * 📱💻 **Quorum Timer (10 phút):** Tất cả approvals phải hoàn tất trong 10 phút từ khi request. Hết timeout → hủy session, yêu cầu restart từ đầu. Ngăn replay attack.
      * 🗄️ **HSM Lagrange Reconstruction (Secure Arena):** Sau khi đủ 3 mảnh, Lõi Rust chạy Lagrange Interpolation trong `mlock`-protected arena (plaintext `Escrow_Key` tồn tại < 100ms) để tái tạo khóa gốc.
      * 📱 **Thiết bị mới phát Remote Wipe:** Sau khi tái thiết lập định danh thành công, thiết bị mới phát lệnh `{Remote_Wipe, Revoke}` tới 2 thiết bị đã mất — `ZeroizeOnDrop` khi chúng chạm mạng.
    * 📱💻 **TH2 (Chỉ mất Điện thoại, Laptop vẫn còn an toàn):**
      * **1. Kiến trúc Cấp phép:**
        Quy trình này loại bỏ việc Laptop tự quyết, buộc mọi thao tác liên quan đến Company_Key phải có chữ ký điện tử (Ed25519) từ tài khoản cấp cao (HR).

        Bước 1: Báo cáo & Khởi chạy Thu hồi (Revocation)

        💻 Laptop (Nhân viên): Nhân viên mở Laptop, vào Device Management và chọn "Report Lost Phone".

        Lõi Rust (Rust Core) ngay lập tức phát lệnh Crypto-Shredding qua giao thức Gossip. Device_Key của chiếc điện thoại cũ bị phế truất khỏi cây khóa E2EE (MLS Group) trên toàn mạng lưới.

        Bước 2: Yêu cầu Ghép nối (CSR - Certificate Signing Request)

        📱 Mobile (Điện thoại mới): Nhân viên tải TeraChat, ứng dụng sinh ra một cặp khóa mới bên trong Secure Enclave/StrongBox. Thiết bị hiển thị mã QR chứa Device_Public_Key và Provisioning_Token.

        💻 Laptop (Nhân viên): Nhân viên dùng Laptop quét QR này. Thay vì bơm Company_Key ngay, Lõi Rust trên Laptop đóng gói thông tin (Bao gồm UUID máy mới + Chữ ký Laptop) và đẩy một Yêu cầu Phê duyệt (Pending Approval) lên ☁️ VPS Cluster (Control Plane).

        Bước 3: Xác thực Định danh (HR Authorization)

        💻 Laptop / 🖥️ Desktop (Bộ phận HR): HR nhận được cảnh báo thời gian thực. HR xác minh nhân viên (qua bộ đàm Voice nội bộ trên TeraChat Laptop, hoặc gọi video xác nhận khuôn mặt).

        Khi HR nhấn "Phê duyệt" (Approve), Lõi Rust của HR sử dụng Admin_Key để ký điện tử vào Yêu cầu, tạo ra một Authorization Ticket (Vé cấp phép) và đẩy OPA Policy cập nhật xuống mạng lưới.

        Bước 4: Bơm Khóa An toàn (Secure Key Injection)

        💻 Laptop (Nhân viên): Nhận được Authorization Ticket đã có chữ ký của HR. Lõi Rust trên Laptop lúc này mới "mở khóa" hàm xuất Company_Key.

        📱💻 Mobile & Laptop: Kênh P2P (BLE 5.0 / Wi-Fi Direct) được kích hoạt. Laptop mã hóa Company_Key bằng Device_Public_Key của điện thoại mới và truyền sang. Quá trình kết thúc.
* **1. Kỹ thuật: OPA Engine & DLP (Data Loss Prevention)**
  * OPA là một engine mã nguồn mở cho phép Admin viết các luật (Rules) bằng ngôn ngữ khai báo Rego. Trong TeraChat, các luật này không nằm chết trên Server mà được mã hóa và đồng bộ thẳng xuống Lõi Rust của từng thiết bị.
  * ☁️ **VPS Cluster / Cloud (Control Plane):** Nơi CISO/Admin định nghĩa các file chính sách Rego. Ví dụ: `allow_launch if user.department == "HR"`. Sau đó, VPS đẩy chính sách này xuống mạng lưới qua kết nối mTLS.
  * 💻 Laptop / 📱 Mobile (Policy Enforcement Point - Điểm thực thi): Lõi Rust (Rust Core) trên thiết bị đóng vai trò là "Cảnh sát chốt chặn" (Enforcer). Trước khi giao diện UI kịp làm bất cứ điều gì, nó phải xin phép Lõi Rust.
  * **Giới hạn tốc độ (Rate Limiting):** Áp dụng thuật toán Token Bucket ngay trên RAM của Client. Nếu một nhân viên sale cố tình cắm tool gửi 10.000 tin nhắn/phút để kéo dữ liệu khách hàng (Data Exfiltration), Lõi Rust sẽ tự động block socket Egress, ngắt mạng cục bộ của app và ghi cờ đỏ vào Immutable Audit Log.
  * **Thời gian lưu trữ tin nhắn (TTL - Time-to-Live):** Đây không phải là lệnh "ẩn tin nhắn" trên UI. Khi TTL hết hạn (ví dụ: 24h), Lõi Rust kích hoạt Crypto-Shredding. Nó ghi đè các byte ngẫu nhiên (Zeroing) lên đoạn khóa giải mã của tin nhắn đó trong SQLite WAL. Tin nhắn vĩnh viễn biến thành chuỗi rác vô nghĩa, không một thế lực nào khôi phục được.

* **2. Cấu hình Hiển thị Launchpad (UI/UX Glassmorphism)**
  * Launchpad là màn hình chính chứa các .tapp (tiện ích mở rộng, ví dụ: Zalo Office, CRM, AI Agent). Việc ẩn/hiện các .tapp này được điều khiển trực tiếp bởi OPA Policy.
  * 📱💻 **Cơ chế Mapping Policy - UI:** Khi người dùng mở Launchpad, Frontend (Tauri/React Native) gửi một truy vấn IPC xuống Lõi Rust: "Tôi có danh sách 10 .tapp, hãy trả về quyền truy cập". Lõi Rust chạy qua OPA Engine và trả về một ma trận Boolean (True/False).
  * **Trải nghiệm Glassmorphism Enterprise:**
    * **Trạng thái Cấp quyền (Online Mode - Sáng):** Các .tapp được phép dùng (ví dụ: HR dùng Zalo Office) sẽ hiển thị nổi khối (Neumorphism) với viền sáng rõ nét, sẵn sàng tương tác.
    * **Trạng thái Vô hiệu hóa (Unauthorized State):** Nếu nhân viên Marketing nhìn thấy .tapp của HR, biểu tượng ứng dụng sẽ bị ép sang màu đơn sắc (Grayscale). Xung quanh app phủ một lớp kính mờ Glassmorphism đục (`backdrop-filter: blur(8px) brightness(0.5)`). Nút bấm bị vô hiệu hóa hoàn toàn ở tầng OS. Khi di chuột vào, một tooltip viền Hổ phách (Amber) hiện lên với thông báo: *"🔒 OPA Policy: Phân quyền truy cập bị từ chối bởi CISO"*
* Cấu hình chính sách cho mạng liên tổ chức (Federation), như thiết lập `allowed_roles` hoặc `allow_reply` để ngăn nhân viên cấp dưới nhắn tin làm phiền Tổng bộ.
* Ràng buộc ứng dụng `.tapp` khởi chạy hoàn toàn trong môi trường cách ly WASM Sandbox tuyệt đối nhằm ngăn chặn mọi hành vi đọc trộm dữ liệu hội thoại từ cửa sổ ứng dụng, các tính năng chống thất thoát dữ liệu (DLP) như chặn copy/paste, chặn kéo thả file.

* **Quản trị Hệ sinh thái Tiện ích (.tapp) & AI:**
* Kiểm duyệt và cài đặt các gói tiện ích nội bộ (Private Sideloading) thông qua chữ ký `Enterprise_CA`.
* **Cấu hình ISDM (Interactive SLM Dual-Masking):** Thiết lập các quy tắc "gutting" (hủy bỏ) dữ liệu nhạy cảm (PII) trên thiết bị người dùng. Admin định nghĩa danh sách Token (ví dụ: Số điện thoại, Email, Địa chỉ) mà SLM cục bộ phải che mặt trước khi gửi tới LLM.
* Quản lý tập trung các API Key (ví dụ: OpenAI) trong `E2EE Secret Vault` mà không làm lộ Key trên máy chủ, sau đó cấp quyền (Cryptographic Binding) cho các AI Bot.
* Định nghĩa cấu trúc dữ liệu đầu vào (JSON Schema) cho các công cụ nghiệp vụ như Smart Order Entry.

* **Nghi thức Kiểm toán & Liên kết Tổ chức:**
* Thực hiện "Nghi thức Kiểm toán Zero-Trust" (N-of-M Audit Ceremony) sử dụng Shamir's Secret Sharing và YubiKey để giải mã dữ liệu khi có yêu cầu pháp lý mà không tạo ra "cửa hậu" (backdoor).
* Tạo và phê duyệt `Federation Invite Token` để thiết lập cầu nối mTLS an toàn giữa cụm máy chủ Tổng công ty và Công ty con.

---

### 2. Chức năng dành cho Người dùng cuối (User/Nhân viên)

Người dùng được trải nghiệm một môi trường làm việc bảo mật tuyệt đối nhưng vẫn đảm bảo tính liền mạch, ngay cả khi gặp sự cố mạng. Các chức năng chính bao gồm:

* **Giao tiếp và Nhắn tin Cốt lõi:**
* Nhắn tin văn bản, gọi thoại/video HD (WebRTC) được mã hóa đầu cuối (E2EE) qua giao thức chuẩn MLS và Signal.
* Tìm kiếm toàn văn bản (Full-text search) siêu tốc độ bằng SQLite FTS5 tại máy trạm mà không làm rò rỉ siêu dữ liệu (Zero-Knowledge Search).

* **Tài liệu thông minh (Smart Document):**
  * 💻📱 **Quy trình demo :** Người sửa với quyền Editor điều chỉnh nội dung trong file của người gửi . Người gửi sẽ kiểm duyệt và đưa ra 3 lựa chọn : Chấp nhận , Từ chối , Gộp.
  * 🗄️ **Phân quyền Granular Role-Based Access Control (RBAC):**
    * **Viewer:** Chỉ được xem.
    * **Commenter:** Bôi đen để ghim chú thích (Không sửa data).
    * **Editor:** Được tạo "Nhánh thay đổi" (Shadow Branch) can thiệp trực tiếp vào chuỗi DAG.
  * 💻📱 **Quy trình Quản lý Nhánh (Author Workflow):** Chỉ người gửi tài liệu (Author) hoặc Admin trong Group mới nhìn thấy Checkbox quản lý hàng loạt commit trong Resolution Pop-up.
  * 💻📱 **Luồng hoạt động Offline không khả thi:**

* **Làm việc Ngoại tuyến & Mạng Lưới (Mesh/Offline-First):**
  * Khi mất kết nối Internet gửi Pop-up hỏi người dùng có muốn kích hoạt mạng Mesh (Survival Link) qua BLE/Wi-Fi Direct để tiếp tục nhắn tin khẩn cấp.
  * Quét mã QR để thiết lập bắt tay bảo mật (Offline X3DH) và truyền file trực tiếp cho đồng nghiệp với tốc độ cao (50-100MB/s) trong môi trường không có mạng LAN hay Wi-Fi Router.
  * 📱 **iOS Alert — Quyền "Local Network":** Khi kích hoạt Mesh lần đầu, hệ thống hiển thị hộp thoại hướng dẫn riêng cho iOS: *"Để tính năng Mạng Mesh hoạt động theo đúng chính sách quyền riêng tư của Apple, vui lòng cấp quyền 'Tìm kiếm thiết bị mạng cục bộ (Local Network)' trong Cài đặt → TeraChat."* Nếu người dùng từ chối, Mesh Mode tự động thu hẹp xuống BLE-only (Gossip Text, không có Wi-Fi Direct file transfer).

* **Quản lý Không gian làm việc và File (TeraVault):**
* Sắp xếp, kéo thả file từ khung chat vào một cây thư mục ảo (Virtual File System) ngăn nắp mà không làm nhân bản dung lượng file.
* Xem trước các file (PDF, CAD, Video) siêu nhanh nhờ cơ chế nạp "vỏ bọc" Zero-Byte Stub (~5KB).
* 📱 **iOS:** Khi tải file dung lượng lớn, TeraChat giao hẳn URL E2EE cho `NSURLSession Background Transfer` để hệ điều hành tự tải ở chế độ nền; sau khi xong, Core Rust giải mã thẳng từ file tạm qua `mmap/pread` và xoá sạch, không cần app phải mở màn hình liên tục.
* 📱 **Xem video không độ trễ:** Thay vì dựng Local HTTP Server `127.0.0.1`, trình phát AVPlayer/ExoPlayer được nối trực tiếp với Lõi Rust qua Native-to-Rust Media DataSource Bridge (AVAssetResourceLoaderDelegate/MediaDataSource). Người dùng chỉ thấy video phát mượt mà, seek tức thì, kể cả khi app bị đưa ra Background theo đúng giới hạn của iOS/Android.

* **Sử dụng Tiện ích và Phê duyệt:**
* Tương tác với các AI Bot ảo trực tiếp trong nhóm chat (bằng cách `@mention`) thông qua giao thức **ISDM (Interactive SLM Dual-Masking)**/API.
* Sử dụng các Mini-App nghiệp vụ (Smart Order, CRM) chạy siêu mượt với độ trễ < 50ms, hỗ trợ Undo/Redo (Time-Travel).
* Ký số và phê duyệt tài liệu nhiều cấp thông qua Smart Approval (Fintech Bridge) có xác thực sinh trắc học.

### 3. Chức năng Tích hợp & Mở rộng (Dành cho Developer/Integrator)

* **Hệ sinh thái API Đa tầng (Tiered API):** Cung cấp hệ thống REST API, WebSocket và Webhook để kết nối với bên ngoài, được chia từ Tier 1 (chỉ gửi thông báo) đến Tier 4 (Bot Builder SDK để phát triển Mini-app).
* **Đồng bộ Nhân sự Tự động (SCIM 2.0 Identity Sync):** Lắng nghe các sự kiện từ hệ thống nhân sự (như Azure AD, Google Workspace). Khi có nhân sự nghỉ việc, SCIM sẽ tự động kích hoạt chuỗi thu hồi quyền (Offboarding Cascade), khóa tài khoản và xóa khóa thiết bị trong chưa tới 30 giây.

  * **Ephemeral OIDC State Pinning & Pre-authenticated Key Provisioning (Race Condition Fix):**

  > **Vấn đề Race Condition:** Trong luồng SSO truyền thống, Device Key chưa được sinh ra tại thời điểm OIDC token được cấp phát — tạo cửa sổ thời gian khoảng 200–800ms mà kẻ tấn công Man-in-the-Middle có thể thế vào.

  * 📱💻 **1-Tap Magic Deep-Link (Pre-auth Key Binding):** Thay vì redirect sang browser, TeraChat gửi một `magic_deep_link` tới email/SMS của nhân viên mới. Link nhúng `pre_auth_token = HKDF(SCIM_Provisioning_Key, email || timestamp || nonce)`. Khi nhân viên mở link, app tự đặt thiết bị vào trạng thái `pre_authenticated` — Rust Core sinh `Device_Key` ngay lập tức và bind vào `pre_auth_token` trước khi OIDC flow hoàn tất.
  * 📱 **iOS Native OIDC PKCE (prompt=none):** Trên iOS, dùng `ASWebAuthenticationSession` kết hợp cờ `prompt=none` để bypass hiển thị login UI khi đã có token hợp lệ. `state` parameter được pin vào `Device_Key` public hash — Server reject mọi `state` không khớp với device fingerprint đã đăng ký.
  * ☁️ **SCIM 2.0 Offboarding Cascade (< 30s SLA):**
    1. HR trigger `DELETE /Users/{scim_id}` → SCIM API
    2. TeraChat SCIM Listener nhận event → emit `revoke_all_device_sessions(user_id)` vào Kafka topic
    3. Kafka Consumer tại mỗi VPS node flush `Device_Key` + `Session_Key` cho user đó → `ZeroizeOnDrop`
    4. Lõi Rust tại thiết bị nhân viên nhận Push `SESSION_REVOKED` → ghi đè local key store `0x00` → app lock screen
  * ☁️ **SCIM Race Condition Guard:** Server-side SCIM Listener kiểm tra `provision_timestamp` của `Device_Key` phải nằm trong cửa sổ `[oidc_issue_time - 5s, oidc_issue_time + 5s]`. Ngoài cửa sổ → reject provisioning → force re-enrollment.

* **Cổng Tích hợp Đồng thuận (Consent-Driven Bridge):** Quản lý luồng giao tiếp với các ứng dụng bên thứ 3 (Jira, Zoom, Salesforce) thông qua một Bot trung gian (Egress Worker). Hệ thống sẽ hỏi ý kiến (Consent) của Admin trước khi tạm thời giải mã E2EE trên RAM VPS để gọi API ra ngoài.
* **ChatOps & Secure Tunneling:** Cung cấp đường hầm bảo mật cho phép kỹ sư hệ thống truy cập SSH/RDP thẳng vào các máy chủ nội bộ thông qua TeraChat mà không cần thiết lập VPN truyền thống.

### 4. Chức năng Vận hành & Cứu hộ (Dành cho DevOps/SecOps)

* **Graceful Degradation & Circuit Breaker (Quá tải RAM NSE):** Tự động bảo vệ mức RAM eo hẹp 24MB của tiến trình xử lý thông báo ngầm (iOS NSE/Android FCM). Nếu payload mã hóa đẩy về quá lớn (như đợt xoay vòng khóa Epoch Rotation cho group chat 50,000 người) dẫn đến nguy cơ tiêu thụ bộ nhớ vượt 20MB, Micro-Core tự động kích hoạt Circuit Breaker chặn luồng giải mã ngầm, giúp tránh OOM-Kill. Thay vào đó, hệ thống chỉ đánh thức Lõi Rust tiêu chuẩn vào lúc người dùng mở App ở Foreground (nơi trần RAM cho phép lên đến 2GB) để đảm bảo an toàn tuyệt đối.
* **Khôi phục Thảm họa Cơ sở dữ liệu (PostgreSQL PITR):** Chức năng "cỗ máy thời gian" thông qua WAL Archiving. Nếu Admin vô tình chạy lệnh xóa nhầm dữ liệu, hệ thống có thể dựng lại nguyên vẹn Database về đúng một mốc thời gian cụ thể (ví dụ: 14:03:00) dựa trên các log được sao lưu định kỳ.
* **Auto-Healing VMS (Tự phục hồi Vùng Dàn dựng Tạm — iOS NSE/Main App Desync):**
  * 📱 **Trigger:** Lõi Rust phát hiện `nse_staging.db` chứa entry có `status="PENDING"` từ lần bootstrap trước — dấu hiệu Main App bị crash hoặc Force Kill giữa Two-Phase VMS Drain. Hệ thống tự động khởi động quy trình tự phục hồi mà không cần người dùng biết.
  * 📱 **Phase 1 — Integrity Scan:** Chạy `PRAGMA quick_check(1)` trên `nse_staging.db`. Nếu `OK` → tiến hành re-decrypt và merge pending entries vào `hot_dag.db`. Nếu `Err` → kích hoạt Crypto-Shredding `POSIX unlink()` + zero-fill và cuộc phục hồi chuyển sang Phase 2.
  * 📱☁️ **Phase 2 — Gossip Re-hydration:** Sau khi staging DB sạch, Lõi Rust phát `GossipStateRequest` siêu nhẹ để pull lại các tin nhắn bị mất trong khoảng Gap từ Super Node. User không mất tin nhắn, không cần thao tác thủ công.
  * 📱 **Transparency:** DevOps/SecOps có thể theo dõi quá trình Auto-Healing qua Observability Pipeline entry log `AUTO_HEAL_VMS_TRIGGERED` kèm `device_id`, `gap_size`, và `recovery_status`.
* **Lưu trữ Tự chủ (BYOS - Bring Your Own Storage):** Không ép buộc Doanh nghiệp dùng Cloud của TeraChat. Hệ thống tích hợp chuẩn S3-Compatible (MinIO), cho phép IT tự cắm thêm ổ cứng vật lý để mở rộng dung lượng và lưu trữ lịch sử vô hạn (Infinite Retention).

### 5. Chức năng "Tàng hình" của Lõi Rust (Cấp Hệ thống)

* **Truyền tải Đa đường (TeraLink Multipath):** Tự động nhân bản các gói tin nhỏ (như lệnh đồng bộ CRDT) và gửi song song qua cả 3 đường: 4G/5G, Wi-Fi LAN, và BLE Mesh. Giúp hệ thống đạt độ trễ 0ms khi người dùng di chuyển chuyển vùng mạng (Roaming).
* **Trạm Trung chuyển Dữ liệu AI (Predictive Data Mules):** Khi hệ thống rớt mạng diện rộng, lõi Rust chạy mô hình học máy (Edge ML) để phân tích thói quen di chuyển của nhân viên. Dữ liệu sẽ ưu tiên gửi gắm vào máy của những người có tỷ lệ gặp người nhận cao nhất (ví dụ: gửi tài liệu sếp qua máy của trợ lý) thay vì gửi rác mù quáng.
* **Bẫy Hắc Ín chống DDoS (Infinite Tarpit):** Bức tường lửa thông minh bảo vệ máy chủ. Nếu có kẻ tấn công gửi Request vượt hạn mức hoặc sai chữ ký TLS Fingerprint, hệ thống không từ chối ngay mà "treo" kết nối đó, cứ 10 giây mới nhả 1 Byte rác để làm cạn kiệt RAM của kẻ tấn công.
* **Puncturing Stream (Phục hồi luồng tệp đứt gãy):** Khi truyền file lớn (ví dụ: 2GB) qua Wi-Fi Direct mà bị nhiễu sóng (như do lò vi sóng, thiết bị công nghiệp), hệ thống đánh dấu đoạn bị lỗi là "Thủng" (Punctured) và gửi tiếp phần còn lại, sau đó tự động vá lại đoạn hỏng ở cuối phiên thay vì phải gửi lại từ đầu.
* `💻` **FFI Pointer Freezing & Authorization Gateway:** Tự động giải mã Policy_Packet và kiểm tra chữ ký. Đối với Viewer, Lõi Rust lập tức đóng băng (lock) các con trỏ hàm FFI liên quan đến tạo Proposal, ngăn ngụy tạo lệnh từ UI. Đối với Commenter, chỉ mở khóa hàm `ffi_propose_comment`. Đối với Editor, cấp quyền `ffi_propose_change` cho phép chỉnh sửa cục bộ. Lập tức gọi `ZeroizeOnDrop` để dọn dẹp RAM khi phát hiện yêu cầu trái phép.

### 6 Chức năng cho hệ thống Liên tổ chức

## 1. Kiến trúc Độc lập và Cầu nối (Zone 2 Routing)

* Tổng công ty (`Org_ID_HQ`) và Công ty con (`Org_ID_Sub`) là hai thực thể pháp lý độc lập, mỗi bên sở hữu một Private Cluster riêng biệt.
* Luồng giao tiếp giữa HQ và Chi nhánh bắt buộc đi qua **Federation Bridge (Zone 2)** thông qua xác thực mTLS (Mutual Auth) và giao thức Sealed Sender (ẩn danh tính người gửi khỏi trạm trung chuyển).
* **Chủ quyền dữ liệu (Data Sovereignty):** Dữ liệu của HQ ở lại máy chủ HQ, dữ liệu của Chi nhánh ở lại máy chủ Chi nhánh, trạm Federation Bridge ở giữa chỉ chuyển tiếp gói tin mã hóa (Blind Relay) chứ không lưu trữ.

## 2. Quá trình Kết nối Chi nhánh (Cross-Cluster Trust Handshake)

Quá trình kết nối hai công ty diễn ra hoàn toàn an toàn mà không cần đồng bộ Database:

* **Bước 1:** Admin Tổng công ty tạo một mã **Federation Invite Token** (bản chất là một Signed JWT chứa URL của HQ, Public Key và có hạn 24h) rồi gửi cho Admin Chi nhánh qua kênh ngoài (email, điện thoại).
* **Bước 2:** Admin Chi nhánh nhập Token này vào hệ thống của mình để gửi yêu cầu kết nối (Connection Request) chứa Public Key của Chi nhánh sang HQ.
* **Bước 3:** Admin Tổng công ty bấm "Phê duyệt", hai máy chủ trao đổi Public Key và lưu vào sổ cái tin cậy (`federation_trust_registry`). Từ đây, hai bên có thể nhắn tin chéo cho nhau.

## 3. Kiểm soát Đặc quyền và Chống làm phiền (OPA Routing Policy)

Để tránh tình trạng nhân viên Chi nhánh nhắn tin ồ ạt làm phiền lãnh đạo Tổng bộ, Admin Chi nhánh có thể thiết lập các bộ lọc (Policy) thông qua OPA:

* Có thể giới hạn chỉ những người có Role cụ thể (như `Director`, `Manager`, `Branch_Admin`) mới được chủ động khởi tạo tin nhắn sang HQ.
* Nhân viên bình thường vẫn có thể trả lời (reply) nếu người từ HQ chủ động nhắn tin trước.
* Hệ thống có thể giới hạn tần suất nhắn tin liên tổ chức (ví dụ: 20 tin nhắn/giờ).
* `☁️` **Token Bucket Group-Based Rate Limiting & Edge-Level Malicious Packet Dropping:** VPS duy trì Token Bucket cho mỗi Document. VPS liên tục kiểm tra tần suất nhận PROPOSE_CHANGE. Nếu vượt ngưỡng (vd: 50 Đề xuất/phút), VPS thẳng tay rớt (drop) gói tin ngay tại trạm trung chuyển để bảo vệ thiết bị cuối khỏi tấn công DoS.

## 4. Thu hồi quyền liên tổ chức (Offboarding Cascade)

* Khi một nhân viên Chi nhánh nghỉ việc hoặc bị sa thải, Admin Chi nhánh thao tác trên hệ thống nội bộ, bộ lắng nghe SCIM sẽ lập tức khóa tài khoản và xóa khóa thiết bị.
* Ngay khi mất quyền ở Chi nhánh, nhân viên đó **tự động mất luôn quyền truy cập vào kênh mTLS sang HQ trong vòng chưa tới 30 giây**.
* Điểm hay của kiến trúc này là Tổng công ty không cần biết nhân viên Chi nhánh bị đuổi, hệ thống của Chi nhánh sẽ tự dọn dẹp và ngắt luồng liên lạc.

---

## 5. Kiểm soát AI Privacy Shield (Admin/CISO Console)

Admin/CISO là người duy nhất có quyền sinh sát đối với dòng chảy dữ liệu ra ngoài khi sử dụng tính năng `@ai`. Hệ thống không cấm đoán toàn bộ mà cung cấp 3 mức cấu hình linh hoạt:

### Mức 1 — Strict Compliance (Mặc định)

* AI Shield bắt buộc bật vĩnh viễn. Không một role nào được phép tắt.
* Ứng dụng: Khối ngân hàng, bệnh viện (HIPAA), cơ quan nhà nước.
* Kỹ thuật: OPA Policy trả về `allow: false` cho mọi `toggle_shield: true` request bất kể role.

### Mức 1b — Strict Compliance Network Mode (Tùy chọn Mạng)

> **Mục đích:** Tối ưu kết nối cho tổ chức đã biết chắc Firewall DROP UDP — bỏ qua bước thăm dò 50ms, kết nối thẳng TCP.

* 📱💻 **Kích hoạt:** Admin Super bật toggle `Strict Compliance Network Mode` trong CISO Console → OPA Policy push xuống tất cả thiết bị tenant trong < 30s (Kafka broadcast).
* 📱💻 **Hành vi Client khi bật:** Lõi Rust bỏ qua Step 1 (QUIC/UDP probe) hoàn toàn. Kết nối thẳng bằng **gRPC over HTTP/2 (TCP 443)** ngay từ đầu — tiết kiệm 50ms probe time, tối ưu 100% cho môi trường Firewall Enterprise được kiểm soát chặt.
* 📱💻 **Hành vi Client khi tắt (mặc định):** Lõi Rust thực thi ALPN State Machine tự động (QUIC → gRPC → WebSocket) — phù hợp cho thiết bị di động dùng 4G/5G.
* ☁️ **Audit:** Mọi thay đổi `network_mode` được ký `Ed25519` và ghi vào Tamper-Proof Audit Log. Không thể thay đổi mà không để lại dấu vết.

### Mức 2 — Role-Based Risk Acceptance (Chấp nhận Rủi ro theo Vai trò)

* Admin cấp quyền `can_toggle_shield: true` cho các nhóm cụ thể (VD: `Role: Marketing`, `Role: C-Level`, `Role: R&D`).
* Nhân viên các phòng ban được cấp phép khi gõ `@ai` sẽ thấy công tắc Shield có thể gạt sang OFF để lấy bối cảnh sâu nhất cho Prompt.
* **Non-Repudiation Audit:** Mọi truy vấn khi tắt Shield bị gán cờ cảnh báo, lưu Plaintext Hash vào Tamper-Proof Audit Log (Ed25519 Signed) để quy trách nhiệm pháp lý nếu xảy ra rò rỉ dữ liệu.

### Mức 3 — DLP Threshold (Chốt chặn cuối — không thể bypass)

* Ngay cả khi Admin cho phép tắt Shield, Lõi Rust vẫn áp dụng **Byte-Quota Circuit Breaker**.
* Nếu độ dài Payload > 4KB (tương đương ~1 trang A4 văn bản thô) → Lõi Rust tự động ngắt và trả lỗi: `"Khối lượng dữ liệu quá lớn. Vui lòng bật AI Shield hoặc cắt ngắn văn bản để chống Data Dumping."`
* Kỹ thuật: OPA Policy Engine tại Rust Core check `payload_size > 4096 bytes` tại thời điểm IPC Bridge truyền Prompt — không thể bypass từ WASM Sandbox.

### ECRP — AI Context Switch: Định nghĩa & Luồng Quyền

> **"Công tắc này không nhả Khóa mã hóa. Nó chỉ cấp quyền cho Lõi Rust thực hiện Dual-Masking Plaintext trong giới hạn 4KB và gửi vào TEE Sandbox."**

**Cơ chế hoạt động (ECRP — Encrypted Context Relay Protocol):**

* 📱💻🖥️ **Bước 1:** UI gửi lệnh `Request_AI_Context(Depth: 50_messages)` xuống Lõi Rust qua JSI/FFI. UI **không cầm** plaintext — chỉ gửi intent.
* 📱💻🖥️ **Bước 2:** Lõi Rust dùng `Session_Key` (đang nằm trong RAM an toàn — `mlock` trên Desktop, `ZeroizeOnDrop` trên Mobile) để giải mã N tin nhắn thành Plaintext cục bộ.
* 📱💻🖥️ **Bước 3:** Lõi Rust chạy Local ONNX NER Model để quét và tokenize toàn bộ PII thành `[MASK_01]`, `[MASK_02]`. Bảng ánh xạ tồn tại trong RAM — không persist xuống disk.
* 📱💻🖥️ **Bước 4:** Lõi Rust đóng gói đoạn hội thoại đã mask vào `EgressNetworkRequest` (Protobuf), mã hóa TLS 1.3 và gửi thẳng vào vùng TEE (Intel SGX / AWS Nitro) của máy chủ AI.
* 📱💻🖥️ **Bước 5:** AI trả về response chứa `[MASK_01]`. Lõi Rust ánh xạ ngược `[MASK_01]` → tên thật, đẩy lên UI Renderer qua `StateChanged` IPC. `SessionVault` bị `ZeroizeOnDrop` ngay sau đó.

**Quyền gạt công tắc theo 3 mức Admin:**

| Mức | Admin Policy | Hành vi Công tắc |
| --- | ------------ | ---------------- |
| Strict | `allow_toggle: false` toàn tenant | Công tắc hidden/disabled. AI Shield bắt buộc ON. |
| Role-Based | `can_toggle_shield: true` cho nhóm cụ thể | Công tắc gạt được — nhưng mỗi lần tắt bị Ed25519 Audit Log ghi nhận. |
| DLP Threshold | Luôn bật bất kể Mức 1/2 | Byte-Quota Circuit Breaker: hard-block nếu payload > 4KB. Không bypass. |

**Thông số Hiệu năng:**

* Latency Masking: ~150–200ms (ONNX Local NER). Chấp nhận được cho AI chat flow.
* Throughput: Giới hạn 4KB/request — chống Data Exfiltration diện rộng.
* Attack Surface: Khóa không di chuyển. Plaintext RAM bị `ZeroizeOnDrop` ngay khi nhận HTTP Response từ AI.

### 6. Trải nghiệm Giao tiếp Thích ứng Không gian (3-Tier Adaptive Communication)

* **Fallback Voice Recording — Codec Tự động Hạ cấp theo Tier:**
  * **Tier 1 (Online):** Ghi âm chuẩn Opus 128kbps Stereo — chất lượng đầy đủ.
  * **Tier 2 (Offline Near — Wi-Fi Direct):** Codec tự động chuyển sang **AMR-NB 4.75kbps Mono**. File ghi âm 1 phút chỉ nặng ~35KB, đảm bảo lọt qua khe hẹp Mesh. Người dùng vẫn nghe được giọng nói dù chất lượng thấp hơn — tốt hơn là không nhận được gì.
  * **Tier 3 (Offline Far — BLE Long Range):** Nút Micro bị **vô hiệu hóa hoàn toàn** từ UI. Lõi Rust (tùy chọn) gọi Whisper AI cục bộ để tự động phiên dịch file ghi âm đang chờ trong `cold_state_shadow.db` thành Text và gửi E2EE qua BLE.

* **Auto-Pause Media — Chặn từ gốc ở Tier 3:** Khi `Network_State_Machine` phân loại kết nối là Tier 3, Lõi Rust phát signal `MediaUnavailable(tier=3)` về IPC bridge TRƯỚC khi UI render lượt tiếp theo. Icon Camera/File ngay lập tức bị Disabled (không phải Greyed-out mà là bị xóa khỏi Input Bar hoàn toàn theo UI State Machine §15). Người dùng không thể cố chèn file/ảnh ngay cả bằng cách paste từ clipboard.

### 7. Quản trị Agentic & Tuân thủ (Admin — Agentic Federation Management)

* **Cài đặt Agent cho Toàn tổ chức:** Admin có quyền deploy `.tapp` OpenClaw (hoặc bất kỳ AI Agent OAP-compatible nào) cho toàn công ty qua Admin Console. Agent được phân phối qua Federation Bridge — không cần người dùng tự cài.

* **Redaction Rules (Luật Bôi đen trước khi bay ra ngoài):**
  * 💻📱 Trước khi Lõi Rust đẩy prompt ra **OpenClaw API**, một thư viện **Regex + NER (Named Entity Recognition) nhẹ** chạy tại biên thiết bị tự động thay thế chuỗi nhận dạng:
    * Số thẻ tín dụng → `[REDACTED_CC]`
    * Số CMND/Passport → `[REDACTED_ID]`
    * Địa chỉ Email nội bộ → `[REDACTED_EMAIL]`
  * Admin cấu hình Redaction Rules qua JSON Policy. Có thể tùy chỉnh theo từng phòng ban (HR được phép gửi EMAIL, Finance không được phép gửi CC).
  * **Kết quả:** Dữ liệu đã được "làm sạch" trước khi rời thiết bị. AI Agent hoạt động tốt mà không nhận thấy sự can thiệp. Không cần điều kiện ngoại vi phức tạp từ phía API bên ngoài.

* **🗄️ Agentic Audit Log:** Mọi lần `.tapp` gọi `send_agent_request()` đều được Lõi Rust ghi vào Tamper-Proof Audit Log (Ed25519 Signed): `{timestamp, user_id, agent_endpoint, payload_hash, consent_token}`. CISO/Admin có thể query log bất kỳ lúc nào để audit AI usage mà không cần giải mã nội dung.

* **🗄️☁️ CISO Audit Log Dashboard — Non-Repudiation (Chống chối bỏ):**

  > **Mục đích:** Khi API đối tác thứ ba (vd: OpenAI) bị lộ dữ liệu, CISO có bằng chứng mật mã học định danh chính xác thiết bị nào, người dùng nào, lúc nào đã gạt công tắc AI Context và trigger Egress — không ai có thể chối bỏ.

  * ☁️🗄️ **Truy xuất Ed25519 Audit Chain:** Admin/CISO mở TeraChat Console → vào mục `AI Egress Audit` → thấy danh sách từng `Audit_Log_Entry`: `{device_id, user_id, timestamp, payload_hash (BLAKE3), ed25519_sig, shield_state}`.
  * ☁️ **Signature Verification:** Console tự động verify chữ ký `ed25519_sig` đối với `payload_hash`. Entry nào bị tamper hoặc sig không khớp → đánh dấu `INTEGRITY_VIOLATION` màu đỏ.
  * 🗄️ **Cross-reference API Leak:** Nếu provider AI báo cáo incident, CISO export Audit Chain và đối chiếu `payload_hash` với dữ liệu bị lộ — xác định thiết bị nguồn trong vài giây.
  * ☁️ **Filter & Search:** Có thể lọc theo `user_id`, `date_range`, `shield_state` (ON/OFF), `egress_size_kb`. Role CISO-only — Admin thường không có quyền xem raw hash list.
  * 📱💻🖥️ **Không lộ nội dung:** Toàn bộ Dashboard chỉ hiển thị `payload_hash` — không decrypt, không hiển thị plaintext message. Privacy được bảo toàn trong khi Non-Repudiation vẫn đảm bảo.

### 8. Non-Repudiation Egress Telemetry & Signed Audit Logs

* **🗄️ Signed Audit Log (Ed25519):** Mỗi sự kiện Egress (dữ liệu rời thiết bị sang AI Agent) được Lõi Rust ký bằng `Device_Ed25519_Key` và ghi vào Tamper-Proof Audit Chain cục bộ. Chuỗi log không thể xóa hoặc sửa mà không phá vỡ chữ ký. Admin có thể export và verify offline bằng public key.
* **☁️ ISO 27001 Mapping (A.13.1):** Audit log được cấu trúc theo chuẩn ISO 27001 Annex A.13.1 (Information Transfer Policies). Mỗi record chứa: `{event_id, timestamp_utc, user_id_hash, agent_endpoint_hash, payload_size_bytes, consent_token, signature}`. Đủ điều kiện cho SOC2 Type II audit evidence mà không cần expose nội dung chat.
* **📱💻 Byte-Quota Circuit Breaker:** Admin cấu hình `max_daily_egress_mb` per user. Lõi Rust tracking real-time. Khi user đạt 80% quota → UI cảnh báo nhẹ. Khi đạt 100% → Lõi Rust hard-block tất cả Egress calls cho user đó trong 24h. Chống Data Exfiltration qua AI interface.
* **☁️ Control Plane Telemetry (Aggregated, Non-PII):** VPS Control Plane nhận aggregated metrics: `{group_id, total_egress_mb_today, taint_event_count, consent_denial_rate}`. Không có nội dung chat; chỉ metadata thống kê để CISO dashboard monitoring.

### 9. Poisoned Agent Remote Alerting (PARA) — Phản ứng Sự cố AI Bị Compromise

* **🗄️☁️ E2EE Signed Incident Hash:** Khi SASB phát hiện `taint_count > 3` trong một session, Lõi Rust tạo `Incident_Hash = SHA3-256(session_id || taint_events || timestamp)` và ký bằng `Device_Ed25519_Key`. Incident Hash được gửi sang VPS Control Plane qua E2EE channel — Server không biết nội dung, chỉ biết có incident.
* **☁️ Control Plane Alerting Pipeline:** VPS nhận Incident Hash, cross-reference với `agent_endpoint` trong registry. Nếu cùng một `agent_endpoint` bị báo incident từ ≥ 3 thiết bị khác nhau trong 1 giờ, Control Plane kích hoạt pipeline: gửi alert E2EE đến CISO (Admin Super), đánh dấu `agent_endpoint` là `SUSPICIOUS` trong registry.
* **☁️ Automated Agent Suspension Protocol:** CISO nhận alert và có thể kích hoạt "Emergency Suspend" cho `.tapp` đó: Control Plane push `REVOKE_TAPP { tapp_id, signature }` bundle đến tất cả thiết bị trong tenant. Lõi Rust nhận bundle → verify signature → terminate `.tapp` ngay lập tức, xóa `cold_state_shadow.db` của session liên quan. Không cần app update hay store review.

### 10. Centralized Semantic Lexicon Injection (OPA Banned Lexicon)

* **🗄️☁️ OPA Banned Lexicon Policy:** CISO/Admin định nghĩa danh sách cấm (Banned Lexicon) qua CISO Console — danh sách từ khóa, entity pattern, hoặc intent category bị cấm tuyệt đối trong các `.tapp` AI session. Policy được compile và push xuống tất cả thiết bị qua Federation Bridge như một OPA Rego bundle.
* **☁️ Remote Agent Suspension Protocol:** Nếu một AI Agent `.tapp` vi phạm Lexicon Policy > 3 lần trong 1 giờ (cross-device threshold), Control Plane tự động suspend `.tapp` đó theo PARA protocol (§9) — không cần CISO can thiệp thủ công.
* **📱💻 Local Mute-lock Trigger:** Khi Banned Lexicon match được phát hiện trong tin nhắn đến từ AI Agent, Lõi Rust inject `MUTE_LOCK` signal qua JSI/FFI: Agent bubble bị collapse (Magnetic Collapse animation §25), input bar bị disable, session hiển thị banner `"Nội dung vi phạm chính sách. Session bị tạm khóa."` — user phải contact Admin để mở khóa.

### 11. Enforced Anti-Remanence Policy (ARP) — Checkpoint Governance

* **🗄️☁️ Admin-enforced TTL (CISO Console):** Admin Super cấu hình TTL toàn tenant cho AI Checkpoint: `{min_ttl: 1h, max_ttl: 7d, default_ttl: 24h}`. Thiết bị nào có TTL setting cao hơn policy sẽ bị CISO Console override. User không có quyền thay đổi TTL.
* **☁️ Remote Wipe Command (Ed25519):** CISO có thể kích hoạt Remote Wipe cho toàn tenant hoặc user cụ thể: push `WIPE_CHECKPOINT { scope: "all"|user_id, timestamp, Ed25519_signature }` qua Control Plane. Thiết bị nhận lệnh → verify signature → chạy Hierarchical Crypto-Shredding (§5.35 Core_Spec) trên tất cả Checkpoint còn tồn đọng trong vòng 30 giây.
* **🗄️ Forensic-proof Deletion (Zero-fill):** Mọi hành động wipe theo ARP phải được ghi vào Tamper-Proof Audit Log với proof: `[ARP_WIPE | user_id | device_id | checkpoint_count | wipe_method | completion_timestamp | Ed25519_signature]`. Đủ điều kiện trình diện cơ quan điều tra kỹ thuật số (Digital Forensics).

### 12. Autonomous Conversation Sealing & CISO Alerting (SSA)

* **📱💻 Session-lock Trigger:** Khi SSA Retroactive Taint kích hoạt (§5.36 Core_Spec), Lõi Rust thực hiện `session_seal()`: freeze toàn bộ conversation — người dùng không thể gõ thêm, không thể scroll lên cũ (data protection), không thể copy bất kỳ nội dung nào từ conversation bị tainted. Chỉ có thể xem sealed messages qua read-only view với Hazard-Stripe overlay.
* **🗄️ Ed25519 Signed Quarantine Log:** Khi seal xảy ra, Lõi Rust tạo `Quarantine_Record = {session_id, sealed_messages: [hash1, hash2, ...], taint_trigger, timestamp}` và ký bằng `Device_Ed25519_Key`. Record được lưu cục bộ và sync lên Control Plane qua E2EE channel (Server chỉ thấy signed blob, không thấy nội dung).
* **☁️ Control Plane Incident Escalation:** Control Plane nhận signed Quarantine Record → forward E2EE đến CISO dashboard. CISO thấy: "Conversation Sealed on [device] at [timestamp] — Taint: SOCIAL_ENGINEERING (score: 0.82) — [Review Details]". CISO quyết định: `[Release Session]` (nếu false positive) hoặc `[Escalate to Security Team]` (nếu confirmed attack).

### 13. "The Red Pill" — Luồng Kích hoạt Truyền Context gốc (FCP Admin Flow)

* **Admin Console Trigger:** Admin/CISO phải cắm Hard-Token (YubiKey) thứ 2, chọn một Contextual Room (Phòng đặc biệt) và nhập tay chuỗi ký tự `"I_ACCEPT_LIABILITY_FOR_THIRD_PARTY_AI_LLM_EGRESS"`.
* Lõi Rust sinh Token FCP Ed25519 (TTL 1 tuần) và phát sóng CRDT Update cho toàn bộ các thành viên trong Scope Room. Quá trình FCP kích hoạt UI Red Border ngay lập tức trên tất cả Client có mặt trong phòng theo §26 của `Design.md`.
* Bất kỳ thành viên nào tham gia phòng đều bắt buộc văng Modal "Hành trang qua biên giới" — Yêu cầu FaceID hoặc Passcode để đọc cảnh báo Egress. Xác nhận = Vào phòng (FCP ON), Từ chối = Kick.

* **📱💻 Liability Shift Confirmation Flow:** Khi Admin gạt công tắc: (1) Màn hình confirmation xuất hiện, Admin phải gõ chính xác chuỗi `"I_ACCEPT_LIABILITY"` trong text field (không phải checkbox), (2) Admin phải xác thực bằng YubiKey hoặc Biometric, (3) Lõi Rust tạo `FCP_Consent_Record = {admin_id, tapp_id, timestamp, consent_phrase_hash, biometric_signature}` và ký bằng `Admin_Ed25519_Key`. Record không thể xóa.
* **☁️ CRDT Broadcast & Scope Isolation:** Sau khi consent được ghi nhận, cờ `FCP_Enabled = true` cho `.tapp` cụ thể được broadcast qua CRDT Mesh đến tất cả thiết bị trong tenant. FCP scope được isolate: chỉ OpenClaw.tapp có FCP — các `.tapp` khác vẫn chạy với full security. Admin có thể revoke FCP bất kỳ lúc nào; revocation broadcast ngay lập tức.

### 14. Mở khóa dựa trên Đặc quyền và Ngữ cảnh (Privilege-Based Context-Aware Bypass - PCAB)

* ☁️🗄️ Backend cấp phát Contextual Role thông qua Rego (OPA Policies), đánh giá đa biến: Geolocation hiện tại (Văn phòng hay Mạng Public IPv4), Vai trò Admin, và Mức độ Nhạy cảm của Dữ liệu.
* 📱💻 Client Rust Core buộc người dùng Unmask (Gỡ mặt nạ phân cách) cho những Document/Agent bị Quarantine. Lõi yêu cầu thao tác Password-Backed Authentication theo chuẩn Argon2id để thu hồi khóa Vault tạm gỡ niêm phong Acrylic.
* 🖥️📱 Truy xuất Thành công: Giao diện thực thi Shatter Animation (Kính vỡ), nội dung mở ra nguyên vẹn. Thất bại: Trigger Remote Wipe hoặc tự hạ gục (Self-Destruct) Document ngay trước mắt user.

### 15. Hệ thống Chính sách Phân phối Tệp (OPA-driven Format Whitelisting)

* 🗄️ Khởi tạo OPA Policy Enforcement tại Admin Control Plane. Quản trị viên sử dụng cú pháp Rego để định nghĩa tuyệt đối danh sách "Bán kính Nổ An toàn" (`.pdf`, `.txt`, `.jpg`).
* ☁️ Chặn tức thì ở cấp độ Phân phối (Distribution Tier) mọi luồng Macro Document (`.docm`, `.xlsm`, `.vbs`, `.sh`) từ User ra mạng. Các Tệp định dạng không được duyệt (Whitelist Fail) không thể tham gia vào chuỗi MLSTree_KEM.
* 🗄️ Kích hoạt Incident Response (IR) Email Báo động đỏ tự động gắn cờ tài khoản vi phạm và tạm ngừng Token của User nếu tỷ lệ tải tệp vi phạm lớn hơn 5 tệp / phút.

### 16. Chống Nội gián trong Nghi thức Khôi phục (Anti-Insider Key Ceremony)

> **Mục tiêu:** Ngăn chặn bất kỳ nhân viên nội bộ nào đơn phương thực hiện khôi phục chứng chỉ (Anti-Insider Key Ceremony) mà chưa có sự phê duyệt đa bên.

* 📱 **BLE Approval Beacons (Tín hiệu chứng thực từ thiết bị di động lãnh đạo):** Qua trìình kích hoạt HSM chỉ mở khi có Beacon BLE từ ít nhất 2 trong N thiết bị di động thuộc C-Level (CEO, CISO, CFO) trong phạm vi 5m; thiếu Beacon → HSM từ chối mọi thao tác ký.
* 📱 **Hardware Biometric Validation (FaceID/TouchID):** Mỗi lãnh đạo phê duyệt bằng Biometric tại thiết bị của chính mình; chữ ký sinh trắc học được bắt buộc trước khi chuyển BLE Approval Beacon — không thể giả mạo bằng replay.
* 🖥️ **Multi-Sig Authorization Gate (Mở I/O USB khi đủ điều kiện 2-of-N):** HSM chỉ mở kênh USB ghi chứng chỉ mới sau khi nhận đủ 2-of-N chữ ký BLE; nếu chỉ có 1 cá nhân thò tay vào — kênh USB khóa vĩnh viễn.

---

### 17. Quản lý Sự cố và Khôi phục (Incident Response)

> **"Phản ứng tức thì khi phát hiện xâm nhập. Hệ thống tự động chuyển sang trạng thái phòng thủ, phong tỏa dữ liệu và làm sạch vết tích nhạy cảm trong khi duy trì kênh liên lạc cứu hộ."**

* 🖥️ **Incident Response Flow & Live Metadata Sanitization:**
  * 🖥️ **Mesh Mode Hard-lock UI (#0F172A Amber Glow):** Khi phát hiện sự cố bảo mật nghiêm trọng hoặc lệnh từ Admin, thiết bị tự động kích hoạt Hard-lock UI. Màn hình chuyển sang màu xanh đậm (#0F172A) với hiệu ứng Amber Glow (Hổ phách), chặn mọi thao tác ngoại trừ kênh chat khẩn cấp và báo cáo sự cố.
  * 🖥️ **Live Sanitization Stream (Regex PII Redacted):** Luồng dữ liệu thoát (Egress) trong trạng thái Incident được lọc qua bộ lọc Regex thời gian thực để xóa bỏ các thông tin định danh cá nhân (PII), đảm bảo log gửi đi chỉ chứa thông tin kỹ thuật chẩn đoán.
  * 💻 **Hardware Biometric Validation (TouchID/Windows Hello Audit Log):** Mọi thao tác khôi phục hoặc truy cập kênh chuyên dụng trong chế độ Incident yêu cầu xác thực sinh trắc học phần cứng. Kết quả xác thực được ký và lưu vào Audit Log không thể chối bỏ.

