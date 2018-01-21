
import re


def parse(version):
    # type: (str) -> list
    """ Transform version string into comparable list
    :param version: version string, e.g. 0.11.23rc1
    :return: list of version chunks, e.g. [0, 11, 23, 'rc1']
    """
    chunks = []
    for chunk in re.findall(r"(\d+|[A-Za-z]\w*)", version):
        try:
            chunk = int(chunk)
        except ValueError:
            pass
        chunks.append(chunk)
    return chunks


def compare(ver1, ver2):
    # type: (str, str) -> int
    """Compares two version string, returning {-1|0|1} just as cmp().
    >>> compare_versions("0.1.1", "0.1.2")
    -1
    >>> compare_versions("0.1.2", "0.1.1")
    1
    >>> compare_versions("0.1", "0.1.1")
    0
    >>> compare_versions("0.1.1rc1", "0.1.1a")
    1
    >>> compare_versions("0.1.1rc1", "0.1.1")
    -1
    """
    chunks1 = parse(str(ver1))
    chunks2 = parse(str(ver2))
    min_len = min(len(chunks1), len(chunks2))
    for i in range(min_len):
        if chunks1[i] > chunks2[i]:
            return 1
        elif chunks1[i] < chunks2[i]:
            return -1
    if len(chunks1) > min_len and isinstance(chunks1[min_len], str):
        return -1
    if len(chunks2) > min_len and isinstance(chunks2[min_len], str):
        return 1
    return 0
