import unittest
from types import SimpleNamespace
from unittest.mock import patch

import app


class AppLogicTests(unittest.TestCase):
    @patch('app._local_account_exists', return_value=True)
    @patch('app.os.getenv', side_effect=lambda key: {
        'APPDATA': r'C:\Temp\SUPER_NOVA_TEST',
        'USERNAME': 'current-user',
    }.get(key))
    @patch('builtins.open', create=True)
    def test_stale_saved_username_falls_back_to_current_user(
        self, mock_open, _getenv, _account_exists
    ):
        mock_open.return_value.__enter__.return_value.read.return_value = 'old-user'
        self.assertEqual(app.get_target_username(), 'current-user')

    @patch('app._local_account_exists', return_value=True)
    @patch('app.os.getenv', side_effect=lambda key: {
        'APPDATA': r'C:\Temp\SUPER_NOVA_TEST',
        'USERNAME': 'Current-User',
    }.get(key))
    @patch('builtins.open', create=True)
    def test_saved_username_matching_current_user_is_kept(
        self, mock_open, _getenv, _account_exists
    ):
        mock_open.return_value.__enter__.return_value.read.return_value = 'current-user'
        self.assertEqual(app.get_target_username(), 'current-user')

    def test_value_after_colon_ignores_non_field_lines(self):
        self.assertIsNone(app.value_after_colon('SSID'))
        self.assertEqual(app.value_after_colon('SSID : Office'), 'Office')

    @patch('app._load_saved_password_state', return_value=True)
    @patch(
        'app.win32net.NetUserGetInfo',
        return_value={
            'flags': app.win32netcon.UF_PASSWD_NOTREQD,
            'password_age': 123,
        },
    )
    def test_explicit_no_password_flag_wins_over_saved_state(
        self, _get_info, _load_state
    ):
        self.assertFalse(app.has_password('test-user'))

    @patch('app._load_saved_password_state', return_value=False)
    @patch('app.run_powershell', return_value=SimpleNamespace(returncode=0, stdout='SET'))
    @patch(
        'app.win32security.LogonUser',
        side_effect=app.win32security.error(1326, 'bad password', None),
    )
    @patch(
        'app.win32net.NetUserGetInfo',
        return_value={'flags': 0, 'password_age': 123},
    )
    def test_saved_empty_state_resolves_stale_password_date(
        self, _get_info, _logon_user, _run_powershell, _load_state
    ):
        self.assertFalse(app.has_password('test-user'))

    @patch('app.account_allows_blank_password', return_value=True)
    @patch('app.verifier_ancien_mdp', return_value=None)
    def test_restricted_blank_password_is_accepted_when_account_allows_it(
        self, _verify, _allows_blank
    ):
        self.assertTrue(app.verifier_mdp_actuel('test-user', ''))


if __name__ == '__main__':
    unittest.main()
