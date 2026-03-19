```yaml
# DOCUMENT IDENTITY
id:       "TERA-INTRO"
title:    "Introduction — System Gateway"
version:  "0.2.6"
audience: "New Team Member, System Architect, Product Manager, Investor / Executive"
purpose:  "Giải thích tại sao hệ thống tồn tại, kiến trúc tổng thể, thuật ngữ chung và bản đồ định tuyến tài liệu."

ai_routing_hint: |
  "Đọc file này đầu tiên để nắm tổng quan về kiến trúc, lý do tồn tại của hệ thống và điều hướng tài liệu."
```

# Introduction.md — System Gateway

> *"Trong thế giới mà dữ liệu là quyền lực, ai kiểm soát khóa mã hóa — kẻ đó làm chủ cuộc chơi. TeraChat trao lại chìa khóa đó về tay doanh nghiệp."*
>
> — CEO, TeraChat

Chào mừng đến với TeraChat. Đây không đơn thuần là một ứng dụng nhắn tin. Đây là sự khởi đầu của một kỷ nguyên mới về **Chủ quyền số (Digital Sovereignty)** — một hệ điều hành công tác (Operating System for Work) bất khả xâm phạm dành cho các doanh nghiệp, chính phủ và tổ chức từ chối giao phó sinh mệnh dữ liệu của mình cho các máy chủ bên thứ ba.

Tài liệu này là cánh cổng đầu tiên bước vào hệ sinh thái TeraChat. Nó được thiết kế để truyền tải tầm nhìn, các nguyên lý cốt lõi và kiến trúc khái quát định hình nên toàn bộ nền tảng.

---

## 1. [CONCEPT] Vision & Mission

**Nhiệm vụ của chúng tôi là trả lại toàn quyền kiểm soát thông tin cho người sở hữu đích thực của nó.**

Trong thập kỷ qua, các nền tảng đám mây công cộng đã định hình lại cách thế giới làm việc, nhưng sự tiện lợi đó đi kèm với một cái giá đắt: sự phụ thuộc và việc đánh mất quyền kiểm soát thực sự. Các tổ chức tin tưởng đặt toàn bộ tài sản trí tuệ, chiến lược kinh doanh và thông tin tình báo của mình lên các trung tâm dữ liệu mà họ không thể thấu hiểu hoàn toàn.

TeraChat ra đời với một sứ mệnh duy nhất: Xóa bỏ ranh giới của sự phụ thuộc này. Tầm nhìn của chúng tôi là tạo ra thế hệ hạ tầng viễn thông doanh nghiệp đầu tiên trên thế giới mà ở đó, **Sự Bảo Mật Được Đảm Bảo Bằng Toán Học, Không Phải Bằng Lời Hứa.**

---

## 2. [CONCEPT] Why TeraChat Exists

Ngành công nghiệp viễn thông doanh nghiệp hiện nay được xây dựng trên một nền tảng thiếu sự tin cậy:

* Mọi tương tác đều đi qua máy chủ bên thứ ba, vi phạm nguyên tắc bảo mật thông tin và tạo ra lỗ hổng bẩm sinh cho gián điệp công nghiệp.
* Công việc bị đình trệ hoàn toàn khi hệ thống mạng trung tâm gặp sự cố. Sự phụ thuộc vào Internet đang làm tê liệt khả năng làm việc trong môi trường thực địa nhạy cảm, vùng sâu vùng xa hoặc các tình huống khủng hoảng.
* Hệ thống quy định tuân thủ lưu trữ (ISO 27001, SOC2, Luật An ninh mạng) ngày càng nghiêm ngặt nhưng cấu trúc đám mây truyền thống không thể đáp ứng tiêu chuẩn.

