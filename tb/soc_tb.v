`timescale 1ns / 1ps
`default_nettype none

module soc_tb;

    reg clk;
    reg resetn;

    wire trap;
    wire uart_tx;

    integer cycle_count;
    integer rom_addr_seen;
    integer rom_data_seen;

    soc_top dut (
        .clk(clk),
        .resetn(resetn),
        .trap(trap),
    .   uart_tx(uart_tx)
    );

    // 100 MHz simulation clock
    // Physical-design target sẽ quyết định sau.
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        resetn       = 1'b0;
        cycle_count  = 0;
        rom_addr_seen = 0;
        rom_data_seen = 0;

        $dumpfile("tb/soc_tb.vcd");
        $dumpvars(0, soc_tb);

        $display("========================================");
        $display(" PicoRV32 AXI SoC Boot ROM Test");
        $display("========================================");

        // Hold reset for several cycles
        repeat (8)
            @(posedge clk);

        // Release reset away from active clock edge
        @(negedge clk);
        resetn = 1'b1;

        $display("[TB] Reset released");

        // Give CPU enough time to generate AXI instruction fetch
        repeat (300) begin
            @(posedge clk);

            cycle_count = cycle_count + 1;

            // ----------------------------------------------------
            // Detect address transaction routed to ROM (M0)
            // ----------------------------------------------------
            if (dut.m_arvalid[0] && dut.m_arready[0]) begin

                $display(
                    "[TB] ROM AXI READ  cycle=%0d addr=0x%08x",
                    cycle_count,
                    dut.m_araddr[31:0]
                );

                if (dut.m_araddr[11:0] !== 12'h000) begin
                    $display(
                        "[FAIL] Expected ROM offset 0x000, got 0x%03x",
                        dut.m_araddr[11:0]
                    );
                    $finish;
                end

                rom_addr_seen = 1;
            end


            // ----------------------------------------------------
            // Detect instruction returned from Boot ROM
            // ----------------------------------------------------
            if (dut.rom_rvalid && dut.m_rready[0]) begin

                $display(
                    "[TB] ROM RESPONSE cycle=%0d data=0x%08x",
                    cycle_count,
                    dut.rom_rdata
                );

                if (dut.rom_rdata !== 32'h0000_006f) begin
                    $display(
                        "[FAIL] Expected JAL x0,0 = 0x0000006f, got 0x%08x",
                        dut.rom_rdata
                    );
                    $finish;
                end

                rom_data_seen = 1;
            end


            // PicoRV32 should never trap on our infinite JAL loop
            if (trap) begin
                $display("[FAIL] CPU entered TRAP state");
                $finish;
            end


            // ----------------------------------------------------
            // PASS condition
            // ----------------------------------------------------
            if (rom_addr_seen && rom_data_seen) begin

                $display("");
                $display("========================================");
                $display("[PASS] CPU -> AXI -> ROM path works");
                $display("[PASS] Address  : 0x00000000");
                $display("[PASS] Data     : 0x0000006f");
                $display("[PASS] CPU trap : 0");
                $display("========================================");

                repeat (10)
                    @(posedge clk);

                $finish;
            end
        end


        // --------------------------------------------------------
        // Timeout
        // --------------------------------------------------------

        $display("");
        $display("[FAIL] Simulation timeout");

        if (!rom_addr_seen)
            $display("[FAIL] CPU never issued a read to Boot ROM");

        if (!rom_data_seen)
            $display("[FAIL] Boot ROM response was never received");

        $finish;
    end

endmodule

`default_nettype wire
