#!/usr/bin/env bash
# Run the unmodified stm32-vcu firmware in the simulator, check the output, and draw the PNG.
# Needs `sim` with STM32F1 support (a pre-release build until it ships: SIM=/path/to/sim ./run.sh) and python3 with matplotlib.
# ELF: `make get-deps && make` in the repo root, then copy stm32_vcu here as vcu.elf (committed already).
# vtor.bin = the first 512 bytes of stm32_vcu.bin (the vector table): the firmware is linked at 0x08001000 for the OpenInverter bootloader, which
# relocates VTOR; with no bootloader in the sim the table is preloaded at 0x08000000 instead.
set -euo pipefail
cd "$(dirname "$0")"
SIM=${SIM:-sim}
REC=$(mktemp -d)
trap 'rm -rf "$REC"' EXIT
$SIM run --scenario scenario.yaml --ascii --record "$REC" 2>&1 | grep -v "newer sim" | tee run.log
ok() { grep -qF "$1" run.log && echo "PASS  $2" || { echo "FAIL  $2"; exit 1; }; }
ok "(usart3 → term) Set OK" "terminal answers set"
ok "STOP - PRECHARGE" "precharge timeout reported by the errors command"
! grep -qE "HardFault|panicked" run.log && echo "PASS  no HardFault/panic"
python3 plot.py "$REC" vcu.png | tee measured.txt
