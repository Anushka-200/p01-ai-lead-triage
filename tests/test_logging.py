import json
import logging

from app.logging_setup import JsonFormatter, log_event


def make_record(level=logging.INFO, event="something_happened", exc_info=None, **fields):
    record = logging.LogRecord("p01.test", level, __file__, 1, event, (), exc_info)
    for k, v in fields.items():
        setattr(record, k, v)
    return record


def test_output_is_valid_json_with_the_core_fields():
    line = JsonFormatter().format(make_record())
    data = json.loads(line)  # raises if it isn't valid JSON
    assert data["event"] == "something_happened"
    assert data["level"] == "INFO"
    assert "ts" in data and "logger" in data


def test_extra_fields_are_merged_into_the_json():
    line = JsonFormatter().format(make_record(message_id=42, action="new"))
    data = json.loads(line)
    assert data["message_id"] == 42 and data["action"] == "new"


def test_standard_log_record_internals_are_not_leaked():
    line = JsonFormatter().format(make_record())
    data = json.loads(line)
    # 'msg', 'args', 'pathname' etc. are LogRecord plumbing, not our event data
    assert "msg" not in data and "args" not in data and "pathname" not in data


def test_exception_info_is_included_when_present():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        line = JsonFormatter().format(make_record(level=logging.ERROR, exc_info=sys.exc_info()))
    data = json.loads(line)
    assert "ValueError: boom" in data["exc_info"]


def test_log_event_helper_passes_fields_through(caplog):
    logger = logging.getLogger("p01.helper_test")
    with caplog.at_level(logging.INFO, logger="p01.helper_test"):
        log_event(logger, logging.INFO, "message_delivered", message_id=7)
    assert caplog.records[0].message_id == 7
    assert caplog.records[0].getMessage() == "message_delivered"


def test_a_value_that_is_not_json_serializable_does_not_crash_the_formatter():
    class Weird:
        def __str__(self):
            return "weird-thing"

    line = JsonFormatter().format(make_record(thing=Weird()))
    assert json.loads(line)["thing"] == "weird-thing"
