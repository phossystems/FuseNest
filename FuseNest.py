#Author-Nico Schlueter
#Description-SVG nest for Fusion360

import adsk.core, adsk.fusion, adsk.cam, traceback
import math
import re
from xml.dom import minidom
import time, threading

# Global set of event handlers to keep them referenced for the duration of the command
_handlers = []

COMMAND_ID = "fuseNest"
COMMAND_NAME = "FuseNest 2D Nesting"
COMMAND_TOOLTIP = "2D nest/pack parts on a sheet"
 
TOOLBAR_PANELS = ["SolidModifyPanel"]

SVG_UNIT_FACTOR = 100

# Initial persistence Dict
pers = {
    "VISheetWidth": 50,
    "VISheetHeight": 30,
    "VISpacing": 0,
    "VISheetOffsetX": 0,
    "VISheetOffsetY": 5,
    "ISRotations": 4
}

transform_data = None

# Fires when the CommandDefinition gets executed.
# Responsible for adding commandInputs to the command &
# registering the other command handlers.
class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global transform_data 
            global pers
            transform_data = None

            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)

            # Registers the CommandDestryHandler
            onExecute = CommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)
            
            # Registers the CommandInputChangedHandler          
            onInputChanged = CommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)     

                
            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs
            
            siBodies = inputs.addSelectionInput("SIBodies", "Bodies", "Select Bodies")
            siBodies.addSelectionFilter("SolidBodies")
            siBodies.setSelectionLimits(0, 0)
            siBodies.tooltip = "Select parts to be placed"

            viSheetWidth = inputs.addValueInput("VISheetWidth", "Sheet Width", "mm", adsk.core.ValueInput.createByReal(pers["VISheetWidth"]))
            viSheetWidth.tooltip = "Width of the sheet the parts will be placed on"

            viSheetHeight = inputs.addValueInput("VISheetHeight", "Sheet Height", "mm", adsk.core.ValueInput.createByReal(pers["VISheetHeight"]))
            viSheetHeight.tooltip = "Height of the sheet the parts will be placed on"

            viSheetOffsetX = inputs.addValueInput("VISheetOffsetX", "Sheet Offset X", "mm", adsk.core.ValueInput.createByReal(pers["VISheetOffsetX"]))
            viSheetOffsetX.tooltip = "Offset between multiple sheets in x"

            viSheetOffsetY = inputs.addValueInput("VISheetOffsetY", "Sheet Offset Y", "mm", adsk.core.ValueInput.createByReal(pers["VISheetOffsetY"]))
            viSheetOffsetY.tooltip = "Offset between multiple sheets in y"

            viSpacing = inputs.addValueInput("VISpacing", "Spacing", "mm", adsk.core.ValueInput.createByReal(pers["VISpacing"]))
            viSpacing.tooltip = "Spacing between parts"
            viSpacing.tooltipDescription = "May not be exact, can be off by ±0.5mm"

            isRotations = inputs.addIntegerSpinnerCommandInput("ISRotations", "Rotations", 2, 999999, 1, pers["ISRotations"])
            isRotations.tooltip = "Number of possible rotations"
            isRotations.tooltipDescription ="How many rotations to try.\nTrying more rotations will take longer to find a good result, but is necessary for some shapes\n\nRecommendations:\n2    -  Perfectly circular, square or hexagonal\n4    -  Rectangular\n8+ -  Odd/Organic shapes or mixed"

            bvNest = inputs.addBoolValueInput("BVNest", "    Start Nesting    ", False)
            bvNest.isFullWidth = True
            bvNest.tooltip = "Start nesting process"

            root = adsk.core.Application.get().activeProduct.rootComponent
            for i in root.bRepBodies:
                siBodies.addSelection(i)

            for o in root.occurrences:
                for i in o.bRepBodies:
                    siBodies.addSelection(i)

           
        except:
            print(traceback.format_exc())


