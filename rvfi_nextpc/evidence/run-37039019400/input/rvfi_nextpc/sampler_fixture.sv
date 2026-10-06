// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
module sampler_fixture (
  input logic clk_i, rst_ni,
  input logic irq_software_i, irq_timer_i, irq_external_i,
  input logic [14:0] irq_fast_i,
  input logic irq_nm_i, debug_req_i,
  output logic rvfi_valid,
  output logic [63:0] rvfi_order,
  output logic [31:0] rvfi_pc_rdata, rvfi_insn, rvfi_pc_wdata,
  output logic [4:0] rvfi_rs1_addr, rvfi_rs2_addr, rvfi_rd_addr,
  output logic [31:0] rvfi_rs1_rdata, rvfi_rs2_rdata, rvfi_rd_wdata,
  output logic rvfi_trap, rvfi_halt, rvfi_intr,
  output logic [1:0] rvfi_mode, rvfi_ixl,
  output logic [3:0] rvfi_mem_rmask, rvfi_mem_wmask,
  output logic [31:0] rvfi_ext_pre_mip, rvfi_ext_post_mip,
  output logic rvfi_ext_nmi, rvfi_ext_nmi_int, rvfi_ext_debug_req,
  output logic rvfi_ext_debug_mode, rvfi_ext_irq_valid, rvfi_ext_rf_wr_suppress
);
  logic [3:0] beat = 0;
  always_ff @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      beat <= 0;
      rvfi_valid <= 0;
      rvfi_order <= 0;
      rvfi_pc_rdata <= 0;
      rvfi_pc_wdata <= 0;
      rvfi_rs1_rdata <= 0;
      rvfi_rd_wdata <= 0;
    end else begin
      if (beat < 10) beat <= beat + 1'b1;
      rvfi_valid <= beat >= 2 && beat < 5;
      rvfi_order <= 64'(beat) - 2;
      rvfi_pc_rdata <= 32'h80000080 + 4 * (32'(beat) - 2);
      rvfi_pc_wdata <= 32'h80000084 + 4 * (32'(beat) - 2);
      rvfi_rs1_rdata <= 32'(beat) - 2;
      rvfi_rd_wdata <= 32'(beat) - 1;
    end
  end
  assign rvfi_insn = 32'h00140413;
  assign rvfi_rs1_addr = 5'd8;
  assign rvfi_rs2_addr = 0;
  assign rvfi_rd_addr = 5'd8;
  assign rvfi_rs2_rdata = 0;
  assign rvfi_trap = 0;
  assign rvfi_halt = 0;
  assign rvfi_intr = 0;
  assign rvfi_mode = 3;
  assign rvfi_ixl = 1;
  assign rvfi_mem_rmask = 0;
  assign rvfi_mem_wmask = 0;
  assign rvfi_ext_pre_mip = 0;
  assign rvfi_ext_post_mip = 0;
  assign rvfi_ext_nmi = 0;
  assign rvfi_ext_nmi_int = 0;
  assign rvfi_ext_debug_req = 0;
  assign rvfi_ext_debug_mode = 0;
  assign rvfi_ext_irq_valid = 0;
  assign rvfi_ext_rf_wr_suppress = 0;
endmodule
