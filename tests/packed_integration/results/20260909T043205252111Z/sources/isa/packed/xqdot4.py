"""Encoding of the local xqdot4 B3 instruction, ISA prototype v0.1."""
VERSION = "0.1"
MATCH = 0x0000002b
MASK = 0xf600707f


def _bounded(value, name, maximum):
    if type(value) is not int:
        raise TypeError(f"{name} must be an int")
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} out of range")


def encode(rd, rs1, rs2, half):
    for name, value in (("rd",rd),("rs1",rs1),("rs2",rs2)):
        _bounded(value,name,31)
    _bounded(half,"half",1)
    return MATCH | rd << 7 | rs1 << 15 | rs2 << 20 | half << 27


def decode(word):
    _bounded(word,"word",0xffffffff)
    if word & MASK != MATCH:
        raise ValueError("Not an xqdot4 v0.1 encoding")
    return dict(rd=word >> 7 & 31,rs1=word >> 15 & 31,rs2=word >> 20 & 31,half=word >> 27 & 1)
