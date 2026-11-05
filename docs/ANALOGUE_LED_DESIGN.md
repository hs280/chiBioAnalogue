# Chi.Bio Analogue: LED drive redesign

Goal: keep the Chi.Bio reactor, but set every LED's brightness with a steady DC current from a constant current regulator (CCR), not by switching it on and off with PWM.

## Status: what is done and what is not

| Item | State |
|---|---|
| Firmware (`software/app.py`) | Done. Unit-tested against stubbed I2C (`tests/test_led_dac.py`). Not run on real hardware. |
| Design spec, I2C map, BOM changes (this folder) | Done. Written from the BOM, pick-and-place, Gerbers and firmware. |
| Side board schematic and layout | **Not done.** The zip holds Gerbers, not Altium sources, so the new board cannot be generated here. Section 4 lists the exact edits for whoever opens the original project. |
| Values marked **VERIFY** | Inferred from BOM and firmware. Check against the original schematic before ordering boards. |

## 1. What changes and what does not

**Unchanged:** pump board, BeagleBone cape, heater, IR sensor, laser board and its DAC, AS7341 spectrometer board, all structural boards, the stir/heat PWM channels, and the web UI.

**Changed:** only the Side board LED path (LED1 visible array, LED2/UV) and the firmware that talks to it.

| | Original (digital) | Analogue variant |
|---|---|---|
| LED set-point | PCA9685 PWM at 1526 Hz, 12 bit | DC voltage from an I2C DAC, 12 bit |
| LED current | Chopped between 0 and full current | Steady, regulated by the CCR |
| Brightness control | Duty cycle | Current amplitude |
| Spectrometer vs LED | Integration window can alias with PWM | No flicker |
| Audible ringing on the 6 V rail | Possible (firmware comment) | Gone for LEDs |

## 2. Why the existing Side board is close to a CCR already

From the Side BOM and pick-and-place:

- A quad op-amp (AD8534, two of them), one SOT-223 NPN (ZXTN25100DG) per channel, and a 1 ohm 2512 sense resistor per channel (7 of them).
- Divider resistors 38.3k and 10k (9 and 20 of them).

That is the usual op-amp, transistor, sense-resistor current regulator. In the digital board its reference input is the PWM output through a 38.3k/10k divider. **VERIFY** this against the schematic.

If so, the full-scale current is set by the divider and the sense resistor:

```
V_ref(full scale) = V_DAC,max x 10k / (10k + 38.3k) = 3.3 V x 0.207 = 0.683 V
I_LED,max         = V_ref / R_sense                 = 0.683 V / 1 ohm = 0.68 A
```

So a DAC with a 3.3 V full-scale output, wired where the PCA9685 output was, reproduces the original maximum current with no other resistor changes. Per channel: `I_LED = (code / 4095) x I_LED,max`.

## 3. New circuit per LED channel

```
 3V3 -> DAC7578 (VOUTn) --[38.3k]--+--[10k]-- GND          (existing divider, re-fed from DAC)
                                   |
                                   +--> op-amp (+)   op-amp out --[Rb]--> NPN base
                                                      op-amp (-) <-- emitter node
 6 V rail -> LED -> NPN collector;  NPN emitter -> R_sense (1 ohm) -> GND
```

Add per channel: 100 nF from the divider node to ground (DAC glitch and noise filter), unless the board already has one. **VERIFY** whether the original has it.

### DAC choice

Two octal 12-bit I2C DACs, TI **DAC7578** (TSSOP-16), 3.3 V supply, output 0 to VDD. **VERIFY** the part before ordering.

- Channels needed: LEDA to LEDG (7 CCRs) plus UV, plus LEDH and LEDI that the firmware supports for LED version 2. That is 10, so two chips.
- The DAC powers up at zero scale, so LEDs are off at power-on.
- 0x48 is already the laser DAC on each device's I2C branch. The LED DACs must not use it. Firmware defaults are 0x4A and 0x4C. **VERIFY** the strapping needed to get those addresses.

### I2C map per reactor (behind its own mux channel)

