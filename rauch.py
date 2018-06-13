# Rauch/MFB low-pass filter calculator

import mpmath as mp

from siutils import SUFFIXES, si_val, sisuffix
import kicad.schema as sch


def rauch_lpf(f, H0, Q, R1):
    R3 = R1 / H0
    R2 = R1/(1.0 + H0)
    w0 = 2.0 * f * mp.pi
    # The product C1*C2
    C1C2 = 1/(mp.power(w0, 2.0)*R1*R2)
    # The ratio C1/C2
    rC1C2 = mp.power(Q, 2.0)*mp.power(mp.sqrt(R2/R1)*(1+H0)+mp.sqrt(R1/R2), 2.0)
    # C1, C2
    C1 = mp.sqrt(C1C2*rC1C2)
    C2 = C1C2/C1
    return R2, R3, C1, C2

if __name__ == "__main__":
    import sys, os, string

    def usage():
        progname = os.path.split(sys.argv[0])[-1]

        print "usage:"
        print "  %s lowpass f H Q [R1]" % progname
        print "     Rauch/MFB low-pass filter calculator."
        print "     Calculates component values for a cut-off frequency (-3dB) of f Hz,"
        print "     gain H, and a given Q.  R1 can optionally be specified but will be"
        print "     set to 1kohm if omitted."
        print
        print "Suffixes:", string.join(SUFFIXES, " ")
        exit(1)

    if len(sys.argv) < 2:
        usage()

    what = sys.argv[1]
    if what == "lowpass" and len(sys.argv) == 6:
        f  = si_val(sys.argv[2])
        H0  = si_val(sys.argv[3])
        Q  = si_val(sys.argv[4])
        if len(sys.argv) >= 5:
            R1 = si_val(sys.argv[5])
        else:
            R1 = 1000

        R2, R3, C1, C2 = rauch_lpf(f, H0, Q, R1)
    else:
        usage()

    R1 = "%s" % sisuffix(R1)
    R2 = "%s" % sisuffix(R2)
    R3 = "%s" % sisuffix(R3)
    C1 = "%sF" % sisuffix(C1)
    C2 = "%sF" % sisuffix(C2)

    print "R1: %sohm" % R1
    print "R2: %sohm" % R2
    print "R3: %sohm" % R3
    print "C1: %s" % C1
    print "C2: %s" % C2

    # Output schematic

    schema = sch.Schematic("A4")
    stage  = sch.SubCircuit((2000,2000))
    schema.Add(stage)

    inp = sch.GlobalLabel((550, 1000), "Vin", "Input")

    note = sch.Text((350, 150), "Low-pass filter: H=%s, Q=%s, f0=%s" % (H0, Q, f))

    box = sch.Box((300, 50), (3400, 1800))

    r1 = sch.Resistor(R1, (1100,650), sch.VERTICAL)
    r2 = sch.Resistor(R2, (1400,1000), sch.HORIZONTAL)
    r3 = sch.Resistor(R3, (750,1000), sch.HORIZONTAL)
    conn1 = sch.Connection((1100, 1000))

    stage.Add(r1, r2, r3, conn1, inp, note, box,
              sch.Wire.Connect(r1, conn1),
              sch.Wire.Connect(r3, conn1),
              sch.Wire.Connect(conn1, r2),
              sch.Wire.Connect(inp, r3))

    c1 = sch.Capacitor(C1, (1100,1300), sch.VERTICAL)
    c2 = sch.Capacitor(C2, (1700,650), sch.VERTICAL)

    gnd1 = sch.Ground((1100,1500))
    stage.Add(c1, c2, gnd1,
              sch.Wire.Connect(conn1, c1), 
              sch.Wire.Connect(c1, gnd1))

    conn2 = sch.Connection((1700,1000))
    stage.Add(conn2,
              sch.Wire.Connect(r2, conn2), 
              sch.Wire.Connect(c2, conn2))

    conn3 = sch.Connection((1700,300))
    stage.Add(conn3,
              sch.Wire.Connect(conn3, c2))

    corner1 = sch.Corner((1100,300))
    stage.Add(corner1,
              sch.Wire.Connect(conn3, corner1),
              sch.Wire.Connect(corner1, r1),
              sch.Wire.Connect(conn3, c2))

    opamp = sch.OpAmp("LM741", (2450, 900), sch.VERTICAL)

    corner2 = sch.Corner((3050, 900))
    corner3 = sch.Corner((3050, 300))

    stage.Add(opamp, corner2, corner3,
              sch.Wire.Connect(conn2, opamp),
              sch.Wire.Connect(opamp, corner2),
              sch.Wire.Connect(corner2, corner3),
              sch.Wire.Connect(corner3, conn3))
              
    corner4 = sch.Corner((1950, 800))
    gnd2    = sch.Ground((1950, 1200))
    pwr1    = sch.Supply("VDD", (2350, 500), sch.VERTICAL)
    pwr2    = sch.Supply("VSS", (2350, 1300), sch.VERTICAL_FLIP)
    
    stage.Add(corner4, gnd2,
              sch.Wire.Connect(gnd2, corner4),
              sch.Wire.Connect(corner4, opamp.GetInP()),
              pwr1, pwr2,
              sch.Wire.Connect(pwr1, opamp.GetPwrP()),
              sch.Wire.Connect(pwr2, opamp.GetPwrM()))

    with open("filter.sch", "w") as file:
        file.write(schema.ToString())
        print "Wrote schematic to filter.sch"
