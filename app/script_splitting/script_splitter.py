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

import random
import string
import os

from redbaron import RedBaron

from app import app
from app.script_splitting.Labels import Labels
from app.script_splitting.polling_agent_generator import generate_polling_agent


class ScriptSplitter:

    ROOT_SCRIPT = None
    REQUIREMENTS = None
    SPLITTING_LABELS = None
    integrated_blocks = []
    all_possible_return_variables = []
    iterators = []
    all_imports =[]

    def __init__(self, script, requirements, splitting_labels):
        self.ROOT_SCRIPT = script
        self.REQUIREMENTS = requirements
        self.SPLITTING_LABELS = splitting_labels

    def split_script(self):
        code_blocks = self.identify_code_blocks(self.ROOT_SCRIPT)
        for line in self.ROOT_SCRIPT:
            if self.SPLITTING_LABELS[line] == Labels.IMPORTS:
                self.all_imports.append(line)

        result_workflow = [{"type": "start", "variables": []}]
        script_parts = self.build_base_script(self.ROOT_SCRIPT, code_blocks, result_workflow)
        result_workflow.append({"type": "end"})

        for x in result_workflow:
            app.logger.debug(x)

        return {'extracted_parts': script_parts, 'workflow.json': result_workflow, 'iterators': self.iterators}

    def build_base_script(self, nodes, code_blocks, result_workflow):
        script_parts = []
        for node in nodes:
            # if node is not in any code block
            if which_code_block(node, code_blocks) == -1:
                if node in self.SPLITTING_LABELS and self.SPLITTING_LABELS[node] == Labels.LOOP:
                    if node.type == "while":
                        result_workflow.append({"type": "start_while", "condition": node.test.dumps()})
                        sub_parts = self.build_base_script(node, code_blocks, result_workflow)
                        script_parts.extend(sub_parts)
                        result_workflow.append({"type": "end_while"})
                    elif node.type == "for":
                        iterator = self.gen_iterator(node.target.dumps())
                        result_workflow[0]['variables'].append(iterator['name'] + "_var")
                        result_workflow[0]['variables'].append(iterator['name'] + "_elem")
                        result_workflow.append({"type": "start_for", "iterator": iterator['name'], "iterator_script": iterator['name']+".js"})
                        self.iterators.append(iterator)
                        sub_parts = self.build_base_script(node, code_blocks, result_workflow)
                        script_parts.extend(sub_parts)
                        result_workflow.append({"type": "end_for"})
                elif node in self.SPLITTING_LABELS and self.SPLITTING_LABELS[node] == Labels.IF_ELSE_BLOCK:
                    for block in node.value:
                        if block.type == "if":
                            result_workflow.append({"type": "start_if", "condition": block.test.dumps()})
                        elif block.type == "elif":
                            result_workflow.append({"type": "else_if", "condition": block.test.dumps()})
                        elif block.type == "else":
                            result_workflow.append({"type": "else"})
                        sub_parts = self.build_base_script(block, code_blocks, result_workflow)
                        script_parts.extend(sub_parts)
                    result_workflow.append({"type": "end_if"})
                else:
                    pass
            else:
                code_block = code_blocks[which_code_block(node, code_blocks)]
                if code_block not in self.integrated_blocks:
                    part = self.gen_part_from_block(code_block)
                    script_parts.append(part)
                    result_workflow.append({"type": "task", "file": part['name']})
                self.integrated_blocks.append(code_block)
        return script_parts

    def gen_iterator(self, list):
        iterator_name = "it_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        iterator_template_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "templates", "iterator_script.js")
        with open(iterator_template_path, "r") as file:
            iterator_template = file.read()
        iterator_template = iterator_template.replace("### LIST ###", list)
        iterator_template = iterator_template.replace("### ITERATOR VARIABLE ###", iterator_name + "_var")
        iterator_template = iterator_template.replace("### ITERATOR ELEMENT ###", iterator_name + "_elem")

        return {'name': iterator_name, 'file': iterator_template}

    def gen_part_from_block(self, code_block):
        part = {'name': "part_" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))}

        # TODO only import the needed packages
        preamble = self.all_imports[:]

        # Compute list of parameters
        parameters = self.compute_parameters(code_block)
        app.logger.info("Call arguments for code block: %s" % parameters)

        # Compute list of return variables
        return_variables = self.compute_return_variables(code_block)
        self.all_possible_return_variables.extend(return_variables)

        # Generate new method from code block and append to result script
        method_name = "main"
        created_method = create_method(method_name, code_block, parameters, return_variables)
        preamble.append(created_method)
        part['app.py'] = preamble

        part['requirements.txt'] = self.REQUIREMENTS

        part['polling_agent.py'] = generate_polling_agent(parameters, return_variables)

        return part

    def identify_code_blocks(self, nodes):
        list_of_all_code_blocks = []
        code_block = []
        current_label = None
        prevent_split = 0
        for node in nodes:
            if node not in self.SPLITTING_LABELS:
                continue
            label = self.SPLITTING_LABELS[node]

            # Handle loops (only if they are hybrid – otherwise they are labeled Quantum/Classical)
            if label == Labels.LOOP:
                # Close current code block and start new one
                list_of_all_code_blocks.append(code_block[:])
                code_block = []
                # Compute code blocks recursively and add to result
                sub_blocks = self.identify_code_blocks(node)
                list_of_all_code_blocks.extend(sub_blocks)
                continue

            # Handle if-else-blocks (only if they are hybrid - otherwise they are labels Quantum/Classical)
            if label == Labels.IF_ELSE_BLOCK:
                # Close current code block and start new one
                list_of_all_code_blocks.append(code_block[:])
                code_block = []
                # Compute code blocks recursively and add to result
                for block in node.value:
                    sub_blocks = self.identify_code_blocks(block)
                    list_of_all_code_blocks.extend(sub_blocks)
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

            # Start new code block if label changes but only for first line in protected block (prevent_split == 2)
            # or outside protected block (prevented_split <= 0)
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

    def compute_return_variables(self, code_block):
        app.logger.debug("Compute return variables for %s" % code_block)

        # TODO check recursively
        initialized_variables = []
        for line in code_block:
            if line.type == "assignment":
                initialized_variables.append(str(line.target.name))

        app.logger.debug("All initialized variables: %s" % initialized_variables)

        result = []
        for line in self.ROOT_SCRIPT:
            for variable in initialized_variables:
                if is_used_in_line(variable, line) and str(variable) not in result:
                    result.append(str(variable))

        app.logger.debug("Return variables: %s" % result)

        return result

    def compute_parameters(self, code_block):
        parameters = []

        app.logger.debug("Compute parameters for %s" % code_block)
        try:
            for line in code_block:
                app.logger.debug("Scan line for parameters: %s" % line)
                if line.type == "assignment":
                    app.logger.debug("Is an assignment... call recursively with right part.")
                    param_list = self.compute_parameters(line.value)
                    for element in param_list:
                        app.logger.debug("element %s in list %s" % (element, param_list))
                        if element not in parameters:
                            parameters.append(element)
                    continue
                if line.type in ['comment', 'endl', 'import']:
                    continue
                app.logger.debug("All possible return variables: %s" % self.all_possible_return_variables)
                for variable in self.all_possible_return_variables:
                    app.logger.debug("Check if %s is used in line %s. (%s)" % (variable, line, is_used_in_line(variable, line)))
                    if is_used_in_line(variable, line) and str(variable) not in parameters:
                        parameters.append(str(variable))
        except TypeError:
            app.logger.debug(code_block, 'is not iterable')
            # TODO: If a line.value is a simple int or string, recursive call will result in wrong type which is not indexable

        return parameters


def is_used_in_line(variable, line):
    found = line.find_all("NameNode", value=variable)
    # TODO: NameNode includes function calls as well, thus, only search for variables.
    #  The current implementation, however, might return unnecessary variables as well.
    return len(found) > 0


def create_method(method_name, code_block, parameters, return_variables):
    app.logger.info("Extract code block to separate function.")

    # Create new def node
    method = RedBaron("def " + method_name + "(" + ", ".join(parameters) + "):\n    pass")[0]
    # Method body cannot be empty during creation
    method.pop(0)

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
        pass
    if node.type in ['ifelseblock', 'if', 'elif', 'else', 'while', 'for']:
        for block in node.value:
            indent(block)


def which_code_block(node, code_blocks):
    for i in range(len(code_blocks)):
        if node in code_blocks[i]:
            return i
    return -1
