// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
module sampler_fixture (
  input logic clk_i, rst_ni,
  input logic irq_software_i, irq_timer_i, irq_external_i,
  input logic [14:0] irq_fast_i,
  input logic irq_nm_i, debug_req_i,
  input logic [3:0] scenario_i,
  input logic inject_req_i, data_gnt_i, data_rvalid_i, data_err_i,
  output logic data_req_o, data_we_o,
  output logic [3:0] data_be_o,
  output logic [31:0] data_addr_o, data_wdata_o,
  output logic alert_minor_o, alert_major_internal_o, alert_major_bus_o,
  output logic rvfi_valid,
  output logic [63:0] rvfi_order,
  output logic [31:0] rvfi_pc_rdata, rvfi_insn, rvfi_pc_wdata,
  output logic [4:0] rvfi_rs1_addr, rvfi_rs2_addr, rvfi_rd_addr,
  output logic [31:0] rvfi_rs1_rdata, rvfi_rs2_rdata, rvfi_rd_wdata,
  output logic rvfi_trap, rvfi_halt, rvfi_intr,
  output logic [1:0] rvfi_mode, rvfi_ixl,
  output logic [3:0] rvfi_mem_rmask, rvfi_mem_wmask,
  output logic [31:0] rvfi_mem_addr, rvfi_mem_rdata, rvfi_mem_wdata,
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
      rvfi_order <= 64'(beat) - 1;
      rvfi_pc_rdata <= 32'h80000080 + 4 * (32'(beat) - 2);
      rvfi_pc_wdata <= 32'h80000084 + 4 * (32'(beat) - 2);
      rvfi_rs1_rdata <= 32'(beat) - 2;
      rvfi_rd_wdata <= 32'(beat) - 1;
    end
  end
  assign data_req_o = inject_req_i || (scenario_i == 9 && beat == 3);
  assign data_we_o = scenario_i == 10 && beat == 3;
  assign data_be_o = 15;
  assign data_addr_o = 32'h81234560;
  assign data_wdata_o = 32'h12345678;
  assign alert_minor_o = scenario_i == 11 && beat == 3;
  assign alert_major_internal_o = scenario_i == 12 && beat == 3;
  assign alert_major_bus_o = scenario_i == 13 && beat == 3;
  assign rvfi_insn = scenario_i == 2 ? 32'h00042403 : 32'h00140413;
  assign rvfi_rs1_addr = 5'd8;
  assign rvfi_rs2_addr = 0;
  assign rvfi_rd_addr = 5'd8;
  assign rvfi_rs2_rdata = 0;
  assign rvfi_trap = scenario_i == 4;
  assign rvfi_halt = scenario_i == 5;
  assign rvfi_intr = scenario_i == 6;
  assign rvfi_mode = scenario_i == 7 ? 0 : 3;
  assign rvfi_ixl = 1;
  assign rvfi_mem_rmask = scenario_i == 1 ? (beat == 3 ? 1 : beat == 4 ? 5 : 15) : 0;
  assign rvfi_mem_wmask = scenario_i == 3 ? 1 : 0;
  assign rvfi_mem_addr = 32'h12345678;
  assign rvfi_mem_rdata = 32'h87654321;
  assign rvfi_mem_wdata = 32'h12344321;
  assign rvfi_ext_pre_mip = 0;
  assign rvfi_ext_post_mip = 0;
  assign rvfi_ext_nmi = 0;
  assign rvfi_ext_nmi_int = 0;
  assign rvfi_ext_debug_req = 0;
  assign rvfi_ext_debug_mode = scenario_i == 14 && beat == 3;
  assign rvfi_ext_irq_valid = 0;
  assign rvfi_ext_rf_wr_suppress = scenario_i == 8;
endmodule
