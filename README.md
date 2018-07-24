# Flow Balance Repo
This repository contains the source for the flow-balance page accessible through the [data-quality login](https://connected-corridors.berkeley.edu/tool).

## Goal
Flow balance aims to identify misplaced or mistuned PeMS detectors by a simple counting method. It is also a convenient portal for a visual summary of detector status and location.

## Description
Detector failures (miscounts) are assumed to be rare, so flow-balance attempts to blame local miscounts on single detectors.

Some terms:
- **FATV** stands for Fully Accounted Traffic Volume. FATVs are sets of ingress and egress detectors determined automatically from the Aimsun network via a modified strongly connected components. They are guaranteed to be as small as possible by number of detectors and _must_ account for all traffic entering and leaving. The difference in traffic on the incoming and outgoing edges in a FATV is its miscount, and will stay within a small capacity near zero for functioning detectors. A detector can belong to the incoming set of _at most_ 1 FATV and the outgoing set of _at most_ 1 FATV. FATVs are said to be adjacent if they share at least one detector.
- A detector's **neighbor** or **peer** is any detector that belongs to one or both of the same FATVs. Any set of detectors that belong to the same two FATVs are **dependent**. Miscount among dependent detectors cannot be definitively assigned to any of them.
- **Witnesses** are detectors that belong to a FATV that has a miscount and an adjacent FATV with a miscount of similar magnitude and opposite sign. A detector that belongs to such a pair of FATVs is assumed to be the source of the failure and its neighbors are witnesses to that failure. Neighbors may also witness the failure of more than one detector, or a dependent set, in which case it is ambiguous which detector has failed.

Flow balance classifies PeMS detectors with colors. At the moment there are 3 classes:

- Grey: This detector has reported less than 50% mean observation, or all NaN. No data.
- Orange: This detector reported data, but belongs to a FATV in which at least one NaN was reported that day. No analysis is run on these detectors either.
- Green: This detector is reporting data, and if it belongs to a FATV, its count agrees with its neighbors.
- Red: This detector has not reported a NaN, all of its neighbors have not reported a NaN, and each neighbor is an unambiguous witness to its failure.

The red category is a very strong condition, so I believe it is a strong indicator of either an error with the detector, or the model the fatvs are based on.

What counts as a significant miscount is somewhat subjective, and at the moment is based on a heuristic algorithm that tries to find the relative errors based on the finite capacity of each FATV (FATVs that are spread out have larger capacities). The diagnosis is a target for improvement in the future.

To use the flow-balance page, just click on the icon of a detector. The view will zoom to enclose the surrounding neighborhood of the selected detector. The page will present a plot for each FATV the detector belongs to, representing the sum of flow per 5 minutes over the course of the chosen date.

To avoid confusion about the state of the Aimsun model, only the most recently provided version of the Aimsun model is referenced. To update the model, zip together 'detectors.json', 'junctions.json', and 'sections.json' provided by the Aimsun plugin in the scripts directory and upload it to the s3 bucket with the prefix 'info/model.zip'. For the case where the dumps are placed in a 'model/' subdirectory:
```
zip -j model.zip model/*
aws s3 cp model.zip s3://flow-balance/info/model.zip
```
should trigger the update. Model data is used to construct the FATVs and color some detectors, and _not_ to update their visual location on the map. Analysis should be rerun on days of concern following an update to the model data.

## Details
On each analysis day, flow-balance ([fb-daily](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/fb-daily)) retrieves data from the following sources:
- Flows and observed statistice from PeMS `station_5min` dataset
- Detector names, locations and other meta data from the most-recent-prior `station_meta` dataset.
- Accurate detector locations from [info/locations.csv](https://console.aws.amazon.com/s3/buckets/flow-balance/info/?region=us-west-2&tab=overview)
- Detector FATVs from [info/fatvs.json](https://console.aws.amazon.com/s3/buckets/flow-balance/info/?region=us-west-2&tab=overview)

The location and FATV files do _not_ change automatically. They were dumped from an old version of the aimsun model, and the scripts that did so can be found under the deprecated dash/scripts directory.

Ephemeral data is stored under the data/ prefix, which has a maximum lifetime lifecycle policy to avoid data hoarding. This data is retrieved with the [fb-proxy](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/fb-proxy) lambda function.

The categorization ([fb-analyze](https://us-west-2.console.aws.amazon.com/lambda/home?region=us-west-2#/functions/fb-analyze)) is triggered when new data appears in the data/ prefix.

The api also supports triggering an analysis (data download + categorization) via HTTP PATCH. See [the api](https://us-west-2.console.aws.amazon.com/apigateway/home?region=us-west-2#/apis/2o0pm5fi7f/resources).
