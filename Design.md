# Design.md — TeraChat Alpha v0.3.0

> **Status:** `ACTIVE — Design Reference`
> **Audience:** UX/UI Designer · Frontend Engineer · Product Manager
> **Scope:** Glassmorphism Design System, Component Library, Screen Flows, Animation Specs, State Machine Visual Mapping
> **Platform:** Desktop 🖥️ · Laptop 💻 · Mobile 📱
> **Last Updated:** 2026-03-11
> **Depends On:** `Feature_Spec.md` (IPC signals that trigger UI state changes), `Function.md` (user flows)
> **Consumed By:** React Native / Tauri frontend implementation

---

## CHANGELOG

| Version | Date | Change Summary |
| ------- | ---------- | ---------------------------------------------------------------------------- |
| v0.3.5 | 2026-03-13 | Add §37 Adaptive Glassmorphism State Machine & Survival HUD |
| v0.3.0 | 2026-03-11 | Add §30–36: Memory pressure feedback UI; Byzantine fault visual indicators; Crypto-Shred animation spec |
| v0.2.9 | 2026-03-05 | Add §28 Ruthless Self-Destruct Visualization; §29 Memory Zeroization overlay spec |
| v0.2.8 | 2026-03-04 | Add §25 Magnetic Collapse animation; §26 FCP Red Border overlay; §27 Hazard-Stripe sealed session view |

---

## DESIGN CONTRACT: Non-Negotiable UI Rules

> **Vi phạm bất kỳ ràng buộc nào dưới đây → thiết kế bị reject, không review merge.**

- [ ] **Mesh Mode visual state** phải khác biệt rõ ràng với Online Mode: dark navy `#0F172A`, radar pulse, banner "Mesh Active". Không được merge UI trông giống nhau.
- [ ] **Glassmorphism** áp dụng nhất quán: backdrop blur `20px`, `rgba(255,255,255,0.08)` bg, `1px` stroke `rgba(255,255,255,0.12)`.
- [ ] **Typography:** Chỉ dùng Inter (body), JetBrains Mono (code/mono elements). Không dùng system font.
- [ ] **Accent color:** `#24A1DE` (Online) / `#F59E0B` (Warning) / `#EF4444` (Danger). Không dùng màu tự ý.
- [ ] **Không có bubble chat kiểu WhatsApp.** Layout phải theo Data Density model — thông tin dày đặc, compact.
- [ ] Mọi security event (Self-Destruct, Shatter, Crypto-Shred) **phải** có animation spec trước khi implement.
- [ ] Mọi UI state change do Lõi Rust trigger **phải** được document trong section tương ứng với IPC signal reference.

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
  - **QUIC 0-RTT Status HUD:** Góc phải dưới màn hình hiển thị HUD siêu nhỏ (frost glass blur, `backdrop-filter: blur(8px)`, `border-radius: 8px`, `opacity: 0.85`) với text `QUIC: 0-RTT ✓` màu `#24A1DE`, font `Inter 10px SemiBold`. HUD chỉ hiển thị 3 giây sau khi kết nối/tái kết nối thành công rồi fade out (`transition: opacity 0.5s ease`). Không hiện khi ở chế độ ổn định liên tục > 30s. Không block interaction.
- **Mesh Mode** — Offline P2P qua BLE/Wi-Fi Direct: Nền `#0F172A` dark navy, radar pulse trên logo, banner `"Mesh Active – N nodes connected"`.
  - **Dual-Beam Radar Pulse (Hybrid Mesh Bonding):** Khi Hybrid Mesh Bonding kích hoạt, Radar Pulse phát ra hai tia song song thay vì một vòng sóng đơn màu xám:
    - **Tia Cyan `#00D4FF` — Control Plane (BLE):** Xung ngắn (~1.5s period), biên độ nhỏ (r: 16→32px), `opacity: 0.9→0`. Dispatch bởi Lõi Rust event `MESH_BLE_CONTROL_SENT`.
    - **Tia Amber `#F59E0B` — Data Plane (AWDL/Wi-Fi Direct):** Xung dài và rộng (~3s period), biên độ lớn (r: 16→64px), `opacity: 0.7→0`. Dispatch bởi event `MESH_DATA_PLANE_ACTIVE`. Tia chỉ xuất hiện khi có Data Plane active (đang transfer file/DB).
    - Cả hai tia là **Event-driven SVG** — không dùng CSS animation loop. GPU cost = 0 khi không có packet.



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
- 📱 **State: "Missing Local Network Permission" (iOS 14+):** Khi quyền Local Network bị từ chối, banner chuyển sang màu Amber Warning `#F59E0B`: *"⚠️ Thiếu quyền Mạng Cục bộ — Mesh chỉ hoạt động qua BLE. Vào Cài đặt → TeraChat để cấp quyền đầy đủ."* Nút CTA "Mở Cài đặt" deep-link thẳng đến `UIApplication.openSettingsURLString`. Icon Radar chuyển sang pulse chậm (opacity: 0.2 → 0.5) thay vì full-active.
- 📱💻 **State: "Warming up Neural Engine...":** Khi người dùng mở tính năng AI (Smart Summarize / DLP Scan) lần đầu sau khi khởi động app, hiển thị inline progress bar nhỏ bên dưới Input Box: *"⚙️ Đang khởi động Neural Engine..."* với spinner nhỏ 16px. Biến mất sau khi CoreML/NNAPI hoàn thành pre-warm. Không block UI, người dùng vẫn gõ được bình thường.
- `📱` **Mesh Mode Offline Constraint & DAG Fragmentation Prevention:** Nếu thiết bị đang ở trong Mesh Mode không có tín hiệu mạng chạm tới VPS, giao diện tự động vô hiệu hóa các nút chỉnh sửa. Trạng thái UI lập tức chuyển sang "Read-Only (Offline)" để bảo đảm không xảy ra phân mảnh DAG diện rộng.

**Transition:** `fade 0.1s` (rút ngắn từ 0.3s để giảm GPU frame render khi chuyển sang Mesh Mode)

#### Re-sync Adaptive UI Degradation & Skeleton Fallback — Gián đoạn Hiển thị trong Re-sync

> **Bài toán:** Quá trình Deterministic State Reconciliation (kéo Delta-State Gap từ server) kéo dài 2-10 giây tùy kích thước gap. Nếu UI block chờ — trải nghiệm người dùng bị phá vỡ hoàn toàn.

- 📱 **Micro-UI Bridge Integration (Online Mode):** Trong toàn bộ thời gian Re-sync, UI bóc tách logic hiển thị trực tiếp từ `.tapp` qua Micro-UI Bridge, đảm bảo trạng thái hiển thị luôn đồng nhất với logic nghiệp vụ mới nhất mà không cần các màn hình dự phòng tĩnh.
- 📱 **Event-driven SVG Radar Pulse (Mesh Mode):** Nếu Re-sync xảy ra trong Mesh Mode (không có Internet), biểu tượng SVG Radar Pulse được kích hoạt theo model Event-driven: opacity thay đổi (`0.3 → 1.0`) mỗi khi Lõi Rust dispatch tín hiệu `MESH_CHUNK_RECEIVED`.
- 📱 **Sub-300ms Cryptographic State Label:** Phía dưới thanh trạng thái, một label nhỏ cập nhật liên tục: *"⚙️ Verifying Cryptographic State... [Merkle Chunk N/M]"*. Label chỉ cập nhật text content (`innerText`), không re-render DOM.
- 📱 **Dynamic Execution iOS — Background Thread Overflow Trigger:** Tự động delegate các tác vụ nặng sang Main Thread queue ngay khi user mở app nếu phát hiện payload TreeKEM/Epoch vượt quá ngưỡng xử lý an toàn của Background Thread. UI duy trì tính phản hồi cao thông qua Micro-UI Bridge.

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

### Giao diện Cấu hình Chính sách (Glassmorphism Policy Configurator)
- `📱💻` **Glassmorphism UI Policy Configurator:** UI hiển thị một Modal mờ tuyệt đối (Background Blur) khi tác giả định nghĩa Policy_Packet. Cho phép thiết lập Access Control List (ACL) linh hoạt, kéo thả mượt mà để phân bổ quyền Editor, Commenter, Viewer.

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

### Skeleton Row (Trạng thái đang Giải mã từ NSE)

```

[Lock Icon]  ███████████ (Pulse) 14:02
             Đang giải mã an toàn...

```