#Fires when the User executes the Command
#Responsible for doing the changes to the document
class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global transform_data
            if(transform_data):
                selections = []

                for i in range(args.command.commandInputs.itemById("SIBodies").selectionCount):
                    selections.append(args.command.commandInputs.itemById("SIBodies").selection(i).entity)

                first_move = None
                last_move = None

                root = adsk.core.Application.get().activeProduct.rootComponent
                des = adsk.core.Application.get().activeDocument.design

                offset_x = 0
                offset_y = 0
                
                if(args.command.commandInputs.itemById("VISheetOffsetX").value > 0):
                    offset_x = args.command.commandInputs.itemById("VISheetWidth").value + args.command.commandInputs.itemById("VISheetOffsetX").value
                elif(args.command.commandInputs.itemById("VISheetOffsetX").value < 0):
                    offset_x = -args.command.commandInputs.itemById("VISheetWidth").value + args.command.commandInputs.itemById("VISheetOffsetX").value

                if(args.command.commandInputs.itemById("VISheetOffsetY").value > 0):
                    offset_y = args.command.commandInputs.itemById("VISheetHeight").value + args.command.commandInputs.itemById("VISheetOffsetY").value
                elif(args.command.commandInputs.itemById("VISheetOffsetY").value < 0):
                    offset_y = -args.command.commandInputs.itemById("VISheetHeight").value + args.command.commandInputs.itemById("VISheetOffsetY").value


                
                for i, t in transform_data:
                    mat1 = adsk.core.Matrix3D.create()
                    mat1.translation = adsk.core.Vector3D.create(t[0] +  offset_x * t[3], -t[1] - offset_y * t[3], 0)

                    mat2 = adsk.core.Matrix3D.create()
                    mat2.setToRotation(
                        math.radians(-t[2]),
                        adsk.core.Vector3D.create(0,0,1),
                        adsk.core.Point3D.create(0,0,0)
                    )

                    mat2.transformBy(mat1)

                    if(selections[i].parentComponent == root):
                        oc = adsk.core.ObjectCollection.create()
                        oc.add(selections[i])

                        move_input = root.features.moveFeatures.createInput(oc, mat2)
                        
                        if(first_move is None):
                            first_move = root.features.moveFeatures.add(move_input)
                            last_move = first_move
                        else:
                            last_move = root.features.moveFeatures.add(move_input)
                    else:
                        trans = selections[i].assemblyContext.transform
                        trans.transformBy(mat2)
                        selections[i].assemblyContext.transform = trans
                if(des.designType and des.snapshots.hasPendingSnapshot):
                    des.snapshots.add()
                    if(first_move):
                        des.timeline.timelineGroups.add(first_move.timelineObject.index, last_move.timelineObject.index+1)
                elif(first_move and not( first_move == last_move) and des.designType):
                    des.timeline.timelineGroups.add(first_move.timelineObject.index, last_move.timelineObject.index)
        except:
            print(traceback.format_exc())


# Fires when CommandInputs are changed
# Responsible for dynamically updating other Command Inputs
class CommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            if(args.input.id == "BVNest"):

                global pers

                pers["VISheetWidth"] = args.inputs.itemById("VISheetWidth").value
                pers["VISheetHeight"] = args.inputs.itemById("VISheetHeight").value
                pers["VISpacing"] = args.inputs.itemById("VISpacing").value
                pers["ISRotations"] = args.inputs.itemById("ISRotations").value
                pers["VISheetOffsetX"] = args.inputs.itemById("VISheetOffsetX").value
                pers["VISheetOffsetY"] = args.inputs.itemById("VISheetOffsetY").value

                # If there is already a palette, delete it
                # This is mainly for debugging purposes
                ui = adsk.core.Application.get().userInterface
                palette = ui.palettes.itemById('paletteSVGNest')
                if palette:
                    palette.deleteMe()

                global SVG_UNIT_FACTOR
            
                root = adsk.core.Application.get().activeProduct.rootComponent
            

                # Getting selections now, as creating sketches clears em
                selections = []                
                for i in range(args.inputs.itemById("SIBodies").selectionCount):
                    selections.append(args.inputs.itemById("SIBodies").selection(i).entity)

                paths = []

                for s in selections:
                    sketch = root.sketches.add(root.xYConstructionPlane)
                    sketch.project(s)
                    paths.append(sketchToSVGPaths(sketch))
                    sketch.deleteMe()

                svg = buildSVGFromPaths(paths, args.inputs.itemById("VISheetWidth").value, args.inputs.itemById("VISheetHeight").value)

                dataToSend = "{};{};{};{};{}".format(
                    svg,
                    args.inputs.itemById("VISpacing").value * SVG_UNIT_FACTOR,
                    args.inputs.itemById("ISRotations").value,
                    True,
                    True     
                )

                # Re-selects all components, as they get lost during the previous steps
                for s in selections:
                    args.inputs.itemById("SIBodies").addSelection(s)


                palette = ui.palettes.add('paletteSVGNest', '2D Nest', 'SVGnest/index.html', True, True, True, 1500, 1000, True)

                # Dock the palette to the right side of Fusion window.
                palette.dockingState = adsk.core.PaletteDockingStates.PaletteDockStateTop
    
                # Add handler to CloseEvent of the palette.
                onClosed = PaletteCloseEventHandler()
                palette.closed.add(onClosed)
                _handlers.append(onClosed)  

                # Add handler to HTMLEvent of the palette.
                onHTMLEvent = PaletteHTMLEventHandler()
                palette.incomingFromHTML.add(onHTMLEvent)   
                _handlers.append(onHTMLEvent)

                # Sends data to palette after it had time to load
                threading.Timer(4, sendDataToPalette, [palette, dataToSend]).start()

        except:
            print(traceback.format_exc())
          

