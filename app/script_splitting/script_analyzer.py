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
#

from redbaron import RedBaron
from app import app
from app.script_splitting.Labels import Labels
import numpy as np
import logging


def get_labels(script, white_list, black_list):
    line_labels = [None] * len(script)
    quantum_objects = []

    for i in range(len(script)):
        line_label, quantum_objects = label_code_line(script, script[i], white_list, black_list, quantum_objects,
                                                      line_labels)
        logging.debug("%s --> %s" % (repr(script[i].dumps()), line_label))
        line_labels[i] = line_label

    splitting_labels = apply_threshold(script, line_labels)

    return splitting_labels


def label_code_line(root_baron, line_baron, white_list, black_list, quantum_objects, method_labels):
    logging.debug('Label code line: %s...' % repr(line_baron.dumps()))

    # handle imports
    if line_baron.type == 'import' or line_baron.type == 'from_import':
        return Labels.OTHER, quantum_objects

    # handle empty lines
    if line_baron.type == 'endl':
        return Labels.OTHER, quantum_objects

    # handle comments
    if line_baron.type == 'comment':
        return Labels.OTHER, quantum_objects

    # handle classical instructions
    if line_baron.type == 'if' or line_baron.type == 'while' \
            or line_baron.type == 'print' or line_baron.type == 'ifelseblock' or line_baron.type == 'tuple' \
            or line_baron.type == 'int' or line_baron.type == "list":
        logging.info('Basic Type. --> Classical!')
        return Labels.CLASSIC, quantum_objects

    # handle atomtrailers, i.e., method invocations and other basic elements
    if line_baron.type == 'atomtrailers':
        # retrieve identifier on the left to check if it is quantum-specific
        left_most_identifier = line_baron.value[0]
        logging.debug('Object on the left side of the atomtrailer node: %s' % left_most_identifier)

        # check if identifier is contained in the list with assigned quantum objects
        logging.debug('Check if %s is contained in %s: %s' % (
            str(line_baron.value[0]), quantum_objects, str(line_baron.value[0]) in quantum_objects))
        if str(line_baron.value[0]) in quantum_objects:
            logging.debug('Object already assigned as QUANTUM object!')
            return Labels.QUANTUM, quantum_objects
        else:
            logging.debug('Object is NOT assigned as quantum!')

        # check if identifier belongs to method invocation
        if line_baron.value[0] in method_labels:
            logging.debug('Object belongs to method invocation')
            return method_labels[line_baron.value[0]], quantum_objects

        # check if the atomtrailer uses an import that is part of a quantum library defined in the knowledge base
        if uses_quantum_import(line_baron.value[0], root_baron, white_list, black_list):
            return Labels.QUANTUM, quantum_objects
        else:
            return Labels.CLASSIC, quantum_objects

    # handle assignments
    if line_baron.type == 'assignment':

        # handle tuple assignments: a,b = c,d
        if line_baron.target.type == 'tuple':
            logging.debug('Found an assignment tuple. Check if right side elements are Quantum...')
            assignment_labels = []
            # handle all assignments separately
            for i in range(len(line_baron.target.value)):
                right_element = line_baron.value[i]
                left_element = line_baron.target[i]
                # recursively get labels for right part
                assignment_labels = label_code_line(root_baron, right_element, white_list, black_list, quantum_objects,
                                                    method_labels)
                logging.debug('Assignment_labels: %s' % str(assignment_labels))
                if Labels.QUANTUM in assignment_labels:
                    # if element on the right is from a quantum module then the target variable is quantum as well
                    logging.debug('"%s" is QUANTUM, thus, "%s" is QUANTUM as well.' % (right_element, left_element))
                    quantum_objects.append(left_element.value)
            return assignment_labels, quantum_objects

        # handle single element assignments
        elif line_baron.target.type == 'name':
            logging.debug('Found a single assignment. Check if right side is Quantum...')
            assignment_labels = label_code_line(root_baron, line_baron.value, white_list, black_list, quantum_objects,
                                                method_labels)
            # if assignment assigns a quantum object, the corresponding variable is stored
            if Labels.QUANTUM in assignment_labels:
                # if element on the right is from a quantum module then the target variable is quantum as well
                logging.debug(
                    '"%s" is QUANTUM, thus, "%s" is QUANTUM as well.' % (line_baron.value, line_baron.target.value))
                quantum_objects.append(line_baron.target.value)
            return assignment_labels, quantum_objects

    logging.error('Unexpected node type received: %s' % line_baron.type)
    return Labels.CLASSIC, quantum_objects


