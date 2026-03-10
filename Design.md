# TeraChat ( Enterprise Sovereign Messenger ) – Design Specification
>
> **Phiên bản:** Alpha 1.0 | **Nền tảng:** Desktop 🖥️ / Laptop 💻 / Mobile 📱
> **Gửi tới:** Đội ngũ UX/UI Design

---

# PHẦN I – TRIẾT LÝ & HỆ THỐNG THIẾT KẾ

## 0. Triết lý Thiết kế

TeraChat là **Enterprise Sovereign Messenger** — không phải Slack bình thường.

| Câu hỏi | Câu trả lời |
|---|---|
| **Trông như thế nào?** | Glassmorphism. Enterprise. Tối giản nhưng dày thông tin. |
| **Cảm giác như thế nào?** | Nhanh. Đáng tin cậy. Bảo mật ngầm không bắt người dùng để ý. |
| **Mục tiêu người dùng?** | Nhân viên chính phủ, doanh nghiệp tài chính, tập đoàn nội bộ. |
| **Điều không được làm?** | Bubble chat kiểu WhatsApp. Màu nền mỗi người mỗi màu. UX game hóa thái quá. |

### Hai trạng thái hoạt động (bắt buộc phải phân biệt rõ về visual)

- **Online Mode** — Kết nối Server chuẩn: Nền sáng, blur trắng, accent `#24A1DE`.
- **Mesh Mode** — Offline P2P qua BLE/Wi-Fi Direct: Nền `#0F172A` dark navy, radar pulse trên logo, banner `"Mesh Active – N nodes connected"`.

---

## 1. Hệ thống Màu sắc

### Bảng màu chính

| Token | Giá trị | Dùng khi |
|---|---|---|
| `--primary` | `#24A1DE` | Accent, CTA, Active indicator |
| `--bg-online` | `#FFFFFF` | Background Online Mode |
| `--bg-mesh` | `#0F172A` | Background Mesh Mode |
| `--glass-light` | `rgba(255,255,255,0.08)` | Card, Panel nền |
| `--glass-dark` | `rgba(20,30,45,0.4)` | Dark glass container |
| `--border` | `rgba(255,255,255,0.12)` | Border toàn bộ |
| `--muted` | `#64748B` | Text phụ, timestamp |
| `--divider-online` | `#F1F5F9` | Divider Online |
| `--divider-mesh` | `#1E293B` | Divider Mesh |
| `--hover` | `+4% brightness` | Hover state |

---

## 2. Typography

**Font:** Inter / Outfit (Google Fonts)

| Role | Size | Weight |
|---|---|---|
| Heading H1 | 20px | SemiBold |
| Section Label | 13px | Medium |
| Username | 13px | Medium |
| Message Body | 14px | Regular, line-height 1.6 |
| Timestamp | 12px | Regular, muted |
| Badge / Tag | 10px | Uppercase |

---

## 3. Glassmorphism Enterprise Spec

### Layer System

```
Layer 1 → App Background (dark navy gradient hoặc white)
Layer 2 → Sidebar/Rail Glass      (blur: 16–18px)
Layer 3 → Work Area Glass         (blur: 12px)
Layer 4 → Floating Panels/Modals  (blur: 20px)
```

> Mỗi tầng phải có blur depth **khác nhau** để tạo chiều sâu thật sự (không flat).

### Online Mode

- Background: `#FFFFFF`
- Glass: blur 16px, white 70%
- Shadow rất nhẹ
- Accent: `#24A1DE`

### Mesh Mode

> ⚠️ **Adaptive UI Degradation (Chống ccan pin):** Khi kích hoạt Mesh Mode, Engine Glassmorphism PHẢI tự động tắt. Quy tắc bắt buộc: Khi biến `--mode: mesh` được set, toàn bộ `backdrop-filter`, `box-shadow`, và CSS `animation` vô điều kiện phải bị disable.

- **Background:** `#0F172A` solid (OLED Black — tắt pixel cưỡng bức, không GPU composite layer)
- **Glass:** `backdrop-filter: none` — thay bằng mã màu phẳng (Flat Dark) `rgba(255,255,255,0.06)` không blur
- **Text sáng:** `#E2E8F0`
- **Radar — Event-driven SVG** (không dùng CSS loop): Biểu tượng radar là SVG tĩnh, chỉ thay đổi opacity (`0.3 → 1.0 → 0.3`) khi Loo iRust Core dispatch tín hiệu `MESH_PACKET_RECEIVED`. Không có `setInterval` hay `animation: pulse infinite`.
- **Banner top:** `"Mesh Active – N nodes connected"` (cập nhật mỗi lần node join/leave, không animate liên tục)

**Transition:** `fade 0.1s` (rút ngắn từ 0.3s để giảm GPU frame render khi chuyển sang Mesh Mode)

---

## 4. Micro-Animations & Motion

| Event | Animation |
|---|---|
| Tab switch | Fade cross 0.15s |
| Theme switch (Online ↔ Mesh) | Fade 0.3s toàn màn hình |
| New message arrive | Slide-in từ dưới 0.15s |
| Pin .tapp to Rail | Slide-down 0.2s, fade-in |
| Panel open (Info, Smart Action) | Slide từ phải 0.25s |
| Hover icon (Rail) | Scale 1.05, highlight 5% — 0.1s |
| Mesh radar pulse | Event-driven SVG opacity change (Rust dispatch `MESH_PACKET_RECEIVED`) |
| File loading | BlurHash → fade-in 0.3s |
| Loading spinner | 60fps SVG spin |
| Toast notification | Slide từ top-right, auto dismiss 3s |

---

## 5. Interaction Logic chung

**Hover icon (Rail/Sidebar):**

- Background highlight 5%
- Scale 1.05 nhẹ

**Active:**

- Indicator 3px `#24A1DE` bên trái
- Icon fill accent

