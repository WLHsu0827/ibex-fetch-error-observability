# Synthetic variables only; no generated RTL or compiler recipes.
.PHONY: forbidden-build
forbidden-build:
	$(error CODE_ONLY forbids any model/CPU/program build)
CXX = unqualified-default
CC = unqualified-default
LINK = unqualified-default
AR = unqualified-default
PYTHON3 = unqualified-default
PERL = unqualified-default
OBJCACHE = unqualified-default
NUM_JOBS = unqualified-default
define FIXTURE_VALUE_END

NEXTPC_END_VALUE
endef
nextpc-driver-probe: fixture-capture
.PHONY: fixture-capture
fixture-capture:
	$(file >fixture-MAKEFLAGS,$(MAKEFLAGS)$(FIXTURE_VALUE_END))
	$(file >fixture-MFLAGS,$(MFLAGS)$(FIXTURE_VALUE_END))
override LINK := unqualified
