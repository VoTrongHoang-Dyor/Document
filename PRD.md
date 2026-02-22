# TeraChat - Technical Specification (PRD)

**Phiên bản:** Alpha 6.0
**Ngôn ngữ phát triển:** Swift (Native iOS).
**Triết lý cốt lõi:** Tự do & Phi tập trung.

TeraChat là pháo đài số bất khả xâm phạm với nguyên tắc vàng: **Không Số điện thoại, Không Email** – bạn không cần cung cấp bất kỳ thông tin cá nhân nào để bắt đầu. Tại đây, danh tính chỉ là một cặp khóa mã hóa, máy chủ hoàn toàn "mù" trước nội dung và quyền sở hữu dữ liệu được trả về tuyệt đối cho bạn.

Cái "chất" của TeraChat nằm ở sự bất diệt: hệ thống tự động chuyển mình từ "bóng ma" ẩn danh trên Internet sang mạng lưới **Mesh Offline** khi mất mạng, đảm bảo kết nối của bạn không bao giờ bị cắt đứt dù trong hoàn cảnh khắc nghiệt nhất.

Hơn cả một ứng dụng nhắn tin, đây là một **Hệ điều hành Web3 thu nhỏ**, nơi giao tiếp và tài chính (Crypto) hòa làm một, phá bỏ mọi rào cản kiểm duyệt hay giám sát từ bên thứ ba.

---

## 2. Kiến trúc Hệ thống

Hệ thống hoạt động dựa trên cơ chế **"Dual-Stack Connectivity"**, tự động chuyển đổi giữa các trạng thái mạng mà không làm gián đoạn trải nghiệm người dùng.

### Các thành phần kỹ thuật

*   **Tầng Logic (Core):** Rust/C++: Xử lý mã hóa (Noise Protocol), Định tuyến Mesh, Ký giao dịch Web3, **Core Torrent (Libtorrent)**. Chạy Background Thread để đảm bảo hiệu năng tối đa.
*   **Tầng UI (Presentation):** **Swift (SwiftUI):** Xây dựng giao diện Native cho iOS. Tối ưu hóa animations 120Hz và trải nghiệm chạm vuốt. Tuyệt đối KHÔNG chạm vào Private Key trên Main Thread.

### Chiến lược Ưu tiên Kết nối (Connectivity Waterfall)

```
1. LAN (Wi-Fi Direct) [Priority #1] -> Tốc độ cao nhất (ngang dây cáp)
2. WebRTC (P2P Internet) [Priority #2] -> Xuyên NAT, không tốn Server
3. Bluetooth Mesh (Offline) [Priority #3] -> Khi mất Internet, Multi-hop 7 bước
4. VPS Relay (TURN) [Fallback] -> Khi bị chặn Firewalls, chậm nhưng chắc
```

---

## 3. Chế độ Offline (Mesh Technology) [Badge: Bluetooth LE]

### ⚠️ Giới hạn Chức năng Offline

Để đảm bảo độ ổn định của mạng Mesh băng thông thấp (BLE chỉ đạt ~2Mbps lý thuyết, thực tế thấp hơn nhiều qua Multi-hop):

*   **CHỈ GỬI TEXT:** Chỉ cho phép gửi tin nhắn văn bản thuần túy và Emoji ký tự.
*   **VÔ HIỆU HÓA:** Toàn bộ chức năng Gọi điện (Call/Video), Gửi Ảnh, Gửi Video, Gửi File đều bị khóa (Disabled) ở tầng UI. Nút bấm sẽ bị mờ đi.

### 3.1. Kỹ thuật Mật độ Nút (Node Density Control)

Thuật toán điều phối giao thông thông minh dựa trên số lượng thiết bị xung quanh để tránh nghẽn mạng (Broadcast Storm):

*   **Trạng thái Thưa thớt (< 10 peers):** Tăng tần suất Scan & Advertise (mỗi 3-5s) để tìm kiếm kết nối nhanh nhất.
*   **Trạng thái Mật độ Cao (> 20 peers):**
    *   **Giảm Duty Cycle:** Tự động giãn cách thời gian phát sóng (mỗi 15-30s) để giảm nhiễu.
    *   **Chọn lọc Relay:** Chỉ những nút có pin > 50% và tín hiệu mạnh mới được làm Relay chuyển tiếp tin nhắn.
    *   **Jitter ngẫu nhiên:** Thêm độ trễ ngẫu nhiên (100-500ms) trước khi chuyển tiếp gói tin để tránh đụng độ (Collision).

### 3.2. Tối ưu hóa Gói tin

*   **MTU Phân mảnh:** Cố định `469 bytes`.
*   **Nén dữ liệu:** `Zstandard` bắt buộc.
*   **RAM Ring Buffer:** Cấp phát cứng **20MB**. Nếu đầy -> Drop gói tin cũ nhất hoặc từ chối nhận mới (Backpressure).

### 3.3. Chiến lược QoS: Chế độ Chơi Game (Gaming Mode)

Để đảm bảo người dùng đóng vai trò làm trạm trung chuyển (Relay Node) không bị tụt FPS khi đang chơi game nặng (PUBG, Genshin Impact):

*   **Cơ chế Phát hiện (Heuristic Detection):** Tự động kích hoạt khi:
    *   Màn hình xoay ngang (Landscape) + Luôn sáng.
    *   Tải GPU/CPU > 60% liên tục.
    *   Độ trễ âm thanh (Audio Latency) thấp (Dấu hiệu của Game Engine).
    *   **Android 12+ API:** Sử dụng `GameManager.isGameMode` để phát hiện chính xác 100%.
*   **Hành động Bảo vệ FPS:**
    *   **Hạ luồng ưu tiên (Thread Priority):** Đẩy toàn bộ tiến trình Mesh/Bluetooth xuống mức `Background` (thấp nhất). Hệ điều hành sẽ ưu tiên tài nguyên cho Game.
    *   **Bóp băng thông (Throttling):** Giới hạn băng thông trung chuyển xuống tối đa **10KB/s**. Chỉ cho phép các gói tin Text nhỏ đi qua, chặn toàn bộ gói tin Media của người khác.

### 3.4. Phân loại Node theo Hệ điều hành (OS-Aware Node Roles)

Do hạn chế nghiêm ngặt về Background Process của iOS, hệ thống phân chia vai trò rõ ràng:

*   **Apple Devices (iOS):** Đóng vai trò **Light Client** (User Endpoint). Chỉ hoạt động tích cực khi mở màn hình. Khi tắt màn hình, chuyển sang chế độ "Passive Listening" qua BLE (giới hạn tần suất) và không tham gia Relay gói tin cho người khác để tiết kiệm pin.
*   **Android Devices:** Đóng vai trò **Stable Relay**. Sử dụng `Foreground Service` để duy trì kết nối Mesh liên tục, làm xương sống cho mạng lưới cục bộ.
*   **VPS/Desktop:** Đóng vai trò **Super Node**. Chịu tải chính cho lưu lượng Internet.

---

## 4. Chế độ Online & VPS Relay [Badge: Tor Integration]

### 4.1. Kỹ thuật "Hầm Trú Ẩn" (Bunker Mode)

Quy trình phòng thủ khi Server cá nhân bị tấn công DDoS:

1.  **Phát hiện:** Traffic > ngưỡng cho phép.
2.  **Shields Up:** Kích hoạt Tor Daemon, tạo địa chỉ `.onion`.
3.  **Lockdown:** Firewall (iptables) DROP toàn bộ packet vào cổng 443 trên IP public.
4.  **Migration:** Gửi tín hiệu qua Signal để Client chuyển sang kết nối qua Tor Hidden Service.

#### ✔︎ Cơ chế "Điểm danh" & Chống Lạc Bạn (Anti-Lost Friends)

Để đảm bảo không mất kết nối với bạn bè thân thiết trong lúc chuyển nhà sang Tor:

*   **Giai đoạn Trong Bão (In-Bunker):**
    *   Hệ thống duy trì danh sách `Active_Peers = []` (Những người đang chat qua Tor).
    *   Ai nhắn tin đến qua kênh Tor sẽ được thêm vào list này (ví dụ: Bob, Carol). Những người đang ngủ (Dave) sẽ không nằm trong list.
