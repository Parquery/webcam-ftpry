#!/usr/bin/env python3

# pylint: disable=missing-docstring

import unittest

import cv2
import numpy as np

import webcam_ftpry


class TestWebcamFtpry(unittest.TestCase):
    def test_rotate(self):
        img = np.zeros((512, 512, 3), np.uint8)
        img[:] = (255, 255, 255)
        cv2.line(img, (0, 256), (512, 256), (0, 0, 255), 5)

        rotated = webcam_ftpry.rotate(image=img, angle=45.2)

        self.assertTrue((rotated[200, 520, :] == np.array([0, 0, 255])).all())
        self.assertTrue((rotated[222, 533, :] == np.array([255, 255, 255])).all())
        self.assertTrue((rotated[193, 564, :] == np.array([0, 0, 0])).all())


if __name__ == '__main__':
    unittest.main()
