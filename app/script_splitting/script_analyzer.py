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


class ScriptAnalyzer:

    ROOT_SCRIPT = None
    WHITE_LIST = None
    BLACK_LIST = None
    QUANTUM_OBJECTS = []

    def __init__(self, script, white_list, black_list):
        self.ROOT_SCRIPT = script
        self.WHITE_LIST = white_list
        self.BLACK_LIST = black_list

    def get_labels(self):
        # Get Initial labels
        labels = self.get_initial_labels(self.ROOT_SCRIPT)
        app.logger.debug("Initial Labels:")

        for key, value in labels.items():
            app.logger.debug("LABEL: %s - %s" % (value, repr(key.dumps())))

        # If code blocks (ifs, whiles, etc.) are not hybrid, their explicit label is changed to QUANTUM/CLASSICAL
        dirty = True
        max_iterations = 0
        while dirty and max_iterations < 10:
            relabel_code_blocks_if_not_hybrid(self.ROOT_SCRIPT, labels)
            print("\nLabels after relabeling: %s" % labels)
            for key, value in labels.items():
                print("LABEL: %s - %s" % (value, repr(key.dumps())))

            # Apply threshold to labels
            dirty = apply_threshold(self.ROOT_SCRIPT, labels)
            print("\nLabels after applying threshold: %s" % labels)

            for key, value in labels.items():
                print("LABEL: %s - %s" % (value, repr(key.dumps())))

            max_iterations += 1

        return labels

    def get_initial_labels(self, script):
        labels = {}

        for baron_node in script:
            app.logger.debug('Label code line: %s...' % repr(baron_node.dumps()))

            # Handle imports
            if baron_node.type in ['import', 'from_import']:
                app.logger.debug('Found import --> IMPORT')
                labels[baron_node] = Labels.IMPORTS

            # Handle splitting markers
            elif baron_node.type == 'comment':
                if baron_node.value == '# ---start prevent split---':
                    labels[baron_node] = Labels.START_PREVENT_SPLIT
                elif baron_node.value == '# ---end prevent split---':
                    labels[baron_node] = Labels.START_PREVENT_SPLIT
                elif baron_node.value == '# ---force split---':
                    labels[baron_node] = Labels.FORCE_SPLIT
                else:
                    labels[baron_node] = Labels.NO_CODE

            # Handle empty lines and comments
            elif baron_node.type in ['endl']:
                app.logger.debug('Empty Line or Comment --> NO_CODE')
                labels[baron_node] = Labels.NO_CODE

            # Handle if-else-blocks
            elif baron_node.type in ['ifelseblock']:
                app.logger.info('Found ifelse code block --> Handle recursively')
                labels[baron_node] = Labels.IF_ELSE_BLOCK
                for if_else_node in baron_node.value:
                    code_block = if_else_node.value
                    sub_labels = self.get_initial_labels(code_block)
                    labels.update(sub_labels)

            # Handle while-/for-loops
            elif baron_node.type in ['while', 'for']:
                app.logger.info('Found while/for code block --> Handle recursively')
                labels[baron_node] = Labels.LOOP
                code_block = baron_node.value
                sub_labels = self.get_initial_labels(code_block)
                labels.update(sub_labels)

            # Handle basic classical instructions
            elif baron_node.type in ['print', 'tuple', 'int', 'list', 'del']:
                app.logger.info('Basic Type. --> CLASSICAL!')
                labels[baron_node] = Labels.CLASSICAL

            # Handle assignments
            elif baron_node.type == 'assignment':
                if baron_node.value.type != 'atomtrailers':
                    app.logger.error('Unexpected node type received: %s' % baron_node.value.type)
                label = self.handle_atomic_trailer_nodes(baron_node.value)
                labels[baron_node] = label
                if label == Labels.QUANTUM:
                    app.logger.debug(
                        '"%s" is QUANTUM, thus, "%s" is QUANTUM as well.' % (baron_node.value, baron_node.target.value))
                    self.QUANTUM_OBJECTS.append(baron_node.target.value)

            # Handle atomtrailers
            elif baron_node.type == 'atomtrailers':
                label = self.handle_atomic_trailer_nodes(baron_node)
                labels[baron_node] = label

            else:
                app.logger.error('Unexpected node type received: %s' % baron_node.type)
                labels[baron_node] = Labels.CLASSICAL

        return labels

    def handle_atomic_trailer_nodes(self, atom_trailers_node):
        # Retrieve identifier on the left to check if it is quantum-specific
        try:
            left_most_identifier = atom_trailers_node.value[0]
        except IndexError:
            return Labels.CLASSICAL
        app.logger.debug('Object on the left side of the atomtrailer node: %s' % left_most_identifier)

        # Check if identifier is contained in the list with assigned quantum objects
        app.logger.debug('Check if %s is contained in %s: %s' % (
            str(atom_trailers_node.value[0]), self.QUANTUM_OBJECTS, str(atom_trailers_node.value[0]) in self.QUANTUM_OBJECTS))
        if str(atom_trailers_node.value[0]) in self.QUANTUM_OBJECTS:
            app.logger.debug('Object already assigned as QUANTUM object!')
            return Labels.QUANTUM
        else:
            app.logger.debug('Object is NOT yet assigned as quantum!')

        # Check if the atomtrailer uses an import that is part of a quantum library defined in the knowledge base
        if self.uses_quantum_import(atom_trailers_node.value[0]):
            return Labels.QUANTUM
        else:
            return Labels.CLASSICAL

    def uses_quantum_import(self, line_value):
        import_statement = get_import_statement(line_value, self.ROOT_SCRIPT)
        app.logger.info('Related module for line "%s" is: "%s"' % (line_value, import_statement))

        # Check white and black list of knowledge bases separately
        found_in_whitelist = is_in_knowledge_base(import_statement, self.WHITE_LIST)
        found_in_blacklist = is_in_knowledge_base(import_statement, self.BLACK_LIST)
        if found_in_whitelist:
            if found_in_blacklist:
                app.logger.info('Found module in whitelist but in blacklist, too. --> Classical!')
            else:
                app.logger.info('Found module in whitelist but not in blacklist. --> Quantum!')
        else:
            app.logger.info('Did not find module in whitelist. --> Classical!')

        # Element must be in white list but not in blacklist
        return found_in_whitelist and not found_in_blacklist


