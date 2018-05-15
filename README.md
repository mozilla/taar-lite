[![Build Status](https://travis-ci.org/mozilla/taar-lite.svg?branch=master)](https://travis-ci.org/mozilla/taar-lite)

# Taar-lite
A lightweight version of the [TAAR](https://github.com/mozilla/taar) service intended for specific deployments where a reduced feature space is available for the recommendation of addons.

Table of Contents (ToC):
===========================

* [How does it work?](#how-does-it-work)
* [Current Deployments](#current-deployments)
* [Building and Running tests](#build-and-run-tests)

## How does it work?
Each specific deployment recommendation strategy is implemented through this repo, usually accessible via [taar-api-lite](https://github.com/mozilla/taar-api-lite). 
The individual use cases reply on modelling perfromed via use-case-specific ETL jobs hosted in [python_mozetl](https://github.com/mozilla/python_mozetl) which leverage the [Telemetry](https://firefox-source-docs.mozilla.org/toolkit/components/telemetry/telemetry/data/common-ping.html), 
data corpora to drive a set fo recommendation choices.

### Current Deployments
This is the list of the current deployments of TAAR-lite:

| Model | Description | Conditions |
|-------|-------------|------------|
[AMO gui-guid](https://github.com/mozilla/taar-lite) |recommends add-ons based on co-installation rate with other addons.|Sufficient installation rate of requested guid|

#### ETL workflow AMO guid-guid TAAR-lite
* [taar_amodump.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_amodump.py)
	* Scheduled to run daily
	* Collects all listed addons by callign the [AMO public API](https://addons.mozilla.org/api/v3/addons/search/) endpoint
	* Applies filter returning only Firefox Web Browser Extensions
	* Writes __extended_addons_database.json__
* [taar_amowhitelisy.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_amowhitelist.py) 
	* Scheduled to run daily, dependent on successful completion of [taar_amodump.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_amodump.py) 
	* Filters the addons contained in __extended_addons_database.json__
		* removes legacy addons
		* removes Web Extensions with a rating < 3.0
		* removes Web Extensions uploaded less than 60 days ago
		* removes [Firefox Pioneer](https://addons.mozilla.org/en-GB/firefox/addon/firefox-pioneer/?src=search)
	* Writes __whitelist_addons_database.json__
* [taar_lite_guidguid.py](https://github.com/mozilla/python_mozetl/blob/master/mozetl/taar/taar_lite_guidguid.py)
	* Computes the coinstallation rate of each whitelisted addon with other whitelisted addons for a sample of Firefox clients
	* Removes rare combinations of coinstallations 
	* writes __guid_coinstallation.json__

## Build and run tests
WIP
