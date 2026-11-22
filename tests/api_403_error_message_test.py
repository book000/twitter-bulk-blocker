import unittest
from unittest import mock

from twitter_blocker.api import TwitterAPI


def make_api(threshold_reached):
    api = object.__new__(TwitterAPI)
    api.retry_manager = mock.Mock()
    api.retry_manager.error_classifier.classify_403_error.return_value = (
        "generic_403", "description", "low")
    api.cookie_manager = mock.Mock()
    api.cookie_manager.force_refresh_on_error_threshold.return_value = threshold_reached
    api.error_analytics = mock.Mock()
    api._403_error_stats = {"total_403_errors": 0, "classified_errors": {}}
    api._session_start_time = 0
    api.enable_header_enhancement = False
    api._check_early_warning_conditions = mock.Mock()
    api._is_account_locked = mock.Mock(return_value=False)
    return api


def non_json_403():
    response = mock.Mock()
    response.status_code = 403
    response.text = "Forbidden"
    response.headers = {}
    response.json.side_effect = ValueError("not JSON")
    return response


class NonJson403Test(unittest.TestCase):
    def test_below_threshold_records_analytics(self):
        api = make_api(threshold_reached=False)
        message, error_type = api._get_detailed_error_message(non_json_403(), "user")
        self.assertEqual(error_type, "generic_403")
        api.error_analytics.record_error_with_context.assert_called_once()
        api.error_analytics.update_hourly_stats.assert_called_once()

    def test_threshold_reached_sleeps_then_records_analytics(self):
        api = make_api(threshold_reached=True)
        with mock.patch("twitter_blocker.api.time.sleep") as sleep:
            message, error_type = api._get_detailed_error_message(non_json_403(), "user")
        sleep.assert_called_once_with(10)
        self.assertEqual(error_type, "generic_403")
        api.error_analytics.record_error_with_context.assert_called_once()


if __name__ == "__main__":
    unittest.main()
