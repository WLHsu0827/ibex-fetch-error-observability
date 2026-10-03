# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Wei-Lun Hsu
.PHONY: nextpc-outer-driver-probe nextpc-driver-probe
ifeq ($(NEXTPC_PROBE_CHILD),1)
include Vsampler_fixture.mk
nextpc-driver-probe:
	@printf '%s\n' 'CXX=$(CXX)' 'CC=$(CC)' 'LINK=$(LINK)' 'AR=$(AR)' 'PYTHON3=$(PYTHON3)' 'PERL=$(PERL)' 'OBJCACHE=$(OBJCACHE)' 'MAKEFLAGS=$(MAKEFLAGS)'
else
nextpc-outer-driver-probe:
	+@$(MAKE) --no-print-directory -f $(lastword $(MAKEFILE_LIST)) NEXTPC_PROBE_CHILD=1 nextpc-driver-probe
endif
