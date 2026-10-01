`timescale 1ns / 1ps
`default_nettype none

module boot_rom (
    input  wire        clk,
    input  wire        rst,

    // AXI4-Lite read address channel
    input  wire [11:0] s_axil_araddr,
    input  wire [2:0]  s_axil_arprot,
    input  wire        s_axil_arvalid,
    output wire        s_axil_arready,

    // AXI4-Lite read data channel
    output reg  [31:0] s_axil_rdata,
    output wire [1:0]  s_axil_rresp,
    output reg         s_axil_rvalid,
    input  wire        s_axil_rready
);

    // Accept a new read when no response is pending,
    // or when the current response is accepted.
    assign s_axil_arready = ~s_axil_rvalid | s_axil_rready;

    // Always return AXI OKAY
    assign s_axil_rresp = 2'b00;

    // s_axil_arprot is intentionally unused for this ROM.

    always @(posedge clk) begin
        if (rst) begin
            s_axil_rvalid <= 1'b0;
            s_axil_rdata  <= 32'h0000_0013; // NOP
        end
        else begin
            if (s_axil_arvalid && s_axil_arready) begin
                s_axil_rvalid <= 1'b1;

                case (s_axil_araddr[11:2])

                    // ------------------------------------------------------------
                    // Temporary UART test firmware
                    //
                    // x5 = 0x20000000  UART base
                    //
                    // UART_PRESCALE = 2 (fast simulation)
                    // UART_TXDATA   = 'H'
                    // UART_TXDATA   = 'i'
                    // loop forever
                    // ------------------------------------------------------------

                    // lui t0, 0x20000
                    // t0 = 0x20000000
                    10'd0: s_axil_rdata <= 32'h2000_02b7;

                    // li t1, 2
                    // Simulation-only UART prescale
                    10'd1: s_axil_rdata <= 32'h0020_0313;

                    // sw t1, 8(t0)
                    // UART PRESCALE @ 0x20000008
                    10'd2: s_axil_rdata <= 32'h0062_a423;

                    // li t1, 'H' = 72 = 0x48
                    10'd3: s_axil_rdata <= 32'h0480_0313;

                    // sw t1, 0(t0)
                    // UART TXDATA
                    10'd4: s_axil_rdata <= 32'h0062_a023;

                    // li t1, 'i' = 105 = 0x69
                    10'd5: s_axil_rdata <= 32'h0690_0313;

                    // sw t1, 0(t0)
                    10'd6: s_axil_rdata <= 32'h0062_a023;

                    // jal x0, 0
                    10'd7: s_axil_rdata <= 32'h0000_006f;

                    default:
                        s_axil_rdata <= 32'h0000_0013;

                endcase
            end
            else if (s_axil_rvalid && s_axil_rready) begin
                s_axil_rvalid <= 1'b0;
            end
        end
    end

endmodule

`default_nettype wire
