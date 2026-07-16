"""
app-maxwell-filter: Apply Maxwell filtering (SSS/tSSS) to MEG data

This app applies Maxwell filtering (spherical signal separation, SSS or tSSS) to raw MEG data
using MNE-Python's maxwell_filter function. Maxwell filtering suppresses external noise and
artifacts, and can optionally perform head movement compensation.

Inputs
------
fif : str
    Path to input MEG file in .fif format.
calibration : str, optional
    Path to fine calibration (.dat) file (machine/site-specific).
crosstalk : str, optional
    Path to cross-talk correction (.fif) file.
headshape : str, optional
    Path to head position (.pos) file for movement compensation.
destination : str, optional
    Path to destination transformation (.fif) file.
channels : str, optional
    Path to BIDS-compliant channels (.tsv) file.
origin : str or list
    Origin of multipolar moment space in meters ('auto' or 3-element array).
int_order : int
    Order of internal component of spherical expansion (default 8).
ext_order : int
    Order of external component of spherical expansion (default 3).
st_duration : float or None
    Buffer duration in seconds for tSSS (None to skip tSSS).
st_correlation : float
    Inner/outer subspace correlation limit for tSSS (default 0.98).
coord_frame : str
    Coordinate frame for origin ('head' or 'meg').
regularize : str or None
    Basis regularization type ('in' or None).
ignore_ref : bool
    If True, ignore reference channels in compensation.
bad_condition : str
    How to handle ill-conditioned SSS matrices ('error', 'warning', 'info', or 'ignore').
st_fixed : bool
    If True, use median head position for tSSS window.
st_only : bool
    If True, only perform tSSS (temporal) projection.
mag_scale : float or str
    Magnetometer scale factor (default 100.0 or 'auto').
skip_by_annotation : str or list
    Annotation labels to skip during filtering.
extended_proj : list
    Empty-room projection vectors for eSSS.
destination_coords : str or list, optional
    Destination head position as 3-element array (alternative to destination file).

Outputs
-------
out_dir/raw.fif : str
    Maxwell-filtered MEG data.
out_dir/channels.tsv : str
    Updated channels file with interpolated bad channels marked good (if channels file provided).
out_report/report.html : str
    HTML report with before/after comparisons and parameter summary.
product.json : str
    Metadata for Brainlife.io interface.
"""

# Copyright (c) 2026 brainlife.io
#
# Apply Maxwell filtering (SSS/tSSS) to MEG data
#
# Authors:
# - Aurore Bussalb (https://github.com/AuroreBussalb)
# - Maximilien Chaumon (https://github.com/dnacombo)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'brainlife_utils'))

import mne
import numpy as np
import pandas as pd

from brainlife_utils import (
    load_config,
    setup_matplotlib_backend,
    ensure_output_dirs,
    read_optional_files,
    update_data_info_bads,
    message_optional_files_in_reports,
    create_product_json,
    add_info_to_product,
    require_config_keys,
)

# Setup environment
setup_matplotlib_backend()

# Load configuration
config = load_config()
require_config_keys(config, ['fif'])

# Create output directories
ensure_output_dirs('out_dir', 'out_report')

# Initialize product items for Brainlife.io
product_items = []

