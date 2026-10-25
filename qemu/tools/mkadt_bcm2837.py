#!/usr/bin/env python3
"""Minimal Apple Device Tree for xnu-4903's BCM2837 (Raspberry Pi 3) target.

This is the QEMU-milestone ADT: enough nodes for pe_identify_machine(),
the PI3 mini-UART and the early VM. It is deliberately not an iPhone tree.

QEMU raspi3b layout used here:
  RAM       0x00000000 .. 0x40000000 (1 GiB)
  ARM local 0x3f000000
  GIC-400   0x3f00b000 (distributor 0x3f00b200)
  mini UART 0x3f215040
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adt  # noqa: E402

u32 = lambda *v: struct.pack('<%dI' % len(v), *v)
u64 = lambda *v: struct.pack('<%dQ' % len(v), *v)
cstr = lambda s: s.encode() + b'\0'

# Keep everything below the hard-coded BCM2837 panic log at 0x3c0fc000.
DRAM_BASE = 0x00080000
PANIC_LOG = 0x3c0fc000
DRAM_SIZE = PANIC_LOG - DRAM_BASE
SOC_BASE = 0x3f000000
TIMEBASE = 1000000          # matches pe_identify_machine()'s bcm2837 tclk
GIC_DIST = 0x00b200         # relative to SOC_BASE
LOCAL_TIMER = 0x004000      # merely mapped; bcm2837_funcs is empty


def node(name, props=(), children=()):
    n = adt.Node()
    n.props = [('name', 0, cstr(name))] + [(k, 0, v) for k, v in props]
    n.children = list(children)
    return n


def build(seed=None):
    seed = seed if seed is not None else os.urandom(64)

    cpus = node('cpus', [
        ('AAPL,phandle', u32(0x100)),
        ('#address-cells', u32(1)),
        ('#size-cells', u32(0)),
    ], [
        node(f'cpu{i}', [
            ('AAPL,phandle', u32(0x200 + i)),
            ('device_type', cstr('cpu')),
            ('reg', u32(i << 8)),
            ('cpu-id', u32(i)),
            ('state', cstr('running' if i == 0 else 'stopped')),
            ('timebase-frequency', u32(TIMEBASE)),
            ('clock-frequency', u32(1200000000)),
            ('bus-frequency', u32(250000000)),
        ]) for i in range(4)
    ])

    gic = node('interrupt-controller', [
        ('AAPL,phandle', u32(0x300)),
        ('interrupt-controller', cstr('master')),
        ('reg', u32(GIC_DIST, 0x1000)),
    ])
    timer = node('timer', [
        ('AAPL,phandle', u32(0x301)),
        ('device_type', cstr('timer')),
        ('reg', u32(LOCAL_TIMER, 0x1000)),
    ])
    # The PI3 UART is selected by the '-pi3' boot-arg, not by this node, but a
    # boot-console node keeps the generic serial path happy if it is used.
    uart = node('uart0', [
        ('AAPL,phandle', u32(0x302)),
        ('boot-console', cstr('master')),
        ('compatible', cstr('brcm,bcm2835-aux-uart')),
        ('reg', u32(0x215000, 0x100)),
    ])
    arm_io = node('arm-io', [
        ('AAPL,phandle', u32(0x400)),
        ('device_type', cstr('bcm2837-io')),
        ('compatible', cstr('bcm2837-io') + cstr('arm-io')),
        ('#address-cells', u32(1)),
        ('#size-cells', u32(1)),
        # child address 0 -> 0x3f000000; pe_arm_get_soc_base_phys() uses [1]
        ('ranges', u32(0, SOC_BASE, 0x01000000)),
    ], [gic, timer, uart])

    chosen = node('chosen', [
        ('dram-base', u64(DRAM_BASE)),
        ('dram-size', u64(DRAM_SIZE)),
        ('random-seed', seed),
        ('debug-enabled', u32(1)),
        ('firmware-version', cstr('xnu-qemu-bcm2837')),
        ('system-firmware-version', cstr('xnu-qemu-bcm2837')),
        ('embedded-panic-log-size', u32(0x4000)),
    ])

    return node('device-tree', [
        ('AAPL,phandle', u32(0x1)),
        ('compatible', cstr('bcm2837') + cstr('brcm,bcm2837')),
        ('model', cstr('Raspberry Pi 3 Model B')),
        ('target-type', cstr('bcm2837')),
        ('target-sub-type', cstr('bcm2837')),
        ('manufacturer', cstr('Raspberry Pi Foundation')),
        ('#address-cells', u32(2)),
        ('#size-cells', u32(2)),
    ], [chosen, cpus, arm_io, node('pram', [
        ('reg', u64(PANIC_LOG) + u64(0x4000)),
    ])])


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'bcm2837.adt'
    blob = adt.serialize(build())
    open(out, 'wb').write(blob)
    print(f'{out}: {len(blob)} bytes')
