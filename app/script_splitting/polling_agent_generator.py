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
import os


def generate_polling_agent(parameters, return_values):
    # Read from polling agent template
    polling_agent_template_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates", "polling_agent_template.py")
    with open(polling_agent_template_path, "r") as template:
        content = template.read()

    load_input_data = content.find("")

    #content = content.replace('### STORE OUTPUT DATA SECTION ###', "print('write output variables to disk')")

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

    return content

