# Design.md — TeraChat Design System

```yaml
# DOCUMENT IDENTITY
id: "TERA-DESIGN"
title: "TeraChat — Product Requirements Document (Design)"
version: "0.3.7"
status: "ACTIVE — Design Reference"
date: "2026-03-23"
audience: "Designer, Frontend Developer, Product Manager, Security Architect"
purpose:
  "Đặc tả hệ thống thiết kế UI/UX Glassmorphism, component library, UI state
  machine, animation specs, và security state visualization."

depends_on:
  - id: "TERA-FEAT"
    note: "IPC signals triggering UI state"
  - id: "TERA-FUNC"
    note: "User flows and enterprise access model"
  - id: "TERA-CORE"
    note: "Rust Core security events"

consumed_by:
  - "Tauri / Flutter frontend implementation"
```

---

# DESIGN CONTRACT — Non-Negotiable UI Rules

> Vi phạm bất kỳ rule nào dưới đây → **design reject, không merge**

### Visual Modes

| Mode            | Background          | Indicator            |
| --------------- | ------------------- | -------------------- |
| Online Mode     | Glass Light         | Blue #24A1DE         |
| Mesh Mode       | Dark Navy `#0F172A` | Radar Pulse          |
| License Invalid | Charcoal `#1A1A2E`  | Amber warning banner |

Mesh Mode và License Invalid **bắt buộc khác biệt hoàn toàn** với Online Mode.

### Glassmorphism Spec

```css
backdrop-filter: blur(20px);
background: rgba(255, 255, 255, 0.08);
border: 1px solid rgba(255, 255, 255, 0.12);
box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
```

### Typography

| Role               | Font                     |
| ------------------ | ------------------------ |
| Body               | Inter                    |
| Mono               | JetBrains Mono           |
| Display (headings) | System (platform-native) |

Không dùng system font cho body text.

### Accent Colors

| State            | Color   |
| ---------------- | ------- |
| Online           | #24A1DE |
| Warning          | #F59E0B |
| Danger           | #EF4444 |
| Success          | #10B981 |
| License Degraded | #F59E0B |
| License Locked   | #EF4444 |

### Layout Rule

Không sử dụng WhatsApp-style bubble chat. Layout phải theo:

```text
Data Density Model
Compact
Information First
Security Status Always Visible
```

---

## §1 Design Philosophy

TeraChat UI là giao diện của một công cụ doanh nghiệp bảo mật cao — không phải consumer messaging app. Triết lý thiết kế:

```text
Security Visible (trạng thái bảo mật luôn hiển thị)
Density Efficient (thông tin dense, không lãng phí)
Zero Noise (không animation không cần thiết)
Operational Clarity (admin không cần manual)
```

---

## §2 Enterprise Onboarding Flow

Vì TeraChat là enterprise-only, onboarding flow khác với consumer apps:

### 2.1 First Launch (No License)

```text
App Opens
     ↓
[Screen: "TeraChat — Enterprise Messenger"]
[Illustration: secure vault, minimal]
[Primary CTA: "Activate Enterprise License"]
[Secondary: "Contact Your IT Administrator"]
     ↓
License Activation Screen:
  - QR Code scan (từ IT Admin / MDM)
  - Manual domain + token entry
     ↓
License JWT validation (< 3s)
     ↓
Biometric enrollment for DeviceIdentityKey
     ↓
Welcome to {Organization Name}
```

### 2.2 License States trong UI

| State         | Visual                         | User Message                          |
| ------------- | ------------------------------ | ------------------------------------- |
| Valid         | Green badge top-right          | "Workspace: {org_name}"               |
| T-30 days     | Amber banner (Admin view only) | Admin Console warning only            |
| T-0 (expired) | Amber lock icon                | "Liên hệ IT Admin để gia hạn"         |
| T+90          | Red lock icon                  | "License hết hạn — không thể kết nối" |
| Invalid       | Full screen lockout            | "Thiết bị chưa được cấp phép"         |

---

## §3 Architecture Mapping

UI không xử lý logic bảo mật:

