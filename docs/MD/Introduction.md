# Introduction.md — TeraChat System Gateway

```yaml
# DOCUMENT IDENTITY
id: "TERA-INTRO"
title: "TeraChat — System Gateway & Architecture Overview"
version: "0.4.0"
status: "ACTIVE"
date: "2026-03-25"
audience: "New Team Member, System Architect, Product Manager, Enterprise Sales, Investor"
purpose: "Định nghĩa sản phẩm, kiến trúc tổng thể, mô hình truy cập doanh nghiệp, và bản đồ điều hướng tài liệu."

ai_routing_hint: |
  "Đọc file này đầu tiên để hiểu sản phẩm TeraChat là gì, ai được phép sử dụng,
   kiến trúc hoạt động ra sao, và điều hướng đến tài liệu phù hợp."
```

---

## 1. Sản phẩm TeraChat là gì?

TeraChat là **nền tảng messaging doanh nghiệp Zero-Knowledge, End-to-End Encrypted** — được thiết kế cho các tổ chức yêu cầu kiểm soát tuyệt đối dữ liệu giao tiếp nội bộ mà không phụ thuộc vào bất kỳ nhà cung cấp dịch vụ đám mây nào.

**TeraChat không phải ứng dụng công khai.**

Mỗi phiên bản triển khai thuộc về một tổ chức duy nhất. Người dùng không thể đăng ký tài khoản cá nhân — mọi truy cập đều yêu cầu license JWT hợp lệ được cấp bởi tổ chức, được ký bởi HSM FIPS 140-3, và được neo vào domain doanh nghiệp.

> **Cam kết cốt lõi:** Bảo mật được bảo đảm bằng toán học, không phải bằng điều khoản dịch vụ.

---

## 2. Mô hình Truy cập Doanh nghiệp

### 2.1 License-Gated Architecture

```text
Tổ chức ký hợp đồng với TeraChat
         ↓
TeraChat cấp License JWT (HSM FIPS 140-3, signed)
  {tenant_id, domain, max_seats, tier, valid_until, features}
         ↓
IT Admin triển khai TeraRelay (1 binary, 1 command)
         ↓
IT Admin phân phát app đến nhân viên qua MDM hoặc App Store internal
         ↓
Nhân viên cài đặt app — app BẮT BUỘC xác thực License JWT trước khi hoạt động
         ↓
Không có license hợp lệ → app hiển thị màn hình "Liên hệ IT Admin"
```

### 2.2 Phân tầng Tổ chức

| Thành phần        | Vai trò                                               |
| ----------------- | ----------------------------------------------------- |
| **TeraChat Inc.** | Cấp license, duy trì binary, hỗ trợ kỹ thuật          |
| **IT Admin**      | Triển khai relay, quản lý thiết bị, phê duyệt plugins |
| **Nhân viên**     | Sử dụng trong phạm vi chính sách tổ chức              |
| **TeraRelay**     | Binary mù hoàn toàn — chỉ định tuyến ciphertext       |

Không có thành phần "người dùng công khai". Mọi identity đều thuộc về một tổ chức có license.

---

## 3. Nguyên lý Kiến trúc Bất biến

**1. Zero-Knowledge Server**
Máy chủ relay hoạt động như Blind Router — chỉ thấy `destination_device_id`, `blob_size`, và `timestamp`. Không bao giờ thấy plaintext, không bao giờ có khóa giải mã. Đây là thuộc tính kiến trúc, không phải cấu hình.

**2. Key Material không rời Chip**
Mọi private key sinh ra và tồn tại vĩnh viễn trong Secure Enclave (iOS/macOS), StrongBox (Android), hoặc TPM 2.0 (Desktop). Không có đường dẫn nào để export key ra plaintext.

**3. Offline-First Survival**
Hệ thống không phụ thuộc vào Internet. Khi mất kết nối, BLE 5.0 + Wi-Fi Direct tự động tạo mạng P2P sinh tồn. Nhắn tin, file transfer, và voice hoạt động trong phạm vi mesh.

**4. Zero-Trust theo Thiết kế**
Không tin tưởng bất kỳ thành phần nào — bao gồm cả TeraChat Inc. Mọi quyền truy cập đều được kiểm tra bởi OPA Policy Engine tại thiết bị, không chỉ tại server.

**5. License Entanglement**
License JWT được neo vào `DeviceIdentityKey` qua KDF — sai license = key sai = database thành rác. Không thể bypass bằng cách bẻ gãy license file.

---

## 4. Kiến trúc Kỹ thuật Tổng quan

