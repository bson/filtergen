import time

def flip(pos):
    return (pos[1], pos[0])

def addpos(pos1, pos2):
    return (pos1[0] + pos2[0], pos1[1] + pos2[1])

counter = 0
FIELD_REF = 0
FIELD_VALUE = 1
FIELD_FOOTPRINT = 2
FIELD_DOC = 3
HORIZONTAL = [0, 1, 1, 0]
VERTICAL   = [1, 0, 0, -1]
VERTICAL_FLIP = [-1, 0, 0, 1]
FLAG_HIDDEN = 3

FIELD_SPICE_PRIMITIVE = 4
FIELD_SPICE_MODEL = 5
FIELD_SPICE_NETLIST = 6
FIELD_SPICE_LIBFILE = 7
FIELD_SPICE_NODES = 8


class Relocatable(object):
    def __init__(self, pos):
        self.pos    = pos
        self.origin = (0,0)
        
    def Position(self, offset = (0,0)):
        return (self.pos[0] + offset[0], self.pos[1] + offset[1])

    def SheetPosition(self):
        return self.Relocate(self.pos)

    def SetOrigin(self, pos):
        self.origin = pos

    def GetOrigin(self):
        return self.origin

    def Relocate(self, pos):
        return (self.origin[0] + pos[0], self.origin[1] + pos[1])

    def GetPin1Pos(self):
        return self.Position()

    def GetPin2Pos(self):
        return self.Position()

    def ToString(self):
        return ""


class Component(Relocatable):
    def __init__(self, ref, comp, pos, orientation):
        super(Component, self).__init__(pos)

        global counter
        counter = counter + 1
        self.reference   = ref
        self.component   = comp
        self.uid         = "%08X" % (time.time()+counter)
        self.fields      = { 0: self.newField(ref, (0, 0), orientation) }
        self.orientation = orientation

    def newField(self, value, pos, orient):
        if orient == VERTICAL or orient == VERTICAL_FLIP:
            rot = 'H'
        else:
            rot = 'V'
        return { 'value': value,
                 'rot': rot,
                 'pos': pos,
                 'flags': [0,0,0,0],
                 'size': 50,
                 'align': 'C',
                 'style': 'CNN',
                 'name': None }
    
    def ToString(self):
        pos = self.SheetPosition()

        s = "$Comp\nL %s %s\nU 1 1 %s\nP %s\n" % (self.component,
                                                     self.reference,
                                                     self.uid,
                                                     "%s %s" % pos)

        for n in xrange(0,4):
            if not n in self.fields:
                self.fields[n] = self.newField("", (0,0), self.orientation)

        posx, posy = pos

        for n in sorted(self.fields.keys()):
            f = self.fields[n]
            s += "F %s \"%s\" %s %s %s %s %s %s %s" % (n, f['value'], f['rot'],
                                                       f['pos'][0] + posx,
                                                       f['pos'][1] + posy,
                                                       f['size'],
                                                       "%s%s%s%s" % tuple(f['flags']),
                                                       f['align'], f['style'])
            if f['name'] is not None:
                s += ' "' + f['name'] + '"'
            s += "\n"

        s += "\t1   %s %s\n" % pos
        s += "\t%s   %s   %s   %s\n$EndComp\n" % tuple(self.orientation)
        return s

    def SetValue(self, value, pos = None):
        '''Set component value.  If pos omitted, merely update the value string'''
        if pos is None:
            self.fields[FIELD_VALUE]['value'] = value
        else:
            self.fields[FIELD_VALUE] = self.newField(value, pos, self.orientation)

    def SetFlag(self, field, flag, flagValue):
        self.fields[field]['flags'][flag] = flagValue

    def SetFootprint(self, name):
        self.fields[FIELD_FOOTPRINT] = self.newField(value, self.Position(), HORIZONTAL)

    def PlaceField(self, field, offset):
        self.fields[field]['pos'] = offset

    def SetStyle(self, field, style = 'CNN'):
        self.fields[field]['style'] = style

    def SetAlign(self, field, align = 'C'):
        self.fields[field]['align'] = align

    def SetDoc(self, url):
        self.fields[FIELD_DOC] = self.newField(value, self.Position(), HORIZONTAL)

    def SetUserField(self, field, name, value):
        '''Sets a user field's name and value'''
        self.fields[field] = self.newField(value, self.Position(), VERTICAL)
        self.fields[field]['name'] = name
        self.SetFlag(field, FLAG_HIDDEN, '1')
        
