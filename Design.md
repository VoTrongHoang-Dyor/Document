# Design.md — TeraChat Alpha v0.3.0

```yaml
# DOCUMENT IDENTITY
id:       "TERA-DESIGN"
title:    "TeraChat — Product Requirements Document (Design)"
version:  "2.0"
audience: "Designer, Frontend Developer, Product Manager"
purpose:  "Đặc tả hệ thống thiết kế UI/UX Glassmorphism, component library, UI state machine và animation specs."

ai_routing_hint: |
  "AI mở file này khi người dùng hỏi về UI design, Glassmorphism, animation, components, hoặc các trạng thái (states) của UI."
```


> **Status:** `ACTIVE — Design Reference`
> **Audience:** UX/UI Designer · Frontend Engineer · Product Manager · Security Architect
> **Scope:** Glassmorphism Design System · Component Library · Screen Flows · Animation Specs · Security State Visualization · Survival Mesh HUD
> **Platform:** Desktop 🖥️ · Laptop 💻 · Mobile 📱
> **Last Updated:** 2026-03-15
> **Depends On:** → TERA-FEAT (IPC signals triggering UI state), → TERA-FUNC (User flows), → TERA-CORE (Rust Crypto Core)
> **Consumed By:** React Native / Tauri frontend implementation

---

# CHANGELOG

| Version | Date       | Change Summary                                                                      |
| ------- | ---------- | ----------------------------------------------------------------------------------- |
| v0.3.5  | 2026-03-13 | Add §37 Adaptive Glassmorphism State Machine & Survival HUD                         |
| v0.3.0  | 2026-03-11 | Add §30–36 Memory pressure UI · Byzantine fault indicators · Crypto-Shred animation |
| v0.2.9  | 2026-03-05 | Add §28 Self-Destruct Visualization · §29 Memory Zeroization overlay                |
| v0.2.8  | 2026-03-04 | Add §25 Magnetic Collapse animation · §26 FCP Red Border overlay                    |
| v0.2.0  | 2026-02-18 | Initial Glassmorphism UI system                                                     |

---

# DESIGN CONTRACT — Non-Negotiable UI Rules

> Vi phạm bất kỳ rule nào dưới đây → **design reject, không merge**

### Visual Modes

| Mode        | Background          | Indicator   |
| ----------- | ------------------- | ----------- |
| Online Mode | Glass Light         | Blue        |
| Mesh Mode   | Dark Navy `#0F172A` | Radar Pulse |

Mesh Mode **bắt buộc khác Online Mode**.

---

### Glassmorphism Spec

```
Backdrop Blur: 20px
Background: rgba(255,255,255,0.08)
Stroke: 1px rgba(255,255,255,0.12)
Shadow: 0 20px 60px rgba(0,0,0,0.25)
```

---

### Typography

| Role | Font           |
| ---- | -------------- |
| Body | Inter          |
| Mono | JetBrains Mono |

Không dùng **system font**.

---

### Accent Colors

| State   | Color   |
| ------- | ------- |
| Online  | #24A1DE |
| Warning | #F59E0B |
| Danger  | #EF4444 |

---

### Layout Rule

Không sử dụng **WhatsApp style bubble chat**.

Chat layout phải theo:

```
Data Density Model
Compact
Information First
```

---

# §1 Design Philosophy [CONCEPT] [UI]

TeraChat UI được thiết kế theo triết lý:

```
Security Visible
Density Efficient
Zero Noise
Operational Clarity
```

UI phải thể hiện rõ:

* trạng thái **network**
* trạng thái **crypto**
* trạng thái **system integrity**

---

# §2 Architecture Mapping [ARCHITECTURE] [UI]

UI không xử lý logic bảo mật.

```
UI Renderer
    ↓ IPC
Rust Core
    ↓
Crypto Engine
```

Frontend chỉ render **state do Rust Core gửi lên**.

---

# §3 Control Plane vs Data Plane Visualization [ARCHITECTURE] [UI]

| Plane         | Purpose                  | Transport               |
| ------------- | ------------------------ | ----------------------- |
| Control Plane | Auth / session / routing | QUIC / BLE              |
| Data Plane    | Message / file transfer  | Wi-Fi Direct / Internet |

### UI Indicator

```
Control: QUIC ✓
Data: Wi-Fi Direct 480 Mbps
```

---

# §4 Adaptive Glassmorphism State Machine [UI]

UI thay đổi theo state machine:

