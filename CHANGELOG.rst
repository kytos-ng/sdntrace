#########
Changelog
#########
All notable changes to the sdntrace NApp will be documented in this file.

[UNRELEASED] - Under development
********************************

[2025.2.0] - 2026-02-02
***********************

Fixed
=====
- Catching pickle error to avoid crashing for invalid packets.
- Fixed dl_src openapi type as str

Changed
=======
- Internal refactoring updating UI components to use ``pinia``
- Busy waiting has been changed to queue based processing.
- Removed ``requests``, using ``httpx`` to send requests.
- Removed ``TRACE_INTERVAL`` from settings. The traces will be processed as soon as possible.

Added
=====
- Added field to request when making a trace called ``timeout``. If present in the request, modifies the time to wait for a response of the packet out when tracing.

[2025.1.0] - 2025-04-14
***********************

Changed
=======
- Updated watchers

Added
=====
- Inputs used for display only were disabled

Fixed
=====
- Fixed the CSS for the ``k-input-auto``

[2024.1.1] - 2024-09-12
***********************

Fixed
=====
- Fixed bug when fetching an in progress trace

[2024.1.0] - 2024-07-23
***********************

Changed
=======
- Updated python environment installation from 3.9 to 3.11
- Added versioning to API requests
- Upgraded UI framework to Vue3 

Added
=====
- Added support for TCP and UDP protocols.
- Added UI components to send a request, display a single trace, and display all traces.

[2023.1.0] - 2023-06-06
***********************

General Information
===================
- ``@rest`` endpoints are now run by ``starlette/uvicorn`` instead of ``flask/werkzeug``.

Added
=====
- Added support to send an untagged Ethernet frame

Changed
=======
- ``eth`` dict payload is no longer mandatory, if it's not set, it's considered a untagged frame, same behavior as ``sdntrace_cp``.

[2022.3.0] - 2022-12-15
***********************

Removed
=======
- Removed support for OpenFlow 1.0

[2022.2.1] - 2022-08-15
***********************

Fixed
=====
- Made a shallow copy when iterating on shared data structure to avoid RuntimeError size changed


[2022.2.0] - 2022-08-08
***********************

Changed
=======
- KytosEvent PacketOut is now being prioritized on ``msg_out`` for OpenFlow1.3

General Information
===================
- Increased unit test coverage to at least 85%

[2022.1.0] - 2022-02-08
***********************

Added
=====
- Enhanced and standardized setup.py `install_requires` to install pinned dependencies