```text
┌───────────────────────────────────────────────────────────────┐
│                     THIẾT BỊ DOANH NGHIỆP                     │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              RUST CORE (Shared Binary)                  │  │
│  │  MLS E2EE · CRDT DAG · BLE Mesh · Key Management       │  │
│  │  OPA Policy · WASM Sandbox · Offline Storage            │  │
│  └────────────────────────┬────────────────────────────────┘  │
│           IPC/FFI          │                                   │
│  ┌─────────────────────┐  │  ┌───────────────────────────┐    │
│  │  UI Layer           │  │  │  Secure Hardware           │    │
│  │  Flutter / Tauri    │◄─┘  │  Enclave/StrongBox/TPM    │    │
│  │  (Pure Renderer)    │     │  (Key Material — Never Out)│    │
│  └─────────────────────┘     └───────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
          │ TLS 1.3 + mTLS                    │ BLE/Wi-Fi Direct
          ▼                                   ▼
┌───────────────────────┐         ┌──────────────────────────┐
│  TERARELAY (On-Prem)  │         │  PEER DEVICES (Mesh)     │
│  Blind ciphertext     │         │  Store-and-Forward CRDT  │
│  routing only         │         │  P2P encrypted           │
│  License validation   │         └──────────────────────────┘
└───────────────────────┘
```

### Stack Kỹ thuật

| Layer          | Technology                      | Platform                |
| -------------- | ------------------------------- | ----------------------- |
| Core Logic     | Rust (shared binary)            | All platforms           |
| Mobile UI      | Flutter + Dart FFI              | iOS · Android · Huawei  |
| Desktop UI     | Tauri (Rust + WebView)          | macOS · Windows · Linux |
| Protocol       | MLS RFC 9420 + QUIC/gRPC/WSS    | All                     |
| Encryption     | AES-256-GCM + ML-KEM-768 (PQ)   | All                     |
| Storage        | SQLite WAL + SQLCipher          | All                     |
| Plugin Runtime | wasm3 (iOS) / wasmtime (others) | All                     |

---

## 5. Thành phần Sản phẩm

| Thành phần                     | Mô tả                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------- |
| **TeraRelay**                  | Single Rust binary, blind router, tự deploy 5 phút trên VPS $6-$48/tháng     |
| **TeraChat Client**            | App native: iOS, Android, Huawei HarmonyOS, macOS, Windows, Linux            |
| **Admin Console**              | Quản lý license, thiết bị, policy, audit — trên Desktop + Mobile (read-only) |
| **Enterprise Plugin Registry** | Kho plugins (.tapp) do IT Admin phê duyệt và triển khai cho tổ chức          |
| **TeraEdge** (optional)        | Mini-PC hardware để làm Super Node cố định tại văn phòng                     |

---

## 6. Phạm vi và Ngoài phạm vi

**Trong phạm vi:**

- Giao tiếp doanh nghiệp nội bộ (text, voice, video, file)
- Lưu trữ Zero-Knowledge (server không đọc được content)
- Survival mesh khi mất Internet
- Enterprise plugin ecosystem (workflow tích hợp)
- Cross-organization federation (mTLS, sealed sender)
- Compliance và audit cho regulated industries

**Ngoài phạm vi:**

- Tài khoản cá nhân / consumer accounts
- Nhắn tin ra ngoài tổ chức qua plaintext channel
- Lưu trữ plaintext trên bất kỳ server nào
- Tích hợp với nền tảng không tuân thủ zero-knowledge

---

## 7. Mô hình Triển khai

TeraRelay có thể chạy trên nhiều topology khác nhau tùy theo quy mô và yêu cầu bảo mật:

| Tier                  | Infrastructure        | Thời gian Setup | Use Case               |
| --------------------- | --------------------- | --------------- | ---------------------- |
| **Self-Hosted Cloud** | VPS (512MB–8GB RAM)   | 5–20 phút       | SME, startup           |
| **On-Premise**        | Server nội bộ         | 1–4 giờ         | Enterprise, healthcare |
| **Air-Gapped**        | Hardware offline      | Nửa ngày        | Gov, defense, banking  |
| **Hybrid**            | On-prem + cloud relay | 1 ngày          | Tập đoàn đa chi nhánh  |

---

## 8. Bản đồ Điều hướng Tài liệu

| Đối tượng                | Tài liệu                        | Nội dung                                              |
| ------------------------ | ------------------------------- | ----------------------------------------------------- |
| **Developer (Client)**   | `Feature_Spec.md` → TERA-FEAT   | IPC bridge, OS hooks, platform behavior, WASM runtime |
| **System Architect**     | `Core_Spec.md` → TERA-CORE      | MLS, CRDT, Mesh networking, relay infrastructure      |
| **Product Manager**      | `Function.md` → TERA-FUNC       | Capabilities, user flows, RBAC, enterprise features   |
| **UI/UX Designer**       | `Design.md` → TERA-DESIGN       | Glassmorphism system, animations, security state UI   |
| **Plugin Developer**     | `Web_Marketplace.md` → TERA-MKT | .tapp lifecycle, WASM sandbox, plugin registry        |
| **QA / SecEng**          | `TestMatrix.md` → TERA-TEST     | Chaos engineering, combined-failure scenarios         |
| **Investor / Executive** | `Executive_Summary.html`        | Investment thesis, market, financials                 |
| **Sales**                | `Pricing_Packages.html`         | Enterprise pricing, tiers, contracts                  |

---

_TeraChat — Chủ quyền dữ liệu doanh nghiệp, được bảo đảm bằng toán học._

_v0.4.0 · 2026-03-25 · Internal Reference_
