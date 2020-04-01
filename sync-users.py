#!/usr/bin/env python3

import argparse
import configparser

from rocketchat_API.rocketchat import RocketChat
from ldap3 import Server, Connection, ALL

# arguments parsing
parser = argparse.ArgumentParser(description='Invite LDAP-group users to ROCKET-chan with:\n\n ./sync-users.py [--dry-run] LDAP-group ROCKET-chan', formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('group')
parser.add_argument('channel')
parser.add_argument('-k','--kick', help='Kicks users that do not belong to the LDAP group', required=False, action='store_true')
parser.add_argument('-p','--private', help='Select if the channel is private', required=False, action='store_true')
parser.add_argument('-n','--dry-run', help='Only print required changes', required=False, action='store_true')
parser.add_argument('-u', '--users', help='Additonal users to be added', required=False, nargs='+', default=[])
args = parser.parse_args()
should_kick = args.kick
is_private = args.private
should_apply = not args.dry_run
group = args.group
channel = args.channel
users = args.users

# constants
RC_URL = 'https://chat.example.com'
LDAP_SERVER_IP = "10.10.10.10"
LDAP_SEARCH_BASE = 'dc=example,dc=com'
# LDAP query to find users (to be tuned to sort-out irrelevant accounts)
LDAP_USER_QUERY = '(&(objectClass=person)(!(uid=appli*))(!(ou:dn:=disabled_accounts)))'

# credentials from ini file
config = configparser.ConfigParser()
config.read('/home/my/.ldapsync.cfg')
RC_ADMIN_ACCOUNT = config['rocketchat']['AdminUser']
RC_ADMIN_PASSWORD = config['rocketchat']['AdminPassword']
LDAP_BIND_ACCOUNT = config['ldap']['BindAccount']
LDAP_BIND_PASSWORD = config['ldap']['BindPassword']

# init
ldap_server = Server(LDAP_SERVER_IP, port=636, use_ssl=True, get_info=ALL)
ldap_conn = Connection(ldap_server, LDAP_BIND_ACCOUNT, LDAP_BIND_PASSWORD, auto_bind=True)
rc = RocketChat(RC_ADMIN_ACCOUNT, RC_ADMIN_PASSWORD, server_url=RC_URL)

def main():
    # get the full user list of rocket.chat server
    rc_users = {user.get("username"):user.get("_id")for user in rc.users_list(count=0).json()['users']}

    print(f"\n\nmanaging channel {channel} (apply: {should_apply}, private: {is_private})")
        
    try:
        if is_private:
            # channel is private. this is a "group" in rocket.chat terms, and we need to use different API methods
            rc_channel = rc.groups_list_all(query=f'{{"name": {{"$regex":"{channel}"}}}}').json()['groups'][0]
            rc_channel_id = rc_channel.get("_id")
            current_users = [user.get("username") for user in rc.groups_members(rc_channel_id, count=0).json()['members']]
        else:
            rc_channel = rc.channels_list(query=f'{{"name": {{"$regex":"{channel}"}}}}').json()['channels'][0]
            rc_channel_id = rc_channel.get("_id")
            current_users = [user.get("username") for user in rc.channels_members(rc_channel_id, count=0).json()['members']]
    except IndexError:
        print("> ERROR: could not find channel. check the spelling (use machine-readable name of channel) as well as the private flag.")
        return
    except KeyError:
        print("> ERROR: could not get channel members. rcadmin must be in the group to manage it!")
        return

    print(f"> found channel ID {channel} = {rc_channel_id}")
    
    desired_users = ldap_get_usernames(LDAP_USER_QUERY)
    unmatched_users = [user for user in desired_users if not user in rc_users]
    if len(unmatched_users) > 0:
        print(f"> WARNING: the following users don't yet have a rocketchat account and will be ignored:\n{unmatched_users}")
    desired_users = [user for user in desired_users if not user in unmatched_users] # ignore users that are not in rocketchat
    # filter out on whether user is in the required LDAP group
    print("before filtering, nb of users = %d" % len(desired_users))
    desired_users = [user for user in desired_users if user_in_group(user, group)] # ignore users that are not in required group
    print("after filtering, nb of users = %d" % len(desired_users))
    # add required additional users if needed
    desired_users = desired_users + users
    invite_users = [user for user in desired_users if not user in current_users]
    kick_users = [user for user in current_users if not user in desired_users]
        
    print(f"> this action will invite the following users:\n> {invite_users}")
    if should_kick:
        print(f"> this action will kick the following users:\n> {kick_users}")
        
    if should_apply:
        if is_private:
            for user in invite_users:
                rc.groups_invite(rc_channel_id, rc_users[user])
            if should_kick:
                for user in kick_users:
                    rc.groups_kick(rc_channel_id, rc_users[user])
        else:
            for user in invite_users:
                rc.channels_invite(rc_channel_id, rc_users[user])
            if should_kick:
                for user in kick_users:
                    rc.channels_kick(rc_channel_id, rc_users[user])

def ldap_get_usernames(querystring:str) -> list:
    ldap_conn.search(LDAP_SEARCH_BASE, querystring, attributes=["uid"])
    return [str(entry['uid'].values[0]).lower() for entry in ldap_conn.entries]

def get_dn_from_user(user):
    return "%s=%s,%s" % ("uid", user, "ou=users,dc=wyplay,dc=com")

def get_dn_from_group(group):
    if (group.find('-') == -1):
        return '%s=%s,%s' % ("cn", group, "ou=groups,dc=wyplay,dc=com")
    else:
        return '%s=%s,%s' % ("cn", group, "ou=packages,ou=groups,dc=wyplay,dc=com")

def user_in_group(user, group):
    group_search = get_dn_from_group(group)
    group_object = '(objectclass=%s)' % "posixGroup"
    ldap_conn.search(group_search, group_object, attributes=['memberUid'])
    if len(ldap_conn.entries) < 1:
        return False
    members = ldap_conn.entries[0].memberUid
    return user in members

if __name__ == "__main__":
   main()
