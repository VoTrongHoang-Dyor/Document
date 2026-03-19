# TeraChat — Bản Tóm Tắt Đầu Tư 2026 (Business Plan & GTM Strategy)

```yaml
# DOCUMENT IDENTITY
id:       "TERA-BIZ"
title:    "TeraChat — Business Plan & GTM Strategy"
version:  "0.2.6"
audience: "Investor, Executive, Sales, System Architect"
purpose:  "Đặc tả mô hình kinh doanh, chiến lược Go-To-Market, định vị sản phẩm và chiến lược cấp phép (Licensing)."

ai_routing_hint: |
  "AI mở file này khi người dùng hỏi về mô hình kinh doanh, licensing, pricing, GTM strategy, hoặc định vị cạnh tranh của TeraChat."
```

> [!IMPORTANT]
> Tài liệu bảo mật — Chỉ dành cho Nhà Đầu Tư. Q1 2026 · Vòng Gọi Vốn Hạt Giống.

## 01 / 09 [BUSINESS] [CONCEPT] Vấn Đề: Ngành Công Nghiệp $200 Tỷ Được Xây Trên Nền Tảng Mất Tin Cậy

- ☁️ Phụ thuộc 100% vào Cloud bên thứ ba (AWS/Azure/Google Cloud), vi phạm trực tiếp các tiêu chuẩn GDPR, ISO 27001 và Luật An ninh mạng Việt Nam.
- 🖥️ Công cụ cộng tác hiện tại (Slack/Teams) trở thành "điểm lỗi duy nhất" (Single Point of Failure); toàn bộ liên lạc doanh nghiệp bị tê liệt khi mất kết nối Internet.
- 🗄️ Nhà cung cấp hạ tầng giữ quyền truy cập metadata và nội dung, tạo lỗ hổng cho gián điệp công nghiệp và rò rỉ dữ liệu nội bộ.

## 02 / 09 [BUSINESS] [ARCHITECTURE] Giải Pháp: TeraChat — Chủ Quyền Ngay Từ Kiến Trúc

- 🖥️ **Lõi Mật Mã Rust:** Thực thi mã hóa đầu cuối (E2EE) tại thiết bị; máy chủ chỉ xử lý byte đã mã hóa, đảm bảo Zero-Knowledge native.
- 📱 **Survival Mesh Network:** Tận dụng BLE 5.0 và Wi-Fi Direct để duy trì liên lạc nội bộ khi cơ sở hạ tầng mạng sụp đổ; ưu tiên dữ liệu nghiệp vụ khẩn cấp (Delta CRDT).
- 🗄️ **Hạ Tầng Phân Tán:** Triển khai cụm máy chủ riêng tư thuộc sở hữu khách hàng; hỗ trợ kiến trúc đa điểm liên kết (Federated Clusters).
- 💻 **QUIC 0-RTT:** Phục hồi kết nối ngay lập tức (0ms) khi chuyển đổi mạng, tối ưu hóa trải nghiệm trong môi trường thực địa nhạy cảm.

## 03 / 09 [BUSINESS] Cơ Hội Thị Trường

- ☁️ **TAM Toàn Cầu:** Dự kiến đạt $85 tỷ vào năm 2030 (CAGR ~10%).
- 🗄️ **Đông Nam Á:** Cơ hội $2 tỷ+ nhờ các luật nội địa hóa dữ liệu (Thông tư 13 VN, GR 71 ID, PDPA TH) cấm sử dụng công cụ Cloud công cộng cho mảng Ngân hàng và Chính phủ.
- 🖥️ **Phân khúc mục tiêu:** Tài chính ($18B), Chính phủ ($12B), Sản xuất ($22B), Y tế ($8B).

## 04 / 09 [BUSINESS] Mô Hình Kinh Doanh: Zero Bandwidth Cost

- 🗄️ **Biên Lợi Nhuận Gộp >90%:** Chuyển dịch toàn bộ chi phí máy chủ và lưu trữ sang khách hàng; TeraChat chỉ thu phí bản quyền (License).
- ☁️ **Revenue Streams:**
  - Đăng ký doanh nghiệp: $500–$8.000/tháng.
  - Dịch vụ chuyên nghiệp (On-premise / Air-gapped): $50K–$200K/triển khai.
  - Elite Compute Tier (Security Enclaves): $3.000/tháng.
  - .tapp Marketplace: Thu phí 30% doanh thu từ mini-apps bên thứ ba.

## 05 / 09 [BUSINESS] [SECURITY] Lợi Thế Cạnh Tranh: Hào Lũy Được Xây Bằng Rust

