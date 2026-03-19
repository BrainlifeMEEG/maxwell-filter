# app-maxwell-filter

This is the repository of a Brainlife App using [MNE Maxwell Filter](https://mne.tools/dev/generated/mne.preprocessing.maxwell_filter.html).

# Documentation

Apply SSS or tSSS MaxFilter on MEG data to reduce environmental noise.

#### Input files are:
  * a MEG file in `.fif` format,
  * an optional fine calibration file in `.dat`,
  * an optional crosstalk compensation file in `.fif`,
  * an optional head position file in `.pos`,
  * an optional destination file in `.fif`,
  * an optional events file in `.tsv`, 
  * an optional channels file in `.tsv`.
#### Input parameters are:
  * `param_destination`: list of three `float`, optional, list of 3 elements giving the coordinates to translate to (with no rotations). This parameter must be set to None when a destination file is provided. Default is None. 
  * `param_st_duration`: `float`, optional, if not `None`, apply tSSS with specified buffer duration (in seconds). Default is `None`.
  * `param_st_correlation`: `float`, correlation limit between inner and outer subspaces used to reject overlapping intersecting 
    inner/outer signals during tSSS. Default is 0.98.
  * `param_origin`: `str` or list of three `float`, origin of internal and external multipolar moment space in meters. Default is 'auto'.
  * `param_int_order`: `int`, order of internal component of spherical expansion. Default is 8.
  * `param_ext_order`: `int`, order of external component of spherical expansion. Default is 3.
  * `param_coord_frame`: `str`, the coordinate frame that the origin is specified in, either 'meg' or 'head'. Default is 'head'.
  * `param_regularize`: `str`, optional, the destination location for the head, either 'in' or `None`. Default is 'in'.
  * `param_ignore_ref`: `bool`, if `True`, do not include reference channels in compensation. Default is `False`.
  * `param_bad_condition`: `str`, how to deal with ill-conditioned SSS matrices, either 'error', 'warning', 'info', or 'ignore'. Default is 'error'.
  * `param_st_fixed`: `bool`, if `True`, do tSSS using the median head position during the st_duration window. Default is `True`.
  * `param_st_only`: `bool`, if `True`, only tSSS projection of MEG data will be performed on the output data. Default is `False`.
  * `param_mag_scale`: `float` or `str`, the magnetometer scale-factor used to bring the magnetometers to approximately the same order of magnitude as the gradiometers, as they have different units (T vs T/m). Can be "auto". Default is 100.
  * `param_skip_by_annotation`, `str` or `list of str`, any annotation segment that begins with the given string will not be included in filtering, and segments on either side of the given excluded annotated segment will be filtered separately.
    Default is `["edge", bad_acq_skip"]`.
  * `param_extended_proj`: `list`, the empty-room projection vectors used to extend the external SSS basis (i.e., use eSSS). Default is an empty list.
      
This list along with the default values correspond to the parameters of MNE Python version 0.22.0 MaxFilter function.

#### Ouput files are:
  * a `.fif` MEG file after Maxwell filtering,
  * an `.html` report containing figures.

### Authors
- [Aurore Bussalb](aurore.bussalb@icm-institute.org)

### Contributors
- [Aurore Bussalb](aurore.bussalb@icm-institute.org)
- [Maximilien Chaumon](maximilien.chaumon@icm-institute.org)

### Funding Acknowledgement
brainlife.io is publicly funded and for the sustainability of the project it is helpful to Acknowledge the use of the platform. We kindly ask that you acknowledge the funding below in your code and publications. Copy and past the following lines into your repository when using this code.

[![NSF-BCS-1734853](https://img.shields.io/badge/NSF_BCS-1734853-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1734853)
[![NSF-BCS-1636893](https://img.shields.io/badge/NSF_BCS-1636893-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1636893)
[![NSF-ACI-1916518](https://img.shields.io/badge/NSF_ACI-1916518-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1916518)
[![NSF-IIS-1912270](https://img.shields.io/badge/NSF_IIS-1912270-blue.svg)](https://nsf.gov/awardsearch/showAward?AWD_ID=1912270)
[![NIH-NIBIB-R01EB029272](https://img.shields.io/badge/NIH_NIBIB-R01EB029272-green.svg)](https://grantome.com/grant/NIH/R01-EB029272-01)

### Citations
1. Avesani, P., McPherson, B., Hayashi, S. et al. The open diffusion data derivatives, brain data upcycling via integrated publishing of derivatives and reproducible open cloud services. Sci Data 6, 69 (2019). [https://doi.org/10.1038/s41597-019-0073-y](https://doi.org/10.1038/s41597-019-0073-y)
2. Taulu S. and Kajola M. Presentation of electromagnetic multichannel data: The signal space separation method. Journal of Applied Physics, 97 (2005). [https://doi.org/10.1063/1.1935742](https://doi.org/10.1063/1.1935742)
3. Taulu S. and Simola J. Spatiotemporal signal space separation method for rejecting nearby interference in MEG measurements. Physics in Medicine and Biology, 51 (2006). [https://doi.org/10.1088/0031-9155/51/7/008](https://doi.org/10.1088/0031-9155/51/7/008)


## Running the App 

### On Brainlife.io

This App is still private.

### Running Locally (on your machine)

1. git clone this repo
2. Inside the cloned directory, create `config.json` with the same keys as in `config.json.example` but with paths to your input 
   files and values of the input parameters. For instance:

```json
{
  "fif": "rest1-raw.fif"
}
```

3. Launch the App by executing `main`

```bash
./main
```

## Output

The output files are a MEG file in `.fif` format and an `.html` report.

## Citation

Hayashi, S., Caron, B.A., Heinsfeld, A.S. et al. brainlife.io: a decentralized and open-source cloud platform to support neuroscience research. Nat Methods 21, 809–813 (2024). https://doi.org/10.1038/s41592-024-02237-2
