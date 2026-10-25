# ios-j5xnlte

A from-scratch attempt to run **iOS** on a **Samsung Galaxy J5** (MSM8916 / Snapdragon 410) — real XNU boot chain, real hardware, no themes.

> Status: **boot chain proven on hardware; public XNU arm64 kernel now compiles in CI.** The remaining blocker is architectural: Cortex-A53 has **no 16 KB translation granule**, which the stock iOS arm64 kernel/userland assumes. See the site in `docs/`.

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
2. **lk2nd flashed** — written to `boot` offset 0, read-back SHA-256 verified. Fastboot live: `product: lk2nd-msm8916`, hardware auto-detected. (This disproves the claim that no lk2nd build exists for `j5xnlte` — the generic `msm8916` image boots here.)
3. **Public XNU arm64 build** — `xnu-4903.221.2` (iOS 12) is built from the public tree on macOS CI. Every 2018-era build-system/toolchain incompatibility was worked around: py2 scripts, removed CTF tools, internal `edm` arch resolution, `-Werror`, `.s` preprocessing, a rewritten `genassym` parser, and the closed `libfirehose_kernel` / MIG symbols (stubbed). See `.github/workflows/probe-xnu.yml`.

## The real show-stopper: 16 KB pages on Cortex-A53

Compiling is **not** booting. The stock iOS arm64 kernel and userland are built around a **16 KB translation granule**. All four cores in MSM8916 are **Cortex-A53**, which implements only the 4 KB and 64 KB granules — `ID_AA64MMFR0_EL1.TGran16 == 0`. This is the same reason the `ios-topaz` project parks its A53-class cores; on the J5 there are no other cores to fall back to.

So the stock path is dead on this SoC. Two honest options remain:

- **4 KB-page XNU** in the style of **UniXNU** (BCM2837 4K layout + the shared 4K patches), retargeted to `xnu-4903`. Nobody has demonstrated iOS 12 userland on a 4 KB kernel on MSM8916 — this is a research programme, not a port.
- **Kernel-only bring-up first** (entry, timers, GICv2, console/framebuffer, RAM-disk PID 1), then decide whether the iOS 12 userland tolerates 4 KB pages.

Everything else (GICv2 vs GICv3, SDHCI/eMMC vs UFS, MDSS/DSI vs AppleCLCD) is a large but conventional driver project on top of that.

## What the public drop actually contains (and the iOS 10 “blocker” re-stated)

Important correction: **shipped iOS kernels were always ARM/ARM64.** For iOS 10 the shipping kernels were e.g. `xnu-3789.70.16~4/RELEASE_ARM64_S8000`. What is *not* public is the iOS platform configuration and the proprietary iOS drivers. The opensource.apple.com drop for `xnu-3789` is effectively the macOS variant: its `config/` contains only `MASTER` and `MASTER.x86_64`. So the accurate statement is:

> The public `xnu-3789` drop has no arm64 config — **not** “iOS 10 never had an arm64 kernel”.

Also, searching for a literal `MASTER.arm64` is a weak test. Real machine configs are named like `S5L8960X`, `T8015`, etc. What matters is the `MASTER.*` file plus `SUPPORTED_*_MACHINE_CONFIGS` in `makedefs/`.

The cutoff is real, though. From **`xnu-4570` (iOS 11)** onward the public drop includes arm/arm64:

| tag | public arm64 configs | notes |
|---|---|---|
| `xnu-3789.70.16` | none (`MASTER`, `MASTER.x86_64` only) | macOS-oriented drop |
| `xnu-4570.71.2` | `MASTER.arm64` | first public arm64 drop |
| `xnu-4903.221.2` | `MASTER.arm`, `MASTER.arm64`, `MASTER.arm64.bcm2837` | **chosen target** |
| `xnu-6153.141.1` | `MASTER.arm64` | iOS 13 |
| `xnu-7195.141.2` | `MASTER.arm64.iPhoneOS` | iOS 14 |

`xnu-4903` even ships Apple SoC machine configs — `SUPPORTED_ARM64_MACHINE_CONFIGS = S5L8960X T7000 T7001 S8000 S8001 T8010 T8011 BCM2837`, with `DEFAULT_ARM64_MACHINE_CONFIG := S5L8960X` — which is why the CI build is `DEVELOPMENT^ARM64^S5L8960X`.

But “has arm64 configs” ≠ “complete iOS kernel”. The drop still lacks closed pieces (we hit `-lfirehose_kernel` at link) and all iOS platform/userland integration. So this is a **toolchain checkpoint**, not a bootable iOS kernel.

Target choice:

- **iOS 12 (`xnu-4903`)** — 1 GB-RAM class (iPhone 5s/6); best fit for this device's 1.9 GB. **Chosen target.**
- **iOS 14 (`xnu-7195`)** — explicit `MASTER.arm64.iPhoneOS` config; easiest build support, but 2 GB class.

No kernelcache decryption is involved.

## Why it's hard (vs ios-sweet)

| Component | ios-sweet (SM7150) | This device (MSM8916) |
|---|---|---|
| Interrupts | GICv3 redistributor | GIC-400 / GICv2 MMIO |
| Storage | UFS host driver | eMMC / SDCC |
| Display | AppleCLCD, iPhone X panel | MDSS/DSI, S6E8AA5X01 |
| DDR | ~0xb0000000 upper bank | 2 GB @ 0x80000000 |
| Kernel | xnu-8796, buildable arm64 | xnu-4903, buildable arm64 (verified in CI) |

## Layout

```
.github/workflows/probe-xnu3789.yml   reproducible feasibility report for the arm64 build
docs/                                 GitHub Pages site
```

## Credits

Stands on the work of [ios-sweet](https://github.com/0xSojalSec/ios-sweet) (XNU on SM7150), [UniXNU](https://github.com/UniXNU/UniXNU) (4 KB-page XNU) and [msm8916-mainline](https://github.com/msm8916-mainline) (lk2nd + mainline Linux). Not affiliated with Apple or Samsung. No Apple firmware, IPSW, kernelcache or trust cache is included; the XNU source is public under the APSL.
