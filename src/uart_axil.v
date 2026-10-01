`timescale 1ns / 1ps
`default_nettype none

module uart_axil #(
    parameter DEFAULT_PRESCALE = 16'd54
)(
    input  wire        clk,
    input  wire        rst,

    // AXI4-Lite write address
    input  wire [11:0] s_axil_awaddr,
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
    output reg         s_axil_bvalid,
    input  wire        s_axil_bready,

    // AXI4-Lite read address
    input  wire [11:0] s_axil_araddr,
    input  wire [2:0]  s_axil_arprot,
    input  wire        s_axil_arvalid,
    output wire        s_axil_arready,

    // AXI4-Lite read data
    output reg  [31:0] s_axil_rdata,
    output wire [1:0]  s_axil_rresp,
    output reg         s_axil_rvalid,
    input  wire        s_axil_rready,

    // UART serial output
    output wire        txd
);

    // ============================================================
    // Register map
    //
    // 0x000 : TXDATA
    //         write [7:0] to transmit
    //
    // 0x004 : STATUS
    //         bit 0 = UART busy
    //         bit 1 = UART stream ready
    //         bit 2 = TX byte pending
    //
    // 0x008 : PRESCALE
    //         bits [15:0]
    // ============================================================

    localparam REG_TXDATA   = 12'h000;
    localparam REG_STATUS   = 12'h004;
    localparam REG_PRESCALE = 12'h008;


    // ============================================================
    // UART stream interface
    // ============================================================

    reg  [7:0]  tx_data_reg;
    reg         tx_valid_reg;
    wire        tx_ready;
    wire        tx_busy;

    reg [15:0] prescale_reg;


    uart_tx #(
        .DATA_WIDTH(8)
    ) u_uart_tx (
        .clk(clk),
        .rst(rst),

        .s_axis_tdata(tx_data_reg),
        .s_axis_tvalid(tx_valid_reg),
        .s_axis_tready(tx_ready),

        .txd(txd),
        .busy(tx_busy),

        .prescale(prescale_reg)
    );


    // ============================================================
    // AXI write buffering
    //
    // AXI-Lite AW and W channels are independent, so capture them
    // separately before performing a register write.
    // ============================================================

    reg [11:0] awaddr_reg;
    reg        aw_pending;

    reg [31:0] wdata_reg;
    reg [3:0]  wstrb_reg;
    reg        w_pending;


    assign s_axil_awready = !aw_pending && !s_axil_bvalid;
    assign s_axil_wready  = !w_pending  && !s_axil_bvalid;

    assign s_axil_bresp = 2'b00; // OKAY


    // ============================================================
    // AXI read
    // ============================================================

    assign s_axil_arready = !s_axil_rvalid;
    assign s_axil_rresp   = 2'b00; // OKAY


    // ============================================================
    // Sequential logic
    // ============================================================

    always @(posedge clk) begin
        if (rst) begin
            awaddr_reg    <= 12'b0;
            aw_pending    <= 1'b0;

            wdata_reg     <= 32'b0;
            wstrb_reg     <= 4'b0;
            w_pending     <= 1'b0;

            s_axil_bvalid <= 1'b0;

            s_axil_rdata  <= 32'b0;
            s_axil_rvalid <= 1'b0;

            tx_data_reg   <= 8'b0;
            tx_valid_reg  <= 1'b0;

            prescale_reg  <= DEFAULT_PRESCALE;
        end
        else begin

            // ----------------------------------------------------
            // UART AXI-Stream handshake
            // ----------------------------------------------------

            if (tx_valid_reg && tx_ready)
                tx_valid_reg <= 1'b0;


            // ----------------------------------------------------
            // Capture AXI write address
            // ----------------------------------------------------

            if (s_axil_awvalid && s_axil_awready) begin
                awaddr_reg <= s_axil_awaddr;
                aw_pending <= 1'b1;
            end


            // ----------------------------------------------------
            // Capture AXI write data
            // ----------------------------------------------------

            if (s_axil_wvalid && s_axil_wready) begin
                wdata_reg  <= s_axil_wdata;
                wstrb_reg  <= s_axil_wstrb;
                w_pending  <= 1'b1;
            end


            // ----------------------------------------------------
            // Perform register write
            // ----------------------------------------------------

            if (aw_pending && w_pending && !s_axil_bvalid) begin

                case (awaddr_reg)

                    REG_TXDATA: begin
                        // Only accept another character if the
                        // single-entry TX staging register is free.
                        if (!tx_valid_reg) begin
                            if (wstrb_reg[0]) begin
                                tx_data_reg  <= wdata_reg[7:0];
                                tx_valid_reg <= 1'b1;
                            end

                            aw_pending    <= 1'b0;
                            w_pending     <= 1'b0;
                            s_axil_bvalid <= 1'b1;
                        end
                    end


                    REG_PRESCALE: begin
                        if (wstrb_reg[0])
                            prescale_reg[7:0] <= wdata_reg[7:0];

                        if (wstrb_reg[1])
                            prescale_reg[15:8] <= wdata_reg[15:8];

                        aw_pending    <= 1'b0;
                        w_pending     <= 1'b0;
                        s_axil_bvalid <= 1'b1;
                    end


                    default: begin
                        aw_pending    <= 1'b0;
                        w_pending     <= 1'b0;
                        s_axil_bvalid <= 1'b1;
                    end

                endcase
            end


            // ----------------------------------------------------
            // AXI write response
            // ----------------------------------------------------

            if (s_axil_bvalid && s_axil_bready)
                s_axil_bvalid <= 1'b0;


            // ----------------------------------------------------
            // AXI read
            // ----------------------------------------------------

            if (s_axil_arvalid && s_axil_arready) begin

                case (s_axil_araddr)

                    REG_TXDATA:
                        s_axil_rdata <= {
                            24'b0,
                            tx_data_reg
                        };

                    REG_STATUS:
                        s_axil_rdata <= {
                            29'b0,
                            tx_valid_reg,
                            tx_ready,
                            tx_busy
                        };

                    REG_PRESCALE:
                        s_axil_rdata <= {
                            16'b0,
                            prescale_reg
                        };

                    default:
                        s_axil_rdata <= 32'b0;

                endcase

                s_axil_rvalid <= 1'b1;
            end
            else if (s_axil_rvalid && s_axil_rready) begin
                s_axil_rvalid <= 1'b0;
            end

        end
    end


    // Protection attributes are unused.
    wire unused_prot;
    assign unused_prot = ^{s_axil_awprot, s_axil_arprot};

endmodule

`default_nettype wire