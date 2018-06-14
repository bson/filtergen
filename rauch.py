# Rauch/MFB low-pass filter calculator

import mpmath as mp

from siutils import SUFFIXES, si_val, sisuffix, nsigdig
from kicad.schema import *
import pole

NQDIGITS=6
NHDIGITS=4

class Lowpass(Relocatable):
    '''Single low pass filter stage'''

    def __init__(self, pos, f, H0, Q, R1, annot, box = False):
        super(Lowpass, self).__init__(pos)

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
        print "  R1: %sohm" % self.R1
        print "  R2: %sohm" % self.R2
        print "  R3: %sohm" % self.R3
        print "  C1: %s" % self.C1
        print "  C2: %s" % self.C2
        
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


class Cascade(Relocatable):
    def __init__(self, pos, f, H0, n, R1, q_enumerator, kind):
        super(Cascade, self).__init__(pos)

        self.input = None
        self.output = None

        self.circuit = SubCircuit((0,0))

        self.circuit.Add(Text((300, 2100), "%s Multiple-Feedback Low-Pass Filter\\nGain=%s, f=%sHz" % (
            kind, H0, sisuffix(f))))

        Qlist, flist  = q_enumerator(n)
        prev   = None
        xpos   = 0
        outpos = (-150, 1000)
        inpos  = (650, 1000)

        H = mp.root(H0, n)

        i = 1
        for Q in Qlist:
            f_stage = f * flist[i-1]
            stage = Lowpass((xpos, 0), f_stage, H, Q, R1,
                            "MFB LPF Stage %d [H=%s, Q=%s, f0=%s %s]" % (
                                i,
                                nsigdig(H, NHDIGITS),
                                nsigdig(Q, NQDIGITS),
                                "%sHz" % sisuffix(f_stage),
                                kind),
                            True)
            self.circuit.Add(stage)

            if prev is None:
                self.input = stage.GetInput()
            else:
                self.circuit.Add(Wire(outpos, inpos))
                print

            stage.Print("#%s, Q=%s" % (i, nsigdig(Q, NQDIGITS)))
            prev   = stage
            xpos  += 3200
            outpos = addpos(outpos, (3200, 0))
            inpos  = addpos(inpos, (3200, 0))

            i += 1

        self.output  = prev.GetOutput()
        
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


class ButterworthCascade(Cascade):
    '''A lowpass filter cascasde with flat passpand frequency response.'''

    def __init__(self, pos, f, H0, n, R1):
        super(ButterworthCascade, self).__init__(pos, f, H0, n, R1, pole.butterworth,
                                                 "Butterworth")


class BesselCascade(Cascade):
    '''A lowpass filter cascasde with flat passpand phase response.'''

    def __init__(self, pos, f, H0, n, R1):
        super(BesselCascade, self).__init__(pos, f, H0, n, R1, pole.bessel, "Bessel")

        
if __name__ == "__main__":
    import sys, os, string

    def usage():
        progname = os.path.split(sys.argv[0])[-1]

        print "usage:"
        print "  %s butterworth f0 H0 N R1 [filename]" % progname
        print "     N-stage Rauch/MFB low-pass filter calculator with Butterworth response."
        print "     Calculates component values for a cut-off frequency (-3dB) of f0 Hz,"
        print "     gain H0.  R1 is used to scale resistors, with 1k being a good"
        print "     starting point.  If supplied, a KiCAD schmatic is output to 'filename'."
        print
        print "  %s bessel f0 H0 N R1 [filename]" % progname
        print "     N-stage Rauch/MFB low-pass filter calculator with Bessel response."
        print "     Calculates component values for a cut-off frequency (-3dB) of f0 Hz,"
        print "     gain H0.  R1 is used to scale resistors, with 1k being a good"
        print "     starting point.  If supplied, a KiCAD schmatic is output to 'filename'."
        print
        print "  %s stage f0 H0 Q R1 [filename]" % progname
        print "     Single-stage Rauch/MFB low-pass filter calculator."
        print "     Calculates component values for a cut-off frequency (-3dB) of f0 Hz,"
        print "     gain H0, and a given Q.  R1 is used to scale resistors, with 1k a good"
        print "     starting point.  If supplied, a KiCAD schmatic is output to 'filename'."
        print
        print "SI suffixes:", string.join(SUFFIXES, " ")
        exit(1)

    def add_in_out(schema, filter, n):
            Vin = GlobalLabel((2100, 3000), "VIN", "Input")

            outpos = addpos((550, 0), filter.GetPin2Pos())
            outpos = addpos(outpos, filter.Position())
            n = int(n)
            if n >= 1:
                outpos = addpos(outpos, ((n-1)*3200, 0))

            Vout = GlobalLabel(outpos, "VOUT", "Output", 2)

            pinpos = addpos(outpos, (-550, 0))

            hookups = SubCircuit((0,0))
            hookups.Add(Vin, Vout,
                       Wire(Vin.GetPin2Pos(), addpos(filter.GetPin1Pos(), filter.Position())),
                       Wire(pinpos, Vout.GetPin1Pos()))
            hookups.SetOrigin(filter.GetOrigin())
            schema.Add(hookups);


        
    def do_common(func, args):
        filename = None
        if len(args) > 4:
            filename = args[4]

        circuit, n = func(args)
        
        if not filename is None:
            schema = Schematic("A4")
            schema.Add(circuit)

            height = schema.GetSize()[1]
            height = height - (height % 100) # Snap to mil grid

            circuit.SetOrigin((-2500, height - 2000))

            add_in_out(schema, circuit, n)

            with open(filename, "w") as file:
                file.write(schema.ToString())
                print "\nWrote schematic to %s" % filename


    def do_stage(args):
        f, H0, Q, R1 = map(si_val, args[:4])

        stage = Lowpass((2000, 2000), f, H0, Q, R1,
                        "MFB LPF: H=%s, Q=%s, f0=%s" % (H0, nsigdig(Q, NQIGITS), f),
                        True)

        stage.Print("Q=%s" % nsigdig(Q, NQDIGITS))
        return stage, 1
        

    def do_butterworth(args):
        f, H0, N, R1 = map(si_val, args[:4])

        if N > 32:
            print "N is too big; you probably didn't mean to do this"
            exit(1)

        return ButterworthCascade((2000, 2000), f, H0, N, R1), N
        

    def do_bessel(args):
        f, H0, N, R1 = map(si_val, args[:4])

        if N > 32:
            print "N is too big; you probably didn't mean to do this"
            exit(1)

        return BesselCascade((2000, 2000), f, H0, N, R1), N
        

    what = sys.argv[1]
    if what == "stage" and len(sys.argv) >= 6:
        func = do_stage
    elif what == "butterworth" and len(sys.argv) >= 6:
        func = do_butterworth
    elif what == "bessel" and len(sys.argv) >= 6:
        func = do_bessel
    else:
        usage()

    do_common(func, sys.argv[2:])
