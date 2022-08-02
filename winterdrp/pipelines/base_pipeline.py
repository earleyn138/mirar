import logging
import os

import astropy.io.fits
import numpy as np
import copy
from winterdrp.paths import saturate_key
from winterdrp.errors import ErrorStack

logger = logging.getLogger(__name__)

core_fields = ["OBSCLASS", "TARGET", "UTCTIME"]


class Pipeline:
    pipelines = {}
    name = None

    @property
    def pipeline_configurations(self):
        raise NotImplementedError()

    @property
    def gain(self):
        raise NotImplementedError()

    @property
    def non_linear_level(self):
        raise NotImplementedError()

    def __init__(
            self,
            pipeline_configuration: str | list = None,
            night: int | str = "",
    ):

        self.night_sub_dir = os.path.join(self.name, night)

        self.processors = self.load_pipeline_configuration(pipeline_configuration)

        self.configure_processors(sub_dir=self.night_sub_dir)

        for i, (processor) in enumerate(self.processors):

            logger.debug(f"Initialising processor {processor.__class__}")
            processor.set_preceding_steps(previous_steps=self.processors[:i])
            processor.check_prerequisites()

        logger.debug("Pipeline initialisation complete.")

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls.name in cls.pipelines.keys():
            err = f"Pipeline name '{cls.name}' is already found in the pipeline registered keys. " \
                  f"The Pipeline class variable 'name' must be unique!"
            logger.error(err)
            raise ValueError(err)
        cls.pipelines[cls.name] = cls

    def configure_processors(
            self,
            sub_dir: str = ""
    ):
        for processor in self.processors:
            processor.set_night(night_sub_dir=sub_dir)

    @staticmethod
    def download_raw_images_for_night(
            night: str | int
    ):
        raise NotImplemented

    def load_pipeline_configuration(
            self,
            configuration: str | list = None,
    ):
        if isinstance(configuration, str | None):
            return copy.copy(self.pipeline_configurations[configuration])
        else:
            return copy.copy(configuration)

    def reduce_images(
            self,
            batches: list[list[list[np.ndarray], list[astropy.io.fits.header]]],
            output_error_path: str = None,
            catch_all_errors: bool = False
    ):
        err_stack = ErrorStack()

        for i, processor in enumerate(self.processors):
            logger.debug(f"Applying '{processor.__class__}' processor to {len(batches)} batches. "
                         f"(Step {i+1}/{len(self.processors)})")

            batches, new_err_stack = processor.base_apply(
                batches
            )
            err_stack += new_err_stack

            if np.logical_and(not catch_all_errors, len(err_stack.reports) > 0):
                raise err_stack.reports[0].error

        err_stack.summarise_error_stack(output_path=output_error_path)
        return batches, err_stack

    def set_saturation(
            self,
            header: astropy.io.fits.Header
    ) -> astropy.io.fits.Header:
        # update the SATURATE keyword in the header for subsequent sextractor runs
        co_add_head = header['COADDS']
        num_co_adds = int(co_add_head)
        saturation_level = self.non_linear_level * num_co_adds
        if "SKMEDSUB" in header.keys():
            saturation_level -= header['SKMEDSUB']
        header.append((saturate_key, saturation_level, 'Saturation level'), end=True)
        return header