class Passive(Component):
    SIZE = 100

    def __init__(self, ref, comp, value, pos, orientation, spice_prim):
        super(Passive, self).__init__(ref, comp, pos, orientation)
        self.SetValue(value,
                      (self.orientation[0] * 100,
                       self.orientation[1] * 100))

        self.SetUserField(FIELD_SPICE_PRIMITIVE, "Spice_Primitive", spice_prim)
        self.SetUserField(FIELD_SPICE_NETLIST, "Spice_Netlist_Enabled", "Y")

                      
    def GetPin1Pos(self):
        posx, posy = self.Position()
        return (posx - (self.orientation[1] * type(self).SIZE),
                posy - (self.orientation[0] * type(self).SIZE))

    def GetPin2Pos(self):
        posx, posy = self.Position()
        return (posx + (self.orientation[1] * type(self).SIZE),
                posy + (self.orientation[0] * type(self).SIZE))

    def PlaceRefValue(self, width):
        if self.orientation == HORIZONTAL:
            self.PlaceField(FIELD_REF, (-125 - width, 0))
            self.PlaceField(FIELD_VALUE, (-50 - width, 0))
            self.SetStyle(FIELD_REF, 'CNN')
            self.SetStyle(FIELD_VALUE, 'CNN')
            self.SetAlign(FIELD_REF, 'C')
            self.SetAlign(FIELD_VALUE, 'C')
        else:
            self.PlaceField(FIELD_REF, (15 + width, 40))
            self.PlaceField(FIELD_VALUE, (15 + width, -40))
            self.SetStyle(FIELD_REF, 'CNN')
            self.SetStyle(FIELD_VALUE, 'CNN')
            self.SetAlign(FIELD_REF, 'L')
            self.SetAlign(FIELD_VALUE, 'L')


class Resistor(Passive):
    def __init__(self, value, pos, orientation):
        super(Resistor, self).__init__("R?", "device:R_Small", value, pos, orientation, "R")
        self.PlaceRefValue(30)

class Capacitor(Passive):
    def __init__(self, value, pos, orientation):
        super(Capacitor, self).__init__("C?", "device:C_Small", value, pos, orientation,
                                        "C")
        self.PlaceRefValue(60)

class Inductor(Passive):
    def __init__(self, value, pos, orientation):
        super(Inductor, self).__init__("L?", "device:L_Small", value, pos, orientation, "L")
        self.PlaceRefValue(0)

class LED(Passive):
    def __init__(self, value, pos, orientation):
        super(LED, self).__init__("D?", "device:LED_Small", value, pos, orientation, "D")
        self.PlaceRefValue(50)

class Diode(Passive):
    def __init__(self, value, pos, orientation):
        super(Diode, self).__init__("D?", "device:D_Small", value, pos, orientation, "D")
        self.PlaceRefValue(50)

class OpAmp(Component):
    '''Pin1 is the negative input, Pin2 is the output.  GetInP() returns an Anchor for In+.'''
    def __init__(self, comp, pos, orientation, sim):
        if sim:
            super(OpAmp, self).__init__("X?", "linear:LM321", pos, orientation)
        else:
            super(OpAmp, self).__init__("U?", "linear:" + comp, pos, orientation)

        self.SetUserField(FIELD_SPICE_PRIMITIVE, "Spice_Primitive", "X")
        self.SetUserField(FIELD_SPICE_MODEL, "Spice_Model", comp)
        self.SetUserField(FIELD_SPICE_NODES, "Spice_Node_Sequence", "1 3 5 2 4")
        self.SetUserField(FIELD_SPICE_NETLIST, "Spice_Netlist_Enabled", "Y")
        self.SetValue(comp, (75, 200))
    
    def GetInP(self):
        return Anchor(self.Position((-300, -100)))

    def GetPin1Pos(self):
        return self.Position((-300, 100))

    def GetPin2Pos(self):
        return self.Position((300, 0))

    def GetPwrP(self):
        return Anchor(self.Position((-100, -300)))

    def GetPwrM(self):
        return Anchor(self.Position((-100, 300)))

        
class Power(Component):
    def __init__(self, node, pos, orientation):
        super(Power, self).__init__("#PWR?", "power:" + node, pos, orientation)

class Ground(Power):
    def __init__(self, pos):
        super(Ground, self).__init__("GND", pos, VERTICAL)
        self.SetValue("GND", (0, -150))
        self.SetFlag(FIELD_REF, FLAG_HIDDEN, '1')

class Supply(Power):
    def __init__(self, node, pos, orientation):
        super(Supply, self).__init__(node, pos, orientation)
        self.SetValue(node, (0, 150))
        self.SetFlag(FIELD_REF, FLAG_HIDDEN, '1')

class VSource(Component):
    '''A voltage source, mainly for simulation purposes.'''

    def __init__(self, pos, value, sim_value):
        '''Value is the displayed value; sim_value is the spice config'''

        super(VSource, self).__init__("V?", "pspice:VSOURCE", pos, VERTICAL)
        self.SetUserField(FIELD_SPICE_PRIMITIVE, "Spice_Primitive", "V")
        self.SetUserField(FIELD_SPICE_MODEL, "Spice_Model", sim_value)
        self.SetUserField(FIELD_SPICE_NETLIST, "Spice_Netlist_Enabled", "Y")
        self.SetValue(value, (75, 200))

        self.PlaceField(FIELD_REF, (250, 50))
        self.PlaceField(FIELD_VALUE, (250, -50))
        self.PlaceField(FIELD_SPICE_MODEL, (250, -150))
        self.SetStyle(FIELD_REF, 'CNN')
        self.SetStyle(FIELD_VALUE, 'CNN')
        self.SetStyle(FIELD_SPICE_MODEL, 'CNN')
        self.SetAlign(FIELD_REF, 'L')
        self.SetAlign(FIELD_VALUE, 'L')
        self.SetAlign(FIELD_SPICE_MODEL, 'L')

    def GetPin1Pos(self):
        return self.Position((0, 300))

    def GetPin2Pos(self):
        return self.Position((0, -300))


