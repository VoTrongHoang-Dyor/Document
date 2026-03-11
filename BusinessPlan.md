# TeraChat — Hệ điều hành Bảo mật cho Doanh nghiệp Thời đại Số

> *"Chúng tôi không bán phần mềm chat. Chúng tôi bán chủ quyền số — quyền kiểm soát tuyệt đối thông tin của chính doanh nghiệp bạn, ngay cả khi Internet sụp đổ."*
>
> — CEO, TeraChat

---

## Executive Summary

Thế giới doanh nghiệp đang đối mặt với một nghịch lý: càng dùng nhiều công cụ cộng tác, càng mất kiểm soát dữ liệu. Slack, Teams, Zoom — tất cả đều chạy trên hạ tầng của bên thứ ba. Mỗi cuộc họp chiến lược, mỗi hợp đồng nhạy cảm, mỗi quyết định nội bộ — đều đi qua server của người khác.

**TeraChat xây dựng trên nguyên tắc đối lập hoàn toàn:** Zero-Knowledge từ server. End-to-End Encryption từ thiết bị đầu cuối. Khả năng hoạt động ngay cả khi bị cắt Internet hoàn toàn. Kiến trúc "Không Bandwith Cost" — doanh nghiệp tự host, TeraChat chỉ bán License. Mỗi khách hàng mới là doanh thu thuần, không penalizing chi phí vận hành.

**Tại sao bây giờ?** Nguy cơ gián điệp công nghiệp, rò rỉ dữ liệu qua nội bộ, và sức ép pháp lý (GDPR, ISO 27001, Circular 13) tạo ra nhu cầu tức thì tại các thị trường tài chính, chính phủ, và tập đoàn lớn. TeraChat là câu trả lời đầu tiên được xây dựng đúng — không phải chắp vá thêm tính bảo mật sau khi sản phẩm đã ra đời.

> **Document Owner:** CEO / Co-founders / Business Team
> **Audience:** Investors (VC), Executives, Sales, Business Development
> **Scope:** Business model, revenue, competitive advantage, GTM strategy, licensing, and funding.

---

## TABLE OF CONTENTS

