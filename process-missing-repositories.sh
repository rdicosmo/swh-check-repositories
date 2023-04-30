#!/usr/bin/env bash

set -e

if [ ! -z "${_SWH_CHECK_REPOSITORIES_DEBUG}" ]; then
    set -x
fi

[ -z "${GHB_TOKEN}" ] \
    && echo "Missing env variable GHB_TOKEN set with a GitHub bearer token." \
    && exit 1

[ -z "${SWH_TOKEN}" ] \
    && echo "Missing env variable SWH_TOKEN set with a SWH bearer token." \
    && exit 1

tmpdir="swh-check-repositories-$$"
tmppath="/tmp/${tmpdir}"
mkdir -p $tmppath

# In debug mode, this keeps the temporary working directory on your machine. Otherwise,
# the default, this drops the intermediary temporary folder when the script is done.
if [ -z "${_SWH_CHECK_REPOSITORIES_DEBUG}" ]; then
    trap 'rm -rf "$tmppath"' EXIT
fi

INPUT=${1-fulldata.txt}
OUTPUT=${2-priority.list.github}

FULLDATA_LOG=$tmppath/fulldata.log
FORKED_LOG=$tmppath/forked.log
FORKED_DATA=$tmppath/forked.data
LIST_WORKING_DATA=$tmppath/fulldata.data
LIST_NON_FORKS=$tmppath/nonfork.list
LIST_FORKS=$tmppath/forked.list
LIST_PRIORITY=$OUTPUT.full

python3 get-repos-info.py -t "$GHB_TOKEN" -a "$SWH_TOKEN" \
  $INPUT > $LIST_WORKING_DATA 2> $FULLDATA_LOG

# Extract the nonfork repositories that are still in GitHub, and sort them by number of stars
grep -v ISFORK $LIST_WORKING_DATA | sed 's/;.*;/;/' | sort -t \; -k 2 -n -r \
  | grep -v NOTINGITHUB > $LIST_NON_FORKS

# Extract original repository from fork projects
grep ISFORK $LIST_WORKING_DATA | sed 's/.*ISFORK;//' | sed 's/[^;]*;//' \
  | sed 's/;.*//' | sort -u > $LIST_FORKS

# Process the forked list, extract repos still to be archived, sort them by number of
# stars
python3 get-repos-info.py -t "$GHB_TOKEN" -a "$SWH_TOKEN" \
  $LIST_FORKS > $FORKED_DATA 2> $FORKED_LOG

egrep -v "NOTING|UPTODATE|NOWPRIVATE|TOUPDATE" $FORKED_DATA | sed 's/;.*;/;/' | \
  sort -t \; -k 2 -n -r

# Merge with the nonfork.list
cat $LIST_FORKS $LIST_NON_FORKS | sort -u > $LIST_PRIORITY

# Remove number of stars
sed 's/;.*//' $LIST_PRIORITY > $OUTPUT
