// Copyright 2026 Wei-Lun Hsu.
// Licensed under the Apache License, Version 2.0, see LICENSE for details.
// SPDX-License-Identifier: Apache-2.0

`timescale 1ns/1ps

module tb_fetch_fault;
  import ibex_pkg::*;

  localparam logic [31:0] Target = 32'h0000_1000;
  localparam logic [31:0] Nop = 32'h0000_0013;
  localparam logic [IC_INDEX_W-1:0] TargetIndex = Target[IC_INDEX_HI:IC_LINE_W];

  logic clk = 1'b0;
  always #5 clk = ~clk;

  logic rst_n = 1'b0;
  logic req = 1'b0;
  logic branch = 1'b0;
  logic [31:0] branch_addr = Target;
  logic ready = 1'b0;
  logic valid;
  logic [31:0] rdata, addr;
  logic err, err_plus2;
  logic instr_req, instr_gnt, instr_rvalid, instr_err;
  logic [31:0] instr_addr, instr_rdata;
  logic [31:0] response_addr;
  logic [IC_NUM_WAYS-1:0] tag_req, data_req;
  logic tag_write, data_write;
  logic [IC_INDEX_W-1:0] tag_addr, data_addr;
  logic [IC_TAG_SIZE-1:0] tag_wdata, tag_rdata [IC_NUM_WAYS];
  logic [IC_LINE_SIZE-1:0] data_wdata, data_rdata [IC_NUM_WAYS];
  logic busy;
  logic [IC_TAG_SIZE-1:0] tag_mem [IC_NUM_WAYS][IC_NUM_LINES];
  logic [IC_LINE_SIZE-1:0] data_mem [IC_NUM_WAYS][IC_NUM_LINES];

  string scenario;
  bit replay = 1'b0;
  bit inject = 1'b0;
  bit injected = 1'b0;
  bit warmed = 1'b0;
  int unsigned cycle = 0;
  int unsigned warm_handoffs = 0;
  int unsigned target_requests = 0;
  int unsigned target_responses = 0;
  int unsigned fault_injections = 0;
  int unsigned bus_errors = 0;
  int unsigned if_handoffs = 0;
  int unsigned if_errors = 0;
  int unsigned if_good_nops = 0;
  int unsigned cache_hits = 0;
  logic [31:0] lookup_addr_q;

  assign instr_gnt = instr_req;

  ibex_icache #(
    .ICacheECC (1'b0)
  ) dut (
    .clk_i              (clk),
    .rst_ni             (rst_n),
    .req_i              (req),
    .branch_i           (branch),
    .addr_i             (branch_addr),
    .ready_i            (ready),
    .valid_o            (valid),
    .rdata_o            (rdata),
    .addr_o             (addr),
    .err_o              (err),
    .err_plus2_o        (err_plus2),
    .instr_req_o        (instr_req),
    .instr_gnt_i        (instr_gnt),
    .instr_addr_o       (instr_addr),
    .instr_rdata_i      (instr_rdata),
    .instr_err_i        (instr_err),
    .instr_rvalid_i     (instr_rvalid),
    .ic_tag_req_o       (tag_req),
    .ic_tag_write_o     (tag_write),
    .ic_tag_addr_o      (tag_addr),
    .ic_tag_wdata_o     (tag_wdata),
    .ic_tag_rdata_i     (tag_rdata),
    .ic_data_req_o      (data_req),
    .ic_data_write_o    (data_write),
    .ic_data_addr_o     (data_addr),
    .ic_data_wdata_o    (data_wdata),
    .ic_data_rdata_i    (data_rdata),
    .ic_scr_key_valid_i (1'b1),
    .ic_scr_key_req_o   (),
    .icache_enable_i    (1'b1),
    .icache_inval_i     (1'b0),
    .busy_o             (busy),
    .ecc_error_o        ()
  );

  // Match the one-cycle synchronous read timing of prim_ram_1p.
  always @(posedge clk) begin
    if (dut.lookup_actual_ic0) lookup_addr_q <= dut.lookup_addr_ic0;
    for (int way = 0; way < IC_NUM_WAYS; way++) begin
      if (tag_req[way]) begin
        if (tag_write) tag_mem[way][tag_addr] <= tag_wdata;
        else           tag_rdata[way] <= tag_mem[way][tag_addr];
      end
      if (data_req[way]) begin
        if (data_write) data_mem[way][data_addr] <= data_wdata;
        else            data_rdata[way] <= data_mem[way][data_addr];
      end
    end
    if (rst_n && tag_write && tag_addr == TargetIndex && tag_wdata[IC_TAG_SIZE-1]) begin
      warmed <= 1'b1;
    end
  end

  // Every request is granted immediately; the response is valid the following cycle.
  always @(posedge clk) begin
    instr_rvalid <= rst_n && instr_req;
    if (rst_n && instr_req) begin
      instr_rdata <= Nop;
      response_addr <= instr_addr;
      instr_err <= replay && inject && !injected && instr_addr == Target;
      if (replay && inject && !injected && instr_addr == Target) injected <= 1'b1;
    end else begin
      instr_err <= 1'b0;
    end

    if (rst_n) begin
      cycle <= cycle + 1;
      if (!replay && valid && ready && addr == Target) warm_handoffs <= warm_handoffs + 1;
      if (replay) begin
        if (instr_req && instr_gnt && instr_addr == Target) begin
          target_requests <= target_requests + 1;
          $display("PILOT_EVENT:{\"cycle\":%0d,\"kind\":\"request\",\"addr\":\"0x%08x\"}",
                   cycle, instr_addr);
          if (inject && !injected) fault_injections <= fault_injections + 1;
        end
        if (instr_rvalid && response_addr == Target) begin
          target_responses <= target_responses + 1;
          if (instr_err) bus_errors <= bus_errors + 1;
          $display("PILOT_EVENT:{\"cycle\":%0d,\"kind\":\"bus_response\",\"addr\":\"0x%08x\",\"err\":%0d}",
                   cycle, response_addr, instr_err);
        end
        if (dut.lookup_valid_ic1 && dut.tag_hit_ic1 &&
            lookup_addr_q[31:IC_LINE_W] == Target[31:IC_LINE_W]) begin
          cache_hits <= cache_hits + 1;
          $display("PILOT_EVENT:{\"cycle\":%0d,\"kind\":\"cache_hit\",\"line\":\"0x%08x\"}",
                   cycle, {lookup_addr_q[31:IC_LINE_W], {IC_LINE_W{1'b0}}});
        end
        if (valid && ready && addr == Target) begin
          if_handoffs <= if_handoffs + 1;
          if (err) if_errors <= if_errors + 1;
          if (!err && rdata == Nop) if_good_nops <= if_good_nops + 1;
          $display("PILOT_EVENT:{\"cycle\":%0d,\"kind\":\"if_handoff\",\"addr\":\"0x%08x\",\"err\":%0d,\"err_plus2\":%0d,\"rdata\":\"0x%08x\"}",
                   cycle, addr, err, err_plus2, rdata);
        end
      end
    end
  end

  initial begin
    if (!$value$plusargs("scenario=%s", scenario)) $fatal(1, "Specify +scenario");
    if (scenario != "speculative_hit" && scenario != "demand_miss" &&
        scenario != "hit_control") $fatal(1, "Unknown scenario: %s", scenario);
    if ($test$plusargs("trace")) begin
      $dumpfile("trace.vcd");
      $dumpvars(0, tb_fetch_fault);
    end

    repeat (3) @(negedge clk);
    rst_n = 1'b1;
    for (int i = 0; i < 300 && busy; i++) @(negedge clk);
    if (busy) $fatal(1, "Cache invalidation did not finish");

    if (scenario != "demand_miss") begin
      @(negedge clk);
      req = 1'b1;
      branch = 1'b1;
      ready = 1'b1;
      @(negedge clk);
      branch = 1'b0;
      for (int i = 0; i < 30 && warm_handoffs == 0; i++) @(negedge clk);
      if (warm_handoffs == 0) $fatal(1, "Warm-up instruction not handed to IF");
      ready = 1'b0;
      req = 1'b0;
      for (int i = 0; i < 40 && (!warmed || busy || instr_rvalid); i++) @(negedge clk);
      if (!warmed || busy || instr_rvalid) $fatal(1, "Target line not cached and idle");
      repeat (4) @(negedge clk);
    end

    replay = 1'b1;
    inject = scenario != "hit_control";
    req = 1'b1;
    branch = 1'b1;
    ready = 1'b0;
    @(negedge clk);
    branch = 1'b0;
    for (int i = 0; i < 30 && target_responses == 0; i++) @(negedge clk);
    if (target_responses == 0) $fatal(1, "No bus response at target");
    ready = 1'b1;
    for (int i = 0; i < 30 && if_handoffs == 0; i++) @(negedge clk);
    if (if_handoffs == 0) $fatal(1, "No replay handoff at target");
    ready = 1'b0;
    req = 1'b0;
    repeat (8) @(negedge clk);

    $display("PILOT_RESULT:{\"scenario\":\"%s\",\"target_requests\":%0d,\"target_responses\":%0d,\"fault_injections\":%0d,\"bus_errors\":%0d,\"if_handoffs\":%0d,\"if_errors\":%0d,\"if_good_nops\":%0d,\"cache_hits\":%0d,\"cache_warmed\":%0d}",
             scenario, target_requests, target_responses, fault_injections, bus_errors,
             if_handoffs, if_errors, if_good_nops, cache_hits, warmed);
    $finish;
  end
endmodule
