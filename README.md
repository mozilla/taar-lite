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
This is the ordered list of the currently deployments of TAAR-lite:

| Order | Model | Description | Conditions | Generator job |
|-------|-------|-------------|------------|---------------|
| 1 | [AMO gui-guid](https://github.com/mozilla/taar-lite) |recommends add-ons based on co-installation rate with other addons.|Sufficient installation rate of requested guid|WIP|

## Build and run tests
WIP
