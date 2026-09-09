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
    #2000;
    $display("Simulation timed out");
    $finish;
  end

  // check results
  always @(negedge clk) begin
    if (MemWrite) begin
      if (DataAdr === 8 & WriteData === 32'd15) begin
        $display("Simulation succeeded");
        $finish;
      end
      else if (DataAdr === 0 & WriteData === 32'd12) ;
      else if (DataAdr === 4 & WriteData === 32'd4) ;
      else begin
        $display("Unexpected store: Adr=%0d Data=0x%08X", DataAdr, WriteData);
        $finish;
      end
    end
  end
endmodule