class Wire(Relocatable):
    def __init__(self, start, end, kind = 'Wire'):
        super(Wire, self).__init__(start)
        
        self.end    = end
        self.origin = (0,0)
        self.kind   = kind

    @staticmethod
    def Connect(c1, c2):
        return Wire(c1.GetPin2Pos(), c2.GetPin1Pos())

    def GetPin2Pos(self):
        return self.end

    def ToString(self):
        s = "Wire %s Line\n\t" % self.kind
        s += "%s %s" % self.SheetPosition()
        s += " %s %s\n" % self.Relocate(self.end)
        return s

class Line(Wire):
    def __init__(self, start, end):
        super(Line, self).__init__(start, end, 'Notes')

class Box(Relocatable):
    def __init__(self, topleft, botright):
        super(Box, self).__init__(topleft)
        box = SubCircuit((0,0))
        topright = (botright[0], topleft[1])
        botleft  = (topleft[0], botright[1])

        box.Add(Line(topleft, topright),
                Line(topright, botright),
                Line(botright, botleft),
                Line(botleft, topleft))

        self.box = box

    def ToString(self):
        self.box.SetOrigin(self.origin)
        return self.box.ToString()

class Connection(Relocatable):
    def __init__(self, pos):
        super(Connection, self).__init__(pos)

    def ToString(self):
        return "Connection ~ %s %s\n" % self.SheetPosition()

class Corner(Relocatable):
    def __init__(self, pos):
        super(Corner, self).__init__(pos)

class Anchor(Relocatable):
    def __init__(self, pos):
        super(Anchor, self).__init__(pos)

class GlobalLabel(Relocatable):
    def __init__(self, pos, text, shape = 'Input', orientation = 0):
        super(GlobalLabel, self).__init__(pos)
        self.text = text
        self.shape = shape
        self.orient = orientation

    def ToString(self):
        pos = self.SheetPosition()
        return "Text GLabel %s %s %s 50 %s ~ 0\n%s\n" % (pos[0], pos[1],
                                                         self.orient,
                                                         self.shape, self.text)
class Label(Relocatable):
    def __init__(self, pos, text):
        super(Label, self).__init__(pos)
        self.text = text
        self.shape = shape

    def ToString(self):
        pos = self.SheetPosition()
        return "Text Label %s %s 0 50 ~ 0\n%s\n" % (pos[0], pos[1], self.text)

class Text(Relocatable):
    def __init__(self, pos, text):
        super(Text, self).__init__(pos)
        self.text = text

    def ToString(self):
        pos = self.SheetPosition()
        return "Text Notes %s %s 0 50 ~ 0\n%s\n" % (pos[0], pos[1], self.text)

class Schematic(object):
    # Ax - metric sizes
    # Archx - ANSI/ASME Y14.1 technical drafting sizes
    SIZE_MIL = { "A4": (8268, 11693),
                 "A3": (11692, 16535),
                 "A2": (16535, 23385),
                 "A1": (23385, 33110),
                 "A0": (33110, 46811),
                 "US-Letter": (8500, 11000),
                 "US-Legal": (8500, 14000),
                 "US-Ledger": (11000, 17000),
                 "ArchA": (9000, 12000),
                 "ArchB": (12000, 18000),
                 "ArchC": (18000, 24000),
                 "ArchD": (24000, 36000),
                 "ArchE1": (30000, 42000),
                 "ArchE": (36000, 48000) }

    HORIZONTAL = True
    VERTICAL = False

    def __init__(self, size_name, orientation = True):
        self.size_name = size_name
        self.size = type(self).SIZE_MIL[size_name]
        if orientation == type(self).HORIZONTAL:
            self.size = flip(self.size)

        self.items = [ ]

    def GetSize(self):
        return self.size

    def Add(self, *args):
        self.items.extend(args)

    def ToString(self):
        s = "EESchema Schematic File Version 4\nEELAYER 26 0\nEELAYER END\n$Descr %s" % \
                     self.size_name
        s += " %s %s\n" % self.size
        s += "encoding utf-8\nSheet 1 1\nTitle \"\"\nDate \"\"\nRev \"\"\nComp \"\"\nComment1 \"\"\nComment2 \"\"\nComment3 \"\"\nComment4 \"\"\n$EndDescr\n"

        for item in self.items:
            s += item.ToString()

        s += "$EndSCHEMATC\n"

        return s

class SubCircuit(Relocatable):
    def __init__(self, pos):
        super(SubCircuit, self).__init__(pos)

        self.items = [ ]

    def Add(self, *args):
        self.items.extend(args)

    def ToString(self):
        pos = self.SheetPosition()

        s = ""
        for item in self.items:
            item.SetOrigin(pos)
            s += item.ToString()

        return s
