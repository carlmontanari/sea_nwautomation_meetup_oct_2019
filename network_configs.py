#!/usr/bin/env python
import pathlib
import re

from nornir import InitNornir
from nornir.core.task import Result
from nornir.plugins.tasks.text import template_file
from nornir.plugins.tasks.files import write_file
from nornir.plugins.tasks import networking
from nornir.plugins.functions.text import print_result
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from nornsible import InitNornsible, nornsible_task

# Disable urllib3 warnings
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


@nornsible_task
def render_configs(task):
    """
    Nornir task to render device configurations from j2 templates.

    Arguments:
        task: nornir task object

    Returns:
        result: custom created nornir results object

    Raises:
        N/A  # noqa

    """
    result = task.run(
        task=template_file,
        name="Base Template Configuration",
        template="base.j2",
        path=f"templates/{task.host['template_dir']}",
        **task.host,
    )
    task.host["config"] = result.result

    if "eos" in task.host.groups:
        task.host["config"] = "\n".join(
            [row for row in task.host["config"].splitlines() if not row == ""]
        )
    elif "nxos" in task.host.groups:
        task.host["config"] = re.sub(r"(^\s*$){2,}", "", task.host["config"], flags=re.M)
    task.results.pop()
    return Result(host=task.host, result=task.host["config"], failed=False, changed=True)


@nornsible_task
def backup_configs(task):
    """
    Nornir task to backup device configurations.

    Arguments:
        task: nornir task object

    Returns:
        N/A  # noqa

    Raises:
        N/A  # noqa

    """
    if task.host._get_connection_options_recursively("napalm").platform == "nxos":
        conn = task.host.get_connection("napalm", task.nornir.config)
        r = conn._get_checkpoint_file()
        task.host["backup_config"] = r
    else:
        r = task.run(
            task=networking.napalm_get, name="Backup Device Configuration", getters=["config"]
        )
        task.host["backup_config"] = r.result["config"]["running"]

    pathlib.Path("backups").mkdir(exist_ok=True)
    task.run(
        task=write_file, filename=f"backups/{task.host.name}", content=task.host["backup_config"]
    )


@nornsible_task
def deploy_configs(task):
    """
    Nornir task to deploy device configurations.

    Arguments:
        task: nornir task object

    Returns:
        N/A  # noqa

    Raises:
        N/A  # noqa

    """
    task.run(
        task=networking.napalm_configure,
        name="Deploy Configuration",
        configuration=task.host["config"],
        replace=True,
        dry_run=False,
    )


def process_results(nr, task_result):
    """
    Print results of task if failed, skipped if skipped, success if... you get the point

    Arguments:
        nr: nornir object
        task_result: nornir aggregated result object

    Returns:
        N/A  # noqa

    Raises:
        N/A  # noqa

    """
    if task_result.failed:
        print_result(task_result)
    elif task_result.name in nr.skip_tags:
        print(f"{task_result.name} SKIPPED!")
    else:
        print(f"{task_result.name} SUCCESS!")


def main():
    tasks = [render_configs, deploy_configs, backup_configs]
    nr = InitNornir(config_file="nornir_data/config.yaml")
    nr = InitNornsible(nr)

    for task in tasks:
        task_result = nr.run(task=task)
        process_results(nr, task_result)


if __name__ == "__main__":
    main()
