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

    # Add vertical spacer
    self.layout.addStretch(1)
    
    
  def cleanup(self):
    pass

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
    self.cameraControllerAttaced = False
    self.palmControlOn = False  #slicer.modules.slicerleapmodule.widgetRepresentation().self().logic.palmControlOn = True
    self.onFrame()
    print('Initialized Leap')
    

      
  def setEnableAutoCreateTransforms(self, enable):
    self.enableAutoCreateTransforms = enable

  def setTransform(self, handIndex, fingerIndex, fingerTipPosition, direction, grab=False):
    
    transformName = "Hand%iFinger%i" % (handIndex+1,fingerIndex+1) # +1 because to have 1-based indexes for the hands and fingers
    if fingerIndex == -1:
      transformName = "Hand%iPalm" % (handIndex+1)
    # print(transformName)

    

    try:
      transform = slicer.util.getNode(transformName)
    except:
      if self.enableAutoCreateTransforms :
            # Create the missing transform
        transform = slicer.vtkMRMLLinearTransformNode()
        transform.SetName(transformName)
        slicer.mrmlScene.AddNode(transform)
        print('Creating')
        
          
      else :
        print('Ignoring')
        # No transform exist, so just ignore the finger
        return
    # Create the transform if does not exist yet

    newTransform = vtk.vtkTransform()
 
    if grab:
      # Reorder and reorient to match the LeapMotion's coordinate system with RAS coordinate system
      newTransform.Translate(fingerTipPosition[0], -fingerTipPosition[2], fingerTipPosition[1])
    else:

      matrix = self.getRotationFromDirection(direction)
      newTransform.SetMatrix(matrix)

    transform.SetMatrixTransformToParent(newTransform.GetMatrix())
    
  
  def getRotationFromDirection(self, direction, up=[0,-1,0]):
    directionVector = vtk.vtkVector3d()
    directionVector[0] = direction[1]
    directionVector[1] = -direction[2]
    directionVector[2] = -direction[0]
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


  
  def onFrame(self):
    # Get the most recent frame
    frame = self.LeapController.frame()


    for handIndex, hand in enumerate(frame.hands) :
      grab = False
      if hand.grab_strength > 0.8:
        print("Grab")
        grab = True
      elif hand.pinch_strength > 0.8: 
        print("Pinch") 
      
      self.setTransform(handIndex, -1, hand.palm_position, hand.palm_normal, grab) 
      
      
      # for fingerIndex, finger in enumerate(hand.fingers) :
      #   self.setTransform(handIndex, fingerIndex, finger.tip_position, finger.direction)
      #   # print(finger.direction)
      #   # print(self.getRotationFromDirection(finger.direction))

    
    try:
      camera = slicer.util.getNode('Camera')
      transform = slicer.util.getNode('Hand1Palm')
      if self.palmControlOn and not self.cameraControllerAttaced:
        print('Camera attached')        
        camera.SetAndObserveTransformNodeID(transform.GetID())
        self.cameraControllerAttaced = True

      if not self.palmControlOn and self.cameraControllerAttaced:
        camera.SetAndObserveTransformNodeID(None)
        print('Camera detached')
        self.cameraControllerAttaced = False

      self.palmPresentInLastFrame = self.palmPresentInFrame
    except:
      pass
    
    # Theoretically Leap could periodically call a callback function, but due to some reason it does not
    # appear to work, so just poll with a timer instead.
    qt.QTimer.singleShot(100, self.onFrame)