# Fires when Palette is closed
# Responsible for deleting it
class PaletteCloseEventHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            ui = adsk.core.Application.get().userInterface
            palette = ui.palettes.itemById('paletteSVGNest')
            
            #if palette:
            #    palette.deleteMe()
        except:
            print(traceback.format_exc())


# Fires when an HTML event is sent from the Palette
# Responsive for parsing that data              
class PaletteHTMLEventHandler(adsk.core.HTMLEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            if(args.action == "exportSVG"):
                global transform_data
                transform_data =  getTransformsFromSVG(args.data)

                ui = adsk.core.Application.get().userInterface
                palette = ui.palettes.itemById('paletteSVGNest')
                if palette:
                    palette.deleteMe()

        except:
            print(traceback.format_exc())


def sendDataToPalette(palette, data):
    """Sends data string to pallet

    Args:
        palette: (Palette) Palette to send data to
        data: (String) Data string to send to pallete
    """
    if palette:
        palette.sendInfoToHTML("importSVG", data)


def buildSVGFromPaths(paths, width=50, height=25):
    """Constructs a full svg fle from paths

    Args:
        paths: (String[][]) SVG path data
        width: (float) Width ouf bounding rectangle
        height: (float) Height of bounding rectangle

    Returns:
        [string]: full svg

    """
    global SVG_UNIT_FACTOR

    rtn = ""


    rtn += r"<svg version='1.1' xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {0} {1}' width='{0}px' height='{1}px'> ".format(width*SVG_UNIT_FACTOR, height*SVG_UNIT_FACTOR)

    rtn += r"<rect width='{}' height='{}' stroke='black' stroke-width='2' fill-opacity='0'/> ".format(width*SVG_UNIT_FACTOR, height*SVG_UNIT_FACTOR)

    for i, p in enumerate(paths):
        for j in p:
            rtn += r"<path d='{}' id='{}' stroke='black' fill='green' stroke-width='2' fill-opacity='0.5'/> ".format(j, i)

    rtn += r"</svg>"

    return rtn


def getTransformsFromSVG(svg):
    """Imports SVG result from svgnest and extracts transform data

    Args:
        svg: (String) SVG data

    Returns:
        [zip]: zip of index and transform data (x, y, r)
    """

    global SVG_UNIT_FACTOR

    # Wraps svg data into single root node
    svg = "<g>{}</g>".format(svg)

    dom = minidom.parseString(svg)

    #print(svg)

    ids = []
    transforms = []

    p = re.compile(r'[\(\s]-?\d*\.{0,1}\d+')

    for sheetNumber, s in enumerate(dom.firstChild.childNodes):
        for e in s.getElementsByTagName('path'):
            if not(int(e.getAttribute('id')) in ids):
                ids.append(int(e.getAttribute('id')))
                
                # Gets the transform atributes as string
                transformTag = (e.parentNode.getAttribute('transform'))

                # Converts string to list of floats via regex
                # Adds sheet number to the end
                transforms.append([float(i[1:]) for i in p.findall(transformTag)] + [sheetNumber] )
            
    # X, Y, rotation, sheet number
    transformsScaled = [ [t[0]/SVG_UNIT_FACTOR, t[1]/SVG_UNIT_FACTOR, t[2], t[3]] for t in transforms]

    return zip(ids, transformsScaled)
    

def sketchToSVGPaths(sketch):
    """Converts a Sketch into a SVG Path date

    Args:
        sketch: (Sketch) Sketch to convert

    Returns:
        [str]: Array of SVG paths
    """

    rtn = ""

    sortedProfiles = sorted(sketch.profiles, key=lambda x: len(x.profileLoops), reverse=True)

    """for p in sketch.profiles:
        for pl in p.profileLoops:

            if(pl.isOuter):
                rtn.append(loopToSVGPath(pl))
                break
    """


    for pl in sortedProfiles[0].profileLoops:
        # Outer should be clockwise
        # Inner should be counterclockwise
        if(pl.isOuter != isLoopClockwise(pl)):
            rtn += loopToSVGPath(pl, True)
        else:
            rtn += loopToSVGPath(pl, False)

    return [rtn]


def loopToSVGPath(loop, reverse = False):
    """Converts a ProfileLoop into a SVG Path date

    Args:
        loop: (ProfileLoop) Loop to convert
        reverse: (Bool) Invert direction

    Returns:
        str: SVG Path data
    """
    
    global SVG_UNIT_FACTOR

    rtn = ""

    profileCurves = [i for i in loop.profileCurves]

    if(reverse):
        profileCurves.reverse()

    flip = getWhatCurvesToFlip(profileCurves)

    if(reverse and len(flip) == 1):
        flip = [not(i) for i in flip]


    for c, f in zip(profileCurves, flip):
        rtn += curveToPathSegment(
            c,
            1/SVG_UNIT_FACTOR,
            f,
            not rtn
        )

    return rtn


def curveToPathSegment(curve, scale=1, invert=False, moveTo=False):
    """Converts a ProfileCurve into a SVG Path date segment

    Args:
        curve: (ProfileCurve) The curve object to be converted
        scale: (float) How many units are per SVG unit
        invert: (bool) Swaps curve's startPoint and endPoint
        moveTo: (bool) Moves to the startPoint before conversion

    Returns:
        str: Segment of SVG Path data.

    """

    rtn = ""

    if(curve.geometry.objectType == "adsk::core::Line3D"):
        if(not invert):
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    curve.geometry.startPoint.x / scale,
                    -curve.geometry.startPoint.y / scale
                )

            rtn += "L{0:.6f} {1:.2f} ".format(
                curve.geometry.endPoint.x / scale,
                -curve.geometry.endPoint.y / scale)

        else:
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    curve.geometry.endPoint.x / scale,
                    -curve.geometry.endPoint.y / scale
                )

            rtn += "L{0:.6f} {1:.2f} ".format(
                curve.geometry.startPoint.x / scale,
                -curve.geometry.startPoint.y / scale)
    
    elif(curve.geometry.objectType == "adsk::core::Arc3D"):
        if(not invert):
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    curve.geometry.startPoint.x / scale,
                    -curve.geometry.startPoint.y / scale
                )

            # rx ry rot large_af sweep_af x y
            rtn += "A {0:.6f} {0:.6f} 0 {1:.0f} {2:.0f} {3:.6f} {4:.6f}".format(
                curve.geometry.radius / scale,
                curve.geometry.endAngle-curve.geometry.startAngle > math.pi,
                0,
                curve.geometry.endPoint.x / scale,
                -curve.geometry.endPoint.y / scale
            )
        else:
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    curve.geometry.endPoint.x / scale,
                    -curve.geometry.endPoint.y / scale
                )

            # rx ry rot large_af sweep_af x y
            rtn += "A {0:.6f} {0:.6f} 0 {1:.0f} {2:.0f} {3:.6f} {4:.6f}".format(
                curve.geometry.radius / scale,
                curve.geometry.endAngle-curve.geometry.startAngle > math.pi,
                1,
                curve.geometry.startPoint.x / scale,
                -curve.geometry.startPoint.y / scale
            )
    
    elif(curve.geometry.objectType == "adsk::core::Circle3D"):
        sp = curve.geometry.center.copy()
        sp.translateBy(adsk.core.Vector3D.create(curve.geometry.radius, 0, 0))

        ep = curve.geometry.center.copy()
        ep.translateBy(adsk.core.Vector3D.create(0, curve.geometry.radius, 0))

        if(not invert):

            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    sp.x / scale,
                    -sp.y / scale
                )

            rtn += "A {0:.6f} {0:.6f} 0 {1:.0f} {2:.0f} {3:.6f} {4:.6f}".format(
                curve.geometry.radius / scale,
                1,
                1,
                ep.x / scale,
                -ep.y / scale
            )

            rtn += "A {0:.6f} {0:.6f} 0 {1:.0f} {2:.0f} {3:.6f} {4:.6f}".format(
                curve.geometry.radius / scale,
                0,
                1,
                sp.x / scale,
                -sp.y / scale
            )

        else:
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    sp.x / scale,
                    -sp.y / scale
                )

            rtn += "A {0:.6f} {0:.6f} 0 {1:.0f} {2:.0f} {3:.6f} {4:.6f}".format(
                curve.geometry.radius / scale,
                0,
                0,
                ep.x / scale,
                -ep.y / scale
            )

            rtn += "A {0:.6f} {0:.6f} 0 {1:.0f} {2:.0f} {3:.6f} {4:.6f}".format(
                curve.geometry.radius / scale,
                1,
                0,
                sp.x / scale,
                -sp.y / scale
            )

    
    elif(curve.geometry.objectType == "adsk::core::Ellipse3D"):
        sp = curve.geometry.center.copy()
        la = curve.geometry.majorAxis.copy()
        la.normalize()
        la.scaleBy(curve.geometry.majorRadius)
        sp.translateBy(la)

        ep = curve.geometry.center.copy()
        sa = adsk.core.Vector3D.crossProduct(curve.geometry.majorAxis, adsk.core.Vector3D.create(0,0,1))
        sa.normalize()
        sa.scaleBy(curve.geometry.minorRadius)
        ep.translateBy(sa)
        
        angle = -math.degrees(math.atan2(la.y, la.x))

        if(not invert):
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    sp.x / scale,
                    -sp.y / scale
                )

            # rx ry rot large_af sweep_af x y
            rtn += "A {0:.6f} {1:.6f} {2:.6f} {3:.0f} {4:.0f} {5:.6f} {6:.6f}".format(
                curve.geometry.majorRadius / scale,
                curve.geometry.minorRadius / scale,
                angle,
                1,
                1,
                ep.x / scale,
                -ep.y / scale
            )

            rtn += "A {0:.6f} {1:.6f} {2:.6f} {3:.0f} {4:.0f} {5:.6f} {6:.6f}".format(
                curve.geometry.majorRadius / scale,
                curve.geometry.minorRadius / scale,
                angle,
                0,
                1,
                sp.x / scale,
                -sp.y / scale
            )
        else:
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    sp.x / scale,
                    -sp.y / scale
                )

            # rx ry rot large_af sweep_af x y
            rtn += "A {0:.6f} {1:.6f} {2:.6f} {3:.0f} {4:.0f} {5:.6f} {6:.6f}".format(
                curve.geometry.majorRadius / scale,
                curve.geometry.minorRadius / scale,
                angle,
                0,
                0,
                ep.x / scale,
                -ep.y / scale
            )

            rtn += "A {0:.6f} {1:.6f} {2:.6f} {3:.0f} {4:.0f} {5:.6f} {6:.6f}".format(
                curve.geometry.majorRadius / scale,
                curve.geometry.minorRadius / scale,
                angle,
                1,
                0,
                sp.x / scale,
                -sp.y / scale
            )


    elif(curve.geometry.objectType == "adsk::core::EllipticalArc3D"):
        angle = -math.degrees(math.atan2(curve.geometry.majorAxis.y, curve.geometry.majorAxis.x))

        _, sp, ep = curve.geometry.evaluator.getEndPoints()

        if(not invert):
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    sp.x / scale,
                    -sp.y / scale
                )

            # rx ry rot large_af sweep_af x y
            rtn += "A {0:.6f} {1:.6f} {2:.6f} {3:.0f} {4:.0f} {5:.6f} {6:.6f}".format(
                curve.geometry.majorRadius / scale,
                curve.geometry.minorRadius / scale,
                angle,
                curve.geometry.endAngle-curve.geometry.startAngle > math.pi,
                0,
                ep.x / scale,
                -ep.y / scale
            )
        else:
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    ep.endPoint.x / scale,
                    -ep.y / scale
                )

            # rx ry rot large_af sweep_af x y
            rtn += "A {0:.6f} {1:.6f} {2:.6f} {3:.0f} {4:.0f} {5:.6f} {6:.6f}".format(
                curve.geometry.majorRadius / scale,
                curve.geometry.minorRadius / scale,
                angle,
                curve.geometry.endAngle-curve.geometry.startAngle > math.pi,
                1,
                sp.x / scale,
                -sp.y / scale
            )

    elif(curve.geometry.objectType == "adsk::core::NurbsCurve3D"):
        # Aproximates nurbs with straight line segments

        ev = curve.geometry.evaluator
        _, sp, ep = ev.getParameterExtents()

        # List of segments, initially subdivided into two segments
        s = [sp, lerp(sp, ep, 0.5), ep]
        
        # Maxiumum angle two neighboring segments can have 
        maxAngle = math.radians(10)

        # Minimum length of segment
        minLength = 0.05

        i = 0
        while(i < len(s)-1):
            _, t = ev.getTangents(s)
            _, p = ev.getPointsAtParameters(s)

            # If the angle to the next segment is small enough, move one
            if( t[i].angleTo( t[i+1]) < maxAngle or p[i].distanceTo(p[i+1]) < minLength):
                i += 1
            # Otherwise subdivide the next segment into two
            else:
                s.insert(i+1, lerp( s[i], s[i+1], 0.5))

        if(not invert):
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    p[0].x / scale,
                    -p[0].y / scale
                )
            for i in p[1:]:
                rtn += "L{0:.6f} {1:.2f} ".format(
                    i.x / scale,
                    -i.y / scale
                )
        else:
            if(moveTo):
                rtn += "M{0:.6f} {1:.6f} ".format(
                    p[-1].x / scale,
                    -p[-1].y / scale
                )
            for i in reversed(p[:-1]):
                rtn += "L{0:.6f} {1:.2f} ".format(
                    i.x / scale,
                    -i.y / scale
                )

    else:
        print("Warning: Unsupported curve type, could not be converted: {}".format(curve.geometryType))

    return rtn


