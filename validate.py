#!/usr/bin/env python
import re

from nornir import InitNornir
from nornir.core.task import Result
from nornir.plugins.tasks import networking
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from nornsible import InitNornsible, nornsible_delegate, nornsible_task

from helper import process_results

# disable urllib3 warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def find_all_interface_ips(inventory):
    pingable_ips = {}
    for host, host_data in inventory.items():
        eth_ints = host_data["ethernet_interfaces"]
        loop_ints = host_data["loopback_interfaces"]
        intfs = {**eth_ints, **loop_ints}
        ips = [
            intfs[intf]["routed"]["ip"].split("/")[0]
            for intf in intfs
            if "routed" in intfs[intf].keys()
        ]
        pingable_ips[host] = ips
    return pingable_ips


@nornsible_delegate
def gather_reachable_interfaces(task):
    """
    Gather all ips from inventory that should be reachable

    Arguments:
        task: nornir task object

    Returns:
        reachable_ips: dict of hosts and reachable ips#

    Raises:
        N/A  # noqa

    """
    unfiltered_inventory = InitNornir(config_file="nornir_data/config.yaml")
    all_hosts = unfiltered_inventory.inventory.hosts
    reachable_ips = find_all_interface_ips(all_hosts)
    task.host["reachable_ips"] = reachable_ips
    return "IPs gathered and stored in inventory['delegate']['reachable_ips']"


@nornsible_task
def test_reachability(task, timeout=1, count=5, reachable_ips=None):
    """
    Test reachability from all devices

    Arguments:
        task: nornir task object
        timeout: (optional) timeout in seconds
        count: (optional) number of pings to send
        reachable_ips: (optional) dictionary of hosts:[ips] to ping

    Returns:
        N/A  # noqa

    Raises:
        N/A  # noqa

    """
    if reachable_ips is None:
        reachable_ips = task.nornir.inventory.hosts["delegate"]["reachable_ips"]

    reachability_results = {}
    ping_failures = False
    for host, ips in reachable_ips.items():
        reachability_results[host] = {}
        for ip in ips:
            if task.host.platform == "nxos":
                cmd = f"ping {ip} timeout {timeout} count {count}"
            else:
                cmd = f"ping {ip} timeout {timeout} repeat {count}"
            result = task.run(task=networking.netmiko_send_command, command_string=cmd, enable=True)
            packet_loss = re.search(r"([\d\.]+)% packet loss", result.result)
            if packet_loss:
                packet_loss = packet_loss.group(1)
                if 100 - int(float(packet_loss)) < 100:
                    ping_failures = True
                    result = "Fail"
                else:
                    result = "Pass"
            else:
                ping_failures = True
                result = "Fail"

            reachability_results[host][ip] = result
            task.results.pop()
    return Result(host=task.host, result=reachability_results, failed=ping_failures, changed=True)


def _validate_ospf_peers_nxos(task):
    missing_peers = []
    cmd = "show ip ospf neighbor vrf default"
    result = task.run(
        task=networking.netmiko_send_command, command_string=cmd, enable=True, use_textfsm=True
    )
    for peer in task.host.data["expected_state"]["ospf"]["expected_peers"]:
        if peer not in [r["local_ipaddr"] for r in result.result]:
            missing_peers.append(peer)
            continue
        for r in result.result:
            if r["local_ipaddr"] == peer and not r["state"].startswith("FULL"):
                missing_peers.append(peer)
    return missing_peers


def _validate_ospf_peers_eos(task):
    missing_peers = []
    cmd = "show ip ospf neighbor"
    result = task.run(
        task=networking.netmiko_send_command, command_string=cmd, enable=True, use_textfsm=True
    )
    for peer in task.host.data["expected_state"]["ospf"]["expected_peers"]:
        if peer not in [r["address"] for r in result.result]:
            missing_peers.append(peer)
            continue
        for r in result.result:
            if r["address"] == peer and r["state"] != "FULL":
                missing_peers.append(peer)
    return missing_peers


@nornsible_task
def validate_ospf_peers(task):
    if task.host.platform == "nxos":
        missing_peers = _validate_ospf_peers_nxos(task)
    else:
        missing_peers = _validate_ospf_peers_eos(task)

    task.results.pop()

    if missing_peers:
        result = f"The following peer(s) are missing or down: {missing_peers}"
        return Result(host=task.host, result=result, failed=True, changed=True)
    result = "All ospf peers validated successfully!"
    return Result(host=task.host, result=result, failed=False, changed=False)


@nornsible_task
def validate_bgp_neighbors(task):
    missing_neighbors = []
    result = task.run(task=networking.napalm_get, getters=["bgp_neighbors"])
    for neighbor in task.host.data["expected_state"]["bgp"]["expected_neighbors"]:
        if neighbor not in result.result["bgp_neighbors"]["global"]["peers"]:
            missing_neighbors.append(neighbor)
            continue
        if result.result["bgp_neighbors"]["global"]["peers"][neighbor]["is_up"] is False:
            missing_neighbors.append(neighbor)

    task.results.pop()

    if missing_neighbors:
        result = f"The following neighbor(s) are missing or down: {missing_neighbors}"
        return Result(host=task.host, result=result, failed=True, changed=True)
    result = "All bgp neighbors validated successfully!"
    return Result(host=task.host, result=result, failed=False, changed=False)


def _validate_routes_nxos(task):
    missing_routes = []
    for route in task.host.data["expected_state"]["routes"]:
        cmd = f"show ip route {route}"
        result = task.run(task=networking.netmiko_send_command, command_string=cmd)
        if "Route not found" in result.result or route not in result.result:
            missing_routes.append(route)
            continue
        if task.host.data["expected_state"]["routes"][route]["via"] not in result.result:
            missing_routes.append(route)
            continue
        if (
            len(task.host.data["expected_state"]["routes"][route]["next_hops"])
            != result.result.count("via") - 1
        ):
            missing_routes.append(route)
            continue
        task.results.pop()
    return missing_routes


def _validate_routes_eos(task):
    missing_routes = []
    for route in task.host.data["expected_state"]["routes"]:
        result = task.run(
            task=networking.napalm_get,
            getters=["get_route_to"],
            getters_options={"get_route_to": {"destination": route}},
        )
        routes = result.result["get_route_to"]
        if route not in routes.keys():
            missing_routes.append(route)
            continue
        if len(routes[route]) != len(
            task.host.data["expected_state"]["routes"][route]["next_hops"]
        ):
            missing_routes.append(route)
            continue
        if (
            routes[route][0]["protocol"].lower()
            != task.host.data["expected_state"]["routes"][route]["via"]
        ):
            missing_routes.append(route)
        task.results.pop()
    return missing_routes


@nornsible_task
def validate_routes(task):
    if task.host.platform == "nxos":
        missing_routes = _validate_routes_nxos(task)

    else:
        missing_routes = _validate_routes_eos(task)

    if missing_routes:
        result = (
            "The following routes(s) are missing, have incorrect number of next hops, "
            f"or are leaned via the wrong protocol: {missing_routes}"
        )
        return Result(host=task.host, result=result, failed=True, changed=True)
    result = "All routes validated successfully!"
    return Result(host=task.host, result=result, failed=False, changed=False)


def main():
    tasks = [
        gather_reachable_interfaces,
        test_reachability,
        validate_ospf_peers,
        validate_bgp_neighbors,
        validate_routes,
    ]

    nr = InitNornir(config_file="nornir_data/config.yaml")
    nr = InitNornsible(nr)

    for task in tasks:
        task_result = nr.run(task=task)
        process_results(nr, task_result)


if __name__ == "__main__":
    main()
