from src.rore.shell import create_parser
import unittest


class RoreTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        parser = create_parser()
        cls.parser = parser


class IssueTestCase(RoreTestCase):
    def test_with_empty_args(self):
        self.assertRaises(SystemExit, self.parser.parse_args, [])

    def test_issue_argument(self):
        pass
