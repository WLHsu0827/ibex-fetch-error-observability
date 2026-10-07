/* SPDX-License-Identifier: GPL-3.0-or-later
 * External Embench orchestration adapter; official src/input/verifier unchanged.
 */
#include "support.h"
#include "result.h"

#ifndef STOCK_PROFILE_WORKLOAD
#error "The sealed Embench workload name is required"
#endif
#if GLOBAL_SCALE_FACTOR != 1 || WARMUP_HEAT != 1
#error "Preparation contract fixes gsf=1 and warmup_heat=1"
#endif

int main(void) {
  volatile int output;
  int verified;
  initialise_board();
  initialise_benchmark();
  warm_caches(WARMUP_HEAT);
  start_trigger();
  output = benchmark();
  stop_trigger();
  verified = verify_benchmark(output);
  stock_profile_result(STOCK_PROFILE_WORKLOAD, verified);
  return verified == 1 ? 0 : 1;
}
