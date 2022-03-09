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

from redbaron import RedBaron
from app.script_splitting.Labels import Labels
import logging


def split_script(script, splitting_labels):
    for i in range(len(script)):
        logging.debug("%s: %s" % (splitting_labels[i], repr(script[i].dumps())))

    code_blocks = identify_code_blocks(splitting_labels)
    logging.debug("Code block indices: %s" % code_blocks)

    # start building result_script with preamble
    result_script = script[0:code_blocks[0][0]]

    all_possible_return_variables = []
    for block in code_blocks:
        first = block[0]
        last = block[-1]
        code_block = script[first:last+1]

        # compute list of parameters
        parameters = compute_parameters(code_block, all_possible_return_variables)
        logging.info("Call arguments for code block %s: %s" % (block, parameters))

        # compute list of return variables
        return_variables = compute_return_variables(block, script)
        all_possible_return_variables.extend(return_variables)
        logging.info("Return arguments for code block %s: %s" % (block, return_variables))

        # generate new method from code block and append to result script
        method_name = "function_" + str(first) + "to" + str(last)
        created_method = create_method(code_block, method_name, parameters, return_variables)
        result_script.append(created_method)

        # generate method call from method and append to result script
        method_call = ""
        if len(return_variables) > 0:
            method_call += ", ".join(return_variables) + " = "
        method_call += method_name + "(" + ",".join(parameters) + ")"
        logging.debug("Insert method call for created method: %s" % method_call)
        result_script.append(RedBaron(method_call)[0])


def identify_code_blocks(splitting_labels):
    list_of_all_code_block_indices = []
    code_block_indices = []
    current_label = None
    for i in range(len(splitting_labels)):
        label = splitting_labels[i]
        # skip imports
        if label == Labels.IMPORTS:
            continue
        # add empty lines to code block, too
        if label == Labels.NO_CODE:
            code_block_indices.append(i)
            continue
        # tag label of current block
        if current_label is None:
            current_label = label
        # start new code block if label changes
        if label != current_label:
            current_label = label
            list_of_all_code_block_indices.append(code_block_indices[:])
            code_block_indices = []
        # add line to code block
        code_block_indices.append(i)
    # add last code block
    list_of_all_code_block_indices.append(code_block_indices[:])
    return list_of_all_code_block_indices


def compute_return_variables(block_indices, script):
    first = block_indices[0]
    last = block_indices[-1]
    code_block = script[first:last+1]
    remaining_block = []
    if len(script) > last+1:
        remaining_block = script[last+1:]

    initialized_variables = []
    for line in code_block:
        if line.type == "assignment":
            initialized_variables.append(str(line.target.name))

    result = []
    for line in remaining_block:
        for variable in initialized_variables:
            if is_used_in_line(variable, line) and str(variable) not in result:
                result.append(str(variable))

    return result


def is_used_in_line(variable, line):
    found = line.find_all("NameNode", value=variable)
    # TODO: NameNode includes function calls as well, thus, only search for variables.
    #  The current implementation, however, might return unnecessary variables as well.
    return len(found) > 0


def compute_parameters(code_block, all_possible_return_variables):
    parameters = []
    for line in code_block:
        if line.type == "assignment":
            param_list = compute_parameters(line.value, all_possible_return_variables)
            for element in param_list:
                if element not in parameters:
                    parameters.append(element)
            continue
        if line.type in ['comment', 'endl', 'import']:
            continue
        for variable in all_possible_return_variables:
            if is_used_in_line(variable, line) and str(variable) not in parameters:
                parameters.append(str(variable))

    return parameters


def create_method(code_block, method_name, parameters, return_variables):
    # TODO: work on nodes instead of strings to have indentation correct
    logging.info("Extract code block to separate function: %s" % method_name)

    # create new def node
    create_str = "def " + method_name + "(" + ",".join(parameters) + "):"

    # add lines to def node
    for line in code_block:
        create_str += "\n    " + str(line.dumps())

    # add return statement
    if len(return_variables) > 0:
        create_str += "\n    " + "return " + ", ".join(return_variables)

    # return first node which is the complete def node
    return RedBaron(create_str)[0]
