"""Tests - mpts - Multithreaded Ping Two Subnets

    Note:  Some unique challenges are posed in testing mpts, most notably:
    a. mpts runs in multithreaded mode
    b. mpts utilizes subprocess calls which are not (by themselves)
       easily mocked
    c. mocks cannot typically/easily be varied based upon internal parameters
       under test (e.g., mock a ping result based upon a specific ip address
       currently under test)
    Thus, some simplifying assumptions were made:
    a. Rather than mocking the ping request itself, we simply mock returncodes.
    b. Rather than mocking returncodes for specific ip addresses, we simply
       mock various successes and failures over the course of the mpts run and
       ensure that the correct results are recorded and reported as expected.

    We use the unittest framework and mocks for our tests, but these tests are
    intended as functional tests or end-to-end tests rather than unit tests.

    Primarily, we are focused on verifying:
    a. Ping successes
    b. Ping failures
    c. Recording and accurately reporting failures:
          i.   in CIDR1/24 only
          ii.  in CIDR2/24 only
          iii. in both CIDR1/24 and CIDR2/24

    Expected execution time:  ~3 minutes
    Note:  Ping failures (by nature) are slower than successes, and for testing
    purposes we generate many failures.

"""

import unittest
from unittest.mock import Mock
import mpts


class TestMPTS(unittest.TestCase):

    def test_mock_all_pings_pass(self):
        """Verifies ping success scenario via mocked returncode 0
        """
        mpts.get_returncode = Mock()
        # mock returncode - all IP addresses pass ping
        mpts.get_returncode.return_value = 0
        result = mpts.main([])
        self.assertFalse(result[0])  # failed_ips1 is empty
        self.assertFalse(result[1])  # failed_ips2 is empty
        self.assertFalse(result[2])  # failed_ips1_excl_octets is empty
        self.assertFalse(result[3])  # failed_ips2_excl_octets is empty
        self.assertFalse(result[4])  # failed_ips_common_octets is empty

    def test_mock_all_pings_fail(self):
        """Verifies ping failure scenario via mocked returncode 1
        """
        mpts.get_returncode = Mock()
        # mock returncode - all IP addresses fail ping
        mpts.get_returncode.return_value = 1
        result = mpts.main([])
        # failed_ips1 is full
        self.assertTrue(len(result[0]) == 255)
        # failed_ips2 is full
        self.assertTrue(len(result[1]) == 255)
        # failed_ips1_excl_octets is empty
        self.assertFalse(result[2])
        # failed_ips2_excl_octets is empty
        self.assertFalse(result[3])
        # failed_ips_common_octets is full
        self.assertTrue(len(result[4]) == 255)

    def test_mock_many_pings_fail(self):
        """Verifies mixed success/failure results via mock with side_effect.
           The side_effect introduces a combination of numerous failures and
           successes.
           The accurate reporting of failures is verified via verify_octets.
        """
        mpts.get_returncode = Mock()
        side_effect_values = [(lambda x: 1 if x < 300 else 0)
                              for x in range(2000)]
        # the first 300 ping attempts fail, the rest succeed
        mpts.get_returncode.side_effect = side_effect_values
        result = mpts.main([])
        self.assertTrue(len(result[0]) > 5)  # failed_ips1 has numerous values
        self.assertTrue(len(result[1]) > 5)  # failed_ips2 has numerous values
        # note: failed_ips1_excl_octets is indeterminate due to mt timing
        # note: failed_ips2_excl_octets is indeterminate due to mt timing
        # failed_ips_common_octets has numerous values
        self.assertTrue(len(result[4]) > 5)
        # verify the detailed results are as expected
        self.verify_octets(result)

    def test_all_options(self):
        """Verifies that all optional arguments work as expected:
           --cid1, --cidr2, --skip
        """
        mpts.get_returncode = Mock()
        # mock returncode - all IP addresses fail ping
        mpts.get_returncode.return_value = 1

        # custom subnets and skip
        result = mpts.main(['--cidr1', '192.168.7.0/24', '--cidr2',
                            '192.168.8.0/24', '--skip', '42'])
        # custom CIDR1/24 is correctly pinged
        self.assertTrue(all(['192.168.7.' in ip[1] for ip in result[0]]))
        # custom CIDR2/24 is correctly pinged
        self.assertTrue(all(['192.168.8.' in ip[1] for ip in result[1]]))
        # skipped octet is skipped (not tested)
        self.assertTrue(42 not in result[2] and 42 not in result[3] and 42
                        not in result[4])

    def test_no_options(self):
        """Verifies that no optional arguments works as expected.
        """
        mpts.get_returncode = Mock()
        # mock returncode - all IP addresses fail ping
        mpts.get_returncode.return_value = 1

        result = mpts.main([])  # default subnets with no octets skipped
        # default CIDR1/24 is correctly pinged
        self.assertTrue(all(['192.168.1.' in ip[1] for ip in result[0]]))
        # default CIDR2/24 is correctly pinged
        self.assertTrue(all(['192.168.2.' in ip[1] for ip in result[1]]))
        # no octets skipped
        self.assertTrue(len(result[4]) == 255)

    def verify_octets(self, result):
        """Verifies that the final octets of failed ping requests are correctly
           reported.
        """
        # generate cidr1 prefix (first three octets)
        cidr1_octets = result[0][0][1].split(".")
        cidr1_prefix = f"{cidr1_octets[0]}.{cidr1_octets[1]}.{cidr1_octets[2]}"
        # generate cidr2 prefix (first three octets)
        cidr2_octets = result[1][0][1].split(".")
        cidr2_prefix = f"{cidr2_octets[0]}.{cidr2_octets[1]}.{cidr2_octets[2]}"
        # generate list of cidr1 ips from list of tuples
        cidr1_ips_list = []
        for item in result[0]:
            cidr1_ips_list.append(item[1])
        # generate list of cidr2 ips from list of tuples
        cidr2_ips_list = []
        for item in result[1]:
            cidr2_ips_list.append(item[1])
        # verify list of cidr1 failed octets matches cidr1 failed ip list
        for octet in result[2]:
            full_ip = f"{cidr1_prefix}.{octet}"
            self.assertTrue(full_ip in cidr1_ips_list)
        # verify list of cidr2 failed octets matches cidr2 failed ip list
        for octet in result[3]:
            full_ip = f"{cidr2_prefix}.{octet}"
            self.assertTrue(full_ip in cidr2_ips_list)
        # verify list of both cidr1 and cidr2 failed octets matches both
        # cidr1 and cidr2 failed ip list
        for octet in result[4]:
            full_ip1 = f"{cidr1_prefix}.{octet}"
            full_ip2 = f"{cidr2_prefix}.{octet}"
            self.assertTrue(full_ip1 in cidr1_ips_list and full_ip2
                            in cidr2_ips_list)
