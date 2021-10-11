/**
 * This program and the accompanying materials are made available under the
 * terms the Apache Software License 2.0
 * which is available at https://www.apache.org/licenses/LICENSE-2.0.
 *
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { Fragment, PureComponent } from 'camunda-modeler-plugin-helpers/react';
import { Modal } from 'camunda-modeler-plugin-helpers/components';
import { Fill } from 'camunda-modeler-plugin-helpers/components';

import { buildWorkflow } from './Creator';


/**
* Essentially this class will create a seperate button in the toolbar.
* If this button is clicked, the scriptSplitter will be executed.
*/
export default class ScriptSplitterPlugin extends PureComponent {
  constructor(props) {
    super(props);
  }
  componentDidMount() {

    // initialize component with created modeler
    this.props.subscribe('bpmn.modeler.created', (event) => {

      const {
        modeler, tab
      } = event;

      // save modeler and activate as current modeler
      this.modeler = modeler;
      const self = this;

      // register actions to enable invocation over the menu and the API
      this.editorActions = modeler.get('editorActions');
  });
}
  render() {

    // render the button to start the splitting algorithm
    return (<Fragment>
      <Fill slot="toolbar">
        <button type="button" className="src-app-primitives-Button__Button--3Ffn0" title="Start Splitting"
          onClick= {() => this.startSplitting()}>
          <span className="workflow-transformation"><span className="indent">Execute ScriptSplitter</span></span>
        </button>
      </Fill>
    </Fragment>);
  }


  /**
  * start the generation process
  */
  startSplitting() {
    var startMessage = 'Start the Splitting Algorithm.'
    this.props.displayNotification({
      type:'info',
      title: 'ScriptSplitter',
      content: startMessage,
      duration: 10000
      });
      // TODO get this from user-input
      var fileName = 'C:/Users/tjehr/Uni/Masterarbeit/Code/GitHub/qscript-splitter-neu/Example/exampleScript.py';
      buildWorkflow(fileName, this.modeler, this.props);
  }
}
