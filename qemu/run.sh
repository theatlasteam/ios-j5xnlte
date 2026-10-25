#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
KERNEL=${1:?usage: run.sh KERNEL.development [OUTDIR]}
OUT=${2:-$HERE/out}
mkdir -p "$OUT"

CC=${CROSS:-aarch64-linux-gnu-gcc}
OBJCOPY=${CROSS_OBJCOPY:-aarch64-linux-gnu-objcopy}
$CC -nostdlib -static -Wl,--build-id=none -Wl,-N -Ttext=0 \
  -o "$OUT/stub.elf" "$HERE/stub/stub.S"
$OBJCOPY -O binary "$OUT/stub.elf" "$OUT/stub.template.bin"

python3 "$HERE/tools/mkadt_bcm2837.py" "$OUT/bcm2837.adt"
python3 "$HERE/tools/mkpayload.py" "$KERNEL" "$OUT/bcm2837.adt" "$OUT/payload.bin" \
  --cmdline 'debug=0x8 serial=3 cpus=1 keepsyms=1 -pi3'
python3 "$HERE/tools/run_qemu.py" "$OUT/payload.bin" "$OUT" --secs "${SECS:-25}" --live \
  --stub "$OUT/stub.template.bin"
