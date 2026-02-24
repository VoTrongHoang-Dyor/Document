# TeraChat V0.2.1 — Product Requirements Document (PRD)

> **Document Owner:** Product Manager / CEO
> **Audience:** Product, Design, QA, Business Stakeholders
> **Scope:** User-facing features, workflows, UX philosophy, access model, and product roadmap. For implementation details see `TechSpec.md`. For business strategy see `BusinessPlan.md`.

---

## TABLE OF CONTENTS

1. [Product Vision & Scope](#1-product-vision--scope)
2. [User Roles & Access Model](#2-user-roles--access-model)
3. [Core Workflows & Features](#3-core-workflows--features)
4. [UI/UX Philosophy & Constraints](#4-uiux-philosophy--constraints)
5. [Mobile Product](#5-mobile-product)
6. [Ecosystem Integrations (User Perspective)](#6-ecosystem-integrations-user-perspective)
7. [Product Roadmap](#7-product-roadmap)

---

## 1. Product Vision & Scope

### 1.1 Product Vision

> **"TeraChat là Hệ điều hành Công việc (Operating System for Work) cho Enterprise và Chính phủ."**

TeraChat **không phải** ứng dụng nhắn tin giải trí. Đây là **công cụ lao động** được thiết kế để giải quyết 4 bài toán khắt khe của tổ chức quy mô lớn:

| Bài toán | Giải pháp TeraChat |
|---|---|
| **Chủ quyền dữ liệu (Data Sovereignty)** | Mỗi chi nhánh tự host Private Cluster riêng. Dữ liệu không bao giờ rời khỏi ranh giới vật lý. |
| **Độ trễ thấp (Low Latency)** | Nhân viên trong cùng văn phòng kết nối trực tiếp vào Cluster nội bộ — không đi vòng qua Data Center trung tâm. |
| **Sức chống chịu thảm họa** | Khi Internet sập, chi nhánh vẫn hoạt động độc lập. Survival Link (BLE/Wi-Fi Mesh) duy trì liên lạc nội bộ. |
| **Bảo mật Zero-Trust** | Mọi dữ liệu mã hóa E2EE ngay tại thiết bị trước khi truyền. Server không bao giờ thấy nội dung plaintext. |

### 1.2 Target Customers

| Segment | Profile | Key Pain Point |
|---|---|---|
| **Chính phủ / Cơ quan nhà nước** | Văn phòng, Bộ, Cơ quan hành chính | Tuân thủ dữ liệu nội địa, ký số công văn pháp lý |
| **Ngân hàng / Tài chính** | Bank, Fintech, Bảo hiểm | Zero-Trust, compliance (SOC 2, ISO 27001), Smart Approval |
| **Doanh nghiệp lớn (Large Enterprise)** | Tập đoàn đa quốc gia, Manufaturing | Liên lạc liên chi nhánh, bảo mật dữ liệu chiến lược |
| **F&B / Bán lẻ (SME)** | Nhà hàng, chuỗi cafe, shop thời trang | Shared Device (Kiosk), Magic Logger (POS), không cần IT pro |

### 1.3 Product Positioning

- **Bán theo mô hình B2B Enterprise** — không có Consumer/Personal mode.
- **Data Sovereignty first** — TeraChat không lưu dữ liệu của khách hàng trên server của mình.
- **Desktop-First** — Desktop là trung tâm điều khiển. Mobile là trạm phụ (tier-2).

---

## 2. User Roles & Access Model

### 2.1 Ba Vùng Hạ tầng (Zone Architecture)

Hệ thống phân chia người dùng và ngữ cảnh giao tiếp vào 3 vùng hạ tầng rõ ràng:

| Vùng | Tên | Đối tượng sử dụng | Đặc điểm |
|---|---|---|---|
| **Vùng 1** | "Pháo Đài Số" (Intranet) | Nhân viên nội bộ | Dữ liệu không bao giờ rời Private Cluster. Chỉ `Org_ID` hợp lệ mới vào được. |
| **Vùng 2** | "Cổng Hải Quan" (Federation) | Sale, CSKH làm việc với khách ngoài | **Audit Log bắt buộc.** Nhân viên nghỉ việc → mất quyền ngay. Dữ liệu khách ở lại với công ty. |

> [!IMPORTANT]
> **Enterprise Rule:** Sale/CSKH **BẮT BUỘC** dùng Vùng 2 khi chat với khách hàng. Không được dùng kênh cá nhân. Đây là điều kiện then chốt để doanh nghiệp mua gói Enterprise.

### 2.2 Phân quyền theo Vùng

| Tính năng | Vùng 1 (Nội bộ) | Vùng 2 (Đối ngoại) |
|---|---|---|
| Chat mật (E2EE) | ✅ | ✅ (có Audit Log) |
| Smart Approval | ✅ | ❌ |
| Gửi file nội bộ | ✅ | ✅ (có DLP scan) |
| Magic Logger (AI Import) | ✅ | ✅ |
| Gửi file > 1MB | ✅ | ❌ |
| Screen Share | ✅ | ❌ |
| Audio/Video Call | ✅ | ❌ |

### 2.3 User Roles

| Role | Quyền hạn chính |
|---|---|
| **Super Admin / IT Admin** | Quản trị toàn hệ thống. Cấp phép app (Marketplace). Revoke user. WASM Doctor. SCIM sync. |
| **Department Admin** | Quản lý nhóm nội bộ. Cấu hình OPA Policy theo phòng ban. |
| **Director / CFO / CEO** | Ký số chính thức (Smart Approval). Ký ủy quyền (Delegation Certificate). |
| **Manager / Supervisor** | Duyệt file, phê duyệt chi tiêu. Giám sát DLP Quarantine. |
| **Staff (F&B/Kiosk)** | Shared Device (PIN login). Magic Logger POS. |
| **Sale / CSKH** | Bắt buộc Vùng 2. Magic Logger (chốt đơn từ Zalo/Telegram). |
| **Developer (ISV)** | Bot Builder SDK. Viết `.tapp` Mini-App cho Marketplace. |

### 2.4 Onboarding Flow (Self-Sovereign, Non-Custodial)

1. **Admin nhập Email** → Server gửi Invite Link (Signed JWT).
2. **User click Link** → App mở → App tạo Key Pair trong Secure Enclave → Ký xác nhận bằng Private Key.
3. **Server verify** → Bind `Email ↔ Public Key` → User được cấp vào nhóm dựa trên Azure AD/LDAP.
4. **Identity Lock:** Tên hiển thị được khóa theo danh tính doanh nghiệp — user không tự đổi.

**Shared Device Onboarding (F&B/Kiosk):**

- iPad được Register bằng Store Key Pair (định danh chi nhánh).
- Nhân viên đăng nhập bằng **PIN 4-6 số** hoặc **Thẻ từ NFC** → Session tồn tại trong ca làm việc.
- Logout = Ephemeral Session Key bị xóa.

---

## 3. Core Workflows & Features

### 3.1 Smart Approval (Sequential Signing)

**Mô tả:** Luồng phê duyệt tài liệu / chi tiêu tuần tự, mỗi bước yêu cầu xác thực sinh trắc học (FaceID, Windows Hello, USB Token).

**Luồng phê duyệt:**

```
Chuyên viên soạn thảo & ký nháp
        ↓
Trưởng phòng xem xét & ký nháy
        ↓
Giám đốc ký số chính thức (USB Token Gov)
        ↓
Hệ thống Timestamping & Lock Document
```

**User Experience:**

- Chuyên viên soạn đơn → Bấm "Gửi duyệt" → Trưởng phòng nhận notification trong chat.
- Trưởng phòng xem Adaptive Card trong chat → Bấm "DUYỆT" → Windows Hello / FaceID xuất hiện → Xác thực → Ký xong.
- Giám đốc nhận notification → Cắm USB Token → Bấm "Ký số" → Văn bản được lock.
- Chuyên viên nhận notification "Đã được duyệt". Văn bản tự động lưu vào Archive.

**Smart Approval Anti-Fraud:**

- Giao diện phê duyệt hiển thị trong **System Biometric Prompt** (tầng OS) — Malware không thể giả mạo.
- Thông tin giao dịch (số tiền, người nhận, mã đơn) hiển thị rõ ràng **trong chính hộp thoại xác thực**.

**Fintech (Bonus/Payout):**

- `/bonus @employee [amount]` → Blind Fintech Bridge → PayPal Payouts API.
- OAuth Token lưu trong Secure Enclave (không bao giờ plaintext).
- Audit trail write-only cho mọi lệnh duyệt chi.

### 3.2 Magic Logger (Smart Import)

**Concept:** Biến TeraChat thành cổng nhập liệu tự động bằng AI OCR & Regex.

**A. POS Edition (F&B/Retail)**

| Bước | Hành động |
|---|---|
| 1 | Nhân viên chụp ảnh Bill viết tay / Order trên giấy / Màn hình máy POS cũ |
| 2 | AI OCR phát hiện: món ăn, SKU, số lượng → Map vào Inventory System |
| 3 | Tự động tạo phiếu nhập/xuất kho JSON → Nhân viên xem và bấm "Confirm" |
| 4 | Kho tự trừ, CRM cập nhật. **$0** dữ liệu qua TeraChat Central |

**B. Gov Edition (Administrative)**

| Bước | Hành động |
|---|---|
| 1 | Văn thư chụp ảnh công văn giấy / PDF scan |
| 2 | AI trích xuất: Số hiệu, Ngày ban hành, Người ký, Trích yếu |
| 3 | Redact PII (che số điện thoại/địa chỉ riêng tư) |
| 4 | Index vào hệ thống lưu trữ → tự động routing tới người nhận đúng |

**C. Cầu nối Zalo/Telegram/Facebook**

Sale dùng App gốc (Zalo/Telegram/Facebook) chat với khách → **Copy hội thoại hoặc chụp màn hình → Paste vào TeraChat** → Magic Logger tự động OCR & lưu vào CRM.

| Kênh | Yêu cầu Sale | Kết quả |
|---|---|---|
| Zalo OA | Paste vào TeraChat | Magic Logger lo phần nhập liệu CRM. Dữ liệu thuộc công ty. |
| Telegram | Paste vào TeraChat | ↑ |
| Facebook Messenger | Paste vào TeraChat | ↑ |

> Dù Zalo/Facebook thay đổi API, TeraChat vẫn hoạt động 100% — không phụ thuộc bên thứ 3.

### 3.3 Enterprise Launchpad & Marketplace

**Enterprise Launchpad (Productivity Dock)**

Cửa sổ trung tâm điều khiển cho nhân viên, tương tự Dock trên macOS nhưng dành cho doanh nghiệp:

| Trạng thái App | Icon | Hành vi |
|---|---|---|
| **Chưa tải** | ☁️ Cloud | Click → Tải `.tapp` từ Private Cluster về máy |
| **Đã cài** | ✅ App Icon | Click → Khởi chạy trong WASM Sandbox |
| **Cần cập nhật** | 🔄 Badge | Tự cập nhật sau khi Admin push phiên bản mới |

**Nguyên tắc Marketplace:**

- **Admin kiểm soát hoàn toàn** — Nhân viên không tự cài app từ Internet.
- App được phân quyền theo phòng ban (OPA Policy): Sale chỉ thấy Magic Logger, Finance chỉ thấy Finance App.
- Mọi app phải được Admin duyệt trước khi xuất hiện trên Launchpad.

**Quy trình Admin triển khai app:**

```
1. Admin vào TeraChat Marketplace → Tải gói .tapp
2. Upload lên Admin Console → Hệ thống verify chữ ký & tạo Manifest
3. Admin cấu hình: "Chỉ phòng Sale thấy app này" (OPA Policy)
4. Nhân viên Sale mở Launchpad → Thấy icon Magic Logger ☁️ → Click tải
5. App chạy trong WASM Sandbox → PII được che trước khi gửi lên AI API
```

**Link Security (Airlock):**

- Link nội bộ (Trusted Domain) → Mở thẳng trong TeraChat.
- Link ngoài → Bottom Sheet xác nhận trước khi mở trình duyệt.
- Google Safe Browsing API scan tự động.
- Admin có thể push Managed Bookmarks, blacklist domain.

### 3.4 Offline-First (Instant-on)

> **"App mở lên là chạy ngay. Nhân viên làm việc mọi lúc mọi nơi — dữ liệu âm thầm đồng bộ khi có mạng."**

**User Experience:**

- Nhân viên mở app ngay cả khi không có Internet — app chạy dưới 500ms.
- Nhập dữ liệu offline → lưu cục bộ ngay, **không có vòng xoay "Loading"**.
- Khi Internet trở lại → Background Worker tự động sync, người dùng không cần làm gì.
- Xung đột dữ liệu giữa 2 người sửa cùng lúc → hiển thị dialog cho user chọn.

**Survival Link (Mesh — khi Internet sập hoàn toàn):**

1. App phát hiện mất Internet → hiển thị thông báo.
2. User bấm **[BẬT Mesh]** → App tìm thiết bị đồng nghiệp qua Bluetooth.
3. Tin nhắn text truyền qua BLE (relay nhảy cóc A→B→C).
4. File lớn → chuyển sang Wi-Fi Direct (~30MB/s).
5. Khi Internet trở lại → app tự tắt Mesh, đồng bộ về Server.

### 3.5 Federation (Zone 2 — Vùng 2)

**Kịch bản sử dụng:** Sale của Công ty A chat với khách hàng Công ty B.

**Cơ chế user flow:**

1. Sale mở cửa sổ chat mới → Chọn "Liên hệ đối ngoại" → App tự chuyển sang Vùng 2.
2. Audit Log tự động ghi lại toàn bộ cuộc hội thoại (metadata + encrypted hash).
3. Sale nghỉ việc → IT Admin revoke quyền → Dữ liệu khách hàng **ở lại với công ty**, không theo người.

**DLP Quarantine (khi file bị chặn):**

1. Sale cố gửi file từ phòng R&D (bị cấm) → App hiển thị "File cần được duyệt".
2. Supervisor nhận notification → Xem trước nội dung → Bấm "DUYỆT" (ký điện tử).
3. Khi đủ số supervisor yêu cầu (M-of-N) → File được gửi đi.

### 3.6 Inter-org Federation (Phase 2)

- **Transport:** Relay Server A ↔ Relay Server B qua mTLS + Sealed Sender.
- **Data Sovereignty:** Mỗi org giữ dữ liệu riêng, chỉ forward E2EE payload qua Federation Bridge.
- **Audit toàn bộ:** Mọi tin nhắn liên tổ chức → tamper-proof audit log.

---

## 4. UI/UX Philosophy & Constraints

### 4.1 Desktop: Data Density Philosophy

> **"TeraChat là công cụ lao động, không phải mạng xã hội."**

**Core Principles:**

**1. Không có Chat Bubbles:**

- Loại bỏ giao diện bong bóng chat (Facebook/Zalo style) — tốn diện tích, hiển thị ít dòng.
- Sử dụng **List View** (Slack/Discord/Terminal style): Avatar nhỏ 24px, tên người gửi highlight màu, timestamp rõ ràng.
- **Target:** Hiển thị 20 dòng tin nhắn trên màn hình 13 inch (so với 8 dòng của Zalo).

**2. Command Palette (`Cmd+K`):**

- Điều hướng keyboard-centric, không cần chuột.
- Slash Commands: `/sign` (Trình ký), `/approve` (Duyệt chi), `/pos` (Mở máy bán hàng).
- Quick search channel, user, file.

**3. App-in-Chat (Adaptive Widgets):**

- Không pop-up cửa sổ mới.
- Mini-App (Form duyệt, Báo cáo tồn kho) hiển thị dưới dạng **Collapsible Card** ngay trong dòng chat.

**4. Topic-based Threading:**

- Mỗi Channel có Sub-threads gắn chủ đề cụ thể.
- AI Bot tự động đặt tiêu đề và gợi ý Topic cho đoạn chat.

### 4.2 Desktop Security UI

| Feature | UX Detail |
|---|---|
| **Smart Approval** | System Biometric Prompt (FaceID/Windows Hello) hiển thị thông tin giao dịch rõ ràng. |
| **File Preview** | PDF/DOCX/Excel hiển thị với Dynamic Watermark (UserID + Time + IP). Print và Screenshot bị chặn. |
| **AI Toggle** | Nút `[AI Mode: ON/OFF]` rõ ràng. Khi OFF → tuyệt đối không gửi data lên AI API. |
| **Sensitive App** | Khi mở `.tapp` nhạy cảm → Clipboard bị vô hiệu hóa, chặn keylogger global. |

### 4.3 AI Sidecar Panel

Panel bên phải (tương tự Copilot), kích hoạt khi User chủ động:

- **Summarize:** Tóm tắt cuộc họp / thread dài.
- **Translate:** Dịch thuật đa ngôn ngữ.
- **Draft:** Soạn thảo Email / báo cáo.
- **Thread Auto-Title:** Tự động đặt tiêu đề cho Topic.

> **Opt-in Only:** User phải @mention Bot hoặc Add Bot vào nhóm. AI không tự ý đọc tin nhắn.

---

## 5. Mobile Product

### 5.1 Mobile Philosophy: Push-First

> **"Khác với Data Density của Desktop, Mobile sử dụng triết lý 'Vuốt trượt và Cảnh báo'."**

- Thay vì List View hẹp & đặc, Mobile dùng **Feed View** hoặc **Card View**.
- Command Palette thay bằng **Floating / Quick Action Button** phù hợp thao tác 1 ngón tay.
- Mobile là "tay chân tiền tuyến" — nhận thông báo, xem nhanh, phê duyệt nhanh.

### 5.2 Mobile vs Desktop Feature Matrix

| Feature | Desktop | Mobile |
|---|---|---|
| **Chat** | List View, 20 dòng/màn hình | Feed View / Card View |
| **Smart Approval** | Full signing flow | Nhanh — xem & ký bằng FaceID |
| **Magic Logger** | Paste + OCR | Chụp ảnh trực tiếp → OCR |
| **Marketplace** | WASM .tapp đầy đủ | Adaptive Cards (JSON) — không chạy WASM |
| **Offline** | CRDT đầy đủ (toàn bộ lịch sử) | CRDT 30 ngày gần nhất |
| **Survival Link** | Desktop = Super Node (Bridge) | BLE/Wi-Fi Direct trực tiếp |
| **Background** | Luôn kết nối WebSocket | Wake-up Ping (APNS/FCM) |

### 5.3 Kiosk Mode (F&B/Retail)

**Vấn đề:** Nhà hàng, cafe, shop thời trang dùng 1 iPad cho 3–4 nhân viên theo ca.

**Giải pháp UX:**

- iPad hiển thị màn hình đăng nhập ca: ô nhập **PIN 4-6 số** hoặc **quét Thẻ từ NFC**.
- Sau khi nhập PIN → Session mở trong ca làm việc.
- Cuối ca → bấm "Kết thúc ca" → Session Key xóa → màn hình đăng nhập hiện lại.
- Audit Log ghi rõ nhân viên nào đã thao tác lệnh nào.

**Use cases chính trên Kiosk:**

- Nhận/gửi Order từ bàn.
- Magic Logger: chụp ảnh Bill → tự động nhập kho.
- Nhận lệnh điều phối từ quản lý qua nhóm chat.

### 5.4 Mobile Notifications

- Tin nhắn đến → Relay Server gửi Silent Push (không có nội dung, bảo mật tuyệt đối).
- iOS/Android OS đánh thức App → App tự kết nối, giải mã, hiển thị Local Notification: **"Bạn có tin nhắn mới"**.
- Nội dung tin nhắn **không bao giờ** xuất hiện trong payload push.

---

## 6. Ecosystem Integrations (User Perspective)

### 6.1 ChatOps & DevOps Console

- Grafana/Prometheus/Sentry alert → Adaptive Card trong nhóm DevOps.
- Nút bấm "Restart Server", "Rollback", "View Logs" ngay trên thẻ Card.
- Dev có thể SSH vào Server nội bộ qua **TeraChat Tunnel** — không cần VPN.

### 6.2 Pre-built Connectors (User Benefits)

| Connector | Lợi ích cho User |
|---|---|
| **Jira/Linear** | Tạo ticket từ chat, cập nhật trạng thái mà không rời TeraChat |
| **SAP/Oracle ERP** | Nhận thông báo PO, duyệt chi tiêu ngay trong chat |
| **GitHub/GitLab** | Nhận thông báo PR, CI/CD, merge notification |
| **Google Workspace** | Calendar invite, chia sẻ Drive file |
| **Microsoft 365** | Teams bridge, SharePoint, Azure AD sync |
| **Salesforce** | Thông báo lead mới, duyệt deal |
| **Slack Bridge** | 2-way message sync trong giai đoạn migration |

### 6.3 Identity Integration (User-transparent)

- Nhân viên đăng nhập 1 lần qua **SSO (Google, M365, Slack)** — không cần tạo tài khoản mới.
- Khi nhân viên bị xóa khỏi HR → quyền TeraChat bị thu hồi tự động (trong vòng 15 phút với SCIM, real-time với SCIM 2.0 Enterprise).
- Nhân viên nghỉ việc → không mang theo được dữ liệu khách hàng (Vùng 2).

---

## 7. Product Roadmap

### Revised Roadmap (Prioritized Actions)

| Module | Action | Rationale | Audience |
|---|---|---|---|
| **Zone Architecture** | SỬA — xóa logic Vùng 3 cá nhân | Đơn giản hóa kiến trúc, focus Enterprise | Tất cả |
| **Identity (Shared Device Auth)** | NÂNG CẤP | Thêm chế độ 1 Device Key + PIN Session | F&B / Bán lẻ |
| **P2P Transport** | GIỚI HẠN — chỉ LAN P2P | Chặn P2P qua Internet (bảo mật + compliance) | Văn phòng / Tech |
| **Magic Logger** | MỞ RỘNG — context RAG theo ngành | Gov: Văn bản. F&B: Bill. POS: SKU. | Tất cả |
| **Marketplace** | QUY HOẠCH — Admin-push theo Department | Không cho User tự cài. OPA per-dept. | Enterprise |
| **Deployment** | ĐƠN GIẢN HÓA — thêm Reseller Mode | Xóa Personal Mode. MSP partner deploy. | Tech Support / MSP |

### Use Case Selling Points

| Scenario | TeraChat Advantage |
|---|---|
| **Chính phủ / Cứu hộ** | Bão làm sập BTS → Survival Link. Đội cứu hộ điều phối + gửi bản đồ qua P2P. |
| **Nhà máy** | Xe container cắt cáp quang → Kho vận vẫn gửi lệnh xuất kho qua Mesh. |
| **Văn phòng** | Cháy nổ, mất điện → Nhân viên điểm danh + gửi sơ đồ thoát hiểm qua BLE. |
| **F&B Chain** | 1 iPad cho 3 nhân viên → Kiosk Mode + Magic Logger = zero manual data entry. |
| **Bank** | Phê duyệt chi tiêu lớn → Smart Approval 3 cấp với ký số USB Token (Gov CA). |

---

*Tài liệu này chỉ chứa product flows, UX và user requirements. Xem `TechSpec.md` cho technical implementation. Xem `BusinessPlan.md` cho chiến lược kinh doanh.*
