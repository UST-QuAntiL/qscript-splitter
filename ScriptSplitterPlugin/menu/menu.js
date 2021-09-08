/**
* add menu entry
*/
module.exports = function(electronApp, menuState) {
  return [{
    label: 'Execute ScriptSplitter',
    enabled: function() {
      // only enabled for BPMN diagrams
      return menuState.bpmn;
    },
    action: function(){
      test(); 
    }
  }];
};


/**
* create my shapes here
* e.g. this creates a template for the moment.
*/
function test(){
  console.log("hurra")
}