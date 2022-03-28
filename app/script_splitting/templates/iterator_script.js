const list = JSON.parse('### LIST ###');
const iterator_variable = '### ITERATOR VARIABLE ###';
const iterator_element = '### ITERATOR ELEMENT ###';

iterator = parseInt(execution.getVariable(iterator_variable));
if (iterator == null) {
    iterator = 0;
}
iterator++;
execution.setVariable(iterator_variable, iterator);

element = null;
if (iterator < list.length){
    element = list[iterator];
}
execution.setVariable(iterator_element, element);