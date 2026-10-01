`timescale 1ns / 1ps
`default_nettype none

module soc_top (
    input  wire clk,
    input  wire resetn,
    output wire trap,
    output wire uart_tx
);

    // ================================================================
    // Reset synchronizer
    //
    // External resetn:
    //   - asynchronous assertion
    //   - synchronous deassertion
    //
    // Only this synchronizer is driven directly by external resetn.
    // The rest of the SoC uses resetn_int.
    // ================================================================

    (* async_reg = "true" *) reg [1:0] reset_sync;

    always @(posedge clk or negedge resetn) begin
        if (!resetn)
            reset_sync <= 2'b00;
        else
            reset_sync <= {reset_sync[0], 1'b1};
    end

    wire resetn_int;
    assign resetn_int = reset_sync[1];

    // ============================================================
    // PicoRV32 AXI master signals
    // ============================================================

    wire [31:0] cpu_awaddr;
    wire [2:0]  cpu_awprot;
    wire        cpu_awvalid;
    wire        cpu_awready;

    wire [31:0] cpu_wdata;
    wire [3:0]  cpu_wstrb;
    wire        cpu_wvalid;
    wire        cpu_wready;

    wire        cpu_bvalid;
    wire        cpu_bready;
    wire [1:0]  cpu_bresp_unused;

    wire [31:0] cpu_araddr;
    wire [2:0]  cpu_arprot;
    wire        cpu_arvalid;
    wire        cpu_arready;

    wire [31:0] cpu_rdata;
    wire        cpu_rvalid;
    wire        cpu_rready;
    wire [1:0]  cpu_rresp_unused;

    // PicoRV32 unused interfaces
    wire        pcpi_valid;
    wire [31:0] pcpi_insn;
    wire [31:0] pcpi_rs1;
    wire [31:0] pcpi_rs2;

    wire [31:0] eoi;

    wire        trace_valid;
    wire [35:0] trace_data;


    // ============================================================
    // PicoRV32 AXI CPU
    // ============================================================


    // ============================================================
    // V3 Hierarchical CPU
    //
    // Hardened cpu_block macro.
    // PicoRV32 parameters are baked into the hard macro.
    // ============================================================

    cpu_block cpu (
        .clk             (clk),
        .resetn          (resetn_int),
        .trap            (trap),

        .mem_axi_awvalid (cpu_awvalid),
        .mem_axi_awready (cpu_awready),
        .mem_axi_awaddr  (cpu_awaddr),
        .mem_axi_awprot  (cpu_awprot),

        .mem_axi_wvalid  (cpu_wvalid),
        .mem_axi_wready  (cpu_wready),
        .mem_axi_wdata   (cpu_wdata),
        .mem_axi_wstrb   (cpu_wstrb),

        .mem_axi_bvalid  (cpu_bvalid),
        .mem_axi_bready  (cpu_bready),

        .mem_axi_arvalid (cpu_arvalid),
        .mem_axi_arready (cpu_arready),
        .mem_axi_araddr  (cpu_araddr),
        .mem_axi_arprot  (cpu_arprot),

        .mem_axi_rvalid  (cpu_rvalid),
        .mem_axi_rready  (cpu_rready),
        .mem_axi_rdata   (cpu_rdata)
    );



    // ============================================================
    // AXI Interconnect master-side buses
    //
    // M0 = Boot ROM
    // M1 = RAM
    // M2 = UART
    // ============================================================

    wire [95:0] m_awaddr;
    wire [8:0]  m_awprot;
    wire [2:0]  m_awvalid;
    wire [2:0]  m_awready;

    wire [95:0] m_wdata;
    wire [11:0] m_wstrb;
    wire [2:0]  m_wvalid;
    wire [2:0]  m_wready;

    wire [5:0]  m_bresp;
    wire [2:0]  m_bvalid;
    wire [2:0]  m_bready;

    wire [95:0] m_araddr;
    wire [8:0]  m_arprot;
    wire [2:0]  m_arvalid;
    wire [2:0]  m_arready;

    wire [95:0] m_rdata;
    wire [5:0]  m_rresp;
    wire [2:0]  m_rvalid;
    wire [2:0]  m_rready;


    // ============================================================
    // AXI4-Lite Interconnect
    //
    // Memory map:
    //
    // M0 Boot ROM : 0x0000_0000 - 0x0000_0FFF  (4 KiB)
    // M1 RAM      : 0x1000_0000 - 0x1000_03FF  (1 KiB)
    // M2 UART     : 0x2000_0000 - 0x2000_0FFF  (4 KiB)
    //
    // ============================================================

    axil_interconnect #(
        .S_COUNT(1),
        .M_COUNT(3),

        .DATA_WIDTH(32),
        .ADDR_WIDTH(32),

        .M_REGIONS(1),

        // NOTE:
        // M0 occupies least-significant field
        // M1 next
        // M2 most-significant field
        .M_BASE_ADDR({
            32'h2000_0000,   // M2 UART
            32'h1000_0000,   // M1 RAM
            32'h0000_0000    // M0 ROM
        }),

        .M_ADDR_WIDTH({
            32'd12,          // UART 4 KiB
            32'd10,          // RAM  1 KiB
            32'd12           // ROM  4 KiB
        }),

        .M_CONNECT_READ(3'b111),

        // UART = write
        // RAM  = write
        // ROM  = read-only
        .M_CONNECT_WRITE(3'b110),

        .M_SECURE(3'b000)
    ) u_axi_interconnect (
        .clk(clk),

        // axil_interconnect uses active-high reset
        .rst(~resetn_int),

        // --------------------------------------------------------
        // Slave side = CPU
        // --------------------------------------------------------

        .s_axil_awaddr(cpu_awaddr),
        .s_axil_awprot(cpu_awprot),
        .s_axil_awvalid(cpu_awvalid),
        .s_axil_awready(cpu_awready),

        .s_axil_wdata(cpu_wdata),
        .s_axil_wstrb(cpu_wstrb),
        .s_axil_wvalid(cpu_wvalid),
        .s_axil_wready(cpu_wready),

        .s_axil_bresp(cpu_bresp_unused),
        .s_axil_bvalid(cpu_bvalid),
        .s_axil_bready(cpu_bready),

        .s_axil_araddr(cpu_araddr),
        .s_axil_arprot(cpu_arprot),
        .s_axil_arvalid(cpu_arvalid),
        .s_axil_arready(cpu_arready),

        .s_axil_rdata(cpu_rdata),
        .s_axil_rresp(cpu_rresp_unused),
        .s_axil_rvalid(cpu_rvalid),
        .s_axil_rready(cpu_rready),

        // --------------------------------------------------------
        // Master side = ROM / RAM / UART
        // --------------------------------------------------------

        .m_axil_awaddr(m_awaddr),
        .m_axil_awprot(m_awprot),
        .m_axil_awvalid(m_awvalid),
        .m_axil_awready(m_awready),

        .m_axil_wdata(m_wdata),
        .m_axil_wstrb(m_wstrb),
        .m_axil_wvalid(m_wvalid),
        .m_axil_wready(m_wready),

        .m_axil_bresp(m_bresp),
        .m_axil_bvalid(m_bvalid),
        .m_axil_bready(m_bready),

        .m_axil_araddr(m_araddr),
        .m_axil_arprot(m_arprot),
        .m_axil_arvalid(m_arvalid),
        .m_axil_arready(m_arready),

        .m_axil_rdata(m_rdata),
        .m_axil_rresp(m_rresp),
        .m_axil_rvalid(m_rvalid),
        .m_axil_rready(m_rready)
    );


    // ============================================================
    // M0 - Boot ROM placeholder
    //
    // Chưa implement ROM.
    // Chỉ tie-off để test hierarchy/interconnect.
    // ============================================================

        // ============================================================
    // M0 - Boot ROM
    //
    // Address window:
    // 0x0000_0000 - 0x0000_0FFF
    //
    // Current ROM content is only a temporary instruction-fetch
    // test. Real firmware will be added later.
    // ============================================================

    wire        rom_awready;
    wire        rom_wready;
    wire [1:0]  rom_bresp;
    wire        rom_bvalid;

    wire        rom_arready;
    wire [31:0] rom_rdata;
    wire [1:0]  rom_rresp;
    wire        rom_rvalid;


    // ROM is read-only.
    //
    // M_CONNECT_WRITE[0] = 0 in the AXI interconnect,
    // therefore writes are never routed to this slave.
    assign rom_awready = 1'b0;
    assign rom_wready  = 1'b0;
    assign rom_bresp   = 2'b00;
    assign rom_bvalid  = 1'b0;


    boot_rom rom (
        .clk(clk),
        .rst(~resetn_int),

        .s_axil_araddr(m_araddr[0 +: 12]),
        .s_axil_arprot(m_arprot[0 +: 3]),
        .s_axil_arvalid(m_arvalid[0]),
        .s_axil_arready(rom_arready),

        .s_axil_rdata(rom_rdata),
        .s_axil_rresp(rom_rresp),
        .s_axil_rvalid(rom_rvalid),
        .s_axil_rready(m_rready[0])
    );


    // ============================================================
    // M1 - 1 KiB AXI-Lite RAM
    //
    // ADDR_WIDTH = 10
    // 2^10 bytes = 1024 bytes
    // ============================================================

    wire        ram_awready;
    wire        ram_wready;
    wire [1:0]  ram_bresp;
    wire        ram_bvalid;

    wire        ram_arready;
    wire [31:0] ram_rdata;
    wire [1:0]  ram_rresp;
    wire        ram_rvalid;

    // ============================================================
    // M1 - 1 KiB hard SRAM
    //
    // 256 words x 32 bit
    // SKY130 OpenRAM macro
    // ============================================================

    axil_sram ram (
        .clk(clk),
        .rst(~resetn_int),

        // Slot M1
        .s_axil_awaddr(m_awaddr[32 +: 10]),
        .s_axil_awprot(m_awprot[3 +: 3]),
        .s_axil_awvalid(m_awvalid[1]),
        .s_axil_awready(ram_awready),

        .s_axil_wdata(m_wdata[32 +: 32]),
        .s_axil_wstrb(m_wstrb[4 +: 4]),
        .s_axil_wvalid(m_wvalid[1]),
        .s_axil_wready(ram_wready),

        .s_axil_bresp(ram_bresp),
        .s_axil_bvalid(ram_bvalid),
        .s_axil_bready(m_bready[1]),

        .s_axil_araddr(m_araddr[32 +: 10]),
        .s_axil_arprot(m_arprot[3 +: 3]),
        .s_axil_arvalid(m_arvalid[1]),
        .s_axil_arready(ram_arready),

        .s_axil_rdata(ram_rdata),
        .s_axil_rresp(ram_rresp),
        .s_axil_rvalid(ram_rvalid),
        .s_axil_rready(m_rready[1])
    );


    // ============================================================
    // M2 - UART placeholder
    //
    // Chưa implement UART AXI wrapper.
    // ============================================================

        // ============================================================
    // M2 - AXI4-Lite UART TX
    //
    // Address window:
    //
    // 0x2000_0000 - 0x2000_0FFF
    //
    // Local register map:
    //
    // 0x000 : TXDATA
    // 0x004 : STATUS
    // 0x008 : PRESCALE
    // ============================================================

    wire        uart_awready;
    wire        uart_wready;
    wire [1:0]  uart_bresp;
    wire        uart_bvalid;

    wire        uart_arready;
    wire [31:0] uart_rdata;
    wire [1:0]  uart_rresp;
    wire        uart_rvalid;


    uart_axil #(
        .DEFAULT_PRESCALE(16'd54)
    ) u_uart_axil (
        .clk(clk),
        .rst(~resetn_int),

        // --------------------------------------------------------
        // AXI write address
        // M2 occupies slot 2
        // --------------------------------------------------------

        .s_axil_awaddr(m_awaddr[64 +: 12]),
        .s_axil_awprot(m_awprot[6 +: 3]),
        .s_axil_awvalid(m_awvalid[2]),
        .s_axil_awready(uart_awready),

        // --------------------------------------------------------
        // AXI write data
        // --------------------------------------------------------

        .s_axil_wdata(m_wdata[64 +: 32]),
        .s_axil_wstrb(m_wstrb[8 +: 4]),
        .s_axil_wvalid(m_wvalid[2]),
        .s_axil_wready(uart_wready),

        // --------------------------------------------------------
        // AXI write response
        // --------------------------------------------------------

        .s_axil_bresp(uart_bresp),
        .s_axil_bvalid(uart_bvalid),
        .s_axil_bready(m_bready[2]),

        // --------------------------------------------------------
        // AXI read address
        // --------------------------------------------------------

        .s_axil_araddr(m_araddr[64 +: 12]),
        .s_axil_arprot(m_arprot[6 +: 3]),
        .s_axil_arvalid(m_arvalid[2]),
        .s_axil_arready(uart_arready),

        // --------------------------------------------------------
        // AXI read response
        // --------------------------------------------------------

        .s_axil_rdata(uart_rdata),
        .s_axil_rresp(uart_rresp),
        .s_axil_rvalid(uart_rvalid),
        .s_axil_rready(m_rready[2]),

        // --------------------------------------------------------
        // Physical UART output
        // --------------------------------------------------------

        .txd(uart_tx)
    );


    // ============================================================
    // Combine responses from M0/M1/M2 back into interconnect
    //
    // Vector order:
    // { M2, M1, M0 }
    // ============================================================

    assign m_awready = {
        uart_awready,
        ram_awready,
        rom_awready
    };

    assign m_wready = {
        uart_wready,
        ram_wready,
        rom_wready
    };

    assign m_bresp = {
        uart_bresp,
        ram_bresp,
        rom_bresp
    };

    assign m_bvalid = {
        uart_bvalid,
        ram_bvalid,
        rom_bvalid
    };

    assign m_arready = {
        uart_arready,
        ram_arready,
        rom_arready
    };

    assign m_rdata = {
        uart_rdata,
        ram_rdata,
        rom_rdata
    };

    assign m_rresp = {
        uart_rresp,
        ram_rresp,
        rom_rresp
    };

    assign m_rvalid = {
        uart_rvalid,
        ram_rvalid,
        rom_rvalid
    };

endmodule

`default_nettype wire