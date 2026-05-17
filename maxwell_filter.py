#!/usr/local/bin/python3

import json
import mne
import warnings
import numpy as np
import os
import pandas as pd
from brainlife_apps_helper import helper


def apply_maxwell_filter(raw, calibration_file, cross_talk_file, head_pos_file, destination, param_st_duration,
                         param_st_correlation, param_origin, param_int_order, param_ext_order, param_coord_frame, param_regularize,
                         param_ignore_ref, param_bad_condition, param_st_fixed, param_st_only, param_skip_by_annotation,
                         param_mag_scale, param_extended_proj):
    """Perform Maxwell filtering using MNE Python and save the file once filtered.

    Parameters
    ----------
    raw: instance of mne.io.Raw
        Data to be filtered.
    calibration_file: str or None
        Path to the '.dat' file with fine calibration coefficients. This file is machine/site-specific.
    cross_talk_file: str or None
        Path to the FIF file with cross-talk correction information.
    head_pos_file: str or None
        Path to the '.pos' file containing the info to perform movement compensation.
    destination: str, array_like, shape (3,), or None
        The destination location for the head. Can be None, which will not change the head position, a string path
        to a FIF file containing a MEG device<->head transformation or a 3-element array giving the coordinates to 
        translate to (with no rotations).
    param_st_duration: float or None
        If not None, apply spatiotemporal SSS with specified buffer duration (in seconds).
    param_st_correlation: float
        Correlation limit between inner and outer subspaces used to reject ovwrlapping intersecting inner/outer signals
        during spatiotemporal SSS.
    param_origin: str str or array_like, shape (3,)
        Origin of internal and external multipolar moment space in meters. The default is 'auto', which means 
        (0., 0., 0.)when coord_frame='meg', and a head-digitization-based origin fit using fit_sphere_to_headshape()
        when coord_frame='head'.
    param_int_order: int
        Order of internal component of spherical expansion.
    param_ext_order: int
        Order of external component of spherical expansion.
    param_coord_frame: str
        The coordinate frame that the origin is specified in, either 'meg' or 'head' (default).
    param_regularize: str or None
        Basis regularization type, must be “in” (default) or None.
    param_ignore_ref: bool
        If True, do not include reference channels in compensation.
    param_bad_condition: str
        How to deal with ill-conditioned SSS matrices. Can be “error” (default), “warning”, “info”, or “ignore”.
    param_st_fixed: bool
        If True (default), do spatiotemporal SSS using the median head position during the param_st_duration window.
    param_st_only: bool
        If True, only tSSS (temporal) projection of MEG data will be performed on the output data.
    param_skip_by_annotation: str or list of str
        If a string (or list of str), any annotation segment that begins with the given string will not be included in
        filtering, and segments on either side of the given excluded annotated segment will be filtered separately.
    param_mag_scale: float or str
        The magenetometer scale-factor used to bring the magnetometers to approximately the same order of magnitude as
        the gradiometers (default 100.), as they have different units (T vs T/m). Can be "auto".
    param_extended_proj: list
        The empty-room projection vectors used to extend the external SSS basis (i.e., use eSSS). Default is an empty list. 

    Returns
    -------
    raw_maxwell_filter: instance of mne.io.Raw
        The raw data with Maxwell filtering applied.
    """

    # Check if Maxwell Filter was already applied on the data
    if raw.info['proc_history']:
        sss_info = raw.info['proc_history'][0]['max_info']['sss_info']
        tsss_info = raw.info['proc_history'][0]['max_info']['max_st']
        if bool(sss_info) or bool(tsss_info) is True:
            value_error_message = f'You cannot apply Maxwell filtering if data have been already ' \
                                  f'processed with Maxwell filtering.'
            # Raise exception
            raise ValueError(value_error_message)

    # Apply Maxwell Filter
    raw_maxwell_filter = mne.preprocessing.maxwell_filter(raw, calibration=calibration_file, cross_talk=cross_talk_file,
                                                          head_pos=head_pos_file, destination=destination,
                                                          st_duration=param_st_duration, st_correlation=param_st_correlation,
                                                          origin=param_origin, int_order=param_int_order, 
                                                          ext_order=param_ext_order, coord_frame=param_coord_frame, 
                                                          regularize=param_regularize, ignore_ref=param_ignore_ref, 
                                                          bad_condition=param_bad_condition, st_fixed=param_st_fixed, 
                                                          st_only=param_st_only, skip_by_annotation=param_skip_by_annotation,
                                                          mag_scale=param_mag_scale, extended_proj=param_extended_proj)

    # Save file
    raw_maxwell_filter.save("out_dir_maxwell_filter/meg.fif", overwrite=True)

    return raw_maxwell_filter


