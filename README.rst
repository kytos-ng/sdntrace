|Tag| |License|

.. raw:: html

  <div align="center">
    <h1><code>amlight/sdntrace</code></h1>

    <strong> Napp that traces OpenFlow paths in the data plane</strong>

    <h3><a href="https://kytos-ng.github.io/api/sdntrace.html">OpenAPI Docs</a></h3>
  </div>


Overview
========
An OpenFlow Path Trace for Kytos SDN controller v0.3

Requirements
============

- `amlight/coloring <https://github.com/amlight/coloring>`_

Modus operandi
==============
The AmLight SDNTrace gets the "colored" flows from the AmLight Coloring Napp. These colors are used
to create path trace probe messages to be sent via PacketOut.

Once one submits a request via REST, it will receive a Trace ID. This Trace ID is used by the napp
to support parallel traces and to allow one to retrieve the result.

When the TraceManager receives the request, a Tracer thread is created, sending PacketOut and
looking for PacketIn. If a PacketIn is not received in 1.5s, another PacketOut is sent. Three
PacketOuts are sent before generating a TimeOut event. Once the timeout is detected, all
steps of the data plane path trace are provided via REST.

This Napp works with both OpenFlow 1.0 and 1.3. Queries and results are also available through
WEB UI.

Events
======

Subscribed
----------

- ``kytos/of_core.v0x0[14].messages.in.ofpt_packet_in``

Published
---------

kytos/of_lldp.messages.out.ofpt_packet_out
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

*buffer*: ``message_out``

Standard message out event with a PacketOut sending a specific packet

Content:

.. code-block:: python3

    { 'message': <object>, # instance of a python-openflow PacketOut message
      'destination': <object> # instance of kytos.core.switch.Connection class
    }


References
==========
This napp is based on the following ACM paper:

Agarwal, K., Rozner, E., Dixon, C., & Carter, J. (2014, August). SDN traceroute:
  Tracing SDN forwarding without changing network behavior. In Proceedings of the
  third workshop on Hot topics in software defined networking (pp. 145-150). ACM.

.. TAGs

.. |License| image:: https://img.shields.io/github/license/amlight/sdntrace.svg
   :target: https://github.com/amlight/sdntrace/blob/master/LICENSE
.. |Build| image:: https://scrutinizer-ci.com/g/amlight/sdntrace/badges/build.png?b=master
  :alt: Build status
  :target: https://scrutinizer-ci.com/g/amlight/sdntrace/?branch=master
.. |Coverage| image:: https://scrutinizer-ci.com/g/amlight/sdntrace/badges/coverage.png?b=master
  :alt: Code coverage
  :target: https://scrutinizer-ci.com/g/amlight/sdntrace/?branch=master
.. |Quality| image:: https://scrutinizer-ci.com/g/amlight/sdntrace/badges/quality-score.png?b=master
  :alt: Code-quality score
  :target: https://scrutinizer-ci.com/g/amlight/sdntrace/?branch=master
.. |Stable| image:: https://img.shields.io/badge/stability-stable-green.svg
   :target: https://github.com/amlight/sdntrace
.. |Tag| image:: https://img.shields.io/github/tag/amlight/sdntrace.svg
   :target: https://github.com/amlight/sdntrace/tags
