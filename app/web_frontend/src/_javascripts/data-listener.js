'use strict';

(function (window) {
  function DataListener() {
    this.dataFunctions = {};
    this.functionOptions = {};
    this.params = {};
  }

  function findComponentId(cid) {
    return $('#' + cid).parents('*[data-domtype="component"]').attr("id");
  }

  function exec(fc, params, options) {
    fc(params);
  }

  DataListener.prototype.addDataFunction = function (cid, f, options) {
    var id = findComponentId(cid);
    if (this.dataFunctions[id]) {
      this.dataFunctions[id].push(f);
      this.functionOptions[id].push(options);
    } else {
      this.dataFunctions[id] = [f];
      this.functionOptions[id] = [options];
    }
  };

  DataListener.prototype.execDataFunction = function (id, params) {
    if (id) {
      var fs = this.dataFunctions[id];
      var options = this.functionOptions[id];
      fs.forEach(function (item) {
        exec(item, params, options);
      });
    } else {
      for (var key in this.dataFunctions) {
        var fs = this.dataFunctions[key];
        var options = this.functionOptions[key];
        fs.forEach(function (item) {
          exec(item, params, options);
        });
      }
    }
  };

  DataListener.prototype.setGlobalParams = function (params) {
    this.params = params;
  };

  DataListener.prototype.getGlobalParams = function () {
    return this.params;
  };

  window.DataListener = new DataListener();
})(window);
