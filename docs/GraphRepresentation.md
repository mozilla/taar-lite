
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


### Degree normalization

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

This treatment is implemented as [`DegreeNorm`](../taar_lite/recommenders/treatments.py#L87).


#### Example

Suppose we have a universe of 101 add-ons,
with the following coinstallation data:

```python
coinstalls = {
    # A is coinstalled with every other add-on
    'A': {'B': 50, 'C': 50, 'D': 50, ...},
    'B': {'A': 50, 'C': 5, 'D': 1},
    'C': {'A': 50, 'B': 5},
    'D': {'A': 50, 'B': 1},
    # Each other add-on is coinstalled at least with A,
    # and possibly with other add-ons outside of B, C, D.
    ...
}
```

The associated adjacency matrix is:

|     |A    |B    |C    |D    |...  |
|:---:|:---:|:---:|:---:|:---:|:---:|
|A    |     |50   |50   |50   |...  |
|B    |50   |     |5    |1    |     |
|C    |50   |5    |     |     |     |
|D    |50   |1    |     |     |     |
|...  |...  |     |     |     |...  |

To apply the normalization, we count the number of non-zero entries
down each column of the matrix:

```python
non_zero_counts = {
    'A': 100, # A is coinstalled with 100 add-ons
    'B': 3,   # B is coinstalled with 3 add-ons
    'C': 2,   # C is coinstalled with 2 add-ons
    'D': 2,   # D is coinstalled with 2 add-ons
    ...
}
```

and divide each column of the matrix by the corresponding count:

|     |A    |B    |C    |D    |...  |
|:---:|:---:|:---:|:---:|:---:|:---:|
|A    |     |16.7 |25   |25   |...  |
|B    |0.5  |     |2.5  |0.5  |     |
|C    |0.5  |1.67 |     |     |     |
|D    |0.5  |0.33 |     |     |     |
|...  |...  |     |     |     |...  |

Observe:

- The relevance of A to each other add-on
    (the value in column A for each other row),
    has been downweighted.
- A is no longer the most relevant add-on for B and C (looking along their rows).
- The interplay between B, C, and D has risen to the surface.
- The relevances of other add-ons to A (along row A)
    are no longer all equal, as those coinstalled with more add-ons
    have been downweighted.
- The matrix is no longer symmetric, eg. the relevance of B to A (entry (A,B))
  is no longer the same as the relevance of A to B (entry (B,A)).


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


#### Example

In this example, we have a universe of only 5 add-ons,
with the following coinstallation data:

```python
coinstalls = {
    'A': {'B': 1000, 'C': 100, 'D': 10, 'E': 1},
    'B': {'A': 1000, 'C': 50, 'D': 50},
    'C': {'A': 100, 'B': 50, 'D': 100},
    'D': {'A': 10, 'B': 50, 'C': 100, 'E': 5},
    'E': {'A': 1, 'D': 5}
}
```

The associated adjacency matrix is:

|     |A    |B    |C    |D    |E    |
|:---:|:---:|:---:|:---:|:---:|:---:|
|A    |     |1000 |100  |10   |1    |
|B    |1000 |     |50   |50   |     |
|C    |100  |50   |     |100  |     |
|D    |10   |50   |100  |     |5    |
|E    |1    |     |     |5    |     |

To apply the normalization, we sum the values
down each column of the matrix:

```python
column_sums = {
    'A': 1111, # A is coinstalled 1111 times
    'B': 1100, # B is coinstalled 1100 times
    'C': 250,  # C is coinstalled 250 times
    'D': 165,  # D is coinstalled 165 times
    'E': 6     # E is coinstalled 6 times
}
```

and divide each column of the matrix by the corresponding sum:

|     |A    |B    |C    |D    |E    |
|:---:|:---:|:---:|:---:|:---:|:---:|
|A    |     |0.91 |0.4  |0.061|0.167|
|B    |0.9  |     |0.2  |0.3  |     |
|C    |0.09 |0.045|     |0.61 |     |
|D    |0.009|0.045|0.4  |     |0.83 |
|E    |0.001|     |     |0.03 |     |

Observe:

- B is still the most relevant add-on to A (along row A),
    since in a coinstall with B, the other add-on is most likely to be A.
    For the same reason, A is still the most relevant add-on to B (along row B).
- E is now the second-last most relevant add-on to A, rather than D.
- The relevances of C and D to B (along row B) are no longer equal.
- Similarly, D is now the most relevant add-on to C,
    and A is now in last place along row C.
- The relevance of E to D has been upweighted significantly,
    since out of the few coinstalls that include E,
    the other add-on is most likely to be D.
- The matrix is no longer symmetric, eg. the relevance of B to A (entry (A,B))
  is no longer the same as the relevance of A to B (entry (B,A)).
- Columns sum to 1, but row sums are not meaningful.


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

Another way to think about the initial row-wise normalization is that
it corrects for differences in scale of the relevance scores between add-ons.
In the case of coinstallation counts, suppose there is an add-on A
which is much more commonly installed than any of the others.
A's row in the matrix will then tend to have much larger values
than the other rows.
The column sums of the total relevance normalization
are each dominated by the value in row A,
artificially shrinking the scores in the other rows.
If the row-wise normalization is applied first,
each row's relevance scores are rescaled to the interval $[0,1]$.

This treatment is implemented as [`RowNormSum`](../taar_lite/recommenders/treatments.py#L126).


#### Example

Consider a coinstallation dataset consisting of 4 add-ons:

```python
coinstalls = {
    'A': {'B': 50, 'C': 50, 'D': 50},
    'B': {'A': 50, 'C': 10, 'D': 1},
    'C': {'A': 50, 'B': 10},
    'D': {'A': 50, 'B': 1}
}
```

The associated adjacency matrix is:

|     |A    |B    |C    |D    |
|:---:|:---:|:---:|:---:|:---:|
|A    |     |50   |50   |50   |
|B    |50   |     |10   |1    |
|C    |50   |10   |     |     |
|D    |50   |1    |     |     |

To apply the normalization, the first step is to sum the values
along each row of the matrix:

```python
row_sums = {
    'A': 150, # A has 150 coinstallations
    'B': 61,  # B has 61 coinstallations
    'C': 60,  # C has 60 coinstallations
    'D': 51   # D has 51 coinstallations
}
```

and divide each row of the matrix by the corresponding sum:

|     |A    |B    |C    |D    |
|:---:|:---:|:---:|:---:|:---:|
|A    |     |0.33 |0.33 |0.33 |
|B    |0.82 |     |0.16 |0.016|
|C    |0.83 |0.17 |     |     |
|D    |0.98 |0.02 |     |     |

We then apply the total relevance normalization to this matrix,
summing the values down each column:

```python
column_sums = {
    'A': 2.63,
    'B': 0.52,
    'C': 0.49,
    'D': 0.346
}
```

and dividing each column by its corresponding sum:

|     |A    |B    |C    |D    |
|:---:|:---:|:---:|:---:|:---:|
|A    |     |0.63 |0.67 |0.95 |
|B    |0.31 |     |0.33 |0.046|
|C    |0.32 |0.33 |     |     |
|D    |0.37 |0.038|     |     |

Observe:

- The relevance of B and C to each other have been boosted enough
    to overtake A as the most relevant recommendation
    (entries (B,C) and (C,B)).
- The relevances of other add-ons to A (along row A)
    are no longer all equal, and the relevance of D to A has been upweighted
    enough to make it the top recommendation.
- As above, the matrix is no longer symmetric.
- Columns sum to 1, but row sums are not meaningful.

Compare this to the result of applying the total relevance normalization
directly:

|     |A    |B    |C    |D    |
|:---:|:---:|:---:|:---:|:---:|
|A    |     |0.82 |0.83 |0.98 |
|B    |0.33 |     |0.17 |0.02 |
|C    |0.33 |0.16 |     |     |
|D    |0.33 |0.016|     |     |

- A is now surfaced as the most relevant recommendation for every other add-on.
    This is because the large values in row A of the coinstallation matrix
    have overshadowed those for other combinations of add-ons
    when computing the normalization.


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

This treatment removes add-on vertices whose relevance scores are lower
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


#### Example

Consider coinstallations over a universe of 5 add-ons:

```python
coinstalls = {
    'A': {'B': 1000, 'C': 100, 'D': 10, 'E': 1},
    'B': {'A': 1000, 'C': 50, 'D': 50},
    'C': {'A': 100, 'B': 50, 'D': 100},
    'D': {'A': 10, 'B': 50, 'C': 100, 'E': 5},
    'E': {'A': 1, 'D': 5}
}
```

The associated adjacency matrix is:

|     |A    |B    |C    |D    |E    |
|:---:|:---:|:---:|:---:|:---:|:---:|
|A    |     |1000 |100  |10   |1    |
|B    |1000 |     |50   |50   |     |
|C    |100  |50   |     |100  |     |
|D    |10   |50   |100  |     |5    |
|E    |1    |     |     |5    |     |

and the add-on relational graph has the following form:

```
    A----B
  _/|\  /|
 /  | \/ |
E   | /\ |
 \_ |/  \|
   \D----C
```

where all edges are undirected, since the coinstallation matrix is symmetric.

Additionally, suppose we have the following auxiliary scores for these add-ons:

```python
ranking_dict = {
    'A': 1500,
    'B': 1200,
    'C': 250,
    'D': 170,
    'E': 10
}
```

The mean of these scores is 626, and we compute the relevance threshold
as 5% of the mean, which is 31.3.
The auxiliary score for add-on E falls below the threshold,
and so we drop its vertex from the graph.

The new adjacency matrix is:

|     |A    |B    |C    |D    |
|:---:|:---:|:---:|:---:|:---:|
|A    |     |1000 |100  |10   |
|B    |1000 |     |50   |50   |
|C    |100  |50   |     |100  |
|D    |10   |50   |100  |     |

and the updated graph is:

```
    A----B
    |\  /|
    | \/ |
    | /\ |
    |/  \|
    D----C
```

Note that this does not affect the direction or weights
on any of the remaining edges.


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


#### Example

Suppose we have a collection of 5 add-ons with the following relevance scores:

```python
coinstalls = {
    'A': {'B': 0.91, 'C': 0.4, 'D': 0.061, 'E': 0.167},
    'B': {'A': 0.9, 'C': 0.25, 'D': 0.25},
    'C': {'A': 0.09, 'B': 0.045, 'D': 0.61},
    'D': {'A': 0.009, 'B': 0.045, 'C': 0.4, 'E': 0.83},
    'E': {'A': 0.001, 'D': 0.03}
}
```

The associated adjacency matrix is:

|     |A    |B    |C    |D    |E    |
|:---:|:---:|:---:|:---:|:---:|:---:|
|A    |     |0.91 |0.4  |0.061|0.167|
|B    |0.9  |     |0.25 |0.25 |     |
|C    |0.09 |0.045|     |0.61 |     |
|D    |0.009|0.045|0.4  |     |0.83 |
|E    |0.001|     |     |0.03 |     |

and the corresponding graph has the form:

```
    A+----+B
   +++    ++
  / | \  / |
 +  |  \/  |
E   |  /\  |
 +  | /  \ |
  \ ++    ++
   +D+----+C
```

where `+` denotes arrowheads indicating the direction of the edges.
In fact, this graph is effectively undirected,
since each edge runs in both directions.

We are also given the following auxiliary scores to be used for tie-breaking:

```python
tie_breaker_dict = {
    'A': 1500,
    'B': 1200,
    'C': 150,
    'D': 170,
    'E': 10
}
```

We wish to select 2 recommendations for each add-on.
To do this, we order each add-on's candidate list
(row in the adjacency matrix)
by decreasing relevance:

```python
ordered_candidates = {
    #'A': {'B': 0.91, 'C': 0.4, 'D': 0.061, 'E': 0.167}
    'A': ['B', 'C', 'E', 'D'],
    #'B': {'A': 0.9, 'C': 0.25, 'D': 0.25}
    # tie_breaker_dict['C'] is 150, tie_breaker_dict['D'] is 170
    'B': ['A', 'D', 'C'],
    #'C': {'A': 0.09, 'B': 0.045, 'D': 0.61}
    'C': ['D', 'A', 'B'],
    #'D': {'A': 0.009, 'B': 0.045, 'C': 0.4, 'E': 0.83}
    'D': ['E', 'C', 'B', 'A'],
    #'E': {'A': 0.001, 'D': 0.03}
    'E': ['D', 'A']
}
```

Note that, when ordering the candidates for B, we used the auxiliary scores
to break the tie between C and D.
To generate the final recommendations, we select the first 2 items
from each list:

```python
recommendations = {
    'A': ['B', 'C'],
    'B': ['A', 'D'],
    'C': ['D', 'A'],
    'D': ['E', 'C'],
    'E': ['D', 'A']
}
```

We interpret the result as an unweighted add-on relational graph
with adjacency matrix:

|     |A    |B    |C    |D    |E    |
|:---:|:---:|:---:|:---:|:---:|:---:|
|A    |     |1    |1    |     |     |
|B    |1    |     |     |1    |     |
|C    |1    |     |     |1    |     |
|D    |     |     |1    |     |1    |
|E    |1    |     |     |1    |     |

and corresponding graph:

```
    A+----+B
   + +    / 
  /   \  /  
 /     \/   
E      /\   
 +    /  \  
  \  +    + 
   +D+----+C
```

----

__Note:__ R code to generate the matrices and apply the treatments
used in the examples is available in [this gist](https://gist.github.com/dzeber/fbf558c9cdbf3f5573d74e6b75f6bdc5).