**Scroll Behavior:**

- Smooth scroll
- New message slide-in 0.15s
- Khi đang scroll lên → không auto kéo xuống
- Show `"New messages ↓"` indicator

---

# PHẦN II – BỐ CỤC & ĐIỀU HƯỚNG

## 6. Cấu trúc Bố cục Tổng thể

### 🖥️💻 Desktop / Laptop (≥ 960px)

```
┌──────────────────────────────────────────────────────────┐
│  [Left Rail 76px] │ [Panel 280–360px] │ [Main Area fill] │
└──────────────────────────────────────────────────────────┘
```

- **Left Rail** (76px cố định): Navigation chính — Glassmorphism, blur 16px.
- **Middle Panel**: Danh sách (Chats, Files, Notifications…).
- **Main Area**: Nội dung chính (Chat Frame, Dashboard, Tools).

> Panel có thể ẩn/hiện bằng `Cmd/Ctrl + \`.

### 📱 Mobile (< 960px)

```
┌───────────────────┐
│     Screen        │
│   (Full Width)    │
│                   │
│ [Bottom Tab Bar]  │
└───────────────────┘
```

- **Bottom Tab Bar** thay thế Left Rail.
- Chat List → Chat View: **Push Navigation** (trượt phải để back).
- Không có panel cố định — dùng **Bottom Sheet** cho context actions.

### Responsive Breakpoints

| Màn hình | Layout | Nav Pattern |
|---|---|---|
| Desktop ≥ 1440px | 3 cột (Rail + Panel + Main) | Left Rail 76px cố định |
| Laptop 960–1440px | 3 cột (có thể collapse panel) | Left Rail 76px, `Cmd+\` ẩn panel |
| Tablet 768–959px | 2 cột (Rail + Main, panel overlay) | Left Rail thu hẹp 60px |
| Mobile < 768px | 1 cột full screen | Bottom Tab Bar 5 tabs |

---

## 7. Left Rail – Navigation (Desktop/Laptop)

**Kích thước:** 76px cố định.

- Online: `rgba(255,255,255,0.7)`, border right 1px subtle.
- Mesh: `rgba(15,23,42,0.7)`, text sáng.

### Thứ tự icon (trên → dưới)

| # | Tab | Mô tả |
|---|---|---|
| 1 | **Logo** | Click → Home. Long press → Workspace switch. Mesh: radar pulse. |
| 2 | **Home** | Dashboard tổng quan. `Cmd+1` |
| 3 | **Chats** | Chat List + Chat View. `Cmd+2` |
| 4 | **Notifications** | Mentions, Approvals, Security Alerts. |
| 5 | **Files** | TeraVault file center. |
| 6 | **Tools (.tapp)** | Enterprise Launchpad. |
| 7 | *(Dynamic)* | Pinned .tapp apps (xuất hiện sau khi user pin). |
| 8 | **Settings** | Cuối cùng. |

**Pinned .tapp:**

- Animate slide-down khi pin, fade-in 0.2s.
- Có badge nếu có alert.
- Right-click → Unpin / App Settings / Permissions.

---

## 8. Bottom Tab Bar – Navigation (Mobile)

```
[Home] [Chats] [Notif] [Files] [Tools]
```

- Indicator: dot `#24A1DE` phía trên icon active.
- Icon + badge (không text label).
- Gesture: swipe left/right giữa các tab chính.

---

# PHẦN III – CÁC MÀN HÌNH CHI TIẾT

## 9. Home Dashboard

### Triết lý Home

> **Home = Operational Control Surface** — Không phải Activity Feed đơn thuần.

| So sánh | Slack | Telegram | TeraChat |
|---|---|---|---|
| Pinned nổi bật | ❌ | ✅ | ✅ Enterprise style |
| Zone status | ❌ | ❌ | ✅ |
| Network-aware | ❌ | ❌ | ✅ |
| Tools tích hợp sâu | ❌ | ❌ | ✅ |

### Layout Desktop/Laptop (2 cột — 35% / 65%)

```
┌──────────────────┬─────────────────────────────────────────┐
│  LEFT COLUMN     │              RIGHT COLUMN               │
│  (Pinned Chats + │  (Welcome + Overview + Activity + Tools)│
│   Departments)   │                                         │
└──────────────────┴─────────────────────────────────────────┘
```

### LEFT COLUMN — Pinned Channels

**📌 Pinned Channels** (tối đa 6, scroll nếu nhiều hơn):

```
[Icon]  Gov-Operations
        Last message preview
        [12 unread badge]
```

- Glass card mini, radius 12px.
- Drag để reorder.
- Hover: highlight 4%.
- Right-click → Pin/Unpin, Mute, Go to channel.
- Double-click → mở Split View.

**Hành vi ghim (Telegram logic):**

- Right-click channel → `"Pin to Home"` → xuất hiện trong Home > Pinned.
- Unpin → biến mất khỏi Home. Không ảnh hưởng sidebar.

**🏢 Department Groups** (bên dưới pinned):

```
Departments
  > Finance
  > Operations
  > Security
  > HR
```

Click → mở Chat View.

### RIGHT COLUMN — Dashboard

**Header:**

```
Welcome back, [Username]          [Zone Badge: Online ●]
[Workspace Name]                  [Encryption: E2EE Active]
```

**Section 1 — Operational Overview** (Grid 2×2, glass cards):

| Card | Nội dung |
|---|---|
| Active Channels | Số kênh đang hoạt động |
| Pending Approvals | Phê duyệt chờ xử lý + CTA |
| Online Members | Avatar stack |
| Security Alerts | Badge mức độ |

Card style: radius 16px, blur 12px, border subtle.

**Section 2 — Activity Feed** (Slack-style timeline):

```
14:02 · User A approved "Budget_Q2.pdf"
14:01 · New file uploaded in Finance
13:58 · Zone changed to Mesh
```

