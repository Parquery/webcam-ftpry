#!/usr/bin/env python3
"""
Runs a live test.
"""
import argparse
import contextlib
import logging
import pathlib
import socket
import tempfile
import threading
from typing import Optional  # pylint: disable=unused-import
import time

import pyftpdlib.authorizers
import pyftpdlib.handlers
import pyftpdlib.servers

import webcam_ftpry


def find_free_port() -> int:
    """
    :return: a free port; mind that this is not multi-process safe and can lead to race conditions.
    """
    skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with contextlib.closing(skt):
        skt.bind(('', 0))
        _, port = skt.getsockname()
        return int(port)


class ThreadedFTPServer:
    """
    Creates a dummy FTP server which serves in a loop running in a separate thread.
    """

    # pylint: disable=too-many-instance-attributes

    def __init__(self, hostname: str, port: int, timeout: int, homedir: pathlib.Path, user: str, password: str) -> None:
        # pylint: disable=too-many-arguments
        self.port = port
        self.hostname = hostname
        self.timeout = timeout
        self.user = user
        self.password = password

        self.thread = None  # type: Optional[threading.Thread]
        self.lock = threading.Lock()
        self.__stop_flag = False

        authorizer = pyftpdlib.authorizers.DummyAuthorizer()
        authorizer.add_user(self.user, self.password, homedir=homedir.as_posix(), perm='elradfmwMT')

        handler = pyftpdlib.handlers.FTPHandler
        handler.authorizer = authorizer
        handler.timeout = self.timeout

        self.ftpd = pyftpdlib.servers.FTPServer((self.hostname, self.port), handler)

    def __enter__(self) -> None:
        def serve_forever() -> None:
            """ Serves the FTP clients in a poll loop and breaks as soon as __stop_flag was set """
            while not self.__stop_flag:
                with self.lock:
                    self.ftpd.serve_forever(timeout=0.001, blocking=False)

        self.thread = threading.Thread(target=serve_forever)
        self.thread.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.lock:
            self.__stop_flag = True
            self.ftpd.close_all()

        self.thread.join()


def main() -> None:
    """"
    Main routine
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--device_id", help="Device ID of the web cam", default=0, type=int)
    args = parser.parse_args()

    logging.Formatter.converter = time.gmtime
    logging.basicConfig(level=logging.DEBUG)

    with contextlib.ExitStack() as exit_stack:
        tmp_dir = tempfile.TemporaryDirectory()
        exit_stack.push(tmp_dir)

        homedir = pathlib.Path(tmp_dir.name)

        port = find_free_port()
        user = 'some-user'
        password = 'some-password'
        ftpd = ThreadedFTPServer(
            hostname='127.0.0.1', port=port, timeout=60, homedir=homedir, user=user, password=password)

        ftpd.__enter__()
        exit_stack.push(ftpd)

        params = webcam_ftpry.Params()
        params.device_id = int(args.device_id)
        params.operation_dir = None
        params.period = 5
        params.hostname = '127.0.0.1'
        params.port = port
        params.user = user
        params.password = password
        params.path_format = '/some-dir/%Y-%m-%d/%Y-%m-%dT%H-%M-%SZ.jpg'

        webcam_ftpry.run(params=params)


if __name__ == "__main__":
    main()
