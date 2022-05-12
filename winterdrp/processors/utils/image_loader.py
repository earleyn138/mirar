import os

import astropy.io.fits
import numpy as np
from winterdrp.paths import get_output_path, get_output_dir, latest_save_key, latest_mask_save_key
from winterdrp.processors.base_processor import BaseProcessor
from winterdrp.paths import raw_img_key, core_fields
import logging
from collections.abc import Callable
from winterdrp.io import open_fits
from glob import glob

logger = logging.getLogger(__name__)

print(raw_img_key)



class ImageLoader(BaseProcessor):

    base_key = "load"

    def __init__(
            self,
            input_sub_dir: str,
            load_image: Callable = open_fits,
            *args,
            **kwargs
    ):
        self.input_sub_dir = input_sub_dir
        self.load_image = load_image

    def open_raw_image(
            self,
            path: str
    ) -> tuple[np.array, astropy.io.fits.Header]:

        data, header = self.load_image(path)

        for key in core_fields:
            if key not in header.keys():
                err = f"Essential key {key} not found in header. " \
                      f"Please add this field first. Available fields are: {list(header.keys())}"
                logger.error(err)
                raise KeyError(err)

        return data.astype(np.float64), header

    def open_raw_image_batch(
            self,
            paths: list
    ) -> tuple[list, list]:

        images = []
        headers = []
        for path in paths:
            data, header = self.open_raw_image(path)
            images.append(data)
            headers.append(header)

        return images, headers

    def _apply_to_images(
            self,
            images: list[np.ndarray],
            headers: list[astropy.io.fits.Header],
    ) -> tuple[list[np.ndarray], list[astropy.io.fits.Header]]:

        input_dir = get_output_dir(
            self.input_sub_dir,
            sub_dir=self.night_sub_dir
        )

        img_list = glob(f'{input_dir}/*.fits')

        new_images = []
        new_headers = []

        for path in img_list:
            img, header = self.open_raw_image(path)
            new_images.append(img)
            new_headers.append(header)

        return new_images, new_headers





    


