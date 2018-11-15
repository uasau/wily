"""
Compares metrics between uncommitted files and indexed files
"""
from wily import logger
import wily.cache as cache
from wily.config import DEFAULT_GRID_STYLE
from wily.operators import resolve_metric, resolve_operator, get_metric
import tabulate


def diff(config, files, metrics, changes_only=True):
    """
    Show the differences in metrics for each of the files.

    :param config: The wily configuration
    :type  config: :namedtuple:`wily.config.WilyConfig`
    """
    archiver = config.archiver
    config.targets = files
    if cache.has_index(config, archiver):
        index = cache.get_index(config, archiver)
        last_revision = index[0]
    else:
        raise RuntimeError("Missing index, run `wily build`.")

    # Convert the list of metrics to a list of metric instances
    operators = {resolve_operator(metric.split(".")[0]) for metric in metrics}
    metrics = [(metric.split(".")[0], resolve_metric(metric)) for metric in metrics]
    data = {}
    results = []

    # Build a set of operators
    _operators = [operator.cls(config) for operator in operators]

    for operator in _operators:
        logger.debug(f"Running {operator.name} operator")
        data[operator.name] = operator.run(None, config)

    # Write a summary table..
    last_entry = cache.get(config, archiver, last_revision["revision"])

    for file in files:
        try:
            metrics_data = []
            has_changes = False
            for operator, metric in metrics:
                current = get_metric(
                    last_entry["operator_data"], operator, file, metric.name
                )
                new = data[operator][file][metric.name]
                if new != current:
                    has_changes = True
                metrics_data.append("{0:n} -> {1:n}".format(current, new))
            if has_changes or not changes_only:
                results.append((file, *metrics_data))
            else:
                logger.debug(metrics_data)
        except KeyError as e:
            logger.debug(f"Could not find {e}")
            pass

    descriptions = [metric.description for operator, metric in metrics]
    headers = ("File", *descriptions)
    if len(results) > 0:
        print(
            # But it still makes more sense to show the newest at the top, so reverse again
            tabulate.tabulate(
                headers=headers, tabular_data=results, tablefmt=DEFAULT_GRID_STYLE
            )
        )
