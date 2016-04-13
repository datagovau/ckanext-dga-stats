# ckanext-dga-stats

Fork of CKAN's built-in Statistics plugin modified for data.gov.au

* Remove private datasets from all statistics (except top users)
* Add summary page
* Add activity summary page
* Add organisation public/private dataset count page
* Add two config directives:
  * `dga.recent_time_period = 60`
  * `dga.recent_page_limit = 50` 
* Recently Created Datasets and Recently Updated Datasets statistics show changes since now minus dga.recent_time_period up to the dga.recent_page_limit

## System Requirements

* CKAN 2.4+
