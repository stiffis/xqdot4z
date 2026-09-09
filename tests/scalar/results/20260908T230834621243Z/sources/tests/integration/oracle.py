"""Bounded functional oracle for the M3 test programs, NOT a complete RISC-V ISS.

Decodes emitted bytes independently of isa/xqdot4zi.py and the RTL. Unhandled
instructions are rejected; registers and data words initially zero in tests.
"""

from model.xqdot4z import qdot4z_bits


def signed(value, width):
    return value - (1 << width) if value & (1 << (width - 1)) else value


def execute(binary, enabled, stop_before=None, *, mul_enabled=False):
    regs, memory, pc = [0]*32, {}, 0
    retired, stores, qdots = [], [], []
    muls = []
    def finish(fault=None):
        result = dict(retired=retired, stores=stores, qdots=qdots, muls=muls, regs=regs)
        if fault is not None:
            result["fault"] = fault
        return result
    for _ in range(20000):
        if pc == stop_before:
            return finish()
        if pc % 2 or pc+2 > len(binary):
            return finish([1,pc])
        halfword = int.from_bytes(binary[pc:pc+2], "little")
        length = 4 if halfword & 3 == 3 else 2
        if pc+length > len(binary):
            raise ValueError("Truncated program instruction")
        word = int.from_bytes(binary[pc:pc+length], "little")
        next_pc, rd, value = pc+length, 0, 0
        if length == 2:
            op = halfword >> 13
            if halfword & 3 != 1 or op not in (0,2):
                raise ValueError(f"Unsupported test C instruction {halfword:04x}")
            rd = halfword >> 7 & 31
            imm = signed((halfword >> 12 & 1) << 5 | (halfword >> 2 & 31), 6)
            value = (regs[rd] if op == 0 else 0) + imm
        else:
            opcode, funct3 = word & 127, word >> 12 & 7
            dest, rs1, rs2 = word >> 7 & 31, word >> 15 & 31, word >> 20 & 31
            a, b = regs[rs1], regs[rs2]
            imm = signed(word >> 20, 12)
            if word == 0x00100073:
                return finish([3,pc])
            if opcode == 0x0b:
                # Field-by-field decode, deliberately not the encoder's mask helper.
                if not enabled or funct3 != 0 or (word >> 25 & 3) != 0:
                    return finish([2,pc])
                z, h = word >> 28, word >> 27 & 1
                rd, value = dest, qdot4z_bits(a,b,z,h)
                qdots.append([pc,a,b,z,h])
            elif opcode == 0x37:
                rd, value = dest, word & 0xfffff000
            elif opcode == 0x13 and funct3 == 0:
                rd, value = dest, a+imm
            elif opcode == 0x33 and funct3 == 0 and word >> 25 == 0:
                rd, value = dest, a+b
            elif opcode == 0x33 and word >> 25 == 1:
                if not mul_enabled or funct3 != 0:
                    return finish([2,pc])
                # Independent unbounded signed arithmetic, normalized below.
                rd, value = dest, signed(a,32)*signed(b,32)
                muls.append([pc,a,b])
            elif opcode == 0x03 and funct3 == 2:
                address = (a+imm) & 0xffffffff
                if address % 4 or address >= 256: raise ValueError("Oracle load address")
                rd, value = dest, memory.get(address,0)
            elif opcode == 0x23 and funct3 == 2:
                offset = signed((word >> 25) << 5 | (word >> 7 & 31),12)
                address = (a+offset) & 0xffffffff
                if address % 4 or address >= 256: raise ValueError("Oracle store address")
                memory[address] = b; stores.append([address,b])
            elif opcode == 0x63 and funct3 in (0,1,4,5):
                offset = signed((word >> 31) << 12 | (word >> 7 & 1) << 11 |
                                (word >> 25 & 63) << 5 | (word >> 8 & 15) << 1,13)
                taken = {0:a==b,1:a!=b,4:signed(a,32)<signed(b,32),5:signed(a,32)>=signed(b,32)}[funct3]
                if taken: next_pc = pc+offset
            elif opcode == 0x6f:
                offset = signed((word >> 31) << 20 | (word >> 12 & 255) << 12 |
                                (word >> 20 & 1) << 11 | (word >> 21 & 1023) << 1,21)
                rd, value, next_pc = dest, pc+4, pc+offset
            elif opcode == 0x67 and funct3 == 0:
                rd, value, next_pc = dest, pc+4, (a+imm) & 0xfffffffe
            else:
                raise ValueError(f"Unhandled test opcode {word:08x} at {pc:x}")
        value &= 0xffffffff
        if rd:
            regs[rd] = value
        retired.append([pc,rd,value if rd else 0])
        pc = next_pc & 0xffffffff
    raise ValueError("Oracle instruction limit exceeded")
