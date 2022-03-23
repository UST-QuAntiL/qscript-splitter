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
    for node in script:
        app.logger.debug("%s: %s" % (splitting_labels[node], repr(node)))

    code_blocks, sizes = identify_code_blocks_new(splitting_labels)
    app.logger.debug("Code block sizes: %s" % sizes)

    preamble = []
    result_script = []
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
        created_method = create_method(code_block, method_name, parameters, return_variables)
        part['app.py'] = created_method

        print(created_method.dumps())

        # Copy imports to extracted files
        part['requirements.txt'] = requirements

        # Generate imports into base file
        app.logger.debug("Insert import to extracted file into base script")
        import_as_name = part['name']
        preamble.append(RedBaron('from ' + part['name'] + '.app import ' + method_name + ' as ' + import_as_name)[0])

        # Generate method call from method and append to result script
        method_call = ""
        if len(return_variables) > 0:
            method_call += ", ".join(return_variables) + " = "
        method_call += import_as_name + "(" + ", ".join(parameters) + ")"
        app.logger.debug("Insert method call for created method: %s" % method_call)
        result_script.append(RedBaron(method_call)[0])

        result_workflow.append({"type": "task", "part": part['name']})

        result['extracted_parts'].append(part)

    preamble.extend(result_script)
    result['base_script.py'] = preamble
    result_workflow.append({"type": "end"})
    result['workflow.json'] = result_workflow

    return result


def identify_code_blocks_new(splitting_labels):
    sizes = []
    result = []
    block = []
    for key, value in splitting_labels.items():
        block.append(key)
    result.append(block)
    sizes.append(len(block))
    return result, sizes


def identify_code_blocks(splitting_labels):
    list_of_all_code_block_indices = []
    code_block_indices = []
    current_label = None
    prevent_split = 0
    for i in range(len(splitting_labels)):
        label = splitting_labels[i]

        if type(label) is list:
            if len(code_block_indices) > 0:
                list_of_all_code_block_indices.append(code_block_indices[:])
                code_block_indices = []
            current_label = None
            if label[0] is list:
                app.logger.debug("We have an if-Block here!: %s" % label)
                for element in label:
                    x = identify_code_blocks(element)
            else:
                app.logger.debug("We have a while-Loop here!: %s" % label)
                x = identify_code_blocks(label)
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
            if len(code_block_indices) > 0 and (label == Labels.FORCE_SPLIT or label != current_label):
                list_of_all_code_block_indices.append(code_block_indices[:])
                code_block_indices = []
            if label == Labels.FORCE_SPLIT:
                current_label = None
            else:
                current_label = label

        # Add line to code block
        code_block_indices.append(i)

    # Add last code block
    list_of_all_code_block_indices.append(code_block_indices[:])

    return list_of_all_code_block_indices


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


def create_method(code_block, method_name, parameters, return_variables):
    app.logger.info("Extract code block to separate function: %s" % method_name)

    # Create new def node
    method = RedBaron("def " + method_name + "(" + ", ".join(parameters) + "):\n    pass")[0]
    # Method cannot be empty during creation. Thus, pop the first line 'pass' now
    method.value.pop(0)

    # Add all lines of code block to def node
    for line in code_block:
        app.logger.debug("Add line to method: %s" % repr(line.dumps()))
        method.value.append(line)

    # Add return statement
    if len(return_variables) > 0:
        app.logger.debug("Add return statement to method")
        method.value.append(RedBaron("return " + ", ".join(return_variables)))

    return RedBaron(method)
