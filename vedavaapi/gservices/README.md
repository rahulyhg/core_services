This defines a `VedavaapiGservices` class which is subclass of `vedavaapi.common.VedavaapiService`. it's config is mapped to `gservices` key.

it's config should contain fallowing keys:
```python
server_config = {
    "gservices" : {
        "google_creds_base_dir" : "/home/samskritam/vedavaapi/core_services/vedavaapi/conf_local/creds/google/",
        "credentials_path" : "vedavaapi-credentials.json", #should be relative to google_creds_base_dir
        "is_service_account_credentials" : 0,
        "scopes" : ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets.readonly"]
  }
}
```

to enable it, we have to add `gservices` in run.py services. then object of this service will be created and will be avialable from `common.VedavaapiServices` store.

where ever we need it, we just have to get it's object from VedavaapiServices, and from that access gservices.

####example code:

```python
from vedavaapi.common import VedavaapiServices

gservices = VedavaapiServices.lookup("gservices").services() #it is our services factory.
gsheets = gservices.gsheets() #get what ever helper services we want. this for sheets
gdrive = gservices.gdrive() #yet another helper service for drive

#now use them
details, code = gsheets.spreadsheet_details_for('1yP82Y5d5mGrvNV2e-OPc6rBhPEtTYWI2vEwYN7uZdnU')
vakyas_sheet_values, statuscode = gsheets.sheet_values_for(spreadsheet_id='someGooGleSheetId',sheet_id='Vakyas', pargs={'idType':'title', 'valuesFormat':'maps', 'fields':['Vakya_id', 'Tantrayukti_tag', 'Vakya'], 'range':'1:27'} )

```

in some cases, if any VedavaapiService needed seperate credentials, due to their destructive writable scopes enabled, then -
just pass that specialized config to .services() call like below. then VedavaapiGservices will use that configuration, instead of it's default config. it is incremental. i.e. if any of required detail about credentials config, not provided in that custom config, then for that argument, it will fallback on default config. thus only extra/custom attributes need to be overrided. fallowing is example using additional options.

```python
from vedavaapi.common import VedavaapiServices

gservices = VedavaapiServices.lookup("gservices").services(custom_config_dict) #it is our services factory customised for our custom_config.

gdrive = gservices.gdrive(force=True, expose_backend_errors=False) #force=True will force recreate gdrive helper, even if it exists prior. it may be needed in some rare cases
'''
fallowing gsheets will also links to gdrive to retrieve extra modification_details, creation_details, etc of spreadsheet. this is not possible with sheet's api. drive api calls are required.
'''
gsheets = gservices.gsheets(enable_drive_service_linking=True, expose_backend_errors=False)

details, code = gsheets.spreadsheet_details_for('1yP82Y5d5mGrvNV2e-OPc6rBhPEtTYWI2vEwYN7uZdnU')
vakyas_sheet_values, statuscode = gsheets.sheet_values_for(spreadsheet_id='someGooGleSheetId',sheet_id='Vakyas', pargs={'idType':'title', 'valuesFormat':'maps', 'fields':['Vakya_id', 'Tantrayukti_tag', 'Vakya'], 'range':'1:27'} )

```
####Api
this package also provides api blueprint for gproxy api. It acts as a proxy to google apis. It authorises on behalf of callees with default credentials and returns what ever result it get to callee.
It not just give some helper url endpoints, but also is 'true proxy'. i.e we can use every readonly feature of google apis instead of just some convinient features. each namespace provides a `/raw/<path: path>` endpoint, where path can be any valid path of corresponding google api. this api then gets token from refresh token in credentials, and then signs http request with token authorisation info, and sends request to googleapis. then passes on results directly in response. example urls are like below.

```html
https://sheets.googleapis.com/v4/spreadsheets/1CxowriO8-FIbV4ux5UBoNawdY4O1S6lTe-U6BAnc1Wo/values:batchGet?ranges=Concept-sum!A1:D5&ranges=Sambandhas!A1:D5&majorDimension=COLUMNS

above google sheets api url which requests some batch ranges values in a spreadsheet using A1 notation will translates to following in gproxy api.(assuming app running on 127.0.0.1:5000)

http://127.0.0.1:5000/gproxy/gsheets/raw/1CxowriO8-FIbV4ux5UBoNawdY4O1S6lTe-U6BAnc1Wo/values:batchGet?ranges=Concept-sum!A1:D5&ranges=Sambandhas!A1:D5&majorDimension=COLUMNS

i.e prefix https://sheets.googleapis.com/v4/spreadsheets/ will be replaced with http://127.0.0.1:5000/gproxy/gsheets/raw/


same thing can be done with gdrive endpoint.
```

along with proxy /raw/ endpoint, each namespace (like gsheets) supports their own helper endpoints. like following

```html
http://127.0.0.1:5000/gproxy/gsheets/1CxowriO8-FIbV4ux5UBoNawdY4O1S6lTe-U6BAnc1Wo/Concept-sum?idType=title
is to get Concept-sum sheets's values, with headers resolved, values mapped, and comments considered, and other required optimisations.
```