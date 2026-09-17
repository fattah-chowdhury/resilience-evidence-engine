# REE data sources and storage policy

Operational review: 2026-09-09. Code license is MIT; provider data retain separate rights. Public access
alone does not establish permission to redistribute every linked product. Registry reference metadata
is preserved so frozen evidence does not drift; this document records the current operational review.

| Registered source | Access and relevance | Availability / authentication | Rights and storage | Citation / limits |
| --- | --- | --- | --- | --- |
| usgs_catalog — U.S. Geological Survey | Fixed HTTPS FDSN GeoJSON query; global earthquakes; registered dates from 1900; bbox/time/magnitude filters | Documentation reachable; real engine request fails DNS here. No API key. Explicit --live required | USGS-produced summary records only; contributor filter plus net validation. No linked third-party products or images. Public raw summary cache is opt-in | Credit USGS and retain record/request URLs. Client uses bounded retries; provider universal request-per-second limit is not asserted |
| usgs_pages — U.S. Geological Survey | Three bundled factual transcriptions/short excerpts about 2024 earthquakes and tsunami | Frozen assets work offline. No runtime page scraping, credentials or current page availability assumption | Narrow USGS-authored facts/excerpts under the provider public-domain policy; no imagery/products | Retain each original URL and acquisition/transcription method; curated input is not a captured API response |
| nasa_excerpt — NASA Science / Photojournal | One eight-word Sylhet flooding excerpt; Bangladesh reference window 2023-10 through 2024-05 | Bundled and offline. Source/usage-policy pages reviewed; no runtime collector | Narrow attributed informational excerpt; excludes imagery, logos and third-party basemap rights | Credit NASA Science/Photojournal. No endorsement. Event occurrence date remains unknown |
| reliefweb — OCHA ReliefWeb | Planned humanitarian report API; flood/cyclone/displacement topics, global | Disabled. A pre-approved appname is required; no approval obtained or private credentials requested | Item-specific rights unresolved. No collection, caching or redistribution is enabled | Preserve original publisher rights if a future adapter is reviewed; API approval alone does not clear item rights |

The [USGS API documentation](https://earthquake.usgs.gov/fdsnws/event/1/) supports the bounded query
parameters. It recommends real-time feeds for recurring display applications where applicable; this
adapter is a limited study query, not continuous dashboard polling. REE's one-hour cache TTL is a client
choice, not a claimed provider rule.

[USGS copyrights and credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)
distinguishes USGS-produced public-domain information from third-party material. Retain attribution.
[NASA usage guidance](https://www.nasa.gov/nasa-brand-center/images-and-media/) has scope and branding
conditions; this bundle uses only the limited informational text excerpt, not NASA identifiers or imagery.
[ReliefWeb API parameters](https://apidoc.reliefweb.int/parameters) describes the pre-approved appname
requirement. These policies were reviewed through web access, which does not prove engine network access.

## Frozen source references

- [USGS Noto finite-fault source](https://earthquake.usgs.gov/earthquakes/eventpage/us6000m0xl/finite-fault)
- [USGS Taiwan finite-fault source](https://earthquake.usgs.gov/earthquakes/eventpage/us7000m9g4/finite-fault)
- [USGS Noto earthquake story](https://www.usgs.gov/news/featured-story/new-years-day-m75-earthquake-shakes-japans-west-coast)
- [NASA SWOT flooding in Bangladesh](https://science.nasa.gov/photojournal/swot-captures-flooding-in-bangladesh/)

The embedded acquisition fields identify how each record was curated. Review scientific suitability
before treating these transcriptions as analytical observations. The geographic gazetteer is a small
name/reference demonstration, not an authoritative administrative boundary dataset.

## Additional inputs and demonstrations

The three records in examples/custom_csv/fixture.csv and the external adapter output are explicitly
synthetic software tests created for REE, distributed under MIT. They demonstrate configuration and
extension behavior; they are not observations or evidence of real hazards. No private corpus was used.

User-local sources default to sensitive and unapproved for redistribution. Public mode suppresses
unapproved/sensitive records before checkpointing or exporting. A named rights basis and explicit
redistribution declaration are required to admit them publicly. Cache never stores local inputs.
Source-adapter extensions must supply a separate source identity and permitted-storage metadata.
