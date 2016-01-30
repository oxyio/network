// oxy.io
// File: webpack.config.js
// Desc: oxy.io webpack config

const oxyio = require('oxy.io');

module.exports = oxyio.bootWebpack(
    __dirname,
    'network',
    ['device', 'ipblock']
);
