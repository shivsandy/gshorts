# Assets and licensing

The renderer draws diagrams, shapes, particles, and typographic layouts directly with Pillow. It does not fetch stock footage, images, fonts, music, or remote assets at runtime. Narration is rendered locally with `espeak-ng` (preferred) or `espeak` for local development. Those programs and their voices are separately licensed by their respective projects; install them from your OS package manager and review the license applicable to your distribution and selected voice before commercial use.

The system currently adds no background music. This is intentional: generated speech remains clear and the default build has no third-party music licensing dependency. Fonts use a locally installed DejaVu Sans/Liberation Sans font when available; the workflow installs Debian's `fonts-dejavu-core` package. Consult the font package license before redistributing font files. No font binaries are committed to this repository.
