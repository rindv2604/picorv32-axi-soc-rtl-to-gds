`default_nettype none

module cpu_block (
    input  wire        clk,
    input  wire        resetn,

    output wire        trap,

    // ============================================================
    // AXI4-Lite Master Interface
    // ============================================================

    // Write address channel
    output wire        mem_axi_awvalid,
    input  wire        mem_axi_awready,
    output wire [31:0] mem_axi_awaddr,
    output wire [2:0]  mem_axi_awprot,

    // Write data channel
    output wire        mem_axi_wvalid,
    input  wire        mem_axi_wready,
    output wire [31:0] mem_axi_wdata,
    output wire [3:0]  mem_axi_wstrb,

    // Write response channel
    input  wire        mem_axi_bvalid,
    output wire        mem_axi_bready,

    // Read address channel
    output wire        mem_axi_arvalid,
    input  wire        mem_axi_arready,
    output wire [31:0] mem_axi_araddr,
    output wire [2:0]  mem_axi_arprot,

    // Read data channel
    input  wire        mem_axi_rvalid,
    output wire        mem_axi_rready,
    input  wire [31:0] mem_axi_rdata
);

    // ============================================================
    // PicoRV32 AXI CPU
    //
    // Configuration kept identical to soc_top V2.
    // PCPI / IRQ / TRACE are disabled and are NOT exposed as
    // physical macro boundary pins.
    // ============================================================

    picorv32_axi #(
        .ENABLE_COUNTERS(1),
        .ENABLE_COUNTERS64(1),
        .ENABLE_REGS_16_31(1),
        .ENABLE_REGS_DUALPORT(1),

        .BARREL_SHIFTER(0),
        .COMPRESSED_ISA(0),

        .ENABLE_PCPI(0),
        .ENABLE_MUL(0),
        .ENABLE_FAST_MUL(0),
        .ENABLE_DIV(0),

        .ENABLE_IRQ(0),
        .ENABLE_TRACE(0),

        .PROGADDR_RESET(32'h0000_0000),

        // RAM:
        // 0x1000_0000 - 0x1000_03FF
        // Stack grows downward from 0x1000_0400
        .STACKADDR(32'h1000_0400)
    ) u_cpu (
        .clk(clk),
        .resetn(resetn),
        .trap(trap),

        .mem_axi_awvalid(mem_axi_awvalid),
        .mem_axi_awready(mem_axi_awready),
        .mem_axi_awaddr (mem_axi_awaddr),
        .mem_axi_awprot (mem_axi_awprot),

        .mem_axi_wvalid(mem_axi_wvalid),
        .mem_axi_wready(mem_axi_wready),
        .mem_axi_wdata (mem_axi_wdata),
        .mem_axi_wstrb (mem_axi_wstrb),

        .mem_axi_bvalid(mem_axi_bvalid),
        .mem_axi_bready(mem_axi_bready),

        .mem_axi_arvalid(mem_axi_arvalid),
        .mem_axi_arready(mem_axi_arready),
        .mem_axi_araddr (mem_axi_araddr),
        .mem_axi_arprot (mem_axi_arprot),

        .mem_axi_rvalid(mem_axi_rvalid),
        .mem_axi_rready(mem_axi_rready),
        .mem_axi_rdata (mem_axi_rdata),

        // PCPI disabled
        .pcpi_valid(),
        .pcpi_insn(),
        .pcpi_rs1(),
        .pcpi_rs2(),
        .pcpi_wr(1'b0),
        .pcpi_rd(32'b0),
        .pcpi_wait(1'b0),
        .pcpi_ready(1'b0),

        // IRQ disabled
        .irq(32'b0),
        .eoi(),

        // Trace disabled
        .trace_valid(),
        .trace_data()
    );

endmodule

`default_nettype wire