def uses_quantum_import(line_value, root_baron, white_list, black_list):
    import_statement = get_import_statement(line_value, root_baron)
    logging.info('Related module for line "%s" is: "%s"' % (line_value, import_statement))
    # check white and black list of knowledge base separately
    found_in_whitelist = is_in_knowledge_base(import_statement, white_list)
    found_in_blacklist = is_in_knowledge_base(import_statement, black_list)
    if found_in_whitelist:
        if found_in_blacklist:
            logging.info('Found module in whitelist but in blacklist, too. --> Classical!')
        else:
            logging.info('Found module in whitelist but not in blacklist. --> Quantum!')
    else:
        logging.info('Did not find module in whitelist. --> Classical!')
    # element must be in white list but not in blacklist
    return found_in_whitelist and not found_in_blacklist


def get_import_statement(line_value, root_baron):
    logging.info('Get module for %s...' % line_value)

    # Search through all 'from' imports and return matching modules
    # E.g.: from qiskit.visualization import plot_histogram --> return qiskit.visualization.plot_histogram
    as_imports = root_baron.find_all('import')
    for as_import in as_imports:
        for dottedAsNameNode in as_import.value:
            if dottedAsNameNode.target == line_value.value:
                return [value.value for value in dottedAsNameNode.value if value.type == 'name']

    # Search through all 'as' imports and return matching modules
    # E.g.: import qiskit as qs --> return qiskit
    from_imports = root_baron.find_all('from_import')
    for from_import in from_imports:
        for target in from_import.targets:
            if str(target.value) == str(line_value):
                import_parts = [value.value for value in from_import.value if value.type == 'name']
                import_parts.append(target.value)
                return import_parts

    # Return empty list since statement is not from any imported module
    return []


def is_in_knowledge_base(package_orig, knowledge_base):
    logging.info('Check if %s is part of %s' % (package_orig, knowledge_base))

    # if any parameter is not defined, log warning and return False
    if package_orig is None or knowledge_base is None:
        logging.warning("Search for %s in %s is invalid since one of both is None." % (package_orig, knowledge_base))
        return False

    # if search term is empty, return False
    if not package_orig:
        logging.debug("Search for empty list in knowledge base --> return False")
        return False

    # copy array to work on a copy instead of the original
    package_copy = package_orig[:]

    # Search in KB iteratively adding elements from package_orig to search term.
    # E.g.: packages_copy =  ['first','second','third']
    # Start to search for 'first' in KB. Continue with 'first.second', and finally search for 'first.second.third' in KB
    search_list = []
    while len(package_copy) > 0:
        search_list.append(package_copy.pop(0))
        if ".".join(search_list) in knowledge_base:
            return True

    return False


def apply_threshold(script, line_labels):
    logging.debug("Start relabeling with threshold=%s" % app.config["SPLITTING_THRESHOLD"])
    splitting_labels = line_labels[:]

    if Labels.CLASSIC not in line_labels:
        logging.warning("No relabeling necessary since it does not contain any classical parts!")
        return splitting_labels
    if Labels.QUANTUM not in line_labels:
        logging.warning("No relabeling necessary since it does not contain any quantum parts!")
        return splitting_labels

    # calculate number of classical lines before each quantum block and relabel if it is smaller than threshold
    classical_indices = []
    for i in range(len(script)):
        if line_labels[i] == Labels.QUANTUM:
            relabel_if_necessary(classical_indices, splitting_labels)
            classical_indices = []
        if line_labels[i] == Labels.CLASSIC:
            classical_indices.append(i)
    # calculate number of trailing classical lines and relabel if it is smaller than threshold
    relabel_if_necessary(classical_indices, splitting_labels)

    logging.debug("Labels without threshold %s" % line_labels)
    logging.debug("Labels with threshold(%s) %s" % (app.config["SPLITTING_THRESHOLD"], splitting_labels))

    return splitting_labels


def relabel_if_necessary(classical_indices, splitting_labels):
    if 0 < len(classical_indices) < app.config["SPLITTING_THRESHOLD"]:
        for classical_index in classical_indices:
            splitting_labels[classical_index] = Labels.QUANTUM
