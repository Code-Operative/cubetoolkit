#!/bin/bash
# Fetch all legacy diary data from the master server
# Works much better if ssh is configured with certificates.
#
# Not very profound, this one.

SERVER="www.cubecinema.com"
USER="cube"
RSYNC="/usr/bin/rsync"

MEDIA_PATH="../media"

LOCAL_PATH="./source_data"

if [ $(hostname -s) = sparror ] ; then
echo "Running on sparror, doing local copy"
SRC_ROOT=
else
SRC_ROOT=$USER@$SERVER:
fi

# Give up if a command fails
set -e 

##############################################################################

DIARY_SERVER_PATH="/home/cube/cgi-bin/diary/data"
DIARY_LOCAL_PATH="$LOCAL_PATH/diary"

EVENTS_SERVER_PATH="/home/cube/cgi-bin/events/data"
EVENTS_LOCAL_PATH="$LOCAL_PATH/events"

MEMBERS_SERVER_FILE="/home/cube/cgi-bin/members/members.dat"
MEMBERS_LOCAL_PATH="$LOCAL_PATH/"

VOLUNTEERS_SERVER_FILE="/home/cube/cgi-bin/volunteers/notes/notes.dat"
VOLUNTEERS_LOCAL_PATH="$LOCAL_PATH/"

ROLES_SERVER_PATH="/home/cube/cgi-bin/volunteers/roles/"
ROLES_LOCAL_PATH="$LOCAL_PATH/roles/"

FORMATS_SERVER_PATH="/home/cube/cgi-bin/events/data/formats"
FORMATS_LOCAL_PATH="$LOCAL_PATH/formats"

EVENT_PHOTO_SERVER_PATH="/home/cube/htdocs/events/images/"
EVENT_PHOTO_LOCAL_PATH="$MEDIA_PATH/diary/"

VOL_PHOTO_SERVER_PATH="/home/cube/htdocs/volunteers/portraits/"
VOL_PHOTO_LOCAL_PATH="$MEDIA_PATH/volunteers/"

EVENT_PHOTO_THUMBS_SERVER_PATH="/home/cube/htdocs/events/images/thumb/"
EVENT_PHOTO_THUMBS_LOCAL_PATH="$MEDIA_PATH/diary_thumbnails/"

VOL_PHOTO_THUMBS_SERVER_PATH="/home/cube/htdocs/volunteers/portraits/thumb/"
VOL_PHOTO_THUMBS_LOCAL_PATH="$MEDIA_PATH/volunteers_thumbnails/"

INDEX_LINKS_SERVER_PATH="/home/cube/cgi-bin/toolkit/tools.dat"
INDEX_LINKS_LOCAL_PATH="$LOCAL_PATH/tools.dat"

echo "Getting Diary"
$RSYNC -av --exclude='.svn' ${SRC_ROOT}$DIARY_SERVER_PATH/*.dat $DIARY_LOCAL_PATH/
echo "Getting Events"
$RSYNC -av --exclude='.svn' ${SRC_ROOT}$EVENTS_SERVER_PATH/*.dat $EVENTS_LOCAL_PATH/
echo "Getting Event roles"
$RSYNC -av --exclude='.svn' ${SRC_ROOT}$EVENTS_SERVER_PATH/roles/* $EVENTS_LOCAL_PATH/roles/

echo "Getting Members"
$RSYNC -av --exclude='.svn' ${SRC_ROOT}$MEMBERS_SERVER_FILE $MEMBERS_LOCAL_PATH
echo "Getting Volunteer notes"
$RSYNC -av --exclude='.svn' ${SRC_ROOT}$VOLUNTEERS_SERVER_FILE $VOLUNTEERS_LOCAL_PATH
echo "Getting Volunteer roles"
$RSYNC -av --exclude='.svn' ${SRC_ROOT}$ROLES_SERVER_PATH/ $ROLES_LOCAL_PATH/
echo "Getting Event formats"
$RSYNC -av --exclude='.svn' ${SRC_ROOT}$FORMATS_SERVER_PATH/ $FORMATS_LOCAL_PATH/
echo "Getting Volunteer photos"
$RSYNC -av --exclude='.svn' --exclude='thumb' --progress ${SRC_ROOT}$VOL_PHOTO_SERVER_PATH $VOL_PHOTO_LOCAL_PATH
echo "Getting Event photos"
$RSYNC -av --exclude='.svn' --exclude='thumb' --progress ${SRC_ROOT}$EVENT_PHOTO_SERVER_PATH $EVENT_PHOTO_LOCAL_PATH
echo "Getting Volunteer thumbs"
$RSYNC -av --exclude='.svn' --progress ${SRC_ROOT}$VOL_PHOTO_THUMBS_SERVER_PATH $VOL_PHOTO_THUMBS_LOCAL_PATH
echo "Getting Event thumbs"
$RSYNC -av --exclude='.svn' --progress ${SRC_ROOT}$EVENT_PHOTO_THUMBS_SERVER_PATH $EVENT_PHOTO_THUMBS_LOCAL_PATH
echo "Getting index links"
$RSYNC -av --exclude='.svn' --progress ${SRC_ROOT}$INDEX_LINKS_SERVER_PATH $INDEX_LINKS_LOCAL_PATH

exit 0
