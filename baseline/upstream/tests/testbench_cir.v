module testbench;
  reg         clk;
  reg         reset;
  wire [31:0] WriteData;
  wire [31:0] DataAdr;
  wire        MemWrite;

  top dut (
      .clk(clk),
      .reset(reset),
      .WriteData(WriteData),
      .DataAdr(DataAdr),
      .MemWrite(MemWrite)
  );

  initial begin
    reset = 1;
    #22;
    reset = 0;
  end

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

  always @(negedge clk) begin
    if (MemWrite) begin
      if (DataAdr === 0 & WriteData === 32'd17) ;
      else if (DataAdr === 4 & WriteData === 32'd4096) begin
        $display("c.lui/slli/add subset succeeded: Mem[0]=17 Mem[4]=4096");
        $finish;
      end
      else begin
        $display("Unexpected store: Adr=%0d Data=%0d", DataAdr, WriteData);
        $finish;
      end
    end
  end
endmodule