def isLoopClockwise(loop):
    """Determins if a ProfileLoop is clockwise

    Args:
        loop: (ProfileLoop) The loop to check

    Returns:
        bool: True if clockwise.
    """

    # If if it has only one segment it is clockwise by definition
    if(len(loop.profileCurves) == 1):
        return False;

    # https://stackoverflow.com/questions/1165647/how-to-determine-if-a-list-of-polygon-points-are-in-clockwise-order
    res = 0

    sp = [getStartPoint(i.geometry) for i in loop.profileCurves]
    ep = [getEndPoint(i.geometry) for i in loop.profileCurves]
    

    # range(len()) one of the deally sins of python
    for s, e in zip(sp, ep):
        res += (e.x - s.x) * (e.y + s.y)

    return res > 0


def getWhatCurvesToFlip(curves):
    """Determins which ProfileCurves need their startPoint and endPoint flipped to line up end to end

    Args:
        curves: (ProfileCurves) The List of points to check agains

    Returns:
        bool[]: List of bools of equal length to curves.
    """

    if(len(curves)==1):
        return [False]
    else:
        rtn = []

        for i in range(len(curves)):
            if(i==0):
                rtn.append(
                    isPointInList(
                        getStartPoint(curves[i].geometry),
                        [getStartPoint(curves[1].geometry), getEndPoint(curves[1].geometry)]
                    )
                )
            else:
                rtn.append(
                    not isPointInList(
                        getStartPoint(curves[i].geometry),
                        [getStartPoint(curves[i-1].geometry), getEndPoint(curves[i-1].geometry)]
                        )
                )
        return rtn


