// XQDot4Z numerical contract v0.1 (model/SPEC.md).
// Standalone four-lane combinational datapath: no ISA state or accumulator.
`timescale 1ns/1ps
`default_nettype none
module xqdot4z (
    input  wire [31:0] weights_word,
    input  wire [31:0] activations_word,
    input  wire [3:0]  zero_point,
    input  wire        half,
    output wire [31:0] result
);
    wire [15:0] selected_weights;
    wire signed [4:0] centered [0:3];
    wire signed [7:0] activation [0:3];
    wire signed [12:0] product [0:3];
    wire signed [13:0] pair_low, pair_high;
    wire signed [14:0] subtotal;

    // Selecting the upper half changes weights only, never activation order.
    assign selected_weights = half ? weights_word[31:16] : weights_word[15:0];
    genvar lane;
    generate
        for (lane = 0; lane < 4; lane = lane + 1) begin : lanes
            // Zero-extend U4 before signed subtraction; do not reinterpret as S4.
            assign centered[lane] = $signed({1'b0, selected_weights[4*lane +: 4]})
                                  - $signed({1'b0, zero_point});
            assign activation[lane] = $signed(activations_word[8*lane +: 8]);
            // Preserve all 13 bits of a generic S5 x S8 product.
            assign product[lane] = centered[lane] * activation[lane];
        end
    endgenerate

    // Extend before addition, preserving a carry/sign bit at each tree level.
    assign pair_low = $signed({product[0][12], product[0]})
                    + $signed({product[1][12], product[1]});
    assign pair_high = $signed({product[2][12], product[2]})
                     + $signed({product[3][12], product[3]});
    assign subtotal = $signed({pair_low[13], pair_low})
                    + $signed({pair_high[13], pair_high});
    assign result = {{17{subtotal[14]}}, subtotal};
endmodule
`default_nettype wire
