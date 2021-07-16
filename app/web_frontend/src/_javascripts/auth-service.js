'use strict';

(function (window) {
  function AuthService() {}

  AuthService.prototype.setAuth = function (token, username, expired) {
    localStorage['zeus_token'] = token;
    localStorage['zeus_username'] = username;
    localStorage['zeus_expired'] = expired;
  };

  AuthService.prototype.getAuth = function () {
    var token = localStorage['zeus_token'];
    var expired = localStorage['zeus_expired'];
    return {
      token: token,
      expired: expired
    };
  };

  AuthService.prototype.logout = function () {
    window.AuthService.clean();
    window.location.reload();
  };

  AuthService.prototype.clean = function () {
    localStorage['zeus_token'] = undefined;
    localStorage['zeus_expired'] = undefined;
    localStorage['zeus_username'] = undefined;
  };

  window.AuthService = new AuthService();
})(window);