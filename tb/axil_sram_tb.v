`timescale 1ns / 1ps

module axil_sram_tb;

    reg clk = 0;
    always #10 clk = ~clk;   // 50 MHz

    reg rst = 1;

    reg  [9:0]  awaddr;
    reg  [2:0]  awprot;
    reg         awvalid;
    wire        awready;

    reg  [31:0] wdata;
    reg  [3:0]  wstrb;
    reg         wvalid;
    wire        wready;

    wire [1:0]  bresp;
    wire        bvalid;
    reg         bready;

    reg  [9:0]  araddr;
    reg  [2:0]  arprot;
    reg         arvalid;
    wire        arready;

    wire [31:0] rdata;
    wire [1:0]  rresp;
    wire        rvalid;
    reg         rready;

    axil_sram dut (
        .clk(clk),
        .rst(rst),

        .s_axil_awaddr(awaddr),
        .s_axil_awprot(awprot),
        .s_axil_awvalid(awvalid),
        .s_axil_awready(awready),

        .s_axil_wdata(wdata),
        .s_axil_wstrb(wstrb),
        .s_axil_wvalid(wvalid),
        .s_axil_wready(wready),

        .s_axil_bresp(bresp),
        .s_axil_bvalid(bvalid),
        .s_axil_bready(bready),

        .s_axil_araddr(araddr),
        .s_axil_arprot(arprot),
        .s_axil_arvalid(arvalid),
        .s_axil_arready(arready),

        .s_axil_rdata(rdata),
        .s_axil_rresp(rresp),
        .s_axil_rvalid(rvalid),
        .s_axil_rready(rready)
    );

    task axil_write;
        input [9:0] addr;
        input [31:0] data;
        input [3:0] strb;
        begin
            @(negedge clk);

            awaddr  = addr;
            awvalid = 1'b1;

            wdata   = data;
            wstrb   = strb;
            wvalid  = 1'b1;

            wait (awready && wready);
            @(posedge clk);
            @(negedge clk);

            awvalid = 1'b0;
            wvalid  = 1'b0;

            wait (bvalid);

            if (bresp !== 2'b00) begin
                $display("[FAIL] AXI write BRESP = %b", bresp);
                $finish;
            end

            bready = 1'b1;
            @(posedge clk);
            @(negedge clk);
            bready = 1'b0;
        end
    endtask

    task axil_read;
        input [9:0] addr;
        output [31:0] data;
        begin
            @(negedge clk);

            araddr  = addr;
            arvalid = 1'b1;

            wait (arready);
            @(posedge clk);
            @(negedge clk);

            arvalid = 1'b0;

            wait (rvalid);

            data = rdata;

            if (rresp !== 2'b00) begin
                $display("[FAIL] AXI read RRESP = %b", rresp);
                $finish;
            end

            rready = 1'b1;
            @(posedge clk);
            @(negedge clk);
            rready = 1'b0;
        end
    endtask

    reg [31:0] rd;

    initial begin
        awaddr  = 0;
        awprot  = 0;
        awvalid = 0;

        wdata   = 0;
        wstrb   = 0;
        wvalid  = 0;

        bready  = 0;

        araddr  = 0;
        arprot  = 0;
        arvalid = 0;

        rready  = 0;

        repeat (5) @(posedge clk);
        rst = 0;

        // ----------------------------------------------------------
        // Full 32-bit write/read
        // ----------------------------------------------------------

        axil_write(10'h010, 32'hDEADBEEF, 4'b1111);
        axil_read (10'h010, rd);

        if (rd !== 32'hDEADBEEF) begin
            $display(
                "[FAIL] Full-word readback: expected DEADBEEF, got %08x",
                rd
            );
            $finish;
        end

        $display("[PASS] Full-word SRAM write/read");

        // ----------------------------------------------------------
        // Byte-mask test:
        // Replace byte [15:8] BE -> AA
        //
        // DE AD BE EF
        //       ↓
        // DE AD AA EF
        // ----------------------------------------------------------

        axil_write(10'h010, 32'h0000AA00, 4'b0010);
        axil_read (10'h010, rd);

        if (rd !== 32'hDEADAAEF) begin
            $display(
                "[FAIL] Byte-mask readback: expected DEADAAEF, got %08x",
                rd
            );
            $finish;
        end

        $display("[PASS] SRAM byte write mask");
        $display("[PASS] AXI4-Lite -> SRAM macro wrapper");

        $finish;
    end

endmodule
