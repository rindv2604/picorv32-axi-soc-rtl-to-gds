`timescale 1ns / 1ps

module axil_sram (
    input  wire        clk,
    input  wire        rst,

    // AXI4-Lite write address
    input  wire [9:0]  s_axil_awaddr,
    input  wire [2:0]  s_axil_awprot,
    input  wire        s_axil_awvalid,
    output wire        s_axil_awready,

    // AXI4-Lite write data
    input  wire [31:0] s_axil_wdata,
    input  wire [3:0]  s_axil_wstrb,
    input  wire        s_axil_wvalid,
    output wire        s_axil_wready,

    // AXI4-Lite write response
    output wire [1:0]  s_axil_bresp,
    output wire        s_axil_bvalid,
    input  wire        s_axil_bready,

    // AXI4-Lite read address
    input  wire [9:0]  s_axil_araddr,
    input  wire [2:0]  s_axil_arprot,
    input  wire        s_axil_arvalid,
    output wire        s_axil_arready,

    // AXI4-Lite read data
    output wire [31:0] s_axil_rdata,
    output wire [1:0]  s_axil_rresp,
    output wire        s_axil_rvalid,
    input  wire        s_axil_rready
);

    // ----------------------------------------------------------------
    // AXI request holding registers
    // ----------------------------------------------------------------

    reg        aw_pending;
    reg [9:0]  awaddr_reg;

    reg        w_pending;
    reg [31:0] wdata_reg;
    reg [3:0]  wstrb_reg;

    reg        ar_pending;
    reg [9:0]  araddr_reg;

    // ----------------------------------------------------------------
    // Response/state registers
    // ----------------------------------------------------------------

    reg        write_wait;
    reg        read_wait;

    reg        bvalid_reg;
    reg        rvalid_reg;
    reg [31:0] rdata_reg;

    assign s_axil_bvalid = bvalid_reg;
    assign s_axil_bresp  = 2'b00;     // AXI OKAY

    assign s_axil_rvalid = rvalid_reg;
    assign s_axil_rdata  = rdata_reg;
    assign s_axil_rresp  = 2'b00;     // AXI OKAY

    // One outstanding transaction per direction.
    assign s_axil_awready =
        !aw_pending && !write_wait && !bvalid_reg;

    assign s_axil_wready =
        !w_pending && !write_wait && !bvalid_reg;

    assign s_axil_arready =
        !ar_pending && !read_wait && !rvalid_reg;

    // ----------------------------------------------------------------
    // SRAM transaction scheduling
    //
    // Serialize SRAM read/write requests.  This avoids undefined
    // same-address read/write behavior between the 1RW and 1R ports.
    // ----------------------------------------------------------------

    wire memory_idle =
        !write_wait &&
        !read_wait &&
        !bvalid_reg &&
        !rvalid_reg;

    wire write_launch =
        memory_idle &&
        aw_pending &&
        w_pending;

    wire read_launch =
        memory_idle &&
        !write_launch &&
        ar_pending;

    // 10-bit AXI byte address:
    //
    //   [9:2] = SRAM word address
    //   [1:0] = byte offset within 32-bit word
    //
    wire [7:0] sram_write_addr = awaddr_reg[9:2];
    wire [7:0] sram_read_addr  = araddr_reg[9:2];

    wire [31:0] sram_dout0;
    wire [31:0] sram_dout1;

    // ----------------------------------------------------------------
    // Hard SRAM macro
    //
    // Port 0 : write
    // Port 1 : read
    //
    // csb = active low
    // web = active low
    // ----------------------------------------------------------------

    (* keep = "true" *)
    sky130_sram_1kbyte_1rw1r_32x256_8 u_sram_macro (
        // Port 0 - RW, used here for AXI writes
        .clk0   (clk),
        .csb0   (~write_launch),
        .web0   (1'b0),
        .wmask0 (wstrb_reg),
        .addr0  (sram_write_addr),
        .din0   (wdata_reg),
        .dout0  (sram_dout0),

        // Port 1 - read only
        .clk1   (clk),
        .csb1   (~read_launch),
        .addr1  (sram_read_addr),
        .dout1  (sram_dout1)
    );

    // ----------------------------------------------------------------
    // AXI control
    // ----------------------------------------------------------------

    always @(posedge clk) begin
        if (rst) begin
            aw_pending <= 1'b0;
            awaddr_reg <= 10'd0;

            w_pending <= 1'b0;
            wdata_reg <= 32'd0;
            wstrb_reg <= 4'd0;

            ar_pending <= 1'b0;
            araddr_reg <= 10'd0;

            write_wait <= 1'b0;
            read_wait  <= 1'b0;

            bvalid_reg <= 1'b0;
            rvalid_reg <= 1'b0;
            rdata_reg  <= 32'd0;
        end else begin

            // --------------------------------------------------------
            // Capture AXI write address
            // --------------------------------------------------------

            if (s_axil_awready && s_axil_awvalid) begin
                aw_pending <= 1'b1;
                awaddr_reg <= s_axil_awaddr;
            end

            // --------------------------------------------------------
            // Capture AXI write data
            // --------------------------------------------------------

            if (s_axil_wready && s_axil_wvalid) begin
                w_pending <= 1'b1;
                wdata_reg <= s_axil_wdata;
                wstrb_reg <= s_axil_wstrb;
            end

            // --------------------------------------------------------
            // Launch SRAM write
            //
            // SRAM samples control/address/data on this rising edge
            // and performs the modeled operation afterward.
            // --------------------------------------------------------

            if (write_launch) begin
                aw_pending <= 1'b0;
                w_pending  <= 1'b0;
                write_wait <= 1'b1;
            end else if (write_wait) begin
                write_wait <= 1'b0;
                bvalid_reg <= 1'b1;
            end

            // Write response consumed
            if (bvalid_reg && s_axil_bready)
                bvalid_reg <= 1'b0;

            // --------------------------------------------------------
            // Capture AXI read address
            // --------------------------------------------------------

            if (s_axil_arready && s_axil_arvalid) begin
                ar_pending <= 1'b1;
                araddr_reg <= s_axil_araddr;
            end

            // --------------------------------------------------------
            // Launch SRAM read
            // --------------------------------------------------------

            if (read_launch) begin
                ar_pending <= 1'b0;
                read_wait  <= 1'b1;
            end else if (read_wait) begin
                // SRAM result from previous transaction
                rdata_reg  <= sram_dout1;
                rvalid_reg <= 1'b1;
                read_wait  <= 1'b0;
            end

            // Read response consumed
            if (rvalid_reg && s_axil_rready)
                rvalid_reg <= 1'b0;
        end
    end

    // AXI PROT is intentionally unused for this simple SRAM slave.
    wire unused_prot = &{1'b0, s_axil_awprot, s_axil_arprot};

endmodule
