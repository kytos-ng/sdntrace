Overview
========
An OpenFlow Path Trace for Kytos SDN controller v0.2

Requirements
============
Python: pip install dill
Kytos: amlight/coloring

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

References
==========
This napp is based on the following ACM paper:

Agarwal, K., Rozner, E., Dixon, C., & Carter, J. (2014, August). SDN traceroute:
  Tracing SDN forwarding without changing network behavior. In Proceedings of the
  third workshop on Hot topics in software defined networking (pp. 145-150). ACM.

License
=======
GPL3.0