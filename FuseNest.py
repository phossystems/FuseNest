#Author-Nico Schlueter
#Description-SVG nest for Fusion360

import adsk.core, adsk.fusion, adsk.cam, traceback
import math
import re
from xml.dom import minidom
import json
import time, threading

# Global set of event handlers to keep them referenced for the duration of the command
_handlers = []

COMMAND_ID = "svgNestFusion"
COMMAND_NAME = "2D Nest"
COMMAND_TOOLTIP = "2D nest parts with SVGnest"
 
TOOLBAR_PANELS = ["SolidModifyPanel"]

SVG_UNIT_FACTOR = 100

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
            transform_data = None

            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)

            # Registers the CommandDestryHandler
            onExecute = CommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)  
            
            # Registers the CommandExecutePreviewHandler
            onExecutePreview = CommandExecutePreviewHandler()
            cmd.executePreview.add(onExecutePreview)
            _handlers.append(onExecutePreview)
            
            # Registers the CommandInputChangedHandler          
            onInputChanged = CommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)            
            
            # Registers the CommandDestryHandler
            onDestroy = CommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

                
            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs
            
            siBodies = inputs.addSelectionInput("SIBodies", "Bodies", "Select Bodies")
            siBodies.addSelectionFilter("Occurrences")
            siBodies.setSelectionLimits(0, 0)

            viSheetWidth = inputs.addValueInput("VISheetWidth", "Sheet Width", "mm", adsk.core.ValueInput.createByString("500 mm"))

            viSheetHeight = inputs.addValueInput("VISheetHeight", "Sheet Height", "mm", adsk.core.ValueInput.createByString("300 mm"))

            #viSpacing = inputs.addValueInput("VISpacing", "Spacing", "mm", adsk.core.ValueInput.createByString("10 mm"))

            #isRotations = inputs.addIntegerSpinnerCommandInput("ISRotations", "Rotations", 2, 999999, 1, 4)

            #ddPreset = inputs.addDropDownCommandInput("DDPreset", "Preset", 0)
            #ddPreset.listItems.add("Round", False, "")
            #ddPreset.listItems.add("Square", False, "")

            bvNest = inputs.addBoolValueInput("BVNest", "    Start Nesting    ", False)
            bvNest.isFullWidth = True


           
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

                root = adsk.core.Application.get().activeProduct.rootComponent
                sketch = root.sketches.add(root.xYConstructionPlane)
                for i, t in transform_data:
                    mat1 = adsk.core.Matrix3D.create()
                    mat1.translation = adsk.core.Vector3D.create(t[0], -t[1], 0)
                    #mat1.translation = adsk.core.Vector3D.create(1, 0, 0)

                    mat2 = adsk.core.Matrix3D.create()
                    mat2.setToRotation(
                        math.radians(-t[2]),
                        adsk.core.Vector3D.create(0,0,1),
                        adsk.core.Point3D.create(0,0,0)
                    )

                    mat2.transformBy(mat1)

                    trans = selections[i].transform
                    trans.transformBy(mat2)
                    selections[i].transform = trans

                    #move_input = root.features.moveFeatures.createInput(oc, mat2)
                    #root.features.moveFeatures.add(move_input)
                adsk.core.Application.get().activeDocument.design.snapshots.add()
        except:
            print(traceback.format_exc())




# Fires when the Command is being created or when Inputs are being changed
# Responsible for generating a preview of the output.
# Changes done here are temporary and will be cleaned up automatically.
class CommandExecutePreviewHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:

            # Doesn't work
            """
            global transform_data
            if(transform_data):
                selections = []

                for i in range(args.command.commandInputs.itemById("SIBodies").selectionCount):
                    selections.append(args.command.commandInputs.itemById("SIBodies").selection(i).entity)

                root = adsk.core.Application.get().activeProduct.rootComponent
                sketch = root.sketches.add(root.xYConstructionPlane)
                for i, t in transform_data:
                    mat1 = adsk.core.Matrix3D.create()
                    mat1.translation = adsk.core.Vector3D.create(t[0], -t[1], 0)
                    #mat1.translation = adsk.core.Vector3D.create(1, 0, 0)

                    mat2 = adsk.core.Matrix3D.create()
                    mat2.setToRotation(
                        math.radians(-t[2]),
                        adsk.core.Vector3D.create(0,0,1),
                        adsk.core.Point3D.create(0,0,0)
                    )

                    mat2.transformBy(mat1)

                    trans = selections[i].transform
                    trans.transformBy(mat2)
                    selections[i].transform = trans

                    #move_input = root.features.moveFeatures.createInput(oc, mat2)
                    #root.features.moveFeatures.add(move_input)
                adsk.core.Application.get().activeDocument.design.snapshots.add()
            """
            args.isValidResult = False                
            
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
                    sketch.project(s.bRepBodies[0])
                    paths += sketchToSVGPaths(sketch) 

                svg = buildSVGFromPaths(paths, args.inputs.itemById("VISheetWidth").value, args.inputs.itemById("VISheetHeight").value)

                # Here is here i would also incude other setting but I havn't
                #data = {
                #    "svg": svg,
                #    "spacing": args.inputs.itemById("VISpacing").value * SVG_UNIT_FACTOR,
                #    "rotations": args.inputs.itemById("ISRotations").value
                #}
                #print(json.dumps(data))
                
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
                threading.Timer(2.5, sendSVGToPalette, [palette, svg]).start()

        except:
            print(traceback.format_exc())
                
                
                
