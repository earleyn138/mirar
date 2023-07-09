"""
Module for WINTER data reduction
"""
from mirar.io import open_fits
from mirar.paths import BASE_NAME_KEY, FITS_MASK_KEY
from mirar.pipelines.winter.config import (
    sextractor_anet_config,
    sextractor_autoastrometry_config,
    sextractor_photometry_config,
    swarp_config_path,
)
from mirar.pipelines.winter.generator import (
    scamp_config_path,
    winter_astrometric_catalog_generator,
    winter_photometric_catalog_generator,
    winter_reference_generator,
)
from mirar.pipelines.winter.load_winter_image import (
    load_proc_winter_image,
    load_raw_winter_image,
    load_stacked_winter_image,
)
from mirar.processors.astromatic import Scamp
from mirar.processors.astromatic.sextractor.sextractor import (
    Sextractor,
    sextractor_checkimg_map,
)
from mirar.processors.astromatic.swarp.swarp import Swarp
from mirar.processors.astrometry.anet.anet_processor import AstrometryNet
from mirar.processors.astrometry.validate import AstrometryStatsWriter
from mirar.processors.csvlog import CSVLog
from mirar.processors.dark import DarkCalibrator
from mirar.processors.mask import MaskPixelsFromPath, WriteMaskedCoordsToFile
from mirar.processors.photcal import PhotCalibrator
from mirar.processors.reference import GetReferenceImage
from mirar.processors.sky import NightSkyMedianCalibrator, SkyFlatCalibrator
from mirar.processors.split import SplitImage
from mirar.processors.utils import (
    ImageBatcher,
    ImageDebatcher,
    ImageLoader,
    ImageSaver,
    ImageSelector,
)
from mirar.processors.utils.multi_ext_parser import MultiExtParser

refbuild = [
    ImageDebatcher(),
    GetReferenceImage(
        ref_image_generator=winter_reference_generator,
    ),
    ImageSaver(output_dir_name="stacked_ref"),
]

BOARD_ID = 4
TARGET_NAME = "m39"
split = [
    MultiExtParser(
        input_sub_dir="raw/",
        extension_num_header_key="BOARD_ID",
        only_extract_num=BOARD_ID,
        output_sub_dir=f"raw_split_{BOARD_ID}",
    )
]

split_all_boards = [
    MultiExtParser(
        input_sub_dir="raw/",
        extension_num_header_key="BOARD_ID",
        output_sub_dir="raw_split",
    )
]
load = [
    ImageLoader(
        input_sub_dir=f"raw_split_{BOARD_ID}", load_image=load_raw_winter_image
    ),
    ImageSelector(("OBSTYPE", ["FOCUS", "DARK", "FLAT", "SCIENCE"])),
]

split_images = [
    ImageDebatcher(),
    SplitImage(n_x=1, n_y=2),
    ImageSaver(output_dir_name="split"),
]

load_all_boards = [
    ImageLoader(input_sub_dir="raw_split", load_image=load_raw_winter_image),
    ImageSelector(("OBSTYPE", ["FOCUS", "DARK", "FLAT", "SCIENCE"])),
]

load_proc = [
    ImageLoader(input_sub_dir=f"skysub_{BOARD_ID}", load_image=load_raw_winter_image),
    # ImageSelector(("TARGNAME", f"{TARGET_NAME}"), ("OBSTYPE", "SCIENCE")),
]

load_dark = [
    ImageLoader(input_sub_dir=f"darkcal_{BOARD_ID}", load_image=load_raw_winter_image),
    # ImageSelector(("TARGNAME", f"{TARGET_NAME}")),
]

load_anet = [
    ImageLoader(input_sub_dir=f"anet_{BOARD_ID}", load_image=load_proc_winter_image),
    # ImageSelector(("TARGNAME", f"{TARGET_NAME}"), ("OBSTYPE", "SCIENCE")),
]

load_stack = [
    ImageLoader(input_sub_dir=f"anet_{BOARD_ID}", load_image=load_proc_winter_image),
    # ImageSelector(("TARGNAME", f"{TARGET_NAME}"), ("OBSTYPE", "SCIENCE")),
    ImageBatcher("EXPTIME"),
]