```
Online
↓
Encrypted Session
↓
Mesh Fallback
↓
Emergency Mesh
```

### State mapping

| State   | Visual      |
| ------- | ----------- |
| Online  | Glass white |
| Secure  | Glass blue  |
| Warning | Amber glow  |
| Danger  | Red overlay |

---

# §5 Survival Mesh HUD [UI]

Mesh Mode UI phải hiển thị:

```
Mesh Active
Nodes: 6
Transport: BLE + Wi-Fi Direct
Latency: 220ms
```

### Radar Visualization

```
User device center
Nodes pulse outward
```

---

# §6 Messaging Layout [UI]

Layout:

```
| Sidebar | Conversation | Tools |
```

Message block:

```
timestamp
sender
message content
security badge
```

---

# §7 Security Event Animation [SECURITY] [UI]

Mọi security event **bắt buộc animation spec**.

---

## Self-Destruct

```
Timer ring collapse
Message fragment dissolve
```

Duration:

```
400ms
```

---

## Crypto-Shred

Visual:

```
data fragments
pixel noise
wipe
```

Duration:

```
350ms
```

---

## Magnetic Collapse

Used when:

```
session revoked
```

Animation:

```
elements collapse to center
fade out
```

---

# §8 Memory Zeroization Overlay [SECURITY] [UI]

Khi Rust Core phát IPC:

```
memory_zeroize
```

UI hiển thị:

```
SECURE MEMORY PURGE
```

Overlay:

```
dark glass
progress bar
```

---

# §9 Byzantine Fault Indicator [SECURITY] [UI]

Nếu cluster phát hiện fault:

```
consensus_fault_detected
```

UI hiển thị:

```
⚠ Byzantine Fault
Node isolation triggered
```

---

# §10 Failure Containment Protocol (FCP) [SECURITY] [UI]

UI hiển thị:

```
RED BORDER
```

khi IPC signal:

```
fcp_triggered
```

---

# §11 Sealed Session View [SECURITY] [UI]

Khi session bị sealed:

```
hazard stripe overlay
```

Indicator:

```
SESSION SEALED
```

---

# §12 Memory Pressure Feedback [UI] [PERFORMANCE]

Nếu thiết bị thiếu RAM:

IPC:

```
memory_pressure_high
```

UI hiển thị:

```
System Resource Pressure
Reducing visual effects
```

Glass blur giảm:

```
20px → 8px
```

---

# §13 E2EE State Indicator [SECURITY] [UI]

Trạng thái encryption hiển thị trên header.

```
E2EE Active
Key Epoch 304
```

Nếu rekey:

```
Rekeying session
```

---

# §14 DID Identity Visualization [SECURITY] [UI]

Identity badge:

```
Verified DID
```

Key fingerprint hiển thị:

```
SHA256 fingerprint
```

---

# §15 AI Mode Indicator [UI]

Nếu AI SLM hoạt động:

```
AI Mode: Local Secure
```

hoặc

```
AI Mode: External ⚠
```

---

# §16 WASM Sandbox App View (.tapp) [PLUGIN] [UI]

Marketplace apps chạy trong:

```
WASM Sandbox
```

UI hiển thị:

```
App Permissions
```

---

# §17 IPC Signal Mapping [IMPLEMENTATION] [UI]

Rust Core gửi IPC → UI update.

| Signal              | UI Response        |
| ------------------- | ------------------ |
| session_established | enable chat        |
| mesh_mode_active    | switch dark UI     |
| memory_zeroize      | show purge overlay |
| crypto_shred        | run animation      |
| fcp_triggered       | red border         |
| consensus_fault     | fault warning      |

---

# §18 Latency Visualization [PERFORMANCE] [UI]

```
Latency: 45 ms
```

Color:

| Latency | Color |
| ------- | ----- |
| <100ms  | Green |
| 100-300 | Amber |

> 300 | Red |

---

# §19 Throughput Indicator [PERFORMANCE] [UI]

```
Transfer: 120 Mbps
```

---

# §20 Attack Surface Awareness [SECURITY] [UI]

Nếu suspicious activity:

```
Security anomaly detected
```

---

# §21 Desktop Layout 🖥️ [PLATFORM] [UI]

```
| Sidebar | Conversation | Tools |
```

---

# §22 Mobile Layout 📱 [PLATFORM] [UI]

```
Conversation Fullscreen
```

Sidebar slide.

---

# §23 Laptop Layout 💻 [PLATFORM] [UI]

Adaptive grid.

