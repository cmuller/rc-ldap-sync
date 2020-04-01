#!/bin/sh

# arguments parsing
if [ "$1" = "-n" ]; then
    DRYRUN="--dry-run"
else
    DRYRUN=""
fi

# function ask to whether to sync or not (param = channel-name)
ask() {
    echo -n "Ok to sync ${DRYRUN} $1? (q|[Y]/n) "
    read ans
    if [ "$ans" = "q" ] ; then
        echo "Quitting.."
        exit 0
    fi
    if [ "$ans" = "n" ] ; then
        return 1
    else
        return 0
    fi
}

# Public channels = #general, #testchannel

ask CHAN && ./sync-users.py $DRYRUN ldapgroup chan

# Private groups = Places, Topics, Projects

echo "=== Topic related channels ==="
ask CHAN1 && ./sync-users.py $DRYRUN --private group1 chan1 --users supplementaryuser1 supplementaryuser2
ask CHAN2 && ./sync-users.py $DRYRUN --private group2 chan2