load_multiboard_stack = [
    ImageLoader(
        input_sub_dir=f"stack_all_{TARGET_NAME}", load_image=load_stacked_winter_image
    ),
    ImageSelector(
        # ("TARGNAME", f"{TARGET_NAME}"),
        ("OBSTYPE", "SCIENCE"),
    ),
]
# ImageBatcher("COADDS")]
log = (
    split
    + load
    + [
        CSVLog(
            export_keys=[
                "FILTER",
                "UTCTIME",
                "EXPTIME",
                "OBSTYPE",
                "UNIQTYPE",
                "BOARD_ID",
                "OBSCLASS",
                "TARGET",
                "FILTER",
                "BASENAME",
                "TARGNAME",
                "RADEG",
                "DECDEG",
                "MEDCOUNT",
                "STDDEV",
                "T_ROIC",
            ]
        )
    ]
)

log_all_boards = (
    split_all_boards
    + load_all_boards
    + [
        CSVLog(
            export_keys=[
                "FILTER",
                "UTCTIME",
                "EXPTIME",
                "OBSTYPE",
                "UNIQTYPE",
                "BOARD_ID",
                "OBSCLASS",
                "TARGET",
                "FILTER",
                "BASENAME",
                "TARGNAME",
                "RADEG",
                "DECDEG",
                "MEDCOUNT",
                "STDDEV",
                "T_ROIC",
            ]
        )
    ]
)

dark_cal = [
    ImageSelector(("BOARD_ID", f"{BOARD_ID}")),
    ImageBatcher(["BOARD_ID", "EXPTIME", "SUBCOORD"]),
    WriteMaskedCoordsToFile(output_dir="mask_raw"),
    DarkCalibrator(cache_sub_dir=f"calibration_{BOARD_ID}"),
    ImageSaver(output_dir_name=f"darkcal_{BOARD_ID}"),
    ImageDebatcher(),
]

dark_cal_all_boards = [
    ImageBatcher(["BOARD_ID", "EXPTIME", "SUBCOORD"]),
    WriteMaskedCoordsToFile(output_dir="mask_raw"),
    DarkCalibrator(cache_sub_dir="calibration"),
    ImageSaver(output_dir_name="darkcal"),
    ImageDebatcher(),
]

flat_cal = [
    # ImageSelector(("OBSTYPE", ["FOCUS", "SCIENCE", "FLAT"])),
    # ImageSelector(("TARGNAME", ["INTERESTING"])),
    # ImageBatcher(["BOARD_ID", "FILTER"]),
    # FlatCalibrator(flat_mask_key=FITS_MASK_KEY,
    #                cache_sub_dir=f"calibration_{board_id}"
    #                ),
    ImageSelector(("OBSTYPE", ["SCIENCE"]), ("TARGNAME", f"{TARGET_NAME}")),
    ImageBatcher(["BOARD_ID", "FILTER", "TARGNAME", "EXPTIME", "SUBCOORD"]),
    SkyFlatCalibrator(flat_mask_key=FITS_MASK_KEY, cache_sub_dir=f"skycals_{BOARD_ID}"),
    ImageSelector(("OBSTYPE", ["SCIENCE"])),
    ImageSaver(output_dir_name=f"skyflatcal_{BOARD_ID}"),
    NightSkyMedianCalibrator(flat_mask_key=FITS_MASK_KEY),
    ImageSaver(output_dir_name=f"skysub_{BOARD_ID}"),
]

flat_cal_all_boards = [
    # ImageSelector(("OBSTYPE", ["SCIENCE"]), ("TARGNAME", f"{TARGET_NAME}")),
    ImageSelector(("OBSTYPE", ["SCIENCE"])),
    ImageBatcher(["BOARD_ID", "FILTER", "EXPTIME", "SUBCOORD"]),
    SkyFlatCalibrator(flat_mask_key=FITS_MASK_KEY, cache_sub_dir="skycals"),
    ImageSelector(("OBSTYPE", ["SCIENCE"])),
    ImageSaver(output_dir_name="skyflatcal"),
    NightSkyMedianCalibrator(flat_mask_key=FITS_MASK_KEY),
    ImageSaver(output_dir_name="skysub"),
]

