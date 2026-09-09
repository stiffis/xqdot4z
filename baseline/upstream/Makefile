RTL = rtl/*.v
PROG ?= isa

.PHONY: test hazard demo-hazard wave clean

test:
	@./run_tests.sh

hazard:
	@./run_hazard_demo.sh

demo-hazard:
	@mkdir -p build
	@bash -c 'cp -f riscvtest.mem build/riscvtest.mem.bak 2>/dev/null; \
	  trap "cp -f build/riscvtest.mem.bak riscvtest.mem 2>/dev/null" EXIT; \
	  cp tests/programs/riscvtest_deps_nonop.mem riscvtest.mem; \
	  iverilog -g2012 -o build/sim_nonop $(RTL) tests/testbench_deps.v && \
	  vvp build/sim_nonop 2>/dev/null | grep -v -i warning'

wave:
	@./toolchain/gen_wave.sh $(PROG)

clean:
	rm -rf build wave.vcd *.vcd
