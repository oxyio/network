webpackJsonpnetwork([1,0],[
/* 0 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';

	var _react = __webpack_require__(1);

	var _react2 = _interopRequireDefault(_react);

	var _reactDom = __webpack_require__(5);

	var _reactDom2 = _interopRequireDefault(_reactDom);

	__webpack_require__(3);

	var _status = __webpack_require__(2);

	var _status2 = _interopRequireDefault(_status);

	function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

	// Get DOM bits
	// oxy.io Network
	// File: webpacks/device/main.js
	// Desc: the entry point for the device view webpack

	var $device = document.querySelector('#device');
	var $statusTab = $device.querySelector('[data-tab=status]');
	var $processesTab = $device.querySelector('[data-tab=processes]');

	// Render the Reacts!
	window.addEventListener('load', function () {
	    var requestKey = $statusTab.getAttribute('data-websocket-key');

	    _reactDom2.default.render(_react2.default.createElement(_status2.default, {
	        requestKey: requestKey
	    }), $statusTab.querySelector('[data-device-status]'));
	});

	// TODO: remove this addTabLoader crap!
	$processesTab.addTabLoader(function () {
	    console.log('LOAD DE PROCESSES');
	});

/***/ },
/* 1 */
/***/ function(module, exports, __webpack_require__) {

	module.exports = React;

/***/ },
/* 2 */
/***/ function(module, exports, __webpack_require__) {

	'use strict';

	var _createClass = function () { function defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } } return function (Constructor, protoProps, staticProps) { if (protoProps) defineProperties(Constructor.prototype, protoProps); if (staticProps) defineProperties(Constructor, staticProps); return Constructor; }; }();

	Object.defineProperty(exports, "__esModule", {
	    value: true
	});

	var _lodash = __webpack_require__(6);

	var _lodash2 = _interopRequireDefault(_lodash);

	var _react = __webpack_require__(1);

	var _react2 = _interopRequireDefault(_react);

	function _interopRequireDefault(obj) { return obj && obj.__esModule ? obj : { default: obj }; }

	function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

	function _possibleConstructorReturn(self, call) { if (!self) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return call && (typeof call === "object" || typeof call === "function") ? call : self; }

	function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function, not " + typeof superClass); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, enumerable: false, writable: true, configurable: true } }); if (superClass) Object.setPrototypeOf ? Object.setPrototypeOf(subClass, superClass) : subClass.__proto__ = superClass; } // oxy.io Network
	// File: network/webpacks/device/status.js
	// Desc: the device status component

	var Status = function (_Component) {
	    _inherits(Status, _Component);

	    function Status(props) {
	        _classCallCheck(this, Status);

	        var _this = _possibleConstructorReturn(this, Object.getPrototypeOf(Status).call(this, props));

	        _this.state = {
	            load: 0,
	            networkIn: 0,
	            networkOut: 0,
	            cpuPercentage: 0,
	            cpuColor: '',
	            memoryPercentage: 0,
	            memoryColor: '',
	            disks: []
	        };
	        return _this;
	    }

	    _createClass(Status, [{
	        key: 'getPercentageColor',
	        value: function getPercentageColor(percent) {
	            if (percent >= 90) return 'red';else if (percent >= 80) return 'orange';else if (percent > 70) return 'yellow';

	            return 'green';
	        }
	    }, {
	        key: 'formatPercentage',
	        value: function formatPercentage(percent) {
	            return percent.toFixed(1);
	        }
	    }, {
	        key: 'parseNetworkStats',
	        value: function parseNetworkStats(stats) {
	            var transmitBytes = 0;
	            var receiveBytes = 0;

	            _lodash2.default.each(stats, function (stat) {
	                if (stat.detail == 'receive_bytes') receiveBytes += stat.value;

	                if (stat.detail == 'transmit_bytes') transmitBytes += stat.value;
	            });

	            this.setState({
	                networkIn: receiveBytes,
	                networkOut: transmitBytes
	            });
	        }
	    }, {
	        key: 'parseCpuStats',
	        value: function parseCpuStats(stats) {
	            var totalPercent = _lodash2.default.reduce(stats, function (memo, stat) {
	                if (stat.key == 'cpu') memo += stat.value;

	                return memo;
	            }, 0);

	            this.setState({
	                cpuPercentage: this.formatPercentage(totalPercent),
	                cpuColor: this.getPercentageColor(totalPercent)
	            });
	        }
	    }, {
	        key: 'parseMemoryStats',
	        value: function parseMemoryStats(stats) {
	            var data = {
	                total: 0,
	                free: 0,
	                cached: 0,
	                buffers: 0
	            };

	            _lodash2.default.each(stats, function (stat) {
	                if (stat.key != 'memory') return;

	                _lodash2.default.each(_lodash2.default.keys(data), function (key) {
	                    if (stat.detail === key) data[key] = stat.value;
	                });
	            });

	            var used = data.total - data.free - data.cached - data.buffers;
	            var usedPercent = used / data.total * 100;

	            this.setState({
	                memoryPercentage: this.formatPercentage(usedPercent),
	                memoryColor: this.getPercentageColor(usedPercent)
	            });
	        }
	    }, {
	        key: 'parseDiskStats',
	        value: function parseDiskStats(stats) {
	            var _this2 = this;

	            var diskData = {};

	            _lodash2.default.each(stats, function (stat) {
	                if (!diskData[stat.key]) diskData[stat.key] = {};

	                diskData[stat.key][stat.detail] = stat.value;
	            });

	            var disks = _lodash2.default.reduce(diskData, function (memo, data, name) {
	                var total = data.available + data.used;
	                var percentage = data.used / total * 100;

	                memo.push({
	                    name: name,
	                    percentage: _this2.formatPercentage(percentage),
	                    color: _this2.getPercentageColor(percentage)
	                });

	                return memo;
	            }, []);

	            this.setState({
	                disks: disks
	            });
	        }
	    }, {
	        key: 'handleEvent',
	        value: function handleEvent(msg) {
	            var _JSON$parse = JSON.parse(msg.data);

	            var data = _JSON$parse.data;
	            var event = _JSON$parse.event;

	            switch (event) {
	                case 'cpu':
	                    this.parseCpuStats(data);
	                    break;

	                case 'memory':
	                    this.parseMemoryStats(data);
	                    break;

	                case 'network_io':
	                    this.parseNetworkStats(data);
	                    break;

	                case 'disk':
	                    this.parseDiskStats(data);
	                    break;

	                // Currently not in-use by Status component
	                case 'disk_io':
	                    break;

	                default:
	                    console.error('Unknown device stat type: ' + event, data);
	            }
	        }
	    }, {
	        key: 'componentDidMount',
	        value: function componentDidMount() {
	            var ws = new WebSocket('ws://' + window.location.host + '/websocket?key=' + this.props.requestKey);

	            ws.addEventListener('message', this.handleEvent.bind(this));
	        }
	    }, {
	        key: 'render',
	        value: function render() {
	            var disks = _lodash2.default.reduce(this.state.disks, function (memo, disk) {
	                memo.push(_react2.default.createElement(
	                    'div',
	                    { key: disk.name },
	                    _react2.default.createElement(
	                        'strong',
	                        null,
	                        disk.name
	                    ),
	                    _react2.default.createElement(
	                        'div',
	                        { className: 'bar ' + disk.color },
	                        _react2.default.createElement('div', { style: { width: disk.percentage + '%' } }),
	                        _react2.default.createElement(
	                            'span',
	                            null,
	                            disk.percentage,
	                            '%'
	                        )
	                    )
	                ));

	                return memo;
	            }, []);

	            return _react2.default.createElement(
	                'div',
	                null,
	                _react2.default.createElement(
	                    'div',
	                    { className: 'block base' },
	                    _react2.default.createElement(
	                        'div',
	                        { className: 'block third' },
	                        _react2.default.createElement(
	                            'strong',
	                            null,
	                            'Load'
	                        ),
	                        _react2.default.createElement(
	                            'span',
	                            { className: 'stat' },
	                            this.state.load
	                        )
	                    ),
	                    _react2.default.createElement(
	                        'div',
	                        { className: 'block third' },
	                        _react2.default.createElement(
	                            'strong',
	                            null,
	                            'Network In'
	                        ),
	                        _react2.default.createElement(
	                            'span',
	                            { className: 'stat' },
	                            this.state.networkIn,
	                            'b/s'
	                        )
	                    ),
	                    _react2.default.createElement(
	                        'div',
	                        { className: 'block third' },
	                        _react2.default.createElement(
	                            'strong',
	                            null,
	                            'Network Out'
	                        ),
	                        _react2.default.createElement(
	                            'span',
	                            { className: 'stat' },
	                            this.state.networkOut,
	                            'b/s'
	                        )
	                    )
	                ),
	                _react2.default.createElement(
	                    'div',
	                    { id: 'bars', className: 'block wide' },
	                    _react2.default.createElement(
	                        'strong',
	                        null,
	                        'CPU'
	                    ),
	                    _react2.default.createElement(
	                        'div',
	                        { className: 'bar ' + this.state.cpuColor },
	                        _react2.default.createElement(
	                            'span',
	                            null,
	                            this.state.cpuPercentage,
	                            '%'
	                        )
	                    ),
	                    _react2.default.createElement(
	                        'strong',
	                        null,
	                        'Memory'
	                    ),
	                    _react2.default.createElement(
	                        'div',
	                        { className: 'bar ' + this.state.memoryColor },
	                        _react2.default.createElement(
	                            'span',
	                            null,
	                            this.state.memoryPercentage,
	                            '%'
	                        )
	                    ),
	                    _react2.default.createElement(
	                        'h3',
	                        null,
	                        'Disks'
	                    ),
	                    disks
	                )
	            );
	        }
	    }]);

	    return Status;
	}(_react.Component);

	exports.default = Status;
	;

/***/ },
/* 3 */
/***/ function(module, exports, __webpack_require__) {

	// removed by extract-text-webpack-plugin

/***/ },
/* 4 */,
/* 5 */
/***/ function(module, exports, __webpack_require__) {

	module.exports = ReactDOM;

/***/ },
/* 6 */
/***/ function(module, exports, __webpack_require__) {

	module.exports = _;

/***/ }
]);