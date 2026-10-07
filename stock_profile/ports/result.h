/* SPDX-License-Identifier: Apache-2.0 */
#ifndef STOCK_PROFILE_RESULT_H
#define STOCK_PROFILE_RESULT_H
#include "stock_profile_config.h"

int putchar(int);

static void stock_profile_text(const char *text) {
  while (*text) {
    putchar(*text++);
  }
}

static void stock_profile_result(const char *workload, int verified) {
  stock_profile_text("STOCK_PROFILE_V1 workload=");
  stock_profile_text(workload);
  stock_profile_text(" config=" STOCK_PROFILE_CONFIG_SHA
                     " mode=selfcheck_only verify=");
  stock_profile_text(verified == 1 ? "1" : verified == 0 ? "0" :
                     verified == -1 ? "-1" : "INVALID_VERIFIER_RETURN");
  stock_profile_text(" complete=1\n");
}
#endif
