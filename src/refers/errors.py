class TagAlreadyExistsError(Exception):
    pass


class MultipleTagsInOneLine(Exception):
    pass


class TagNotFoundError(Exception):
    pass


class OptionNotFoundError(Exception):
    pass


class DocumentAlreadyExistsError(Exception):
    pass


class NotAFileError(Exception):
    pass


class PyprojectNotFound(Exception):
    pass