def get_import_statement(line_value, script):
    app.logger.info('Get module for %s...' % line_value)

    # Search through all 'from' imports and return matching modules
    # E.g.: from qiskit.visualization import plot_histogram --> return qiskit.visualization.plot_histogram
    as_imports = script.find_all('import')
    for as_import in as_imports:
        for dottedAsNameNode in as_import.value:
            if hasattr(line_value, 'value') and dottedAsNameNode.target == line_value.value:
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

    # If search term is empty, return False
    if not package_orig:
        app.logger.debug("Search for empty list in knowledge base --> return False")
        return False

    # Copy array to work on a copy instead of the original
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


def relabel_code_blocks_if_not_hybrid(script, splitting_labels):
    found_quantum = False
    found_classical = False
    found_hybrid = False

    for node in script:
        if node not in splitting_labels:
            continue

        # Handle ifs recursively
        if splitting_labels[node] == Labels.IF_ELSE_BLOCK:
            labels = []
            for block in node.value:
                label = relabel_code_blocks_if_not_hybrid(block, splitting_labels)
                labels.append(label)
            if "hybrid" not in labels:
                if Labels.QUANTUM not in labels:
                    splitting_labels[node] = Labels.CLASSICAL
                elif Labels.CLASSICAL not in labels:
                    splitting_labels[node] = Labels.QUANTUM

        # Handle loops recursively
        elif splitting_labels[node] == Labels.LOOP:
            label = relabel_code_blocks_if_not_hybrid(node.value, splitting_labels)
            if label == Labels.QUANTUM:
                splitting_labels[node] = Labels.QUANTUM
            elif label == Labels.CLASSICAL:
                splitting_labels[node] = Labels.CLASSICAL

        # If any one node in the list is Quantum/Classical, set found_quantum/found_classical to true
        if splitting_labels[node] == Labels.QUANTUM:
            found_quantum = True
        elif splitting_labels[node] == Labels.CLASSICAL:
            found_classical = True
        elif splitting_labels[node] in [Labels.IF_ELSE_BLOCK, Labels.LOOP]:
            found_hybrid = True

    if found_hybrid:
        return "hybrid"
    if found_quantum and not found_classical:
        return Labels.QUANTUM
    if found_classical and not found_quantum:
        return Labels.CLASSICAL
    return "hybrid"



