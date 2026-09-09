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
      if (DataAdr === 52 & WriteData === 32'd3) begin
        $display("bsearch_rv32i(18) succeeded: index=3, Mem[52]=3");
        $finish;
      end
      else if (DataAdr === 32 & WriteData === 32'd3) ;
      else if (DataAdr === 36 & WriteData === 32'd7) ;
      else if (DataAdr === 40 & WriteData === 32'd12) ;
      else if (DataAdr === 44 & WriteData === 32'd18) ;
      else if (DataAdr === 48 & WriteData === 32'd25) ;
      else if (DataAdr === 60 & WriteData === 32'd2) ;
      else if (DataAdr === 64 & WriteData === 32'd3) ;
      else begin
        $display("Unexpected store: Adr=%0d Data=%0d", DataAdr, WriteData);
        $finish;
      end
    end
  end
endmodule