Timestamp nhỏ, không avatar to, hover highlight nhẹ.

**Section 3 — Quick Tools** (1 hàng icons):

[Smart Approval] [CRM] [POS] [HR]     [Open Full Tools →]

```

### Mesh Mode — Home

- Background chuyển dark navy.
- Radar icon ở header.
- Banner: `"Mesh Active – Local secure network connected"`.

### Layout Mobile

- Single column.
- Pinned Channels: horizontal scroll cards.
- Activity Feed + Quick Tools bên dưới.
- Empty state hero text 60px: *"Secure Communication Infrastructure for Critical Operations."*

---

## 10. Chats

### Layout Desktop/Laptop

```

| Left Rail | Chat List (360px) | Chat Frame (fill) | Info Panel (overlay) |

```

### Chat List Panel

- Search bar: `"Search chats…"`, glass input, radius 12px, focus glow `#24A1DE 30%`.
- Group chats theo Section: **Direct** / **Channels** / **Departments**.
- Mỗi row:

  ```

  [Avatar 36px] Channel Name              14:02
                Last message preview      [3 unread badge]

  ```

- Hover: highlight 3%, indicator trái nhẹ.
- Right-click: Pin to Home / Mute / Leave.

### Chat Header (56px)

Glass background blur 12–16px.

**Bên trái:**

- Channel name `16px SemiBold`
- Department tag badge
- `🔒 E2EE Active` icon

**Bên phải:**

- Search in conversation
- Call (nếu Zone 1)
- Screen share (Zone 1)
- Info icon (mở Info Panel)

**Mesh Mode:**

- Radar icon pulse
- Banner mỏng phía dưới header: `"Mesh Active – 12 nearby nodes connected"`

### Message List (Trọng tâm — KHÔNG BUBBLE)

```

[Avatar 28px]  Username          14:02
               Message nội dung đầy đủ chiều rộng
               [Attachment preview]
───────────────────────────────────────────────────

```

**Typography:**

- Username: 13px Medium
- Timestamp: 12px muted
- Message: 14px Regular, line-height 1.6

#### Khởi động Lạnh & Skeleton UI (Render khung xương cứng)

- 📱💻🖥️ **Hardcoded Skeleton UI:** Hiển thị tức thì (0ms - 50ms) khung xương mang phong cách Glassmorphism mà không cần chờ I/O từ cơ sở dữ liệu.
- 📱💻🖥️ **Pure Renderer Architecture:** Logic xử lý dữ liệu được tách biệt hoàn toàn khỏi tầng hiển thị (Native/DOM), giúp UI không bị block bởi quá trình khởi động hệ thống tĩnh của Rust Core.
- 📱 **Quy tắc Điều hướng Thị giác:** Layout Skeleton hardcode sẵn thanh Input và các khối tin nhắn dạng mờ (Blur) cố định để định hướng ánh nhìn của người dùng ngay khi app vừa mở.

#### Hiệu ứng Magic Reveal & Stubs (Staggered Native Reveal)

- 📱 **Staggered Slide-Up:** Animation trượt so le từ trên xuống được thực thi trực tiếp trên Native Thread (tác động thẳng vào Transform Y và Opacity), đảm bảo đạt 120fps mà không chịu nghẽn luồng từ JS Bridge.
- 📱💻🖥️ **Zero-Byte Blur-Hash Stubbing:** Trước khi tải ảnh gốc, UI lập tức render các "Zero-Byte Stubs" (<5KB JPEG E2EE chứa Hash Blur) tạo thành khối màu kính Glassmorphism mờ ảo.
- 📱 **Spring Physics:** Áp dụng hiệu ứng nảy nhẹ (Spring) mang tính vật lý cho mỗi tin nhắn khi xuất hiện, tăng cảm giác chân thực và không gian tương tác.

#### Glassmorphism State Update & Glow Effect (Hiệu ứng Thông minh)

- 📱💻🖥️ **Trạng thái `ai_ready`:** Cập nhật trạng thái hệ thống và giao diện UI thông qua luồng IPC siêu nhẹ để bật hiệu ứng Glow lóe sáng viền mượt mà mang phong cách kính khi AI rà quét (tìm kiếm thông minh) thành công 20 tin nhắn gần nhất, báo hiệu sẵn sàng xử lý siêu văn bản.

**Nhóm message** (cùng user < 5 phút):

```

Avatar  User Name   14:02
        Message 1
        Message 2
        Message 3

```

Không lặp avatar. Hiển thị 20–25 dòng / màn hình 13".

**Hover message:**

```

[React] [Reply] [Copy] [More…]

```

Inline actions — không floating button lố. Background highlight 3%.

**System messages:**

```

──────────── User X approved document ────────────

```

Center aligned, muted text, không avatar.

### Attachments

**Ảnh:**

- BlurHash placeholder → fade-in 0.3s khi load.
- Border subtle.
- Dynamic watermark nếu Zone 2 (Restricted).

**File card:**

```

📄 Contract_v2.pdf    2.4MB | 🔒 Encrypted
[Download]  [Preview]

```

Glass card, radius 8px.

### Message Input (64px min)

Glass container.

```

[+] [😊] [📎]   |  Type secure message…  |  [🎤] [➤]

```

- **Enter** = Send. **Shift+Enter** = New line.
- Disable Send nếu không có quyền (Zone DLP block).
- Loading spinner khi đang gửi.
- `"New messages ↓"` indicator khi scroll lên.

### Info Panel (Slide từ phải — 0.25s)

Click `ℹ` → slide từ phải.

Tabs: **Members** / **Files** / **Audit Log** / **Permissions** / **Zone Status**

### Layout Mobile

