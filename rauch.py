# Rauch/MFB low-pass filter calculator

import mpmath as mp

from siutils import SUFFIXES, si_val, sisuffix, nsigdig
from kicad.schema import *
import pole

NQDIGITS=6
NHDIGITS=4

class Lowpass(Relocatable):
    '''Single low pass filter stage'''

    def __init__(self, pos, f, H0, Q, R1, annot, box = False, sim = False):
        super(Lowpass, self).__init__(pos)

        self.annot = annot
        self.box   = box
        self.sim   = sim

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

        if self.sim:
            self.OPAMP = "${SIM.PARAMS}"
        else:
            self.OPAMP = "LM358" # Just a dummy value

        self.Build()

    def Print(self, ident):
        print("Rauch LPF Stage (%s)" % ident)
        print("  R1: %sohm" % self.R1)
        print("  R2: %sohm" % self.R2)
        print("  R3: %sohm" % self.R3)
        print("  C1: %s" % self.C1)
        print("  C2: %s" % self.C2)
        
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

        opamp = OpAmp(self.OPAMP, (2450, 1000), VERTICAL, sim)

        corner2 = Connection((3050, 1000))
        corner3 = Corner((3050, 300))
        corner4 = Corner((3050, 1000))

        inp_corner = Corner((1950, 1100))
        inp_corner2 = Corner((1950,1000))

        stage.Add(opamp, corner2, corner3,
                  Wire.Connect(conn2, inp_corner2),
                  Wire.Connect(inp_corner2, inp_corner),
                  Wire.Connect(inp_corner, opamp),
                  Wire.Connect(opamp, corner2),
                  Wire.Connect(corner2, corner3),
                  Wire.Connect(corner3, conn3),
                  Wire.Connect(corner2, corner4))

        corner5 = Corner((2050, 900))
        gnd2    = Ground((2050, 1400))
        pwr1    = Supply("VDD", (2350, 600), VERTICAL)
        pwr2    = Supply("VSS", (2350, 1400), VERTICAL_FLIP)

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

    def PartsList(self):
        return self.circuit.PartsList()


class Cascade(Relocatable):
    def __init__(self, pos, f, H0, n, R1, q_enumerator, kind, sim):
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

        H = H0

        i = 1
        for Q in Qlist:
            f_stage = f * flist[i-1]
            stage = Lowpass((xpos, 0), f_stage, H, Q, R1,
                            "#%d: H=%s, Q=%s, f0=%s" % (
                                i,
                                nsigdig(H, NHDIGITS),
                                nsigdig(Q, NQDIGITS),
                                "%sHz" % sisuffix(f_stage)),
                            True, sim)
            self.circuit.Add(stage)

            if prev is None:
                self.input = stage.GetInput()
            else:
                self.circuit.Add(Wire(outpos, inpos))
                print()

            stage.Print("#%s, H=%s, Q=%s, f=%sHz" % (i, nsigdig(H, NHDIGITS),
                                                     nsigdig(Q, NQDIGITS),
                                                     sisuffix(f_stage)))
            prev   = stage
            xpos  += 3200
            outpos = addpos(outpos, (3200, 0))
            inpos  = addpos(inpos, (3200, 0))

            i += 1
            H  = 1.0

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

    def PartsList(self):
        return self.circuit.PartsList()


class ButterworthCascade(Cascade):
    '''A lowpass filter cascasde with flat passpand frequency response.'''

    def __init__(self, pos, f, H0, n, R1, sim):
        super(ButterworthCascade, self).__init__(pos, f, H0, n, R1, pole.butterworth,
                                                 "Butterworth", sim)


class BesselCascade(Cascade):
    '''A lowpass filter cascasde with flat passpand phase response.'''

    def __init__(self, pos, f, H0, n, R1, sim):
        super(BesselCascade, self).__init__(pos, f, H0, n, R1, pole.bessel, "Bessel", sim)

        
