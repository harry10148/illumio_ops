"""Typed exception hierarchy for illumio_ops."""


class IllumioOpsError(Exception):
    pass


class APIError(IllumioOpsError):
    pass


class ConfigError(IllumioOpsError):
    pass


class ReportError(IllumioOpsError):
    pass


class AlertError(IllumioOpsError):
    pass


class SchedulerError(IllumioOpsError):
    pass


class EventError(IllumioOpsError):
    pass
