# State files

- `history.json` records videos only after the YouTube Data API confirms a video ID, or after the code recovers an already-uploaded run marker. It is intentionally Git-tracked: the GitHub workflow commits the small JSON file so the next scheduled runner can detect used topics and script fingerprints.
- `analytics.json` contains optional YouTube Data API snapshots of view and like counts. Retention and revenue are not inferred from endpoints that do not expose them.

Do not manually add fake video IDs or secrets. If editing history by hand, keep valid JSON and preserve the `published` array structure. Concurrent workflow runs are serialized, but direct external uploads are not tracked unless the factory can see them in the channel's recent upload history.
