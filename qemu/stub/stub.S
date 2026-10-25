/*
 * QEMU raspi3b boot stub for xnu-4903 (BCM2837).
 *
 * QEMU starts at EL3 (Raspberry Pi firmware starts at EL2/EL1). XNU's
 * start.s expects EL1 with the MMU off and x0 = boot_args. Drop through
 * EL3 -> EL2 -> EL1, park secondary CPUs, then jump.
 *
 * The last 16 bytes are patched by tools/run_qemu.py:
 *   .quad boot_args_pa
 *   .quad xnu_entry_pa
 */
	.section .text
	.global _start
_start:
	mrs	x9, mpidr_el1
	and	x9, x9, #0xff
	cbnz	x9, park

	mrs	x9, CurrentEL
	lsr	x9, x9, #2
	cmp	x9, #3
	b.ne	1f
	mov	x9, #0x41d		/* SCR_EL3: NS|IRQ|FIQ|EA|RW */
	msr	scr_el3, x9
	mov	x9, #0x3c9		/* SPSR_EL3: EL2h, DAIF masked */
	msr	spsr_el3, x9
	adr	x9, 1f
	msr	elr_el3, x9
	eret
1:
	mrs	x9, CurrentEL
	lsr	x9, x9, #2
	cmp	x9, #2
	b.ne	2f
	mov	x9, #0x80000000		/* HCR_EL2.RW = 1 */
	msr	hcr_el2, x9
	mov	x9, #0x3c5		/* SPSR_EL2: EL1h, DAIF masked */
	msr	spsr_el2, x9
	adr	x9, 2f
	msr	elr_el2, x9
	eret
2:
	mov	x9, #0x0800
	movk	x9, #0x30d0, lsl #16	/* SCTLR_EL1 reset value, MMU/caches off */
	msr	sctlr_el1, x9
	isb
	ldr	x0, boot_args_lit
	ldr	x1, entry_lit
	br	x1

park:
	wfe
	b	park

	.align 3
boot_args_lit:
	.quad	0
entry_lit:
	.quad	0