def relabel_code_blocks_if_not_hybrid_old(script, splitting_labels, parent=None):
    found_quantum = False
    found_classical = False
    found_hybrid = False
    for node in script:
        if node not in splitting_labels:
            continue
        # Handle ifs recursively
        if splitting_labels[node] == Labels.IF_ELSE_BLOCK:
            for block in node.value:
                relabel_code_blocks_if_not_hybrid(block, splitting_labels, node)
        # Handle loops recursively
        elif splitting_labels[node] == Labels.LOOP:
            relabel_code_blocks_if_not_hybrid(node.value, splitting_labels, node)

        # If any one node in the list is Quantum/Classical, set found_quantum/found_classical to true
        if splitting_labels[node] == Labels.QUANTUM:
            found_quantum = True
        elif splitting_labels[node] == Labels.CLASSICAL:
            found_classical = True
        elif splitting_labels[node] in [Labels.IF_ELSE_BLOCK, Labels.LOOP]:
            found_hybrid = True

    if found_hybrid or (found_quantum and found_classical):
        return

    # False for the first iteration where parent is root
    if parent is not None and parent in splitting_labels:
        # Relabel if only quantum labels were found
        if found_quantum and not found_classical:
            app.logger.debug('Relabel %s from %s to QUANTUM since it only contains quantum nodes' % (repr(parent.dumps()), splitting_labels[parent]))
            splitting_labels[parent] = Labels.QUANTUM
        # Relabel if only classical labels were found
        elif found_classical and not found_quantum:
            app.logger.debug('Relabel %s from %s to CLASSICAL since it only contains classical nodes' % (repr(parent.dumps()), splitting_labels[parent]))
            splitting_labels[parent] = Labels.CLASSICAL


def apply_threshold(script, splitting_labels):
    app.logger.debug("Start relabeling with threshold=%s..." % app.config["SPLITTING_THRESHOLD"])
    result = False

    # Calculate number of classical lines before each quantum block and relabel if it is smaller than threshold
    classical_nodes = []
    any_quantum = False
    for node in script:
        if node not in splitting_labels:
            continue

        # Handle if-else-blocks recursively. Do not relabel preceding classical.
        if splitting_labels[node] == Labels.IF_ELSE_BLOCK:
            for block in node.value:
                result = result or apply_threshold(block.value, splitting_labels)
            classical_nodes = []

        # Handle while-/for-blocks recursively. Do not relabel preceding classical.
        if splitting_labels[node] == Labels.LOOP:
            result = result or apply_threshold(node.value, splitting_labels)
            classical_nodes = []

        # If a quantum label if found, relabel preceding classical nodes (when threshold is missed)
        if splitting_labels[node] == Labels.QUANTUM:
            result = result or relabel_if_threshold_not_reached(classical_nodes, splitting_labels)
            classical_nodes = []
            any_quantum = True

        # Add classical labels to list of 'preceding' classical_nodes
        if splitting_labels[node] == Labels.CLASSICAL:
            classical_nodes.append(node)

    # Calculate number of trailing classical lines and relabel if it is smaller than threshold.
    # For code blocks only containing classical elements, any_quantum is False.
    if any_quantum:
        result = result or relabel_if_threshold_not_reached(classical_nodes, splitting_labels)

    return result


def relabel_if_threshold_not_reached(classical_nodes, splitting_labels):
    result = False
    # Code blocks (ifs, whiles, etc.) also have additional code lines counted for threshold
    weight = 0
    for node in classical_nodes:
        weight += calc_weight(node)

    # Relabel classical nodes if threshold is not reached
    if 0 < weight < app.config["SPLITTING_THRESHOLD"]:
        for node in classical_nodes:
            if node in splitting_labels and splitting_labels[node] != Labels.QUANTUM:
                relabel(node, splitting_labels)
                result = True
    return result


def relabel(node, splitting_labels):
    splitting_labels[node] = Labels.QUANTUM
    # Relabel if-else-blocks recursively
    if splitting_labels[node] == Labels.IF_ELSE_BLOCK:
        for block in node.value:
            for x in block.value:
                if x in splitting_labels:
                    relabel(x, splitting_labels)
    # Relabel while-/for-blocks recursively
    if splitting_labels[node] == Labels.LOOP:
        for block in node.value:
            if block in splitting_labels:
                relabel(block, splitting_labels)


def calc_weight(node):
    weight = 1
    if node.type == 'ifelseblock':
        for block in node.value:
            weight -= 1
            for x in block.value:
                weight += calc_weight(x)
    if node.type in ['while', 'for']:
        weight -= 1
        for block in node.value:
            weight += calc_weight(block)
    return weight
