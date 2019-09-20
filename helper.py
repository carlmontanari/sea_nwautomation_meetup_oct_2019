from nornsible import print_result


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
