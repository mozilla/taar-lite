
# Overview

The GUID-GUID coinstallation recommender system generates recommendations
for add-ons which are similar to a given add-on,
where similarity is based on the number of Firefox profiles
which have both add-ons installed.

As recommendations are only determined from
a training dataset of add-on coinstallation counts,
and do not depend on any user characteristics collected at runtime,
recommendation sets for each add-on can be (and are) computed in advance.

Recommendations are generated as follows:

1. The [input data](#input-data),
    consisting of coinstallation counts for each pair of add-ons,
    is loaded from a precomputed file.
2. For each add-on, we determine a [__candidate list__](#generating-the-scored-candidate-lists)
    of "related" add-ons,
    together with associated __relevance scores__,
    based on the coinstallation data.
3. Recommendations for a given add-on are [selected](#selecting-recommendations)
    by retaining the N add-ons in the candidate list
    with the highest relevance scores.

Further technical details on each of these steps
are provided on [this page](./GraphRepresentation.md).

Once the recommender has been trained,
we apply various [metrics](./GraphRepresentation.md#quality-and-health-metrics)
to the coinstallation data, candidate lists, and recommendations,
to evaluate the overall health of the system
and the quality of recommendations.



# Input data

The primary data source used in generating recommendations
is a JSON file containing coinstallation counts
for each pair of add-ons belonging to a filtered list,
computed based on the Telemetry data
submitted by a random sample of recently active Firefox profiles.
Details of the steps to generate this file are provided in the [README](../README.md).

The data is stored in sparse matrix representation as a nested object/dict
of the form
```python
{
    'guid_a': {'guid_b': 10, 'guid_c': 13},
    'guid_b': {'guid_a': 10, 'guid_c': 4},
    'guid_c': {'guid_a': 13, 'guid_b': 4},
    ...
}
```
In this example, `guid_a` is coinstalled with `guid_b` 10 times
and with `guid_c` 13 times, and is not coinstalled with any other add-ons
(ie. zero counts are dropped).
On initializing a `GuidGuidCoinstallRecommender`,
this dict is supplied as [`raw_coinstall_dict`](../taar_lite/recommenders/guidguid.py#L25).

Using this dataset as the basis for recommendations
entails the following constraints:

- The set of add-ons appearing in the coinstallation dataset represent
    the universe of known add-ons for the purpose of generating recommendations.
- We are only dealing with add-ons that were coinstalled
    with at least one other add-on on the list
    (otherwise they would not appear in the file at all).
- Profiles with only a single add-on installed do not contribute to the counts.

In computing relevance scores, we also draw on an auxiliary dataset
containing an overall ranking for each add-on in our list,
read from a JSON file of the form
```python
{
    'guid_a': 53,
    'guid_b': 41,
    ...
}
```
This is used to break ties when sorting candidates on relevance score,
and in pruning out rare add-ons.
On initializing a `GuidGuidCoinstallRecommender`,
it is supplied as [`tie_breaker_dict`](../taar_lite/recommenders/guidguid.py#L28).

The tie-breaking dataset is currently computed using
overall add-on installation counts obtained from AMO.
Note that this is not the same as finding total installs
by adding up coinstallation counts,
because of the constraints listed above.

Coincidentally, this dataset of overall rankings
is also used as the [`ranking_dict`](../taar_lite/recommenders/treatments.py#L55)
passed to the `MinInstallPrune` treatment,
although the two arguments are not related.


# Generating the scored candidate lists

The TAAR-lite recommender is built on the following underlying principle:
_add-ons which tend to be installed together are complimentary,
and the number of coinstallations indicates the strength of this relationship._
Thus, starting from a given add-on, good recommendations for other add-ons
are those which are most often coinstalled.

Given an add-on A, a natural choice for a candidate list and relevance scores
is then just the list of add-ons that are coinstalled with A,
together with their coinstallation counts.
However, recommendation quality can be improved by making certain adjustments
to these preliminary scored lists, such as:

- tempering the influence of highly popular add-ons
    so that they don't drown out more relevant, less common ones
- pruning out obscure add-ons
- better balancing relevance against diversity
- improving the experience for users clicking through a chain of recommendations
    on AMO, such as pruning out cyclical recommendations.

Final candidate lists and relevance scores are generated
by applying a sequence of such transformations,
referred to as __treatments__,
to the raw coinstallation data.
As recommendations are based solely on the treated data,
we are assuming that this encapsulates all the information
necessary in generating recommendations.
Treatments are discussed in more detail in terms of their graph representations
[here](./GraphRepresentation.md#treatments).

On initializing a `GuidGuidCoinstallRecommender`,
a list of `BaseTreatment` instances are supplied as [`treatments`](../taar_lite/recommenders/guidguid.py#L26).
When the treated dataset is built, the treatments are applied in sequence
to the raw coinstallation data,
and the result is stored as the recommender instance's `treated_graph`.
Candidate lists and relevance scores are then drawn
from the treated dataset.


# Selecting recommendations

Recommendations for a given add-on A are generated
by ordering A's candidate list by decreasing relevance score
and selecting the first N add-ons from the sorted list.

Ties in relevance score are broken using an additional list
of add-on tie-breaking scores,
by further ordering tied candidates by decreasing tie-breaking score.