*   **Giai đoạn Hồi quy (Normalization & Recall):**
    *   Khi hết DDoS -> Mở lại cổng 443 trên IP Public.
    *   **Lệnh Recall:** Gửi tín hiệu riêng cho Bob và Carol (trong `Active_Peers`): "Hết bão rồi, quay về IP đi".
    *   **TTL Timer:** Chỉ tắt Tor sau khi nhận được `ACK` từ Bob/Carol hoặc sau thời gian chờ (Timeout) 2 giờ.

#### 4.1.b. Chiến lược Xuyên Tường lửa (GFW Penetration)

Phân tích kịch bản kết nối xuyên biên giới (Mỹ - Trung Quốc), nơi P2P trực tiếp thường xuyên bị chặn.

1.  **Thách thức (The Problem):**
    *   **Chặn UDP:** GFW thường bóp băng thông hoặc chặn WebRTC UDP để ngăn VPN/Game.
    *   **Symmetric NAT:** Cấu trúc mạng nội địa phức tạp khiến P2P "Hole Punching" thất bại.
    *   **Lộ IP:** P2P trực tiếp làm lộ IP thật, dễ bị đánh dấu (Flagged).
2.  **Giải pháp: Tự động Chuyển mạch (Auto-Failover):**
    1.  **Bước 1 (Probe):** Thử STUN/P2P. Nếu thất bại hoặc Packet Loss cao -> Trigger Failover.
    2.  **Bước 2 (Relay Mode - Priority):** Tự động chuyển sang **TURN-over-TCP (Port 443)**.
        *   **Ngụy trang:** Traffic nhìn giống HTTPS thông thường, khó bị phân loại.
        *   **Hiệu quả:** Vượt qua được NAT nghiêm ngặt và lệnh cấm UDP.
    3.  **Bước 3 (Bunker Mode):** Nếu cả IP Relay cũng bị Blacklist -> Kích hoạt Tor Bridge để đi vòng.

### 4.2. Phân cấp Quyền hạn VPS (VPS Permission Hierarchy)

Hệ thống phân chia quyền truy cập VPS thành 2 cấp độ rõ rệt để cân bằng giữa sự tiện lợi và an ninh:

*   **1. Người nhà (Family Member):**
    *   **Cấp quyền:** "Một chạm" (One-touch) từ giao diện Admin.
    *   **Quyền hạn:** Sub-Admin (dưới chủ VPS). Được sử dụng Full băng thông, không giới hạn tính năng.
    *   **Phiên truy cập:** Vô hạn (Unlimited). Không bao giờ hết hạn trừ khi bị Admin thu hồi.
*   **2. Khách (Guest):**
    *   **Cơ chế:** Được Admin/Family "mời vào nhà" khi có cuộc gọi hoặc tin nhắn P2P.
    *   **Quyền hạn:** Thấp nhất (Minimal).
    *   **Băng thông:** Bị giới hạn (Throttle), chỉ đủ cho VoIP và nhắn tin, chặn download file lớn.
    *   **Tự động đá (Auto-Kick):** Phiên truy cập sẽ **tự hủy sau 10 phút** nếu không có hoạt động trao đổi dữ liệu (Idle Timeout).

### 4.3. Thiết lập & Vai trò VPS (VPS Setup & Roles)

VPS cá nhân đóng vai trò "Trái tim" của kết nối Online, đảm nhiệm 3 chức năng song song:

*   **STUN Server:** Giúp thiết bị Client tự nhìn thấy địa chỉ Public IP thực của mình (NAT Discovery).
*   **TURN Server (Relay):** Cầu nối trung gian để truyền dữ liệu (Media/Text) khi P2P trực tiếp bị chặn hoàn toàn.
*   **Signaling Server (Tín hiệu):**
    *   Là nơi lưu trữ tạm thời các **ICE Candidates** (IP/Port) để các thiết bị tìm thấy nhau.
    *   **Cơ chế "Dọn dẹp tức thì":** Ngay khi người dùng bấm "Logout" hoặc mất kết nối (Socket Disconnect), hệ thống phải **lập tức xóa** bản ghi trong Redis/Database.
    *   *Lý do:* Ngăn chặn Client khác gửi tin đến một IP đã chết (Dead IP), gây lãng phí băng thông và nguy cơ rò rỉ danh tính cũ.

*   **Sự Linh hoạt (Agility):** Lợi thế lớn nhất của VPS là khả năng **Xoay IP (IP Rotation)**. Nếu bị lộ hoặc bị chặn, chỉ cần "Destroy & Re-create" VPS để có IP mới trong 5 phút.

### 4.4. CƠ CHẾ CHUYỂN MẠCH P2P & BẢO TOÀN DỮ LIỆU E2EE

**(P2P Failover & E2EE Session Continuity Protocol)**

#### 1. Kiến trúc Lưu trữ Cục bộ (Local Store-and-Forward)
Do không có máy chủ trung gian lưu tin nhắn, Client gửi đóng vai trò là "Server tạm thời" cho chính tin nhắn của mình.

*   **Cấu trúc hàng đợi (Secure Outbox):**
    1.  **Mã hóa:** Tin nhắn được mã hóa E2EE bằng Session Key hiện tại ngay lập tức.
    2.  **Đóng gói:** Gói tin mã hóa được đưa vào `Local_Outbox` với trạng thái `PENDING`.
    3.  *Lưu ý:* Khi chuyển mạng (IP -> Tor), hệ thống gửi nguyên vẹn gói binary này, **không mã hóa lại** để đảm bảo tính thứ tự chuỗi khóa (Ratchet Chain).

#### 2. Giao thức Chuyển mạch P2P (Handover Protocol)

*   **Hold & Retry Logic:**
    *   Khi Socket đứt: Đánh dấu tin chưa ACK là `RETRY`.
    *   **Session Freeze:** Tạm dừng xoay vòng khóa để tránh lệch pha.
    *   **Thiết lập lại:** Bắt tay qua Tor (Transport Handshake), KHÔNG trao đổi khóa E2EE mới.
    *   **Xả hàng (Flush):** Gửi lại toàn bộ gói binary trong Outbox qua đường hầm mới.

#### 3. Cơ chế Chống mất tin & Trùng lặp

*   **Packet UID:** Mỗi gói tin có Header không mã hóa chứa UID ngẫu nhiên.
*   **Receiver Logic:**
    *   Nếu `UID` đã tồn tại trong lịch sử: Bỏ qua nội dung, nhưng GỬI LẠI `ACK` (vì Sender gửi lại nghĩa là họ chưa nhận được ACK).
    *   Nếu chưa tồn tại: Giải mã và hiển thị.

#### 4. Kịch bản Chuyển đổi (Workflow)

```
# Kịch bản 1: Bão DDoS (IP -> Tor)
1. A gửi M1 qua IP -> Mất kết nối (Timeout).
2. A chuyển sang Tor -> Kết nối .onion của B.
3. A lấy M1 (đã mã hóa) từ Outbox -> Gửi lại qua Tor.
4. B nhận M1 -> Gửi ACK qua Tor -> A xóa M1 (Done).

# Kịch bản 2: Hết bão (Tor -> IP) "Soft Handover"
1. A phát hiện Server an toàn -> Mở kết nối IP song song (Dual-Socket).
2. Trong lúc chờ IP: Tin nhắn mới (M2) vẫn đi qua Tor (đường cũ).
3. Khi IP OK: Đánh dấu IP là Primary -> M3, M4 đi qua IP.
4. Socket Tor được giữ thêm 30s (Keep-alive) rồi mới đóng.
```

**Tổng kết An ninh:** Việc chuyển đổi chỉ thay đổi "người vận chuyển" (Carrier), nội dung phong bì (Payload E2EE) vẫn nguyên vẹn. Khóa bí mật không bao giờ rời khỏi thiết bị.

### 4.5. Cơ chế Gọi điện & Nhắn tin (Communication Protocols)

