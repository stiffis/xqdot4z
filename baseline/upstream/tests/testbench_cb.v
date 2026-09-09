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
      if (DataAdr === 0 & WriteData === 32'd10) ;
      else if (DataAdr === 4 & WriteData === 32'hFFFFFFFC) ;
      else if (DataAdr === 8 & WriteData === 32'd4) begin
        $display("c.srli/srai/andi subset succeeded: 10, -4, 4");
        $finish;
      end
      else begin
        $display("Unexpected store: Adr=%0d Data=0x%08X", DataAdr, WriteData);
        $finish;
      end
    end
  end
endmodule
