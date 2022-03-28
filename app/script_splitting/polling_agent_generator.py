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
    content = content.replace("### CALL SCRIPT PART ###", "print('load input variables')")
    content = content.replace('### STORE OUTPUT DATA SECTION ###', "print('write output variables to disk')")
    return content