Kiến trúc chi tiết về cách dữ liệu thoại và tin nhắn được truyền tải, đảm bảo nguyên tắc "Server mù" (Blind Relay) và quyền sở hữu hạ tầng.

#### I. Giao thức Gọi Thoại/Video (RTC - Caller-Allocated Relay)

Khác với mô hình tập trung, TeraChat sử dụng chính VPS của người gọi (Caller) làm cầu nối Media (TURN), giúp loại bỏ sự phụ thuộc vào bên thứ 3.

*   **1. Cấp quyền (Authorization):** Client A (Người gọi) yêu cầu Server của chính mình cấp một **Ephemeral TURN Credential** (Token tạm thời, có thời hạn ngắn).
*   **2. Tín hiệu (Signaling):** A gửi tin nhắn tín hiệu đã mã hóa E2EE cho B, chứa: `[IP Server A, Port, Token, SDP]`.
*   **3. Kết nối (Connection):** B nhận tin, giải mã và dùng Token để kết nối trực tiếp vào Server A. Luồng Media (SRTP) được chuyển tiếp qua Server A.

**Bảo mật & Quyền riêng tư:**
*   **Người gọi (A):** Kiểm soát hoàn toàn băng thông và nhật ký kết nối (Logs) trên Server của mình.
*   **Người nghe (B):** Chỉ tiết lộ IP cho Server của A (Server này đóng vai trò Relay), không lộ IP trực tiếp cho thiết bị A. Nội dung cuộc gọi được mã hóa đầu cuối (DTLS-SRTP), Server không thể giải mã.

#### II. Cơ chế Nhắn tin Không đồng bộ (Asynchronous Messaging)

Hệ thống tuân thủ nguyên tắc **Store-and-Forward** (Lưu và Chuyển tiếp). Server tuyệt đối không hoạt động như một Database lưu trữ lịch sử chat.

*   **Hộp thư chết (Dead Drop):**
    *   Server chỉ lưu trữ tin nhắn **tạm thời** dưới dạng các khối nhị phân mã hóa (Encrypted Blobs).
    *   Ngay khi B online và gửi tín hiệu xác nhận (ACK), Server sẽ **xóa vĩnh viễn** dữ liệu khỏi ổ cứng.
*   **Quy trình Mã hóa (X3DH Key Agreement):**
    1.  **Định vị:** A tìm địa chỉ Home Server của B.
    2.  **Thiết lập:** A tải gói khóa (PreKey Bundle) của B từ Server.
    3.  **Mã hóa & Gửi:** A mã hóa tin nhắn trên máy mình -> Gửi vào Hộp thư của B.
*   **Đồng bộ Đa thiết bị (Multi-Device):** Không đồng bộ qua Server trung tâm. App sử dụng cơ chế "Gửi đa điểm" (Multicast): A sẽ mã hóa từng bản sao riêng biệt cho điện thoại B, máy tính B, và iPad B. Server chỉ đóng vai trò người đưa thư.

### 4.6. TeraChat Deployer (Client-Side Provisioning)

Biến ứng dụng thành một "Admin Tool" tích hợp SSH Client, giúp người dùng phổ thông cài đặt Relay dễ dàng mà không cần biết lệnh Linux.

#### I. Quy trình (User Flow)

*   **A. I have my own VPS:**
    1.  Nhập IP, User (root), Pass/Key vào Form trong App.
    2.  Bấm **"Deploy Node"** -> App tự động SSH và cài đặt.
*   **B. I need a VPS (Mua qua DApp):**
    1.  App mở **DApp Hosting** (BitLaunch, Vultr...) tích hợp sẵn.
    2.  User mua VPS bằng Crypto/Visa qua DApp đó.
    3.  **Auto-Config:** Sau khi thanh toán, DApp trả về IP/Pass về cho TeraChat (qua Deep Link/Callback).
    4.  App tự động nhận thông tin và chuyển sang bước Deploy Nostr Relay.

#### II. Logic Kỹ thuật (Under-the-Hood)

App thực hiện chuỗi hành động ngầm qua SSH:

```
1. SSH Handshake: App -> VPS (Port 22).
2. Env Check: Kiểm tra Docker. Nếu chưa có -> Curl install Docker.
3. Deploy Core: Gửi file `docker-compose.yml` (Relay + Tor) -> `docker up`.
4. Get Onion: Đợi Tor khởi động -> Lấy Hostname từ `/var/lib/tor/`.
5. Integration: Tự động thêm Onion URL vào danh sách Relay của App -> Done.
```

#### ⚠️ III. Cảnh báo Bảo mật (Security Hardening)
SSH Credentials là quyền Root - cao nhất. Hệ thống bắt buộc tuân thủ:
*   **Secure Storage:** Mật khẩu/SSH Key lưu trong **Secure Enclave/Keychain**. Không Plaintext.
*   **Wipe After Use:** Xóa ngay khỏi RAM sau khi Deploy hoàn tất (nếu user chọn "Không lưu").
*   **Script Verification:** Tính Hash của `auto-install.sh` trước khi chạy để chống MITM.
*   **Device Trust:** Hiển thị cảnh báo *"Chỉ thực hiện trên thiết bị cá nhân tin cậy"*.

---

## 5. Bảo mật & An ninh [Badge: DevSecOps]

*   **Giao thức Bắt tay:** **Tera-Shake** (dựa trên Noise Protocol Framework). Xác thực 2 chiều, chống MIMT.
*   **Chống Giả mạo:** **Identity Pinning (TOFU):** Ghim khóa công khai lần đầu gặp. Cảnh báo ĐỎ nếu khóa thay đổi đột ngột.
*   **Tự phục hồi (Self-Healing):** Xử lý **Mất đồng bộ phiên (Ratchet Drift)**: Nếu gặp lỗi *Undecryptable Message*, hệ thống tự động đàm phán lại khóa (Re-Keying) để khôi phục kết nối.
*   **Ẩn danh Mạng:** Sử dụng **IPv6 Link-Local** sinh từ Public Key Hash. Không dùng IP thật của thiết bị.

### 5.1. Cơ chế Phát hiện Giả mạo (Anti-Impersonation Mechanism)

Hệ thống không cấm trùng tên (vì ẩn danh), nhưng ngăn chặn việc lợi dụng trùng tên để lừa đảo bạn bè.

*   **Giới hạn đổi tên (Rate Limit):** Mỗi danh tính chỉ được phép đổi Display Name tối đa **2 lần/tháng**.
*   **Phát hiện Xung đột (Collision Detection):**
    Nếu `User A` (Mới) đổi tên giống hệt `User B` (Đã có trong danh bạ của bạn):
    *   Hệ thống so sánh **Thời gian kết bạn** (Timestamp).
    *   **Hành động:** Đánh dấu `User A` là **GIẢ MẠO (IMPOSTER)** màu đỏ rực.
    *   Hiển thị cảnh báo: *"Cảnh báo: Người này sử dụng tên giống bạn của bạn, nhưng khóa công khai KHÁC NHAU."*

### 5.2. Định danh Đa hình (Polymorphic Identity)

Hệ thống sử dụng cơ chế định danh linh hoạt tùy theo ngữ cảnh mối quan hệ và trạng thái mạng:

| Ngữ cảnh | Định dạng (Format) | Mô tả |
| :--- | :--- | :--- |
| **1. Với Người lạ** | `@username:Hash(Public Key)` | Chỉ công khai tên và mã băm khóa. Không lộ IP Server. |
| **2. Với Bạn bè** | **UI:** `@username:Hash(Public Key)`<br>**System:** `@username:Hash(PK):ip_server` | Hệ thống âm thầm đính kèm `ip_server` vào metadata để thiết lập kết nối P2P tốc độ cao. |
| **3. Khi bị DDoS**<br>[Badge: Bunker Mode] | `@username:Hash(PK):address.onion` | Thay thế `ip_server` bằng địa chỉ `.onion`.<br>*Hệ thống tự động ưu tiên kết nối qua Tor dựa trên hậu tố này.* |

