Kytos SDNTrace Napp

How to try the sdntrace napp?

1 - Install Python3.6+, create an venv, download Kytos, and install mininet using the tutorial below:

  https://tutorials.kytos.io/napps/development_environment_setup/

2 - Install and Enable amlight/sdntrace napp

  kytos napps install amlight/sdntrace
  kytos napps enable amlight/sdntrace

3 - Start Mininet using the topology provided:

  sudo python3.6 loop_topology_mininet.py

4 - Depending of the pre-built test you want to use, use one of the following Bash scripts:

  flows_h1_to_h4_working.sh: Configure switches for OpenFlow and create a functional path from H1 to H4
  flows_h1_to_h4_loop.sh: Configure switches for OpenFlow and create a loop on S3 between H1 and H4

  To use, just run (add 1.0 if you want to use OpenFlow 1.0 instead of 1.3):

  sudo sh <FILE> [1.0]

5 - Open a second console and start Kytos enabling all links and switches

  kytosd -fE

  Option -f will keep the Kytosd daemon in foreground
  Option -E will enable all switches and ports

6 - Using CURL, submit trace requests using the sdntrace's REST

  curl -X PUT -d@request_trace_l2.json -H "Content-Type: application/json" http://localhost:8181/api/amlight/sdntrace/trace

  HINT: Look Kytosd's output to see Kytos running the trace in real time

7 - Using a browser or CURL, query for all traces requested so far:

  curl http://localhost:8181/api/amlight/sdntrace/trace

8 - Now, try another configuration, selecting a different file from #4 and keep playing with it. If you want to
    replicate a black hole, just mess with any OpenFlow FLOW_MOD and you will see the trace ending at a different
    point.

If you have a question or comment, just send it to sdn@amlight.net or to users@kytos.io.

Have fun!