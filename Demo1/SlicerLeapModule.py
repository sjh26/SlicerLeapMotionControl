from __future__ import print_function
import os
from __main__ import vtk, qt, ctk, slicer

#
# SlicerLeapModule
#

class SlicerLeapModule(object):
  def __init__(self, parent):
    parent.title = "LeapMotion control"
    parent.categories = ["Gesture control"]
    parent.dependencies = []
    parent.contributors = ["Andras Lasso (PerkLab, Queen's)"]
    parent.helpText = "This is a simple example of interfacing with the LeapMotion controller in 3D Slicer."
    parent.acknowledgementText = ""
    self.parent = parent
    
    # Create the logic to start processing Leap messages on Slicer startup
    logic = SlicerLeapModuleLogic()

#
# qSlicerLeapModuleWidget
#

class SlicerLeapModuleWidget(object):
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    # Instantiate and connect widgets ...
    self.logic = SlicerLeapModuleLogic()
    #
    # Reload and Test area
    #
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload && Test"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # reload button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "SlicerLeapModule Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # reload and test button
    # (use this during development, but remove it when delivering
    #  your module to users)
    self.reloadAndTestButton = qt.QPushButton("Reload and Test")
    self.reloadAndTestButton.toolTip = "Reload this module and then run the self tests."
    reloadFormLayout.addWidget(self.reloadAndTestButton)
    self.reloadAndTestButton.connect('clicked()', self.onReloadAndTest)

     #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Check box to enable creating output transforms automatically.
    # The function is useful for testing and initial creation of the transforms but not recommended when the
    # transforms are already in the scene.
    #
    self.enableAutoCreateTransformsCheckBox = qt.QCheckBox()
    self.enableAutoCreateTransformsCheckBox.checked = 0
    self.enableAutoCreateTransformsCheckBox.setToolTip("If checked, then transforms are created automatically (not recommended when transforms exist in the scene already).")
    parametersFormLayout.addRow("Auto-create transforms", self.enableAutoCreateTransformsCheckBox)
    self.enableAutoCreateTransformsCheckBox.connect('stateChanged(int)', self.setEnableAutoCreateTransforms)

    self.calibrateButton = qt.QPushButton('Calibrate Palm Position')
    parametersFormLayout.addRow("Click to calibrate", self.calibrateButton)
    self.calibrateButton.clicked.connect(self.logic.calibratePalm)

    self.palmControlCheckBox = qt.QCheckBox()
    self.palmControlCheckBox.checked = 0
    parametersFormLayout.addRow("Enable palm camera control", self.palmControlCheckBox)
    self.palmControlCheckBox.connect('stateChanged(int)', self.setPalmControl)
    

    # Add vertical spacer
    self.layout.addStretch(1)
    
    
  def cleanup(self):
    pass

  def setPalmControl(self,enable):
    if enable:
      self.logic.calibratePalm()
    self.logic.palmControlOn = enable
  
  def setEnableAutoCreateTransforms(self, enable):
    self.logic.setEnableAutoCreateTransforms(enable)
  
  def onReload(self,moduleName="SlicerLeapModule"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)

    # delete the old widget instance
    if hasattr(globals()['slicer'].modules, widgetName):
      getattr(globals()['slicer'].modules, widgetName).cleanup()

    # create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()
    setattr(globals()['slicer'].modules, widgetName, globals()[widgetName.lower()])

  def onReloadAndTest(self,moduleName="SlicerLeapModule"):
    try:
      self.onReload()
      evalString = 'globals()["%s"].%sTest()' % (moduleName, moduleName)
      tester = eval(evalString)
      tester.runTest()
    except Exception as e:
      import traceback
      traceback.print_exc()
      qt.QMessageBox.warning(slicer.util.mainWindow(), 
          "Reload and Test", 'Exception!\n\n' + str(e) + "\n\nSee Python Console for Stack Trace")


#
# SlicerLeapModuleLogic
#

