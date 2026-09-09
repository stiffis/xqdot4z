// B3 arithmetic candidate: four U4-by-S8 products, without zero-point correction.
// Contract: rtl/packed/SPEC.md v0.1. No ISA or accumulation state.
`timescale 1ns/1ps
`default_nettype none
module xqdot4 (
    input wire [31:0] weights_word,
    input wire [31:0] activations_word,
    input wire half,
    output wire [31:0] result
);
    wire [15:0] selected_weights;
    wire signed [4:0] weight [0:3];
    wire signed [7:0] activation [0:3];
    wire signed [12:0] product [0:3];
    wire signed [13:0] pair_low, pair_high;
    wire signed [14:0] subtotal;

    assign selected_weights = half ? weights_word[31:16] : weights_word[15:0];
    genvar lane;
    generate
        for (lane = 0; lane < 4; lane = lane + 1) begin : lanes
            // U4 is nonnegative; casting the nibble alone would reinterpret S4.
            assign weight[lane] = $signed(selected_weights[4*lane +: 4]);
            assign activation[lane] = $signed(activations_word[8*lane +: 8]);
            assign product[lane] = weight[lane] * activation[lane];
        end
    endgenerate
    assign pair_low = $signed({product[0][12], product[0]})
                    + $signed({product[1][12], product[1]});
    assign pair_high = $signed({product[2][12], product[2]})
                     + $signed({product[3][12], product[3]});
    assign subtotal = $signed({pair_low[13], pair_low})
                    + $signed({pair_high[13], pair_high});
    assign result = {{17{subtotal[14]}}, subtotal};
endmodule
`default_nettype wire