def getStartPoint(curve):
    """Gets the start point of any Curve3D object

    Args:
        curves: (Curve3D) The curve

    Returns:
        Point3D: Start point of the curve
    """

    if(curve.objectType in ["adsk::core::Line3D", "adsk::core::Arc3D"]):
        return curve.startPoint

    elif(curve.objectType == "adsk::core::Circle3D"):
        sp = curve.center.copy()
        sp.translateBy(adsk.core.Vector3D.create(curve.radius, 0, 0))
        return sp

    elif(curve.objectType == "adsk::core::Ellipse3D"):
        sp = curve.center.copy()
        la = curve.majorAxis.copy()
        la.normalize()
        la.scaleBy(curve.majorRadius)
        sp.translateBy(la)
        return sp

    elif(curve.objectType in ["adsk::core::EllipticalArc3D", "adsk::core::NurbsCurve3D"]):
        _, sp, ep = curve.evaluator.getEndPoints()
        return sp


def getEndPoint(curve):
    """Gets the end point of any Curve3D object

    Args:
        curves: (Curve3D) The curve

    Returns:
        Point3D: End point of the curve
    """

    if(curve.objectType in ["adsk::core::Line3D", "adsk::core::Arc3D"]):
        return curve.endPoint

    elif(curve.objectType == "adsk::core::Circle3D"):
        ep = curve.center.copy()
        ep.translateBy(adsk.core.Vector3D.create(curve.radius, 0, 0))
        return ep

    elif(curve.objectType == "adsk::core::Ellipse3D"):
        ep = curve.center.copy()
        la = curve.majorAxis.copy()
        la.normalize()
        la.scaleBy(curve.majorRadius)
        ep.translateBy(la)
        return ep

    elif(curve.objectType in ["adsk::core::EllipticalArc3D", "adsk::core::NurbsCurve3D"]):
        _, sp, ep = curve.evaluator.getEndPoints()
        return ep


