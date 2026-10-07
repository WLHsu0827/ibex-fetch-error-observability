/* SPDX-License-Identifier: Apache-2.0 */
#include "result.h"

/* Only vendored core_main.c would be renamed, never the algorithms or this file. */
int stock_profile_coremark_main(int, char **);

int main(int argc, char **argv) {
  int returned = stock_profile_coremark_main(argc, argv);
  /* Its return code cannot represent total_errors; host checks official output. */
  stock_profile_result("coremark", -1);
  return returned;
}