process = dark_cal + flat_cal
process_proc = [
    ImageDebatcher(),
    AstrometryNet(
        output_sub_dir=f"anet_{BOARD_ID}",
        scale_bounds=[25, 40],
        scale_units="amw",
        use_sextractor=True,
        parity="neg",
        search_radius_deg=1.0,
        sextractor_config_path=sextractor_autoastrometry_config["config_path"],
        use_weight=True,
    ),
    ImageSaver(output_dir_name=f"anet_{BOARD_ID}"),
    Sextractor(
        **sextractor_autoastrometry_config,
        write_regions_bool=True,
        output_sub_dir="scamp",
    ),
    Scamp(
        temp_output_sub_dir="scamp",
        ref_catalog_generator=winter_astrometric_catalog_generator,
        scamp_config_path=scamp_config_path,
        cache=False,
    ),
    ImageDebatcher(),
    Swarp(
        swarp_config_path=swarp_config_path,
        calculate_dims_in_swarp=True,
        include_scamp=True,
        subtract_bkg=False,
        cache=True,
        center_type="ALL",
        temp_output_sub_dir=f"stack_all_{TARGET_NAME}",
    ),
]

process_proc_all_boards = [
    ImageDebatcher(),
    ImageBatcher(["UTCTIME", "BOARD_ID", "SUBCOORD"]),
    ImageSelector(("FIELDID", "2789")),
    ImageSaver(output_dir_name="pre_anet"),
    AstrometryNet(
        output_sub_dir="anet",
        scale_bounds=[10, 20],
        scale_units="amw",
        use_sextractor=True,
        parity="neg",
        search_radius_deg=1.0,
        sextractor_config_path=sextractor_anet_config["config_path"],
        use_weight=True,
    ),
    ImageSaver(output_dir_name="post_anet"),
    Sextractor(
        **sextractor_autoastrometry_config,
        write_regions_bool=True,
        output_sub_dir="scamp",
    ),
    ImageDebatcher(),
    ImageBatcher(["BOARD_ID", "FILTER", "TARGNAME", "SUBCOORD"]),
    Scamp(
        temp_output_sub_dir="scamp",
        ref_catalog_generator=winter_astrometric_catalog_generator,
        scamp_config_path=scamp_config_path,
        cache=False,
    ),
    Swarp(
        swarp_config_path=swarp_config_path,
        calculate_dims_in_swarp=True,
        include_scamp=True,
        subtract_bkg=False,
        cache=False,
        center_type="ALL",
        temp_output_sub_dir="stack_all",
    ),
    ImageSaver(output_dir_name="stack"),
]

process_noise = [
    Sextractor(
        **sextractor_autoastrometry_config,
        write_regions_bool=True,
        output_sub_dir="mask_sextractor",
        checkimage_type="SEGMENTATION",
        cache=True,
        verbose_type="FULL",
    ),
    MaskPixelsFromPath(
        mask_path_key=sextractor_checkimg_map["SEGMENTATION"],
        write_masked_pixels_to_file=True,
        output_dir="mask1",
    ),
    ImageSaver(output_dir_name=f"noisemask_{BOARD_ID}"),
]
# process_proc = [ImageDebatcher(),
#                 ImageSelector(("OBSTYPE", ["SCIENCE"])),
#                 Sextractor(**sextractor_autoastrometry_config,
#                            write_regions_bool=True,
#                            output_sub_dir="sextractor",
#                            cache=False),
#                 AutoAstrometry(catalog="tmc", pixel_scale=1.07,
#                                write_crosscheck_files=True,
#                                inv=False,
#                                ), ]

stack_proc = [
    ImageBatcher(["TARGNAME", "FILTER"]),
    Swarp(
        swarp_config_path=swarp_config_path,
        calculate_dims_in_swarp=True,
        include_scamp=False,
        subtract_bkg=True,
        cache=True,
        center_type="MANUAL",
    ),
    ImageSaver(output_dir_name=f"stack_{TARGET_NAME}"),
]

photcal = [
    # ImageSelector(("BOARD_ID", board_id)),
    ImageDebatcher(),
    ImageBatcher(["BOARD_ID", "FILTER", "TARGNAME", "SUBCOORD"]),
    Sextractor(
        **sextractor_photometry_config,
        output_sub_dir="phot",
        checkimage_type="BACKGROUND_RMS",
    ),
    PhotCalibrator(
        ref_catalog_generator=winter_photometric_catalog_generator,
        temp_output_sub_dir="phot",
        write_regions=True,
        cache=True,
    ),
    AstrometryStatsWriter(
        ref_catalog_generator=winter_photometric_catalog_generator,
        write_regions=True,
        cache=True,
    ),
    # ImageSaver(output_dir_name=f"phot_{board_id}_{target_name}")
    ImageSaver(output_dir_name="photcal"),
]

