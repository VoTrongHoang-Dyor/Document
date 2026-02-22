      [TeraChat Enterprise](#) Part 1: User Scenarios [1.1 Secure Workspace](#secure-workspace) [1.2 Code Sandbox](#code-sandbox) [1.3 Smart Approval](#smart-finance) [1.4 Remote Wipe](#remote-wipe) Part 2: Core Engine [2.1 Architecture V2](#architecture) [2.2 Biometric Signing](#biometric-signing) [2.3 Enterprise Identity](#iam-governance) [2.4 Access Policy (OPA)](#opa-policy) [2.5 Endpoint Trust](#endpoint-trust) [2.6 Formal Verification](#formal-verification) [2.7 Binary Hardening](#binary-hardening) [2.8 Fuzzing](#fuzzing-infra) [2.9 Threat Model](#threat-model) [2.10 Global Deduplication](#deduplication) Part 3: Networking [3.1 Air-Gapped Mesh](#mesh-core) [3.2 Hybrid Transport](#hybrid-transport) [3.3 Metadata Privacy](#sealed-sender) Part 4: Operations [4.1 Observability & SLA](#observability) [4.2 Deployment & K8s](#deployment) [4.3 Production Config](#production-config) [4.4 Interoperability](#interoperability) [4.5 Security Governance](#day2-ops) Part 5: Deep Dive Protocols [5.1 Messaging (MLS)](#messaging-protocol) [5.2 Calling (WebRTC)](#calling-protocol) [5.3 Tech Matrix](#tech-matrix) [5.4 Infra Sizing & HA](#infra-sizing) [5.5 Identity (BYOI)](#identity-onboarding) Appendix [Reusability Matrix](#tech-reuse)    

# Technical Specification v2.0
 

 Tài liệu này xác định kiến trúc cho **TeraChat Enterprise OS**. Chúng ta đã loại bỏ các thành phần cũ (Gossip Mobile-First, VPS cá nhân đơn lẻ) để chuyển sang mô hình **Cụm Relay Doanh nghiệp (Federated Clusters)** và **Desktop-First** nhằm đáp ứng nhu cầu bảo mật và hiệu năng cao của tổ chức. 
  

### ✨ Triết lý cốt lõi: Chủ quyền Số & Vận hành Bất biến
 

**TeraChat Enterprise** là pháo đài số nơi doanh nghiệp nắm quyền sở hữu tuyệt đối: **Dữ liệu của bạn, Hạ tầng của bạn**. Chúng tôi chỉ cung cấp công nghệ "Zero-Knowledge" – hoàn toàn "mù" trước bí mật kinh doanh của bạn.
 

Sức mạnh nằm ở sự Bất diệt: Kiến trúc **Cụm Máy chủ Tự trị (Federated Clusters)** thay thế cho máy chủ đơn lẻ, đảm bảo huyết mạch thông tin tự phục hồi và thông suốt 24/7 bất chấp mọi sự cố hạ tầng.
 

Đây là **Hệ điều hành Web3**, nơi Giao tiếp, Quản trị và Tài chính (Crypto) hợp nhất làm một, xóa bỏ vĩnh viễn rủi ro từ bên thứ ba.
    

## 1.1 Secure Workspace  `Digital Bunker`
 

> **User Experience**
>  
>  **Hành động** Alex vào nhóm chat **"Project X Core Team"**.  
>  **Trải nghiệm** Giao diện y hệt Telegram – mượt, nhanh, vuốt chạm sướng tay. Không có độ trễ tải lại tin nhắn.  
>  **Sự khác biệt**  Đây không phải là Group Chat bình thường. Đây là một **"Hầm trú ẩn số" (Digital Bunker)**. 
 
* Server của TeraChat hoàn toàn "mù" (Zero-knowledge). 
* Dữ liệu thực tế nằm trên **Server nội bộ của Nebula AI** (Công ty của Alex). 
* Client chạy song song trên **Workstation của Alex** (Windows/macOS) với hiệu năng xử lý cực cao. 
    

> **Under The Hood**
>  Deep Dive: Federated Private Clusters 

Thay thế VPS cá nhân đơn lẻ (Single Point of Failure) bằng kiến trúc **Cluster**:
 
 
* **Encryption:** Toàn bộ Payload được mã hóa bằng `Company_Key` trước khi rời thiết bị. 
* **Storage:** Cluster gồm 3-5 Nodes chạy thuật toán **Erasure Coding** (Sharding dữ liệu). Nếu 1 Node sập, dữ liệu tự phục hồi từ các mảnh còn lại. 
* **Routing:** Client kết nối trực tiếp tới IP của Company Cluster, không đi qua Cloud công cộng của TeraChat. 
    

## 1.2 Code Sandbox  `Mini-App`
 

> **User Experience**
>  
>  **Tình huống** Trưởng nhóm dev gửi một thuật toán quan trọng cho Alex review.  
>  **Vấn đề cũ**  ~~Gửi file .txt hoặc paste text~~ -> Rủi ro copy nhầm, lộ code ra ngoài, file lưu lộn xộn.  
>  **Giải pháp Mới**  Dev nhấn **+** -> Chọn **"Code Vault"**. 
 
* Một cửa sổ Popup hiện lên (như Mini Program). 
* Code hiển thị có **Watermark** tên "Alex" chạy loang lổ (chống chụp màn hình). 
* Nút Copy bị **Disabled**. Chỉ cho phép Xem (View Only). 
    

> **Under The Hood**
>  Engine: WASM Sandbox & P2P Stream 
 
* **Runtime:** Mini-App chạy trong container **WebAssembly (Wasm)** bị cô lập. Không có quyền truy cập Clipboard hệ thống (trừ khi được cấp phép). 
* **Data Flow:** Code không được lưu vào Database. Nó được **Stream P2P** trực tiếp từ RAM máy Dev sang RAM máy Alex (Ephemeral Streaming). 
* **Cache:** Ngay khi đóng cửa sổ, dữ liệu bị ghi đè (Zeroing Memory). 
  🛡️ The Digital Glass Room (Security Layers) 

Kiến trúc "Nhìn được nhưng không mang đi được":
 
 
* **Lớp 1 (OS Level):** Sử dụng API chống chụp màn hình mức hệ thống: `SetWindowDisplayAffinity` (Windows) và `window.sharingType = .none` (macOS 14+). 
* **Lớp 2 (Native Overlay):** Vẽ **Dynamic Watermark** (User ID + Time + IP) đè lên cửa sổ ứng dụng. Chữ chạy random vị trí mỗi 5s để chống AI Inpainting. 
* **Lớp 3 (Input Jammer):** Chặn Global Hooks bàn phím (Keylogger) và vô hiệu hóa Clipboard khi cửa sổ Active. 
   

> **Under The Hood**
>  🔒 Engine: Ephemeral Memory & Swap Defense 

Cơ chế bảo vệ dữ liệu nhạy cảm (Private Key, Code snippet) khỏi việc bị ghi xuống đĩa cứng thông qua Swap File/Pagefile:
  **A. RAM Pinning (Chống Swap)** 
 
* **Vấn đề:** Khi thiếu RAM hoặc ngủ đông (Hibernate), OS sẽ dump toàn bộ bộ nhớ (bao gồm cả Key đã giải mã) xuống ổ cứng (`Swap/Hiberfil.sys`). Dữ liệu này tồn tại ngay cả khi tắt máy. 
* **Giải pháp (System Call):** Sử dụng **Memory Locking** để "ghim" cứng các trang nhớ nhạy cảm: 
 
  * Linux/macOS: `mlock()` hoặc `mlockall()` 
  * Windows: `VirtualLock()` 
  
   **B. Encrypted Swap Policy (Lớp phòng thủ cuối)** 
 
* **MDM Policy:** TeraChat Client kiểm tra trạng thái mã hóa ổ đĩa khi khởi động. 
* **Yêu cầu bắt buộc:** Nếu phát hiện thiết bị không bật **BitLocker** (Windows) hoặc **FileVault** (macOS), ứng dụng từ chối khởi chạy. 
   **Code Sample: Memory Locking**  
 `// Rust (cross-platform)`  
 `libc::mlock(ptr as *const c_void, size);`  
 `// Windows: kernel32::VirtualLock(ptr, size);`     

## 1.3 Smart Approval & Pay  `Fintech`
 

> **User Experience**
>  
>  **Tình huống** Alex muốn thưởng nóng $500 cho nhân viên Alice sau khi deploy thành công.  
>  **Vấn đề cũ** Thoát app -> Mở Email duyệt -> Mở App Ngân hàng -> Chụp bill -> Gửi lại chat. (Mất 5-10 phút). Slack/Teams phải cài app bên thứ 3 rất lằng nhằng.  
>  **Giải pháp Mới**  
 
1. Alex gõ lệnh `/bonus 500` hoặc bấm nút **"Thưởng nóng"** ngay trong khung chat. 
1. **Adaptive Card** hiện ra: *"Xác nhận chuyển $500 cho Alice qua PayPal?"*. 
1. Alex quét **FaceID/TouchID (Mac)** hoặc **Windows Hello** — xác thực phần cứng. 
1. **Tự động:** TeraChat Server gọi **PayPal Payouts API** → Tiền vào ví PayPal của Alice sau 3 giây. Alex không bao giờ rời khỏi khung chat. 
    

> **Under The Hood**
>  Engine: Blind Fintech Bridge 

Kiến trúc tách biệt giữa hệ thống E2EE (TeraChat) và hệ thống thanh toán tập trung (PayPal), đảm bảo PayPal không bao giờ thấy nội dung chat.
 
* **One-time Binding:** Nhân viên link tài khoản PayPal *một lần duy nhất* vào Profile công ty. OAuth Token được mã hóa và lưu trong **Secure Enclave** của thiết bị. 
* **PayPal Payouts API:** Lệnh `/bonus` trigger REST call đến PayPal Payouts API qua Enterprise Relay Server. TeraChat Server chỉ forward lệnh thanh toán đã ký, không đọc được nội dung chat. 
* **Audit Trail:** Mọi lệnh duyệt chi được ghi trong **tamper-proof audit log** nội bộ (write-only, append-only) với chữ ký số của người duyệt.

  ⚡ Blind Fintech Bridge — PayPal Payout Flow

Luồng thanh toán tự động qua PayPal Payouts API:
  

```

// Rust — Blind Fintech Bridge (Simplified)
async fn execute_payout(cmd: PayoutCommand, ctx: &AppContext) -> Result<PayoutReceipt> {
    // 1. Xác thực phần cứng (FaceID/TouchID/Windows Hello)
    let signature = ctx.secure_enclave.biometric_sign(&cmd.to_bytes())?;
    
    // 2. Lấy OAuth Token từ Secure Enclave (đã link 1 lần)
    let oauth_token = ctx.secure_enclave.decrypt_token("paypal_oauth")?;
    
    // 3. Gọi PayPal Payouts API
    let payout = PayPalPayout {
        sender_batch_header: SenderBatchHeader {
            sender_batch_id: generate_idempotency_key(),
            email_subject: "Thưởng nóng từ công ty",
        },
        items: vec![PayoutItem {
            recipient_type: "EMAIL",
            amount: Amount { currency: "USD", value: cmd.amount },
            receiver: cmd.recipient_paypal_email,
        }],
    };
    
    let receipt = ctx.paypal_client.create_payout(&oauth_token, &payout).await?;
    
    // 4. Ghi Audit Log (tamper-proof, chữ ký số)
    ctx.audit_log.append(AuditEntry {
        action: "PAYOUT",
        signer: signature,
        amount: cmd.amount,
        recipient: cmd.recipient_paypal_email,
        paypal_batch_id: receipt.batch_id,
        timestamp: SystemTime::now(),
    })?;
    
    Ok(receipt)
}

```

   **Security Constraints:** 
 
* **OAuth Token Rotation:** Token PayPal được rotate tự động mỗi 30 ngày. Token cũ bị Crypto-Shred từ Secure Enclave. 
* **Idempotency Key:** Mỗi lệnh thanh toán mang `sender_batch_id` duy nhất để chống replay/double-spend. 
* **Rate Limiting:** Giới hạn tổng giải ngân/ngày theo chính sách OPA (ví dụ: max $10,000/ngày/user). 
* **Biometric Gate:** Mọi lệnh thanh toán > $0 đều yêu cầu xác thực phần cứng — không có ngoại lệ. 
      

## 1.4 Remote Wipe  `Kill Switch`
 

> **User Experience**
>  
>  **Tình huống** Nhân viên "Tuấn" nghỉ việc và có dấu hiệu mang dữ liệu sang đối thủ.  
>  **Vấn đề cũ** Kick khỏi nhóm chat, nhưng Tuấn vẫn giữ lịch sử tin nhắn và file đã tải về máy.  
>  **Giải pháp Mới**  Alex vào Admin Panel -> Bấm **"Revoke Access"** tài khoản Tuấn.   
**Ngay lập tức trên máy Tuấn:** 
 
* Ứng dụng tự nhận lệnh hủy. 
* Toàn bộ lịch sử chat biến thành **Garbage Data** (chuỗi mã hóa vô nghĩa). 
* File trong Sandbox Storage bị xóa trắng. 
    

> **Under The Hood**
>  Engine: Hierarchical Key Management (HKMS) 
 
* **Key Rotation:** Khi bấm Revoke, Server phát lệnh **Key Ratchet Rotation**. Khóa giải mã cũ bị hủy hiệu lực. 
* **Dead Man Switch (Hardware-Backed):** 
 
  * **Monotonic Counter:** Sử dụng Hardware Counter (iOS: Secure Enclave Counter, Android: StrongBox) thay vì đồng hồ hệ thống để chống Time Travel Attack. 
  * **Mechanism:** Mỗi lần unlock DB → Counter++. Server lưu "Last Valid Counter Value" cho mỗi device. 
  * **Verification:** Khi online, Client gửi Counter hiện tại lên Server. Nếu Counter < Server's Value → Device đã bị revert/clone → Từ chối và trigger Self-Destruct. 
  * **Offline Grace Period:** Client có thể hoạt động offline tối đa 72h. Sau đó bắt buộc phải online 1 lần để verify counter. 
  
  ⚡ Technical Implementation (MLS Protocol) 

Logic thực thi **Remote Wipe** tái sử dụng cơ chế `Epoch Rotation` của giao thức MLS:
 
 
1. **Event Listener:** App lắng nghe `onEpochChanged`. Nếu `self.userID` nằm trong danh sách `removedMembers`... 
1. **Poison Pill (Tự hủy):** 
 
  * `KeyStore.deleteKeys()`: Xóa Private Key trong Secure Enclave -> Dữ liệu thành rác. 
  * `WatermelonDB.unsafeResetDatabase()`: Drop bảng chat. 
  * `FileSystem`: Quét và xóa file Sandbox. 
  
1. **Constraint:** Thực thi trong `autoreleasepool` (iOS) hoặc `try-finally` (Android) để đảm bảo không thể bị chặn bởi User. 
   

> **Under The Hood**
>  🧹 Crypto-Shredding: The Only Reliable Method 

Trên SSD/NVMe hiện đại, việc overwrite data là **VÔ HIỆU QUẢ** do Wear Leveling. Giải pháp duy nhất: **Crypto-Shredding** - Xóa khóa giải mã thay vì xóa dữ liệu.
  **❌ Tại sao Overwrite KHÔNG hoạt động trên SSD:** 
 
* SSD Controller sử dụng **Wear Leveling**: Khi ghi đè Sector A, controller thực tế ghi vào Sector B và đánh dấu A là "trống". 
* Dữ liệu gốc vẫn còn nguyên vật lý trên chip NAND Flash, có thể khôi phục bằng **Chip-off Forensics**. 
* Overwrite 1000 lần vẫn vô nghĩa vì chỉ xóa ở tầng logic, không phải tầng vật lý. 
         **** ****  
   **** ****  
   **** ****  
****   **** ****  
****  
******  

| Lớp Bảo Mật | Crypto-Shredding Implementation |
| --- | --- |
| Data Layer | Toàn bộ DB được mã hóa bằng DEK (Data Encryption Key) - 256-bit AES-GCM.                             DEK là random unique key cho mỗi database instance. |
| Key Layer | DEK được mã hóa (wrapped) bằng KEK (Key Encryption Key).                             KEK được derive từ Master Key trong Secure Enclave/TPM. |
| Master Key | Master Key nằm trong Hardware Security Module (Secure Enclave/StrongBox).                             KHÔNG BAO GIỜ rời khỏi chip bảo mật. |
| ⚡ Shredding Process | 1. Xóa KEK từ Secure Enclave → DEK không thể decrypt                             2. DEK trở nên vô dụng → Toàn bộ DB = garbage data                             3. Dữ liệu vẫn còn trên SSD nhưng vĩnh viễn không đọc được (cryptographically erased) |

   

```

// Swift (iOS) - Crypto-Shredding Implementation
func secureDataDestruction() {
    // 1. Delete KEK from Secure Enclave
    let query: [String: Any] = [
        kSecClass as String: kSecClassKey,
        kSecAttrApplicationTag as String: "com.terachat.kek"
    ]
    SecItemDelete(query as CFDictionary)
    
    // 2. Zero out any cached DEK in RAM
    memset_s(&dek, dek.count, 0, dek.count)
    
    // 3. (Optional) Zero-fill DB file for defense in depth
    // But understand this is NOT reliable on SSD
}

```

   **✅ Best Practices:** 
 
* **KEK Rotation:** Rotate KEK mỗi 30 ngày. Re-encrypt DEK với KEK mới. 
* **RAM Pinning:** Sử dụng `mlock()` để prevent DEK bị swap xuống disk. 
* **Full Disk Encryption:** Bắt buộc BitLocker/FileVault làm lớp phòng thủ cuối cùng. 
* **Audit Logging:** Log mọi KEK deletion event (tamper-proof, write-only log). 
     

## 5.1 Giao thức Nhắn tin (Messaging)  `MLS / RFC 9420`
 

Mục tiêu: Xử lý chat nhóm lớn (5000+ người), bảo mật E2EE, đồng bộ đa thiết bị và hỗ trợ Audit log nhưng không lộ nội dung.
 

> **Under The Hood**
>  1. Giao thức Lõi: MLS (Messaging Layer Security) 

Thay thế Double Ratchet (Signal) bằng **MLS (IETF RFC 9420)** để tối ưu cho nhóm lớn:
 
 
* **TreeKEM Structure:** Mã hóa 1 lần cho cả nhóm (O(log n)) thay vì mã hóa n lần (O(n)). Tăng tốc độ và tiết kiệm pin. 
* **Self-Healing:** Cơ chế **Epoch Rotation** (Xoay vòng kỷ nguyên). Khi nhân viên bị Kick, hệ thống tự động cập nhật Group Key mới. 
  

> **Under The Hood**
>  2. Cơ chế Vận chuyển: Encrypted Log Streams 

Sử dụng mô hình **Log Streams (Kafka P2P)** thay vì Gossip:
 
 
* **Federated Relay:** Cluster đóng vai trò "Hộp thư Append-only". 
* **Sealed Sender:** Server biết đích đến nhưng **không biết người gửi** (From: Encrypted) để chống phân tích hành vi. 
    

## 5.2 Giao thức Gọi thoại (Calling)  `WebRTC / Blind Relay`
 

Mục tiêu: Đạt SLA 99.9%, độ trễ thấp (<200ms) và ẩn danh IP người gọi.
 

> **Under The Hood**
>  1. WebRTC qua Blind Relay 
 
* **Signaling (Chat Channel):** Trao đổi SDP qua kênh chat MLS bảo mật. 
* **Media Transport (SRTP):** Chạy trên UDP, mã hóa đầu cuối. 
* **Blind Server:** TURN Server chỉ chuyển tiếp gói tin, **không có Key** giải mã. 
  

> **Under The Hood**
>  2. High-Availability TURN Cluster 
 
* **Floating IP (VIP):** Cụm Server dùng chung 1 IP ảo. Failover trong 3 giây nếu Server chính sập. 
* **DTLS Handshake:** Xác thực "Tôi đang nói chuyện đúng người" trước khi truyền tiếng. 
* **Adaptive Bitrate:** Ưu tiên độ mượt âm thanh, tự động giảm chất lượng Video khi mạng yếu. 
    

## 5.3 Bảng Tổng hợp Kỹ thuật  `Stack Summary`
            ****     ****     ****     ****     ****     ****     

| Thành phần | Kỹ thuật / Giao thức | Vai trò Enterprise V2.0 |
| --- | --- | --- |
| Định danh | Ed25519 + X.509 Binding | User giữ Key (Non-custodial). Admin ký xác nhận (Binding). |
| Mã hóa Chat | MLS (RFC 9420) | Quản lý khóa nhóm lớn, hỗ trợ Key Rotation. |
| Lưu trữ | SQLite + SQLCipher | Encrypted Local DB. Server không lưu Plaintext. |
| Kết nối Gọi | WebRTC + ICE/TURN | Chuẩn công nghiệp Real-time. |
| Bảo mật Gọi | DTLS-SRTP | Mã hóa Media. Server mù về nội dung. |
| Hạ tầng | HA TURN Cluster | Tự phục hồi (Failover), SLA 99.9%. |

  

> **User Experience**
>  
>  **Secure Flow**  **Quy trình Gọi điện An toàn:** 
 
1. **Caller:** Sinh Session Key ngẫu nhiên. 
1. **Signaling:** Gửi Key + IP Relay (Mã hóa) qua Chat cho B. 
1. **Connect:** Cả 2 kết nối vào HA Cluster. 
1. **Verify:** So sánh mã SAS (Emoji) để chống MITM. 
1. **Talk:** Thoại được mã hóa bằng Session Key đi qua Server Mù. 
      

## 5.4 Hạ tầng Gọi thoại (Infrastructure Deep Dive)  `SLA 99.9%`
 

Phân tích bài toán cấu hình VPS và kiến trúc High Availability để đảm bảo kết nối không gián đoạn cho doanh nghiệp (50-100 users/node).
 

> **Under The Hood**
>  1. Phân tích Cấu hình VPS (Sizing) 

Cấu hình đề xuất cho 1 Node chịu tải ~50 luồng đồng thời (HD Video/Screenshare):
            ****     ****     ****     ****     ****     

| Thành phần | Cấu hình Đề xuất | Lý do kỹ thuật |
| --- | --- | --- |
| CPU | 4 vCPUs (Compute Opt) | Xử lý mã hóa DTLS-SRTP. |
| RAM | 8 GB | Cache session tables & Monitoring agents. |
| Network | 1 Gbps Port | Bắt buộc để chịu traffic đột biến. |
| Bandwidth | 4TB - 10TB Transfer | Video Relay tiêu tốn băng thông lớn. |
| Disk | 80GB NVMe | I/O cao cho boot nhanh. Zero-log policy (tắt log nội dung). |

   

> **Under The Hood**
>  2. Giải pháp HA & Admin Strategy 

**Kiến trúc Active-Passive (Keepalived):**
 
 
* Sử dụng **Floating IP (VIP)** trỏ về Node Master. 
* Tự động chuyển mạch (Failover) sang Node Backup trong **3 giây** nếu Master sập. 
 

**Chiến lược Resource Pool (Khuyên dùng):**
 
 
* Gộp tất cả VPS thành 1 Pool chung thay vì chia lẻ cho từng phòng ban. 
* Cân bằng tải tự động (DNS Round Robin / GLB). Tăng hiệu quả kinh tế và chịu lỗi tốt hơn. 
  

> **User Experience**
>  
>  **Implementation**  **Triển khai Coturn (Docker):** 

```

docker run -d --network=host --name=coturn \
  -v /etc/coturn/turnserver.conf:/etc/coturn/turnserver.conf \
  coturn/coturn-4.5.2-r11
```

 **Config tối ưu (turnserver.conf):** 

```

listening-port=3478
no-tcp-relay      # Tắt TCP để tối ưu CPU
min-port=49152    # Dải port UDP
max-port=65535
```

      

## 5.5 Identity Onboarding (BYOI)  `Non-Custodial`
 

Quy trình "Bring Your Own Identity" - Admin chỉ cấp quyền, User nắm giữ Khóa.
 

> **Under The Hood**
>  1. Quy trình Onboarding "Self-Sovereign"            ****  
**   
**   
   ****  
**   
**   
   ****  
**   
**   
   ****  
**   
**   
   ****  
**    
   

| Chức năng | Kỹ thuật | Mô tả User Flow |
| --- | --- | --- |
| 1. Khởi tạo Danh tính(Ref: User Action) | Ed25519 / BIP-39(On-Device Gen) | App tự sinh Key & Seed Phrase trong Secure Enclave.User sao lưu 12/24 từ khóa. User là "Bóng ma" ẩn danh. |
| 2. Admin Mời(Ref: Admin Action) | Invite Token(Signed JWT) | Admin nhập Email -> Server gửi Link chứa Token (Role/Dept).Server chưa biết Public Key của User. |
| 3. Liên kết 1 Chạm(Ref: Handshake) | Deep Link(Challenge-Response) | User bấm Link -> App dùng Private Key ký xác nhận.Gửi gói tin `Sign(Token) + PubKey` lên Server. |
| 4. Xác thực & Cấp quyền(Ref: Verify) | PKI Mapping(PostgreSQL) | Server verify chữ ký -> Map `Email <-> PubKey`.Mã hóa tin công ty cho PubKey này. |
| 5. Thu hồi Quyền(Ref: Offboarding) | Key Rotation | Admin xóa Email -> Server cắt liên kết.Các nhóm chat xoay vòng Key (Epoch). User giữ lại Ví. |

   

> **Under The Hood**
>  2. Data Flow Diagram 

```

[USER DEVICE]                          [ADMIN SERVER]
     |                                        |
1. Gen Key (Pub/Priv)                         |
     |                                        |
     | <------- 2. Email (Invite Link) ------ |
     |                                        |
3. Click Link -> App Open                     |
     |                                        |
4. Sign(Invite_Token) + PubKey -------------> | 5. Verify Signature
     |                                        |    Bind: Email <-> PubKey
     |                                        |    Add PubKey to Groups
     | <------- 6. Sync Group Data ---------- |
     |                                        |
[USER READY] (User owns the Key)
```

 

 **Điểm khác biệt cốt lõi:** Admin không bao giờ cầm Private Key của nhân viên. Khi nghỉ việc, nhân viên mất quyền truy cập dữ liệu công ty nhưng *vẫn giữ được tài khoản* (Danh tính số) của riêng họ. 
  

> **Under The Hood**
>  🛑 Reserved Namespace (Enterprise Policy) 

Ngăn chặn mạo danh (Impersonation) trong môi trường doanh nghiệp:
    **** ````   **** ********   **** ****  
**``````   

| Vấn đề | Kẻ xấu nhanh tay đăng ký username @ceo, @admin hoặc tên trùng với lãnh đạo để lừa đảo. |
| --- | --- |
| Enterprise Rule | NO FREE CHOICE: Trong Enterprise OS, User không được phép tự chọn Username. |
| Binding Mechanism | Danh tính được map 1:1 với Directory Service (LDAP / Azure AD / Google Workspace).                             Ví dụ: Email alex@nebula.ai → Username tự động là Alex (Nebula) hoặc @alex_nebula. |

  **⚠️ Anti-Squatting Enforcement:**  
  Hệ thống sẽ từ chối mọi public key không có chữ ký xác thực (Attestation) từ Identity Provider (IdP) của công ty. Namespace của công ty là tài sản được bảo vệ, không phải tài nguyên công cộng.      

## Technical Reusability & Gap Analysis
 

Phân tích khả năng tái sử dụng module lõi của TeraChat Alpha 6.0 cho mô hình Enterprise.
 

> **Under The Hood**
>  1. Reusability Map (Bản đồ Tái sử dụng)  **A. Offline & Mesh Networking** 
 
*  `REUSE` **Air-Gapped Security:** Dùng Mesh cho phòng họp bí mật không Internet. 
*  `MODIFY` **Filter:** Thêm `Organization ID` để Mesh chỉ kết nối thiết bị cùng công ty. 
   **B. Bắt tay P2P (Noise Protocol)** 
 
*  `REUSE` **Zero-Trust:** Server Nebula AI chỉ làm Relay, không giải mã được nội dung. 
*  `MODIFY` **Auth:** Xác thực khóa dựa trên Certificate Authority (CA) của Doanh nghiệp thay vì TOFU. 
   **C. Mã hóa E2EE (MLS Protocol)** 
 
*  `REUSE` **Perfect Fit:** MLS sinh ra để quản lý nhóm lớn (Enterprise). 
* **Benefit:** Tính năng *Post-Compromise Security* tự động vô hiệu hóa Key của nhân viên bị sa thải. 
   **D. Blind Relay (Calling)** 
 
*  `MODIFY` **Self-hosted:** Nebula AI tự host Signaling/TURN Server nội bộ để đảm bảo tốc độ và bí mật tuyệt đối. 
   

> **Under The Hood**
>  2. Gap Analysis (Mảnh ghép còn thiếu)           ****  ****   ****  ****   ****  ****   

| Module | Logic Cá nhân (Cũ) | Logic Enterprise (Mới) |
| --- | --- | --- |
| Lưu trữ Key | Secure Enclave (User toàn quyền) | Managed Enclave (Key bị wrap bởi Company Token). |
| Xóa dữ liệu | Manual / Auto-clear | Remote Kill Switch (Lệnh từ Server -> App tự xóa DB). |
| Mini Apps | Tor / Public Relay | Secure Sandbox (Watermark, Chặn Copy, Audit Log). |

    

## 1.6 Enterprise Launchpad  `Productivity Dock`

**"Chrome Bookmark Bar cho Doanh nghiệp"** — Ghim Web App công việc (Jira, Trello, Google Sheets, CRM) ngay trong TeraChat. User không rời app để làm việc, nhưng khi cần mở link ngoài, hệ thống bảo vệ bằng 3 lớp "Túi khí".

> **Triết lý CEO:** Đừng làm "Launcher" để mở App đối thủ. Giữ chân user → **Retention**. Biến TeraChat thành "Bàn làm việc số" (Digital Workspace).

### Smart Deep Link — Cơ chế hoạt động

| Loại Link | Hành vi | Ví dụ |
|-----------|---------|-------|
| `https://` | Gọi trình duyệt mặc định (Chrome/Safari) | `https://docs.google.com/...` |
| `scheme://` | Gọi OS đánh thức App tương ứng | `zalo://`, `slack://`, `zoommtg://` |
| Internal Link | Mở ngay trong TeraChat (Trusted Domain) | `https://jira.company.com` |

**Tương thích 100%:** Không cần lo render web bị lỗi, không lo cookie. Trình duyệt của user lo hết.

### 3 Lớp Bảo mật "Túi khí" (Airbags)

**Lớp 1 — The Airlock (Khoang đệm an toàn):**
Khi User click vào Icon link ngoài (ví dụ "Google Drive"):
* Hiển thị **Bottom Sheet Popup:** *"Bạn đang rời khỏi TeraChat để mở Google Drive. Kết nối này không được mã hóa bởi chúng tôi. Bạn có muốn tiếp tục?"*
* Tùy chọn: ☐ **"Không nhắc lại cho trang web này"** (Trust this domain)
* Nếu là domain nội bộ (Trusted) → Bypass Airlock

**Lớp 2 — Visual Trust (Niềm tin thị giác):**
* **Favicon Fetcher:** Khi user paste link `vietcombank.com.vn`, hệ thống tự động crawler lấy Favicon chính chủ làm logo. Không cho user tự upload logo lung tung (tránh phishing).
* **Verified Badge:** Domain thuộc Whitelist công ty → hiện 🛡️ **khiên xanh** bên cạnh icon.
* **Google Safe Browsing API:** Mọi link được add vào thanh Bar phải đi qua Proxy Scan check phishing/malware.

**Lớp 3 — Admin Policy (Quyền lực của Sếp):**
Đây là chỗ kiếm tiền từ bản Enterprise:
* **Managed Bookmarks (Push):** Admin đẩy link bắt buộc xuống máy tất cả nhân viên. Ví dụ: *"Chấm công", "HR Portal", "Tài liệu đào tạo"*. Nhân viên **không được xóa** các icon này.
* **Blacklist Domain:** Admin chặn domain cấm (web cờ bạc, web đối thủ). Nếu cố add → App báo lỗi: *"Bị chặn bởi chính sách công ty"*.
* **Audit Log:** Ghi lại toàn bộ link được add/remove/click bởi nhân viên.

> **Under The Hood — Sandbox Isolation**
> Mọi WebView (nếu có) chạy trong **Isolated Process**. Nếu trang web bị hack, nó không thể đọc trộm dữ liệu chat TeraChat (**Cookie/Storage Isolation**). Tương đương với cơ chế Sandbox của Section 1.2.

---

## 2.1 Architecture V2  `Enterprise Core`
 

Tổng hợp các thay đổi kỹ thuật cốt lõi (Refactor Manifest).
           ****   ****  
   ****   ****  
   ****   ****  
   ****   ****  
   

| Thành phần | Cũ (V1 - Personal) | Mới (V2 - Enterprise) |
| --- | --- | --- |
| Client Engine | Swift/Kotlin (Native Mobile) | Rust + Tauri (Desktop Central)Tận dụng sức mạnh PC để chạy Node. |
| Đồng bộ (Sync) | Gossip Protocol (Lan truyền) | Encrypted Log Streams (Kafka P2P)Đồng bộ tức thì, hỗ trợ history cực lớn. |
| Hạ tầng (Infra) | VPS Cá nhân (Dễ chết lẻ tẻ) | Federated ClustersCụm 3-5 node tự cân bằng tải và sao lưu. |
| Crypto & Privacy | Curve25519 (Standard) | Post-Quantum (Kyber/Dilithium) + Sealed SenderChống máy tính lượng tử & ẩn Metadata. |

   

## 2.2 Hardware-Backed Signing  `Non-Custodial`
 

Cơ chế biến FaceID thành Chữ ký Blockchain (TON) mà không bao giờ để lộ Private Key ra khỏi chip bảo mật.
 

> **Under The Hood**
>  1. Architecture: The Black Box 

Hệ thống chia làm 2 thế giới tách biệt:
 
 
* **Thế giới mở (The App Land):** Nơi ứng dụng chạy (CPU/RAM thường). KHÔNG AN TOÀN. 
* **Thế giới kín (The Fortress):** Chip bảo mật vật lý (Secure Enclave/Titan M). Private Key nằm tại đây và KHÔNG BAO GIỜ ra ngoài. 
  

> **User Experience**
>  2. The Flow (Quy trình ký) 
 
1. **Unsigned Payload:** App tạo gói tin `[Chuyển 50k USDT]` dạng Binary. 
1. **Thách thức:** App gọi System API (TPM/Secure Enclave). OS chặn lại: "Cần Xác thực". 
1. **Mở khóa:** Quét vân tay TouchID hoặc Windows Hello Camera -> Mở khóa Hardware Chip. 
1. **Ký trong Bóng tối:** Gói tin được đẩy VÀO Chip -> Ký bằng Private Key -> Đẩy RA chữ ký `Signature`. 
 

*Kết quả: App có chữ ký để gửi lên Chain, nhưng không bao giờ thấy Private Key.*
  

> **Under The Hood**
>  3. Seed Phrase Import (Vấn đề "Nhập ví") 

Làm sao đưa 12 từ khóa vào "Hộp đen" an toàn?
 
 
* **Secure Input:** Ô nhập có cờ `secureTextEntry` (chặn keylogger/screenshot). 
* **Wrapping:** App yêu cầu Enclave tạo **Master Key** nội bộ -> Mã hóa 12 từ khóa thành `Encrypted_Seed` -> Lưu vào bộ nhớ máy. 
* **Unwrapping:** Khi cần dùng, Enclave giải mã `Encrypted_Seed` trong RAM kín -> Derive Key -> Ký -> Wipe RAM ngay lập tức. 
   Implementation Guide: BiometricSigner 

Chỉ dẫn implementation Native (Swift/Kotlin):
        ``  
``  
`` ``  
``  
``  

| macOS (Swift/Rust Bridge) | Windows (Rust/C++) |
| --- | --- |
| CryptoTokenKit (SmartCard API)                              Key Type: kSecAttrTokenIDSecureEnclave                              Access: SecAccessControlCreateWithFlags(..., .userPresence) | CNG (Cryptography Next Gen)                              Provider: Microsoft Platform Crypto Provider (TPM)                              Auth: NCryptSignHash + UI Context. |

    

> **Under The Hood**
>  🚨 4. WYSIWYS Vulnerability (What You See Is What You Sign) 

Lỗ hổng chết người khi Secure Enclave chỉ ký Hash "mù" mà không biết Hash đại diện cho nội dung gì.
  **Attack Vectors:** 
 
* **UI Redressing (Overlay Attack):** Malware vẽ lớp trong suốt đè lên UI thật (Accessibility Service / Window Hooks). 
* **Function Hooking (Frida):** Hook `renderTransactionDetails()` để hiển thị giả, hook `preparePayload()` để tráo dữ liệu thật. 
   **Kịch bản tấn công:** 
 
1. App hiển thị: `"Chuyển $50 cho Dev A"` 
1. User: Nhìn thấy → Bấm FaceID 
1. App (Malware injected): Gửi `Hash({ "to": "Hacker", "amt": 50000 })` vào Enclave 
1. Enclave: **"Mù" (Blind)** → Ký và trả về chữ ký hợp lệ cho giao dịch $50,000 
   

> **User Experience**
>  5. Defense-in-Depth (Giải pháp đa lớp)  **Solution 1: System-Managed Trusted UI** 

Nhúng thông tin giao dịch vào **Biometric Prompt của OS**. Malware không thể vẽ đè lên System Prompt (Sandbox và Z-order protection).
 
 
* **Kỹ thuật:** Prompt hiện: *"Confirm sending 50,000 USDT to 0x123...abc"* thay vì chỉ "Xác thực bằng FaceID". 
* **Yêu cầu:** Android 10+ / iOS 13+. 
   **Solution 2: Visual Challenge-Response** 

Phá vỡ kịch bản Scripting của Malware bằng cách yêu cầu User nhập liệu ngẫu nhiên.
 
 
* Không dùng nút Yes/No → Yêu cầu nhập **3 số cuối ví đích + số tiền**. 
* Bàn phím hiển thị là **Randomized Layout** (vị trí số thay đổi mỗi lần). 
* Nếu Malware vẽ đè thông tin giả ($50) → User nhập sai → Hash không khớp → Ký thất bại. 
   **Solution 3: Structured Data Signing (EIP-712 / TEP-81)** 

Không bao giờ ký chuỗi Hash vô nghĩa (`0x8f2...`). Dữ liệu được phân rã thành cấu trúc (To, From, Amount, Token) để Wallet có thể parse và hiển thị lại trước khi ký.
   

> **Under The Hood**
>  6. Implementation: System-Managed Trusted UI  **Android (Kotlin) - BiometricPrompt**  

```

val promptInfo = BiometricPrompt.PromptInfo.Builder()
    .setTitle("Xác thực Giao dịch")
    .setSubtitle("Chuyển tiền Smart Contract")
    // CRITICAL: Inject thông tin vào System Prompt
    .setDescription("LỆNH: Gửi ${payload.amount} USDT\nĐẾN: ...${payload.toAddress.takeLast(6)}")
    .setConfirmationRequired(true)
    .build()

biometricPrompt.authenticate(promptInfo, BiometricPrompt.CryptoObject(signature))

```

    **iOS (Swift) - LAContext**  

```

// Localized Reason hiển thị trên FaceID dialog của iOS
let reason = "Phê duyệt chuyển khoản: \(amount) tới \(recipient)"

// SecKeyCreateSignature xử lý UI FaceID ngầm nếu Key có flag .biometryCurrentSet
guard let signature = SecKeyCreateSignature(
    privateKey,
    .ecdsaSignatureMessageX962SHA256,
    payload as CFData,
    &error
) as Data? else { throw error!.takeRetainedValue() as Error }

```

    

> **Under The Hood**
>  7. Enterprise Security Checklist 

Các cơ chế bổ sung để thuyết phục InfoSec của ngân hàng:
 
 
* **🛡️ Anti-Overlay Detection:** Service quét liên tục Floating Windows. Nếu phát hiện App có quyền `SYSTEM_ALERT_WINDOW` → Tự động vô hiệu hóa Smart Approval, fallback Password thủ công. 
* **📵 Screenshot Protection:** Set cờ `FLAG_SECURE` (Android) để Malware chụp màn hình chỉ nhận được màu đen. 
* **✅ Server-Side Verification:** Relay Server phải verify: `Recover(Signature, Hash(PlainData)) == User_Public_Key`. Không chỉ nhận "Signed Hash". 
 

**⚠️ Lưu ý:** Lỗ hổng WYSIWYS không thể vá hoàn toàn nếu OS đã bị root. Với System-Managed Trusted UI, Malware phải khai thác lỗ hổng Kernel mới can thiệp được.
  

> **Under The Hood**
>  🛡️ 8. SECURITY PATCH: Trusted Path Architecture 

Phân tích chuyên sâu về kiến trúc **Z-Order Protection** để ngăn chặn UI Redressing:
  **Window Layer Hierarchy:** 
 
* **App UI (Layer thấp - Untrusted):** Giao diện do TeraChat vẽ. Malware có quyền `SYSTEM_ALERT_WINDOW` có thể vẽ đè lên lớp này (ví dụ: vẽ "$50" đè lên "$50,000"). 
* **System UI (Layer cao nhất - Trusted):** Giao diện do Kernel/System Server vẽ (Biometric Prompt, Permission Dialog). Hệ điều hành **CẤM** app thứ 3 vẽ đè lên layer này. 
   **Nguyên lý Trusted Path:** 
 
* Thông tin hiển thị trên System UI đi qua "con đường tin cậy": `App → OS API → Màn hình` 
* Malware không thể intercept để sửa đổi nội dung text trên đường đi này (trừ khi máy đã bị Root/Jailbreak). 
* **Chiến lược:** Buộc App chuyển chuỗi text giao dịch cho OS. OS hiển thị trong hộp thoại sinh trắc học → Tin tưởng tuyệt đối. 
          **** `` **``   **** `` ````  

| OS | API Implementation | Cơ chế Bảo vệ |
| --- | --- | --- |
| Android | BiometricPrompt.setDescription() | Inject chuỗi "Gửi 50K đến ví ...ABC" vào hộp thoại hệ thống. Malware không thể sửa text này. Yêu cầu Key có setUserAuthenticationRequired(true). |
| iOS | LAContext.localizedReason | Hiển thị context trên FaceID Dialog. Key phải được tạo với cờ .biometryCurrentSet và .privateKeyUsage. |

   **⚠️ CRITICAL FALLBACK REQUIREMENT:**  
 Nếu OS không hỗ trợ hiển thị đủ thông tin (iOS cũ cắt bớt text), App phải kích hoạt **Out-of-Band Verification**: Yêu cầu nhập lại 3 ký tự cuối của ví đích vào **Randomized Keyboard** (bàn phím vị trí số ngẫu nhiên) trước khi gọi FaceID.     

## 2.3 Enterprise Identity & Governance  `Federated PKI`
 

Giải pháp định danh doanh nghiệp, tích hợp SSO (Azure AD/Okta/Google Workspace) với bảo mật E2EE của TeraChat. **Doanh nghiệp 5,000+ nhân viên không thể gửi Invite Code thủ công** — cần Zero-Touch Provisioning.
 

> **User Experience**
>  Zero-Touch Provisioning (Tự động hóa hoàn toàn) 

1. HR thêm nhân viên mới "Mai" vào **Azure AD / Okta / Google Workspace**.
2. **SCIM Webhook** tự động sync → TeraChat tạo tài khoản + join Teams mặc định (theo Department).
3. Mai mở TeraChat lần đầu → Đăng nhập bằng **SSO công ty** (1 click) → Sẵn sàng chat.
4. Mai nghỉ việc → HR deactivate trên Azure AD → TeraChat **tức thì** revoke access + trigger **Remote Wipe** (Section 1.4).
    

> **Under The Hood**
>  1. Gap Analysis: Tại sao cần Federated Identity?        ****  ****   ****  ****   ****  ****  

| Tiêu chí | Mô hình cũ (Personal) | Enterprise Requirements |
| --- | --- | --- |
| Nguồn Định danh | Self-sovereign Key (Tự tạo) | Centralized IdP (**Azure AD, Okta, Google Workspace**). |
| Onboarding | Mời thủ công từng Key. | **Auto-Sync (SCIM):** Tự động đồng bộ 5000+ nhân viên từ HR System. |
| Offboarding | Revoke Key thủ công. | **Kill Switch:** HR xóa user -> Quyền truy cập TeraChat bị cắt tức thì + Remote Wipe. |

  

> **User Experience**
>  2. Architecture: Federated Identity with Key Binding 
 
* **Identity Broker (Keycloak/Dex):** Cầu nối giữa TeraChat và Azure AD/Okta/Google Workspace. Hỗ trợ OIDC/SAML. 
* **Enterprise CA:** Hệ thống PKI nội bộ. Chỉ tin tưởng Key được ký bởi CA doanh nghiệp, không tin Key tự sinh. 
* **SCIM Listener:** Service lắng nghe sự kiện nhân sự (Tuyển dụng/Sa thải) từ **Azure AD, Okta, Google Workspace** để cập nhật DB tức thì. 
  

> **Under The Hood**
>  3. Database Schema (PostgreSQL for SCIM Store) 

Ánh xạ định danh doanh nghiệp sang định danh Crypto:
  

```

-- 1. Users (Synced from Azure AD)
CREATE TABLE enterprise_users (
    internal_id UUID PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE, -- Azure Object ID
    email VARCHAR(255) UNIQUE NOT NULL,
    active BOOLEAN DEFAULT TRUE, -- Kill Switch State
    attributes JSONB DEFAULT '{}', -- Dept, Title for ABAC
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Certificate Binding (The Link)
CREATE TABLE pki_bindings (
    binding_id UUID PRIMARY KEY,
    user_id UUID REFERENCES enterprise_users(internal_id),
    device_public_key TEXT NOT NULL, -- User's Ed25519 Key
    certificate_body TEXT NOT NULL, -- Signed by Enterprise CA
    revoked BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL
);

-- Trigger: Auto-Revoke when HR deactivates user
CREATE TRIGGER trg_auto_revoke 
AFTER UPDATE OF active ON enterprise_users
FOR EACH ROW EXECUTE FUNCTION auto_revoke_on_terminate();

```

     

## 2.4 Access Policy Engine (OPA)  `Zero-Trust`
 

Phân quyền động dựa trên Attribute-Based Access Control (ABAC) thay vì Role tĩnh.
 

> **Under The Hood**
>  Policy Logic (Rego) 

Luật quyết định: *"Ai được vào nhóm nào?"*
  

```

package terachat.authz
default allow = false

# Rule: Chỉ nhân viên phòng Finance mới được vào nhóm Budget
allow {
    input.action == "join"
    input.resource.type == "chat_group"
    input.resource.required_dept == "Finance"
    
    # Check Attribute từ DB Sync
    input.user.attributes.department == "Finance"
}

# Rule: Chặn truy cập từ quốc gia bị cấm (Geofencing)
deny {
    input.resource.geo_restriction == "US-Only"
    input.user.attributes.location != "US"
}

```

     

## 2.5 Zero-Trust Endpoint Assurance  `Hardware Root of Trust`
 

Giải quyết lỗ hổng "The Lying Endpoint": Server từ chối cấp phát Key nếu thiết bị không chứng minh được sự toàn vẹn phần cứng (Hardware Integrity).
 

> **Under The Hood**
>  🚨 Why RASP Fails (Ring 3 Problem) 
 
* **RASP chạy ở User Mode (Ring 3):** Nếu Hacker chiếm Kernel (Ring 0) qua Root/Jailbreak hoặc VM, hắn có thể hook hàm `open()` để trả về "File not found" khi RASP kiểm tra `/sbin/su`. 
* **Kết quả:** Thiết bị đã bị Root nhưng RASP bị bịt mắt, báo cáo "sạch". 
  

> **Under The Hood**
>  1. Architecture: Remote Attestation Flow 

Quy trình "Challenge-Response" để xác minh thiết bị thật bằng phần cứng:
 
 
1. **Challenge:** Khi Login, Server gửi một chuỗi ngẫu nhiên `nonce` xuống Client. 
1. **Attestation:** Client yêu cầu Chip bảo mật (TPM/Secure Element) tạo "Health Quote" chứa: 
 
  * `nonce` (chống Replay attack) 
  * Trạng thái Boot (Secure Boot: ON/OFF) 
  * Chữ ký số của Chip (ký bởi Root CA của Apple/Google/Microsoft) 
  
1. **Verification:** Client gửi Quote lên Server. Server verify chữ ký với Vendor CA → Cấp Session Token. 
  

> **User Experience**
>  2. Implementation Strategy (OS Specific)         **** ``    **** `` ``   **** ``   

| Platform | Native API | Cơ chế xác thực |
| --- | --- | --- |
| iOS | DCAppAttestService | Verify App là bản gốc (không Mod) và chạy trên iPhone thật (không Jailbreak). |
| Android | Play Integrity API | Yêu cầu MEETS_STRONG_INTEGRITY (Hardware-backed Keystore, chặn Emulator/Root). |
| Windows | TPM 2.0 Health Attestation | Kiểm tra PCR (Platform Configuration Registers) đảm bảo Kernel chưa bị tamper + BitLocker đang bật. |

   CODE: ANDROID PLAY INTEGRITY  

```

// 1. Client: Request Integrity Token
val integrityManager = IntegrityManagerFactory.create(context)
val tokenResponse = integrityManager.requestIntegrityToken(
    IntegrityTokenRequest.builder()
        .setNonce(serverNonce) // Nonce từ Server
        .build()
).await()

// 2. Server Verify - Payload phải đạt:
{
  "deviceIntegrity": {
    "deviceRecognitionVerdict": ["MEETS_STRONG_INTEGRITY"] // Hardware Required
  },
  "appIntegrity": {
    "appRecognitionVerdict": "PLAY_RECOGNIZED",
    "certificateSha256Digest": ["SHA_CỦA_TERACHAT_SIGNING_KEY"]
  }
}

```

  

 **POLICY:** Nếu chỉ đạt `MEETS_BASIC_INTEGRITY` (Software Only) hoặc phát hiện Root → Server từ chối Handshake và gửi lệnh **Remote Wipe**. 
     

## 2.6 Formal Verification  `Math Proof`
 

Thay thế niềm tin vào "Human Review" bằng "Mathematical Proof". Chứng minh tính đúng đắn của Smart Contract ở cấp độ toán học.
 

> **Under The Hood**
>  Why Unit Test Is Not Enough         ****   ****   ****   ****   ****   ****  

| Tiêu chí | Unit/Integration Test | Formal Verification |
| --- | --- | --- |
| Bản chất | Probabilistic. "Tôi đã thử 100 trường hợp, đều ổn." | Deterministic. "Tôi chứng minh được không tồn tại trường hợp sai." |
| Phạm vi | Kiểm tra các code path đã biết. | Quét toàn bộ State Space của hợp đồng. |
| Kết quả | Tìm thấy lỗi (Bugs found). | Chứng minh sự vắng mặt của lỗi (Absence of bugs). |

   

> **Under The Hood**
>  1. Methodology: Invariant-Based Safety 

Hệ thống không tìm kiếm lỗi, mà tìm kiếm sự vi phạm các **Bất biến (Invariants)**:
        ****  
 ``  
   ****  
 ``  
   ****  
 ``  
  

| Loại Bất biến | Logic (Tact/FunC) |
| --- | --- |
| Solvency(Khả năng thanh toán) | assert(Vault.balance >= sum(User.deposits))Tiền trong két không bao giờ nhỏ hơn tổng nợ người dùng. |
| Access Control(Quyền truy cập) | forall state: withdraw() => msg.sender == ownerMọi trạng thái: chỉ Owner gọi được hàm rút. |
| Monotonicity(Tính đơn điệu) | nonce_new > nonce_oldSố thứ tự giao dịch chỉ tăng, không bao giờ giảm (chống Replay). |

   

> **User Experience**
>  2. Implementation: Z3 SMT Solver 

Vì hệ sinh thái TON chưa có công cụ FV tự động như Certora (EVM), sử dụng phương pháp **Model Checking**:
  

```

// 1. Tact Logic (Simplified)
fun withdraw(amount: Int) {
  require(balance >= amount, "Insufficient funds");
  balance = balance - amount;
}

// 2. SMT-LIB Model (Z3 Prover)
(declare-const balance_old Int)
(declare-const amount Int)
(declare-const balance_new Int)

(assert (>= balance_old amount))           // require condition
(assert (= balance_new (- balance_old amount))) // logic
(assert (< balance_new 0))                  // Attack: Can balance go negative?

(check-sat) 
// UNSAT = Không tìm được cách hack → AN TOÀN
// SAT   = Z3 trả về giá trị cụ thể để hack → FIX NGAY

```

   **✅ AUTOMATED CI/CD PIPELINE:**  
 Smart Contract Pipeline tự động dịch Tact → SMT Model → Chạy Z3 Solver. Nếu tìm thấy kẽ hở toán học → **Block Deploy ngay lập tức**.     

## 2.7 Binary Hardening & Obfuscation  `Anti-RE`
 

Biến ứng dụng thành "Hộp đen" thực sự. Tăng chi phí tấn công ngược (Reverse Engineering) lên mức tối đa.
 

> **Under The Hood**
>  1. Obfuscation Strategy (O-LLVM) 

Áp dụng các kỹ thuật làm rối mã ở tầng Compiler (LLVM Pass):
         **** ````    ****     **** ````   

| Kỹ thuật | Cơ chế | Mục tiêu phòng thủ |
| --- | --- | --- |
| Control Flow Flattening | Biến if-else/loop thành vòng lặp switch khổng lồ và phẳng. | Phá vỡ CFG trong IDA Pro/Ghidra. |
| Bogus Control Flow | Chèn mã giả (Junk Code) không bao giờ được thực thi. | Làm nhiễu phân tích tĩnh. |
| Instruction Substitution | Thay a + b bằng a - (-b) + x - x. | Làm rối Decompiler. |

   

> **User Experience**
>  2. Secrets Protection (Compile-time XOR) 

Ngăn chặn trích xuất API Key, URL bằng lệnh `strings`.
 
 
* **String Encryption:** Mọi chuỗi tĩnh được mã hóa XOR với key ngẫu nhiên tại thời điểm biên dịch. 
* **Stack Decryption:** Chuỗi chỉ giải mã trên Stack trước khi dùng và bị Zeroized ngay sau đó. 
  

```

// Rust: String Obfuscation (obfstr crate)
use obfstr::obfstr;

fn verify_license() {
    // Chuỗi này KHÔNG tồn tại trong Binary
    // Thay bằng mảng bytes đã XOR, giải mã tại runtime
    let endpoint = obfstr!("https://auth.terachat.internal/verify");
    
    if check_server(endpoint) {
        println!("{}", obfstr!("Access Granted"));
    } else {
        println!("{}", obfstr!("Error: 0x99")); // Hacker không trace được
    }
}

```

   ⚠️ TAMPER DETECTION (Self-Checksumming) 

 App tự tính Hash của `.text section` khi khởi chạy. Nếu phát hiện Hash thay đổi (Hacker patch `JZ` → `JMP`) → Kích hoạt **Silent Crash** (treo ngẫu nhiên) thay vì thông báo lỗi. 
     

## 2.8 Continuous Fuzzing Infrastructure  `Anti-ZeroDay`
 

Chuyển từ kiểm thử xác định (Unit Test) sang kiểm thử ngẫu nhiên (Fuzzing) để tìm các lỗi bộ nhớ và logic tiềm ẩn mà con người không thể nghĩ ra.
 

> **Under The Hood**
>  Why Unit Test Is Not Enough 
 
* **Unit Test:** "Tôi đưa vào `A`, mong đợi ra `B`." → Chỉ kiểm tra những gì bạn *biết*. 
* **Thực tế:** Hacker đưa vào `FFFF...` (tràn bộ đệm), `NULL`, emoji, binary méo mó. 
* **Hậu quả:** Packet Parser chạy đúng 100% Unit Test, nhưng gói tin 1MB dị dạng → **Crash (DoS)** hoặc **RCE**. 
  

> **Under The Hood**
>  1. Architecture: Coverage-Guided Fuzzing 

Hệ thống tự động sinh hàng tỉ test-case dị dạng để tấn công vào các điểm yếu:
         ****  
     ****  
     ****  
    

| Target Component | Fuzzing Strategy | Mục tiêu phát hiện |
| --- | --- | --- |
| Packet Parser(Protobuf/Binary) | Structure-Aware Fuzzing (LibFuzzer) | Buffer Overflow, Integer Overflow, Infinite Loops (DoS). |
| Crypto Handshake(Noise/MLS) | Stateful Fuzzing | Sai thứ tự gói tin → Deadlock hoặc bypass xác thực. |
| File Processing(Image/Docs) | File Format Mutation (AFL++) | Memory Corruption (như ImageTragick) khi xử lý file đính kèm độc hại. |

   

> **User Experience**
>  2. CI/CD Integration (Security Pipeline) 

Fuzzing là quy trình bắt buộc (Mandatory Gate) trong Release Cycle, không phải sự kiện một lần.
 
 
* **Smoke Fuzz (PR Gate):** Mọi Pull Request sửa Core Logic phải vượt qua 10 phút Fuzzing. Nếu Crash → Block Merge. 
* **Deep Fuzz (Nightly):** Server chuyên dụng chạy Fuzzer 24h/ngày trên nhánh `main`. 
* **LLVM Sanitizers:** 
 
  * `AddressSanitizer (ASan)`: Phát hiện Buffer Overflow, Use-after-free. 
  * `MemorySanitizer (MSan)`: Phát hiện biến chưa khởi tạo. 
  * `UBSan`: Phát hiện tràn số, chia cho 0. 
  
  

```

// Rust Fuzz Target (cargo-fuzz + libFuzzer)
#![no_main]
use libfuzzer_sys::fuzz_target;
use terachat_core::protocol::parse_packet;

fuzz_target!(|data: &[u8]| {
    // Fuzzer bơm dữ liệu ngẫu nhiên vào `data`
    // Chỉ quan tâm: Hàm có Panic/Crash/Leak không?
    if let Ok(packet) = parse_packet(data) {
        let _encoded = packet.to_bytes(); // Round-trip test
    }
});

```

   **⚠️ ZERO-TRUST POLICY:**  
 Bất kỳ thư viện bên thứ 3 nào (XML Parser, Image Decoder) **BẮT BUỘC** phải được Fuzzing độc lập trước khi tích hợp vào TeraChat Core. Không tin tưởng code của người khác.     

## 2.9 Threat Model & Security Mitigation  `Red Team Analysis`
 

Phân tích toàn diện các attack vectors và mitigations dựa trên góc nhìn của Red Teamer (Penetration Testing).
 

> **Under The Hood**
>  Security Threat Priority Matrix 

Đánh giá mức độ nghiêm trọng dựa trên Impact và Likelihood:
                **** ****   ****  ``  ****   **** ****   ****  ``  ****   **** ****   ****  ``  ****   **** ****   ****  ``    **** ****   ****  ``    **** ****   ****  ``    

| # | Attack Vector | Severity | Likelihood | Risk Score | Priority | Mitigation Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Dead Man Switch Time Travel | CRITICAL | High | 9/10 | P0 | ✅ FIXED: Hardware Counter |
| 2 | Signing Oracle Attack | CRITICAL | Medium | 8/10 | P0 | ✅ MITIGATED: WYSIWYS + Rate Limiting |
| 3 | SSD Wear Leveling | HIGH | Medium | 7/10 | P1 | ✅ FIXED: Crypto-Shredding |
| 4 | Mesh Network MITM | HIGH | Medium | 7/10 | P1 | ⚠️ PARTIAL: Node Rotation Required |
| 5 | Non-Custodial Enterprise Risk | MEDIUM | High | 6/10 | P2 | 📋 POLICY: Multi-Sig Strategy |
| 6 | Analog Hole (Camera) | LOW | High | 4/10 | P3 | ⚠️ ACCEPTED: Physical Limitation |

    

> **Under The Hood**
>  🎯 Attack Vector #1: Dead Man Switch Time Travel  **Attack Scenario:** 
 
1. Attacker lấy trộm laptop nhân viên, ngay lập tức bỏ vào **Lồng Faraday** (chặn sóng 100%). 
1. Vào BIOS hoặc dùng tool hook API `GetSystemTime`, đóng băng thời gian hoặc lùi lại quá khứ. 
1. Client nghĩ: *"Mới trôi qua 5 phút, chưa cần xóa"* → Không trigger Self-Destruct. 
1. Attacker ung dung dump RAM hoặc Clone ổ cứng để brute-force từ từ. 
   **✅ Mitigation Strategy** 
 
* **Hardware Monotonic Counter:** Sử dụng Secure Enclave Counter (iOS) / StrongBox (Android) không thể revert. 
* **Verification Protocol:** Server lưu "Last Valid Counter Value" cho mỗi device. 
* **Detection:** Counter < Server's Value → Device bị revert/clone → Từ chối + Self-Destruct. 
* **Trade-off:** Yêu cầu online 1 lần/72h để verify counter. 
 

**Implementation:** Đã cập nhật Section 1.4 Remote Wipe.
    

> **Under The Hood**
>  📅 Security Implementation Roadmap  **Phase 1: Pre-Alpha (Blocking Issues)** 
 
* ✅ **DONE:** Fix Dead Man Switch → Hardware counter-based 
* ✅ **DONE:** Implement Crypto-Shredding cho DB cleanup 
* ✅ **DONE:** Transaction-level biometric auth 
   **Phase 2: Beta** 
 
* ⏳ **IN PROGRESS:** Node rotation cho Mesh network 
* 📋 **PLANNED:** Multi-Sig wallet cho Enterprise tier 
* 📋 **PLANNED:** Byzantine fault tolerance implementation 
   **Phase 3: Post-Launch** 
 
* 📋 **PLANNED:** External penetration testing 
* 📋 **PLANNED:** Bug bounty program 
* 📋 **PLANNED:** Incident response playbook 
     

## 2.10 Global Deduplication  `Single Instance Storage`
  
 
 Giải pháp tối ưu hóa lưu trữ và băng thông: "Lưu một, Tham chiếu nhiều" (Store Once, Reference Many).
  
 
 > **Under The Hood**
 >  1. Nguyên lý Cốt lõi: Content-Addressable Storage (CAS) 
 
 Trong mô hình Enterprise, dữ liệu không được quản lý theo tên file, mà dựa trên **Bản băm nội dung (Content Hash)**:
  
  
 * **Logic:** Hệ thống tệp tin cục bộ hoạt động như một kho Object Store. 
 * **Physical Filename:** Là chuỗi SHA-256 của chính nội dung file đó (Ví dụ: `a1b2c3d4...`). 
 * **Database (SQLite):** Chỉ lưu metadata và đường dẫn tham chiếu (Symlink). 
   
 
 > **User Experience**
 >  2. Quy trình Xử lý Trùng lặp (Workflow) 
 
 Cơ chế "Check-before-Write" tại tầng **Rust Core** giúp tiết kiệm 100% băng thông cho file trùng lặp.
   **Bước 1: Nhận Metadata (Signaling Phase)** 
  
 * Client nhận gói tin Metadata trước khi tải file: 
  
   * `File_Name`: "Bao_cao_Tai_chinh.pdf" 
   * `Content_Hash`: `sha256:8f9d...` (Hash tin cậy của file gốc) 
   * `Encrypted_Hash`: `sha256:7a2b...` (Hash của bản mã hóa) 
   
    **Bước 2: Kiểm tra Kho cục bộ (Local Lookup)** 
  
 ```
 
 SELECT file_path FROM local_assets WHERE content_hash = 'sha256:8f9d...';
 ```
 
  
 * **Kịch bản A (Cache Hit):** File đã tồn tại (do người khác gửi trước đó). -> **Hủy tải xuống (Abort)**. Hiển thị ngay lập tức bằng cách trỏ tham chiếu (Symlink). 
 * **Kịch bản B (Cache Miss):** Chưa có file. -> Tiến hành tải từ Encrypted Log Streams (Kafka) hoặc P2P Torrent. 
     
 
 > **Under The Hood**
 >  3. Cơ chế Nâng cao (Advanced Dedup)        **** ****   **** ****  
 
 | Tính năng | Cơ chế Kỹ thuật |
 | --- | --- |
 | Big Data Deduplication(P2P / Torrent) | Sử dụng Merkle Tree để check trùng lặp từng Block/Piece nhỏ.                             Nếu User A forward file 1GB cho C, máy User B (đã có file) tự động chuyển sang chế độ Seeding mà không cần tải lại. |
 | Packet Deduplication(Dual-Stack Network) | Do chạy Dual-Stack (Mesh + Internet), 1 tin nhắn có thể đến 2 lần.                             Solution: Bloom Filter trong RAM ghi nhớ PacketID (UUID) trong 10 phút. Drop gói tin trùng ngay tại cổng mạng. |
 
    
 
 > **Under The Hood**
 >  So sánh: Alpha V1 vs Enterprise V2           ****  ****   ****  ****   ****  ****   
 
 | Tiêu chí | Alpha V1 (Mobile-First) | Enterprise V2 (Desktop-First) |
 | --- | --- | --- |
 | Định danh File | Hash đơn giản (SHA-256) | Content-Addressable Storage (CAS) |
 | Phạm vi Check | Chỉ check file hoàn tất | Check cả Block đang tải dở (Resume) |
 | Lưu trữ | Mỗi Chat 1 file (Dư thừa) | Global Single Instance (1 File cho N Chat) |
 
     
 
 ## 3.1 Air-Gapped Mesh Protocol  `MeshCore v2.1`
 

Giao thức kết nối nội bộ cho môi trường không Internet (Hybrid P2P Discovery).
 

> **Under The Hood**
>  1. Architecture: The Desktop Super Node 

Trong khi Mobile tập trung tiết kiệm pin, Desktop đóng vai trò xương sống (Backbone) của mạng Mesh:
 
 
* **Stable Relay:** Máy tính (có nguồn điện ổn định) lưu trữ và chuyển tiếp gói tin cho Mobile. 
* **Internet Bridge:** Máy tính có LAN/Wi-Fi đóng vai trò cầu nối, hút tin từ Internet và phát tán vào mạng Bluetooth Mesh cho các thiết bị di động xung quanh. 
  

> **User Experience**
>  2. Scenario-Based Specs  **2.1. Blind Echo Discovery (Phòng họp kín)** 
 
* **Logic:** Phát `Ephemeral_ID` thay vì tên thật. 
* **Payload:** `[Protocol: 2] + [Hash(Org_ID + Daily_Key): 8]`. 
* **Filter:** Chỉ thiết bị cùng Org_ID mới giải mã được -> Chống nghe trộm. 
   **2.2. Multi-hop Gossip Routing (Vùng chết)** 
 
* **TTL Strategy:** `TTL = 7`. Giảm 1 qua mỗi Hop -> Chống tin nhắn chạy vòng tròn. 
* **Vector Clock:** Chỉ đồng bộ tin mới hơn Clock hiện tại. 
   **2.3. Node Density Control (Sự kiện >20 người)** 
 
* **Passive Mode:** Khi > 20 peers, tăng `AdvertiseInterval` lên 5000ms. 
* **QoS:** Drop toàn bộ gói tin Media, chỉ cho Text/Command đi qua. 
   **2.4. Desktop Bridge Mode (Cầu nối Internet)** 
 
* **Logic:** Desktop Super Node kết nối Internet, nhận tin nhắn từ Cloud và phát tán vào mạng Bluetooth Mesh cho các thiết bị di động xung quanh. 
* **Security:** Mã hóa E2EE từ Cloud đến Mobile, Desktop chỉ là Relay không giải mã được nội dung. 
   **2.5. Desktop-First Torrent P2P (Big Data)** 
 
* **Logic:** Tận dụng ổ cứng lớn của PC để làm Seed/Leech cho các file dữ liệu khổng lồ (>10GB). 
* **Protocol:** Libtorrent (uTP) chạy song song với ứng dụng chat, chia nhỏ file và gửi đa luồng cho nhiều người cùng lúc. 
   

> **Under The Hood**
>  3. Comparison: Mobile vs Desktop Mesh         ****     ****  ****   ****  ****  

| Tính năng | Mobile (iOS/Android) | Desktop (Win/Mac/Linux) |
| --- | --- | --- |
| Giao thức | Bluetooth LE / Mesh | LAN / Wi-Fi Direct / Gossip |
| Vai trò | Light Client (Tiết kiệm pin) | Super Node / Gateway |
| Lưu trữ | Limited Ring Buffer (20MB) | Unlimited (Database Mode) |

  

* Desktop đóng vai trò "Hub" trung chuyển để duy trì sự sống cho mạng lưới thiết bị di động.
    

## 3.2 Hybrid Transport  `High Priority`
 

Giải pháp "đường cao tốc" P2P để truyền tải Big Data (Database, Source Code) trong môi trường Offline.
 

> **Under The Hood**
>  1. Workflow: From Dirt Road to Highway 
 
* **Giai đoạn 1 (Signaling):** Dùng Bluetooth Mesh để tìm nhau và thỏa thuận "Tôi muốn gửi file 1GB". 
* **Giai đoạn 2 (Upgrade):** Tự động kích hoạt Wi-Fi P2P để bắn dữ liệu (Tốc độ 20-50MB/s). 
  

> **User Experience**
>  2. Technology Stack Analysis (Desktop)  **A. Local LAN P2P (mDNS/Bonjour)** 
 
* **Speed:** 1Gbps (Ethernet) hoặc 300Mbps+ (Wi-Fi 6). Cực nhanh, ổn định. 
* **Discovery:** Sử dụng Multicast DNS để tìm peers trong cùng Subnet. 
* **Critical:** Không phụ thuộc vào Internet Gateway. Máy A bắn thẳng sang Máy B. 
   **B. USB-Eth Bridging (Air-Gapped Extreme)** 
 
* **Scenario:** Kết nối trực tiếp 2 máy tính qua cáp mạng (Cross-over cable) hoặc USB Bridge. 
* **Security:** Tách biệt vật lý hoàn toàn khỏi hạ tầng mạng tòa nhà. 
   

> **Under The Hood**
>  3. Cross-Platform Bridge (Android <-> iOS) 

Giải pháp khi 2 hệ điều hành không nói cùng ngôn ngữ P2P:
 
 
1. **Android Host:** Tạo *Local Only Hotspot* (Router ảo). 
1. **Signaling:** Gửi SSID/Pass qua Bluetooth cho iOS. 
1. **iOS Client:** Join vào Hotspot này. 
1. **Transport:** Hai máy cùng mạng LAN ảo -> Bắn qua TCP Socket chuẩn. 
    

## 3.3 Metadata Privacy  `Sealed Sender`
 

Bảo vệ danh tính người gửi và làm nhiễu thông tin định tuyến. Ngăn chặn tấn công phân tích lưu lượng (Traffic Analysis).
 

> **Under The Hood**
>  1. Sealed Sender Architecture 

Nguyên tắc: Server Relay biết gói tin đi **ĐẾN đâu**, nhưng không biết nó **ĐẾN TỪ ai**.
         ****  
 ``  
`` ``  
**   ****  
 `` ``````   ****   ****  

| Thành phần | Standard Mode (Lộ Metadata) | Sealed Mode (Riêng tư) |
| --- | --- | --- |
| Header(Unencrypted) | From: Alice_IDTo: Bob_ID | To: Bob_Delivery_Token(Trường From bị bỏ trống) |
| Payload(Encrypted) | Body: "Hello" | Sender: Alice_ID + Sign: Alice_Sig + Body |
| Server Action | Verify Alice là người gửi → Forward | Check Token hợp lệ → Forward (Không biết ai gửi) |

   

> **User Experience**
>  2. Traffic Padding Strategy (PADME Protocol) 

Chống lại việc đoán nội dung dựa trên kích thước file (Side-channel Attack).
 
 
* **Fixed Size Chunks:** Mọi gói tin được đệm (Padding) để đạt kích thước  `4KB` hoặc lũy thừa của 2.   
*Ví dụ: Gửi text "OK" (2 bytes) → Gói tin thực tế: 4096 bytes (4094 bytes rác).*  
* **Cover Traffic:** Trong High Security Mode, Client tự động gửi gói tin rác (Dummy Packet) ngẫu nhiên mỗi 5-10 giây để làm phẳng biểu đồ lưu lượng. 
  

```

// Rust: The Sealed Envelope
struct SealedMessage {
    // Visible to Server (Routing only)
    recipient_token: [u8; 32], // Hash(Recipient_Secret + Epoch)
    
    // Encrypted Content (Server sees random noise)
    ciphertext: [u8; 4096],    // Cố định 4KB (đã padding)
}

// Bên trong ciphertext sau Decrypt:
struct InnerPayload {
    sender_id: PublicKey,  // Server không thấy
    signature: Signature,  // Xác thực tại Client nhận
    padding_len: u16,
    content: Vec
}

```

   **✅ ENTERPRISE ANSWER:**  
 *"Nếu Server bị chiếm quyền, họ có biết CEO đang liên lạc với ai không?"* → **KHÔNG**. Server chỉ thấy các gói 4KB bay đến Token vô danh, không có thông tin người gửi (Signal-grade privacy).     

## 4.1 Observability & SLA  `White Box Ops`
 

Biến hạ tầng thành "Hộp trắng" vận hành (Metrics, Logs, Traces) nhưng vẫn giữ "Hộp đen" về dữ liệu nội dung.
 

> **Under The Hood**
>  1. The O11y Pipeline (LGTM Stack) 

Stack đo lường tiêu chuẩn, tích hợp sẵn trong Binary (Rust/Go):
 
 
* **Metrics (Prometheus):** Đo nhịp tim hệ thống (CPU, RAM, Connections). 
* **Logs (Loki):** Structured JSON Logs (Che giấu IP/User). 
* **Traces (Tempo):** Theo vết gói tin qua các Relay Node (Waterfall Chart). 
  

> **User Experience**
>  2. Key Metrics & Code Instrumentation  

```

// Rust Example: Measuring Packet Latency
async fn handle_packet(req: Request) -> Response {
    let start = Instant::now();
    let response = process(req).await;
    
    // Ghi vào Prometheus Histogram (đơn vị ms)
    histogram!("terachat_delivery_latency_ms", start.elapsed().as_millis());
    
    if response.is_error() {
        counter!("terachat_errors_total", 1);
    }
    response
}

```

         ``     ``     ``     ``    

| Metric Name | Type | Ý nghĩa Enterprise |
| --- | --- | --- |
| active_connections | Gauge | Số lượng User đang online. |
| delivery_latency_ms | Histogram | Quan trọng nhất cho SLA (Target < 200ms). |
| relay_buffer_bytes | Gauge | Cảnh báo nghẽn (Backpressure) nếu đầy. |
| decryption_failures | Counter | Phát hiện tấn công hoặc lệch Key. |

  

> **Under The Hood**
>  3. Service Level Agreement (SLA) Targets 

Cam kết chất lượng dịch vụ với khách hàng Doanh nghiệp:
 
 
* **Availability:** 99.9% (Downtime < 43 phút/tháng). Dựa trên Healthcheck API. 
* **Latency (p95):** < 200ms trong mạng LAN/WAN nội bộ (Loại trừ Tor). 
* **Error Rate:** < 0.1% Request 5xx. 
    

## 4.2 Deployment & Orchestration  `Cloud Native`
 

Kiến trúc triển khai quy mô lớn (20.000+ Users) sử dụng Kubernetes và các chuẩn Enterprise.
 

> **Under The Hood**
>  1. Architecture: K8s-First Strategy 

Chuyển từ "VPS lẻ" (Pets) sang "Cluster tự động" (Cattle):
 
 
* **Helm Charts:** Đóng gói tiêu chuẩn (Relay, Signaling, IAM, DB HA). 
* **High Availability (HA):** Auto-scaling (HPA) cho Relay Nodes. Postgres Operator cho Database. 
* **GitOps:** Quản lý cấu hình bằng Code (ArgoCD). Rollback tự động khi lỗi. 
  

> **User Experience**
>  2. Client Deployment: Mobile Device Management (MDM) 

Tự động cấu hình 20.000 thiết bị qua **AppConfig Community Standard** (Intune/VMware).
         **** `` ``   **** ``  
``  
``  

| Tiêu chí | Windows (Intune/GPO) | macOS (Jamf/MDM) |
| --- | --- | --- |
| Cơ chế | Registry Key (HKLM\Software\Policies) | Managed Preferences (plist) |
| Key Config | - server_url: https://internal-chat.bank-x.com                             - cert_pinning_hash: "sha256/..."                             - disable_camera: true |  |

   

> **Under The Hood**
>  3. Air-Gapped Delivery (Mạng cô lập) 

Quy trình triển khai cho môi trường không Internet (Quốc phòng/Chính phủ):
 
 
1. **Offline Bundle:** Script `docker save` toàn bộ hệ thống -> File `.tar.gz` (5GB). 
1. **Private Registry:** Load ảnh vào Harbor nội bộ của khách hàng. 
1. **Local Helm:** Cài đặt trỏ về Registry nội bộ. Không kết nối Docker Hub. 
    

## 4.3 Production Config (5,000 CCU)  `Ready-to-Deploy`
 

Cấu hình Helm Chart chuẩn Enterprise cho quy mô 5.000 Concurrent Users. Tuân thủ nguyên tắc High Availability (HA).
 

> **Under The Hood**
>  Strategy: "Cattle, not Pets" 

File `values-production-5k.yaml` này định nghĩa hạ tầng có khả năng tự phục hồi:
 
 
* **Relay Nodes:** 3 Replicas chạy trên 3 server vật lý khác nhau (Anti-Affinity). 
* **Resource Limits:** QoS Burstable (0.5 -> 2 Core) để chịu tải đột biến. 
* **Data Layer:** Postgres HA (Repmgr) tự động bầu Master mới trong 10s. 
   # values-production-5k.yaml 

```

global:
  domain: "chat.bank-enterprise.internal"
  environment: "production"
  imageRegistry: "registry.bank-internal.com"

# 1. RELAY NODES (Stateless Backbone)
relay:
  enabled: true
  image: { repository: "terachat/enterprise-relay", tag: "v2.1.0-rust-optimized" }
  replicaCount: 3
  
  # Autoscaling: CPU > 70% -> Scale up to 15 pods
  autoscaling:
    enabled: true
    minReplicas: 3
    maxReplicas: 15
    targetCPUUtilizationPercentage: 70

  # QoS: Burstable
  resources:
    requests: { cpu: "500m", memory: "512Mi" }
    limits: { cpu: "2000m", memory: "2Gi" }

  # Topology Spread: Ensure High Availability across physical nodes
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchExpressions:
              - key: app
                operator: In
                values: ["terachat-relay"]
          topologyKey: "kubernetes.io/hostname"

# 2. SIGNALING (WebSockets)
signaling:
  enabled: true
  replicaCount: 3
  sessionAffinity: { enabled: true, timeoutSeconds: 3600 }

# 3. IDENTITY BRIDGE
iam:
  enabled: true
  provider: "keycloak-sidecar"
  config: { scimEnabled: true, syncInterval: "30s" }

# 4. STORAGE HA (Bitnami Sub-charts)
postgresql-ha:
  enabled: true
  postgresql: { repmgr: { enabled: true } } # Auto-failover
  pgpool: { enabled: true, replicaCount: 2 }

redis-ha:
  enabled: true
  sentinel: { enabled: true }

# 5. SECURITY GATEWAY
ingress:
  enabled: true
  annotations:
    nginx.ingress.kubernetes.io/limit-rps: "100"
    nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8"

```

  

> **Under The Hood**
>  Deployment Command 

Triển khai cho khách hàng:
  helm install terachat-enterprise ./charts/terachat \  
 --namespace terachat-prod \  
 --values values-production-5k.yaml \  
 --set postgresql-ha.postgresql.password=$(vault kv get -field=db_pass secret/terachat)     

## 4.4 Interoperability & ESB  `Integration Hub`
 

Phá bỏ rào cản "Walled Garden". Biến TeraChat thành cổng giao tiếp trung tâm (Notifications Center) cho mọi ứng dụng doanh nghiệp (SAP, Jira, CRM).
 

> **Under The Hood**
>  1. Architecture: The "Headless" Bot Gateway 

Middleware đóng vai trò phiên dịch viên giữa thế giới HTTP/JSON (Legacy) và E2EE/MLS (TeraChat):
 
 
* **Inbound (Gửi tin):** SAP gọi Webhook -> Gateway mã hóa E2EE (dùng Key ảo) -> Đẩy xuống App. 
* **Outbound (Hành động):** User bấm nút trên App -> App ký số -> Gateway giải mã & xác thực -> Gọi lại API SAP. 
  

> **User Experience**
>  2. UI/UX: Adaptive Cards Engine 

Thay vì tin nhắn text vô hồn, gửi các Mini-Form tương tác (JSON-driven UI).
  

```

// JSON Payload from SAP to Mobile App
{
  "type": "interactive_card",
  "body": [
    { "type": "text", "text": "YÊU CẦU THANH TOÁN", "weight": "heavy" },
    { "type": "fact_set", "facts": [
        { "title": "Vendor:", "value": "AWS Inc" },
        { "title": "Amount:", "value": "$50,000" }
      ]
    }
  ],
  "actions": [
    {
      "type": "button",
      "style": "positive",
      "label": "DUYỆT NGAY (Windows Hello)",
      "action_id": "approve_payment_123",
      "require_biometric": true // Trigger Hardware Signer
    }
  ]
}

```

  

* Desktop App sẽ render JSON này thành Native View (React/Tauri) mượt mà.
  

> **Under The Hood**
>  3. Security Hardening & Plugins        **** ****   **** ****  

| Layer | Giải pháp |
| --- | --- |
| Transport Auth | mTLS (Mutual TLS): Gateway chỉ nhận request từ Server có Certificate nội bộ hợp lệ. Chống giả mạo SAP. |
| Extensibility | Lua/WASM Plugins: Cho phép IT viết script xử lý luồng (Logic) tùy chỉnh mà không cần sửa core Gateway. |

   LUA PLUGIN EXAMPLE:  if jira_data.priority == "High" then  
 terachat.send_card(jira_data.assignee, { title="CRITICAL BUG", actions=["Fix Now"] })  
 end       

## 4.5 Security Governance & Day-2 Ops  `CIO Mandatory`
 

Không chỉ là tính năng, đây là cam kết về Sự an toàn Chuỗi cung ứng, Vận hành bền vững và Tuân thủ pháp lý cao cấp.
 

> **Under The Hood**
>  1. Supply Chain Security (SBOM) 

Chống cài cắm mã độc từ gốc (Build Phase):
 
 
* **SBOM (Software Bill of Materials):** Cung cấp file `spdx.json` liệt kê toàn bộ 1,500 thư viện phụ thuộc. Khách hàng có thể quét lỗ hổng (CVE) độc lập. 
* **Reproducible Builds:** Cam kết Binary Hash luôn trùng khớp với Source Code, chứng minh không có "Backdoor" được inject bí mật khi compile. 
  

> **Under The Hood**
>  2. Advanced Database Strategy        **** ****   **** ****  

| Yêu cầu | Giải pháp Day-2 |
| --- | --- |
| Zero-Downtime Migration | Sử dụng Blue-Green Deploys cho DB. Ứng dụng hỗ trợ song song 2 phiên bản Schema (n-1 và n) trong quá trình Rolling Update. |
| Data Sovereignty | Geo-Partitioning (Postgres): Dữ liệu user Đức (GDPR) được ghim cứng tại Node Frankfurt, không replicate sang Node Vietnam. |

   

> **Under The Hood**
>  3. Must-Have Operations Checklist 

Danh sách các module bổ trợ bắt buộc cho Enterprise:
 
 
* **🛡️ RASP (Runtime Protection):** Chống Debug/Dump RAM ngay cả khi máy bị nhiễm virus. 
* **🧠 UEBA (Behavior Analytics):** Dùng ML phát hiện CEO đăng nhập lúc 3h sáng để tải 1GB dữ liệu -> Block ngay. 
* **🌪️ Chaos Engineering:** Tích hợp Chaos Mesh để khách hàng tự diễn tập "rút dây nguồn" Server. 
* **🔍 Encrypted Search:** Tìm kiếm trên dữ liệu mã hóa (Blind Seer) mà Server không cần giải mã. 
* **⚖️ Legal Hold:** Chế độ "Đóng băng" tài khoản đang bị điều tra, vô hiệu hóa Remote Wipe. 
  

> **User Experience**
>  4. Deep Dive: Critical Solutions  **A. Air-Gapped Patching (BSDiff)** 
 
* **Thực trạng:** Mạng nội bộ băng thông yếu, không thể tải 500MB update cho 5,000 máy. 
* **Giải pháp:** Chỉ tải file **Delta Patch** (vài KB/MB). Client tự vá binary cũ (In-place patching) sau khi verify chữ ký số. 
   **B. GDPR-Compliant Blockchain (Crypto-shredding)** 
 
* **Mâu thuẫn:** Blockchain là vĩnh viễn <-> GDPR yêu cầu quyền được quên. 
* **Giải pháp:** Chỉ lưu `Hash(Encrypted_Data)` lên Chain. Khi cần xóa, chỉ cần hủy khóa giải mã (Key Destruction). Dữ liệu còn đó nhưng vĩnh viễn không thể đọc. 
   

> **Under The Hood**
>  5. Endpoint Trust & Quality (Military Grade) 

Cơ chế xác thực thiết bị và kiểm thử nâng cao:
 
 
* **Remote Attestation (TPM 2.0):** Server chỉ gửi Key giải mã sau khi nhận được "Health Quote" có chữ ký của TPM, chứng minh Secure Boot đang bật và Kernel không bị tamper. 
* **Continuous Fuzzing (AFL++):** Hệ thống CI/CD liên tục bơm dữ liệu rác vào các hàm Protocol để tìm lỗi Mem Leak/Crash tiềm ẩn (Zero-day). 
  

> **Under The Hood**
>  6. Deep Security & Obfuscation 

Làm nản lòng Reverse Engineer:
 
 
* **Control Flow Flattening:** Biến đổi luồng code (Workflow) thành một Switch-Case khổng lồ để che giấu logic thật. 
* **String Encryption (XOR):** Không bao giờ lưu chuỗi plain text (API Key, Error Msg) trong binary. 
      

## 4.6 Web-based Installer `One-Tap Deploy`

Hiện thực hóa khái niệm "1 chạm" (One-Tap) cho việc triển khai hạ tầng phức tạp. **"Bấm Next 3 lần → Có ngay hệ thống Chat nội bộ riêng tư."** Target: Công ty SME không có đội IT xịn.

> **Triết lý CEO:** Đừng cố "1 chạm" từ A-Z cho mọi thứ. Dùng chiến thuật **"Abstraction Layer"** — ẩn Terraform/Ansible bên dưới. Chia 2 luồng: Cloud có API vs Server riêng không API.

### Luồng 1: Cloud Path (AWS / GCP / DigitalOcean) — Terraform

**Bước 1: Chọn Chế Độ**
* 👤 **Personal:** Tự host trên VPS $5. Free License.
* 🏢 **Enterprise:** Cho công ty >50 người. Cần License Key.

**Bước 2: Chọn Cloud Provider**
* Grid Layout: [AWS], [DigitalOcean], [Google Cloud].
* **UX 1 Chạm (OAuth):** Nút "Connect Account" → Cấp quyền API tự động.

**Bước 3: Cấu hình Quy mô (Enterprise Only)**
* **Start-up:** 1 Server (Docker Compose). Max 100 User.
* **SME:** 3 Servers (K8s Cluster). Max 1,000 User.
* **Corp:** 5+ Servers (HA). Max 5,000 User.

**Bước 4: 🚀 DEPLOY NOW**
* Backend điền API Key của user vào `main.tf` → chạy `terraform apply` ngầm.
* Tự động: Tạo VM → Mở Port → Cài Docker → Pull Image TeraChat → Start.
* User chỉ thấy **Progress Bar** đẹp mắt + Log rút gọn.

### Luồng 2: BYOS — Bring Your Own Server (Magic Script)

Dành cho khách hàng có server riêng (Bare Metal, VPS cũ, On-Premise). Không có API → không thể dùng Terraform.

**Giải pháp: Magic Command (1 dòng lệnh duy nhất)**

```bash
curl -sL install.terachat.com | sudo bash
```

Khách hàng chỉ cần SSH vào server → paste dòng lệnh trên. Script tự động:
1. **Pre-flight Check** (Kiểm tra trước khi cất cánh)
2. Cài Docker & Docker Compose
3. Kéo Image TeraChat về và chạy
4. Gửi tín hiệu "Thành công" ngược lại Web Installer

### Pre-flight Check (Bắt buộc cho cả 2 luồng)

Trước khi cài đặt, hệ thống kiểm tra yêu cầu tối thiểu. Nếu không đạt → **từ chối cài đặt** (đừng cố cài đè rồi gây lỗi):

| Kiểm tra | Yêu cầu tối thiểu | Hành vi khi Fail |
|----------|-------------------|-------------------|
| RAM | ≥ 4GB | ❌ Báo lỗi đỏ, dừng ngay |
| Port 443/80 | Phải trống | ⚠️ Cảnh báo xung đột, hướng dẫn giải phóng |
| OS | Ubuntu 20+ / Debian 11+ / CentOS 8+ | ❌ Từ chối, hiện danh sách OS hỗ trợ |
| Docker | Bất kỳ version | ✅ Tự cài nếu chưa có |
| Disk | ≥ 20GB trống | ❌ Báo lỗi, yêu cầu dọn dẹp |

### Docker Containerization (Tách biệt hoàn toàn)

> **CEO Rule:** Đóng gói TẤT CẢ (Database, Redis, App) vào trong Docker. Không cài trực tiếp lên Host OS.

Điều này đảm bảo môi trường TeraChat **tách biệt hoàn toàn** với phần mềm rác trên máy khách hàng. Nếu cần xóa TeraChat → `docker compose down -v` → Sạch sẽ.

### Stateful Installer (Chống mất kết nối)

> **Rủi ro:** User tắt trình duyệt giữa chừng, mạng lag, mất kết nối WiFi.

**Giải pháp:** Tiến trình cài đặt chạy trên **Backend** (server của TeraChat), không phải trên trình duyệt.

* User tắt browser đi ngủ → Sáng mai mở lại → Installer hiện: *"Đã cài xong 80%, đang đợi khởi động Database"*
* **WebSocket** push trạng thái real-time từ Backend → Frontend
* Mỗi bước cài đặt có **checkpoint**. Nếu fail giữa chừng → resume từ checkpoint, không cài lại từ đầu.

### Day-2 Ops: Update & Rollback

| Tính năng | UX Mechanism |
| --- | --- |
| **1-Tap Update** | Thanh thông báo: *"Đã có phiên bản mới v1.2.0"*. Nút **[ Update System Now ]** với cảnh báo bảo trì 30s. |
| **Time Machine** | Nút **[ Rollback ]** về v1.1.0 ngay lập tức nếu bản mới lỗi. GitOps/Helm Rollback ngầm. |

### Tech Stack

* **Frontend:** React/Vue.js (SPA mượt mà).
* **Backend:** Rust (Hiệu năng cao, WebSocket server).
* **Cloud Orchestrator:** Terraform (Tạo server) + Ansible (Cài software). Ẩn toàn bộ YAML/CLI.
* **BYOS Orchestrator:** Shell Script + Docker Compose. Zero dependency ngoài `curl` và `bash`.
 

## 6.1 Business API Integration Package  `Productivity Hub`
 

Biến TeraChat thành **trung tâm năng suất doanh nghiệp** (Productivity Hub), không chỉ là ứng dụng chat. Gói API Business chuẩn hóa cho phép mọi hệ thống doanh nghiệp tích hợp sâu vào luồng giao tiếp E2EE.
 

> **Under The Hood**
>  1. Architecture: Business API Gateway 

```

┌─────────────────────────────────────────────────┐
│             TeraChat Business API               │
│                  (Gateway)                      │
├─────────────┬──────────────┬───────────────────┤
│  REST API   │  WebSocket   │  Webhook Engine   │
│  (CRUD)     │  (Realtime)  │  (Event Push)     │
├─────────────┴──────────────┴───────────────────┤
│           Authentication & Authorization        │
│     (OAuth 2.0 + API Key + mTLS + OPA)         │
├────────────────────────────────────────────────┤
│               E2EE Bridge Layer                │
│   (Bot KeyPair → MLS Group → Encrypt/Decrypt)  │
├────────────────────────────────────────────────┤
│             TeraChat Core (Rust)               │
└────────────────────────────────────────────────┘

```

  

> **Under The Hood**
>  2. Tiered API Packages 

| Gói | Tên | Tính năng | Đối tượng |
| --- | --- | --- | --- |
| **Tier 1** | **Notify API** | Gửi tin nhắn, Adaptive Cards, File đính kèm vào channel | IT Manager cần thông báo tự động |
| **Tier 2** | **Workflow API** | Approval flows, Interactive buttons, Form submission, Slash commands | PM cần quy trình duyệt |
| **Tier 3** | **Data Export API** | Compliance export, Audit trail, Legal Hold integration | CISO/DPO cần tuân thủ |
| **Tier 4** | **Bot Builder SDK** | Full bot lifecycle, Custom Mini-Apps, Plugin marketplace | Developer tạo tích hợp riêng |

  

> **User Experience**
>  3. REST API Endpoints 

```

# ── MESSAGING ──────────────────────────────
POST   /api/v1/messages                  # Gửi tin nhắn (text/card/file)
POST   /api/v1/messages/card             # Gửi Adaptive Card (Interactive UI)
GET    /api/v1/messages/{channel_id}     # Lấy tin nhắn (Encrypted metadata only)
DELETE /api/v1/messages/{msg_id}         # Xóa tin nhắn (Crypto-Shred)

# ── CHANNELS ───────────────────────────────
POST   /api/v1/channels                  # Tạo channel
GET    /api/v1/channels                  # Liệt kê channels (có phân quyền OPA)
PUT    /api/v1/channels/{id}/members     # Quản lý thành viên
POST   /api/v1/channels/{id}/topics      # Tạo Topic Thread

# ── WORKFLOWS ──────────────────────────────
POST   /api/v1/workflows/approval        # Tạo luồng phê duyệt
POST   /api/v1/workflows/slash-command   # Đăng ký Slash Command
GET    /api/v1/workflows/{id}/status     # Theo dõi trạng thái

# ── USERS & IDENTITY ──────────────────────
GET    /api/v1/users                     # Danh sách users (SCIM-synced)
GET    /api/v1/users/{id}/presence       # Online status
POST   /api/v1/users/{id}/notify         # Direct notification

# ── WEBHOOKS ───────────────────────────────
POST   /api/v1/webhooks/incoming         # Đăng ký incoming webhook
POST   /api/v1/webhooks/outgoing         # Đăng ký outgoing webhook
GET    /api/v1/webhooks/{id}/logs        # Audit log webhook delivery

# ── COMPLIANCE (Tier 3) ───────────────────
POST   /api/v1/compliance/export         # Export dữ liệu (GDPR)
POST   /api/v1/compliance/legal-hold     # Đóng băng tài khoản
GET    /api/v1/compliance/audit-trail    # Truy vết hành vi

# ── BOT MANAGEMENT (Tier 4) ──────────────
POST   /api/v1/bots                      # Đăng ký bot mới
PUT    /api/v1/bots/{id}/permissions     # Cấu hình quyền bot
POST   /api/v1/bots/{id}/miniapp        # Deploy Mini-App cho bot

```

  

> **Under The Hood**
>  4. WebSocket Realtime Events 

```json

{
  "type": "event",
  "event": "message.new",
  "data": {
    "channel_id": "ch_abc123",
    "sender_id": "usr_xyz789",
    "content_type": "adaptive_card",
    "encrypted_payload": "base64...",
    "timestamp": "2026-02-10T12:00:00Z"
  }
}

```

**Danh sách Events quan trọng:**

* `message.new` / `message.deleted` / `message.reaction`
* `channel.member_joined` / `channel.member_left`
* `workflow.approval_requested` / `workflow.approved` / `workflow.rejected`
* `user.presence_changed` / `user.device_verified`
* `security.threat_detected` / `security.device_revoked`
  

> **Under The Hood**
>  5. E2EE Bridge cho Bot 

Giải quyết bài toán Bot cần đọc/gửi tin trong môi trường E2EE (Server "mù"):

| Mô hình | Cơ chế | Khi nào dùng |
| --- | --- | --- |
| **Service Bot (On-Prem)** | Bot chạy trong network nội bộ, có KeyPair riêng, join MLS Group như member thường | Khi cần bot đọc nội dung (AI Assistant, Search) |
| **Notification Bot (Proxy)** | Bot không join MLS Group, chỉ gửi tin 1 chiều qua Gateway → Encrypt bằng Bot Key → Forward | Khi chỉ cần push thông báo (Jira, SAP) |
| **Stateless Webhook** | Không có key, chỉ trigger event ra ngoài (không nội dung, chỉ metadata) | Khi cần integration nhẹ (Zapier, n8n) |

  

> **User Experience**
>  6. Pre-built Connectors 

| Connector | Loại | Chức năng |
| --- | --- | --- |
| **Jira/Linear** | Workflow | Tạo ticket từ chat, cập nhật trạng thái, notify assignee |
| **SAP/Oracle ERP** | Notify + Workflow | Yêu cầu duyệt chi, PO approval, budget alert |
| **GitHub/GitLab** | Notify | PR review, CI/CD status, merge notification |
| **Google Workspace** | Workflow | Calendar invite từ chat, Drive file sharing |
| **Microsoft 365** | Workflow | Teams bridge, SharePoint integration, Azure AD sync |
| **Salesforce** | Notify + Workflow | Lead notification, deal approval, quote signing |
| **Slack Bridge** | Bridge | 2-way message sync cho giai đoạn migration |
| **n8n/Zapier** | Webhook | No-code automation cho IT teams |

  

> **User Experience**
>  7. TypeScript SDK Example 

```typescript

import { TeraChatClient } from '@terachat/sdk';

const client = new TeraChatClient({
  apiKey: process.env.TERACHAT_API_KEY,
  serverUrl: 'https://chat.company.internal',
});

// Gửi Adaptive Card
await client.messages.sendCard('channel_budget', {
  title: 'YÊU CẦU DUYỆT NGÂN SÁCH',
  facts: [
    { title: 'Vendor', value: 'AWS Inc' },
    { title: 'Amount', value: '$50,000' },
  ],
  actions: [
    {
      label: '✅ DUYỆT (Sinh trắc học)',
      action: 'approve_payment_123',
      requireBiometric: true
    },
    {
      label: '❌ TỪ CHỐI',
      action: 'reject_payment_123'
    }
  ]
});

// Lắng nghe Realtime Events
client.on('workflow.approved', async (event) => {
  await sapClient.releasePO(event.data.reference_id);
  await client.messages.send(event.channel_id, 
    `✅ PO #${event.data.reference_id} đã được giải ngân.`
  );
});

