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
import json
import os
import random
import string

from redbaron import RedBaron


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
    for inputParameter in parameters:
        load_data_str += '\n'
        load_data_str += '                    if variables.get("' + inputParameter + '").get("type") == "String":\n'
        load_data_str += '                        ' + inputParameter + ' = variables.get("' + inputParameter + '").get("value")\n'
        load_data_str += '                    else:\n'
        load_data_str += '                        ' + inputParameter + ' = download_data(camundaEndpoint + "/process-instance/" + externalTask.get("processInstanceId") + "/variables/' + inputParameter + '/data")'

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
                    "filename": "file_name.txt",
                    "encoding": ""
                }
            }
        }
    }
    '''
    # load RedBaron with current polling agent content
    pollingAgentBaron = RedBaron(content)
    print(pollingAgentBaron.help())

    # get the poll method from the template
    pollDefNode = pollingAgentBaron.find('def', name='poll')

    # get the try catch block in the method
    tryNode = pollDefNode.value.find('try')
    ifNode = tryNode.value.find('ifelseblock').value[0].value.find('for').value.find('ifelseblock').find('if')

    # get the position of the output placeholders within the template
    outputNodeIndex = ifNode.index(ifNode.find('comment', recursive=True, value='### STORE OUTPUT DATA SECTION ###'))
    outputBodyNode = ifNode.find('assign', target=lambda target: target and (target.value == 'body'))

    outputDict = {"workerId": pollingAgentName, "variables": {}}
    for outputParameter in return_values:
        # encode output parameter as file to circumvent the Camunda size restrictions on strings
        encoding = 'encoded_' + outputParameter + ' = base64.b64encode(str.encode(pickle.dumps(' \
                   + outputParameter \
                   + '))).decode("utf-8") '
        ifNode.insert(outputNodeIndex + 1, encoding)

        # add to final result object send to Camunda
        outputDict["variables"][outputParameter] = {"value": 'encoded_' + outputParameter, "type": "File",
                                                    "valueInfo": {
                                                        "filename": outputParameter + ".txt",
                                                        "encoding": ""
                                                    }
                                                    }

    # remove the quotes added by json.dumps for the variables in the target file
    outputJson = json.dumps(outputDict)
    for outputParameter in return_values:
        outputJson = outputJson.replace('"encoded_' + outputParameter + '"', 'encoded_' + outputParameter)

    # remove the placeholder
    ifNode.remove(ifNode[outputNodeIndex])

    # update the result body with the output parameters
    outputBodyNode.value = outputJson

    # workaround due to RedBaron bug which wrongly idents the exception
    pollingAgentString = pollingAgentBaron.dumps()
    pollingAgentString = pollingAgentString.replace("except Exception as err:", "    except Exception as err:")
    print(pollingAgentString)

    return pollingAgentString

