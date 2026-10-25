#!/usr/bin/env python3
"""Boot a SWEETXNU payload on QEMU's raspi3b (BCM2837 / Cortex-A53).

This is the milestone-2 harness: no Apple firmware, no kernelcache. The
payload is produced by tools/mkpayload.py from a kernel built with
MACHINE_CONFIGS=BCM2837 and the ADT from tools/mkadt_bcm2837.py.

QEMU raspi3b has RAM at 0, the mini-UART at 0x3f215040, and a GIC-400.
The stub lives at 0x0; the kernel image (segments + ADT + boot_args) is
loaded at the ADT's dram-base (0x80000).
"""
import argparse
import json
import os
import struct
import subprocess
import sys
import time

PAGE = 0x4000
BOOT_LINE_LENGTH = 608
STUB_PA = 0x0


def build_image(payload):
    magic, ver, nsegs = struct.unpack_from('<8sII', payload, 0)
    assert magic == b'SWEETXNU' and ver == 1, 'not a SWEETXNU v1 payload'
    (virt_base, entry_va, adt_off, adt_size, kernel_end,
     phys_base, mem_size) = struct.unpack_from('<7Q', payload, 0x10)
    cmdline = payload[0x48:0x48 + BOOT_LINE_LENGTH]
    delta = phys_base - virt_base
    adt_pa = kernel_end + delta
    ba_pa = (adt_pa + adt_size + PAGE - 1) & ~(PAGE - 1)
    top = ba_pa + PAGE
    assert phys_base == 0x80000, f'unexpected dram-base {phys_base:#x}'
    img = bytearray(top - phys_base)
    for i in range(nsegs):
        vmaddr, vmsize, foff, fsize = struct.unpack_from('<4Q', payload, 0x2a8 + 32 * i)
        o = vmaddr + delta - phys_base
        img[o:o + fsize] = payload[foff:foff + fsize]
    img[adt_pa - phys_base:adt_pa - phys_base + adt_size] = payload[adt_off:adt_off + adt_size]
    # no display on raspi3b; serial is selected with -pi3
    ba = struct.pack('<HH4x4Q6QI4xQI', 2, 2, virt_base, phys_base, mem_size, top,
                     0, 0, 0, 0, 0, 0, 0, adt_pa - delta, adt_size)
    ba += cmdline + b'\0' * 4 + struct.pack('<QQ', 0, mem_size)
    assert len(ba) == 736
    img[ba_pa - phys_base:ba_pa - phys_base + len(ba)] = ba
    return phys_base, bytes(img), ba_pa, entry_va + delta


def stub(ba_pa, entry_pa):
    return struct.pack('<4I2Q', 0x58000080, 0x580000a1, 0xd61f0020, 0xd503201f,
                       ba_pa, entry_pa)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('payload')
    ap.add_argument('outdir')
    ap.add_argument('--secs', type=int, default=25)
    ap.add_argument('--live', action='store_true')
    a = ap.parse_args()

    payload = open(a.payload, 'rb').read()
    phys_base, img, ba_pa, entry_pa = build_image(payload)
    os.makedirs(a.outdir, exist_ok=True)
    ram = os.path.join(a.outdir, 'ram.bin')
    stb = os.path.join(a.outdir, 'stub.bin')
    open(ram, 'wb').write(img)
    open(stb, 'wb').write(stub(ba_pa, entry_pa))
    serial = os.path.join(a.outdir, 'serial.txt')
    log = os.path.join(a.outdir, 'qemu.log')
    print(f'phys_base={phys_base:#x} boot_args={ba_pa:#x} entry={entry_pa:#x}', file=sys.stderr)

    cmd = [
        'qemu-system-aarch64', '-M', 'raspi3b', '-smp', '1', '-m', '1G',
        '-nographic', '-monitor', 'none', '-no-reboot',
        '-serial', 'null', '-serial', f'file:{serial}',
        '-d', 'int,guest_errors,unimp', '-D', log,
        '-device', f'loader,file={stb},addr={STUB_PA:#x},force-raw=on',
        '-device', f'loader,file={ram},addr={phys_base:#x},force-raw=on',
        '-device', f'loader,addr={STUB_PA:#x},cpu-num=0',
    ]
    print(' '.join(cmd), file=sys.stderr)
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL)
    pos = 0
    t0 = time.time()
    while p.poll() is None and time.time() - t0 < a.secs:
        if os.path.exists(serial) and a.live:
            with open(serial, 'rb') as f:
                f.seek(pos)
                chunk = f.read()
                pos += len(chunk)
                sys.stdout.write(chunk.decode('utf-8', 'replace'))
                sys.stdout.flush()
        time.sleep(0.3)
    if p.poll() is None:
        p.kill()
        p.wait()
    if os.path.exists(serial):
        data = open(serial, 'rb').read()
        print(f'\n--- serial ({len(data)} bytes) ---', file=sys.stderr)
        print(data.decode('utf-8', 'replace'))
        open(os.path.join(a.outdir, 'result.json'), 'w').write(json.dumps({
            'serial_bytes': len(data), 'qemu_returncode': p.returncode,
        }, indent=2) + '\n')
    else:
        print('no serial file produced', file=sys.stderr)


if __name__ == '__main__':
    main()
