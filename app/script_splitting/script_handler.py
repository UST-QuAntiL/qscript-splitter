# ******************************************************************************
#  Copyright (c) 2022 University of Stuttgart
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
from redbaron import RedBaron
from app.script_splitting.labeler import split_local_function
import json


def split_qc_script(script):
    app.logger.info('Starting script splitting algorithm...')

    # load white and black lists
    with open('script_splitting/knowledge_base.json', 'r') as knowledge_base:
        knowledge_base_json = json.load(knowledge_base)
    white_list = knowledge_base_json['white_list']
    black_list = knowledge_base_json['black_list']
    print('Number of white list rules: ', len(white_list))
    print('Number of black list rules: ', len(black_list))

    # RedBaron object containing all information about the hybrid program to generate
    with open(script, "r") as source_code:
        qc_script_baron = RedBaron(source_code.read())

    # retrieve all nodes invoking a function (contain a call node at the second position)
    function_invocation_nodes = qc_script_baron.find_all('atomtrailers',
                                                         value=lambda atomtrailer_node_value: len(atomtrailer_node_value) >= 2
                                                         and atomtrailer_node_value[1].type == 'call')
    print('Found %d function invocations!' % len(function_invocation_nodes))

    # extract names of invoked functions
    invoked_function_names = []
    for function_invocation_node in function_invocation_nodes:
        invoked_function_names.append(function_invocation_node[0].value)
    print('Invoked functions: ', invoked_function_names)

    # get all def nodes in the script
    def_nodes = qc_script_baron.find_all('def', name=lambda name: name in invoked_function_names)
    # TODO: handle ifs, while, ifelseblock, etc. contained in identified def_nodes
    # TODO: assign global variables to list of quantum objects

    # split local methods and retrieve label if they are quantum or classical
    label_map = {}
    for def_node in def_nodes:
        label_map = split_local_function(qc_script_baron, def_node, white_list, black_list, label_map, [])
        print('Retrieved label %s for method with name: %s' % (label_map[def_node.name], def_node.name))


    print('##############################')