---

# §24 Animation Timing [UI]

| Animation      | Duration  |
| -------------- | --------- |
| Message send   | 120ms     |
| State change   | 200ms     |
| Security event | 350-500ms |

---

# §25 Magnetic Collapse Animation

Used for:

```
session destruction
```

---

# §26 FCP Red Border Overlay

```
border: 4px red
pulse animation
```

---

# §27 Hazard Stripe Overlay

```
diagonal yellow-black stripes
```

---

# §28 Ruthless Self-Destruct Visualization

Message:

```
auto wipe
```

---

# §29 Memory Zeroization Visualization

```
glass overlay + wipe
```

---

# §30 Memory Pressure UI

Blur reduce.

---

# §31 Byzantine Fault Indicators

Cluster fault detection UI.

---

# §32 Crypto-Shred Animation

Data wipe visualization.

---

# §33 Security State Machine

```
Normal
↓
Secure
↓
Warning
↓
Containment
```

---

# §34 Survival Mesh Energy Mode

Battery optimization.

```
BLE control
```

---

# §35 Device Indicator

Device type icon.

📱
💻
🖥️

---

# §36 Network Transport Indicator

```
BLE
Wi-Fi Direct
QUIC
```

---

# §37 Adaptive Glassmorphism HUD

```
Network
Crypto
Mesh
AI
```

Displayed in **top status bar**.

---


---

## Mục Mới: Glassmorphism WASM States & Network Topology UX [UI] [PLUGIN]

### DESIGN-WASM-01: Glass Card States cho .tapp

| Trạng thái | Hiệu ứng Glass Card | Màu Viền | Nghĩa |
|---|---|---|---|
| Online + DID hợp lệ | Frosted Glass, độ trong suốt cao | Xanh lá (Trust Indicator) | .tapp đáng tin cậy, mạng đầy đủ |
| Network I/O đang truyền | Dải gradient mờ di chuyển ở góc | Xanh lam nhạt | Proxy đang xử lý API request |
| Rate Limit Warning | Warning Glow | Cam | .tapp gọi API quá nhanh |
| Mesh Mode | Làm mờ mạnh, độ trong suốt giảm | Xám | .tapp bị cô lập khỏi Internet |
| Kill-Switch (Zero-day) | Shatter Effect → Blood-Red frosted | Đỏ máu | `.tapp` bị vô hiệu hóa toàn cầu |
| Re-hydrating | Shimmering Water Effect | Mờ xanh | `.tapp` đang thức dậy từ Snapshot |
| Hard Timeout (WASM) | Shimmering → Đỏ Neon → Crack → Rebuild | Neon đỏ → Trong suốt | Snapshot lỗi, Fresh Start |
| Ring Buffer Overflow | Viền chớp nháy | Cam (Amber) | Dữ liệu bị gián đoạn do máy chậm |

### DESIGN-WASM-02: IPC & Trust Hub UI

- 💻🖥️ **Glass Bridge Animation:** Khi `.tapp` CRM yêu cầu share sang `.tapp` Kế toán, một cầu nối thủy tinh xuất hiện nối giữa 2 Glass Card + Modal xác nhận người dùng.
- 💻🖥️ **Trust Hub (Online Mode):** Giao diện Glassmorphism. Các luồng dữ liệu được cấp phép tự động hiện dưới dạng Bio-lines phát sáng mờ nối giữa các Glass Card. Kéo thả → Revoke Trust.
- 📱 **Auto-save Bio-dot:** Khi `.tapp` lưu transient state, chấm sáng sinh học nhỏ chớp tắt nhẹ ở góc phải Glass Card.

### DESIGN-WASM-03: AI SLM Visual Feedback

- 💻📱 **AI Core Glow (Online Mode):** Khi SLM đang chạy, Control Bar hiện luồng huỳnh quang chạy dọc mép kính mờ.
- 💻📱 **Typing Effect:** Glass Card của `.tapp` nhận Token SLM có hiệu ứng "gợn sóng sinh học" nhỏ khi từng từ được stream về.
- 📱 **KV-Cache Loading:** Crystalline Progress Bar mỏng ở cạnh dưới Glass Card trong ~0.2s.
- 📱 **Mesh/Survival:** Tất cả hiệu ứng AI tắt hoàn toàn.

