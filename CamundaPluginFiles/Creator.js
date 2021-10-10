/**
 * This program and the accompanying materials are made available under the
 * terms the Apache Software License 2.0
 * which is available at https://www.apache.org/licenses/LICENSE-2.0.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import { createModeler } from '../quantme/Utilities';
import { layout } from 'client/src/app/quantme/layouter/Layouter';
import { getRootProcess } from 'client/src/app/quantme/utilities/Utilities';

/**
* This is the main entry point
* @param fileName the source-file which contains a quantum-skript
* @param modeler the currently active modeler from camunda
* @param props for debugging only
**/
export function buildWorkflow(fileName, modeler, props) {
  // call the scriptSplitter
  var metadata = callScriptSplitter(fileName);
  var loopBo = createTemplate(modeler);
  createConditionExpression(modeler, loopBo, metadata);
  // start polling agents manually...

  props.displayNotification({
    type:'info',
    title: 'Displaying Meta Data',
    content: metadata,
    duration: 10000
    });
}



/**
* create my shapes here
* e.g. this creates a template for the moment.
* @param modeler the currently active modeler
*/
export function createTemplate(modeler) {
  // initialize modeling helpers
  let modeling = modeler.get('modeling');
  let elementRegistry = modeler.get('elementRegistry');
  let elementFactory = modeler.get('bpmnFactory');
  // get root element of the current diagram and THE ROOT PROCESS
  const definitions = modeler.getDefinitions();
  const rootElement = getRootProcess(definitions);
  var process = elementRegistry.get(rootElement.id);

  // get the random topic names
  var topics = getTopics();
  // get the (default) start event
  var startEvent = elementRegistry.get('StartEvent_1');
  // create
  var quantumTask = modeling.createShape({ type: 'bpmn:ServiceTask', implementation: 'External' }, { x: 100, y: 100 }, process, {});
  var quantumTaskBo = elementRegistry.get(quantumTask.id).businessObject;
  quantumTaskBo.name = 'Quantum Part';
  quantumTaskBo.type = 'external';
  quantumTaskBo.topic = topics[1];
  var preprocessingTask = modeling.createShape({ type: 'bpmn:ServiceTask' }, { x: 100, y: 100 }, process, {});
  var preprocessingTaskBo = elementRegistry.get(preprocessingTask.id).businessObject;
  preprocessingTaskBo.name = 'Preprocessing Part';
  preprocessingTaskBo.type = 'external';
  preprocessingTaskBo.topic = topics[0];
  var postprocessingTask = modeling.createShape({ type: 'bpmn:ServiceTask' }, { x: 100, y: 100 }, process, {});
  var postprocessingTaskBo = elementRegistry.get(postprocessingTask.id).businessObject;
  postprocessingTaskBo.name = 'Postprocessing Part';
  postprocessingTaskBo.type = 'external';
  postprocessingTaskBo.topic = topics[2];
  var endEvent = modeling.createShape({ type: 'bpmn:EndEvent' }, { x: 100, y: 100 }, process, {});
  var splittingGateway = modeling.createShape({ type: 'bpmn:ExclusiveGateway' }, { x: 50, y: 50 }, process, {});
  var splittingGatewayBo = elementRegistry.get(splittingGateway.id).businessObject;
  splittingGatewayBo.name = 'Quantum-Loop';
  var joiningGateway = modeling.createShape({ type: 'bpmn:ExclusiveGateway' }, { x: 50, y: 50 }, process, {});
  var joiningGatewayBo = elementRegistry.get(joiningGateway.id).businessObject;
  joiningGatewayBo.name = 'Quantum-Loop completed?'
  // connect
  modeling.connect(startEvent, preprocessingTask, { type: 'bpmn:SequenceFlow' });
  modeling.connect(preprocessingTask, splittingGateway, { type: 'bpmn:SequenceFlow' });
  modeling.connect(splittingGateway, quantumTask, { type: 'bpmn:SequenceFlow' });
  modeling.connect(quantumTask, joiningGateway, { type: 'bpmn:SequenceFlow' });
  modeling.connect(postprocessingTask, endEvent, { type: 'bpmn:SequenceFlow' });
  // here comes the tricky part about conditions
  let quantumLoopConnector = modeling.connect(joiningGateway, splittingGateway, { type: 'bpmn:SequenceFlow' });
  let quantumLoopConnectorBo = elementRegistry.get(quantumLoopConnector.id).businessObject;
  quantumLoopConnectorBo.name = 'Quantum Loop not finished';

  let quantumLoopEndConnector = modeling.connect(joiningGateway, postprocessingTask, { type: 'bpmn:SequenceFlow' });
  let quantumLoopEndConnectorBo = elementRegistry.get(quantumLoopEndConnector.id).businessObject;
  quantumLoopEndConnectorBo.name = 'Quantum Loop finished';



  // make it pretty
  layout(modeling, elementRegistry, rootElement);
  // return loopCondition-bo to make further adjustments
  return quantumLoopConnectorBo;
}

/**
* adjust the template s.t. the loop-condition corresponds to meta-data
*@param modeler the current active modeler
*@param quantumLoopConnectorBo BO holding the loop-condition
*@param metaData the meta-data retrieved from scriptSplitting
*/
function createConditionExpression(modeler, quantumLoopConnectorBo, metaData){
  // TODO implement
  let elementFactory = modeler.get('bpmnFactory');
  let loopCondition = elementFactory.create('bpmn:FormalExpression');
  const obj = JSON.parse(metaData);
  var tmpCondition = obj.LoopConditions[1];

  loopCondition.body = tmpCondition;
  quantumLoopConnectorBo.conditionExpression = loopCondition;
}

/**
* generate random names for topics
*/
function getTopics() {
  // TODO randomize topic-names
  var topics = ["RandomPre", "RandomQuantum", "RandomPost"];

  return topics;
}

/**
* call the Script Splitting Algorithm over the local flask app
*@param fileName the name of the file which contains the source-code
**/
function callScriptSplitter(fileName){

  var url = 'http://127.0.0.1:5000/scriptSplitter';
  var metaData;
  const data = { 'source-file': fileName, 'dada': 'dada' };

  fetch(url, {
    method: 'POST', // or 'PUT'
    headers: {
      'Content-Type': 'application/json',
    },
    body:JSON.stringify({sourceFile: fileName})
    })
    .then((resp) => resp.json())
    .then(function(data) {
      let res = data.results;
      metaData = res;
    });

  //metaData = "TEST";
  metaData = JSON.stringify({
    PreStart: 12,
    QuantumStart: 26,
    PostStart: 87,
    LoopConditions: ['Nope','False']
  })
  return metaData;
}

/**
* simple test function that
* @param message the data for the test
* @param props property element for displaying the message
*/
export function test(message, props) {
  props.displayNotification({
    type:'warning',
    title: 'TEST',
    content: message,
    duration: 20000
  });

}
