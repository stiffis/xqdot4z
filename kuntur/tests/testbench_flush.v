module testbench;
  reg         clk;
  reg         reset;
  wire [31:0] WriteData;
  wire [31:0] DataAdr;
  wire        MemWrite;

  // instantiate device to be tested
  top dut (
      .clk(clk),
      .reset(reset),
      .WriteData(WriteData),
      .DataAdr(DataAdr),
      .MemWrite(MemWrite)
  );

  // initialize test
  initial begin
    $dumpfile("wave.vcd");
    $dumpvars(0, testbench);
    reset = 1;
    #22;
    reset = 0;
  end

  // generate clock to sequence tests
  always begin
    clk = 1;
    #5;
    clk = 0;
    #5;
  end

  initial begin
    #1000;
    $display("Simulation timed out");
    $finish;
  end

  // check results: con el salto tomado y descartado, la unica escritura debe ser
  // Mem[4] = 5. Cualquier escritura a Mem[0] significa que el camino erroneo se ejecuto.
  always @(negedge clk) begin
    if (MemWrite) begin
      if (DataAdr === 4 & WriteData === 5) begin
        $display("Simulation succeeded");
        $finish;
      end else begin
        $display("Simulation failed");
        $finish;
      end
    end
  end
endmodule
