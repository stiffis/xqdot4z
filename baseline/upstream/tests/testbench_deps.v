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

  // check results
  always @(negedge clk) begin
    if (MemWrite) begin
      if (DataAdr === 124 & WriteData === 17) begin
        $display("Simulation succeeded");
        $finish;
      end else if (DataAdr === 0   & WriteData === 16) ;
      else if (DataAdr === 100 & WriteData === 6)  ;
      else if (DataAdr === 104 & WriteData === 10) ;
      else if (DataAdr === 108 & WriteData === 16) ;
      else if (DataAdr === 112 & WriteData === 6)  ;
      else if (DataAdr === 116 & WriteData === 64) ;
      else if (DataAdr === 120 & WriteData === 70) ;
      else begin
        $display("Simulation failed");
        $finish;
      end
    end
  end
endmodule
