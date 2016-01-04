// Oxypanel Network
// File: webpacks/device/main.js
// Desc: the entry point for the device view webpack

'use strict';

require('./style.less');

var React = require('react');
var Status = require('./status.js');

var $device = document.querySelector('#device');
var $statusTab = $device.querySelector('[data-tab=status]');
var $processesTab = $device.querySelector('[data-tab=processes]');


$statusTab.addTabLoader(function($status) {
    var requestKey = $statusTab.getAttribute('data-websocket-request-key');
    React.render(React.createElement(
        Status, {
            requestKey: requestKey
        }
    ), $statusTab);
});


$processesTab.addTabLoader(function($processes) {
    console.log('LOAD DE PROCESSES');
});