### 5.3. Chống Bot & Botfarm (Anti-Emulator Ecosystem)

Ngăn chặn các "Trại điện thoại" (Phone Farms) và phần mềm giả lập (Bluestacks/Nox) thao túng mạng lưới.

1.  **Chứng thực Thiết bị (Device Attestation):** Không tin vào User, chỉ tin vào Hardware.
    *   **iOS:** Sử dụng **DCAppAttestService** (Apple) để đảm bảo App đang chạy trên iPhone thật, chưa bị Jailbreak.
    *   **Android:** Sử dụng **Play Integrity API** (Hardware Backed) để chặn Root và Emulator.
2.  **Phát hiện Giả lập (Emulator Detection):**
    *   **Sensor Fusion:** Kiểm tra dữ liệu gia tốc kế (Accelerometer/Gyroscope). Botfarm thường đặt máy nằm im (dữ liệu tĩnh) hoặc giả lập trả về số 0 tròn trĩnh. Máy thật luôn có "nhiễu" (noise) do rung động môi trường.
    *   **Network Fingerprint:** Chặn các dải IP Data Center. Chỉ chấp nhận IP Dân dụng (Residential IP/4G/5G) cho các node mới.
3.  **Proof of Work (PoW):** Yêu cầu thiết bị thực hiện tính toán Hash tốn tài nguyên (5-10s CPU) khi gửi tin nhắn đầu tiên -> Làm cho việc chạy Bot quy mô lớn trở nên quá đắt đỏ (Cost-prohibitive).

### 5.4. Chiến lược Chống Spam: "Chi phí thuộc về Kẻ tấn công" (Cost-to-Attacker)

Hệ thống chuyển gánh nặng từ hạ tầng mạng sang tài nguyên CPU của thiết bị gửi để chống Spam Farm.

1.  **Chế độ Offline (Mesh/BLE Hardening):** Ngăn chặn Sybil Attack và Flood mạng băng thông thấp:
    *   **Quy tắc "Một chạm" (Single Hello Packet):** Người lạ chỉ được gửi **1 tin duy nhất** để chào hỏi.
    *   **Giới hạn Payload:** `[PK Sender] + [Signature] + [Content (Max 64 chars)]`.
    *   **Adaptive Proof-of-Work (PoW):** Thuật toán tự động điều chỉnh độ khó:
        *   **Người lạ (Hello Packet):** Độ khó cao (Hash tốn 3-5s CPU) -> Chống Spam.
        *   **Bạn bè (Whitelisted):** Độ khó bằng 0 (Zero-cost) -> Chat thời gian thực mượt mà.
2.  **Chế độ Online (Anti-DoS):** Bảo vệ hộp thư đến và tài nguyên Server:
    *   **"Tem thư" Hashcash:** Server người nhận gửi thách thức (Challenge). Sender phải giải mới được đẩy tin vào Inbox.
    *   **Exponential Backoff:** Nếu 1 IP gửi liên tục, độ khó thuật toán tăng theo cấp số nhân.
    *   **Silent Filtering (Client-side):** Tin nhắn người lạ (Stranger) được tải về nhưng **KHÔNG RUNG/KHÔNG CHUÔNG**. Chỉ hiện badge đỏ trong tab Request.
3.  **Quyền quyết định (Decentralized Moderation):** Giao diện Sandbox "Tin nhắn đang chờ":
    *   **[CHẤP NHẬN]:** Whitelist PK -> Mở full tính năng (Ảnh/Link).
    *   **[CHẶN]:** Đưa PK vào Blacklist -> Tự động Drop ở tầng Network lần sau.

### 5.5. Cơ chế Khám phá không DHT (No-DHT Discovery)

Loại bỏ bảng băm phân tán (DHT) để chuyển từ mô hình "Tìm kiếm công khai" sang "Dựa trên lời mời" (Invite-only).

1.  **Offline (Cơ chế Tiếng Vọng - Blind Echo):** Không dùng IP. Dựa vào sự lan truyền vật lý:
    *   **Probe Packet:** Người lạ gửi gói tin chứa `Hash(PK_Recv)` vào không gian.
    *   **Blind Relay:** Các máy trung gian lặp lại gói tin (Re-broadcast) mà không biết đích đến.
    *   **Passive Listen:** Máy đích "tỉnh dậy" khi bắt được Hash đúng -> Phản hồi handshake.
2.  **Online (Cơ chế "Danh thiếp" - Digital Card):** Không có danh bạ toàn cầu. Kết nối dựa trên Deep Link:
    *   **Deep Link:** `terachat://invite?id=[PK]&relay=[IP:Port]`.
    *   **Rào cản Spam:** Kẻ tấn công biết Public Key nhưng **không biết IP Relay** -> Không thể gửi tin.
    *   **Public Lobby (Optional):** Cho phép user đăng ký thêm 1 Relay công cộng để nhận tin người lạ.
    *   **Bootstrap Lobbies (Cold Start Fix):** Để tránh trải nghiệm "App trống trơn" cho người mới, App tự động subscribe vào các **Public Channels mặc định** (ví dụ: `#welcome-lounge`) chạy trên các Community Relay miễn phí. Giúp người dùng thấy hoạt động ngay khi cài App.

### 5.6. Mã hóa E2EE Nhóm (Group Encryption Protocol)

Hệ thống sử dụng **MLS Protocol (Messaging Layer Security - RFC 9420)** - giao thức chuẩn IETF cho mã hóa đầu cuối nhóm, đảm bảo khả năng mở rộng (Scalability) lên hàng nghìn thành viên mà không làm suy giảm hiệu năng đáng kể.

#### I. Kiến trúc Ratchet Tree (Cây Khóa Phân cấp)

Thay vì mã hóa riêng cho từng thành viên (O(n) như Signal Groups), MLS sử dụng cấu trúc **Binary Tree** để đạt độ phức tạp O(log n):

```
                    [Group Secret]
                         │
           ┌─────────────┴─────────────┐
           │                           │
      [SubTree L]                 [SubTree R]
           │                           │
     ┌─────┴─────┐               ┌─────┴─────┐
     │           │               │           │
  [Alice]    [Bob]           [Carol]     [Dave]
  (Leaf)     (Leaf)          (Leaf)      (Leaf)
```

*   **Leaf Node:** Mỗi thành viên sở hữu một **HPKE KeyPair** (Hybrid Public Key Encryption) riêng biệt, được lưu trong Secure Enclave.
*   **Intermediate Node:** Chứa **Path Secret** - được dẫn xuất (Derive) từ khóa của các node con.
*   **Root Node:** Chứa **Group Secret** - khóa gốc dùng để mã hóa mọi tin nhắn trong nhóm.

#### II. Quy trình Vận hành (Operational Flows)

##### A. Tạo nhóm mới (Group Creation)
1.  **Admin (Alice)** khởi tạo Ratchet Tree với chính mình là Leaf duy nhất.
2.  Sinh **Group ID** (UUID v4) và **Epoch 0** (phiên bản khóa đầu tiên).
3.  Broadcast `GroupInfo` package chứa: `[Group ID, Cipher Suite, Public Tree]`.

##### B. Thêm thành viên (Add Member - Commit Proposal)
1.  **Alice** muốn thêm **Bob** vào nhóm:
    *   Tải **KeyPackage** của Bob từ Prekey Server (chứa Public Key + Signature + Lifetime).
    *   Tạo **Add Proposal**: `Add(Bob.KeyPackage)`.
2.  **Commit & Broadcast:**
    *   Alice tính toán **Path Update**: Cập nhật tất cả khóa từ Leaf của Bob lên Root.
    *   Sinh **Epoch N+1** với Group Secret mới.
    *   Mã hóa **Welcome Message** bằng Public Key của Bob, chứa đầy đủ Tree State.
    *   Broadcast Commit đến tất cả thành viên hiện tại.
3.  **Bob nhận Welcome:**
    *   Giải mã Welcome, đồng bộ Tree State.
    *   Từ đây Bob có thể giải mã mọi tin nhắn trong Epoch mới.

