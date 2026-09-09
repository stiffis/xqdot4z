`timescale 1ns/1ps
`default_nettype none
module tb_packed;
    reg [31:0] weights_word, activations_word;
    reg [3:0] zero_point;
    reg half;
    wire [31:0] packed_result, fused_result;
    wire signed [31:0] activation_sum, corrected_result;
    reg [63:0] w_field, a_field, z_field, h_field, p_field, d_field;
    reg [1023:0] line;
    reg [7:0] character;
    string vector_path;
    integer fd, parsed, checked=0, count, line_bytes, byte_index, trace_from=-1;

    xqdot4 packed_dut(.weights_word(weights_word), .activations_word(activations_word),
                     .half(half), .result(packed_result));
    xqdot4z fused_dut(.weights_word(weights_word), .activations_word(activations_word),
                     .zero_point(zero_point), .half(half), .result(fused_result));
    // Reference-only logic: this is NOT the implementation/cost of B3 correction.
    assign activation_sum = $signed({{24{activations_word[7]}},activations_word[7:0]})
                          + $signed({{24{activations_word[15]}},activations_word[15:8]})
                          + $signed({{24{activations_word[23]}},activations_word[23:16]})
                          + $signed({{24{activations_word[31]}},activations_word[31:24]});
    assign corrected_result = $signed(packed_result) - $signed({28'b0, zero_point}) * activation_sum;

    initial begin
        if (!$value$plusargs("VECTORS=%s",vector_path) ||
            !$value$plusargs("COUNT=%d",count) || count<=0)
            $fatal(1,"PACKED_FAIL arguments");
        if ($value$plusargs("TRACE_FROM=%d",trace_from)) begin end
        fd=$fopen(vector_path,"r");
        if (fd==0) $fatal(1,"PACKED_FAIL cannot open vectors");
        line_bytes=$fgets(line,fd);
        while (line_bytes!=0) begin
            // W A z h P d: 8/8/1/1/8/8 hex digits, single spaces and LF.
            if (line_bytes!=40 || line[7:0]!==8'h0a)
                $fatal(1,"PACKED_FAIL malformed vector");
            for (byte_index=1;byte_index<40;byte_index=byte_index+1) begin
                character=line[8*byte_index +: 8];
                if (byte_index==9 || byte_index==18 || byte_index==20 ||
                    byte_index==22 || byte_index==31) begin
                    if (character!==8'h20) $fatal(1,"PACKED_FAIL malformed vector");
                end else if (!((character>=8'h30 && character<=8'h39) ||
                               (character>=8'h61 && character<=8'h66)))
                    $fatal(1,"PACKED_FAIL malformed vector");
            end
            parsed=$sscanf(line,"%h %h %h %h %h %h",w_field,a_field,z_field,h_field,p_field,d_field);
            if (parsed!=6) $fatal(1,"PACKED_FAIL malformed vector");
            if ((w_field>>32)!=0 || (a_field>>32)!=0 || z_field>15 || h_field>1 ||
                (p_field>>32)!=0 || (d_field>>32)!=0)
                $fatal(1,"PACKED_FAIL out-of-range vector");
            weights_word=w_field[31:0]; activations_word=a_field[31:0];
            zero_point=z_field[3:0]; half=h_field[0];
            #1; // Settling only, not a frequency or cycle measurement.
            if (packed_result!==p_field[31:0])
                $fatal(1,"PACKED_FAIL packed mismatch vector=%0d",checked);
            if (fused_result!==d_field[31:0])
                $fatal(1,"PACKED_FAIL fused mismatch vector=%0d",checked);
            if (corrected_result!==fused_result)
                $fatal(1,"PACKED_FAIL factorization mismatch vector=%0d",checked);
            if (trace_from>=0 && checked>=trace_from)
                $display("PACKED_OBS|%0d|%08h|%08h",checked,packed_result,fused_result);
            checked=checked+1;
            line_bytes=$fgets(line,fd);
        end
        $fclose(fd);
        if (checked!=count) $fatal(1,"PACKED_FAIL vector count");
        $display("PACKED_PASS checked=%0d",checked); $finish;
    end
endmodule
`default_nettype wire
