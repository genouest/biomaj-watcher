/*jslint browser: true, indent: 4, vars: true, nomen: true */
(function () {
  'use strict';
  function Bank($resource) {
    return $resource('/bank', {}, {
      list: {
        method: 'GET',
        isArray: true
      }
    });
  }
  angular.module('biomaj.resources', ['ngResource']).factory('Bank', Bank);
}());
/*global  angular:false */
/*jslint sub: true, browser: true, indent: 4, vars: true, nomen: true */
'use strict';
// Declare app level module which depends on filters, and services
angular.module('biomaj', [
  'biomaj.resources',
  'ngSanitize',
  'ngCookies',
  'ngRoute',
  'ui.utils',
  'ui.bootstrap',
  'ngGrid'
]).config([
  '$routeProvider',
  '$logProvider',
  function ($routeProvider) {
    $routeProvider.when('/welcome', {
      templateUrl: 'views/welcome.html',
      controller: 'WelcomeCtrl'
    });
    $routeProvider.when('/bank', {
      templateUrl: 'views/banks.html',
      controller: 'banksCtrl'
    });
    $routeProvider.otherwise({ redirectTo: '/bank' });
  }
]);
angular.module('biomaj').controller('WelcomeCtrl', function () {
});
angular.module('biomaj').controller('biomajCtrl', [
  '$rootScope',
  function ($rootScope) {
    $rootScope.alerts = [];
    $rootScope.closeAlert = function (index) {
      $rootScope.alerts.splice(index, 1);
    };
  }
]);
angular.module('biomaj').controller('banksCtrl', [
  '$scope',
  'Bank',
  function ($scope, Bank) {
    var banks = Bank.list();
    for (var i = 0; i < banks.length; i++) {
      var bank = banks[i];
      var release = '';
      if (bank['current'] !== undefined && bank['current'] !== null) {
        for (var p = 0; p < bank['production'].length; p++) {
          var prod = bank['production'][p];
          if (bank['current'] === prod['session']) {
            release = prod['release'];
            break;
          }
        }
      }
      bank['release'] = release;
    }
    $scope.banks = banks;
  }
]);