### DESIGN-WASM-04: Network Topology Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    COMPANY NETWORK                           │
│                                                             │
│  ┌─────────────┐     mTLS/PKI      ┌─────────────────────┐ │
│  │   Branch A  │◄─────────────────►│      HQ VPS         │ │
│  │  Relay Nodes│                   │  (Control Plane)    │ │
│  │ (Desktop/   │                   │  WebSocket/gRPC     │ │
│  │  Laptop)    │                   └──────────┬──────────┘ │
│  └──────┬──────┘                              │            │
│         │ BLE/Wi-Fi Direct                    │ VPN        │
│  ┌──────▼──────┐                   ┌──────────▼──────────┐ │
│  │Light Nodes  │                   │    Branch B         │ │
│  │(Mobile iOS/ │                   │  Relay Nodes        │ │
│  │  Android)   │                   │  (Desktop)          │ │
│  └─────────────┘                   └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### DESIGN-WASM-05: mDNS P2P → TURN Server Relay Degradation Flowchart

```
[Người dùng nhấn "Gọi Video"]
           ↓
[Host ICE Gathering từ Pre-warmed ICE Pool]
           ↓
[SDP gửi mDNS Candidate ← terachat-node-xxxx.local]
           ↓
   [200ms timeout?]
    /              \
  Không             Có
   ↓                ↓
[P2P Direct]   [Restricted NAT/Firewall detected]
[Network Shield:    ↓
 "P2P (Direct)"]  [Fallback → Internal TURN Server (DMZ)]
                   ↓
              [WebRTC DTLS-SRTP qua Relay]
                   ↓
              [Network Shield: "Relayed (E2EE)"]
```

### DESIGN-WASM-06: Online/Mesh UI Transition States

| Mode | UI Theme | Glass Opacity | Hiệu ứng | Pin Priority |
|---|---|---|---|---|
| Online (Mặc định) | Light/Frosted Glass | Cao | Gradient nhẹ, blur | Normal |
| Intermittent | Dark Glass dần | Trung bình | Shimmer data sync | Bình thường |
| Mesh (>10 phút mất mạng) | Dark/Cyberpunk | Thấp | Biểu tượng 📡 Survival Mesh Active | Cao |
| Re-syncing | Dark → Light | Tăng dần | Thanh "Đang xác thực Zero-Trust..." | Normal |
| Kill-Switch | Blood-Red overlay | Max | Shatter Animation → Shield icon | N/A |

### DESIGN-WASM-07: Video Call Security UX

- 💻📱 **Insta-Connect:** Khi nhấn gọi, Frosted Glass Ring bao Avatar người nhận sáng rực Xanh Neon ngay lập tức (Pre-warmed ICE Pool). Không có màn hình "Đang kết nối..." chờ đợi.
- 💻 **P2P Live Indicator:** Orbiting Glow viền gradient chạy vòng quanh Glass Card khi WebRTC active.
- 💻 **Hardware Security Badge:** Biểu tượng Chip lục giác màu Xanh lục ở góc trên phải màn hình Video Call ("Hardware Secured Shield").
- 💻📱 **mDNS Masking:** Mục "IP LAN" trong Settings bị Frosted Blur → "Được bảo vệ bởi mDNS Masking".

### DESIGN-WASM-08: Admin DKG Control Panel

- 🗄️ **Dark Glassmorphism Command Center:** 7 trụ tinh thể đại diện 7 node DKG. Bio-lines Cryptographic chạy đan chéo khi SMPC đang diễn ra.
- 🗄️ **DKG Refresh Ritual:** Các đường sinh học xác thực → "Self-healing Network" hoàn tất.
- 🗄️ **BFT Emergency:** Node phá hoại → Shattered Glass animation → Đẩy ra khỏi Topology Graph. `FORCED_KEY_ROTATION_SUCCESS` hiện lên.
- 🗄️ **KILL_DIRECTIVE Pending:** "Pending Signatures: 2/5" → đủ 5 → lệnh phát đi.

### DESIGN-WASM-09: Cryptographic Erasure UI

- 💻🖥️ **TOMBSTONE Animation (Online/Desktop):** Bong bóng chat của A: kính rạn nứt từ từ → Dust Particle Effect bay mất. Để lại Panel kính viền đỏ sẫm: "Dữ liệu đã được tiêu hủy vĩnh viễn theo Quyền Lãng quên (GDPR Compliance)."
- 📱 **Mesh Silent Erasure:** Xóa khóa âm thầm. Không render, tiết kiệm RAM/pin.
- 💻📱 **Rolling Key Eviction UI:** Khi Lease Renewal thành công, viền Glass Card Chat lóe Cyan Sweep 0.2s. Biểu tượng khóa: "Khóa phiên đang được bảo vệ (Cập nhật 2 phút trước)".


