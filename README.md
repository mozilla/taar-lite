[![Build Status](https://travis-ci.org/mozilla/taar-lite.svg?branch=master)](https://travis-ci.org/mozilla/taar-lite)

# TAAR-lite
A lightweight version of the [TAAR](https://github.com/mozilla/taar) service intended for specific deployments where a reduced feature space is available for the recommendation of add-ons.

Table of Contents:
==================

* [How does it work?](#how-does-it-work)
* [Current Deployments](#current-deployments)
* [Building and Running tests](#build-and-run-tests)
* [Setting up analysis environment](#setting-up-analysis-environment)

## How does it work?
Each specific deployment recommendation strategy is implemented through this repo, usually accessible via [taar-api-lite](https://github.com/mozilla/taar-api-lite). 
The individual use cases rely on modeling performed via use-case-specific ETL jobs hosted in [python_mozetl](https://github.com/mozilla/python_mozetl) which leverage Firefox [Telemetry](https://firefox-source-docs.mozilla.org/toolkit/components/telemetry/telemetry/data/common-ping.html)
data to drive a set of recommendation choices.

### Current Deployments
This is the list of the current deployments of TAAR-lite:

| Model | Description | Conditions |
|-------|-------------|------------|
[AMO GUID-GUID](https://github.com/mozilla/taar-lite) |Recommends add-ons based on coinstallation rate with other add-ons|Sufficient installation rate of requested GUID|

#### ETL workflow for AMO GUID-GUID TAAR-lite
* [taar_amodump.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_amodump.py)
	* Scheduled to run daily
	* Collects all add-ons listed on AMO by calling the [AMO public API](https://addons.mozilla.org/api/v3/addons/search/) endpoint
	* Applies filter returning only Firefox Web Browser Extensions
	* Writes __extended_addons_database.json__
* [taar_amowhitelisy.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_amowhitelist.py) 
	* Scheduled to run daily, dependent on successful completion of [taar_amodump.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_amodump.py) 
	* Filters the add-ons contained in __extended_addons_database.json__:
		* removes legacy add-ons
		* removes Web Extensions with a rating < 3.0
		* removes Web Extensions uploaded less than 60 days ago
		* removes [Firefox Pioneer](https://addons.mozilla.org/en-GB/firefox/addon/firefox-pioneer/?src=search)
	* Writes __whitelist_addons_database.json__
* [taar_lite_guidguid.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_lite_guidguid.py)
	* Computes the coinstallation rate of each whitelisted add-on with other whitelisted add-ons for a sample of Firefox clients
    * Further filters the whitelisted add-ons:
        * removes system add-ons
        * removes disabled add-ons (although there shouldn't be any in the client data)
        * removes sideloaded add-ons
	* Writes __guid_coinstallation.json__

## Build and run tests

    $ python setup.py test

Or

    $ pip install -r requirements.txt
    $ pip install -r requirements_test.txt
    $ py.test

## Setting up analysis environment

conda env

    $ conda create -n taarlite_analysis python=3.6
    $ conda activate taarlite_analysis
    $ pip install -r requirements.txt
    $ conda install --file requirements_analysis.txt
