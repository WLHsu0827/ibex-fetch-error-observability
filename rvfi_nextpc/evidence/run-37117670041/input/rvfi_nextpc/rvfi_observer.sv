// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
module rvfi_observer (
  input logic clk_i, rst_ni,
  input logic irq_software_i, irq_timer_i, irq_external_i,
  input logic [14:0] irq_fast_i,
  input logic irq_nm_i, debug_req_i,
  input logic data_req_o, data_gnt_i, data_rvalid_i, data_we_o, data_err_i,
  input logic [3:0] data_be_o,
  input logic [31:0] data_addr_o, data_wdata_o,
  input logic alert_minor_o, alert_major_internal_o, alert_major_bus_o,
  input logic rvfi_valid,
  input logic [63:0] rvfi_order,
  input logic [31:0] rvfi_pc_rdata, rvfi_insn, rvfi_pc_wdata,
  input logic [4:0] rvfi_rs1_addr, rvfi_rs2_addr, rvfi_rd_addr,
  input logic [31:0] rvfi_rs1_rdata, rvfi_rs2_rdata, rvfi_rd_wdata,
  input logic rvfi_trap, rvfi_halt, rvfi_intr,
  input logic [1:0] rvfi_mode, rvfi_ixl,
  input logic [3:0] rvfi_mem_rmask, rvfi_mem_wmask,
  input logic [31:0] rvfi_mem_addr, rvfi_mem_rdata, rvfi_mem_wdata,
  input logic [31:0] rvfi_ext_pre_mip, rvfi_ext_post_mip,
  input logic rvfi_ext_nmi, rvfi_ext_nmi_int, rvfi_ext_debug_req,
  input logic rvfi_ext_debug_mode, rvfi_ext_irq_valid, rvfi_ext_rf_wr_suppress
);
  integer fd;
  integer cycle = 0;
  integer pre_cycle = 0;
  bit reset_seen = 0;
  bit started = 0;
  string filename;

  initial begin
    if (!$value$plusargs("sv_log=%s", filename)) $fatal(1, "NEXTPC_MISSING_LOG");
    fd = $fopen(filename, "w");
    if (fd == 0) $fatal(1, "NEXTPC_OPEN_LOG");
    $fwrite(fd, "S\t2\tsv\tnonmemory-nextpc-v2\n");
  end

  task automatic controls(input string phase, input integer index);
    $fwrite(fd, "%s\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\n",
            phase, index, rst_ni, irq_software_i, irq_timer_i, irq_external_i,
            irq_fast_i, irq_nm_i, debug_req_i, rvfi_ext_debug_mode,
            data_req_o, data_gnt_i, data_rvalid_i, data_we_o, data_be_o,
            data_addr_o, data_wdata_o, data_err_i,
            alert_minor_o, alert_major_internal_o, alert_major_bus_o);
    $fflush(fd);
    if (irq_software_i || irq_timer_i || irq_external_i || (|irq_fast_i) ||
        irq_nm_i || debug_req_i || rvfi_ext_debug_mode ||
        data_req_o || data_gnt_i || data_rvalid_i || data_we_o || data_err_i ||
        alert_minor_o || alert_major_internal_o || alert_major_bus_o)
      $fatal(1, "NEXTPC_CONTROL");
  endtask

  // Inputs/outputs settled before the rising edge: sample before sequential NBA updates.
  always @(posedge clk_i) begin
    controls("P", pre_cycle);
    pre_cycle <= pre_cycle + 1;
  end

  // Falling edge samples stable registered output ports, not the rising-edge NBA input.
  always @(negedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      if (started) begin
        $fflush(fd);
        $fatal(1, "NEXTPC_RESET_AFTER_START");
      end
      reset_seen <= 1;
    end else if (reset_seen) begin
      started <= 1;
    end
    controls("Q", cycle);
    if (rvfi_valid) begin
      if (!started) begin
        $fflush(fd);
        $fatal(1, "NEXTPC_MISSING_RESET");
      end
      $fwrite(fd,
        "R\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\t%0d\n",
        cycle, rvfi_order, rvfi_pc_rdata, rvfi_insn, rvfi_pc_wdata,
        rvfi_rs1_addr, rvfi_rs2_addr, rvfi_rs1_rdata, rvfi_rs2_rdata,
        rvfi_rd_addr, rvfi_rd_wdata, rvfi_trap, rvfi_halt, rvfi_intr,
        rvfi_mode, rvfi_ixl, rvfi_mem_rmask, rvfi_mem_wmask,
        rvfi_ext_pre_mip, rvfi_ext_post_mip, rvfi_ext_nmi, rvfi_ext_nmi_int,
        rvfi_ext_debug_req, rvfi_ext_debug_mode, rvfi_ext_irq_valid, rvfi_ext_rf_wr_suppress,
        rvfi_mem_addr, rvfi_mem_rdata, rvfi_mem_wdata);
    end
    $fflush(fd);
    cycle <= cycle + 1;
  end

  final begin
    $fflush(fd);
    $fclose(fd);
  end
endmodule

bind `OBSERVER_TARGET rvfi_observer independent_sv (
  .clk_i(clk_i), .rst_ni(rst_ni),
  .irq_software_i(irq_software_i), .irq_timer_i(irq_timer_i),
  .irq_external_i(irq_external_i), .irq_fast_i(irq_fast_i),
  .irq_nm_i(irq_nm_i), .debug_req_i(debug_req_i),
  .data_req_o(data_req_o), .data_gnt_i(data_gnt_i), .data_rvalid_i(data_rvalid_i),
  .data_we_o(data_we_o), .data_be_o(data_be_o), .data_addr_o(data_addr_o),
  .data_wdata_o(data_wdata_o), .data_err_i(data_err_i),
  .alert_minor_o(alert_minor_o), .alert_major_internal_o(alert_major_internal_o),
  .alert_major_bus_o(alert_major_bus_o),
  .rvfi_valid(rvfi_valid), .rvfi_order(rvfi_order),
  .rvfi_pc_rdata(rvfi_pc_rdata), .rvfi_insn(rvfi_insn), .rvfi_pc_wdata(rvfi_pc_wdata),
  .rvfi_rs1_addr(rvfi_rs1_addr), .rvfi_rs2_addr(rvfi_rs2_addr),
  .rvfi_rd_addr(rvfi_rd_addr), .rvfi_rs1_rdata(rvfi_rs1_rdata),
  .rvfi_rs2_rdata(rvfi_rs2_rdata), .rvfi_rd_wdata(rvfi_rd_wdata),
  .rvfi_trap(rvfi_trap), .rvfi_halt(rvfi_halt), .rvfi_intr(rvfi_intr),
  .rvfi_mode(rvfi_mode), .rvfi_ixl(rvfi_ixl),
  .rvfi_mem_rmask(rvfi_mem_rmask), .rvfi_mem_wmask(rvfi_mem_wmask),
  .rvfi_mem_addr(rvfi_mem_addr), .rvfi_mem_rdata(rvfi_mem_rdata), .rvfi_mem_wdata(rvfi_mem_wdata),
  .rvfi_ext_pre_mip(rvfi_ext_pre_mip), .rvfi_ext_post_mip(rvfi_ext_post_mip),
  .rvfi_ext_nmi(rvfi_ext_nmi), .rvfi_ext_nmi_int(rvfi_ext_nmi_int),
  .rvfi_ext_debug_req(rvfi_ext_debug_req), .rvfi_ext_debug_mode(rvfi_ext_debug_mode),
  .rvfi_ext_irq_valid(rvfi_ext_irq_valid), .rvfi_ext_rf_wr_suppress(rvfi_ext_rf_wr_suppress)
);
