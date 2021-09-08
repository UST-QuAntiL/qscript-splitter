import React, { useState } from 'camunda-modeler-plugin-helpers/react';
import { Modal } from 'camunda-modeler-plugin-helpers/components';
//var react = require('camunda-modeler-plugin-helpers/react');
//var fill = require('camunda-modeler-plugin-helpers/components');

//import {createMyShapes} from './Creator';
var test = require("./Creator");

//module.exports = class ScriptSplitterPlugin extends PureComponent {
export default class ScriptSplitterPlugin extends PureComponent {
  constructor(props) {
    super(props);
  }
  render() {

    // render config button and pop-up menu
    return (<Fragment>
      <Fill slot="toolbar">
        <button type="button" className="src-app-primitives-Button__Button--3Ffn0" title=" Execute Splitter"
          onClick={() => createMyShapes("")}>
          <span className="config"><span className="indent">Configuration</span></span>
        </button>
      </Fill>
    </Fragment>);
  }
}