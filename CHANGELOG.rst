#########
Changelog
#########
All notable changes to the sdntrace NApp will be documented in this file.

[UNRELEASED] - Under development
********************************
Added
=====

Changed
=======

Deprecated
==========

Removed
=======
- Removed support for OpenFlow 1.0

Fixed
=====

Security
========

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