- 🖥️ **Kiến Trúc Zero-Knowledge:** Ngăn chặn việc nhà cung cấp truy cập plaintext ngay từ thiết kế lõi, không thể sao chép trên các nền tảng Cloud-first hiện có.
- 💻 **Elite TEE Enclaves:** Sử dụng Intel SGX / AMD SEV để thực thi AI/ML trong môi trường bộ nhớ được bảo vệ ở cấp CPU, ngay cả Admin hệ thống cũng không thể can thiệp.
- 📱 **Survival Mesh:** Độc quyền công nghệ liên lạc Mesh offline qua BLE, tạo lợi thế tuyệt đối cho các ngành Hàng hải, Mỏ mỏ và Quốc phòng.

## 06 / 09 [BUSINESS] Chiến Lược Tăng Trưởng: Đòn Bẩy Zone 2

- 📱 **Phase 1 (0-18 tháng):** Chiếm lĩnh mảng F&B (Kiosk Mode / AI Scanner) và Hành chính công (Smart Approval / Chữ ký số Ed25519).
- 🗄️ **Phase 2 (12-36 tháng):** Triển khai Zone 2 (Giao tiếp đối ngoại) cho Ngân hàng; thiết lập Survival Mesh cho khối Sản xuất.
- ☁️ **Phase 3 (24-48 tháng):** Mở rộng hệ sinh thái .tapp Marketplace; cung cấp module HSM Air-gapped cho khối Tình báo & Quốc phòng.

## 07 / 09 [BUSINESS] Dự Báo Tài Chính & Phân Bổ Vốn

- 💹 **Mục Tiêu ARR:** Năm 1 ($480K), Năm 2 ($2.16M), Năm 3 ($9M).
- 🛡️ **Sử Dụng Vòng Seed:**
  - 20%: Kiểm toán & Chứng chỉ (ISO 27001, SOC 2, HIPAA).
  - 40%: R&D Lõi (Mật mã Rust, CRDT Engine, Native Apps).
  - 25%: GTM & Mạng lưới Reseller (MSP).
  - 15%: Quỹ dự phòng hoạt động 18-24 tháng.

## 08 / 09 [BUSINESS] [CONCEPT] Tầm Nhìn Dài Hạn

- 🖥️ **Work OS:** Trở thành giao diện tác nhân AI thống nhất cho mọi quy trình tự động hóa doanh nghiệp.
- ☁️ **Sovereign Network:** Xây dựng mạng lưới liên kết kỹ thuật số chủ quyền xuyên biên giới, đảm bảo tuân thủ cư trú dữ liệu tại từng quốc gia.

## 09 / 09 [BUSINESS] [RULE] Chiến Lược Cấp Phép & Sở Hữu Trí Tuệ

- 🖥️ **Open-Core (AGPLv3):** Công khai lõi mật mã Rust và Giao thức liên kết để các tổ chức Gov/Banking xác minh độc lập, xóa bỏ rào cản về "backdoor".
- 🗄️ **Proprietary:** Bảo vệ bản quyền Admin Console, Module AI (Magic Logger) và Hệ thống License Manager nhằm đảm bảo dòng tiền doanh thu.
- 🗄️ **Protocol Versioning:** Sử dụng tính không tương thích của các phiên bản giao thức lớn để thúc đẩy chu kỳ nâng cấp License định kỳ theo yêu cầu tuân thủ IT.

---

## Mục Mới: Huawei Strategy, Signing Pipeline, License & TCO [BUSINESS] [PLATFORM]

### BIZ-HUAWEI-01: Huawei AppGallery Distribution Strategy

- 📱 **Thị trường mục tiêu Huawei:** Việt Nam, Đông Nam Á, Trung Đông, Đông Âu — vùng Huawei có thị phần >20% doanh nghiệp.
- 📱 **AppGallery Listing:** Submit `.apk` + AOT-bundled `.tapp` packages. Không có dynamic WASM download.
- 📱 **HMS Freemium:** Cung cấp Community tier miễn phí trên AppGallery để tăng DAU. Upsell Enterprise qua HMS Enterprise Bundle.
- 📱 **Enterprise MDM:** Tích hợp Huawei Device Manager cho Enterprise enrollment — tương đương Apple DEP/Android EMM.

**Market Sizing (Huawei Segment):**

- Việt Nam: ~3M thiết bị Huawei trong doanh nghiệp SME (ước tính IDC 2025)
- Cơ hội: Enterprise tier @150USD/user/năm × 5% penetration = ~45M USD TAM

