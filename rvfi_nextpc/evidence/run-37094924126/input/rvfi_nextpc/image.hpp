// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Wei-Lun Hsu
#ifndef RVFI_NEXTPC_IMAGE_HPP
#define RVFI_NEXTPC_IMAGE_HPP
#include <charconv>
#include <cstdint>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

inline uint32_t decimal(const char *text) {
  const std::string input(text);
  uint32_t value = 0;
  const auto parsed = std::from_chars(input.data(), input.data() + input.size(), value);
  if (input.empty() || parsed.ec != std::errc{} || parsed.ptr != input.data() + input.size())
    throw std::runtime_error("invalid exact unsigned decimal argument");
  return value;
}

inline std::vector<unsigned char> load_image(const char *filename, uint32_t terminal, uint32_t budget) {
  if (budget == 0 || budget > 20000) throw std::runtime_error("invalid cycle limit");
  std::ifstream image(filename, std::ios::binary);
  if (!image) throw std::runtime_error("cannot open fresh program");
  image.seekg(0, std::ios::end);
  const auto length = image.tellg();
  if (length < 4 || length > 2048 || (length % 2) != 0)
    throw std::runtime_error("invalid bounded fresh image size");
  image.seekg(0);
  std::vector<unsigned char> bytes{std::istreambuf_iterator<char>(image), {}};
  if (image.bad() || static_cast<std::streamoff>(bytes.size()) != length)
    throw std::runtime_error("fresh image read failed");
  if (uint64_t(terminal) + 4 != uint64_t(0x80000080) + bytes.size())
    throw std::runtime_error("terminal/image boundary mismatch");
  const auto end = bytes.end();
  if (*(end - 4) != 0x6f || *(end - 3) != 0 || *(end - 2) != 0 || *(end - 1) != 0)
    throw std::runtime_error("terminal must be jal x0,0");
  return bytes;
}
#endif
