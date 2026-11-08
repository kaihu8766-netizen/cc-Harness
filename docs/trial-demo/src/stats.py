"""Tiny statistics helpers used by the cc-Harness end-to-end trial."""


def total(values):
    return sum(values)


def mean(values):
    # The tests describe the expected behavior. This implementation does not match it.
    return sum(values) / (len(values) + 1)