- **Approval:** CTA `[Review]` inline.
- **Security Alert:** badge đỏ, tap mở detail.
- **Audit Event:** muted, không CTA.

#### Trạng thái Skeleton khi đang giải mã an toàn từ NSE

- 📱💻 Khi Notification đến từ NSE nhưng Main App chưa kịp đồng bộ khóa mới (OOB Push Ratchet) hoặc **khi Circuit Breaker bị kích hoạt do payload quá lớn (chẳng hạn đợt Epoch Rotation cho group 50,000 người)**, UI **không** hiển thị ngay nội dung thực mà dùng một hàng Skeleton cố định:
  - Title dạng generic: `"🔒 Bạn có một tin nhắn mã hóa mới"`.
  - Subtitle hiển thị Blur/Skeleton bar (khối mờ 60–70% width), không lộ từ khóa hay nội dung nhạy cảm.
- 📱 Ngay khi người dùng chạm vào thông báo mở Main App (Foreground Mode) và Lõi Rust phân bổ RAM để giải mã xong (quá trình Atomic Drain tốn chưa tới 15ms), hàng Skeleton được thay thế bằng nội dung thật thông qua hiệu ứng fade 0.15s (Giao diện hiển thị bộ khung Skeleton Loading dạng Glassmorphism mờ đục trong 0.2s che phủ độ trễ này mượt mà). Nếu đồng bộ thất bại, Skeleton chuyển thành trạng thái lỗi an toàn `"Không thể giải mã — chạm để thử lại"`.

---

### Tương tác nhóm (Conflict Resolution)

- 💻 **Git-Diff Glassmorphism Pop-ups:** Khi ấn vào một Shadow Node, UI hiển thị modal Glassmorphism (nền mờ `#0F172A`) với giao diện split-view hoặc inline-diff (Màu xanh cho dòng thêm mới, Đỏ gạch ngang cho dòng xóa).
- 📱 **Smart Approval Biometric Prompt:** Đối với các đề xuất thay đổi lớn (sửa Smart Contract, thay đổi Policy mạng), UI yêu cầu xác thực Face ID/Touch ID sinh trắc học trước khi cấp phép hệ thống ký Ed25519.
- 🖥️💻📱 **Bulk Resolution UI (Giao diện Xử lý Hàng loạt):** Trong Pop-up quản lý xung đột, thay vì từng nút duyệt lẻ tẻ, hiển thị danh sách dạng Bảng (Table List) với các Checkboxes cho phép Author tick chọn nhiều nhánh cùng lúc.
- 🖥️💻 **Action Bar Glassmorphism:** Khi Author tick chọn nhiều nhánh, một thanh công cụ (Floating Action Bar) nổi lên với hiệu ứng Heavy Background Blur, cung cấp các nút: **Merge Selected** (Gộp các mục đã chọn), **Reject Selected** (Xóa), **Reject All**.
- 📱 **Mesh Mode Disablement:** Khi ứng dụng chuyển sang nền Dark Navy (Mesh Mode), toàn bộ các nút "Đề xuất sửa" (Propose) bị làm mờ (Greyed Out) kèm theo tooltip: *"Tính năng cộng tác nhánh tạm khóa khi không có kết nối Server"*.

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

#### Token Auth Failure — Static Noise/Glitch Screen (Video Stream Security)

> **Trigger:** Khi Video Stream nhận phản hồi `UNAUTHORIZED_SCHEME_ACCESS` từ Lõi Rust (Token OTP hết hạn, sai PID, hoặc bị hijack bởi app lạ trên cùng máy).

- 📱💻🖥️ **Không được crash:** UI tuyệt đối không crash hay hiển thị màn hình trắng/đen khi token stream xác thực thất bại. Thay vào đó, Video Player chuyển sang trạng thái **Static Noise/Glitch Screen**: hiệu ứng nhiễu hạt (noise grain) CSS filter `contrast(200%) brightness(0.3) saturate(0)`, animation nhấp nháy 4Hz trong 0.5 giây.
- 📱💻🖥️ **Inline Alert (không modal):** Bên dưới video frame, xuất hiện inline banner với nội dung: *"🔐 Kết nối luồng an toàn bị gián đoạn. Nhấn để thử lại."* — màu `#EF4444` (Red-500), icon shield-slash, không block thao tác khác trên UI.
- 📱💻🖥️ **Auto-Retry:** Nếu user không nhấn sau 5 giây, Lõi Rust tự động request token mới và thử lại stream (tối đa 3 lần). Nếu vẫn fail sau 3 lần → hiển thị alert cứng: *"Phiên stream đã hết hạn. Vui lòng mở lại file."*
- 📱💻🖥️ **Security Log Toast (DevMode only):** Trong Developer Mode, thêm toast nhỏ ở góc phải dưới: *"Security event: SCHEME_HIJACK_ATTEMPT detected from PID [xxxx]"* — hỗ trợ DevOps trace incident nhanh.



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

#### Visual Threat Intelligence & Asynchronous Progress Rendering (ISO 27001 A.8.2.2)

- 📱 **iOS Hazard-Stripe Red/Orange Toast Notification:** Khi Lõi Rust phát hiện OS Restriction (Background Execution bị OS cắt, Jetsam sắp kích hoạt, hoặc BLE bị throttle), UI hiển thị Toast mỏng 32px phía trên thanh Input với sọc cảnh báo màu đỏ cam (`#EF4444` / `#F59E0B`) — cung cấp Visual Threat Intelligence tức thời, không modal, không block thao tác.
- 📱 **Independent Main-Thread 1px/2px ProgressBar Rendering:** Thanh tiến trình DAG Sync (1px khi đang tải nhẹ, 2px khi đang tải nặng) được render hoàn toàn độc lập trên Main-Thread Native — không phụ thuộc JS Bridge, đảm bảo ProgressBar không bao giờ bị đóng băng kể cả khi Data Plane đang bận tải DAG lớn.


#### Large Transfer UI — Mesh Mode (Wi-Fi Direct 10GB, Không qua Server)

> **Trigger:** Khi 2 thiết bị phát hiện cùng LAN/Wi-Fi Direct range và file cần transfer > 100MB, hệ thống tự động trigger "Mesh Large Transfer Mode" — bypass hoàn toàn VPS/Cloud.

- 📱💻🖥️ **Background Color:** Nền `#0F172A` (Dark Navy — Mesh Mode). Toàn bộ Glassmorphism effect (`backdrop-filter`, `box-shadow`) **TẮT** để tiết kiệm GPU/CPU cho băng thông tối đa.
- 📱💻🖥️ **Transfer Card — Center Stage:**

  ```
  ┌─────────────────────────────────────────┐
  │  📡 Mesh Transfer — Không qua Cloud      │
  │  budget_2025.mp4 → Nguyen Van A          │
  │  ████████████████░░░░  80% — 8.0/10GB    │
  │  ⚡ 950 MB/s  |  ETA: 00:02:13            │
  │  [ Hủy ]                                  │
  └─────────────────────────────────────────┘
  ```

  - Border: `1px rgba(99,102,241,0.4)` (Indigo tím nhẹ — màu "secure local link").
  - Progress bar: gradient `#6366F1 → #22D3EE` (Indigo → Cyan), animate left-to-right.
  - Speed badge: `#22C55E` (Green) khi speed > 100MB/s, `#F59E0B` (Amber) khi < 100MB/s.
- 📱💻🖥️ **Radar Pulse Animation:** Biểu tượng SVG Radar (như Mesh Mode) nhấp nháy `opacity: 0.4 → 1.0` mỗi khi Lõi Rust dispatch event `MESH_CHUNK_SENT` — event-driven, không CSS loop.
- 📱💻🖥️ **Security Micro-badge:** Góc phải card hiển thị `🔒 E2EE Mesh — Direct Link` badge màu `rgba(34,197,94,0.15)` nền xanh mờ, nhắc nhở user file đi thẳng P2P, không qua bất kỳ server nào.
- 📱💻🖥️ **Completion Toast:** Khi transfer xong → Toast 3 giây: *"✅ budget_2025.mp4 — Đã truyền qua Mesh an toàn. Tốc độ trung bình: 870 MB/s. Băng thông Cloud tiết kiệm: 10GB."*
- 💻🖥️ **Fallback Trigger:** Nếu Wi-Fi Direct không khả dụng (VD: iOS background) → tự động chuyển sang S3 Multipart Upload qua NSURLSession Background Transfer, header banner đổi thành: `"Uploading via Secure Cloud — Mesh unavailable"`.

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

