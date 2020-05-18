"""mpts - Multithreaded Ping Two Subnets (designed for two CIDR/24 subnets)

This script concurrently pings (in multithreaded mode) two separate CIDR/24
subnets (called CIDR1/24 and CIDR2/24) and outputs:
    1. All ping results
    2. If all success:
        "Both CIDR1/24 and CIDR2/24 are fully responding to ping requests.
         No failures."
    3. If any failures:
        a. IP addresses in CIDR1/24 that failed ping
        b. IP addresses in CIDR2/24 that failed ping
        c. Final octets of failed ping requests in CIDR1/24 but not CIDR2/24
        d. Final octets of failed ping requests in CIDR2/24 but not CIDR1/24
        e. Final octets of failed ping requests in both CIDR1/24 and CIDR2/24
"""

from subprocess import Popen
from subprocess import PIPE
from threading import Thread
import ipaddress
import queue
import sys
import getopt


def initiate_ping_queues(cidr1, cidr2, skip):
    """Initiates the multithreaded ping queues

    Parameters
    ----------
        cidr1 : str
            The CIDR1/24 subnet (e.g., "192.168.1.0/24")
        cidr2 : str
            The CIDR2/24 subnet (e.g., "192.168.2.0/24")
        skip : str
            A skipped octet, if any

    Returns
    -------
        result : list
    """
    num_threads = 20
    ips_q1, ips_q2 = queue.Queue(), queue.Queue()
    ips1, ips2 = [], []
    failed_ips1, failed_ips2 = [], []

    for ip in ipaddress.IPv4Network(cidr1):
        ip_str = str(ip)
        octets = ip_str.split(".")
        final_octet = int(octets[3])
        if final_octet == 0 or final_octet == skip:
            continue  # disregard 0 (broadcast) octet or skipped octet
        ips1.append((final_octet, ip_str))

    for ip in ipaddress.IPv4Network(cidr2):
        ip_str = str(ip)
        octets = ip_str.split(".")
        final_octet = int(octets[3])
        if final_octet == 0 or final_octet == skip:
            continue  # disregard 0 (broadcast) octet or skipped octet
        ips2.append((final_octet, ip_str))

    # start the queue1 thread pool
    for i in range(num_threads):
        worker = Thread(target=ping_thread, args=(i, ips_q1, failed_ips1))
        worker.setDaemon(True)
        worker.start()

    # fill queue1
    for ip in ips1:
        ips_q1.put(ip)

    # start the queue2 thread pool
    for i in range(num_threads):
        worker = Thread(target=ping_thread, args=(i, ips_q2, failed_ips2))
        worker.setDaemon(True)
        worker.start()

    # fill queue2
    for ip in ips2:
        ips_q2.put(ip)

    # wait until queue1 worker threads are done to exit
    ips_q1.join()

    # wait until queue2 worker threads are done to exit
    ips_q2.join()

    result = print_results(cidr1, failed_ips1, cidr2, failed_ips2)
    return result


def ping_thread(i, q, faillist):
    """Single ping thread

    Parameters
    ----------
    i : int
        thread id
    q : queue.Queue()
        multithreaded ping queue
    faillist : list
        List containing tuples of failed CIDR/24 IP addresses.
        Each tuple contains the final octet and the IP address.

    Returns
    -------
    None.
    """
    while True:
        ip = q.get()
        attempt = 1
        while attempt < 4:
            with Popen(['ping', '-c', '1', '-W', '1', ip[1]], stdout=PIPE) \
              as response:
                result = response.wait()
                # print the ping output if desired
                # print(response.communicate()[0])
                return_code = get_returncode(ip, response)
                if return_code == 0:
                    print(ip[1], 'is up')
                    break
                elif return_code != 0 and attempt == 3:
                    print(ip[1], 'is down')
                    faillist.append(ip)
                    break
                else:
                    print(ip[1], f"failed ping - attempt {attempt}")
                    attempt += 1
        q.task_done()


def get_returncode(ip, response):
    """Returns the returncode of the ping request.
       Deliberately extracted into function to allow mock of ping request
    """
    return response.returncode


