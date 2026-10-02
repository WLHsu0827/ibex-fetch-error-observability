// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
#include "Vsampler_fixture.h"
#include "verilated.h"
#include "sample.hpp"
#include <fstream>
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 4) return 2;
  const std::string scenario = argv[1];
  if (scenario != "good" && scenario != "no_reset" && scenario != "reset_again") return 2;
  VerilatedContext context;
  context.commandArgs(argc, argv);
  Vsampler_fixture model{&context};
  std::ofstream log(argv[2], std::ios::binary);
  if (!log) return 2;
  model.clk_i = 0;
  model.rst_ni = 1;
  model.irq_software_i = model.irq_timer_i = model.irq_external_i = 0;
  model.irq_fast_i = model.irq_nm_i = model.debug_req_i = 0;
  model.eval();
  for (unsigned cycle = 0; cycle < 20; ++cycle) {
    model.rst_ni = scenario == "no_reset" || cycle >= 5;
    if (scenario == "reset_again" && cycle == 14) model.rst_ni = 0;
    model.eval();
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
