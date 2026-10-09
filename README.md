# Apply Maxwell Filtering

[![Run on Brainlife.io](https://img.shields.io/badge/Brainlife-bl.app.476-blue.svg)](https://doi.org/10.25663/brainlife.app.476)

## Description

This app applies Maxwell filtering (SSS, or tSSS when a buffer duration is given) to continuous MEG
data recorded on an Elekta/MEGIN/Neuromag (or compatible) system, using
[`mne.preprocessing.maxwell_filter`](https://mne.tools/stable/generated/mne.preprocessing.maxwell_filter.html).
Maxwell filtering uses spatial signal-space separation to suppress environmental and system noise,
and can optionally perform temporal signal-space separation (tSSS) and head-movement compensation.
If a BIDS-compliant `channels.tsv` is provided, channels marked bad are applied to the data before
filtering, then interpolated by the Maxwell filter and reported as good in the output channels file.

The app generates:
- a Maxwell-filtered MEG `.fif` file,
- an updated `channels.tsv` file, with previously-bad channels marked good (only if a channels file
  was provided),
- an HTML report with before/after temporal and PSD plots and a summary of the parameters used.

## Inputs

- **`fif`** (`neuro/meg/fif`): continuous MEG recording to Maxwell-filter (required).
- **`crosstalk`** (`neuro/meg/fif`): optional cross-talk compensation file bundled with the MEG
  recording.
- **`calibration`** (`neuro/meg/fif`): optional fine calibration file bundled with the MEG
  recording.
- **`events`** (`neuro/meg/fif`): optional events file bundled with the MEG recording; read but not
  used by this app.
- **`headshape`** (`neuro/meg/fif`): optional head-digitization points bundled with the MEG
  recording (BIDS coregistration format). Not used for head-movement compensation by this app —
  see `headshape_override` below.
- **`channels`** (`neuro/meg/fif`): optional BIDS-compliant `channels.tsv`; must include a
  `status` column.
- **`destination`** (`neuro/meg/fif`): optional path to a destination transformation `.fif` file
  to translate the head position to; mutually exclusive with `destination_coords`.
- **`headshape_override`** (`neuro/meg/fif-override`): optional head-position `.pos` file (the
  output of app-head-pos), in the quaternion-array format read by `mne.chpi.read_head_pos()` and
  required by `maxwell_filter(head_pos=...)` for head-movement compensation.
- **`channels_override`** (`neuro/meg/fif-override`): optional BIDS `channels.tsv` (e.g. computed
  by app-bad-channels) that overrides the `channels` file above.
- **`destination_override`** (`neuro/meg/fif-override`): optional destination transformation
  `.fif` file (e.g. computed by app-mean-transformation-matrix) that overrides `destination` above.

## Outputs

- `out_dir/meg.fif` (`neuro/meg/fif`): Maxwell-filtered MEG data.
- `out_dir_channels/channels.tsv` (`neuro/meg/fif-override`): updated channels file with
  previously-bad channels marked good (only produced if a channels file was provided).
- `out_report/report.html` (`report/html`): HTML report with before/after PSD comparisons and a
  table of the parameters used.
- `product.json`: processing status and metadata for the Brainlife.io interface.

## Configuration Parameters

| key | type | default | description |
|---|---|---|---|
| `origin` | `string` or list of 3 `float` | `"auto"` | Origin of the internal and external multipolar moment space, in meters. |
| `int_order` | `int` | `8` | Order of the internal component of the spherical expansion. |
| `ext_order` | `int` | `3` | Order of the external component of the spherical expansion. |
| `st_duration` | `float` or `null` | `null` | Buffer duration (seconds) for tSSS; `null` skips tSSS. |
| `st_correlation` | `float` | `0.98` | Correlation limit between inner and outer subspaces used to reject overlapping intersecting signals during tSSS. |
| `coord_frame` | `string` | `"head"` | Coordinate frame that `origin` is specified in: `"meg"` or `"head"`. |
| `regularize` | `string` or `null` | `"in"` | Basis regularization: `"in"` or `null`. |
| `ignore_ref` | `bool` | `false` | If `true`, do not include reference channels in compensation. |
| `bad_condition` | `string` | `"error"` | How to handle ill-conditioned SSS matrices: `"error"`, `"warning"`, `"info"`, or `"ignore"`. |
| `st_fixed` | `bool` | `true` | If `true`, do tSSS using the median head position during the `st_duration` window. |
| `st_only` | `bool` | `false` | If `true`, only the tSSS (temporal) projection is performed on the output data. |
| `mag_scale` | `float` or `string` | `100.0` | Magnetometer scale factor to bring magnetometers to approximately the same order of magnitude as gradiometers. Can be `"auto"`. |
| `skip_by_annotation` | `string` or list of `string` | `["edge", "bad_acq_skip"]` | Annotation labels; segments starting with one of these are excluded from filtering and the data on either side is filtered separately. |
| `extended_proj` | `list` | `[]` | Empty-room projection vectors used to extend the external SSS basis (eSSS). |
| `destination_coords` | list of 3 `float` or `null` | `null` | Destination head position as a 3-element array, as an alternative to the `destination` file. Must be `null` if a `destination` file is provided. |

## Usage

### Running on Brainlife.io

1. Register on [brainlife.io](https://brainlife.io).
2. Go to the "Apps" tab, search for "Apply Maxwell filtering", and add it to a process in a
   project containing a `neuro/meg/fif` MEG recording (optionally with a `neuro/meg/fif-override`
   bundle for head position, channels, or destination overrides).
3. Set the configuration parameters, or leave the defaults, and submit the process.
4. Download the Maxwell-filtered MEG data, the updated channels file (if applicable), and the
   HTML report from the process outputs.

### Local Testing

```bash
git clone <this-repo-url>
cd maxwell-filter
# create config.json with paths to your input files and the parameter values you want
./main
```

## Technical Details

- The Docker image used by `main` is `brainlifemeeg/mne:1.12.1`.
- `headshape` (the primary MEG input's digitization points) and `headshape_override` (an
  app-head-pos output) are different formats: `headshape` is the BIDS coregistration point cloud,
  while `maxwell_filter(head_pos=...)` needs the quaternion head-position array read by
  `mne.chpi.read_head_pos()`. Only `headshape_override` is used for head-movement compensation.

## Authors
- Aurore Bussalb (https://github.com/AuroreBussalb)
- Maximilien Chaumon (https://github.com/dnacombo)

## Citations
1. Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2
2. Gramfort, A. et al. MEG and EEG data analysis with MNE-Python. Front. Neurosci. 7, 267 (2013). https://doi.org/10.3389/fnins.2013.00267
3. Taulu S. and Kajola M. Presentation of electromagnetic multichannel data: The signal space separation method. Journal of Applied Physics, 97 (2005). https://doi.org/10.1063/1.1935742
4. Taulu S. and Simola J. Spatiotemporal signal space separation method for rejecting nearby interference in MEG measurements. Physics in Medicine and Biology, 51 (2006). https://doi.org/10.1088/0031-9155/51/7/008

## Funding Acknowledgement

brainlife.io is publicly funded and for the sustainability of the project it is helpful to
acknowledge the use of the platform. We kindly ask that you acknowledge the funding below in your
code and publications.

[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-1636893](https://img.shields.io/badge/NSF_BCS-1636893-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-ACI-1916518](https://img.shields.io/badge/NSF_ACI-1916518-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1916518)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NIH-NIBIB-R01EB029272](https://img.shields.io/badge/NIH_NIBIB-R01EB029272-green.svg)](https://grantome.com/grant/NIH/R01-EB029272-01)
[![NIH-NIBIB-R01EB030896](https://img.shields.io/badge/NIH_NIBIB-R01EB030896-green.svg)](https://grantome.com/grant/NIH/R01-EB030896-01)

## License

Copyright (c) 2026 MEEG Brainlife team. Licensed under AGPL-3.0, see [license.txt](license.txt).
