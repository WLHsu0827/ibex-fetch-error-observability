# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
.PHONY: nextpc-outer-driver-probe nextpc-driver-probe
ifeq ($(NEXTPC_PROBE_CHILD),1)
include $(NEXTPC_PROBE_MAKEFILE)
define NEXTPC_VALUE_END

NEXTPC_END_VALUE
endef
define NEXTPC_CAPTURE
$(file >nextpc_driver_probe/$(1),$($(1))$(NEXTPC_VALUE_END))
endef
nextpc-driver-probe:
	$(foreach field,CXX CC LINK AR PYTHON3 PERL OBJCACHE NUM_JOBS MAKELEVEL MAKEFLAGS MFLAGS MAKEOVERRIDES NEXTPC_PROBE_MAKEFILE NEXTPC_PROBE_CHILD,$(call NEXTPC_CAPTURE,$(field)))
else
nextpc-outer-driver-probe:
	+@$(MAKE) --no-print-directory -f nextpc_driver_probe.mk NEXTPC_PROBE_CHILD=1 nextpc-driver-probe
endif
