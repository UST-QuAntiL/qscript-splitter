//var test = require("./Test.js");

//var modeler = require("./bpmn-js/lib/Modeler")

/**
* add menu entry
*/
module.exports = function(electronApp, menuState) {
  return [{
    label: 'Execute ScriptSplitter',
    enabled: function() {
      // only enabled for BPMN diagrams
      return menuState.bpmn;
    },
    action: function() {
    createMyShapes(); 
    }
  }];
};


/**
* create my shapes here
* e.g. this creates a template for the moment.
* @param: modeler 
* @param: metaData
*/
function createMyShapes(modeler, metaData){
  let modeling = modeler.get('modeling');
  let elementRegistry = modeler.get('elementRegistry');
  let bpmnFactory = modeler.get('bpmnFactory'); 
  
  const process = elementRegistry.get('Process_1');
  const startEvent = elementRegistry.get('StartEvent_1');
  const endEvent = elementFactory.createShape({ type: 'bpmn:EndEvent'});
  const PreprocessingTask = elementFactory.createShape({ type: 'bpmn:ScripTask'});
  const QuantumTask = elementFactory.createShape({ type: 'bpmn:ScripTask'});
  const PostprocessingTask = elementFactory.createShape({ type: 'bpmn:ScripTask'});
  const splittingGateway = elementFactory.createShape({ type: 'bpmn:ExclusiveGateway'});
  const joiningGateway = elementFactory.createShape({ type: 'bpmn:ExclusiveGateway'});

  modeling.createShape(splittingGateway, { x: 50, y: 50 }, process)
  modeling.createShape(joiningGateway, { x: 50, y: 50 }, process)
  modeling.createShape(PreprocessingTask, { x: 50, y: 50 }, process);
  modeling.createShape(QuantumprocessingTask, { x: 50, y: 50 }, process);
  modeling.createShape(PostprocessingTask, { x: 50, y: 50 }, process);

  // TODO handle loops according to splitting output
  modeling.connect(startEvent, PreprocessingTask);
  modeling.connect(PreprocessingTask, splittingGateway);
  modeling.connect(splittingGateway, QuantumprocessingTask);
  modeling.connect(QuantumprocessingTask, joiningGateway);
  modeling.connect(joiningGateway, PostprocessingTask );
  modeling.connect(joiningGateway, splittingGateway);
  modeling.connect(PostprocessingTask, endEvent);
}




