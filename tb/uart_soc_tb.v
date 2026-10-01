`timescale 1ns / 1ps
`default_nettype none

module uart_soc_tb;

    reg clk;
    reg resetn;

    wire trap;
    wire uart_tx;

    integer cycle_count;
    integer byte_count;

    reg tx_started;

    soc_top dut (
        .clk(clk),
        .resetn(resetn),
        .trap(trap),
        .uart_tx(uart_tx)
    );

    // 100 MHz simulation clock
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        resetn     = 1'b0;
        cycle_count = 0;
        byte_count  = 0;
        tx_started  = 0;

        $dumpfile("tb/uart_soc_tb.vcd");
        $dumpvars(0, uart_soc_tb);

        $display("========================================");
        $display(" PicoRV32 AXI UART Test");
        $display("========================================");

        repeat (8)
            @(posedge clk);

        @(negedge clk);
        resetn = 1'b1;

        $display("[TB] Reset released");


        repeat (3000) begin
            @(posedge clk);

            cycle_count = cycle_count + 1;

            // CPU must not trap
            if (trap) begin
                $display("[FAIL] CPU entered TRAP");
                $finish;
            end


            // ----------------------------------------------------
            // Observe byte accepted by actual uart_tx block
            //
            // uart_axil:
            //   tx_valid_reg -> uart_tx.s_axis_tvalid
            //   tx_ready     <- uart_tx.s_axis_tready
            // ----------------------------------------------------

            if (dut.u_uart_axil.tx_valid_reg &&
                dut.u_uart_axil.tx_ready) begin

                if (byte_count == 0) begin

                    $display(
                        "[TB] UART accepted byte 0: 0x%02x '%c'",
                        dut.u_uart_axil.tx_data_reg,
                        dut.u_uart_axil.tx_data_reg
                    );

                    if (dut.u_uart_axil.tx_data_reg !== 8'h48) begin
                        $display("[FAIL] Expected 'H' (0x48)");
                        $finish;
                    end

                    byte_count = 1;

                end
                else if (byte_count == 1) begin

                    $display(
                        "[TB] UART accepted byte 1: 0x%02x '%c'",
                        dut.u_uart_axil.tx_data_reg,
                        dut.u_uart_axil.tx_data_reg
                    );

                    if (dut.u_uart_axil.tx_data_reg !== 8'h69) begin
                        $display("[FAIL] Expected 'i' (0x69)");
                        $finish;
                    end

                    byte_count = 2;

                end

            end


            // Serial TX start bit observed
            if (!uart_tx)
                tx_started = 1;


            // ----------------------------------------------------
            // PASS
            // ----------------------------------------------------

            if (byte_count == 2 && tx_started) begin

                $display("");
                $display("========================================");
                $display("[PASS] CPU -> AXI -> UART path works");
                $display("[PASS] UART accepted 'H'");
                $display("[PASS] UART accepted 'i'");
                $display("[PASS] Serial TX start bit observed");
                $display("[PASS] CPU trap = 0");
                $display("========================================");

                repeat (20)
                    @(posedge clk);

                $finish;
            end

        end


        $display("");
        $display("[FAIL] UART simulation timeout");
        $display("byte_count = %0d", byte_count);
        $display("tx_started = %0d", tx_started);

        $finish;
    end

endmodule

`default_nettype wire
