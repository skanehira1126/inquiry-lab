class DuplicateNodeIdError(ValueError):
    """A tree already contains a node with the supplied ID."""


class NodeNotFoundError(KeyError):
    """The requested ID does not identify a node in this tree."""


class InvalidTreeFormatError(ValueError):
    """A decoded JSON document does not match the saved tree format."""


class InvalidSearchFilterError(ValueError):
    """A node type, status, or their combination is invalid for tree search."""


class InvalidConnectionError(ValueError):
    pass


class ParentNotFoundError(ValueError):
    pass