def print_results(cidr1, failed_ips1, cidr2, failed_ips2):
    """Displays the results of the multithreaded ping queues

    Parameters
    ----------
    cidr1 : str
        The first subnet (CIDR1/24)
    cidr2 : str
        The second subnet (CIDR2/24)
    failed_ips1 : list
        List containing tuples of failed CIDR1/24 IP addresses.
        Each tuple contains the final octet and the IP address.
    failed_ips2 : list
        List containing tuples of failed CIDR2/24 IP addresses.
        Each tuple contains the final octet and the IP address.

    Returns
    -------
    failed_ips1 : list
        List containing tuples of failed CIDR1/24 IP addresses.
        Each tuple contains the final octet and the IP address.
    failed_ips2 : list
        List containing tuples of failed CIDR2/24 IP addresses.
        Each tuple contains the final octet and the IP address.
    failed_ips1_excl_octets : list
        List containing final octets of pings that failed CIDR1/24 (only).
    failed_ips2_excl_octets : list
        List containing final octets of pings that failed CIDR2/24 (only).
    failed_ips_common_octets : list
        List containing final octets of pings that failed CIDR1/24
        and CIDR2/24 (both).
    """
    failed_ips1_octets = [item[0] for item in failed_ips1]
    failed_ips2_octets = [item[0] for item in failed_ips2]
    failed_ips1_addrs = [item[1] for item in failed_ips1]
    failed_ips2_addrs = [item[1] for item in failed_ips2]

    failed_ips1_excl_octets, failed_ips_common_octets = [], []
    for octet in failed_ips1_octets:
        if octet not in failed_ips2_octets:
            failed_ips1_excl_octets.append(octet)
        else:
            failed_ips_common_octets.append(octet)

    failed_ips2_excl_octets = []
    for octet in failed_ips2_octets:
        if octet not in failed_ips1_octets:
            failed_ips2_excl_octets.append(octet)

    failed_ips1_excl_octets.sort()
    failed_ips2_excl_octets.sort()
    failed_ips_common_octets.sort()

    if not failed_ips1 and not failed_ips2:
        print(f"Both {cidr1} and {cidr2} are fully responding to ping "
              f"requests.  No failures.")
    else:
        print(f"Failed ping requests in {cidr1}: ", failed_ips1_addrs)
        print(f"Failed ping requests in {cidr2}: ", failed_ips2_addrs)
        print(f"Final octets of failed ping requests in {cidr1}, but not "
              f"{cidr2}: ", failed_ips1_excl_octets)
        print(f"Final octets of failed ping requests in {cidr2}, but not "
              f"{cidr1}: ", failed_ips2_excl_octets)
        print(f"Final octets of failed ping requests in both {cidr1} and "
              f"{cidr2}: ", failed_ips_common_octets)
    return (failed_ips1, failed_ips2, failed_ips1_excl_octets,
            failed_ips2_excl_octets, failed_ips_common_octets)


def main(argv):
    """Main method which takes arguments from the command line
        Available command line arguments include:
        --cidr1 <CIDR1>   Allows specification of custom CIDR1/24 subnet
        --cidr2 <CIDR2>   Allows specification of custom CIDR2/24 subnet
        --skip <octet>    Allows specification of octet to be excluded from
                          ping test

        Returns
        -------
        result : list
    """
    cidr1 = "192.168.1.0/24"
    cidr2 = "192.168.2.0/24"
    skip = ""
    try:
        opts, args = getopt.getopt(argv, "h", ["cidr1=", "cidr2=", "skip="])
    except getopt.GetoptError:
        print("usage:  python3 mpts.py --cidr1 <CIDR1/24> --cidr2 <CIDR2/24> "
              "--skip <octet>")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("help:  python3 mpts.py --cidr1 <CIDR1/24> --cidr2 "
                  "<CIDR2/24> --skip <octet>")
            sys.exit()
        if opt in ("--cidr1"):
            cidr1 = arg
            if cidr1[-3:] != "/24":
                print("--cidr1 and --cidr2 accept CIDR/24 subnets only.")
                sys.exit()
        elif opt in ("--cidr2"):
            cidr2 = arg
            if cidr2[-3:] != "/24":
                print("--cidr1 and --cidr2 accept CIDR/24 subnets only.")
                sys.exit()
        elif opt in ("--skip"):
            skip = arg
            try:
                skip = int(skip)
                assert 0 <= skip <= 255
            except ValueError or AssertionError:
                print("--skip <octet> must have a valid octet value (0 <= "
                      "octet <= 255)")
                sys.exit()
        else:
            assert False, "unhandled option"

    print("")
    print("CIDR1: ", cidr1)
    print("CIDR2: ", cidr2)
    result = initiate_ping_queues(cidr1, cidr2, skip)
    return result


if __name__ == "__main__":
    main(sys.argv[1:])
