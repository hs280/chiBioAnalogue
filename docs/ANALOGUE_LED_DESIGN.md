# Chi.Bio Analogue: LED drive redesign

Goal: keep the Chi.Bio reactor, but set every LED's brightness with a steady DC current from a constant current regulator (CCR), not by switching it on and off with PWM.

## Status

| Item | State |
|---|---|
| Side board schematic and layout | **Source received** (`hardware/source-altium/`). Schematic netlist extracted and cross-checked against the PCB: all 69 multi-pin nets match. |
| Firmware (`software/app.py`) | Done, matched to the real schematic. Tested against stubbed I2C only (`tests/test_led_dac.py`). Not run on hardware. |
| Modified Side board | **Not done.** Section 4 lists the edits. Nothing has been routed or fabricated. |
| Items marked **VERIFY** | Need a datasheet or a bench measurement. |

An earlier version of this document guessed the circuit from the BOM. The real schematic changed three things: one DAC is enough, the UV stage is already a CCR, and the CCR has a built-in dead zone. This version replaces it.

## 1. What changes and what does not

**Unchanged:** every other board (pump, BeagleBone cape, heater, IR sensor, laser board and its DAC, spectrometer, structural boards), the stir and heat PWM channels, and the web UI.

**Changed:** the Side board LED inputs, and the firmware that drives them.

| | Original (digital) | Analogue variant |
|---|---|---|
| LED set-point | PCA9685 PWM at 1526 Hz | DC voltage from an I2C DAC |
| LED current | Chopped between 0 and full current | Steady, regulated by the CCR |
| Spectrometer vs LED | Integration window can alias with PWM | No flicker |

## 2. The existing LED circuit (from the schematic)

Every LED channel is already a closed-loop current regulator. Set-point voltage comes from a PCA9685 output through a divider into an op-amp.

```
PCA9685 out --[R2 38.3k]--+--[R1 10k]-- GND
                          |
                          +--> op-amp (+)        op-amp out --> NPN base (ZXTN25100DG)
 6 V -----[R4 1M]---+--> op-amp (-)              6 V -> LED -> NPN collector
 NPN emitter --[R1 10k]--+                       NPN emitter --[R3 1 ohm]--> GND
```

Op-amps are two AD8534 quads (OA1-1, OA1-2). Channel map, taken from the netlist and confirmed against the firmware's PCA9685 register addresses:

| Firmware name | Colour | PCA9685 pin (output) | Op-amp, out / + / - pins | Transistor | Sense R | LED pin |
|---|---|---|---|---|---|---|
| LEDC | Cyan | 7 (LED1) | OA1-1: 1 / 3 / 2 | TR2-1 | R3-1, 1 ohm | LED1.11 |
| LEDH | Yellow | 15 (LED8) | OA1-1: 7 / 5 / 6 | TR2-2 | R3-2, 1 ohm | LED1.15 |
| LEDI | Lime 2 | 17 (LED10) | OA1-1: 8 / 10 / 9 | TR2-3 | R3-3, 1 ohm | LED1.17 |
| LEDJ | Lime 1 | 19 (LED12) | OA1-1: 14 / 12 / 13 | TR2-4 | R3-4, 1 ohm | LED1.20 |
| LEDD | Green | 11 (LED5) | OA1-2: 1 / 3 / 2 | TR2-5 | R3-5, 1 ohm | LED1.21 |
| LEDB | Blue | 10 (LED4) | OA1-2: 7 / 5 / 6 | TR2-6 | R3-6, 1 ohm | LED1.23 |
| LEDF | Red | 12 (LED6) | OA1-2: 8 / 10 / 9 | TR2-7 | R3-7, 1 ohm | LED1.24 |
| UV | UV | 22 (LED15) | OA1-2: 14 / 12 / 13 | TR2-8 | R9, 40.2 ohm | LED2.1 |

Other PCA9685 outputs: pin 6 (LED0) is stir, pin 21 (LED14) is heat. Pins 8, 9, 13, 16, 18 and 20 (LEDA, LEDG, LEDE and three spare) are unconnected on this board. This is the LED version 2 board. LEDA, LEDE and LEDG exist only in the firmware.

Findings that matter for the redesign:

- **The UV stage is already a CCR.** I earlier thought it was resistor-limited. It has the same op-amp loop with a 40.2 ohm sense resistor and a 12 V supply. Its set-point goes straight to the op-amp (with a 10k pull-down), not through a divider.
- **Full-scale current.** LEDs: 3.3 V x 10k/48.3k = 0.683 V set-point, about 0.63 A. UV: 3.3 V set-point, about 80 mA. A 3.3 V DAC reproduces both with no resistor changes. At 100 percent PWM duty the original board already ran these currents continuously, so 100 percent analogue is no new worst case.
- **Built-in dead zone.** R4 (1M from the supply) and R1 (10k to the sense node) hold the op-amp's inverting input above the sense node by 6 V x 10k/1.01M = 59 mV (LEDs) or 119 mV (UV). The set-point must exceed that before current flows. This gives a true zero when off, and it absorbs op-amp input offset. It also means the lowest 8.7 percent (LEDs) or 3.6 percent (UV) of DAC range does nothing. The firmware adds it back so intensity maps linearly onto current.
- **No existing filter.** There are no capacitors on the set-point nodes.

