#!/usr/bin/env python3
"""
Captures images from a web cam and uploads them to an FTP server.
"""
import argparse
import contextlib
import datetime
import ftplib
import getpass
import logging
import pathlib
import tempfile
import time
from typing import Optional  # pylint: disable=unused-import

import numpy as np
import cv2
import reconnecting_ftp


def rotate(image: np.array, angle: float) -> np.array:
    """
    Rotates the image around the center, expanding the image if necessary.

    :param image: to rotate
    :param angle: counter-clockwise
    :return: rotated image
    """
    # Inspired by https://www.pyimagesearch.com/2017/01/02/rotate-images-correctly-with-opencv-and-python/
    (height, width) = image.shape[:2]
    center_x, center_y = (width // 2, height // 2)

    rotmat = cv2.getRotationMatrix2D((center_x, center_y), angle, 1.0)

    cos = np.abs(rotmat[0, 0])
    sin = np.abs(rotmat[0, 1])

    new_width = int((height * sin) + (width * cos))
    new_height = int((height * cos) + (width * sin))

    # adjust the rotation matrix to take into account translation
    rotmat[0, 2] += (new_width / 2) - center_x
    rotmat[1, 2] += (new_height / 2) - center_y

    # perform the actual rotation and return the image
    return cv2.warpAffine(image, rotmat, (new_width, new_height))


def upload(ftp: reconnecting_ftp.Client, local_path: pathlib.Path, remote_path: pathlib.Path) -> None:
    """
    Uploads the image to the FTP server
    :param ftp: client
    :param local_path: image on the local disk
    :param remote_path: image on the remote disk
    :return:
    """
    logger = logging.getLogger('webcam_ftpry')

    remote_parent = remote_path.parent
    pwd = pathlib.Path(ftp.pwd())

    err_perm = None  # type: Optional[ftplib.error_perm]

    for dirname in remote_parent.parts:
        try:
            ftp.cwd(dirname=dirname)
        except ftplib.error_perm as err:
            err_perm = err

        if err_perm is not None:
            if str(err_perm).startswith('550 '):
                ftp.mkd(dirname=dirname)
                ftp.cwd(dirname=dirname)
                pwd = pwd / dirname
            else:
                msg = "Failed to create the directory {!r} in {!r}; aborting the upload".format(dirname, pwd.as_posix())
                logger.log(logging.ERROR, msg)
                return

    with local_path.open('rb') as fid:
        ftp.storbinary('STOR {}'.format(remote_path.name), fid)


class Params:
    """
    Parsed command line parameters
    """

    # pylint: disable=too-many-instance-attributes
    def __init__(self):
        self.device_id = 0
        self.operation_dir = None  # type: Optional[pathlib.Path]
        self.period = 0.0
        self.angle = 0.0
        self.hostname = ''
        self.port = 0
        self.user = ''
        self.password = ''
        self.path_format = ''


def run(params: Params) -> None:
    """
    Runs the webcam_ftpry.

    :param params: parsed command-line parameters
    :return:
    """
    ftp = reconnecting_ftp.Client(
        hostname=params.hostname, port=params.port, user=params.user, password=params.password)

    with contextlib.ExitStack() as exit_stack:
        if params.operation_dir:
            operation_dir = pathlib.Path(params.operation_dir)
            operation_dir.mkdir(exist_ok=True, parents=True)
        else:
            tmp_dir = tempfile.TemporaryDirectory()
            exit_stack.push(tmp_dir)
            operation_dir = pathlib.Path(tmp_dir.name)

        cap = cv2.VideoCapture(params.device_id)
        exit_stack.callback(callback=cap.release)

        ftp.__enter__()
        exit_stack.push(ftp)

        logger = logging.getLogger('webcam_ftpry')

        latest_upload = None  # type: Optional[datetime.datetime]
        while True:
            ret, frame = cap.read()
            if not ret:
                raise RuntimeError("Unexpected end of video")

            now = datetime.datetime.utcnow()
            if latest_upload is None or (now - latest_upload).total_seconds() > params.period:
                remote_pth = pathlib.Path(now.strftime(params.path_format))

                with tempfile.NamedTemporaryFile(
                        prefix=remote_pth.stem, suffix=remote_pth.suffix, dir=operation_dir.as_posix()) as tmp_file:
                    local_pth = pathlib.Path(tmp_file.name)

                    if params.angle:
                        frame = rotate(image=frame, angle=params.angle)

                    ret = cv2.imwrite(local_pth.as_posix(), frame)
                    if not ret:
                        raise RuntimeError("Failed to save the image to: {}".format(local_pth))

                    msg = "Uploading the image from local {} to remote {}...".format(local_pth, remote_pth)
                    logger.log(logging.INFO, msg)

                    upload(ftp=ftp, local_path=local_pth, remote_path=remote_pth)
                    latest_upload = now

                    msg = "Image uploaded to {}".format(remote_pth)
                    logger.log(logging.INFO, msg)


def main() -> None:
    """"
    Main routine
    """
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--device_id", help="Device ID of the web cam", default=0, type=int)
    parser.add_argument("--operation_dir", help="operation directory; if not specified, uses mkdtemp")
    parser.add_argument("--period", help="between two captures, in seconds", type=float, required=True)
    parser.add_argument("--angle", help="if set, rotates the image counter-clockwise; in degrees", type=float)
    parser.add_argument("--hostname", help="of the ftp server", required=True)
    parser.add_argument("--port", help="port to upload to", type=int, default=21)
    parser.add_argument("--user", help="user name on the FTP server", default='')
    parser.add_argument("--password", help="password to access the FTP server; if not set, asked on the prompt")
    parser.add_argument(
        "--path_format",
        help="format of the remote path; using strftime syntax, timestamps in UTC",
        default='/%Y%m%dT%H%M%S.jpg')
    args = parser.parse_args()

    params = Params()
    params.device_id = int(args.device_id)
    params.operation_dir = pathlib.Path(args.operation_dir) if args.operation_dir else None
    params.period = int(args.period)
    params.angle = float(args.angle)
    params.hostname = str(args.hostname)
    params.port = int(args.port)
    params.user = str(args.user)
    params.password = str(args.password) if args.password else getpass.getpass()
    params.path_format = str(args.path_format)

    logging.Formatter.converter = time.gmtime
    logging.basicConfig(level=logging.INFO)

    run(params=params)


if __name__ == "__main__":
    main()
