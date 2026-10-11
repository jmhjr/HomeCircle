# Follow the selected person

A single selected member now recenters the map when their usable location coordinates change. Retain the viewer’s zoom, including any manual zoom adjustment after selection. Manual panning remains until a new position arrives; battery, freshness and other members’ updates do not recenter the map. Everyone/category views retain their existing viewport behavior. Missing positions leave the viewport steady; a recovered position resumes following.

This uses existing HomeCircle snapshots and makes no additional tracker or location requests. It follows reported positions rather than predicting motion between reports. Initial member selection still zooms three levels above the overview default; Everyone and the recenter control retain their existing behavior. Normal map movement continues to pause radar animation.

Validation: 92 frontend tests pass, including real Leaflet map following, preserved zoom, unrelated-member updates, missing/recovered positions, and overview viewport retention. Existing radar, zoom, empty categories, resizing and lifecycle tests pass. Frontend-only deployment requires a browser refresh, with no HA restart. Physical DAKboard acceptance is separate. Published beta 17 assets are unchanged.

Live deployment: all 25 installed candidate files and the served card match the package. HA remains RUNNING; HomeCircle and HA Person configuration files are unchanged. Candidate ZIP SHA-256: `c8fa4f447ad8904e0a3d776d24022ee51db96a409b1ba7fdaf5ba5349e9a80c8`.
