
from . import utils


def sort_pyobject(sans):
    processor = utils.Sorter()
    if not processor.is_sortable(sans):
        raise SystemError('Input is not sortable.')

    return processor.sort()


def sort_json(sans):
    processor = utils.Sorter()
    if not processor.is_json_sortable(sans):
        raise SystemError('Input is not sortable.')

    return utils._convert_to_json(processor.sort())
