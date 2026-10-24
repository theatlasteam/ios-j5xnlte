# ios-j5xnlte

A from-scratch attempt to run **iOS** on a **Samsung Galaxy J5** (MSM8916 / Snapdragon 410) — real XNU boot chain, real hardware, no themes.

> Status: **boot chain proven on hardware; kernel path blocked and documented.** See the site in `docs/`.

## Hardware (verified on device via lk2nd)

| | |
|---|---|
| SoC | Qualcomm MSM8916 / Snapdragon 410, 4× Cortex-A53 (ARMv8-A, arm64-capable) |
| RAM | ~1.9 GB |
| Display | 720×1280, `ss_dsi_panel_S6E8AA5X01_AMS520KT01_HD` |
| Storage | eMMC |
| Bootloader | unlocked (`secure:yes`), lk2nd flashed |
| Interrupts | GIC-400 (GICv2) |

## What has been done

1. **Bootloader unlocked** — adb root, full partition table captured.
2. **lk2nd flashed** — written to `boot` offset 0, read-back SHA-256 verified. Fastboot live: `product: lk2nd-msm8916`.
3. **Hardware auto-detected** — panel, storage, RAM.

## The iOS 10 blocker — and the clean way around it

The public **`xnu-3789.70.16`** (iOS 10) source tree contains **only x86_64 kernel configurations** — no `MASTER.arm64`. So a clean source build of an **arm64 iOS 10 kernel is impossible**.

But the cutoff is exactly iOS 10. From **`xnu-4570` (iOS 11)** onward Apple published arm64 configs:

| tag | iOS gen | arm64 configs |
|---|---|---|
| `xnu-3789.70.16` | iOS 10 | none (x86_64 only) |
| `xnu-4570.71.2` | iOS 11 | `MASTER.arm64` |
| `xnu-4903.221.2` | iOS 12 | `MASTER.arm64` |
| `xnu-6153.141.1` | iOS 13 | `MASTER.arm64` |
| `xnu-7195.141.2` | iOS 14 | `MASTER.arm64.iPhoneOS` |

So instead of decrypting Apple firmware (the "gray" route), we **target a slightly newer iOS**:

- **iOS 12 (`xnu-4903`)** — 1 GB-RAM class (iPhone 5s/6); best fit for this device's 1.9 GB. **Chosen target.**
- **iOS 14 (`xnu-7195`)** — explicit `MASTER.arm64.iPhoneOS` config; easiest build support, but 2 GB class.

No kernelcache decryption required.

## Why it's hard (vs ios-sweet)

| Component | ios-sweet (SM7150) | This device (MSM8916) |
|---|---|---|
| Interrupts | GICv3 redistributor | GIC-400 / GICv2 MMIO |
| Storage | UFS host driver | eMMC / SDCC |
| Display | AppleCLCD, iPhone X panel | MDSS/DSI, S6E8AA5X01 |
| DDR | ~0xb0000000 upper bank | 2 GB @ 0x80000000 |
| Kernel | xnu-8796, buildable arm64 | xnu-3789, x86_64-only source |

## Layout

```
.github/workflows/probe-xnu3789.yml   reproducible feasibility report for the arm64 build
docs/                                 GitHub Pages site
```

## Credits

Stands on the work of [ios-sweet](https://github.com/dipa-studio/ios-sweet) (XNU on SM7150) and [msm8916-mainline](https://github.com/msm8916-mainline) (lk2nd + mainline Linux). Not affiliated with Apple or Samsung.