- Chat List: màn hình đầu tiên (full screen).
- Tap conversation → push sang Chat Frame (full screen).
- Header: Back trái + Channel name + Icons.
- Input bar cố định ở đáy, trên bàn phím khi mở.
- Info Panel → **Bottom Sheet** khi tap Info icon.

---

## 11. Notifications

### Filter bar

```

[All]  [Mentions]  [System]  [Approval]

```

### Notification row

```

[Icon type]  Title               14:02
             Short description

```

- **Approval:** CTA `[Review]` inline.
- **Security Alert:** badge đỏ, tap mở detail.
- **Audit Event:** muted, không CTA.

#### Trạng thái Skeleton khi đang giải mã an toàn từ NSE

- 📱💻 Khi Notification đến từ NSE nhưng Main App chưa kịp đồng bộ khóa mới (OOB Push Ratchet) hoặc **khi Circuit Breaker bị kích hoạt do payload quá lớn (chẳng hạn đợt Epoch Rotation cho group 50,000 người)**, UI **không** hiển thị ngay nội dung thực mà dùng một hàng Skeleton cố định:
  - Title dạng generic: `"🔒 Bạn có một tin nhắn mã hóa mới"`.
  - Subtitle hiển thị Blur/Skeleton bar (khối mờ 60–70% width), không lộ từ khóa hay nội dung nhạy cảm.
- 📱 Ngay khi người dùng chạm vào thông báo mở Main App (Foreground Mode) và Lõi Rust phân bổ RAM để giải mã xong, hàng Skeleton được thay thế bằng nội dung thật thông qua hiệu ứng fade 0.15s (Giao diện hiển thị bộ khung Skeleton Loading dạng Glassmorphism mờ đục trong 0.2s trước khi text xuất hiện). Nếu đồng bộ thất bại, Skeleton chuyển thành trạng thái lỗi an toàn `"Không thể giải mã — chạm để thử lại"`.

---

## 12. Files (TeraVault)

### Layout Desktop/Laptop

```

| Left Rail | File Sidebar (280px) | File Workspace (fill) |

```

### File Sidebar (Glass Panel)

Background: `rgba(255,255,255,0.08)`, blur 18px, border 1px `rgba(255,255,255,0.12)`, radius 20px.

**Header:**

```

Files
[ + Upload ]

```

Upload button: gradient nhẹ `#24A1DE → transparent`, icon arrow up, hover glow subtle.

**Filter Section:**

- All Files
- My Files
- Shared with Me
- Department Files
- Mesh Storage (nếu offline)

Active item: nền glass sáng hơn 4%, viền trái accent `#24A1DE` 3px.

**Quick Access (Pinned Files):**

```

[PDF icon] Budget_2026.pdf
           Finance Dept · Updated 2h ago

```

Hover: elevation nhẹ, icon action `⋯` bên phải.

### File Workspace

**Header:**

```

📁 Department / Finance     [Search files...]     [Sort ▼] [Filter]

```

**View Toggle:** Grid (default) / List.

**Grid View:**

```

┌──────────────┐
│   [Icon]     │
│ Budget.xlsx  │
│   12 MB      │
│ Updated 2h   │
└──────────────┘

```

Card: background `rgba(255,255,255,0.06)`, blur 12px, radius 18px. Hover: sáng hơn 6%.

File type color (subtle):

- PDF → đỏ subtle
- Excel → xanh lá
- Doc → xanh dương
- Image → tím

**List View:**

| Name | Owner | Department | Updated | Size | Security |
|---|---|---|---|---|---|
| Budget.pdf | Hoang | Finance | 2h ago | 2.4MB | 🔒 Encrypted |

Security column:

- 🔒 Encrypted
- 🌐 Cloud
- 📡 Mesh Local

Row hover: nền trắng 3%, border glow mỏng.

**Security Badge (góc phải mỗi file):**

```

[ENCRYPTED]  [CLASSIFIED]  [INTERNAL]  [PUBLIC]

```

Glass mini, blur 6px, text uppercase 10px.

**Smart Action Bar (khi click file):**

```

Preview / Share / Generate Approval / AI Summary / Download / Move to Mesh

```

Floating glass panel, shadow nhẹ, border glow `#24A1DE` mờ.

### Mesh Mode Behavior

Header banner: `"Mesh Mode Active – Files syncing locally"`

File icons:

- 📡 Local
- ☁ Sync Pending

Sync animation: subtle pulse.

#### Skeleton UI cho File được mở từ Notification khi nội dung còn đang giải mã

- 📱💻 Khi người dùng chạm vào Notification dẫn tới một file (PDF/Video) được bảo vệ E2EE, màn `Files`/Viewer phải hiển thị **khung xương an toàn** trong lúc Core Rust đang giải mã:
  - Khung preview file là một card Glassmorphism xám mờ, icon file dạng placeholder, kèm dòng text `"Đang giải mã an toàn..."`.
  - Thanh timeline video (nếu có) hiển thị dạng skeleton bar, không cho seek cho đến khi có đủ key/byte đầu tiên từ Native-to-Rust Media DataSource Bridge.
- 📱Ngay khi pipeline giải mã/streaming sẵn sàng, Skeleton fade-out 0.2s và thay bằng preview/video thực; nếu phát hiện key desync, Skeleton giữ nguyên kèm CTA nhỏ `"Thử đồng bộ lại"` thay vì crash hoặc để UI trắng.

### Layout Mobile

- File Sidebar → **Bottom Sheet** filter thay thế.
- Grid 2 cột.
- Tap file → Bottom Sheet với Smart Actions.

---

## 13. Tools (.tapp) — Enterprise Launchpad

### Desktop/Laptop

Click Tools icon → **Glass Modal lớn** trung tâm màn hình. Grid 3–4 cột:

```

[Smart Approval] [CRM] [POS] [HR]
[Internal App 1] [Internal App 2] ...

```

