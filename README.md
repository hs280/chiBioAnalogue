# Chi.Bio Analogue

A variant of the [Chi.Bio](https://github.com/HarrisonSteel/ChiBio) bioreactor whose LEDs are driven by analogue constant-current regulators (CCR) with a DAC set-point, instead of digital PWM.

- `docs/ANALOGUE_LED_DESIGN.md`: the redesign, I2C map, trade-offs and bring-up steps. Start here.
- `software/`: Chi.Bio control software with an analogue LED driver (`LED_DRIVE_MODE`). `analogue-led.patch` is the diff from upstream.
- `hardware/baseline-digital/`: the original digital-LED PCB package, unchanged, as supplied.
- `hardware/analogue-changes/`: BOM changes for the Side board.
- `tests/test_led_dac.py`: checks the DAC bytes the firmware sends, using stubbed I2C.

**Status:** firmware is tested only against stubs. The Side board PCB itself has not been redrawn, because the source project was not available. See the design document for the open items marked VERIFY.

Software is derived from Chi.Bio by Harrison Steel's group. Check the upstream repository for its licence before redistributing.
