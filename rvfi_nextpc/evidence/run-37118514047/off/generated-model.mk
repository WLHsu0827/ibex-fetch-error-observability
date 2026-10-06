# Verilated -*- Makefile -*-
# DESCRIPTION: Verilator output: Makefile for building Verilated archive or executable
#
# Execute this makefile from the object directory:
#    make -f Vnextpc_top.mk

default: Vnextpc_top

### Constants...
# Perl executable (from $PERL)
PERL = /usr/bin/perl
# Path to Verilator kit (from $VERILATOR_ROOT)
VERILATOR_ROOT = /usr/share/verilator
# SystemC include directory with systemc.h (from $SYSTEMC_INCLUDE)
SYSTEMC_INCLUDE ?= 
# SystemC library directory with libsystemc.a (from $SYSTEMC_LIBDIR)
SYSTEMC_LIBDIR ?= 

### Switches...
# C++ code coverage  0/1 (from --prof-c)
VM_PROFC = 0
# SystemC output mode?  0/1 (from --sc)
VM_SC = 0
# Legacy or SystemC output mode?  0/1 (from --sc)
VM_SP_OR_SC = $(VM_SC)
# Deprecated
VM_PCLI = 1
# Deprecated: SystemC architecture to find link library path (from $SYSTEMC_ARCH)
VM_SC_TARGET_ARCH = linux

### Vars...
# Design prefix (from --prefix)
VM_PREFIX = Vnextpc_top
# Module prefix (from --prefix)
VM_MODPREFIX = Vnextpc_top
# User CFLAGS (from -CFLAGS on Verilator command line)
VM_USER_CFLAGS = \
	-Isrc/lowrisc_dv_dv_fcov_macros_0 \
	-Isrc/lowrisc_prim_util_get_scramble_params_0/rtl \
	-Isrc/lowrisc_prim_util_memload_0/rtl \
	-Isrc/lowrisc_prim_assert_0.1/rtl \
	-Isrc/lowrisc_prim_secded_0.1/rtl \
	-Isrc/lowrisc_prim_fifo_0/rtl \
	-Isrc/wlh_observations_nextpc_1.0 \
	-std=c++17 -Wall -Wextra -Werror \

# User LDLIBS (from -LDFLAGS on Verilator command line)
VM_USER_LDLIBS = \

# User .cpp files (from .cpp's on Verilator command line)
VM_USER_CLASSES = \
	main \

# User .cpp directories (from .cpp's on Verilator command line)
VM_USER_DIR = \
	src/wlh_observations_nextpc_1.0 \


### Default rules...
# Include list of all generated classes
include Vnextpc_top_classes.mk
# Include global rules
include $(VERILATOR_ROOT)/include/verilated.mk

### Executable rules... (from --exe)
VPATH += $(VM_USER_DIR)

main.o: src/wlh_observations_nextpc_1.0/main.cpp
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST) -c -o $@ $<

### Link rules... (from --exe)
Vnextpc_top: $(VK_USER_OBJS) $(VK_GLOBAL_OBJS) $(VM_PREFIX)__ALL.a $(VM_HIER_LIBS)
	$(LINK) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) $(LIBS) $(SC_LIBS) -o $@


# Verilated -*- Makefile -*-