def _compute_snr(meg_file, meg_channels_type):
    # Compute the SNR

    # Select only MEG channels and exclude the bad channels
    meg_file = meg_file.pick_types(meg=True, exclude='bads')

    # Compute SNR on gradiometers or magnetometers
    meg_file = meg_file.pick(picks=meg_channels_type)

    # Create fixed length events
    array_events = mne.make_fixed_length_events(meg_file, duration=10)

    # Create epochs
    epochs = mne.Epochs(meg_file, array_events)

    # Compute mean signal amplitude on each epoch
    epochs_data = epochs.get_data()
    mean_signal_amplitude_per_epoch = epochs_data.mean(axis=(1, 2))  # mean on channels and times

    # Compute mean across all epochs and its std error
    mean_final = mean_signal_amplitude_per_epoch.mean()
    std_error_final = np.std(mean_signal_amplitude_per_epoch, ddof=1) / np.sqrt(
        np.size(mean_signal_amplitude_per_epoch))

    # Compute SNR
    snr = mean_final / std_error_final

    return snr


def _generate_report(data_file_before, raw_before_preprocessing, raw_after_preprocessing, bad_channels,
                     report_cross_talk_file, report_calibration_file, 
                     report_head_pos_file, report_destination_file, 
                     report_param_destination,
                     param_st_duration, param_st_correlation, param_origin,
                     param_int_order, param_ext_order, param_coord_frame, 
                     param_regularize, param_ignore_ref, param_bad_condition, param_st_fixed,
                     param_st_only, param_skip_by_annotation, param_mag_scale, param_extended_proj):
    # Generate a report

    # Create instance of mne.Report
    report = mne.Report(title='Results Maxwell filter', verbose=True)

    ## Give some info about the file before preprocessing ##
    sampling_frequency = raw_before_preprocessing.info['sfreq']
    highpass = raw_before_preprocessing.info['highpass']
    lowpass = raw_before_preprocessing.info['lowpass']

    # Put this info in html format #
    # Info on data
    html_text_info = f"""<html>
    <head>
        <style type="text/css">
            table {{ border-collapse: collapse;}}
            td {{ text-align: center; border: 1px solid #000000; border-style: dashed; font-size: 15px; }}
        </style>
    </head>

    <body>
        <table width="50%" height="80%" border="2px">
            <tr>
                <td>Input file: {data_file_before}</td>
            </tr>
            <tr>
                <td>Bad channels: {bad_channels}</td>
            </tr>
            <tr>
                <td>Sampling frequency: {sampling_frequency}Hz</td>
            </tr>
            <tr>
                <td>Highpass: {highpass}Hz</td>
            </tr>
            <tr>
                <td>Lowpass: {lowpass}Hz</td>
            </tr>
        </table>
    </body>

    </html>"""

    # Add html to reports
    report.add_htmls_to_section(html_text_info, captions='MEG recording features', section='Data info', replace=False)

    # Plot MEG signals in temporal domain
    fig_raw = raw_before_preprocessing.pick(['meg'], exclude='bads').plot(duration=10, scalings='auto', butterfly=False,
                                                                          show_scrollbars=False, proj=False, show=False)
    fig_raw_maxfilter = raw_after_preprocessing.pick(['meg'], exclude='bads').plot(duration=10, scalings='auto',
                                                                                   butterfly=False,
                                                                                   show_scrollbars=False, proj=False,show=False)
    # Plot power spectral density
    fig_raw_psd = raw_before_preprocessing.plot_psd(show=False)
    fig_raw_maxfilter_psd = raw_after_preprocessing.plot_psd(show=False)

    # Add figures to report
    report.add_figs_to_section(fig_raw, captions='MEG signals before Maxwell Filter', section='Temporal domain')
    report.add_figs_to_section(fig_raw_maxfilter, captions='MEG signals after Maxwell Filter', section='Temporal domain')
    report.add_figs_to_section(fig_raw_psd, captions='Power spectral density before Maxwell Filter',
                               section='Frequency domain')
    report.add_figs_to_section(fig_raw_maxfilter_psd, captions='Power spectral density after Maxwell Filter',
                               section='Frequency domain')


    # Info on SNR
    # html_text_snr = f"""<html>
    # <head>
    #     <style type="text/css">
    #         table {{ border-collapse: collapse;}}
    #         td {{ text-align: center; border: 1px solid #000000; border-style: dashed; font-size: 15px; }}
    #     </style>
    # </head>

    # <body>
    #     <table width="50%" height="80%" border="2px">
    #         <tr>
    #             <td>SNR before MaxFilter: {snr_before}</td>
    #         </tr>
    #         <tr>
    #             <td>SNR after MaxFilter: {snr_after}</td>
    #         </tr>
    #     </table>
    # </body>

    # </html>"""


    # report.add_htmls_to_section(html_text_snr, captions='Signal to noise ratio', section='Signal to noise ratio',
    #                             replace=False)


    ## Values of the parameters of the App ## 
    mne_version = mne.__version__

    # Put this info in html format # 
    html_text_parameters = f"""<html>

    <head>
        <style type="text/css">
            table {{ border-collapse: collapse;}}
            td {{ text-align: center; border: 1px solid #000000; border-style: dashed; font-size: 15px; }}
        </style>
    </head>

    <body>
        <table width="50%" height="80%" border="2px">
            <tr>
                <td>Cross-talk file: {report_cross_talk_file}</td>
            </tr>
            <tr>
                <td>Calibration file: {report_calibration_file}</td>
            </tr>
            <tr>
                <td>Headshape file: {report_head_pos_file}</td>
            </tr>
            <tr>
                <td>Destination file: {report_destination_file}</td>
            </tr>
            <tr>
                <td>Destination (if no destination file provided): {report_param_destination}</td>
            </tr>
            <tr>
                <td>Origin: {param_origin}</td>
            </tr>
            <tr>
                <td>Order of internal component of sherical expansion: {param_int_order}</td>
            </tr>
            <tr>
                <td>Order of external component of sherical expansion: {param_ext_order}</td>
            </tr>
            <tr>
                <td>Buffer duration: {param_st_duration}(in seconds)</td>
            </tr>
            <tr>
                <td>Correlation limit between inner and outer subspaces: {param_st_correlation}</td>
            </tr>
            <tr>
                <td>Coordinate frame: {param_coord_frame}</td>
            </tr>
            <tr>
                <td>Regularize: {param_regularize}</td>
            </tr>
            <tr>
                <td>Ignore reference channel: {param_ignore_ref}</td>
            </tr>
            <tr>
                <td>Bad condition: {param_bad_condition}</td>
            </tr>
            <tr>
                <td>Apply tSSS using the median head position: {param_st_fixed}</td>
            </tr>
            <tr>
                <td>Only tSSS projection of MEG data: {param_st_only}</td>
            </tr>
            <tr>
                <td>Magnetomer scale-factor: {param_mag_scale}</td>
            </tr>
            <tr>
                <td>Skip by annotation: {param_skip_by_annotation}</td>
            </tr>
            <tr>
                <td>Empty-room projection vectors: {param_extended_proj}</td>
            </tr>
            <tr>
                <td>MNE version used: {mne_version}</td>
            </tr>
        </table>
    </body>

    </html>"""

    # Add html to reports
    report.add_htmls_to_section(html_text_parameters, captions='Values of the parameters of the App', 
                                section='Parameters of the App', replace=False)

    # Save report
    report.save('out_dir_report/report_maxwell_filter.html', overwrite=True)


