// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
//
// Controlled public synthetic stimulus. Values are labels, not ISA execution.
module trace_monitor_fixture;
  logic clk = 1'b0;
  logic rst_n = 1'b1;
  logic active = 1'b0;
  logic capture = 1'b0;
  logic retire = 1'b0;
  string scenario;

  trace_phase_observer dut (
    .clk_i(clk), .rst_ni(rst_n),
    .instr_first_cycle_i(active), .instr_executing_i(active),
    .branch_in_dec_i(active), .pc_id_i(32'h00000100),
    .insn_id_i(32'h00000013), .branch_decision_i(1'b1),
    .predicted_taken_i(1'b0), .correction_i(1'b0),
    .correction_addr_i(32'h0), .redirect_i(1'b0),
    .next_label_i(32'h00000104), .target_label_i(32'h00000104),
    .capture_i(capture), .retire_i(retire), .order_i(64'd1),
    .retire_label_i(32'h00000100), .retire_word_i(32'h00000013),
    .retire_next_label_i(32'h00000104), .trap_i(1'b0),
    .interrupt_i(1'b0), .halt_i(1'b0),
    .operand_a_index_i(5'd0), .operand_a_value_i(32'h0),
    .operand_b_index_i(5'd0), .operand_b_value_i(32'h0),
    .control_software_i(1'b0), .control_timer_i(1'b0),
    .control_external_i(1'b0), .control_fast_i(15'd0),
    .control_nm_i(1'b0), .debug_request_i(1'b0),
    .debug_mode_i(1'b0), .new_control_i(1'b0)
  );

  task automatic tick;
    #1 clk = 1'b1;
    #1 clk = 1'b0;
    #1;
  endtask

  task automatic capture_then_retire;
    active = 1'b1;
    capture = 1'b1;
    retire = 1'b0;
    #1 clk = 1'b1;
    #1 retire = 1'b1;
    clk = 1'b0;
    #1;
    active = 1'b0;
    capture = 1'b0;
    tick();
    retire = 1'b0;
  endtask

  initial begin
    if (!$value$plusargs("CASE=%s", scenario)) $fatal(1, "MISSING_CASE");
    case (scenario)
      "delayed": begin
        active = 1'b1; capture = 1'b1; retire = 1'b1;
        tick(); tick();
        active = 1'b0; capture = 1'b0; retire = 1'b0;
        rst_n = 1'b0;
        tick(); tick();
        rst_n = 1'b1;
        capture_then_retire();
      end
      "initial_low": begin
        rst_n = 1'b0;
        tick(); tick();
        rst_n = 1'b1;
        capture_then_retire();
      end
      "held_reset": begin
        rst_n = 1'b0;
        active = 1'b1; capture = 1'b1; retire = 1'b1;
        tick(); tick(); tick(); tick();
        active = 1'b0; capture = 1'b0; retire = 1'b0;
        rst_n = 1'b1;
        capture_then_retire();
      end
      "async_between_edges": begin
        tick();
        rst_n = 1'b0;
        #1 rst_n = 1'b1;
        #1;
        capture_then_retire();
      end
      "no_reset": begin
        active = 1'b1; capture = 1'b1; retire = 1'b1;
        tick(); tick(); tick();
      end
      "reset_again": begin
        rst_n = 1'b0;
        tick();
        rst_n = 1'b1;
        capture_then_retire();
        rst_n = 1'b0;
        #1;
      end
      "fatal_text_then_hang": begin
        $display("TRACE_MONITOR_RESET_AFTER_START");
        $fflush();
        forever #1;
      end
      default: $fatal(1, "UNKNOWN_CASE");
    endcase
    $finish;
  end
endmodule
