#Usage
* pkgutil, tqdm, bs4 and pathlib have to be installed for the script to work
* you also have to install google big query:
`pip install --upgrade google-cloud-bigquery`
* you also need to use your google credentials:
    + go to your service account
    + download the key
    + do `$ export GOOGLE_APPLICATION_CREDENTIALS="/path/to/keyfile.json"` in a terminal
* run script: `python libraries_parser.py`
* you probably shouldn't mess with the `lib_number` file unless you know what you're doing
* analysis results should be in `{library_name}_everything.json` files, and timing logs should be in `{library_name}_timing.log` (these show how long it took to download and process pages)
* at the moment **only the latest version of a given library gets analysed**. You can set `LVO = False` in the script, but that would probably lengthen the analysis considerably

**WARNING!**
* at the moment the script is meant to be run in a single process. Running it in more than one process/thread would probably fail, and may cause inconsistent logging, errors and 
FUBARing your system python.