# TeraChat V0.2.1 — Business Plan & Go-to-Market Strategy

> **Document Owner:** CEO / Co-founders / Business Team
> **Audience:** Investors (VC), Executives, Sales, Business Development
> **Scope:** Business model, revenue, competitive advantage, GTM strategy, licensing, and funding. For product features see `PRD.md`. For technical implementation see `TechSpec.md`.

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

**A. Phí cấp phép theo người dùng (Per-Seat License — B2B Subscription)**

- Nguồn thu **chính và lớn nhất**.
- Thu phí Subscription theo năm dựa trên số lượng nhân sự.
- Ví dụ pricing: **$5/user/tháng** (trả trước hàng năm).
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

### 2.3 "Zero Bandwidth Cost" Business Model

Biên lợi nhuận gộp > 90% cho phép:

- Định giá linh hoạt để cạnh tranh với Slack/Teams.
- Đầu tư nhiều hơn vào R&D mà không cần đốt tiền Server.
- Mở rộng sang thị trường mới với rủi ro thấp.

### 2.4 Local-First Performance

- Desktop app mở trong < 500ms không cần Internet.
- Tìm kiếm millisecond (SQLite FTS5) — không gửi query lên Server.
- File lớn qua LAN P2P (~200MB/s) — không tốn băng thông WAN.
- Survival Link: Vẫn hoạt động khi Internet sập hoàn toàn.

### 2.5 Compliance-Ready (Gov & Banking)

- ISO 27001, SOC 2 Type II, GDPR Compliant (roadmap).
- USB Token / SmartCard (PKCS#11) cho Gov-grade signing.
- Tamper-proof Audit Log (Merkle Tree) — yêu cầu pháp lý.
- Legal Hold (đóng băng tài khoản điều tra).

---

## 3. Go-to-Market Strategy & Operations

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

**On-Premise (1 lệnh):**

```bash
curl -sL install.terachat.com | sudo bash --token=[License_Key]
```

Máy tính biến thành Private Node trong vài phút. Không cần IT chuyên sâu.

**Cloud Hybrid:** Admin nhập IP + SSH Key VPS → TeraChat tự SSH vào → cài Docker/K8s → bàn giao Admin Console.

### 3.4 Chốt đơn & Giữ khách

**Hợp đồng:** 1-3 năm, trả trước. Discount 15–20% cho hợp đồng 3 năm.

**Giữ khách bằng dữ liệu:** Dữ liệu (chat history, CRM, audit log) nằm trong Private Cluster của doanh nghiệp. Chuyển sang đối thủ = mất continuity toàn bộ lịch sử.

---

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

| Component | Lý do đóng |
|---|---|
| **Enterprise Admin Console** | Giá trị cốt lõi để thu tiền: OPA Policy, Vùng 2, LDAP/Azure AD, quản trị phân quyền. |
| **License Manager & Billing** | Kiểm tra License Key, đếm Seat, giới hạn tính năng theo tier. |
| **AI Modules** (Magic Logger / RAG Context) | Bảo vệ thuật toán và lời hứa *không dùng dữ liệu khách hàng để train model*. |
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