```text
UI Renderer (Flutter / Tauri)
     ↓ IPC (CoreSignal / UICommand)
Rust Core (crypto, DAG, mesh, license)
     ↓
Hardware Chip (Secure Enclave / TPM)
```

Frontend chỉ render state do Rust Core gửi lên.

---

## §4 Adaptive Glassmorphism State Machine

| State               | Visual                   | Trigger            |
| ------------------- | ------------------------ | ------------------ |
| `ONLINE`            | Glass white, blue accent | Internet connected |
| `ENCRYPTED_SESSION` | Glass blue, lock badge   | MLS session active |
| `MESH_FALLBACK`     | Dark navy, radar pulse   | No internet        |
| `EMERGENCY_MESH`    | Dark + amber warning     | EMDP active        |
| `LICENSE_WARNING`   | Glass + amber banner     | T-30 days          |
| `LICENSE_DEGRADED`  | Amber tint               | T-0 expired        |

---

## §5 Survival Mesh HUD

Mesh Mode UI phải hiển thị (top status bar):

```text
📡 Mesh Active · Nodes: 6 · BLE + Wi-Fi Direct · Latency: 220ms
```

### Radar Visualization

```text
Thiết bị của user ở trung tâm
Các node pulse outward theo khoảng cách thực
Border Node hiển thị màu xanh lá (có Internet)
```

---

## §6 Messaging Layout

```text
| Sidebar | Conversation | Tools |
```

Message block:

```text
[timestamp]  [sender name]  [security badge: E2EE ✓]
[message content — compact, information-dense]
[status: Delivered / Read / Pending]
```

---

## §7 Security Event Animations

Mọi security event **bắt buộc animation spec**.

### Self-Destruct (Remote Wipe)

```text
Timer ring collapse (400ms)
Message fragments dissolve from edges
Duration: 400ms total
```

### Crypto-Shred

```text
Data fragments → pixel noise → wipe to black
Duration: 350ms
```

### Magnetic Collapse (Session Revoked)

```text
UI elements collapse to center point
Fade to dark overlay
Duration: 300ms
```

### License Lockout Transition

```text
Soft amber overlay fades in (200ms)
Content blurs to 8px
Lock icon materializes center (100ms)
"Liên hệ IT Admin" button appears
```

---

## §8 Memory Zeroization Overlay

Khi Rust Core phát `CoreSignal::MemoryPressureWarning`:

```text
Overlay: dark glass (opacity 0.7)
Text: "SECURE MEMORY PURGE"
Progress bar: thin, teal, animated left-to-right
Duration: until purge complete
```

---

## §9 Byzantine Fault Indicator

Khi cluster phát hiện fault:

```text
⚠ Byzantine Fault Detected
Node isolation triggered — mesh topology reconfiguring
```

Hiển thị trong Survival Mesh HUD, không interrupt messaging.

---

## §10 Failure Containment Protocol (FCP)

Khi IPC signal `fcp_triggered`:

```text
Border: 4px solid #EF4444
Pulse animation: 1s interval
Badge: "SESSION CONTAINED"
```

---

## §11 Sealed Session View

Khi session bị sealed (SSA taint):

```text
Hazard stripe overlay (diagonal yellow-black)
Badge: "SESSION SEALED — Pending Review"
Subtext: "AI detected potential policy violation"
```

---

## §12 Memory Pressure Feedback

Khi IPC `memory_pressure_high`:

```text
Glassmorphism blur giảm: 20px → 8px
Banner (subtle): "System Resource Pressure — Reducing effects"
```

---

## §13 E2EE State Indicator

Header bar hiển thị luôn:

```text
🔒 E2EE Active · Key Epoch {N} · {org_name}
```

Khi re-keying:

```text
🔄 Rekeying session...
```

---

## §14 AI Mode Indicator

```text
🤖 AI: Local Secure    (SLM on-device, no cloud)
🤖 AI: VPS Enclave     (cloud, PII redacted)
⚠️ AI: Disabled        (Mesh Mode)
```

---

## §15 Enterprise Plugin View (.tapp)

IT Admin phê duyệt plugin → plugin xuất hiện trong launcher:

```text
[Plugin Icon]  [Plugin Name]
[Vendor badge] [Permission scope summary]
[Status: Active / Suspended / Pending Update]
```

End user không thể install, chỉ use or request to IT Admin.

---

## §16 IPC Signal → UI Mapping

| Signal                | UI Response                                     |
| --------------------- | ----------------------------------------------- |
| `session_established` | Enable chat; show E2EE badge                    |
| `mesh_mode_active`    | Switch Dark Navy UI; show Radar HUD             |
| `memory_zeroize`      | Show SECURE MEMORY PURGE overlay                |
| `crypto_shred`        | Run Crypto-Shred animation                      |
| `fcp_triggered`       | Show red border + FCP badge                     |
| `consensus_fault`     | Show Byzantine Fault indicator in Mesh HUD      |
| `license_warning`     | Show amber banner (Admin Console only)          |
| `license_degraded`    | Show amber tint + lock icon + contact IT prompt |
| `dead_man_deferral`   | Amber badge "Bảo mật tạm hoãn" (non-blocking)   |
| `emdp_shun_event`     | Toast: node removed from Mesh topology          |

---

## §17 Latency Visualization

```text
Latency: 45ms ●  (green: < 100ms)
Latency: 180ms ●  (amber: 100-300ms)
Latency: 450ms ●  (red: > 300ms)
```

---

## §18 Desktop Layout 🖥️

```text
| Sidebar (256px) | Conversation (flex) | Context Panel (320px, collapsible) |
```

---

## §19 Mobile Layout 📱

```text
Conversation Fullscreen
Sidebar: slide-in gesture (swipe right)
Context Panel: slide-in (swipe left)
```

---

## §20 Animation Timing

| Animation          | Duration  |
| ------------------ | --------- |
| Message send       | 120ms     |
| State change       | 200ms     |
| Security event     | 350-500ms |
| License transition | 300ms     |
| Mesh mode switch   | 500ms     |

---

## §21 GPU Capability Fallback

| Tier  | Condition            | Rendering                        |
| ----- | -------------------- | -------------------------------- |
| **A** | Hardware compositing | `backdrop-filter: blur(16-24px)` |
| **B** | Software compositing | `blur(8px)`, opacity 0.85        |
| **C** | No compositing       | Flat solid + border accent       |

Rust Core emit `GpuCapability { compositing_tier: u8 }` lúc init → UI chọn variant.

---

## §22 WASM Plugin Glass Card States

| State              | Glass Effect            | Border   | Meaning                       |
| ------------------ | ----------------------- | -------- | ----------------------------- |
| Active + Valid     | Frosted, high opacity   | Xanh lá  | Plugin trusted, network ready |
| Network I/O        | Moving gradient         | Blue     | Proxy processing request      |
| Rate Limit Warning | Warning Glow            | Amber    | Approaching quota limit       |
| Mesh Mode          | Heavy blur, low opacity | Grey     | Isolated from Internet        |
| Revoked            | Shatter → Blood-Red     | Deep red | IT Admin revoked              |
| Updating           | Shimmer Water Effect    | Teal     | New version installing        |

---

## §23 Admin Console UI Patterns

### License Status Dashboard

```text
[License Status Card]
  Tier: Enterprise | Seats: 234/500
  Status: Active ✓ | Expires: 2027-03-15
  [Renew] [Export Report]
```

### Plugin Registry Panel

```text
[Available] [Installed] [Pending Review]

Plugin Card:
  [Icon] [Name] [Publisher] [Tier Badge]
  [Permissions: network.egress, storage.persist]
  [Security Score: 95/100]
  [Deploy to Workspace] [View Security Report]
```

---

## CHANGELOG

| Version | Date       | Summary                                                                                                                  |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------ |
| 1.0.0   | 2026-03-23 | Enterprise repositioning: license states, onboarding flow, plugin admin controls, align với enterprise-only access model |
| 0.2.6   | 2026-03-13 | Thêm Adaptive Glassmorphism HUD & Survival HUD, WASM states, GPU tiers                                                   |
