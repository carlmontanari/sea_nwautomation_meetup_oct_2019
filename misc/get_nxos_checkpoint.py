#!/usr/bin/env python
from napalm import get_network_driver


def main():
    driver = get_network_driver("nxos_ssh")
    conn = driver(hostname="172.18.0.12", username="vrnetlab", password="VR-netlab9")
    conn.open()
    checkpoint = conn._get_checkpoint_file()
    conn.close()
    with open("nxos_checkpoint", "w") as f:
        f.write(checkpoint)


if __name__ == "__main__":
    main()
