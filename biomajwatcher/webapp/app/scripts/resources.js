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
        return $resource('/stat', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: true
            }
        });
    }

    function Search($resource) {
        return $resource('/search', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: true
            }
        });
    }

    function Schedule($resource) {
        return $resource('/schedule', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: false
            },
            update: {
              url: '/schedule/:name',
              method: 'POST',
              isArray: true,
              cache: false
            },
            remove: {
              url: '/schedule/:name',
              method: 'DELETE',
              isArray: true,
              cache: false
            }
        });
    }

    function BankStatus($resource) {
      return $resource('/bank/:name/status');
    }

    function Bank($resource) {
        return $resource('/bank', {}, {
            list: {
              method: 'GET',
              isArray: true,
              cache: true
            },
            get: {
              url: '/bank/:name',
              method: 'GET',
              isArray: false,
              cache: false
            },
            config: {
              url: '/bank/:name/config',
              method: 'GET',
              isArray: false,
              cache: false
            },
            locked: {
              url: '/bank/:name/locked',
              method: 'GET',
              isArray: false,
              cache: false
            },
            delete: {
              url: '/bank/:name/:release',
              method: 'DELETE',
              isArray: false,
              cache: false
            },
            update: {
              url: '/bank/:name',
              method: 'PUT',
              isArray: false,
              cache: false
            }

        });
    }

    function Logout($resource) {
      return $resource('/logout');
    }

    function User($resource) {
        //var user = null;
        return $resource('/auth', {}, {
            list: {
              url: '/user',
              method: 'GET',
              isArray: true,
              cache: true
            },
            get: {
              url: '/user/:name',
              method: 'GET',
              isArray: false,
              cache: true
            },
            is_authenticated: {
              url: '/auth',
              method: 'GET',
              isArray: false,
              cache: false
            },
            authenticate: {
              url: '/auth/:name',
              method: 'POST',
              isArray: false,
              cache: false
            },
            banks: {
              url: '/user/:name/banks',
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
