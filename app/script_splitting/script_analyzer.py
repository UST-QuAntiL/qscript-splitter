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

from app import app
from app.script_splitting.Labels import Labels


def get_labels(script, white_list, black_list):
    line_labels = []
    quantum_objects = []

    for line_baron in script:
        app.logger.debug('Label code line: %s...' % repr(line_baron.dumps()))

        # handle imports, comments, and black lines
        if line_baron.type in ['import', 'from_import']:
            app.logger.debug('Found import --> IMPORT')
            label = Labels.IMPORTS

        elif line_baron.type in ['endl', 'comment']:
            app.logger.debug('Empty Line or Comment --> NO_CODE')
            label = Labels.NO_CODE

        # handle basic classical instructions
        elif line_baron.type in ['if', 'while', 'print', 'ifelseblock', 'tuple', 'int', 'list']:
            app.logger.info('Basic Type. --> CLASSICAL!')
            label = Labels.CLASSIC

        # handle assignments
        elif line_baron.type == 'assignment':
            if line_baron.value.type != 'atomtrailers':
                app.logger.error('Unexpected node type received: %s' % line_baron.value.type)
            label = handle_atomic_trailer_nodes(line_baron.value, script, white_list, black_list, quantum_objects)
            if label == Labels.QUANTUM:
                app.logger.debug('"%s" is QUANTUM, thus, "%s" is QUANTUM as well.' % (line_baron.value, line_baron.target.value))
                quantum_objects.append(line_baron.target.value)

        # handle atomtrailers
        elif line_baron.type == 'atomtrailers':
            label = handle_atomic_trailer_nodes(line_baron, script, white_list, black_list, quantum_objects)

        else:
            app.logger.error('Unexpected node type received: %s' % line_baron.type)
            label = Labels.NO_CODE

        line_labels.append(label)

    splitting_labels = apply_threshold(script, line_labels)

    return splitting_labels


def handle_atomic_trailer_nodes(atom_trailers_node, script, white_list, black_list, quantum_objects):
    # retrieve identifier on the left to check if it is quantum-specific
    left_most_identifier = atom_trailers_node.value[0]
    app.logger.debug('Object on the left side of the atomtrailer node: %s' % left_most_identifier)

    # check if identifier is contained in the list with assigned quantum objects
    app.logger.debug('Check if %s is contained in %s: %s' % (
        str(atom_trailers_node.value[0]), quantum_objects, str(atom_trailers_node.value[0]) in quantum_objects))
    if str(atom_trailers_node.value[0]) in quantum_objects:
        app.logger.debug('Object already assigned as QUANTUM object!')
        return Labels.QUANTUM
    else:
        app.logger.debug('Object is NOT yet assigned as quantum!')

    # check if the atomtrailer uses an import that is part of a quantum library defined in the knowledge base
    if uses_quantum_import(atom_trailers_node.value[0], script, white_list, black_list):
        return Labels.QUANTUM
    else:
        return Labels.CLASSIC


def uses_quantum_import(line_value, script, white_list, black_list):
    import_statement = get_import_statement(line_value, script)
    app.logger.info('Related module for line "%s" is: "%s"' % (line_value, import_statement))
    # check white and black list of knowledge bases separately
    found_in_whitelist = is_in_knowledge_base(import_statement, white_list)
    found_in_blacklist = is_in_knowledge_base(import_statement, black_list)
    if found_in_whitelist:
        if found_in_blacklist:
            app.logger.info('Found module in whitelist but in blacklist, too. --> Classical!')
        else:
            app.logger.info('Found module in whitelist but not in blacklist. --> Quantum!')
    else:
        app.logger.info('Did not find module in whitelist. --> Classical!')
    # element must be in white list but not in blacklist
    return found_in_whitelist and not found_in_blacklist


def get_import_statement(line_value, script):
    app.logger.info('Get module for %s...' % line_value)

    # Search through all 'from' imports and return matching modules
    # E.g.: from qiskit.visualization import plot_histogram --> return qiskit.visualization.plot_histogram
    as_imports = script.find_all('import')
    for as_import in as_imports:
        for dottedAsNameNode in as_import.value:
            if dottedAsNameNode.target == line_value.value:
                return [value.value for value in dottedAsNameNode.value if value.type == 'name']

    # Search through all 'as' imports and return matching modules
    # E.g.: import qiskit as qs --> return qiskit
    from_imports = script.find_all('from_import')
    for from_import in from_imports:
        for target in from_import.targets:
            if str(target.value) == str(line_value):
                import_parts = [value.value for value in from_import.value if value.type == 'name']
                import_parts.append(target.value)
                return import_parts

    # Return empty list since statement is not from any imported module
    return []


def is_in_knowledge_base(package_orig, knowledge_base):
    # if any parameter is not defined, log warning and return False
    if package_orig is None or knowledge_base is None:
        app.logger.warning("Search for %s in %s is invalid since one of both is None." % (package_orig, knowledge_base))
        return False

    # if search term is empty, return False
    if not package_orig:
        app.logger.debug("Search for empty list in knowledge base --> return False")
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
    app.logger.debug("Start relabeling with threshold=%s..." % app.config["SPLITTING_THRESHOLD"])
    splitting_labels = line_labels[:]

    # if code is not hybrid, no splitting is necessary
    if Labels.CLASSIC not in line_labels:
        app.logger.warning("No relabeling necessary since it does not contain any classical parts!")
        return splitting_labels
    if Labels.QUANTUM not in line_labels:
        app.logger.warning("No relabeling necessary since it does not contain any quantum parts!")
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

    app.logger.debug("Labels without threshold: %s" % line_labels)
    app.logger.debug("Labels with threshold(%s): %s" % (app.config["SPLITTING_THRESHOLD"], splitting_labels))

    return splitting_labels


def relabel_if_necessary(classical_indices, splitting_labels):
    if 0 < len(classical_indices) < app.config["SPLITTING_THRESHOLD"]:
        for classical_index in classical_indices:
            splitting_labels[classical_index] = Labels.QUANTUM