photcal_indiv = [
    ImageSelector(("BOARD_ID", BOARD_ID)),
    ImageDebatcher(),
    ImageBatcher(["UTCTIME"]),
    Sextractor(
        **sextractor_photometry_config,
        output_sub_dir=f"phot_{BOARD_ID}_{TARGET_NAME}",
        checkimage_type="BACKGROUND_RMS",
    ),
    PhotCalibrator(
        ref_catalog_generator=winter_photometric_catalog_generator,
        temp_output_sub_dir=f"phot_{BOARD_ID}_{TARGET_NAME}",
        write_regions=True,
        cache=True,
    ),
    ImageSaver(output_dir_name=f"phot_{BOARD_ID}_{TARGET_NAME}"),
]

stack_multiboard = [
    Swarp(
        swarp_config_path=swarp_config_path,
        calculate_dims_in_swarp=True,
        include_scamp=False,
        subtract_bkg=False,
        cache=True,
        temp_output_sub_dir=f"multiboard_stack_{TARGET_NAME}",
        center_type="MANUAL",
    )
]
# commissioning = \
#     log + process_proc

select_subset = [
    ImageSelector(
        ("EXPTIME", 120.0), ("FILTER", ["dark", "J"]), ("BOARD_ID", BOARD_ID)
    ),
    ImageSaver(output_dir_name="raw_subset"),
]

commissioning = log + process

commissioning_dark = log + dark_cal
commissioning_proc = load_proc + process_proc
commissioning_flat = load_dark + flat_cal
commissioning_reduce = log + dark_cal + flat_cal
commissioning_stack = load_stack + stack_proc
commissioning_multiboard_stack = load_multiboard_stack + stack_multiboard
commissioning_noise = load_anet + process_noise
commissioning_photcal = load_multiboard_stack + photcal
commissioning_photcal_indiv = load_anet + photcal_indiv

extract_subset = [
    MultiExtParser(
        input_sub_dir="raw/",
        extension_num_header_key="BOARD_ID",
        output_sub_dir=f"raw_board_{BOARD_ID}",
        only_extract_num=BOARD_ID,
    ),
    ImageLoader(
        input_sub_dir=f"raw_board_{BOARD_ID}", load_image=load_raw_winter_image
    ),
    ImageSelector(("OBSTYPE", ["DARK", "SCIENCE"])),
    ImageSelector(
        ("EXPTIME", 120.0), ("FILTER", ["dark", "J"]), ("BOARD_ID", BOARD_ID)
    ),
]

extract_all = [
    MultiExtParser(
        input_sub_dir="raw/",
        extension_num_header_key="BOARD_ID",
        output_sub_dir="raw_split",
    ),
    ImageLoader(input_sub_dir="raw_split", load_image=load_raw_winter_image),
]

split_indiv = [
    SplitImage(n_x=1, n_y=2),
    ImageDebatcher(),
]

select_split_subset = [ImageSelector(("SUBCOORD", "0_0"))]

make_log_and_save = [
    CSVLog(
        export_keys=[
            "SUBCOORD",
            "FILTER",
            "UTCTIME",
            "EXPTIME",
            "OBSTYPE",
            "UNIQTYPE",
            "BOARD_ID",
            "OBSCLASS",
            "TARGET",
            "FILTER",
            "BASENAME",
            "TARGNAME",
            "RADEG",
            "DECDEG",
            "MEDCOUNT",
            "STDDEV",
            "T_ROIC",
        ]
    ),
    ImageSaver(output_dir_name="raw_unpacked", write_mask=False),
]

unpack_subset = extract_subset + split_indiv + select_split_subset + make_log_and_save
unpack_all = extract_all + split_indiv + make_log_and_save

load_unpacked = [
    ImageLoader(input_sub_dir="raw_unpacked", load_image=open_fits),
]

full_commissioning = load_unpacked + process + process_proc  # + stack_proc
full_commissioning_all_boards = (
    load_unpacked + dark_cal_all_boards + flat_cal_all_boards + process_proc_all_boards
)
# commissioning_split = load_all_boards + split_images + process + \
# process_proc_all_boards + photcal
commissioning_split = (
    load_unpacked
    + split_images
    + dark_cal_all_boards
    + flat_cal_all_boards
    + process_proc_all_boards
    + photcal
)
