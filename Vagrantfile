# oxy.io Network
# File: Vagrantfile
# Desc: test devices (Linux, currently)

Vagrant.configure('2') do |config|
    # Attach our test SSH key
    config.ssh.insert_key = false
    config.ssh.private_key_path = '../../oxyio/test/insecure_private_key'

    # Disable shared folder
    config.vm.synced_folder '.', '/vagrant', disabled: true

    # Give the box less memory
    config.vm.provider 'virtualbox' do |vbox|
        vbox.customize ['modifyvm', :id, '--memory', 256]
    end

    # Ubuntu test device
    config.vm.define :ubuntu_device do |ubuntu_device|
        ubuntu_device.vm.box = 'ubuntu/trusty64'
        ubuntu_device.vm.hostname = 'oxypanel-ubuntu-device'
        ubuntu_device.vm.network :private_network, ip: '192.168.255.150'
    end

    # Debian test device
    config.vm.define :debian_device do |debian_device|
        debian_device.vm.box = 'debian/wheezy64'
        debian_device.vm.hostname = 'oxypanel-debian-device'
        debian_device.vm.network :private_network, ip: '192.168.255.151'
    end

    # Centos test device
    config.vm.define :centos_device do |centos_device|
        centos_device.vm.box = 'boxcutter/centos67'
        centos_device.vm.hostname = 'oxypanel-centos-device'
        centos_device.vm.network :private_network, ip: '192.168.255.152'
    end
end
