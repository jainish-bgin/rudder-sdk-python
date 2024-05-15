# Changelog

All notable changes to this project will be documented in this file. 

## [2.0.0]
## Features
- Update SDK with latest code.
- Update tests with latest dependencies 
## Breaking Changes
- Updated package name to rudderstack.analytics
- Added optional gzip capabilities
- Batch size reduced to 500KB
- Max message size reduced to 32KB
- flush_at is now renamed to upload_size
- flush_interval renamed to upload_interval
- Removed support for python 3.6

## [2.0.1]
## Fixes
- Default gzip value is set to True

## [2.0.2]
## Fixes
- Fixed dataPlaneUrl setter issue [#20](https://github.com/rudderlabs/rudder-sdk-python/issues/20)

## [2.1.0]
## Fixes
- Fixed versions of dependencies. Moved to use flexible depencencies.
- Updated License

## [2.1.1]
## Fixes
- Fixed versions of dotenv dependency. Moved to use a higher upper limit (2.0.0)
- Updated License
