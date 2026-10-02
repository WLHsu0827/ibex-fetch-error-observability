// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
//
// Instrument-only public observer. Signal names are opaque fixture labels unless this
// module is explicitly integrated and qualified against a separate design.
module trace_phase_observer (
  input logic        clk_i,
  input logic        rst_ni,
  input logic        instr_first_cycle_i,
  input logic        instr_executing_i,
  input logic        branch_in_dec_i,
  input logic [31:0] pc_id_i,
  input logic [31:0] insn_id_i,
  input logic        branch_decision_i,
  input logic        predicted_taken_i,
  input logic        correction_i,
  input logic [31:0] correction_addr_i,
  input logic        redirect_i,
  input logic [31:0] next_label_i,
  input logic [31:0] target_label_i,
  input logic        capture_i,
  input logic        retire_i,
  input logic [63:0] order_i,
  input logic [31:0] retire_label_i,
  input logic [31:0] retire_word_i,
  input logic [31:0] retire_next_label_i,
  input logic        trap_i,
  input logic        interrupt_i,
  input logic        halt_i,
  input logic [4:0]  operand_a_index_i,
  input logic [31:0] operand_a_value_i,
  input logic [4:0]  operand_b_index_i,
  input logic [31:0] operand_b_value_i,
  input logic        control_software_i,
  input logic        control_timer_i,
  input logic        control_external_i,
  input logic [14:0] control_fast_i,
  input logic        control_nm_i,
  input logic        debug_request_i,
  input logic        debug_mode_i,
  input logic        new_control_i
);
  integer log_file;
  integer cycle = 0;
  string log_name;
  logic capture_pending = 1'b0;
  logic reset_observed = 1'b0;
  logic measurement_started = 1'b0;

  initial begin
    if (!$value$plusargs("trace_log=%s", log_name)) begin
      $fatal(1, "TRACE_MONITOR_MISSING_LOG_PATH");
    end
    log_file = $fopen(log_name, "w");
    if (log_file == 0) begin
      $fatal(1, "TRACE_MONITOR_CANNOT_OPEN_LOG");
    end
  end

  always @(posedge clk_i or negedge rst_ni) begin
    if (!rst_ni) begin
      if (measurement_started) begin
        $fatal(1, "TRACE_MONITOR_RESET_AFTER_START");
      end
      reset_observed <= 1'b1;
      cycle <= 0;
      capture_pending <= 1'b0;
    end else if (reset_observed) begin
      measurement_started <= 1'b1;
      cycle <= cycle + 1;
      capture_pending <= capture_i;
      $fwrite(log_file, "Q\t%0d\t%0d\t%0d\t%0d\t%04x\t%0d\t%0d\t%0d\t%0d\n",
              cycle, control_software_i, control_timer_i, control_external_i,
              control_fast_i, control_nm_i, debug_request_i, debug_mode_i,
              new_control_i);
      if (instr_first_cycle_i && instr_executing_i && branch_in_dec_i) begin
        $fwrite(log_file, "B\t%0d\t%08x\t%08x\t%0d\t%0d\t%0d\t%08x\t%0d\n",
                cycle, pc_id_i, insn_id_i, branch_decision_i,
                predicted_taken_i, correction_i, correction_addr_i,
                redirect_i);
      end
      if (capture_i) begin
        $fwrite(log_file, "PRE\t%0d\t%08x\t%08x\t%0d\t%08x\t%08x\t%0d\t%08x\t%0d\t%0d\n",
                cycle, pc_id_i, insn_id_i, redirect_i, next_label_i,
                target_label_i, correction_i, correction_addr_i,
                branch_decision_i, predicted_taken_i);
      end
      if (retire_i) begin
        $fwrite(log_file,
                "R\t%0d\t%0d\t%08x\t%08x\t%08x\t%0d\t%0d\t%0d\t%0d\t%08x\t%0d\t%08x\n",
                cycle, order_i, retire_label_i, retire_word_i,
                retire_next_label_i, trap_i, interrupt_i, halt_i,
                operand_a_index_i, operand_a_value_i,
                operand_b_index_i, operand_b_value_i);
      end
    end
  end

  always @(negedge clk_i or negedge rst_ni) begin
    if (rst_ni && reset_observed && capture_pending) begin
      $fwrite(log_file, "POST\t%0d\t%0d\t%08x\t%08x\t%08x\t%0d\t%0d\t%0d\n",
              cycle - 1, order_i, retire_label_i, retire_word_i,
              retire_next_label_i, retire_i, trap_i, interrupt_i);
    end
  end
endmodule
