#!/usr/bin/env python3
from configparser import ConfigParser
import socket

from re2oapi import Re2oAPIClient
from django.core.mail import send_mail
from django.template import loader, Context

import os
import grp

config = ConfigParser()
config.read('config.ini')

api_hostname = config.get('Re2o', 'hostname')
api_password = config.get('Re2o', 'password')
api_username = config.get('Re2o', 'username')

api_client = Re2oAPIClient(api_hostname,api_username,api_password)

client_hostname = socket.gethostname().split('.',1)[0]

def reconfigure(api_client):

    users = api_client.list("users/homecreation")

    error = False

    for user in users:
        print('creation du home de {}'.format(user['pseudo']))
        home = '/home-adh/{}/{}/'.format(user['pseudo'][0].lower(),user['pseudo'].lower())
        uid = user['uid']
        gid = user['gid']

        if not os.path.exists(home):  # Home dosen't exist, create it
            os.makedirs(home,0o701)
            os.chown(home,int(uid),int(gid))
        
        # Mail
        if not os.path.exists(home + '/Mail'):
            os.makedirs(home + '/Mail', 0o700)
        os.chown(home + '/Mail', int(uid), int(gid))
        if not os.path.exists('/home-adh/mail/' + user['pseudo']):
            os.makedirs('/home-adh/mail/' + user['pseudo'], 0o700)
        os.chown('/home-adh/mail/' + user['pseudo'], int(uid), 8)

        # Owncloud dans le home
        if not os.path.exists(home + '/OwnCloud'):
            os.makedirs(home + '/OwnCloud')
        os.chown(home + '/OwnCloud',int(uid),grp.getgrnam('www-data').gr_gid)
        os.chmod(home + '/OwnCloud', 0o770)

        # Simlink
        link = '/home-adh/{}'.format(user['pseudo'].lower())
        if not os.path.islink(link):
            os.symlink(home, link)

        if not (os.path.exists(home+'/Mail') and os.path.exists(home+'OwnCloud') and os.path.islink(link)):
            error = True

        print("error: {}".format(error))
        input("passer au suivant ?")

    api_client.patch(service['home'], data={'need_regen': error})  # regen it if there is an error

for service in api_client.list("services/regen/"):
    if service['hostname'] == client_hostname and \
        service['service_name'] == 'dns' and \
        service['need_regen']:
        reconfigure(api_client)
        api_client.patch(service['api_url'], data={'need_regen': False})
