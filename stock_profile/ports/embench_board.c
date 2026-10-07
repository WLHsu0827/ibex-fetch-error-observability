/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "simple_system_common.h"

void initialise_board(void) {
  pcount_enable(0);
  icache_enable(0);
}

void start_trigger(void) {
  pcount_reset();
  pcount_enable(1);
}

void stop_trigger(void) {
  pcount_enable(0);
}
