
# Graph representation

It is helpful to discuss candidate lists, relevance scores and treatments
(as described in the [GUID-GUID recommender docs](./GuidGuidRecommender.md))
in terms of an __add-on relational graph__ structure,
as much of the intuition behind the treatments
is drawn from this representation.

An add-on relational graph is a graph $G = (V,E)$,
which may or may not be directed, and in which:

- each vertex is an add-on appearing in the dataset
- there is an edge from A to B if add-on B is considered __related__ to add-on A
- each edge from A to B has an associated weight
    indicating the strength of the relationship:
    the __relevance__ of B to A.

Note that add-on relation and relevance may not be symmetric,
in which case the graph is directed.
A treatment may produce a graph in which
A is related to B but B is not related to A,
for example if it removes edges whose weight falls below a threshold.
The corresponding graph would have an edge running from B to A
but not the other way.
It is also possible for both add-ons to be related to each other,
but for the relevance of B to A to be different from
the relevance of A to B.
In this case, the graph has edges between A and B in both directions,
but with different weights.
However, since the relation of _being coinstalled_ is symmetric,
the initial coinstallation graph is undirected.

The data used in generating recommendations can be summarized
by such a graph, where
an add-on's [candidate list](./GuidGuidRecommender.md#generating-the-scored-candidate-lists)
corresponds to its set of neighbours in the graph,
with relevance scores given by the edge weights.
In this setting:

- The [coinstallation data](./GuidGuidRecommender.md#input-data)
    can be represented as an undirected relational graph,
    considering add-ons related if they are coinstalled,
    and using coinstallation counts
    (or some metric derived from these)
    as weights.
- [Treatments](./GuidGuidRecommender.md#generating-the-scored-candidate-lists)
    can be thought of as transformations
    which modify add-on relational graphs by
    adding or deleting edges, or adjusting the edge weights.
    They are discussed in detail [below](#treatments).
- The final [selection of recommendations](./GuidGuidRecommender.md#selecting-recommendations)
    can itself be viewed as a treatment,
    which outputs a graph containing, for each add-on A,
    an edge from A to each of A's N recommendations.

The recommendation algorithm can be rephrased
in terms of this representation as follows:

1. Load the input data and create the __coinstallation graph__.
2. Apply each of the specified treatments in turn to the coinstallation graph,
    resulting in the __treated graph__.
3. Apply the recommendation selection treatment to the treated graph
    to produce the __recommendation graph__.

A relational graph has an associated __adjacency matrix__ $C$,
in which rows and columns are indexed by add-ons (graph vertices),
and entry $C_{ij}$ contains the weight for edge $(i,j)$
if these two add-ons are connected in the graph, or 0 otherwise.
The initial coinstallation dataset is in fact stored
as a [sparse representation](./GuidGuidRecommender.md#input-data)
of its adjacency matrix.
Since this graph is undirected, the adjacency matrix is symmetric
($C_{ij} = C_{ji}$ for any pair $i,j$).
Also, the row sum (or column sum, by symmetry) for add-on $i$ gives
its overall number of installs across all Firefox profiles
considered in the dataset.


## Graph properties

For reference, we now list some of the main properties of
each of the milestone relational graphs listed above.
A glossary of graph theory terms is available [here](https://en.wikipedia.org/wiki/Glossary_of_graph_theory_terms).


### Coinstallation graph

The graph induced by the raw coinstallation counts has the following properties:

- It is undirected, ie. each edge runs both ways.
- Its vertex degree may take values from 1 to $|V|$,
    the overall number of add-ons in the graph.
    In other words, every vertex has at least one incident edge.
- Edge weights correspond to the raw coinstallation count.
- It may or may not be connected.
    However, there are no unreachable (singleton) vertices.


### Treated graph

The result of applying the treatments to the coinstallation graph
has these properties:

- It is directed in general,
    as treatments may not operate on edges symmetrically.
    In particular, some or all pairs of vertices may be connected by edges
    running in both directions but bearing different weights.
- Both vertex in-degree and out-degree may take values from 0 to $|V|$,
    and may be different.
    In general, a treated vertex may have any number of incident edges.
- Edge weights represent general relevance scores, which may not be symmetric.
    The weight on edge (A,B) represents the relevance of B in relation to A,
    which may be different from the relevance of A in relation to B.
- It may or may not be strongly or weakly connected.


### Recommendation graph

The recommendation graph is obtained by dropping all edges except those
leading to each add-on's top N most relevant recommendations,
with these properties:

- It is a strict subset of the treated graph,
    with the same vertices and a subset of the edges.
- It is directed.
    For example, that B is a recommendation for A does not imply that
    A is a recommendation for B.
- Vertex in-degree may take values from 0 to $|V|$,
    meaning that any number of add-ons may recommend the current vertex add-on.
- Vertex out-degree is constrained to be at most N, representing the add-ons
    recommended for the current vertex add-on.
- Edge weights no longer play a role.
    Without loss of generality, they can all be set to 1.
- It may or may not be strongly or weakly connected.
    In particular, there may be a number of add-ons which have outgoing edges
    but no incoming edges,
    in that they have associated recommendations,
    but are never recommended from other add-ons.


# Treatments

A __treatment__ is a function which takes an add-on relational graph,
applies a transformation and returns the result,
which is also an add-on relational graph.
Hence, multiple treatments can be applied in sequence,
ie. the treatment functions can be composed,
to form a general graph transformation workflow.

The following treatments are [implemented](../taar_lite/recommenders/treatments.py)
for the `GuidGuidCoinstallRecommender`.
We categorize them into [normalizations](#normalizations)
and [graph pruning](#graph-pruning).


## Normalizations

One issue with drawing recommendations directly
from the raw coinstallation graph
is that popular add-ons can greatly outweigh more relevant add-ons,
since the distribution of add-on install counts is heavily skewed.
If a popular add-on such as AdBlock Plus is coinstalled with a given add-on A,
it will likely have the highest raw count out all add-ons coinstalled with A,
and thus would top the list of recommendations.
Furthermore, such popular add-ons are likely to appear
on most add-ons' coinstall lists.
Thus, we seek to transform coinstallation counts in such a way as to discount
the effect of overall popularity.
This corresponds to adjusting the edge weights in the graph representation.

Note that, even though the raw coinstallation graph is undirected
(with a symmetric adjacency matrix),
the graph generated by the normalization treatments may no longer be undirected.
Although no edges are added or removed,
the edge weights may be modified asymmetrically,
meaning that a single undirected edge in the original graph
may get transformed into two directed edges with different weights
in the result.

Although these normalizations are described
in terms of the raw coinstallation matrix,
they can be applied as treatments to any add-on relational graph.

The currently implemented normalization treatments are [add-on count](#add-on-count-normalization),
[total relevance](#total-relevance-normalization),
and [proportional total](#proportional-total-normalization).


### Add-on count normalization

This treatment accounts for the popularity of an add-on in terms of
how widely it is coinstalled,
ie. how many different add-ons it appears coinstalled with.
It reweights the graph based on the hypothesis:
__the more add-ons a given add-on is coinstalled with,
the less likely it is to be a relevant recommendation__.

For each add-on B coinstalled with a given add-on A,
the coinstallation count for (A,B) is divided by
the total number of add-ons that B is coinstalled with.

Given the adjacency matrix $C$,
the treatment divides each each entry $C_{ab}$
by the number of non-zero entries in column $b$.
In terms of the graph representation,
the weight on each edge (A,B) leaving A is divided by
the (in-)degree of the neighbour B.

Intuitively, the total number of coinstalls with B (column sum)
divided by the number of add-ons B is coinstalled with (number of non-zero entries)
represents the average number of coinstallations per coinstalled add-on.
The normalized score for (A,B) can be thought of as the contribution
to this average from add-on A.
This normalization is most effective when comparing add-ons B
with similar total installation counts,
of which some may be coinstalled more widely than others.

This treatment is implemented as [`RowCount`](../taar_lite/recommenders/treatments.py#L87).


### Total relevance normalization

This treatment accounts for the popularity of an add-on in terms of
its overall total number of coinstallations,
under the assumption that
__the more often an add-on is coinstalled with other add-ons overall,
the less likely it is to be relevant__.

For each add-on B coinstalled with a given add-on A,
the coinstallation count for (A,B) is divided by
the total number of coinstallations of B across all other add-ons.
(This will be greater than the total number of installations of B
if some Firefox profiles have more than two add-ons,
since these profiles will get counted more than once.)

Given the adjacency matrix $C$,
the treatment divides each each entry $C_{ab}$
by the column sum for column $b$.
In terms of the graph representation,
the weight on each edge (A,B) leaving A is divided by
the sum of the weights on all edges entering B.

Intuitively, the normalized score for (A,B) represents
the proportion of B's total coinstalls contributed by Firefox profiles
that also have A installed.
Thus, out of all the add-ons related to A,
those with the highest normalized scores
are those which are more likely
to be coinstalled with A than with other add-ons.
We would expect this normalization to do a better job
than the [add-on count normalization](#add-on-count-normalization)
at controlling for the heavy skew of the distribution
of overall install counts.

As discussed [above](#graph-representation), in the raw coinstallation matrix,
row sums are equal to column sums for each add-on
and represent the total number of coinstalls.
For a general add-on relational graph, the matrix may no longer be symmetric,
but the intuition behind the normalization still applies.
In this case, we can view the column sum for B
as an __aggregate relevance score__ over the universe of add-ons,
as it is the sum of relevance scores for B
in relation to each other add-on A.
The normalization converts raw relevance scores to
the proportion of aggregate relevance derived from add-on A.


This treatment is implemented as [`RowSum`](../taar_lite/recommenders/treatments.py#L64).


### Proportional total normalization

This treatment is a rescaled version of the [total relevance normalization](#total-relevance-normalization).
Rather than total coinstalls, popularity is quantified in terms of
the proportion of coinstalls associated with each add-on.
Here, the assumption is that
__more relevant recommendations tend to account for
a higher proportion out of the given add-on's coinstallations than it does
for other add-ons__.

Given add-on A, the coinstallation count for (A,B) for each add-on B
is first divided by the sum of all A's coinstallation counts.
The total relevance normalization is then applied to the resulting proportions.

Given the adjacency matrix $C$,
the treatment first divides each each entry $C_{ab}$
by the row sum for row $a$,
and then divides each entry by the column sum for column $b$
in the resulting matrix.
In terms of the graph representation,
the weight on each edge (A,B) leaving A is first divided by
the sum of the weights on all edges leaving A,
and then the resulting edge weight is divided by
the sum of the weights on all edges entering B.

Intuitively, the first step converts coinstallation counts for A
to the proportion of coinstallations of A allocated to each add-on B.
In the case of general relevance scores, we can think of the row sum for A
as a __relevance budget__,
ie. the total amount of relevance it has available to assign to other add-ons.
The first division has the effect of normalizing each add-on's
relevance budget to 1.
The next step then normalizes each coinstalled add-on's
resulting aggregate relevance to 1.

This treatment is implemented as [`RowNormSum`](../taar_lite/recommenders/treatments.py#L126).


## Graph pruning

Another class of treatments we may wish to apply involves modifying
the sets of vertices or edges of the relational graph themselves,
possibly as a function of the edge weights.
For example, we may wish to remove vertices or edges that fall below
a minimum relevance threshold, in order to avoid recommending rare add-ons.
Also, we may wish to ensure certain properties of the graph as a whole.
It is possible for a user visiting AMO to "walk" the recommendation graph
by clicking through a chain of subsequent recommendations.
Although the recommendations themselves are memoryless,
in that they only depend on the current add-on,
we are interesting in optimizing the quality of experience
for such users as well,
such as not returning to a previous add-on in a short number of steps.
This can be accomplished by adding or removing edges between certain vertices.

The currently implemented graph pruning treatments are [minimum relevance](#minimum-relevance-pruning)
and [recommendation selection](#recommendation-selection).

### Minimum relevance pruning

This treatment removes add-on vertices whose relevance score is lower
than a given threshold,
under the assumption that
__candidates with such low relevance would not make good recommendations,
even if there are no candidates with higher relevance__.
When relevance is given by coinstallation counts,
this also helps to preserve privacy
by dropping rare add-on combinations from the recommendation candidate lists.

The relevance threshold is computed based on an auxiliary list
of overall relevance scores for each add-on.
It is chosen as 5% of the mean of all the overall scores.
Then, if any add-on has a relevance score below this value,
its vertex (and all incident edges) is removed from the relational graph.
Equivalently, the corresponding row and column are removed from the matrix $C$.

This treatment is implemented as [`MinInstallPrune`](../taar_lite/recommenders/treatments.py#L36).
The auxiliary score list is supplied as the keyword arg `ranking_dict`,
a dict mapping add-on GUIDs to overall relevance scores.


### Recommendation selection

The procedure for [selecting recommendations](./GuidGuidRecommender.md#selecting-recommendations)
is itself just another graph pruning treatment.

For each add-on A in the graph, the edges leaving A are ordered
by decreasing relevance score (weight),
with ties broken using a supplied list of auxiliary add-on scores.
All but those edges with the top N highest weights are then
deleted from the graph.

The output of this treatment is the final recommendation graph,
in which the recommendations for a given add-on A
can be read off as A's neighbours.
As these final recommendations are considered unordered,
we ignore the final edge weights, and can optionally set them to all to 1.

