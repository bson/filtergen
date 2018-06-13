# Rauch/MFB low-pass filter calculator

import mpmath as mp

from siutils import SUFFIXES, si_val, sisuffix
from kicad.schema import *

class RauchLPF(Relocatable):
    '''Single low pass filter stage'''

    def __init__(self, pos, f, H0, Q, R1, annot, box = False):
        super(RauchLPF, self).__init__(pos)

        self.annot = annot
        self.box   = box

        # Calculate component values
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

        self.R1 = "%s" % sisuffix(R1)
        self.R2 = "%s" % sisuffix(R2)
        self.R3 = "%s" % sisuffix(R3)
        self.C1 = "%sF" % sisuffix(C1)
        self.C2 = "%sF" % sisuffix(C2)
        self.f  = "%sHz" % sisuffix(f)

        self.OPAMP = "LM358" # Just a dummy value

        self.Build()

    def Print(self, ident):
        print "Rauch LPF Stage (%s)" % ident
        print "R1: %sohm" % self.R1
        print "R2: %sohm" % self.R2
        print "R3: %sohm" % self.R3
        print "C1: %s" % self.C1
        print "C2: %s" % self.C2
        
    def Build(self):
        '''Build a filter stage subcircuit.'''
        stage = SubCircuit((0,0))
        
        if self.annot != "":
            stage.Add(Text((350, 150), self.annot))

        if self.box:
            stage.Add(Box((300, 50), (3400, 1800)))

        r1 = Resistor(self.R1, (1100,650), VERTICAL)
        r2 = Resistor(self.R2, (1400,1000), HORIZONTAL)
        r3 = Resistor(self.R3, (750,1000), HORIZONTAL)
        conn1 = Connection((1100, 1000))

        stage.Add(r1, r2, r3, conn1,
                  Wire.Connect(r1, conn1),
                  Wire.Connect(r3, conn1),
                  Wire.Connect(conn1, r2))

        c1 = Capacitor(self.C1, (1100,1300), VERTICAL)
        c2 = Capacitor(self.C2, (1700,650), VERTICAL)

        gnd1 = Ground((1100,1500))
        stage.Add(c1, c2, gnd1,
                  Wire.Connect(conn1, c1), 
                  Wire.Connect(c1, gnd1))

        conn2 = Connection((1700,1000))
        stage.Add(conn2,
                  Wire.Connect(r2, conn2), 
                  Wire.Connect(c2, conn2))

        conn3 = Connection((1700,300))
        stage.Add(conn3,
                  Wire.Connect(conn3, c2))

        corner1 = Corner((1100,300))
        stage.Add(corner1,
                  Wire.Connect(conn3, corner1),
                  Wire.Connect(corner1, r1),
                  Wire.Connect(conn3, c2))

        opamp = OpAmp(self.OPAMP, (2450, 900), VERTICAL)

        corner2 = Connection((3050, 900))
        corner3 = Corner((3050, 300))
        corner4 = Corner((3050, 1000))

        stage.Add(opamp, corner2, corner3,
                  Wire.Connect(conn2, opamp),
                  Wire.Connect(opamp, corner2),
                  Wire.Connect(corner2, corner3),
                  Wire.Connect(corner3, conn3),
                  Wire.Connect(corner2, corner4))

        corner5 = Corner((1950, 800))
        gnd2    = Ground((1950, 1200))
        pwr1    = Supply("VDD", (2350, 500), VERTICAL)
        pwr2    = Supply("VSS", (2350, 1300), VERTICAL_FLIP)

        stage.Add(corner5, gnd2,
                  Wire.Connect(gnd2, corner5),
                  Wire.Connect(corner5, opamp.GetInP()),
                  pwr1, pwr2,
                  Wire.Connect(pwr1, opamp.GetPwrP()),
                  Wire.Connect(pwr2, opamp.GetPwrM()))

        self.circuit = stage
        self.output  = corner4
        self.input   = r3

    def GetPin1Pos(self):
        return self.input.GetPin1Pos()

    def GetPin2Pos(self):
        return self.output.GetPin2Pos()

    def GetInput(self):
        return self.input

    def GetOutput(self):
        return self.output

    def ToString(self):
        self.circuit.SetOrigin(self.SheetPosition())
        return self.circuit.ToString()


if __name__ == "__main__":
    import sys, os, string

    def usage():
        progname = os.path.split(sys.argv[0])[-1]

        print "usage:"
        print "  %s stage f0 H0 Q R1 [filename]" % progname
        print "     Single-stage Rauch/MFB low-pass filter calculator."
        print "     Calculates component values for a cut-off frequency (-3dB) of f0 Hz,"
        print "     gain H0, and a given Q.  R1 can optionally be specified but will be"
        print "     set to 1kohm if omitted.  If supplied, a KiCAD schmatic is output to"
        print "     'filename'."
        print
        print "SI suffixes:", string.join(SUFFIXES, " ")
        exit(1)

    def do_stage(args):
        '''Generate filter stage.'''

        f, H0, Q, R1 = map(si_val, args[:4])

        filename = None
        if len(args) > 4:
            filename = args[4]

        stage = RauchLPF((2000, 2000), f, H0, Q, R1,
                         "Low-pass filter: H=%s, Q=%s, f0=%s" % (H0, Q, f), True)

        stage.Print("Q=%s" % Q)

        if not filename is None:
            schema = Schematic("A4")
            schema.Add(stage)

            Vin = GlobalLabel((2100, 3000), "VIN", "Input")
            Vout = GlobalLabel((5600, 3000), "VOUT", "Output", 2)

            schema.Add(Vin, Vout,
                       Wire(Vin.GetPin2Pos(), addpos(stage.GetPin1Pos(), stage.Position())),
                       Wire(addpos(stage.GetPin2Pos(), stage.Position()), Vout.GetPin1Pos()))

            with open(filename, "w") as file:
                file.write(schema.ToString())
                print "Wrote schematic to %s" % filename
        

    if len(sys.argv) < 2:
        usage()

    what = sys.argv[1]
    if what == "stage" and len(sys.argv) >= 6:
        do_stage(sys.argv[2:])
    else:
        usage()
