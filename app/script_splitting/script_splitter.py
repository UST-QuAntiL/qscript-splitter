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
from app.script_splitting.Labels import Labels


def split_script(script, requirements, splitting_labels):

    code_blocks = identify_code_blocks(script, splitting_labels)

    result_workflow = [{"type": "start"}]
    result = {'extracted_parts': []}
    all_possible_return_variables = []

    i = 0
    for code_block in code_blocks:
        i += 1
        part = {'name': "part_" + str(i)}

        # Compute list of parameters
        parameters = compute_parameters(code_block, all_possible_return_variables)
        app.logger.info("Call arguments for code block %s: %s" % (i, parameters))

        # Compute list of return variables
        return_variables = compute_return_variables(code_block, script)
        all_possible_return_variables.extend(return_variables)
        app.logger.info("Return arguments for code block %s: %s" % (i, return_variables))

        # Generate new method from code block and append to result script
        method_name = "main"
        created_method = create_method(method_name, code_block, parameters, return_variables)
        part['app.py'] = created_method

        # Copy imports to extracted files
        part['requirements.txt'] = requirements

        # Add task to 'workflow'
        result_workflow.append({"type": "task", "part": part['name']})

        # Add part to result
        result['extracted_parts'].append(part)

    result_workflow.append({"type": "end"})
    result['workflow.json'] = result_workflow

    return result


def identify_code_blocks(script, splitting_labels):
    list_of_all_code_blocks = []
    code_block = []
    current_label = None
    prevent_split = 0
    for node in script:
        label = splitting_labels[node]

        # Handle loops and if blocks (only if they are hybrid – otherwise they are labeled Quantum/Classical)
        if label in [Labels.LOOP, Labels.IF_ELSE_BLOCK]:
            continue

        if label == Labels.START_PREVENT_SPLIT:
            prevent_split = 2
            continue
        if label == Labels.END_PREVENT_SPLIT:
            prevent_split = 0
            continue
        # Skip imports
        if label == Labels.IMPORTS:
            continue
        # Add empty lines to code block, too
        if label == Labels.NO_CODE:
            # code_block_indices.append(i)
            continue

        # Tag label of first block
        if current_label is None:
            current_label = label

        # Start new code block if label changes
        # Only for first line in protected block (prevent_split == 2) or outside protected block (prevented_split <= 0)
        if prevent_split != 1:
            prevent_split -= 1
            if len(code_block) > 0 and (label == Labels.FORCE_SPLIT or label != current_label):
                list_of_all_code_blocks.append(code_block[:])
                code_block = []
            if label == Labels.FORCE_SPLIT:
                current_label = None
            else:
                current_label = label

        # Add line to code block
        code_block.append(node)

    # Add last code block
    list_of_all_code_blocks.append(code_block[:])

    return list_of_all_code_blocks


def compute_return_variables(code_block, script):
    remaining_block = script[:]
    # TODO pop code_block

    # TODO check recursively
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

    # TODO: Bug if a line.value is a simple int or string, recursive call will result in wrong type which is not indexable
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


def create_method(method_name, code_block, parameters, return_variables):
    app.logger.info("Extract code block to separate function.")

    # Create new def node
    method = RedBaron("def " + method_name + "(" + ", ".join(parameters) + "):\n    pass")[0]
    # Method body cannot be empty during creation
    method.value = '1+1'

    for node in code_block:
        indent(node)
        method.append(node)

    # Add return statement
    if len(return_variables) > 0:
        app.logger.debug("Add return statement to method")
        method.append(RedBaron("return " + ", ".join(return_variables)))

    return method


def indent(node):
    try:
        node.increase_indentation(4)
    except AttributeError:
        print(node.help())
    if node.type in ['ifelseblock', 'if', 'elif', 'else', 'while', 'for']:
        for block in node.value:
            indent(block)
