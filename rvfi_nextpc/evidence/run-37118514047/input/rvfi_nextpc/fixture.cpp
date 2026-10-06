// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
#include "Vsampler_fixture.h"
#include "verilated.h"
#include "sample.hpp"
#include <fstream>
#include <iostream>
#include <string>
#include <chrono>
#include <thread>
#include <map>

int main(int argc, char **argv) {
  if (argc != 4) return 2;
  const std::string scenario = argv[1];
  const std::map<std::string, unsigned> modes = {
    {"good", 0}, {"no_reset", 0}, {"reset_again", 0}, {"hang", 0},
    {"extra_read", 1}, {"memory_opcode", 2}, {"write_mask", 3}, {"trap", 4},
    {"halt", 5}, {"intr", 6}, {"privilege", 7}, {"rf_suppress", 8},
    {"post_request", 9}, {"write_control", 10}, {"minor_alert", 11},
    {"internal_alert", 12}, {"bus_alert", 13}, {"debug_mode", 14},
    {"pre_request", 0}, {"grant", 0}, {"response", 0}, {"data_error", 0},
    {"irq", 0}, {"debug_req", 0},
  };
  if (!modes.count(scenario)) return 2;
  VerilatedContext context;
  context.commandArgs(argc, argv);
  Vsampler_fixture model{&context};
  std::ofstream log(argv[2], std::ios::binary);
  if (!log) return 2;
  log << "S\t2\tcpp\tnonmemory-nextpc-v2\n";
  log.flush();
  if (scenario == "hang") {
    std::cout << "NEXTPC_CONTROL" << std::endl;
    std::this_thread::sleep_for(std::chrono::seconds(30));
    return 2;
  }
  model.clk_i = 0;
  model.rst_ni = 1;
  model.irq_software_i = model.irq_timer_i = model.irq_external_i = 0;
  model.irq_fast_i = model.irq_nm_i = model.debug_req_i = 0;
  model.scenario_i = modes.at(scenario);
  model.inject_req_i = model.data_gnt_i = model.data_rvalid_i = model.data_err_i = 0;
  model.eval();
  for (unsigned cycle = 0; cycle < 20; ++cycle) {
    model.rst_ni = scenario == "no_reset" || cycle >= 5;
    if (scenario == "reset_again" && cycle == 14) model.rst_ni = 0;
    model.inject_req_i = scenario == "pre_request" && cycle == 10;
    model.data_gnt_i = scenario == "grant" && cycle == 10;
    model.data_rvalid_i = scenario == "response" && cycle == 10;
    model.data_err_i = scenario == "data_error" && cycle == 10;
    model.irq_fast_i = scenario == "irq" && cycle == 10 ? 1 : 0;
    model.debug_req_i = scenario == "debug_req" && cycle == 10;
    model.eval();
    controls(log, model, cycle, 'P');
    model.clk_i = 1;
    context.timeInc(1);
    model.eval();
    sample(log, model, cycle);
    model.clk_i = 0;
    context.timeInc(1);
    model.eval();
  }
  model.final();
  std::cout << "NEXTPC_FIXTURE_COMPLETE" << std::endl;
  return 0;
}
