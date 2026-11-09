# Chi.Bio Analogue

A variant of the [Chi.Bio](https://github.com/HarrisonSteel/ChiBio) bioreactor whose LEDs are driven by analogue constant-current regulators (CCR) with a DAC set-point, instead of digital PWM.

- `docs/ANALOGUE_LED_DESIGN.md`: the redesign, I2C map, trade-offs and bring-up steps. Start here.
- `software/`: Chi.Bio control software with an analogue LED driver (`LED_DRIVE_MODE`). `analogue-led.patch` is the diff from upstream.
- `hardware/baseline-digital/`: the original digital-LED PCB package, unchanged, as supplied.
- `hardware/source-altium/`: Side board Altium project (schematic, PCB, project) from the Chi.Bio authors, plus a KiCad import of the PCB.
- `hardware/analogue-changes/`: BOM changes for the Side board.
- `tools/`: scripts that extract the netlist from the Altium schematic and convert the PCB to KiCad.
- `tests/test_led_dac.py`: checks the DAC bytes the firmware sends, using stubbed I2C.

**Status:** the real Side board schematic is in the repo and the design is matched to it. Firmware is tested only against stubs. The modified Side board has not been laid out or fabricated. See the design document for the open items marked VERIFY.

Software is derived from Chi.Bio by Harrison Steel's group. Check the upstream repository for its licence before redistributing.
