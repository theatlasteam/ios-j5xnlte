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

## The blocker (important)

The public **`xnu-3789.70.16`** (iOS 10 generation) source tree contains **only x86_64 kernel configurations**:

```
$ ls xnu-3789/config | grep -i arm      # nothing
$ ls xnu-3789/config | grep x86_64
BSDKernel.x86_64.exports
MASTER.x86_64
...
```

Apple never published ARM64 kernel configs for that era (there were no arm64 Macs). So a clean source build of an **arm64 iOS 10 kernel is not possible**. Modern XNU (iOS 16 era) *is* buildable arm64 because Apple Silicon made those configs public — which is why `ios-sweet` works and this doesn't, yet.

Remaining options for a real iOS 10 arm64 kernel:
- Apple's encrypted kernelcache (legally gray; QEMU-friendly but bound to Apple drivers, so it doesn't give MSM8916 drivers directly), or
- a newer iOS generation with a buildable arm64 kernel (wrong ABI for iOS 10 userland).

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
