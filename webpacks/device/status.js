'use strict';

var _ = require('lodash');
var React = require('react');
var AnimateMixin = require('react-animate');


var getBarColour = function(percentage) {
    if (percentage > 90)
        return 'red';
    else if (percentage > 70)
        return 'orange';
    else
        return 'green';
};

var parseCpuStats = function(stats) {
};

var parseMemoryStats = function(stats) {
    /*Take memory stats (includes memory & swap) and return a memory percentage.*/
    var memoryPercentage;

    _.each(stats, function(stat) {
        if (stat.key == 'memory') {
            var used = stat.total - stat.free - stat.cached;
            memoryPercentage = used / stat.total * 100;
        }
    });

    return memoryPercentage.toFixed(2);
};

var Status = React.createClass({
    mixins: [AnimateMixin],

    getInitialState: function() {
        return {
            load: 0,
            networkIn: 0,
            networkOut: 0,
            cpuPercentage: 0,
            cpuColour: '',
            memoryPercentage: 0,
            memoryColour: '',
            disks: []
        };
    },

    componentDidMount: function() {
        var ws = new WebSocket(
            'ws://' + window.location.host + '/websocket?key=' + this.props.requestKey
        );

        ws.addEventListener('message', function(msg) {
            var data = JSON.parse(msg.data);

            switch(data.event) {
                case 'memory':
                    var memoryPercentage = parseMemoryStats(data.data);

                    // Animate the bar
                    this.animate(
                        'memory-bar-width',
                        {width: this.state.memoryPercentage + '%'},
                        {width: memoryPercentage + '%'},
                        100
                    );

                    // Set the value & bar colour
                    this.setState({
                        memoryPercentage: memoryPercentage,
                        memoryColour: getBarColour(memoryPercentage)
                    });
            }
        }.bind(this));
    },

    render: function() {
        return (<div>
                <div className="block threeeighth">
                    <div className="block base">
                        <div className="block quarter">
                            <strong>Load</strong>
                            <span className="stat">{this.state.load}</span>
                        </div>
                        <div className="block threequarter">
                            <div className="block base">
                                <div className="block half">
                                    <strong>Network In</strong>
                                    <span className="stat">{this.state.networkIn}</span>
                                </div>
                                <div className="block half">
                                    <strong>Network Out</strong>
                                    <span className="stat">{this.state.networkOut}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div id="bars" className="block wide">
                        <strong>CPU</strong>
                        <div className={'bar ' + this.state.cpuColour}>
                            <div style={this.getAnimatedStyle('cpu-bar-width')}></div>
                            <span>{this.state.cpuPercentage}%</span>
                        </div>

                        <strong>Memory</strong>
                        <div className={'bar ' + this.state.memoryColour}>
                            <div style={this.getAnimatedStyle('memory-bar-width')}></div>
                            <span>{this.state.memoryPercentage}%</span>
                        </div>

                        <strong>Disk: /vz</strong>
                        <div className="bar red">
                            <div style={{width: 75 + '%'}}></div>
                            <span>95.2%</span>
                        </div>
                    </div>
                </div>

                <div className="block half">
                    STATUS HISTORY GRAPHS
                </div>
        </div>);
    }
});

module.exports = Status;
