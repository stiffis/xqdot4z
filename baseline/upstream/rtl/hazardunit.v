module hazardunit(input  [4:0] Rs1D, Rs2D,
                  input  [4:0] Rs1E, Rs2E,
                  input  [4:0] RdE, RdM, RdW,
                  input  [1:0] ResultSrcE,
                  input  RegWriteM, RegWriteW,
                  input  PCSrcE,
                  output StallF, StallD,
                  output FlushD, FlushE,
                  output [1:0] ForwardAE, ForwardBE);

  wire lwStall;

  assign lwStall = (ResultSrcE == 2'b01) &
                   ((Rs1D != 0 && Rs1D == RdE) ||
                    (Rs2D != 0 && Rs2D == RdE));

  assign ForwardAE = (Rs1E != 0 && Rs1E == RdM && RegWriteM) ? 2'b10 :
                     (Rs1E != 0 && Rs1E == RdW && RegWriteW) ? 2'b01 : 2'b00;

  assign ForwardBE = (Rs2E != 0 && Rs2E == RdM && RegWriteM) ? 2'b10 :
                     (Rs2E != 0 && Rs2E == RdW && RegWriteW) ? 2'b01 : 2'b00;

  assign StallF = lwStall;
  assign StallD = lwStall;
  assign FlushD = PCSrcE;
  assign FlushE = lwStall | PCSrcE;
endmodule
