// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
#ifndef RVFI_NEXTPC_SAMPLE_HPP
#define RVFI_NEXTPC_SAMPLE_HPP
#include <cstdint>
#include <ostream>

template <typename Model>
void sample(std::ostream &out, const Model &m, unsigned cycle) {
  out << "Q\t" << cycle << '\t' << unsigned(m.rst_ni)
      << '\t' << unsigned(m.irq_software_i) << '\t' << unsigned(m.irq_timer_i)
      << '\t' << unsigned(m.irq_external_i) << '\t' << unsigned(m.irq_fast_i)
      << '\t' << unsigned(m.irq_nm_i) << '\t' << unsigned(m.debug_req_i)
      << '\t' << unsigned(m.rvfi_ext_debug_mode) << '\n';
  if (m.rvfi_valid) {
    out << "R\t" << cycle << '\t' << uint64_t(m.rvfi_order)
        << '\t' << uint32_t(m.rvfi_pc_rdata) << '\t' << uint32_t(m.rvfi_insn)
        << '\t' << uint32_t(m.rvfi_pc_wdata) << '\t' << unsigned(m.rvfi_rs1_addr)
        << '\t' << unsigned(m.rvfi_rs2_addr) << '\t' << uint32_t(m.rvfi_rs1_rdata)
        << '\t' << uint32_t(m.rvfi_rs2_rdata) << '\t' << unsigned(m.rvfi_rd_addr)
        << '\t' << uint32_t(m.rvfi_rd_wdata) << '\t' << unsigned(m.rvfi_trap)
        << '\t' << unsigned(m.rvfi_halt) << '\t' << unsigned(m.rvfi_intr)
        << '\t' << unsigned(m.rvfi_mode) << '\t' << unsigned(m.rvfi_ixl)
        << '\t' << unsigned(m.rvfi_mem_rmask) << '\t' << unsigned(m.rvfi_mem_wmask)
        << '\t' << uint32_t(m.rvfi_ext_pre_mip) << '\t' << uint32_t(m.rvfi_ext_post_mip)
        << '\t' << unsigned(m.rvfi_ext_nmi) << '\t' << unsigned(m.rvfi_ext_nmi_int)
        << '\t' << unsigned(m.rvfi_ext_debug_req) << '\t' << unsigned(m.rvfi_ext_debug_mode)
        << '\t' << unsigned(m.rvfi_ext_irq_valid) << '\t' << unsigned(m.rvfi_ext_rf_wr_suppress)
        << '\n';
  }
  out.flush();
}
#endif