# Fires when the Command gets Destroyed regardless of success
# Responsible for cleaning up                 
class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # TODO: Add Destroy stuff
            pass
        except:
            print(traceback.format_exc())


class PaletteCloseEventHandler(adsk.core.UserInterfaceGeneralEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            ui = adsk.core.Application.get().userInterface
            palette = ui.palettes.itemById('paletteSVGNest')
            palette.deleteMe()
        except:
            print(traceback.format_exc())


# Event handler for the palette HTML event.                
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
                palette.deleteMe()
            
        except:
            print(traceback.format_exc())


def sendSVGToPalette(palette, svg):
    if palette:
        palette.sendInfoToHTML("importSVG", svg)


def buildSVGFromPaths(paths, width=50, height=25):
    """Constructs a full svg fle from paths

    Args:
        paths: (String[]) SVG path data
        width: (float) Width ouf bounding rectangle
        height: (float) Height of bounding rectangle

    Returns:
        [string]: full svg

    """
    global SVG_UNIT_FACTOR

    rtn = ""

    rtn += r'<svg version="1.1" xmlns="http://www.w3.org/2000/svg"> '

    rtn += r'<rect width="{}" height="{}" stroke="black" stroke-width="2" fill-opacity="0"/> '.format(width*SVG_UNIT_FACTOR, height*SVG_UNIT_FACTOR)

    for i, p in enumerate(paths):
        rtn += r'<path d="{}" id="{}" stroke="black" fill="green" stroke-width="2" fill-opacity="0.5"/> '.format(p, i)

    rtn += r'</svg>'

    return rtn


def getTransformsFromSVG(svg):
    """Imports SVG result from svgnest and extracts transform data

    Args:
        svg: (String) SVG data

    Returns:
        [zip]: zip of index and transform data (x, y, r)
    """

    global SVG_UNIT_FACTOR

    dom = minidom.parseString(svg)

    ids = []
    transforms = []

    p = re.compile(r'[\(\s]-?\d*\.{0,1}\d+')

    for e in dom.getElementsByTagName('path'):
        ids.append(int(e.getAttribute('id')))
        transformTag = (e.parentNode.getAttribute('transform'))
        transforms.append([float(i[1:]) for i in p.findall(transformTag)])
        
    transformsScaled = [ [t[0]/SVG_UNIT_FACTOR, t[1]/SVG_UNIT_FACTOR, t[2]] for t in transforms]

    return zip(ids, transformsScaled)
    

def sketchToSVGPaths(sketch):
    """Converts a Sketch into a SVG Path date

    Args:
        sketch: (Sketch) Sketch to convert

    Returns:
        [str]: Array of SVG paths
    """

    rtn = []

    for p in sketch.profiles:
        for pl in p.profileLoops:
            if(pl.isOuter):
                rtn.append(loopToSVGPath(pl))
                break

    return rtn


def loopToSVGPath(loop):
    """Converts a ProfileLoop into a SVG Path date

    Args:
        loop: (ProfileLoop) Loop to convert

    Returns:
        str: SVG Path data
    """
    
    global SVG_UNIT_FACTOR

    rtn = ""

    flip = getWhatCurvesToFlip(loop.profileCurves)

    for c, f in zip(loop.profileCurves, flip):
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
        
        angle = math.degrees(math.atan2(la.y, la.x))

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

    elif(curve.geometry.objectType == "adsk::core::EllipticalArc3D"):
        angle = math.degrees(math.atan2(curve.geometry.majorAxis.y, curve.geometry.majorAxis.x))

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

