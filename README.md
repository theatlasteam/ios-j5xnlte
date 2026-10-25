# ios-j5xnlte

A from-scratch attempt to run **iOS** on a **Samsung Galaxy J5** (MSM8916 / Snapdragon 410) — real XNU boot chain, real hardware, no themes.

> Status: **boot chain proven on hardware; a public-source `xnu-4903` arm64 kernel now builds and links in CI.** It is configured as `S5L8960X` (Apple A7 / Cyclone), which uses a **4 KB hardware granule** — a granule Cortex-A53 *does* implement. The page-size blocker was overstated; the real remaining work is Apple-specific CPU/platform bring-up and drivers. See the site in `docs/`.

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

## Page size: the 16 KB “show-stopper” was overstated

The earlier claim here was that stock iOS arm64 assumes a 16 KB translation granule, which Cortex-A53 lacks. The code says otherwise for the machine config we build:

- `S5L8960X` maps to **`APPLECYCLONE` (A7)** in `pexpert/pexpert/arm64/board_config.h`.
- `APPLECYCLONE` — like `APPLETYPHOON` (A8) — does **not** define `__ARM_16K_PG__`. Only `APPLETWISTER`/`APPLEHURRICANE`/`APPLEMONSOON` (A9/A10/A11) do.
- Therefore `ARM_PGSHIFT = 12` and `TCR_TG0_GRANULE_SIZE = TCR_TG0_GRANULE_4KB` in this build. The CI kernel is a **4 KB-granule kernel**.
- With >1 GB RAM, `arm_init.c` sets `PAGE_SHIFT_CONST = PAGE_MAX_SHIFT` (16 KB VM pages) and uses `__ARM64_PMAP_SUBPAGE_L1__` to back them with 4 KB hardware pages; it can also be forced to 4 KB VM pages (`radar_20804515=0` + `-use_hwpagesize`).

So the J5 does not need a made-from-scratch 4 KB port just to get page tables. iOS 12 shipped on the 4 KB-granule A7/A8, so a 4 KB-capable iOS 12 userland exists. The genuine remaining problems are different:

- `start.s` applies **Cyclone-specific writes to Apple HID registers** (`HID0/1/3/5/8`) that do not exist on Cortex-A53; these must be skipped or guarded.
- Apple CPU/platform identification, timers, interrupt controller, and the platform expert still assume Apple hardware.
- GICv2, eMMC/SDCC, MDSS/DSI, and iOS userland integration remain a large driver project.

Older iOS does **not** rescue this. iOS 7–10 on 32-bit devices did use 4 KB pages (and A53 runs AArch32), but the public drops for those releases contain **no ARM source at all** — `xnu-2422`, `xnu-2782`, `xnu-3248`, and `xnu-3789` ship only `osfmk/i386`/`x86_64` and `config/MASTER{,.x86_64}`. The first public drop with `osfmk/arm` + `osfmk/arm64` is **`xnu-4570` (iOS 11)**, and its 32-bit targets are Apple Watch (`S7002/T8002/T8004`), not iPhone. So “older iOS” trades a non-blocker for a real one: no public ARM kernel source.


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
