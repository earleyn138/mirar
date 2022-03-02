import astropy.io.fits
import numpy as np
import os
from winterdrp.io import create_fits
import logging
import pandas as pd
from collections.abc import Callable
from winterdrp.processors.base_processor import ProcessorWithCache
from winterdrp.paths import cal_output_dir
# from winterdrp.pipelines.base_pipeline import Pipeline

logger = logging.getLogger(__name__)


def default_select_bias(
       observing_log: pd.DataFrame
) -> [str]:
    mask = observing_log["OBJECT"].lower() == "flat"
    return list(observing_log[mask]["RAWIMAGEPATH"])


class FlatCalibrator(ProcessorWithCache):

    base_name = "master_flat"
    base_key = "flat"

    def __init__(
            self,
            instrument_vars: dict,
            select_cache_images: Callable[[pd.DataFrame], list] = default_select_bias,
            *args,
            **kwargs
    ):
        super().__init__(instrument_vars, *args, **kwargs)
        self.x_min = int(instrument_vars["x_min"])
        self.x_max = int(instrument_vars["x_max"])
        self.y_min = int(instrument_vars["y_min"])
        self.y_max = int(instrument_vars["y_max"])
        self.flat_nan_threshold = instrument_vars["flat_nan_threshold"]
        self.select_cache_images = select_cache_images

    def get_file_path(
            self,
            header: astropy.io.fits.Header,
            sub_dir: str = ""
    ):
        cal_dir = cal_output_dir(sub_dir=sub_dir)
        filtername = header['FILTER'].replace(" ", "_")
        name = f"{self.base_name}_{filtername}.fits"
        return os.path.join(cal_dir, name)

    def _apply_to_images(
            self,
            images: list,
            headers: list,
            sub_dir: str = ""
    ) -> (list, list):

        for i, data in enumerate(images):
            header = headers[i]
            master_flat, _ = self.load_cache_file(self.get_file_path(header, sub_dir=sub_dir))
            if np.any(master_flat < self.flat_nan_threshold):
                master_flat[master_flat < self.flat_nan_threshold] = np.nan
            data = data / master_flat
            header["CALSTEPS"] += "flat,"
            images[i] = data
            headers[i] = header
        return images, headers

    def make_cache_files(
            self,
            image_list: list,
            preceding_steps: list,
            sub_dir: str = "",
            *args,
            **kwargs
    ):

        logger.info(f'Found {len(image_list)} flat frames')

        _, primary_header = self.open_fits(image_list[0])

        nx = primary_header['NAXIS1']
        ny = primary_header['NAXIS2']

        filter_list = []

        for flat in image_list:
            _, header = self.open_fits(flat)
            filter_list.append(header['FILTER'])

        image_list = np.array(image_list)

        for filt in list(set(filter_list)):

            mask = np.array([x == filt for x in filter_list])

            cut_flat_list = image_list[mask]

            n_frames = np.sum(mask)

            logger.info(f'Found {n_frames} frames for filer {filt}')

            flats = np.zeros((ny, nx, n_frames))

            for i, flat in enumerate(cut_flat_list):
                logger.debug(f'Reading flat {i + 1}/{n_frames}')

                img, header = self.open_fits(flat)

                # Iteratively apply corrections
                for f in preceding_steps:
                    img, header = f([img], [header], sub_dir=sub_dir)

                median = np.nanmedian(img[0][self.x_min:self.x_max, self.y_min:self.y_max])
                flats[:, :, i] = img / median

            logger.info(f'Median combining {n_frames} flats')

            master_flat = np.nanmedian(flats, axis=2)

            # Create a new HDU with the processed image data

            primary_header['BZERO'] = 0
            primary_header["FILTER"] = filt

            master_flat_path = self.get_file_path(primary_header, sub_dir=sub_dir)

            logger.info(f"Saving stacked 'master flat' for f {filt} to {master_flat_path}")

            self.save_fits(master_flat, primary_header, master_flat_path)


class StandardFlatCalibrator(FlatCalibrator):

    def __init__(
            self,
            open_fits: Callable[[str], astropy.io.fits.HDUList],
            x_min: float = 0.,
            x_max: float = np.inf,
            y_min: float = 0.,
            y_max: float = np.inf,
            flat_nan_threshold: float = np.nan,
            standard_flat_dir: str = None
    ):
        FlatCalibrator.__init__(
            self,
            open_fits=open_fits,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            flat_nan_threshold=flat_nan_threshold
        )
        if standard_flat_dir is None:
            err = "For StandardFlatCalibrator, you must specify "
            logger.error(err)
            raise ValueError(err)

    def make_cache_files(
            self,
            image_list: list,
            sub_dir: str = "",
            subtract_bias: Callable[[astropy.io.fits.HDUList], astropy.io.fits.HDUList] = None,
            subtract_dark: Callable[[astropy.io.fits.HDUList], astropy.io.fits.HDUList] = None,
            **kwargs
    ):
        pass

    def get_file_path(
            self,
            header: astropy.io.fits.Header,
            sub_dir: str = ""
    ):
        cal_dir = cal_output_dir(sub_dir=sub_dir)
        filtername = header['FILTER']
        name = f"{self.base_name}_{filtername}.fits"
        return os.path.join(cal_dir, name)