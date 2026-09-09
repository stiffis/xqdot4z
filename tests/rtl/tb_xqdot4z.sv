`timescale 1ns/1ps
`default_nettype none
module tb_xqdot4z;
    reg [31:0] weights_word, activations_word;
    reg [3:0] zero_point;
    reg half;
    wire [31:0] result;
    reg [63:0] w_field, a_field, z_field, h_field, expected_field;
    reg [1023:0] line;
    reg [7:0] character;
    string vector_path;
    integer fd, parsed, checked, expected_count, line_bytes, byte_index;

    xqdot4z dut (
        .weights_word(weights_word), .activations_word(activations_word),
        .zero_point(zero_point), .half(half), .result(result)
    );

    initial begin
        checked = 0;
        if (!$value$plusargs("VECTORS=%s", vector_path))
            $fatal(1, "RTL_FAIL missing VECTORS argument");
        if (!$value$plusargs("COUNT=%d", expected_count) || expected_count <= 0)
            $fatal(1, "RTL_FAIL missing or invalid COUNT argument");
        fd = $fopen(vector_path, "r");
        if (fd == 0) $fatal(1, "RTL_FAIL cannot open vectors");
        // Parse complete lines: $fscanf EOF behavior differs across simulators
        // and can otherwise hide a partial final record after the expected count.
        line_bytes = $fgets(line, fd);
        while (line_bytes != 0) begin
            // Fixed exported format: eight/eight/one/one/eight hex digits,
            // single spaces and LF (31 bytes). Validate before numeric parsing;
            // reject extra columns, X/Z digits and oversized/truncated fields.
            if (line_bytes != 31 || line[7:0] !== 8'h0a)
                $fatal(1, "RTL_FAIL malformed vector after %0d checks", checked);
            for (byte_index = 1; byte_index < 31; byte_index = byte_index + 1) begin
                character = line[8*byte_index +: 8];
                if (byte_index == 9 || byte_index == 11 || byte_index == 13 || byte_index == 22) begin
                    if (character !== 8'h20)
                        $fatal(1, "RTL_FAIL malformed vector after %0d checks", checked);
                end else if (!((character >= 8'h30 && character <= 8'h39) ||
                               (character >= 8'h61 && character <= 8'h66) ||
                               (character >= 8'h41 && character <= 8'h46))) begin
                    $fatal(1, "RTL_FAIL malformed vector after %0d checks", checked);
                end
            end
            parsed = $sscanf(line, "%h %h %h %h %h", w_field, a_field,
                            z_field, h_field, expected_field);
            if (parsed == 5) begin
                if ((w_field >> 32) != 0 || (a_field >> 32) != 0 ||
                    z_field > 15 || h_field > 1 || (expected_field >> 32) != 0)
                    $fatal(1, "RTL_FAIL out-of-range vector %0d", checked);
                weights_word = w_field[31:0];
                activations_word = a_field[31:0];
                zero_point = z_field[3:0];
                half = h_field[0];
                // Allow delta-cycle settling. This is NOT a timing measurement.
                #1;
                if (result !== expected_field[31:0])
                    $fatal(1, "RTL_FAIL mismatch vector=%0d W=%h A=%h z=%h h=%b got=%h expected=%h",
                           checked, weights_word, activations_word, zero_point,
                           half, result, expected_field[31:0]);
                checked = checked + 1;
            end else begin
                $fatal(1, "RTL_FAIL malformed vector after %0d checks", checked);
            end
            line_bytes = $fgets(line, fd);
        end
        $fclose(fd);
        if (checked != expected_count)
            $fatal(1, "RTL_FAIL vector count got=%0d expected=%0d", checked, expected_count);
        $display("RTL_PASS checked=%0d", checked);
        $finish;
    end
endmodule
`default_nettype wire