```

    

## 6.2 Topic-based Threading  `Productivity`
 

Giải quyết vấn đề chat doanh nghiệp 5000+ người trôi tuyến tính, mất thông tin. Học từ mô hình **Zulip** (Topic Threading) và **Element** (Matrix Threads/Spaces) — nhưng **đơn giản hóa UI** và thêm **AI Summary** mà Zulip không có.
 

> **Under The Hood**
>  Architecture: Hierarchical Channel → Topic Model 

* Mỗi Channel có thể tạo **Topic Thread** (sub-channel gắn với chủ đề cụ thể).
* MLS Group Key được chia cấp: `Channel_Key → Topic_Key`.
* Thread metadata được index trong SQLCipher để hỗ trợ tìm kiếm nhanh.
* **UI Layout (Anti-Zulip):** Sidebar trái = **Channel List**, sidebar phải = **Active Threads**. Không trộn lẫn vào giữa như Zulip (quá rối mắt cho non-dev).
* **🤖 AI Thread Summary (Local Llama 3):** Tích hợp AI chạy **100% Local** (không gửi data ra ngoài). Sếp đi vắng 1 tuần? Bấm nút **"Tóm tắt"** → AI tóm tắt toàn bộ Thread: *"Đội Dev cãi nhau về API, cuối cùng chốt phương án B, đã deploy lúc 3h chiều"*. **Đây là điểm sát thủ so với Zulip.**
  

> **User Experience**
>  Quy trình Sử dụng 

1. User vào Channel "Engineering" → Thấy danh sách Topics: `[Bug #1234]`, `[Release v2.1]`, `[Code Review]`
2. Gửi tin vào Topic cụ thể → Tin nhắn được gắn nhãn Topic, không trôi lẫn.
3. Notification thông minh: Chỉ ping khi có tin trong Topic mà user theo dõi.
4. **AI Catch-up:** Sếp bấm nút 🤖 trên Topic → Nhận bản tóm tắt nội dung tuần qua trong 3 giây (xử lý hoàn toàn trên thiết bị).
    

## 6.3 CRDT-based Offline Conflict Resolution  `Resilience`
 

Giải quyết vấn đề Air-Gapped Mesh thiếu cơ chế resolve conflict khi 2 người edit cùng lúc offline. Học từ **Berty** (Wesh Protocol/CRDT) và **Keet** (Hypercore).
 

> **Under The Hood**
>  Engine: Automerge CRDT Integration 

* Tích hợp **Automerge CRDT** (Rust library) vào Rust Core.
* Mỗi document/message mang **Vector Clock** + **Causal ordering**.
* Khi reconnect, merge tự động thay vì "Last Write Wins".
* Áp dụng cho: Message ordering, Shared Document editing, Admin Policy sync.
    

## 6.4 Integration Hub & Multi-Platform Bridge  `Integration Hub`
 

**"Dùng 1 app, quản lý mọi nền tảng."** Thay vì cố xây Federation phức tạp như Matrix (Synapse ăn RAM khủng khiếp), TeraChat ưu tiên **Bridges-first** — kết nối với hệ sinh thái có sẵn để doanh nghiệp không cần ép nhân viên đổi app.
 

> **Under The Hood**
>  Architecture: TeraChat Integration Hub 

**Phase 1 — Multi-Platform Bridges (MVP):**
* **Telegram Bridge:** Nhận/gửi tin nhắn từ Telegram Group ngay trong TeraChat.
* **WhatsApp Bridge:** Hỗ trợ khách hàng qua WhatsApp mà không rời khung chat.
* **Slack Bridge:** Đồng bộ Channel Slack ↔ TeraChat cho giai đoạn chuyển đổi.
* **Tất cả Bridges** chạy qua E2EE Relay — tin nhắn được mã hóa ở 2 đầu, Bridge Server chỉ thấy blob.

**Phase 2 — Inter-org Federation:**
* Relay Server A ↔ Relay Server B qua **mTLS + Sealed Sender**.
* Mỗi org giữ dữ liệu riêng, chỉ forward E2EE payload qua Federation Bridge.

> **Lợi thế vs Element:** Không cần cài Synapse nặng nề. Bridges nhẹ, dễ deploy, target SME không có đội IT xịn.
    

## 6.5 Rich File Preview  `Sandbox Extension`
 

Mở rộng WASM Sandbox (Code Vault) để preview tài liệu kinh doanh. Học từ **Nextcloud Talk** (tích hợp Nextcloud Files).
 

> **Under The Hood**
>  Engine: Extended WASM Sandbox 

* Render trong WASM Sandbox: PDF (`pdf.js`), DOCX (`Mammoth.js`), Excel (`SheetJS`).
* Giữ nguyên **Dynamic Watermark + Anti-Screenshot** cho tất cả preview.
* Streaming P2P từ RAM (không lưu file), giống cơ chế Code Vault hiện tại.
    

## Appendix B: Competitive Analysis Matrix
 

Đối sánh TeraChat V0.2.1 Alpha với 8 nền tảng nhắn tin doanh nghiệp tham chiếu.

| Tiêu chí | TeraChat V0.2.1 | Zulip | Element (Matrix) | Wire | Threema | Jami | Keet | Berty |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Mô hình** | Federated Clusters + Mesh | Client-Server | Federated (S2S) | Client-Server | Client-Server | Pure P2P (DHT) | Pure P2P (Hypercore) | P2P (IPFS/CRDT) |
| **E2EE** | MLS (RFC 9420) | ❌ (TLS only) | Megolm/Vodozemac | MLS (Proteus→MLS) | NaCl-based | TLS 1.3 + SIP/TLS | Noise Protocol | X3DH + Double Ratchet |
| **Offline** | Air-Gapped Mesh + BLE | ❌ | ❌ | ❌ | ❌ | Giới hạn (DHT) | Hyperswarm | ✅ BLE/Wi-Fi Direct |
| **Self-hosted** | ✅ Enterprise | ✅ OSS | ✅ Homeserver | ✅ On-Prem | ❌ (SaaS) | ✅ (No server) | ✅ (No server) | ✅ (No server) |
| **Enterprise IAM** | OIDC/SCIM + OPA | LDAP/SAML | OIDC/SAML | SCIM/SSO | MDM API | ❌ | ❌ | ❌ |
| **Thanh toán tích hợp** | ✅ PayPal Native (1-chạm) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Business API** | ✅ Tiered (4 gói) | ✅ REST API | ✅ Client-Server API | ✅ REST + Bot SDK | ✅ Gateway API | ❌ | ❌ | ❌ |
| **Topic Threading** | ✅ (Section 6.2) | ✅ (Core USP) | ✅ (Threads/Spaces) | ❌ | ❌ | ❌ | ❌ | ❌ |
| **AI Local** | ✅ Llama 3 (100% Local) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **LAN P2P Transfer** | ✅ 100MB/s (P2P Torrent) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Hypercore | ❌ |
| **Bots/Integration** | ✅ SDK + Connectors | ✅ Bot Framework | ✅ Widgets/Bridges | ✅ Bot Service | ✅ Gateway | ❌ | ❌ | ❌ |
      