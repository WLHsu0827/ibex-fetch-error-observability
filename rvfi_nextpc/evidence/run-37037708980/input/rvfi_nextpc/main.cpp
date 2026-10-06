// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
#include "Vnextpc_top.h"
#include "verilated.h"
#include "sample.hpp"
#include <fstream>
#include <iostream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

int main(int argc, char **argv) {
  try {
    if (argc != 6) throw std::runtime_error("arguments: image cpp-log terminal budget +sv_log=...");
    VerilatedContext context;
    context.commandArgs(argc, argv);
    Vnextpc_top model{&context};
    std::ifstream image(argv[1], std::ios::binary);
    if (!image) throw std::runtime_error("cannot open fresh program");
    std::vector<unsigned char> bytes{std::istreambuf_iterator<char>(image), {}};
    if (bytes.empty() || bytes.size() > 2048) throw std::runtime_error("invalid fresh image size");
    std::ofstream log(argv[2], std::ios::binary);
    if (!log) throw std::runtime_error("cannot open C++ stream");
    const auto terminal = std::stoul(argv[3], nullptr, 0);
    const auto budget = std::stoul(argv[4], nullptr, 0);
    if (budget > 20000 || budget == 0) throw std::runtime_error("invalid cycle limit");
    auto rom = [&bytes](uint32_t address) {
      uint32_t result = 0;
      if (address < 0x80000000 || address >= 0x80001000 || (address & 3))
        throw std::runtime_error("instruction request outside explicit ROM");
      for (unsigned i = 0; i < 4; ++i) {
        const int64_t offset = int64_t(address) + i - 0x80000080;
        const unsigned char value = offset >= 0 && uint64_t(offset) < bytes.size()
          ? bytes.at(size_t(offset)) : (i == 0 ? 0x13 : 0);
        result |= uint32_t(value) << (8 * i);
      }
      return result;
    };
    model.clk_i = 0;
    model.rst_ni = 1;
    model.irq_software_i = model.irq_timer_i = model.irq_external_i = 0;
    model.irq_fast_i = model.irq_nm_i = model.debug_req_i = 0;
    model.instr_rvalid_i = 0;
    model.instr_rdata_i = 0;
    model.eval();
    bool pending = false;
    uint32_t response = 0;
    unsigned terminals = 0;
    for (unsigned cycle = 0; cycle < budget; ++cycle) {
      model.rst_ni = cycle < 2 || cycle >= 7;
      model.instr_rvalid_i = model.rst_ni && pending;
      model.instr_rdata_i = response;
      model.eval();
      const bool request = model.rst_ni && model.instr_req_o;
      const uint32_t address = model.instr_addr_o;
      model.clk_i = 1;
      context.timeInc(1);
      model.eval();
      sample(log, model, cycle);
      if (model.data_req_o || model.alert_minor_o || model.alert_major_internal_o || model.alert_major_bus_o)
        throw std::runtime_error("unexpected data request or DUT alert");
      if (model.rvfi_valid && model.rvfi_pc_rdata == terminal) ++terminals;
      model.clk_i = 0;
      context.timeInc(1);
      model.eval();
      if (context.gotFinish()) throw std::runtime_error("premature HDL finish");
      pending = request;
      if (request) response = rom(address);
      if (terminals == 4) {
        model.final();
        std::cout << "NEXTPC_COMPLETE terminal_records=4 cycles=" << cycle + 1 << std::endl;
        return 0;
      }
    }
    model.final();
    throw std::runtime_error("NEXTPC_CYCLE_TIMEOUT");
  } catch (const std::exception &error) {
    std::cerr << "NEXTPC_STOP " << error.what() << std::endl;
    return 2;
  }
}