## 37. Adaptive Glassmorphism State Machine & Survival HUD

> **Giải pháp:** Cung cấp phản hồi thị giác ngay lập tức khi hệ thống thay đổi trạng thái triển khai hoặc gặp sự cố server.

- 🖥️ 💻 **Admin Setup Wizard (Light Mode Glassmorphism):** Giao diện thiết lập ban đầu sử dụng phong cách Glassmorphism sáng màu, tập trung vào tính hướng dẫn cao để Admin dễ dàng vượt qua các bước cấu hình VPS.
- 📱 💻 **Mesh Mode UI Transition (Dark Navy 0.15s Cross-fade):** Khi phát hiện gián đoạn mạng hoặc sập Server, UI ngay lập tức thực hiện hiệu ứng Cross-fade sang nền Dark Navy của Mesh Mode. Trạng thái này báo hiệu hệ thống đã chuyển sang cơ chế P2P Survival Mesh, với các thành phần UI được tải động từ `.tapp` thay vì placeholder tĩnh.
- 📱 **HUD Radar Event-driven SVG:** Hiển thị radar tìm kiếm thiết bị xung quanh sử dụng SVG hướng sự kiện (Event-driven). Radar chỉ nhấp nháy khi có sự kiện thực tế trong mạng Mesh, giúp người dùng nhận diện trạng thái kết nối mà không làm hao pin thiết bị.

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

## 18. Thiết kế Luồng Self-Recovery & HR Recovery (Glassmorphism UI)

- 📱🖥️ **Recovery Room UI (Glassmorphism):** Giao diện khôi phục sử dụng tone màu Mesh Mode (Nền `#0F172A`).
- 📱 **Radar Pulse Visual:** Khi chờ HR/Admin phê duyệt qua BLE, màn hình hiển thị radar pulse màu cam cảnh báo (Security Accent).
- 📱 **Multi-Sig Indicator:** Hiển thị progress bar dạng tinh thể kính (Glass step-tracker) báo hiệu: "Đã nhận 1/2 chữ ký quản trị. Đang chờ thiết bị HR thứ hai...".
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
  > Nếu thất bại 3 lần, chuyển sang luồng Cryptographic PIN Entry (Micro-UI).
- **Cryptographic PIN Entry (Micro-UI):** Giao diện nhập PIN tối giản (Glassmorphism trơn, không có bóng viền) được cấp từ Lõi Rust qua JSI Bridge, hiển thị trạng thái giải mã `Policy_Packet` theo thời gian thực (Real-time Decryption Progress).
  - PIN được truyền thẳng qua **FFI Pointer** xuống Lõi Rust mà không lưu lại trên State của giao thức UI.
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
- [ ] **Cryptographic PIN Entry (Micro-UI)** (Bàn phím FFI 6 số siêu tối giản, không track state qua Bridge).
- [ ] Hoạt cảnh **Ruthless Self-Destruct Visualization** (Màn hình nháy đỏ + Shredding Effect 1s).
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

---

## 15. UI State Machine — Glassmorphism Adaptive Controls (3-Tier Spatial)

> **Nguyên tắc:** Giao diện phải là **"Pure Renderer"** phản ánh chính xác ranh giới vật lý của kênh truyền tải. Lõi Rust là nguồn sự thật duy nhất (Source of Truth) — UI không tự phán đoán Tier, chỉ render trạng thái do `Network_State_Machine` báo về qua IPC.

### Trạng thái Sáng — Tier 1: Online (Full Glassmorphism)

- 🖥️📱💻 **Background:** Full Glassmorphism — backdrop-filter blur(24px), vignette gradient nhẹ.
- 🖥️📱 **Input Bar (Thanh công cụ chat):** Hiểu thị đầy đủ 4 icon: `[+] [🎤 Micro] [📷 Camera] [📎 File]`.
- 🎨 **Màu sắc:** Accent xanh lam hệ thống (`#3B82F6`). Badge indicator màu xanh lá (`#22C55E`) trên avatar.

### Trạng thái Tối — Tier 2: Offline Near (Dark Navy Tactical Mesh)