TeraChat tồn tại để xóa bỏ "điểm đứt gãy duy nhất" (Single Point of Failure). Chúng tôi thiết kế lại toàn bộ luồng giao tiếp theo phương thức **Zero-Knowledge**, nơi nhà cung cấp dịch vụ trở nên mù lòa vĩnh viễn trước dữ liệu của khách hàng, đồng thời duy trì khả năng sinh tồn tuyệt đối trong môi trường Offline (→ TERA-CORE §[Mạng lưới Sinh tồn]).

---

## 3. [RULE] Core Principles

Hệ thống được thiết kế xung quanh 4 nguyên lý bất di bất dịch:

* **Zero-Knowledge Architecture:** Máy chủ của chúng tôi hoạt động theo mô hình máy chủ mù (`Blind Relay`). Hệ thống chỉ thực hiện việc định tuyến các gói tin đã mã hóa. Chúng tối hoàn toàn không nắm giữ khóa giải mã, không biết danh tính thực của người dùng, và không có khả năng đọc được nội dung thảo luận (→ TERA-CORE).
* **End-to-End Encryption (E2EE):** Toàn bộ vòng đời của dữ liệu – từ văn bản, tệp tin đến các cuộc gọi thoại và video – được mã hóa và giải mã ngay tại thiết bị vật lý của người dùng. Dữ liệu không bao giờ tồn tại dưới dạng bản rõ (plaintext) trên không gian mạng.
* **Offline Survival Capability:** Quyền kết nối không phụ thuộc vào Internet. Ngay cả khi hạ tầng mạng quốc gia hoặc toàn cầu sụp đổ, hệ thống vẫn duy trì sống sót bằng cách tự động kết nối các thiết bị thông qua mạng lưới vô tuyến cục bộ, tạo ra một mạng sinh tồn độc lập cho doanh nghiệp (`Survival Mesh`).
* **Zero-Trust System Design:** Hệ thống không bao giờ tin tưởng bất kỳ ai, thiết bị hay kết nối nào, kể cả ở môi trường nội bộ. Mọi quyền truy cập, mọi luồng giao tiếp ra khỏi thiết bị đều bị chất vấn, đóng đinh bởi bộ xử lý bảo mật trước khi được cấp phép thực thi.

---

## 4. [ARCHITECTURE] High-Level Architecture

TeraChat là sự hội tụ giữa khoa học mật mã và kỹ thuật máy tính phân tán. Các thành phần nền móng định hình nên kiến trúc này bao gồm:

* **Shared Rust Core:** Một lõi xử lý duy nhất xuyên nền tảng, đảm đương 100% nghiệp vụ mạng, mật mã học nhằm đồng nhất tuyệt đối nguyên tắc an toàn (→ TERA-CORE).
* **Client-Side Cryptography:** Chìa khóa bảo mật được sinh ra, quản lý và sử dụng bên trong các vi mạch an toàn của thiết bị cực đoan phần cứng, loại trừ nguy cơ giải mã từ xa.
* **Blind Relay Servers:** Cơ sở hạ tầng trung chuyển dữ liệu mù loà làm nhiệm vụ lưu trữ, trung chuyển nhưng không có chìa khóa, xóa bỏ quyền lực đọc hiểu từ nền tảng máy chủ đám mây.
* **Survival Mesh Networking:** Kiến trúc kết nối mạng ngang hàng sinh tồn (P2P), cho phép tạo chuỗi mạng không dây độc lập và tự chữa lành.
* **Tiered Connectivity Model:** Chiến lược thích ứng thông minh tự đo lường tình trạng băng thông từ Internet quốc tế tới Bluetooth tầm xa để quyết định luồng dữ liệu truyền tải tối ưu.

---

## 5. [CONCEPT] Core Capabilities

Những năng lực then chốt mà nền tảng mang lại cho một tổ chức quy mô lớn:

