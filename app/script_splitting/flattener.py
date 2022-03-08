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

import logging


def flatten(script):
    # retrieve all nodes invoking a function (contain a call node at the second position)
    function_invocation_nodes = script.find_all('atomtrailers',
                                                         value=lambda atomtrailer_node_value: len(atomtrailer_node_value) >= 2 and atomtrailer_node_value[1].type == 'call')
    logging.debug('Found %d function invocations!' % len(function_invocation_nodes))


    # extract names of invoked functions
    invoked_function_names = []
    for function_invocation_node in function_invocation_nodes:
        invoked_function_names.append(function_invocation_node[0].value)
    logging.debug('Invoked functions: %s' % invoked_function_names)

    # get all def nodes in the script
    def_nodes = script.find_all('def', name=lambda name: name in invoked_function_names)
    # TODO: handle ifs, while, ifelseblock, etc. contained in identified def_nodes
    # TODO: assign global variables to list of quantum objects
    return script
