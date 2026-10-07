"""Only fake stdlib processes: no workload source imports, compilers or simulators."""

import os
import pathlib
import signal
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from config import CONFIG_SHA
from result import VALIDATED

case = sys.argv[1]
marker = (f"STOCK_PROFILE_V1 workload=aha-mont64 config={CONFIG_SHA} "
          "mode=selfcheck_only verify=1 complete=1\n")
coremark = (
    "CoreMark Size    : 666\nIterations       : 10\nMemory location  : STACK\n"
    "seedcrc          : 0xe9f5\n[0]crclist       : 0xe714\n"
    "[0]crcmatrix     : 0x1fd7\n[0]crcstate      : 0x8e3a\n"
    "[0]crcfinal      : 0x1234\n" + VALIDATED + "\n"
    + marker.replace("aha-mont64", "coremark").replace("verify=1", "verify=-1")
)
log = pathlib.Path("benchmark.log")
if case.startswith("coremark"):
    text = coremark
    if case == "coremark_bad_crc":
        text = text.replace("0xe714", "0x0000")
    elif case == "coremark_unknown":
        text = text.replace(VALIDATED, "Cannot validate operation for these seed values")
    elif case == "coremark_missing":
        text = text.replace("[0]crcstate      : 0x8e3a\n", "")
    elif case == "coremark_duplicate":
        text += "[0]crclist       : 0xe714\n"
    elif case == "coremark_wrong_input":
        text = text.replace("Iterations       : 10", "Iterations       : 11")
    elif case == "coremark_error":
        text += "ERROR! Please define ee_u32 to a 32b unsigned type!\n"
    elif case == "coremark_forged_verify":
        text = text.replace("verify=-1", "verify=1")
    log.write_bytes(text.encode())
elif case == "missing":
    log.write_bytes(b"normal halt without selfcheck\n")
elif case == "duplicate":
    log.write_bytes((marker * 2).encode())
elif case == "truncated":
    log.write_bytes(marker[:-1].encode())
elif case == "malformed":
    log.write_bytes(marker.replace("complete=1", "complete=true").encode())
elif case == "configwrong":
    log.write_bytes(marker.replace(CONFIG_SHA, "0" * 64).encode())
elif case == "workloadwrong":
    log.write_bytes(marker.replace("aha-mont64", "dummy").encode())
elif case == "selfcheck_minus1":
    log.write_bytes(marker.replace("verify=1", "verify=-1").encode())
elif case == "selfcheck_fail":
    log.write_bytes(marker.replace("verify=1", "verify=0").encode())
elif case == "selfcheck_invalid":
    log.write_bytes(marker.replace("verify=1", "verify=2").encode())
elif case == "bad_utf8":
    log.write_bytes(marker.encode() + b"\xff\n")
elif case == "flood_program":
    log.write_bytes(b"x" * (256 * 1024))
else:
    log.write_bytes(marker.encode())
print("synthetic stdout", flush=True)
print("synthetic stderr", file=sys.stderr, flush=True)
if case in ("hang", "marker_hang"):
    time.sleep(30)
elif case == "wrong_channel":
    print(marker, end="", flush=True)
elif case == "cycle_timeout":
    print("Simulation timeout of 50000000 cycles reached, shutting down simulation.")
elif case == "trap":
    print("EXCEPTION!!!")
elif case == "nonzero":
    sys.exit(7)
elif case == "signal":
    os.kill(os.getpid(), signal.SIGTERM)
elif case == "resource_cpu":
    while True:
        pass
elif case == "resource_file":
    signal.signal(signal.SIGXFSZ, signal.SIG_DFL)
    with pathlib.Path("oversize.bin").open("wb") as output:
        output.write(b"x" * 262144)
elif case == "resource_address":
    try:
        allocation = bytearray(1024**3)
    except MemoryError:
        os.write(2, b"STOCK_RESOURCE_LIMIT address_space\n")
        sys.exit(78)
    raise SystemExit("expected RLIMIT_AS was not enforced")
elif case == "flood_stdout":
    os.write(1, b"x" * 262144)
elif case == "flood_stderr":
    os.write(2, b"x" * 262144)
elif case == "orphan_pipe" and os.name == "posix":
    if os.fork() == 0:
        time.sleep(30)
