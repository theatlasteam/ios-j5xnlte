# Milestone 2 — QEMU bring-up

Goal: boot **our own** `xnu-4903` kernel in QEMU and get a serial line out of it,
then iterate toward a ramdisk `launchd`. No Apple firmware, no kernelcache, no
decryption.

## Why BCM2837, not S5L8960X

The first CI build used `S5L8960X` (Apple A7). That was the wrong base for this
device:

| | S5L8960X (A7) | BCM2837 (Pi 3) | MSM8916 (J5) |
|---|---|---|---|
| CPU | Cyclone | **Cortex-A53** | **Cortex-A53** |
| Page granule | 4 KB | **4 KB** | **4 KB** |
| Interrupts | Apple AIC | **GIC-400 / GICv2** | **GIC-400 / GICv2** |
| UART | Apple | **mini-UART** | Qualcomm |
| xnu-4903 config | yes | **yes** | needs a new machine config |

`xnu-4903` ships `config/MASTER.arm64.bcm2837` and
`pexpert/pexpert/arm64/BCM2837.h`, plus a PI3 mini-UART driver in
`pexpert/arm/pe_serial.c`. So BCM2837 is Apple's own public A53/GICv2 bring-up
target. It is a much better stand-in for MSM8916 than an A7 with Apple AIC.

`S5L8960X` is still useful as the *iOS-12-userland-compatible* build (A7 shipped
iOS 12 on a 4 KB granule), but it is not the QEMU bootstrap.

## Build

The `probe-xnu` workflow now takes a `machine` input:

```sh
gh workflow run probe-xnu.yml -R theatlasteam/ios-j5xnlte \
  -f tag=xnu-4903.221.2 -f machine=BCM2837
```

It uploads `xnu-arm64-BCM2837` containing `kernel.development`.

Known BCM2837 build gaps found so far:

- `CORE_NCTRS` is not defined for the board → patched in CI to `8`.

## Pack and run

```sh
qemu/run.sh /path/to/kernel.development qemu/out
```

The wrapper:

1. `tools/mkadt_bcm2837.py` — minimal Apple Device Tree
   (`/chosen`, `/cpus`, `/arm-io` with `bcm2837-io`, GIC-400, timer, UART).
2. `tools/mkpayload.py` — loads the Mach-O, resolves chained fixups, builds the
   `SWEETXNU` payload.
3. `tools/run_qemu.py` — boots QEMU `raspi3b` with a tiny stub at `0x0` and the
   kernel image at `0x80000`.

The kernel command line includes `-pi3`, which selects the mini-UART driver
(`pexpert/arm/pe_serial.c`, `PI3_UART`). No display driver is needed.

## QEMU

```
qemu-system-aarch64 -M raspi3b -smp 1 -m 1G -nographic \
  -serial null -serial file:qemu/out/serial.txt \
  -device loader,file=qemu/out/stub.bin,addr=0x0,force-raw=on \
  -device loader,file=qemu/out/ram.bin,addr=0x80000,force-raw=on \
  -device loader,addr=0x0,cpu-num=0
```

Expected first milestone: a few lines from `pe_serial` / `pe_identify_machine`,
then a panic. The panic is useful; it tells us which ADT node or platform hook
is still missing.

## What is deliberately not here

- No IPSW, kernelcache, iBoot, DeviceTree.im4p, or trust cache.
- No Apple userland. The first target is kernel console; `launchd` needs a
  ramdisk and the later `ios-sweet` patches (`0016`–`0024`).
- QEMU `raspi3b` is not MSM8916. Passing here proves entry, MMU, timer, Mach and
  BSD — not GIC wiring on the J5, MDSS, or eMMC.

## Next

1. Get `kernel.development` for BCM2837 to link.
2. Get one line of serial output in `raspi3b`.
3. Fix the first panic (likely `/chosen` or `/arm-io` properties).
4. Add a ramdisk and aim for `launchd`.
