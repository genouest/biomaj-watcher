/*global  angular:false */
/*jslint sub: true, browser: true, indent: 4, vars: true, nomen: true */
'use strict';

// Declare app level module which depends on filters, and services
angular.module('biomaj', ['biomaj.resources', 'ngSanitize', 'ngCookies', 'ngRoute', 'ui.utils', 'ui.bootstrap','ui.codemirror', 'ngGrid', 'angularCharts']).

config(['$routeProvider','$logProvider',
    function ($routeProvider) {
        $routeProvider.when('/welcome', {
            templateUrl: 'views/welcome.html',
            controller: 'WelcomeCtrl'
        });
        $routeProvider.when('/stat', {
            templateUrl: 'views/stats.html',
            controller: 'statsCtrl'
        });
        $routeProvider.when('/search', {
            templateUrl: 'views/search.html',
            controller: 'searchCtrl'
        });
        $routeProvider.when('/bank', {
            templateUrl: 'views/banks.html',
            controller: 'banksCtrl'
        });
        $routeProvider.when('/bank/:name', {
            templateUrl: 'views/bank.html',
            controller: 'bankCtrl'
        });
        $routeProvider.when('/bank/:name/:release', {
            templateUrl: 'views/release.html',
            controller: 'bankReleaseCtrl'
        });
        $routeProvider.when('/login', {
            templateUrl: 'views/login.html',
            controller: 'LoginCtrl'
        });
        $routeProvider.when('/bank/:name/log/:session', {
            templateUrl: 'views/sessionlog.html',
            controller: 'sessionLogCtrl'
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
  function($scope, $rootScope, $routeParams, $log, $location, User, Auth, Logout) {

    $rootScope.$on('LoginCtrl.login', function (event, user) {
      $scope.user = user;
      $scope.is_logged = true;
    });


    User.is_authenticated().$promise.then(function(data) {
        if(data.user != null) {
         $scope.user = data.user;
         $scope.user['is_admin'] = data.is_admin;
         $scope.is_logged = true;
         Auth.setUser($scope.user);
       }
    });

    $scope.logout = function() {
      Logout.get().$promise.then(function(){
        $scope.user = null;
        $scope.is_logged = false
        Auth.setUser(null);
        $location.path("bank");
      });
    };

    $scope.search = '';
    $scope.onSearch = function() {
      $log.info('search '+$scope.search);
      if($scope.search!='') {
        $location.path('search').search({q: $scope.search});
      }
    }
  });

angular.module('biomaj').controller('LoginCtrl',
  function ($scope, $rootScope, $routeParams, $log, $location, User, Auth) {
    $scope.userid = '';
    $scope.password = '';
    $scope.msg = '';
    $scope.auth = function(user_id, password) {
       User.authenticate({'name': user_id},{'password': password}).$promise.then(function(data) {
           if(data.user != null) {
            $scope.user = data.user;
            $scope.user['is_admin'] = data.is_admin;
            Auth.setUser($scope.user);
            $rootScope.$broadcast('LoginCtrl.login', $scope.user);
            $location.path("bank");
          }
          else {
            $scope.msg = 'Login error';
          }
          });
    };
  });

angular.module('biomaj').service('Auth', function() {
	var user =null;
	return {
		getUser: function() {
			return user;
		},
		setUser: function(newUser) {
			user = newUser;
		},
		isConnected: function() {
			return !!user;
		}
	};
});

angular.module('biomaj').controller('sessionLogCtrl',
    function ($scope, $routeParams, $log, $http) {
      $scope.session = $routeParams.session
      $scope.bank = $routeParams.name
      $http({method: "GET", url: "/bank/"+$routeParams.name+"/log/"+$routeParams.session})
        .success(function(data){
          $scope.log = data;
        })
        .error(function(data){
          $scope.log = 'Log file not found';
        });
    });

angular.module('biomaj').controller('bankCtrl',
    function ($scope, $routeParams, $log, $interval, Bank, BankStatus, Auth) {
      if(Auth.isConnected()) {
        $scope.user = Auth.getUser();
      }
      else {
        $scope.user = null;
      }
      $scope.name = $routeParams.name;

      $scope.get_keys = function(obj) {
        var keys = [];
        for(var k in obj) keys.push(k);
        return keys;
      }

      /**
      * Return an array of process name/process status
      */
      $scope.get_proc_status = function(process, proc) {
        if(process[proc]==undefined) { return []; }
        if(proc == 'postprocess') {
          var blocks = $scope.get_keys(process[proc]);
          var res = [];
          for(var i = 0;i < blocks.length; i++) {
              var metas =$scope.get_keys(process[proc][blocks[i]]);
              for(var j = 0;j < metas.length; j++) {
                var procs = $scope.get_keys(process[proc][blocks[i]][metas[j]]);
                for(var k = 0;k < procs.length; k++) {
                    var elt = {};
                    elt['name'] = blocks[i]+'.'+metas[j]+'.'+procs[k];
                    elt['status'] = process[proc][blocks[i]][metas[j]][procs[k]];
                    res.push(elt);
                }
              }
          }
        }
        else {
            var metas = $scope.get_keys(process[proc]);
            var res = [];
                for(var j = 0;j < metas.length; j++) {
                  var procs = $scope.get_keys(metas[j]);
                  for(var k = 0;k < procs.length; k++) {
                    var elt = {};
                    elt['name'] = metas[j]+'.'+procs[k];
                    elt['status'] = process[proc][metas[j]][procs[k]];
                    res.push(elt);
                  }
                }
        }
        return res;
      };

      $scope.updateworkflow = ['init', 'check', 'depends', 'preprocess', 'release','download', 'postprocess', 'publish', 'over'];

      $scope.get_status = function() {
        BankStatus.get({'name': $routeParams.name}).$promise.then(function(data) {
          if(data!=null) {
            var keys = [];
            for(var k in data) {
              //this.substring( 0, str.length ) === str
              if(k.substring(0, 1) !== '$') {
                keys.push(k);
              }
            }
            if(keys.length>0) {
              $scope.status = data;
              $scope.keys = keys
            }
          }
        });
      } ;

      $scope.status_loop = $interval($scope.get_status,5000);
      $scope.$on('$destroy', function() {
        // Make sure that the interval is destroyed too
        $interval.cancel($scope.status_loop);
      });

      $scope.load_bank = function() {
          Bank.get({'name': $routeParams.name}).$promise.then(function(data) {
            $scope.bank = data;
            var last_update = data['last_update_session'];
            for(var i=data['sessions'].length-1;i>=0;i--) {
              if(data['sessions'][i]['id'] == last_update) {
                $scope.last_update_session = data['sessions'][i];
                break;
              }
            }
          });
      };
      $scope.load_bank();
    });

angular.module('biomaj').controller('bankReleaseCtrl',
    function ($scope, $routeParams, $log, Bank) {
      $scope.showHide = false;
      $scope.name = $routeParams.name;
      $scope.release = $routeParams.release;
      Bank.get({'name': $routeParams.name}).$promise.then(function(data) {
        for(var i=0;i<data['production'].length;i++) {
          if(data['production'][i]['release'] == $routeParams.release || data['production'][i]['release'] == $scope.name+'-'+$routeParams.release) {
            $scope.production = data['production'][i];
            for(var j=0;j<data['sessions'].length;j++){
              if(data['sessions'][j]['release'] == $routeParams.release && data['sessions'][j]['action'] == 'update') {
                $scope.session = data['sessions'][j];
                break;
              }
            }
            break;
          }
        }
      });
    });

angular.module('biomaj').controller('banksCtrl',
    function ($scope, $log, Bank) {

      Bank.list().$promise.then(function(banks) {
        for(var i=0;i<banks.length;i++) {
          var bank = banks[i];
          var release = '';
          var formats = [];
          if (bank['current'] !== undefined && bank['current']!== null) {
            for(var p=0;p<bank['production'].length;p++) {
              var prod = bank['production'][p];
              if (bank['current'] === prod['session']) {
                release = prod['release'];
                formats = prod['formats'];
                break;
              }
            }
          }
          bank['release'] = release;
          bank['formats'] = formats.join();
        }
        $scope.banks = banks;
      });
    });

angular.module('biomaj').controller('searchCtrl',
    function ($scope, $log, $location, Search, ReorderSearchResults) {
      var query = $location.search().q
      $scope.query = query;
      Search.list({q: query}).$promise.then(function(res) {
        var banks = ReorderSearchResults.reorder(res);
        $scope.result = banks;
      });
    });

angular.module('biomaj').controller('statsCtrl',
    function ($scope, $log, Stat) {
      $scope.config = {
          "labels": false,
          "title": "Banks disk usage",
          "legend": {
            "display": true,
            "position": "right"
          },
          "mouseover": function(d) {
            $scope.bank_size = d.data.x+": "+$scope.get_size(d.data.y[0]);
          },
          "click" : function(d) {
            var bank = d.data.x;
            $scope.releaseconfig = {
                "labels": false,
                "title": bank+" disk usage",
                "legend": {
                  "display": true,
                  "position": "right"
                },
                "mouseover": function(d) {
                  $scope.release_size = d.data.x+": "+$scope.get_size(d.data.y[0]);
                },
                "click" : function(d) {
                  var bank = d.data.x;
                },
                "innerRadius": 0,
                "lineLegend": "lineEnd"
              };
              var series = [bank];
              var data= [];
              var selected_bank = null;
              var stats = $scope.stats;
              for(var i=0;i<stats.length;i++) {
                if(stats[i]['name']==bank) {
                  selected_bank = stats[i];
                  break;
                }
              }
              if(selected_bank!=null) {

                for(var j=0;j<selected_bank['releases'].length;j++) {
                  var elt = {'x': selected_bank['releases'][j]['name'], 'y': [selected_bank['releases'][j]['size']]};
                  data.push(elt);
                }
                $scope.release = {'series': series, 'data': data};
              }
          },
          "innerRadius": 0,
          "lineLegend": "lineEnd"
        };
        $scope.chartType = 'pie';

      $scope.get_size = function(size) {
        if(size > 1024*1024*1024) {
          return Math.floor(size/(1024*1024*1024))+'Gb';
        }
        else if(size > 1024*1024) {
          return Math.floor(size/(1024*1024))+'Mb';
        }
        else if(size > 1024) {
          return Math.floor(size/(1024))+'Kb';
        }
      };

      Stat.list().$promise.then(function(stats) {
        $scope.stats = stats;
        var series = ['banks'];
        var data= [];
        //var data = { 'x': 'banks', 'y': []}
        for(var i=0;i<stats.length;i++) {
          var elt = {'x': stats[i]['name'], 'y': [stats[i]['size']]};
          //data['y'].push(stats[i]['size'])
          //series.push(stats[i]['name']);
          data.push(elt);
        }

        $scope.data = {'series': series, 'data': data};
      });
    });
