# ******************************************************************************
#  Copyright (c) 2021 University of Stuttgart
#
#  See the NOTICE file(s) distributed with this work for additional
#  information regarding copyright ownership.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# ******************************************************************************
from app import app
import os
import random
import string


def generate_polling_agent(parameters, return_values):
    # Read from polling agent template
    polling_agent_template_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates", "polling_agent_template.py")
    with open(polling_agent_template_path, "r") as template:
        content = template.read()

    # generate random name for the polling agent and replace placeholder
    pollingAgentName = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    content = content.replace("$ServiceNamePlaceholder", pollingAgentName)

    # handle variable retrieval for input data
    load_data_str = ''
    app.logger.debug('Number of input parameters: %d' % len(parameters))
    for inputParameter in parameters:
        load_data_str += '\n'
        load_data_str += '                    if variables.get("' + inputParameter + '").get("type").casefold() in ["string", "long", "double", "boolean"]:\n'
        load_data_str += '                        print("Input Parameter ' + inputParameter + ' (basic type)")\n'
        load_data_str += '                        ' + inputParameter + ' = variables.get("' + inputParameter + '").get("value")\n'
        load_data_str += '                        print("...value: %s" % ' + inputParameter + ')\n'
        load_data_str += '                    else:\n'
        load_data_str += '                        print("Input Parameter ' + inputParameter + ' (pickle)")\n'
        load_data_str += '                        ' + inputParameter + ' = download_data(camundaEndpoint + "/process-instance/" + externalTask.get("processInstanceId") + "/variables/' + inputParameter + '/data")\n'
        load_data_str += '                        print("...downloaded value: %s" % ' + inputParameter + ')\n'
        load_data_str += '                        ' + inputParameter + ' = pickle.loads(' + inputParameter + ')\n'
        load_data_str += '                        print("...decoded value: %s" % ' + inputParameter + ')\n'

    content = content.replace("### LOAD INPUT DATA ###", load_data_str)

    call_str = ", ".join(return_values)
    if len(return_values) > 0:
        call_str += " = "
    call_str += "app.main(" + ", ".join(parameters) + ")"
    content = content.replace("### CALL SCRIPT PART ###", call_str)

    # handle output
    '''
    Required return value by Camunda:
    {
        "workerId": pollingAgentName, 
        "variables": {
            "variable_name": {
                "value": 'base64_content',
                "type": "File",
                "valueInfo": {
                    "filename": "file_name",
                    "encoding": ""
                }
            }
        }
    }
    '''
    outputHandler = '\n'
    outputHandler += '                    body = {"workerId": "' + pollingAgentName + '"}\n'
    outputHandler += '                    body["variables"] = {}\n'
    for outputParameter in return_values:
        # encode output parameter as file to circumvent the Camunda size restrictions on strings
        outputHandler += '\n'
        outputHandler += '                    if isinstance(' + outputParameter + ', str):\n'
        outputHandler += '                        print("OutputParameter (string) %s" % ' + outputParameter + ')\n'
        outputHandler += '                        body["variables"]["' + outputParameter + '"] = {"value": ' + outputParameter + ', "type": "string"}\n'
        outputHandler += '                    elif isinstance(' + outputParameter + ', int):\n'
        outputHandler += '                        print("OutputParameter (int) %s" % ' + outputParameter + ')\n'
        outputHandler += '                        body["variables"]["' + outputParameter + '"] = {"value": ' + outputParameter + ', "type": "long"}\n'
        outputHandler += '                    elif isinstance(' + outputParameter + ', float):\n'
        outputHandler += '                        print("OutputParameter (float) %s" % ' + outputParameter + ')\n'
        outputHandler += '                        body["variables"]["' + outputParameter + '"] = {"value": ' + outputParameter + ', "type": "double"}\n'
        outputHandler += '                    elif isinstance(' + outputParameter + ', bool):\n'
        outputHandler += '                        print("OutputParameter (bool) %s" % ' + outputParameter + ')\n'
        outputHandler += '                        body["variables"]["' + outputParameter + '"] = {"value": ' + outputParameter + ', "type": "boolean"}\n'
        outputHandler += '                    else:\n'
        outputHandler += '                        try:\n'
        outputHandler += '                            print("Encode OutputParameter %s" % ' + outputParameter + ')\n'
        outputHandler += '                            encoded_' + outputParameter + ' = base64.b64encode(pickle.dumps(' + outputParameter + ')).decode()\n'
        outputHandler += '                            print("Encoded: %s" % encoded_' + outputParameter + ')\n'
        outputHandler += '                            body["variables"]["' + outputParameter + '"] = {"value": encoded_' + outputParameter + ', "type": "File", "valueInfo": {"filename": "' + outputParameter + '", "encoding": "utf-8"}}\n'
        outputHandler += '                        except Exception as err:\n'
        outputHandler += '                            print("Could not pickle %s" % err)\n'
        outputHandler += '                    print("body: %s" % body)'

    # remove the placeholder
    return content.replace("### STORE OUTPUT DATA SECTION ###", outputHandler)
