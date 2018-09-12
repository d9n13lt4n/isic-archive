# Vagrant > 1.8.1 is required due to
# https://github.com/mitchellh/vagrant/issues/6793
Vagrant.require_version ">= 1.8.3"

def true?(obj)
  obj = obj.to_s.downcase
  obj != "false" && obj != "off" && obj != "0"
end

Vagrant.configure("2") do |config|
  bind_node_modules = true?(ENV.fetch("BIND_NODE_MODULES", Vagrant::Util::Platform.windows?))

  config.vm.box = "ubuntu/bionic64"
  config.vm.hostname = "isic-archive.devel"
  config.vm.provider "virtualbox" do |virtualbox|
    virtualbox.name = "isic-archive.devel"
    virtualbox.memory = 2048
    # Prevent 'xenial-16.04-cloudimg-console.log' from being created
    virtualbox.customize [ "modifyvm", :id, "--uartmode1", "disconnected" ]
  end

  config.vm.network :private_network, ip: "192.168.3.10"
  config.vm.network "forwarded_port", guest: 80, host: 8080
  config.vm.post_up_message = "ISIC Archive is running at http://localhost:8080"

  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.synced_folder ".", "/home/vagrant/isic_archive"

  config.vm.provision "ansible_local" do |ansible|
    ansible.provisioning_path = "/home/vagrant/isic_archive/ansible"
    ansible.galaxy_role_file = "requirements.yml"
    ansible.playbook = "vagrant-playbook.yml"
    ansible.extra_vars = {
      ansible_python_interpreter: "/usr/bin/python2.7",
      bind_node_modules: bind_node_modules,
      isic_archive_clone: false
    }
  end

  config.ssh.forward_agent = true
  config.ssh.forward_x11 = true
end
