Process list of repository URLS that are potentially missing from SWH
=====================================================================

Notice: the tool and process is tailored to GitHub, but it should be straightforward
        to adapt it for other forge technologies

Tools
-----

get-repos-info.py

take a list of github repository urls and output relevant information in the form of a semi-colon separated lines containing the following fields
 * canonicalurl: canonical url of the repository on GitHub
 * number of commits: number of commits (provides estimate of size of repository)
 - lastcommitdate: date of last commit on GitHub
 - swhlastvisit: date of last visit from SWH
 - visitstatus: status of the last visit as returned by SWH
 - status: summary of repository status, can be one of the following: UPTODATE, TOUPDATE, NOTINSWH, NOTINGITHUB, NOWPRIVATEONGITHUB
 - isfork: ISFORK if this repository is an explicit fork
 - forkurl: url of the repository that has been forked to create this one
 - sourceurl: url of the original repository at the root of the fork chain
 - stars: number of stars on github

Example processing
==================

From [issue 5823 we get 28198 repository urls](https://forge.softwareheritage.org/T4400#88794) that failed git ingestion, in the file
`fulldata.txt`; we want to get the relevant nonfork repositories to ingest.
We need bearer tokens for the GH API and the SWH API, we suppose they are stored
in the files `github-token` and `swh-api-token` respectively.

Step 1
------

```
python3 get-repos-info.py -t `cat github-token` -a `cat swh-api-token` fulldata.txt > fulldata.data 2>fulldata.log
```

Step 2
------
Extract the nonfork repositories that are still in GitHub, and sort them by number of stars

```
grep -v ISFORK fulldata.data | sed 's/;.*;/;/' | sort -t \; -k 2 -n -r | grep -v NOTINGITHUB > nonfork.list
```

Step 3
------
Extract original repository from fork projects

```
grep ISFORK fulldata.data | sed 's/.*ISFORK;//' | sed 's/[^;]*;//' | sed 's/;.*//' | sort -u > forked.txt
```

Step 4
------
Process the forked list, extract repos still to be archived, sort them by number of stars

```
python3 get-repos-info.py -t `cat github-token` -a `cat swh-api-token` forked.txt > forked.data 2>forked.log
egrep -v "NOTING|UPTODATE|NOWPRIVATE|TOUPDATE" forked.data | sed 's/;.*;/;/' | sort -t \; -k 2 -n -r 
```

Step 5
------
Merge with the nonfork.list

```
cat forked.list nonfork.list | sort -u > priority.list
```

Step 6
------
Remove number of stars

```
sed 's/;.*//' priority.list > priority.list.github
```

Step 7
------

Use `priority.list.github` to feed the loaders
