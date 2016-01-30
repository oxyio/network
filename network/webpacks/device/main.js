// oxy.io Network
// File: webpacks/device/main.js
// Desc: the entry point for the device view webpack

import React from 'react';
import ReactDOM from 'react-dom';

import 'device/style.less';
import Status from 'device/status';

// Get DOM bits
const $device = document.querySelector('#device');
const $statusTab = $device.querySelector('[data-tab=status]');
const $processesTab = $device.querySelector('[data-tab=processes]');


// Render the Reacts!
window.addEventListener('load', () => {
    const requestKey = $statusTab.getAttribute('data-websocket-key');

    ReactDOM.render(
        <Status
            requestKey={requestKey}
        />,
        $statusTab.querySelector('[data-device-status]')
    );
});


// TODO: remove this addTabLoader crap!
$processesTab.addTabLoader(function() {
    console.log('LOAD DE PROCESSES');
});