---

## Mục Mới: GPU Capability Tiers, Huawei Breakpoints & XPC Recovery States [UI] [PLATFORM]

### DESIGN-GPU-01: GPU Capability Fallback Matrix

| Tier | Điều kiện | Glassmorphism Rendering | CSS |
|---|---|---|---|
| **Tier A** | GPU Hardware Compositing | Full Glass: `backdrop-filter: blur(16-24px)` | `transform: translateZ(0); will-change: backdrop-filter` |
| **Tier B** | Software Compositing | Frosted Glass Lite: `blur(8px)`, `opacity: 0.85` | `backdrop-filter: blur(8px)` |
| **Tier C** | No Compositing (Intel UHD 620 cũ) | Flat Solid với border accent | `background: rgba(255, 255, 255, 0.75)` |

```css
.glass-layer {
  transform: translateZ(0);          /* Force GPU composite */
  will-change: backdrop-filter;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  background: rgba(255, 255, 255, 0.75); /* Tier C fallback */
}
```

Rust Core detect WebView2 GPU caps lúc init → emit `GpuCapability(has_backdrop_filter: bool)` → UI render Glass hoặc Flat variant.

### DESIGN-GPU-02: Responsive States cho Mesh Role Changed

| UI State | Trigger | Banner | Theme |
|---|---|---|---|
| Normal Operation | Online/Mesh | - | Normal |
| **MeshRoleChanged** | iOS handover Super Node sang Desktop | Toast: "Đã chuyển vai trò Relay sang [tên thiết bị]" | Dark subtle |
| AWDL Unavailable | Hotspot active / CarPlay | Warning bar: "Hotspot đang bật — Mesh chuyển sang BLE. Voice tạm không khả dụng." | Amber |
| Voice Drop | AWDL timeout 30s | Notification: "Cuộc gọi bị ngắt do mất kết nối Mesh" | Red |

### DESIGN-GPU-03: XPC Crash Recovery UI State

- 💻 **macOS:** Khi XPC Worker crash giữa Smart Approval → hiển thị modal:
  - *"Phiên ký bị gián đoạn. Vui lòng ký lại."*
  - Nút primary: "Ký lại" | Nút secondary: "Bỏ qua"
  - Glass Modal viền cam (Warning Indicator)

### DESIGN-GPU-04: Huawei HarmonyOS Breakpoints

- 📱 **Breakpoint Huawei:** Tuân thủ HarmonyOS Design Language (tương tự Material 3 nhưng có adaptation riêng). Padding mặc định 16dp, đỉnh status bar theo HarmonyOS spec.
- 📱 **Glassmorphism trên Huawei:** wasmtime JIT có sẵn → Tier A full Glass.
- 📱 **Font hệ thống:** HarmonyOS Sans (fallback: system-ui).

### DESIGN-GPU-05: Conflict Resolution UI

- 💻📱🖥️ **Online Conflict (Shadow DAG):** Modal Glassmorphism hiện 2 cột: "Phiên bản của [Bạn]" và "Phiên bản của [Đồng nghiệp]". Toolbar merge: "Giữ của tôi", "Giữ của họ", "Gộp thủ công".
- 📱💻 **Mesh Conflict Marker:** Badge ⚠️ trên document với tooltip "Mâu thuẫn phát hiện — sẽ được giải quyết khi có kết nối đầy đủ".
- 🚫 **Không bao giờ silent LWW** trên document `content_type = CONTRACT | POLICY | APPROVAL`.

### DESIGN-GPU-06: AES-NI Performance Warning

- 📱💻 **Software Crypto Warning:** Trong Settings > Bảo mật, chip không có AES-NI → badge nhỏ: *"Chế độ mã hóa phần mềm — hiệu suất thấp hơn. Nâng cấp thiết bị để cải thiện."*

### DESIGN-GPU-07: License Graceful Degradation UI

| Thời điểm | UI | Ảnh hưởng hoạt động |
|---|---|---|
| T-30 ngày | Banner vàng trong Admin Console | Không ảnh hưởng |
| T-0 | Admin Console partial lock | Chat/Mesh bình thường, AI + add user bị khóa |
| T+90 | System refuse new bootstrap | App đang chạy OK, không restart được |
| Gia hạn | JWT mới → restore trong <5s | Không restart |