- Card radius 16px, blur 12px.
- Hover: glow nhẹ `#24A1DE 20%`.
- Mỗi `.tapp` chạy trong **WASM Sandbox** — hoàn toàn cô lập.
- Nút bị mờ/disable nếu phòng ban không được cấp quyền (OPA Policy).

### Mobile

- Tools → **Full screen Bottom Sheet** dạng 2 cột.
- `.tapp` khi mở → full screen modal, header tên App + nút Close.

### Pinned .tapp

- Right-click / long-press → `"Pin to Sidebar"`.
- Animate slide-down vào Rail / Tab bar (dynamic zone).
- Badge alert nếu app có notification.

---

## 14. Settings

| Section | Nội dung |
|---|---|
| **Account** | Profile, Avatar, Display name |
| **Security** | E2EE keys, Device list, Revoke sessions |
| **OPA Policy** | Xem chính sách DLP (read-only cho user) |
| **Zone Config** | Cấu hình Online / Mesh priority |
| **Storage** | Ring Buffer info, Offline storage quota |
| **Developer Mode** | Toggle (nếu được cấp quyền) |

---

## 15. Admin Console (Role-based — chỉ Admin thấy)

Entry point: Settings → `[Admin Console]` button.

### Tab Structure

| Tab | Chức năng |
|---|---|
| **User Management** | Invite Token, Revoke, Remote Wipe |
| **Key Management** | KMS Bootstrap, Master Key status, Epoch Rotation |
| **OPA Policies** | Tạo/sửa/xóa chính sách per-department |
| **Federation** | Invite Token liên tổ chức, trust registry |
| **Audit Log** | Timeline filter theo user/action/time |
| **Tools Registry** | Whitelist/blacklist `.tapp`, quản lý API Keys |
| **Infrastructure** | Node health, Cluster scaling wizard |

### Trải nghiệm Quản trị 1-Chạm (Wizard-driven UX)

#### Khởi tạo Cụm Trực quan (Cluster Setup Wizard)

1. **Pre-flight Check** — Scan phần cứng + network. Status badge ✅ / ❌. Nút `[Deploy Cluster]` chỉ sáng khi đủ điều kiện.
2. **Config Form** — Dropdown chọn provider (Vultr/DO), nhập 3 IP, drag-drop `id_rsa`. Không terminal.
3. **Deploy Progress Bar** — Phân nấc `WireGuard → Longhorn → K8s → Ready`. Text ngôn ngữ tự nhiên, không log terminal.
4. **Bootstrap QR** — QR code để Admin scan trên mobile → thiết lập kênh mTLS, tự đặt IP/Port.
5. **Day-2 Dashboard** — Cluster health `3/3 Online`, storage gauge, 1-click `[Zero-Downtime Update]`.

#### Mở rộng Cụm Không Gián Đoạn (Add Node Wizard)

- Bảng trượt tối giản: nhập 3 trường — IP Address, Node Label, SSH Key.
- Progress động: `Initializing → Joining → Ready`.
- Rollback tự động + thông báo tiếng người nếu Node thất bại.

#### Phản hồi Thời gian thực

- Biểu đồ động: WireGuard speed, Cluster capacity tăng gộp theo thời gian thực.
- K8s Scheduler tự cân bằng tải sang Node ít bận hơn.

---

# PHẦN IV – LUỒNG UX BẢO MẬT

## 16. Smart Approval Flow

```

Notification → [Review] → Detail Modal → Ghi chú lý do
→ [Biometric/PIN xác nhận] → Approved ✅ / Rejected ❌

```

- Bắt buộc **User Presence** (Touch ID / Face ID / PIN) trước khi ký.
- Processing spinner → Success / Error state.

---

## 17. Mesh Activation Flow
```

Detect mất kết nối
→ Toast: "Switching to Mesh Mode..."
→ UI fade sang Dark theme (0.3s)
→ Banner: Nút CTA chính (Màu Đỏ Cam cảnh báo): "Khởi động mạng Mesh để duy trì liên lạc".
→ Tiếp tục nhắn tin qua BLE/Wi-Fi Direct

- Offline message queue: `⏱ đang chờ` → `✓ đã đồng bộ`.
- 📱💻🖥️ Khi mất mạng (Offline Mode), UI hiển thị một Modal Overlap (Glassmorphism với nền Dark Navy `#0F172A`).
- 📱 iOS Màn hình áp dụng hiệu ứng `UIBlurEffectStyle.systemUltraThinMaterialDark`.
- 📱💻 Giao diện tự động vô hiệu hóa toàn bộ hiệu ứng Animation nặng để tiết kiệm pin cho thiết bị trong kịch bản thảm họa.

## 18. Thiết kế Luồng Self-Recovery (Glassmorphism UI)

- 💻🖥️ **Màn hình KMS Bootstrap:** Nền tối (Mesh Mode Dark Navy `#0F172A`). Ở giữa hiển thị biểu tượng YubiKey xoay 3D với viền sáng mờ. Thông báo: "Đang chờ xác thực phần cứng C-Level..."
- 💻🖥️ **FIDO2 Prompt:** Pop-up hệ thống nổi lên yêu cầu mã PIN hoặc vân tay trên YubiKey. Giao diện TeraChat bị khóa mờ (`UIBlurEffect`) hoàn toàn để tránh can thiệp click-jacking.
- 📱💻 **Cảnh báo TH2 (Tự phế truất):** Khi thực hiện "Revoke", nút bấm phải sử dụng màu Đỏ Cảnh Báo (`#EF4444`) và yêu cầu gõ lại chữ "REVOKE" để xác nhận, tránh thao tác nhầm trên thiết bị còn lại.

---

## 19. QR Enrollment (Onboarding nhân viên)

```

Admin: Tạo Invite Token → Hiển thị QR
Nhân viên: Mở TeraChat → Scan QR → Auto thiết lập E2EE + CA

```

---

