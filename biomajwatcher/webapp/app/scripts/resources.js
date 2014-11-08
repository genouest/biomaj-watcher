/*jslint browser: true, indent: 4, vars: true, nomen: true */

(function () {
  'use strict';

    function Bank($resource) {
        return $resource('/bank', {}, {
            list: {
                method: 'GET',
                isArray: true,
                cache: true
            }
        });
    }


  angular.module('biomaj.resources', ['ngResource'])
    .factory('Bank', Bank);

}());