| Address | Device | Status |
|---|---|---|
| 0x18 / 0x1B | Thermometers | unchanged |
| 0x39 | AS7341 | unchanged |
| 0x48 | Laser DAC | unchanged |
| 0x4A | LED DAC 0 (LEDA..LEDH, channels 0 to 7) | **new** |
| 0x4C | LED DAC 1 (LEDI channel 0, UV channel 1) | **new** |
| 0x5A | IR thermometer | unchanged |
| 0x60 | PWM chip (stir, heat; LEDs when in PWM mode) | unchanged |
| 0x61 | Pump PWM chip | unchanged |

### UV channel

On the digital board the UV LED uses a power transistor with a fixed 40.2 ohm resistor (R9), not a 1 ohm sense resistor. To make it a true CCR, replace R9 with a sense resistor sized `R = V_ref,max / I_UV,max` and give it the same op-amp stage. **I did not find the UV LED's rated current in the files**, so pick it from the LED datasheet.

## 4. Edits for the Side board project (Altium)

1. Add two DAC7578 on the 3.3 V I2C branch (SDA/SCL already present for the PCA9685) with decoupling and the address strapping.
2. For each LED channel net, cut it from the PCA9685 output and connect it to the matching DAC output (map in `software/app.py`, `LED_DAC_MAP`).
3. Add the 100 nF filter at each divider node if absent.
4. Convert the UV stage as described above.
5. Keep the PCA9685 for Stir and Heat. Its unused LED outputs stay unconnected.
6. Regenerate Gerbers, BOM and pick-and-place. The part-level BOM delta is in `hardware/analogue-changes/side_board_bom_delta.csv`.

## 5. Known trade-offs of analogue dimming

- **True off.** PWM gave exact zero. A CCR leaves a small current if the op-amp has input offset. With a 1 ohm sense resistor, every 1 mV of offset is about 1 mA. Check the AD8534 offset in its datasheet. The firmware always writes exactly zero when a channel is off, and `LED_DAC_OFFSET_CODES` can compensate while on. If measured leakage matters for fluorescence, add a pull-down on each divider node driven from a spare PCA9685 output.
- **Wavelength shift.** LED peak wavelength drifts with current. At low dimming levels the colour differs from a PWM-dimmed LED at the same average power. Recalibrate OD and fluorescence factors (`OD0` and the `FP` settings) after switching.
- **Low-level resolution.** 12 bits over 0.68 A is about 0.17 mA per step, same as the original PWM resolution.
- **Dissipation.** The pass transistor now burns `(V_rail - V_LED - V_sense) x I` continuously instead of in pulses. At full current this is heat inside the reactor. Check against the thermostat and the SOT-223 thermal limit before running all channels at once.
- **Existing calibrations.** Intensity numbers saved in old experiments are PWM duty. In this variant they are current fraction. Treat them as different instruments.

## 6. Firmware

Everything is in `software/app.py`; `software/analogue-led.patch` is the diff against upstream Chi.Bio.

- `LED_DRIVE_MODE = 'ANALOGUE'` selects DAC drive. `'PWM'` restores the original behaviour for digital boards.
- `LED_DAC_MAP` maps each output to a DAC chip and channel.
- `LED_DAC_FULLSCALE` clamps a channel's maximum, for example to protect an LED after you measure its current.
- `LED_DAC_OFFSET_CODES` adds a per-channel offset while on.
- `setLED()` replaces the old LED/UV PWM calls. `LEDV` (the virtual white mixing LEDB and LEDI) works unchanged.
- `turnEverythingOff()` also zeroes all LED DAC channels.

Bring-up order:

1. Power the Side board with LEDs unplugged. Confirm DAC addresses with `i2cdetect` through the mux channel.
2. Set `LED_DAC_FULLSCALE` low (for example 0.1) for all channels.
3. Measure the sense-resistor voltage at 10, 50 and 100 percent for each channel. Expect `V = (code/4095) x 0.683 V`.
4. Raise the clamp to the LED's rated current only after step 3 matches.
