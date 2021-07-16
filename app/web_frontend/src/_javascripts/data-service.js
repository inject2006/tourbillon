'use strict';

(function (window) {
  function DataService() {
    this.service_host = window.zeusServerHost;
  }

  function getToken() {
    return localStorage['zeus_token'];
  }

  DataService.prototype.getHost = function () {
    return this.service_host;
  };

  DataService.prototype.get = function (options, success, error) {
    var self = this;
    $.ajax({
      url: self.service_host + options.url,
      method: 'get',
      headers: { 'Zeus-Token': getToken() },
      data: options.data
    }).success(function (data) {
      if (success) {
        success(data);
      }
    }).error(function (data) {
      if (error) {
        error(data);
      }
      if (data.status === 401) {
        AuthService.clean();
        document.location.reload();
      }
    });
  };

  DataService.prototype.post = function (options, done, fail) {
    var self = this;
    $.ajax({
      url: self.service_host + options.url,
      method: 'POST',
      headers: { 'zeus-token': getToken() },
      contentType: 'application/json',
      data: JSON.stringify(options.data)
    }).done(function (data) {
      if (done) {
        done(data);
      }
    }).fail(function (data) {
      if (fail) {
        fail(data);
      }
      if (data.status === 401) {
        AuthService.clean();
        document.location.reload();
      }
    });
  };

  window.DataService = new DataService();
})(window);