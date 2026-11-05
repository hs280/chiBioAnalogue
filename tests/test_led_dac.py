"""Runs the real app.py against stubbed hardware and checks the bytes sent to the LED DACs.
Run:  python3 tests/test_led_dac.py   (needs flask, numpy, simplejson; no BeagleBone needed)"""
import sys, types, os, importlib.util

log = []  # (address, command, data)

class FakeDev:
    def __init__(self, addr): self.addr = addr; self.regs = {}
    def writeList(self, reg, data): log.append((self.addr, reg, list(data)))
    def write8(self, reg, val): self.regs[reg] = val; log.append((self.addr, reg, [val]))
    def write16(self, reg, val): log.append((self.addr, reg, [val]))
    def readU8(self, reg): return self.regs.get(reg, 0)
    def readRaw8(self): return 0

def stub(name, **attrs):
    m = types.ModuleType(name); m.__dict__.update(attrs); sys.modules[name] = m; return m

stub('Adafruit_GPIO'); stub('Adafruit_GPIO.I2C', get_i2c_device=lambda a, b: FakeDev(a))
stub('Adafruit_BBIO'); stub('Adafruit_BBIO.GPIO', output=lambda *a: None, setup=lambda *a: None,
                            OUT=0, HIGH=1, LOW=0, IN=0)
stub('serial'); stub('smbus2', SMBus=lambda bus=0: FakeDev(0x5a))
for mod in ('simplejson',):
    try: __import__(mod)
    except ImportError: import json; stub('simplejson', **json.__dict__)

src = open(os.path.join(os.path.dirname(__file__), '..', 'software', 'app.py')).read()
# Stop the hardware start-up (initialiseAll) from running at import time.
src = src.replace("if __name__ == '__main__':\n    initialiseAll()", "if __name__ == '__main__':\n    pass")
src = src.replace("else:\n    initialiseAll()", "else:\n    pass")
app = types.ModuleType('app'); app.__file__ = 'app.py'
exec(compile(src, 'app.py', 'exec'), app.__dict__)

M = 'M0'
app.sysData[M]['present'] = 1
app.sysItems['Multiplexer']['device'] = FakeDev(0x74)
app.sysItems['Multiplexer']['device'].readRaw8 = lambda: int(app.sysItems['Multiplexer'][M], 2)
for n, a in app.LED_DAC_ADDRESSES.items():
    app.sysDevices[M][n] = {'device': FakeDev(a)}

app.sysDevices[M]['PWM']['device'] = FakeDev(0x60)

def dac_writes():
    out = [e for e in log if e[0] in app.LED_DAC_ADDRESSES.values() and len(e[2]) == 2]
    log.clear(); return out

fails = 0
def check(label, got, want):
    global fails
    ok = got == want
    fails += not ok
    print(('PASS ' if ok else 'FAIL ') + label + ('' if ok else f'  got={got} want={want}'))

# full scale on LEDA -> chip 0x4A, cmd 0x30|0, code 4095 left-justified = 0xFFF0
app.sysData[M]['LEDA']['target'] = 1.0; app.SetOutputOn(M, 'LEDA', 1)
check('LEDA 100%', dac_writes(), [(0x4A, 0x30, [0xFF, 0xF0])])
# half scale LEDG -> chip 0x4A, channel 6
app.sysData[M]['LEDG']['target'] = 0.5; app.SetOutputOn(M, 'LEDG', 1)
check('LEDG 50%', dac_writes(), [(0x4A, 0x36, [0x80, 0x00])])
# off -> exact zero
app.SetOutputOn(M, 'LEDG', 0)
check('LEDG off', dac_writes(), [(0x4A, 0x36, [0x00, 0x00])])
# LEDI lives on second chip, channel 0
app.sysData[M]['LEDI']['target'] = 0.25; app.SetOutputOn(M, 'LEDI', 1)
check('LEDI 25%', dac_writes(), [(0x4C, 0x30, [0x40, 0x00])])
# UV on second chip, channel 1
app.sysData[M]['UV']['target'] = 1.0; app.SetOutputOn(M, 'UV', 1)
check('UV 100%', dac_writes(), [(0x4C, 0x31, [0xFF, 0xF0])])
# LEDV mixes LEDB (x ScaleFactor) and LEDI
app.sysData[M]['LEDV']['target'] = 0.5; app.SetOutputOn(M, 'LEDV', 1)
sf = app.sysData[M]['LEDV']['ScaleFactor']
w = dac_writes()
check('LEDV writes LEDB then LEDI', [(a, c) for a, c, _ in w], [(0x4A, 0x31), (0x4C, 0x30)])
# clamp / full-scale limit / offset
app.LED_DAC_FULLSCALE['LEDC'] = 0.5
app.sysData[M]['LEDC']['target'] = 1.0; app.SetOutputOn(M, 'LEDC', 1)
check('LEDC clamped to 50% full-scale', dac_writes(), [(0x4A, 0x32, [0x80, 0x00])])
# all off writes every channel to zero
app.setAllLEDsZero(M)
w = dac_writes()
check('all-off hits 10 channels, all zero', (len(w), all(d == [0, 0] for _, _, d in w)), (10, True))
# PWM mode still routes to the PCA9685
app.LED_DRIVE_MODE = 'PWM'; log.clear()
app.sysData[M]['LEDA']['target'] = 1.0; app.SetOutputOn(M, 'LEDA', 1)
pca = any(e[0] == 0x60 for e in log)
check('PWM mode uses PCA9685 (0x60), no DAC writes', (dac_writes(), pca), ([], True))
sys.exit(1 if fails else 0)
