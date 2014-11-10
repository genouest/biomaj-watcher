/*global  angular:false */
/*jslint sub: true, browser: true, indent: 4, vars: true, nomen: true */
'use strict';

// Declare app level module which depends on filters, and services
angular.module('biomaj', ['biomaj.resources', 'ngSanitize', 'ngCookies', 'ngRoute', 'ui.utils', 'ui.bootstrap', 'ngGrid']).

config(['$routeProvider','$logProvider',
    function ($routeProvider) {
        $routeProvider.when('/welcome', {
            templateUrl: 'views/welcome.html',
            controller: 'WelcomeCtrl'
        });
        $routeProvider.when('/bank', {
            templateUrl: 'views/banks.html',
            controller: 'banksCtrl'
        });
        $routeProvider.when('/bank/:name', {
            templateUrl: 'views/bank.html',
            controller: 'bankCtrl'
        });
        $routeProvider.when('/login', {
            templateUrl: 'views/login.html',
            controller: 'LoginCtrl'
        });
        $routeProvider.otherwise({
            redirectTo: '/bank'
        });
}]);

angular.module('biomaj').controller('WelcomeCtrl',
    function () {});

angular.module('biomaj').controller('biomajCtrl',
    function ($rootScope) {
        $rootScope.alerts = [];
        $rootScope.closeAlert = function (index) {
            $rootScope.alerts.splice(index, 1);
        };
    });

angular.module('biomaj').controller('UserCtrl',
  function($scope, $rootScope, $routeParams, $log, User, Logout) {

    $rootScope.$on('LoginCtrl.login', function (event, user) {
      $scope.user = user;
      $scope.is_logged = true;
    });


    User.is_authenticated().$promise.then(function(data) {
        if(data.user != null) {
         $scope.user = data.user;
         $scope.user['is_admin'] = data.is_admin;
         $scope.is_logged = true;
       }
       });

    $scope.logout = function() {
      Logout.get().$promise.then(function(){
        $scope.user = null;
        $scope.is_logged = false
      });
    };
  });

angular.module('biomaj').controller('LoginCtrl',
  function ($scope, $rootScope, $routeParams, $log, User) {
    $scope.userid = '';
    $scope.password = '';
    $scope.auth = function(user_id, password) {
       User.authenticate({'name': user_id},{'password': password}).$promise.then(function(data) {
           if(data.user != null) {
            $scope.user = data.user;
            $scope.user['is_admin'] = data.is_admin;
            $rootScope.$broadcast('LoginCtrl.login', $scope.user);
          }
          });
    };
  });


angular.module('biomaj').controller('bankCtrl',
    function ($scope, $routeParams, $log, Bank) {
      $scope.name = $routeParams.name;
      $scope.bank = Bank.get({'name': $routeParams.name});
    });

angular.module('biomaj').controller('banksCtrl',
    function ($scope, Bank) {
      var banks = Bank.list();
      for(var i=0;i<banks.length;i++) {
        var bank = banks[i];
        var release = '';
        var formats = [];
        if (bank['current'] !== undefined && bank['current']!== null) {
          for(var p=0;p<bank['production'].length;p++) {
            var prod = bank['production'][p];
            if (bank['current'] === prod['session']) {
              release = prod['release'];
              formats = prod['formats']
              break;
            }
          }
        }
        bank['release'] = release;
        bank['formats'] = formats.join();
      }
      $scope.banks = banks;
    });