##### C. Xóa thành viên (Remove Member)
1.  **Admin** tạo **Remove Proposal**: `Remove(Carol.LeafIndex)`.
2.  **Blanking Node:** Vị trí Leaf của Carol bị đánh dấu "trống".
3.  **Path Update & Epoch Rotation:**
    *   Admin cập nhật Path từ node trống lên Root.
    *   Sinh Epoch mới với Group Secret hoàn toàn khác.
    *   Carol **KHÔNG THỂ** giải mã tin nhắn từ Epoch mới (Forward Secrecy đối với người rời nhóm).

##### D. Cập nhật khóa định kỳ (Key Update / Self-Update)
*   Mỗi thành viên có thể chủ động **Update** KeyPair của mình bất kỳ lúc nào.
*   Đảm bảo **Post-Compromise Security (PCS):** Nếu khóa bị lộ hôm nay, sau khi Update, kẻ tấn công không thể đọc tin nhắn tương lai.
*   **Chính sách TeraChat:** Tự động kích hoạt Update sau mỗi **24 giờ** hoặc **100 tin nhắn** (tùy điều kiện nào đến trước).

#### III. Cơ chế Mã hóa Tin nhắn (Message Encryption)

```
Sender Flow:
1. Derive [Message Key] từ [Group Secret] + [Message Counter].
2. Nonce = Hash(Epoch || Counter || Sender ID).
3. Ciphertext = AES-256-GCM(Message Key, Nonce, Plaintext).
4. Authenticate = HMAC-SHA256(Sender Signature Key, Ciphertext).
5. Broadcast: [Epoch, Counter, Ciphertext, Auth Tag, Sender Leaf Index].

Receiver Flow:
1. Kiểm tra Epoch. Nếu cũ hơn local -> DROP (Replay Protection).
2. Tính lại Message Key từ Group Secret đã lưu.
3. Verify Auth Tag -> Nếu sai -> DROP (Tampering Detection).
4. Giải mã Plaintext.
```

#### IV. Xử lý Xung đột & Đồng bộ (Conflict Resolution)

*   **Concurrent Commits:** Khi 2 Admin cùng gửi Commit trong 1 Epoch:
    *   Ưu tiên Commit có **Timestamp nhỏ hơn** (Vector Clock).
    *   Commit thua cuộc phải **Re-propose** dựa trên trạng thái mới.
*   **Out-of-Order Messages:**
    *   Lưu buffer tối đa **50 tin nhắn** chờ xử lý tuần tự.
    *   Nếu vượt quá -> Request **Full State Sync** từ peer gần nhất.

#### V. Phân quyền Quản trị (Decentralized Admin - Multi-Sig Commit)

Để tránh lạm quyền và Single Point of Failure, các hành động nhạy cảm yêu cầu chữ ký kép:

| Hành động | Yêu cầu |
| :--- | :--- |
| **Remove Member** | 2/2 Admin ký (Nguyên tắc 2 chìa khóa) |
| **Change Group Settings** | 2/2 Admin ký |
| **Add New Admin** | 2/2 Admin hiện tại ký |
| **Add Member** | 1 Admin ký (Đơn giản hóa UX) |
| **Self-Leave** | Tự ký (Không cần phê duyệt) |

*   **Cơ chế:** Admin A tạo `Pending Proposal` -> Gửi cho Admin B -> B ký xác nhận -> Commit được phát sóng.
*   **Timeout:** Proposal hết hạn sau **72 giờ** nếu không được ký đủ.

#### VI. Bảo mật Nâng cao (Advanced Security Guarantees)

1.  **Forward Secrecy (FS):**
    *   Khóa cũ bị xóa ngay sau mỗi Epoch.
    *   Kẻ tấn công chiếm được khóa hiện tại KHÔNG giải mã được tin nhắn quá khứ.
2.  **Post-Compromise Security (PCS):**
    *   Sau khi thành viên Update, Session được "chữa lành".
    *   Kẻ tấn công cần liên tục chiếm khóa để theo dõi liên tục.
3.  **Sender Authentication:**
    *   Mỗi tin nhắn được ký bằng **Signature Key** riêng (Ed25519).
    *   Chống giả mạo danh tính trong nhóm.
4.  **Membership Verification:**
    *   Mọi thành viên có thể **Audit** danh sách thành viên bất kỳ lúc nào.
    *   Hash của Tree được public -> Phát hiện thành viên "bóng ma" (Shadow Member).

#### VII. Tối ưu hóa cho TeraChat (Platform-Specific Optimizations)

*   **Lazy Tree Sync:** Trên thiết bị yếu, chỉ tải phần Tree liên quan (Path từ Leaf đến Root), không tải toàn bộ.
*   **Epoch Caching:** Lưu tối đa 5 Epoch gần nhất trong Secure Storage để hỗ trợ giải mã tin nhắn đến muộn.
*   **Offline Member Handling:**
    *   Thành viên offline quá **7 ngày** sẽ được đánh dấu `STALE`.
    *   Khi online lại -> Yêu cầu **Full Resync** từ Admin hoặc peer đang online.
*   **Large Group (>100 members):**
    *   Sử dụng **Sub-Group Tree** để phân cấp.
    *   Admin broadcast `TreeUpdate Summary` thay vì Full Tree.

---

## 6. Chi tiết Tính năng (Functional Specification)

### I. Giao tiếp Cơ bản (Basic Communication)

*   **Nhắn tin:** Văn bản (Text), Phản hồi (Reply), Voice Message.
*   **Kết nối:** Gửi kết bạn (Contact).
*   **Media & File Transfer:** Cơ chế **"Hybrid Transfer" (TeraShare)** - Tự động chọn kênh truyền tải tối ưu:
    *   **⚡ Fast-Path (File nhỏ < 100MB):** Đi qua **VPS Relay/Mesh** để đạt tốc độ tức thì (Instant).
    *   **🧲 TeraShare (Big Data 100MB - 1TB):** Tự động kích hoạt **Torrent Engine (Libtorrent)**.
        *   **Không Server:** Dữ liệu đi trực tiếp P2P (Peer-to-Peer), Server chỉ làm nhiệm vụ bắt tay (Signaling).
        *   **Resumable:** Tự động nối lại khi mất mạng. Hỗ trợ *Sequential Download* (Vừa tải vừa xem phim).
        *   **Private Swarm:** Tắt DHT Public, chỉ kết nối với Peer được xác thực qua E2EE để bảo mật IP.
*   **Gọi điện:** P2P Call. [Badge: Offline Disabled]

### II. Giao tiếp Nâng cao & Biểu cảm

