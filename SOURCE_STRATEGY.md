# Public-source strategy and bundled data rights

Reviewed 2026-09-07. Runtime registry: src/ree/assets/source_registry.json.
Public accessibility alone is not redistribution permission. Rights are checked for the material
actually included, not for all linked imagery, logos, articles or third-party products.

## Implemented scope

| Source | Use/status | Rights and access boundary |
| --- | --- | --- |
| USGS official pages / selected facts | Curated offline earthquake facts and one short tsunami excerpt | USGS-produced facts/text under the stated government-information policy; no third-party images included |
| NASA Photojournal | One short Bangladesh flood excerpt | Attribution and NASA information-use guidance; no imagery, logos or implied endorsement |
| USGS FDSN catalog | One implemented bounded API adapter; real connectivity check blocked by DNS | Fixed endpoint, USGS contributor only, no credentials, policy/response checks, no completeness claim |
| ReliefWeb | Registry candidate, no collector | Approved appname and item-specific rights remain prerequisites |
| Local files | Implemented ingestion | User-declared rights; private/sensitive by default; public output requires explicit declarations |

USGS [GeoJSON documentation](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php),
[catalog API](https://earthquake.usgs.gov/fdsnws/event/1/) and
[copyright policy](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
were reviewed. ReliefWeb's [parameters documentation](https://apidoc.reliefweb.int/parameters) requires
an approved appname; none is supplied or borrowed. Broader NOAA/open-portal/RSS sources can be added
only with explicit adapters, rights review and verification. Local RSS parsing is not a live RSS crawler.

## What the frozen sample actually is

The only canonical input is assets/frozen.json. It contains four curated records:

1. Noto earthquake facts, including the rounded starting location described by the USGS finite-fault
   model. This point is marked model_reference/representational, not the final epicenter or error bound.
   Source: [USGS Noto finite-fault page](https://earthquake.usgs.gov/earthquakes/eventpage/us6000m0xl/finite-fault).
2. Hualien earthquake facts transcribed from the official indexed event header, with source-reported
   coordinates. Source: [USGS Hualien event page](https://earthquake.usgs.gov/earthquakes/eventpage/us7000m9g4/finite-fault).
3. A short USGS sentence about the Noto tsunami, with the dated article serving as a relative-weekday
   anchor. Source: [USGS January 2024 account](https://www.usgs.gov/news/featured-story/new-years-day-m75-earthquake-shakes-japans-west-coast).
4. A short sentence about flooding around Sylhet. The excerpt does not specify occurrence time, so that
   field stays unknown despite the page's publication date; city versus surrounding-area extent is unresolved.
   Source: [NASA SWOT Bangladesh page](https://science.nasa.gov/photojournal/swot-captures-flooding-in-bangladesh/).

The official indexed fields and readable pages were checked during curation. Event pages depend on
JavaScript, and direct API retrieval was unavailable. These are attributed factual transcriptions and
short excerpts, **not raw API response snapshots**. Each record records acquisition kind, source URL,
reviewed date and limitations. The NASA guidance is documented at
[NASA images/media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/).
No copyrighted source image, logo, third-party map or whole narrative article is redistributed.

The tiny gazetteer contains only names/hierarchy facts and two alternative Sylhet interpretations, with
no invented coordinates or asserted administrative boundary. Public source facts do not turn this into
an independently annotated accuracy benchmark. Synthetic input edge cases exist only inside tests.

## Frozen versus live

Frozen inputs are versioned; output regression expectations are retained independently of each run.
Live collection queries current provider records and may change. A real bounded historical query was
attempted during this build and failed with temporary DNS resolution failure. Its failure manifest is
preserved in the release audit. Mocked HTTP tests do not count as a successful live API acceptance test.
No blocked request was replaced with fabricated live data.

## Collection and disclosure policy

Registry metadata carries topics, geography, date/language coverage, formats, endpoint/access method,
rights, authentication, rate/budget guidance and implementation status. Discovery only selects registered
candidates. Unknown storage/redistribution permission disables the affected live operation. Implemented
USGS collection requests budget + one sentinel, reports truncation and does not paginate exhaustively.

Local source identity cannot impersonate a registry source. Whole-record public suppression covers
sensitive or redistribution-unapproved input before database, replay or export writes. Config paths may
remain in metadata; private runs retain content. Automatic PII detection, aggregation and spatial masking
are not implemented. Review declared rights and outputs before sharing. Code's MIT license does not
relicense external data. This audit addresses the included narrow sample, not future source additions.