## 19. File Approval Flow (Zone 2 Restricted)

```

Chọn file → [Generate Approval] → Điền lý do → [Gửi yêu cầu]
Manager nhận notification → [Review] → Approve / Reject
User nhận thông báo kết quả

```

---

# PHẦN VI – CÁC GIAO DIỆN MỞ RỘNG (SSO & LIÊN TỔ CHỨC)

## 22. Giao diện Đăng nhập (Enterprise SSO Login)

TeraChat tuyệt đối không dùng xác thực mật khẩu cục bộ. Mọi luồng Login đều qua Identity Broker (Keycloak/Dex) kết nối Azure AD, Google Workspace hoặc Okta.

### Layout Desktop/Mobile (Màn hình Welcome)

- **Background (Layer 1):** Dark navy gradient tĩnh, blur sâu tạo cảm giác chìm sâu (immerse).
- **Center Glass Card (Layer 4):** Khối thẻ xác thực lơ lửng giữa màn hình, radius 24px. Glass Dark (blur 20px, `rgba(20,30,45,0.6)`), viền phát sáng nhẹ `rgba(255,255,255,0.1)`.

```text
┌─────────────────────────────────────────────┐
│               [TeraChat Logo]               │
│        Secure Enterprise Communication      │
│                                             │
│  [ Input: Khóa/Workspace ID (terachat...) ] │
│                                             │
│  [ 🔑 Log in with Microsoft Azure AD     ]  │
│  [ 🛡️ Log in with Google Workspace       ]  │
│                                             │
│       ─ Hoặc xác thực phần cứng ─           │
│           [ YubiKey / Security Key ]        │
└─────────────────────────────────────────────┘
```

**UX & Motion Logic (Zero-Trust Core Initialization):**

- **Biometric-Bound Initialization (Bắt buộc Sinh trắc học):** Ngay sau khi Identity Broker (SSO) trả về thành công, Lõi Rust tạm dừng tiến trình và bật Native Prompt của OS (FaceID/TouchID).
  > *"TeraChat cần FaceID để khởi tạo Khóa phần cứng (Device_Key)"*
  > Nếu thất bại 3 lần, chuyển sang luồng Cryptographic PIN Fallback.
- **Cryptographic PIN Fallback UI:** Giao diện bàn phím số (Dialpad) 6 ô vuông cực kỳ tối giản (Glassmorphism trơn, không có bóng viền).
  - PIN được truyền thẳng qua **FFI Pointer** xuống Lõi Rust mà không lưu lại trên State của React Native.
  - Phía dưới hiển thị dòng chữ cảnh báo mờ: `Attempt X/5`.
- **Trải nghiệm Bảo mật Hủy dữ liệu (Ruthless Self-Destruct & Memory Zeroization):** Nếu nhập sai PIN lần thứ 5 hoặc nhận lệnh `Remote Wipe`.
  - 📱💻 **Remote Wipe & Secure Enclave Wipe:** Lệnh `Remote Wipe` thực thi xóa trắng Private Key trong chip bảo mật (Secure Enclave/StrongBox) thông qua tín hiệu từ SCIM/OIDC Listener.
  - 📱💻🖥️ **Memory Zeroization:** Cơ chế `ZeroizeOnDrop` (RAII) lập tức thực hiện ghi đè `0x00` lên toàn bộ vùng nhớ nhạy cảm trên RAM ngay khi lệnh hủy được kích hoạt.
  - 📱💻🖥️ **Crypto-Shredding:** Đánh dấu các sector dữ liệu là rác ngay lập tức sau khi xóa KEK.
  - 📱 **Ruthless Visualization:** Màn hình nháy đỏ rực (Red Flash blend mode: overlay, 0.2s). Hoạt cảnh Pixel Disintegration (Rã điểm ảnh) hoặc Glitch effect được đẩy trực tiếp xuống Native UI Thread để đảm bảo độ mượt 120fps trước khi app văng ra Loading Screen ban đầu (Trạng thái Factory Reset).
- **Tiến trình Khởi tạo mượt mà:** Nếu xác thực thành công (Biometrics/PIN), hiển thị thanh Progress bar (chiều cao 4px, màu `#24A1DE`) chạy fade-in trong `< 3 giây` với dòng text *"Đang thiết lập Lõi Mật Mã..."*.
- **Input Workspace ID:** Nền glass trắng mờ, outline chuyển `#24A1DE` cùng bóng đổ mờ khi focus/active.
- **Button Style:** Background sử dụng màu thương hiệu của SSO (Azure Blue/Google Gray) nhưng bắt buộc blend theo Layer Glass nhẹ để không phá vỡ tính nguyên khối cấu trúc UI tổng thể.

---

## 23. Giao diện Thiết lập Chi nhánh (Cross-Cluster Federation Handshake)

Luồng kết nối HQ và Chi nhánh được định vị tại **Admin Console > Federation**. Mục tiêu UX: Biến một luồng kết nối mật mã mTLS phức tạp thành trải nghiệm "Click & Connect" trực quan.

### Ở phía Tổng công ty (HQ Admin)

1. **CTA Button:** Nút `[ + Generate Federation Invite ]` nằm góc phải trên (Primary `#24A1DE`).
2. **Setup Modal (Slide từ trung tâm):**
   - Tên Chi nhánh: Khung Input field thường.
   - Quyền hạn OPA: Dropdown menu bo góc, tích hợp icon trạng thái (Vd: `👁️ Chỉ Reply`, `💬 Nhắn tin`).
   - Thời hạn Token: Slider kéo thả linh hoạt `1h — 24h` dán nhãn màu.
3. **Kết quả (Success State):** Sinh JWT Token khổng lồ để mời Chi nhánh.
   - Modal chia 2 cột: Cột trái hiện mã QR Scan độ tương phản cao (radius 16px). Cột phải đính hộp JWT Hash có thể scroll dọc kèm nút `[ Copy Token ]` + icon clipboard.

