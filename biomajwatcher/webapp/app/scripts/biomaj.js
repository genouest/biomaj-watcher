/*global  angular:false */
/*jslint sub: true, browser: true, indent: 4, vars: true, nomen: true */
'use strict';

// Declare app level module which depends on filters, and services
var app = angular.module('biomaj', ['biomaj.resources', 'ngSanitize', 'ngCookies', 'ngRoute', 'ui.utils', 'ui.bootstrap','ui.codemirror', 'ngGrid', 'angularCharts', 'datatables', 'xeditable']).

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
        $routeProvider.when('/schedule', {
            templateUrl: 'views/schedule.html',
            controller: 'scheduleCtrl'
        });
        $routeProvider.when('/user', {
            templateUrl: 'views/users.html',
            controller: 'userMngtCtrl'
        });
        $routeProvider.when('/bank', {
            templateUrl: 'views/banks.html',
            controller: 'banksCtrl'
        });
        $routeProvider.when('/bank/:name', {
            templateUrl: 'views/bank.html',
            controller: 'bankCtrl'
        });
        $routeProvider.when('/bank/:name/edit', {
            templateUrl: 'views/bankedit.html',
            controller: 'bankEditCtrl'
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

app.run(function(editableOptions) {
  editableOptions.theme = 'bs3'; // bootstrap3 theme. Can be also 'bs2', 'default'
});

angular.module('biomaj').controller('WelcomeCtrl',
    function () {});


angular.module('biomaj').controller('biomajCtrl', ['$scope', '$rootScope', '$location',
    function ($scope, $rootScope, $location) {
        $rootScope.alerts = [];
        $rootScope.elements = [];
        $rootScope.closeAlert = function (index) {
            $rootScope.alerts.splice(index, 1);
        };
        $rootScope.isActive = function(path){
          if ($location.path().substr(0, path.length) === path) {
            return true;
          } else {
            return false;
          }
        };
    }]);

angular.module('biomaj').controller('scheduleCtrl',
    function ($scope, $rootScope, $routeParams, $log, $location, Bank, User, Auth, Schedule) {
      $scope.cron = [];
      Bank.list().$promise.then(function(banks) {
        var banknames = [];
        for(var b=0;b<banks.length;b++){
          banknames.push(banks[b].name);
          $scope.names = banknames;
        }
        //$scope.banks = banks;
      });
      if(Auth.isConnected()) {
        $scope.user = Auth.getUser();
      }
      else {
        $scope.user = null;
      }
      $scope.save = function(c) {
        if(c.slices.split(" ").length !=5) {
          $scope.msg = 'Wrong schedule cron syntax';
          return;
        }
        if(c.banks.length == 0){
          $scope.msg = 'Task must contain at least one bank';
          return;
        }
        if(c['oldcomment'] == undefined) { c['oldcomment'] = c['comment']; }
        Schedule.update({'name': c['oldcomment']},
                        { 'comment': c['comment'],
                          'slices': c['slices'],
                          'banks': c['banks'].join(',')
                        }).$promise.then(function(data){
                          $scope.msg = "Task updated";
                        });

        c['save'] = false;
        $scope.msg = "";
      };
      $scope.newcron = function() {
        $scope.cron.push({ 'comment': 'newcrontask', 'slices': '* * 1 * *', 'banks': []});
      }
      $scope.updateCron = function(c){
        c['save'] = true;
        c['oldcomment'] = c['comment'];
      }
      $scope.addToCron = function(c) {
        c.banks.push(c.add);
        c['save'] = true;
      };
      $scope.removeFromCron = function(c, b) {
        var index = c.banks.indexOf(b);
        c.banks.splice(index, 1);
        c['save'] = true;
      }
      $scope.removeCron = function(c) {
        Schedule.remove({'name': c['comment']},{});
        for (var i =0; i < $scope.cron.length; i++)
          if ($scope.cron[i].comment === c['comment']) {
              $scope.cron.splice(i,1);
              break;
        }
      };

      Schedule.list().$promise.then(function(data){
        for(var i=0;i<data.length;i++){
          data['save'] = false;
        }
        $scope.cron = data;
      });

    });

angular.module('biomaj').controller('userMngtCtrl',
  function($scope, $rootScope, $routeParams, $log, $location, User) {

  User.list().$promise.then(function(data) {
    $scope.users = data;
  });

  $scope.banks = '';

  $scope.show_user_banks = function(user_name) {
    User.banks({name: user_name}).$promise.then(function(data){
      $scope.banks = data;
      $scope.selected_user = user_name;
    });
  };

});

angular.module('biomaj').controller('UserCtrl',
  function($scope, $rootScope, $routeParams, $log, $location, User, Auth, Logout) {

    $rootScope.$on('LoginCtrl.login', function (event, user) {
      $scope.user = user;
      $scope.is_logged = true;
    });


    User.is_authenticated().$promise.then(function(data) {
        if(data.user !== null) {
         $scope.user = data.user;
         $scope.user['is_admin'] = data.is_admin;
         $scope.is_logged = true;
         Auth.setUser($scope.user);
       }
    });

    $scope.logout = function() {
      Logout.get().$promise.then(function(){
        $scope.user = null;
        $scope.is_logged = false;
        Auth.setUser(null);
        $location.path('bank');
      });
    };

    $scope.search = '';
    $scope.onSearch = function() {
      $log.info('search '+$scope.search);
      if($scope.search !== '') {
        $location.path('search').search({q: $scope.search});
      }
    };
  });

angular.module('biomaj').controller('LoginCtrl',
  function ($scope, $rootScope, $routeParams, $log, $location, User, Auth) {
    $scope.userid = '';
    $scope.password = '';
    $scope.msg = '';
    $scope.auth = function(user_id, password) {
       User.authenticate({'name': user_id},{'password': password}).$promise.then(function(data) {
           if(data.user !== null) {
            $scope.user = data.user;
            $scope.user['is_admin'] = data.is_admin;
            Auth.setUser($scope.user);
            $rootScope.$broadcast('LoginCtrl.login', $scope.user);
            $location.path('bank');
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
      $scope.session = $routeParams.session;
      $scope.bank = $routeParams.name;
      $http({method: 'GET', url: '/bank/'+$routeParams.name+'/log/'+$routeParams.session})
        .success(function(data){
          $scope.log = data;
        })
        .error(function(){
          $scope.log = 'Log file not found';
        });
    });


angular.module('biomaj').controller('bankEditCtrl',
    function ($scope, $routeParams, $log, $interval, Bank, BankStatus, Auth) {
      if(Auth.isConnected()) {
        $scope.user = Auth.getUser();
      }
      else {
        $scope.user = null;
      }
      Bank.config({name: $routeParams.name}).$promise.then(function(data) {
        $scope.config = data;
      },function(reason){
        // Does not exists or new one
        $scope.config = {};
      });

      $scope.save_config = function() {

        Bank.saveconfig({name: $scope.config['db.name']},$scope.config).$promise.then(function(data) {
          alert(data.msg);
        });
      };

      $scope.bank_depends_selected = "";
      $scope.bank_depends_add = function() {
        if($scope.config['depends'] === undefined) {
          $scope.config['depends'] = [];
        }
        $scope.config['depends'].push({ 'name': $scope.bank_depends_selected, 'files.move': ''});
      };

      $scope.bank_depends_rm = function(name) {
        var index = -1;
        for(var i=0;i<$scope.config['depends'].length;i++) {
          if($scope.config['depends'][i]['name'] == name) {
            index = i;
            break;
          }
        }
        $scope.config['depends'].splice(index,1);
      };

      $scope.add_meta = function(section) {

        if($scope.config['db.'+section+'.process'] === undefined) {
          $scope.config['db.'+section+'.process'] = [];
        }

        var metas = null;
        if(section == 'post') {
          metas = $scope.metas;
        }
        else {
          metas = $scope.config['db.'+section+'.process'];
        }

        metas.push({
          'name': new Date().getTime(),
          'procs': []
        });
      };

      $scope.add_proc = function(section, meta) {

        var metas = null;
        if(section == 'post') {
          metas = $scope.metas;
        }
        else {
          metas = $scope.config['db.'+section+'.process'];
        }

        for(var i=0;i<metas.length;i++){
          if(metas[i]['name'] == meta) {
            metas[i]['procs'].push({
              'name': '',
              'desc': '',
              'cluster': '',
              'native': '',
              'docker': '',
              'exe': '',
              'args': '',
              'format': '',
              'types': '',
              'tags': '',
              'files': ''
            });
            break;
          }
        }
      };
      $scope.add_multi_file = function() {
        if($scope.config['multi'] == undefined) {
          $scope.config['multi'] = [];
        }
        $scope.config['multi'].push({
          'name': '',
          'method': 'GET',
          'protocol': '',
          'server': '',
          'path': '',
          'credentials': ''
        });
      };

      $scope.rm_multi_file = function(path) {
        var index = -1;
        for(var i=0;i<$scope.config['multi'].length;i++){
          if($scope.config['multi'][i]['path'] == path) {
            index = i;
            break;
          }
        }
        $scope.config['multi'].splice(index, 1);
      };

      $scope.bank_meta_rm = function(section, meta) {
        var index = -1;
        var metas = null;
        if(section == 'post') {
          metas = $scope.metas;
        }
        else {
          metas = $scope.config['db.'+section+'.process'];
        }

        for(var i=0;i<metas.length;i++){
          if(metas[i]['name'] == meta) {
            index = i;
            break;
          }
        }
        metas.splice(index, 1);
      };

      $scope.bank_block_rm = function(block) {
        var index = -1;

        for(var i=0;i<$scope.config['blocks'].length;i++){
          if($scope.config['blocks'][i]['name'] == block) {
            index = i;
            break;
          }
        }
        $scope.config['blocks'].splice(index, 1);
      };

      $scope.bank_block_show = function(block) {
        $scope.section = 'post';
        for(var i=0;i<$scope.config['blocks'].length;i++){
          if($scope.config['blocks'][i]['name'] == block) {
            $scope.metas = $scope.config['blocks'][i]['metas'];
            break;
          }
        }
      };

      $scope.bank_show = function(section) {
        $scope.section = section;
        if($scope.config['db.'+section+'.process'] === undefined) {
          $scope.config['db.'+section+'.process'] = [];
        }
        $scope.metas = $scope.config['db.'+section+'.process'];
      };

      $scope.add_block = function() {
        if($scope.config['blocks'] === undefined) {
          $scope.config['blocks'] = [];
        }
        $scope.config['blocks'].push({
          'name': new Date().getTime(),
          'metas': []
        });
      };

      $scope.bank_proc_rm = function(section, meta, proc) {
        var metas = null;
        if(section == 'post') {
          metas = $scope.metas;
        }
        else {
          metas = $scope.config['db.'+section+'.process'];
        }

        for(var i=0;i<metas.length;i++){
          if(metas[i]['name'] == meta) {
            var index = -1;
            for(var j=0;j<metas[i]['procs'].length;j++){
              if(metas[i]['procs']['name'] == proc) {
                index = j;
                break;
              }
            }
            metas[i]['procs'].splice(index, 1);
            break;
          }
        }
      };



      Bank.list().$promise.then(function(banks) {
        var banklist = [];
        for(var i=0;i<banks.length;i++) {
          banklist.push(banks[i].name);
        }
        $scope.banklist = banklist;
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
        for(var k in obj) { keys.push(k); }
        return keys;
      };

      /**
      * Return an array of process name/process status
      */
      $scope.get_proc_status = function(process, proc) {
        var res = [];
        var metas = null;
        var elt = {};
        var procs = null;
        if(process[proc] === undefined) { return []; }
        if(proc === 'postprocess') {
          var blocks = $scope.get_keys(process[proc]);
          for(var i = 0;i < blocks.length; i++) {
              metas =$scope.get_keys(process[proc][blocks[i]]);
              for(var j = 0;j < metas.length; j++) {
                procs = $scope.get_keys(process[proc][blocks[i]][metas[j]]);
                for(var k = 0;k < procs.length; k++) {
                    elt = {};
                    elt['name'] = blocks[i]+'.'+metas[j]+'.'+procs[k];
                    elt['status'] = process[proc][blocks[i]][metas[j]][procs[k]];
                    res.push(elt);
                }
              }
          }
        }
        else {
                metas = $scope.get_keys(process[proc]);
                for(var j2 = 0;j2 < metas.length; j2++) {
                  procs = $scope.get_keys(metas[j2]);
                  for(var k2 = 0;k2 < procs.length; k2++) {
                    elt = {};
                    elt['name'] = metas[j2]+'.'+procs[k2];
                    elt['status'] = process[proc][metas[j2]][procs[k2]];
                    res.push(elt);
                  }
                }
        }
        return res;
      };

      $scope.updateworkflow = ['init', 'check', 'depends', 'preprocess', 'release','download', 'postprocess', 'publish', 'over'];

      $scope.locked = false;
      $scope.get_status = function() {
        BankStatus.get({'name': $routeParams.name}).$promise.then(function(data) {
          if(data !== null) {
            var keys = [];
            for(var k in data) {
              //this.substring( 0, str.length ) === str
              if(k.substring(0, 1) !== '$') {
                keys.push(k);
              }
            }
            if(keys.length > 0) {
              $scope.status = data;
              $scope.keys = keys;
            }
          }
        });

        Bank.locked({'name': $routeParams.name}).$promise.then(function(data) {
          if(data.status == 1) {
            $scope.locked = true;
          }
          else {
            $scope.locked = false;
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
              if(data['sessions'][i]['id'] === last_update) {
                $scope.last_update_session = data['sessions'][i];
                break;
              }
            }
          });
      };
      $scope.load_bank();

      $scope.remove = function(release) {
        Bank.delete({'name': $routeParams.name, 'release': release}).$promise.then(function(data) {
          alert(data.msg);
        });
      };

      $scope.update = function() {
        $scope.status = null;
        Bank.update({'name': $routeParams.name},{}).$promise.then(function(data) {
          alert(data.msg);
        });
      };

      $scope.update_from_scratch = function() {
        $scope.status = null;
        Bank.update({'name': $routeParams.name},{fromscratch: 1}).$promise.then(function(data) {
          alert(data.msg);
        });
      };

  });

angular.module('biomaj').controller('bankReleaseCtrl',
    function ($scope, $routeParams, $log, Bank) {
      $scope.showHide = false;
      $scope.name = $routeParams.name;
      $scope.release = $routeParams.release;
      Bank.get({'name': $routeParams.name}).$promise.then(function(data) {
        for(var i=0;i<data['production'].length;i++) {
          if(data['production'][i]['release'] === $routeParams.release || data['production'][i]['release'] === $scope.name+'-'+$routeParams.release) {
            $scope.production = data['production'][i];
            for(var j=0;j<data['sessions'].length;j++){
              if(data['sessions'][j]['release'] === $routeParams.release && data['sessions'][j]['action'] === 'update') {
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
    function ($scope, $log, Bank, Auth) {

      if(Auth.isConnected()) {
        $scope.user = Auth.getUser();
      }
      else {
        $scope.user = null;
      }

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
      var query = $location.search().q;
      $scope.query = query;
      Search.list({q: query}).$promise.then(function(res) {
        var banks = ReorderSearchResults.reorder(res);
        $scope.result = banks;
      });
    });

angular.module('biomaj').controller('statsCtrl',
    function ($scope, $log, Stat) {
      $scope.config = {
          'labels': false,
          'title': 'Banks disk usage',
          'legend': {
            'display': true,
            'position': 'right'
          },
          'mouseover': function(d) {
            $scope.bank_size = d.data.x+': '+$scope.get_size(d.data.y[0]);
          },
          'click' : function(d) {
            var bank = d.data.x;
            $scope.releaseconfig = {
                'labels': false,
                'title': bank+' disk usage',
                'legend': {
                  'display': true,
                  'position': 'right'
                },
                'mouseover': function(d) {
                  $scope.release_size = d.data.x+': '+$scope.get_size(d.data.y[0]);
                },
                'click' : function() {
                  //var bank = d.data.x;
                },
                'innerRadius': 0,
                'lineLegend': 'lineEnd'
              };
              var series = [bank];
              var data= [];
              var selected_bank = null;
              var stats = $scope.stats;
              for(var i=0;i<stats.length;i++) {
                if(stats[i]['name'] === bank) {
                  selected_bank = stats[i];
                  break;
                }
              }
              if(selected_bank !== null) {

                for(var j=0;j<selected_bank['releases'].length;j++) {
                  var elt = {'x': selected_bank['releases'][j]['name'], 'y': [selected_bank['releases'][j]['size']]};
                  data.push(elt);
                }
                $scope.release = {'series': series, 'data': data};
              }
          },
          'innerRadius': 0,
          'lineLegend': 'lineEnd'
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
        else {
          return size+'b';
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
