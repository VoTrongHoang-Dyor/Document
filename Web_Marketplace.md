# Web_Marketplace.md — TeraChat Ecosystem & Storefront

> **Audience:** 3rd-party Developers, IT Admins, Business Team
> **Scope:** Quy trình duyệt App, Thanh toán (Payment Gateway), License Management, và Tiêu chuẩn Bảo mật Nền tảng.

## 1. Tổng quan Hệ sinh thái TeraChat Marketplace

TeraChat Web Marketplace (`marketplace.terachat.io`) là chợ ứng dụng B2B dành riêng cho các tiện ích `.tapp`.

- **Với Developer/Đối tác SI:** Nơi đăng bán các `.tapp` tiện ích (AI Summarizer, CRM Bridge, ERP Connector) để tiếp cận tệp khách hàng Doanh nghiệp/Chính phủ.
- **Với Doanh nghiệp:** Nơi mua sắm, kiểm duyệt (Audit) và tải các công cụ đã được TeraChat bảo chứng an toàn tuyệt đối.
- **Mesh_Recovery.tapp:** Cung cấp một Tapp chuyên dụng trên Marketplace để các IT Admin có thể rà quét và thu gom các Blind Shard đang trôi nổi trong các thiết bị của nhân viên sau khi mạng Server được khôi phục, nhằm dọn dẹp dung lượng rác (Crypto-Shredding rác mạng).

## 2. Mô hình Kinh doanh & Thanh toán (B2B Billing)

- **Cơ cấu Doanh thu:** Developer tự định giá `.tapp` (Trả một lần hoặc Thuê bao hàng tháng). TeraChat thu phí hoa hồng cố định **10%** trên mọi giao dịch (thấp hơn nhiều so với mức 30% của Apple/Google để kích thích cộng đồng).
- **Cổng Thanh toán Tích hợp:** Hỗ trợ thanh toán B2B qua **PayPal Business**, **Stripe (Mastercard/Visa)**, và Chuyển khoản ngân hàng (Wire Transfer cho hóa đơn lớn).
- **Air-Gapped License Token:** Vì máy chủ VPS của Doanh nghiệp thường chặn Internet, thanh toán không thể diễn ra trong App.
  - Admin thanh toán trên nền tảng Web (`marketplace.terachat.io`).
  - Hệ thống sinh ra một file chữ ký số `License_Token.teralic` (Ví dụ: "Hợp lệ từ 01/2026 đến 12/2026").
  - Admin tải file `.tapp` + `License_Token` về máy và upload thủ công lên Private VPS. Lõi Rust trên VPS sẽ xác thực chữ ký offline này để kích hoạt App.

## 3. Quy trình Kiểm duyệt "Bàn tay sắt" (App Audit Workflow)

Mọi `.tapp` trước khi lên Store phải qua 3 vòng kiểm duyệt khắt khe, tuân thủ Luật Bất Di Bất Dịch: **"Không tuồn dữ liệu Doanh nghiệp"**.

1. **Automated Static Scan:** TeraChat CI/CD quét file WASM, chặn các syscall trái phép.
2. **Network Whitelist Binding:** Developer bắt buộc nộp tệp `Manifest.json` khai báo đúng 1-2 Domain đích (Ví dụ: `api.openai.com`). Nếu domain này thuộc hệ thống không có chính sách bảo vệ dữ liệu doanh nghiệp (No-Logging Policy), app sẽ bị **Từ chối (Reject) tự động**.
3. **Manual Security Audit:** Đội ngũ kỹ sư TeraChat dịch ngược (Decompile) mã WASM để kiểm tra thuật toán. Nếu đạt, file `.tapp` sẽ được ký số bằng khóa `TeraChat_Store_CA` (Ed25519) và cấp nhãn **Verified Badge 🛡️**.

## 4. Quản lý Trách nhiệm Pháp lý (Liability Shift)

Khi Admin doanh nghiệp bấm mua và tải `.tapp`, Web Marketplace sẽ hiển thị một **Security Manifest Consent** (Bảng Thỏa thuận Bảo mật).
Nội dung ghi rõ: *"Tiện ích này sẽ gửi dữ liệu đến `api.partner.com`. Bằng việc cài đặt, Doanh nghiệp chấp nhận định tuyến dữ liệu ra ngoài TeraVault. TeraChat không chịu trách nhiệm về dữ liệu sau khi dữ liệu đã rời khỏi Gateway nội bộ."* -> Trách nhiệm pháp lý thuộc về Admin và Developer, bảo vệ TeraChat khỏi các vụ kiện rò rỉ dữ liệu.