try:
    # Load input data
    data_file = config.pop('fif')
    raw = mne.io.read_raw_fif(data_file, allow_maxshield=True)

    # Normalise extended_proj empty string representation
    if config.get('extended_proj') == '[]':
        config['extended_proj'] = []

    # Read optional files (crosstalk, calibration, headshape, channels, destination)
    config, files_dict = read_optional_files(config, 'out_dir')
    cross_talk_file = files_dict['cross_talk_file']
    calibration_file = files_dict['calibration_file']
    head_pos_file = files_dict['head_pos_file']
    channels_file = files_dict['channels_file']
    destination = files_dict['destination']

    # Raise an error if both a destination file and destination_coords are provided
    if config.get('destination_coords') is not None and destination is not None:
        raise ValueError(
            "You can't provide both a destination file and destination_coords. "
            "One of them must be None."
        )

    # Handle channels file (must be BIDS compliant with 'status' column)
    if channels_file is not None:
        add_info_to_product(
            product_items,
            "Channels file provided - ensure it is BIDS compliant with 'status' column.",
            msg_type='warning',
        )
        raw, warning_msg = update_data_info_bads(raw, channels_file)
        if warning_msg is not None:
            add_info_to_product(product_items, warning_msg, msg_type='warning')

    # -- Convert parameters --

    # origin: convert string/list to numpy array when not 'auto'
    origin = config.get('origin', 'auto')
    if isinstance(origin, list):
        origin = np.array(origin)
    elif isinstance(origin, str) and origin != 'auto':
        origin = np.array(list(map(float, origin.split(', '))))
    if not isinstance(origin, str) and np.asarray(origin).shape[0] != 3:
        raise ValueError("Origin must contain three elements.")
    config['origin'] = origin

    # destination_coords: convert string/list to numpy array when provided
    report_destination_coords = None
    destination_coords = config.pop('destination_coords', None)
    if destination_coords is not None:
        report_destination_coords = destination_coords
        if isinstance(destination_coords, list):
            destination = np.array(destination_coords)
        elif isinstance(destination_coords, str):
            destination = np.array(list(map(float, destination_coords.split(', '))))
        else:
            destination = destination_coords
        if isinstance(destination, np.ndarray) and destination.shape[0] != 3:
            raise ValueError("destination_coords must contain three elements.")

    # mag_scale: convert to float when not 'auto'
    mag_scale = config.get('mag_scale', 100.0)
    if isinstance(mag_scale, str) and mag_scale != 'auto':
        config['mag_scale'] = float(mag_scale)

    # skip_by_annotation: normalise string representation to list
    skip_by_an = config.get('skip_by_annotation', [])
    if skip_by_an == '[]':
        skip_by_an = []
    elif isinstance(skip_by_an, str) and '[' in skip_by_an:
        skip_by_an = list(map(str, skip_by_an.replace('[', '').replace(']', '').split(', ')))
    config['skip_by_annotation'] = skip_by_an

    # Warn if no bad channels are marked
    if not raw.info['bads']:
        add_info_to_product(
            product_items,
            "No channels are marked as bad. Make sure to check for bad channels before "
            "applying Maxwell Filtering.",
            msg_type='warning',
        )

    # Keep bad channels before Maxwell filter interpolates them
    bad_channels = raw.info['bads'].copy()

    # Check that Maxwell filtering has not already been applied
    if raw.info['proc_history']:
        sss_info = raw.info['proc_history'][0]['max_info']['sss_info']
        tsss_info = raw.info['proc_history'][0]['max_info']['max_st']
        if bool(sss_info) or bool(tsss_info):
            raise ValueError(
                "You cannot apply Maxwell filtering if data have been already "
                "processed with Maxwell filtering."
            )

    # Apply Maxwell filter
    raw_maxwell = mne.preprocessing.maxwell_filter(
        raw,
        calibration=calibration_file,
        cross_talk=cross_talk_file,
        head_pos=head_pos_file,
        destination=destination,
        st_duration=config.get('st_duration'),
        st_correlation=config.get('st_correlation', 0.98),
        origin=config.get('origin', 'auto'),
        int_order=config.get('int_order', 8),
        ext_order=config.get('ext_order', 3),
        coord_frame=config.get('coord_frame', 'head'),
        regularize=config.get('regularize', 'in'),
        ignore_ref=config.get('ignore_ref', False),
        bad_condition=config.get('bad_condition', 'error'),
        st_fixed=config.get('st_fixed', True),
        st_only=config.get('st_only', False),
        skip_by_annotation=config.get('skip_by_annotation', ['edge', 'bad_acq_skip']),
        mag_scale=config.get('mag_scale', 100.0),
        extended_proj=config.get('extended_proj', []),
    )

    # Save filtered data
    raw_maxwell.save('out_dir/raw.fif', overwrite=True)
    add_info_to_product(product_items, "Maxwell Filter was applied successfully.", msg_type='success')

    # Update channels.tsv if provided (bad channels were interpolated → mark as good)
    if channels_file is not None:
        df_channels = pd.read_csv(channels_file, sep='\t')
        for bad in bad_channels:
            idx = df_channels[df_channels['name'] == bad].index
            df_channels.loc[idx, 'status'] = 'good'
        df_channels.to_csv('out_dir/channels.tsv', sep='\t', index=False)

    # -- Generate HTML report --
    report_files = message_optional_files_in_reports(files_dict)
    report = mne.Report(title='Results Maxwell Filter', verbose=True)

    # Data info section
    html_info = f"""
    <table style="border-collapse: collapse;">
        <tr><td style="border: 1px dashed black; padding: 8px;">Input file: {data_file}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Bad channels: {bad_channels}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Sampling frequency: {raw.info['sfreq']} Hz</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Highpass: {raw.info['highpass']} Hz</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Lowpass: {raw.info['lowpass']} Hz</td></tr>
    </table>
    """
    report.add_html(html_info, title='MEG Recording Features')

    # Before/after plots
    try:
        fig_before = raw.copy().pick(['meg'], exclude='bads').plot(
            duration=10, scalings='auto', butterfly=False,
            show_scrollbars=False, proj=False, show=False,
        )
        fig_after = raw_maxwell.copy().pick(['meg'], exclude='bads').plot(
            duration=10, scalings='auto', butterfly=False,
            show_scrollbars=False, proj=False, show=False,
        )
        fig_psd_before = raw.compute_psd().plot(show=False)
        fig_psd_after = raw_maxwell.compute_psd().plot(show=False)

        report.add_figure(fig_before, title='MEG Signals Before Maxwell Filter', section='Temporal Domain')
        report.add_figure(fig_after, title='MEG Signals After Maxwell Filter', section='Temporal Domain')
        report.add_figure(fig_psd_before, title='PSD Before Maxwell Filter', section='Frequency Domain')
        report.add_figure(fig_psd_after, title='PSD After Maxwell Filter', section='Frequency Domain')
    except Exception as e:
        print(f"Warning: Could not generate plots: {e}")

    # Parameters section
    html_params = f"""
    <table style="border-collapse: collapse;">
        <tr><td style="border: 1px dashed black; padding: 8px;">Cross-talk file: {report_files.get('report_cross_talk_file', 'N/A')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Calibration file: {report_files.get('report_calibration_file', 'N/A')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Headshape file: {report_files.get('report_head_pos_file', 'N/A')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Destination file: {report_files.get('report_destination', 'N/A')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Destination coords (if no file): {report_destination_coords}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Origin: {config.get('origin')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Internal order: {config.get('int_order')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">External order: {config.get('ext_order')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Buffer duration (tSSS): {config.get('st_duration')} s</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Correlation limit: {config.get('st_correlation')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Coordinate frame: {config.get('coord_frame')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Regularize: {config.get('regularize')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Ignore reference: {config.get('ignore_ref')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Bad condition: {config.get('bad_condition')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">tSSS median head position: {config.get('st_fixed')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">tSSS only: {config.get('st_only')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Magnetometer scale: {config.get('mag_scale')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Skip by annotation: {config.get('skip_by_annotation')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">Extended projection: {config.get('extended_proj')}</td></tr>
        <tr><td style="border: 1px dashed black; padding: 8px;">MNE version: {mne.__version__}</td></tr>
    </table>
    """
    report.add_html(html_params, title='Parameters')

    report.save('out_report/report.html', overwrite=True)

except Exception as e:
    add_info_to_product(product_items, str(e), msg_type='error')
    raise

finally:
    create_product_json(product_items)
