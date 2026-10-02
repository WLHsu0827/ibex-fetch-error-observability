// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
//
// Minimal synthetic counterexample: logging before reset creates Q 0,1,0,1.
module unarmed_trace_counterexample;
  logic clk = 1'b0;
  logic rst_n = 1'b1;
  integer cycle = 0;
  integer log_file;
  string log_name;

  initial begin
    if (!$value$plusargs("trace_log=%s", log_name)) $fatal(1, "MISSING_LOG");
    log_file = $fopen(log_name, "w");
    if (log_file == 0) $fatal(1, "CANNOT_OPEN_LOG");
  end

  always @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      cycle <= 0;
    end else begin
      $fwrite(log_file, "Q\t%0d\t0\t0\t0\t0000\t0\t0\t0\t0\n", cycle);
      cycle <= cycle + 1;
    end
  end

  task automatic tick;
    #1 clk = 1'b1;
    #1 clk = 1'b0;
    #1;
  endtask

  initial begin
    tick(); tick();
    rst_n = 1'b0;
    tick();
    rst_n = 1'b1;
    tick(); tick();
    $finish;
  end
endmodule