def main():

    # Generate a json.product to display messages on Brainlife UI
    dict_json_product = {'brainlife': []}

    # Load inputs from config.json
    with open('config.json') as config_json:
        config = json.load(config_json)

    # Read the files
    data_file = config.pop('fif')
    raw = mne.io.read_raw_fif(data_file, allow_maxshield=True)

    # Convert empty strings values to None
    config = helper.convert_parameters_to_None(config)

    # Check if param_extended_proj parameter is empty
    if config['param_extended_proj'] == '[]':
        config['param_extended_proj'] = [] 

    # Read and save optional files
    config, cross_talk_file, calibration_file, events_file, head_pos_file, channels_file, destination = helper.read_optional_files(config, 'out_dir_maxwell_filter')

    # Fall back to repo-bundled calibration files if not provided via Brainlife input
    if calibration_file is None and os.path.exists('calibration_meg.dat'):
        calibration_file = 'calibration_meg.dat'
    if cross_talk_file is None and os.path.exists('crosstalk_meg.fif'):
        cross_talk_file = 'crosstalk_meg.fif'

    # Raise a value error if the user provides both the destination file and the destination parameter
    if config['param_destination'] is not None and destination is not None:
        value_error_message = f"You can't provide both a destination file and a " \
                              f"destination parameter. One of them must be None."
        raise ValueError(value_error_message)

    # Channels.tsv must be BIDS compliant
    if channels_file is not None:
        user_warning_message_channels = f'The channels file provided must be ' \
                                        f'BIDS compliant and the column "status" must be present. ' 
        warnings.warn(user_warning_message_channels)
        dict_json_product['brainlife'].append({'type': 'warning', 'msg': user_warning_message_channels})
        # Update raw.info['bads'] with info contained in channels.tsv
        raw, user_warning_message_channels = helper.update_data_info_bads(raw, channels_file)
        if user_warning_message_channels is not None: 
            warnings.warn(user_warning_message_channels)
            dict_json_product['brainlife'].append({'type': 'warning', 'msg': user_warning_message_channels})


    ## Convert parameters ##      

    # Deal with param_origin parameter #
    # Convert origin parameter into array when the app is run locally
    if isinstance(config['param_origin'], list):
       config['param_origin'] = np.array(config['param_origin'])

    # Convert origin parameter into array when the app is run on BL
    if isinstance(config['param_origin'], str) and config['param_origin'] != "auto":
       param_origin = list(map(float, config['param_origin'].split(', ')))
       config['param_origin'] = np.array(param_origin)

    # Raise an error if param origin is not an array of shape 3
    if config['param_origin'] != "auto" and config['param_origin'].shape[0] != 3:
        value_error_message = f"Origin parameter must contain three elements."
        raise ValueError(value_error_message)

    # Deal with param_destination parameter #
    if config['param_destination'] is not None: 
        destination = config['param_destination']
        report_param_destination = destination

        # Convert destination parameter into array when the app is run locally
        if isinstance(destination, list):
           destination = np.array(destination)

        # Convert destination parameter into array when the app is run on BL
        if isinstance(destination, str):
            report_param_destination = destination
            destination = list(map(float, destination.split(', ')))
            destination = np.array(destination)

        # Raise an error if param destination is not an array of shape 3
        if isinstance(destination, np.ndarray) and destination.shape[0] != 3:
            value_error_message = f"Destination parameter must contain three elements."
            raise ValueError(value_error_message)
    else:
        report_param_destination = None

    # Deal with param_mag_scale parameter #
    # Convert param_mag_scale parameter into float when the app is run on BL
    if isinstance(config['param_mag_scale'], str) and config['param_mag_scale'] != "auto":
        config['param_mag_scale'] = float(config['param_mag_scale'])

    # Deal with skip_by_annotation parameter #
    # Convert param_mag_scale into a list of strings when the app runs on BL
    skip_by_an = config['param_skip_by_annotation']
    if skip_by_an == "[]":
        skip_by_an = []
    elif isinstance(skip_by_an, str) and skip_by_an.find("[") != -1 and skip_by_an != "[]": 
        skip_by_an = skip_by_an.replace('[', '')
        skip_by_an = skip_by_an.replace(']', '')
        skip_by_an = list(map(str, skip_by_an.split(', ')))         
    config['param_skip_by_annotation'] = skip_by_an 

    
    # Display a warning if bad channels are empty
    if not raw.info['bads']:
        user_warning_message = f'No channels are marked as bad. ' \
                               f'Make sure to check (automatically or visually) for bad channels before ' \
                               f'applying Maxwell Filtering.'
        warnings.warn(user_warning_message)
        dict_json_product['brainlife'].append({'type': 'warning', 'msg': user_warning_message})

    
    ## Define kwargs ##

    # Delete keys values in config.json when this app is executed on Brainlife
    config = helper.define_kwargs(config)

    # Delete the param_destination key    
    del config['param_destination'] 

    # Define kwargs   
    kwargs = config  


    # Keep bad channels in memory
    bad_channels = raw.info['bads'] 


    # Apply Maxwell Filter
    raw_maxwell_filter = apply_maxwell_filter(raw, calibration_file, cross_talk_file, 
                                              head_pos_file, destination,
                                              **kwargs)

    # Update channels.tsv if it exists because bad channels were interpolated
    if channels_file is not None:
        df_channels = pd.read_csv(channels_file, sep='\t')
        for bad in bad_channels:
            index_bad_channel = df_channels[df_channels['name'] == bad].index
            df_channels.loc[index_bad_channel, 'status'] = 'good'

        # Save channels.tsv
        df_channels.to_csv('out_dir_maxwell_filter/channels.tsv', sep = '\t', index=False)

    # Write a success message in product.json
    dict_json_product['brainlife'].append({'type': 'success', 'msg': 'Maxwell Filter was applied successfully.'})

    # Compute SNR on magnetometers
    # snr_before_mag = _compute_snr(raw, meg_channels_type='mag')
    # snr_after_mag = _compute_snr(raw_maxfilter, meg_channels_type='mag')

    # Compute SNR on gradiometers
    # snr_before_mag = _compute_snr(raw, meg_channels_type='grad')
    # snr_after_mag = _compute_snr(raw_maxfilter, meg_channels_type='grad')

    ## Generate html report ##

    # Get messages to add to the html report
    report_calibration_file, report_cross_talk_file, report_head_pos_file, report_destination_file = helper.message_optional_files_in_reports(calibration_file, cross_talk_file, head_pos_file, destination)
    
    # Generate report
    _generate_report(data_file, raw, raw_maxwell_filter, bad_channels, 
                     report_cross_talk_file, report_calibration_file, 
                     report_head_pos_file, report_destination_file, 
                     report_param_destination, **kwargs)

    # Save the dict_json_product in a json file
    with open('product.json', 'w') as outfile:
        json.dump(dict_json_product, outfile)


if __name__ == '__main__':
    main()
