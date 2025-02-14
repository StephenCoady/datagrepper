# SPDX-License-Identifier: GPL-2.0+
# Copyright 2018 Mike Bonnet <mikeb@redhat.com>

import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import datagrepper.app


class TestAPI(unittest.TestCase):
    def setUp(self):
        datagrepper.app.app.testing = True
        self.client = datagrepper.app.app.test_client()

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    def test_raw_defaults(self, grep):
        resp = self.client.get("/raw")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(grep.call_args[0], ())
        kws = grep.call_args[1]
        self.assertIsNone(kws["start"])
        self.assertIsNone(kws["end"])
        self.assertEqual(kws["page"], 1)
        self.assertEqual(kws["rows_per_page"], 25)
        self.assertEqual(kws["order"], "desc")
        for arg in [
            "users",
            "packages",
            "categories",
            "topics",
            "contains",
            "not_users",
            "not_packages",
            "not_categories",
            "not_topics",
        ]:
            self.assertEqual(kws[arg], [])

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    def test_raw_default_result(self, grep):
        resp = self.client.get("/raw")
        self.assertEqual(resp.status_code, 200)
        result = json.loads(resp.get_data())
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["pages"], 0)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["raw_messages"], [])

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    def test_raw_contains_delta(self, grep):
        # At one point, this would produce a traceback/500.
        resp = self.client.get("/raw?delta=14400&category=wat&contains=foo")
        self.assertEqual(resp.status_code, 200)

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    def test_raw_contains_delta_and_start(self, grep):
        resp = self.client.get("/raw?start=1564503781&delta=600")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(grep.call_args[0], ())
        kws = grep.call_args[1]

        expected_start = datetime.fromtimestamp(1564503781)
        self.assertEqual(kws["start"], expected_start)

        expected_end = expected_start + timedelta(seconds=600)
        self.assertEqual(kws["end"], expected_end)

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    @patch.dict(datagrepper.app.app.config, {"DEFAULT_QUERY_DELTA": 180})
    def test_raw_default_query_delta(self, grep):
        resp = self.client.get("/raw")
        self.assertEqual(resp.status_code, 200)
        kws = grep.call_args[1]
        # Verify the default query delta was applied
        self.assertEqual((kws["end"] - kws["start"]).total_seconds(), 180.0)

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    @patch.dict(datagrepper.app.app.config, {"DEFAULT_QUERY_DELTA": 180})
    def test_raw_default_query_delta_with_start(self, grep):
        resp = self.client.get("/raw?start=1564503781")
        self.assertEqual(resp.status_code, 200)
        kws = grep.call_args[1]
        # Verify the default query delta was not applied
        self.assertNotEqual((kws["end"] - kws["start"]).total_seconds(), 180.0)

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    @patch.dict(datagrepper.app.app.config, {"DEFAULT_QUERY_DELTA": 180})
    def test_raw_default_query_delta_with_delta(self, grep):
        resp = self.client.get("/raw?delta=7200")
        self.assertEqual(resp.status_code, 200)
        kws = grep.call_args[1]
        # Verify the default query delta was not applied
        self.assertEqual((kws["end"] - kws["start"]).total_seconds(), 7200.0)

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    @patch.dict(datagrepper.app.app.config, {"DEFAULT_QUERY_DELTA": 180})
    def test_raw_default_query_delta_with_end(self, grep):
        resp = self.client.get("/raw?end=1564503781")
        self.assertEqual(resp.status_code, 200)
        kws = grep.call_args[1]
        self.assertEqual((kws["end"] - kws["start"]).total_seconds(), 180.0)

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    def test_raw_default_query_with_start_and_end_native(self, grep):
        resp = self.client.get(
            "/raw?start=2012-01-02T03:04:05%2B00:00&end=2012-01-02T04:04:05%2B00:00"
        )
        self.assertEqual(resp.status_code, 200)
        kws = grep.call_args[1]
        self.assertEqual(
            kws["start"].astimezone(timezone.utc),
            datetime(2012, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(
            kws["end"].astimezone(timezone.utc),
            datetime(2012, 1, 2, 4, 4, 5, tzinfo=timezone.utc),
        )

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    def test_raw_contains_without_delta(self, grep):
        """https://github.com/fedora-infra/datagrepper/issues/206"""
        resp = self.client.get("/raw?category=wat&contains=foo")
        self.assertEqual(resp.status_code, 400)
        target = b"When using contains, specify a start at most eight months"
        assert target in resp.data, f"{target!r} not in {resp.data!r}"

    @patch("datagrepper.app.dm.Message.query", autospec=True)
    def test_id(self, query):
        msg = query.filter_by.return_value.first.return_value
        msg.__json__ = MagicMock(return_value={"key": "value"})
        resp = self.client.get("/id?id=one")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(query.filter_by.call_args, ((), {"msg_id": "one"}))

    @patch("datagrepper.app.count_all_messages", autospec=True, return_value=42)
    def test_count(self, count_all_messages):
        resp = self.client.get("/messagecount")
        self.assertEqual(resp.status_code, 200)
        result = json.loads(resp.get_data())
        self.assertEqual(result, {"messagecount": 42})

    @patch("datagrepper.app.dm.Message.grep", return_value=(0, 0, []))
    def test_chart_line(self, grep):
        resp = self.client.get("/charts/line")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, "image/svg+xml")
        self.assertIn(
            b'<svg xmlns:xlink="http://www.w3.org/1999/xlink', resp.get_data()
        )