## 3. The change

Replace the 8 PCA9685 outputs above with the 8 channels of one octal DAC. This is why one chip is enough.

```
3V3 --> DAC7578 (U?) --VOUT0..7--> the 7 divider inputs (R2-x pin 2) and the UV op-amp input (OA1-2 pin 12 / R1-14)
SDA, SCL: existing nets.   Decoupling: 100 nF + 1 uF.
```

| DAC channel | Output | Net | Replaces |
|---|---|---|---|
| 0 | LEDB, Blue | Blue0 | PWM1.10 |
| 1 | LEDC, Cyan | Cyan0 | PWM1.7 |
| 2 | LEDD, Green | Green0 | PWM1.11 |
| 3 | LEDF, Red | Red0 | PWM1.12 |
| 4 | LEDH, Yellow | Yellow0 | PWM1.15 |
| 5 | LEDI, Lime 2 | Lime20 | PWM1.17 |
| 6 | LEDJ, Lime 1 | Lime10 | PWM1.19 |
| 7 | UV | net on PWM1.22 | PWM1.22 |

The channel order is a free choice and can follow whatever routes best. If you change it, edit `LED_DAC_MAP` in `software/app.py`.

DAC choice: TI **DAC7578** (octal, 12 bit, I2C, 2.7 to 5.5 V, TSSOP-16). The TSSOP package powers up at zero scale, so LEDs are off at power-on. **VERIFY** before ordering:

- The I2C address table for the ADDR0 and ADDR1 pins. The firmware default is 0x4A. It must not be 0x48 (laser DAC), 0x60 (PCA9685), 0x39 or the thermometer addresses.
- That output full scale equals the 3.3 V supply (not an internal reference).

## 4. Edits to the Side board

1. Add the DAC and its decoupling on the 3.3 V rail, with ADDR strapping, on the existing SDA and SCL nets.
2. For each row in the table, cut the net from the PCA9685 pin and connect it to the DAC output.
3. Leave the PCA9685 in place for stir and heat. Its freed pins stay unconnected.
4. Regenerate Gerbers, BOM and pick-and-place.

Altium sources are in `hardware/source-altium/`. A KiCad import of the board is `Side.imported-from-altium.kicad_pcb` (92 footprints, 70 nets, 51.45 x 115.05 mm outline). Pad and net names are preserved. Footprints are Altium-derived and the copper pour and silkscreen should be checked after any edit. BOM delta: `hardware/analogue-changes/side_board_bom_delta.csv`.

## 5. Trade-offs

- **Wavelength shift.** LED peak wavelength drifts with current, so a dimmed LED has a different colour than a PWM-dimmed one at the same average power. Recalibrate OD (`OD0`) and fluorescence settings after switching.
- **Dissipation.** The pass transistor burns power continuously at partial brightness. At 100 percent it is the same as the original. Check the SOT-223 thermal margin with several channels at mid-level.
- **Dead-zone accuracy.** The 59 mV and 119 mV thresholds depend on the 1M and 10k resistor tolerances (0.1 percent parts reduce the error). Measure each channel and adjust `LED_DAC_DEADBAND`.
- **Old intensity numbers.** Saved intensities were PWM duty. Here they are current fraction. Treat them as a different instrument.

## 6. Firmware

All in `software/app.py`. `software/analogue-led.patch` is the diff against upstream Chi.Bio.

- `LED_DRIVE_MODE` is `'ANALOGUE'` (DAC) or `'PWM'` (original boards).
- `LED_DAC_MAP`, `LED_DAC_DEADBAND`, `LED_DAC_FULLSCALE` set the channel map, the dead-zone correction and a per-channel clamp.
- `setLED()` replaces the LED and UV PWM calls. Unfitted LEDs (LEDA, LEDE, LEDG) are ignored. LEDV, the virtual white, works unchanged.
- `turnEverythingOff()` zeroes every DAC channel.

Bring-up:

1. Power the board with LEDs unplugged. Find the DAC with `i2cdetect` through the mux channel.
2. Set `LED_DAC_FULLSCALE` to about 0.1 for all channels.
3. Measure the sense-resistor voltage at 10, 50 and 100 percent. Expect about 0.63 V at 100 percent for the LEDs, and 3.2 V across R9 for UV.
4. Raise the clamp only after step 3 matches, and never above the LED's rated current.

## 7. Reproducing the netlist

```
python3 -I tools/altium_sch_netlist.py tools/altium_sch_parse.py hardware/source-altium/Side.SchDoc far netlist.json
```

`docs/side_board_netlist.csv` is the full extracted netlist.
