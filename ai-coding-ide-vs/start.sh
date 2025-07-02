#!/bin/bash
set -e

# Start nginx in the background, now in foreground mode
nginx &

# Start code-server in the foreground
exec code-server /root/sandbox