*   **Tương tác:** Reply từng tin nhắn, Mention (@), Reaction (Thả tim pixel), Emojiq (Pixel), Sticker.
*   **Nhóm & Riêng tư:** Chat nhóm (Group), Tin nhắn tự hủy (Secret Chat), Ghim tin nhắn.
    *   **Group Key Management (MLS Protocol):** Khi thành viên Join/Leave, Group Key được xoay vòng (Rotate) tự động. Admin đóng vai trò Commit Node. *📌 Xem chi tiết kỹ thuật tại [Mục 5.6. Mã hóa E2EE Nhóm](#56-mã-hóa-e2ee-nhóm-group-encryption-protocol).*
    *   **Decentralized Admin:** Nhóm yêu cầu 2 Admin (theo nguyên tắc 2 chìa khóa) để tránh lạm quyền. Quyết định quan trọng cần cả 2 ký.
*   **Tiếp cận (Engagement):** Chuỗi Streak 🔥 (Tạo thói quen tương tác hàng ngày).

### III. Quản trị Nhóm (Community Management) [Badge: Online Only]

*   **Phân quyền:** 2 Admin (nguyên tắc 2 chìa khóa) để tránh lạm quyền.
*   **Thành viên:** Mời, Xóa, Phê duyệt, Cấm chat (Mute), Ban.
*   **Nội dung:** Thiết lập Nội quy nhóm, Ghim thông báo, Thống kê tương tác.

### IV. Bảo mật & Quyền riêng tư
*📌 Xem chi tiết tại [Mục 5. Bảo mật & An ninh](#security).*

### V. Lưu trữ & Đồng bộ (Storage & Synchronization)

Giải pháp đồng bộ đa thiết bị (Multi-Device) phi tập trung, không sử dụng server trung tâm lưu trữ lịch sử, đảm bảo E2EE tuyệt đối.

*   **Saved Messages:** Lưu tin nhắn quan trọng vào bộ nhớ máy.
*   **Auto-Clear:** Tự động xóa lịch sử theo thời gian để giải phóng dung lượng.
*   **Gossip Sync:** Đồng bộ dữ liệu mạng qua giao thức Mesh.
*   **Cầu nối (Bridge):** Đồng bộ tin nhắn giữa Bluetooth Mesh và Nostr Relay khi có mạng.
*   **Kỹ thuật Đồng bộ (Sync Tech):** Dựa trên lõi BitChat (`GossipSyncManager.swift`):
    *   **Online (Real-time):** Dùng giao thức **Gossip**. Thiết bị B kết nối vào mạng Mesh/Tor, tự động "hỏi" A để lấy update mới nhất. Gửi tin nhắn dạng Multicast (1 bản cho người nhận, 1 bản cho thiết bị linked).
    *   **Offline (Async):** Sử dụng **Blind Relay** (Nostr/Tor). Thiết bị A gửi gói `SyncEvent` đã mã hóa lên Relay. Thiết bị B khi online sẽ tải về giải mã.
*   **Toàn vẹn Dữ liệu (Consistency):**
    *   **Deduplication:** Sử dụng `PacketIdUtil` & Hash nội dung để loại bỏ tin trùng lặp nhận từ nhiều nguồn (Mesh vs Relay).
    *   **CRDTs:** Quản lý trạng thái danh tính (State) để đảm bảo đồng bộ danh bạ/profile không bị xung đột.

#### 4. Cơ chế "Không Cloud, Chỉ có Peers" (Peer-to-Peer Backup)
Triết lý cốt lõi: **Các thiết bị của chính bạn đóng vai trò là Server dự phòng cho nhau.**

*   **A. Kho chứa tạm thời (Dead Drop):** VPS Relay chỉ đóng vai trò *Store-and-Forward*:
    1.  **Offline:** Tin nhắn được mã hóa nằm chờ trên VPS (Encrypted Blob).
    2.  **Destruction:** Ngay khi nhận được tín hiệu ACK từ Client, Server **xóa vĩnh viễn** dữ liệu khỏi ổ cứng.
*   **B. Đồng bộ hóa Tin đồn (Gossip Sync):** Giải quyết vấn đề đồng bộ giữa các thiết bị (iPhone <-> iPad) khi Server đã xóa tin:
    *   **Cơ chế:** Khi các thiết bị cùng một User online (qua Internet hoặc Bluetooth Mesh), chúng tự động "trò chuyện": *"Tôi có tin #100, bạn có chưa?"*.
    *   **Action:** Tự động truyền file/tin nhắn thiếu trực tiếp cho nhau (P2P).
*   **C. Khôi phục máy mới (Backfill Protocol):** Vì không có Cloud Backup, quy trình đổi máy yêu cầu thiết bị cũ (Master):
    1.  **Pairing:** Quét QR -> Thiết lập kênh truyền bí mật E2EE.
    2.  **Request:** Máy mới gửi `RequestSyncPacket`.
    3.  **Transfer:** Máy cũ mã hóa và đẩy toàn bộ lịch sử sang máy mới qua LAN/Relay.
    *   *⚠️ **Rủi ro:** Mất tất cả thiết bị cùng lúc = Mất sạch dữ liệu vĩnh viễn.*

### V.B So sánh Mô hình Kiến trúc (Architecture Comparison)

| Tiêu chí | TeraChat (Decentralized) | Traditional Apps (Centralized) |
| :--- | :--- | :--- |
| **Hạ tầng** | **Phân tán:** Hàng ngàn VPS nhỏ lẻ do User tự kiểm soát/thuê. | **Tập trung:** Cloud khổng lồ của Meta/Google kiểm soát toàn bộ. |
| **Lưu trữ** | **Local-First:** Chỉ lưu trên máy User. Server xóa ngay sau khi gửi. | **Cloud-Native:** Lưu vĩnh viễn trên Server. Đăng nhập là thấy lại. |
| **Quyền riêng tư** | **Ẩn danh (No-KYC):** Server chỉ thấy Key, không biết User là ai. | **Định danh:** Gắn liền SĐT, Danh bạ. Thu thập Metadata để quảng cáo. |
| **Kiểm duyệt** | **Uncensored:** Bạn là chủ Server, không ai được quyền Ban/Xóa bài. | **Strict Moderation:** Nền tảng có quyền khóa tài khoản nếu vi phạm. |
| **Chi phí/Tốc độ** | Tốn phí VPS ($5/mo). Tốc độ phụ thuộc cấu hình cá nhân. | Miễn phí (trả bằng dữ liệu). Tốc độ cao & ổn định. |

### VI. Công việc & Tiện ích (Utilities)

*   **Lịch & Nhắc nhở:** Reminder, Calendar.
*   **Công cụ:** Highlight tin nhắn, Chia sẻ vị trí (Share Location).

### VII. Thanh toán & Web3 (Payment) [Badge: Online Only]

*   **Ví (Wallet):** Tích hợp ví Non-custodial. Hỗ trợ Stablecoin (USDT/USDC) trên mạng Tron/Polygon.
*   **Tính năng:** Chuyển tiền cá nhân (P2P Transfer), Cơ chế thưởng (Rewards).

### VIII. Cài đặt & Cá nhân hóa

*   Cài đặt Âm thanh tin nhắn.
*   Đổi Ngôn ngữ.
*   Quản lý Dung lượng (Storage Manager).
*   Cài đặt Quyền riêng tư (Privacy Settings).

**IX. Cập nhật:** Realtime qua Store (AppStore/PlayStore).

### X. Hệ sinh thái DApps
*📌 Xem chi tiết tại [7. Hệ sinh thái Web3 & DApps](#ecosystem).*

---

## 7. Hệ sinh thái Web3 & DApps (Mini Programs)

### 7.1. Giao diện "DApps Super-Row" (The Immortal Row)

Biến giao diện chat thành trung tâm tài chính mà không làm rối UI.

*   **Vị trí Cố định (Index 0):** Hàng đầu tiên trong danh sách chat luôn là DApps. Không thể xóa, không thể trôi xuống dưới.
*   **Hiển thị Trực quan:**
    *   Thay vì hiển thị tin nhắn xem trước (preview), dòng này hiển thị **Số dư Thời gian thực** (Ví dụ: `💳 $12,450.00`).
    *   **Badge:** Hiển thị số thông báo từ các dịch vụ (Ví dụ: "Đơn hàng đã giao", "Biến động số dư").
*   **Trạng thái Offline:** Row chuyển sang màu xám (Greyscale), hiển thị số dư cache, tắt tính năng mua sắm, chỉ hiện QR Code nhận tiền.

### 7.2. Cơ chế Thanh toán Một chạm (Biometric-Sign)

Tính năng "Killer Feature" giúp tiêu tiền Crypto dễ như mở khóa điện thoại.

1.  **Nhập Ví (Import Only):** Thay vì tạo ví mới, người dùng **nhập 12/24 từ khóa (Seed Phrase)** của ví TON chính (như Tonkeeper) vào App. Hệ thống mã hóa chuỗi này bằng **Biometric Key** và lưu vào Secure Enclave.
2.  **Thanh toán (Pay):** Khi bấm "Thanh toán":
    1.  App gọi FaceID/TouchID.
    2.  Chip bảo mật giải mã Private Key trong RAM.
    3.  Ký giao dịch (Sign) -> Gửi lên Blockchain.
    4.  **Wipe RAM:** Xóa ngay lập tức Private Key khỏi bộ nhớ.

#### ⚠️ 3. Cảnh báo Bảo mật Seed Phrase
Seed Phrase là chìa khóa tài sản. Phải tuân thủ nghiêm ngặt:
*   **Secure Input:** Bật `secureTextEntry` (iOS) và `FLAG_SECURE` (Android) để chặn keylogger.
*   **Anti-Screenshot:** Disable chụp màn hình khi màn hình nhập Seed hiển thị.
*   **Clipboard Clear:** Tự động xóa Clipboard sau 60 giây nếu User copy/paste Seed.
*   **Word-by-Word Confirm:** Cân nhắc xác nhận từng từ một để chống nhập sai và giảm rủi ro lộ toàn bộ cụm từ.

### 7.3. Kiến trúc Hệ sinh thái TeraChat DApps (Technical Specs)

Mô hình kết hợp giữa **Secure Sandbox** và **Authorized Proxy** để đảm bảo sự riêng tư tuyệt đối ngay cả khi giao tiếp với các dịch vụ tập trung (Shopee, Tiki).

#### I. Kiến trúc Người dùng (Client-Side)
*   **Trạng thái Bóng ma (Ghost State):** Mặc định App chỉ lưu file Manifest `.json` nhẹ. Icon hiển thị màu xám (Grayscale). DApps được lọc hiển thị theo `Region ID` người dùng chọn.
*   **Cơ chế Tải & Xác thực (Secure Deployment):**
    1.  **Request:** Tải gói Bundle (`.zip` mã hóa) từ Server.
    2.  **Verify:** Tự động tính Hash (SHA-256) của file tải về và so sánh với Hash gốc trong Manifest. Nếu khớp -> Giải nén & Active màu Icon.
*   **Giao diện (Native UI Shell):**
    *   DApp KHÔNG vẽ HTML/CSS phức tạp để tránh chậm.
    *   DApp gửi logic JSON (Ví dụ: `render: 'product_list'`) -> Native Shell render ra các Widget gốc (Native Widgets) để đạt tốc độ 120Hz mượt mà.

#### II. Cơ chế Kết nối (Network Flow) - Authorized Proxy

Nguyên tắc: **Không kết nối trực tiếp từ thiết bị User đến Server Dịch vụ.**

```
1. User Action ("Mua hàng") -> Local Bridge (JSON Payload).
2. Native Shell -> Đóng gói request -> Mạng Tor -> TeraChat Relay Server.
3. Relay Server (Proxy) -> Sử dụng Partner API Key -> Server Dịch vụ (Shopee/Lazada).
-> Server đích chỉ thấy IP của Relay & API Key đối tác, KHÔNG thấy IP/Danh tính User.
4. Response -> Trả về JSON sạch -> DApp hiển thị.
```

**⚠️ Lưu ý Kiến trúc:** "TeraChat Relay Server" hiện tại là điểm tập trung tiềm ẩn. **Phase 3:** Thay thế bằng **Mixnet** hoặc **Tor Proxy Chaining** nhiều lớp để phi tập trung hóa hoàn toàn.

#### III. Lộ trình (Roadmap)
*   **Phase 1 (Hiện tại):** Team tự phát triển "Wrapper DApps" dùng API đối tác.
*   **Phase 2 (Open Platform):** Đối tác dùng SDK chuẩn. Quy trình: Gửi App -> Audit -> Ký số (Signing) -> OTA Update.

#### IV. Bảo mật (Security)
*   **Chống giả mạo:** Verify Hash mọi file tải về.
*   **Chống theo dõi:** Chặn tracker/analytics, đi qua Tor & Relay.
*   **Cô lập (Sandbox):** Tự động xóa cache/cookie ngay khi đóng App.

### 7.4. Kiến trúc DApp Serverless trên TON (TON-Native Architecture)

Mô hình xây dựng DApp phi tập trung hoàn toàn, loại bỏ backend truyền thống, sử dụng TON Blockchain và USDT làm cơ sở hạ tầng logic và thanh toán.

#### I. Kiến trúc Tổng thể (Architecture)

| Thành phần | Giải pháp Serverless trên TON |
| :--- | :--- |
| **Backend Logic** | **TON Smart Contracts (Tact/FunC):** Lưu trữ trạng thái đơn hàng, xử lý logic kinh doanh trực tiếp trên chuỗi. |
| **Hosting** | **IPFS / Arweave:** Lưu trữ Frontend (HTML/JS/CSS) vĩnh viễn, chống kiểm duyệt. |
| **Thanh toán** | **USDT Jetton Contract:** Chuyển tiền ổn định (Stablecoin), kích hoạt logic hợp đồng thông minh. |
| **Kết nối** | **TeraChat Mini App Interface:** Sandbox bảo mật kết nối ví qua TON Connect. |

#### II. Tech Stack & Quy trình
*   **Smart Contract:** Ngôn ngữ **Tact** (Cú pháp giống TypeScript). Xử lý nhận USDT -> Logic kinh doanh -> Phân chia doanh thu tự động.
*   **Frontend:** React/Vue.js tích hợp `@tonconnect/ui-react`. Gọi dữ liệu trực tiếp từ TON API Nodes (không qua Server riêng).
*   **Deploy:** Contract -> Mainnet. Frontend -> IPFS. Tích hợp vào TeraChat qua `ipfs://CID`.

#### III. Giải pháp Phi máy chủ
*   **Bảo mật Logic:** Logic công khai (Audit được). Dữ liệu riêng tư (Key giải mã) được mã hóa Asymmetric bằng Public Key người dùng.
*   **Lưu trữ Media:** Ảnh/Video lưu trên IPFS/TeraStorage. Smart Contract chỉ lưu Hash CID.
*   **Cập nhật:** Dùng TON DNS trỏ về CID mới hoặc cơ chế OTA Update có chữ ký số.

#### IV. Ví dụ Luồng hoạt động (User Flow)

```
1. User mở DApp (từ IPFS) -> Web App tự động detect Ví TON.
2. User bấm "Mua vé ($10)" -> App tạo Payload giao dịch USDT (Jetton Transfer).
3. TeraChat gọi FaceID/Vân tay -> Ký giao dịch -> Gửi lên Blockchain.
4. Smart Contract nhận 10 USDT -> Tự động Mint NFT Vé -> Gửi về Ví User.
-> Loại bỏ hoàn toàn AWS/Database/Server trung gian.
```

### 7.5. Cơ chế Xây dựng DApp (Local-First & Serverless Model)

Kiến trúc phát triển ứng dụng khác biệt hoàn toàn với mô hình Client-Server truyền thống. DApp chạy local trong Sandbox, kết nối trực tiếp Blockchain.

#### I. Mô hình "Local Sandbox & On-Chain Backend"
Web App không phải là website chạy trên server (AWS/Vercel), mà là **gói phần mềm tĩnh (Static Package)** được tải về thiết bị.
*   **App Core (Frontend):** File nén `.zip` chứa HTML/JS/CSS/WASM. Chạy offline-first sau khi verify hash.
*   **Database (User):** Lưu tại **IndexedDB / LocalStorage** trong Sandbox, mã hóa bởi Key người dùng.
*   **Database (Shared):** Lưu trạng thái toàn cục trên **TON Blockchain**.
*   **Logic:** Phân tán giữa **JavaScript Client** (UI) và **Smart Contract** (Tiền tệ/Quy trình).

#### II. Quy trình Xây dựng (Build Process)
1.  **Static Build:** Dùng React/Vite/Next.js (mode `output: export`). Không dùng Server-Side Rendering (SSR).
2.  **Security SDK:** Sử dụng `window.TeraChatBridge` để gọi sinh trắc học ký giao dịch. Không lưu Private Key trong App.
3.  **Smart Contract (Tact):** Viết logic nhận USDT và xử lý đơn hàng thay cho Backend Server.
4.  **Deploy:** Upload folder `dist` lên IPFS -> Lấy CID -> Đăng ký lên **TON DNS** (On-chain Registry, phi tập trung, chống kiểm duyệt).

#### III. Kết nối Mạng (Network Proxy)
*   **Vấn đề:** Gọi API bên thứ 3 (Thời tiết, Giá vàng) sẽ lộ IP người dùng.
*   **Giải pháp:** App gọi qua **TeraChat Relay** (Tor Network).
    `App Local -> TeraChat Proxy -> Tor -> API Đích`

#### IV. So sánh kiến trúc (vs Telegram Mini App)

| Đặc điểm | Telegram Mini App | TeraChat DApp |
| :--- | :--- | :--- |
| **Hosting** | Web Server (AWS/Vercel) | **IPFS / Local Package (Offline-first)** |
| **Backend** | Node.js/Python Server | **Smart Contract + Local Logic** |
| **Dữ liệu** | Server nắm giữ | **User nắm giữ (Encrypted)** |
| **Bảo mật** | HTTPS (SSL/TLS) | **Content Hash & Digital Signature** |

### 7.6. Nền tảng TeraChat Mini App (Embedded Web3 Platform)

Biến TeraChat thành Super App với kiến trúc nhúng Web App sâu vào hệ sinh thái TON. Không chỉ là Browser, đây là OS cho Web3.

#### I. Kiến trúc 3 Trụ cột (Platform Architecture)
1.  **TeraChat JS SDK (Client-Side):** Thư viện cầu nối `terachat.js` giúp DApp giao tiếp với Native App:
    *   `TeraChat.WebApp.init()`: Khởi tạo, đồng bộ Theme (Dark/Light).
    *   `TeraChat.WebApp.getUser()`: Lấy Identity ẩn danh.
    *   `TeraChat.Wallet.sendTransaction(tx)`: Gọi Native Wallet để ký & thanh toán.
2.  **Native WebView Bridge (App-Side):** Lớp trung gian bảo mật trên iOS/Android:
    *   **Injection:** Tự động tiêm object `TeraChat` vào mọi DApp.
    *   **Message Handler:** Chặn các lệnh nhạy cảm (Payment/Sign) -> Hiển thị Native Prompt xác thực vân tay.
3.  **Deep TON Integration:**
    *   Tích hợp **TonLib** trực tiếp vào Core.
    *   DApp không bao giờ chạm vào Private Key. Mọi chữ ký diễn ra ở tầng Native (Secure Enclave).

#### II. User Flow & Trải nghiệm (UX)
1.  **Discover:** Mở "Apps Center" hoặc click link `terachat://tma/game_abc`.
2.  **Load:** Native WebView load DApp Bundle từ IPFS (Check Hash).
3.  **Pay:** Bấm "Mua item" -> Native Sheet hiện lên "Xác nhận chuyển 5 TON?" -> FaceID -> Xong.
*-> Trải nghiệm mượt mà, không redirect, không popup ví ngoài.*

---

## 8. Lợi nhuận & Chiến lược (Revenue & Pivot Strategy 2.0)

Chuyển dịch sang mô hình **"Hybrid Service Provider"**: Kết hợp giữa Mã nguồn mở (Trust) và Dịch vụ quản lý (Convenience).

### Chiến lược "Kiềng 3 chân" (Cashflow Mix)

1.  **Managed Cloud Services (Dòng tiền Bền vững):** **TeraChat Premium Cloud ($4.99/tháng)**
    *   **Vấn đề:** 95% User muốn riêng tư nhưng sợ kỹ thuật (dòng lệnh, SSH).
    *   **Giải pháp:** Bán sự tiện lợi "One-Click". TeraChat quản lý hạ tầng container, User nắm giữ Key.
    *   **Biên lợi nhuận:** 30-50% (Mô hình Mua sỉ bán lẻ Tài nguyên).
2.  **Creator Economy (Dòng tiền Tăng trưởng):** **Paid Channels & Groups (Hoa hồng 10-20%)**
    *   **Mô hình:** Thu phí thành viên tham gia nhóm kín (Tư vấn, Crypto Signals, Coaching).
    *   **Bảo vệ Content:** Tính năng chống Screenshot/Forward để bảo vệ nội dung độc quyền của Creator.
3.  **Digital Goods Marketplace (NFT-based DRM):** Thị trường "Cái tôi" và "Địa vị số" có cơ chế bảo vệ bản quyền Web3:
    *   **Quyền sở hữu (On-chain):** Sticker/Theme được Mint dưới dạng NFT.
    *   **Cơ chế Verify:** App người nhận tự động check Blockchain: *"Ví của Sender có giữ NFT Sticker này không?"*.
    *   **Anti-Piracy:** Nếu không sở hữu -> Chỉ hiển thị ảnh mờ (Blur) hoặc Placeholder. Ngăn chặn việc copy file ảnh và dùng chùa (Right-click save).
4.  **Enterprise Solutions (B2B):** **TeraChat for Workspaces ($15/user/tháng)**
    *   Phục vụ Doanh nghiệp cần bảo mật tuyệt đối (Luật, Tài chính).
    *   **Tính năng:** Quản lý nhân sự tập trung nhưng **Zero-Knowledge** (Admin không đọc được tin nhắn).
    *   **Chính sách:** Tự động xóa tin nhắn (Ephemeral) để giảm rủi ro pháp lý.

---

## 9. Chiến lược Phòng thủ (Defensive Moats) [Badge: Anti-Fork Strategy]

Giải quyết bài toán "Hiệu ứng Chùa" (Free Rider) để bảo vệ Startup Open Source trước các đối thủ sao chép.

### Chiến thuật "Giữ Chìa Khóa Cổng" (Gatekeeper Strategy)
Mã nguồn Mở, nhưng Hạ tầng và Dịch vụ Giá trị gia tăng là Độc quyền.

1.  **Bẫy Push Notification (Hàng rào Kỹ thuật):** **APNS Certificate Authority**
    *   **Cơ chế:** Trên iOS, App tắt chạy nền BẮT BUỘC cần APNS để nhận tin. Chứng chỉ APNS gắn liền với Apple Developer Account chính chủ.
    *   **Rào cản:** Bên Fork code không thể dùng Server Push của TeraChat. App của họ sẽ "câm" khi tắt màn hình.
    *   **Chi phí:** Tự vận hành Push Server tốn kém và phức tạp nhân sự hơn nhiều so với phí $5/tháng.
2.  **Lõi Mở - Vỏ Đóng (Open Core Model):**
    *   **Community Edition (Open Source):** Tính năng cốt lõi (Chat P2P, E2EE) -> Lấy Trust & Growth.
    *   **Enterprise/Pro Plugins (Proprietary Source):** Các Module đóng mã nguồn: SSO (LDAP/Okta), MDM (Quản lý thiết bị), Audit Logs & Compliance.
3.  **Giấy phép AGPLv3 (Vũ khí Pháp lý):**
    *   **Quy định:** Nếu sửa đổi code và chạy như Dịch vụ (SaaS/Network), BẮT BUỘC phải công khai mã nguồn sửa đổi.
    *   **Doanh nghiệp sợ gì:** Lộ bí mật công nghệ hoặc quy trình nội bộ.
    *   **Lối thoát (Dual-Licensing):** Mua **Commercial License** để được miễn trừ AGPL -> Doanh thu B2B.
4.  **Hiệu ứng Mạng lưới (Official Network Badge):**
    *   **Cô lập:** Bản Fork tự chạy (Private Relay) là những "ốc đảo", không kết nối được với Global Network của TeraChat.
    *   **Đặc quyền Official:** Chỉ người dùng trên Mạng chính thức mới có Global Search và Username độc quyền (@tom, @jerry).

### Tổng kết Mô hình Dòng tiền (Refined Tiering)

| Gói | Đối tượng | Giá trị cốt lõi |
| :--- | :--- | :--- |
| **Personal (Free)** | Đại chúng | Privacy, P2P Core (Self-hosted device). |
| **Power User ($5/mo)** | Pro Users | **Tiện lợi:** Cloud Relay, Push mượt mà, Sticker độc quyền. |
| **Enterprise ($15+/mo)** | Doanh nghiệp | **Kiểm soát:** Admin Tools, SSO, Support, miễn trừ AGPL. |

---

> **TeraChat Engineering Document - Internal Use Only**
> © 2026 Antigravity AI - Refactored Technical Specification