### BIZ-SIGNING-02: CI/CD Code Signing Pipeline & Certificate Management

```yaml
iOS Signing:
  - Apple Distribution Certificate (GitHub Secrets encrypted)
  - Provisioning Profile: Main App + NSE + Share Extension (riêng biệt)
  - fastlane match để sync certificates
  - Notarize via Apple Transporter

macOS Signing:
  - Developer ID Application Certificate
  - notarytool (Xcode 13+)
  - Staple ticket vào .dmg

Windows Signing:
  - EV Code Signing Certificate (DigiCert KeyLocker — Cloud HSM)
  - signtool.exe integration trong GitHub Actions
  - SmartScreen: cần 30+ ngày clean submissions để reputation tốt
  - MSIX packaging cho Microsoft Store

Android Signing:
  - Keystore file (encrypted in GitHub Secrets)
  - Google Play App Signing (delegate signing to Google)
  - APK + AAB dual signing

Linux Signing:
  - GPG key cho .deb/.rpm packages
  - Cosign cho AppImage
  - Public key: packages.terachat.com/gpg.key
```

**COGS note:** Windows EV Code Signing Certificate (Cloud HSM) ~$500/năm — bắt buộc để SmartScreen không cảnh báo. Thêm vào COGS và pricing model.

### BIZ-LICENSE-03: License Architecture Gaps (Resolution)

**Open-Core Boundary rõ ràng:**

| Thành phần | License | Ai có thể audit |
|---|---|---|
| `terachat-core` (Crypto, MLS, CRDT, Mesh) | AGPLv3 | Gov, Bank, Public |
| `terachat-license-guard` | BSL (Business Source License) | Không public |
| `terachat-ui` (Tauri, Flutter) | Apache 2.0 | Public |

Sales pitch → Gov/Bank: *"Toàn bộ cryptographic core có thể compile và audit độc lập. License validation là module riêng không ảnh hưởng security audit scope."*

**License Distribution Channels:**

- Online: JWT qua email bảo mật + `cosign verify-blob` để chống supply chain attack
- Air-Gapped (SCIF): JWT trên USB AES-256, giao vật lý cho CISO

### BIZ-TCO-04: TCO Reference Architecture (Enterprise On-Premise)

| Quy mô | Cold Storage/năm | VPS tối thiểu | DR RTO |
|---|---|---|---|
| 1,000 users | ~500GB | 4 vCPU, 8GB RAM, 100GB SSD | <15 phút |
| 5,000 users | ~2.5TB | 8 vCPU, 16GB RAM, 250GB SSD | <15 phút |
| 10,000 users | ~5TB | 16 vCPU, 32GB RAM, 1TB SSD | <15 phút |

**DR Strategy:** Active-Passive với PostgreSQL/SQLite WAL streaming replication. RTO <15 phút, RPO <5 phút.

**Backup:** Admin cần export và lưu trữ Shamir shares (5 YubiKey cho C-Level). Mất toàn bộ shares = mất hệ thống.

### BIZ-TIER-05: GovMilitary Tier – Premium Features

| Feature | Community | Enterprise | **GovMilitary** |
|---|---|---|---|
| Offline TTL | 24h | 7 ngày (configurable) | **30 ngày** |
| EMDP Tactical Relay | ❌ | ✅ | ✅ |
| Air-Gapped License | ❌ | ✅ | ✅ |
| Compliance Retention | ❌ | 90 ngày | **7 năm** |
| Chaos Engineering Plan | ❌ | Optional | **Bắt buộc trước go-live** |
| TEE License (SGX option) | ❌ | ❌ | **Available** |

**Pricing note:** GovMilitary tier — custom pricing, minimum commitment 3 năm.

### BIZ-AES-06: AES-NI Performance Tier Note (SME Market)

Tại thị trường SME Việt Nam/Đông Nam Á, các thiết bị Android cũ (Cortex-A53, Helio A22) phổ biến. TeraChat vẫn functional với software crypto backend, nhưng mã hóa chậm 3x. Định vị: *"Chạy được trên mọi thiết bị, tối ưu nhất trên thiết bị từ 2019 trở đi."*

### BIZ-CHAOS-07: Chaos Engineering Plan (Điều kiện tiên quyết Gov Contract)

Trước khi ký hợp đồng với Government/Military customers, **bắt buộc** demonstrate 7 combined-failure scenarios trong → TERA-TEST. Đây là non-negotiable — Gov customers yêu cầu evidence-based reliability, không chỉ documentation.

**Thời gian ước tính:** 4-6 tuần Chaos Engineering + UAT với khách hàng pilot Gov.