def isPointInList(point, pointList, tol=1e-4):
    """Determins if a Point3D is almost-equal to a Point3D in a list

    Args:
        point: (Point3D) The Point to be checked
        pointList: (Point3D[]) The List of points to check agains
        tol: (float) Tollerance for almost-equality

    Returns:
        bool: True if almost equal to any Point in list
    """

    for i in pointList:
        if(isPointEqual(point, i, tol)):
            return True
    return False


def isPointEqual(point1, point2, tol=1e-4):
    """Determins if a Point3D is almost-equal to a Point3D in a list

    Args:
        point1: (Point3D) The Point to be checked
        point2: (Point3D) The Points to check agains
        tol: (float) Tollerance for almost-equality

    Returns:
        bool: True if almost equal to point
    """
    return math.isclose(point1.x, point2.x, rel_tol=tol) and math.isclose(point1.y, point2.y, rel_tol=tol) and math.isclose(point1.z, point2.z, rel_tol=tol)


def lerp(a, b, i):
    """Linearly interpolates from a to b

    Args:
        a: (float) The value to interpolate from
        b: (float) The value to interpolate to
        i: (float) Interpolation factor

    Returns:
        float: Interpolation result
    """
    return a + (b-a)*i


def run(context):
    try:
        
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        commandDefinitions = ui.commandDefinitions
        #check the command exists or not
        cmdDef = commandDefinitions.itemById(COMMAND_ID)
        if not cmdDef:
            cmdDef = commandDefinitions.addButtonDefinition(COMMAND_ID, COMMAND_NAME,
                                                            COMMAND_TOOLTIP, '')

            cmdDef.tooltip = "Automatically lays out parts on a sheet optimizing for material usage"
            cmdDef.toolClipFilename = 'resources/description.png'
        #Adds the commandDefinition to the toolbar
        for panel in TOOLBAR_PANELS:
            ui.allToolbarPanels.itemById(panel).controls.addCommand(cmdDef)
        
        onCommandCreated = CommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
    except:
        print(traceback.format_exc())


def stop(context):
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        
        #Removes the commandDefinition from the toolbar
        for panel in TOOLBAR_PANELS:
            p = ui.allToolbarPanels.itemById(panel).controls.itemById(COMMAND_ID)
            if p:
                p.deleteMe()

            
        #Deletes the commandDefinition
        ui.commandDefinitions.itemById(COMMAND_ID).deleteMe()
            
            
            
    except:
        print(traceback.format_exc())

