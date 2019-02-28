/*jslint sub:true, browser: true, indent: 4, vars: true, nomen: true */

(function () {
  'use strict';

  /**
  * Reorder index search results, grouping bank and releases
  */
  function ReorderSearchResults(){
    return {
            reorder: function(res) {
                  var banks = [];
                  for(var i=0;i<res.length;i++){
                    var id = res[i]['_source']['bank'];
                    var bank = {};
                    var new_bank = true;
                    for(var b=0;b<banks.length;b++){
                      if(banks[b]['name'] === id) {
                        bank = banks[b];
                        new_bank = false;
                        break;
                      }
                    }
                    if(new_bank) {
                      bank['name'] = id;
                      bank['release'] = [];
                      banks.push(bank);
                    }
                    var new_release = true;
                    var release = res[i]['_source']['release'];
                    var rel = [];
                    for(var r=0;r<bank['release'];r++) {
                      if(bank['release'][r]['name'] === release) {
                        rel = bank['release'][r]['elts'];
                        new_release = false;
                        break;
                      }
                    }

                    if(new_release) {
                      rel = {'name': release, 'elts': []};
                      bank['release'].push(rel);
                    }
                    rel['elts'].push({'format': res[i]['_source']['format'],
                                                      'types': res[i]['_source']['types'],
                                                      'tags': res[i]['_source']['tags']

                      });

                  }
                  return banks;
                }
    };
  }

    function Stat($resource) {
        return $resource('/api/watcher/stat', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: true
            }
        });
    }

    function Search($resource) {
        return $resource('/api/watcher/search', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: true
            }
        });
    }

    function Schedule($resource) {
        return $resource('/api/watcher/schedule', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: false
            },
            update: {
              url: '/api/watcher/schedule/:name',
              method: 'POST',
              isArray: true,
              cache: false
            },
            remove: {
              url: '/api/watcher/schedule/:name',
              method: 'DELETE',
              isArray: true,
              cache: false
            }
        });
    }

    function BankStatus($resource) {
      return $resource('/api/watcher/bank/:name/status');
    }

    function Bank($resource) {
        return $resource('/api/watcher/bank', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: true
            },
            get: {
              url: '/api/watcher/bank/:name',
              method: 'GET',
              isArray: false,
              cache: false
            },
            config: {
              url: '/api/watcher/bank/:name/config',
              method: 'GET',
              isArray: false,
              cache: false
            },
            saveconfig: {
              url: '/api/watcher/bank/:name/config',
              method: 'POST',
              isArray: false,
              cache: false
            },
            locked: {
              url: '/api/watcher/bank/:name/locked',
              method: 'GET',
              isArray: false,
              cache: false
            },
            delete: {
              url: '/api/watcher/bank/:name/:release',
              method: 'DELETE',
              isArray: false,
              cache: false
            },
            update: {
              url: '/api/watcher/bank/:name',
              method: 'PUT',
              isArray: false,
              cache: false
            }

        });
    }

    function Logout($resource) {
      return $resource('/api/watcher/logout');
    }

    function User($resource) {
        //var user = null;
        return $resource('/api/watcher/auth', {}, {
            list: {
              url: '/api/watcher/user',
              method: 'GET',
              isArray: true,
              cache: true
            },
            get: {
              url: '/api/watcher/user/:name',
              method: 'GET',
              isArray: false,
              cache: true
            },
            is_authenticated: {
              url: '/api/watcher/auth',
              method: 'GET',
              isArray: false,
              cache: false
            },
            authenticate: {
              url: '/api/watcher/auth/:name',
              method: 'POST',
              isArray: false,
              cache: false
            },
            banks: {
              url: '/api/watcher/user/:name/banks',
              method: 'GET',
              isArray: true,
              cache: false
            }
        });
    }


  angular.module('biomaj.resources', ['ngResource'])
    .factory('ReorderSearchResults', ReorderSearchResults)
    .factory('Search', Search)
    .factory('Stat', Stat)
    .factory('Bank', Bank)
    .factory('BankStatus', BankStatus)
    .factory('User', User)
    .factory('Schedule', Schedule)
    .factory('Logout', Logout);

}());