1. [Business Model & Revenue Streams](#1-business-model--revenue-streams)
2. [Competitive Advantage](#2-competitive-advantage)
3. [Go-to-Market Strategy & Operations](#3-go-to-market-strategy--operations)
4. [Licensing & IP Strategy (Open-Core)](#4-licensing--ip-strategy-open-core)
5. [Anti-Fragmentation & Forced Upgrade Strategy](#5-anti-fragmentation--forced-upgrade-strategy)
6. [Funding Allocation](#6-funding-allocation)

---

## 1. Business Model & Revenue Streams

### 1.1 Tổng quan Mô hình Kinh doanh

> **"Chúng ta không bán dung lượng. Chúng ta bán Sự tự chủ và Bảo mật tuyệt đối."**

TeraChat hoạt động theo mô hình **B2B Enterprise Software** với điều khác biệt cốt lõi: **Doanh nghiệp tự trả tiền cho hạ tầng của họ — TeraChat chỉ bán License phần mềm.**

**Kiến trúc "Zero Bandwidth Cost":**

| Mô hình truyền thống (Slack, Teams) | TeraChat |
|---|---|
| Khách hàng dùng Cloud Server của nhà cung cấp | Khách hàng tự host Private Cluster/VPS của họ |
| Chi phí Server tăng theo số User | Chi phí Server của TeraChat = $0 (Khách hàng tự trả) |
| Biên lợi nhuận gộp 60–75% | Biên lợi nhuận gộp **> 90%** |
| OPEX phình to theo quy mô | OPEX **không phình** theo số lượng khách hàng |

**Kết quả:** Mỗi khách hàng mới thêm → doanh thu tăng, chi phí không tăng theo.

### 1.2 Revenue Streams

**A. Phí Subscription theo quy mô (Enterprise Subscription)**

- Nguồn thu **chính và lớn nhất**.
- Thu phí Subscription theo năm .
- Ví dụ pricing: **$500/tháng** (trả trước hàng năm).
- Doanh nghiệp nhập Azure AD/LDAP → hệ thống tự map số user → xuất hóa đơn.
- Hợp đồng 1–3 năm, **trả tiền upfront** → dòng tiền dương ngay từ ngày đầu.

**B. Phí Bảo trì & SLA (Maintenance + Service Level Agreement)**

- Thu phí bảo trì hàng năm đảm bảo nhận bản vá bảo mật + hỗ trợ kỹ thuật (Tier 2/3).
- Với Chính phủ / Ngân hàng: thu phí **triển khai on-premise ban đầu rất cao** (Professional Services).

**C. Enterprise Add-ons & Marketplace**

- **AI Module (Magic Logger / RAG):** Tích hợp AI phân tích hóa đơn F&B, văn bản hành chính — không đẩy dữ liệu ra ngoài để train model. Phí module riêng.
- **Reseller Mode:** Cấp phép cho công ty IT Service (MSP) đi bán và cài đặt cho chuỗi nhà hàng, bán lẻ. Ăn chia doanh thu với đối tác.
- **Compliance Export / Legal Hold:** Tier 3 API (CISO/DPO). Phí cao cho segment Gov/Banking.

**D. Deployment Models & Pricing Tiers**

| Model | Đối tượng | Hạ tầng | Ghi chú |
|---|---|---|---|
| **Managed SaaS** | Nhà hàng, SME (Non-Tech) | TeraChat Cloud | TeraChat quản lý hạ tầng. Admin công ty chỉ quản lý User. |
| **On-Premise** | Bank, Gov, Large Enterprise | Private Server (vật lý/VMware/K8s) | IT doanh nghiệp tự quản (Helm Chart). Data Sovereignty 100%. |
| **Reseller** | MSP / IT Service Company | Khách hàng cuối | MSP mua License bulk, cài & bảo trì cho chuỗi nhà hàng, shop. |

### 1.3 Vòng quay Dòng tiền (Cash Flow)

- Khách hàng Enterprise B2B ký hợp đồng dài hạn (1–3 năm) và **trả tiền trước (Upfront)**.
- Không gánh chi phí Server/Cloud hàng tháng cho khách → **Positive Cash Flow từ ngày đầu**.
- Dòng tiền này trực tiếp trả lương đội ngũ R&D mà không cần vốn bên ngoài cho giai đoạn đầu.

---

## 2. Competitive Advantage

### 2.1 Data Sovereignty (Chủ quyền Dữ liệu)

Đây là lý do duy nhất và đủ để Chính phủ và Ngân hàng mua TeraChat thay vì Slack hoặc Microsoft Teams:

> **"Dữ liệu sinh ra ở chi nhánh nào, nằm trên máy chủ vật lý của chi nhánh đó."**

| Đối thủ | Dữ liệu nằm ở đâu | Rủi ro |
|---|---|---|
| Slack | AWS Cloud (Mỹ) | Vi phạm GDPR, Luật An ninh mạng VN |
| Microsoft Teams | Azure (Global) | Tương tự |
| Zalo | Máy chủ VNG (VN) | Không phù hợp nhu cầu bảo mật cao nhất |
| **TeraChat** | **Private Cluster của doanh nghiệp** | **Zero-risk về data sovereignty** |

### 2.2 Zero-Trust Architecture

- Không ai, kể cả TeraChat, có thể đọc dữ liệu của khách hàng.
- E2EE tại thiết bị: Server chỉ thấy gói byte mã hóa.
- Kiến trúc "Blind Server": Metadata cũng được bảo vệ (Sealed Sender).
- Open-Core: Khách hàng có thể tự compile và kiểm chứng không có backdoor.

### 2.3 Transparent Transport Architecture — Kiến trúc Mạng Minh bạch

> **Lập trường:** TeraChat không sử dụng bất kỳ kỹ thuật shadow IT tunnel hay lách Firewall nào. Đây là Điểm bán hàng chiến lược với khách hàng Ngân hàng và Chính phủ — những tổ chức phải pass Penetration Test và Compliance Audit nghiêm ngặt nhất.

- ☁️📱💻 **ALPN Graceful Fallback (QUIC → gRPC → WebSocket):** Thay vì cố tình bypass Firewall, TeraChat tự động đàm phán giao thức xuống cấp: QUIC 0-RTT (nếu UDP được phép) → gRPC/HTTP2 TCP (mọi Firewall cho phép) → WebSocket (fallback tối thượng). Toàn bộ trong < 50ms, hoàn toàn minh bạch.
- ☁️ **Zero Shadow IT:** Mọi traffic của TeraChat đều đi qua cổng **TCP 443** chuẩn — Firewall Palo Alto, Fortinet, F5 đều nhận diện đây là HTTPS hợp lệ. Không có tunnel ẩn, không có port kỳ lạ, không có binary protocol không khai báo.
- ☁️🗄️ **Terraform/Helm Infrastructure-as-Code:** Cung cấp file cấu hình chuẩn cho IT Admin triển khai: khai báo minh bạch `udp_port_443: optional`, `tcp_port_443: required`, Token Bucket Rate-Limit để chống UDP Amplification DDoS. IT Admin toàn quyền quyết định network policy — TeraChat không yêu cầu exception đặc biệt.
- 📱💻 **Strict Compliance Network Mode:** Cho phép CISO/Admin tắt hẳn UDP probe, chạy straight TCP — tối ưu cho môi trường Firewall đã cấu hình sẵn. Mọi thay đổi network mode được audit log Ed25519 signed.
- 🏆 **Kết quả Penetration Test:** Kiến trúc này pass mọi bài test: không có open port bất thường, không có traffic pattern đáng ngờ, không bypass DPI. **Điểm bán:** *"TeraChat là ứng dụng chat duy nhất mà Security Officer của Ngân hàng Nhà nước có thể ký duyệt mà không cần exception policy đặc biệt."*

### 2.3 "Zero Bandwidth Cost" Business Model

Biên lợi nhuận gộp > 90% cho phép:

- Định giá linh hoạt để cạnh tranh với Slack/Teams.
- Đầu tư nhiều hơn vào R&D mà không cần đốt tiền Server.
- Mở rộng sang thị trường mới với rủi ro thấp.

#### GTM "Sát thủ": Tại sao TeraChat cho phép gửi file 10GB mà không sập tiệm?

> *"Slack giới hạn file 10GB vì Slack phải trả tiền lưu trữ cho mỗi file đó. TeraChat không giới hạn — vì TeraChat không lưu trữ file của bạn."*

- ☁️🗄️ **Zero Storage Cost Model:** File 10GB của doanh nghiệp được mã hóa từng chunk 2MB và đẩy thẳng lên **AWS S3 / MinIO riêng của doanh nghiệp** (BYOS — Bring Your Own Storage). TeraChat VPS chỉ relay metadata Stub (< 512 bytes) và Merkle Root Hash — không một byte nào của video 10GB chạm vào hạ tầng Terachat.
- 📱💻🖥️ **Streaming Encryption = Chi phí Server ~0:** Lõi Rust dùng Streaming AEAD (không Monolithic Encryption) — mã hóa và đẩy từng chunk 2MB. Không cần server buffer toàn bộ plaintext, không cần RAM server > 10GB. CPU overhead trên VPS là 0 cho tác vụ này.
- 📱💻🖥️ **Wi-Fi Direct Local Bypass:** Nếu 2 nhân viên cùng phòng, file 10GB đi P2P qua Wi-Fi Direct tốc độ **~1Gbps** (~80 giây) — không qua Internet, không qua Cloud, băng thông WAN = **0 bytes consumed**. Đây là điểm độc nhất vô nhị không một SaaS competitor nào có thể làm được.
- ☁️ **Pitch to CISO/CTO:** *"Chúng tôi bán giải pháp mã hóa dòng (Streaming Encryption Pipeline). Dữ liệu của bạn ở lại trên hạ tầng của bạn. Chúng tôi tính phí trên số lượng người dùng, không phải trên gigabyte."* — Đây là lập luận chốt hạ với mọi Enterprise có phòng Compliance yêu cầu Data Residency.

- Desktop app mở trong < 500ms không cần Internet.
- Tìm kiếm millisecond (SQLite FTS5) — không gửi query lên Server.
- File lớn qua LAN P2P (~200MB/s) — không tốn băng thông WAN.
- Survival Link: Vẫn hoạt động khi Internet sập hoàn toàn.

### 2.4 TeraChat Elite — "Sovereign Confidential Compute" (VPS Enclave Tier)

> **Chiến lược Pivot:** Từ "Zero Bandwidth Cost" (thuần Client-side) → nâng cấp thành **"Sovereign Confidential Compute"**: Doanh nghiệp đóng góp VPS của mình làm Compute Node, TeraChat biến VPS đó thành cỗ máy xử lý nghiệp vụ bảo mật mà IT Admin nội bộ không thể đọc được.

#### Vấn đề thực tế của Mobile-only Architecture

- **Pin sụt + Máy nóng = App bị gỡ:** Chạy WASM sandbox `.tapp` nặng + SQLite WAL I/O + AI NLP cùng lúc trên điện thoại CEO → Battery drain rõ rệt. Trong môi trường Enterprise, "App làm nóng máy" = "App bị gỡ cài đặt" sau 2 tuần, bất kể bảo mật đến đâu.
- **VPS khách hàng đang chạy không tải:** Self-hosted Server chỉ làm nhiệm vụ relay `cold_state.db` là lãng phí tài nguyên × chi phí thuê Cloud tháng.

#### Giải pháp: TEE-Backed Confidential Offloading

```text
📱 Mobile Client                      ☁️ VPS Enclave (Intel SGX/AMD SEV/AWS Nitro)
     │                                         │
     ├─ Remote Attestation (DCAP) ────────────▶ Verify CPU Signature
     │  (Kiểm tra VPS chưa bị IT Admin can thiệp)
     │                                         │
     ├─ E2EE Channel TLS → đâm xuyên vào Enclave ──▶ Receive Ciphertext
     │                                         │
     │                                    Decrypt trong CPU (OS không thể đọc)
     │                                    Chạy .tapp Heavyweight / Local LLM
     │                                    Re-encrypt kết quả
     │                                    ZeroizeOnDrop → clear RAM
     │                                         │
     ◀──────────── Return Encrypted Result ────┘
     Decrypt locally, hiển thị cho user
```

- ☁️ **Client-to-Enclave E2EE:** Ngoài E2EE Client-to-Client thông thường, gói Elite thêm chuẩn mã hóa **Client-to-Enclave**: TLS session được thiết lập trực tiếp với vùng Enclave CPU — OS của VPS host (kể cả IT Admin) không thể intercept plaintext. Dữ liệu chỉ decrypted **bên trong SGX/SEV protected memory pages**.
- 📱 **Giảm tải 90% cho Mobile:** Điện thoại chỉ làm UI rendering + end-to-end encryption/decryption. Tất cả tính toán nặng (AI NLP, `.tapp` Heavyweight, Data Mining) offload lên VPS Enclave. Pin không sụt, máy không nóng.
- ☁️ **VPS trở thành Asset:** VPS của khách hàng không còn ngồi chơi — nó xử lý nghiệp vụ AI/`.tapp` của chính doanh nghiệp. ROI rõ ràng từ chi phí Server.

#### Chiến lược Upsell (Up-sell Lever)

| Tier | Giá | `.tapp` | AI | VPS Compute |
|------|-----|---------|-----|------------|
| Standard | $1,000/tháng | Lightweight only | ClawBot API | ❌ |
| **Elite** | **$3,000/tháng** | **Lightweight + Heavyweight** | **Local LLM trong Enclave** | **✅ SGX/SEV** |
| Enterprise Gov | $8,000/tháng | Tất cả + Custom | Air-gapped Sovereign LLM | ✅ Bare-metal HSM |

- 🏆 **Pitch to CTO/CISO:** *"Gói Elite biến VPS của bạn thành một cỗ máy tính toán bảo mật mà chính bạn (CTO) cũng không thể đọc được nội dung — nhưng nhân viên của bạn thì có. Đây là định nghĩa đúng của Data Sovereignty."*
- ☁️ **Revenue Impact:** Up-sell từ Standard ($1K) → Elite ($3K) = 3× ARR per customer. Target 30% Enterprise customers upgrade Elite trong Year 2. Projected ARR boost: **+$540,000** (Year 2, 60 customers Elite).

### 2.5 Compliance-Ready (Gov & Banking)

- ISO 27001, SOC 2 Type II, GDPR Compliant (roadmap).
- USB Token / SmartCard (PKCS#11) cho Gov-grade signing.
- Tamper-proof Audit Log (Merkle Tree) — yêu cầu pháp lý.
- Legal Hold (đóng băng tài khoản điều tra).

### 2.6 AI Risk Governance (Lợi thế Quản trị Rủi ro AI)

**Thách thức của đối thủ:** Slack/Teams tích hợp AI một cách "mù quáng" — doanh nghiệp buộc phải tin tưởng nhà cung cấp AI xử lý dữ liệu khách hàng, dẫn đến e ngại từ khối Enterprise nhạy cảm về tuân thủ.

**Giải pháp TeraChat — Giao quyền làm chủ cho CISO:**

| Tính năng | Đối thủ (Slack/Teams) | TeraChat |
|---|---|---|
| Kiểm soát PII trước khi gửi AI | ❌ Không có | ✅ Local Micro-NER Masking |
| Admin toggle AI Exposure | ❌ All-or-nothing | ✅ OPA 3-Level Dynamic Toggle |
| Audit Log khi AI dùng dữ liệu | ❌ Không có | ✅ Ed25519 Tamper-Proof Log |
| Trách nhiệm pháp lý rò rỉ | Nhà cung cấp | ✅ IT doanh nghiệp tự quyết định |

**Chiến lược Risk Delegation:** Bằng cách đẩy trách nhiệm chấp nhận rủi ro (Risk Acceptance) về phía bộ phận IT của khách hàng thông qua OPA Toggle, TeraChat:

- Tự bảo vệ khỏi cáo buộc pháp lý nếu API bên thứ 3 bị rò rỉ.
- Cung cấp công cụ Audit Log sắc bén nhất cho doanh nghiệp chứng minh compliance.
- Giải quyết vấn đề Shadow IT: hệ thống linh hoạt ngăn người dùng "đi cửa sau" dùng AI ngoài.

### 2.7 Multi-Sig HR Recovery

- ☁️ Giảm thiểu Single Point of Failure (SPOF) truyền thống của phòng IT. Dành riêng cho khối Tài chính/Chính phủ, nơi việc sinh lại khóa Master bắt buộc phải có sự đồng thuận từ thiết chế nhân sự (HR) thay vì trao mạo hiểm toàn quyền cho 1 SysAdmin.

### 2.8 Hardware Upselling Strategy (Kinh doanh Hạ tầng)

- ☁️ **Đòn bẩy Server-Side Aggregation cho GTM:** Sử dụng tính năng "Server-Side Aggregation cho Cộng tác Nhóm lớn" như một đòn bẩy để tư vấn doanh nghiệp nâng cấp gói phần cứng VPS — từ VPS 4-Core lên Bare-metal Server 16-Core — nhằm chịu tải được luồng dữ liệu cộng tác nội bộ dày đặc, tăng doanh thu từ dịch vụ triển khai hạ tầng.

### 2.9 Adaptive Spatial Connectivity — Lợi thế Cạnh tranh Chiến thuật

- 📱💻🖥️ **GTM Pitch:** *"TeraChat không chỉ là phần mềm chat — mà là **Radar Giao tiếp Chiến thuật** (Tactical Communication Radar)."* Khả năng tự động hạ cấp tính năng (**Graceful Degradation**) từ Full-HD Streaming (Online) xuống Voice/File Tactical (Wi-Fi Direct) xuống Text-only Survival BLE biến TeraChat thành công cụ vô giá cho:
  - 🗄️ **Quân sự & Chính phủ:** Môi trường tác chiến nơi mạng rớt từ Vệ tinh → Bộ đàm cự ly gần chỉ trong tíc tắc.
  - ☁️ **Khai khoáng & Hàng hải:** Tàu biển, mỏ ngầm — nơi Internet Vệ tinh (VSAT) chập chờn, cần fallback nội bộ đảm bảo mệnh lệnh đến đúng chỗ.
  - 📱💻 **Doanh nghiệp Phân tán:** Nhà máy, khu công nghiệp, tòa nhà với nhiều tầng hầm hoặc vùng phủ sóng yếu.
- 💻🖥️ **Lợi thế kỹ thuật không thể copy nhanh:** Adaptive Payload Gating yêu cầu Lõi Rust xử lý RSSI/RTT real-time tại tầng Kernel — không thể implement trên kiến trúc SaaS thuần cloud của Slack/Teams trong vòng 12-18 tháng.
- ☁️📱💻 **Key Selling Point — SLA 99.999% trong điều kiện mạng khắc nghiệt:** *"TeraChat cam kết uptime **SLA 99.999%** (<5.26 phút downtime/năm) ngay cả trong môi trường mạng di động cực kỳ bất ổn nhờ hai công nghệ độc quyền:*
  - **(1) QUIC 0-RTT:** Khi kết nối bị gián đoạn và tái kết nối (chuyển 4G→Wi-Fi, vào hầm, tín hiệu yếu), TeraChat phục hồi kết nối trong **0ms Handshake** thay vì 200–800ms của TCP/TLS truyền thống — người dùng không cảm nhận được gián đoạn.*
  - **(2) Anti-Entropy Merkle Sync:** Ngay cả sau khi bị cô lập mạng hàng giờ, các node tự động đối chiếu `BLAKE3 Root_Hash` và hội tụ trạng thái chính xác trong **<100ms** khi mạng phục hồi — không mất tin nhắn, không cần manual refresh."*
  > **Sales Differentiator:** Slack/Teams mất 5–30 giây để tái kết nối sau network switch. TeraChat: 0ms. Đây là lợi thế quyết định trong môi trường Tactical/Field/Military.

## 3. Go-to-Market Strategy & Operations

### 3.6 UAB — Chiến lược "Aggregator của các Agent"

> *"Chúng tôi không bán AI. Chúng tôi bán cái hộp an toàn để AI của bạn hoạt động trong đó."*

- ☁️ **Định vị Unique:** Bằng cách không giới hạn AI, TeraChat là **giao diện duy nhất (Unified Interface)** cho mọi Agentic Workflow. Khách hàng mua TeraChat Core License → tự do cài `.tapp` OpenClaw/ClaudeBot/Gemini mà **không trả token fee cho TeraChat**.
- ☁️ **Zero Bandwidth Cost cho AI Traffic:** Khi nhân viên gọi API tới ClawBot, Egress Traffic đi thẳng từ mạng của nhân viên (hoặc VPN doanh nghiệp) đến Server của AI Agent. TeraChat VPS = 0 Egress cost cho AI calls. Biên lợi nhuận gộp giữ trên 90%.
- 📱💻🖥️ **Moat kỹ thuật — OAP Standard Lock-in:** Khi một doanh nghiệp đã train AI Agent theo chuẩn OAP (Open-Agent Protocol) của TeraChat, chi phí chuyển đổi sang nền tảng khác tăng đột biến. Đây là **Network Effect + Data Lock-in** mà không vi phạm quyền sở hữu dữ liệu của khách hàng.

### 3.7 Chiến lược "Unchained AI" — Full-Context Passthrough & Liability Shift

> *"Chúng tôi không bán AI. Chúng tôi bán Không gian An toàn. Và nếu bạn muốn tháo xích — bạn có thể ký tên vào đó."*

- ☁️ **Định vị "Unchained AI":** Khác với các nền tảng tự xây AI ngầm định giới hạn năng lực (OpenAI moderated API, Azure Content Filter), TeraChat bán **Secure Sandbox với quyền tùy chỉnh mức bảo vệ**. Nếu CISO khách hàng chủ động ký `Security Manifest Consent` (biometric + typed `"I_ACCEPT_LIABILITY"`), họ có thể "cởi trói" hoàn toàn cho OpenClaw: 100% raw context, 0% redaction.
- ☁️ **Liability Shift (Chuyển giao Trách nhiệm pháp lý):** Cơ chế FCP tạo ra một `FCP_Consent_Record` bất biến, ký số bằng `Admin_Ed25519_Key`, không thể xóa khỏi Tamper-Proof Audit Chain. Nếu dữ liệu bị rò rỉ từ máy chủ OpenClaw, TeraChat có bằng chứng Non-Repudiation chứng minh: *"Admin của quý tổ chức đã ký consent ngày [X], chúng tôi chỉ tuân theo chỉ thị."* Trách nhiệm pháp lý chuyển 100% sang phía khách hàng.
- 💻🖥️ **Competitive Moat — Execution Integrity Boundary:** Điều mà đối thủ không làm được: dù FCP bypass toàn bộ Egress filter, **Ingress (AI response về lại giao diện) vẫn đi qua SASB**. OpenClaw có IQ 100% nhưng không thể inject XSS/malicious code. Đây là điểm khác biệt kỹ thuật không thể copy nhanh: Execution Integrity tách rời khỏi Data Confidentiality.
- 📱💻🖥️ **GTM Segment: Enterprise với "Chủ quyền Dữ liệu AI":** Phân khúc khách hàng mục tiêu cho FCP: Công ty Luật (cần AI đọc hồ sơ mật), Bệnh viện (cần AI đọc medical record không được filter), Military/Intelligence (cần AI context đầy đủ cho tình huống tác chiến). Đây là phân khúc $500K-$5M ARR mà Slack/Teams không thể phục vụ vì kiến trúc Cloud-first của họ không cho phép Client-Side routing.

### 3.1 GTM Phases

**Phase 1: Vertical Focus (F&B + Gov)**

- Target 2 verticals rõ ràng: Nhà hàng/Cafe chuỗi (dễ bán, Kiosk Mode + Magic Logger) và Cơ quan hành chính (Smart Approval + ký số).
- Sản phẩm demo dễ WOW: chụp ảnh bill → tự động nhập kho.

**Phase 2: Enterprise Expansion**

- Banking → Fintech Bridge (Smart Approval, Blind Payout).
- Manufacturing → Survival Link (khi cáp bị cắt nhà máy vẫn hoạt động).
- Multi-national Corp → Federated Private Clusters (data sovereignty liên quốc gia).

**Phase 3: Ecosystem & Marketplace**

- Mở Marketplace cho ISV (Independent Software Vendors) viết `.tapp` Mini-Apps.
- Revenue share model với developers.

### 3.2 Sales Strategy: Zone 2 as Enterprise Upsell Hook

> [!IMPORTANT]
> **Nút thắt bán hàng cốt lõi:** Nếu doanh nghiệp không enforce Vùng 2 cho Sale/CSKH → dữ liệu khách hàng sẽ mất theo nhân viên nghỉ việc → doanh nghiệp **sẽ không dám mua gói Enterprise**.

**Kịch bản bán hàng:**

1. Demo: Sale dùng Zalo chat với khách → nghỉ việc → mang số Zalo đi → công ty mất khách.
2. Solution: TeraChat Vùng 2 → Mọi cuộc hội thoại với khách đều thuộc về công ty, có Audit Log.
3. Close: IT Admin deploy On-Premise → Dữ liệu không bao giờ rời văn phòng.

**Reseller Mode (MSP Channel):**

- Target: Công ty IT service, hệ thống tích hợp (SI), hãng phần mềm khu vực.
- Model: MSP mua License bulk → cài đặt và bảo trì cho khách hàng cuối (nhà hàng, bán lẻ).
- TeraChat cung cấp: Công cụ triển khai 1 dòng lệnh, tài liệu kỹ thuật, đào tạo chứng chỉ.

### 3.3 Enterprise Onboarding (Fast Deploy)

**On-Premise (CLI Install & Supply Chain Integrity):**

```bash
# 1. Download Signed Script & Manifest
curl -sL https://install.terachat.com/install.sh -o /tmp/install.sh
curl -sL https://install.terachat.com/manifest.sig -o /tmp/manifest.sig

# 2. GPG/Cosign Verify & No-Execute Guard & Install
cosign verify-blob --key terachat.pub --signature /tmp/manifest.sig /tmp/install.sh && \
sha256sum -c /tmp/manifest.sig --ignore-missing && \
sudo bash /tmp/install.sh --token=[License_Key]
```

- Ngăn chặn tuyệt đối mã độc (Supply Chain) bằng đối soát mã băm SHA-256 từ Manifest chính thức.
- Thực thi giới nghiêm `chmod -x` (No-Execute) trên thư mục `/tmp` trước khi cấp quyền `sudo`.
- Máy tính biến thành Private Node trong vài phút. Không cần IT chuyên sâu.

**Cloud Hybrid:** Admin nhập IP + SSH Key VPS → TeraChat tự SSH vào → cài Docker/K8s → bàn giao Admin Console.

### 3.4 Chốt đơn & Giữ khách

**Hợp đồng:** 1-3 năm, trả trước. Discount 15–20% cho hợp đồng 3 năm.

**Giữ khách bằng dữ liệu:** Dữ liệu (chat history, CRM, audit log) nằm trong Private Cluster của doanh nghiệp. Chuyển sang đối thủ = mất continuity toàn bộ lịch sử.

---

### 3.5 Gói Upsell (Bán chéo) "Enterprise Survival Kit"

- **Biến điểm yếu thành cơ hội kinh doanh:** Đóng gói bán kèm giải pháp phần cứng. Khách hàng mua License TeraChat sẽ được chào mời mua thêm gói phần cứng cứu hộ (YubiKey chuẩn FIDO2 do TeraChat phân phối) định tuyến riêng cho C-Level với giá Premium, gia tăng biên lợi nhuận.
- **Enterprise Survival Kit:** Bán chéo combo 1 YubiKey FIDO2 Type-C + 1 NFC Smart Ring bọc Titan.
  - **Thông điệp GTM (Go-to-Market):** "CEO của bạn có thể mất mọi hành lý, ở vùng không có Internet, nhưng không bao giờ mất quyền kiểm soát dữ liệu công ty."
  - Định giá gói phần cứng này ở mức Premium ($500 - $1,000/set) dành riêng cho C-Level, vì nó giải quyết nỗi sợ hãi cốt lõi của họ.

## 4. Licensing & IP Strategy (Open-Core)

### 4.1 Vấn đề Cần Giải quyết

| Chiến lược | Rủi ro |
|---|---|
| **Mã nguồn Đóng** (Zalo, Teams) | Enterprise (Gov/Bank) không thể tự kiểm chứng backdoor. Đòi hỏi chi phí Audit cao. Mất deal. |
| **Mã nguồn Mở hoàn toàn** (Matrix, Signal) | Đối thủ lớn "hút máu" — dùng miễn phí để cạnh tranh trực tiếp mà không đóng góp lại. |
| **Open-Core (TeraChat)** | ✅ Cân bằng: Mở đủ để doanh nghiệp tin tưởng. Đóng đủ để bảo vệ doanh thu. |

### 4.2 Phân tách Open-Core

**PHẦN BẮT BUỘC MỞ — "Phòng khách" (chứng minh không backdoor):**

| Component | Lý do mở |
|---|---|
| **Core Cryptography (Rust Core)** | E2EE, hàm băm, `Company_Key`, CRDT offline — chứng minh không có backdoor. Gov/Bank tự compile kiểm chứng. |
| **Client Apps** (Desktop — Win/macOS/Linux) | Ứng dụng người dùng — chứng minh không thu thập telemetry ngầm. |
| **Federation Protocol** (P2P/LAN P2P) | Giao thức truyền tải — chứng minh không route dữ liệu qua server trái phép. |

**PHẦN BẮT BUỘC ĐÓNG — "Két sắt" (bảo vệ bí mật thương mại):**

> **Nghịch lý Obfuscation:** Làm rối (Obfuscation) toàn bộ ứng dụng gây lãng phí tài nguyên và phá vỡ tính minh bạch của Enterprise Security. Do đó, kỹ thuật Obfuscation (O-LLVM, Bogus Flow) **chỉ giới hạn nghiêm ngặt** ở các module Két sắt dưới đây, bảo toàn sự trong suốt cho Core Rust.

| Component | Lý do đóng |
|---|---|
| **Enterprise Admin Console** | Giá trị cốt lõi để thu tiền: OPA Policy, Vùng 2, LDAP/Azure AD. **Được phép apply Obfuscation/Minification**. |
| **License Manager & Billing** | Kiểm tra License Key, đếm Seat. **Bắt buộc áp dụng Obfuscation chuyên sâu** chống crack. |
| **AI Modules** (Magic Logger / RAG Context) | Bảo vệ thuật toán AI độc quyền. |
| **Deployment Scripts** (K8s/Docker HA) | Kịch bản auto-scale HA TURN Cluster. |

### 4.3 License Strategy ("Trói chân" đối thủ)

**AGPLv3 — Cho Core Cryptography & Federation:**

- Bất kỳ công ty nào dùng mã nguồn TeraChat để làm **Cloud SaaS** thương mại → **BẮT BUỘC mở ngược toàn bộ mã nguồn của họ**.
- Ngăn chặn triệt để việc đối thủ thương mại "hút máu" Core Engine miễn phí.

**BSL (Business Source License) — Cho một số thành phần khác:**

- Source-Available: có thể tham khảo, dùng miễn phí cho cá nhân.
- **CẤM** các tổ chức thương mại cạnh tranh trực tiếp trong 3–4 năm đầu.
- Sau thời gian đó → tự chuyển thành Open Source hoàn toàn.

> **Tóm lại:** Chúng ta mở cửa phòng khách (Client, Thuật toán mã hóa) để khách hàng thấy nhà sạch và an toàn. Nhưng khóa chặt phòng bếp và két sắt (Admin Console, AI, Tích hợp doanh nghiệp).

### 4.4 Tuân thủ Chính sách Apple Review (W^X & Static Crypto)

- **Khai báo Minh bạch:** Trong tài liệu nộp cho Apple Review, TeraChat khai báo rõ `terachat-nse-core` chỉ là một thư viện mật mã thuần túy (Static Crypto Library). Tiến trình chạy ngầm (NSE) tuyệt đối không tải bất kỳ file `.tapp` nào qua mạng.
- **W^X Lockdown:** Không sử dụng JIT Compiler. Cấu hình WASM3 dưới dạng Pure AOT (Ahead-of-Time). Mọi plugin AI/WASM chỉ được thực thi ở Foreground (Main App) để vượt ải kiểm duyệt khắt khe của Apple về rủi ro Remote Code Execution (RCE) qua Push Notification.
- 📱 **Rủi ro App Store Review Rule 2.5.2 (Web Marketplace & .tapp):**
  - > **Rủi ro:** Các ứng dụng Web Marketplace tải `.tapp` (file WASM) từ mạng có thể vi phạm Rule 2.5.2 *"Apps must not download, install, or execute code which introduces or changes features or functionality of the app"*.
  - > **Biện pháp Giảm thiểu (Mitigation):** Khẳng định rõ trong Apple Enterprise entitlement submission: `.tapp` **KHÔNG** thay đổi UI/Logic chính của TeraChat. Mỗi `.tapp` chỉ chạy trong môi trường Sandbox V8/WASM gọi là "DLP Processor", giới hạn hoàn toàn trong xử lý text offline (NER/PII Scan). Không có FFI call ra ngoài Sandbox, không có quyền Network, không có quyền UI rendering. Model được khai báo tường minh là "Data Processor Plugin", tương tự việc tải font hoặc spell-check dictionary — không phải code thay đổi app.
  - > **Chiến lược nộp Enterprise:** Ưu tiên phân phối qua Apple MDM/Enterprise Distribution (không qua App Store Consumer) để tránh hoàn toàn Rule 2.5.2 cho môi trường B2B. Consumer App Store version sẽ có `.tapp` marketplace bị disable, chỉ bundle sẵn các plugin đã được Apple review từ trước.

- 📱☁️ **Dual-Registry Distribution Model (iOS vs Android/Desktop):**
  - > **Vấn đề cốt lõi:** Model phân phối `.tapp` hiện tại ("tải WASM từ `marketplace.terachat.io`") hoạt động hoàn hảo trên Android và Desktop nhưng vi phạm cứng Rule 2.5.2 trên iOS — Apple coi đây là Remote Code Execution.
  - 📱 **iOS Registry — AOT Feature Flag via OPA Policy:** Portal `marketplace.terachat.io` đối với client iOS **không bao giờ trả về file `.tapp` (WASM binary)**. Thay vào đó, chỉ trả về **OPA Policy JSON** chứa Feature Flag — ví dụ: `{"plugin_id": "smart_ocr", "enabled": true}`. Lõi Rust iOS nhận flag này và gọi vào **AOT `.dylib` tương ứng đã bundled sẵn trong `.ipa`** từ lúc build. Tuyệt đối không có WASM byte nào được tải về qua mạng trên iOS.
  - 💻🖥️📱 **Android/Desktop Registry — Dynamic WASM Download:** Giữ nguyên model hiện tại. Marketplace trả về file `.tapp` (WASM) qua HTTPS. Lõi Rust Android/Desktop chạy Wasmtime JIT hoặc Wasm3 Interpreter tùy platform. Sandbox vẫn áp dụng đầy đủ.
  - ☁️ **Registry Routing Logic (VPS-side):** Backend `marketplace.terachat.io` đọc header `X-TeraChat-Platform: ios | android | desktop` trong API request và tự động route: iOS → Policy JSON endpoint, non-iOS → WASM binary endpoint. Không có client-side logic phức tạp.

---

## 5. Anti-Fragmentation & Forced Upgrade Strategy

> **"Sự phân mảnh phiên bản (Version Fragmentation) là căn bệnh kinh điển của phần mềm On-Premise. Chúng ta dùng Kỷ luật Hệ thống và Nút thắt Kiến trúc để điều phối dòng tiền SLA."**

### 5.1 Nút thắt Thương mại: Subscription License (không bán Perpetual)

- **Admin Console** cần **License Key** để hoạt động. License có thời hạn (1 năm).
- Khi ngừng gia hạn → Admin Console **khóa tính năng** (không thêm được user, Module AI ngừng, Azure AD Sync lỗi). Hệ thống **không chết** ngay (tránh rủi ro pháp lý).
- Kết quả: Doanh nghiệp bắt buộc phải gia hạn License → tự động nhận bản nâng cấp mới.

### 5.2 Nút thắt Bảo mật: Security Deprecation

Với Gov/Banking, tuân thủ bảo mật là sinh tử:

- Mỗi khi ra phiên bản mới → công bố kèm **CVE / Security Patch notes**. VD: *"Bản 2.0 vá lỗ hổng bộ nhớ CRDT. Các bản 1.x sẽ End-of-Life sau 90 ngày."*
- IT Admin thấy CVE → **bắt buộc tự tải bản mới** để tránh vi phạm compliance nội bộ.

### 5.3 Nút thắt Giao thức: Protocol Versioning

**Đòn bẩy kỹ thuật mạnh nhất:**

- Chi nhánh A (v2.0) giao tiếp Vùng 2 với Chi nhánh B (v1.0) → Federation Bridge báo lỗi `Incompatible Protocol Version`.
- Kết quả: Muốn các chi nhánh chat được với nhau → **IT Admin buộc phải nâng cấp đồng bộ tất cả lên version mới**.
- Thuật toán mã hóa và định dạng payload `Company_Key` **không tương thích ngược**.

### 5.4 Giải pháp Kỹ thuật: Local OTA Update (Nhanh, An toàn)

Cập nhật không tải từ Server của TeraChat — tải từ **VPS nội bộ của khách hàng**:

1. IT Admin tải file Update về cụm VPS Private (kể cả Air-Gapped).
2. Admin Console → Bấm "Thả bản cập nhật".
3. VPS bắn lệnh ép nâng cấp cho toàn bộ nhân viên qua **LAN** (tốc độ cực cao).
4. Nhân viên từ chối nhấn nâng cấp → Client **chối kết nối vào Cluster nội bộ**.

> **Tóm lại chiến lược Forced Upgrade:** Chúng ta giao quyền kiểm soát mã nguồn và dữ liệu vật lý để lấy niềm tin. Nhưng nắm giữ **License Key, Chuẩn giao thức, và CVE** để điều phối nhịp đập cập nhật và dòng tiền SLA.

---

## 6. Funding Allocation

> **Tiền đầu tư (nếu có từ VC) tuyệt đối không đốt vào thuê Server Cloud hay chạy quảng cáo.**

| Hạng mục | Tỷ lệ | Chi tiết |
|---|---|---|
| **Audit & Chứng chỉ Bảo mật** | **20%** | Thuê Cure53 (hoặc tương đương) Pen-test E2EE + CRDT. Lấy chứng chỉ ISO 27001, SOC 2 Type II, GDPR Compliance. Đây là điều kiện tiên quyết để close deal Gov/Banking. |
| **Mở rộng R&D Core** | **40%** | Tuyển chuyên gia Rust/C++ tối ưu CRDT Sync và thuật toán mã hóa. Kiến trúc sư hệ thống phân tán. Multi-platform native quality (Win/macOS/Linux/iOS/Android). |
| **Mạng lưới Đối tác & Reseller** | **25%** | Đào tạo và cấp chứng chỉ cho công ty IT nội địa (MSP) đi bán và cài đặt TeraChat cho chuỗi nhà hàng/bán lẻ. Sự kiện B2B, case study thực tế. |
| **Quỹ Dự phòng** | **15%** | Đảm bảo runway tối thiểu **18–24 tháng** trong điều kiện kinh tế xấu nhất. |

### Rationale

- **Audit trước** → Không có chứng chỉ → Gov/Bank không mua → doanh thu không đến.
- **R&D Core** → Chất lượng phần mềm → Ít bug → Ít SLA penalty → Margin cao hơn.
- **Reseller network** → Tiếp cận hàng nghìn SME mà không cần tuyển Sales trực tiếp.
- **Không đốt Server** → Biên lợi nhuận bảo toàn → Runway dài hơn.

---

*Tài liệu này chỉ chứa chiến lược kinh doanh, doanh thu, licensing và GTM. Xem `PRD.md` cho product features & user flows. Xem `TechSpec.md` cho technical implementation.*

---

## 7. Chính sách Thu hồi Tài nguyên Định danh (Deterministic Resource Reclamation SLA)

> **Vị trí:** Hề thống Generational Handle &amp; Seqlock không chỉ là kỹ thuật bảo mật — chúng là căn cứ pháp lý để TeraChat cam kết Zero Bandwidth Cost trên Marketplace.

- ☁️ **Generational Handle SLA Binding:** Một hợp đồng Perpetual License chỉ được ký sau khi Publisher cam kết tuân ủ chuẩn Generational Handle Valđatịn đối với mọi API call ra ngoài WASM Sandbox — trách nhiệm rò rỉ bộ nhớ chuyển sang Publisher.
- 💻 **Memory Quota Audit cho `.tapp` Marketplace:** Tại Admin Console, CISO có thể tra cứu tâm Resident Memory hiện tại của từng `.tapp` đang chạy kèm số lần GC Cycle và Total Reclaimed Bytes; không cần công cụ thứ 3.
- 🗄️ **Zero Bandwidth Cost (Kiểm soát Vòng đời RAM):** Chính sách `munmap()` chủ động kết hợp Generational Slot Reclaim loại bỏ hoàn toàn cấu trúc GC-dựa — CPU footprint cho Enterprise Tier ≤ 3% so với model WebSocket-over-Bridge truyền thống.

## 8. Phân mảnh Phiên bản (Protocol Versioning Binding & Forced Upgrade)

- ☁️ **`Max_Protocol_Version` trong License Token:** Mỗi License Token mã hóa thời gian của phiên bản Giao thức tối đa (`Max_Protocol_Version`) đang được hoạt động. Hết date License = hết quyền sử dụng Giao thức mới nhất.
- 🗄️ **MLS Epoch Versioning (Federation Bridge ngắt kết nối nếu không khớp Epoch v4):** Federation Bridge tự động ngắt kết nối Cluster nào còn chạy Epoch v3 trong khi nếu phần còn lại đã lên v4 — tạo áp lực nâng cấp đồng bộ toàn cụm.
- 💻 **Protocol Isolation (Barrier Cô lập Giao thức):** Thiết lập rào cản cô lập giao thức ngay tại tầng Lõi Rust; bất kỳ Client nào cưỡng ép giữ phiên bản cũ sẽ bị Quorum Peers chủ động loại khỏi DAG Sync.

## 9. Mô hình Kinh doanh Cách ly Mạng (Air-Gapped Revenue Model)

> **Khách hàng mục tiêu:** Quốc phòng, Tình báo, Hạ tầng Trọng yếu (CNTT) không thể tồn tại Online.

- 🗄️ **Cấu hình Vật lý HSM Sub-CA:** Từ ngữ hoà nghiễm ngoặt cung cấp Hàng mục phần cứng HSM thiết lập tại vật lý hầm bảo mật của khách hàng; TeraChat không từng có cấu trúc Remote Access vào Namespace HSM.
- ☁️ **Air-Gapped License Token Model:** License Token phát hành một lần qua USB mãt mã; không có online telemetry hay "phone home" callback — phù hợp cho môi trường SCIF/Viện NAN giãi phiết.
- 🗄️ **SLA Insurance cho Hạ tầng Trọng yếu:** Tích hợp chính sách SLA 99.999% Uptime kèm bảo hiểm theo hợp đồng cho các Phấn tại khím đoạn — phân khúc giá trị cao nhất.

## 10. Zero-Trust SLA cho Quân sự và Tình báo

> **Định vị sản phẩm:** Kiến trúc E2EE Phân tán (Client-side Key, Zero-Centralized C2) + Byzantine Fault Tolerance (BFT) Client Quorum định vị TeraChat như một Survival Communication Platform cho Hạ tầng Quốc gia.

- 🗄️ **Kiến trúc E2EE Phân tán (Client-side Key):** Không có điểm lưu trữ khóa trung tâm; mọi `Device_Key` nằm trong Secure Enclave/StrongBox của từng thiết bị — đáp ứng định nghĩa "Zero Centralized C2" của Pentagon.
- ☁️ **Phát hiện phỪ biết thông tin tich hợp SLA:** SLA cam kết cơ chế tự động chuyển sang Mesh Mode < 2s khi phát hiện dắn các hiệu ứng phỮong toả (Eclipse Attack Indicators).
- 💻 **Byzantine Fault Tolerance (BFT) Client Quorum:** Hệ thống vẫn hoạt động chính xác kể cả khi $f$ Client bị nâm giữa Quorum (Thức theo bất bình đẳng $N > 3f$) — không có thực thể đơn lẻ nào giả mạo toàn bộ sự thực của mạng lưới.