if __name__ == "__main__":
    import sys, os, string

    def usage():
        progname = os.path.split(sys.argv[0])[-1]

        print("usage:")
        print("  %s [sim] stage f0 H0 Q R1 [filename]" % progname)
        print("  %s [sim] butterworth f0 H0 N R1 [filename]" % progname)
        print("  %s [sim] bessel f0 H0 N R1 [filename]" % progname)
        print()
        print("     Generates either a single stage or an N-stage Rauch/MFB low-pass filter")
        print("     with a specific response.  Calculates component values for a cut-off")
        print("     frequency (-3dB) of f0 Hz, gain H0.")
        print("     R1 is used to scale resistors, with 1k being a good starting point.")
        print("     If supplied, a KiCad schmatic is output to 'filename'.")
        print()
        print("     Adding an initial 'sim' argument outputs a KiCad schematic suitable")
        print("     for simulation with KiCad's built-in ngspice support.")
        print()
        print("SI suffixes:", " ".join(SUFFIXES))
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


    def add_sim_stuffs(schema, f0):
        '''Adds simulation bits: VSS, VDD supplies, a source, a 100k load, etc.'''

        v1      = VSource((1300, 3600), "15V", "dc 15", "1=+ 2=-", "DC", "V", "VDC", "")
        v2      = VSource((1300, 4200), "15V", "dc 15", "1=+ 2=-", "DC", "V", "VDC", "")
        conn1   = Connection((1300, 3900))
        gnd1    = Ground((1900, 4000))
        vdd     = Supply("VDD", (1300, 3300), VERTICAL)
        vss     = Supply("VSS", (1300, 4500), VERTICAL_FLIP)
        corner1 = Corner((1900,3900))

        schema.Add(v1, v2, conn1, gnd1, vdd, vss, corner1,
                   Wire.Connect(v1, vdd),
                   Wire.Connect(conn1, v1),
                   Wire.Connect(v2, conn1),
                   Wire.Connect(vss, v2),
                   Wire.Connect(conn1, corner1),
                   Wire.Connect(corner1, gnd1))

        # Set the source frequency to f0/2
        v3val = "dc=0 ampl=1 phase=0 f=%s td=0 theta=0 ac=1 ph=0" % sisuffix(f0/2.0)
        v3      = VSource((1300, 1600), "2Vpp AC", v3val, "1=+ 2=-", "SIN", "V", "VSIN", v3val)

        # Make the spice directive ('model') show
        v3.SetFlag(FIELD_SPICE_MODEL, FLAG_HIDDEN, '0')

        corner5 = Corner((1300, 1250))
        rs      = Resistor("0", (1600, 1250), HORIZONTAL)
        rs.SetRef("R100")
        vin     = GlobalLabel((1900, 1250), "VIN", "Output", 2)
        gnd2    = Ground((1300, 1900))

        schema.Add(v3, rs, vin, gnd2, corner5,
                   Wire.Connect(gnd2, v3),
                   Wire.Connect(v3, corner5),
                   Wire.Connect(corner5, rs),
                   Wire.Connect(rs, vin))

        vout    = GlobalLabel((1900, 4700), "VOUT", "Input")
        corner4 = Corner((2050, 4700))
        rl      = Resistor("100k", (2050, 4950), VERTICAL)
        rl.SetRef("R101")
        gnd4    = Ground((2050, 5200))

        schema.Add(vout, corner4, rl, gnd4,
                   Wire.Connect(rl, gnd4),
                   Wire.Connect(corner4, rl),
                   Wire.Connect(corner4, vout))

        # Set default AC analysis to have > 1 decade of freq span past f0
        fmax = mp.power(10.0, mp.floor(mp.log(f0, 10.0)) + 2)

        if False:
            # Requires running outside of KiCad
            analysis = '.ac dec 10 10 %s' % fmax
            analysis += mc_analysis(schema.PartsList())
            schema.Add(Text((3750, 7650), analysis))


    def mc_analysis(parts):
        '''Returns a monte-carlo analysis for a list of parts to vary
        This is currently incompatible with KiCad - ngspice will run it
        just fine, but there is no way to visualize the result in the
        KiCad simulator tool.  So this is a placeholder.  At some point
        appending this can be made a command line option (when KiCad can
        visualize it).'''
        
        result = '''
.control
    let mc_runs = 100
    let run = 1
    set scratch = $curplot
    define tolerance(val, pct) (val + val * (pct/100) * sunif(0))
    dowhile run <= mc_runs
'''
        for part in sorted(parts.keys()):
            val = parts[part]
            kind = part[:1]
            if not kind in ["R", "L", "C"]:
                continue

            # Default tolerance: C=5%, R=2%
            pct = 2
            if part[:1] == "C":
                pct = 5

            if val[-1] == "F":
                val = val[0:-1]

            result += "        alter %s = tolerance(%s, %s)\n" % (part, val, pct)

        result += '        ' + acanalysis

        result += '''
        set run = $&run
        set dt = $curplot
        setplot $scratch
        let vout{$run}={$dt}.v(vout)
        setplot $dt
        let run = run + 1
    end
.endc
'''
        return result.replace("\n", "\\n")

    def do_common(func, args, sim):
        filename = None
        if len(args) > 4:
            filename = args[4]

        circuit, n, f0 = func(sim, args)
        
        if not filename is None:
            schema = Schematic("A4")
            schema.Add(circuit)

            if sim:
                circuit.SetOrigin((1400, -950))
            else:
                height = schema.GetSize()[1]
                height = height - (height % 100) # Snap to mil grid

                circuit.SetOrigin((-2500, height - 2000))

            add_in_out(schema, circuit, n)

            if sim:
                add_sim_stuffs(schema, f0)

            with open(filename, "w") as file:
                file.write(schema.ToString())
                print("\nWrote schematic to %s" % filename)

        
    def do_stage(sim, args):
        f, H0, Q, R1 = map(si_val, args[:4])

        stage = Lowpass((2000, 2000), f, H0, Q, R1,
                        "MFB LPF: H=%s, Q=%s, f0=%s" % (H0, nsigdig(Q, NQIGITS), f),
                        True, sim)

        stage.Print("Q=%s" % nsigdig(Q, NQDIGITS))
        return stage, 1, f
        

    def do_butterworth(sim, args):
        f, H0, N, R1 = map(si_val, args[:4])

        if N > 32:
            print("N is too big; you probably didn't mean to do this")
            exit(1)

        return ButterworthCascade((2000, 2000), f, H0, N, R1, sim), N, f
        

    def do_bessel(si, args):
        f, H0, N, R1 = map(si_val, args[:4])

        if N > 32:
            print("N is too big; you probably didn't mean to do this")
            exit(1)

        return BesselCascade((2000, 2000), f, H0, N, R1, sim), N, f
        

    if len(sys.argv) < 2:
        usage()


    what = sys.argv[1]
    args = sys.argv[2:]

    sim = what == "sim"
    if sim:
        what = args[0]
        args = args[1:]

    if what == "stage" and len(args) >= 4:
        func = do_stage
    elif what == "butterworth" and len(args) >= 4:
        func = do_butterworth
    elif what == "bessel" and len(args) >= 4:
        func = do_bessel
    else:
        usage()

    do_common(func, args, sim)
