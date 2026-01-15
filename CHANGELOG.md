# Changelog

All notable changes to this project will be documented in this file.

## [1.2.2] - 2026-01-15

### UPDATE
- Fixed the extraction workflow of witchyBND. It can now be efficiently invoked via the command line. Huge thanks to @ividyon for the crucial suggestion.
- Fixed all Chinese localization issues; English text now displays correctly throughout the UI.
- Added support for importing a single XML into a specified library, with visual markers for single imports (green) and edited materials (yellow).
- Fixed a compilation bug that prevented the built program from generating the database correctly from DCX files.
- Various minor text tweaks and visual optimizations, and fixed an issue where _witchy-*.xml files were incorrectly deleted during the cleanup process.

## [1.2.1] - 2026-01-10

### Fixed
- Fixed corrupted XML data loss during export/import cycle.
- Fixed `AttributeError` in main window when adding materials.