- 🖥️📱💻 **Background chuyển sang Dark Navy** (`#0F172A`) với Pulse animation màu Amber-vàng (`#F59E0B`) ở viền — tần suất thấp (1 pulse/3s), ra hiệu kết nối P2P đang hoạt động.
- 🖥️📱 **Input Bar:**
  - Nút `[📷 Camera]` và `[📎 File nặng (> 10MB)]` bị **Disabled — Opacity 30%**, tooltip on-hover: *"Video không khả dụng trong cự ly này"*.
  - Nút `[🎤 Micro]` và `[📎 File nhẹ (< 10MB)]` đổi sang **màu Amber-vàng** (#F59E0B, Bold outline) — báo hiệu đang truyền qua Wi-Fi Direct / AWDL.
- 💬 **Status Banner (1px dưới Header):** Dải text chạy scroll ngang — *"🔶 Offline Near — Wi-Fi Direct @ 250Mbps. Video và File lớn không khả dụng."*

### Trạng thái Đỏ — Tier 3: Offline Far (Survival Mode)

- 🖥️📱💻 **Viền màn hình xuất hiện Pulse màu Cam/Đỏ đậm** (`#DC2626`), tần suất nhanh hơn (1 pulse/1.5s) — cảnh báo tình trạng khẩn cấp.
- 🖥️📱 **Input Bar rút gọn cực đại:** **CHỈ CÒN Ô NHẬP TEXT**. Toàn bộ icon `[+] [Micro] [Camera] [File]` biến mất hoàn toàn khỏi DOM. Lõi Rust chủ động bắn `MediaUnavailable(tier=3)` về UI trước khi render — không thể paste file từ clipboard.
- 💬 **Status Banner màu đỏ** — *"🔴 Offline Far — BLE Long Range. Chỉ văn bản. Payload < 4KB."*
- 📱 **Haptic Feedback (iOS/Android):** Rung 200ms liên tiếp 3 lần khi lần đầu vào Tier 3 để cảnh báo người dùng không nhìn màn hình.

---

## 16. External Agent UI — Universal Agentic Bridge (UAB) Indicators

> **Nguyên tắc:** Khi người dùng tương tác với một `.tapp` gọi AI Agent bên ngoài (như OpenClaw/ClawBot), UI phải hiện rõ ràng rằng **dữ liệu đang có nguy cơ rời khỏi perimeter nội bộ** mà không làm gián đoạn workflow.

### External Agent Glassmorphism Warning

- 🖥️📱 **Chat-box chuyển màu Amber:** Khi `.tapp` OpenClaw ở trạng thái Active, nền chat-box chuyển sang hiệu ứng **Glassmorphism sắc Amber** (`#F59E0B` ở 20% opacity) — phân biệt rõ với Blue nội bộ.
- 🖥️📱 **Badge "EXTERNAL AI"** xuất hiện góc trên-phải của agent bubble — màu Amber, font monospace, uppercase — giúp người dùng phân biệt reply từ AI bên ngoài vs Bot nội bộ.
- 🖥️📱 **Tooltip trên Agent Avatar:** *"@OpenClaw — AI Agent bên ngoài. Dữ liệu bạn chia sẻ sẽ rời khỏi hệ thống TeraChat."*

### Consent Modal — Bottom Sheet Acrylic Blur

- 📱💻🖥️ Khi `.tapp` yêu cầu **`terachat.context.request_read_access`** (đọc N tin nhắn làm context), một **Bottom Sheet trong suốt mờ (Acrylic Blur, backdrop-filter: blur(40px))** trượt lên từ phía dưới màn hình:
  - Tiêu đề in đậm: `"@OpenClaw đang yêu cầu quyền trích xuất dữ liệu"`
  - Body text: `"50 tin nhắn gần nhất sẽ được gửi tới api.openclaw.com để làm context. Dữ liệu này sẽ **rời khỏi hệ thống TeraChat**. Chỉ metadata-stripped — không có attachment."`
  - CTA Buttons: **`[Cho phép — Phiên này]`** (Amber, outline) / **`[Luôn cho phép — 30 ngày]`** (Amber, filled) / **`[Từ chối]`** (Ghost, grey).
- ⏱️ **Auto-timeout 30s:** Nếu không có thao tác, Bottom Sheet tự đóng và trả `CONSENT_DENIED` về `.tapp` — không rò rỉ dữ liệu nếu người dùng bỏ màn hình.
- 🗄️ **Audit Trail:** Lõi Rust ghi nhận mỗi lần Consent được cấp/từ chối vào Tamper-Proof Log (`consent_granted @ {timestamp, scope, user_id}`).

---

## 17. Glassmorphism Security State Injection (GSSI) — Visual Guardrail

> **Mục tiêu:** Người dùng phải THẤY ngay lập tức khi có sự kiện bảo mật bất thường — không phụ thuộc vào họ đọc log hay notification. UI phải là "Pure Security Renderer".

- 🖥️ **Glassmorphism Red Alert Filter (Backdrop-filter CSS):** Khi Lõi Rust phát hiện sự kiện bảo mật cấp cao (VD: SPKI mismatch, Manifest verification fail, Agent taint count > 3), toàn bộ viewport được phủ một lớp `backdrop-filter: blur(8px) saturate(0.3) hue-rotate(320deg)` — màn hình chuyển sang sắc đỏ tối mờ, nội dung chat vẫn nhìn thấy nhưng bị desaturate rõ ràng. Không thể bỏ qua.
- 📱 **iOS/Android Native UI Toast Injection:** Đồng thời, Lõi Rust gọi qua FFI/JSI để inject Native Toast (không phải JS alert) vào foreground: banner đỏ cố định ở top safe area (không bị swipe dismiss), nội dung: `"⚠️ Security Event Detected — [action taken]"`. Toast persist 10 giây, yêu cầu explicit tap để dismiss.
- 💻 **Tauri State Synchronization Bus:** Trên Desktop/Tauri, security state thay đổi được broadcast qua Tauri `emit_all("security_state_changed", payload)`. Tất cả window instances (multi-window mode) đều nhận update đồng thời — không có window nào "không biết" về security event.

---

## 18. Glassmorphism Wave Progress State Machine — Progressive AI Upload UI

> **Mục tiêu:** Khi SD-OAP stream file lớn sang AI Agent (có thể mất 30-120 giây), UI phải cho người dùng cảm giác "đang xử lý an toàn" — không phải màn hình trắng chờ.

- 🖥️📱 **Backdrop-filter Wave Component:** Progress được thể hiện bằng một **Glassmorphism Wave** — `backdrop-filter: blur(16px)` overlay hình sóng (`SVG wave path`) animated từ trái sang phải theo progress %. Wave màu Amber nhạt (`rgba(245, 158, 11, 0.25)`) — không che khuất nội dung chat phía sau.
- 📱💻 **FFI/JSI Progress Callback:** Lõi Rust gọi progress callback `on_egress_progress(bytes_sent, total_bytes, chunk_index)` qua JSI (iOS) / Dart FFI (Android) mỗi khi hoàn thành 1 chunk (2MB). UI cập nhật wave width theo `bytes_sent/total_bytes` — smooth CSS transition 300ms.
- 🖥️📱 **Asynchronous State Injection:** Progress state không block UI thread. Lõi Rust emit `StateChanged("egress_progress", {uuid, pct})` qua IPC bus — UI chủ động poll tại 60fps via `requestAnimationFrame` để update wave mà không gây jank.
- 📱💻 **Pure Renderer Architecture (Zero Blocking Main Thread):** Mọi data-fetch (decryption, DB query, embedding search) được thực hiện 100% trên Rust background thread. UI thread chỉ nhận struct `RenderPayload` đã sẵn sàng — không block bất kỳ frame nào.
- 📱 **React Native JSI Zero-Bridge (Mobile):** Thay vì async bridge serialization (JSON stringify/parse qua MessageQueue), render callback từ Lõi Rust được inject trực tiếp vào JS engine qua JSI C++ shared pointer. Latency UI update < 1ms.
- 💻 **macOS/Windows Glassmorphism Progress Overlay:** `backdrop-filter: saturate(180%) blur(20px)` kết hợp `background: rgba(255,255,255,0.08)` — progress render lên trên content mà không che khuất. GPU-accelerated via `will-change: transform`.

#### §1.5 DMA Intrusion Critical Alert UI

> **Trigger:** `SecurityEvent::DMA_INTRUSION` từ Lõi Rust khi phát hiện PCIe device mới join IOMMU group runtime.

- 💻🖥️ **Full-Screen SecurityCriticalAlert Modal:** Nền full-screen `#0D0000` (near-black red), không thể dismiss bằng Escape/click-outside. Center: icon `🛡️ ⚠️` size 48px, text `"DMA Intrusion Detected — Session Terminated"` màu `#FF4444 font-weight: 700`.
- 💻🖥️ **Countdown Auto-Lockout (10s):** Progress ring countdown màu đỏ đếm ngược 10 giây. Khi hết: màn hình biến mát, tất cả window đóng. Không có nút Dismiss.
- 💻🖥️ **"Report to CISO" Button:** Nút duy nhất trên màn hình — khi nhấn, Lõi Rust tự động compose `IncidentReport {timestamp, device_id, iommu_violation_detail}`, ký Ed25519, gửi vào `#security-incidents` channel qua CRDT State.

#### §Quorum Approval Pending UX (Multi-Sig Executive Break-glass)

> **Trigger:** CEO/C-Level khởi động Break-glass Recovery, cần đủ 2 approvals từ C-Level khác trong phạm vi BLE < 2m.

- 📱 **Pulsing Radar Screen (Full-Screen):** Khi CEO nhấn Break-glass, toàn bộ màn hình chuyển sang `#0F172A` dark navy. Radar animation xuất hiện ở giữa — dual-beam: **Cyan `#00D4FF`** (BLE Control probe) và **Amber `#F59E0B`** (Approval beacon) — pulse nhanh hơn khi phát hiện thiết bị C-Level lân cận.
- 📱 **Proximity Detection Ring:** Khi thiết bị C-Level khác vào phạm vi < 2m (BLE RSSI threshold), một ring xanh lá (`#22C55E`) sáng lên quanh avatar của họ trong danh sách. Text: `"CFO đã phát hiện — Đang chờ xác thực sinh trắc..."`.
- 📱 **Biometric Confirmation Prompt (on approver device):** Thiết bị của CFO/CISO nhận toast full-width: `"Break-glass Request từ CEO — Xác thực FaceID để phê duyệt"`. FaceID prompt hiện ra. Approve → ring chuyển Gold `#F59E0B` với dấu ✓. Reject → ring đỏ.
- 📱 **Quorum Counter:** Góc trên phải màn hình CEO: `"✅ 1 / 3 phê duyệt"` → `"✅ 2 / 3 phê duyệt"` → `"✅ 3 / 3 — Đang tái tạo khóa..."`. Khi đủ quorum, radar animation chuyển sang xanh lá và bắt đầu Lagrange reconstruction progress.
- 📱 **Timer Bar:** Top của màn hình: progress bar đếm ngược 10 phút còn lại (`#F59E0B → #EF4444` khi còn < 2 phút). Hết timer → toàn màn hình flash đỏ, session abort.



---

## 19. Sovereignty-Aware Visual Feedback — Egress Transparency UI

> **Mục tiêu:** Người dùng phải biết bao nhiêu byte đang "chạy ra ngoài" TeraChat perimeter khi sử dụng AI Agent — real-time, không cần đọc log.

- 🖥️📱 **Glassmorphism Blue/Amber State Machine:**
  - **Blue Glassmorphism:** Dữ liệu xử lý locally (ONNX embedding, RAG search nội bộ) — không có egress. Badge "🔵 Local AI" xuất hiện cạnh agent bubble.
  - **Amber Glassmorphism:** Dữ liệu đang egress ra External AI. Chat-box border chuyển Amber pulse animation. Badge "🔶 Ext AI" + egress counter real-time.
- 🖥️📱 **Real-time Egress Metadata Counter:** Hiển thị micro-counter ở corner chat input: `"↑ 2.3KB to OpenClaw"` cập nhật mỗi giây. Màu xanh lá nếu < 10KB (an toàn), vàng nếu 10-100KB, đỏ nếu > 100KB (cảnh báo data dumping). Counter reset về 0 khi session kết thúc.
- 🖥️📱 **Processing State Injection:** Khi ONNX đang embed locally (không egress), hiển thị spinner nhỏ màu Blue với text `"Đang tìm kiếm cục bộ..."`. Khi egress bắt đầu, spinner đổi sang Amber với text `"Đang hỏi OpenClaw..."`. Người dùng luôn biết AI đang làm gì tại mọi thời điểm.

#### §19.1 Cloud Enclave Processing Indicator — VPS TEE Glow UI (Elite)

> **Trigger:** `.tapp Heavyweight` đang chạy computation trên VPS Enclave (Intel SGX/AMD SEV) thay vì Mobile.

- 🖥️📱 **Shield-Cloud Glow Badge (Góc trên khung .tapp):** Khi Enclave đang process, góc trên phải của `.tapp` window frame hiển thị composite icon: **☁️🛡️** (đám mây + khiên) kích thước 18×18px, màu `#3B82F6` (blue-500). Xung quanh icon: **Soft Glow Effect** `box-shadow: 0 0 8px rgba(59,130,246,0.6)` pulsing animation 2s ease-in-out infinite. Không chớp tắt — glow nhè nhẹ liên tục.
- 🖥️📱 **Tooltip khi hover:** `"Tác vụ này đang được xử lý bảo mật trên Server của công ty bạn — không tốn pin thiết bị bạn. (TeraChat Elite)"`. Font `Inter 12px`, background `rgba(15,23,42,0.9)`, border `1px solid rgba(59,130,246,0.3)`.
- 🖥️📱 **State Machine:**
  - `ROUTING` (đang kết nối Enclave): icon xoay spinner màu blue, text `"Đang kết nối Enclave bảo mật..."` — max 3s.
  - `ATTESTING` (DCAP verification): icon shield + loading ring, text `"Đang xác minh Server an toàn..."` — max 2s.
  - `PROCESSING` (Enclave đang compute): Glow badge ổn định + micro counter `"⚙️ Enclave: 1.3s"` đếm elapsed time.
  - `DONE`: Badge fade out 500ms, result render bình thường.
  - `ATTESTATION_FAILED`: Badge đổi đỏ `#EF4444` + modal `"Không thể xác minh Server an toàn. Kết nối bị từ chối."` Non-dismissable, require Admin action.
- 📱 **Mobile Power Save Notification:** Khi `.tapp` Lightweight bị override route lên Enclave do pin < 20%, hiển thị toast nhỏ ở bottom: `"🔋 Chế độ tiết kiệm pin: Tác vụ chuyển lên Server"` màu `#7C3AED` (tím), auto-dismiss 3s.
- 🖥️ **Desktop Taskbar Indicator:** Trên Desktop (Tauri), khi Enclave đang active, icon TeraChat trong system tray có badge chấm xanh `#3B82F6` nhỏ góc dưới phải — visual cue nhẹ không làm phiền workflow.



---

## 20. Resource-Aware Visual State Machine (RAVSM) — Device Performance Feedback

> **Mục tiêu:** Khi THARG phát hiện thiết bị đang bị quá tải (thermal throttling, low RAM), UI phải thông báo cho người dùng thay vì để app bị ANR/crash.

- 🖥️📱 **Glassmorphism Grey State (`#64748B`):** Khi Lõi Rust phát hiện `heap_usage > 75%` hoặc `cpu_temp > 45°C`, AI Agent panel chuyển sang Grey Glassmorphism (`backdrop-filter: blur(8px) grayscale(60%)`). Nút "Ask AI" bị desaturate nhẹ — báo hiệu performance mode bị giới hạn nhưng không block hoàn toàn.
- 🖥️📱 **Expectation Management Modals:** Khi user tap "Ask AI" trong Grey State, một bottom modal xuất hiện: `"Thiết bị của bạn đang ở hiệu suất thấp. Câu trả lời có thể mất lâu hơn bình thường. [Tiếp tục] / [Hủy]"` — không silent degradation, không bất ngờ.
- 📱💻 **JSI/FFI Performance Telemetry:** Lõi Rust emit `StateChanged("perf_tier", {tier: "low"|"mid"|"high", heap_mb, cpu_temp})` qua JSI/FFI mỗi 5 giây. UI subscribe và cập nhật RAVSM state tương ứng — không polling aggressive, không battery drain.

#### Giải pháp: Visual Threat Intelligence & Aggressive UI Throttling (Phản hồi Giao diện khi Mạng suy thoái và Rủi ro Timeout trong Mesh Mode)

- 📱 **Glassmorphism State Transition:** Khi mạng rơi vào trạng thái suy thoái (Degradation), giao diện tự động mờ dần sang các gam màu cảnh báo (Amber/Xám) thông qua kỹ thuật Glassmorphism, giúp người dùng nhận thức ngay lập tức về tình trạng kết nối yếu mà không gây hoảng loạn.
- 💻🖥️ **Progressive Disclosure (Skeleton Loading):** Thay vì để màn hình trắng hoặc treo UI, hệ thống chỉ hiển thị khung xương (Skeleton) của nội dung đang tải kết hợp hiệu ứng Shimmer. Kỹ thuật này giảm thiểu cảm giác chờ đợi và ẩn đi sự chậm trễ của quá trình Render dữ liệu.
- 📱💻 **Exponential Backoff Retry UI:** Triển khai cơ chế Retry tuyến tính kết hợp với UI đếm ngược thời gian chờ ngày càng tăng (Exponential Backoff). Nút "Thử lại" sẽ bị vô hiệu hóa tạm thời (Disabled) để ngăn chặn User Spam Click làm nghẽn thêm hàng đợi I/O của Lõi Rust.

---

## 21. Glassmorphism Sanitized Node Indicator (GSNI) — XSS Attempt Visual Alert

> **Mục tiêu:** Khi SASB phát hiện và prune node XSS trong AI response, người dùng phải thấy rõ ràng rằng "có điều gì đó bị chặn" — không silent, không render trống.

- 🖥️📱 **Crimson Glassmorphism Component (`#E11D48`):** Ở vị trí node bị prune trong AI response bubble, thay vì bỏ trống, UI render một placeholder component: nền Crimson Glassmorphism `backdrop-filter: blur(4px)` + icon shield + text `"[Nội dung bị chặn bởi Security Filter]"`. Rõ ràng nhưng không panic người dùng.
- 🖥️📱 **Native-only Component Mapping (Zero-HTML):** Placeholder component được implement bằng native component (React Native View / Tauri native element) — không phải HTML div với innerHTML. Đảm bảo không có escape path nào cho malicious content render.
- 🖥️📱 **Real-time State Injection:** Mỗi lần prune event xảy ra, Lõi Rust emit `StateChanged("node_pruned", {session_id, count})` qua IPC. UI render GSNI component ngay lập tức tại đúng vị trí trong chat bubble tree — không cần re-render toàn bộ bubble.

---

## 22. Clipboard Content Integrity Indicator — Copy-Safety Badge

> **Mục tiêu:** Người dùng phải biết khi nào nội dung họ copy đã được "sanitize" bởi PCB — tránh mất dữ liệu quan trọng và tăng awareness về clipboard security.

- 🖥️📱 **Glassmorphism Copy-Safety Badge:** Ngay sau khi người dùng copy text từ TeraChat, một micro-badge xuất hiện tại vị trí copy point trong 2 giây: nền Glassmorphism xanh lá nhạt (`rgba(34, 197, 94, 0.2)`) + icon ✓ + text `"Đã làm sạch metadata"` — xác nhận PCB đã xử lý thành công.
- 🖥️📱 **Clipboard Entropy Warning Modal:** Nếu PCB phát hiện Shannon Entropy của nội dung copy > 6.0 bits/char (khả năng chứa encoded data), thay vì copy ngay, UI hiện Modal cảnh báo: `"Nội dung này có độ phức tạp bất thường. Bạn có muốn copy không?"` với 2 nút: `[Copy Có Lọc]` và `[Không Copy]`. Không có nút "Copy Nguyên bản" — bảo vệ cứng.
- 🖥️📱 **"Sanitized Copy" Visual Feedback:** Khi copy thành công qua PCB, text thuần text segment được highlight nhẹ (blue underline flash 500ms) — feedback trực quan rằng đây là "Sanitized Copy" khác với Ctrl+C thông thường. iOS sử dụng Haptic (light impact) để confirm.

---

## 23. Hazard-Stripe Semantic Alert UI — ESF Guardrail Visual

> **Mục tiêu:** Khi EDES hoặc EICB phát hiện Intent Score vượt ngưỡng nguy hiểm, UI phải "seal" visual context của conversation đó một cách không thể bỏ qua.

- 🖥️📱 **Glassmorphism Hazard-Stripe Component:** Conversation bubble của AI Agent bị flag được bao quanh bởi **Hazard-Stripe overlay** — pattern CSS diagonal stripes màu Amber/Black (`repeating-linear-gradient`) với `backdrop-filter: blur(4px)`. Nội dung vẫn đọc được nhưng bị frame rõ ràng là "flagged". Không thể dismiss bằng swipe.
- 🖥️📱 **Non-bypassable Modal Injection:** Đồng thời, một Modal xuất hiện ở center screen: `"⚠️ Nội dung này bị chặn bởi Semantic Guardrail. Intent Score: [category] [score]. [Xem Chi tiết] / [Đóng Session]"`. Modal không có nút "X" — chỉ có 2 lựa chọn rõ ràng. User phải acknowledge trước khi tiếp tục.
- 🖥️📱 **Visual Integrity Signal:** Sau khi Modal dismissed, Status Bar của conversation hiển thị badge nhỏ màu Amber: `"🛡️ Guardrail Active"` — persistent indicator cho biết session này đã có ít nhất 1 flag event. Badge không biến mất cho đến khi session kết thúc.

#### §23.1 Unsafe Sideloaded .tapp — Hazard-Stripe Warning Frame

> **Trigger:** `.tapp` được sideload trực tiếp (không qua TeraChat Marketplace review + Ed25519 signature của Enterprise_CA).

- 🖥️📱 **Hazard-Stripe Window Border:** Toàn bộ window frame của `.tapp` được bao quanh bởi **viền sọc Vàng-Đen** (`repeating-linear-gradient(45deg, #F59E0B 0px, #F59E0B 10px, #1C1917 10px, #1C1917 20px)`) — 4px border, không thể bị `.tapp` content che khuất (render ở Z-index System Level, ngoài WASM sandbox). Chạy liên tục, không fade.
- 🖥️📱 **Persistent Warning Badge:** Header của `.tapp` window hiển thị badge `"⚠️ UNVERIFIED EXTENSION"` màu Amber `#F59E0B`, font `Inter 11px SemiBold`. Tooltip khi hover: `"Tiện ích này không được TeraChat Marketplace xác minh. Dữ liệu bạn nhập có thể không được bảo vệ."`.
- 🖥️📱 **TeraChat Liability Disclaimer Modal (One-time per session):** Lần đầu mở `.tapp` sideloaded trong session, modal xuất hiện: `"Bạn đang khởi động một tiện ích không được xác minh. TeraChat không chịu trách nhiệm về bất kỳ rủi ro bảo mật nào phát sinh. [Tôi hiểu, Tiếp tục] / [Đóng tiện ích]"`. Không có nút "Không hiển thị lại".
- ☁️ **Admin Console Override:** Admin có thể whitelist `.tapp` sideloaded qua CISO Console bằng OPA Policy — khi được whitelist, Hazard-Stripe biến mất và thay bằng badge xanh `"✅ Admin Approved"`. Mọi whitelist action được audit log Ed25519 signed.

#### §23.2 Pending Merge State — Dashed Border (Optimistic Append-Only Mesh)

> **Trigger:** Tin nhắn gửi khi không có Desktop Super Node trong Mesh (Optimistic Append-Only mode).

- 📱 **Dashed Border Bubble:** Bubble tin nhắn ở trạng thái `PENDING_MERGE` hiển thị với `border: 1.5px dashed rgba(148, 163, 184, 0.5)` (xám xanh nhạt, 50% opacity), background `rgba(15, 23, 42, 0.6)` (dark navy semi-transparent). Text đọc được bình thường nhưng bubble trông "mờ" hơn bubble đã confirmed.
- 📱 **Status Indicator:** Góc phải dưới bubble: icon `⋯` (3 chấm xoay) màu xám `#94A3B8` với tooltip `"Chờ Desktop merge"`. Không phải icon "đã gửi" (✓) hay "đã đọc" (✓✓).
- 📱 **Reconcile Animation:** Khi Desktop Super Node vào Mesh và merge hoàn tất, bubble transition: `border: dashed → solid`, `opacity: 0.6 → 1.0`, icon `⋯ → ✓✓` trong 500ms ease-out. Toàn bộ PENDING_MERGE bubbles reconcile cùng lúc tạo hiệu ứng "cascade solidify" từ trên xuống dưới.
- 📱 **Temporary Dictator Badge:** Khi Android thiết bị đang là Temporary Dictator, Status Bar hiển thị `"📱 Mesh Dictator (Tạm thời)"` badge màu `#7C3AED` (tím nhạt) — phân biệt với Desktop Dictator `"💻 Mesh Dictator"` màu `#2563EB` (xanh).



---

## 24. Security Cleanup Visual — Checkpoint Purge Confirmation

> **Mục tiêu:** Người dùng (và CISO) cần thấy bằng chứng rằng Checkpoint đã bị xóa thực sự — không phải "unlink" giả.", không phải trải qua một nút "Delete" và không có gì xảy ra.

- 🖥️📱 **Glassmorphism "Purge" Animation:** Khi GC trigger xóa Checkpoint batch, một animation xuất hiện 2 giây tại Settings > Security > AI Context: các card "Checkpoint" được đại diện bởi mini Glassmorphism tiles, mỗi tile bị "shred" animation (vỡ vụn thành pixel) lần lượt từ trái sang phải. Số đếm: `"Đã xóa 3/3 checkpoint an toàn"`.
- 🖥️📱 **Security Audit Log Entry:** Mỗi hành động purge được ghi vào Security Audit Log trong app (`Settings > Security > Audit Log`): `[GC_PURGE | {n} checkpoints | Method: 3-pass shred | Timestamp]`. CISO có thể screenshot log này cho compliance evidence.
- 🖥️📱 **State-driven Cleanup Feedback:** Sau khi purge hoàn tất, AI Context card trong Settings chuyển sang state Empty: background `#0F172A` dark navy, text trung tâm `"Không có dữ liệu AI tạm thời nào đang lưu trữ"` + icon shield màu xanh lá. Người dùng có thể confirm bằng mắt rằng bộ nhớ AI đã sạch.

---

## 25. Magnetic Collapse & Retroactive Visual Sealing — SSA Salami Attack UI

> **Mục tiêu:** Khi SSA phát hiện Salami Attack (Retroactive Taint trên N-3 messages), UI phải "phản ứng" một cách drama để user không thể bỏ qua — đây là sự kiện bảo mật nghiêm trọng.

- 🖥️📱 **Magnetic Collapse Animation (Native UI):** N-3 tin nhắn bị retroactive taint đồng loạt bị thu nhỏ (scale 1.0 → 0.1) trong 300ms với easing `cubic-bezier(0.4, 0, 1, 1)` — hiệu ứng "collapse về phía tin nhắn gốc" như magnetic pull. Sau collapse, placeholder Hazard-Stripe xuất hiện tại vị trí của mỗi tin nhắn.
- 🖥️📱 **Hazard-Stripe Glassmorphism Overlay (`#F59E0B`):** Toàn bộ conversation area (không chỉ bubble) được phủ một layer Glassmorphism Amber semi-transparent (`rgba(245, 158, 11, 0.15)`) + diagonal stripes — báo hiệu "toàn bộ session này đang bị quarantine".
- 🖥️📱 **Atomic IPC State Update (`SharedArrayBuffer`):** Toàn bộ animation được trigger bởi một atomic `StateChanged("ssa_taint_detected", {sealed_messages: [id1, id2, ...], seal_timestamp})` từ Lõi Rust qua `SharedArrayBuffer`. UI consume state change tại 60fps next render — zero jank, zero partial state display.

---

## 26. FCP Active UI — "Naked AI" Interface (Full-Context Passthrough Mode)

> **Nguyên tắc:**- Khi luồng FCP được kích hoạt tại Administrative Plane (§13 `Function.md`), toàn bộ các Client trong phòng đó (bất kể thiết bị di động hay Desktop) lập tức bị áp dụng **FCP Active UI**.
- 🖥️📱 **Thay đổi cấu trúc Frame:** Khung chat tổng được bao bọc bởi một dải viền cứng Solid Red Border (Độ dày 2px, viền đỏ Hex `#E11D48`). Góc phải trên cùng hiển thị Icon Cảnh báo: `"Naked AI — Uncensored LLM Tunnel"`.
- 🖥️📱 **Persistent Watermark:** Nền Background của phòng chat xuất hiện Watermark Text in chìm gạch chéo: `[LIABILITY SHIFT ACTIVE — NO SEMANTIC QUARANTINE]`.
- 🖥️📱 **Đồng hồ Băng thông (Telemetry Counter):** Cạnh Input Bar nảy lên một bộ đếm Byte (Red Indicator). User gõ 1 ký tự, bộ đếm nhảy số Byte thô trực tiếp bay sang 3rd-party LLM ($103$ KB $\uparrow$). Hình ảnh đập vào mắt người dùng liên tục nhằm khẳng định: Mọi hành động của bạn tại session này đang thoát ra khỏi ranh giới Zero-Knowledge của cấu trúc lưới.

## 27. Soft Quarantine Glassmorphism UI (Rào chắn Phân định Ngữ cảnh)

- **Nguyên lý thiết kế:** Người dùng phải biết một nội dung bị cách ly mà không cảm thấy sợ hãi (Panic).
- 🖥️📱 **Acrylic Blur Masking (Che khuất Mờ):** Bất kỳ Payload nghi ngờ độc hại hoặc sai trái Context Role (§14 PCAB của `Function.md`) đều bị render đè một lớp Component Viewports:
  - Background: `rgba(0, 0, 0, 0.45)`, Acrylic Blur `30px`.
  - Icon Center: 🔒 **Locked Context** kèm dòng chữ trắng `"Unlock with PIN/Biometrics"`.
- 🖥️📱 **Shatter Animation (Kính Vỡ):** Khi xác thực PCAB Argon2id thành công, hệ thống không chỉ ẩn lớp Masking mà thực thi một animation "Mảnh kính vỡ" (Particle Shatter) kéo dài 300ms. Hiệu ứng Native này mang lại haptic feedback, thông báo trạng thái "Quyền đã được gỡ niêm phong".

## 28. Glassmorphism Hazard-Stripe Quarantine UI (Dấu hiệu Tệp tin Weaponized)

- **Nguyên lý thiết kế:** File bị nhúng mã độc phải lộ diện rõ ràng mà không phá vỡ UI tổng thể.
- 🖥️📱 **Màu sắc và Hoạ tiết:** Khi một tệp tin (`.pdf`, `.docx`) tải xuống bị Safe-Rust CDR Engine (§5.39 `Core_Spec.md`) bóc tách macro/phát hiện zero-day, Component UI bọc file đó sẽ chuyển sang trạng thái Hazard: Hình nền Component xen kẽ các đường gạch chéo sọc Đen/Vàng (#FACC15).
- 🖥️📱 **Visual Integrity Signal:** Dấu mộc Đỏ Textbox nổi trên tệp tin: `"Tệp tin đã được Khử độc (Sanitized)"` hoặc `"Tệp bị Cách ly"`. Nhấp vào sẽ hiển thị Modal chi tiết lượng Byte Code nhúng rác đã bị hệ thống vứt bỏ bằng quá trình Zero-Copy I/O Prevention.

## 29. Thiết kế Giao diện Khóa Vùng Nhớ (Memory Air-Gapping)

> **Bài toán:** Phân chia rạch ròi vòng đời của Component Giao diện để ngăn chặn DOM/Native Views vô tình lưu trữ plaintext nhạy cảm trong Cache.

- 📱 **JSI Native Memory Bridge:** Giao diện tự động thu hồi và tiêu hủy phân đoạn (teardown) JSI Native Pointer ngay khi màn hình chat bị unmount hoặc bị ứng dụng khác che khuất (Backgrounded).
- 📱 **Screen-Level Memory Teardown:** Ràng buộc vòng đời (Lifecycle) của Component Native với lệnh `ZeroizeOnDrop` của Lõi Rust. Unmount UI đồng nghĩa với việc dọn sạch Sandbox RAM tĩnh.
- 🖥️ **Air-gapped UI Thread (WASM Isolation):** Trên Desktop, luồng UI và luồng WASM bị ép chạy trên hai Dedicated Web Workers hoàn toàn cách ly (Air-gapped), chỉ giao tiếp qua DMZ Shared Memory chuyên biệt, xóa bỏ rủi ro rò rỉ dữ liệu qua Global DOM.

## 30. Phản hồi Trạng thái Nạp Bộ nhớ (Memory Hydration Feedback Loop)

- 📱💻 **Glassmorphism Blur + Skeleton Loading tại phân hệ .tapp:** Khi Lõi Rust đẩy tiến trình Hydration (nạp Vector Embeddings theo chunk), phân hệ .tapp hiển thị Skeleton Loading phủ lới Glassmorphism Blur `blur(16px)` ngay lập tức — không để màn hình trống.
- 📱💻 **Accent Pulse `#24A1DE`:** Thanh tiến trình nhấp nháy (Pulse Animation 1.2s) màu `#24A1DE` báo hiệu trạng thái Hydrating thời gian thực — phân biệt rõ ràng với trạng thái Idle.
- 📱💻 **Radar Pulse Mesh Mode:** Trên nền `#0F172A` (Mesh Mode), vòng Radar Pulse quét chậm với dâu vết `pulse 3s ease-in-out infinite` thay thế Accent bar — tối ưu hóa năng lượng trong môi trường Survival.

## 31. Phản hồi Trạng thái Thu hồi Tài nguyên (Memory Reclamation Feedback)

- 📱 **Frost Glass Badge Cam "Tái cấp phát bộ nhớ...":** Khi Lõi Rust thực thi Generational Handle Reuse, UI phủ lới Frost Glass mờ lên phân hệ .tapp kèm Badge cam `#F97316` với text `"Tái cấp phát bộ nhớ..."` — người dùng nắm được hệ thống đang tối ưu, không hoảng lạc.
- 💻 **Skeleton Loading `#24A1DE` tại phân hệ .tapp:** Xung nhấp nhái cài đặt trừb tiến `#24A1DE → transparent` đồng bộ với chu kỳ `munmap()` của Lõi Rust.
- 📱 **LED Red Pulse + `[MEM_RECLAIM]` (Mesh Mode):** Trên nền `#0F172A`, LED đỏ nhấp màu `#EF4444` kèm nhãn Mono-space `[MEM_RECLAIM]` xuất hiện góc trên phải; vùng nội dung vẫn hiển thị đồng thời bằng Preserved Frame — thông tin không mất.

## 32. Phản hồi Trạng thái .tapp bị Giết cưỡng bức (Tapp Crash State)

- 📱 **Event-driven `Tapp_Terminated_DoS_Protection` signal:** Lõi Rust phát tín hiệu `TAPP_TERMINATED` qua IPC khi Sandbox bị Kill do vượt Timer Guard 50ms; UI nhận tín hiệu event-driven — không polling.
- 💻 **Red Glassmorphism Overlay (TAPP_TIMEOUT):** Overlay Glassmorphism đỏ `rgba(239,68,68,0.15)` phủ vùng .tapp kèm mã lỗi `TAPP_TIMEOUT` và nút `[Khởi động lại]` — người dùng luôn có lối thoát rõ ràng.
- 🖥️ **Mesh Mode SIGKILL Log Overlay:** Trên Desktop, phủ vượt thanh thông báo `Survival Protection: TAPP_SIGKILL` màu đỏ tối `#7F1D1D` xác nhận hệ thống đang bảo vệ Messaging Core.

## 33. Lock-down State Feedback UI (Zero-Access & License Expiry)

- 💻 **Dải Warning Amber `#F59E0B` (Frost Glass, 30 ngày trước hết hạn):** Hiển thị dải cảnh báo nhấp nhái màu Amber phờ trên đầu màn hình với nội dung `"Giấy phép hết hạn trong N ngày"` — Admin nhìn vào là hiểu ngay.
- 🖥️ **Dark Glass Lockdown (Zero-Access):** Khi vượt hạn, toàn bộ Data Plane bị ngắt và UI chuyển sang nền `#0F172A` + khóa màn hình Dark Glass với text `"Giấy phép hết hạn. Liên hệ Admin để gia hạn."` — không thể tương tác thêm.
- 📱 **Ngắt luồng IPC Data Plane (Tầng nhị phân):** Lõi Rust ngắt cỡng luồng IPC của Data Plane; nhắm khoá khả năng tránh bằng cách vá UI — bảo vệ ở tầng binary.

## 34. Zero-Access Lockdown Renderer (Survival Activation)

- 🖥️ **Dark Glassmorphism (Nền `#0F172A`):** Toàn bộ giao diện chuyển sang Dark Glassmorphism kích hoạt chế độ Zero-Access; chỉ hiển thị thông tin trạng thái + CTA khởi động ngoại tuyến.
- 🖥️ **Radar Pulse Animation (Tìm Quorum):** Vòng Radar Pulse quét chậm với hiệu ứng `pulse 2s ease-in-out infinite` biểu diễn trạng thái đang tìm kiếm phê chuẩn Quorum từ người dùng khác.
- 🖥️ **Warning Amber `#F59E0B` + `Hardware Provisioning Quota`:** Hiển thị trạng thái `Hardware Provisioning Quota: N/N` màu Amber — Admin thấy rõ có bao nhiêu slot Hiếu Chuyển còn lại trong HSM Sub-CA.

## 35. Byzantine Fault Lockdown UI (Lỗi đồng thuận ác ý)

- 📱 **Nền Dark Glassmorphism + viền nhấp nháy đỏ (`#EF4444`):** Khi phát hiện Byzantine Fault (Root_Hash lệch Quorum), viền giao diện nhấp nháy đỏ `#EF4444` trên nền `#0F172A` báo trằng thái nguy hiểm đang xảy ra.
- 🖥️ **Circuit Breaker ngắt kết nối vật lý:** UI hiển thị thông báo `"Kết nối Server bị tạm dừng do phát hiện lỗi đồng thuận"` — Circuit Breaker đã cắt Socket Egress ở tầng Lõi ngay tực thời.
- 📱 **Nút "Disconnect & Report" cưỡng bức:** Nút hành động duy nhất khả dụng là `[Ngắt và Báo cáo]` — người dùng không thể Resume phiên tồi bại mà chưa chứng thực lại.

## 36. Glassmorphism Eclipse Feedback (Tấn công Nhật thực UI)

- 📱 **Viền Warning Amber `#F59E0B` (Verifying State Integrity):** Trong khi Chéo-đối soát Gossip bắt đầu, viền giao diện chuyển sang Amber nhấp nháy + text `"Xem xét tính toàn vẹn mạng lưới..."` — người dùng được thông báo chuyển động.
- 💻 **Haptic Feedback + nền Dark Mesh `#0F172A`:** Trên Desktop, âm thanh cảnh báo nhẹ kèm nền tối kích hoạt trạng thái Survival; Haptic Feedback trên Mobile thực hiện rị nhẹ 3 lần.
- 🖥️ **Banner Cảnh báo Đỏ sắm `#991B1B`:** Khi Eclipse Attack xác nhận, Banner đỏ sắm `#991B1B` hiển thị duyền giao diện `"Thực tại lưới bị phân mảnh. Cuộc trò chuyện bị cầch ly khỏi Server."` — cưỡng bức đóng băng thực tại giả.

## 37. AI Privacy Shield Indicator — Glassmorphism Enterprise

> Công tắc AI Context không phải là nút gạt vô tri. Nó là **AI Privacy Shield Indicator** — hiển thị trạng thái bảo vệ dữ liệu real-time cho người dùng nhận thức được rủi ro.

### Online Mode (Nền sáng — Standard Enterprise)

💻 **Laptop** / 🖥️ **Desktop** / 📱 **iOS** / 📱 **Android**:

- **Trạng thái OFF (Mặc định — Shield ACTIVE):**
  - Toggle đặt ngay cạnh thanh Chat Input Bar.
  - Màu nền: Frosted Glass mờ (`backdrop-filter: blur(12px); background: rgba(255,255,255,0.12)`).
  - Icon: **Khiên khóa chặt** — màu xám lạnh `#94A3B8`.
  - Label nhỏ bên cạnh: `"AI Shield: ON"` — font Mono `11px`.
  - Tooltip khi hover: `"Dữ liệu được che mặt trước khi gửi AI. Nhấn để nạp ngữ cảnh đầy đủ."`.

- **Trạng thái ON (Shield DISABLED — người dùng tự chọn tắt):**
  - Toggle chuyển sang màu **Amber cảnh báo** `#F59E0B`.
  - Viền sáng nhẹ: `box-shadow: 0 0 10px rgba(245,158,11,0.4)` — **Amber Glow Pulse** (`animation: glowPulse 2s ease-in-out infinite`).
  - Icon: **Khiên mở / cảnh báo** (shield với dấu `!` bên trong).
  - Label: `"AI Shield: OFF"` — màu Amber `#F59E0B`.
  - **Tuân thủ ISO 27001:** Tooltip bổ sung cảnh báo: `"Dữ liệu thô đang được gửi vào TEE Sandbox. Hành động này được ghi nhật ký bảo mật."`.
  - Non-Rep Audit Badge nhỏ góc phải Toggle: icon **Audit log** màu cam.

### Mesh Mode (Nền tối `#0F172A` — Survival / Offline P2P)

💻 **Laptop** / 🖥️ **Desktop** / 📱 **iOS** / 📱 **Android**:

- Toggle bị **vô hiệu hóa hoàn toàn (Disabled):**
  - Màu nền: Mờ đục `rgba(255,255,255,0.04)` — không phân biệt rõ ràng với background.
  - Icon: Khiên với **gạch chéo `✕`** — màu xám tối `#475569`.
  - **Không có Glow Pulse, không có Amber** — phân biệt rõ với trạng thái cảnh báo Online.
  - Cursor: `not-allowed` — ngăn nhầm tưởng tương tác.

- **Khi người dùng tap / click vào Toggle bị disabled:**
  - Hiện **Toast Notification** từ đáy màn hình (Mobile) hoặc góc trên phải (Desktop):
    > *"Tính năng nạp ngữ cảnh AI bị vô hiệu hóa trong mạng Mesh P2P để bảo vệ Chủ quyền Dữ liệu."*
  - Toast style: Nền `#1E293B`, viền `#334155`, icon khiên màu `#64748B`, timeout `4000ms`, không có action button.

### Design Tokens

| Token | Online OFF | Online ON | Mesh Disabled |
| ----- | ---------- | --------- | ------------- |
| Nền Toggle | `rgba(255,255,255,0.12)` | `#F59E0B` | `rgba(255,255,255,0.04)` |
| Icon Color | `#94A3B8` | `#1C1917` | `#475569` |
| Glow | — | `glowPulse 2s` Amber | — |
| Cursor | `pointer` | `pointer` | `not-allowed` |

## 38. Mesh Topology Visualization — Survival HUD

> **Mục tiêu:** Cung cấp cho người dùng cái nhìn trực quan về cấu trúc lưới P2P, giúp xác định các "điểm nghẽn" và khoảng cách kết nối trong môi trường không có Internet.

- 📱 **Offline Survival HUD (StatusBar Overlay):** Khi Mesh Mode active, StatusBar hiển thị một dải Glassmorphism siêu mỏng (`height: 2px`) chạy dọc cạnh trên. Màu sắc thay đổi theo **RSSI (Signal Strength)**:
  - 🟢 **Xanh lá:** Kết nối mạnh (> -60dBm).
  - 🟡 **Vàng:** Kết nối trung bình (-60 đến -80dBm).
  - 🔴 **Đỏ:** Kết nối yếu, nguy cơ mất Mesh (< -80dBm).
- 📱 **iOS Alert — Quyền 'Local Network':** Khi kích hoạt Mesh lần đầu, hệ thống hiển thị hộp thoại hướng dẫn riêng cho iOS: *"Để tính năng Mạng Mesh hoạt động theo đúng chính sách quyền riêng tư của Apple, vui lòng cấp quyền 'Tìm kiếm thiết bị mạng cục bộ (Local Network)' trong Cài đặt → TeraChat."*

## 39. Crypto-Shred Animation Spec

- **Trigger:** Lõi Rust phát tín hiệu `CRYPTO_SHRED_COMPLETE` (Xóa sạch bộ nhớ tạm).
- **Animation:** Toàn bộ text nhạy cảm trên màn hình (được đánh dấu bằng `is-private` class) thực hiện hiệu ứng **"Digital Dissolve"**:
  - Ký tự vỡ vụn thành các pixel `0x00` và bay lên trên (`translateY: -20px`, `opacity: 0`).
  - Thời gian: 400ms.
  - Sau animation, vùng text trống trơn hoặc quay về Skeleton state.
