"""Directed CPU fixtures for B3; deliberately not timed/optimized benchmarks."""
import itertools
import random
import struct
from isa.packed.xqdot4 import encode
from verify_integration import li

SEED = 20260913


def dot(rd,a,b,h=0):
    return f"xqdot4 x{rd},x{a},x{b},{h}\n"


def matrix_fixtures():
    rng = random.Random(SEED)
    fixtures = []
    for index,zeros in enumerate(((0,0),(8,8),(15,15),(3,12))):
        if index == 0:
            acts = [4,-3,2,1,-128,127,-1,2]
            weights = [[5,9,10,4,0,15,8,7],[15,0,3,12,8,7,6,5]]
        else:
            acts = [rng.randrange(-128,128) for _ in range(8)]
            weights = [[rng.randrange(16) for _ in range(8)] for _ in range(2)]
        expected = [sum((w-z)*a for w,a in zip(row,acts)) for row,z in zip(weights,zeros)]
        fixtures.append(dict(name=f"matrix_{index}",activations=acts,weights=weights,
                             zero_points=list(zeros),activation_sum=sum(acts),expected=expected))
    return fixtures


def matrix_program(fixture, fused):
    acts,weights = fixture["activations"],fixture["weights"]
    data = [int.from_bytes(struct.pack("4b",*acts[i:i+4]),"little") for i in (0,4)]
    data += [sum(w << (4*i) for i,w in enumerate(row)) for row in weights]
    body = "".join(li(1,word)+f"sw x1,{4*i}(x0)\n" for i,word in enumerate(data))
    if not fused:
        body += li(10,0x11111111)+"addi x11,x0,0\n"
        for offset in (0,4):
            body += f"lw x2,{offset}(x0)\n"+dot(3,10,2)+"add x11,x11,x3\n"
    for row,z in enumerate(fixture["zero_points"]):
        body += f"lw x1,{8+4*row}(x0)\nlw x2,0(x0)\n"
        body += f"xqdot4zi x3,x1,x2,{z},0\n" if fused else dot(3,1,2,0)
        body += "lw x2,4(x0)\n"
        body += f"xqdot4zi x4,x1,x2,{z},1\n" if fused else dot(4,1,2,1)
        body += "add x5,x3,x4\n"
        if not fused:
            body += f"addi x12,x0,{z}\nmul x6,x12,x11\nsub x5,x5,x6\n"
        body += f"sw x5,{64+4*row}(x0)\n"
    return body


