:warning: Note: this code is not used anymore as we have chosen to use a *Matrix/Synpase* server with *Element* UI instead of *RocketChat*. But feel free to use, adapt and propose changes if needed.

# Install
* Python >= 3.6
* `pip install -r requirements.txt`

# Usage
* edit `$HOME/.ldapsync.cfg` with LDAP and RocketChat credentials
* edit `invite.sh` to map LDAP groups to RocketChat channels and/or groups
* run `$ ./invite.sh`

# Caveats
* to manage private groups, the admin user that consumes the API must be a member of this groups. this ruins the privacy of that group.
* all this is fairly untested and bare bones.
