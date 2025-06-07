import os
import tempfile
import unittest
from unittest.mock import patch
import configparser

import FTP_Connection

class TestLoadFtpConfig(unittest.TestCase):
    def test_missing_option_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            try:
                with open('connections.ini', 'w') as f:
                    f.write('[FTP]\n')
                    f.write('host=localhost\n')
                    f.write('port=21\n')
                    f.write('password=secret\n')  # missing user option
                with patch.object(FTP_Connection, 'messagebox') as mock_msg:
                    with self.assertRaises(configparser.Error):
                        FTP_Connection.load_ftp_config()
                    self.assertTrue(mock_msg.showerror.called)
            finally:
                os.chdir(cwd)

if __name__ == '__main__':
    unittest.main()