### Ở phía Chi nhánh (Branch Admin)

1. Mở Admin Console > Federation. Click `[ Join Federation Network ]`.
2. **Modal Nhập Token:** Khung Paste lớn chiếm 50% modal. Ngay khi paste, **Lõi Rust (WASM)** phân tích realtime (<50ms) và load ra thẻ Info Card xác nhận tin cậy:
   > ⚠️ **Bảo mật:** Bạn đang yêu cầu kết nối mTLS với máy chủ **[Tên HQ]**. Trạng thái chứng chỉ: *Hợp lệ*.
3. **Animation `[ Confirm & Handshake ]`:** Giữ nguyên hiệu ứng Loading Spinner tại nút trong 1-2s. Sau khi Handshake xong, xuất hiện màn hình pháo hoa mini tinh tế hoặc tick `✅ Connected` sang mảng màu xanh Success tươi sáng.

---

## 24. Giao diện Ép/Thêm Member (Directory Sync & Invites)

Thiết kế giao diện cho luồng đồng bộ nhân sự lớn từ Azure AD/HR xuống, thay vì mời thủ công rủi ro. Thao tác tại **Admin Console > User Management**.

### Tab 1: Directory Sync (SCIM 2.0 Tự động)

**Dashboard Control (Dải Ribbon trên cùng):**

```text
[Trạng thái SCIM 2.0: 🟢 ACTIVE]   |   Lần đồng bộ: 2 phút trước  |  [Sync Now] [Config Rules]
```

- **Status Badge:** `🟢 Active (Xanh lá)`, `🟡 Warning (Vàng)`, `🔴 Error (Đỏ)`. Thêm hiệu ứng pulse nhấp nháy vào dấu chấm `🟢`.

**Data Grid (Danh sách User dạng List View Glass):**

| Username | Department | Sync Source | Tình trạng Khóa (E2EE) | Action |
|---|---|---|---|---|
| Nguyen Van A | Finance | Azure AD | 🟢 Provisioned | `[Revoke]` |
| Tran Thi B | Sales | Azure AD | 🟡 Pending Login | `[Resend]` |

**UX Logic (Offboarding Không Chạm):**

- Khi nhân sự nghỉ việc trên hệ thống mẹ (IdP), hàng dữ liệu của nhân sự lập tức **đổi màu đỏ nhạt (Red Glass, opacity 10%)** và nhãn Auth đổi thành `🔒 Revoked`.
- Các nút Action biến mất hoặc bị disable (mờ đi) kèm tooltip rõ ràng: *"Managed by IdP. Khóa thiết bị đã bị hủy."*

### Tab 2: Manual / Guest Invites

Dành cho nhà thầu hoặc đối tác outsource tạm thời.

1. Click `[ + Generate Invite Token ]`.
2. **Cấu hình (Modal):** Nhập Tên cá nhân, Dropdown chọn Role (Guest, Contractor), Khung Box nhập Thời gian (12 giờ, 24 giờ).
3. **Màn hình Trả ra (Output Modal):**
   - Mã QR xuất hiện trung tâm khổng lồ. (Lưu ý: Card Glass chứa QR cần lót nền trắng phía dưới để Camera quét được).
   - Đi kèm nút Copy URL bảo mật.
4. **End-user Onboarding (Người nhận trên Mobile):**
   - Trên màn hình Mobile của đối tác hiện nút Scan cực lớn `[ 📷 Scan QR to Join ]`.
   - UI bật khung ngắm (Viewfinder blur) bắt viền lấy nét QR siêu nhanh.
   - Khi bắt được QR -> Hiệu ứng màn hình mở khóa (Unlock animation chớp nhoáng), tự động thiết lập chứng chỉ Certificate và thả rơi user thẳng vào Chat Room mà không hỏi mật khẩu.

## 25. Giao diện Đăng nhập Ngầm & Phân quyền HR (Magic Deep-Link SSO)

Bài toán mâu thuẫn giữa Bảo mật cao (Zero-Trust + SSO) và Trải nghiệm người mới (Frictionless Onboarding) được giải quyết qua luồng **Delegated Provisioning kết hợp Magic Deep-Link SSO**.

### Phần 1: Phân quyền Mời (Delegation via OPA)

Super Admin sẽ không đi mời từng người, mà **ủy quyền (Delegate) cho bộ phận HR** thông qua OPA Engine mà không làm hỏng tính toàn vẹn hệ thống.

1. **Ủy quyền:** Sếp tạo nhóm `HR_Department` trong Admin Console.
2. **Tiêm luật OPA:** Gán Policy đặc biệt để Lõi Rust kiểm tra nội bộ:
   `allow if user.group == "HR_Department" and action == "generate_invite_token"`
3. **UX hiển thị:** Chỉ những account thuộc `HR_Department` mới thấy xuất hiện nút `[ + Mời nhân viên ]` trên giao diện.

### Phần 2: Workflow 1-Tap Magic SSO

Luồng này loại bỏ hoàn toàn giao diện gõ email/mật khẩu thủ công thông qua 3 bước chớp nhoáng:

1. **HR Phát hành Lời mời:**
   - HR nhập email công ty của nhân viên mới (VD: `nhanvien@congty.com`).
   - Lõi Rust sinh `Invite_Token` (Signed JWT) hạn 24h và tự động gửi một Email chứa nút **"Tham gia TeraChat"**.

2. **Người dùng Chạm 1-Tap (Magic Deep-Link):**
   - Nhân viên bấm nút từ Email (app Gmail/Outlook trên điện thoại).
   - Lớp OS (iOS/Android) sẽ không mở trình duyệt mà kích hoạt **Universal Link/App Link** truyền thẳng URL: `https://join.terachat.com/invite?token=abc&hint=nhanvien@congty.com` vào app TeraChat.

