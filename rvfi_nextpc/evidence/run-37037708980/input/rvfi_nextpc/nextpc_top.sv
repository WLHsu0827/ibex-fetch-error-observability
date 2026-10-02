// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
module nextpc_top #(
  parameter int unsigned BranchPredictor = 0
) (
  input logic clk_i, rst_ni,
  input logic irq_software_i, irq_timer_i, irq_external_i,
  input logic [14:0] irq_fast_i,
  input logic irq_nm_i, debug_req_i,
  output logic instr_req_o,
  output logic [31:0] instr_addr_o,
  input logic instr_rvalid_i,
  input logic [31:0] instr_rdata_i,
  output logic data_req_o, alert_minor_o, alert_major_internal_o, alert_major_bus_o,
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
  import ibex_pkg::*;
  ibex_top #(
    .BaseIsa(BaseIsaRV32I), .RV32E(1'b0), .RV32M(RV32MFast),
    .RV32B(RV32BNone), .RV32ZC(RV32Zca), .RegFile(RegFileFF),
    .BranchTargetALU(1'b0), .WritebackStage(1'b0),
    .BranchPredictor(bit'(BranchPredictor)), .ICache(1'b0), .ICacheECC(1'b0),
    .ICacheScramble(1'b0), .DbgTriggerEn(1'b0), .SecureIbex(1'b0),
    .PMPEnable(1'b0), .PMPGranularity(0), .PMPNumRegions(4),
    .MHPMCounterNum(0), .MHPMCounterWidth(40)
  ) dut (
    .clk_i(clk_i), .rst_ni(rst_ni), .test_en_i(1'b1), .scan_rst_ni(1'b1),
    .ram_cfg_icache_tag_i('0), .ram_cfg_icache_tag_o(),
    .ram_cfg_icache_data_i('0), .ram_cfg_icache_data_o(),
    .cheriot_enable_i(IbexMuBiOff), .hart_id_i(32'b0), .boot_addr_i(32'h80000000),
    .trvk_heap_base_addr_i(32'b0),
    .instr_req_o(instr_req_o), .instr_gnt_i(instr_req_o),
    .instr_rvalid_i(instr_rvalid_i), .instr_addr_o(instr_addr_o),
    .instr_rdata_i(instr_rdata_i), .instr_rdata_intg_i(7'b0), .instr_err_i(1'b0),
    .data_req_o(data_req_o), .data_gnt_i(1'b0), .data_rvalid_i(1'b0),
    .data_we_o(), .data_be_o(), .data_addr_o(), .data_wdata_o(),
    .data_wdata_intg_o(), .data_tag_o(), .data_rdata_i(32'b0),
    .data_rdata_intg_i(7'b0), .data_tag_i(1'b0), .data_err_i(1'b0),
    .trvk_revbm_req_o(), .trvk_revbm_gnt_i(1'b0), .trvk_revbm_rvalid_i(1'b0),
    .trvk_revbm_addr_o(), .trvk_revbm_rdata_i(32'b0), .trvk_revbm_rdata_intg_i(7'b0),
    .trvk_revbm_err_i(1'b0),
    .irq_software_i(irq_software_i), .irq_timer_i(irq_timer_i),
    .irq_external_i(irq_external_i), .irq_fast_i(irq_fast_i),
    .irq_nm_i(irq_nm_i), .debug_req_i(debug_req_i),
    .scramble_key_valid_i(1'b0), .scramble_key_i('0), .scramble_nonce_i('0),
    .scramble_req_o(), .crash_dump_o(), .double_fault_seen_o(),
    .rvfi_valid(rvfi_valid), .rvfi_order(rvfi_order), .rvfi_insn(rvfi_insn),
    .rvfi_trap(rvfi_trap), .rvfi_halt(rvfi_halt), .rvfi_intr(rvfi_intr),
    .rvfi_mode(rvfi_mode), .rvfi_ixl(rvfi_ixl),
    .rvfi_rs1_addr(rvfi_rs1_addr), .rvfi_rs2_addr(rvfi_rs2_addr), .rvfi_rs3_addr(),
    .rvfi_rs1_rdata(rvfi_rs1_rdata), .rvfi_rs2_rdata(rvfi_rs2_rdata), .rvfi_rs3_rdata(),
    .rvfi_rs1_rcap(), .rvfi_rs2_rcap(), .rvfi_rd_wcap(),
    .rvfi_rd_addr(rvfi_rd_addr), .rvfi_rd_wdata(rvfi_rd_wdata),
    .rvfi_pc_rdata(rvfi_pc_rdata), .rvfi_pc_wdata(rvfi_pc_wdata),
    .rvfi_mem_addr(), .rvfi_mem_rmask(rvfi_mem_rmask), .rvfi_mem_wmask(rvfi_mem_wmask),
    .rvfi_mem_rdata(), .rvfi_mem_wdata(), .rvfi_mem_is_cap(), .rvfi_mem_rcap(), .rvfi_mem_wcap(),
    .rvfi_ext_pre_mip(rvfi_ext_pre_mip), .rvfi_ext_post_mip(rvfi_ext_post_mip),
    .rvfi_ext_nmi(rvfi_ext_nmi), .rvfi_ext_nmi_int(rvfi_ext_nmi_int),
    .rvfi_ext_debug_req(rvfi_ext_debug_req), .rvfi_ext_debug_mode(rvfi_ext_debug_mode),
    .rvfi_ext_rf_wr_suppress(rvfi_ext_rf_wr_suppress), .rvfi_ext_mcycle(),
    .rvfi_ext_mhpmcounters(), .rvfi_ext_mhpmcountersh(), .rvfi_ext_ic_scr_key_valid(),
    .rvfi_ext_irq_valid(rvfi_ext_irq_valid), .rvfi_ext_expanded_insn_valid(),
    .rvfi_ext_expanded_insn(), .rvfi_ext_expanded_insn_last(),
    .fetch_enable_i(IbexMuBiOn), .mcounteren_writable_i(IbexMuBiOff),
    .alert_minor_o(alert_minor_o), .alert_major_internal_o(alert_major_internal_o),
    .alert_major_bus_o(alert_major_bus_o), .core_sleep_o(), .lockstep_cmp_en_o(),
    .data_req_shadow_o(), .data_we_shadow_o(), .data_be_shadow_o(), .data_addr_shadow_o(),
    .data_wdata_shadow_o(), .data_wdata_intg_shadow_o(), .instr_req_shadow_o(),
    .instr_addr_shadow_o()
  );

  initial begin
    $display("NEXTPC_CONFIG BP=%0d WB=%0d BTA=%0d ZC=%0d IC=%0d",
             dut.BranchPredictor, dut.WritebackStage, dut.BranchTargetALU, dut.RV32ZC, dut.ICache);
  end
endmodule
