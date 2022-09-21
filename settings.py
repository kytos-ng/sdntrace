"""
 sdntrace settings
"""

# Default field used to define color
# It will be updated by shared.colors.Colors()
COLOR_FIELD = "dl_src"
COLOR_VALUE = "ee:ee:ee:ee:ee:"

# Interval between queries to the request_queue
TRACE_INTERVAL = 1

# OpenFlow PacketOut Action OFPP_TABLE for OF1.3
OFPP_TABLE_13 = 4294967289

# Number of Parallel Traces allowed
PARALLEL_TRACES = 10

# URL for coloring app
COLORS_URL = "http://localhost:8181/api/amlight/coloring/colors"
