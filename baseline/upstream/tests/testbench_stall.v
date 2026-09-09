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

  // check results: se espera Mem[8] = 7 (sw) y Mem[0] = 14 (add x3 = x2 + x2)
  always @(negedge clk) begin
    if (MemWrite) begin
      if (DataAdr === 0 & WriteData === 14) begin
        $display("Simulation succeeded");
        $finish;
      end else if (DataAdr === 8 & WriteData === 7) ;
      else begin
        $display("Simulation failed");
        $finish;
      end
    end
  end
endmodule
