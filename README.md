[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

sea_nwautomation_meetup_oct_2019
=======

Repository for my demo/presentation "Nornir for ad hoc Configuration and Verification" for the inaugural Seattle Network Automation Meetup meeting!

- Samir's presentation on Batfish is [comingsoon!]()
- My presentation is [here](/presentation/Nornir_for_Adhoc_Tasks_Carl_Montanari.pdf)
- Eric's presentation on Network Evolution is [here](/presentation/Network_Automation_Evolution_Eric_Chou.pdf)
- Chip's presentation on Netbox and Peering Manager is [here](/presentation/Netbox_and_Peering_Manager_Chip_Marshall.pdf)

Huge thanks to Intentionet and Samir and Ratul for hosting the Meetup and to everyone who came out!

# Overview

In this presentation/demo I will outline how complete Nornir scripts can be slightly modified to support a more ad hoc style usage. A simple example of this is running a validation script, that would normally validate an entire network/site, against only a single host in the inventory, and controlling this host selection via simple command-line arguments. I will also demonstrate using Nornir with "tags", again controlled via command-line arguments. This allows for senior engineers/automation focused engineers to craft "complete" Nornir scripts (complete in that they run a full suite of configurations/validations against all hosts in an inventory) that are easily filtered down with simple flags to run a subset of tasks or against a subset of hosts.

# Demo Environment

This demo runs in a simple Ubuntu virtual machine, the only purpose of the vm is so that I can have native KVM support on my (mac) laptop. Within the virtual machine, [vrnetlab](https://github.com/plajjan/vrnetlab) was used to create containers for Cisco NX-OS and Arista vEOS devices. Other than that, there isn't much special about the environment!

# Caveats

- vEOS: The vEOS vmdk was booted up manually (using qemu/kvm), and the command `zerotouch disable` was ran. This ensures that the configuration can be saved -- without executing this command the vEOS image wants to be booted via ZTP or have this command executed and then be rebooted. Doing this *before* making the Docker container is important so NAPALM can actually save the configurations without vEOS complaining about ZTP.

- TextFSM: TextFSM is used for some parsing data in the demo. The EOS "show_ip_ospf_neighbor" template has been updated to include an extra digit representing the instance (I assume this is VRF instance but did not look into it closely), the updated template is here for reference:

```
Value NEIGHBOR_ID (\d+.\d+.\d+.\d+)
Value VRF (\S+)
Value PRIORITY (\d+)
Value STATE (\S+)
Value DEAD_TIME (\d+:\d+:\d+)
Value ADDRESS (\d+.\d+.\d+.\d+)
Value INTERFACE (\S+)

Start
  ^${NEIGHBOR_ID}\s+\d+\s+${VRF}\s+${PRIORITY}\s+${STATE}\s+${DEAD_TIME}\s+${ADDRESS}\s+${INTERFACE} -> Record

 ```