* **Secure messaging & Voice/video:** Nhắn tin, gọi video/âm thanh nhóm an toàn tuyệt đỉnh chống nghe lén.
* **Offline collaboration:** Khả năng chat và chia sẻ tài liệu ngang hàng (P2P) khi các hệ thống truyền thống mất kết nối.
* **AI privacy protection:** Lõi kiến trúc làm sạch ẩn danh thực hiện quét và tự động loại bỏ mọi dữ liệu định danh cấu trúc/thông tin nhạy cảm của doanh nghiệp trước khi giao tiếp AI.
* **Cross-organization federation:** Thiết lập các "đường hầm liên kết ngầm" cho phép Tổng công ty lớn và nhiều cơ quan, chi nhánh con hoạt động ở từng Private Cloud riêng biệt nhưng vẫn an toàn trao đổi (→ TERA-FUNC).
* **Extension ecosystem (`.tapp`):** Môi trường cách ly để tích hợp an toàn các tiện ích nghiệp vụ nội bộ (Zalo Office, Quản lý kho, Quản lý tài liệu). Kích hoạt tiềm năng khổng lồ từ thị trường công cụ quản trị B2B (→ TERA-MKT).

---

## 6. [RULE] System Terminology

Sự thống nhất về khái niệm là cơ sở cho các kiến trúc vĩ đại.

* **`.tapp`:** Tiện ích nghiệp vụ siêu nhỏ chạy cách ly an toàn trên thiết bị bảo mật.
* **`Company_Key`:** Khóa cấp doanh nghiệp/tổ chức, mã hóa mọi lưu lượng dữ liệu trước khi đi qua đám mây.
* **`Blind Relay`:** Các máy chủ trung gian chuyển dữ liệu mà không nắm giữ quyền giải mã.
* **`TreeKEM / MLS`:** Phương thức quản trị khóa nhóm mã hóa tối tân, mở rộng được cho cả 5.000 tham dự viên trong một nhóm chat an toàn.
* **`Survival Mesh`:** Mạng lưới giao tiếp tự thiết lập giúp duy trì kết nối Offline.
* **`Shared Rust Core`:** Trái tim mật mã xử lý mọi giao dịch bảo mật cốt lõi chung cho mọi thiết bị.

---

## 7. [RULE] Product Scope

**In Scope (Trong Phạm vi Thực thi)**

* Môi trường truyền thông an toàn tuyệt đối cấp độ tổ chức.
* Cơ sở hạ tầng trung chuyển Zero-knowledge.
* Khả năng sinh tồn đồng bộ nhóm khi vắng bóng nền tảng mạng Internet.
* Chống chia cắt thông tin giữa các thực thể liên minh tổ chức (Federation).

**Out of Scope (Ngoài Phạm vi Cung cấp)**

* Lưu trữ thông tin văn bản thuần (plaintext) trên đám mây quốc gia.
* Nền tảng làm việc chia sẻ bắt buộc dựa dẫm vào kết nối Cloud trung tâm.
* Can thiệp kiểm duyệt tự động dựa trên phân tích từ vựng đối thoại tại máy chủ.

---

## 8. [RULE] Documentation Reading Map

Cánh cổng này sẽ dẫn dắt từng chuyên môn tìm đến tài liệu lõi của mình:

* **Developers (Lập trình ứng dụng Client):** Xin mời đọc `Feature_Spec.md` (→ TERA-FEAT).
* **System Architects (Kiến trúc sư hệ thống khối Cloud & Mạng lưới Rust):** Xin mời đọc `Core_Spec.md` (→ TERA-CORE).
* **Product Managers (Giám đốc sản phẩm chức năng phân quyền nhóm):** Xin mời đọc `Function.md` (→ TERA-FUNC).
* **Designers (Thiết kế hệ thống giao diện đặc chủng):** Xin mời đọc `Design.md` (→ TERA-DESIGN).
* **Platform Ecosystem Builders (Phát triển hệ sinh thái thị trường ứng dụng Sandbox .tapp):** Xin mời đọc `Web_Marketplace.md` (→ TERA-MKT).

*TeraChat — Trao lại chủ quyền số cho người tiên phong.*
