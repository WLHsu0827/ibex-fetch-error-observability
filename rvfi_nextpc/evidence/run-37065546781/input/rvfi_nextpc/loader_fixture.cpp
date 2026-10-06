// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
#include "image.hpp"
#include <iostream>

int main(int argc, char **argv) {
  try {
    if (argc != 4) throw std::runtime_error("arguments: image terminal budget");
    const auto bytes = load_image(argv[1], decimal(argv[2]), decimal(argv[3]));
    std::cout << "NEXTPC_LOADER_PASS bytes=" << bytes.size() << std::endl;
    return 0;
  } catch (const std::exception &error) {
    std::cerr << "NEXTPC_LOADER_REJECT " << error.what() << std::endl;
    return 2;
  }
}
