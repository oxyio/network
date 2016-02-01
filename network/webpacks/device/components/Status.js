// oxy.io Network
// File: network/webpacks/device/status.js
// Desc: the device status component

import _ from 'lodash';
import React, { Component } from 'react';


class Bar extends Component {
    getPercentageColor(percent) {
        if (percent >= 90)
            return 'red';

        else if (percent >= 80)
            return 'orange';

        else if (percent > 70)
            return 'yellow';

        return 'green';
    }

    formatPercentage(percent) {
        return percent.toFixed(1);
    }

    render() {
        return (
            <div>
                <strong>{this.props.title}</strong>

                <div className={'bar ' + this.getPercentageColor(this.props.percent)}>
                    <div style={{width: this.props.percent + '%'}}></div>
                    <span>
                        {this.formatPercentage(this.props.percent)}%
                    </span>
                </div>
            </div>
        );
    }
}


export default class Status extends Component {
    constructor(props) {
        super(props)

        this.state = {
            load: 0,
            networkIn: 0,
            networkOut: 0,
            cpuPercentage: 0,
            cpuColor: '',
            memoryPercentage: 0,
            memoryColor: '',
            disks: []
        };
    }

    parseNetworkStats(stats) {
        let transmitBytes = 0;
        let receiveBytes = 0;

        _.each(stats, (stat) => {
            if (stat.detail == 'receive_bytes')
                receiveBytes += stat.value;

            if (stat.detail == 'transmit_bytes')
                transmitBytes += stat.value;
        });

        this.setState({
            networkIn: receiveBytes,
            networkOut: transmitBytes
        });
    }

    parseCpuStats(stats) {
        const totalPercent = _.reduce(stats, (memo, stat) => {
            if (stat.key == 'cpu')
                memo += stat.value;

            return memo;
        }, 0);

        this.setState({
            cpuPercentage: totalPercent
        });
    }

    parseMemoryStats(stats) {
        const data = {
            total: 0,
            free: 0,
            cached: 0,
            buffers: 0
        }

        _.each(stats, (stat) => {
            if (stat.key != 'memory')
                return;

            _.each(_.keys(data), (key) => {
                if (stat.detail === key)
                    data[key] = stat.value;
            });
        });

        const used = data.total - data.free - data.cached - data.buffers;
        const usedPercent = (used / data.total) * 100;

        this.setState({
            memoryPercentage: usedPercent
        });
    }

    parseDiskStats(stats) {
        const diskData = {};

        _.each(stats, (stat) => {
            if (!diskData[stat.key])
                diskData[stat.key] = {};

            diskData[stat.key][stat.detail] = stat.value;
        });

        const disks = _.reduce(diskData, (memo, data, name) => {
            const total = data.available + data.used;
            const percentage = data.used / total * 100;

            memo.push({
                name: name,
                percentage: percentage
            });

            return memo;
        }, []);

        this.setState({
            disks: disks
        });
    }

    handleEvent(msg) {
        const { data, event } = JSON.parse(msg.data);

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
                console.error(`Unknown device stat type: ${event}`, data)
        }
    }

    componentDidMount() {
        const ws = new WebSocket(
            'ws://' + window.location.host + '/websocket?key=' + this.props.requestKey
        );

        ws.addEventListener('message', this.handleEvent.bind(this));
    }

    render() {
        const disks = _.reduce(this.state.disks, (memo, disk) => {
            memo.push(
                <Bar
                    key={disk.name}
                    title={`Disk: ${disk.name}`}
                    percent={disk.percentage}
                />
            );

            return memo;
        }, []);

        return (
            <div className='block base'>
                <div className='block third'>
                    <div className='block third'>
                        <strong>Load</strong>
                        <span className='stat'>{this.state.load}</span>
                    </div>
                    <div className='block third'>
                        <strong>Network In</strong>
                        <span className='stat'>{this.state.networkIn}b/s</span>
                    </div>
                    <div className='block third'>
                        <strong>Network Out</strong>
                        <span className='stat'>{this.state.networkOut}b/s</span>
                    </div>
                </div>

                <div className='block third'>
                    <Bar
                        title='CPU'
                        percent={this.state.cpuPercentage}
                    />

                    <Bar
                        title='Memory'
                        percent={this.state.memoryPercentage}
                    />
                </div>

                <div className='block third'>
                    {disks}
                </div>
            </div>
        );
    }
};
