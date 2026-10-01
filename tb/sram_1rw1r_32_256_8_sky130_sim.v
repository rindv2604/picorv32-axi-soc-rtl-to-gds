`timescale 1ns / 1ps

module sram_1rw1r_32_256_8_sky130 (
    input  wire        clk0,
    input  wire        csb0,
    input  wire        web0,
    input  wire [3:0]  wmask0,
    input  wire [7:0]  addr0,
    input  wire [31:0] din0,
    output reg  [31:0] dout0,

    input  wire        clk1,
    input  wire        csb1,
    input  wire [7:0]  addr1,
    output reg  [31:0] dout1
);

    reg [31:0] mem [0:255];

    // Port 0: read/write
    always @(posedge clk0) begin
        if (!csb0) begin
            if (!web0) begin
                if (wmask0[0])
                    mem[addr0][7:0] <= din0[7:0];

                if (wmask0[1])
                    mem[addr0][15:8] <= din0[15:8];

                if (wmask0[2])
                    mem[addr0][23:16] <= din0[23:16];

                if (wmask0[3])
                    mem[addr0][31:24] <= din0[31:24];
            end else begin
                dout0 <= mem[addr0];
            end
        end
    end

    // Port 1: read only
    always @(posedge clk1) begin
        if (!csb1)
            dout1 <= mem[addr1];
    end

endmodule
