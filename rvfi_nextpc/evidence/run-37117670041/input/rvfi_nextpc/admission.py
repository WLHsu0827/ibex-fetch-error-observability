# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
"""New preregistered admission; never applied to legacy rejected streams."""

NAME = "nonmemory-nextpc-v2"
SCHEMA = 2
CONTROLS = (
    "reset", "irq_software", "irq_timer", "irq_external", "irq_fast", "irq_nm",
    "debug_req", "debug_mode", "data_req", "data_gnt", "data_rvalid", "data_we",
    "data_be", "data_addr", "data_wdata", "data_err", "alert_minor",
    "alert_major_internal", "alert_major_bus",
)
LIMITS = {name: 1 for name in CONTROLS} | {
    "irq_fast": 32767, "data_be": 15, "data_addr": 0xFFFFFFFF, "data_wdata": 0xFFFFFFFF,
}
IDLE_INFORMATION = {"data_be", "data_addr", "data_wdata"}


def control(values: list[int]) -> dict[str, int]:
    if len(values) != len(CONTROLS):
        raise ValueError("missing/malformed v2 bus/control fields")
    result = dict(zip(CONTROLS, values))
    if any(not 0 <= value <= LIMITS[name] for name, value in result.items()):
        raise ValueError("out-of-domain bus/control field")
    if any(value for name, value in result.items() if name not in IDLE_INFORMATION | {"reset"}):
        raise ValueError("observed bus request/grant/response/write/error/alert/IRQ/debug violation")
    return result