def programs():
    cases = []
    setup = li(1,0x78f04a95)+li(2,0x02ff7f80)
    def add(name,body,m,q,p=1,stalls=0,**extra):
        cases.append(dict(name=f"{name}_m{m}q{q}p{p}",body=body,m=m,q=q,p=p,stalls=stalls,**extra))
    rng = random.Random(SEED)
    pairs = [(0xffffffff,0x80808080),(0xffffffff,0x7f7f7f7f),(0,0x80808080),(0x78f04a95,0x02ff7f80)]
    pairs += [(rng.getrandbits(32),rng.getrandbits(32)) for _ in range(512)]
    numeric = "".join(li(1,w)+li(2,a)+dot(3,1,2,h)+"sw x3,0(x0)\n" for w,a in pairs for h in (0,1))
    for m,q in itertools.product(range(2),repeat=2):
        for p in (0,1):
            add("base",setup+"add x3,x1,x2\nsw x3,0(x0)\nlw x4,0(x0)\nsub x5,x4,x1\nsw x5,4(x0)\n",m,q,p,1)
            add("wrong_path","jal x0,target\n"+dot(3,1,2)+".word 0x1000002b\n"
                "target:\naddi x3,x0,7\nsw x3,0(x0)\n",m,q,p)
        for h in (0,1):
            add(f"disabled_h{h}",setup+dot(3,1,2,h)+"sw x3,0(x0)\n",m,q,0)
        add("forwarding",setup+dot(3,1,2)+dot(4,3,2)+dot(5,1,4,1)+
            "add x6,x5,x3\nsw x6,0(x0)\n"+dot(7,1,2,1)+"addi x0,x0,0\n"+
            dot(8,7,7)+"sw x8,4(x0)\n",m,q)
        add("load_weights",setup+"sw x1,0(x0)\nlw x5,0(x0)\n"+dot(6,5,2)+"sw x6,4(x0)\n",m,q,stalls=1)
        add("load_activations",setup+"sw x2,0(x0)\nlw x5,0(x0)\n"+dot(6,1,5,1)+"sw x6,4(x0)\n",m,q,stalls=1)
        add("load_both",setup+"sw x2,0(x0)\nlw x5,0(x0)\n"+dot(6,5,5,1)+"sw x6,4(x0)\n",m,q,stalls=1)
        add("aliases_x0",setup+dot(1,1,2)+dot(2,1,2,1)+dot(2,2,2)+dot(0,1,2)+
            dot(3,0,2)+dot(4,1,0)+"sw x2,0(x0)\nsw x3,4(x0)\nsw x4,8(x0)\n",m,q)
        add("branch_taken",setup+dot(3,0,2)+"beq x3,x0,target\n"+dot(4,1,2)+
            "sw x4,0(x0)\ntarget:\n"+dot(5,1,2,1)+"sw x5,4(x0)\n",m,q)
        add("branch_not_taken",setup+dot(3,1,2)+"beq x3,x0,bad\n"+dot(4,1,2,1)+
            "jal x0,end\nbad:\n.word 0x1000002b\nend:\nsw x4,0(x0)\n",m,q)
        add("jalr_consumer",setup+dot(3,0,2)+"jalr x0,x3,%lo(target)\n"+dot(4,1,2)+
            "sw x4,0(x0)\ntarget:\n"+dot(5,1,2,1)+"sw x5,4(x0)\n",m,q)
        add("compressed_crossing",setup+".option rvc\nc.nop\n.option norvc\n"+dot(3,1,2)+
            ".option rvc\nc.li x8,-7\nc.addi x8,1\n.option norvc\n"+dot(4,1,8,1)+"sw x4,0(x0)\n",m,q)
        add("older_packed_drains",setup+dot(3,1,2)+".word 0x1000002b\n"+dot(4,1,2)+"sw x4,0(x0)\n",m,q)
        add("reset_in_execute",setup+"addi x3,x0,99\n"+"addi x0,x0,0\n"*5+
            "reset_packed:\n"+dot(3,1,2)+"sw x3,0(x0)\n",m,q)
        add("numeric",numeric,m,q)
        for bit in (12,13,14,25,26,28,29,30,31):
            word = encode(3,1,2,1) | (1 << bit)
            add(f"reserved_bit{bit}",setup+f".word 0x{word:08x}\nsw x3,0(x0)\n",m,q)
        if not q:
            add("d_stays_disabled",setup+dot(3,1,2)+"xqdot4zi x4,x1,x2,8,0\nsw x4,0(x0)\n",m,q)
        if not m:
            add("mul_stays_disabled",setup+dot(3,1,2)+"mul x4,x1,x2\nsw x4,0(x0)\n",m,q)
        if m or q:
            body = setup+dot(3,1,2)
            if m: body += "mul x4,x3,x2\n"+dot(5,4,3,1)
            if q: body += "xqdot4zi x6,x3,x2,15,0\n"+dot(7,1,6,1)+"xqdot4zi x8,x7,x3,8,1\n"
            if m and q: body += "mul x9,x8,x5\n"+dot(10,9,8)+"xqdot4zi x11,x10,x9,0,1\n"
            body += "sw x3,0(x0)\nsw x11,4(x0)\n"
            add("mixed",body,m,q)
    for fixture in matrix_fixtures():
        for fused in (False,True):
            add(fixture["name"]+"_"+("d" if fused else "b3"),matrix_program(fixture,fused),
                1,int(fused),int(not fused),4 if fused else 6,matrix=fixture["name"],fused=fused)
    return cases