3. **Đăng nhập Ngầm (Zero-Click SSO - Dưới 0.5s):**
   - Thay vì hiện màn hình đăng nhập 2 nút (Azure/Google), Lõi Rust chộp lấy `hint=nhanvien@congty.com` và kích hoạt luồng OIDC (PKCE).
   - Ép gửi tham số `prompt=none & login_hint=email`. Nhờ việc người dùng đang mở app Mail nội bộ, máy điện thoại **đã có sẵn Session SSO**.
   - Hệ thống tự động xác thực ngầm, trình duyệt hệ thống bật lên chớp nhoáng rồi tắt, sau đó Lõi Rust sinh khóa E2EE (`Device_Key`) thả thẳng người dùng vào nhóm Chat.

> **TỔNG KẾT 4 KỸ THUẬT LÕI ĐƯỢC ÁP DỤNG:**
>
> 1. **Deferred Deep Linking:** Ghi nhớ URL lời mời kể cả khi người dùng phải bay qua App Store tải App lần đầu.
> 2. **OIDC `login_hint` & `prompt=none`:** Kỹ thuật ép SSO không được hiện màn hình chọn Account màn lấy luôn Session hiện tại.
> 3. **Smart Routing OPA:** Quyền sinh JWT Pre-approved được chốt chặt ở lõi hệ thống.
> 4. **AppAuth (PKCE):** Giao thức bảo mật bắt buộc để nhận Token trên thiết bị di động không cần Client Secret.

---

# PHẦN VII – ACCESSIBILITY & CHECKLIST

## 26. Accessibility

- Minimum contrast **4.5:1** cho text chính.
- Keyboard navigable: Tab order `Rail → Panel → Main`.
- Tất cả icon phải có `aria-label` hoặc tooltip.
- Focus ring: `outline 2px #24A1DE, offset 2px`.
- Screen reader support cho alerts và security status badges.

---

## 27. Checklist cho Designer

- [ ] Thiết kế Online Mode và Mesh Mode cho **từng màn hình**.
- [ ] Component Library: Button, Input, Card (Glass), Badge, Toast, Modal, Bottom Sheet.
- [ ] Icon set **monochrome** (không màu mè, không multicolor).
- [ ] Responsive breakpoints: Mobile / Tablet / Laptop / Desktop.
- [ ] Admin Console screens (tách biệt rõ với UI giao diện tương tác User).
- [ ] Empty states (màn hình hero khi chưa có dữ liệu).
- [ ] Error states (Cảnh báo mất kết nối, Cấm quyền, Lỗi đồng bộ SCIM).
- [ ] **Onboarding flow 1:** Luồng Enterprise SSO Login truyền thống (Hiệu ứng Lõi Zero-Trust).
- [ ] Máy Quét Thuật toán **Biometric-bound Key Generation** (FaceID/TouchID Prompt UI).
- [ ] **Cryptographic PIN Fallback Dialpad** (Bàn phím FFI 6 số siêu tối giản, không track state).
- [ ] Hoạt cảnh **Ruthless Self-Destruct** (Màn hình nháy đỏ + Shredding Effect 1s).
- [ ] **Onboarding flow 2:** Luồng Quét QR Enroll nội bộ.
- [ ] **Onboarding flow 3:** Luồng 1-Tap Magic Deep-Link SSO cho nhân sự mới (1-chú chạm từ Email, bypass Login).
- [ ] Smart Approval biometric prompt screen (Modal phê duyệt sinh trắc học).
- [ ] Cluster Setup Wizard (Admin — Desktop only).
- [ ] **Cross-Cluster Federation Handshake** (Modal sinh mời + Giao diện Paste Token).
- [ ] **User Management & UI Tự động Đồng bộ SCIM 2.0 / Phân quyền HR**.
- [ ] Indicator **AI Privacy Shield** (Icon khiên che chắn dữ liệu khi bật tính năng AI Blind Inference).

# PHẦN VIII – CROSS-PLATFORM ARCHITECTURE

## 28.   Tầng UI chỉ đóng vai trò là "Pure Renderer" (Thợ vẽ thuần túy) – tước bỏ toàn bộ logic và chỉ hiển thị những thay đổi trạng thái (StateChanged) do Core báo về. Việc cấm tuyệt đối port Crypto hay Business Logic lên luồng JS/Dart là bắt buộc để tránh rò rỉ bộ nhớ và đảm bảo nhất quán mật mã trên cả 5 nền tảng

Dưới đây là các ngôn ngữ và framework được sử dụng để đồng bộ đa nền tảng:

1. Phân hệ Desktop / Laptop (Windows, macOS, Linux)

Framework: Hệ thống sử dụng Tauri để xây dựng giao diện.

Giao tiếp (IPC Bridge): Tách biệt Control Plane và Data Plane. Giao tiếp với Lõi Rust qua SharedArrayBuffer và Protobuf.

Hiệu năng: Cơ chế Zero-Copy Flow cho phép thông lượng truyền tải qua RAM vật lý đạt ngưỡng ~500MB/s mà không gây nghẽn cổ chai IPC.

1. Phân hệ Mobile (iOS, Android)

Frameworks: Sử dụng kết hợp React Native và Flutter.

Tích hợp iOS: Áp dụng cổng React Native JSI bọc con trỏ C++ Shared Memory (std::unique_ptr) đâm thẳng vào luồng nhận của Rust FFI, bỏ qua WebView Bridge truyền thống.

Tích hợp Android: Áp dụng giao diện Dart FFI TypedData thực thi tín hiệu Zero-Copy nạp thẳng sang kiến trúc C ABI tĩnh.

Hiệu năng: Cả hai nền tảng Mobile đều đạt thông lượng (throughput) ~400MB/s khi giao tiếp giữa UI và Lõi Rust.
