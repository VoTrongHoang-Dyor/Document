# TeraChat — Bản Tóm Tắt Đầu Tư 2026 (Business Plan & GTM Strategy)

> [!IMPORTANT]
> Tài liệu bảo mật — Chỉ dành cho Nhà Đầu Tư. Q1 2026 · Vòng Gọi Vốn Hạt Giống.

## 01 / 09 Vấn Đề: Ngành Công Nghiệp $200 Tỷ Được Xây Trên Nền Tảng Mất Tin Cậy

- ☁️ Phụ thuộc 100% vào Cloud bên thứ ba (AWS/Azure/Google Cloud), vi phạm trực tiếp các tiêu chuẩn GDPR, ISO 27001 và Luật An ninh mạng Việt Nam.
- 🖥️ Công cụ cộng tác hiện tại (Slack/Teams) trở thành "điểm lỗi duy nhất" (Single Point of Failure); toàn bộ liên lạc doanh nghiệp bị tê liệt khi mất kết nối Internet.
- 🗄️ Nhà cung cấp hạ tầng giữ quyền truy cập metadata và nội dung, tạo lỗ hổng cho gián điệp công nghiệp và rò rỉ dữ liệu nội bộ.

## 02 / 09 Giải Pháp: TeraChat — Chủ Quyền Ngay Từ Kiến Trúc

- 🖥️ **Lõi Mật Mã Rust:** Thực thi mã hóa đầu cuối (E2EE) tại thiết bị; máy chủ chỉ xử lý byte đã mã hóa, đảm bảo Zero-Knowledge native.
- 📱 **Survival Mesh Network:** Tận dụng BLE 5.0 và Wi-Fi Direct để duy trì liên lạc nội bộ khi cơ sở hạ tầng mạng sụp đổ; ưu tiên dữ liệu nghiệp vụ khẩn cấp (Delta CRDT).
- 🗄️ **Hạ Tầng Phân Tán:** Triển khai cụm máy chủ riêng tư thuộc sở hữu khách hàng; hỗ trợ kiến trúc đa điểm liên kết (Federated Clusters).
- 💻 **QUIC 0-RTT:** Phục hồi kết nối ngay lập tức (0ms) khi chuyển đổi mạng, tối ưu hóa trải nghiệm trong môi trường thực địa nhạy cảm.

## 03 / 09 Cơ Hội Thị Trường

- ☁️ **TAM Toàn Cầu:** Dự kiến đạt $85 tỷ vào năm 2030 (CAGR ~10%).
- 🗄️ **Đông Nam Á:** Cơ hội $2 tỷ+ nhờ các luật nội địa hóa dữ liệu (Thông tư 13 VN, GR 71 ID, PDPA TH) cấm sử dụng công cụ Cloud công cộng cho mảng Ngân hàng và Chính phủ.
- 🖥️ **Phân khúc mục tiêu:** Tài chính ($18B), Chính phủ ($12B), Sản xuất ($22B), Y tế ($8B).

## 04 / 09 Mô Hình Kinh Doanh: Zero Bandwidth Cost

- 🗄️ **Biên Lợi Nhuận Gộp >90%:** Chuyển dịch toàn bộ chi phí máy chủ và lưu trữ sang khách hàng; TeraChat chỉ thu phí bản quyền (License).
- ☁️ **Revenue Streams:**
    - Đăng ký doanh nghiệp: $500–$8.000/tháng.
    - Dịch vụ chuyên nghiệp (On-premise / Air-gapped): $50K–$200K/triển khai.
    - Elite Compute Tier (Security Enclaves): $3.000/tháng.
    - .tapp Marketplace: Thu phí 30% doanh thu từ mini-apps bên thứ ba.

## 05 / 09 Lợi Thế Cạnh Tranh: Hào Lũy Được Xây Bằng Rust

- 🖥️ **Kiến Trúc Zero-Knowledge:** Ngăn chặn việc nhà cung cấp truy cập plaintext ngay từ thiết kế lõi, không thể sao chép trên các nền tảng Cloud-first hiện có.
- 💻 **Elite TEE Enclaves:** Sử dụng Intel SGX / AMD SEV để thực thi AI/ML trong môi trường bộ nhớ được bảo vệ ở cấp CPU, ngay cả Admin hệ thống cũng không thể can thiệp.
- 📱 **Survival Mesh:** Độc quyền công nghệ liên lạc Mesh offline qua BLE, tạo lợi thế tuyệt đối cho các ngành Hàng hải, Mỏ mỏ và Quốc phòng.

## 06 / 09 Chiến Lược Tăng Trưởng: Đòn Bẩy Zone 2

- 📱 **Phase 1 (0-18 tháng):** Chiếm lĩnh mảng F&B (Kiosk Mode / AI Scanner) và Hành chính công (Smart Approval / Chữ ký số Ed25519).
- 🗄️ **Phase 2 (12-36 tháng):** Triển khai Zone 2 (Giao tiếp đối ngoại) cho Ngân hàng; thiết lập Survival Mesh cho khối Sản xuất.
- ☁️ **Phase 3 (24-48 tháng):** Mở rộng hệ sinh thái .tapp Marketplace; cung cấp module HSM Air-gapped cho khối Tình báo & Quốc phòng.

## 07 / 09 Dự Báo Tài Chính & Phân Bổ Vốn

- 💹 **Mục Tiêu ARR:** Năm 1 ($480K), Năm 2 ($2.16M), Năm 3 ($9M).
- 🛡️ **Sử Dụng Vòng Seed:** 
    - 20%: Kiểm toán & Chứng chỉ (ISO 27001, SOC 2, HIPAA).
    - 40%: R&D Lõi (Mật mã Rust, CRDT Engine, Native Apps).
    - 25%: GTM & Mạng lưới Reseller (MSP).
    - 15%: Quỹ dự phòng hoạt động 18-24 tháng.

## 08 / 09 Tầm Nhìn Dài Hạn

- 🖥️ **Work OS:** Trở thành giao diện tác nhân AI thống nhất cho mọi quy trình tự động hóa doanh nghiệp.
- ☁️ **Sovereign Network:** Xây dựng mạng lưới liên kết kỹ thuật số chủ quyền xuyên biên giới, đảm bảo tuân thủ cư trú dữ liệu tại từng quốc gia.

## 09 / 09 Chiến Lược Cấp Phép & Sở Hữu Trí Tuệ

- 🖥️ **Open-Core (AGPLv3):** Công khai lõi mật mã Rust và Giao thức liên kết để các tổ chức Gov/Banking xác minh độc lập, xóa bỏ rào cản về "backdoor".
- 🗄️ **Proprietary:** Bảo vệ bản quyền Admin Console, Module AI (Magic Logger) và Hệ thống License Manager nhằm đảm bảo dòng tiền doanh thu.
- 🗄️ **Protocol Versioning:** Sử dụng tính không tương thích của các phiên bản giao thức lớn để thúc đẩy chu kỳ nâng cấp License định kỳ theo yêu cầu tuân thủ IT.