class SlicerLeapModuleLogic(object):
  """This class implements all the actual computation in the module.
  """
  
  def __init__(self):
    import Leap.Leap as Leap
    self.LeapController = Leap.Controller()
    self.enableAutoCreateTransforms = True    
    self.cameraControllerAttached = False
    self.palmControlOn = False  #slicer.modules.slicerleapmodule.widgetRepresentation().self().logic.palmControlOn = True
    self.onFrame()
    self.grabbed = False
    self.pinched = False
    self.calibrated = False
    self.calibrationInProgress = False
    self.previousPinchValue = -1
    print('Initialized Leap')
    

      
  def setEnableAutoCreateTransforms(self, enable):
    self.enableAutoCreateTransforms = enable

  def setTransform(self, handIndex, fingerIndex, fingerTipPosition, direction):
    
    transformName = "Hand%iFinger%i" % (handIndex+1,fingerIndex+1) # +1 because to have 1-based indexes for the hands and fingers
    if fingerIndex == -1:
      transformName = "Hand%iPalm" % (handIndex+1)
    # print(transformName)

    

    try:
      transformP = slicer.util.getNode(transformName+"Position")
    except:
      if self.enableAutoCreateTransforms :
            # Create the missing transform
        transformP = slicer.vtkMRMLLinearTransformNode()
        transformP.SetName(transformName+"Position")
        slicer.mrmlScene.AddNode(transformP)
        print('Creating')

    try:
      transformO = slicer.util.getNode(transformName+"Orientation")
    except:
      if self.enableAutoCreateTransforms :
            # Create the missing transform
        transformO = slicer.vtkMRMLLinearTransformNode()
        transformO.SetName(transformName+"Orientation")
        slicer.mrmlScene.AddNode(transformO)
        transformO.SetAndObserveTransformNodeID(transformP.GetID())
        print('Creating')

      try:
        compositedNode = slicer.util.getNode('Hand1PalmComposited')
      except:
        compositedNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', 'Hand1PalmComposited')
        compositedNode.SetAndObserveTransformNodeID(transformO.GetID())
        compositedNode.CreateDefaultDisplayNodes()
        # compositedNode.GetDisplayNode().SetEditorVisibility(True)
        
          
      else :
        print('Ignoring')
        # No transform exist, so just ignore the finger
        return
    # Create the transform if does not exist yet

    newTransformPosition = vtk.vtkTransform()
    newTransformOrientation = vtk.vtkTransform()
 
      # Reorder and reorient to match the LeapMotion's coordinate system with RAS coordinate system
    newTransformPosition.Translate(fingerTipPosition[0], -fingerTipPosition[2], fingerTipPosition[1])
  

    matrix = self.getRotationFromDirection(direction)
    newTransformOrientation.SetMatrix(matrix)

    

    if self.pinched:
      return


    # grab both when calibration
    if self.calibrationInProgress:
      transformP.SetMatrixTransformToParent(newTransformPosition.GetMatrix())
      transformO.SetMatrixTransformToParent(newTransformOrientation.GetMatrix())
      return


    if self.grabbed:
      transformP.SetMatrixTransformToParent(newTransformPosition.GetMatrix())
    else:
      transformO.SetMatrixTransformToParent(newTransformOrientation.GetMatrix())

    

  def cloneNode(self, inputNode, outputNodeName):
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    itemIDToClone = shNode.GetItemByDataNode(inputNode)
    clonedItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode, itemIDToClone)
    clonedNode = shNode.GetItemDataNode(clonedItemID)
    clonedNode.SetName(outputNodeName)
    return clonedNode
  
  def calibratePalm(self):

    self.calibrationInProgress = True
    # self.onFrame()
    try:
      node = slicer.util.getNode('Hand1PalmPositionCalibration')
      slicer.mrmlScene.RemoveNode(node)
    except:
      pass

    try:
      node = slicer.util.getNode('Hand1PalmOrientationCalibration')
      slicer.mrmlScene.RemoveNode(node)
    except:
      pass

    

    compositedNode = slicer.util.getNode('Hand1PalmComposited')

    position = slicer.util.getNode('Hand1PalmPosition')
    positioncalibration = self.cloneNode(position, 'Hand1PalmPositionCalibration')  
    positioncalibration.Inverse()
    positioncalibration.SetAndObserveTransformNodeID(position.GetID())

    orientation = slicer.util.getNode('Hand1PalmOrientation')
    orientationcalibration = self.cloneNode(orientation, 'Hand1PalmOrientationCalibration')  
    orientationcalibration.Inverse()
    orientationcalibration.SetAndObserveTransformNodeID(orientation.GetID())

    orientation.SetAndObserveTransformNodeID(positioncalibration.GetID())

    compositedNode.SetAndObserveTransformNodeID(orientationcalibration.GetID())
    self.calibrationInProgress = False
    # self.onFrame()

    
    
  
  def getRotationFromDirection(self, direction, up=[0,0,1]):
    directionVector = vtk.vtkVector3d()
    directionVector[0] = direction[0]
    directionVector[1] = direction[1]
    directionVector[2] = direction[2]
    directionVector.Normalize()
    upVector = vtk.vtkVector3d(up)
    upVector.Normalize()
    normalVector = directionVector.Cross(upVector)
    normalVector.Normalize()

    upVector = normalVector.Cross(directionVector)
    directionVector.Normalize()

    #Create matrix
    matrix = vtk.vtkMatrix4x4()
    matrix.SetElement(0,0,directionVector[0])
    matrix.SetElement(1,0,directionVector[1])
    matrix.SetElement(2,0,directionVector[2])

    matrix.SetElement(0,1,upVector[0])
    matrix.SetElement(1,1,upVector[1])
    matrix.SetElement(2,1,upVector[2])

    matrix.SetElement(0,2,normalVector[0])
    matrix.SetElement(1,2,normalVector[1])
    matrix.SetElement(2,2,normalVector[2])

    return matrix

  def createPalmNormal(self, palm_normal):
    try:
      lineNode = slicer.util.getNode("PalmNormal")
    except:
          # Create the missing transform
      lineNode = slicer.vtkMRMLMarkupsLineNode()
      lineNode.SetName("PalmNormal")
      slicer.mrmlScene.AddNode(lineNode)
      print('Creating')

    lineNode.RemoveAllControlPoints()
    lineNode.AddControlPoint(vtk.vtkVector3d([0,0,0]))
    lineNode.AddControlPoint(vtk.vtkVector3d([60 * palm_normal[0], 60 * -palm_normal[2], 60 * palm_normal[1]]))
  
  def onFrame(self):
    # Get the most recent frame
    frame = self.LeapController.frame()


    for handIndex, hand in enumerate(frame.hands) :
      grab = False
      pinch = False
      if hand.grab_strength > 0.9:
        grab = True
      elif hand.pinch_strength > 0.7: 
        pinch = True 
      self.grabbed = grab
      self.pinched = pinch
      if self.pinched:
            print(hand.pinch_distance)
      self.setTransform(handIndex, -1, hand.palm_position, hand.palm_normal) 
      self.createPalmNormal(hand.palm_normal)
      
      
      # for fingerIndex, finger in enumerate(hand.fingers) :
      #   self.setTransform(handIndex, fingerIndex, finger.tip_position, finger.direction)
      #   # print(finger.direction)
      #   # print(self.getRotationFromDirection(finger.direction))

    
    try:
      camera = slicer.util.getNode('Camera')
      transform = slicer.util.getNode('Hand1PalmComposited')
      if self.palmControlOn and not self.cameraControllerAttached:
        print('Camera attached')        
        camera.SetAndObserveTransformNodeID(transform.GetID())
        self.cameraControllerAttached = True

      if not self.palmControlOn and self.cameraControllerAttached:
        camera.SetAndObserveTransformNodeID(None)
        print('Camera detached')
        self.cameraControllerAttached = False

      if self.pinched and self.palmControlOn:
        if self.previousPinchValue != -1:
              if self.previousPinchValue > hand.pinch_distance:
                camera.GetCamera().Zoom(0.90)
              else:
                camera.GetCamera().Zoom(1.2)   
        self.previousPinchValue = hand.pinch_distance

      self.palmPresentInLastFrame = self.palmPresentInFrame
    except:
      pass
    
    # Theoretically Leap could periodically call a callback function, but due to some reason it does not
    # appear to work, so just poll with a timer instead.
    qt.QTimer.singleShot(100, self.onFrame)
