# mpts - multithreaded ping two subnets

**mpts** is a Python script that executes multithreaded ping tests against two CIDR/24 subnets concurrently.

Default subnets:  192.168.1.0/24 and 192.168.2.0/24

Typical execution time: < 5s  (depending upon subnet performance, of course)

## Requirements / Assumptions

* Linux (or macOS)
* Python 3.7+

## Usage

```python
python3 mpts.py
# executes ping test against default subnets 192.168.1.0/24 and 192.168.2.0/24

python3 mpts.py --cidr1 192.168.3.0/24 --cidr2 192.168.4.0/24
# executes ping test against specified subnets 192.168.3.0/24 and 192.168.4.0/24

python3 mpts.py --skip 72
# executes ping test against default subnets skipping the specified final octet

python3 -m unittest test_mpts.py
# executes tests
```
## Sample Output
```
Failed ping requests in 192.168.1.0/24:  ['192.168.1.25', '192.168.1.67', '192.168.1.87']
Failed ping requests in 192.168.2.0/24:  ['192.168.2.43', '192.168.2.87', '192.168.2.175']
Final octets of failed ping requests in 192.168.1.0/24, but not 192.168.2.0/24:  [25, 67]
Final octets of failed ping requests in 192.168.2.0/24, but not 192.168.1.0/24:  [43, 175]
Final octets of failed ping requests in both 192.168.1.0/24 and 192.168.2.0/24:  [87]
```

## Possible Future Features
* The current ping timeout is set to 1s.  It would be relatively easy to add a new option to allow custom specification of the ping timeout.
* Ping retries is currently set to 2.  It would be relatively easy to add a new option to allow custom specification of ping retry attempts.
* Windows implements ping slightly differently than Linux/macOS.  Thus, mpts may or may not work as expected in Windows.  But it should be relatively easy to add Windows support if desired.

## Feature Requests

Feature requests are welcome.  If you wish mpts worked differently or if you have an idea for a new needed feature, please just let me know.  I am happy to modify or improve mpts, as time allows.

## License
[The Unlicense](https://choosealicense.com/licenses/unlicense/)

A license with no conditions whatsoever which dedicates works to the public domain. Unlicensed works, modifications, and larger works may be distributed under different terms and without source code.
